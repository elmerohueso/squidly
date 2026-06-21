"""Plex-related helpers and utilities."""

import concurrent.futures
import json
import logging
import re
import threading
import time
from datetime import datetime
from urllib.parse import quote_plus
import requests
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer
from squidly.infrastructure.db import get_db_connection
from squidly.infrastructure.storage import (
    get_plex_config,
    save_plex_config,
)

logger = logging.getLogger(__name__)

# For PIN login state (in-memory, per-process; production should use persistent store)
plex_pin_sessions = {}

# --- Plex Healthcheck Status Tracking ---
_plex_health_status = {
    'ok': None,
    'value': None,
    'timestamp': None
}
_plex_health_status_lock = threading.Lock()
_playlist_operation_lock = threading.Lock()


def _plex_call_with_timeout(fn, *args, timeout=30, label="Plex operation", **kwargs):
    """Execute a Plex API call with a hard timeout.

    If the call doesn't complete within `timeout` seconds, raises TimeoutError.
    This prevents individual Plex API calls from hanging indefinitely.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args, **kwargs)
        return future.result(timeout=timeout)


def _get_or_create_playlist(plex, playlist_name, items=None):
    """Find an existing playlist by name, or create a new one.

    Returns (playlist, created) tuple.
    Must be called within _playlist_operation_lock.
    """
    try:
        playlists = plex.playlists()
        for pl in playlists:
            if pl.title == playlist_name:
                return pl, False
    except Exception as e:
        logger.warning("[PLEX] Error listing playlists: %s", str(e))

    if items:
        playlist = plex.createPlaylist(playlist_name, items=items)
        logger.info("[PLEX] Created playlist '%s' with %d tracks", playlist_name, len(items))
    else:
        playlist = plex.createPlaylist(playlist_name)
        logger.info("[PLEX] Created empty playlist '%s'", playlist_name)
    return playlist, True


def _add_items_to_playlist(playlist, items):
    """Add items to a playlist, handling 'already in' errors gracefully.

    Returns (added, skipped, failed) counts.
    """
    added = 0
    skipped = 0
    failed = 0
    for item in items:
        try:
            playlist.addItems(item)
            added += 1
        except Exception as e:
            if 'already in' in str(e).lower():
                skipped += 1
            else:
                logger.warning("[PLEX] Error adding item to playlist '%s': %s", playlist.title, str(e))
                failed += 1
    return added, skipped, failed


def set_plex_health_status(ok, value):
    """Update cached Plex healthcheck status."""
    with _plex_health_status_lock:
        _plex_health_status['ok'] = ok
        _plex_health_status['value'] = value
        _plex_health_status['timestamp'] = datetime.utcnow().isoformat() + 'Z'


def get_plex_health_status():
    """Return cached Plex healthcheck status."""
    with _plex_health_status_lock:
        return dict(_plex_health_status)


def plex_healthcheck():
    """Check whether stored Plex config is valid and reachable."""
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()

    if not server_url or not api_token:
        set_plex_health_status(False, 'No Plex credentials configured')
        return False, 'No Plex credentials configured'

    try:
        plex = PlexServer(server_url.rstrip('/'), api_token, timeout=10)
        name = getattr(plex, 'friendlyName', None) or getattr(plex, 'title', None) or 'Plex'
        set_plex_health_status(True, name)
        return True, name
    except BaseException as e:
        msg = str(e)
        set_plex_health_status(False, msg)
        return False, msg


def test_plex_connection(server_url, api_token):
    """Test that Plex credentials are valid and return list of music libraries."""
    if not server_url.startswith('http://') and not server_url.startswith('https://'):
        return False, 'Server URL must start with http:// or https://', None

    test_url = f"{server_url.rstrip('/')}/library/sections"
    headers = {'X-Plex-Token': api_token}

    try:
        response = requests.get(test_url, headers=headers, timeout=10, verify=False)
        if response.status_code == 401:
            return False, 'Invalid API token or unauthorized access', None
        if response.status_code == 404:
            return False, 'Server not found at URL', None
        if not response.ok:
            return False, f'Server returned status {response.status_code}', None

        try:
            plex = PlexServer(server_url.rstrip('/'), api_token, timeout=10)
            libraries = [s.title for s in plex.library.sections() if s.type == 'artist']
            return True, 'Successfully connected to Plex server', libraries
        except Exception as e:
            return True, 'Connected successfully (could not retrieve libraries)', []

    except requests.exceptions.Timeout:
        return False, 'Connection timeout - server not responding', None
    except requests.exceptions.ConnectionError:
        return False, 'Cannot connect to server - check URL and network', None
    except Exception as e:
        return False, f'Failed to connect to Plex: {e}', None


def get_all_plex_users():
    """Fetch all users (owner and managed) from MyPlexAccount."""
    config = get_plex_config()
    api_token = config.get('api_token')

    if not api_token:
        return False, [], "Plex API token not configured"

    try:
        acc = MyPlexAccount(token=api_token)
        owner = {
            'id': str(acc.id),
            'client_id': str(acc.id),
            'title': acc.title or acc.username,
            'username': acc.username,
            'email': acc.email,
            'is_owner': True,
            'is_managed': False,
            'thumb': getattr(acc, 'thumb', None)
        }
        users = [owner]

        for u in acc.users():
            # Only include restricted managed users (home users), not Plex friends.
            is_restricted = getattr(u, 'restricted', None)
            if is_restricted not in (True, 1, '1'):
                continue

            users.append({
                'id': str(u.id),
                'client_id': str(u.id),
                'title': u.title,
                'username': u.username,
                'email': u.email,
                'is_owner': False,
                'is_managed': True,
                'thumb': getattr(u, 'thumb', None)
            })

        return True, users, None
    except Exception as e:
        logger.exception("[PLEX] Failed to fetch Plex users")
        return False, [], str(e)


def _get_plex_server_for_user(server_url, api_token, user_id=None):
    """Return a PlexServer instance for the owner or a managed user."""
    try:
        server_url = server_url.rstrip('/')
        plex = PlexServer(server_url, api_token, timeout=10)
        if not user_id:
            return plex

        # Attempt to use managed user if specified
        try:
            acc = MyPlexAccount(token=api_token)
            users = list(acc.users())
            user_id_str = str(user_id or '').strip()
            user_id_lower = user_id_str.lower()
            
            for u in users:
                candidate_ids = [
                    str(getattr(u, 'id', '') or '').strip(),
                    str(getattr(u, 'username', '') or '').strip(),
                    str(getattr(u, 'title', '') or '').strip(),
                    str(getattr(u, 'uuid', '') or '').strip(),
                    str(getattr(u, 'client_id', '') or '').strip(),
                ]
                candidate_ids_lower = [c.lower() for c in candidate_ids if c]
                if user_id_lower and user_id_lower in candidate_ids_lower:
                    try:
                        # Use switchUser to get a PlexServer instance scoped to the managed user
                        return plex.switchUser(u)
                    except Exception as e:
                        logger.warning("[PLEX] Failed to switch to managed user %s: %s", user_id_str, e)
                        continue
        except Exception as e:
                logger.warning("[PLEX] Failed to fetch managed users for user selection %s: %s", user_id, e)

        return plex
    except Exception as e:
        logger.exception("[PLEX] Failed to create PlexServer for user %s", user_id)
        raise


def get_plex_music_playlists(server_url, api_token, user_id=None):
    """Return list of non-smart audio playlists with their ratingKeys."""
    try:
        plex = _get_plex_server_for_user(server_url, api_token, user_id)
        playlists = []
        for playlist in plex.playlists():
            playlist_type = (getattr(playlist, 'playlistType', None) or '').lower()
            if playlist_type and playlist_type != 'audio':
                continue

            smart_attr = getattr(playlist, 'smart', False)
            try:
                is_smart = smart_attr() if callable(smart_attr) else bool(smart_attr)
            except Exception:
                is_smart = bool(smart_attr)

            if is_smart:
                continue

            title = getattr(playlist, 'title', None)
            rating_key = getattr(playlist, 'ratingKey', None)
            if isinstance(title, str) and title.strip():
                playlists.append({
                    'name': title.strip(),
                    'ratingKey': str(rating_key) if rating_key else None
                })

        return True, sorted(playlists, key=lambda p: p['name'].casefold()), None

    except Exception as e:
        logger.exception("[PLEX] Failed to fetch playlists")
        return False, [], str(e)


def add_tracks_to_plex_playlist(server_url, api_token, library_name, playlist_name, full_path, user_id=None):
    """Add a track to a Plex playlist, resolving it via local tracks table."""
    try:
        # Robustness: extract name if playlist_name is a dictionary (from potential frontend bug)
        if isinstance(playlist_name, dict) and 'name' in playlist_name:
            playlist_name = playlist_name['name']
        
        playlist_name = str(playlist_name or '').strip()
        if not playlist_name:
            return False, 'playlist_name is required'

        server_url = server_url.rstrip('/')
        token_len = len(api_token) if isinstance(api_token, str) else 0
        logger.info(
            "[PLEX] Add-to-playlist start: url=%s, library='%s', playlist='%s', token_len=%d, user_id=%s",
            server_url, library_name, playlist_name, token_len, user_id,
        )

        plex = _get_plex_server_for_user(server_url, api_token, user_id)
        logger.info("[PLEX] Connected to Plex server")

        library = None
        for section in plex.library.sections():
            if section.title == library_name and section.type == 'artist':
                library = section
                break

        if not library:
            available = [f"{section.title} ({section.type})" for section in plex.library.sections()]
            logger.info("[PLEX] Library not found. Available sections: %s", available)
            return False, f'Library "{library_name}" not found or is not a music library'

        raw_full_path = str(full_path or '').strip()
        if not raw_full_path:
            return False, 'file_path is required to resolve Plex ratingKey'

        path_parts = [part for part in re.split(r'[\\/]+', raw_full_path) if part]
        if not path_parts:
            return False, 'file_path is required to resolve Plex ratingKey'

        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        normalized_file_path = '\\'.join(tail_parts)
        trailing_suffix = '/'.join(tail_parts)
        logger.info("[PLEX] Resolving ratingKey via tracks for file_path=%s", normalized_file_path)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT library_id, title, artist_id
            FROM tracks
            WHERE lower(right(replace(path, '\\', '/'), length(%s))) = lower(%s)
              AND library_id IS NOT NULL
              AND library_id <> ''
            ORDER BY last_seen_at DESC
            """,
            (trailing_suffix, trailing_suffix)
        )
        rating_rows = cur.fetchall() or []
        conn.close()

        rating_keys = [
            str(row.get('library_id') or '').strip()
            for row in rating_rows
            if str(row.get('library_id') or '').strip()
        ]

        if not rating_keys:
            logger.info("[PLEX] No library_id found in tracks for file_path=%s", normalized_file_path)
            return False, (
                f'file_path "{normalized_file_path}" was not found in tracks with a library_id. '
                'Run a Plex library sync first.'
            )

        track = None
        for rating_key in rating_keys:
            metadata_key = rating_key if rating_key.startswith('/library/metadata/') else f'/library/metadata/{rating_key}'
            try:
                candidate = _plex_call_with_timeout(plex.fetchItem, metadata_key, timeout=15, label="fetchItem")
                if candidate is not None:
                    track = candidate
                    logger.info("[PLEX] Resolved track using ratingKey=%s", rating_key)
                    break
            except Exception as e:
                logger.warning("[PLEX] Failed to fetch item for ratingKey=%s: %s", rating_key, str(e))

        if track is None:
            return False, (
                f'Could not resolve Plex track for file_path "{normalized_file_path}" using stored library IDs. '
                'Run a Plex library sync to refresh the tracks table.'
            )

        with _playlist_operation_lock:
            playlist, created = _get_or_create_playlist(plex, playlist_name, items=[track])
            if created:
                return True, f'Created playlist "{playlist_name}" and added track'

            added, skipped, failed = _add_items_to_playlist(playlist, [track])
            if added:
                return True, f'Added track to playlist "{playlist_name}"'
            if skipped:
                return True, f'Track already in playlist "{playlist_name}"'
            return False, f'Failed to add track to playlist "{playlist_name}"'

    except Exception as e:
        logger.exception("[PLEX] Unexpected error in add_tracks_to_plex_playlist")
        return False, f'Unexpected error: {str(e)}'


