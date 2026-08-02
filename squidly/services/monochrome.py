"""Monochrome Track API client for Squidly.

Uses Playwright + Chrome on Xvfb to solve Cloudflare Turnstile challenges,
then calls the Monochrome track-api to get direct FLAC stream URLs.

Requires: google-chrome, xvfb, playwright (with chromium)
"""

import json
import logging
import os
import shutil
import subprocess
import time

from squidly.services import turnstile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Browser JS: call Monochrome playback API (Turnstile JWT handled separately)
# ---------------------------------------------------------------------------

_MONOCHROME_API_JS = '''
(async () => {
    const API_BASE_URL = __API_URL__;
    const JWT_VALUE = __JWT__;
    const TRACK = __TRACK_JSON__;

    // Build playback request body
    const body = {
        song_name: TRACK.title,
        artist: TRACK.artist,
        isrc: TRACK.isrc || '',
        duration: TRACK.duration || 0,
    };

    // Add optional bypass_token if provided
    if (TRACK.bypass_token) {
        body.bypass_token = TRACK.bypass_token;
    }

    const trackResp = await fetch(API_BASE_URL + '/playback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + JWT_VALUE,
        },
        body: JSON.stringify(body),
    });
    if (!trackResp.ok) {
        const text = await trackResp.text();
        throw new Error('Monochrome API failed: ' + trackResp.status + ' ' + text);
    }
    const trackData = await trackResp.json();

    // Flatten response wrappers
    let raw = trackData;
    if (raw && typeof raw === 'object') {
        raw = raw.data || raw.track || raw.result || raw;
    }
    return {
        url: raw.url || '',
        track_id: raw.track_id || '',
        title: raw.title || TRACK.title,
        artists: raw.artists || [],
        isrc: raw.isrc || TRACK.isrc || '',
        duration_seconds: raw.duration_seconds || 0,
    };
})()
'''


def _build_track_metadata(track_object: dict) -> dict:
    """Extract Monochrome API parameters from a normalized Tidal track object."""
    track = track_object.get('track', track_object) if isinstance(track_object.get('track'), dict) else track_object

    artists = track.get('artists', [])
    if isinstance(artists, list) and artists:
        artist_names = [a.get('name', '') for a in artists if isinstance(a, dict) and a.get('name')]
        artist_str = '; '.join(artist_names) if artist_names else 'Unknown Artist'
    elif isinstance(track.get('artist'), dict):
        artist_str = track['artist'].get('name', 'Unknown Artist')
    else:
        artist_str = 'Unknown Artist'

    return {
        'title': track.get('title', 'Unknown Track'),
        'artist': artist_str,
        'isrc': track.get('isrc', ''),
        'duration': track.get('duration', 0) or 0,
    }


def _call_monochrome_api_from_browser(page, api_base_url: str, jwt: str, track_metadata: dict) -> dict:
    """Run the Monochrome playback API call inside the browser page using an existing JWT."""
    track_json = json.dumps(track_metadata)
    js = _MONOCHROME_API_JS.replace('__API_URL__', json.dumps(api_base_url))
    js = js.replace('__JWT__', json.dumps(jwt))
    js = js.replace('__TRACK_JSON__', track_json)
    return page.evaluate(js)


def download_track_by_isrc(
    isrc: str,
    quality: str,
    track_id: str = '',
    track_object: dict = None,
) -> dict:
    """Download a track from the Monochrome Track API.

    Args:
        isrc: ISRC code (not used for API call, but part of the interface).
        quality: Squidly quality preset (always FLAC regardless).
        track_id: Tidal track ID (not used directly).
        track_object: Normalized Tidal track object with metadata.

    Returns:
        dict with 'file_path' and 'source' keys.

    Raises:
        ValueError: if track_object is missing or config is incomplete.
        RuntimeError: if Chrome/Xvfb/Playwright fails.
    """
    if not track_object:
        raise ValueError('track_object is required for Monochrome downloads')

    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()

    api_base_url = (settings.get('monochrome_api_base_url') or '').strip().rstrip('/')
    site_key = (settings.get('monochrome_turnstile_site_key') or '').strip()
    monochrome_domain = (settings.get('monochrome_domain') or '').strip()

    if not api_base_url:
        raise ValueError('Monochrome API base URL is not configured')
    if not site_key:
        raise ValueError('Monochrome Turnstile site key is not configured')
    if not monochrome_domain:
        raise ValueError('Monochrome domain is not configured')

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

            # Navigate to monochrome domain for Turnstile context
            # The HAR shows the origin is monochrome.samidy.com — the Turnstile site key
            # is registered for this domain. The track-api accepts tokens solved from here
            # with action='auth'.
            logger.info("[MONOCHROME] Navigating to %s for Turnstile auth", monochrome_domain)
            page.route('**/*', lambda route: route.abort()
                       if monochrome_domain in route.request.url
                          and route.request.resource_type in ('stylesheet', 'image', 'font', 'script', 'xhr', 'fetch')
                       else route.continue_())
            try:
                page.goto(f'https://{monochrome_domain}', wait_until='domcontentloaded')
            except Exception as e:
                raise ValueError(f'Failed to load auth page ({monochrome_domain}): {e}') from None

            # Solve Turnstile and get JWT via shared utility
            logger.info("[MONOCHROME] Solving Turnstile and exchanging for JWT")
            try:
                jwt = turnstile.solve_turnstile_get_jwt(
                    page,
                    api_base_url=api_base_url,
                    site_key=site_key,
                    auth_path='/auth/turnstile',
                    token_field='turnstile_token',
                    action='auth',
                )
            except Exception as e:
                raise ValueError(f'Turnstile auth failed — {e}') from None
            if not jwt:
                raise ValueError('Turnstile returned empty token')

            # Call Monochrome playback API with the JWT
            logger.info("[MONOCHROME] Calling Monochrome playback API")
            try:
                result = _call_monochrome_api_from_browser(page, api_base_url, jwt, track_metadata)
            except Exception as e:
                raise ValueError(f'Playback API call failed — {e}') from None

            page.close()
            context.close()

        stream_url = result.get('url', '')
        title_display = result.get('title', track_metadata['title'])

        if not stream_url:
            raise ValueError(f'Monochrome API returned no stream URL: {result}')

        logger.info(
            "[MONOCHROME] Got stream: title='%s', isrc=%s, duration=%s",
            title_display, result.get('isrc', ''), result.get('duration_seconds', ''),
        )

        # Download FLAC stream directly
        temp_folder = '/app/temp'
        os.makedirs(temp_folder, exist_ok=True)
        output_path = os.path.join(temp_folder, f'monochrome_{track_id or "track"}.flac')

        logger.info("[MONOCHROME] Downloading FLAC stream")
        subprocess.run(
            ['curl', '-L', '-s', '-o', output_path, stream_url],
            check=True,
            timeout=300,
        )

        flac_size = os.path.getsize(output_path)
        logger.info("[MONOCHROME] Downloaded: %.1f MB → %s", flac_size / (1024 * 1024), output_path)

        return {
            'file_path': output_path,
            'source': 'monochrome',
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
