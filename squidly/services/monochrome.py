"""Unified Playback API client for Squidly.

Calls the Monochrome Unified Playback API to get stream URLs from multiple
sources (Monochrome, Amazon, Tidal) via a single endpoint.

Handles Turnstile JWT authentication and routes downloads based on source type:
- monochrome: Direct FLAC or DASH manifest
- amazon: Encrypted MP4 with CENC decryption
- tidal: DASH/HLS manifests (handled by existing ffmpeg support)

Requires: google-chrome, xvfb, playwright (with chromium) for Turnstile solving
"""

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Optional

from squidly.services import turnstile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unified Playback API configuration
# ---------------------------------------------------------------------------

DEFAULT_API_BASE_URL = 'https://music-api.geeked.wtf'
DEFAULT_API_TOKEN = 'amp_29b2lIr4mze4tK-P8QDOxfMZ9anCgJ9_uGTUks3nIyo'
TURNSTILE_SITE_KEY = '0x4AAAAAADgxqF6QVMm0GLHH'
AUTH_PATH = '/api/auth/turnstile'
TRACK_API_PATH = '/api/v2/track/'


# ---------------------------------------------------------------------------
# Browser JS: Solve Turnstile and get JWT
# ---------------------------------------------------------------------------

_TURNSTILE_JS = '''
(async () => {
    const API_BASE_URL = %s;
    const SITE_KEY = %s;
    const API_TOKEN = %s;

    // Load Turnstile
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
    await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = () => reject(new Error('Failed to load Turnstile'));
        document.head.appendChild(script);
    });

    // Render invisible widget and execute
    const token = await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Turnstile timed out')), 30000);
        const widgetId = turnstile.render(document.body, {
            sitekey: SITE_KEY,
            size: 'invisible',
            execution: 'execute',
            callback: (t) => { clearTimeout(timeout); resolve(t); },
            'error-callback': () => { clearTimeout(timeout); reject(new Error('Turnstile failed')); },
            'expired-callback': () => { clearTimeout(timeout); reject(new Error('Turnstile expired')); },
        });
        turnstile.execute(widgetId);
    });

    // Exchange token for JWT
    const authResp = await fetch(API_BASE_URL + '%s', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + API_TOKEN,
        },
        body: JSON.stringify({ turnstile_token: token }),
    });
    if (!authResp.ok) {
        const text = await authResp.text();
        throw new Error('Auth failed: ' + authResp.status + ' ' + text);
    }
    const authData = await authResp.json();
    return authData.access_token || authData.token || authData.jwt;
})()
'''


# ---------------------------------------------------------------------------
# Browser JS: Call Unified Playback API
# ---------------------------------------------------------------------------

_UNIFIED_PLAYBACK_JS = '''
(async () => {
    const API_BASE_URL = __API_URL__;
    const API_TOKEN = __API_TOKEN__;
    const JWT = __JWT__;
    const PARAMS = __PARAMS__;

    const url = API_BASE_URL + '%s?' + PARAMS;
    const resp = await fetch(url, {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + API_TOKEN,
            'X-Turnstile-JWT': JWT,
        },
    });
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error('Unified Playback API failed: ' + resp.status + ' ' + text);
    }
    return resp.json();
})()
'''


def _build_track_metadata(track_object: dict) -> dict:
    """Extract Unified Playback API parameters from a normalized Tidal track object."""
    track = track_object.get('track', track_object) if isinstance(track_object.get('track'), dict) else track_object

    artists = track.get('artists', [])
    if isinstance(artists, list) and artists:
        artist_names = [a.get('name', '') for a in artists if isinstance(a, dict) and a.get('name')]
        artist_str = '; '.join(artist_names) if artist_names else 'Unknown Artist'
    elif isinstance(track.get('artist'), dict):
        artist_str = track['artist'].get('name', 'Unknown Artist')
    else:
        artist_str = 'Unknown Artist'

    album_data = track.get('album', {})
    album_title = ''
    if isinstance(album_data, dict):
        album_title = album_data.get('title', '')

    return {
        'title': track.get('title', 'Unknown Track'),
        'artist': artist_str,
        'album': album_title,
        'isrc': track.get('isrc', ''),
        'duration': track.get('duration', 0) or 0,
    }


def _build_query_params(track_metadata: dict, quality: str) -> str:
    """Build URL query parameters for Unified Playback API."""
    from urllib.parse import urlencode

    params = {
        'track': track_metadata['title'],
    }
    if track_metadata.get('artist'):
        params['artist'] = track_metadata['artist']
    if track_metadata.get('album'):
        params['album'] = track_metadata['album']
    if track_metadata.get('isrc'):
        params['isrc'] = track_metadata['isrc'].upper()
    if track_metadata.get('duration'):
        params['duration'] = str(int(track_metadata['duration']))

    # Map quality
    quality_map = {
        'LOSSLESS': 'LOSSLESS',
        'HIGH': 'HIGH',
        'LOW': 'LOW',
        'HI_RES_LOSSLESS': 'HI_RES_LOSSLESS',
    }
    params['quality'] = quality_map.get(quality, 'LOSSLESS')
    params['intent'] = 'stream'

    return urlencode(params)


