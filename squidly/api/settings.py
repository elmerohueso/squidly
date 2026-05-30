"""Settings, endpoints, ListenBrainz, and YouTube Music routes."""

import json
import logging
import re
import threading
import time
import hashlib
from http.cookies import SimpleCookie

import requests
from flask import Blueprint, jsonify, request

from squidly.infrastructure import downloads
from squidly.infrastructure.db import get_db_connection
from squidly.infrastructure.storage import (
    get_download_settings,
    save_download_settings,
    get_listenbrainz_config,
    save_listenbrainz_config,
    get_ytm_config,
    save_ytm_config,
    get_all_plex_account_mappings,
    set_fresh_finds_auto_download,
    get_fresh_finds_retention_count,
    set_fresh_finds_retention_count,
    get_fresh_finds_new_track_pct,
    set_fresh_finds_new_track_pct,
    get_fresh_finds_track_count,
    set_fresh_finds_track_count,
    get_fresh_finds_history_days,
    set_fresh_finds_history_days,
)
from squidly.infrastructure.config import app_timezone, DEFAULT_DOWNLOAD_SETTINGS

from squidly.services.playlist_matching import _score_track_candidate
from squidly.services.track_resolver import resolve_best_match
from urllib.parse import urlencode, urlparse, parse_qs

settings_bp = Blueprint('settings', __name__)
logger = logging.getLogger(__name__)


def _run_async(fn):
    """Run a callable in a background daemon thread."""
    def _wrapper():
        try:
            fn()
        except Exception as e:
            logger.info("[ENDPOINTS] Async operation failed: %s", e)
    threading.Thread(target=_wrapper, daemon=True).start()


def _async_validate_endpoints():
    """Run endpoint validation in a background thread."""
    _run_async(lambda: downloads.validate_all_endpoints_from_db())


def _get_ytmusic(user_id):
    """Load YTM headers from DB and return an authenticated YTMusic instance."""
    from ytmusicapi import YTMusic

    conn = get_db_connection()
    cur = conn.cursor()
    if user_id:
        cur.execute(
            "SELECT ytm_headers FROM user_settings WHERE plex_client_id = %s",
            (user_id,)
        )
    else:
        cur.execute(
            "SELECT ytm_headers FROM user_settings WHERE ytm_headers IS NOT NULL ORDER BY id ASC LIMIT 1"
        )
    row = cur.fetchone()
    conn.close()

    if not row or not row.get('ytm_headers'):
        return None

    headers = json.loads(row['ytm_headers'])

    # Regenerate SAPISIDHASH since the timestamp expires
    cookie = headers.get('cookie', '')
    if cookie:
        c = SimpleCookie()
        c.load(cookie.replace('"', ''))
        sapisid = c['__Secure-3PAPISID'].value
        timestamp = str(int(time.time()))
        sha1 = hashlib.sha1()
        sha1.update(f'{timestamp} {sapisid} https://music.youtube.com'.encode('utf-8'))
        headers['authorization'] = f'SAPISIDHASH {timestamp}_{sha1.hexdigest()}'

    return YTMusic(headers)


