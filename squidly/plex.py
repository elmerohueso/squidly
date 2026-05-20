"""Plex-related helpers and utilities."""

import concurrent.futures
import json
import logging
import re
import threading
import time
from datetime import datetime
import requests
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer
from squidly import jobs
from squidly.db import get_db_connection
from squidly.storage import (
    can_start_plex_library_update,
    get_plex_config,
    save_plex_config,
    set_last_library_update_time,
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
        logger.info("[PLEX] Error listing playlists: %s", str(e))

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
                logger.info("[PLEX] Error adding item to playlist '%s': %s", playlist.title, str(e))
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
        logger.info("[PLEX] Failed to fetch Plex users: %s", str(e))
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
                        logger.info("[PLEX] Failed to switch to managed user %s: %s", user_id_str, e)
                        continue
        except Exception as e:
                logger.info("[PLEX] Failed to fetch managed users for user selection %s: %s", user_id, e)

        return plex
    except Exception as e:
        logger.info("[PLEX] Failed to create PlexServer for user %s: %s", user_id, e)
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
        logger.info("[PLEX] Failed to fetch playlists: %s", str(e))
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
                logger.info("[PLEX] Failed to fetch item for ratingKey=%s: %s", rating_key, str(e))

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
        logger.info("[PLEX] Unexpected error: %s", str(e))
        return False, f'Unexpected error: {str(e)}'


def bulk_add_tracks_to_playlists(job_id, server_url, api_token, library_name):
    """Process all rows in pending_playlist_adds, grouped by (user_id, playlist_name).

    Returns a result dict with progress fields for the job card.
    """
    from squidly.jobs import update_job_progress
    from squidly.orchestration import (
        get_pending_playlist_adds,
        delete_pending_playlist_adds,
    )

    stages = {
        'resolving_tracks': 'pending',
        'adding_to_playlists': 'pending',
    }
    progress = {
        'total_tracks': 0,
        'tracks_processed': 0,
        'tracks_added': 0,
        'tracks_skipped': 0,
        'tracks_failed': 0,
    }
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    pending = get_pending_playlist_adds()
    total = len(pending)
    progress['total_tracks'] = total
    update_job_progress(job_id, {'progress': progress})

    logger.info("[BULK_PLAYLIST] Job %s: found %d pending playlist adds", job_id, total)
    for item in pending:
        logger.info("[BULK_PLAYLIST] Job %s: pending add parent_job_id=%s file_path=%s playlist=%s", job_id, item.get('parent_job_id'), item.get('file_path'), item.get('playlist_name'))

    if total == 0:
        stages['resolving_tracks'] = 'skipped'
        stages['adding_to_playlists'] = 'skipped'
        update_job_progress(job_id, {'stages': stages, 'progress': progress})
        return {
            'total_tracks': 0,
            'tracks_added': 0,
            'tracks_skipped': 0,
            'tracks_failed': 0,
            'summary': 'No pending tracks',
        }

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT library_id, path
        FROM tracks
        WHERE library_id IS NOT NULL AND library_id <> ''
        """
    )
    rows = cur.fetchall() or []
    conn.close()

    path_index = {}
    for row in rows:
        raw_path = str(row.get('path') or '').strip()
        library_id = str(row.get('library_id') or '').strip()
        if not raw_path or not library_id:
            continue
        path_parts = [p for p in re.split(r'[\\/]+', raw_path) if p]
        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        path_tail = '\\'.join(tail_parts).lower()
        path_index.setdefault(path_tail, []).append(library_id)
    conn.close()

    stages['resolving_tracks'] = 'done'
    update_job_progress(job_id, {'stages': stages})

    groups = {}
    for item in pending:
        file_path = str(item.get('file_path') or '').strip()
        playlist_name = str(item.get('playlist_name') or '').strip()
        plex_user_id = item.get('plex_user_id')

        path_parts = [p for p in re.split(r'[\\/]+', file_path) if p]
        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        path_tail = '\\'.join(tail_parts).lower()

        library_ids = path_index.get(path_tail, [])
        key = (plex_user_id, playlist_name)
        groups.setdefault(key, {'tracks': [], 'ids': []})
        groups[key]['tracks'].append(item)
        groups[key]['ids'].extend(library_ids)

    stages['adding_to_playlists'] = 'in_progress'
    update_job_progress(job_id, {'stages': stages})

    successful_ids = []
    plex_cache = {}

    for (plex_user_id, playlist_name), group_data in groups.items():
        user_display = plex_user_id or 'Owner'
        logger.info("[BULK_PLAYLIST] Processing %d tracks for playlist '%s' (user: %s)", len(group_data['tracks']), playlist_name, user_display)

        if plex_user_id not in plex_cache:
            try:
                plex_cache[plex_user_id] = _get_plex_server_for_user(server_url, api_token, plex_user_id)
            except Exception as e:
                logger.info("[BULK_PLAYLIST] Failed to get Plex server for user %s: %s", user_display, str(e))
                for item in group_data['tracks']:
                    progress['tracks_processed'] += 1
                    progress['tracks_failed'] += 1
                    update_job_progress(job_id, {'progress': progress})
                continue

        plex = plex_cache[plex_user_id]

        unique_library_ids = list(dict.fromkeys(group_data['ids']))
        tracks_to_add = []

        for rating_key in unique_library_ids:
            metadata_key = rating_key if rating_key.startswith('/library/metadata/') else f'/library/metadata/{rating_key}'
            try:
                candidate = _plex_call_with_timeout(plex.fetchItem, metadata_key, timeout=15, label="fetchItem")
                if candidate is not None:
                    tracks_to_add.append(candidate)
            except Exception as e:
                logger.info("[BULK_PLAYLIST] Failed to fetch ratingKey=%s: %s", rating_key, str(e))

        if not tracks_to_add:
            for item in group_data['tracks']:
                progress['tracks_processed'] += 1
                progress['tracks_failed'] += 1
                update_job_progress(job_id, {'progress': progress})
            continue

        with _playlist_operation_lock:
            playlist, created = _get_or_create_playlist(plex, playlist_name, items=tracks_to_add)
            if created:
                for item in group_data['tracks']:
                    progress['tracks_processed'] += 1
                    progress['tracks_added'] += 1
                    successful_ids.append(item['id'])
                    update_job_progress(job_id, {'progress': progress})
                continue

            added, skipped, failed = _add_items_to_playlist(playlist, tracks_to_add)
            for item in group_data['tracks']:
                progress['tracks_processed'] += 1
                if added > 0:
                    progress['tracks_added'] += 1
                    successful_ids.append(item['id'])
                elif skipped > 0:
                    progress['tracks_skipped'] += 1
                    successful_ids.append(item['id'])
                else:
                    progress['tracks_failed'] += 1
                update_job_progress(job_id, {'progress': progress})

    stages['adding_to_playlists'] = 'done'
    update_job_progress(job_id, {'stages': stages})

    if successful_ids:
        parent_ids = set()
        for item in pending:
            if item['id'] in successful_ids and item.get('parent_job_id'):
                parent_ids.add(item['parent_job_id'])

        for pid in parent_ids:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT result_json FROM jobs WHERE id = %s AND job_type = 'download_track'
                    """,
                    (pid,),
                )
                row = cur.fetchone()
                if row and row.get('result_json'):
                    result = json.loads(row['result_json'])
                    if isinstance(result, dict):
                        stages = result.get('stages', {})
                        if isinstance(stages, dict) and stages.get('playlist_added') == 'queued':
                            stages['playlist_added'] = 'done'
                            result['stages'] = stages
                            cur.execute(
                                """
                                UPDATE jobs SET result_json = %s, updated_at = NOW()
                                WHERE id = %s AND status <> 'cancelled'
                                """,
                                (json.dumps(result, separators=(',', ':'), sort_keys=True), pid),
                            )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.info("[BULK_PLAYLIST] Failed to update parent job %s: %s", pid, str(e))

        delete_pending_playlist_adds(successful_ids)

    summary = (
        f"{progress['tracks_processed']}/{total} tracks processed • "
        f"{progress['tracks_added']} added • "
        f"{progress['tracks_skipped']} skipped • "
        f"{progress['tracks_failed']} failed"
    )

    return {
        'total_tracks': total,
        'tracks_processed': progress['tracks_processed'],
        'tracks_added': progress['tracks_added'],
        'tracks_skipped': progress['tracks_skipped'],
        'tracks_failed': progress['tracks_failed'],
        'summary': summary,
    }


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
            logger.info('[LIBRARY_UPDATE] Timed out waiting for Plex scan completion.')
            return False, saw_active

        time.sleep(max(1, poll_interval_seconds))



