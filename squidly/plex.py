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
    """Return a list of owned + managed Plex users."""
    config = get_plex_config()
    token = config.get('api_token')
    if not token:
        return []

    try:
        acc = MyPlexAccount(token=token)
    except Exception as e:
        print(f"[PLEX] Failed to create MyPlexAccount: {e}", flush=True)
        return []

    users = []
    owner_id = str(getattr(acc, 'id', '') or '').strip() or str(getattr(acc, 'username', '') or '').strip() or str(getattr(acc, 'title', '') or '').strip()
    users.append({
        'client_id': owner_id,
        'username': getattr(acc, 'username', None),
        'title': getattr(acc, 'title', None),
        'id': getattr(acc, 'id', None),
        'is_owner': True,
        'is_managed': False,
        'user_obj': acc
    })

    try:
        for u in acc.users():
            # Only include restricted managed users (not Plex friends) to match UI behavior.
            if getattr(u, 'restricted', None) not in (True, 1, '1'):
                continue

            managed_id = str(getattr(u, 'id', '') or '').strip() or str(getattr(u, 'username', '') or '').strip() or str(getattr(u, 'title', '') or '').strip()
            users.append({
                'client_id': managed_id,
                'username': getattr(u, 'username', None),
                'title': getattr(u, 'title', None),
                'id': getattr(u, 'id', None),
                'is_owner': False,
                'is_managed': True,
                'user_obj': u
            })
    except Exception as e:
        print(f"[PLEX] Failed to fetch managed users: {e}", flush=True)

    return users


def _get_plex_server_for_user(server_url, api_token, user_id=None):
    """Return a PlexServer instance for the owner or a managed user."""
    server_url = server_url.rstrip('/')
    plex = PlexServer(server_url, api_token, timeout=10)

    if not user_id:
        return plex

    try:
        acc = MyPlexAccount(token=api_token)
        users = list(acc.users())
        user_id_str = str(user_id or '').strip().lower()
        for u in users:
            candidate_ids = [
                str(getattr(u, 'id', '') or '').strip(),
                str(getattr(u, 'username', '') or '').strip(),
                str(getattr(u, 'title', '') or '').strip(),
                str(getattr(u, 'uuid', '') or '').strip(),
                str(getattr(u, 'client_id', '') or '').strip(),
            ]
            candidate_ids_lower = [c.lower() for c in candidate_ids if c]
            if user_id_str and user_id_str in candidate_ids_lower:
                try:
                    return acc.user(user_id_str)
                except Exception:
                    break
    except Exception as e:
        print(f"[PLEX] Failed to fetch managed users for user selection {user_id}: {e}", flush=True)

    return plex


def get_plex_music_playlists(server_url, api_token, user_id=None):
    """Return list of non-smart audio playlists."""
    try:
        plex = _get_plex_server_for_user(server_url, api_token, user_id)
        playlist_titles = []
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
            if isinstance(title, str) and title.strip():
                playlist_titles.append(title.strip())

        return True, sorted(set(playlist_titles), key=str.casefold), None

    except Exception as e:
        print(f"[PLEX] Failed to fetch playlists: {str(e)}", flush=True)
        return False, [], str(e)


def add_tracks_to_plex_playlist(server_url, api_token, library_name, playlist_name, full_path, user_id=None):
    """Add a track to a Plex playlist, resolving it via local plex_songs table."""
    try:
        server_url = server_url.rstrip('/')
        plex = _get_plex_server_for_user(server_url, api_token, user_id)

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

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT "ratingKey", title, artist
            FROM plex_songs
            WHERE lower(right(replace(file_path, '\\', '/'), length(%s))) = lower(%s)
              AND "ratingKey" IS NOT NULL
              AND btrim("ratingKey") <> ''
            ORDER BY updated_at DESC
            """,
            (trailing_suffix, trailing_suffix)
        )
        rating_rows = cur.fetchall() or []
        conn.close()

        rating_keys = [
            str(row.get('ratingKey') or '').strip()
            for row in rating_rows
            if str(row.get('ratingKey') or '').strip()
        ]

        if not rating_keys:
            return False, (
                f'file_path "{normalized_file_path}" was not found in plex_songs with a ratingKey. '
                'Run a Plex library sync first.'
            )

        track = None
        for rating_key in rating_keys:
            metadata_key = rating_key if rating_key.startswith('/library/metadata/') else f'/library/metadata/{rating_key}'
            try:
                candidate = plex.fetchItem(metadata_key)
                if candidate is not None:
                    track = candidate
                    break
            except Exception as e:
                print(f"[PLEX] Failed to fetch item for ratingKey={rating_key}: {str(e)}", flush=True)

        if track is None:
            return False, (
                f'Could not resolve Plex track for file_path "{normalized_file_path}" using stored ratingKeys. '
                'Run a Plex library sync to refresh plex_songs.'
            )

        playlist = None
        try:
            playlists = plex.playlists()
            for pl in playlists:
                if pl.title == playlist_name:
                    playlist = pl
                    break
        except Exception as e:
            print(f"[PLEX] Error getting playlists: {str(e)}", flush=True)

        if not playlist:
            try:
                playlist = plex.createPlaylist(playlist_name, items=[track])
                return True, f'Created playlist "{playlist_name}" and added track'
            except Exception as e:
                print(f"[PLEX] Error creating playlist: {str(e)}", flush=True)
                return False, f'Error creating playlist: {str(e)}'
        else:
            try:
                playlist.addItems(track)
                return True, f'Added track to playlist "{playlist_name}"'
            except Exception as e:
                if 'already in' in str(e).lower():
                    return True, f'Track already in playlist "{playlist_name}"'
                print(f"[PLEX] Error adding track to playlist: {str(e)}", flush=True)
                return False, f'Error adding to playlist: {str(e)}'

    except Exception as e:
        print(f"[PLEX] Unexpected error: {str(e)}", flush=True)
        return False, f'Unexpected error: {str(e)}'
