"""Plex-related helpers and utilities."""

import json
import re
import threading
from datetime import datetime
import requests
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer
from squidly.db import get_db_connection
from squidly.storage import get_plex_config, save_plex_config

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
    except Exception as e:
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
        print(f"[PLEX] Failed to fetch Plex users: {str(e)}", flush=True)
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
                        print(f"[PLEX] Failed to switch to managed user {user_id_str}: {e}", flush=True)
                        continue
        except Exception as e:
            print(f"[PLEX] Failed to fetch managed users for user selection {user_id}: {e}", flush=True)

        return plex
    except Exception as e:
        print(f"[PLEX] Failed to create PlexServer for user {user_id}: {e}", flush=True)
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
        print(f"[PLEX] Failed to fetch playlists: {str(e)}", flush=True)
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
        print(
            f"[PLEX] Add-to-playlist start: url={server_url}, library='{library_name}', playlist='{playlist_name}', token_len={token_len}, user_id={user_id}",
            flush=True
        )

        plex = _get_plex_server_for_user(server_url, api_token, user_id)
        print("[PLEX] Connected to Plex server", flush=True)

        library = None
        for section in plex.library.sections():
            if section.title == library_name and section.type == 'artist':
                library = section
                break

        if not library:
            available = [f"{section.title} ({section.type})" for section in plex.library.sections()]
            print(f"[PLEX] Library not found. Available sections: {available}", flush=True)
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
        print(f"[PLEX] Resolving ratingKey via tracks for file_path={normalized_file_path}", flush=True)

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
            print(f"[PLEX] No library_id found in tracks for file_path={normalized_file_path}", flush=True)
            return False, (
                f'file_path "{normalized_file_path}" was not found in tracks with a library_id. '
                'Run a Plex library sync first.'
            )

        track = None
        for rating_key in rating_keys:
            metadata_key = rating_key if rating_key.startswith('/library/metadata/') else f'/library/metadata/{rating_key}'
            try:
                candidate = plex.fetchItem(metadata_key)
                if candidate is not None:
                    track = candidate
                    print(f"[PLEX] Resolved track using ratingKey={rating_key}", flush=True)
                    break
            except Exception as e:
                print(f"[PLEX] Failed to fetch item for ratingKey={rating_key}: {str(e)}", flush=True)

        if track is None:
            return False, (
                f'Could not resolve Plex track for file_path "{normalized_file_path}" using stored library IDs. '
                'Run a Plex library sync to refresh the tracks table.'
            )

        # Synchronize playlist operations to prevent duplicates during concurrent jobs
        with _playlist_operation_lock:
            playlist = None
            try:
                playlists = plex.playlists()
                print(f"[PLEX] Existing playlists found: {len(playlists)}", flush=True)
                for pl in playlists:
                    if pl.title == playlist_name:
                        playlist = pl
                        break
            except Exception as e:
                print(f"[PLEX] Error getting playlists: {str(e)}", flush=True)

            if not playlist:
                try:
                    print(f"[PLEX] Creating playlist: {playlist_name}", flush=True)
                    playlist = plex.createPlaylist(playlist_name, items=[track])
                    print(f"[PLEX] Created new playlist: {playlist_name}", flush=True)
                    return True, f'Created playlist "{playlist_name}" and added track'
                except Exception as e:
                    print(f"[PLEX] Error creating playlist: {str(e)}", flush=True)
                    return False, f'Error creating playlist: {str(e)}'
            else:
                print(f"[PLEX] Using existing playlist: {playlist_name}", flush=True)
            
            try:
                playlist.addItems(track)
                print(f"[PLEX] Added track to playlist: {playlist_name}", flush=True)
                return True, f'Added track to playlist "{playlist_name}"'
            except Exception as e:
                if 'already in' in str(e).lower():
                    return True, f'Track already in playlist "{playlist_name}"'
                print(f"[PLEX] Error adding track to playlist: {str(e)}", flush=True)
                return False, f'Error adding to playlist: {str(e)}'

    except Exception as e:
        print(f"[PLEX] Unexpected error: {str(e)}", flush=True)
        return False, f'Unexpected error: {str(e)}'
