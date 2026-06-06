"""Deezer API client for Squidly.

Handles ISRC search, ARL-based session auth, FLAC stream URL retrieval,
and Blowfish-decrypted download.
"""

import hashlib
import logging
import os
from typing import Optional

import requests
from Crypto.Cipher import Blowfish

logger = logging.getLogger(__name__)

_USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:135.0) Gecko/20100101 Firefox/135.0'


def md5hex(data: bytes) -> bytes:
    """Return the hex-encoded MD5 digest of *data* as bytes."""
    return hashlib.md5(data).hexdigest().encode()


def calcbfkey(songid: str) -> str:
    """Calculate the Blowfish decryption key for a given Deezer track ID.

    Ported from deezer-downloader.
    """
    key = b"g4el58wc0zvf9na1"
    songid_md5 = md5hex(songid.encode())
    xor_op = lambda i: chr(songid_md5[i] ^ songid_md5[i + 16] ^ key[i])
    return "".join([xor_op(i) for i in range(16)])


def decryptfile(
    response: requests.Response,
    key: str,
    output_path: str,
) -> bool:
    """Download and decrypt a Deezer audio stream to *output_path*.

    Every 3rd 2048-byte block is Blowfish-CBC encrypted (BF_CBC_STRIPE).
    """
    block_size = 2048
    iv = bytes.fromhex("0001020304050607")

    try:
        with open(output_path, 'wb') as f:
            i = 0
            for data in response.iter_content(block_size):
                if not data:
                    break

                is_encrypted = (i % 3) == 0
                is_whole_block = len(data) == block_size

                if is_encrypted and is_whole_block:
                    c = Blowfish.new(key.encode(), Blowfish.MODE_CBC, iv)
                    data = c.decrypt(data)

                f.write(data)
                i += 1
    except Exception as exc:
        logger.error("[DEEZER] Decrypt/download failed: %s", exc)
        return False

    return True


