"""Helpers for downloading and handling mirror/mirror routing logic."""

import base64
from datetime import datetime
import json
import os
import re
import subprocess
import time
from itertools import cycle
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCOP, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
import requests
from squidly.db import get_db_connection


def format_tidal_image_url(image_id_or_path: str, size: int) -> str:
    """Format a Tidal CDN image URL from a UUID/path and requested square size."""
    if not image_id_or_path:
        return ''

    image_path = image_id_or_path.replace('-', '/')
    return f"https://resources.tidal.com/images/{image_path}/{size}x{size}.jpg"


def make_request_with_retry(url, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    """Make an HTTP request with exponential backoff retries."""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)

            # Retry on 5xx server errors
            if response.status_code >= 500:
                last_exception = requests.exceptions.HTTPError(f"{response.status_code}: {response.text}")
                raise last_exception

            return response

        except requests.exceptions.Timeout as e:
            last_exception = e
        except requests.exceptions.ConnectionError as e:
            last_exception = e
        except requests.exceptions.RequestException as e:
            # Some errors should not be retried
            last_exception = e

        if attempt < max_retries:
            delay = backoff_factor * (2 ** attempt)
            time.sleep(delay)

    if last_exception:
        raise last_exception
    return None


def get_online_mirror_names():
    """Return set of mirror names that are currently marked online."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM mirror_endpoints
        WHERE online = 1
        """
    )
    rows = cur.fetchall()
    conn.close()
    return {row['name'] for row in rows}


def select_next_mirror(url_iterator, allowed_names, total_count):
    if not allowed_names:
        return next(url_iterator)

    for _ in range(total_count):
        candidate = next(url_iterator)
        if candidate['name'] in allowed_names:
            return candidate

    return next(url_iterator)


# Rate-limit tuning state (in-memory).
RATE_LIMIT_HISTORY_SECONDS = 300
RATE_LIMIT_TARGET_429_RATE = 0.05
RATE_LIMIT_MIN_INTERVAL = 0.5  # seconds
RATE_LIMIT_MAX_INTERVAL = 60.0  # seconds
RATE_LIMIT_429_WINDOW_SECONDS = 120
RATE_LIMIT_SUCCESS_STREAK_FOR_DECREASE = 3
RATE_LIMIT_DECREASE_FACTOR = 0.85
RATE_LIMIT_INCREASE_FACTOR = 2.0
RATE_LIMIT_429_STEP_INTERVALS = [1.0, 2.0, 5.0, 15.0, 30.0, 60.0]

_mirror_rate_limit_state = {
    'current_interval': RATE_LIMIT_MIN_INTERVAL,
    'last_request_timestamp': None,
    'request_history': [],  # [(timestamp, status_code)]
    'consecutive_successes': 0
}


def _prune_rate_limit_history():
    cutoff = time.time() - RATE_LIMIT_HISTORY_SECONDS
    _mirror_rate_limit_state['request_history'] = [
        (t, code) for (t, code) in _mirror_rate_limit_state['request_history'] if t >= cutoff
    ]


def _get_rate_limit_recovery_factor(current_interval):
    if current_interval >= 30.0:
        return 0.5
    if current_interval >= 10.0:
        return 0.65
    if current_interval >= 2.0:
        return 0.8
    return RATE_LIMIT_DECREASE_FACTOR


def _count_recent_429s(now):
    cutoff = now - RATE_LIMIT_429_WINDOW_SECONDS
    return sum(
        1
        for (timestamp, status_code) in _mirror_rate_limit_state['request_history']
        if timestamp >= cutoff and status_code == 429
    )