def _is_plex_library_scan_active(plex, library):
    """Best-effort check for whether the target Plex library is actively scanning."""
    try:
        _plex_call_with_timeout(library.reload, timeout=10, label="library.reload")
        if bool(getattr(library, 'refreshing', False)):
            return True
    except Exception:
        pass

    section_id = str(getattr(library, 'key', '') or '').strip('/')

    try:
        activities = _plex_call_with_timeout(plex.activities, timeout=10, label="plex.activities") or []
    except Exception:
        activities = []

    for activity in activities:
        title = str(getattr(activity, 'title', '') or '').lower()
        activity_type = str(getattr(activity, 'type', '') or '').lower()
        activity_context = str(getattr(activity, 'context', '') or '').lower()

        data = getattr(activity, '_data', None)
        data_text = ''
        if data is not None:
            try:
                data_text = json.dumps(data).lower()
            except Exception:
                data_text = str(data).lower()

        mentions_scan = ('scan' in title) or ('scan' in activity_type) or ('scan' in activity_context) or ('scan' in data_text)
        if not mentions_scan:
            continue

        if section_id:
            if section_id in data_text or section_id in activity_context:
                return True
        else:
            return True

    return False


def wait_for_plex_library_scan_completion(plex, library, timeout_seconds=600, poll_interval_seconds=5, startup_grace_seconds=30):
    """
    Poll Plex until the library scan appears to finish.

    Returns:
        tuple[bool, bool]: (completed, saw_scan_active)
    """
    start = time.monotonic()
    saw_active = False

    while True:
        elapsed = time.monotonic() - start
        active = _is_plex_library_scan_active(plex, library)

        if active:
            saw_active = True
            logger.info('[LIBRARY_UPDATE] Plex scan still in progress...')
        elif saw_active:
            logger.info('[LIBRARY_UPDATE] Plex scan appears complete.')
            return True, True
        elif elapsed >= startup_grace_seconds:
            logger.info('[LIBRARY_UPDATE] Did not observe an active scan during startup grace window.')
            return False, False

        if elapsed >= timeout_seconds:
            logger.warning('[LIBRARY_UPDATE] Timed out waiting for Plex scan completion.')
            return False, saw_active

        time.sleep(max(1, poll_interval_seconds))


