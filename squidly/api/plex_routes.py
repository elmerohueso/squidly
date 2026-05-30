"""Plex routes."""
import logging
import threading
import re
from urllib.parse import quote_plus

from flask import Blueprint, jsonify, request
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

from squidly.infrastructure.plex import (
    _get_plex_server_for_user,
    get_all_plex_users,
    get_plex_health_status,
    get_plex_music_playlists,
    plex_healthcheck,
    plex_pin_sessions,
    set_plex_health_status,
    test_plex_connection,
)
from squidly.infrastructure.storage import (
    clear_plex_config,
    clear_plex_user_settings,
    get_plex_config,
    get_plex_user_settings,
    save_plex_config,
    save_plex_user_setting,
)
from squidly.jobs.orchestration import start_plex_library_update_job
from squidly.services.playlist_matching import _lookup_track_metadata
from squidly.infrastructure.db import get_db_connection

logger = logging.getLogger(__name__)

plex_bp = Blueprint("plex", __name__)


@plex_bp.route('/api/plex/users', methods=['GET'])
def plex_list_users():
    """Return saved Plex users, or refresh the saved list when requested."""
    sync_flag = str(request.args.get('sync', '') or '').strip().lower() in ('1', 'true', 'yes', 'on')

    if sync_flag:
        try:
            success, users, error = get_all_plex_users()
            if success:
                for user in users:
                    plex_client_id = str(user.get('id') or '').strip()
                    username = str(user.get('title') or user.get('username') or '').strip()
                    plex_owner = bool(user.get('is_owner'))
                    if plex_client_id and username:
                        try:
                            save_plex_user_setting(username, plex_client_id, plex_owner)
                        except Exception as e:
                            logger.info("[PLEX] Failed to save user setting for %s/%s: %s", username, plex_client_id, e)
            else:
                logger.info("[PLEX] Failed to fetch users for sync: %s", error)
        except Exception as e:
            logger.info("[PLEX] /api/plex/users?sync failed: %s", e)
            return jsonify({'users': []}), 200

        result = [
            {k: v for k, v in user.items() if k not in ('user_obj',)}
            for user in users
        ]
        return jsonify({'users': result})

    try:
        rows = get_plex_user_settings()
        result = []
        for row in rows:
            client_id = str(row.get('plex_client_id') or '').strip()
            username = str(row.get('username') or '').strip()
            plex_owner = bool(row.get('plex_owner'))
            if not client_id or not username:
                continue
            result.append({
                'id': client_id,
                'client_id': client_id,
                'username': username,
                'title': username,
                'is_owner': plex_owner,
                'is_managed': not plex_owner,
            })
        return jsonify({'users': result})
    except Exception as e:
        logger.info("[PLEX] /api/plex/users failed to read saved users: %s", e)
        return jsonify({'users': []}), 200


@plex_bp.route('/api/plex/healthcheck', methods=['GET'])
def run_plex_healthcheck():
    ok, value = plex_healthcheck()
    if ok:
        return jsonify({'ok': True, 'server_name': value})
    else:
        status = 400 if value == 'No Plex credentials configured' else 200
        return jsonify({'ok': False, 'error': value}), status


@plex_bp.route('/api/plex/health', methods=['GET'])
def plex_health_status():
    """Return the cached Plex healthcheck state without triggering a new check."""
    return jsonify(get_plex_health_status())


@plex_bp.route('/api/plex/clear_credentials', methods=['POST'])
def plex_clear_credentials():
    """Clear saved Plex configuration and Plex user settings."""
    clear_plex_config()
    clear_plex_user_settings()
    set_plex_health_status(False, 'No Plex credentials configured')
    return jsonify({'ok': True})


@plex_bp.route('/api/plex/pin/start', methods=['POST'])
def plex_pin_start():
    logger.info("[DEBUG] /api/plex/pin/start called")
    try:
        logger.info("[DEBUG] Attempting to create MyPlexPinLogin...")
        pinlogin = MyPlexPinLogin(oauth=False)
        logger.info("[DEBUG] MyPlexPinLogin created")
        pin = pinlogin.pin
        logger.info("[DEBUG] PIN generated: %s", pin)
        client_id = id(pinlogin)
        plex_pin_sessions[client_id] = pinlogin
        logger.info("[DEBUG] Stored pinlogin in session with client_id: %s", client_id)
        return jsonify({
            'ok': True,
            'pin': pin,
            'client_id': client_id
        })
    except Exception as e:
        logger.info("[ERROR] Exception in /api/plex/pin/start: %s", e)
        import traceback; traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@plex_bp.route('/api/plex/pin/status', methods=['POST'])