@settings_bp.route('/api/settings', methods=['GET', 'POST'])
def download_settings():
    """Get or update download settings stored in SQLite."""
    if request.method == 'GET':
        settings = get_download_settings()
        settings['timezone'] = app_timezone
        return jsonify(settings)

    payload = request.get_json(silent=True) or {}
    current = get_download_settings()

    file_naming_album = (
        payload.get('fileNamingAlbum')
        or payload.get('file_naming_album')
        or payload.get('fileNaming')
        or payload.get('file_naming')
        or current['file_naming_album']
    )

    tag_keys = [
        'tag_title', 'tag_artist', 'tag_album_artist', 'tag_album', 'tag_year',
        'tag_track_number', 'tag_track_total', 'tag_disc_number', 'tag_disc_total',
        'tag_version', 'tag_tidal_track_id', 'tag_tidal_album_id', 'tag_isrc',
        'tag_copyright', 'tag_cover_art', 'tag_explicit', 'tag_explicit_suffix',
    ]
    penalty_keys = [
        'penalty_compilation', 'penalty_single', 'penalty_karaoke', 'penalty_live',
    ]

    updated = {
        'format': current['format'],
        'quality': payload.get('quality', current.get('quality', DEFAULT_DOWNLOAD_SETTINGS['quality'])),
        'parent_folder': current['parent_folder'],
        'file_naming_album': file_naming_album,
        'jobs_refresh_interval_seconds': payload.get('jobsRefreshIntervalSeconds', payload.get('jobs_refresh_interval_seconds', current.get('jobs_refresh_interval_seconds', DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds']))),
        'ignore_matches': payload.get('ignoreMatches', payload.get('ignore_matches', current.get('ignore_matches', DEFAULT_DOWNLOAD_SETTINGS.get('ignore_matches', False)))),
        'download_source': payload.get('downloadSource', payload.get('download_source', current.get('download_source', DEFAULT_DOWNLOAD_SETTINGS['download_source']))),
    }

    for key in tag_keys:
        updated[key] = payload.get(key, current.get(key, DEFAULT_DOWNLOAD_SETTINGS.get(key, True)))

    for key in penalty_keys:
        updated[key] = payload.get(key, current.get(key, DEFAULT_DOWNLOAD_SETTINGS.get(key, True)))

    if updated['quality'] not in ('LOSSLESS', 'HIGH', 'LOW'):
        return jsonify({'error': 'Invalid quality value'}), 400

    # Validate comma-separated download source priority list
    download_sources = [s.strip() for s in updated['download_source'].split(',')]
    if not download_sources or not all(s in ('tidal', 'qobuz') for s in download_sources):
        return jsonify({'error': 'Invalid download source value(s)'}), 400
    # Normalize: preserve order, remove duplicates
    seen = set()
    normalized = []
    for s in download_sources:
        if s not in seen:
            seen.add(s)
            normalized.append(s)
    updated['download_source'] = ','.join(normalized)

    if not isinstance(updated['file_naming_album'], str):
        return jsonify({'error': 'Invalid settings payload'}), 400

    try:
        updated['jobs_refresh_interval_seconds'] = int(updated['jobs_refresh_interval_seconds'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid jobs refresh interval'}), 400

    if updated['jobs_refresh_interval_seconds'] < 1:
        return jsonify({'error': 'Jobs refresh interval must be at least 1 second'}), 400

    updated['ignore_matches'] = bool(updated['ignore_matches'])
    for key in tag_keys:
        updated[key] = bool(updated[key])
    for key in penalty_keys:
        updated[key] = bool(updated[key])

    save_download_settings(updated)

    result = {
        'format': updated['format'],
        'quality': updated['quality'],
        'file_naming': updated['file_naming_album'],
        'file_naming_album': updated['file_naming_album'],
        'jobs_refresh_interval_seconds': updated['jobs_refresh_interval_seconds'],
        'ignore_matches': updated['ignore_matches'],
        'download_source': updated['download_source'],
    }
    for key in tag_keys:
        result[key] = updated[key]
    for key in penalty_keys:
        result[key] = updated[key]

    return jsonify(result)


@settings_bp.route('/api/endpoints/status', methods=['GET'])
def endpoints_status():
    """Return the current status of all endpoints"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, encoded_url, online, response_time, last_checked, enabled, mirror_type, downloads_enabled
        FROM mirror_endpoints
        ORDER BY response_time ASC NULLS LAST, name ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    endpoints = []
    for row in rows:
        endpoints.append({
            'name': row['name'],
            'encodedUrl': row['encoded_url'],
            'online': bool(row['online']),
            'responseTime': row['response_time'],
            'lastChecked': row['last_checked'],
            'enabled': bool(row['enabled']),
            'mirrorType': row.get('mirror_type', 'tidal'),
            'downloadsEnabled': bool(row.get('downloads_enabled', True)),
        })

        mirror_rate_limit_status = {}
    try:
        mirror_rate_limit_status = downloads.get_mirror_rate_limit_status() or {}
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to get mirror rate limit status: %s", e)

    return jsonify({
        'endpoints': endpoints,
        'summary': {
            'total': len(endpoints),
            'online': sum(1 for e in endpoints if e.get('online')),
            'offline': sum(1 for e in endpoints if not e.get('online'))
        },
        'mirrorRateLimitStatus': mirror_rate_limit_status,
    })


@settings_bp.route('/api/endpoints', methods=['POST'])
def add_endpoint():
    """Add a new mirror endpoint."""
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400

    url = payload.get('url', '').strip()
    if not url:
        return jsonify({'error': 'url is required'}), 400

    mirror_type = payload.get('mirrorType', 'tidal').strip().lower()
    if mirror_type not in ('tidal', 'qobuz'):
        return jsonify({'error': 'mirrorType must be "tidal" or "qobuz"'}), 400

    try:
        downloads.add_mirror(url, mirror_type=mirror_type)
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to add mirror: %s", e)
        return jsonify({'error': str(e)}), 500

    _async_validate_endpoints()

    return jsonify({'url': url, 'added': True, 'mirrorType': mirror_type}), 201


@settings_bp.route('/api/endpoints/<name>', methods=['DELETE'])
def delete_endpoint(name):
    """Remove a mirror endpoint."""
    try:
        downloads.remove_mirror(name)
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to remove mirror: %s", e)
        return jsonify({'error': str(e)}), 500

    _async_validate_endpoints()

    return jsonify({'name': name, 'removed': True}), 200


@settings_bp.route('/api/endpoints/<name>/toggle', methods=['POST'])
def toggle_endpoint(name):
    """Toggle the enabled state of a mirror endpoint."""
    try:
        new_state = downloads.toggle_mirror(name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to toggle mirror: %s", e)
        return jsonify({'error': str(e)}), 500

    if new_state == 1:
        _run_async(lambda: downloads.validate_single_endpoint(name))

    return jsonify({'name': name, 'enabled': bool(new_state)}), 200


@settings_bp.route('/api/endpoints/<name>/toggle-download', methods=['POST'])
def toggle_endpoint_downloads(name):
    """Toggle whether a mirror is enabled for downloads."""
    try:
        new_state = downloads.toggle_mirror_downloads(name)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to toggle mirror downloads: %s", e)
        return jsonify({'error': str(e)}), 500
    return jsonify({'name': name, 'downloadsEnabled': bool(new_state)}), 200


@settings_bp.route('/api/listenbrainz/config', methods=['GET'])
def get_listenbrainz_config_endpoint():
    """Get the current ListenBrainz configuration"""
    user_id = request.args.get('user_id')
    config = get_listenbrainz_config(user_id)
    return jsonify({
        'has_token': config['user_token'] is not None,
        'username': config.get('username')
    })


@settings_bp.route('/api/listenbrainz/config', methods=['POST'])
def save_listenbrainz_config_endpoint():
    """Save ListenBrainz user token"""
    payload = request.get_json()
    
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400
    
    user_token = payload.get('user_token')
    user_id = payload.get('user_id')
    
    username = payload.get('username')
    
    if not user_token:
        return jsonify({'error': 'user_token is required'}), 400
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    save_listenbrainz_config(user_token, user_id, username)
    return jsonify({
        'success': True
    })


@settings_bp.route('/api/fresh-finds/auto-download', methods=['GET'])
def get_fresh_finds_auto_download_config():
    """Get the Fresh Finds auto-download setting for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    mappings = get_all_plex_account_mappings()
    user_row = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            user_row = m
            break

    if not user_row:
        return jsonify({'error': 'User not found'}), 404

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT auto_download_fresh_finds FROM user_settings WHERE plex_client_id = %s",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()

    enabled = bool(row.get('auto_download_fresh_finds')) if row else False
    return jsonify({'enabled': enabled})


@settings_bp.route('/api/fresh-finds/auto-download', methods=['POST'])
def save_fresh_finds_auto_download_config():
    """Set the Fresh Finds auto-download toggle for a specific user."""
    payload = request.get_json(silent=True) or {}

    user_id = payload.get('user_id')
    enabled = payload.get('enabled', False)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    set_fresh_finds_auto_download(user_id, enabled)
    return jsonify({'success': True, 'enabled': bool(enabled)})


@settings_bp.route('/api/fresh-finds/retention', methods=['GET'])
def get_fresh_finds_retention():
    """Get the Fresh Finds retention count setting for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    count = get_fresh_finds_retention_count(plex_account_id)
    return jsonify({'count': count})


@settings_bp.route('/api/fresh-finds/retention', methods=['POST'])
def save_fresh_finds_retention():
    """Set the Fresh Finds retention count for a specific user. Clamps to [1, 100]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    count = payload.get('count', 10)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    set_fresh_finds_retention_count(user_id, count)
    return jsonify({'success': True, 'count': max(1, min(100, int(count)))})


@settings_bp.route('/api/fresh-finds/new-track-pct', methods=['GET'])
def get_fresh_finds_new_track_pct_route():
    """Get the Fresh Finds new-track percentage for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    pct = get_fresh_finds_new_track_pct(plex_account_id)
    return jsonify({'pct': pct})


@settings_bp.route('/api/fresh-finds/new-track-pct', methods=['POST'])
def save_fresh_finds_new_track_pct_route():
    """Set the Fresh Finds new-track percentage for a specific user. Clamps to [0, 100]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    pct = payload.get('pct', 50)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    set_fresh_finds_new_track_pct(user_id, pct)
    return jsonify({'success': True, 'pct': max(0, min(100, int(pct)))})


@settings_bp.route('/api/fresh-finds/track-count', methods=['GET'])
def get_fresh_finds_track_count_route():
    """Get the Fresh Finds track count for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    count = get_fresh_finds_track_count(plex_account_id)
    return jsonify({'count': count})


@settings_bp.route('/api/fresh-finds/track-count', methods=['POST'])
def save_fresh_finds_track_count_route():
    """Set the Fresh Finds track count for a specific user. Clamps to [10, 50]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    count = payload.get('count', 25)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    set_fresh_finds_track_count(user_id, count)
    return jsonify({'success': True, 'count': max(10, min(50, int(count)))})


@settings_bp.route('/api/fresh-finds/history-days', methods=['GET'])
def get_fresh_finds_history_days_route():
    """Get the Fresh Finds history window (days) for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    days = get_fresh_finds_history_days(plex_account_id)
    return jsonify({'days': days})


@settings_bp.route('/api/fresh-finds/history-days', methods=['POST'])
def save_fresh_finds_history_days_route():
    """Set the Fresh Finds history window (days) for a specific user. Clamps to [10, 60]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    days = payload.get('days', 30)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    set_fresh_finds_history_days(user_id, days)
    return jsonify({'success': True, 'days': max(10, min(60, int(days)))})


@settings_bp.route('/api/listenbrainz/playlists', methods=['GET'])
def get_listenbrainz_playlists():
    """Fetch recommended playlists created for user from ListenBrainz"""
    user_id = request.args.get('user_id')
    config = get_listenbrainz_config(user_id)
    
    if not config['user_token']:
        return jsonify({'error': 'ListenBrainz token not configured'}), 400
    
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'username parameter is required'}), 400
    
    playlist_type = request.args.get('type')
    
    try:
        headers = {'Authorization': f'Token {config["user_token"]}'}
        
        if playlist_type == 'createdfor':
            endpoints = [f'https://api.listenbrainz.org/1/user/{username}/playlists/createdfor']
        elif playlist_type == 'collaborator':
            endpoints = [f'https://api.listenbrainz.org/1/user/{username}/playlists/collaborator']
        elif playlist_type == 'user':
            endpoints = [f'https://api.listenbrainz.org/1/user/{username}/playlists']
        else:
            endpoints = [
                f'https://api.listenbrainz.org/1/user/{username}/playlists/createdfor',
                f'https://api.listenbrainz.org/1/user/{username}/playlists',
                f'https://api.listenbrainz.org/1/user/{username}/playlists/collaborator'
            ]

        combined_playlists = []
        seen_identifiers = set()
        total_count = 0
        success_count = 0
        errors = []

        for url in endpoints:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                success_count += 1

                count = data.get('count')
                if isinstance(count, int):
                    total_count += count

                for item in data.get('playlists', []) or []:
                    playlist = item.get('playlist') if isinstance(item, dict) else None
                    if not isinstance(playlist, dict):
                        continue

                    if isinstance(count, int) and 'count' not in playlist:
                        playlist['count'] = count

                    identifier = playlist.get('identifier')
                    if identifier and identifier in seen_identifiers:
                        continue
                    if identifier:
                        seen_identifiers.add(identifier)

                    combined_playlists.append({'playlist': playlist})

            except requests.exceptions.RequestException as e:
                errors.append(str(e))

        if success_count == 0:
            return jsonify({'error': f'Failed to fetch from ListenBrainz: {"; ".join(errors)}'}), 500

        return jsonify({
            'count': total_count,
            'offset': 0,
            'playlist_count': len(combined_playlists),
            'playlists': combined_playlists
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch from ListenBrainz: {str(e)}'}), 500


@settings_bp.route('/api/listenbrainz/playlist/<playlist_mbid>', methods=['GET'])
def get_listenbrainz_playlist(playlist_mbid):
    """Fetch a ListenBrainz playlist and its tracks by MBID"""
    user_id = request.args.get('user_id')
    config = get_listenbrainz_config(user_id)
    
    if not config['user_token']:
        return jsonify({'error': 'ListenBrainz token not configured'}), 400

    try:
        url = f'https://api.listenbrainz.org/1/playlist/{playlist_mbid}'
        response = requests.get(url, timeout=10, headers={'Authorization': f'Token {config["user_token"]}'})
        response.raise_for_status()
        data = response.json()
        
        return jsonify(data)
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch playlist from ListenBrainz: {str(e)}'}), 500


@settings_bp.route('/api/listenbrainz/match', methods=['POST'])
def match_listenbrainz_track():
    """Match a ListenBrainz track to HiFi using MBID→ISRC lookup with text search fallback."""
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400

    title = str(payload.get('title') or '').strip()
    artist = str(payload.get('artist') or '').strip()
    album = str(payload.get('album') or '').strip()
    identifier = str(payload.get('identifier') or '').strip()

    if not title or not artist:
        return jsonify({'error': 'title and artist are required'}), 400

    settings = get_download_settings()

    from squidly.services.listenbrainz_matching import match_listenbrainz_tracks
    results = match_listenbrainz_tracks([{
        'title': title,
        'artist': artist,
        'album': album,
        'identifier': identifier,
    }], settings)

    r = results[0] if results else {'match': None, 'method': None, 'confidence': 0.0, 'error': None}
    return jsonify({
        'match': r.get('match'),
        'method': r.get('method'),
        'confidence': min(r.get('confidence', 0.0), 1.0),
    })


@settings_bp.route('/api/youtube_music/playlist', methods=['POST'])
def youtube_music_playlist():
    """
    Parse a YouTube Music playlist and return track metadata.
    Accepts JSON body with 'playlistUrl' field.
    Returns the playlist name and list of tracks to search for.
    """
    from ytmusicapi import YTMusic
    
    data = request.get_json() or {}
    playlist_url = str(data.get('playlistUrl', '')).strip()

    if not playlist_url:
        return jsonify({'error': 'Playlist URL is required'}), 400

    try:
        parsed = urlparse(playlist_url)
        query_params = parse_qs(parsed.query)
        playlist_id = (query_params.get('list') or [''])[0].strip()

        if not playlist_id:
            return jsonify({'error': 'Invalid YouTube Music playlist URL. Missing list parameter.'}), 400

        ytmusic = YTMusic()
        playlist = ytmusic.get_playlist(playlist_id, limit=None)

        playlist_name = str(playlist.get('title') or 'YouTube Music Playlist').strip()
        raw_tracks = playlist.get('tracks') or []
        tracks = []
        seen_tracks = set()

        for track in raw_tracks:
            track_name = str(track.get('title') or '').strip()
            artists = track.get('artists') or []
            artist_names = [
                str(artist.get('name') or '').strip()
                for artist in artists
                if str(artist.get('name') or '').strip()
            ]
            artist_name = '; '.join(artist_names).strip()

            if not track_name or not artist_name:
                continue

            track_key = f"{artist_name.casefold()}|{track_name.casefold()}"
            if track_key in seen_tracks:
                continue

            seen_tracks.add(track_key)
            tracks.append({
                'name': track_name,
                'artist': artist_name
            })

        if len(tracks) == 0:
            return jsonify({
                'error': 'No tracks found. The playlist may be private, empty, or unavailable.'
            }), 400

        return jsonify({
            'playlistName': playlist_name,
            'trackCount': len(tracks),
            'tracks': tracks
        })

    except Exception as e:
        logger.info("YouTube Music playlist parsing error: %s", e)
        return jsonify({
            'error': 'Failed to process YouTube Music playlist',
            'details': str(e)
        }), 500


@settings_bp.route('/api/youtube_music/config', methods=['GET'])
def get_ytm_config_endpoint():
    """Check if YouTube Music is configured for the user."""
    user_id = request.args.get('user_id')
    config = get_ytm_config(user_id)
    return jsonify(config)


@settings_bp.route('/api/youtube_music/config', methods=['POST'])
def save_ytm_config_endpoint():
    """Save YouTube Music cookie and generate auth headers."""
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400

    cookie = payload.get('cookie', '').strip()
    user_id = payload.get('user_id', '').strip()

    if not cookie:
        return jsonify({'error': 'cookie is required'}), 400
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    try:
        save_ytm_config(cookie, user_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'success': True})


@settings_bp.route('/api/youtube_music/playlists', methods=['GET'])
def get_ytm_playlists():
    """Fetch the user's YouTube Music library playlists, excluding video playlists."""
    user_id = request.args.get('user_id')
    ytmusic = _get_ytmusic(user_id)

    if not ytmusic:
        return jsonify({'error': 'YouTube Music not configured'}), 400

    def _is_video_playlist(pl):
        """Video playlists use i.ytimg.com thumbnails; music playlists use lh3.googleusercontent.com."""
        for thumb in pl.get('thumbnails', []):
            if 'i.ytimg.com' in thumb.get('url', ''):
                return True
        return False

    try:
        playlists = ytmusic.get_library_playlists(limit=None)

        result = []
        for pl in playlists:
            playlist_id = pl.get('playlistId', '')
            if playlist_id == 'LM':
                continue
            if _is_video_playlist(pl):
                continue
            result.append({
                'title': pl.get('title', ''),
                'playlistId': playlist_id,
                'count': pl.get('count', '?'),
            })

        result.sort(key=lambda p: p['title'].casefold())

        return jsonify({'playlists': result})

    except Exception as e:
        logger.info("YouTube Music playlists error: %s", e)
        return jsonify({'error': f'Failed to fetch playlists: {str(e)}'}), 500


@settings_bp.route('/api/youtube_music/playlist/<playlist_id>', methods=['GET'])
def get_ytm_playlist(playlist_id):
    """Fetch tracks for a specific YouTube Music playlist."""
    user_id = request.args.get('user_id')
    ytmusic = _get_ytmusic(user_id)

    if not ytmusic:
        return jsonify({'error': 'YouTube Music not configured'}), 400

    try:
        pl_data = ytmusic.get_playlist(playlist_id, limit=None)

        tracks = []
        for t in pl_data.get('tracks', []):
            tracks.append({
                'title': t.get('title', ''),
                'artists': t.get('artists') or [],
                'album': t.get('album'),
                'duration': t.get('duration', ''),
                'duration_seconds': t.get('duration_seconds'),
                'videoId': t.get('videoId', ''),
            })

        return jsonify({
            'title': pl_data.get('title', ''),
            'trackCount': pl_data.get('trackCount', len(tracks)),
            'tracks': tracks,
        })

    except Exception as e:
        logger.info("YouTube Music playlist error: %s", e)
        return jsonify({'error': f'Failed to fetch playlist: {str(e)}'}), 500


@settings_bp.route('/api/youtube_music/match', methods=['POST'])
def match_ytm_track():
    """Match a YouTube Music track to Hi-Fi library by text search."""
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400

    title = str(payload.get('title') or '').strip()
    artist = str(payload.get('artist') or '').strip()
    album = str(payload.get('album') or '').strip()

    if not title or not artist:
        return jsonify({'error': 'title and artist are required'}), 400

    settings = get_download_settings()

    query = f'{title} {artist}'
    response, _ = downloads.make_request_with_retry_rotating_mirrors(
        f"/search/?{urlencode({'s': query, 'limit': '50'})}",
        downloads.get_squid_urls(),
        method='GET',
        timeout=10,
        max_retries=3
    )

    if not response.ok:
        return jsonify({'error': 'Failed to search HiFi library'}), 500

    result = response.json()
    tracks = result.get('tracks', []) if isinstance(result, dict) else []

    best_match = None
    best_score = 0.0

    for item in tracks:
        score = _score_track_candidate(title, artist, album, item)
        if score > best_score:
            best_score = score
            best_match = item

    if best_match:
        resolved = resolve_best_match(best_match, settings)
        if resolved:
            best_match = resolved

        return jsonify({
            'match': best_match,
            'confidence': min(best_score, 1.0)
        })

    return jsonify({'match': None, 'confidence': 0.0})