def _resolve_plex_user_context(plex, user_id):
    """Best-effort managed user switch for Plex context."""
    requested_user_id = str(user_id or '').strip()
    if not requested_user_id:
        return plex, None

    selected_user = None
    success, users, _ = get_all_plex_users()
    if success:
        for user in users:
            candidate_ids = {
                str(user.get('client_id') or '').strip(),
                str(user.get('id') or '').strip(),
                str(user.get('username') or '').strip(),
                str(user.get('title') or '').strip(),
            }
            candidate_ids = {value for value in candidate_ids if value}
            if requested_user_id in candidate_ids:
                selected_user = user
                break

    if selected_user and not bool(selected_user.get('is_owner')):
        switch_target = (
            str(selected_user.get('username') or '').strip()
            or str(selected_user.get('title') or '').strip()
            or str(selected_user.get('id') or '').strip()
            or requested_user_id
        )
        try:
            switched = plex.switchUser(switch_target)
            logger.info("[PLEX_LIBRARY] Switched to user %s (requested %s)", switch_target, requested_user_id)
            return switched, switch_target
        except Exception as e:
            logger.warning("[PLEX_LIBRARY] Failed to switch user %s via '%s': %s. Using owner context.", requested_user_id, switch_target, str(e))
            return plex, None

    if selected_user and bool(selected_user.get('is_owner')):
        logger.info("[PLEX_LIBRARY] Requested owner user %s; using owner context", requested_user_id)
    else:
        logger.info("[PLEX_LIBRARY] User %s not found in current account; using owner context", requested_user_id)

    return plex, None


