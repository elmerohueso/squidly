"""Qobuz-DL API client for Squidly.

Handles search, stream URL retrieval, quality mapping, and validation
for Qobuz-DL mirror endpoints.
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Browser-like User-Agent to avoid 403 blocks from some Qobuz-DL instances
_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Quality code mapping from Tidal quality presets to Qobuz quality codes
QOBUZ_QUALITY_MAP = {
    'LOSSLESS': 6,          # CD-quality FLAC (16-bit/44.1kHz)
    'HI_RES_LOSSLESS': 27,  # Hi-Res FLAC (up to 24-bit/192kHz)
    'HIGH': 5,              # AAC 320kbps
}

# File extensions by Qobuz quality code
QOBUZ_QUALITY_EXTENSIONS = {
    27: '.flac',
    7:  '.flac',
    6:  '.flac',
    5:  '.m4a',
}

# Supported Tidal quality values for Qobuz downloads (LOW is not supported)
QOBUZ_SUPPORTED_QUALITIES = {'LOSSLESS', 'HIGH'}


def get_qobuz_quality_code(tidal_quality: str) -> int:
    """Map a Tidal quality preset to a Qobuz quality code.

    Returns the Qobuz quality code integer, defaulting to 6 (CD FLAC)
    if the quality is not recognized.
    """
    return QOBUZ_QUALITY_MAP.get(tidal_quality.upper(), 6)


def get_qobuz_file_extension(quality_code: int) -> str:
    """Get the file extension for a Qobuz quality code."""
    return QOBUZ_QUALITY_EXTENSIONS.get(quality_code, '.flac')


def search_qobuz_track(
    base_url: str,
    isrc: str,
    timeout: int = 30,
) -> tuple[dict | None, str | None]:
    """Search the Qobuz catalog by ISRC and return the first matching track
    whose ISRC matches exactly.

    The Qobuz search endpoint is text-based, so we search by ISRC string
    and then validate that a returned track's ISRC matches the one we
    searched for.

    Args:
        base_url: Qobuz-DL instance base URL (e.g. 'https://qdl-api.monochrome.tf')
        isrc: ISRC code to search for
        timeout: Request timeout in seconds

    Returns:
        (track_dict, None) on success
        (None, 'http_error') on HTTP 4xx/5xx
        (None, 'network_error') on connection/timeout failures
        (None, 'not_found') when no matching track is found
    """
    url = f'{base_url.rstrip("/")}/api/get-music'
    params = {'q': isrc, 'offset': 0}

    logger.info("[QOBUZ] Searching for ISRC: %s", isrc)

    try:
        response = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': _USER_AGENT})
        response.raise_for_status()
    except requests.RequestException as exc:
        if isinstance(exc, requests.exceptions.HTTPError):
            logger.error("[QOBUZ] Search request returned HTTP error: %s", exc)
            return None, 'http_error'
        logger.error("[QOBUZ] Search request failed (network error): %s", exc)
        return None, 'network_error'

    data = response.json()
    if not data.get('success'):
        logger.error("[QOBUZ] Search returned success=false for ISRC %s", isrc)
        return None, 'http_error'

    result_data = data.get('data', {})
    if not isinstance(result_data, dict):
        logger.error("[QOBUZ] Unexpected search response format for ISRC %s", isrc)
        return None, 'http_error'

    tracks_obj = result_data.get('tracks', {})
    if isinstance(tracks_obj, dict):
        items = tracks_obj.get('items', [])
    elif isinstance(tracks_obj, list):
        items = tracks_obj
    else:
        items = []

    if not items:
        logger.warning("[QOBUZ] No tracks found for ISRC %s", isrc)
        return None, 'not_found'

    # Find the first track whose ISRC matches exactly
    for track in items:
        track_isrc = (track.get('isrc') or '').strip().upper()
        if track_isrc == isrc.strip().upper():
            track_id = track.get('id')
            track_title = track.get('title', 'Unknown')
            logger.info(
                "[QOBUZ] Found ISRC match: %s (Qobuz ID: %s, title: %s)",
                track_isrc, track_id, track_title
            )
            return track, None

    logger.warning(
        "[QOBUZ] No track with matching ISRC found for %s (searched %d results)",
        isrc, len(items)
    )
    return None, 'not_found'


def get_qobuz_stream_url(
    base_url: str,
    track_id: int,
    quality_code: int,
    timeout: int = 30,
) -> Optional[str]:
    """Get the download/stream URL for a Qobuz track.

    Args:
        base_url: Qobuz-DL instance base URL
        track_id: Qobuz track ID (numeric)
        quality_code: Qobuz quality code (6=CD FLAC, 27=Hi-Res, 5=AAC)
        timeout: Request timeout in seconds

    Returns:
        The stream URL string, or None if the request fails.
    """
    url = f'{base_url.rstrip("/")}/api/download-music'
    params = {'track_id': str(track_id), 'quality': str(quality_code)}

    logger.info("[QOBUZ] Getting stream URL for track %s, quality %s", track_id, quality_code)

    try:
        response = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': _USER_AGENT})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[QOBUZ] Stream URL request failed: %s", exc)
        return None

    data = response.json()
    if not data.get('success'):
        logger.error("[QOBUZ] Stream URL returned success=false for track %s", track_id)
        return None

    result_data = data.get('data', {})
    if isinstance(result_data, dict):
        stream_url = result_data.get('url')
    else:
        stream_url = None

    if not stream_url:
        logger.error("[QOBUZ] No stream URL in response for track %s", track_id)
        return None

    return stream_url


def download_qobuz_track(
    base_url: str,
    isrc: str,
    tidal_quality: str,
    output_path: str,
    timeout: int = 30,
) -> Optional[dict]:
    """Download a track from Qobuz using its ISRC.

    This is the main entry point for Qobuz downloads. It:
    1. Searches Qobuz by ISRC and validates the match
    2. Gets the stream URL
    3. Downloads the file to output_path

    Args:
        base_url: Qobuz-DL instance base URL
        isrc: ISRC code of the track (from Tidal metadata)
        tidal_quality: Tidal quality preset ('LOSSLESS' or 'HIGH')
        output_path: Path to save the downloaded file
        timeout: Request timeout in seconds

    Returns:
        A dict with track info and file path on success, or None on failure.
        On success: {'track': <qobuz track dict>, 'file_path': <str>, 'quality_code': <int>}
    """
    quality_code = get_qobuz_quality_code(tidal_quality)

    # Step 1: Search by ISRC and validate match
    track, search_error = search_qobuz_track(base_url, isrc, timeout=timeout)
    if track is None:
        if search_error == 'not_found':
            logger.warning("[QOBUZ] Track ISRC %s not found in Qobuz catalog", isrc)
            raise ValueError("not found in Qobuz catalog")
        logger.error("[QOBUZ] Search failed for ISRC %s (error: %s)", isrc, search_error)
        return None

    track_id = track.get('id')
    if not track_id:
        logger.error("[QOBUZ] Track found for ISRC %s but has no ID", isrc)
        return None

    # Step 2: Get stream URL
    stream_url = get_qobuz_stream_url(base_url, track_id, quality_code, timeout=timeout)
    if stream_url is None:
        logger.error("[QOBUZ] Could not get stream URL for track %s (ISRC: %s)", track_id, isrc)
        return None

    # Step 3: Download the file
    logger.info("[QOBUZ] Downloading track %s from %s", track_id, stream_url[:80])
    try:
        response = requests.get(stream_url, stream=True, timeout=120, headers={'User-Agent': _USER_AGENT})
        response.raise_for_status()

        total = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                f.write(chunk)
                downloaded += len(chunk)

        logger.info(
            "[QOBUZ] Downloaded %d bytes for track %s (ISRC: %s)",
            downloaded, track_id, isrc
        )

        try:
            actual_size = os.path.getsize(output_path)
            logger.info("[QOBUZ] Written file size: %d bytes (%s)", actual_size, output_path)
        except OSError:
            logger.info("[QOBUZ] Written file size: unknown (%s)", output_path)

        try:
            with open(output_path, 'rb') as fmt_file:
                from squidly.infrastructure.downloads import detect_audio_format
                detected_fmt = detect_audio_format(fmt_file.read(32))
            logger.info("[QOBUZ] Detected format: %s (%s)", detected_fmt, output_path)
        except Exception:
            pass

    except requests.RequestException as exc:
        logger.error("[QOBUZ] Download failed for track %s: %s", track_id, exc)
        return None
    except OSError as exc:
        logger.error("[QOBUZ] File write failed for track %s: %s", track_id, exc)
        return None

    return {
        'track': track,
        'file_path': output_path,
        'quality_code': quality_code,
    }


def validate_qobuz_endpoint(url: str, timeout: int = 5) -> dict:
    """Validate a Qobuz-DL mirror endpoint.

    Checks that the server is reachable by hitting the /api/get-countries
    endpoint and confirming a 200 response.

    Args:
        url: The base URL of the Qobuz-DL instance
        timeout: Request timeout in seconds

    Returns:
        Dict with 'online' (bool), 'responseTime' (ms or None),
        'lastChecked' (ISO timestamp), and 'error' (str or None).
    """
    from datetime import datetime

    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        start_time = time.time()
        response = requests.get(
            f"{url.rstrip('/')}/api/get-countries",
            timeout=timeout,
            headers={'User-Agent': _USER_AGENT},
        )
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            return {
                'online': True,
                'responseTime': round(response_time, 2),
                'lastChecked': timestamp,
                'error': None,
            }
        else:
            return {
                'online': False,
                'responseTime': None,
                'lastChecked': timestamp,
                'error': f'HTTP {response.status_code}',
            }

    except requests.exceptions.Timeout:
        return {'online': False, 'responseTime': None, 'lastChecked': timestamp, 'error': 'Timeout'}
    except requests.exceptions.RequestException as e:
        return {'online': False, 'responseTime': None, 'lastChecked': timestamp, 'error': str(e)}