def plex_pin_status():
    logger.info("[DEBUG] /api/plex/pin/status called")
    data = request.get_json(force=True)
    client_id = data.get('client_id')
    pin = data.get('pin')
    logger.info("[DEBUG] Received client_id=%s, pin=%s", client_id, pin)
    if not client_id or not pin:
        logger.info("[DEBUG] Missing client_id or pin")
        return jsonify({'ok': False, 'error': 'Missing client_id or pin'}), 400
    pinlogin = plex_pin_sessions.get(client_id)
    if not pinlogin:
        logger.info("[DEBUG] Session expired or not found for client_id")
        return jsonify({'ok': False, 'error': 'Session expired or not found'}), 404
    if getattr(pinlogin, 'expired', False):
        logger.info("[DEBUG] PIN expired for client_id")
        return jsonify({'ok': False, 'expired': True, 'error': 'PIN expired'}), 410
    try:
        logger.info("[DEBUG] Calling pinlogin.checkLogin()")
        if pinlogin.checkLogin():
            logger.info("[DEBUG] pinlogin.checkLogin() returned True")
            token = getattr(pinlogin, 'token', None)
            acc = None
            try:
                logger.info("[DEBUG] Creating MyPlexAccount")
                acc = MyPlexAccount(token=token)
            except Exception as e:
                logger.info("[DEBUG] Failed to create MyPlexAccount: %s", e)
                return jsonify({'ok': False, 'error': f'Login succeeded but failed to create MyPlexAccount: {e}'}), 500
            try:
                logger.info("[DEBUG] Fetching acc.resources()")
                res = acc.resources()
            except Exception as e:
                logger.info("[DEBUG] Failed to fetch resources: %s", e)
                return jsonify({'ok': False, 'error': f'Login succeeded but failed to fetch resources: {e}'}), 500
            server_res = None
            for r in res:
                provides = getattr(r, 'provides', '') or ''
                if 'server' in provides:
                    server_res = r
                    break
            baseurl = None
            if server_res:
                conns = getattr(server_res, 'connections', []) or []
                local_conn = next((c for c in conns if getattr(c, 'local', False)), None)
                if local_conn:
                    baseurl = getattr(local_conn, 'uri', None)
            logger.info("[DEBUG] baseurl=%s, token=%s", baseurl, token)
            if baseurl and token:
                logger.info("[DEBUG] Saving Plex config to DB")
                save_plex_config(baseurl, token, '')
                logger.info("[DEBUG] Plex config saved")
            plex_pin_sessions.pop(client_id, None)
            logger.info("[DEBUG] Removed pinlogin from session")
            return jsonify({
                'ok': True,
                'baseurl': baseurl,
                'token': token
            })
        else:
            logger.info("[DEBUG] pinlogin.checkLogin() returned False")
            return jsonify({'ok': False, 'expired': False}), 202
    except Exception as e:
        logger.info("[ERROR] Exception in /api/plex/pin/status: %s", e)
        import traceback; traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


@plex_bp.route('/api/plex/config', methods=['GET'])
def get_plex_config_endpoint():
    """Get the current Plex configuration"""
    config = get_plex_config()
    return jsonify({
        'has_config': config['server_url'] is not None and config['api_token'] is not None,
        'server_url': config['server_url'],
        'library_name': config['library_name'],
        'sync_interval_hours': config.get('sync_interval_hours', 24)
    })