def _get_unified_playback_jwt(page, api_base_url: str, api_token: str) -> str:
    """Solve Turnstile and get JWT for Unified Playback API."""
    js = _TURNSTILE_JS % (
        json.dumps(api_base_url),
        json.dumps(TURNSTILE_SITE_KEY),
        json.dumps(api_token),
        json.dumps(AUTH_PATH),
    )
    return page.evaluate(js)


def _call_unified_playback_api(page, api_base_url: str, api_token: str, jwt: str, params: str) -> dict:
    """Call the Unified Playback API and return the envelope response."""
    js = _UNIFIED_PLAYBACK_JS.replace('__API_URL__', json.dumps(api_base_url))
    js = js.replace('__API_TOKEN__', json.dumps(api_token))
    js = js.replace('__JWT__', json.dumps(jwt))
    js = js.replace('__PARAMS__', json.dumps(params))
    js = js % (TRACK_API_PATH,)
    return page.evaluate(js)


def _select_best_source(envelope: dict) -> Optional[dict]:
    """Select the best playback source from the Unified Playback envelope.

    Priority: monochrome (direct) > amazon > tidal > monochrome (DASH)
    """
    playback = envelope.get('playback', [])
    if not playback:
        return None

    # Score each resource
    scored = []
    for resource in playback:
        url = resource.get('url', '')
        source = resource.get('source', '').lower()
        delivery = resource.get('delivery', '')
        kind = resource.get('kind', '')

        if not url:
            continue

        # Skip if no audio kind
        if kind not in ('audio', 'manifest', ''):
            continue

        # Score based on source and delivery
        score = 0
        if source in ('mono', 'monochrome'):
            if delivery == 'direct':
                score = 100  # Best: direct FLAC
            else:
                score = 90   # DASH manifest
        elif source == 'amazon':
            score = 80
        elif source == 'tidal':
            score = 70
        else:
            score = 0

        scored.append((score, resource))

    if not scored:
        return None

    # Return highest scored
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _download_direct_flac(url: str, output_path: str) -> None:
    """Download a direct FLAC stream."""
    logger.info("[MONOCHROME] Downloading direct FLAC stream")
    subprocess.run(
        ['curl', '-L', '-s', '-o', output_path, url],
        check=True,
        timeout=300,
    )


def _download_encrypted_mp4(url: str, decryption_key: str, output_path: str) -> None:
    """Download an encrypted MP4 and decrypt to FLAC."""
    temp_folder = '/app/temp'
    os.makedirs(temp_folder, exist_ok=True)
    encrypted_path = os.path.join(temp_folder, 'monochrome_encrypted.mp4')

    logger.info("[MONOCHROME] Downloading encrypted Amazon stream")
    subprocess.run(
        ['curl', '-L', '-s', '-o', encrypted_path, url],
        check=True,
        timeout=300,
    )

    file_size = os.path.getsize(encrypted_path)
    logger.info("[MONOCHROME] Encrypted stream downloaded: %.1f MB", file_size / (1024 * 1024))

    logger.info("[MONOCHROME] Decrypting to FLAC")
    subprocess.run(
        [
            'ffmpeg', '-y',
            '-decryption_key', decryption_key,
            '-i', encrypted_path,
            '-c:a', 'copy',
            output_path,
        ],
        capture_output=True,
        check=True,
        timeout=120,
    )

    # Cleanup encrypted temp file
    try:
        os.remove(encrypted_path)
    except OSError:
        pass


def _download_dash_manifest(url: str, output_path: str) -> None:
    """Download audio from a DASH manifest using ffmpeg."""
    logger.info("[MONOCHROME] Downloading DASH manifest via ffmpeg")
    subprocess.run(
        [
            'ffmpeg', '-y',
            '-hide_banner',
            '-loglevel', 'error',
            '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
            '-i', url,
            '-map', '0:a:0',
            '-c', 'copy',
            output_path,
        ],
        capture_output=True,
        check=True,
        timeout=300,
    )


