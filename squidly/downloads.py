"""Helpers for downloading and handling mirror/mirror routing logic."""

import base64
from datetime import datetime
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from threading import Lock
import time
from itertools import cycle
from urllib.parse import urljoin, urlencode, urlparse
from mutagen.flac import FLAC
from mutagen.mp4 import MP4, MP4Cover
import requests
from squidly.db import get_db_connection
from squidly.utils import clean_path_components, extract_year_from_text, sanitize_filename_component
from squidly.services import qobuz

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQUID_URLS shared accessor
# ---------------------------------------------------------------------------
# Cache for enabled mirror URLs, populated at app startup.
# Use refresh_squid_urls() to update the cache.
# Use get_squid_urls() to read the current cache.

_SQUID_URLS_CACHE = []


def get_squid_urls():
    """Return the current cache of enabled mirror URLs."""
    return _SQUID_URLS_CACHE


def refresh_squid_urls():
    """Refresh the SQUID_URLS cache from the database."""
    global _SQUID_URLS_CACHE
    _SQUID_URLS_CACHE = load_enabled_mirror_urls()


# ---------------------------------------------------------------------------
# Download-specific error classes
# ---------------------------------------------------------------------------
# These inherit from the generic RetryableError/PermanentError in jobs.py
# so the generic worker_loop() catches them correctly.

from squidly.job_queue import RetryableError, PermanentError


class ManifestDownloadError(RetryableError):
    """Raised when a manifest fetch fails (triggers retry)."""
    pass


class TransientDownloadError(RetryableError):
    """Raised when a temporary/download failure occurs (triggers retry)."""
    pass


class PermanentDownloadError(PermanentError):
    """Raised when a non-retryable download failure occurs (immediate fail)."""
    pass


def download_track_all_stages_done(stages):
    """Check if all required download track stages are complete.

    Returns True if downloaded, tagged, and written are 'done',
    and converted is either 'done' or 'skipped'.
    """
    if not isinstance(stages, dict):
        return False

    required_stages = (
        'downloaded',
        'tagged',
        'written'
    )
    if not all(stages.get(stage_name) == 'done' for stage_name in required_stages):
        return False

    if stages.get('converted') not in ('done', 'skipped'):
        return False

    return True


def format_tidal_image_url(image_id_or_path: str, size: int) -> str:
    """Format a Tidal CDN image URL from a UUID/path and requested square size."""
    if not image_id_or_path:
        return ''

    image_path = image_id_or_path.replace('-', '/')
    return f"https://resources.tidal.com/images/{image_path}/{size}x{size}.jpg"


HLS_TAG_MAP_RE = re.compile(r'#EXT-X-MAP:.*URI="([^"]+)"')

QUALITY_PRESETS = {
    'DOLBY_ATMOS': (['EAC3_JOC'], 'MPEG_DASH'),
    'HIRES_LOSSLESS': (['FLAC_HIRES'], 'HLS'),
    'HI_RES_LOSSLESS': (['FLAC_HIRES'], 'HLS'),
    'LOSSLESS': (['FLAC'], 'HLS'),
    'HIGH': (['AACLC'], 'HLS'),
    'LOW': (['HEAACV1'], 'HLS'),
}


def resolve_formats_and_manifest_type(
    quality: str | None,
    manifest_type: str | None = None,
) -> tuple[list[str], str]:
    quality_key = str(quality or '').strip().upper()
    if quality_key in QUALITY_PRESETS:
        formats, quality_manifest = QUALITY_PRESETS[quality_key]
        manifest_type = manifest_type or quality_manifest
    else:
        formats, quality_manifest = QUALITY_PRESETS['LOSSLESS']
        manifest_type = manifest_type or quality_manifest

    return formats, manifest_type or 'HLS'