@plex_bp.route('/api/plex/config', methods=['POST'])
def save_plex_config_endpoint():
    """Save Plex configuration"""
    payload = request.get_json()
    
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400
    
    current = get_plex_config()

    server_url = payload.get('server_url', '').strip() or (current.get('server_url') or '')
    api_token = payload.get('api_token', '').strip()
    library_name = (payload.get('library_name', '') or '').strip() or (current.get('library_name') or '')

    if api_token.lower() == 'configured':
        api_token = ''
    api_token = api_token or (current.get('api_token') or '')
    sync_interval_hours_raw = payload.get('sync_interval_hours', 24)

    try:
        sync_interval_hours = int(sync_interval_hours_raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'sync_interval_hours must be an integer'}), 400

    if sync_interval_hours < 1:
        return jsonify({'error': 'sync_interval_hours must be at least 1'}), 400
    
    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'server_url, api_token, and library_name are required'}), 400
    
    save_plex_config(server_url, api_token, library_name, sync_interval_hours)
    return jsonify({'success': True})


@plex_bp.route('/api/plex/sync', methods=['POST'])
def start_plex_sync_endpoint():
    """Queue a manual Plex library sync (scan → match → playlist pipeline)."""
    result = start_plex_library_update_job(trigger='manual')
    if not result.get('ok'):
        status_code = result.get('status_code', 500)
        return jsonify({'error': result.get('error')}), int(status_code)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202