def download_track_by_isrc(
    isrc: str,
    quality: str,
    track_id: str = '',
    track_object: Optional[dict] = None,
) -> dict:
    """Download a track from the Unified Playback API.

    Args:
        isrc: ISRC code (used for API lookup).
        quality: Squidly quality preset (LOSSLESS, HIGH, LOW).
        track_id: Tidal track ID (used for temp file naming).
        track_object: Normalized Tidal track object with metadata.

    Returns:
        dict with 'file_path' and 'source' keys.

    Raises:
        ValueError: if track_object is missing or config is incomplete.
        RuntimeError: if Chrome/Xvfb/Playwright fails.
    """
    if not track_object:
        raise ValueError('track_object is required for Unified Playback downloads')

    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()

    api_base_url = (settings.get('monochrome_api_base_url') or DEFAULT_API_BASE_URL).strip().rstrip('/')
    api_token = (settings.get('monochrome_api_token') or DEFAULT_API_TOKEN).strip()

    if not api_base_url:
        raise ValueError('Unified Playback API base URL is not configured')

    track_metadata = _build_track_metadata(track_object)

    logger.info(
        "[MONOCHROME] Downloading: title='%s', artist='%s', isrc=%s",
        track_metadata['title'], track_metadata['artist'], track_metadata['isrc'],
    )

    xvfb_proc = None
    try:
        # Start Xvfb
        xvfb_proc = turnstile.start_xvfb()

        # Launch Playwright with persistent Chrome context
        from playwright.sync_api import sync_playwright

        chrome_env = os.environ.copy()
        for key in ('WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'GDK_BACKEND'):
            chrome_env.pop(key, None)
        chrome_env['DISPLAY'] = ':99'

        profile_dir = os.path.expanduser('~/.squidly-chrome-profile')

        logger.info("[MONOCHROME] Launching Chrome via Playwright")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                executable_path=shutil.which('google-chrome'),
                user_data_dir=profile_dir,
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-gpu',
                    '--ozone-platform=x11',
                    '--disable-blink-features=AutomationControlled',
                ],
                env=chrome_env,
            )
            page = context.new_page()

            # Navigate to a Monochrome domain for Turnstile context
            turnstile_domain = 'monochrome.tf'
            logger.info("[MONOCHROME] Navigating to %s for Turnstile auth", turnstile_domain)
            page.route('**/*', lambda route: route.abort()
                       if turnstile_domain in route.request.url
                          and route.request.resource_type in ('stylesheet', 'image', 'font', 'script', 'xhr', 'fetch')
                       else route.continue_())
            try:
                page.goto(f'https://{turnstile_domain}', wait_until='domcontentloaded')
            except Exception as e:
                raise ValueError(f'Failed to load auth page ({turnstile_domain}): {e}') from None

            # Solve Turnstile and get JWT
            logger.info("[MONOCHROME] Solving Turnstile and exchanging for JWT")
            try:
                jwt = _get_unified_playback_jwt(page, api_base_url, api_token)
            except Exception as e:
                raise ValueError(f'Turnstile auth failed — {e}') from None
            if not jwt:
                raise ValueError('Turnstile returned empty token')

            # Build query params and call Unified Playback API
            params = _build_query_params(track_metadata, quality)
            logger.info("[MONOCHROME] Calling Unified Playback API")
            try:
                envelope = _call_unified_playback_api(page, api_base_url, api_token, jwt, params)
            except Exception as e:
                raise ValueError(f'Unified Playback API call failed — {e}') from None

            page.close()
            context.close()

        # Parse envelope and select best source
        if not envelope or not isinstance(envelope, dict):
            raise ValueError('Unified Playback returned invalid response')

        resource = _select_best_source(envelope)
        if not resource:
            raise ValueError(f'Unified Playback returned no playable resources: {envelope.get("sources", envelope)}')

        source = resource.get('source', '').lower()
        url = resource.get('url', '')
        delivery = resource.get('delivery', '')
        decryption_key = resource.get('decryption_key') or resource.get('decryptionKey')

        if not url:
            raise ValueError(f'Unified Playback resource has no URL: {resource}')

        logger.info(
            "[MONOCHROME] Selected source: %s, delivery: %s, quality: %s",
            source, delivery, resource.get('quality', ''),
        )

        # Prepare output path
        temp_folder = '/app/temp'
        os.makedirs(temp_folder, exist_ok=True)
        output_path = os.path.join(temp_folder, f'monochrome_{track_id or "track"}.flac')

        # Download based on source and delivery type
        if source in ('mono', 'monochrome'):
            if delivery == 'direct':
                _download_direct_flac(url, output_path)
            else:
                # DASH manifest - use ffmpeg
                _download_dash_manifest(url, output_path)
        elif source == 'amazon':
            if decryption_key:
                _download_encrypted_mp4(url, decryption_key, output_path)
            else:
                # No decryption key - try direct download (shouldn't happen for Amazon)
                _download_direct_flac(url, output_path)
        elif source == 'tidal':
            # Tidal DASH/HLS - use ffmpeg
            _download_dash_manifest(url, output_path)
        else:
            raise ValueError(f'Unsupported Unified Playback source: {source}')

        file_size = os.path.getsize(output_path)
        logger.info("[MONOCHROME] Downloaded: %.1f MB → %s", file_size / (1024 * 1024), output_path)

        return {
            'file_path': output_path,
            'source': f'unified_playback:{source}',
        }

    except Exception:
        # Cleanup on failure
        if xvfb_proc:
            try:
                xvfb_proc.kill()
                xvfb_proc.wait(timeout=5)
            except Exception:
                pass
        raise

    finally:
        # Always kill Xvfb
        if xvfb_proc:
            try:
                xvfb_proc.kill()
                xvfb_proc.wait(timeout=5)
            except Exception:
                pass