def _resolve_plex_library_context(server_url, api_token, library_name, user_id=None):
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=10)
    plex, effective_user = _resolve_plex_user_context(plex, user_id)

    library = None
    for section in plex.library.sections():
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    return plex, library, effective_user


def _build_plex_image_url(server_url, api_token, image_path, image_size=None):
    raw_path = str(image_path or '').strip()
    if not raw_path:
        return None

    base = server_url.rstrip('/')
    if raw_path.startswith('http://') or raw_path.startswith('https://'):
        return raw_path

    sized_path = raw_path
    if image_size:
        joiner = '&' if '?' in sized_path else '?'
        sized_path = f'{sized_path}{joiner}width={int(image_size)}&height={int(image_size)}&minSize=1&upscale=1'

    token = quote_plus(str(api_token or '').strip())
    if not token:
        return f'{base}{sized_path}'

    joiner = '&' if '?' in sized_path else '?'
    return f'{base}{sized_path}{joiner}X-Plex-Token={token}'


def _get_match_review_plex_context():
    """Get Plex context (server_url, api_token, library) for match review artwork.
    
    Returns (server_url, api_token, library) tuple, or (None, None, None) if
    Plex is not configured or library cannot be resolved.
    """
    from squidly.infrastructure.storage import get_plex_config
    
    try:
        config = get_plex_config()
        server_url = str(config.get('server_url') or '').strip()
        api_token = str(config.get('api_token') or '').strip()
        library_name = str(config.get('library_name') or '').strip()
        if not server_url or not api_token or not library_name:
            return None, None, None

        _, library, _ = _resolve_plex_library_context(server_url, api_token, library_name)
        if not library:
            return None, None, None

        return server_url, api_token, library
    except Exception as e:
        logger.warning("[MATCH_REVIEW] Unable to resolve Plex context for artwork: %s", str(e))
        return None, None, None