@plex_bp.route('/api/plex/connection-tests', methods=['POST'])
def test_plex_connection_endpoint():
    """Test Plex server connection"""
    payload = request.get_json()
    
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400
    
    server_url = payload.get('server_url', '').strip()
    api_token = payload.get('api_token', '').strip()
    
    if not server_url or not api_token:
        return jsonify({'error': 'server_url and api_token are required'}), 400
    
    success, message, libraries = test_plex_connection(server_url, api_token)
    
    if success:
        return jsonify({
            'success': True,
            'message': message,
            'libraries': libraries or []
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400


@plex_bp.route('/api/plex/playlists', methods=['GET'])
def get_plex_playlists_endpoint():
    """Get existing non-smart Plex music playlists for current configuration."""
    config = get_plex_config()
    server_url = config.get('server_url')
    api_token = config.get('api_token')

    if not server_url or not api_token:
        return jsonify({'error': 'Plex is not configured'}), 400

    user_id = request.args.get('user_id')

    success, playlists, message = get_plex_music_playlists(server_url, api_token, user_id=user_id)
    if not success:
        return jsonify({'error': f'Failed to fetch Plex playlists: {message}'}), 500

    return jsonify({'playlists': playlists})


@plex_bp.route('/api/plex/playlist/tracks', methods=['GET'])
def get_plex_playlist_tracks():
    """Get tracks from a Plex playlist by ratingKey."""
    config = get_plex_config()
    server_url = config.get('server_url')
    api_token = config.get('api_token')

    if not server_url or not api_token:
        return jsonify({'error': 'Plex is not configured'}), 400

    rating_key = request.args.get('rating_key', '').strip()
    user_id = request.args.get('user_id')

    if not rating_key:
        return jsonify({'error': 'rating_key parameter is required'}), 400

    try:
        rating_key_int = int(rating_key)
    except ValueError:
        return jsonify({'error': 'rating_key must be a valid integer'}), 400

    try:
        plex = _get_plex_server_for_user(server_url, api_token, user_id)

        playlist = plex.fetchItem(rating_key_int)

        tracks = []
        for item in playlist.items():
            track_type = getattr(item, 'type', None)
            if track_type and track_type.lower() != 'track':
                continue

            title = getattr(item, 'title', None) or 'Unknown'
            artist = getattr(item, 'grandparentTitle', None) or getattr(item, 'parentTitle', None) or ''
            album = getattr(item, 'parentTitle', None) if track_type and track_type.lower() == 'track' else ''

            duration = getattr(item, 'duration', None)
            if duration:
                duration = int(duration)

            track_number = getattr(item, 'index', None)
            disc_number = getattr(item, 'parentIndex', None)

            cover = None
            thumb = getattr(item, 'thumb', None)
            if thumb:
                cover = f"{server_url.rstrip('/')}{thumb}"

            rating_key_val = getattr(item, 'ratingKey', None)

            tracks.append({
                'id': str(rating_key_val) if rating_key_val else '',
                'title': str(title),
                'artist': str(artist) if artist else None,
                'album': str(album) if album else None,
                'duration': duration,
                'track_number': int(track_number) if track_number else None,
                'disc_number': int(disc_number) if disc_number else None,
                'cover': cover
            })

        return jsonify({
            'success': True,
            'playlist': {
                'id': str(rating_key),
                'title': getattr(playlist, 'title', 'Playlist'),
                'track_count': len(tracks)
            },
            'tracks': tracks
        })

    except Exception as e:
        logger.info("[PLEX] Failed to fetch playlist tracks: %s", str(e))
        return jsonify({'error': f'Failed to fetch playlist tracks: {str(e)}'}), 500


@plex_bp.route('/api/plex/playlists', methods=['POST'])
def create_plex_playlist_endpoint():
    """Validate and prepare for creating a Plex playlist (actual creation happens on first track add)."""
    config = get_plex_config()
    server_url = config.get('server_url')
    api_token = config.get('api_token')

    if not server_url or not api_token:
        return jsonify({'error': 'Plex is not configured'}), 400

    data = request.get_json()
    playlist_name = data.get('playlist_name', '').strip()
    user_id = data.get('user_id')

    if not playlist_name:
        return jsonify({'error': 'Playlist name is required'}), 400

    try:
        plex = PlexServer(server_url, api_token)
        
        if user_id:
            try:
                plex = plex.switchUser(user_id)
                logger.info("[PLEX] Switched to user %s for playlist creation", user_id)
            except Exception as e:
                logger.info("[PLEX] Failed to switch user: %s", str(e))
                return jsonify({'error': f'Failed to switch user: {str(e)}'}), 400

        logger.info("[PLEX] Checking if playlist exists: %s", playlist_name)
        try:
            playlists = plex.playlists()
            for pl in playlists:
                if pl.title == playlist_name:
                    logger.info("[PLEX] Playlist already exists: %s", playlist_name)
                    return jsonify({'success': True, 'playlist_name': playlist_name, 'already_exists': True})
        except Exception as e:
            logger.info("[PLEX] Error checking playlists: %s", str(e))

        logger.info("[PLEX] Playlist will be created on first track add: %s", playlist_name)
        return jsonify({'success': True, 'playlist_name': playlist_name})
    except Exception as e:
        logger.info("[PLEX] Error validating playlist: %s", str(e))
        return jsonify({'error': f'Failed to validate playlist: {str(e)}'}), 500


@plex_bp.route('/api/plex/libraries', methods=['GET'])
def get_plex_libraries_endpoint():
    """Get Plex music libraries for current configuration."""
    config = get_plex_config()
    server_url = config.get('server_url')
    api_token = config.get('api_token')

    if not server_url or not api_token:
        return jsonify({'error': 'Plex is not configured'}), 400

    success, message, libraries = test_plex_connection(server_url, api_token)
    if not success:
        return jsonify({'error': f'Failed to fetch Plex libraries: {message}'}), 500

    return jsonify({'libraries': libraries or []})


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
            logger.info("[PLEX_LIBRARY] Failed to switch user %s via '%s': %s. Using owner context.", requested_user_id, switch_target, str(e))
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


@plex_bp.route('/api/plex/library', methods=['GET'])
def get_plex_library_overview_endpoint():
    """Return a lightweight overview of the configured Plex music library."""
    config = get_plex_config()
    server_url = str(config.get('server_url') or '').strip()
    api_token = str(config.get('api_token') or '').strip()
    library_name = str(config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'Plex server_url, api_token, and library_name must be configured'}), 400

    user_id = (request.args.get('user_id') or '').strip()

    try:
        limit = int(request.args.get('limit') or 24)
    except Exception:
        limit = 24
    limit = max(1, min(limit, 100))

    try:
        plex, library, _ = _resolve_plex_library_context(server_url, api_token, library_name, user_id=user_id)

        if not library:
            return jsonify({'error': f'Plex music library "{library_name}" not found'}), 404

        try:
            artists_raw = library.search(libtype='artist', maxresults=limit)
        except Exception:
            artists_raw = library.search(libtype='artist')[:limit]

        try:
            albums_raw = library.search(libtype='album', maxresults=limit)
        except Exception:
            albums_raw = library.search(libtype='album')[:limit]

        try:
            tracks_raw = library.search(libtype='track', maxresults=limit)
        except Exception:
            tracks_raw = library.search(libtype='track')[:limit]

        artists = []
        for artist in artists_raw or []:
            artists.append({
                'name': str(getattr(artist, 'title', '') or '').strip(),
                'picture': _build_plex_image_url(server_url, api_token, getattr(artist, 'thumb', None)),
                'summary': str(getattr(artist, 'summary', '') or '').strip(),
            })

        albums = []
        for album in albums_raw or []:
            albums.append({
                'title': str(getattr(album, 'title', '') or '').strip(),
                'artist': str(getattr(album, 'parentTitle', '') or '').strip(),
                'year': getattr(album, 'year', None),
                'track_count': getattr(album, 'leafCount', None),
                'cover': _build_plex_image_url(server_url, api_token, getattr(album, 'thumb', None)),
            })

        tracks = []
        for track in tracks_raw or []:
            duration = getattr(track, 'duration', None)
            try:
                duration = int(duration) if duration is not None else None
            except Exception:
                duration = None

            tracks.append({
                'title': str(getattr(track, 'title', '') or '').strip(),
                'artist': str(getattr(track, 'grandparentTitle', '') or '').strip(),
                'album': str(getattr(track, 'parentTitle', '') or '').strip(),
                'duration': duration,
                'year': getattr(track, 'year', None),
                'cover': _build_plex_image_url(server_url, api_token, getattr(track, 'thumb', None)),
            })

        return jsonify({
            'success': True,
            'server_name': str(getattr(plex, 'friendlyName', None) or getattr(plex, 'title', None) or 'Plex'),
            'library_name': library_name,
            'artists': artists,
            'albums': albums,
            'tracks': tracks,
        })
    except Exception as e:
        logger.info("[PLEX_LIBRARY] Failed to fetch overview: %s", str(e))
        return jsonify({'error': f'Failed to fetch Plex library overview: {str(e)}'}), 500


@plex_bp.route('/api/plex/library/artists', methods=['GET'])
def get_plex_library_artists_endpoint():
    """Return paginated artists from the configured Plex music library."""
    config = get_plex_config()
    server_url = str(config.get('server_url') or '').strip()
    api_token = str(config.get('api_token') or '').strip()
    library_name = str(config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'Plex server_url, api_token, and library_name must be configured'}), 400

    user_id = (request.args.get('user_id') or '').strip()
    try:
        offset = int(request.args.get('offset') or 0)
    except Exception:
        offset = 0
    try:
        limit = int(request.args.get('limit') or 50)
    except Exception:
        limit = 50

    offset = max(0, offset)
    limit = max(1, min(limit, 100))

    try:
        plex, library, _ = _resolve_plex_library_context(server_url, api_token, library_name, user_id=user_id)
        if not library:
            return jsonify({'error': f'Plex music library "{library_name}" not found'}), 404

        artists_raw = library.search(libtype='artist') or []
        artists_raw = sorted(
            artists_raw,
            key=lambda item: str(getattr(item, 'title', '') or '').lower()
        )

        total = len(artists_raw)
        page_items = artists_raw[offset: offset + limit]

        artists = []
        for artist in page_items:
            artist_id = str(getattr(artist, 'ratingKey', '') or '').strip()
            artists.append({
                'id': artist_id,
                'name': str(getattr(artist, 'title', '') or '').strip(),
                'picture': _build_plex_image_url(server_url, api_token, getattr(artist, 'thumb', None)),
            })

        return jsonify({
            'success': True,
            'server_name': str(getattr(plex, 'friendlyName', None) or getattr(plex, 'title', None) or 'Plex'),
            'library_name': library_name,
            'total': total,
            'offset': offset,
            'limit': limit,
            'artists': artists,
        })
    except Exception as e:
        logger.info("[PLEX_LIBRARY] Failed to fetch artists: %s", str(e))
        return jsonify({'error': f'Failed to fetch Plex artists: {str(e)}'}), 500


