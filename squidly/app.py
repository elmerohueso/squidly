
import logging
from squidly.logging_setup import setup_logging
setup_logging()

from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer


from flask import Flask, render_template, jsonify, request, session, Response, stream_with_context
from flask_cors import CORS
import threading
import os
import json
import base64
import requests
import concurrent.futures
import psycopg2
import psycopg2.extras
from squidly.utils import (
    _now_utc,
    _safe_float,
    _safe_int,
    clean_path_components,
    extract_year_from_text,
    normalize_match_text,
    sanitize_filename_component,
)
from squidly.hifi import (
    get_hifi_album_object,
    get_hifi_artist_object,
    get_hifi_track_object,
    _build_normalized_hifi_track_object,
    _get_hifi_album_dedupe_key,
    _get_hifi_track_dedupe_key,
    _get_hifi_audio_quality_rank,
)
from itertools import cycle
from datetime import datetime, timedelta
import time
import sys
import subprocess
import shutil
import re
import threading
import socket
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCOP, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from io import BytesIO

from squidly.plex import (
    _get_plex_server_for_user,
    _is_plex_library_scan_active,
    _plex_call_with_timeout,
    get_all_plex_users,
    get_plex_health_status,
    get_plex_music_playlists,
    plex_healthcheck,
    plex_pin_sessions,
    process_plex_library_update_job,
    set_plex_health_status,
    test_plex_connection,
    wait_for_plex_library_scan_completion,
)

from squidly.matching import (
    MATCH_REVIEW_ARTWORK_SIZE,
    MATCH_REVIEW_HIFI_ARTWORK_SIZE,
    MATCH_REVIEW_HIFI_ARTIST_ARTWORK_SIZE,
    _extract_hifi_item_artists,
    _extract_primary_hifi_artist,
    _merge_match_state,
    _is_hifi_explicit,
    _format_hifi_track_title,
    _extract_hifi_album_track_titles,
    _has_explicit_marker,
    _score_explicit_alignment,
    _score_album_track_title_alignment,
    _score_artist_candidate_name,
    _extract_album_candidate_artist_names,
    _score_album_candidate_artist_alignment,
    _score_album_candidate_title,
    _score_track_candidate_payload,
    _serialize_match_variants,
    _evaluate_album_candidate,
    _get_artist_row,
    _get_album_row,
    _get_track_row_by_path,
    _upsert_artist_row,
    _upsert_album_row,
    _upsert_track_row,
    upsert_download_match_hint,
    _fetch_source_album_track_titles_map,
    _find_hifi_track_search_candidate,
    _cascade_track_confirm_ids,
    _refresh_album_completeness,
    _build_stored_track_match_lookup,
    _build_stored_album_match_lookup,
    _build_stored_artist_match_lookup,
    _fetch_match_review_row,
    _build_artist_match_candidates,
    _build_album_match_candidates,
    _build_track_match_candidates,
)

from squidly.playlist_matching import (
    compute_playlist_match_penalty,
    _lookup_track_metadata,
)

from squidly.tag_reader import scan_library_for_tags, _resolve_library_file_path
from squidly.hifi_matcher import find_missing_hifi_ids

from squidly.hifi import (
    _fetch_hifi_search_results,
    _fetch_hifi_artist_payload,
    _fetch_hifi_album_payload,
    _fetch_hifi_track_payload,
    _fetch_hifi_track_manifests_payload,
    _fetch_hifi_track_info_payload,
    _normalize_hifi_playlist_items,
    _extract_hifi_album_track_items,
)

from squidly.workers import (
    JobCancelledError,
    _raise_if_job_cancelled,
    start_workers,
)

from ytmusicapi import YTMusic

from squidly import downloads
from squidly import qobuz
from squidly import jobs

from squidly.orchestration import (
    is_job_type_running_or_queued,
    queue_pending_playlist_addition,
    queue_plex_listen_history_sync,
    queue_recommendation_generation,
    start_plex_library_update_job,
    wait_for_job_type,
)

from squidly.storage import (
    any_download_jobs_running,
    can_start_plex_library_update,
    clear_plex_config,
    clear_plex_user_settings,
    get_all_plex_account_mappings,
    get_download_settings,
    get_download_write_gate_state,
    get_existing_artist_titles,
    get_existing_isrcs,
    get_last_download_activity_at,
    get_library_update_status,
    get_listen_history,
    get_listen_history_sync_status,
    get_listenbrainz_config,
    get_plex_config,
    get_plex_user_settings,
    get_recent_listen_history_seeds,
    get_recommendation_playlist,
    get_todays_recommendation_playlist,
    get_ytm_config,
    has_listen_history,
    list_recommendation_playlists,
    normalize_db_timestamp,
    save_download_settings,
    save_listenbrainz_config,
    save_plex_account_id,
    save_plex_config,
    save_plex_user_setting,
    save_ytm_config,
    set_last_download_activity_at,
    set_last_job_finished_at,
    set_last_library_update_time,
    set_listen_history_sync_status,
    upsert_listen_history_entries,
    set_library_update_needed,
    save_recommendation_playlist,
)

logger = logging.getLogger(__name__)

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(
    __name__,
    static_folder=os.path.join(base_dir, 'static'),
    template_folder=os.path.join(base_dir, 'templates')
)
CORS(app)

# ...existing code...
@app.route('/api/plex/users', methods=['GET'])
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
# --- Plex PIN OAuth API ---
import threading

@app.route('/api/plex/healthcheck', methods=['GET'])
def run_plex_healthcheck():
    ok, value = plex_healthcheck()
    if ok:
        return jsonify({'ok': True, 'server_name': value})
    else:
        # 400 for missing config, 200 for other errors (to match previous behavior)
        status = 400 if value == 'No Plex credentials configured' else 200
        return jsonify({'ok': False, 'error': value}), status

@app.route('/api/plex/health', methods=['GET'])
def plex_health_status():
    """Return the cached Plex healthcheck state without triggering a new check."""
    return jsonify(get_plex_health_status())

@app.route('/api/plex/clear_credentials', methods=['POST'])
def plex_clear_credentials():
    """Clear saved Plex configuration and Plex user settings."""
    clear_plex_config()
    clear_plex_user_settings()
    set_plex_health_status(False, 'No Plex credentials configured')
    return jsonify({'ok': True})

@app.route('/api/plex/pin/start', methods=['POST'])
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

@app.route('/api/plex/pin/status', methods=['POST'])
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
    # Check if already expired
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
            # Find local server baseurl
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
            # Save to DB
            if baseurl and token:
                logger.info("[DEBUG] Saving Plex config to DB")
                config = get_plex_config()
                save_plex_config(baseurl, token, config.get('library_name') or '', config.get('sync_interval_hours') or 24)
            # Clean up session
            logger.info("[DEBUG] Cleaning up pin session")
            plex_pin_sessions.pop(client_id, None)
            return jsonify({'ok': True, 'token': token, 'baseurl': baseurl, 'username': getattr(acc, 'username', None)})
        else:
            logger.info("[DEBUG] pinlogin.checkLogin() returned False (pending)")
            return jsonify({'ok': False, 'pending': True})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.info("[DEBUG] Exception in /api/plex/pin/status: %s %s", e, tb)
        return jsonify({'ok': False, 'error': str(e), 'traceback': tb}), 500

from squidly.config import (
    DATABASE_URL,
    DOWNLOADS_ROOT,
    DEFAULT_DOWNLOAD_SETTINGS,
    WORKER_ID,
)

# Verify downloads directory exists and is writable
# Note: Don't call os.makedirs() here - volume mounts are configured in docker-compose
# Attempting to create them can shadow the mount points

if not os.path.exists(DOWNLOADS_ROOT):
    logger.error("Error: Downloads directory does not exist: %s", DOWNLOADS_ROOT)
    logger.error("Check docker-compose volume mounts are configured correctly")
elif not os.access(DOWNLOADS_ROOT, os.W_OK):
    logger.error("Error: Downloads directory is not writable: %s", DOWNLOADS_ROOT)
else:
    logger.info("Downloads directory ready: %s", DOWNLOADS_ROOT)

from squidly.db import get_db_connection, init_db


def _normalize_library_track_path(file_path):
    raw_path = str(file_path or '').strip()
    if not raw_path:
        return ''

    normalized = raw_path.replace('\\', '/').strip()
    downloads_root = DOWNLOADS_ROOT.rstrip('/').replace('\\', '/')
    if downloads_root and normalized.startswith(downloads_root + '/'):
        normalized = normalized[len(downloads_root) + 1:]
    parts = [part for part in normalized.split('/') if part and part != '.']

    if downloads_root and not normalized.startswith(downloads_root + '/') and len(parts) >= 3:
        parts = parts[-3:]

    if parts and parts[0] in ('full_albums', 'loose_tracks'):
        parts = parts[1:]

    return '/'.join(parts)


