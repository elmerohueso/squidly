"""Deezer mirror download client for Squidly.

Handles health-check validation and track downloads
from Deezer mirror endpoints.
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_USER_AGENT = "Squidly/1.0 (+https://github.com/elmerohueso/squidly)"
_ORIGIN = "https://monochrome.tf"
_REFERER = "https://monochrome.tf/"


def validate_deezer_mirror_endpoint(url: str, timeout: int = 5) -> dict:
    """Health check for a Deezer mirror by hitting GET /health.

    Args:
        url: The base URL of the Deezer mirror instance.
        timeout: Request timeout in seconds.

    Returns:
        Dict with 'online' (bool), 'responseTime' (ms or None),
        'lastChecked' (ISO timestamp), and 'error' (str or None).
    """
    from datetime import datetime

    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        start_time = time.time()
        response = requests.get(
            f"{url.rstrip('/')}/health",
            headers={'User-Agent': _USER_AGENT, 'Origin': _ORIGIN, 'Referer': _REFERER},
            timeout=timeout,
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


def download_deezer_mirror_track(
    base_url: str,
    isrc: str,
    output_path: str,
    timeout: int = 120,
) -> Optional[dict]:
    """Download a track from a Deezer mirror by ISRC.

    GET {base_url}/stream/?isrc={ISRC}&format=FLAC
    Sends Origin/Referer headers matching what Monochrome sends from browser.
    Streams raw FLAC bytes to output_path.

    Args:
        base_url: Deezer mirror base URL.
        isrc: ISRC code of the track.
        output_path: Path to save the downloaded file.
        timeout: Request timeout in seconds.

    Returns:
        {'file_path': output_path} on success, None on failure.
    """
    stream_url = f'{base_url.rstrip("/")}/stream/'

    logger.info("[DEEZER_MIRROR] Downloading track ISRC %s from %s", isrc, stream_url)

    params = {'isrc': isrc, 'format': 'FLAC'}
    headers = {
        'User-Agent': _USER_AGENT,
        'Origin': _ORIGIN,
        'Referer': _REFERER,
    }

    try:
        response = requests.get(
            stream_url,
            params=params,
            headers=headers,
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()

        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                f.write(chunk)
                downloaded += len(chunk)

        logger.info(
            "[DEEZER_MIRROR] Downloaded %d bytes for ISRC %s",
            downloaded, isrc,
        )

        try:
            actual_size = os.path.getsize(output_path)
            logger.debug("[DEEZER_MIRROR] Written file size: %d bytes (%s)", actual_size, output_path)
        except OSError:
            logger.debug("[DEEZER_MIRROR] Written file size: unknown (%s)", output_path)

    except requests.RequestException as exc:
        logger.error("[DEEZER_MIRROR] Download failed for ISRC %s: %s", isrc, exc)
        return None
    except OSError as exc:
        logger.error("[DEEZER_MIRROR] File write failed for ISRC %s: %s", isrc, exc)
        return None

    return {'file_path': output_path}


def download_track_by_isrc(
    isrc: str,
    quality: str,
    *,
    track_id: str | None = None,
) -> dict:
    """Download a track from a Deezer mirror by ISRC. Returns {'file_path', 'source'}.

    Iterates enabled Deezer mirrors until one succeeds. Raises on failure.
    """
    from squidly.infrastructure.downloads import (
        load_enabled_mirror_urls,
        make_temp_download_path,
        cleanup_file,
    )

    deezer_mirrors = load_enabled_mirror_urls(mirror_type='deezer', for_download=True)
    if not deezer_mirrors:
        raise ValueError("No Deezer mirrors available (need enabled, online, premium)")

    src_error = None
    for mirror in deezer_mirrors:
        base_url = mirror['url']
        temp_path = make_temp_download_path(isrc, 'deezer_mirror', quality)
        try:
            result = download_deezer_mirror_track(
                base_url=base_url,
                isrc=isrc,
                output_path=temp_path,
            )
            if result:
                return {'file_path': temp_path, 'source': base_url}
        except Exception as e:
            logger.warning("[DEEZER_MIRROR] Mirror %s failed: %s", base_url, e)
            src_error = e
            cleanup_file(temp_path)
            continue

    if src_error:
        raise ValueError(f"Failed to download from Deezer Mirror (ISRC: {isrc}): {src_error}")
    raise ValueError(f"Failed to download from Deezer Mirror (ISRC: {isrc})")