@plex_bp.route('/api/plex/library/artists/<artist_id>/albums', methods=['GET'])
def get_plex_artist_albums_endpoint(artist_id):
    """Return albums for a specific Plex artist."""
    config = get_plex_config()
    server_url = str(config.get('server_url') or '').strip()
    api_token = str(config.get('api_token') or '').strip()
    library_name = str(config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'Plex server_url, api_token, and library_name must be configured'}), 400

    user_id = (request.args.get('user_id') or '').strip()
    artist_id = str(artist_id or '').strip()
    if not artist_id:
        return jsonify({'error': 'artist_id is required'}), 400

    try:
        _, library, _ = _resolve_plex_library_context(server_url, api_token, library_name, user_id=user_id)
        if not library:
            return jsonify({'error': f'Plex music library "{library_name}" not found'}), 404

        artist_item = library.fetchItem(f'/library/metadata/{artist_id}')
        if not artist_item:
            return jsonify({'error': f'Plex artist "{artist_id}" not found'}), 404

        albums_raw = artist_item.albums() or []
        albums_raw = sorted(
            albums_raw,
            key=lambda item: (
                -int(getattr(item, 'year', 0) or 0),
                str(getattr(item, 'title', '') or '').lower()
            )
        )

        albums = []
        for album in albums_raw:
            albums.append({
                'id': str(getattr(album, 'ratingKey', '') or '').strip(),
                'title': str(getattr(album, 'title', '') or '').strip(),
                'artist': str(getattr(album, 'parentTitle', '') or '').strip() or str(getattr(artist_item, 'title', '') or '').strip(),
                'year': getattr(album, 'year', None),
                'track_count': getattr(album, 'leafCount', None),
                'cover': _build_plex_image_url(server_url, api_token, getattr(album, 'thumb', None)),
            })

        return jsonify({
            'success': True,
            'artist': {
                'id': artist_id,
                'name': str(getattr(artist_item, 'title', '') or '').strip(),
                'picture': _build_plex_image_url(server_url, api_token, getattr(artist_item, 'thumb', None)),
            },
            'albums': albums,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to fetch Plex artist albums: {str(e)}'}), 500


@plex_bp.route('/api/plex/library/albums/<album_id>/tracks', methods=['GET'])
def get_plex_album_tracks_endpoint(album_id):
    """Return tracks for a specific Plex album."""
    config = get_plex_config()
    server_url = str(config.get('server_url') or '').strip()
    api_token = str(config.get('api_token') or '').strip()
    library_name = str(config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'Plex server_url, api_token, and library_name must be configured'}), 400

    user_id = (request.args.get('user_id') or '').strip()
    album_id = str(album_id or '').strip()
    if not album_id:
        return jsonify({'error': 'album_id is required'}), 400

    try:
        _, library, _ = _resolve_plex_library_context(server_url, api_token, library_name, user_id=user_id)
        if not library:
            return jsonify({'error': f'Plex music library "{library_name}" not found'}), 404

        album_item = library.fetchItem(f'/library/metadata/{album_id}')
        if not album_item:
            return jsonify({'error': f'Plex album "{album_id}" not found'}), 404

        tracks_raw = album_item.tracks() or []
        tracks_raw = sorted(
            tracks_raw,
            key=lambda item: (
                int(getattr(item, 'parentIndex', 1) or 1),
                int(getattr(item, 'trackNumber', 0) or 0),
                str(getattr(item, 'title', '') or '').lower()
            )
        )

        tracks = []
        for track in tracks_raw:
            duration = getattr(track, 'duration', None)
            try:
                duration = int(duration) if duration is not None else None
            except Exception:
                duration = None

            quality_format = None
            quality_bitrate_kbps = None
            try:
                media_list = getattr(track, 'media', None) or []
                if media_list:
                    media = media_list[0]
                    bitrate_value = getattr(media, 'bitrate', None)
                    if bitrate_value is not None:
                        try:
                            quality_bitrate_kbps = int(bitrate_value)
                        except Exception:
                            quality_bitrate_kbps = None

                    part_list = getattr(media, 'parts', None) or []
                    if part_list:
                        part = part_list[0]
                        quality_format = str(getattr(part, 'container', '') or '').strip().lower() or None
            except Exception:
                quality_format = None
                quality_bitrate_kbps = None

            tracks.append({
                'id': str(getattr(track, 'ratingKey', '') or '').strip(),
                'title': str(getattr(track, 'title', '') or '').strip(),
                'artist': str(getattr(track, 'grandparentTitle', '') or '').strip(),
                'artist_id': str(getattr(track, 'grandparentRatingKey', '') or '').strip() or None,
                'album': str(getattr(track, 'parentTitle', '') or '').strip(),
                'track_number': getattr(track, 'trackNumber', None),
                'disc_number': getattr(track, 'parentIndex', None),
                'duration': duration,
                'quality_format': quality_format,
                'quality_bitrate_kbps': quality_bitrate_kbps,
                'cover': _build_plex_image_url(server_url, api_token, getattr(track, 'thumb', None)),
            })

        return jsonify({
            'success': True,
            'album': {
                'id': album_id,
                'title': str(getattr(album_item, 'title', '') or '').strip(),
                'artist': str(getattr(album_item, 'parentTitle', '') or '').strip(),
                'year': getattr(album_item, 'year', None),
                'track_count': getattr(album_item, 'leafCount', None),
                'cover': _build_plex_image_url(server_url, api_token, getattr(album_item, 'thumb', None)),
            },
            'tracks': tracks,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to fetch Plex album tracks: {str(e)}'}), 500


@plex_bp.route('/api/plex/library/tracks/<track_id>/stream', methods=['GET'])
def get_plex_library_track_stream_endpoint(track_id):
    """Return a direct Plex stream URL for a library track."""
    config = get_plex_config()
    server_url = str(config.get('server_url') or '').strip()
    api_token = str(config.get('api_token') or '').strip()
    library_name = str(config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        return jsonify({'error': 'Plex server_url, api_token, and library_name must be configured'}), 400

    user_id = (request.args.get('user_id') or '').strip()
    track_id = str(track_id or '').strip()
    if not track_id:
        return jsonify({'error': 'track_id is required'}), 400

    try:
        plex, library, _ = _resolve_plex_library_context(server_url, api_token, library_name, user_id=user_id)
        if not library:
            return jsonify({'error': f'Plex music library "{library_name}" not found'}), 404

        track_item = library.fetchItem(f'/library/metadata/{track_id}')
        if not track_item:
            return jsonify({'error': f'Plex track "{track_id}" not found'}), 404

        media_list = getattr(track_item, 'media', None) or []
        if not media_list:
            return jsonify({'error': 'No playable media found for track'}), 404

        part_list = getattr(media_list[0], 'parts', None) or []
        if not part_list:
            return jsonify({'error': 'No playable media parts found for track'}), 404

        part_key = str(getattr(part_list[0], 'key', '') or '').strip()
        if not part_key:
            return jsonify({'error': 'Playable media URL is missing for track'}), 404

        token = str(getattr(plex, '_token', None) or api_token or '').strip()
        stream_url = _build_plex_image_url(server_url, token, part_key)
        if not stream_url:
            return jsonify({'error': 'Failed to build stream URL for track'}), 500

        return jsonify({
            'success': True,
            'track_id': track_id,
            'stream_url': stream_url,
        })
    except Exception as e:
        logger.info("[PLEX_LIBRARY] Failed to fetch track stream %s: %s", track_id, str(e))
        return jsonify({'error': f'Failed to fetch Plex track stream URL: {str(e)}'}), 500


@plex_bp.route('/api/plex/songs/match', methods=['POST'])
def match_plex_songs_endpoint():
    """Match candidate tracks against locally synced Plex inventory."""
    payload = request.get_json(silent=True) or {}
    tracks = payload.get('tracks')

    if not isinstance(tracks, list):
        return jsonify({'error': 'tracks array is required'}), 400

    if len(tracks) > 200:
        return jsonify({'error': 'tracks array too large (max 200)'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    matches = []

    for idx, item in enumerate(tracks):
        if not isinstance(item, dict):
            matches.append({'exists': False, 'variants': []})
            continue

        title = str(item.get('title') or '').strip()
        artist = str(item.get('artist') or '').strip()
        album = str(item.get('album') or '').strip()

        if not title or not artist:
            matches.append({'exists': False, 'variants': []})
            continue

        rows = _lookup_track_metadata(cur, title, artist, album, fuzzy=True)

        variants = []
        seen = set()
        for row in rows:
            fmt = str(row.get('format') or '').strip().lower() or 'unknown'
            bitrate = row.get('bitrate')
            bitrate_int = int(bitrate) if isinstance(bitrate, int) else None
            key = (fmt, bitrate_int)
            if key in seen:
                continue
            seen.add(key)
            variants.append({
                'format': fmt,
                'bitrate': bitrate_int,
            })

        matches.append({
            'exists': len(variants) > 0,
            'variants': variants,
        })

    conn.close()

    return jsonify({'matches': matches})