def _extract_plex_library_id(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    if raw.startswith('/library/metadata/'):
        return raw.split('/')[-1] or None
    return raw


def _read_embedded_hifi_ids(file_path):
    track_id = None
    album_id = None
    isrc = None
    raw_path = str(file_path or '').strip()
    if not raw_path:
        return {'track_id': None, 'album_id': None, 'isrc': None}
    if not raw_path.startswith('/'):
        raw_path = f"{DOWNLOADS_ROOT}/{raw_path}"
    if not os.path.exists(raw_path):
        logger.info("[MATCH] Path does not exist after resolution: %s", file_path)
        return {'track_id': None, 'album_id': None, 'isrc': None}

    try:
        lower_path = raw_path.lower()
        if lower_path.endswith('.flac'):
            audio = FLAC(raw_path)
            track_values = audio.get('TIDAL_TRACK_ID') or audio.get('tidal_track_id') or []
            album_values = audio.get('TIDAL_ALBUM_ID') or audio.get('tidal_album_id') or []
            isrc_values = audio.get('ISRC') or audio.get('isrc') or []
            track_id = str(track_values[0]).strip() if track_values else None
            album_id = str(album_values[0]).strip() if album_values else None
            isrc = str(isrc_values[0]).strip() if isrc_values else None
        elif lower_path.endswith('.m4a'):
            audio = MP4(raw_path)
            track_values = audio.get('----:com.apple.iTunes:tidal_track_id') or []
            album_values = audio.get('----:com.apple.iTunes:tidal_album_id') or []
            isrc_values = audio.get('----:com.apple.iTunes:isrc') or []
            if track_values:
                first_value = track_values[0]
                track_id = first_value.decode('utf-8', errors='ignore').strip() if isinstance(first_value, bytes) else str(first_value).strip()
            if album_values:
                first_value = album_values[0]
                album_id = first_value.decode('utf-8', errors='ignore').strip() if isinstance(first_value, bytes) else str(first_value).strip()
            if isrc_values:
                first_value = isrc_values[0]
                isrc = first_value.decode('utf-8', errors='ignore').strip() if isinstance(first_value, bytes) else str(first_value).strip()
        elif lower_path.endswith('.mp3'):
            audio = MP3(raw_path, ID3=ID3)
            track_frame = audio.tags.get('TXXX:tidal_track_id') if audio.tags else None
            album_frame = audio.tags.get('TXXX:tidal_album_id') if audio.tags else None
            isrc_frame = audio.tags.get('ISRC') if audio.tags else None
            if not isrc_frame:
                isrc_frame = audio.tags.get('TXXX:isrc') if audio.tags else None
            if track_frame and getattr(track_frame, 'text', None):
                track_id = str(track_frame.text[0]).strip()
            if album_frame and getattr(album_frame, 'text', None):
                album_id = str(album_frame.text[0]).strip()
            if isrc_frame and getattr(isrc_frame, 'text', None):
                isrc = str(isrc_frame.text[0]).strip()
        
        if track_id or album_id or isrc:
            logger.info("[MATCH] Found embedded IDs: track=%s, album=%s, isrc=%s", track_id, album_id, isrc)
        else:
            logger.info("[MATCH] No embedded Tidal IDs or ISRC found in file")
    except Exception as e:
        logger.info("[MATCH] Failed to read embedded hifi IDs from %s: %s", raw_path, str(e))

    return {
        'track_id': track_id or None,
        'album_id': album_id or None,
        'isrc': isrc or None,
    }


def _get_file_audio_info(file_path):
    raw_path = _resolve_library_file_path(file_path)
    if not raw_path or not os.path.exists(raw_path):
        return {'duration': None, 'isrc': None}

    try:
        lower_path = raw_path.lower()
        if lower_path.endswith('.flac'):
            audio = FLAC(raw_path)
            isrc_values = audio.get('ISRC') or audio.get('isrc') or []
            isrc = str(isrc_values[0]).strip() if isrc_values else None
            duration = int(audio.info.length) if audio.info and audio.info.length else None
        elif lower_path.endswith('.m4a'):
            audio = MP4(raw_path)
            isrc_values = audio.get('----:com.apple.iTunes:isrc') or []
            isrc = isrc_values[0].decode('utf-8', errors='ignore').strip() if isrc_values else None
            duration = int(audio.info.length) if audio.info and audio.info.length else None
        elif lower_path.endswith('.mp3'):
            audio = MP3(raw_path, ID3=ID3)
            isrc_frame = audio.tags.get('ISRC') if audio.tags else None
            if not isrc_frame:
                isrc_frame = audio.tags.get('TXXX:isrc') if audio.tags else None
            isrc = str(isrc_frame.text[0]).strip() if isrc_frame and getattr(isrc_frame, 'text', None) else None
            duration = int(audio.info.length) if audio.info and audio.info.length else None
        else:
            return {'duration': None, 'isrc': None}

        return {'duration': duration, 'isrc': isrc or None}
    except Exception:
        return {'duration': None, 'isrc': None}


def _get_match_review_plex_context():
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
        logger.info("[MATCH_REVIEW] Unable to resolve Plex context for artwork: %s", str(e))
        return None, None, None


def _fetch_plex_item_image_map(library, server_url, api_token, library_ids, image_size=None):
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
            logger.info("[MATCH_REVIEW] Failed to fetch Plex artwork for %s: %s", normalized_id, str(e))
            image_map[normalized_id] = None

    return image_map


def process_automatic_matching_job(job_id, payload):
    """Run the full automatic matching pipeline:
    1. Queue Plex library update
    2. Wait for Plex sync to complete
    3. Run tag analysis to fill missing fields from file tags
    4. Run HiFi gap-fill for remaining unmatched records
    """
    stages = {
        'tag_analysis': 'pending',
        'hifi_gap_fill': 'pending',
    }
    progress = {
        'tag_scanned': 0,
        'tag_filled': 0,
        'hifi_tracks_matched': 0,
        'hifi_albums_matched': 0,
        'hifi_artists_matched': 0,
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    trigger = payload.get('trigger') if isinstance(payload, dict) else 'manual'

    # Stage 1: Tag analysis
    stages['tag_analysis'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[AUTO_MATCH] Job %s running tag analysis", job_id)

    def tag_progress(current, total):
        progress['tag_scanned'] = current
        jobs.update_job_progress(job_id, {'progress': progress})

    tag_result = scan_library_for_tags(progress_callback=tag_progress)
    progress['tag_scanned'] = tag_result.get('total_scanned', 0)
    progress['tag_filled'] = tag_result.get('fields_filled', 0)

    stages['tag_analysis'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
    logger.info("[AUTO_MATCH] Job %s tag analysis complete, scanned=%s, filled=%s", job_id, progress['tag_scanned'], progress['tag_filled'])

    # Stage 2: HiFi gap-fill
    stages['hifi_gap_fill'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[AUTO_MATCH] Job %s running HiFi gap-fill", job_id)

    def hifi_progress(entity_type, current, total):
        jobs.update_job_progress(job_id, {'progress': progress})

    hifi_result = find_missing_hifi_ids(progress_callback=hifi_progress)
    progress['hifi_tracks_matched'] = hifi_result.get('tracks_matched', 0)
    progress['hifi_albums_matched'] = hifi_result.get('albums_matched', 0)
    progress['hifi_artists_matched'] = hifi_result.get('artists_matched', 0)

    stages['hifi_gap_fill'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
    logger.info("[AUTO_MATCH] Job %s HiFi gap-fill complete, tracks=%s, albums=%s, artists=%s", job_id, progress['hifi_tracks_matched'], progress['hifi_albums_matched'], progress['hifi_artists_matched'])

    return {
        'trigger': trigger,
        'stages': stages,
        'progress': progress,
    }


def process_plex_sync_job(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or 'Music').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured before syncing')

    stages = {
        'reading_plex_library': 'in_progress',
        'updating_local_index': 'pending',
        'labeling_explicit_albums': 'pending',
        'backfilling_track_ids_from_tags': 'pending',
    }
    progress = {
        'processed_tracks': 0,
        'total_tracks': 0,
        'upserted_songs': 0,
        'deleted_songs': 0,
        'explicit_albums_labeled': 0,
        'tags_read': 0,
        'tags_updated': 0,
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    logger.info("[PLEX_SYNC] Job %s connecting to Plex at %s", job_id, server_url)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)
    jobs.update_job_progress(job_id, {'stages': stages})

    library = None
    sections = _plex_call_with_timeout(plex.library.sections, timeout=30, label="library.sections")
    for section in sections:
        _raise_if_job_cancelled(job_id)
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    logger.info("[PLEX_SYNC] Job %s fetching tracks from library '%s'", job_id, library_name)
    tracks = []
    try:
        _raise_if_job_cancelled(job_id)
        tracks = _plex_call_with_timeout(library.all, libtype='track', timeout=120, label="library.all")
    except Exception:
        _raise_if_job_cancelled(job_id)
        tracks = _plex_call_with_timeout(library.search, libtype='track', timeout=120, label="library.search")

    progress['total_tracks'] = len(tracks)
    stages['reading_plex_library'] = 'done'
    stages['updating_local_index'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    conn = get_db_connection()
    cur = conn.cursor()
    now_dt = _now_utc()
    now = now_dt.isoformat() + 'Z'
    seen_paths = set()
    explicit_album_keys = set()
    upserted = 0

    for idx, track in enumerate(tracks, start=1):
        title = getattr(track, 'title', None) or 'Unknown Title'
        artist = getattr(track, 'grandparentTitle', None) or None
        album = getattr(track, 'parentTitle', None) or None
        rating_key = str(getattr(track, 'ratingKey', None) or '').strip() or None
        album_key = _extract_plex_library_id(getattr(track, 'parentRatingKey', None) or getattr(track, 'parentKey', None))
        artist_key = _extract_plex_library_id(getattr(track, 'grandparentRatingKey', None) or getattr(track, 'grandparentKey', None))
        disc_number = _safe_int(getattr(track, 'parentIndex', None))
        track_number = _safe_int(getattr(track, 'trackNumber', None))

        # Track albums with [Explicit] in the name for later labeling
        if album_key and album and '[Explicit]' in album:
            explicit_album_keys.add(album_key)

        media_list = getattr(track, 'media', None) or []
        for media in media_list:
            parts = getattr(media, 'parts', None) or []
            bitrate = _safe_int(getattr(media, 'bitrate', None))
            media_format = (getattr(media, 'container', None) or '').strip().lower() or None

            for part in parts:
                file_path = (getattr(part, 'file', None) or '').strip()
                if not file_path:
                    continue

                if not media_format:
                    _, ext = os.path.splitext(file_path)
                    media_format = ext.replace('.', '').lower() if ext else None

                seen_paths.add(file_path)
                upserted += 1

                relative_path = _normalize_library_track_path(file_path)
                existing_track_row = _get_track_row_by_path(cur, relative_path) if relative_path else None

                album_artist_row = None
                album_row = None
                if existing_track_row and existing_track_row.get('album_id'):
                    album_row = _get_album_row(cur, existing_track_row['album_id'])
                if album_row and album_row.get('artist_id'):
                    album_artist_row = _get_artist_row(cur, album_row['artist_id'])

                if album_artist_row:
                    album_artist_row_id = _upsert_artist_row(
                        cur,
                        name=artist or 'Unknown Artist',
                        library_id=artist_key,
                        hifi_id=album_artist_row.get('hifi_id'),
                        confidence=_safe_float(album_artist_row.get('confidence')),
                        last_seen_at=now_dt,
                    )
                else:
                    album_artist_row_id = _upsert_artist_row(
                        cur,
                        name=artist or 'Unknown Artist',
                        library_id=artist_key,
                        confidence=0.0,
                        last_seen_at=now_dt,
                    )

                track_artist_row_id = album_artist_row_id
                if existing_track_row and existing_track_row.get('artist_id') and existing_track_row.get('artist_id') != album_artist_row_id:
                    track_artist_row = _get_artist_row(cur, existing_track_row['artist_id'])
                    if track_artist_row:
                        track_artist_row_id = _upsert_artist_row(
                            cur,
                            name=artist or 'Unknown Artist',
                            library_id=track_artist_row.get('library_id'),
                            hifi_id=track_artist_row.get('hifi_id'),
                            confidence=_safe_float(track_artist_row.get('confidence')),
                            last_seen_at=now_dt,
                        )

                existing_album_hifi_id = album_row.get('hifi_id') if album_row else None
                existing_album_confidence = _safe_float(album_row.get('confidence')) if album_row else 0.0
                existing_album_complete = album_row.get('complete') if album_row else False
                existing_album_matched_track_count = album_row.get('matched_track_count') if album_row else 0
                existing_album_expected_track_count = album_row.get('expected_track_count') if album_row else 0

                album_row_id = _upsert_album_row(
                    cur,
                    artist_id=album_artist_row_id,
                    title=album or 'Unknown Album',
                    library_id=album_key,
                    hifi_id=existing_album_hifi_id,
                    confidence=existing_album_confidence,
                    complete=existing_album_complete,
                    last_seen_at=now_dt,
                    matched_track_count=existing_album_matched_track_count,
                    expected_track_count=existing_album_expected_track_count,
                )

                existing_track_hifi_id = existing_track_row.get('hifi_id') if existing_track_row else None
                existing_track_confidence = _safe_float(existing_track_row.get('confidence')) if existing_track_row else 0.0

                track_duration = getattr(track, 'duration', None)
                try:
                    track_duration = int(track_duration) if track_duration is not None else None
                except Exception:
                    track_duration = None

                _upsert_track_row(
                    cur,
                    album_id=album_row_id,
                    artist_id=track_artist_row_id,
                    title=title,
                    path=relative_path or file_path.replace('\\', '/').lstrip('/'),
                    library_id=rating_key,
                    hifi_id=existing_track_hifi_id,
                    confidence=existing_track_confidence,
                    last_seen_at=now_dt,
                    audio_format=media_format,
                    bitrate=bitrate,
                    disc_number=disc_number,
                    track_number=track_number,
                    duration=track_duration,
                )

        progress['processed_tracks'] = idx
        progress['upserted_songs'] = upserted
        if idx % 25 == 0 or idx == len(tracks):
            jobs.update_job_progress(job_id, {'progress': progress})

    conn.commit()
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    deleted = 0
    if seen_paths:
        cur.execute(
            """
            DELETE FROM tracks
            WHERE library_id IS NOT NULL
              AND last_seen_at < %s
            """,
            (now_dt,)
        )
        deleted = cur.rowcount or 0
        cur.execute(
            """
            DELETE FROM albums AS albums_to_delete
            WHERE albums_to_delete.library_id IS NOT NULL
              AND albums_to_delete.last_seen_at < %s
              AND NOT EXISTS (
                    SELECT 1
                    FROM tracks
                    WHERE tracks.album_id = albums_to_delete.album_id
                )
            """,
            (now_dt,)
        )
        cur.execute(
            """
            DELETE FROM artists AS artists_to_delete
            WHERE artists_to_delete.library_id IS NOT NULL
              AND artists_to_delete.last_seen_at < %s
              AND NOT EXISTS (
                    SELECT 1
                    FROM albums
                    WHERE albums.artist_id = artists_to_delete.artist_id
                )
              AND NOT EXISTS (
                    SELECT 1
                    FROM tracks
                    WHERE tracks.artist_id = artists_to_delete.artist_id
                )
            """,
            (now_dt,)
        )

    conn.commit()

    # Add "Explicit" label to albums that contain [Explicit] in their name
    # (explicit_album_keys was populated during the track processing loop above)

    progress['deleted_songs'] = deleted
    stages['updating_local_index'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['labeling_explicit_albums'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    labeled_count = 0
    if explicit_album_keys:
        logger.info("[PLEX_SYNC] Job %s: Adding 'Explicit' label to %s albums", job_id, len(explicit_album_keys))
        for album_key in explicit_album_keys:
            try:
                # album_key format is /library/metadata/ID, extract the ID
                album_id = int(album_key.split('/')[-1])
                album = plex.fetchItem(album_id)
                if album and hasattr(album, 'addLabel'):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(album.addLabel, 'Explicit')
                        future.result(timeout=10)
                    labeled_count += 1
                    logger.info("[PLEX_SYNC] Job %s: Added 'Explicit' label to album %s", job_id, album_key)
            except concurrent.futures.TimeoutError:
                logger.info("[PLEX_SYNC] Job %s: Timed out adding label to album %s", job_id, album_key)
                continue
            except Exception as e:
                logger.info("[PLEX_SYNC] Job %s: Failed to add 'Explicit' label to album %s: %s", job_id, album_key, str(e))
                continue
        logger.info("[PLEX_SYNC] Job %s: Successfully labeled %s albums as Explicit", job_id, labeled_count)

    progress['explicit_albums_labeled'] = labeled_count
    stages['labeling_explicit_albums'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['backfilling_track_ids_from_tags'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    cur.execute(
        """
        SELECT tracks.track_id, tracks.album_id, tracks.path, tracks.hifi_id, tracks.isrc,
               albums.hifi_id AS album_hifi_id
        FROM tracks
        LEFT JOIN albums ON albums.album_id = tracks.album_id
        WHERE tracks.library_id IS NOT NULL
          AND (
                tracks.hifi_id IS NULL
             OR tracks.isrc IS NULL
             OR albums.hifi_id IS NULL
          )
        ORDER BY tracks.track_id ASC
        """
    )
    tag_rows = cur.fetchall() or []
    tags_read = 0
    tags_updated = 0
    albums_backfilled = set()

    for tag_row in tag_rows:
        _raise_if_job_cancelled(job_id)
        file_path = str(tag_row.get('path') or '').strip()
        if not file_path:
            continue

        embedded = _read_embedded_hifi_ids(file_path)
        embedded_track_id = str(embedded.get('track_id') or '').strip() or None
        embedded_album_id = str(embedded.get('album_id') or '').strip() or None
        embedded_isrc = str(embedded.get('isrc') or '').strip() or None

        if not embedded_track_id and not embedded_album_id and not embedded_isrc:
            continue

        tags_read += 1
        update_fields = []
        update_values = []

        if embedded_track_id and not tag_row.get('hifi_id'):
            update_fields.append('hifi_id = %s')
            update_values.append(embedded_track_id)
            update_fields.append('confidence = 0.99')

        if embedded_isrc and not tag_row.get('isrc'):
            update_fields.append('isrc = %s')
            update_values.append(embedded_isrc)

        if update_fields:
            update_values.append(tag_row['track_id'])
            cur.execute(
                f"UPDATE tracks SET {', '.join(update_fields)} WHERE track_id = %s",
                update_values
            )
            tags_updated += 1

        if embedded_album_id and not tag_row.get('album_hifi_id'):
            album_id_val = int(tag_row.get('album_id') or 0)
            if album_id_val and album_id_val not in albums_backfilled:
                cur.execute(
                    "UPDATE albums SET hifi_id = %s, confidence = 0.99 WHERE album_id = %s AND (hifi_id IS NULL OR hifi_id = '')",
                    (embedded_album_id, album_id_val)
                )
                albums_backfilled.add(album_id_val)

        if tags_read % 50 == 0 or tags_read == len(tag_rows):
            conn.commit()
            progress['tags_read'] = tags_read
            progress['tags_updated'] = tags_updated
            jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
            logger.info("[PLEX_SYNC] Job %s: Tag backfill progress: read=%s, updated=%s, albums_backfilled=%s", job_id, tags_read, tags_updated, len(albums_backfilled))

    conn.commit()
    logger.info("[PLEX_SYNC] Job %s: Tag backfill complete: read=%s, updated=%s, albums_backfilled=%s", job_id, tags_read, tags_updated, len(albums_backfilled))

    stages['backfilling_track_ids_from_tags'] = 'done'
    progress['tags_read'] = tags_read
    progress['tags_updated'] = tags_updated
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    logger.info("[PLEX_SYNC] Job %s finished. tracks=%s upserted=%s deleted=%s explicit_albums_labeled=%s tags_read=%s tags_updated=%s", job_id, progress['total_tracks'], upserted, deleted, labeled_count, tags_read, tags_updated)

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'total_tracks': progress['total_tracks'],
        'upserted_songs': upserted,
        'deleted_songs': deleted,
        'explicit_albums_labeled': labeled_count,
        'tags_read': tags_read,
        'tags_updated': tags_updated,
    }

def process_download_job(job_id, payload):
    track_id = payload.get('trackId')
    quality_choice = str(payload.get('downloadQuality', payload.get('quality'))).strip().upper()
    if quality_choice not in ('LOSSLESS', 'HIGH', 'LOW'):
        quality_choice = 'LOSSLESS'

    stages = {
        'downloaded': 'pending',
        'tagged': 'pending',
        'converted': 'pending',
        'written': 'pending',
        'playlist_added': 'pending'
    }

    if not track_id:
        raise ValueError('trackId is required')

    logger.info("[DOWNLOAD] Fetching track metadata from normalized HiFi object for quality=%s", quality_choice)
    try:
        track_object = get_hifi_track_object(
            track_id,
            include_streams=False,
            include_album=True,
            audio_quality=quality_choice,
            mirror_type='tidal',
        )
    except Exception as e:
        raise downloads.TransientDownloadError(f"Failed to fetch download track object: {str(e)}") from e

    if not isinstance(track_object, dict):
        raise downloads.TransientDownloadError("Failed to build normalized track object")

    file_naming = payload.get('fileNaming')
    if not file_naming:
        file_naming = payload.get('fileNamingAlbum') or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']

    tag_settings = get_download_settings()

    download_source = tag_settings.get('download_source', 'tidal').lower()

    downloads_folder = DOWNLOADS_ROOT

    if not os.path.exists(downloads_folder):
        logger.info("[DOWNLOAD] WARNING: Downloads folder does not exist, creating it: %s", downloads_folder)
        os.makedirs(downloads_folder, exist_ok=True)

    track_data = track_object.get('track') if isinstance(track_object.get('track'), dict) else {}
    album_data = track_data.get('album') if isinstance(track_data.get('album'), dict) else {}

    output_format = 'flac' if quality_choice == 'LOSSLESS' else 'm4a'
    logger.info("[DOWNLOAD] Selected output format=%s for quality='%s'", output_format, quality_choice)

    track_data = track_object.get('track') if isinstance(track_object.get('track'), dict) else {}
    album_data = track_data.get('album') if isinstance(track_data.get('album'), dict) else {}

    # --- Extract metadata before downloading (needed for match check and file naming) ---

    track_artist_name = 'Unknown Artist'
    track_artist_id = None
    album_artist_name = None
    album_artist_id = None
    album_name = 'Unknown Album'
    track_title = 'Unknown Track'
    track_version = ''
    track_num = '01'
    disc_num = ''
    release_year = ''
    copyright_text = ''
    cover_url = ''
    album_id = ''
    album_disc_count = 1
    album_has_multiple_discs = False
    track_artists = []

    if isinstance(track_data, dict):
        if isinstance(track_data.get('artists'), list) and track_data['artists']:
            artist_names = [str(a.get('name', '')).strip() for a in track_data['artists'] if isinstance(a, dict) and a.get('name')]
            track_artist_name = '; '.join(artist_names) if artist_names else 'Unknown Artist'
            track_artists = artist_names
            first_artist = track_data['artists'][0] if isinstance(track_data['artists'][0], dict) else None
            if first_artist and first_artist.get('id') is not None:
                track_artist_id = str(first_artist.get('id')).strip() or None
        elif isinstance(track_data.get('artists'), dict):
            artist = track_data['artists']
            track_artist_name = str(artist.get('name', 'Unknown Artist'))
            if artist.get('name'):
                track_artists = [track_artist_name]
            if artist.get('id') is not None:
                track_artist_id = str(artist.get('id')).strip() or None

        track_title = str(track_data.get('title') or track_title)
        track_version = str(track_data.get('version') or '').strip()
        if track_data.get('explicit') and tag_settings.get('tag_explicit_suffix', True) and '[Explicit]' not in track_title:
            track_title += ' [Explicit]'
        if track_version:
            track_title = f"{track_title} ({track_version})"

        track_number = track_data.get('trackNumber')
        if track_number is not None:
            track_num = str(track_number).zfill(2)

        disc_value = track_data.get('discNumber')
        if disc_value is None:
            disc_value = track_data.get('volumeNumber')
        if disc_value is not None:
            try:
                parsed_disc_num = int(str(disc_value).strip())
                if parsed_disc_num > 0:
                    disc_num = str(parsed_disc_num)
            except (TypeError, ValueError):
                disc_num = ''

        if isinstance(track_data.get('copyright'), str) and track_data.get('copyright').strip():
            copyright_text = str(track_data.get('copyright')).strip()

    if isinstance(album_data, dict):
        album_name = str(album_data.get('title') or album_name)
        album_id = str(album_data.get('id')) if album_data.get('id') is not None else ''
        cover_url = str(album_data.get('cover') or '')
        if album_data.get('explicit') and tag_settings.get('tag_explicit_suffix', True) and '[Explicit]' not in album_name:
            album_name += ' [Explicit]'

        if isinstance(album_data.get('releaseDate'), str) and len(album_data.get('releaseDate')) >= 4:
            release_year = album_data.get('releaseDate')[:4]

        album_artists = []
        main_album_artist_name = None
        if isinstance(album_data.get('artists'), list):
            for artist in album_data['artists']:
                if isinstance(artist, dict) and artist.get('name'):
                    artist_name = str(artist.get('name')).strip()
                    album_artists.append(artist_name)
                    if main_album_artist_name is None and str(artist.get('type') or '').upper() == 'MAIN':
                        main_album_artist_name = artist_name
                    if album_artist_id is None and artist.get('id') is not None:
                        album_artist_id = str(artist.get('id')).strip() or None
        elif isinstance(album_data.get('artists'), dict):
            artist = album_data['artists']
            if isinstance(artist, dict) and artist.get('name'):
                artist_name = str(artist.get('name')).strip()
                album_artists.append(artist_name)
                if str(artist.get('type') or '').upper() == 'MAIN':
                    main_album_artist_name = artist_name
                if artist.get('id') is not None:
                    album_artist_id = str(artist.get('id')).strip() or None

        if main_album_artist_name:
            album_artist_name = main_album_artist_name
        elif album_artists:
            album_artist_name = album_artists[0]

        try:
            album_disc_count = int(album_data.get('numberOfDiscs') or album_data.get('numberOfVolumes') or 1)
        except (TypeError, ValueError):
            album_disc_count = 1
        album_has_multiple_discs = album_disc_count > 1

    if not release_year and copyright_text:
        release_year = extract_year_from_text(copyright_text)

    if not cover_url and album_id:
        cover_url = downloads.format_tidal_image_url(str(album_id), 1280)

    if not album_artist_name:
        album_artist_name = track_artist_name

    artist_name = track_artist_name
    effective_artist_name = album_artist_name or track_artist_name

    logger.info("[DOWNLOAD] Extracted metadata: TrackArtist='%s', AlbumArtist='%s', EffectiveArtistForPath='%s', Album='%s', Title='%s', TrackNum='%s', DiscNum='%s', Year='%s', Cover='%s'", track_artist_name, album_artist_name or '', effective_artist_name, album_name, track_title, track_num, disc_num, release_year, cover_url)

    # --- Compute file path (shared by both match-found and download branches) ---

    file_ext = output_format

    safe_artist = sanitize_filename_component(effective_artist_name)
    safe_album = sanitize_filename_component(album_name)
    safe_title = sanitize_filename_component(track_title)
    safe_track = sanitize_filename_component(track_num)

    if album_has_multiple_discs and disc_num:
        prefixed_track = f"{disc_num}-{safe_track}"
        safe_track = sanitize_filename_component(prefixed_track)

    file_path = file_naming.replace('{artist}', safe_artist)
    file_path = file_path.replace('{album}', safe_album)
    file_path = file_path.replace('{track}', safe_track)
    file_path = file_path.replace('{title}', safe_title)
    file_path = file_path.replace('{ext}', file_ext)
    file_path = clean_path_components(file_path)

    # --- Check for existing matches before downloading ---

    conn = get_db_connection()
    cur = conn.cursor()
    metadata_rows = _lookup_track_metadata(cur, track_title, artist_name, album_name)
    conn.close()

    ignore_matches = bool(payload.get('ignore_matches', False))
    matching_rows = []
    if not ignore_matches:
        matching_rows = [row for row in metadata_rows if _matches_requested_format(output_format, row.get('format'))]

    summary_rows = [
        {
            'format': str(row.get('format') or '').strip().lower() or 'unknown',
            'bitrate': row.get('bitrate'),
            'album': row.get('album')
        }
        for row in metadata_rows[:8]
    ]
    logger.info("[DOWNLOAD_DECISION] Job %s: metadata_candidates=%s, matching_selected_format=%s, candidate_summary=%s", job_id, len(metadata_rows), len(matching_rows), summary_rows)
    if matching_rows:
        matched_row = matching_rows[0]
        matched_path = str(matched_row.get('file_path') or '').strip()

        full_path = matched_path if matched_path else os.path.join(downloads_folder, file_path)
        full_path = os.path.normpath(full_path)

        logger.info("[DOWNLOAD_DECISION] Job %s: skipping download because existing Plex inventory metadata matches selected format and quality (format='%s', bitrate='%s')", job_id, matched_row.get('format'), matched_row.get('bitrate'))
        logger.info("[DOWNLOAD] Existing metadata match found - skipping download pipeline")
        stages['downloaded'] = 'done'
        stages['tagged'] = 'done'
        stages['converted'] = 'skipped'
        stages['written'] = 'done'
        set_last_download_activity_at(datetime.utcnow())
        jobs.update_job_progress(job_id, {
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': payload.get('plex_playlist'),
            'stages': stages
        })

        playlist_name = payload.get('plex_playlist')
        if playlist_name:
            stages['playlist_added'] = 'done'
            jobs.update_job_progress(job_id, {'stages': stages})
            logger.info("[DOWNLOAD] Job %s: queuing playlist add (existing match) for path=%s playlist=%s", job_id, full_path, playlist_name)
            queue_pending_playlist_addition(
                full_path,
                playlist_name,
                parent_job_id=job_id,
                plex_user_id=payload.get('plex_user_id')
            )
            logger.info("[DOWNLOAD] Playlist requested - queued for bulk playlist add")
        else:
            logger.info("[DOWNLOAD] Plex playlist update skipped. No playlist requested.")
            stages['playlist_added'] = 'skipped'
            jobs.update_job_progress(job_id, {'stages': stages})

        upsert_download_match_hint(
            track_title=track_title,
            track_artist_name=track_artist_name,
            album_title=album_name,
            album_artist_name=album_artist_name or track_artist_name,
            full_path=full_path,
            audio_format=output_format,
            hifi_track_id=str(track_id),
            hifi_album_id=str(album_id) if album_id else None,
            track_hifi_artist_id=track_artist_id,
            album_hifi_artist_id=album_artist_id or track_artist_id,
            isrc=track_data.get('isrc'),
            duration=track_data.get('duration'),
            track_number=track_number,
            disc_number=_safe_int(disc_num) if disc_num else None,
        )

        return {
            'file_path': full_path,
            'format': output_format,
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': playlist_name,
            'download_skipped_existing': True,
            'stages': stages
        }

    logger.info("[DOWNLOAD_DECISION] Job %s: downloading because no existing Plex inventory metadata matched selected format '%s'", job_id, output_format)

    full_path = os.path.join(downloads_folder, file_path)
    full_path = os.path.normpath(full_path)

    logger.info("[DOWNLOAD_DEBUG] file_naming='%s' template -> file_path='%s'", file_naming, file_path)
    logger.info("[DOWNLOAD_DEBUG] resolved full_path='%s' downloads_folder='%s'", full_path, downloads_folder)
    logger.info("[DOWNLOAD_DECISION] Job %s: selected_format='%s', title='%s', artist='%s', album='%s', effective_artist='%s'", job_id, output_format, track_title, artist_name, album_name, effective_artist_name)

    # --- Download track to temp ---

    temp_folder = '/app/temp'
    os.makedirs(temp_folder, exist_ok=True)

    download_mirror = None  # Track which mirror was used

    # --- Download track with source fallback ---
    # Build priority order from comma-separated download_source (e.g. "tidal,qobuz")
    download_sources = [s.strip() for s in download_source.split(',') if s.strip() in ('tidal', 'qobuz')]
    if not download_sources:
        download_sources = ['tidal']

    last_download_error = None
    audio_format = None
    expected_duration = track_data.get('duration')

    for current_source in download_sources:
        if current_source == 'qobuz' and not track_data.get('isrc'):
            logger.info("[DOWNLOAD] Skipping Qobuz: track has no ISRC")
            last_download_error = "Qobuz requires ISRC"
            continue

        # Create a fresh temp path for each attempt
        temp_source_path = os.path.join(temp_folder, f'temp_{track_id}_{current_source}.{output_format}')

        try:
            if current_source == 'qobuz':
                # --- Qobuz download path ---
                isrc = track_data['isrc']
                current_quality = quality_choice
                if current_quality not in qobuz.QOBUZ_SUPPORTED_QUALITIES:
                    logger.info("[DOWNLOAD] Qobuz does not support quality '%s', falling back to LOSSLESS", current_quality)
                    current_quality = 'LOSSLESS'

                qobuz_mirrors = downloads.load_enabled_mirror_urls(mirror_type='qobuz')
                if not qobuz_mirrors:
                    raise ValueError("No Qobuz mirrors configured")

                qobuz_result = None
                src_error = None
                for mirror in qobuz_mirrors:
                    base_url = mirror['url']
                    logger.info("[QOBUZ] Trying mirror: %s", base_url)
                    try:
                        qobuz_result = qobuz.download_qobuz_track(
                            base_url=base_url,
                            isrc=isrc,
                            tidal_quality=current_quality,
                            output_path=temp_source_path,
                        )
                        if qobuz_result:
                            download_mirror = base_url
                            break
                    except Exception as e:
                        logger.warning("[QOBUZ] Mirror %s failed: %s", base_url, e)
                        src_error = e
                        continue

                if qobuz_result is None:
                    error_msg = f"Failed to download from Qobuz (ISRC: {isrc})"
                    if src_error:
                        error_msg += f": {src_error}"
                    raise ValueError(error_msg)

                logger.info("[QOBUZ] Successfully downloaded track via Qobuz (ISRC: %s)", isrc)

                # Detect format
                with open(temp_source_path, 'rb') as tmp_file:
                    audio_format = downloads.detect_audio_format(tmp_file.read(32))
                if audio_format == 'unknown':
                    audio_format = 'flac'
                logger.info("[DOWNLOAD] Detected downloaded audio format: %s", audio_format)

                # Validate duration
                downloads.validate_audio_duration(temp_source_path, expected_duration)

            else:
                # --- Tidal download path ---
                logger.info("[DOWNLOAD] Downloading track data from trackManifests into temporary file: %s", temp_source_path)
                _, tidal_target = downloads.download_track_manifest(
                    track_id=track_id,
                    output_path=temp_source_path,
                    quality=quality_choice,
                    url_list=SQUID_URLS,
                    usage='DOWNLOAD',
                    for_download=True,
                )
                download_mirror = tidal_target['url'].rstrip('/')

                # Detect format
                with open(temp_source_path, 'rb') as tmp_file:
                    audio_format = downloads.detect_audio_format(tmp_file.read(32))
                logger.info("[DOWNLOAD] Detected downloaded audio format: %s", audio_format)
                if audio_format == 'unknown':
                    logger.info("[DOWNLOAD] WARNING: Could not detect audio format, assuming FLAC")
                    audio_format = 'flac'

                # Validate duration
                try:
                    downloads.validate_audio_duration(temp_source_path, expected_duration)
                except RuntimeError:
                    if tidal_target:
                        downloads.disable_mirror_downloads(tidal_target['name'])
                    raise

            # Success — exit the source loop
            break

        except (ValueError, downloads.TransientDownloadError, RuntimeError, requests.exceptions.RequestException) as e:
            last_download_error = str(e)
            logger.info("[DOWNLOAD] Source '%s' failed, %s", current_source,
                        "trying next source..." if len(download_sources) > 1 else "no more sources")
            downloads.cleanup_file(temp_source_path)
            continue

    if download_mirror is None:
        raise downloads.TransientDownloadError(
            f"All download sources failed: {last_download_error or 'unknown error'}"
        )

    logger.info(" [DOWNLOAD] Job %s starting for track %s", job_id, track_id)

    jobs.update_job_progress(job_id, {
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': payload.get('plex_playlist'),
        'stages': stages
    })

    media_tags = []
    audio_quality = None
    if isinstance(track_data, dict):
        audio_quality = track_data.get('maxAudioQuality') or track_data.get('audioQuality')
        if isinstance(audio_quality, str) and audio_quality:
            media_tags.append(audio_quality)

    # Treat DOLBY_ATMOS as HIRES_LOSSLESS since it requires high-quality audio
    if 'DOLBY_ATMOS' in media_tags and 'HIRES_LOSSLESS' not in media_tags:
        media_tags.append('HIRES_LOSSLESS')

    logger.info("[DOWNLOAD] File path template result: %s", file_path)

    logger.info("[DOWNLOAD] Full output path: %s", full_path)

    output_dir = os.path.dirname(full_path)
    logger.info("[DOWNLOAD] Creating directory structure: %s", output_dir)

    os.makedirs(output_dir, exist_ok=True)
    logger.info("[DOWNLOAD] SUCCESS: Directory created/exists: %s", output_dir)

    logger.info("[DOWNLOAD] Download complete. Using temporary source file: %s", temp_source_path)

    cover_image_data = None
    if cover_url:
        cover_image_data = downloads.download_cover_image(cover_url)

    album_track_count = None
    if isinstance(album_data.get('numberOfTracks'), int):
        album_track_count = album_data.get('numberOfTracks')
    elif isinstance(album_data.get('numberOfTracks'), str) and album_data.get('numberOfTracks').isdigit():
        album_track_count = int(album_data.get('numberOfTracks'))

    album_disc_count = None
    if isinstance(album_data.get('numberOfDiscs'), int):
        album_disc_count = album_data.get('numberOfDiscs')
    elif isinstance(album_data.get('numberOfDiscs'), str) and album_data.get('numberOfDiscs').isdigit():
        album_disc_count = int(album_data.get('numberOfDiscs'))

    metadata_dict = {
        'artist': track_artist_name,
        'track_artists': track_artists or [track_artist_name],
        'album_artist': album_artist_name,
        'album_artists': album_artists or ([album_artist_name] if album_artist_name else []),
        'title': track_title,
        'album': album_name,
        'year': release_year,
        'track_number': track_num,
        'disc_number': disc_num,
        'track_total': album_track_count,
        'disc_total': album_disc_count,
        'version': track_version,
        'copyright': copyright_text,
        'track_explicit': bool(track_data.get('explicit')),
        'album_explicit': bool(album_data.get('explicit')),
        'explicit': bool(track_data.get('explicit') or album_data.get('explicit')),
        'tidal_track_id': track_id,
        'tidal_album_id': album_id,
        'isrc': track_data.get('isrc'),
        'audio_quality': track_data.get('maxAudioQuality') or track_data.get('audioQuality'),
    }

    logger.info("[DOWNLOAD_DEBUG] cover_url='%s' cover_bytes=%s", cover_url, len(cover_image_data) if cover_image_data else 0)
    logger.info("[DOWNLOAD_DEBUG] metadata_dict=%s", metadata_dict)

    temp_folder = '/app/temp'
    os.makedirs(temp_folder, exist_ok=True)

    temp_target_path = os.path.join(temp_folder, f'temp_{track_id}.{output_format}')

    logger.info("[DOWNLOAD] Using temporary source file: %s", temp_source_path)

    stages['downloaded'] = 'done'
    set_last_download_activity_at(datetime.utcnow())
    jobs.update_job_progress(job_id, {'stages': stages})

    logger.info("[DOWNLOAD] Adding metadata to staged %s: %s", output_format.upper(), temp_source_path)
    logger.info("[DOWNLOAD_DEBUG] tagging temp_source_path='%s'", temp_source_path)
    downloads.add_id3_tags_to_file(temp_source_path, metadata_dict, cover_image_data, tag_settings)
    logger.info("[DOWNLOAD_DEBUG] tagging complete for temp_source_path='%s'", temp_source_path)
    stages['tagged'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    converted = False
    if output_format == 'm4a' and audio_format != 'm4a':
        logger.info("[DOWNLOAD] Output format is AAC - converting staged %s to M4A", audio_format.upper())
        success = convert_to_aac(temp_source_path, temp_target_path, source_format=audio_format)
        if not success:
            downloads.cleanup_file(temp_source_path)
            downloads.cleanup_file(temp_target_path)
            raise Exception(f"Failed to convert {audio_format.upper()} to M4A")

        shutil.move(temp_target_path, full_path)
        logger.info("[DOWNLOAD_DEBUG] tagging final M4A full_path='%s'", full_path)
        downloads.add_id3_tags_to_file(full_path, metadata_dict, cover_image_data, tag_settings)
        logger.info("[DOWNLOAD_DEBUG] tagging complete for final M4A full_path='%s'", full_path)
        converted = True
    elif output_format == 'flac' and audio_format != 'flac':
        logger.info("[DOWNLOAD] Output format is FLAC - converting staged %s to FLAC", audio_format.upper())
        success = convert_to_flac(temp_source_path, temp_target_path, source_format=audio_format)
        if not success:
            downloads.cleanup_file(temp_source_path)
            downloads.cleanup_file(temp_target_path)
            raise Exception(f"Failed to convert {audio_format.upper()} to FLAC")

        shutil.move(temp_target_path, full_path)
        logger.info("[DOWNLOAD_DEBUG] tagging final FLAC full_path='%s'", full_path)
        downloads.add_id3_tags_to_file(full_path, metadata_dict, cover_image_data, tag_settings)
        logger.info("[DOWNLOAD_DEBUG] tagging complete for final FLAC full_path='%s'", full_path)
        converted = True
    else:
        if not full_path.endswith(f'.{output_format}'):
            full_path = full_path.rsplit('.', 1)[0] + f'.{output_format}'
            logger.info("[DOWNLOAD] Updated output path with correct extension: %s", full_path)

        logger.info("[DOWNLOAD] Output is %s - moving from temp", output_format.upper())
        shutil.move(temp_source_path, full_path)

    stages['converted'] = 'done' if converted else 'skipped'
    stages['written'] = 'done'
    set_last_download_activity_at(datetime.utcnow())
    jobs.update_job_progress(job_id, {'stages': stages})

    if converted:
        downloads.cleanup_file(temp_source_path)
        downloads.cleanup_file(temp_target_path)
    else:
        downloads.cleanup_file(temp_source_path)

    logger.info("[DOWNLOAD] SUCCESS: Downloaded and saved to %s", full_path)

    playlist_name = payload.get('plex_playlist')
    if playlist_name:
        stages['playlist_added'] = 'done'
        jobs.update_job_progress(job_id, {'stages': stages})
        logger.info("[DOWNLOAD] Job %s: queuing playlist add for path=%s playlist=%s", job_id, full_path, playlist_name)
        queue_pending_playlist_addition(
            full_path,
            playlist_name,
            parent_job_id=job_id,
            plex_user_id=payload.get('plex_user_id')
        )
        logger.info("[DOWNLOAD] Playlist requested - queued for bulk playlist add")
    else:
        logger.info("[DOWNLOAD] Plex playlist update skipped. No playlist requested.")
        stages['playlist_added'] = 'skipped'
        jobs.update_job_progress(job_id, {'stages': stages})

    final_audio_format = output_format
    upsert_download_match_hint(
        track_title=track_title,
        track_artist_name=track_artist_name,
        album_title=album_name,
        album_artist_name=album_artist_name or track_artist_name,
        full_path=full_path,
        audio_format=final_audio_format,
        hifi_track_id=str(track_id),
        hifi_album_id=str(album_id) if album_id else None,
        track_hifi_artist_id=track_artist_id,
        album_hifi_artist_id=album_artist_id or track_artist_id,
        isrc=track_data.get('isrc'),
        duration=track_data.get('duration'),
        track_number=track_number,
        disc_number=_safe_int(disc_num) if disc_num else None,
    )

    result = {
        'file_path': full_path,
        'format': output_format,
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': playlist_name,
        'download_mirror': download_mirror,
        'mirror_type': current_source,
        'stages': stages
    }
    return result


# Plex Functions
# Initialize database and mirror data (skip during testing)
if os.environ.get("SQUIDLY_SKIP_STARTUP") != "1":
    init_db()
    jobs.recover_stale_in_progress_jobs()
    downloads.seed_mirrors_from_json()

    # Initialize URL list and round-robin iterator
    SQUID_URLS = downloads.load_enabled_mirror_urls()
    url_iterator = cycle(SQUID_URLS)

    # Run validation on startup
    # With gunicorn --preload, this runs once before workers are forked
    logger.info("Squidly starting up...")
    downloads.validate_all_endpoints()
    plex_healthcheck()

    # Start all background workers and schedulers
    start_workers()

    # Download folders already created and validated at module level above

    try:
        os.makedirs('/app/temp', exist_ok=True)
        logger.info("Temp folder ready (/app/temp)")
    except Exception as e:
        logger.info("WARNING: Failed to create temp folder: %s", str(e))


# Helper to check if Plex credentials are valid
def get_plex_credentials_valid():
    ok, _ = plex_healthcheck()
    return ok

def _get_album_quality_rank(album):
    """
    Extract audio quality rank from an album object.
    Higher numbers = better quality.
    """
    quality_order = {
        'HI_RES_LOSSLESS': 5,
        'HIRES_LOSSLESS': 5,
        'DOLBY_ATMOS': 5,  # Treat as hi-res
        'LOSSLESS': 4,
        'HIGH': 2,
        'LOW': 1
    }
    
    # Default to LOW if unknown
    rank = 0
    
    # Check mediaMetadata.tags
    media_metadata = album.get('mediaMetadata')
    if isinstance(media_metadata, dict):
        tags = media_metadata.get('tags')
        if isinstance(tags, list):
            for tag in tags:
                if tag in quality_order:
                    rank = max(rank, quality_order[tag])
    
    # Check audioQuality field (as fallback)
    audio_quality = album.get('audioQuality')
    if isinstance(audio_quality, str) and audio_quality in quality_order:
        rank = max(rank, quality_order[audio_quality])
    
    return rank


def _derive_audio_quality_from_tags(album):
    """
    Derive maxAudioQuality from mediaTags or mediaMetadata.tags on an album object.
    Returns the highest quality tag found, or None.
    """
    quality_priority = ['DOLBY_ATMOS', 'HIRES_LOSSLESS', 'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW']

    media_metadata = album.get('mediaMetadata')
    if isinstance(media_metadata, dict):
        tags = media_metadata.get('tags')
        if isinstance(tags, list):
            tags_upper = [t.upper() for t in tags if t]
            for q in quality_priority:
                if q in tags_upper:
                    return q

    media_tags = album.get('mediaTags')
    if isinstance(media_tags, list):
        tags_upper = [t.upper() for t in media_tags if t]
        for q in quality_priority:
            if q in tags_upper:
                return q

    return None


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html', plex_credentials_valid=get_plex_credentials_valid())

@app.route('/api/hifi/search', methods=['GET'])
def search():
    """
    Unified search endpoint for tracks, albums, artists, playlists, and track-by-ID.
    Query parameters:
    - s={query}       : Search tracks
    - a={query}       : Search artists
    - al={query}      : Search albums
    - p={query}       : Search playlists
    - trackid={query} : Search by exact Tidal track ID
    - limit={n}       : Optional page size
    - offset={n}      : Optional page offset
    """
    supported_search_types = ('s', 'a', 'al', 'p', 'trackid')
    provided_search_types = [key for key in supported_search_types if key in request.args]

    if not provided_search_types:
        return jsonify({'error': 'No search parameter provided. Use s, a, al, or p'}), 400

    if len(provided_search_types) > 1:
        return jsonify({'error': 'Provide exactly one search parameter: s, a, al, or p'}), 400

    search_type = provided_search_types[0]
    query = request.args.get(search_type)

    if not query:
        return jsonify({'error': 'Query value cannot be empty'}), 400

    if search_type == 'trackid':
        if not query.isdigit():
            return jsonify({'error': 'Track ID must be numeric'}), 400

        try:
            response, target = downloads.make_request_with_retry_rotating_mirrors(
                f"/info/?{urlencode({'id': query})}",
                SQUID_URLS,
                method='GET',
                timeout=10,
                max_retries=3
            )

            if not response.ok:
                return jsonify({
                    'error': f'Upstream API error via {target["name"]}',
                    'status_code': response.status_code
                }), response.status_code

            result = response.json() if response.content else {}
            track_item = None

            if isinstance(result, dict):
                data = result.get('data') or {}
                if isinstance(data, dict) and data.get('track'):
                    track_item = data.get('track')
                elif isinstance(data, dict) and data.get('items'):
                    items = data.get('items')
                    if isinstance(items, list) and items:
                        track_item = items[0]
                elif isinstance(result.get('track'), dict):
                    track_item = result.get('track')
                elif isinstance(result.get('data'), dict):
                    track_item = result.get('data')

            if not track_item:
                return jsonify({
                    'data': {'items': []},
                    'proxied_via': target['name']
                })

            if 'id' not in track_item or not track_item.get('id'):
                track_item['id'] = int(query)

            normalized_track_item = _build_normalized_hifi_track_object(track_item) if isinstance(track_item, dict) else track_item

            # Coerce to track-list shape for front-end
            return jsonify({
                'data': {'items': [normalized_track_item]},
                'proxied_via': target['name']
            })

        except requests.exceptions.RequestException as e:
            return jsonify({
                'error': 'Proxy error',
                'details': str(e),
                'query': query
            }), 502

    upstream_params = [(search_type, query)]
    for param_name in ('limit', 'offset'):
        param_value = request.args.get(param_name)
        if param_value:
            upstream_params.append((param_name, param_value))

    upstream_query = urlencode(upstream_params)
    
    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/search/?{upstream_query}",
                SQUID_URLS,
            max_retries=3
        )
        
        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code
        
        result = response.json()
        result['proxied_via'] = target['name']
        
        # Deduplicate search results locally while preserving upstream payload shape.
        if isinstance(result, dict):
            data = result.get('data')
            if isinstance(data, dict):
                if search_type == 'al':
                    albums = data.get('albums')
                    if isinstance(albums, dict):
                        album_items = albums.get('items')
                        if isinstance(album_items, list):
                            best_by_key = {}
                            for album in album_items:
                                if not isinstance(album, dict):
                                    continue
                                key = _get_hifi_album_dedupe_key(album)
                                if key is None:
                                    continue
                                existing = best_by_key.get(key)
                                if existing is None:
                                    best_by_key[key] = album
                                    continue
                                current_rank = _get_hifi_audio_quality_rank(album.get('audioQuality'))
                                existing_rank = _get_hifi_audio_quality_rank(existing.get('audioQuality'))
                                if current_rank > existing_rank:
                                    best_by_key[key] = album

                            deduped_items = []
                            seen_keys = set()
                            for album in album_items:
                                if not isinstance(album, dict):
                                    continue
                                key = _get_hifi_album_dedupe_key(album)
                                if key is None:
                                    deduped_items.append(album)
                                    continue
                                if key in seen_keys:
                                    continue
                                chosen = best_by_key.get(key)
                                if chosen is not None:
                                    deduped_items.append(chosen)
                                    seen_keys.add(key)
                                else:
                                    deduped_items.append(album)
                                    seen_keys.add(key)

                            albums['items'] = deduped_items
                elif search_type == 's':
                    items = data.get('items')
                    if isinstance(items, list):
                        best_by_key = {}
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            key = _get_hifi_track_dedupe_key(item)
                            if key is None:
                                continue
                            existing = best_by_key.get(key)
                            if existing is None:
                                best_by_key[key] = item
                                continue
                            current_rank = _get_hifi_audio_quality_rank(item.get('audioQuality'))
                            existing_rank = _get_hifi_audio_quality_rank(existing.get('audioQuality'))
                            if current_rank > existing_rank:
                                best_by_key[key] = item

                        deduped_items = []
                        seen_keys = set()
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            key = _get_hifi_track_dedupe_key(item)
                            if key is None:
                                deduped_items.append(item)
                                continue
                            if key in seen_keys:
                                continue
                            chosen = best_by_key.get(key)
                            if chosen is not None:
                                deduped_items.append(chosen)
                                seen_keys.add(key)
                            else:
                                deduped_items.append(item)
                                seen_keys.add(key)

                        data['items'] = [_build_normalized_hifi_track_object(item) if isinstance(item, dict) else item for item in deduped_items]

        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e),
            'query': query
        }), 502

@app.route('/api/hifi/tracks/<track_id>', methods=['GET'])
def track_info(track_id=None):
    """
    Get detailed track metadata.
    Query parameter:
    - id={trackId} : Tidal track ID
    """
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    upstream_query = urlencode({'id': track_id})
    
    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/info/?{upstream_query}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )
        
        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code
        
        result = response.json()
        result['proxied_via'] = target['name']
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/hifi/tracks/<track_id>/object', methods=['GET'])
def track_object(track_id=None):
    """
    Get a normalized HiFi track object.
    Query parameters:
    - id={trackId}            : Tidal track ID
    - include_streams={bool}  : include track manifest streams (true/false)
    - include_album={bool}    : include nested album metadata (true/false)
    """
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    include_streams = str(request.args.get('include_streams', 'false')).strip().lower() in ('1', 'true', 'yes')
    include_album = str(request.args.get('include_album', 'false')).strip().lower() in ('1', 'true', 'yes')
    audio_quality = str(request.args.get('audio_quality', '')).strip() or None

    try:
        result = get_hifi_track_object(
            track_id,
            include_streams=include_streams,
            include_album=include_album,
            audio_quality=audio_quality
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build track object', 'details': str(e)}), 500

@app.route('/api/hifi/tracks/<track_id>/stream', methods=['GET'])
def track_stream(track_id=None):
    """
    Proxy a HiFi track stream through the application.
    Query parameters:
    - id={trackId} : Tidal track ID
    - quality={quality} : Quality level (HI_RES_LOSSLESS, LOSSLESS, HIGH, LOW)
    """
    track_id = str(track_id or request.args.get('id', '')).strip()
    quality = str(request.args.get('quality', 'LOW')).strip().upper()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    valid_qualities = {'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW'}
    if quality not in valid_qualities:
        return jsonify({'error': 'Invalid quality. Must be one of: ' + ', '.join(sorted(valid_qualities))}), 400

    try:
        result = get_hifi_track_object(
            track_id,
            include_streams=True,
            include_album=False,
            audio_quality=quality
        )

        track = result.get('track') if isinstance(result, dict) else None
        if not isinstance(track, dict):
            return jsonify({'error': 'Failed to build track object'}), 500

        streams = track.get('track_streams') if isinstance(track.get('track_streams'), dict) else {}
        stream_entry = streams.get(quality) or next(
            (entry for entry in streams.values() if isinstance(entry, dict) and isinstance(entry.get('url'), str) and entry.get('url')), None
        )

        if not stream_entry or not isinstance(stream_entry.get('url'), str):
            return jsonify({'error': 'No stream URL available for this track'}), 500

        stream_url = stream_entry.get('url')
        headers = {}
        if request.headers.get('Range'):
            headers['Range'] = request.headers.get('Range')

        upstream_response = requests.get(stream_url, headers=headers, stream=True, timeout=20)
        if upstream_response.status_code >= 400:
            return jsonify({
                'error': 'Failed to fetch upstream audio stream',
                'status_code': upstream_response.status_code,
                'details': upstream_response.reason
            }), upstream_response.status_code

        excluded_headers = {
            'content-encoding',
            'transfer-encoding',
            'connection',
            'keep-alive',
            'proxy-authenticate',
            'proxy-authorization',
            'te',
            'trailers',
            'upgrade'
        }

        response_headers = [
            (name, value)
            for name, value in upstream_response.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(
            stream_with_context(upstream_response.iter_content(chunk_size=65536)),
            status=upstream_response.status_code,
            headers=response_headers
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502
    except Exception as e:
        return jsonify({'error': 'Failed to stream track', 'details': str(e)}), 500

@app.route('/api/hifi/albums/<album_id>', methods=['GET'])
def album_object(album_id=None):
    """
    Get a normalized HiFi album object.
    Query parameters:
    - include_streams={bool} : include track manifest streams for each track (true/false)
    - audio_quality={quality}: Preferred audio quality
    """
    album_id = str(album_id or '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID path parameter is required'}), 400

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID path parameter must be a numeric Tidal album ID'}), 400

    include_streams = str(request.args.get('include_streams', 'false')).strip().lower() in ('1', 'true', 'yes')
    audio_quality = str(request.args.get('audio_quality', '')).strip() or None

    try:
        result = get_hifi_album_object(
            album_id,
            include_streams=include_streams,
            audio_quality=audio_quality
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build album object', 'details': str(e)}), 500

@app.route('/api/hifi/artists/<artist_id>', methods=['GET'])
def artist_info(artist_id=None):
    """
    Get a normalized HiFi artist object.
    Query parameters:
    - include_tracks={bool}  : include normalized top track objects (true/false)
    - include_albums={bool}  : include album objects (true/false)
    """
    artist_id = str(artist_id or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID path parameter is required'}), 400

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID parameter must be a numeric Tidal artist ID'}), 400

    include_tracks = str(request.args.get('include_tracks', 'true')).strip().lower() in ('1', 'true', 'yes')
    include_albums = str(request.args.get('include_albums', 'true')).strip().lower() in ('1', 'true', 'yes')

    try:
        result = get_hifi_artist_object(
            artist_id,
            include_tracks=include_tracks,
            include_albums=include_albums
        )
        if not result:
            return jsonify({'error': 'Failed to build artist object'}), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build artist object', 'details': str(e)}), 500

@app.route('/api/hifi/playlists/<playlist_id>', methods=['GET'])
def playlist_info(playlist_id=None):
    """
    Get playlist with all tracks.
    Query parameter:
    - id={playlistId} : Tidal playlist UUID
    """
    playlist_id = str(playlist_id or request.args.get('id', '')).strip()

    if not playlist_id:
        return jsonify({'error': 'Playlist ID parameter is required'}), 400

    params = {'id': playlist_id}
    limit = request.args.get('limit')
    offset = request.args.get('offset')
    if limit is not None:
        params['limit'] = limit
    if offset is not None:
        params['offset'] = offset

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/playlist/?{urlencode(params)}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )
        
        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code
        
        result = response.json()
        result['proxied_via'] = target['name']

        if isinstance(result, dict):
            data = result.get('data')
            if isinstance(data, dict):
                playlist_items = data.get('items')
                if isinstance(playlist_items, list):
                    data['items'] = _normalize_hifi_playlist_items(playlist_items)
                    result['data'] = data
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/hifi/tracks/<track_id>/manifest', methods=['GET'])
def track_download(track_id=None):
    """
    Get track download/streaming manifest.
    Query parameters:
    - id={trackId} : Tidal track ID
    - quality={quality} : Quality level (HI_RES_LOSSLESS, LOSSLESS, HIGH, LOW)
    """
    track_id = str(track_id or request.args.get('id', '')).strip()
    quality = request.args.get('quality', 'LOSSLESS')

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    valid_qualities = {'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW'}
    if quality not in valid_qualities:
        return jsonify({'error': 'Invalid quality. Must be one of: ' + ', '.join(sorted(valid_qualities))}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/track/?{urlencode({'id': track_id, 'quality': quality})}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )
        
        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code
        
        result = response.json()
        result['proxied_via'] = target['name']
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/hifi/tracks/<track_id>/similar', methods=['GET'])
def track_similar(track_id=None):
    """
    Get similar tracks for a track.
    Query parameter:
    - id={trackId} : Tidal track ID
    """
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    params = {'id': track_id}

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/recommendations/?{urlencode(params)}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']
        
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/hifi/artists/<artist_id>/similar', methods=['GET'])
def artist_similar(artist_id=None):
    """
    Get similar artists.
    Query parameters:
    - id={artistId} : Tidal artist ID
    - cursor={cursor} : Optional cursor for paginated results
    """
    artist_id = str(artist_id or request.args.get('id') or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID parameter must be a numeric Tidal artist ID'}), 400

    params = {'id': artist_id}
    cursor = request.args.get('cursor')
    if cursor is not None:
        params['cursor'] = cursor

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/artist/similar/?{urlencode(params)}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']

        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/hifi/albums/<album_id>/similar', methods=['GET'])
def album_similar(album_id=None):
    """
    Get similar albums.
    Query parameters:
    - id={albumId} : Tidal album ID
    - cursor={cursor} : Optional cursor for paginated results
    """
    album_id = str(album_id or request.args.get('id') or '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID parameter must be a numeric Tidal album ID'}), 400

    params = {'id': album_id}
    cursor = request.args.get('cursor')
    if cursor is not None:
        params['cursor'] = cursor

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/album/similar/?{urlencode(params)}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']

        albums = result.get('albums')
        if isinstance(albums, list):
            for album in albums:
                if isinstance(album, dict) and 'maxAudioQuality' not in album:
                    album['maxAudioQuality'] = _derive_audio_quality_from_tags(album)

        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/api/lastfm/playlist', methods=['POST'])
def lastfm_playlist():
    """
    Scrape a Last.fm playlist and return the track list.
    Accepts JSON body with 'playlistUrl' field.
    Returns the playlist name and list of tracks to search for.
    """
    import re
    
    data = request.get_json()
    playlist_url = data.get('playlistUrl', '')
    
    if not playlist_url:
        return jsonify({'error': 'Playlist URL is required'}), 400
    
    try:
        # Fetch the playlist page
        response = requests.get(playlist_url, timeout=15)
        
        if not response.ok:
            return jsonify({
                'error': f'Failed to fetch playlist page: HTTP {response.status}'
            }), 500
        
        html = response.text
        
        # Extract playlist name
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        playlist_name = title_match.group(1).strip() if title_match else 'Last.fm Playlist'
        
        # Parse tracks from chartlist-row elements
        tracks = []
        seen_tracks = set()
        
        # Pattern to find chartlist-row tr elements with chartlist-name and chartlist-artist
        chartlist_pattern = re.compile(
            r'<tr[^>]*class="[^"]*chartlist-row[^"]*"[^>]*>[\s\S]*?'
            r'<td[^>]*class="[^"]*chartlist-name[^"]*"[^>]*>[\s\S]*?<a[^>]*>([^<]+)</a>[\s\S]*?'
            r'<td[^>]*class="[^"]*chartlist-artist[^"]*"[^>]*>[\s\S]*?<a[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        
        for match in chartlist_pattern.finditer(html):
            track_name = match.group(1).strip()
            artist_name = match.group(2).strip()
            
            track_key = f"{artist_name}|{track_name}"
            if track_key not in seen_tracks:
                seen_tracks.add(track_key)
                tracks.append({
                    'name': track_name,
                    'artist': artist_name
                })
        
        if len(tracks) == 0:
            return jsonify({
                'error': 'No tracks found. The playlist may be private, empty, or the page structure has changed.'
            }), 400
        
        # Return the scraped tracks without searching
        return jsonify({
            'playlistName': playlist_name,
            'trackCount': len(tracks),
            'tracks': tracks
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Failed to fetch Last.fm playlist',
            'details': str(e)
        }), 500
    except Exception as e:
        logger.info("Last.fm scraping error: %s", e)
        return jsonify({
            'error': 'Failed to process Last.fm playlist',
            'details': str(e)
        }), 500

@app.route('/api/youtube_music/playlist', methods=['POST'])
def youtube_music_playlist():
    """
    Parse a YouTube Music playlist and return track metadata.
    Accepts JSON body with 'playlistUrl' field.
    Returns the playlist name and list of tracks to search for.
    """
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


def _requested_download_format(file_format):
    normalized = str(file_format or '').strip().lower()
    if normalized in ('m4a', 'aac', 'mp4'):
        return 'm4a'
    if normalized == 'flac':
        return 'flac'
    return 'm4a'

def _matches_requested_format(file_format, candidate_format):
    normalized_request = _requested_download_format(file_format)
    normalized_candidate = str(candidate_format or '').strip().lower()

    if normalized_request == 'flac':
        return normalized_candidate == 'flac'

    return normalized_candidate in ('m4a', 'aac', 'mp4')


def _download_job_exists_in_plex(cur, result_payload, job_payload):
    if not isinstance(result_payload, dict):
        return False

    artist = str(result_payload.get('artist') or '').strip()
    title = str(result_payload.get('title') or '').strip()
    album = str(result_payload.get('album') or '').strip()

    if not artist or not title:
        return False

    requested_format = _requested_download_format(
        job_payload.get('format') if isinstance(job_payload, dict) else None
    )

    # print(f"[PLEX_EXISTS_CHECK] Checking: '{title}' by '{artist}' in format {requested_format}", flush=True)
    rows = _lookup_track_metadata(cur, title, artist, album)
    exists = any(_matches_requested_format(requested_format, row.get('format')) for row in rows)
    # print(f"[PLEX_EXISTS_CHECK] Result: exists={exists}, found {len(rows)} rows with matching format={requested_format}", flush=True)
    return exists

@app.route('/api/downloads', methods=['POST'])
def download_track():
    """
    Enqueue a download job with specified settings.
    Expects JSON body with:
    - trackId: integer
    - quality: 'LOSSLESS' | 'HIGH' | 'LOW'
    - fileNaming: string (template for filename, e.g. '{artist}/{album}/{track} - {title}.{ext}')
    - fileNamingAlbum: string (file naming template)
    """
    payload = request.get_json(silent=True) or {}
    track_id = payload.get('trackId')

    settings = get_download_settings()
    file_naming_album = settings.get('file_naming_album', DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'])

    file_naming = payload.get('fileNamingAlbum') or payload.get('fileNaming') or file_naming_album

    if not track_id:
        logger.info("[DOWNLOAD] ERROR: trackId is missing")
        return jsonify({'error': 'trackId is required'}), 400

    quality_choice = str(payload.get('downloadQuality', payload.get('quality', 'LOSSLESS'))).strip().upper()
    if quality_choice not in ('LOSSLESS', 'HIGH', 'LOW'):
        quality_choice = 'LOSSLESS'

    ignore_matches = payload.get('ignore_matches')
    if ignore_matches is None:
        ignore_matches = settings.get('ignore_matches', DEFAULT_DOWNLOAD_SETTINGS.get('ignore_matches', False))
    ignore_matches = bool(ignore_matches)

    plex_playlist = payload.get('plex_playlist')
    plex_user_id = payload.get('plex_user_id')

    logger.info(
        "[DOWNLOAD_ENQUEUE] track_id=%s quality=%s playlist=%s user_id=%s ignore_matches=%s",
        track_id, quality_choice, plex_playlist, plex_user_id, ignore_matches
    )

    artist_name = None
    title_name = None
    try:
        track_obj = get_hifi_track_object(track_id, include_streams=False, include_album=False, audio_quality=quality_choice)
        track_data = track_obj.get('track') if isinstance(track_obj, dict) else {}
        if isinstance(track_data, dict):
            title_name = track_data.get('title')
            artists = track_data.get('artists')
            if isinstance(artists, list) and artists:
                names = [str(a.get('name', '')).strip() for a in artists if isinstance(a, dict) and a.get('name')]
                artist_name = '; '.join(names) if names else None
            elif isinstance(artists, dict) and artists.get('name'):
                artist_name = str(artists.get('name')).strip()
    except Exception as e:
        logger.info("[DOWNLOAD] Failed to prefetch track metadata for job payload: %s", e)

    job_payload = {
        'trackId': track_id,
        'fileNaming': file_naming,
        'fileNamingAlbum': payload.get('fileNamingAlbum') or file_naming_album,
        'plex_playlist': plex_playlist,
        'plex_user_id': plex_user_id,
        'ignore_matches': ignore_matches,
        'downloadQuality': quality_choice,
    }

    if artist_name:
        job_payload['artist'] = artist_name
    if title_name:
        job_payload['title'] = title_name

    job_id = jobs.enqueue_job('download_track', job_payload)
    set_last_download_activity_at(datetime.utcnow())

    logger.info("[DOWNLOAD_ENQUEUE] Queued download job %s for track %s", job_id, track_id)

    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List jobs with optional filters.
    Query parameters:
    - status: filter by raw job status
    - job_type: filter by job type
    - jobs_filter: one of incomplete|complete|failed
    - exclude_bulk_playlist_add: default false
    - limit: optional max number of rows (no backend-enforced maximum)
    - offset: pagination offset (default 0)
    """
    status_filter = request.args.get('status')
    job_type_filter = request.args.get('job_type')
    jobs_filter = request.args.get('jobs_filter')
    exclude_bulk_playlist_add = request.args.get('exclude_bulk_playlist_add', '0').lower() in ('1', 'true', 'yes')

    limit = None
    limit_raw = request.args.get('limit')
    if limit_raw is not None:
        try:
            parsed_limit = int(limit_raw)
            if parsed_limit >= 1:
                limit = parsed_limit
        except ValueError:
            limit = None

    try:
        offset = int(request.args.get('offset', '0'))
    except ValueError:
        offset = 0
    offset = max(0, offset)

    where_clauses = []
    params = []
    if status_filter:
        where_clauses.append('status = %s')
        params.append(status_filter)
    if job_type_filter:
        where_clauses.append('job_type = %s')
        params.append(job_type_filter)
    if exclude_bulk_playlist_add:
        where_clauses.append('job_type <> %s')
        params.append('bulk_playlist_add')

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT id, job_type, status, payload_json, result_json, error_message,
               attempt_count, max_attempts, created_at, updated_at, run_after,
               locked_at, locked_by, started_at, finished_at, priority
        FROM jobs
        {where_sql}
        ORDER BY created_at DESC
        """,
        tuple(params)
    )
    rows = cur.fetchall() or []

    if jobs_filter:
        def matches_jobs_filter(row):
            effective_status = _effective_job_status(
                row.get('job_type'),
                row.get('status'),
                row.get('result_json')
            )

            if jobs_filter == 'failed':
                return effective_status == 'failed'
            if jobs_filter == 'complete':
                return effective_status == 'succeeded'
            if jobs_filter == 'incomplete':
                return effective_status in ('queued', 'in_progress')
            return True

        rows = [row for row in rows if matches_jobs_filter(row)]

    if jobs_filter == 'complete':
        rows.sort(
            key=lambda row: (
                row.get('finished_at') is not None,
                row.get('finished_at') or row.get('created_at')
            ),
            reverse=True
        )

    total_count = len(rows)
    if limit is None:
        paged_rows = rows[offset:]
    else:
        paged_rows = rows[offset:offset + limit]
    conn.close()

    jobs = []
    for row in paged_rows:
        try:
            payload = json.loads(row['payload_json'])
        except (TypeError, ValueError):
            payload = None
        try:
            result = json.loads(row['result_json']) if row['result_json'] else None
        except (TypeError, ValueError):
            result = None

        jobs.append({
            'id': row['id'],
            'job_type': row['job_type'],
            'status': row['status'],
            'payload': payload,
            'result': result,
            'error_message': row['error_message'],
            'attempt_count': row['attempt_count'],
            'max_attempts': row['max_attempts'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'run_after': row['run_after'],
            'locked_at': row['locked_at'],
            'locked_by': row['locked_by'],
            'started_at': row['started_at'],
            'finished_at': row['finished_at'],
            'priority': row['priority']
        })

    totals = get_jobs_filter_totals(exclude_bulk_playlist_add=exclude_bulk_playlist_add)
    return jsonify({'jobs': jobs, 'totals': totals, 'total_count': total_count})

def _effective_job_status(job_type, status, result_json):
    if job_type != 'download_track':
        return status

    try:
        result = json.loads(result_json) if result_json else {}
    except (TypeError, ValueError):
        result = {}

    stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}

    if stages.get('written') == 'failed':
        return 'failed'

    return status

def get_jobs_filter_totals(exclude_bulk_playlist_add=False):
    where_sql = 'WHERE job_type <> %s' if exclude_bulk_playlist_add else ''
    params = ('bulk_playlist_add',) if exclude_bulk_playlist_add else ()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT job_type, status, result_json
        FROM jobs
        {where_sql}
        """,
        params
    )
    rows = cur.fetchall() or []
    conn.close()

    totals = {
        'incomplete': 0,
        'complete': 0,
        'failed': 0
    }

    for row in rows:
        effective_status = _effective_job_status(
            row.get('job_type'),
            row.get('status'),
            row.get('result_json')
        )

        if effective_status in ('queued', 'in_progress'):
            totals['incomplete'] += 1
        elif effective_status == 'succeeded':
            totals['complete'] += 1
        elif effective_status == 'failed':
            totals['failed'] += 1

    return totals

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get job by id."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, job_type, status, payload_json, result_json, error_message,
               attempt_count, max_attempts, created_at, updated_at, run_after,
               locked_at, locked_by, started_at, finished_at, priority
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': 'Job not found'}), 404

    try:
        payload = json.loads(row['payload_json'])
    except (TypeError, ValueError):
        payload = None
    try:
        result = json.loads(row['result_json']) if row['result_json'] else None
    except (TypeError, ValueError):
        result = None

    return jsonify({
        'id': row['id'],
        'job_type': row['job_type'],
        'status': row['status'],
        'payload': payload,
        'result': result,
        'error_message': row['error_message'],
        'attempt_count': row['attempt_count'],
        'max_attempts': row['max_attempts'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'run_after': row['run_after'],
        'locked_at': row['locked_at'],
        'locked_by': row['locked_by'],
        'started_at': row['started_at'],
        'finished_at': row['finished_at'],
        'priority': row['priority']
    })

@app.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a queued or in-progress job."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT status
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': 'Job not found'}), 404

    if row['status'] not in ('queued', 'in_progress'):
        return jsonify({'error': f"Job is not cancellable (status={row['status']})"}), 400

    jobs.mark_job_cancelled(job_id)
    return jsonify({'success': True, 'job_id': job_id, 'status': 'cancelled'})

@app.route('/api/jobs/cancel-pending', methods=['POST'])
def cancel_all_pending_jobs():
    """Delete user-visible incomplete jobs from the queue/table."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, job_type, status, result_json
        FROM jobs
        """
    )
    rows = cur.fetchall() or []

    delete_ids = []
    for row in rows:
        status = row.get('status')
        job_type = row.get('job_type')

        if job_type == 'bulk_playlist_add':
            continue

        if status in ('queued', 'in_progress'):
            delete_ids.append(row['id'])
            continue

        if job_type != 'download_track' or status != 'succeeded':
            continue

        try:
            result = json.loads(row['result_json']) if row.get('result_json') else {}
        except (TypeError, ValueError):
            result = {}

        stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}
        if stages.get('playlist_added') == 'queued':
            delete_ids.append(row['id'])

    if not delete_ids:
        conn.close()
        return jsonify({'success': True, 'deleted_count': 0})

    placeholders = ','.join(['%s'] * len(delete_ids))
    cur.execute(
        f"DELETE FROM jobs WHERE id IN ({placeholders})",
        tuple(delete_ids)
    )
    deleted_count = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'deleted_count': deleted_count})

@app.route('/api/jobs/cancel-failed', methods=['POST'])
def cancel_failed_jobs():
    """Cancel all failed jobs?"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status = 'cancelled',
            updated_at = %s,
            finished_at = %s
        WHERE status = 'failed'
        """,
        (datetime.utcnow().isoformat() + 'Z', datetime.utcnow().isoformat() + 'Z')
    )
    cancelled_count = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'cancelled_count': cancelled_count})

@app.route('/api/jobs/<int:job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """Retry an existing failed/completed-with-errors job by re-queueing it."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT job_type, status, result_json, payload_json
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()

    if row is None:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404

    effective_status = _effective_job_status(row['job_type'], row['status'], row.get('result_json'))
    retryable = effective_status == 'failed'

    if not retryable:
        conn.close()
        return jsonify({'error': f"Job is not retryable (status={row['status']}, effective_status={effective_status})"}), 400

    # For download_track jobs, check if the track already exists in Plex
    if row['job_type'] == 'download_track':
        try:
            result = json.loads(row['result_json']) if row['result_json'] else {}
        except (TypeError, ValueError):
            result = {}

        try:
            payload = json.loads(row['payload_json']) if row.get('payload_json') else {}
        except (TypeError, ValueError):
            payload = {}

        playlist_name = ''
        if isinstance(payload, dict):
            playlist_name = str(payload.get('plex_playlist') or '').strip()
        if not playlist_name and isinstance(result, dict):
            playlist_name = str(result.get('playlist_name') or '').strip()

        if not playlist_name and _download_job_exists_in_plex(cur, result, payload):
            conn.close()
            return jsonify({
                'error': 'Track already exists in Plex for the selected format. Retry skipped.',
                'job_id': job_id,
                'status': 'already_exists_in_plex'
            }), 409

    cur.execute(
        """
        UPDATE jobs
        SET status = 'queued',
            attempt_count = 0,
            result_json = NULL,
            error_message = NULL,
            updated_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL,
            started_at = NULL,
            finished_at = NULL
        WHERE id = %s
        """,
        (now, now, job_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'})

@app.route('/api/app/config', methods=['GET'])
def app_config():
    from squidly.config import app_timezone
    return jsonify({'timezone': app_timezone})

@app.route('/api/settings', methods=['GET', 'POST'])
def download_settings():
    """Get or update download settings stored in SQLite."""
    if request.method == 'GET':
        return jsonify(get_download_settings())

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
        'penalty_compilation', 'penalty_karaoke', 'penalty_live',
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

@app.route('/api/endpoints/status', methods=['GET'])
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


def _async_validate_endpoints():
    """Run endpoint validation in a background thread."""
    _run_async(lambda: downloads.validate_all_endpoints_from_db())


def _run_async(fn):
    """Run a callable in a background daemon thread."""
    def _wrapper():
        try:
            fn()
        except Exception as e:
            logger.info("[ENDPOINTS] Async operation failed: %s", e)
    threading.Thread(target=_wrapper, daemon=True).start()


@app.route('/api/endpoints', methods=['POST'])
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

    _run_async(lambda: downloads.validate_all_endpoints_from_db())

    return jsonify({'url': url, 'added': True, 'mirrorType': mirror_type}), 201


@app.route('/api/endpoints/<name>', methods=['DELETE'])
def delete_endpoint(name):
    """Remove a mirror endpoint."""
    try:
        downloads.remove_mirror(name)
    except Exception as e:
        logger.info("[ENDPOINTS] Failed to remove mirror: %s", e)
        return jsonify({'error': str(e)}), 500

    _run_async(lambda: downloads.validate_all_endpoints_from_db())

    return jsonify({'name': name, 'removed': True}), 200


@app.route('/api/endpoints/<name>/toggle', methods=['POST'])
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


@app.route('/api/endpoints/<name>/toggle-download', methods=['POST'])
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


@app.route('/api/listenbrainz/config', methods=['GET'])
def get_listenbrainz_config_endpoint():
    """Get the current ListenBrainz configuration"""
    user_id = request.args.get('user_id')
    config = get_listenbrainz_config(user_id)
    return jsonify({
        'has_token': config['user_token'] is not None,
        'username': config.get('username')
    })

@app.route('/api/listenbrainz/config', methods=['POST'])
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


@app.route('/api/fresh-finds/auto-download', methods=['GET'])
def get_fresh_finds_auto_download_config():
    """Get the Fresh Finds auto-download setting for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import get_all_plex_account_mappings
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


@app.route('/api/fresh-finds/auto-download', methods=['POST'])
def save_fresh_finds_auto_download_config():
    """Set the Fresh Finds auto-download toggle for a specific user."""
    payload = request.get_json(silent=True) or {}

    user_id = payload.get('user_id')
    enabled = payload.get('enabled', False)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import set_fresh_finds_auto_download
    set_fresh_finds_auto_download(user_id, enabled)
    return jsonify({'success': True, 'enabled': bool(enabled)})


@app.route('/api/fresh-finds/retention', methods=['GET'])
def get_fresh_finds_retention():
    """Get the Fresh Finds retention count setting for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import get_fresh_finds_retention_count
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


@app.route('/api/fresh-finds/retention', methods=['POST'])
def save_fresh_finds_retention():
    """Set the Fresh Finds retention count for a specific user. Clamps to [1, 100]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    count = payload.get('count', 10)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import set_fresh_finds_retention_count
    set_fresh_finds_retention_count(user_id, count)
    return jsonify({'success': True, 'count': max(1, min(100, int(count)))})


@app.route('/api/fresh-finds/new-track-pct', methods=['GET'])
def get_fresh_finds_new_track_pct_route():
    """Get the Fresh Finds new-track percentage for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import get_fresh_finds_new_track_pct
    from squidly.storage import get_all_plex_account_mappings
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


@app.route('/api/fresh-finds/new-track-pct', methods=['POST'])
def save_fresh_finds_new_track_pct_route():
    """Set the Fresh Finds new-track percentage for a specific user. Clamps to [0, 100]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    pct = payload.get('pct', 50)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import set_fresh_finds_new_track_pct
    set_fresh_finds_new_track_pct(user_id, pct)
    return jsonify({'success': True, 'pct': max(0, min(100, int(pct)))})


@app.route('/api/fresh-finds/track-count', methods=['GET'])
def get_fresh_finds_track_count_route():
    """Get the Fresh Finds track count for a specific user."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import get_fresh_finds_track_count
    from squidly.storage import get_all_plex_account_mappings
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


@app.route('/api/fresh-finds/track-count', methods=['POST'])
def save_fresh_finds_track_count_route():
    """Set the Fresh Finds track count for a specific user. Clamps to [5, 100]."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id')
    count = payload.get('count', 25)

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    from squidly.storage import set_fresh_finds_track_count
    set_fresh_finds_track_count(user_id, count)
    return jsonify({'success': True, 'count': max(5, min(100, int(count)))})


@app.route('/api/listenbrainz/playlists', methods=['GET'])
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

@app.route('/api/listenbrainz/playlist/<playlist_mbid>', methods=['GET'])
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

@app.route('/api/listenbrainz/match', methods=['POST'])
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

    def normalize(s):
        return re.sub(r'[^a-z0-9]+', '', s.lower().strip())

    def score_candidate(item):
        score = 0.0
        item_title = normalize(item.get('title') or '')
        item_artist = normalize((item.get('artist') or {}).get('name') or '')
        item_album = normalize((item.get('album') or {}).get('title') or '')
        norm_title = normalize(title)
        norm_artist = normalize(artist)
        norm_album = normalize(album)

        if item_title and norm_title:
            if item_title == norm_title:
                score += 0.50
            elif norm_title in item_title or item_title in norm_title:
                score += 0.30

        if item_artist and norm_artist:
            if item_artist == norm_artist:
                score += 0.30
            elif norm_artist in item_artist or item_artist in norm_artist:
                score += 0.15

        if norm_album and item_album:
            if item_album == norm_album:
                score += 0.20
            elif norm_album in item_album or item_album in norm_album:
                score += 0.10

        score -= compute_playlist_match_penalty(item, settings)
        return score

    isrcs = []
    mbid_match = re.search(r'recording/([a-f0-9-]+)', identifier, re.IGNORECASE)

    if mbid_match:
        mbid = mbid_match.group(1)
        try:
            mb_url = f'https://musicbrainz.org/ws/2/recording/{mbid}?inc=isrcs&fmt=json'
            mb_resp = requests.get(
                mb_url,
                timeout=10,
                headers={'User-Agent': 'Squidly/1.0 (https://github.com/brendan/squidly)'}
            )
            if mb_resp.ok:
                mb_data = mb_resp.json()
                isrcs = mb_data.get('isrcs') or []
        except requests.exceptions.RequestException:
            pass

    def search_hifi(search_type, search_query, limit=25):
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/search/?{urlencode({search_type: search_query, 'limit': str(limit)})}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )
        if not response.ok:
            return []
        result = response.json()
        return result.get('data', {}).get('items') or []

    try:
        best_match = None
        best_score = 0.0
        method = None

        if isrcs:
            seen_ids = set()
            all_items = []
            for isrc in isrcs:
                items = search_hifi('i', isrc, limit=50)
                for item in items:
                    item_id = item.get('id')
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        all_items.append(item)
            for item in all_items:
                s = score_candidate(item)
                if s > best_score:
                    best_score = s
                    best_match = item
            if best_match:
                method = 'isrc'

        if not best_match:
            parts = [artist]
            if album:
                parts.append(album)
            parts.append(title)
            items = search_hifi('s', ' '.join(parts), limit=5)
            for item in items:
                s = score_candidate(item)
                if s > best_score:
                    best_score = s
                    best_match = item
            if best_match and not method:
                method = 'text'

        if best_match and best_score >= 0.50:
            return jsonify({
                'match': best_match,
                'method': method,
                'confidence': min(best_score, 1.0)
            })

        return jsonify({'match': None, 'method': None, 'confidence': 0.0})

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502


def _get_ytmusic(user_id):
    """Load YTM headers from DB and return an authenticated YTMusic instance."""
    from ytmusicapi import YTMusic
    import hashlib
    import time
    from http.cookies import SimpleCookie

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


@app.route('/api/youtube_music/config', methods=['GET'])
def get_ytm_config_endpoint():
    """Check if YouTube Music is configured for the user."""
    user_id = request.args.get('user_id')
    config = get_ytm_config(user_id)
    return jsonify(config)


@app.route('/api/youtube_music/config', methods=['POST'])
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


@app.route('/api/youtube_music/playlists', methods=['GET'])
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


@app.route('/api/youtube_music/playlist/<playlist_id>', methods=['GET'])
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


@app.route('/api/youtube_music/match', methods=['POST'])
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

    def normalize(s):
        return re.sub(r'[^a-z0-9]+', '', s.lower().strip())

    def score_candidate(item):
        score = 0.0
        item_title = normalize(item.get('title') or '')
        item_artist = normalize((item.get('artist') or {}).get('name') or '')
        item_album = normalize((item.get('album') or {}).get('title') or '')
        norm_title = normalize(title)
        norm_artist = normalize(artist)
        norm_album = normalize(album)

        if item_title and norm_title:
            if item_title == norm_title:
                score += 0.50
            elif norm_title in item_title or item_title in norm_title:
                score += 0.30

        if item_artist and norm_artist:
            if item_artist == norm_artist:
                score += 0.30
            elif norm_artist in item_artist or item_artist in norm_artist:
                score += 0.15

        if norm_album and item_album:
            if item_album == norm_album:
                score += 0.20
            elif norm_album in item_album or item_album in norm_album:
                score += 0.10

        score -= compute_playlist_match_penalty(item, settings)
        return score

    def search_hifi(search_type, search_query, limit=25):
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/search/?{urlencode({search_type: search_query, 'limit': str(limit)})}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3,
        )
        if not response.ok:
            return []
        result = response.json()
        return result.get('data', {}).get('items') or []

    try:
        best_match = None
        best_score = 0.0

        parts = [artist]
        if album:
            parts.append(album)
        parts.append(title)
        items = search_hifi('s', ' '.join(parts), limit=5)
        for item in items:
            s = score_candidate(item)
            if s > best_score:
                best_score = s
                best_match = item

        if best_match and best_score >= 0.50:
            return jsonify({
                'match': best_match,
                'confidence': min(best_score, 1.0)
            })

        return jsonify({'match': None, 'confidence': 0.0})

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502


@app.route('/api/plex/config', methods=['GET'])
def get_plex_config_endpoint():
    """Get the current Plex configuration"""
    config = get_plex_config()
    return jsonify({
        'has_config': config['server_url'] is not None and config['api_token'] is not None,
        'server_url': config['server_url'],
        'library_name': config['library_name'],
        'sync_interval_hours': config.get('sync_interval_hours', 24)
    })

@app.route('/api/plex/config', methods=['POST'])
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

@app.route('/api/plex/syncs', methods=['POST'])
def start_plex_sync_endpoint():
    """Queue a manual Plex library update and sync job."""
    result = start_plex_library_update_job(trigger='manual')
    if not result.get('ok'):
        status_code = result.get('status_code', 500)
        return jsonify({'error': result.get('error')}), int(status_code)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202

@app.route('/api/plex/library-updates', methods=['POST'])
def start_plex_library_update_endpoint():
    """Queue a manual Plex library update and sync job."""
    result = start_plex_library_update_job(trigger='manual')
    if not result.get('ok'):
        status_code = result.get('status_code', 500)
        return jsonify({'error': result.get('error')}), int(status_code)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202


@app.route('/api/hifi/matches', methods=['POST'])
def start_hifi_match_endpoint():
    """Queue a Plex library update, which chains to sync → automatic matching."""
    result = start_plex_library_update_job(trigger='manual')
    if not result.get('ok'):
        status_code = result.get('status_code', 500)
        return jsonify({'error': result.get('error')}), int(status_code)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202





@app.route('/api/hifi/matches/lookup', methods=['POST'])
def lookup_hifi_matches_endpoint():
    payload = request.get_json(silent=True) or {}
    track_ids = payload.get('track_ids') or []
    album_ids = payload.get('album_ids') or []
    artist_ids = payload.get('artist_ids') or []

    if not isinstance(track_ids, list) or not isinstance(album_ids, list) or not isinstance(artist_ids, list):
        return jsonify({'error': 'track_ids, album_ids, and artist_ids must be arrays'}), 400

    if len(track_ids) > 200 or len(album_ids) > 200 or len(artist_ids) > 200:
        return jsonify({'error': 'track_ids, album_ids, and artist_ids are limited to 200 items each'}), 400

    normalized_track_ids = [str(item).strip() for item in track_ids if str(item).strip()]
    normalized_album_ids = [str(item).strip() for item in album_ids if str(item).strip()]
    normalized_artist_ids = [str(item).strip() for item in artist_ids if str(item).strip()]

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return jsonify({
            'success': True,
            'tracks': _build_stored_track_match_lookup(cur, normalized_track_ids),
            'albums': _build_stored_album_match_lookup(cur, normalized_album_ids),
            'artists': _build_stored_artist_match_lookup(cur, normalized_artist_ids),
        })
    finally:
        conn.close()


@app.route('/api/hifi/matches/review', methods=['GET'])
def get_hifi_match_review_endpoint():
    entity_type = str(request.args.get('entity_type') or 'all').strip().lower()
    limit = _safe_int(request.args.get('limit')) or 50
    limit = max(1, min(limit, 200))
    max_confidence = _safe_float(request.args.get('max_confidence'), default=0.94)

    include_artists = entity_type in ('all', 'artist', 'artists')
    include_albums = entity_type in ('all', 'album', 'albums')
    include_tracks = entity_type in ('all', 'track', 'tracks')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        response = {
            'success': True,
            'summary': {
                'artists': 0,
                'albums': 0,
                'tracks': 0,
            }
        }
        server_url, api_token, library = _get_match_review_plex_context()

        if include_artists:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM artists
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['artists'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
                FROM artists
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                ORDER BY confidence ASC, artist_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            artists = cur.fetchall() or []
            artist_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in artists],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in artists:
                item['picture'] = artist_image_map.get(str(item.get('library_id') or '').strip())
            response['artists'] = artists

        if include_albums:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM albums
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['albums'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT albums.album_id, albums.artist_id, albums.title, albums.library_id, albums.hifi_id,
                       albums.confidence, albums.complete, albums.matched_track_count,
                       albums.expected_track_count, albums.last_seen_at,
                       artists.name AS artist_name
                FROM albums
                LEFT JOIN artists ON artists.artist_id = albums.artist_id
                WHERE albums.library_id IS NOT NULL
                  AND (albums.hifi_id IS NULL OR albums.confidence < %s)
                ORDER BY albums.confidence ASC, albums.album_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            albums = cur.fetchall() or []
            album_track_titles_map = _fetch_source_album_track_titles_map(cur, [item.get('album_id') for item in albums])
            album_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in albums],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in albums:
                item['track_titles'] = album_track_titles_map.get(int(item.get('album_id')), []) if item.get('album_id') is not None else []
                item['cover'] = album_image_map.get(str(item.get('library_id') or '').strip())
            response['albums'] = albums

        if include_tracks:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM tracks
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['tracks'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT tracks.track_id, tracks.album_id, tracks.artist_id, tracks.title, tracks.library_id,
                       tracks.hifi_id, tracks.confidence, tracks.path, tracks.format, tracks.bitrate,
                       tracks.disc_number, tracks.track_number, tracks.last_seen_at, tracks.isrc, tracks.duration,
                       albums.title AS album_title,
                       albums.library_id AS album_library_id,
                       artists.name AS artist_name,
                       artists.library_id AS artist_library_id
                FROM tracks
                LEFT JOIN albums ON albums.album_id = tracks.album_id
                LEFT JOIN artists ON artists.artist_id = tracks.artist_id
                WHERE tracks.library_id IS NOT NULL
                  AND (tracks.hifi_id IS NULL OR tracks.confidence < %s)
                ORDER BY tracks.confidence ASC, tracks.track_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            tracks = cur.fetchall() or []
            track_album_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('album_library_id') for item in tracks],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            track_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in tracks],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in tracks:
                album_library_id = str(item.get('album_library_id') or '').strip()
                track_library_id = str(item.get('library_id') or '').strip()
                item['cover'] = track_album_image_map.get(album_library_id) or track_image_map.get(track_library_id)
            response['tracks'] = tracks

        return jsonify(response)
    finally:
        conn.close()


@app.route('/api/hifi/matches/candidates', methods=['GET'])
def get_hifi_match_candidates_endpoint():
    entity_type = str(request.args.get('entity_type') or '').strip().lower()
    entity_id = _safe_int(request.args.get('id'))
    limit = _safe_int(request.args.get('limit')) or 3
    limit = max(1, min(limit, 20))
    query_override = str(request.args.get('query') or '').strip() or None

    if entity_type not in ('artist', 'album', 'track'):
        return jsonify({'error': 'entity_type must be one of artist, album, or track'}), 400
    if not entity_id:
        return jsonify({'error': 'id is required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = _fetch_match_review_row(cur, entity_type, entity_id)
        if not row:
            return jsonify({'error': f'{entity_type} not found'}), 404

        if entity_type == 'artist':
            candidates = _build_artist_match_candidates(row, limit=limit, query_override=query_override)
        elif entity_type == 'album':
            source_track_titles_map = _fetch_source_album_track_titles_map(cur, [row.get('album_id')])
            source_track_titles = source_track_titles_map.get(int(row.get('album_id')), []) if row.get('album_id') is not None else []
            candidates = _build_album_match_candidates(row, limit=limit, query_override=query_override, source_track_titles=source_track_titles)
            if not candidates and not query_override:
                album_title = str(row.get('title') or '').strip()
                artist_name = str(row.get('artist_name') or '').strip()
                stripped_title = re.sub(r'\s*\([^)]*\)', '', album_title).strip()

                fallback_queries = []
                for value in (
                    artist_name,
                    stripped_title,
                    f"{artist_name} {stripped_title}".strip() if artist_name and stripped_title else '',
                    f"{artist_name} {album_title}".strip() if artist_name and album_title else '',
                ):
                    query = str(value or '').strip()
                    if query and query not in fallback_queries:
                        fallback_queries.append(query)

                merged = []
                seen_hifi_ids = set()
                for fallback_query in fallback_queries:
                    fallback_candidates = _build_album_match_candidates(
                        row,
                        limit=limit,
                        query_override=fallback_query,
                        source_track_titles=source_track_titles,
                    )
                    for candidate in fallback_candidates:
                        hifi_id = str(candidate.get('hifi_id') or '').strip()
                        if not hifi_id or hifi_id in seen_hifi_ids:
                            continue
                        seen_hifi_ids.add(hifi_id)
                        merged.append(candidate)
                    if len(merged) >= limit:
                        break

                if merged:
                    merged.sort(key=lambda candidate: (-_safe_float(candidate.get('confidence')), str(candidate.get('title') or '').lower()))
                    candidates = merged[:limit]
        else:
            candidates = _build_track_match_candidates(row, limit=limit, query_override=query_override)

        return jsonify({'success': True, 'candidates': candidates})
    finally:
        conn.close()


@app.route('/api/hifi/matches/review', methods=['POST'])
def update_hifi_match_review_endpoint():
    payload = request.get_json(silent=True) or {}
    entity_type = str(payload.get('entity_type') or '').strip().lower()
    action = str(payload.get('action') or '').strip().lower()
    raw_hifi_id = str(payload.get('hifi_id') or '').strip() or None
    entity_id = _safe_int(payload.get('id'))

    if entity_type not in ('artist', 'album', 'track'):
        return jsonify({'error': 'entity_type must be one of artist, album, or track'}), 400
    if action not in ('confirm', 'reject'):
        return jsonify({'error': 'action must be confirm or reject'}), 400
    if not entity_id:
        return jsonify({'error': 'id is required'}), 400

    if is_job_type_running_or_queued('hifi_match'):
        return jsonify({'error': 'Manual matching is disabled while Hifi Match is running. Please wait for the current scan to finish.'}), 409

    table_name = {'artist': 'artists', 'album': 'albums', 'track': 'tracks'}[entity_type]
    id_column = {'artist': 'artist_id', 'album': 'album_id', 'track': 'track_id'}[entity_type]
    now_dt = _now_utc()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT * FROM {table_name} WHERE {id_column} = %s",
            (entity_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'error': f'{entity_type} not found'}), 404

        if action == 'confirm':
            effective_hifi_id = raw_hifi_id or (str(row.get('hifi_id') or '').strip() or None)
            if not effective_hifi_id:
                return jsonify({'error': 'hifi_id is required to confirm an unmatched row'}), 400
            if entity_type == 'track':
                updated_track_album_id = _cascade_track_confirm_ids(cur, row, effective_hifi_id, now_dt)
            else:
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = %s,
                        confidence = 1.0
                    WHERE {id_column} = %s
                    """,
                    (effective_hifi_id, entity_id)
                )
        else:
            if entity_type == 'album':
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = NULL,
                        confidence = 0,
                        complete = FALSE,
                        matched_track_count = 0,
                        expected_track_count = 0
                    WHERE {id_column} = %s
                    """,
                    (entity_id,)
                )
            else:
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = NULL,
                        confidence = 0
                    WHERE {id_column} = %s
                    """,
                    (entity_id,)
                )

        if entity_type == 'album':
            album_row = _get_album_row(cur, entity_id)
            if album_row:
                _refresh_album_completeness(cur, album_row)
        elif entity_type == 'track':
            album_id = updated_track_album_id or row.get('album_id')
            if album_id:
                album_row = _get_album_row(cur, album_id)
                if album_row:
                    _refresh_album_completeness(cur, album_row)

        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()

@app.route('/api/plex/connection-tests', methods=['POST'])
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

@app.route('/api/plex/playlists', methods=['GET'])
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

@app.route('/api/plex/playlist/tracks', methods=['GET'])
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
        from plexapi.server import PlexServer

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

@app.route('/api/plex/playlists', methods=['POST'])
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
        from plexapi.server import PlexServer
        
        plex = PlexServer(server_url, api_token)
        
        # Switch to the specified user if provided
        if user_id:
            try:
                plex = plex.switchUser(user_id)
                logger.info("[PLEX] Switched to user %s for playlist creation", user_id)
            except Exception as e:
                logger.info("[PLEX] Failed to switch user: %s", str(e))
                return jsonify({'error': f'Failed to switch user: {str(e)}'}), 400

        # Check if playlist already exists
        logger.info("[PLEX] Checking if playlist exists: %s", playlist_name)
        try:
            playlists = plex.playlists()
            for pl in playlists:
                if pl.title == playlist_name:
                    logger.info("[PLEX] Playlist already exists: %s", playlist_name)
                    return jsonify({'success': True, 'playlist_name': playlist_name, 'already_exists': True})
        except Exception as e:
            logger.info("[PLEX] Error checking playlists: %s", str(e))

        # Playlist doesn't exist yet - that's fine, we'll create it on first track add
        logger.info("[PLEX] Playlist will be created on first track add: %s", playlist_name)
        return jsonify({'success': True, 'playlist_name': playlist_name})
    except Exception as e:
        logger.info("[PLEX] Error validating playlist: %s", str(e))
        return jsonify({'error': f'Failed to validate playlist: {str(e)}'}), 500

@app.route('/api/plex/libraries', methods=['GET'])
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


@app.route('/api/plex/library', methods=['GET'])
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


@app.route('/api/plex/library/artists', methods=['GET'])
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


@app.route('/api/plex/library/artists/<artist_id>/albums', methods=['GET'])
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


@app.route('/api/plex/library/albums/<album_id>/tracks', methods=['GET'])
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


@app.route('/api/plex/library/tracks/<track_id>/stream', methods=['GET'])
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

@app.route('/api/plex/songs/match', methods=['POST'])
def match_plex_songs_endpoint():
    """Match candidate tracks against locally synced Plex inventory."""
    payload = request.get_json(silent=True) or {}
    tracks = payload.get('tracks')

    if not isinstance(tracks, list):
        return jsonify({'error': 'tracks array is required'}), 400

    if len(tracks) > 200:
        return jsonify({'error': 'tracks array too large (max 200)'}), 400
    
    # print(f"[PLEX_MATCH_ENDPOINT] Matching {len(tracks)} tracks", flush=True)

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

        # print(f"[PLEX_MATCH_ENDPOINT] Track {idx}: '{title}' by '{artist}' from '{album}'", flush=True)
        
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
                'file_path': str(row.get('file_path') or '').strip() or None
            })

        exists = len(rows) > 0
        # print(f"[PLEX_MATCH_ENDPOINT] Track {idx} result: exists={exists}, variants={len(variants)}", flush=True)
        
        matches.append({
            'exists': exists,
            'variants': variants
        })

    conn.close()
    return jsonify({'matches': matches})


# --- Listen History ---

def process_plex_listen_history_sync(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured')

    stages = {
        'resolving_accounts': 'pending',
        'fetching_history': 'pending',
        'storing_entries': 'pending'
    }
    progress = {
        'users_processed': 0,
        'total_users': 0,
        'entries_fetched': 0,
        'entries_stored': 0
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)

    accounts = plex.systemAccounts() or []
    account_name_to_id = {}
    for acc in accounts:
        name = str(getattr(acc, 'name', '') or '').strip()
        acc_id = getattr(acc, 'id', None)
        if name and acc_id is not None:
            account_name_to_id[name] = int(acc_id)

    user_mappings = get_all_plex_account_mappings()
    progress['total_users'] = len(user_mappings)
    jobs.update_job_progress(job_id, {'progress': progress})

    stages['resolving_accounts'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    resolved_users = []
    for mapping in user_mappings:
        username = str(mapping.get('username') or '').strip()
        plex_client_id = str(mapping.get('plex_client_id') or '').strip()
        plex_account_id = mapping.get('plex_account_id')
        plex_owner = bool(mapping.get('plex_owner'))

        if plex_account_id is None:
            resolved_id = account_name_to_id.get(username)
            if resolved_id is not None:
                save_plex_account_id(plex_client_id, resolved_id)
                plex_account_id = resolved_id

        if plex_account_id is not None:
            resolved_users.append({
                'username': username,
                'plex_account_id': int(plex_account_id),
                'plex_client_id': plex_client_id,
                'plex_owner': plex_owner
            })

    stages['resolving_accounts'] = 'done'
    stages['fetching_history'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    global_status = get_listen_history_sync_status(0)
    last_synced = global_status.get('last_synced_at')
    mindate = None
    if last_synced:
        if isinstance(last_synced, datetime):
            dt = last_synced
        else:
            try:
                dt = datetime.fromisoformat(str(last_synced).replace('Z', '+00:00'))
                dt = dt.replace(tzinfo=None)
            except Exception:
                dt = None
        if dt:
            mindate = dt - timedelta(hours=1)
    else:
        mindate = datetime.utcnow() - timedelta(days=30)
        logger.info("[HISTORY_SYNC] Initial sync — limiting to last 30 days (mindate=%s)", mindate.isoformat())

    logger.info("[HISTORY_SYNC] Fetching Plex history (mindate=%s, maxresults=50000)...", mindate)
    try:
        history_items = plex.history(mindate=mindate, maxresults=50000)
    except Exception as e:
        raise ValueError(f'Failed to fetch Plex history: {e}')
    logger.info("[HISTORY_SYNC] Fetched %s history items", len(history_items))

    account_id_to_users = {}
    for u in resolved_users:
        account_id_to_users.setdefault(u['plex_account_id'], []).append(u)

    entries_by_account = {}
    for item in history_items:
        item_account_id = getattr(item, 'accountID', None)
        if item_account_id not in account_id_to_users:
            continue

        item_type = str(getattr(item, 'type', '') or '').strip().lower()
        if item_type != 'track':
            continue

        rating_key = str(getattr(item, 'ratingKey', '') or '').strip()
        title = str(getattr(item, 'title', '') or '').strip()
        grandparent = str(getattr(item, 'grandparentTitle', '') or '').strip()
        parent = str(getattr(item, 'parentTitle', '') or '').strip()
        duration = getattr(item, 'duration', None)
        last_viewed = getattr(item, 'viewedAt', None) or getattr(item, 'lastViewedAt', None)
        view_offset = getattr(item, 'viewOffset', None)
        view_count = getattr(item, 'viewCount', None)

        if not title or not last_viewed:
            continue

        if isinstance(last_viewed, datetime):
            played_at = last_viewed.replace(tzinfo=None)
        else:
            try:
                played_at = datetime.fromisoformat(str(last_viewed).replace('Z', '+00:00'))
                played_at = played_at.replace(tzinfo=None)
            except Exception:
                continue

        entry = {
            'track_library_id': rating_key or None,
            'title': title,
            'artist': grandparent or None,
            'album': parent or None,
            'duration': int(duration) if duration else None,
            'played_at': played_at,
            'view_offset': int(view_offset) if view_offset else None,
            'view_count': int(view_count) if view_count else None,
        }
        entries_by_account.setdefault(item_account_id, []).append(entry)

    total_entries_fetched = sum(len(v) for v in entries_by_account.values())
    progress['entries_fetched'] = total_entries_fetched
    jobs.update_job_progress(job_id, {'progress': progress})

    stages['fetching_history'] = 'done'
    stages['storing_entries'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    all_library_ids = []
    for entries in entries_by_account.values():
        all_library_ids.extend([e['track_library_id'] for e in entries if e.get('track_library_id')])

    hifi_lookup = {}
    duration_lookup = {}
    if all_library_ids:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT library_id, hifi_id, duration FROM tracks WHERE library_id = ANY(%s)",
            (list(set(all_library_ids)),)
        )
        for row in cur.fetchall():
            lib_id = str(row['library_id'])
            if row.get('hifi_id'):
                hifi_lookup[lib_id] = str(row['hifi_id'])
            if row.get('duration'):
                duration_lookup[lib_id] = int(row['duration'])
        conn.close()

    total_entries_stored = 0
    global_max_played = None

    for account_id, entries in entries_by_account.items():
        _raise_if_job_cancelled(job_id)

        for e in entries:
            if e['track_library_id']:
                e['hifi_id'] = hifi_lookup.get(e['track_library_id'])
                if e['duration'] is None:
                    e['duration'] = duration_lookup.get(e['track_library_id'])

        users_for_account = account_id_to_users.get(account_id, [])
        for user_info in users_for_account:
            stored = upsert_listen_history_entries(entries, account_id, user_info['username'])
            total_entries_stored += stored

            if entries:
                max_played = max(e['played_at'] for e in entries)
                set_listen_history_sync_status(account_id, max_played, 'success')
                if global_max_played is None or max_played > global_max_played:
                    global_max_played = max_played

        progress['users_processed'] += len(users_for_account)
        progress['entries_stored'] = total_entries_stored
        jobs.update_job_progress(job_id, {'progress': progress})

    set_listen_history_sync_status(0, global_max_played or datetime.utcnow(), 'success')

    stages['fetching_history'] = 'done'
    stages['storing_entries'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    return {
        'trigger': payload.get('trigger') if isinstance(payload, dict) else 'unknown',
        'stages': stages,
        'progress': progress,
        'total_entries_fetched': total_entries_fetched,
        'total_entries_stored': total_entries_stored
    }


@app.route('/api/listen-history', methods=['GET'])
def get_listen_history_route():
    user_id = request.args.get('user_id', '').strip() or None
    limit = request.args.get('limit', '100').strip()
    since = request.args.get('since', '').strip() or None

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 500))

    plex_account_id = None
    if user_id:
        mappings = get_all_plex_account_mappings()
        for m in mappings:
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break

    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            since_dt = since_dt.replace(tzinfo=None)
        except Exception:
            since_dt = None

    rows = get_listen_history(plex_account_id=plex_account_id, limit=limit, since=since_dt)
    result = []
    for row in rows:
        played_at = row.get('played_at')
        synced_at = row.get('synced_at')
        result.append({
            'id': row['id'],
            'plex_account_id': row['plex_account_id'],
            'plex_username': row['plex_username'],
            'track_library_id': row['track_library_id'],
            'hifi_id': row['hifi_id'],
            'title': row['title'],
            'artist': row['artist'],
            'album': row['album'],
            'duration': row['duration'],
            'played_at': played_at.isoformat() + 'Z' if isinstance(played_at, datetime) else str(played_at),
            'view_offset': row['view_offset'],
            'view_count': row['view_count'],
            'synced_at': synced_at.isoformat() + 'Z' if isinstance(synced_at, datetime) else str(synced_at),
        })

    return jsonify({'history': result})


@app.route('/api/listen-history/users', methods=['GET'])
def get_listen_history_users():
    mappings = get_all_plex_account_mappings()
    result = []
    for m in mappings:
        plex_account_id = m.get('plex_account_id')
        status = {}
        if plex_account_id is not None:
            status = get_listen_history_sync_status(int(plex_account_id))
        result.append({
            'username': m.get('username'),
            'plex_client_id': m.get('plex_client_id'),
            'plex_account_id': plex_account_id,
            'plex_owner': m.get('plex_owner'),
            'last_synced_at': status.get('last_synced_at'),
            'sync_status': status.get('sync_status'),
        })
    return jsonify({'users': result})


@app.route('/api/listen-history/sync', methods=['POST'])
def trigger_listen_history_sync():
    trigger = request.json.get('trigger', 'manual') if request.is_json else 'manual'
    result = queue_plex_listen_history_sync(trigger=trigger)
    if result is None:
        return jsonify({'ok': False, 'error': 'A listen history sync job is already queued or in progress'}), 409
    return jsonify({'ok': True, 'job_id': result, 'status': 'queued'}), 202


@app.route('/api/listen-history/sync-status', methods=['GET'])
def get_listen_history_sync_status_route():
    mappings = get_all_plex_account_mappings()
    result = []
    for m in mappings:
        plex_account_id = m.get('plex_account_id')
        status = {}
        if plex_account_id is not None:
            status = get_listen_history_sync_status(int(plex_account_id))
        result.append({
            'username': m.get('username'),
            'plex_account_id': plex_account_id,
            'last_synced_at': status.get('last_synced_at'),
            'sync_status': status.get('sync_status'),
        })

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM jobs
        WHERE job_type = 'plex_listen_history_sync'
          AND status IN ('queued', 'in_progress')
        """
    )
    row = cur.fetchone() or {}
    conn.close()

    return jsonify({
        'users': result,
        'sync_in_progress': (row.get('count') or 0) > 0
    })


# --- Recommendations ---

def process_recommendation_job(job_id, payload):
    from urllib.parse import urlencode

    stages = {
        'syncing_listen_history': 'pending',
        'gathering_seeds': 'pending',
        'fetching_recommendations': 'pending',
        'processing_tracks': 'pending',
        'saving_playlist': 'pending'
    }
    progress = {
        'seeds_found': 0,
        'recommendations_fetched': 0,
        'tracks_after_filter': 0,
        'tracks_saved': 0
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    plex_account_id = payload.get('plex_account_id')
    plex_username = payload.get('plex_username', 'Unknown')
    slug = payload.get('slug', 'fresh-finds')
    trigger = payload.get('trigger', 'manual')

    if plex_account_id is None:
        raise ValueError('plex_account_id is required in payload')

    # Stage 1: Sync listen history
    stages['syncing_listen_history'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s syncing listen history for %s", job_id, plex_username)

    sync_job_id = queue_plex_listen_history_sync('recommendation')
    if sync_job_id:
        from squidly.orchestration import wait_for_job_type
        wait_for_job_type('plex_listen_history_sync', timeout=120, poll_interval=2, check_cancelled_job_id=job_id)

    stages['syncing_listen_history'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 2: Gather seeds
    stages['gathering_seeds'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s gathering seeds for %s", job_id, plex_username)

    seeds = get_recent_listen_history_seeds(plex_account_id, limit=20)
    progress['seeds_found'] = len(seeds)
    jobs.update_job_progress(job_id, {'progress': progress})

    if not seeds:
        raise ValueError(f'No listen history seeds found for user {plex_username}')

    stages['gathering_seeds'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 3: Fetch recommendations
    stages['fetching_recommendations'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s fetching recommendations for %d seeds", job_id, len(seeds))

    raw_recommendations = []
    for seed in seeds:
        _raise_if_job_cancelled(job_id)
        hifi_id = seed['hifi_id']
        try:
            response, target = downloads.make_request_with_retry_rotating_mirrors(
                f"/recommendations/?{urlencode({'id': hifi_id})}",
                SQUID_URLS,
                method='GET',
                timeout=10,
                max_retries=2
            )
            if response.ok:
                data = response.json()
                items = []
                if isinstance(data, dict):
                    data_items = data.get('data', {}).get('items') or data.get('items') or []
                    items = data_items if isinstance(data_items, list) else []
                for item in items:
                    track = item.get('track') or item.get('item') or item
                    if isinstance(track, dict) and track.get('id') and track.get('title'):
                        artists = track.get('artists') or []
                        primary_artist = artists[0] if isinstance(artists, list) and len(artists) > 0 else {}
                        album = track.get('album') if isinstance(track.get('album'), dict) else {}
                        raw_recommendations.append({
                            'hifi_id': int(track['id']),
                            'title': track['title'],
                            'artist': primary_artist.get('name') if isinstance(primary_artist, dict) else '',
                            'artist_id': primary_artist.get('id') if isinstance(primary_artist, dict) else None,
                            'album': album.get('title') if isinstance(album, dict) else '',
                            'album_id': album.get('id') if isinstance(album, dict) else None,
                            'duration': track.get('duration'),
                            'cover': album.get('cover') if isinstance(album, dict) else track.get('cover'),
                            'quality': track.get('maxAudioQuality') or track.get('audioQuality') or '',
                            'seed_hifi_id': hifi_id,
                            'isrc': track.get('isrc'),
                        })
                progress['recommendations_fetched'] = len(raw_recommendations)
                jobs.update_job_progress(job_id, {'progress': progress})
        except Exception as e:
            logger.info("[RECOMMENDATION] Job %s failed to fetch recommendations for seed %s: %s", job_id, hifi_id, e)
            continue

    stages['fetching_recommendations'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 4: Process tracks - quality filter, dedupe by ISRC, classify, split
    stages['processing_tracks'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s processing %d raw recommendations", job_id, len(raw_recommendations))

    # Step 1: Filter by minimum quality from download settings (same as before)
    settings = get_download_settings()
    min_quality = settings.get('quality', 'LOSSLESS')
    min_rank = _get_hifi_audio_quality_rank(min_quality)
    quality_filtered = []
    for rec in raw_recommendations:
        rec_rank = _get_hifi_audio_quality_rank(rec.get('quality', ''))
        if rec_rank >= min_rank:
            quality_filtered.append(rec)
    progress['tracks_after_quality_filter'] = len(quality_filtered)
    jobs.update_job_progress(job_id, {'progress': progress})

    # Step 2: Deduplicate by ISRC, aggregate frequency score.
    #         Fallback: use normalized artist+title when ISRC is missing.
    from squidly.storage import get_existing_isrcs, get_existing_artist_titles
    from squidly.utils import normalize_match_text

    deduped = {}
    for rec in quality_filtered:
        key = str(rec.get('isrc') or '').strip().upper()
        if not key:
            key = normalize_match_text(rec.get('artist', '')) + '||' + normalize_match_text(rec.get('title', ''))
        if key not in deduped:
            deduped[key] = {**rec, 'score': 1}
        else:
            deduped[key]['score'] += 1

    # Step 3: Classify each deduped track into NEW or LIBRARY candidate pools
    existing_isrcs = get_existing_isrcs()
    existing_artist_titles = get_existing_artist_titles()
    library_candidates = []
    new_candidates = []

    for rec in deduped.values():
        rec_isrc = str(rec.get('isrc') or '').strip().upper()
        is_library_track = False

        if rec_isrc and rec_isrc in existing_isrcs:
            is_library_track = True
        elif not rec_isrc:
            # Fallback: check normalized artist+title against library
            at = (
                normalize_match_text(rec.get('artist', '')),
                normalize_match_text(rec.get('title', ''), strip_trailing_parenthetical=True)
            )
            if at in existing_artist_titles:
                is_library_track = True

        if is_library_track:
            library_candidates.append(rec)
        else:
            new_candidates.append(rec)

    # Step 4: Exclude library tracks recently played by this user (30 days)
    from squidly.storage import get_recently_played_isrcs
    recently_played_isrcs = get_recently_played_isrcs(plex_account_id, days=30)
    library_candidates = [
        rec for rec in library_candidates
        if str(rec.get('isrc') or '').strip().upper() not in recently_played_isrcs
    ]

    # Step 5: Sort both pools by frequency score descending
    new_candidates.sort(key=lambda x: x['score'], reverse=True)
    library_candidates.sort(key=lambda x: x['score'], reverse=True)

    # Step 6: Calculate distribution based on user settings
    from squidly.storage import get_fresh_finds_new_track_pct, get_fresh_finds_track_count
    new_track_pct = get_fresh_finds_new_track_pct(plex_account_id)
    track_count = get_fresh_finds_track_count(plex_account_id)
    n_new = round(track_count * new_track_pct / 100)
    n_library = track_count - n_new

    selected_new = new_candidates[:n_new]
    selected_library = library_candidates[:n_library]

    # Handle overflow: if one pool is too short, fill from the other
    if len(selected_new) < n_new and len(library_candidates) > n_library:
        extra = n_new - len(selected_new)
        selected_library = library_candidates[:n_library + extra]
    elif len(selected_library) < n_library and len(new_candidates) > n_new:
        extra = n_library - len(selected_library)
        selected_new = new_candidates[:n_new + extra]

    progress['tracks_new_candidates'] = len(new_candidates)
    progress['tracks_library_candidates'] = len(library_candidates)
    progress['tracks_selected_new'] = len(selected_new)
    progress['tracks_selected_library'] = len(selected_library)
    jobs.update_job_progress(job_id, {'progress': progress})

    # Step 7: Resolve library picks to local library instance
    from squidly.storage import get_local_track_by_isrc

    for rec in selected_library:
        rec_isrc = str(rec.get('isrc') or '').strip().upper()
        if rec_isrc:
            local = get_local_track_by_isrc(rec_isrc)
            if local:
                rec['library_id'] = local['library_id']
                rec['hifi_id'] = local['hifi_id']  # Use the local track's hifi_id

    # Step 8: Combine — new tracks first, then library tracks
    top_tracks = selected_new + selected_library
    top_tracks = top_tracks[:track_count]

    progress['tracks_after_filter'] = len(top_tracks)
    progress['tracks_saved'] = len(top_tracks)
    jobs.update_job_progress(job_id, {'progress': progress})

    stages['processing_tracks'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 5: Save playlist
    stages['saving_playlist'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s saving %d tracks for %s", job_id, len(top_tracks), plex_username)

    from squidly.config import app_timezone
    from zoneinfo import ZoneInfo
    now_tz = datetime.now(ZoneInfo(app_timezone))
    playlist_name = f"Fresh Finds ({now_tz.strftime('%-m')}-{now_tz.strftime('%-d')})"

    # Save playlist to DB first, then create in Plex
    playlist_id = save_recommendation_playlist(
        plex_account_id=plex_account_id,
        slug=slug,
        name=playlist_name,
        strategy='fresh-finds',
        seed_count=len(seeds),
        tracks=top_tracks
    )

    # Stage 6: Create Plex playlist and store key
    from squidly.plex import create_fresh_finds_plex_playlist
    plex_playlist_key = None
    try:
        success, result = create_fresh_finds_plex_playlist(
            plex_account_id=plex_account_id,
            playlist_name=playlist_name,
            tracks=top_tracks
        )
        if success:
            plex_playlist_key = result
            logger.info("[RECOMMENDATION] Job %s created Plex playlist with key=%s", job_id, plex_playlist_key)
        else:
            logger.info("[RECOMMENDATION] Job %s Plex playlist creation failed (non-fatal): %s", job_id, result)
    except Exception as e:
        logger.info("[RECOMMENDATION] Job %s Plex playlist creation error (non-fatal): %s", job_id, str(e))

    # Update the playlist record with the Plex key
    if plex_playlist_key and playlist_id:
        try:
            conn_inner = get_db_connection()
            cur_inner = conn_inner.cursor()
            cur_inner.execute(
                "UPDATE recommendation_playlists SET plex_playlist_key = %s WHERE id = %s",
                (plex_playlist_key, playlist_id)
            )
            conn_inner.commit()
            conn_inner.close()
        except Exception as e:
            logger.info("[RECOMMENDATION] Job %s failed to save playlist key (non-fatal): %s", job_id, str(e))

    # Stage 7: Cleanup old Fresh Finds playlists
    from squidly.storage import cleanup_old_fresh_finds
    try:
        cleanup_result = cleanup_old_fresh_finds(plex_account_id)
        logger.info(
            "[RECOMMENDATION] Job %s cleanup: deleted %d old DB playlists, %d Plex playlists",
            job_id, cleanup_result.get('deleted_count', 0), cleanup_result.get('plex_deleted', 0)
        )
    except Exception as e:
        logger.info("[RECOMMENDATION] Job %s cleanup failed (non-fatal): %s", job_id, str(e))

    progress['tracks_saved'] = len(top_tracks)
    stages['saving_playlist'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    return {
        'stages': stages,
        'progress': progress,
        'trigger': trigger,
        'plex_username': plex_username,
    }


def process_fresh_finds_auto_download_job(job_id, payload):
    """Process a fresh_finds_auto_download job: read the playlist for each enabled user and queue download_track jobs."""
    from squidly.storage import get_recommendation_playlist, get_download_settings, get_fresh_finds_auto_download_users
    from squidly.orchestration import is_job_type_running_or_queued
    from squidly.jobs import enqueue_job, RetryableError

    slug = payload.get('slug', 'fresh-finds')

    # If generate_recommendations jobs are still running, retry later.
    # The scheduler queues this job alongside recommendation jobs, so we need
    # to wait for them to finish before reading the playlists.
    if is_job_type_running_or_queued('generate_recommendations'):
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: generate_recommendations still running, retrying later", job_id)
        raise RetryableError("generate_recommendations jobs still in progress")

    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s processing for all enabled users", job_id)

    # Get all users with auto-download enabled
    auto_download_users = get_fresh_finds_auto_download_users()

    if not auto_download_users:
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: no users with auto-download enabled", job_id)
        return {'tracks_queued': 0, 'reason': 'no_users'}

    # Get global download settings for quality and naming
    settings = get_download_settings()
    quality = settings.get('quality', 'LOSSLESS')
    file_naming = settings.get('file_naming_album', '{artist}/{album}/{track} - {title}.{ext}')
    file_naming_album = settings.get('file_naming_album', '{artist}/{album}/{track} - {title}.{ext}')

    total_tracks_queued = 0
    users_processed = []

    for user in auto_download_users:
        plex_account_id = user.get('plex_account_id')
        plex_username = user.get('username', 'Unknown')

        if plex_account_id is None:
            continue

        # Read the Fresh Finds playlist for this user
        playlist = get_todays_recommendation_playlist(plex_account_id, slug)

        if not playlist:
            logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: no playlist found for user %s (account %s)", job_id, plex_username, plex_account_id)
            continue

        tracks = playlist.get('tracks', [])
        playlist_name = playlist.get('name', 'Fresh Finds')

        if not tracks:
            logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: empty playlist for user %s (account %s)", job_id, plex_username, plex_account_id)
            continue

        # Queue a download_track job for each track
        tracks_queued = 0
        for track in tracks:
            hifi_id = track.get('hifi_id')
            if not hifi_id:
                continue

            plex_client_id = user.get('plex_client_id')
            job_payload = {
                'trackId': hifi_id,
                'fileNaming': file_naming,
                'fileNamingAlbum': file_naming_album,
                'plex_playlist': playlist_name,
                'plex_user_id': plex_client_id if plex_client_id is not None else plex_account_id,
                'downloadQuality': quality,
            }

            artist = track.get('artist')
            title = track.get('title')
            if artist:
                job_payload['artist'] = artist
            if title:
                job_payload['title'] = title

            try:
                download_job_id = enqueue_job('download_track', job_payload)
                if download_job_id:
                    tracks_queued += 1
                    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued download_track %s for track %s - %s (user: %s)",
                                job_id, download_job_id, artist or 'Unknown', title or str(hifi_id), plex_username)
            except Exception as e:
                logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: failed to queue download for track %s: %s",
                            job_id, hifi_id, str(e))

        total_tracks_queued += tracks_queued
        users_processed.append(plex_username)
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued %d/%d tracks for %s",
                    job_id, tracks_queued, len(tracks), plex_username)

    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued %d total tracks for %d users (%s)",
                job_id, total_tracks_queued, len(users_processed), ', '.join(users_processed))

    return {
        'tracks_queued': total_tracks_queued,
        'users_processed': users_processed,
    }


@app.route('/api/recommendations/playlists', methods=['GET'])
def list_recommendation_playlists_route():
    user_id = request.args.get('user_id', '').strip() or None

    plex_account_id = None
    if user_id:
        mappings = get_all_plex_account_mappings()
        for m in mappings:
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break

    if plex_account_id is None:
        return jsonify({'playlists': [], 'has_history': False})

    has_history = has_listen_history(plex_account_id)
    playlists = list_recommendation_playlists(plex_account_id)

    result = []
    for p in playlists:
        generated_at = p.get('generated_at')
        result.append({
            'id': p['id'],
            'name': p['name'],
            'slug': p['slug'],
            'strategy': p['strategy'],
            'seed_count': p['seed_count'],
            'track_count': p['track_count'],
            'generated_at': generated_at.isoformat() + 'Z' if isinstance(generated_at, datetime) else str(generated_at),
        })

    return jsonify({'playlists': result, 'has_history': has_history})


@app.route('/api/recommendations/generate', methods=['POST'])
def generate_recommendation_playlist():
    data = request.json if request.is_json else {}
    slug = data.get('slug', 'fresh-finds')
    user_id = data.get('user_id', '').strip()

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    plex_account_id = None
    plex_username = None
    mappings = get_all_plex_account_mappings()
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            plex_username = m.get('username')
            break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    job_id = queue_recommendation_generation(
        slug=slug,
        plex_account_id=plex_account_id,
        plex_username=plex_username or 'Unknown',
        trigger='manual'
    )
    if job_id is None:
        return jsonify({'error': 'A recommendation generation job is already queued or in progress'}), 409

    return jsonify({'ok': True, 'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/recommendations/<slug>', methods=['GET'])
def get_recommendation_playlist_route(slug):
    user_id = request.args.get('user_id', '').strip() or None

    plex_account_id = None
    if user_id:
        mappings = get_all_plex_account_mappings()
        for m in mappings:
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break

    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404

    playlist_id_param = request.args.get('playlist_id', '').strip()
    playlist_id = int(playlist_id_param) if playlist_id_param.isdigit() else None

    playlist_data = get_recommendation_playlist(plex_account_id, slug, playlist_id=playlist_id)
    if not playlist_data:
        return jsonify({'error': 'Playlist not found'}), 404

    generated_at = playlist_data.get('generated_at')
    tracks = []
    for t in playlist_data['tracks']:
        artist_id = t.get('artist_id')
        album_id = t.get('album_id')
        tracks.append({
            'id': t['hifi_id'],
            'title': t['title'],
            'artists': [{'id': artist_id, 'name': t['artist'] or 'Unknown Artist'}] if t['artist'] else [],
            'album': {'id': album_id, 'title': t['album'] or '', 'cover': t['cover']} if t['album'] or t['cover'] else {},
            'duration': t['duration'],
            'explicit': False,
            'maxAudioQuality': t.get('quality') or '',
        })

    return jsonify({
        'playlist': {
            'slug': playlist_data['slug'],
            'name': playlist_data['name'],
            'track_count': playlist_data['track_count'],
            'generated_at': generated_at.isoformat() + 'Z' if isinstance(generated_at, datetime) else str(generated_at),
        },
        'tracks': tracks
    })