def extract_track_manifest_uri(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise ValueError('Track manifests payload is not a dictionary')

    candidates = []
    data_node = payload.get('data')
    if isinstance(data_node, dict):
        nested = data_node.get('data')
        if isinstance(nested, dict):
            data_node = nested
        if isinstance(data_node.get('attributes'), dict):
            candidates.append(data_node['attributes'].get('uri'))
        candidates.append(data_node.get('uri'))

    candidates.append(payload.get('uri'))

    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate

    raise ValueError('No manifest URI found in trackManifests payload')


def download_binary(url: str, timeout: int = 30) -> bytes:
    response = make_request_with_retry(url, method='GET', timeout=timeout, max_retries=3, allow_redirects=True)
    if response is None:
        raise requests.exceptions.RequestException(f'Failed to download binary URL: {url}')
    response.raise_for_status()
    return response.content


def ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def demux_flac(input_path: Path, output_path: Path) -> None:
    if not ffmpeg_available():
        raise RuntimeError('ffmpeg is required to demux FLAC from MP4. Install ffmpeg and retry.')

    try:
        subprocess.run(
            [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-loglevel',
                'error',
                '-i',
                str(input_path),
                '-map',
                '0:a:0',
                '-c',
                'copy',
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f'ffmpeg failed while demuxing {input_path} -> {output_path}: {exc.returncode}\n{exc.stderr}'
        ) from exc


def download_dash_audio(manifest_uri: str, output_path: Path) -> None:
    if not ffmpeg_available():
        raise RuntimeError('ffmpeg is required to download DASH audio. Install ffmpeg and retry.')

    try:
        subprocess.run(
            [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-loglevel',
                'error',
                '-protocol_whitelist',
                'file,http,https,tcp,tls,crypto',
                '-i',
                manifest_uri,
                '-map',
                '0:a:0',
                '-c',
                'copy',
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f'ffmpeg failed while downloading DASH audio from {manifest_uri} -> {output_path}: {exc.returncode}\n{exc.stderr}'
        ) from exc


def parse_hls_playlist(text: str, playlist_url: str):
    init_uri = None
    segment_uris = []
    variant_uri = None

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if line.startswith('#EXTM3U'):
            continue

        if line.startswith('#EXT-X-STREAM-INF'):
            for next_line in lines[index + 1 :]:
                if not next_line.startswith('#'):
                    variant_uri = urljoin(playlist_url, next_line)
                    break
            break

        if line.startswith('#EXT-X-MAP'):
            match = HLS_TAG_MAP_RE.search(line)
            if match:
                init_uri = match.group(1)
            continue

        if line.startswith('#'):
            continue

        segment_uris.append(urljoin(playlist_url, line))

    if variant_uri:
        return None, [variant_uri]

    if not segment_uris:
        raise ValueError('No segment URIs found in the HLS playlist')

    if init_uri:
        init_uri = urljoin(playlist_url, init_uri)

    return init_uri, segment_uris


def download_track_manifest(
    track_id: str,
    output_path,
    quality: str | None,
    url_list,
    usage: str = 'DOWNLOAD',
    manifest_type: str | None = None,
    for_download: bool = False,
):
    formats, manifest_type = resolve_formats_and_manifest_type(quality, manifest_type)
    params = {
        'id': str(track_id),
        'formats': ','.join(formats),
        'usage': usage,
        'manifestType': manifest_type,
        'adaptive': 'true',
        'uriScheme': 'HTTPS',
    }

    response, target = make_request_with_retry_rotating_mirrors(
        f"/trackManifests/?{urlencode(params)}",
        url_list,
        method='GET',
        timeout=10,
        max_retries=3,
        for_download=for_download,
        mirror_type='tidal',
    )
    if not response.ok:
        raise requests.exceptions.HTTPError(f"Failed to fetch track manifest for {track_id}: {response.status_code}")

    payload = response.json() or {}
    manifest_uri = extract_track_manifest_uri(payload)

    playlist_resp = make_request_with_retry(manifest_uri, method='GET', timeout=30, max_retries=3, allow_redirects=True)
    if playlist_resp is None:
        raise requests.exceptions.RequestException(f'Failed to fetch track manifest URI: {manifest_uri}')
    playlist_resp.raise_for_status()

    playlist_uri = manifest_uri
    playlist_text = playlist_resp.text

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    intermediate_path = output_path
    should_demux = formats[0].upper() in {'FLAC', 'FLAC_HIRES'} and output_path.suffix.lower() == '.flac'

    if output_path.suffix.lower() == '.flac' and formats[0].upper() not in {'FLAC', 'FLAC_HIRES'}:
        raise ValueError('Only FLAC/FLAC_HIRES formats support .flac output when using HLS. Use a different output extension or format.')

    if should_demux:
        intermediate_path = output_path.with_suffix('.m4a')

    try:
        if manifest_type == 'HLS' or playlist_uri.endswith('.m3u8') or '#EXTM3U' in playlist_text:
            init_uri, segment_uris = parse_hls_playlist(playlist_text, playlist_uri)
            if '#EXT-X-STREAM-INF' in playlist_text and segment_uris:
                playlist_uri = segment_uris[0]
                playlist_resp = make_request_with_retry(playlist_uri, method='GET', timeout=30, max_retries=3, allow_redirects=True)
                if playlist_resp is None:
                    raise requests.exceptions.RequestException(f'Failed to fetch HLS variant playlist: {playlist_uri}')
                playlist_resp.raise_for_status()
                playlist_text = playlist_resp.text
                init_uri, segment_uris = parse_hls_playlist(playlist_text, playlist_uri)

            logger.info("[DOWNLOAD] Found %d segment URIs", len(segment_uris))
            if init_uri:
                logger.info("[DOWNLOAD] Found init segment URI")

            with intermediate_path.open('wb') as output_file:
                if init_uri:
                    logger.info("[DOWNLOAD] Downloading HLS init segment")
                    try:
                        output_file.write(download_binary(init_uri))
                    except Exception as exc:
                        raise RuntimeError(f'Failed to download HLS init segment: {init_uri}') from exc

                logger.info("[DOWNLOAD] Downloading %d HLS segments", len(segment_uris))
                downloaded_segments = 0
                for segment_url in segment_uris:
                    try:
                        output_file.write(download_binary(segment_url))
                    except Exception as exc:
                        raise RuntimeError(
                            f'Failed to download HLS segment {downloaded_segments + 1}/{len(segment_uris)}'
                        ) from exc
                    downloaded_segments += 1

                logger.info("[DOWNLOAD] Downloaded %d/%d HLS segments", downloaded_segments, len(segment_uris))

            if should_demux:
                logger.info("[DOWNLOAD] Demuxing FLAC from MP4 container: %s -> %s", intermediate_path, output_path)
                demux_flac(intermediate_path, output_path)
                intermediate_path.unlink()
                logger.info("[DOWNLOAD] Demux complete: %s", output_path)
            else:
                logger.info("[DOWNLOAD] Download complete: %s", output_path)

        elif manifest_type == 'MPEG_DASH' or playlist_uri.endswith('.mpd') or '<MPD' in playlist_text:
            if output_path.suffix.lower() == '.mpd':
                logger.info("[DOWNLOAD] Saving MPEG-DASH manifest to: %s", output_path)
                output_path.write_bytes(playlist_resp.content)
                logger.info("[DOWNLOAD] MPEG-DASH manifest saved. Media segment download is not implemented in this helper.")
            else:
                logger.info("[DOWNLOAD] Downloading MPEG-DASH audio from manifest: %s", playlist_uri)
                download_dash_audio(playlist_uri, output_path)
                logger.info("[DOWNLOAD] Download complete: %s", output_path)
        else:
            raise ValueError('Unsupported manifest type or response content for download.')
    except Exception:
        if should_demux and intermediate_path.exists():
            try:
                intermediate_path.unlink()
            except Exception:
                pass
        raise

    return str(output_path), target


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


def get_online_mirror_names(mirror_type=None):
    """Return set of mirror names that are currently marked online and enabled.

    Args:
        mirror_type: Optional filter for mirror type ('tidal' or 'qobuz').
    """
    conn = get_db_connection()
    cur = conn.cursor()
    if mirror_type:
        cur.execute(
            """
            SELECT name
            FROM mirror_endpoints
            WHERE online = 1 AND enabled = 1 AND mirror_type = %s
            """,
            (mirror_type,)
        )
    else:
        cur.execute(
            """
            SELECT name
            FROM mirror_endpoints
            WHERE online = 1 AND enabled = 1
            """
        )
    rows = cur.fetchall()
    conn.close()
    return {row['name'] for row in rows}


def select_next_mirror(url_iterator):
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
MIRROR_PREFERRED_PENALTY_SECONDS = 180.0

_mirror_rate_limit_state = {
    'current_interval': RATE_LIMIT_MIN_INTERVAL,
    'last_request_timestamp': None,
    'request_history': [],  # [(timestamp, status_code)]
    'consecutive_successes': 0
}

_mirror_preference_state = {
    'preferred_index': 0,
    'preferred_until': 0.0,
    'lock': Lock(),
}


def _get_ordered_online_mirrors(url_list, mirror_type=None, for_download=False):
    conn = get_db_connection()
    cur = conn.cursor()
    if mirror_type:
        cur.execute(
            """
            SELECT name, response_time
            FROM mirror_endpoints
            WHERE online = 1 AND enabled = 1 AND mirror_type = %s
            """ + (" AND downloads_enabled = 1" if for_download else ""),
            (mirror_type,)
        )
    else:
        cur.execute(
            """
            SELECT name, response_time
            FROM mirror_endpoints
            WHERE online = 1 AND enabled = 1
            """ + (" AND downloads_enabled = 1" if for_download else "")
        )
    online_rows = cur.fetchall()
    conn.close()

    response_times = {}
    for row in online_rows:
        try:
            response_times[row['name']] = float(row.get('response_time'))
        except (TypeError, ValueError):
            response_times[row['name']] = None

    eligible_urls = [
        url_info
        for url_info in url_list
        if url_info.get('name') in response_times
    ]
    if not eligible_urls:
        return []

    eligible_urls.sort(
        key=lambda candidate: response_times.get(candidate.get('name'))
        if response_times.get(candidate.get('name')) is not None
        else float('inf')
    )
    return eligible_urls


def _get_preferred_mirror_index(total_count):
    if total_count <= 0:
        return 0

    with _mirror_preference_state['lock']:
        now = time.time()
        if now < _mirror_preference_state['preferred_until']:
            return min(_mirror_preference_state['preferred_index'], total_count - 1)

        _mirror_preference_state['preferred_index'] = 0
        _mirror_preference_state['preferred_until'] = 0.0
        return 0


def _set_preferred_mirror_index(index, total_count):
    if total_count <= 0:
        return

    with _mirror_preference_state['lock']:
        _mirror_preference_state['preferred_index'] = index % total_count
        _mirror_preference_state['preferred_until'] = time.time() + MIRROR_PREFERRED_PENALTY_SECONDS


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
        logger.info("[DOWNLOAD] Rate limiter sleeping %.2fs to enforce interval %ss", needed, _mirror_rate_limit_state['current_interval'])
        time.sleep(needed)


def make_request_with_retry_rotating_mirrors(url_base, url_list, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, for_download=False, mirror_type=None, **kwargs):
    """Make an HTTP request via rotating mirrors with retry/backoff.

    Args:
        url_base: The URL path to append to the base mirror URL (e.g. "/search/?s=...").
        url_list: List of mirror dicts ({'name', 'url'}).
        for_download: If True, only consider mirrors with downloads_enabled=1.
        mirror_type: If set, only consider mirrors of this type ('tidal' or 'qobuz').
    """
    last_exception = None
    last_target = None

    eligible_urls = _get_ordered_online_mirrors(url_list, mirror_type=mirror_type, for_download=for_download)
    if not eligible_urls:
        raise RuntimeError('No configured mirror URLs are currently marked online')

    eligible_count = len(eligible_urls)
    start_index = _get_preferred_mirror_index(eligible_count)
    rotated_urls = eligible_urls[start_index:] + eligible_urls[:start_index]
    url_iterator = cycle(rotated_urls)

    rate_limit_sleep_seconds = 30
    rate_limit_attempts = 0

    for attempt in range(max_retries + 1):
        enforce_mirror_rate_limit()

        try:
            target = select_next_mirror(url_iterator)
            target_url = target['url'].rstrip('/')
            full_url = f"{target_url}{url_base}"
            last_target = target

            logger.info("[DOWNLOAD] Trying mirror '%s' (%s) attempt %d/%d", target['name'], full_url, attempt + 1, max_retries + 1)
            response = make_request_with_retry(full_url, method=method, timeout=timeout, backoff_factor=backoff_factor, **kwargs)

            if response is not None:
                logger.info("[DOWNLOAD] Mirror '%s' returned %d for %s", target['name'], response.status_code, url_base)

                if response.status_code == 429:
                    _record_rate_limit_event(429)
                    current_index = (start_index + attempt) % eligible_count
                    _set_preferred_mirror_index(current_index + 1, eligible_count)

                    if rate_limit_attempts == 0:
                        logger.info("[DOWNLOAD] Mirror '%s' returned 429 Too Many Requests. Waiting %ds before retrying...", target['name'], rate_limit_sleep_seconds)
                    else:
                        logger.info("[DOWNLOAD] Mirror '%s' still returning 429. Doubling wait to %ds and retrying...", target['name'], rate_limit_sleep_seconds)

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


def load_enabled_mirror_urls(mirror_type=None):
    """Load enabled mirror URLs from the database.

    Args:
        mirror_type: Optional filter for mirror type ('tidal' or 'qobuz').
    """
    conn = get_db_connection()
    cur = conn.cursor()
    if mirror_type:
        cur.execute(
            """
            SELECT name, encoded_url, mirror_type
            FROM mirror_endpoints
            WHERE enabled = 1 AND mirror_type = %s
            """,
            (mirror_type,)
        )
    else:
        cur.execute(
            """
            SELECT name, encoded_url, mirror_type
            FROM mirror_endpoints
            WHERE enabled = 1
            """
        )
    rows = cur.fetchall()
    conn.close()

    decoded_urls = []
    for row in rows:
        decoded_url = base64.b64decode(row['encoded_url']).decode('utf-8')
        decoded_urls.append({'name': row['name'], 'url': decoded_url, 'mirror_type': row['mirror_type']})

    return decoded_urls


def derive_mirror_name(url):
    """Derive a mirror name from a URL hostname."""
    parsed = urlparse(url)
    return parsed.hostname or url


def seed_mirrors_from_json():
    """Seed mirror_endpoints table from squidurls.json only if empty."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM mirror_endpoints')
    count = cur.fetchone()['count']
    if count > 0:
        logger.info("[MIRRORS] Skipping seed — mirror_endpoints table is not empty")
        conn.close()
        return

    logger.info("[MIRRORS] Seeding mirror_endpoints from squidurls.json")
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)

    for entry in urls_data:
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')
        name = derive_mirror_name(decoded_url)
        cur.execute(
            """
            INSERT INTO mirror_endpoints (name, encoded_url, online, response_time, last_checked, enabled, mirror_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name, entry['encodedUrl'], 0, None, None, 1, 'tidal')
        )


def add_mirror(url, mirror_type='tidal'):
    """Add a new mirror endpoint to the database from a plain URL.

    Args:
        url: The plain URL of the mirror endpoint.
        mirror_type: The type of mirror ('tidal' or 'qobuz'). Defaults to 'tidal'.
    """
    name = derive_mirror_name(url)
    encoded_url = base64.b64encode(url.encode('utf-8')).decode('utf-8')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mirror_endpoints (name, encoded_url, online, response_time, last_checked, enabled, mirror_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO NOTHING
        """,
        (name, encoded_url, 0, None, None, 1, mirror_type)
    )
    conn.commit()
    conn.close()


def remove_mirror(name):
    """Remove a mirror endpoint from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM mirror_endpoints WHERE name = %s', (name,))
    conn.commit()
    conn.close()


def toggle_mirror(name):
    """Toggle the enabled state of a mirror. Returns the new enabled state."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT enabled FROM mirror_endpoints WHERE name = %s', (name,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f'Mirror "{name}" not found')
    new_state = 0 if row['enabled'] else 1
    cur.execute('UPDATE mirror_endpoints SET enabled = %s WHERE name = %s', (new_state, name))
    conn.commit()
    conn.close()
    return new_state


def toggle_mirror_downloads(name):
    """Toggle the downloads-enabled state of a mirror. Returns the new state."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT downloads_enabled FROM mirror_endpoints WHERE name = %s', (name,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f'Mirror "{name}" not found')
    new_state = 0 if row['downloads_enabled'] else 1
    cur.execute('UPDATE mirror_endpoints SET downloads_enabled = %s WHERE name = %s', (new_state, name))
    conn.commit()
    conn.close()
    return new_state


def disable_mirror_downloads(name):
    """Disable downloads for a mirror by name.

    Sets downloads_enabled = 0 so the mirror is excluded from download
    rotation but still usable for metadata/search requests.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE mirror_endpoints SET downloads_enabled = 0 WHERE name = %s', (name,))
    conn.commit()
    conn.close()


def validate_single_endpoint(name):
    """Validate a single mirror endpoint by name."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name, encoded_url, mirror_type FROM mirror_endpoints WHERE name = %s', (name,))
    mirror = cur.fetchone()
    if mirror is None:
        conn.close()
        raise ValueError(f'Mirror "{name}" not found')
    decoded_url = base64.b64decode(mirror['encoded_url']).decode('utf-8')
    mirror_type = mirror.get('mirror_type', 'tidal')

    if mirror_type == 'qobuz':
        result = qobuz.validate_qobuz_endpoint(decoded_url, timeout=5)
    else:
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
    conn.commit()
    conn.close()
    return result


def validate_all_endpoints_from_db():
    """Validate all enabled mirror endpoints from the database and update their status."""
    logger.info("\n%s", "=" * 60)
    logger.info("Starting Squid URL Validation")
    logger.info("%s", "=" * 60)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name, encoded_url, mirror_type FROM mirror_endpoints WHERE enabled = 1')
    mirrors = cur.fetchall()
    conn.close()

    online_count = 0
    offline_count = 0

    conn = get_db_connection()
    cur = conn.cursor()

    for mirror in mirrors:
        name = mirror['name']
        mirror_type = mirror['mirror_type']
        decoded_url = base64.b64decode(mirror['encoded_url']).decode('utf-8')

        logger.info("\n[%s] Checking %s (type: %s)...", name, decoded_url, mirror_type)

        if mirror_type == 'qobuz':
            result = qobuz.validate_qobuz_endpoint(decoded_url, timeout=5)
        else:
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
            logger.info("  ✓ ONLINE - Response time: %sms", result['responseTime'])
        else:
            offline_count += 1
            logger.info("  ✗ OFFLINE - %s", result.get('error', 'Unknown error'))

    conn.commit()
    conn.close()

    logger.info("\n%s", "=" * 60)
    logger.info("Validation Complete")
    logger.info("%s", "=" * 60)
    logger.info("Total endpoints: %d", len(mirrors))
    logger.info("Online: %d", online_count)
    logger.info("Offline: %d", offline_count)
    logger.info("%s\n", "=" * 60)

    return {
        'total': len(mirrors),
        'online': online_count,
        'offline': offline_count
    }


def validate_all_endpoints():
    """Validate all squid mirror endpoints and update database state."""
    return validate_all_endpoints_from_db()


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
            logger.info("[DOWNLOAD] Cleaned up temporary file")
    except Exception as e:
        logger.info("[DOWNLOAD] WARNING: Failed to clean up temp file: %s", str(e))


def add_id3_tags_to_file(file_path, metadata, cover_image_data=None, tag_settings=None):
    """
    Add ID3 tags to an audio file (handles FLAC, MP3, and M4A/AAC).

    Args:
        file_path: Path to the audio file
        metadata: Dict with keys: artist, title, album, year, track_number, disc_number
        cover_image_data: Binary image data to embed as cover art
        tag_settings: Dict of tagging toggle settings (defaults to all True)
    """
    if tag_settings is None:
        tag_settings = {}

    def tag_enabled(key, default=True):
        return bool(tag_settings.get(key, default))

    try:
        artist = metadata.get('artist', 'Unknown Artist')
        title = metadata.get('title', 'Unknown Track')
        album = metadata.get('album', 'Unknown Album')
        year = metadata.get('year', '')
        track_num = metadata.get('track_number', '1')
        disc_num = metadata.get('disc_number', '')
        file_type = os.path.splitext(file_path)[1].lower().lstrip('.')
        logger.info("[ID3_DEBUG] Writing tags for '%s' type='%s'", file_path, file_type)
        logger.info(
            "[ID3_DEBUG] tag payload artist=%r track_artists=%r album_artist=%r album_artists=%r title=%r album=%r year=%r track_number=%r disc_number=%r version=%r isrc=%r audio_quality=%r",
            artist, metadata.get('track_artists'), metadata.get('album_artist'), metadata.get('album_artists'), title, album, year, track_num, disc_num, metadata.get('version'), metadata.get('isrc'), metadata.get('audio_quality')
        )

        # Handle FLAC files
        if file_path.lower().endswith('.flac'):
            try:
                audio = FLAC(file_path)
                audio.clear()
                if tag_enabled('tag_title'):
                    audio['TITLE'] = title
                if tag_enabled('tag_artist'):
                    if isinstance(metadata.get('track_artists'), list) and metadata.get('track_artists'):
                        audio['ARTIST'] = metadata.get('track_artists')
                    else:
                        audio['ARTIST'] = artist
                if tag_enabled('tag_album_artist'):
                    if isinstance(metadata.get('album_artists'), list) and metadata.get('album_artists'):
                        audio['ALBUMARTIST'] = metadata.get('album_artists')
                    elif metadata.get('album_artist'):
                        audio['ALBUMARTIST'] = metadata.get('album_artist')
                if tag_enabled('tag_album'):
                    audio['ALBUM'] = album
                if tag_enabled('tag_year') and year:
                    audio['DATE'] = str(year)
                if tag_enabled('tag_track_number'):
                    audio['TRACKNUMBER'] = str(track_num)
                if tag_enabled('tag_track_total') and metadata.get('track_total') is not None:
                    audio['TRACKTOTAL'] = str(metadata.get('track_total'))
                if tag_enabled('tag_disc_number') and disc_num:
                    audio['DISCNUMBER'] = str(disc_num)
                if tag_enabled('tag_disc_total') and metadata.get('disc_total') is not None:
                    audio['DISCTOTAL'] = str(metadata.get('disc_total'))
                if tag_enabled('tag_version') and metadata.get('version'):
                    audio['VERSION'] = str(metadata.get('version'))
                if tag_enabled('tag_copyright') and metadata.get('copyright'):
                    audio['COPYRIGHT'] = str(metadata.get('copyright'))
                if tag_enabled('tag_explicit') and metadata.get('explicit'):
                    audio['ITUNESADVISORY'] = '1'
                if tag_enabled('tag_tidal_track_id') and metadata.get('tidal_track_id'):
                    audio['TIDAL_TRACK_ID'] = str(metadata.get('tidal_track_id'))
                if tag_enabled('tag_tidal_album_id') and metadata.get('tidal_album_id'):
                    audio['TIDAL_ALBUM_ID'] = str(metadata.get('tidal_album_id'))
                if tag_enabled('tag_isrc') and metadata.get('isrc'):
                    audio['ISRC'] = str(metadata.get('isrc'))
                if tag_enabled('tag_cover_art') and cover_image_data:
                    from mutagen.flac import Picture
                    pic = Picture()
                    pic.data = cover_image_data
                    pic.type = 3
                    pic.mime = 'image/jpeg'
                    audio.add_picture(pic)

                audio.save()
                logger.info("[ID3] Successfully added FLAC metadata to %s", file_path)
            except Exception as e:
                logger.info("[ID3] Warning: Could not write FLAC tags: %s", str(e))

        # Handle M4A/AAC files
        elif file_path.lower().endswith('.m4a'):
            try:
                audio = MP4(file_path)
                if tag_enabled('tag_title'):
                    audio['\xa9nam'] = title
                if tag_enabled('tag_artist'):
                    if isinstance(metadata.get('track_artists'), list) and metadata.get('track_artists'):
                        audio['\xa9ART'] = metadata.get('track_artists')
                    else:
                        audio['\xa9ART'] = [artist]
                if tag_enabled('tag_album_artist'):
                    if isinstance(metadata.get('album_artists'), list) and metadata.get('album_artists'):
                        audio['aART'] = metadata.get('album_artists')
                    elif metadata.get('album_artist'):
                        audio['aART'] = [metadata.get('album_artist')]
                if tag_enabled('tag_album'):
                    audio['\xa9alb'] = album

                if tag_enabled('tag_year') and year:
                    audio['\xa9day'] = str(year)

                if tag_enabled('tag_track_number') and track_num:
                    try:
                        track_number = int(track_num)
                        track_total = metadata.get('track_total')
                        if isinstance(track_total, int):
                            audio['trkn'] = [(track_number, track_total)]
                        else:
                            audio['trkn'] = [(track_number, 0)]
                    except ValueError:
                        pass

                if tag_enabled('tag_disc_number') and disc_num:
                    try:
                        disc_number = int(disc_num)
                        disc_total = metadata.get('disc_total')
                        if isinstance(disc_total, int):
                            audio['disk'] = [(disc_number, disc_total)]
                        else:
                            audio['disk'] = [(disc_number, 0)]
                    except ValueError:
                        pass

                if tag_enabled('tag_copyright') and metadata.get('copyright'):
                    audio['\xa9cpy'] = str(metadata.get('copyright'))
                if tag_enabled('tag_explicit') and metadata.get('explicit'):
                    audio['rtng'] = [1]
                if tag_enabled('tag_tidal_track_id') and metadata.get('tidal_track_id'):
                    audio['----:com.apple.iTunes:tidal_track_id'] = [str(metadata.get('tidal_track_id')).encode('utf-8')]
                if tag_enabled('tag_tidal_album_id') and metadata.get('tidal_album_id'):
                    audio['----:com.apple.iTunes:tidal_album_id'] = [str(metadata.get('tidal_album_id')).encode('utf-8')]
                if tag_enabled('tag_version') and metadata.get('version'):
                    audio['----:com.apple.iTunes:version'] = [str(metadata.get('version')).encode('utf-8')]
                if tag_enabled('tag_isrc') and metadata.get('isrc'):
                    audio['----:com.apple.iTunes:isrc'] = [str(metadata.get('isrc')).encode('utf-8')]

                if tag_enabled('tag_cover_art') and cover_image_data:
                    audio['covr'] = [MP4Cover(cover_image_data, imageformat=MP4Cover.FORMAT_JPEG)]

                audio.save()
                logger.info("[ID3] Successfully added M4A metadata to %s", file_path)
            except Exception as e:
                logger.info("[ID3] Warning: Could not write M4A tags: %s", str(e))

        # MP3 tagging is not supported


    except Exception as e:
        logger.info("[ID3] Error adding ID3 tags: %s", str(e))


def download_cover_image(cover_url):
    """
    Download album cover image from URL.
    Returns binary image data or None if download fails.
    """
    if not cover_url:
        logger.info("[COVER] No cover URL provided")
        return None
    
    try:
        logger.info("[COVER] Downloading cover image from: %s", cover_url)
        response = requests.get(cover_url, timeout=10)
        
        if response.ok:
            logger.info("[COVER] Successfully downloaded cover image (%d bytes)", len(response.content))
            return response.content
        else:
            logger.info("[COVER] Failed to download cover image. Status: %d", response.status_code)
            return None
    except requests.exceptions.Timeout:
        logger.info("[COVER] ERROR: Timeout downloading cover image from %s", cover_url)
        return None
    except Exception as e:
        logger.info("[COVER] Error downloading cover image: %s", str(e))
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
        logger.info("[FFMPEG] Converting %s to MP3 (highest VBR quality): %s -> %s", source_format.upper(), source_path, mp3_path)

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

        logger.info("[FFMPEG] Command: %s", ' '.join(cmd))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info("[FFMPEG] SUCCESS: Converted to %s", mp3_path)
            return True

        logger.info("[FFMPEG] ERROR: Conversion failed with code %d", result.returncode)
        logger.info("[FFMPEG] stderr: %s", result.stderr)
        return False

    except subprocess.TimeoutExpired:
        logger.info("[FFMPEG] ERROR: Conversion timeout")
        return False
    except Exception as e:
        logger.info("[FFMPEG] ERROR: %s", str(e))
        return False


_DURATION_RE = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')


def validate_audio_duration(file_path, expected_duration_seconds):
    """Validate that the actual decoded audio duration matches expectations.

    Runs a full decode via ffmpeg to detect truncated/preview files where
    container metadata claims a longer duration than the actual audio stream.

    Args:
        file_path: Path to the audio file to validate.
        expected_duration_seconds: Expected duration in seconds (from track metadata).

    Raises:
        RuntimeError: If actual duration is < 50% of expected.
    """
    if not expected_duration_seconds:
        return

    try:
        expected = int(expected_duration_seconds)
    except (TypeError, ValueError):
        return

    if expected < 10:
        return

    try:
        result = subprocess.run(
            ['ffmpeg', '-i', file_path, '-f', 'null', '/dev/null'],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        logger.info("[DOWNLOAD] Duration validation timed out for %s", file_path)
        return
    except Exception as e:
        logger.info("[DOWNLOAD] Duration validation skipped: %s", e)
        return

    match = _DURATION_RE.search(result.stderr)
    if not match:
        logger.info("[DOWNLOAD] Duration validation skipped: could not parse ffmpeg output for %s", file_path)
        return

    hours, minutes, seconds, fraction = match.groups()
    actual_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(fraction) / (10 ** len(fraction))

    if actual_seconds < expected * 0.5:
        raise RuntimeError(
            f"Downloaded audio is truncated: expected ~{expected}s but actual decoded duration is {actual_seconds:.1f}s"
        )

    logger.info("[DOWNLOAD] Duration validation passed: expected ~%ds, actual %.1fs", expected, actual_seconds)
