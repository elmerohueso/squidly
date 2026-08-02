"""Shared Cloudflare Turnstile solving utility.

Uses Playwright + Chrome on Xvfb to solve Cloudflare Turnstile challenges
and exchange the resulting token for a JWT access token.

Requires: google-chrome, xvfb, playwright (with chromium)
"""

import json
import logging
import os
import subprocess
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Browser JS: Solve Turnstile → exchange for JWT
# ---------------------------------------------------------------------------

# Template placeholders: API_BASE_URL, SITE_KEY, AUTH_PATH, TOKEN_FIELD
_TURNSTILE_JS = '''
(async () => {
    const API_BASE_URL = %s;
    const SITE_KEY = %s;
    const AUTH_PATH = %s;
    const TOKEN_FIELD = %s;

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
    const body = {};
    body[TOKEN_FIELD] = token;
    const authResp = await fetch(API_BASE_URL + AUTH_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!authResp.ok) {
        const text = await authResp.text();
        throw new Error('Auth failed: ' + authResp.status + ' ' + text);
    }
    const authData = await authResp.json();
    return authData.access_token || authData.token || authData.jwt;
})()
'''


def start_xvfb():
    """Start Xvfb virtual framebuffer. Returns the subprocess."""
    display = ':99'
    logger.info("[TURNSTILE] Starting Xvfb on %s", display)
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


def solve_turnstile_get_jwt(
    page,
    api_base_url,
    site_key,
    auth_path='/auth/turnstile',
    token_field='turnstile_token',
    action=None,
):
    """Run Turnstile solve + JWT exchange in a browser page.

    Args:
        page: A Playwright page object (already navigated to a suitable origin).
        api_base_url: Base URL of the API (e.g. 'https://track-api.monochrome.tf').
        site_key: Cloudflare Turnstile site key.
        auth_path: Path to the auth endpoint (e.g. '/auth/turnstile').
        token_field: JSON body field name for the Turnstile token (e.g. 'turnstile_token').
        action: Optional Turnstile action parameter (e.g. 'auth').

    Returns:
        The JWT access token string.
    """
    js = _TURNSTILE_JS % (
        json.dumps(api_base_url),
        json.dumps(site_key),
        json.dumps(auth_path),
        json.dumps(token_field),
    )
    if action:
        action_json = json.dumps(action)
        js = js.replace(
            "execution: 'execute',",
            f"execution: 'execute', action: {action_json},",
        )
    return page.evaluate(js)
