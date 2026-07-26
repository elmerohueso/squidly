"""Amazon Music API mirror client for Squidly.

Uses Playwright + Chrome on Xvfb to solve Cloudflare Turnstile challenges,
then calls the Amazon Music API mirror to get encrypted stream URLs.
Decrypts the stream to FLAC via ffmpeg.

Requires: google-chrome, xvfb, playwright (with chromium)
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quality mapping: Squidly quality presets → Amazon quality tiers
# ---------------------------------------------------------------------------

AMAZON_QUALITY_MAP = {
    'LOSSLESS': 'HD',
    'HI_RES_LOSSLESS': 'UHD',
    'HIRES_LOSSLESS': 'UHD',
    'HIGH': 'SD_HIGH',
    'LOW': 'SD_LOW',
}

# ---------------------------------------------------------------------------
# Browser JS: Turnstile → JWT → Amazon Music API
# ---------------------------------------------------------------------------

BROWSER_JS = '''
(async () => {
    const API_BASE_URL = API_URL;
    const SITE_KEY = SITE_KEY_PLACEHOLDER;
    const TRACK = TRACK_JSON;

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
    const authResp = await fetch(API_BASE_URL + '/api/auth/turnstile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cf_turnstile_response: token }),
    });
    if (!authResp.ok) {
        const text = await authResp.text();
        throw new Error('Auth failed: ' + authResp.status + ' ' + text);
    }
    const authData = await authResp.json();
    const jwt = authData.access_token || authData.token || authData.jwt;

    // Build Amazon API URL from track metadata
    const params = new URLSearchParams({
        track: TRACK.title,
        artist: TRACK.artist,
        album: TRACK.album,
        duration: String(TRACK.duration),
        quality: TRACK.quality,
    });
    const trackUrl = API_BASE_URL + '/api/track/?' + params.toString();

    // Call Amazon Music API
    const trackResp = await fetch(trackUrl, {
        headers: { 'X-Turnstile-JWT': jwt },
    });
    if (!trackResp.ok) {
        const text = await trackResp.text();
        throw new Error('Amazon API failed: ' + trackResp.status + ' ' + text);
    }
    const trackData = await trackResp.json();

    // Flatten response wrappers
    let raw = trackData;
    if (raw && typeof raw === 'object') {
        raw = raw.data || raw.track || raw.result || raw;
    }
    return {
        stream_url: raw.stream_url || raw.url || raw.streamUrl || '',
        decryption_key: raw.decryption_key || raw.key || '',
        title: raw.title || TRACK.title,
        artist: raw.artist_name || raw.artist || TRACK.artist,
        quality: raw.quality_selected || TRACK.quality,
    };
})()
'''


def _map_quality(tidal_quality: str) -> str:
    """Map a Squidly/Tidal quality preset to an Amazon quality tier."""
    return AMAZON_QUALITY_MAP.get(str(tidal_quality).strip().upper(), 'HD')


def _build_track_metadata(track_object: dict) -> dict:
    """Extract Amazon API parameters from a normalized Tidal track object."""
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
        'duration': track.get('duration', 0) or 0,
    }


def _start_xvfb():
    """Start Xvfb virtual framebuffer. Returns the subprocess."""
    display = ':99'
    logger.info("[AMAZON] Starting Xvfb on %s", display)
    xvfb_proc = subprocess.Popen(
        ['Xvfb', display, '-screen', '0', '1920x1080x24'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    if xvfb_proc.poll() is not None:
        raise RuntimeError('Xvfb failed to start. Install it: apt install xvfb')
    os.environ['DISPLAY'] = display
    return xvfb_proc


def _call_amazon_api_from_browser(page, api_base_url: str, site_key: str, track_metadata: dict) -> dict:
    """Run the full Turnstile + Amazon API flow inside the browser page."""
    track_json = json.dumps(track_metadata)
    js = BROWSER_JS.replace('SITE_KEY_PLACEHOLDER', json.dumps(site_key))
    js = js.replace('API_URL', json.dumps(api_base_url))
    js = js.replace('TRACK_JSON', track_json)
    return page.evaluate(js)


def download_track_by_isrc(
    isrc: str,
    quality: str,
    track_id: str = '',
    track_object: dict = None,
) -> dict:
    """Download a track from the Amazon Music API mirror.

    Args:
        isrc: ISRC code (not used for API call, but part of the interface).
        quality: Squidly quality preset (LOSSLESS, HIGH, LOW).
        track_id: Tidal track ID (not used directly).
        track_object: Normalized Tidal track object with metadata.

    Returns:
        dict with 'file_path' and 'source' keys.

    Raises:
        ValueError: if track_object is missing or config is incomplete.
        RuntimeError: if Chrome/Xvfb/Playwright fails.
    """
    if not track_object:
        raise ValueError('track_object is required for Amazon downloads')

    # Import here to avoid circular imports at module level
    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()

    api_base_url = (settings.get('amazon_api_base_url') or '').strip().rstrip('/')
    site_key = (settings.get('amazon_turnstile_site_key') or '').strip()
    monochrome_domain = (settings.get('amazon_monochrome_domain') or '').strip()

    if not api_base_url:
        raise ValueError('Amazon API base URL is not configured')
    if not site_key:
        raise ValueError('Amazon Turnstile site key is not configured')
    if not monochrome_domain:
        raise ValueError('Amazon Monochrome domain is not configured')

    track_metadata = _build_track_metadata(track_object)
    amazon_quality = _map_quality(quality)
    track_metadata['quality'] = amazon_quality

    logger.info(
        "[AMAZON] Downloading: title='%s', artist='%s', album='%s', quality=%s",
        track_metadata['title'], track_metadata['artist'],
        track_metadata['album'], amazon_quality,
    )

    xvfb_proc = None
    try:
        # Start Xvfb
        xvfb_proc = _start_xvfb()

        # Launch Playwright with persistent Chrome context
        from playwright.sync_api import sync_playwright

        chrome_env = os.environ.copy()
        for key in ('WAYLAND_DISPLAY', 'XDG_SESSION_TYPE', 'GDK_BACKEND'):
            chrome_env.pop(key, None)
        chrome_env['DISPLAY'] = ':99'

        profile_dir = os.path.expanduser('~/.squidly-chrome-profile')

        logger.info("[AMAZON] Launching Chrome via Playwright")
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
            logger.info("[AMAZON] Navigating to %s for Turnstile auth", monochrome_domain)
            page.route('**/*', lambda route: route.abort()
                       if monochrome_domain in route.request.url
                          and route.request.resource_type in ('stylesheet', 'image', 'font', 'script', 'xhr', 'fetch')
                       else route.continue_())
            page.goto(f'https://{monochrome_domain}', wait_until='domcontentloaded')

            # Run Turnstile + Amazon API flow
            logger.info("[AMAZON] Authenticating and calling Amazon Music API")
            result = _call_amazon_api_from_browser(page, api_base_url, site_key, track_metadata)

            page.close()
            context.close()

        stream_url = result.get('stream_url', '')
        decryption_key = result.get('decryption_key', '')
        title_display = result.get('title', track_metadata['title'])
        artist_display = result.get('artist', track_metadata['artist'])

        if not stream_url or not decryption_key:
            raise ValueError(f'Missing stream URL or decryption key: {result}')

        logger.info(
            "[AMAZON] Got stream: title='%s', artist='%s', quality=%s",
            title_display, artist_display, result.get('quality', amazon_quality),
        )

        # Download encrypted stream
        temp_folder = '/app/temp'
        os.makedirs(temp_folder, exist_ok=True)
        encrypted_path = os.path.join(temp_folder, f'amazon_encrypted_{track_id or "track"}.mp4')

        logger.info("[AMAZON] Downloading encrypted stream")
        subprocess.run(
            ['curl', '-L', '-s', '-o', encrypted_path, stream_url],
            check=True,
            timeout=300,
        )

        file_size = os.path.getsize(encrypted_path)
        logger.info("[AMAZON] Encrypted stream downloaded: %.1f MB", file_size / (1024 * 1024))

        # Decrypt to FLAC
        output_path = os.path.join(temp_folder, f'amazon_{track_id or "track"}.flac')
        logger.info("[AMAZON] Decrypting to FLAC")
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

        flac_size = os.path.getsize(output_path)
        logger.info("[AMAZON] Decrypted: %.1f MB → %s", flac_size / (1024 * 1024), output_path)

        # Cleanup encrypted temp file
        try:
            os.remove(encrypted_path)
        except OSError:
            pass

        return {
            'file_path': output_path,
            'source': 'amazon',
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