def process_plex_library_update_job(job_id, payload, gate_snapshot=None):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        raise ValueError('Plex server_url, api_token, and library_name must be configured before updating library')

    stages = {
        'scanning_plex_library': 'pending'
    }
    progress = {
        'download_gate_status': 'pending',
        'download_gate_checks': 0,
        'download_gate_blocking_count': 0,
        'download_gate_idle_seconds': 0,
        'download_gate_required_idle_seconds': 180,
        'download_gate_last_activity_at': None,
        'scan_detected': False,
        'scan_completed': False,
        'sync_job_id': None,
        'sync_queue_status': 'pending'
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    gate = gate_snapshot or can_start_plex_library_update(required_idle_seconds=180)
    gate_state = gate.get('gate_state') or {}
    progress['download_gate_checks'] = 1
    progress['download_gate_blocking_count'] = gate_state.get('blocking_count') or 0
    progress['download_gate_idle_seconds'] = gate.get('idle_seconds') or 0
    progress['download_gate_required_idle_seconds'] = gate.get('required_idle_seconds') or 180
    progress['download_gate_last_activity_at'] = gate.get('last_activity_at')
    progress['download_gate_status'] = 'ready'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['scanning_plex_library'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    logger.info("[LIBRARY_UPDATE_JOB] Job %s connecting to Plex at %s", job_id, server_url)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)

    library = None
    sections = _plex_call_with_timeout(plex.library.sections, timeout=30, label="library.sections")
    for section in sections:
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    logger.info("[LIBRARY_UPDATE_JOB] Job %s triggering scan on library '%s'", job_id, library_name)
    _plex_call_with_timeout(library.update, timeout=30, label="library.update")

    completed, saw_active = wait_for_plex_library_scan_completion(
        plex,
        library,
        timeout_seconds=600,
        poll_interval_seconds=5,
        startup_grace_seconds=30
    )

    progress['scan_detected'] = bool(saw_active)
    progress['scan_completed'] = bool(completed)
    stages['scanning_plex_library'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    set_last_library_update_time(datetime.utcnow())

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    scan_outcome = 'completed' if completed else ('started_but_timeout' if saw_active else 'not_observed')
    logger.info(
        "[LIBRARY_UPDATE_JOB] Job %s finished. scan_outcome=%s",
        job_id,
        scan_outcome,
    )

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'scan_outcome': scan_outcome,
    }


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
