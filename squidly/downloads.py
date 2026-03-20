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
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK, TPOS
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

    for attempt in range(max_retries + 1):
        try:
            target = select_next_mirror(url_iterator, allowed_names, total_count)
            target_url = target['url'].rstrip('/')
            full_url = f"{target_url}{url_base}"
            last_target = target

            response = make_request_with_retry(full_url, method=method, timeout=timeout, backoff_factor=backoff_factor, **kwargs)
            if response is not None:
                return response, target

        except requests.exceptions.Timeout as e:
            last_exception = e
        except requests.exceptions.ConnectionError as e:
            last_exception = e
        except requests.exceptions.RequestException as e:
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

        # Handle FLAC files
        if file_path.lower().endswith('.flac'):
            try:
                audio = FLAC(file_path)
                audio['TITLE'] = title
                audio['ARTIST'] = artist
                audio['ALBUM'] = album
                if year:
                    audio['DATE'] = str(year)
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