def _get_rate_limit_429_interval(current_interval, recent_429_count, consecutive_successes):
    forgiveness_steps = min(2, consecutive_successes // RATE_LIMIT_SUCCESS_STREAK_FOR_DECREASE)
    effective_429_count = max(0, recent_429_count - forgiveness_steps)
    target_index = min(effective_429_count, len(RATE_LIMIT_429_STEP_INTERVALS) - 1)
    target_interval = RATE_LIMIT_429_STEP_INTERVALS[target_index]

    if current_interval >= 30.0:
        return min(RATE_LIMIT_MAX_INTERVAL, current_interval * RATE_LIMIT_INCREASE_FACTOR)

    return min(RATE_LIMIT_MAX_INTERVAL, max(current_interval, target_interval))


def _record_rate_limit_event(status_code):
    now = time.time()
    previous_successes = _mirror_rate_limit_state['consecutive_successes']
    _mirror_rate_limit_state['request_history'].append((now, status_code))
    _mirror_rate_limit_state['last_request_timestamp'] = now

    if status_code == 429:
        recent_429_count = _count_recent_429s(now)
        _mirror_rate_limit_state['consecutive_successes'] = 0
        _mirror_rate_limit_state['current_interval'] = _get_rate_limit_429_interval(
            _mirror_rate_limit_state['current_interval'],
            recent_429_count,
            previous_successes,
        )
    elif status_code >= 500 or status_code == 0:
        # transient failure, do not decay the interval quickly
        _mirror_rate_limit_state['consecutive_successes'] = 0
    else:
        _mirror_rate_limit_state['consecutive_successes'] += 1
        if _mirror_rate_limit_state['consecutive_successes'] >= RATE_LIMIT_SUCCESS_STREAK_FOR_DECREASE:
            recovery_factor = _get_rate_limit_recovery_factor(_mirror_rate_limit_state['current_interval'])
            _mirror_rate_limit_state['current_interval'] = max(
                RATE_LIMIT_MIN_INTERVAL,
                _mirror_rate_limit_state['current_interval'] * recovery_factor
            )
            _mirror_rate_limit_state['consecutive_successes'] = 0


def get_mirror_rate_limit_status():
    _prune_rate_limit_history()
    history = _mirror_rate_limit_state['request_history']
    total = len(history)
    if total == 0:
        return {
            'safe_interval': _mirror_rate_limit_state['current_interval'],
            'safe_rps': round(1.0 / _mirror_rate_limit_state['current_interval'], 2),
            'safe_rpm': round(60.0 / _mirror_rate_limit_state['current_interval'], 2),
            'error_rate_429': 0.0,
            'sample_size': 0
        }

    count_429 = sum(1 for (_, code) in history if code == 429)
    return {
        'safe_interval': _mirror_rate_limit_state['current_interval'],
        'safe_rps': round(1.0 / _mirror_rate_limit_state['current_interval'], 2),
        'safe_rpm': round(60.0 / _mirror_rate_limit_state['current_interval'], 2),
        'error_rate_429': round(count_429 / total, 4),
        'sample_size': total
    }


def enforce_mirror_rate_limit():
    last = _mirror_rate_limit_state.get('last_request_timestamp')
    if last is None:
        return

    elapsed = time.time() - last
    needed = _mirror_rate_limit_state['current_interval'] - elapsed
    if needed > 0:
        print(f"[DOWNLOAD] Rate limiter sleeping {needed:.2f}s to enforce interval { _mirror_rate_limit_state['current_interval'] }s", flush=True)
        time.sleep(needed)


def make_request_with_retry_rotating_mirrors(url_base, url_list, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    """Make an HTTP request via rotating mirrors with retry/backoff.

    Args:
        url_base: The URL path to append to the base mirror URL (e.g. "/search/?s=...").
        url_list: List of mirror dicts ({'name', 'url'}).
    """
    last_exception = None
    last_target = None

    allowed_names = get_online_mirror_names()
    if not allowed_names:
        raise RuntimeError('No online mirror endpoints available')

    total_count = len(url_list)
    url_iterator = cycle(url_list)

    rate_limit_sleep_seconds = 30
    rate_limit_attempts = 0

    for attempt in range(max_retries + 1):
        enforce_mirror_rate_limit()

        try:
            target = select_next_mirror(url_iterator, allowed_names, total_count)
            target_url = target['url'].rstrip('/')
            full_url = f"{target_url}{url_base}"
            last_target = target

            print(f"[DOWNLOAD] Trying mirror '{target['name']}' ({full_url}) attempt {attempt + 1}/{max_retries + 1}", flush=True)
            response = make_request_with_retry(full_url, method=method, timeout=timeout, backoff_factor=backoff_factor, **kwargs)

            if response is not None:
                print(f"[DOWNLOAD] Mirror '{target['name']}' returned {response.status_code} for {url_base}", flush=True)

                if response.status_code == 429:
                    _record_rate_limit_event(429)
                    if rate_limit_attempts == 0:
                        print(
                            f"[DOWNLOAD] Mirror '{target['name']}' returned 429 Too Many Requests. Waiting {rate_limit_sleep_seconds}s before retrying...",
                            flush=True
                        )
                    else:
                        print(
                            f"[DOWNLOAD] Mirror '{target['name']}' still returning 429. Doubling wait to {rate_limit_sleep_seconds}s and retrying...",
                            flush=True
                        )

                    if attempt >= max_retries:
                        last_exception = requests.exceptions.HTTPError(f"429: {response.text}")
                        continue

                    time.sleep(rate_limit_sleep_seconds)
                    rate_limit_attempts += 1
                    rate_limit_sleep_seconds *= 2
                    continue

                if response.ok:
                    _record_rate_limit_event(response.status_code)
                    return response, target

                # non-2xx response from a mirror is treated as mirror-specific failure; try next mirror
                _record_rate_limit_event(response.status_code)
                last_exception = requests.exceptions.HTTPError(f"{response.status_code}: {response.text}")
                continue

        except requests.exceptions.Timeout as e:
            _record_rate_limit_event(0)
            last_exception = e
        except requests.exceptions.ConnectionError as e:
            _record_rate_limit_event(0)
            last_exception = e
        except requests.exceptions.RequestException as e:
            _record_rate_limit_event(0)
            last_exception = e

    if last_exception:
        raise last_exception
    return None, None


def load_squid_urls():
    """Load and decode squid mirror URLs from squidurls.json."""
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)

    decoded_urls = []
    for entry in urls_data:
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')
        decoded_urls.append({'name': entry['name'], 'url': decoded_url})

    return decoded_urls


def seed_mirrors_from_json():
    """Seed mirror_endpoints table from squidurls.json."""
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)

    conn = get_db_connection()
    cur = conn.cursor()

    # Clear existing entries
    cur.execute('DELETE FROM mirror_endpoints')

    # Insert fresh data from JSON with initial values
    for entry in urls_data:
        cur.execute(
            """
            INSERT INTO mirror_endpoints (name, encoded_url, online, response_time, last_checked)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (entry.get('name'), entry.get('encodedUrl'), 0, None, None)
        )

    conn.commit()
    conn.close()


def validate_endpoint(url, name, timeout=5):
    """Validate a mirror endpoint and return status info."""
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        start_time = time.time()
        response = requests.get(f"{url}/", timeout=timeout)
        response_time = (time.time() - start_time) * 1000

        online = False
        error = None

        if response.status_code == 200:
            try:
                response.json()
                online = True
            except json.JSONDecodeError:
                error = 'Invalid JSON response'
        else:
            error = f'HTTP {response.status_code}'

        return {
            'online': online,
            'responseTime': round(response_time, 2) if online else None,
            'lastChecked': timestamp,
            'error': error
        }

    except requests.exceptions.Timeout:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'error': 'Timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'error': str(e)
        }


def validate_all_endpoints():
    """Validate all squid mirror endpoints and update database state."""
    print("\n" + "=" * 60, flush=True)
    print("Starting Squid URL Validation", flush=True)
    print("=" * 60, flush=True)

    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)

    online_count = 0
    offline_count = 0

    conn = get_db_connection()
    cur = conn.cursor()

    for entry in urls_data:
        name = entry['name']
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')

        print(f"\n[{name}] Checking {decoded_url}...", flush=True)
        result = validate_endpoint(decoded_url, name, timeout=5)

        cur.execute(
            """
            UPDATE mirror_endpoints
            SET online = %s, response_time = %s, last_checked = %s
            WHERE name = %s
            """,
            (
                1 if result['online'] else 0,
                result['responseTime'],
                result['lastChecked'],
                name
            )
        )

        if result['online']:
            online_count += 1
            print(f"  ✓ ONLINE - Response time: {result['responseTime']}ms", flush=True)
        else:
            offline_count += 1
            print(f"  ✗ OFFLINE - {result.get('error', 'Unknown error')}", flush=True)

    conn.commit()
    conn.close()

    print("\n" + "=" * 60, flush=True)
    print("Validation Complete", flush=True)
    print("=" * 60, flush=True)
    print(f"Total endpoints: {len(urls_data)}", flush=True)
    print(f"Online: {online_count}", flush=True)
    print(f"Offline: {offline_count}", flush=True)
    print("=" * 60 + "\n", flush=True)

    return {
        'total': len(urls_data),
        'online': online_count,
        'offline': offline_count
    }


def sanitize_filename_component(value: str) -> str:
    """Sanitize a single component used in filesystem paths."""
    if not value:
        return ''

    sanitized = value.replace('/', '-').replace('\\', '-')
    sanitized = sanitized.replace('<', '').replace('>', '')
    sanitized = sanitized.replace(':', '-').replace('"', "'")
    sanitized = sanitized.replace('|', '-')
    sanitized = sanitized.replace('?', '')
    sanitized = sanitized.replace('*', '')

    # Replace Unicode quotes and apostrophes with ASCII equivalents
    for src, dst in [
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
        ('', '-'),
    ]:
        sanitized = sanitized.replace(src, dst)

    return sanitized


def clean_path_components(file_path: str) -> str:
    """Ensure each path component is clean and no unsafe traversal is possible."""
    parts = [p for p in file_path.split('/') if p and p not in ('.', '..')]
    return '/'.join(parts)


def extract_year_from_text(text: str) -> str:
    """Extract a four-digit year from arbitrary text."""
    if not text or not isinstance(text, str):
        return ''
    m = re.search(r'(19|20)\d{2}', text)
    return m.group(0) if m else ''


def detect_audio_format(data: bytes) -> str:
    """Detect audio format by checking magic bytes."""
    if len(data) < 12:
        return 'unknown'

    if data[:4] == b'fLaC':
        return 'flac'

    if len(data) >= 12 and data[4:8] == b'ftyp':
        if data[8:12] in [b'M4A ', b'mp42', b'isom', b'iso2']:
            return 'm4a'

    if data[:3] == b'ID3' or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return 'mp3'

    return 'unknown'


def cleanup_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"[DOWNLOAD] Cleaned up temporary file", flush=True)
    except Exception as e:
        print(f"[DOWNLOAD] WARNING: Failed to clean up temp file: {str(e)}", flush=True)


def add_id3_tags_to_file(file_path, metadata, cover_image_data=None):
    """Add metadata tags to FLAC, M4A, or MP3 files."""
    try:
        artist = metadata.get('artist', 'Unknown Artist')
        title = metadata.get('title', 'Unknown Track')
        album = metadata.get('album', 'Unknown Album')
        year = metadata.get('year', '')
        track_num = metadata.get('track_number', '1')
        disc_num = metadata.get('disc_number', '')
        copyright_text = metadata.get('copyright', '')
        tidal_track_id = metadata.get('tidal_track_id', None)
        tidal_album_id = metadata.get('tidal_album_id', None)

        # Handle FLAC files
        if file_path.lower().endswith('.flac'):
            try:
                audio = FLAC(file_path)
                audio['TITLE'] = title
                audio['ARTIST'] = artist
                audio['ALBUM'] = album
                if year:
                    audio['DATE'] = str(year)
                if copyright_text:
                    audio['COPYRIGHT'] = copyright_text
                if tidal_track_id:
                    audio['TIDAL_TRACK_ID'] = str(tidal_track_id)
                if tidal_album_id:
                    audio['TIDAL_ALBUM_ID'] = str(tidal_album_id)
                audio['TRACKNUMBER'] = str(track_num)
                if disc_num:
                    audio['DISCNUMBER'] = str(disc_num)

                # Add cover art if available
                if cover_image_data:
                    from mutagen.flac import Picture
                    pic = Picture()
                    pic.data = cover_image_data
                    pic.type = 3  # Cover (front)
                    pic.mime = 'image/jpeg'
                    audio.add_picture(pic)

                audio.save()
                print(f"[ID3] Successfully added FLAC metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write FLAC tags: {str(e)}", flush=True)

        # Handle M4A/AAC files
        elif file_path.lower().endswith('.m4a'):
            try:
                audio = MP4(file_path)
                audio['\xa9nam'] = title
                audio['\xa9ART'] = artist
                audio['\xa9alb'] = album

                if year:
                    audio['\xa9day'] = str(year)

                if copyright_text:
                    audio['\xa9c'] = str(copyright_text)

                if tidal_track_id:
                    audio['----:com.apple.iTunes:tidal_track_id'] = [str(tidal_track_id).encode('utf-8')]
                if tidal_album_id:
                    audio['----:com.apple.iTunes:tidal_album_id'] = [str(tidal_album_id).encode('utf-8')]

                if track_num:
                    try:
                        track_number = int(track_num)
                        audio['trkn'] = [(track_number, 0)]
                    except ValueError:
                        pass

                if disc_num:
                    try:
                        disc_number = int(disc_num)
                        audio['disk'] = [(disc_number, 0)]
                    except ValueError:
                        pass

                if cover_image_data:
                    audio['covr'] = [MP4Cover(cover_image_data, imageformat=MP4Cover.FORMAT_JPEG)]

                audio.save()
                print(f"[ID3] Successfully added M4A metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write M4A tags: {str(e)}", flush=True)

        # Handle MP3 files
        elif file_path.lower().endswith('.mp3'):
            try:
                try:
                    audio = MP3(file_path, ID3=ID3)
                except:
                    audio = MP3(file_path)
                    audio.add_tags()

                # Remove existing tags to ensure clean slate
                audio.delete()
                audio = MP3(file_path)
                audio.add_tags()

                # Add text tags
                audio['TIT2'] = TIT2(encoding=3, text=title)
                audio['TPE1'] = TPE1(encoding=3, text=artist)
                audio['TALB'] = TALB(encoding=3, text=album)
                if year:
                    audio['TDRC'] = TDRC(encoding=3, text=str(year))
                if copyright_text:
                    audio['TCOP'] = TCOP(encoding=3, text=copyright_text)
                if tidal_track_id:
                    audio['TXXX:tidal_track_id'] = TXXX(encoding=3, desc='tidal_track_id', text=str(tidal_track_id))
                if tidal_album_id:
                    audio['TXXX:tidal_album_id'] = TXXX(encoding=3, desc='tidal_album_id', text=str(tidal_album_id))
                audio['TRCK'] = TRCK(encoding=3, text=str(track_num))
                if disc_num:
                    audio['TPOS'] = TPOS(encoding=3, text=str(disc_num))

                # Add cover art if available
                if cover_image_data:
                    audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_image_data)

                audio.save(v2_version=4)
                print(f"[ID3] Successfully added MP3 metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write MP3 tags: {str(e)}", flush=True)
                
    except Exception as e:
        print(f"[ID3] Error adding ID3 tags: {str(e)}", flush=True)


def download_cover_image(cover_url):
    """
    Download album cover image from URL.
    Returns binary image data or None if download fails.
    """
    if not cover_url:
        print(f"[COVER] No cover URL provided", flush=True)
        return None
    
    try:
        print(f"[COVER] Downloading cover image from: {cover_url}", flush=True)
        response = requests.get(cover_url, timeout=10)
        
        if response.ok:
            print(f"[COVER] Successfully downloaded cover image ({len(response.content)} bytes)", flush=True)
            return response.content
        else:
            print(f"[COVER] Failed to download cover image. Status: {response.status_code}", flush=True)
            return None
    except requests.exceptions.Timeout:
        print(f"[COVER] ERROR: Timeout downloading cover image from {cover_url}", flush=True)
        return None
    except Exception as e:
        print(f"[COVER] Error downloading cover image: {str(e)}", flush=True)
        return None


def convert_to_mp3(source_path: str, mp3_path: str, source_format: str = 'audio') -> bool:
    """
    Convert an audio file (e.g., FLAC or M4A/AAC) to highest VBR quality MP3 using ffmpeg.

    Args:
        source_path: Path to the source audio file
        mp3_path: Path where the MP3 should be saved
        source_format: Source format label for logging

    Returns:
        True on success, False on failure
    """
    try:
        print(
            f"[FFMPEG] Converting {source_format.upper()} to MP3 (highest VBR quality): {source_path} -> {mp3_path}",
            flush=True
        )

        mp3_dir = os.path.dirname(mp3_path)
        if mp3_dir:
            os.makedirs(mp3_dir, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-i', source_path,
            '-c:a', 'libmp3lame',
            '-q:a', '0',
            '-y',
            mp3_path
        ]

        print(f"[FFMPEG] Command: {' '.join(cmd)}", flush=True)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"[FFMPEG] SUCCESS: Converted to {mp3_path}", flush=True)
            return True

        print(f"[FFMPEG] ERROR: Conversion failed with code {result.returncode}", flush=True)
        print(f"[FFMPEG] stderr: {result.stderr}", flush=True)
        return False

    except subprocess.TimeoutExpired:
        print(f"[FFMPEG] ERROR: Conversion timeout", flush=True)
        return False
    except Exception as e:
        print(f"[FFMPEG] ERROR: {str(e)}", flush=True)
        return False