def search_deezer_track(isrc: str, timeout: int = 30) -> Optional[dict]:
    """Search the public Deezer API for a track by ISRC.

    Hits ``GET https://api.deezer.com/track/isrc:{ISRC}`` (no auth).

    Returns:
        The track dict on success (contains ``id``, ``title``, ``track_token``,
        ``isrc``, etc.), or None on failure.
    """
    url = f"https://api.deezer.com/track/isrc:{isrc}"
    logger.info("[DEEZER] Searching for ISRC: %s", isrc)

    try:
        resp = requests.get(url, timeout=timeout, headers={'User-Agent': _USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[DEEZER] Search request failed for ISRC %s: %s", isrc, exc)
        return None

    data = resp.json()
    if 'error' in data:
        logger.error("[DEEZER] Search returned an error for ISRC %s: %s", isrc, data['error'])
        return None

    track_id = data.get('id')
    track_title = data.get('title', 'Unknown')
    logger.info("[DEEZER] Found track: %s (ID: %s)", track_title, track_id)
    return data


def get_deezer_session(arl: str, timeout: int = 30) -> Optional[dict]:
    """Authenticate with Deezer using an ARL cookie and return session info.

    Creates a requests session with the ARL, calls the gw-light API to get
    a license token and lossless flag.

    Returns:
        A dict with ``license_token`` (str), ``lossless`` (bool), and
        ``session`` (requests.Session), or None on failure.
    """
    headers = {
        'User-Agent': _USER_AGENT,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.deezer.com',
        'Accept': '*/*',
        'Referer': 'https://www.deezer.com/login',
    }

    session = requests.session()
    session.headers.update(headers)
    session.cookies.update({'arl': arl, 'comeback': '1'})

    logger.info("[DEEZER] Getting user data from gw-light API")

    try:
        resp = session.post(
            'https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=',
            data='',
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[DEEZER] Failed to get user data: %s", exc)
        return None

    try:
        results = resp.json()['results']
        options = results['USER']['OPTIONS']
        license_token = options['license_token']
        web_sound_quality = options['web_sound_quality']
        lossless = web_sound_quality.get('lossless', False)
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("[DEEZER] Failed to parse user data response: %s", exc)
        return None

    logger.info("[DEEZER] Session established (lossless: %s)", lossless)
    return {
        'license_token': license_token,
        'lossless': lossless,
        'session': session,
    }


def get_deezer_stream_url(
    track_token: str,
    license_token: str,
    session: requests.Session,
    timeout: int = 30,
) -> Optional[str]:
    """Get a FLAC stream URL for a Deezer track.

    POSTs to the media API with the track token and license token requesting
    a FLAC stream encrypted with BF_CBC_STRIPE.

    Returns:
        The stream URL string, or None on failure.
    """
    payload = {
        'license_token': license_token,
        'media': [{
            'type': 'FULL',
            'formats': [{'cipher': 'BF_CBC_STRIPE', 'format': 'FLAC'}],
        }],
        'track_tokens': [track_token],
    }

    logger.info("[DEEZER] Getting stream URL for track token %s", track_token[:20])

    try:
        resp = session.post(
            'https://media.deezer.com/v1/get_url',
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[DEEZER] Stream URL request failed: %s", exc)
        return None

    try:
        data = resp.json()
        url = data['data'][0]['media'][0]['sources'][0]['url']
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.error("[DEEZER] Failed to parse stream URL response: %s", exc)
        return None

    return url


def download_deezer_track(
    isrc: str,
    output_path: str,
    arl: str,
    timeout: int = 30,
) -> Optional[dict]:
    """Download a track from Deezer by ISRC.

    Full pipeline:
    1. Search the public API for the track by ISRC
    2. Authenticate with the ARL cookie to get a license token
    3. Get a FLAC stream URL
    4. Download and decrypt the stream to *output_path*

    Returns:
        A dict with ``track`` (the track dict from the search response) and
        ``file_path`` (str), or None if any step fails.
    """
    # Step 1: Search by ISRC
    track = search_deezer_track(isrc, timeout=timeout)
    if track is None:
        logger.error("[DEEZER] No track found for ISRC %s — cannot download", isrc)
        return None

    track_token = track.get('track_token') or track.get('TRACK_TOKEN')
    song_id = track.get('id') or track.get('SNG_ID')

    if not track_token:
        logger.error("[DEEZER] Track found for ISRC %s but has no track_token", isrc)
        return None

    if not song_id:
        logger.error("[DEEZER] Track found for ISRC %s but has no id/SNG_ID", isrc)
        return None

    # Step 2: Get Deezer session + license token
    session_info = get_deezer_session(arl, timeout=timeout)
    if session_info is None:
        logger.error("[DEEZER] Could not create Deezer session for ISRC %s", isrc)
        return None

    license_token = session_info['license_token']
    session = session_info['session']

    # Step 3: Get stream URL
    stream_url = get_deezer_stream_url(track_token, license_token, session, timeout=timeout)
    if stream_url is None:
        logger.error("[DEEZER] Could not get stream URL for ISRC %s", isrc)
        return None

    # Step 4: Download and decrypt
    logger.info("[DEEZER] Downloading from %s", stream_url[:80])
    try:
        resp = session.get(stream_url, stream=True, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("[DEEZER] Download request failed for ISRC %s: %s", isrc, exc)
        return None

    key = calcbfkey(str(song_id))
    success = decryptfile(resp, key, output_path)
    if not success:
        logger.error("[DEEZER] Decrypt/download failed for ISRC %s", isrc)
        return None

    logger.info("[DEEZER] Download complete for ISRC %s -> %s", isrc, output_path)
    try:
        actual_size = os.path.getsize(output_path)
        logger.info("[DEEZER] Written file size: %d bytes (%s)", actual_size, output_path)
    except OSError:
        logger.info("[DEEZER] Written file size: unknown (%s)", output_path)
    return {
        'track': track,
        'file_path': output_path,
    }