def _fetch_plex_item_image_map(library, server_url, api_token, library_ids, image_size=None):
    """Fetch Plex artwork URLs for a list of library IDs.
    
    Returns a dict mapping library_id (string) to image URL or None.
    """
    if not library or not server_url or not api_token:
        return {}

    image_map = {}
    for library_id in library_ids or []:
        normalized_id = str(library_id or '').strip()
        if not normalized_id or normalized_id in image_map:
            continue
        try:
            item = library.fetchItem(f'/library/metadata/{normalized_id}')
            image_map[normalized_id] = _build_plex_image_url(
                server_url,
                api_token,
                getattr(item, 'thumb', None),
                image_size=image_size,
            ) if item else None
        except Exception as e:
            logger.warning("[MATCH_REVIEW] Failed to fetch Plex artwork for %s: %s", normalized_id, str(e))
            image_map[normalized_id] = None

    return image_map



def get_last_successful_plex_sync_finished_at():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT finished_at
        FROM jobs
        WHERE job_type = 'plex_library_sync'
          AND status = 'succeeded'
        ORDER BY finished_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    finished_at = row.get('finished_at')
    if finished_at and not isinstance(finished_at, datetime):
        try:
            finished_at = datetime.fromisoformat(str(finished_at))
        except Exception:
            finished_at = None
    if finished_at and hasattr(finished_at, 'replace'):
        finished_at = finished_at.replace(tzinfo=None)
    return finished_at


def delete_plex_playlists_by_keys_or_names(plex_playlist_keys, fallback_names):
    """Delete Plex playlists by their ratingKey, falling back to name matching.
    
    First tries to delete each playlist by its ratingKey. If a key doesn't match,
    falls back to matching against fallback_names by exact title.
    Best-effort: logs failures but doesn't raise.
    
    Returns count of successfully deleted playlists.
    """
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()

    if not server_url or not api_token:
        logger.info("[PLEX] Cannot delete playlists: Plex not configured")
        return 0

    deleted = 0

    try:
        plex = PlexServer(server_url.rstrip('/'), api_token, timeout=10)
        playlists = plex.playlists()

        # Build lookup by title for fallback matching
        playlists_by_title = {}
        for pl in playlists:
            playlists_by_title[pl.title] = pl

        # Build lookup by ratingKey for key-based deletion
        playlists_by_key = {}
        for pl in playlists:
            key = getattr(pl, 'ratingKey', None)
            if key:
                playlists_by_key[str(key)] = pl

        # Keys that were provided but not found — fallback to name matching
        keys_to_delete = set(str(k) for k in plex_playlist_keys if k)

        for key in list(keys_to_delete):
            pl = playlists_by_key.get(key)
            if pl:
                try:
                    pl.delete()
                    logger.info("[PLEX] Deleted playlist by key '%s': '%s'", key, pl.title)
                    deleted += 1
                except Exception as e:
                    logger.warning("[PLEX] Failed to delete playlist by key '%s': %s", key, str(e))
                keys_to_delete.discard(key)

        # Fallback name matching for keys that weren't resolved and provided fallback names
        names_to_delete = set(str(n) for n in fallback_names if n)
        for title, pl in playlists_by_title.items():
            if title in names_to_delete:
                # Skip if already deleted by key
                pl_key = str(getattr(pl, 'ratingKey', '') or '')
                if pl_key in plex_playlist_keys:
                    continue
                try:
                    pl.delete()
                    logger.info("[PLEX] Deleted playlist by name: '%s'", title)
                    deleted += 1
                except Exception as e:
                    logger.warning("[PLEX] Failed to delete playlist '%s': %s", title, str(e))
    except Exception as e:
        logger.exception("[PLEX] Failed to list playlists for key/name deletion")

    return deleted






