
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer


def init_library_update_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS library_update_status (
            id INTEGER PRIMARY KEY,
            last_update_time TIMESTAMP,
            library_update_needed BOOLEAN NOT NULL DEFAULT FALSE,
            last_job_finished_at TIMESTAMP,
            last_download_activity_at TIMESTAMP
        )
        '''
    )
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'library_update_status'
          AND column_name = 'last_download_activity_at'
        """
    )
    if not cur.fetchone():
        cur.execute('ALTER TABLE library_update_status ADD COLUMN last_download_activity_at TIMESTAMP')

    # Ensure a single row exists
    cur.execute('SELECT id FROM library_update_status WHERE id = 1')
    if not cur.fetchone():
        cur.execute('INSERT INTO library_update_status (id, library_update_needed) VALUES (1, FALSE)')
    conn.commit()
    conn.close()

def get_library_update_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT last_update_time, library_update_needed, last_job_finished_at, last_download_activity_at
        FROM library_update_status
        WHERE id = 1
        '''
    )
    row = cur.fetchone()
    conn.close()
    return row

def normalize_db_timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(raw)
        except Exception:
            return None
    if hasattr(dt, 'replace'):
        dt = dt.replace(tzinfo=None)
    return dt

def set_library_update_needed(value: bool):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE library_update_status SET library_update_needed = %s WHERE id = 1', (value,))
    conn.commit()
    conn.close()

def set_last_library_update_time(ts):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE library_update_status SET last_update_time = %s WHERE id = 1', (ts,))
    conn.commit()
    conn.close()

def set_last_job_finished_at(ts):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE library_update_status SET last_job_finished_at = %s WHERE id = 1', (ts,))
    conn.commit()
    conn.close()

def set_last_download_activity_at(ts):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE library_update_status SET last_download_activity_at = %s WHERE id = 1', (ts,))
    conn.commit()
    conn.close()

def get_last_download_activity_at():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT last_download_activity_at FROM library_update_status WHERE id = 1')
    row = cur.fetchone() or {}
    conn.close()
    return normalize_db_timestamp(row.get('last_download_activity_at'))

def get_download_write_gate_state():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, status, result_json
        FROM jobs
        WHERE job_type = 'download_track'
          AND status IN ('queued', 'in_progress')
        ORDER BY created_at ASC
        """
    )
    rows = cur.fetchall() or []
    conn.close()

    blocking_jobs = []
    ready_count = 0

    for row in rows:
        job_id = row.get('id')
        status = str(row.get('status') or '').strip().lower()

        if status == 'queued':
            blocking_jobs.append(job_id)
            continue

        stages = {}
        try:
            parsed = json.loads(row.get('result_json')) if row.get('result_json') else {}
            if isinstance(parsed, dict) and isinstance(parsed.get('stages'), dict):
                stages = parsed.get('stages')
        except (TypeError, ValueError):
            stages = {}

        written_stage = str(stages.get('written') or '').strip().lower()
        if written_stage in ('done', 'skipped'):
            ready_count += 1
            continue

        blocking_jobs.append(job_id)

    return {
        'total_current_jobs': len(rows),
        'written_ready_jobs': ready_count,
        'blocking_count': len(blocking_jobs),
        'blocking_job_ids': blocking_jobs,
        'all_written_ready': len(blocking_jobs) == 0
    }

def can_start_plex_library_update(required_idle_seconds=180):
    gate_state = get_download_write_gate_state()
    last_activity_at = get_last_download_activity_at()
    now = datetime.utcnow()

    idle_seconds = None
    if last_activity_at:
        idle_seconds = max(0, int((now - last_activity_at).total_seconds()))

    is_idle = idle_seconds is not None and idle_seconds >= required_idle_seconds
    can_start = gate_state['all_written_ready'] and is_idle

    return {
        'can_start': can_start,
        'gate_state': gate_state,
        'idle_seconds': idle_seconds,
        'required_idle_seconds': required_idle_seconds,
        'last_activity_at': last_activity_at.isoformat() + 'Z' if last_activity_at else None
    }

def any_download_jobs_running():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM jobs WHERE job_type = 'download_track' AND status IN ('queued', 'in_progress')")
    row = cur.fetchone() or {}
    count = row.get('count', 0)
    conn.close()
    return count > 0

def _is_plex_library_scan_active(plex, library):
    """Best-effort check for whether the target Plex library is actively scanning."""
    try:
        library.reload()
        if bool(getattr(library, 'refreshing', False)):
            return True
    except Exception:
        pass

    section_id = str(getattr(library, 'key', '') or '').strip('/')

    try:
        activities = plex.activities() or []
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
            print('[LIBRARY UPDATE] Plex scan still in progress...', flush=True)
        elif saw_active:
            print('[LIBRARY UPDATE] Plex scan appears complete.', flush=True)
            return True, True
        elif elapsed >= startup_grace_seconds:
            print('[LIBRARY UPDATE] Did not observe an active scan during startup grace window.', flush=True)
            return False, False

        if elapsed >= timeout_seconds:
            print('[LIBRARY UPDATE] Timed out waiting for Plex scan completion.', flush=True)
            return False, saw_active

        time.sleep(max(1, poll_interval_seconds))

def start_plex_sync_job(trigger='manual'):
    return jobs.start_plex_sync_job(trigger=trigger)

def any_plex_library_update_jobs_running_or_queued():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM jobs
        WHERE job_type = 'plex_library_update'
          AND status IN ('queued', 'in_progress')
        """
    )
    row = cur.fetchone() or {}
    conn.close()
    return (row.get('count') or 0) > 0

def queue_plex_library_update(trigger='scheduled'):
    if any_plex_library_update_jobs_running_or_queued():
        return None

    payload = {
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('plex_library_update', payload, max_attempts=5)

def start_plex_library_update_job(trigger='scheduled'):
    """Queue a Plex library update job if one is not already queued/in progress."""
    config = get_plex_config()
    if not config.get('server_url') or not config.get('api_token') or not config.get('library_name'):
        return {'ok': False, 'status_code': 400, 'error': 'Plex is not fully configured'}

    job_id = queue_plex_library_update(trigger=trigger)
    if job_id is None:
        return {'ok': False, 'status_code': 409, 'error': 'A Plex library update job is already queued or in progress'}

    return {'ok': True, 'status_code': 202, 'job_id': job_id, 'status': 'queued'}

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
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    gate = gate_snapshot or can_start_plex_library_update(required_idle_seconds=180)
    gate_state = gate.get('gate_state') or {}
    progress['download_gate_checks'] = 1
    progress['download_gate_blocking_count'] = gate_state.get('blocking_count') or 0
    progress['download_gate_idle_seconds'] = gate.get('idle_seconds') or 0
    progress['download_gate_required_idle_seconds'] = gate.get('required_idle_seconds') or 180
    progress['download_gate_last_activity_at'] = gate.get('last_activity_at')
    progress['download_gate_status'] = 'ready'
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['scanning_plex_library'] = 'in_progress'
    update_job_progress(job_id, {'stages': stages})

    print(f"[LIBRARY_UPDATE_JOB] Job {job_id} connecting to Plex at {server_url}", flush=True)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)

    library = None
    for section in plex.library.sections():
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    print(f"[LIBRARY_UPDATE_JOB] Job {job_id} triggering scan on library '{library_name}'", flush=True)
    library.update()

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
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    sync_result = start_plex_sync_job(trigger='post_library_update')
    if sync_result.get('ok'):
        progress['sync_job_id'] = sync_result.get('job_id')
        progress['sync_queue_status'] = 'queued'
    elif sync_result.get('status_code') == 409:
        progress['sync_queue_status'] = 'already_queued'
    else:
        update_job_progress(job_id, {'stages': stages, 'progress': progress})
        raise RuntimeError(sync_result.get('error') or 'Failed to queue Plex sync after library update')

    update_job_progress(job_id, {'stages': stages, 'progress': progress})
    set_last_library_update_time(datetime.utcnow())

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    scan_outcome = 'completed' if completed else ('started_but_timeout' if saw_active else 'not_observed')
    print(
        f"[LIBRARY_UPDATE_JOB] Job {job_id} finished. scan_outcome={scan_outcome} sync_queue_status={progress['sync_queue_status']}",
        flush=True
    )

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'scan_outcome': scan_outcome,
        'sync_job_id': progress.get('sync_job_id'),
        'sync_queue_status': progress.get('sync_queue_status')
    }

def plex_library_update_job_worker():
    print("[LIBRARY_UPDATE_JOB_WORKER] Background worker started", flush=True)
    gate_poll_seconds = 15

    while True:
        try:
            gate = can_start_plex_library_update(required_idle_seconds=180)
            if not gate.get('can_start'):
                if any_plex_library_update_jobs_running_or_queued():
                    gate_state = gate.get('gate_state') or {}
                    blocking_count = gate_state.get('blocking_count') or 0
                    idle_seconds = gate.get('idle_seconds')
                    required_idle = gate.get('required_idle_seconds') or 180
                    print(
                        f"[LIBRARY_UPDATE_JOB_WORKER] Waiting to claim update job: blocking={blocking_count} idle_seconds={idle_seconds} required_idle={required_idle}",
                        flush=True
                    )
                time.sleep(gate_poll_seconds)
                continue

            job = claim_next_job('plex_library_update')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                gate_after_claim = can_start_plex_library_update(required_idle_seconds=180)
                if not gate_after_claim.get('can_start'):
                    requeue_claimed_job(
                        job['id'],
                        delay_seconds=gate_poll_seconds,
                        error_message='Waiting for downloads gate before starting Plex library update'
                    )
                    print(f"[LIBRARY_UPDATE_JOB_WORKER] Job {job['id']} deferred until downloads gate is ready", flush=True)
                    time.sleep(1)
                    continue

                result = process_plex_library_update_job(job['id'], payload, gate_snapshot=gate_after_claim)
                mark_job_succeeded(job['id'], result)
                print(f"[LIBRARY_UPDATE_JOB_WORKER] Job {job['id']} completed", flush=True)
            except Exception as e:
                print(f"[LIBRARY_UPDATE_JOB_WORKER] Job {job['id']} failed: {str(e)}", flush=True)
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            print(f"[LIBRARY_UPDATE_JOB_WORKER] Error in background worker: {str(e)}", flush=True)
            time.sleep(5)
from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
import threading
import os
import json
import base64
import requests
import psycopg2
import psycopg2.extras
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
    add_tracks_to_plex_playlist,
    get_all_plex_users,
    get_plex_health_status,
    get_plex_music_playlists,
    plex_healthcheck,
    plex_pin_sessions,
    set_plex_health_status,
    test_plex_connection,
)

from ytmusicapi import YTMusic

from squidly import downloads
from squidly import jobs

from squidly.storage import (
    clear_plex_config,
    get_download_settings,
    get_listenbrainz_config,
    get_plex_config,
    init_db,
    init_library_update_status,
    save_download_settings,
    save_listenbrainz_config,
    save_plex_config,
)

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
    """Return a list of Plex users (owner and managed) as JSON."""
    users = get_all_plex_users()
    # Remove user_obj (not serializable)
    result = [
        {k: v for k, v in user.items() if k not in ('user_obj',)}
        for user in users
    ]
    return jsonify({'users': result})
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
    """Clear saved Plex configuration."""
    clear_plex_config()
    set_plex_health_status(False, 'No Plex credentials configured')
    return jsonify({'ok': True})

@app.route('/api/plex/pin/start', methods=['POST'])
def plex_pin_start():
    print('[DEBUG] /api/plex/pin/start called', flush=True)
    try:
        print('[DEBUG] Attempting to create MyPlexPinLogin...', flush=True)
        pinlogin = MyPlexPinLogin(oauth=False)
        print('[DEBUG] MyPlexPinLogin created', flush=True)
        pin = pinlogin.pin
        print(f'[DEBUG] PIN generated: {pin}', flush=True)
        client_id = id(pinlogin)
        plex_pin_sessions[client_id] = pinlogin
        print(f'[DEBUG] Stored pinlogin in session with client_id: {client_id}', flush=True)
        return jsonify({
            'ok': True,
            'pin': pin,
            'client_id': client_id
        })
    except Exception as e:
        print(f'[ERROR] Exception in /api/plex/pin/start: {e}', flush=True)
        import traceback; traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/plex/pin/status', methods=['POST'])
def plex_pin_status():
    print('[DEBUG] /api/plex/pin/status called', flush=True)
    data = request.get_json(force=True)
    client_id = data.get('client_id')
    pin = data.get('pin')
    print(f'[DEBUG] Received client_id={client_id}, pin={pin}', flush=True)
    if not client_id or not pin:
        print('[DEBUG] Missing client_id or pin', flush=True)
        return jsonify({'ok': False, 'error': 'Missing client_id or pin'}), 400
    pinlogin = plex_pin_sessions.get(client_id)
    if not pinlogin:
        print('[DEBUG] Session expired or not found for client_id', flush=True)
        return jsonify({'ok': False, 'error': 'Session expired or not found'}), 404
    # Check if already expired
    if getattr(pinlogin, 'expired', False):
        print('[DEBUG] PIN expired for client_id', flush=True)
        return jsonify({'ok': False, 'expired': True, 'error': 'PIN expired'}), 410
    try:
        print('[DEBUG] Calling pinlogin.checkLogin()', flush=True)
        if pinlogin.checkLogin():
            print('[DEBUG] pinlogin.checkLogin() returned True', flush=True)
            token = getattr(pinlogin, 'token', None)
            acc = None
            try:
                print('[DEBUG] Creating MyPlexAccount', flush=True)
                acc = MyPlexAccount(token=token)
            except Exception as e:
                print(f'[DEBUG] Failed to create MyPlexAccount: {e}', flush=True)
                return jsonify({'ok': False, 'error': f'Login succeeded but failed to create MyPlexAccount: {e}'}), 500
            # Find local server baseurl
            try:
                print('[DEBUG] Fetching acc.resources()', flush=True)
                res = acc.resources()
            except Exception as e:
                print(f'[DEBUG] Failed to fetch resources: {e}', flush=True)
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
            print(f'[DEBUG] baseurl={baseurl}, token={token}', flush=True)
            # Save to DB
            if baseurl and token:
                print('[DEBUG] Saving Plex config to DB', flush=True)
                config = get_plex_config()
                save_plex_config(baseurl, token, config.get('library_name') or '', config.get('sync_interval_hours') or 24)
            # Clean up session
            print('[DEBUG] Cleaning up pin session', flush=True)
            plex_pin_sessions.pop(client_id, None)
            return jsonify({'ok': True, 'token': token, 'baseurl': baseurl, 'username': getattr(acc, 'username', None)})
        else:
            print('[DEBUG] pinlogin.checkLogin() returned False (pending)', flush=True)
            return jsonify({'ok': False, 'pending': True})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f'[DEBUG] Exception in /api/plex/pin/status: {e}\n{tb}', flush=True)
        return jsonify({'ok': False, 'error': str(e), 'traceback': tb}), 500

from squidly.config import (
    DATABASE_URL,
    DOWNLOADS_FULL_ALBUMS_FOLDER,
    DOWNLOADS_LOOSE_TRACKS_FOLDER,
    DOWNLOADS_ROOT,
    DEFAULT_DOWNLOAD_SETTINGS,
    WORKER_ID,
)

# Create downloads directories if they don't exist
full_albums_path = os.path.join(DOWNLOADS_ROOT, DOWNLOADS_FULL_ALBUMS_FOLDER)
loose_tracks_path = os.path.join(DOWNLOADS_ROOT, DOWNLOADS_LOOSE_TRACKS_FOLDER)

# Note: Don't call os.makedirs() here - volume mounts are configured in docker-compose
# Attempting to create them can shadow the mount points

# Verify downloads directories exist and are writable
if not os.path.exists(full_albums_path):
    print(f"Error: Full albums directory does not exist: {full_albums_path}", file=sys.stderr)
    print(f"Check docker-compose volume mounts are configured correctly", file=sys.stderr)
elif not os.access(full_albums_path, os.W_OK):
    print(f"Error: Full albums directory is not writable: {full_albums_path}", file=sys.stderr)
else:
    print(f"Full albums directory ready: {full_albums_path}", flush=True)

if not os.path.exists(loose_tracks_path):
    print(f"Error: Loose tracks directory does not exist: {loose_tracks_path}", file=sys.stderr)
    print(f"Check docker-compose volume mounts are configured correctly", file=sys.stderr)
elif not os.access(loose_tracks_path, os.W_OK):
    print(f"Error: Loose tracks directory is not writable: {loose_tracks_path}", file=sys.stderr)
else:
    print(f"Loose tracks directory ready: {loose_tracks_path}", flush=True)

def make_request_with_retry(url, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    return downloads.make_request_with_retry(url, method=method, timeout=timeout, max_retries=max_retries, backoff_factor=backoff_factor, **kwargs)

def make_request_with_retry_rotating_mirrors(url_base, url_list, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    return downloads.make_request_with_retry_rotating_mirrors(
        url_base, url_list, method=method, timeout=timeout, max_retries=max_retries, backoff_factor=backoff_factor, **kwargs
    )

from squidly.db import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS download_settings (
            id INTEGER PRIMARY KEY,
            format TEXT NOT NULL,
            parent_folder TEXT NOT NULL,
            file_naming TEXT,
            file_naming_loose TEXT,
            file_naming_album TEXT,
            jobs_refresh_interval_seconds INTEGER NOT NULL DEFAULT 30,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT check_single_row CHECK (id = 1)
        )
        """
    )
    # Check if columns exist (PostgreSQL version)
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'download_settings'
        """
    )
    columns = {row['column_name'] for row in cur.fetchall()}
    
    if 'file_naming' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN file_naming TEXT")
    if 'file_naming_loose' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN file_naming_loose TEXT")
    if 'file_naming_album' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN file_naming_album TEXT")
    if 'jobs_refresh_interval_seconds' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN jobs_refresh_interval_seconds INTEGER")
    if 'ignore_matches' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN ignore_matches BOOLEAN NOT NULL DEFAULT FALSE")
    
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mirror_endpoints (
            name TEXT PRIMARY KEY,
            encoded_url TEXT NOT NULL,
            online INTEGER NOT NULL,
            response_time REAL,
            last_checked TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS listenbrainz_config (
            id INTEGER PRIMARY KEY,
            user_token TEXT,
            username TEXT,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT check_single_row_lb CHECK (id = 1)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plex_config (
            id INTEGER PRIMARY KEY,
            server_url TEXT,
            api_token TEXT,
            library_name TEXT,
            sync_interval_hours INTEGER NOT NULL DEFAULT 24,
            update_playlist_name TEXT,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT check_single_row_plex CHECK (id = 1)
        )
        """
    )
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'plex_config'
        """
    )
    plex_columns = {row['column_name'] for row in cur.fetchall()}
    if 'sync_interval_hours' not in plex_columns:
        cur.execute("ALTER TABLE plex_config ADD COLUMN sync_interval_hours INTEGER NOT NULL DEFAULT 24")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plex_songs (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT,
            album TEXT,
            file_path TEXT NOT NULL UNIQUE,
            "ratingKey" TEXT,
            format TEXT,
            bitrate INTEGER,
            updated_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL
        )
        """
    )
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'plex_songs'
        """
    )
    plex_songs_columns = {row['column_name'] for row in cur.fetchall()}
    if 'ratingKey' not in plex_songs_columns:
        cur.execute('ALTER TABLE plex_songs ADD COLUMN "ratingKey" TEXT')

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            result_json TEXT,
            error_message TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 20,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            run_after TIMESTAMP,
            locked_at TIMESTAMP,
            locked_by TEXT,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            priority INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        UPDATE jobs
        SET job_type = %s
        WHERE job_type = %s
        """,
        ('plex_playlist_add', 'plex_add')
    )
    
    conn.commit()
    conn.close()


def any_plex_sync_jobs_running_or_queued():
    return jobs.any_plex_sync_jobs_running_or_queued()

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

def queue_plex_library_sync(trigger='manual'):
    return jobs.queue_plex_library_sync(trigger=trigger)

def process_plex_sync_job(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or 'Music').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured before syncing')

    stages = {
        'reading_plex_library': 'in_progress',
        'updating_local_index': 'pending'
    }
    progress = {
        'processed_tracks': 0,
        'total_tracks': 0,
        'upserted_songs': 0,
        'deleted_songs': 0
    }
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    print(f"[PLEX_SYNC] Job {job_id} connecting to Plex at {server_url}", flush=True)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)
    update_job_progress(job_id, {'stages': stages})

    library = None
    for section in plex.library.sections():
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    print(f"[PLEX_SYNC] Job {job_id} fetching tracks from library '{library_name}'", flush=True)
    tracks = []
    try:
        tracks = library.all(libtype='track')
    except Exception:
        tracks = library.search(libtype='track')

    progress['total_tracks'] = len(tracks)
    stages['reading_plex_library'] = 'done'
    stages['updating_local_index'] = 'in_progress'
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat() + 'Z'
    seen_paths = set()
    upserted = 0

    for idx, track in enumerate(tracks, start=1):
        title = getattr(track, 'title', None) or 'Unknown Title'
        artist = getattr(track, 'grandparentTitle', None) or None
        album = getattr(track, 'parentTitle', None) or None
        rating_key = str(getattr(track, 'ratingKey', None) or '').strip() or None

        media_list = getattr(track, 'media', None) or []
        for media in media_list:
            parts = getattr(media, 'parts', None) or []
            bitrate = getattr(media, 'bitrate', None)
            media_format = (getattr(media, 'container', None) or '').strip().lower() or None

            for part in parts:
                file_path = (getattr(part, 'file', None) or '').strip()
                if not file_path:
                    continue

                if not media_format:
                    _, ext = os.path.splitext(file_path)
                    media_format = ext.replace('.', '').lower() if ext else None

                cur.execute(
                    """
                    INSERT INTO plex_songs (title, artist, album, file_path, "ratingKey", format, bitrate, updated_at, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(file_path) DO UPDATE SET
                        title = excluded.title,
                        artist = excluded.artist,
                        album = excluded.album,
                        "ratingKey" = excluded."ratingKey",
                        format = excluded.format,
                        bitrate = excluded.bitrate,
                        updated_at = excluded.updated_at,
                        last_seen_at = excluded.last_seen_at
                    """,
                    (title, artist, album, file_path, rating_key, media_format, bitrate, now, now)
                )
                seen_paths.add(file_path)
                upserted += 1

        progress['processed_tracks'] = idx
        progress['upserted_songs'] = upserted
        if idx % 25 == 0 or idx == len(tracks):
            update_job_progress(job_id, {'progress': progress})

    conn.commit()
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    deleted = 0
    if seen_paths:
        cur.execute(
            """
            DELETE FROM plex_songs
            WHERE last_seen_at < %s
            """,
            (now,)
        )
        deleted = cur.rowcount or 0

    conn.commit()
    conn.close()

    progress['deleted_songs'] = deleted
    stages['updating_local_index'] = 'done'
    update_job_progress(job_id, {'stages': stages, 'progress': progress})

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    print(
        f"[PLEX_SYNC] Job {job_id} finished. tracks={progress['total_tracks']} upserted={upserted} deleted={deleted}",
        flush=True
    )

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'total_tracks': progress['total_tracks'],
        'upserted_songs': upserted,
        'deleted_songs': deleted
    }

def plex_sync_job_worker():
    print("[PLEX_SYNC_WORKER] Background worker started", flush=True)

    while True:
        try:
            job = claim_next_job('plex_library_sync')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            if any_plex_library_update_jobs_running_or_queued():
                requeue_claimed_job(
                    job['id'],
                    delay_seconds=20,
                    error_message='Waiting for plex_library_update jobs to finish before sync'
                )
                print(f"[PLEX_SYNC_WORKER] Job {job['id']} deferred until library update completes", flush=True)
                time.sleep(1)
                continue

            try:
                result = process_plex_sync_job(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                print(f"[PLEX_SYNC_WORKER] Job {job['id']} completed", flush=True)
            except Exception as e:
                print(f"[PLEX_SYNC_WORKER] Job {job['id']} failed: {str(e)}", flush=True)
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            print(f"[PLEX_SYNC_WORKER] Error in background worker: {str(e)}", flush=True)
            time.sleep(5)

def plex_sync_scheduler_worker():
    print("[PLEX_SYNC_SCHEDULER] Background scheduler started", flush=True)

    while True:
        try:
            config = get_plex_config()
            server_url = (config.get('server_url') or '').strip()
            api_token = (config.get('api_token') or '').strip()
            library_name = (config.get('library_name') or '').strip()

            if not (server_url and api_token and library_name):
                time.sleep(60)
                continue

            interval_hours = config.get('sync_interval_hours')
            try:
                interval_hours = int(interval_hours)
            except Exception:
                interval_hours = 24
            if interval_hours < 1:
                interval_hours = 1

            if any_plex_sync_jobs_running_or_queued():
                time.sleep(60)
                continue

            last_finished = get_last_successful_plex_sync_finished_at()
            should_enqueue = False
            now = datetime.utcnow()
            if not last_finished:
                should_enqueue = True
            else:
                should_enqueue = now - last_finished >= timedelta(hours=interval_hours)

            if should_enqueue:
                queued = queue_plex_library_sync(trigger='interval')
                if queued:
                    print(f"[PLEX_SYNC_SCHEDULER] Queued interval sync job {queued}", flush=True)

        except Exception as e:
            print(f"[PLEX_SYNC_SCHEDULER] Error: {str(e)}", flush=True)

        time.sleep(60)

def serialize_job_payload(payload):
    return jobs.serialize_job_payload(payload)

def enqueue_job(job_type, payload, status='queued', priority=0, run_after=None, max_attempts=20):
    return jobs.enqueue_job(job_type, payload, status=status, priority=priority, run_after=run_after, max_attempts=max_attempts)

def queue_pending_playlist_addition(artist, album, title, file_path, playlist_name, parent_job_id=None, plex_user_id=None):
    return jobs.queue_pending_playlist_addition(artist, album, title, file_path, playlist_name, parent_job_id=parent_job_id, plex_user_id=plex_user_id)

def update_parent_playlist_stage(parent_job_id, playlist_stage_status):
    return jobs.update_parent_playlist_stage(parent_job_id, playlist_stage_status)

def backfill_plex_playlist_add_parent_links():
    return jobs.backfill_plex_playlist_add_parent_links()

def get_pending_playlist_additions():
    return jobs.get_pending_playlist_additions()

def update_pending_addition_attempt(addition_id, error_message=None):
    return jobs.update_pending_addition_attempt(addition_id, error_message)

def remove_pending_addition(addition_id):
    return jobs.remove_pending_addition(addition_id)

def compute_job_backoff_seconds(attempt_count):
    return jobs.compute_job_backoff_seconds(attempt_count)

class ManifestDownloadError(Exception):
    pass

class TransientDownloadError(Exception):
    pass

class PermanentDownloadError(Exception):
    pass

def claim_next_job(job_type):
    return jobs.claim_next_job(job_type)

def mark_job_succeeded(job_id, result):
    return jobs.mark_job_succeeded(job_id, result)

def _download_track_all_stages_done(stages):
    if not isinstance(stages, dict):
        return False

    required_stages = (
        'downloaded',
        'id3_tagged',
        'written'
    )
    if not all(stages.get(stage_name) == 'done' for stage_name in required_stages):
        return False

    if stages.get('converted') not in ('done', 'skipped'):
        return False

    return stages.get('playlist_added') in ('done', 'skipped')

def mark_job_in_progress(job_id):
    return jobs.mark_job_in_progress(job_id)

def requeue_claimed_job(job_id, delay_seconds=30, error_message=None):
    return jobs.requeue_claimed_job(job_id, delay_seconds=delay_seconds, error_message=error_message)

def recover_stale_in_progress_jobs(stale_after_minutes=15):
    return jobs.recover_stale_in_progress_jobs(stale_after_minutes=stale_after_minutes)

def update_job_progress(job_id, updates):
    return jobs.update_job_progress(job_id, updates)

def mark_job_failed(job_id, attempt_count, max_attempts, error_message):
    return jobs.mark_job_failed(job_id, attempt_count, max_attempts, error_message)

def mark_job_retrying(job_id, attempt_count, error_message):
    return jobs.mark_job_retrying(job_id, attempt_count, error_message)

def process_download_job(job_id, payload):
    track_id = payload.get('trackId')
    file_format = payload.get('format', 'original')
    download_type = payload.get('downloadType', 'loose')
    stages = {
        'downloaded': 'pending',
        'id3_tagged': 'pending',
        'converted': 'pending',
        'written': 'pending',
        'playlist_added': 'pending'
    }

    if not track_id:
        raise ValueError('trackId is required')

    if download_type not in ('album', 'loose'):
        download_type = 'loose'

    file_naming = payload.get('fileNaming')
    if not file_naming:
        if download_type == 'album':
            file_naming = payload.get('fileNamingAlbum') or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']
        else:
            file_naming = payload.get('fileNamingLoose') or DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose']

    if file_format not in ('original', 'mp3'):
        raise ValueError('Invalid format value')

    target_folder_name = DOWNLOADS_FULL_ALBUMS_FOLDER if download_type == 'album' else DOWNLOADS_LOOSE_TRACKS_FOLDER
    downloads_folder = os.path.join(DOWNLOADS_ROOT, target_folder_name)

    print(f"\n[DOWNLOAD] Job {job_id} starting for track {track_id}", flush=True)
    print(f"[DOWNLOAD] Format: {file_format}", flush=True)
    print(f"[DOWNLOAD] File naming template: {file_naming}", flush=True)
    print(f"[DOWNLOAD] Download type: {download_type}", flush=True)
    print(f"[DOWNLOAD] Downloads folder: {downloads_folder}", flush=True)

    if not os.path.exists(downloads_folder):
        print(f"[DOWNLOAD] WARNING: Downloads folder does not exist, creating it: {downloads_folder}", flush=True)
        os.makedirs(downloads_folder, exist_ok=True)

    print(f"[DOWNLOAD] Fetching track metadata...", flush=True)
    try:
        info_response, target = make_request_with_retry_rotating_mirrors(
            f"/info/?id={track_id}",
            SQUID_URLS,
            method='GET',
            timeout=10,
            max_retries=3
        )
    except requests.exceptions.RequestException as e:
        raise TransientDownloadError(f"Failed to fetch track info: {str(e)}") from e

    mirror_name = target.get('name') if isinstance(target, dict) else 'unknown'
    print(f"[DOWNLOAD] Track info fetched from mirror '{mirror_name}' with status {info_response.status_code}", flush=True)

    if not info_response.ok:
        raise TransientDownloadError(
            f"Failed to get track info. Status: {info_response.status_code} from mirror '{mirror_name}'"
        )

    info_data = info_response.json()
    print(f"[DOWNLOAD] Track info response structure: {info_data.keys() if isinstance(info_data, dict) else type(info_data)}", flush=True)

    track_info = info_data.get('data', info_data) if isinstance(info_data, dict) else {}
    track_metadata = track_info.get('track', track_info) if 'track' in track_info else track_info

    track_artist_name = 'Unknown Artist'
    album_artist_name = None
    album_name = 'Unknown Album'
    track_title = 'Unknown Track'
    track_version = ''
    track_num = '01'
    disc_num = ''
    release_year = ''
    copyright_text = ''
    cover_url = ''
    album_id = ''

    if isinstance(track_metadata, dict):
        if 'artist' in track_metadata and isinstance(track_metadata['artist'], dict):
            track_artist_name = track_metadata['artist'].get('name', 'Unknown Artist')
        elif 'artists' in track_metadata and isinstance(track_metadata['artists'], list) and len(track_metadata['artists']) > 0:
            track_artist_name = track_metadata['artists'][0].get('name', 'Unknown Artist')
        elif 'artistName' in track_metadata:
            track_artist_name = track_metadata['artistName']


        if 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            album_name = track_metadata['album'].get('title', 'Unknown Album')

            if 'id' in track_metadata['album']:
                album_id = track_metadata['album']['id']

            if 'cover' in track_metadata['album'] and track_metadata['album']['cover']:
                cover_val = track_metadata['album']['cover']
                if isinstance(cover_val, str) and not cover_val.startswith('http'):
                    cover_url = format_tidal_image_url(cover_val, 1280)
                else:
                    cover_url = cover_val

            if not cover_url:
                for cover_field in ['coverUri', 'imageUri', 'image']:
                    if cover_field in track_metadata['album']:
                        cover_val = track_metadata['album'][cover_field]
                        if isinstance(cover_val, str):
                            if not cover_val.startswith('http'):
                                cover_url = format_tidal_image_url(cover_val, 1280)
                            else:
                                cover_url = cover_val
                            break

        elif 'albumTitle' in track_metadata:
            album_name = track_metadata['albumTitle']

        if 'title' in track_metadata:
            track_title = track_metadata['title']

        # Add Explicit tag to title if marked as explicit in TIDAL metadata
        if 'version' in track_metadata and track_metadata['version']:
            track_version = str(track_metadata['version']).strip()

        if 'explicit' in track_metadata:
            if bool(track_metadata['explicit']) == True:
                track_title += ' [Explicit]'

        if track_version:
            track_title = f"{track_title} ({track_version})"

        if 'trackNumber' in track_metadata:
            track_num = str(track_metadata['trackNumber']).zfill(2)

        if 'volumeNumber' in track_metadata:
            volume_number = track_metadata['volumeNumber']
            try:
                parsed_disc_num = int(str(volume_number).strip())
                if parsed_disc_num > 0:
                    disc_num = str(parsed_disc_num)
            except (TypeError, ValueError):
                disc_num = ''

        if 'releaseDate' in track_metadata:
            date_str = track_metadata['releaseDate']
            if isinstance(date_str, str) and len(date_str) >= 4:
                release_year = date_str[:4]
        elif 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            date_str = track_metadata['album'].get('releaseDate')
            if isinstance(date_str, str) and len(date_str) >= 4:
                release_year = date_str[:4]

        if 'copyright' in track_metadata and track_metadata['copyright']:
            copyright_text = str(track_metadata['copyright']).strip()

        if not copyright_text and 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            raw_copyright = track_metadata['album'].get('copyright')
            if raw_copyright:
                copyright_text = str(raw_copyright).strip()

        if not release_year:
            release_year = extract_year_from_text(copyright_text)
        if not release_year and 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            release_year = extract_year_from_text(track_metadata['album'].get('copyright', ''))

        if not cover_url and album_id:
            cover_url = format_tidal_image_url(str(album_id), 1280)

        if not cover_url:
            if 'cover' in track_metadata:
                cover_val = track_metadata['cover']
                if isinstance(cover_val, str) and not cover_val.startswith('http'):
                    cover_url = format_tidal_image_url(cover_val, 1280)
                else:
                    cover_url = cover_val

    # Attempt to resolve album artist from album metadata endpoint (preferred over track-level artist)
    album_artist_name = None
    album_disc_count = 1
    album_has_multiple_discs = False
    if album_id:
        try:
            album_response, album_target = make_request_with_retry_rotating_mirrors(
                f"/album/?id={album_id}",
                SQUID_URLS,
                method='GET',
                timeout=10,
                max_retries=3
            )
            if album_response.ok:
                album_data = album_response.json()
                album_payload = album_data.get('data', album_data) if isinstance(album_data, dict) else {}
                album_obj = album_payload.get('album', album_payload) if isinstance(album_payload, dict) else {}

                # Detect multi-disc album by inspecting the track-level volumeNumber values
                if isinstance(album_payload, dict):
                    album_items = album_payload.get('items', [])
                    volume_numbers = set()
                    if isinstance(album_items, list):
                        for entry in album_items:
                            if isinstance(entry, dict):
                                item = entry.get('item') if isinstance(entry.get('item'), dict) else {}
                                volume_number = item.get('volumeNumber')
                                try:
                                    if volume_number is not None:
                                        volume_numbers.add(int(volume_number))
                                except (TypeError, ValueError):
                                    pass
                    if len(volume_numbers) > 1:
                        album_disc_count = len(volume_numbers)
                        album_has_multiple_discs = True

                if isinstance(album_obj, dict):
                    if 'artist' in album_obj and isinstance(album_obj['artist'], dict):
                        album_artist_name = album_obj['artist'].get('name')
                    elif 'artists' in album_obj and isinstance(album_obj['artists'], list) and len(album_obj['artists']) > 0:
                        first_artist = album_obj['artists'][0]
                        if isinstance(first_artist, dict):
                            album_artist_name = first_artist.get('name')

        except requests.exceptions.RequestException as e:
            print(f"[DOWNLOAD] Warning: Failed to fetch album artist for album {album_id}: {str(e)}", flush=True)

    artist_name = track_artist_name
    effective_artist_name = album_artist_name or track_artist_name

    print(f"[DOWNLOAD] Extracted metadata: TrackArtist='{track_artist_name}', AlbumArtist='{album_artist_name or ''}', EffectiveArtistForPath='{effective_artist_name}', Album='{album_name}', Title='{track_title}', TrackNum='{track_num}', DiscNum='{disc_num}', Year='{release_year}', Cover='{cover_url}'", flush=True)

    file_ext = 'flac' if file_format == 'original' else 'mp3'

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

    full_path = os.path.join(downloads_folder, file_path)
    full_path = os.path.normpath(full_path)

    print(
        f"[DOWNLOAD_DECISION] Job {job_id}: selected_format='{file_format}', title='{track_title}', artist='{artist_name}', album='{album_name}', effective_artist='{effective_artist_name}'",
        flush=True
    )

    conn = get_db_connection()
    cur = conn.cursor()
    metadata_rows = _lookup_plex_songs(cur, track_title, artist_name, album_name)
    conn.close()

    ignore_matches = bool(payload.get('ignore_matches', False))
    matching_rows = []
    if not ignore_matches:
        matching_rows = [row for row in metadata_rows if _matches_requested_format(file_format, row.get('format'))]

    # If downloading MP3, skip the "existing match" shortcut for low-quality copies (≤192 kbps).
    # Those will be re-downloaded and overwrite the existing file.
    low_quality_mp3_rows = []
    if file_format == 'mp3':
        kept, low_quality_mp3_rows = [], []
        for row in matching_rows:
            if (_matches_requested_format('mp3', row.get('format'))
                    and isinstance(row.get('bitrate'), int)
                    and row['bitrate'] <= 192):
                low_quality_mp3_rows.append(row)
            else:
                kept.append(row)
        matching_rows = kept

    is_upgrading = not matching_rows and bool(low_quality_mp3_rows)
    upgrade_from_bitrate = low_quality_mp3_rows[0].get('bitrate') if is_upgrading else None

    summary_rows = [
        {
            'format': str(row.get('format') or '').strip().lower() or 'unknown',
            'bitrate': row.get('bitrate'),
            'album': row.get('album')
        }
        for row in metadata_rows[:8]
    ]
    print(
        f"[DOWNLOAD_DECISION] Job {job_id}: metadata_candidates={len(metadata_rows)}, matching_selected_format={len(matching_rows)}, candidate_summary={summary_rows}",
        flush=True
    )
    if is_upgrading:
        print(
            f"[DOWNLOAD_DECISION] Job {job_id}: re-downloading to upgrade existing MP3 ({upgrade_from_bitrate} kbps ≤ 192 threshold)",
            flush=True
        )

    if matching_rows:
        matched_row = matching_rows[0]
        matched_path = str(matched_row.get('file_path') or '').strip()
        if matched_path:
            full_path = matched_path
        print(
            f"[DOWNLOAD_DECISION] Job {job_id}: skipping download because existing Plex inventory metadata matches selected format and quality (format='{matched_row.get('format')}', bitrate='{matched_row.get('bitrate')}')",
            flush=True
        )
        print(f"[DOWNLOAD] Existing metadata match found - skipping download pipeline", flush=True)
        stages['downloaded'] = 'done'
        stages['id3_tagged'] = 'done'
        stages['converted'] = 'done' if file_format == 'mp3' else 'skipped'
        stages['written'] = 'done'
        set_last_download_activity_at(datetime.utcnow())
        update_job_progress(job_id, {
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': payload.get('plex_playlist'),
            'stages': stages
        })

        playlist_name = payload.get('plex_playlist')
        if playlist_name:
            queue_pending_playlist_addition(
                artist_name,
                album_name,
                track_title,
                full_path,
                playlist_name,
                parent_job_id=job_id,
                plex_user_id=payload.get('plex_user_id')
            )
            stages['playlist_added'] = 'queued'
            print("[DOWNLOAD] Playlist requested - queued separate plex_playlist_add job", flush=True)
        else:
            print("[DOWNLOAD] Plex playlist update skipped. No playlist requested.", flush=True)
            stages['playlist_added'] = 'skipped'
        update_job_progress(job_id, {'stages': stages})

        return {
            'file_path': full_path,
            'format': file_format,
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': playlist_name,
            'download_skipped_existing': True,
            'stages': stages
        }

    print(
        f"[DOWNLOAD_DECISION] Job {job_id}: downloading because no existing Plex inventory metadata matched selected format '{file_format}'",
        flush=True
    )

    update_job_progress(job_id, {
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': payload.get('plex_playlist'),
        'stages': stages
    })

    quality_candidates = []
    media_tags = []
    audio_quality = None
    if isinstance(track_metadata, dict):
        audio_quality = track_metadata.get('audioQuality')
        media_meta = track_metadata.get('mediaMetadata')
        if isinstance(media_meta, dict):
            tags = media_meta.get('tags', [])
            if isinstance(tags, list):
                media_tags = tags

    if isinstance(audio_quality, str) and audio_quality:
        media_tags.append(audio_quality)

    quality_priority = ['HI_RES_LOSSLESS', 'HIRES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW']
    for quality in quality_priority:
        if quality in media_tags and quality not in quality_candidates:
            quality_candidates.append(quality)

    if not quality_candidates:
        quality_candidates = ['HIGH', 'LOW']

    print(f"[DOWNLOAD] Available quality tags, selected: {quality_candidates}", flush=True)

    print(f"[DOWNLOAD] Fetching track manifest...", flush=True)
    manifest_base64 = None
    last_manifest_status = None
    manifest_error_message = None

    for quality in quality_candidates:
        try:
            manifest_response, target = make_request_with_retry_rotating_mirrors(
                f"/track/?id={track_id}&quality={quality}",
                SQUID_URLS,
                method='GET',
                timeout=10,
                max_retries=3
            )
        except requests.exceptions.RequestException as e:
            manifest_error_message = str(e)
            print(f"[DOWNLOAD] Quality '{quality}' manifest fetch failed: {manifest_error_message}", flush=True)
            continue

        last_manifest_status = manifest_response.status_code
        mirror_name = target.get('name') if isinstance(target, dict) else 'unknown'

        print(
            f"[DOWNLOAD] Track manifest request via mirror '{mirror_name}' quality='{quality}' got status {manifest_response.status_code}",
            flush=True
        )

        if manifest_response.status_code in (401, 403):
            body_text = manifest_response.text or ''
            manifest_error_message = f"{manifest_response.status_code}: {body_text.strip()}"
            print(
                f"[DOWNLOAD] Quality '{quality}' returned {manifest_response.status_code}. Trying next quality if available...",
                flush=True
            )
            continue

        if not manifest_response.ok:
            print(
                f"[DOWNLOAD] Mirror '{mirror_name}' returned non-OK status {manifest_response.status_code} for quality '{quality}'",
                flush=True
            )
            manifest_error_message = f"{manifest_response.status_code}: {manifest_response.text or ''}".strip()
            continue

        manifest_data = manifest_response.json()
        print(f"[DOWNLOAD] Track info response keys: {manifest_data.keys()}", flush=True)

        manifest_mime_type = None
        if isinstance(manifest_data, dict):
            data = manifest_data.get('data')
            if isinstance(data, dict):
                manifest_base64 = data.get('manifest') or data.get('manifestBase64')
                manifest_mime_type = data.get('manifestMimeType')

            if not manifest_base64:
                manifest_base64 = manifest_data.get('manifest') or manifest_data.get('manifestBase64')
            if not manifest_mime_type:
                manifest_mime_type = manifest_data.get('manifestMimeType')

        if manifest_mime_type == 'application/dash+xml':
            print(f"[DOWNLOAD] Quality {quality} returned MPD/DASH manifest (not supported), trying next quality...", flush=True)
            manifest_base64 = None
            continue

        if isinstance(manifest_base64, str) and manifest_base64:
            break

    if not isinstance(manifest_base64, str) or not manifest_base64:
        status_note = f" Status: {last_manifest_status}" if last_manifest_status is not None else ""
        error_note = f" Last error: {manifest_error_message}" if manifest_error_message else ""
        raise ManifestDownloadError(f"Failed to get track manifest.{status_note}{error_note}")

    print(f"[DOWNLOAD] Got base64 manifest (length: {len(manifest_base64)})", flush=True)

    normalized = manifest_base64.replace('-', '+').replace('_', '/')
    padding = '=' * (-len(normalized) % 4)
    manifest_json_bytes = base64.b64decode(normalized + padding)
    manifest_json = manifest_json_bytes.decode('utf-8')
    print(f"[DOWNLOAD] Decoded manifest: {manifest_json}", flush=True)

    manifest = json.loads(manifest_json)
    print(f"[DOWNLOAD] Parsed manifest keys: {manifest.keys()}", flush=True)

    if 'urls' not in manifest or not manifest['urls']:
        raise Exception('No download URLs found in manifest')

    download_urls = manifest['urls']
    if not isinstance(download_urls, list) or len(download_urls) == 0:
        raise Exception('Invalid URLs format in manifest')

    download_url = download_urls[0]
    print(f"[DOWNLOAD] Download URL: {download_url}", flush=True)

    print(f"[DOWNLOAD] File path template result: {file_path}", flush=True)

    print(f"[DOWNLOAD] Full output path: {full_path}", flush=True)

    output_dir = os.path.dirname(full_path)
    print(f"[DOWNLOAD] Creating directory structure: {output_dir}", flush=True)

    os.makedirs(output_dir, exist_ok=True)
    print(f"[DOWNLOAD] SUCCESS: Directory created/exists: {output_dir}", flush=True)

    print(f"[DOWNLOAD] Downloading from CDN...", flush=True)
    try:
        track_response = make_request_with_retry(download_url, method='GET', timeout=60, max_retries=3, backoff_factor=2.0)
    except requests.exceptions.RequestException as e:
        raise TransientDownloadError(f"Failed to download track from CDN: {str(e)}") from e

    if not track_response.ok:
        raise TransientDownloadError(f"Failed to download track from CDN. Status: {track_response.status_code}")

    print(f"[DOWNLOAD] Downloaded {len(track_response.content)} bytes", flush=True)

    audio_format = detect_audio_format(track_response.content)
    print(f"[DOWNLOAD] Detected audio format: {audio_format}", flush=True)

    if audio_format == 'unknown':
        print(f"[DOWNLOAD] WARNING: Could not detect audio format, assuming FLAC", flush=True)
        audio_format = 'flac'

    cover_image_data = None
    if cover_url:
        cover_image_data = download_cover_image(cover_url)

    metadata_dict = {
        'artist': artist_name,
        'album_artist': album_artist_name,
        'title': track_title,
        'album': album_name,
        'year': release_year,
        'track_number': track_num,
        'disc_number': disc_num,
        'version': track_version,
        'copyright': copyright_text,
        'tidal_track_id': track_id,
        'tidal_album_id': album_id
    }

    temp_folder = '/app/temp'
    os.makedirs(temp_folder, exist_ok=True)

    temp_source_ext = audio_format if audio_format in ['flac', 'm4a'] else 'flac'
    temp_source_path = os.path.join(temp_folder, f'temp_{track_id}.{temp_source_ext}')
    temp_mp3_path = os.path.join(temp_folder, f'temp_{track_id}.mp3')

    print(f"[DOWNLOAD] Saving temporary {temp_source_ext.upper()}: {temp_source_path}", flush=True)

    with open(temp_source_path, 'wb') as f:
        f.write(track_response.content)

    stages['downloaded'] = 'done'
    set_last_download_activity_at(datetime.utcnow())
    update_job_progress(job_id, {'stages': stages})

    print(f"[DOWNLOAD] Adding metadata to staged {temp_source_ext.upper()}...", flush=True)
    add_id3_tags_to_file(temp_source_path, metadata_dict, cover_image_data)
    stages['id3_tagged'] = 'done'
    update_job_progress(job_id, {'stages': stages})

    if file_format == 'mp3':
        print(f"[DOWNLOAD] Format is MP3 - converting staged {temp_source_ext.upper()}", flush=True)

        success = convert_to_mp3(temp_source_path, temp_mp3_path, source_format=temp_source_ext)

        if not success:
            cleanup_file(temp_source_path)
            cleanup_file(temp_mp3_path)
            raise Exception(f"Failed to convert {temp_source_ext.upper()} to MP3")

        shutil.move(temp_mp3_path, full_path)

        # Ensure final MP3 has correct ID3 metadata after conversion.
        add_id3_tags_to_file(full_path, metadata_dict, cover_image_data)

        stages['converted'] = 'done'
        stages['written'] = 'done'
        set_last_download_activity_at(datetime.utcnow())
        update_job_progress(job_id, {'stages': stages})
        cleanup_file(temp_source_path)
        cleanup_file(temp_mp3_path)

        print(f"[DOWNLOAD] SUCCESS: Converted and saved MP3 to {full_path}", flush=True)
    else:
        original_ext = 'm4a' if audio_format == 'm4a' else 'flac'

        if not full_path.endswith(f'.{original_ext}'):
            full_path = full_path.rsplit('.', 1)[0] + f'.{original_ext}'
            print(f"[DOWNLOAD] Updated output path with correct extension: {full_path}", flush=True)

        print(f"[DOWNLOAD] Format is original ({original_ext.upper()}) - moving from temp", flush=True)
        shutil.move(temp_source_path, full_path)
        stages['converted'] = 'skipped'
        stages['written'] = 'done'
        set_last_download_activity_at(datetime.utcnow())
        update_job_progress(job_id, {'stages': stages})
        cleanup_file(temp_source_path)
        print(f"[DOWNLOAD] SUCCESS: Downloaded and saved to {full_path}", flush=True)

    playlist_name = payload.get('plex_playlist')
    if playlist_name:
        queue_pending_playlist_addition(
            artist_name,
            album_name,
            track_title,
            full_path,
            playlist_name,
            parent_job_id=job_id,
            plex_user_id=payload.get('plex_user_id')
        )
        stages['playlist_added'] = 'queued'
        print("[DOWNLOAD] Playlist requested - queued separate plex_playlist_add job", flush=True)
    else:
        print("[DOWNLOAD] Plex playlist update skipped. No playlist requested.", flush=True)
        stages['playlist_added'] = 'skipped'
    if is_upgrading:
        stages['upgraded_existing'] = 'done'
    update_job_progress(job_id, {'stages': stages})

    result = {
        'file_path': full_path,
        'format': file_format,
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': playlist_name,
        'stages': stages
    }
    if is_upgrading:
        result['download_upgraded_existing'] = True
        result['upgraded_from_bitrate'] = upgrade_from_bitrate
    return result

def download_job_worker():
    print("[DOWNLOAD_WORKER] Background worker started", flush=True)

    while True:
        try:
            job = claim_next_job('download_track')
            if not job:
                time.sleep(2)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_download_job(job['id'], payload)
                stages = result.get('stages') if isinstance(result, dict) else {}

                if _download_track_all_stages_done(stages):
                    mark_job_succeeded(job['id'], result)
                    print(f"[DOWNLOAD_WORKER] Job {job['id']} completed", flush=True)
                elif isinstance(stages, dict) and stages.get('playlist_added') == 'queued':
                    mark_job_in_progress(job['id'])
                    print(f"[DOWNLOAD_WORKER] Job {job['id']} waiting for playlist_add completion", flush=True)
                else:
                    stage_state = stages if isinstance(stages, dict) else {}
                    error_message = f"Download stages incomplete: {serialize_job_payload(stage_state)}"
                    print(f"[DOWNLOAD_WORKER] Job {job['id']} failed: {error_message}", flush=True)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_message)
            except PermanentDownloadError as e:
                print(f"[DOWNLOAD_WORKER] Job {job['id']} failed (permanent): {str(e)}", flush=True)
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
            except (ManifestDownloadError, TransientDownloadError) as e:
                if job['attempt_count'] + 1 >= job['max_attempts']:
                    print(f"[DOWNLOAD_WORKER] Job {job['id']} failed: {str(e)}", flush=True)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                else:
                    print(f"[DOWNLOAD_WORKER] Job {job['id']} retrying (manifest fetch): {str(e)}", flush=True)
                    mark_job_retrying(job['id'], job['attempt_count'], str(e))
                time.sleep(1)
            except Exception as e:
                print(f"[DOWNLOAD_WORKER] Job {job['id']} failed: {str(e)}", flush=True)
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            print(f"[DOWNLOAD_WORKER] Error in background worker: {str(e)}", flush=True)
            time.sleep(5)

def retry_pending_playlist_additions():
    """Background worker that periodically retries failed playlist additions."""
    print("[PLEX_WORKER] Background worker started", flush=True)
    
    while True:
        try:
            # Wait 5 minutes between retry attempts
            time.sleep(300)
            
            plex_config = get_plex_config()
            
            # Skip if Plex is not configured
            if not (plex_config['server_url'] and plex_config['api_token']):
                continue
            
            pending = get_pending_playlist_additions()
            
            if not pending:
                continue
            
            print(f"[PLEX_WORKER] Found {len(pending)} pending playlist additions to retry", flush=True)
            
            for addition in pending:
                parent_job_id = None
                try:
                    payload = addition.get('payload') or {}
                    parent_job_id = payload.get('parent_job_id')
                    artist = payload.get('artist', 'Unknown Artist')
                    title = payload.get('title', 'Unknown Track')
                    file_path = str(payload.get('file_path') or '').strip()
                    playlist_name = payload.get('playlist_name')
                    
                    success, message = add_tracks_to_plex_playlist(
                        plex_config['server_url'],
                        plex_config['api_token'],
                        plex_config['library_name'] or 'Music',
                        playlist_name,
                        file_path,
                        payload.get('plex_user_id')
                    )
                    
                    if success:
                        print(f"[PLEX_WORKER] Successfully added: {artist} - {title}", flush=True)
                        remove_pending_addition(addition['id'])
                        update_parent_playlist_stage(parent_job_id, 'done')
                    else:
                        update_pending_addition_attempt(addition['id'], message)
                        if addition['attempt_count'] + 1 >= addition['max_attempts']:
                            update_parent_playlist_stage(parent_job_id, 'failed')
                            print(f"[PLEX_WORKER] Max attempts reached for: {artist} - {title}", flush=True)
                        else:
                            print(f"[PLEX_WORKER] Retry failed (attempt {addition['attempt_count'] + 1}/{addition['max_attempts']}): {message}", flush=True)
                    
                    # Small delay between tracks to avoid hammering Plex
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[PLEX_WORKER] Error processing addition {addition['id']}: {str(e)}", flush=True)
                    update_pending_addition_attempt(addition['id'], str(e))
                    if addition['attempt_count'] + 1 >= addition['max_attempts']:
                        update_parent_playlist_stage(parent_job_id, 'failed')
        
        except Exception as e:
            print(f"[PLEX_WORKER] Error in background worker: {str(e)}", flush=True)
            # Continue running even if there's an error
            time.sleep(60)


def seed_mirrors_from_json():
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Clear existing entries
    cur.execute("DELETE FROM mirror_endpoints")
    
    # Insert fresh data from JSON with initial values
    for entry in urls_data:
        cur.execute(
            """
            INSERT INTO mirror_endpoints (name, encoded_url, online, response_time, last_checked)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                entry.get('name'),
                entry.get('encodedUrl'),
                0,
                None,
                None
            )
        )
    
    conn.commit()
    conn.close()

def get_download_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album, jobs_refresh_interval_seconds, ignore_matches
        FROM download_settings
        WHERE id = 1
        """
    )
    row = cur.fetchone()

    if row is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            INSERT INTO download_settings (
                id, format, parent_folder, file_naming, file_naming_loose, file_naming_album, jobs_refresh_interval_seconds, ignore_matches, updated_at
            )
            VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                DEFAULT_DOWNLOAD_SETTINGS['format'],
                DEFAULT_DOWNLOAD_SETTINGS['parent_folder'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds'],
                DEFAULT_DOWNLOAD_SETTINGS['ignore_matches'],
                now
            )
        )
        conn.commit()
        cur.execute(
            """
            SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album, jobs_refresh_interval_seconds, ignore_matches
            FROM download_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()

    file_naming_loose = row['file_naming_loose'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose']
    file_naming_album = row['file_naming_album'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']
    jobs_refresh_interval_seconds = row['jobs_refresh_interval_seconds']
    if not isinstance(jobs_refresh_interval_seconds, int) or jobs_refresh_interval_seconds < 1:
        jobs_refresh_interval_seconds = DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds']
    
    ignore_matches = bool(row['ignore_matches'])

    if row['file_naming_loose'] is None or row['file_naming_album'] is None or row['jobs_refresh_interval_seconds'] is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            UPDATE download_settings
            SET file_naming_loose = %s, file_naming_album = %s, jobs_refresh_interval_seconds = %s, updated_at = %s
            WHERE id = 1
            """,
            (
                file_naming_loose,
                file_naming_album,
                jobs_refresh_interval_seconds,
                now
            )
        )
        conn.commit()

    conn.close()
    return {
        'format': row['format'],
        'parent_folder': row['parent_folder'],
        'file_naming': file_naming_loose,
        'file_naming_loose': file_naming_loose,
        'file_naming_album': file_naming_album,
        'jobs_refresh_interval_seconds': jobs_refresh_interval_seconds,
        'ignore_matches': ignore_matches
    }

def save_download_settings(settings):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO download_settings (
            id, format, parent_folder, file_naming, file_naming_loose, file_naming_album, jobs_refresh_interval_seconds, ignore_matches, updated_at
        )
        VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            format = excluded.format,
            parent_folder = excluded.parent_folder,
            file_naming = excluded.file_naming,
            file_naming_loose = excluded.file_naming_loose,
            file_naming_album = excluded.file_naming_album,
            jobs_refresh_interval_seconds = excluded.jobs_refresh_interval_seconds,
            ignore_matches = excluded.ignore_matches,
            updated_at = excluded.updated_at
        """,
        (
            settings['format'],
            settings['parent_folder'],
            settings['file_naming_loose'],
            settings['file_naming_loose'],
            settings['file_naming_album'],
            settings['jobs_refresh_interval_seconds'],
            bool(settings.get('ignore_matches', False)),
            now
        )
    )
    conn.commit()
    conn.close()

# Plex Functions
def test_plex_connection(server_url, api_token):
    """
    Test connection to Plex server by making a direct API request.
    Returns tuple: (success: bool, message: str, libraries: list or None)
    """
    try:
        # Remove trailing slash if present
        server_url = server_url.rstrip('/')
        
        # Validate URL format
        if not server_url.startswith('http://') and not server_url.startswith('https://'):
            return False, 'Server URL must start with http:// or https://', None
        
        # Test connection with a direct HTTP request to validate token
        test_url = f"{server_url}/library/sections"
        headers = {'X-Plex-Token': api_token}
        
        print(f"[PLEX] Testing connection to {test_url}", flush=True)
        response = requests.get(test_url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 401:
            return False, 'Invalid API token or unauthorized access', None
        elif response.status_code == 404:
            return False, 'Server not found at URL', None
        elif not response.ok:
            return False, f'Server returned status {response.status_code}', None
        
        # If we got here, connection is valid. Now try with plexapi to get libraries
        try:
            plex = PlexServer(server_url, api_token, timeout=10)
            
            # Get music libraries
            libraries = []
            for section in plex.library.sections():
                if section.type == 'artist':  # Music library
                    libraries.append(section.title)
            
            return True, 'Successfully connected to Plex server', libraries
        except Exception as e:
            # Connection works but plexapi failed - still report success with libraries from HTTP response
            print(f"[PLEX] Warning: PlexAPI failed but HTTP connection worked: {str(e)}", flush=True)
            return True, 'Connected successfully (could not retrieve libraries)', []
    
    except requests.exceptions.Timeout:
        return False, 'Connection timeout - server not responding', None
    except requests.exceptions.ConnectionError:
        return False, 'Cannot connect to server - check URL and network', None
    except Exception as e:
        error_msg = str(e)
        print(f"[PLEX] Connection test failed: {error_msg}", flush=True)
        return False, f'Failed to connect to Plex: {error_msg}', None

def _get_plex_server_for_user(server_url, api_token, user_id=None):
    """Return a PlexServer instance for the given user (main owner or managed)."""
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
                # Try several fields that may represent the identifier
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
                        # Use the PlexServer.switchUser method so playlists and other calls are executed under the managed user.
                        return plex.switchUser(u)
                    except Exception as e:
                        print(f"[PLEX] Failed to switch to managed user {user_id_str}: {e}", flush=True)
                        # Continue searching in case multiple managed users match the provided identifier.
                        continue
        except Exception as e:
            print(f"[PLEX] Failed to fetch managed users for user selection {user_id}: {e}", flush=True)

        return plex
    except Exception as e:
        print(f"[PLEX] Failed to create PlexServer for user {user_id}: {e}", flush=True)
        raise


def get_plex_music_playlists(server_url, api_token, user_id=None):
    """
    Get existing Plex music playlists, excluding smart playlists.

    Returns:
        tuple: (success: bool, playlists: list[str], error: str | None)
    """
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
    """
    Add downloaded tracks to a Plex playlist.
    
    Args:
        server_url: Plex server URL
        api_token: Plex API token
        library_name: Name of the music library (e.g., "Music")
        playlist_name: Name of the playlist to add to
        full_path: Full path of the downloaded (or matched) file
        user_id: Optional user ID/username/title to use when applying managed user context
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        server_url = server_url.rstrip('/')
        token_len = len(api_token) if isinstance(api_token, str) else 0
        print(
            f"[PLEX] Add-to-playlist start: url={server_url}, library='{library_name}', playlist='{playlist_name}', token_len={token_len}, user_id={user_id}",
            flush=True
        )
        plex = _get_plex_server_for_user(server_url, api_token, user_id)
        print("[PLEX] Connected to Plex server", flush=True)
        
        # Get the music library
        library = None
        for section in plex.library.sections():
            if section.title == library_name and section.type == 'artist':
                library = section
                break
        
        if not library:
            available = [f"{section.title} ({section.type})" for section in plex.library.sections()]
            print(f"[PLEX] Library not found. Available sections: {available}", flush=True)
            return False, f'Library "{library_name}" not found or is not a music library'

        # Resolve track by ratingKey from local plex_songs inventory using only the last 3 path parts
        raw_full_path = str(full_path or '').strip()
        if not raw_full_path:
            return False, 'file_path is required to resolve Plex ratingKey'

        path_parts = [part for part in re.split(r'[\\/]+', raw_full_path) if part]
        if not path_parts:
            return False, 'file_path is required to resolve Plex ratingKey'

        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        normalized_file_path = '\\'.join(tail_parts)
        trailing_suffix = '/'.join(tail_parts)
        print(f"[PLEX] Resolving ratingKey via plex_songs for file_path={normalized_file_path}", flush=True)

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

        first_row = rating_rows[0] if rating_rows else {}
        resolved_title = str(first_row.get('title') or 'Unknown').strip() or 'Unknown'
        resolved_artist = str(first_row.get('artist') or 'Unknown').strip() or 'Unknown'

        rating_keys = [
            str(row.get('ratingKey') or '').strip()
            for row in rating_rows
            if str(row.get('ratingKey') or '').strip()
        ]

        if not rating_keys:
            print(f"[PLEX] No ratingKey found in plex_songs for file_path={normalized_file_path}", flush=True)
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
                    print(f"[PLEX] Resolved track using ratingKey={rating_key}", flush=True)
                    break
            except Exception as e:
                print(f"[PLEX] Failed to fetch item for ratingKey={rating_key}: {str(e)}", flush=True)

        if track is None:
            return False, (
                f'Could not resolve Plex track for file_path "{normalized_file_path}" using stored ratingKeys. '
                'Run a Plex library sync to refresh plex_songs.'
            )
        
        # Get or create the playlist
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
        
        # Create playlist if it doesn't exist
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
        
        # Add track to existing playlist
        try:
            playlist.addItems(track)
            print(f"[PLEX] Added track to playlist: {playlist_name}", flush=True)
            return True, f'Added track to playlist "{playlist_name}"'
        except Exception as e:
            # Check if track already in playlist
            if 'already in' in str(e).lower():
                return True, f'Track already in playlist "{playlist_name}" ({resolved_artist} - {resolved_title})'
            print(f"[PLEX] Error adding track to playlist: {str(e)}", flush=True)
            return False, f'Error adding to playlist: {str(e)}'
    
    except Exception as e:
        print(f"[PLEX] Unexpected error: {str(e)}", flush=True)
        return False, f'Unexpected error: {str(e)}'

# Validation Functions
def validate_endpoint(url, name, timeout=5):
    """
    Validate a single endpoint using the upstream health check (GET /).
    Records response time and whether the mirror is reachable and returning valid JSON.

    Args:
        url: Base URL of the endpoint
        name: Name of the endpoint
        timeout: Request timeout in seconds

    Returns:
        Dict with validation results including online status and response time
    """
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        start_time = time.time()
        response = requests.get(f"{url}/", timeout=timeout)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        online = False
        error = None

        if response.status_code == 200:
            try:
                response.json()
                online = True
            except json.JSONDecodeError:
                error = 'Invalid JSON response'
        else:
            error = f'HTTP {response.status_code}'

        return {
            'online': online,
            'responseTime': round(response_time, 2) if online else None,
            'lastChecked': timestamp,
            'error': error
        }

    except requests.exceptions.Timeout:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'error': 'Timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'error': str(e)
        }

def validate_all_endpoints():
    """
    Validate all squid endpoints on startup.
    Returns validation summary.
    """
    print("\n" + "="*60, flush=True)
    print("Starting Squid URL Validation", flush=True)
    print("="*60, flush=True)
    
    # Load current URLs
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)
    
    online_count = 0
    offline_count = 0

    conn = get_db_connection()
    cur = conn.cursor()

    # Validate each endpoint
    for entry in urls_data:
        name = entry['name']
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')

        print(f"\n[{name}] Checking {decoded_url}...", flush=True)

        result = validate_endpoint(decoded_url, name, timeout=5)

        # Update database with results
        cur.execute(
            """
            UPDATE mirror_endpoints
            SET online = %s, response_time = %s, last_checked = %s
            WHERE name = %s
            """,
            (
                1 if result['online'] else 0,
                result['responseTime'],
                result['lastChecked'],
                name
            )
        )

        if result['online']:
            online_count += 1
            print(f"  ✓ ONLINE - Response time: {result['responseTime']}ms", flush=True)
        else:
            offline_count += 1
            print(f"  ✗ OFFLINE - {result.get('error', 'Unknown error')}", flush=True)

    conn.commit()
    conn.close()

    # Print summary
    print("\n" + "="*60, flush=True)
    print("Validation Complete", flush=True)
    print("="*60, flush=True)
    print(f"Total endpoints: {len(urls_data)}", flush=True)
    print(f"Online: {online_count}", flush=True)
    print(f"Offline: {offline_count}", flush=True)
    print("="*60 + "\n", flush=True)

    return {
        'total': len(urls_data),
        'online': online_count,
        'offline': offline_count
    }

# Load squid URLs and set up round-robin
def load_squid_urls():
    """Load and decode squid URLs from JSON file"""
    with open('squidurls.json', 'r', encoding='utf-8') as f:
        urls_data = json.load(f)
    
    decoded_urls = []
    for entry in urls_data:
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')
        decoded_urls.append({
            'name': entry['name'],
            'url': decoded_url
        })
    
    return decoded_urls

# Initialize SQLite and mirror data
init_db()
init_library_update_status()
recover_stale_in_progress_jobs(stale_after_minutes=15)
seed_mirrors_from_json()

# Initialize URL list and round-robin iterator
SQUID_URLS = load_squid_urls()
url_iterator = cycle(SQUID_URLS)

# Run validation on startup
# With gunicorn --preload, this runs once before workers are forked
print("Squidly starting up...", flush=True)
validate_all_endpoints()
backfill_plex_playlist_add_parent_links()
plex_healthcheck()

# Start background worker for retrying failed Plex playlist additions
plex_retry_thread = threading.Thread(target=retry_pending_playlist_additions, daemon=True)
plex_retry_thread.start()
print("Plex playlist retry worker started\n", flush=True)

# Start background worker for processing download jobs

# Start background worker for processing download jobs
download_worker_thread = threading.Thread(target=download_job_worker, daemon=True)
download_worker_thread.start()
print("Download job worker started\n", flush=True)

# Start background worker for Plex library sync jobs
plex_sync_worker_thread = threading.Thread(target=plex_sync_job_worker, daemon=True)
plex_sync_worker_thread.start()
print("Plex library sync job worker started\n", flush=True)

# Start background worker for Plex library update jobs
plex_library_update_worker_thread = threading.Thread(target=plex_library_update_job_worker, daemon=True)
plex_library_update_worker_thread.start()
print("Plex library update job worker started\n", flush=True)

# Start scheduler for interval-based Plex sync jobs
plex_sync_scheduler_thread = threading.Thread(target=plex_sync_scheduler_worker, daemon=True)
plex_sync_scheduler_thread.start()
print("Plex library sync scheduler started\n", flush=True)

# Legacy timed library update worker is intentionally disabled.
# Updates are now queued on download enqueue and gated in process_plex_library_update_job.

# Download folders already created and validated at module level above

try:
    os.makedirs('/app/temp', exist_ok=True)
    print("Temp folder ready (/app/temp)", flush=True)
except Exception as e:
    print(f"WARNING: Failed to create temp folder: {str(e)}", flush=True)


# Helper to check if Plex credentials are valid
def get_plex_credentials_valid():
    ok, _ = plex_healthcheck()
    return ok

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html', plex_credentials_valid=get_plex_credentials_valid())

@app.route('/search/', methods=['GET'])
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
            response, target = make_request_with_retry_rotating_mirrors(
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

            # Coerce to track-list shape for front-end
            return jsonify({
                'data': {'items': [track_item]},
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
        response, target = make_request_with_retry_rotating_mirrors(
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
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e),
            'query': query
        }), 502

@app.route('/info/', methods=['GET'])
def track_info():
    """
    Get detailed track metadata.
    Query parameter:
    - id={trackId} : Tidal track ID
    """
    track_id = (request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    upstream_query = urlencode({'id': track_id})
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
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

@app.route('/album/', methods=['GET'])
def album_info():
    """
    Get album with all tracks.
    Query parameter:
    - id={albumId} : Tidal album ID
    """
    album_id = request.args.get('id', '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID parameter must be a numeric Tidal album ID'}), 400

    params = {'id': album_id}
    limit = request.args.get('limit')
    offset = request.args.get('offset')
    if limit is not None:
        params['limit'] = limit
    if offset is not None:
        params['offset'] = offset

    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/album/?{urlencode(params)}",
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

@app.route('/artist/', methods=['GET'])
def artist_info():
    """
    Get artist with all albums.
    Query parameter:
    - f={artistId} : Tidal artist ID
    """
    artist_id = request.args.get('f', '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID parameter (f) is required'}), 400

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID parameter must be a numeric Tidal artist ID'}), 400

    params = {'f': artist_id}
    skip_tracks = request.args.get('skip_tracks')
    if skip_tracks is not None:
        params['skip_tracks'] = skip_tracks

    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/artist/?{urlencode(params)}",
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

@app.route('/playlist/', methods=['GET'])
def playlist_info():
    """
    Get playlist with all tracks.
    Query parameter:
    - id={playlistId} : Tidal playlist UUID
    """
    playlist_id = request.args.get('id', '').strip()

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
        response, target = make_request_with_retry_rotating_mirrors(
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
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502

@app.route('/track/', methods=['GET'])
def track_download():
    """
    Get track download/streaming manifest.
    Query parameters:
    - id={trackId} : Tidal track ID
    - quality={quality} : Quality level (HI_RES_LOSSLESS, LOSSLESS, HIGH, LOW)
    """
    track_id = request.args.get('id', '').strip()
    quality = request.args.get('quality', 'HIGH')

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    valid_qualities = {'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW'}
    if quality not in valid_qualities:
        return jsonify({'error': 'Invalid quality. Must be one of: ' + ', '.join(sorted(valid_qualities))}), 400

    try:
        response, target = make_request_with_retry_rotating_mirrors(
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

@app.route('/recommendations/', methods=['GET'])
def track_recommendations():
    """
    Get recommendations for a track.
    Query parameter:
    - id={trackId} : Tidal track ID
    """
    track_id = (request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    params = {'id': track_id}

    try:
        response, target = make_request_with_retry_rotating_mirrors(
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

@app.route('/artist/similar/', methods=['GET'])
def artist_similar():
    """
    Get similar artists.
    Query parameters:
    - id={artistId} : Tidal artist ID
    - cursor={cursor} : Optional cursor for paginated results
    """
    artist_id = (request.args.get('id') or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID parameter must be a numeric Tidal artist ID'}), 400

    params = {'id': artist_id}
    cursor = request.args.get('cursor')
    if cursor is not None:
        params['cursor'] = cursor

    try:
        response, target = make_request_with_retry_rotating_mirrors(
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

@app.route('/album/similar/', methods=['GET'])
def album_similar():
    """
    Get similar albums.
    Query parameters:
    - id={albumId} : Tidal album ID
    - cursor={cursor} : Optional cursor for paginated results
    """
    album_id = (request.args.get('id') or '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID parameter must be a numeric Tidal album ID'}), 400

    params = {'id': album_id}
    cursor = request.args.get('cursor')
    if cursor is not None:
        params['cursor'] = cursor

    try:
        response, target = make_request_with_retry_rotating_mirrors(
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
        print(f"Last.fm scraping error: {e}", flush=True)
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
            artist_name = ', '.join(artist_names).strip()

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
        print(f"YouTube Music playlist parsing error: {e}", flush=True)
        return jsonify({
            'error': 'Failed to process YouTube Music playlist',
            'details': str(e)
        }), 500

def format_tidal_image_url(image_id_or_path: str, size: int) -> str:
    """
    Format a Tidal CDN image URL from a UUID/path and requested square size.

    Args:
        image_id_or_path: Tidal image UUID/path (may contain dashes)
        size: Square image size in pixels

    Returns:
        Full URL to the image
    """
    if not image_id_or_path:
        return ''

    image_path = image_id_or_path.replace('-', '/')
    return f"https://resources.tidal.com/images/{image_path}/{size}x{size}.jpg"

def sanitize_filename_component(value: str) -> str:
    """
    Sanitize a single filename or folder name component by removing/replacing invalid characters.
    This should be called on individual metadata values (artist, album, title) before substituting
    them into path templates.
    
    Args:
        value: A single component value (artist name, track title, etc.)
    
    Returns:
        Sanitized component safe for use in filenames
    """
    if not value:
        return value
    
    # Replace slashes (both forward and back) to prevent unintended subdirectories
    sanitized = value.replace('/', '-').replace('\\', '-')
    
    # Remove or replace other invalid characters on Windows: < > : " | ? *
    sanitized = sanitized.replace('<', '').replace('>', '')
    sanitized = sanitized.replace(':', '-').replace('"', "'")
    sanitized = sanitized.replace('|', '-').replace('?', '')
    sanitized = sanitized.replace('*', '')
    
    # Replace various Unicode apostrophes and quotes with ASCII equivalents
    sanitized = sanitized.replace('\u2018', "'").replace('\u2019', "'")  # ' '
    sanitized = sanitized.replace('\u201c', '"').replace('\u201d', '"')  # " "
    sanitized = sanitized.replace('\u2013', '-').replace('\u2014', '-')  # – —
    
    # Remove control characters (ASCII 0-31)
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    # Strip trailing periods and spaces (invalid on Windows)
    sanitized = sanitized.rstrip('. ')
    
    # Strip leading spaces
    sanitized = sanitized.lstrip(' ')
    
    # If the entire component was invalid, use a placeholder
    if not sanitized:
        sanitized = '_'
    
    return sanitized

def clean_path_components(file_path: str) -> str:
    """
    Clean file path by removing trailing periods and spaces from each directory component.
    This is a final cleanup after template substitution.
    
    Args:
        file_path: File path with potential trailing periods/spaces in components
    
    Returns:
        Cleaned file path
    """
    # Split path into components
    parts = file_path.replace('\\', '/').split('/')
    # Strip trailing periods and spaces from each component
    cleaned_parts = [part.rstrip('. ') if part else part for part in parts]
    # Rejoin with forward slashes
    return '/'.join(cleaned_parts)

def extract_year_from_text(text: str) -> str:
    """
    Extract a 4-digit year from a string like a copyright notice.
    Returns empty string if none found.
    """
    if not text or not isinstance(text, str):
        return ''
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else ''

def _requested_download_format(file_format):
    normalized = str(file_format or 'original').strip().lower()
    if normalized not in ('original', 'mp3'):
        return 'original'
    return normalized

def _matches_requested_format(file_format, candidate_format):
    normalized_request = _requested_download_format(file_format)
    normalized_candidate = str(candidate_format or '').strip().lower()

    if normalized_request == 'mp3':
        return normalized_candidate in ('mp3', 'mpeg')

    return normalized_candidate not in ('', 'mp3', 'mpeg')

def _lookup_plex_songs(cur, title, artist, album, fuzzy=False):
    """Query plex_songs for rows matching title+artist+album, falling back to title+artist.
    If fuzzy=True, falls back further to normalized text matching when exact matches fail."""
    rows = []
    if album:
        cur.execute(
            """
            SELECT title, artist, album, format, bitrate, file_path
            FROM plex_songs
            WHERE lower(COALESCE(title, '')) = lower(%s)
              AND lower(COALESCE(artist, '')) = lower(%s)
              AND lower(COALESCE(album, '')) = lower(%s)
            ORDER BY updated_at DESC
            """,
            (title, artist, album)
        )
        rows = cur.fetchall() or []

    if not rows:
        cur.execute(
            """
            SELECT title, artist, album, format, bitrate, file_path
            FROM plex_songs
            WHERE lower(COALESCE(title, '')) = lower(%s)
              AND lower(COALESCE(artist, '')) = lower(%s)
            ORDER BY updated_at DESC
            """,
            (title, artist)
        )
        rows = cur.fetchall() or []

    if not rows and fuzzy:
        normalized_title = normalize_match_text(title, strip_trailing_parenthetical=True)
        normalized_artist = normalize_match_text(artist)
        normalized_album = normalize_match_text(album, strip_trailing_parenthetical=True) if album else ''

        # For multi-artist strings like "Evanescence, K.Flay", also try each individual
        # artist so a Plex track stored under one artist still gets matched.
        artist_candidates = [normalized_artist]
        split_parts = [normalize_match_text(a.strip()) for a in artist.split(',') if a.strip()]
        if len(split_parts) > 1:
            artist_candidates.extend(split_parts)

        seen_file_paths = set()
        for candidate_artist in artist_candidates:
            cur.execute(
                """
                SELECT title, artist, album, format, bitrate, file_path
                FROM plex_songs
                WHERE trim(regexp_replace(regexp_replace(lower(COALESCE(artist, '')), '[^a-z0-9]+', ' ', 'g'), '\\s+', ' ', 'g')) = %s
                """,
                (candidate_artist,)
            )
            for candidate in (cur.fetchall() or []):
                fp = candidate.get('file_path')
                if fp in seen_file_paths:
                    continue
                candidate_title = normalize_match_text(candidate.get('title'), strip_trailing_parenthetical=True)
                candidate_album = normalize_match_text(candidate.get('album'), strip_trailing_parenthetical=True)

                if candidate_title != normalized_title:
                    continue

                if normalized_album and candidate_album != normalized_album:
                    continue

                seen_file_paths.add(fp)
                rows.append(candidate)

    return rows


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

    rows = _lookup_plex_songs(cur, title, artist, album)
    return any(_matches_requested_format(requested_format, row.get('format')) for row in rows)

def cleanup_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"[DOWNLOAD] Cleaned up temporary file", flush=True)
    except Exception as e:
        print(f"[DOWNLOAD] WARNING: Failed to clean up temp file: {str(e)}", flush=True)

def detect_audio_format(data: bytes) -> str:
    """
    Detect the audio format from the file's magic bytes.
    Returns: 'flac', 'm4a', 'mp3', or 'unknown'
    """
    if len(data) < 12:
        return 'unknown'
    
    # Check for FLAC (starts with 'fLaC')
    if data[:4] == b'fLaC':
        return 'flac'
    
    # Check for M4A/MP4 (has 'ftyp' at offset 4, and typically 'M4A ' or 'mp42' after)
    if len(data) >= 12 and data[4:8] == b'ftyp':
        # Check common M4A/AAC signatures
        if data[8:12] in [b'M4A ', b'mp42', b'isom', b'iso2']:
            return 'm4a'
    
    # Check for MP3 (ID3v2 tag or MPEG sync word)
    if data[:3] == b'ID3' or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return 'mp3'
    
    return 'unknown'

def add_id3_tags_to_file(file_path, metadata, cover_image_data=None):
    """
    Add ID3 tags to an audio file (handles FLAC, MP3, and M4A/AAC).
    
    Args:
        file_path: Path to the audio file
        metadata: Dict with keys: artist, title, album, year, track_number, disc_number
        cover_image_data: Binary image data to embed as cover art
    """
    try:
        artist = metadata.get('artist', 'Unknown Artist')
        title = metadata.get('title', 'Unknown Track')
        album = metadata.get('album', 'Unknown Album')
        year = metadata.get('year', '')
        track_num = metadata.get('track_number', '1')
        disc_num = metadata.get('disc_number', '')
        
        # Handle FLAC files
        if file_path.lower().endswith('.flac'):
            try:
                audio = FLAC(file_path)
                audio['TITLE'] = title
                audio['ARTIST'] = artist
                if metadata.get('album_artist'):
                    audio['ALBUMARTIST'] = metadata.get('album_artist')
                audio['ALBUM'] = album
                if year:
                    audio['DATE'] = str(year)
                audio['TRACKNUMBER'] = str(track_num)
                if disc_num:
                    audio['DISCNUMBER'] = str(disc_num)
                if metadata.get('copyright'):
                    audio['COPYRIGHT'] = str(metadata.get('copyright'))
                if metadata.get('tidal_track_id'):
                    audio['TIDAL_TRACK_ID'] = str(metadata.get('tidal_track_id'))
                if metadata.get('tidal_album_id'):
                    audio['TIDAL_ALBUM_ID'] = str(metadata.get('tidal_album_id'))
                if metadata.get('version'):
                    audio['VERSION'] = str(metadata.get('version'))

                # Add cover art if available
                if cover_image_data:
                    from mutagen.flac import Picture
                    pic = Picture()
                    pic.data = cover_image_data
                    pic.type = 3  # Cover (front)
                    pic.mime = 'image/jpeg'
                    audio.add_picture(pic)
                
                audio.save()
                print(f"[ID3] Successfully added FLAC metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write FLAC tags: {str(e)}", flush=True)
        
        # Handle M4A/AAC files
        elif file_path.lower().endswith('.m4a'):
            try:
                audio = MP4(file_path)
                audio['\xa9nam'] = title
                audio['\xa9ART'] = artist
                if metadata.get('album_artist'):
                    audio['aART'] = metadata.get('album_artist')
                audio['\xa9alb'] = album
                
                if year:
                    audio['\xa9day'] = str(year)
                
                if track_num:
                    try:
                        track_number = int(track_num)
                        audio['trkn'] = [(track_number, 0)]
                    except ValueError:
                        pass

                if disc_num:
                    try:
                        disc_number = int(disc_num)
                        audio['disk'] = [(disc_number, 0)]
                    except ValueError:
                        pass

                if metadata.get('copyright'):
                    audio['©cpy'] = str(metadata.get('copyright'))
                if metadata.get('tidal_track_id'):
                    audio['----:com.apple.iTunes:tidal_track_id'] = [str(metadata.get('tidal_track_id')).encode('utf-8')]
                if metadata.get('tidal_album_id'):
                    audio['----:com.apple.iTunes:tidal_album_id'] = [str(metadata.get('tidal_album_id')).encode('utf-8')]
                if metadata.get('version'):
                    audio['----:com.apple.iTunes:version'] = [str(metadata.get('version')).encode('utf-8')]
                
                if cover_image_data:
                    audio['covr'] = [MP4Cover(cover_image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                
                audio.save()
                print(f"[ID3] Successfully added M4A metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write M4A tags: {str(e)}", flush=True)
        
        # Handle MP3 files
        elif file_path.lower().endswith('.mp3'):
            try:
                try:
                    audio = MP3(file_path, ID3=ID3)
                except:
                    audio = MP3(file_path)
                    audio.add_tags()
                
                # Remove existing tags to ensure clean slate
                audio.delete()
                audio = MP3(file_path)
                audio.add_tags()
                
                # Add text tags
                audio['TIT2'] = TIT2(encoding=3, text=title)
                audio['TPE1'] = TPE1(encoding=3, text=artist)
                if metadata.get('album_artist'):
                    audio['TPE2'] = TPE2(encoding=3, text=str(metadata.get('album_artist')))
                audio['TALB'] = TALB(encoding=3, text=album)
                if year:
                    audio['TDRC'] = TDRC(encoding=3, text=str(year))
                audio['TRCK'] = TRCK(encoding=3, text=str(track_num))
                if disc_num:
                    audio['TPOS'] = TPOS(encoding=3, text=str(disc_num))
                if metadata.get('copyright'):
                    audio['TCOP'] = TCOP(encoding=3, text=str(metadata.get('copyright')))
                if metadata.get('tidal_track_id'):
                    audio['TXXX:tidal_track_id'] = TXXX(encoding=3, desc='tidal_track_id', text=str(metadata.get('tidal_track_id')))
                if metadata.get('tidal_album_id'):
                    audio['TXXX:tidal_album_id'] = TXXX(encoding=3, desc='tidal_album_id', text=str(metadata.get('tidal_album_id')))
                if metadata.get('version'):
                    audio['TXXX:version'] = TXXX(encoding=3, desc='version', text=str(metadata.get('version')))
                
                # Add cover art if available
                if cover_image_data:
                    audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_image_data)
                
                audio.save(v2_version=4)
                print(f"[ID3] Successfully added MP3 metadata to {file_path}", flush=True)
            except Exception as e:
                print(f"[ID3] Warning: Could not write MP3 tags: {str(e)}", flush=True)
                
    except Exception as e:
        print(f"[ID3] Error adding ID3 tags: {str(e)}", flush=True)

def download_cover_image(cover_url):
    """
    Download album cover image from URL.
    Returns binary image data or None if download fails.
    """
    if not cover_url:
        print(f"[COVER] No cover URL provided", flush=True)
        return None
    
    try:
        print(f"[COVER] Downloading cover image from: {cover_url}", flush=True)
        response = requests.get(cover_url, timeout=10)
        
        if response.ok:
            print(f"[COVER] Successfully downloaded cover image ({len(response.content)} bytes)", flush=True)
            return response.content
        else:
            print(f"[COVER] Failed to download cover image. Status: {response.status_code}", flush=True)
            return None
    except requests.exceptions.Timeout:
        print(f"[COVER] ERROR: Timeout downloading cover image from {cover_url}", flush=True)
        return None
    except Exception as e:
        print(f"[COVER] Error downloading cover image: {str(e)}", flush=True)
        return None

def convert_to_mp3(source_path: str, mp3_path: str, source_format: str = 'audio') -> bool:
    """
    Convert an audio file (e.g., FLAC or M4A/AAC) to highest VBR quality MP3 using ffmpeg.

    Args:
        source_path: Path to the source audio file
        mp3_path: Path where the MP3 should be saved
        source_format: Source format label for logging

    Returns:
        True on success, False on failure
    """
    try:
        print(
            f"[FFMPEG] Converting {source_format.upper()} to MP3 (highest VBR quality): {source_path} -> {mp3_path}",
            flush=True
        )

        mp3_dir = os.path.dirname(mp3_path)
        if mp3_dir:
            os.makedirs(mp3_dir, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-i', source_path,
            '-c:a', 'libmp3lame',
            '-q:a', '0',
            '-y',
            mp3_path
        ]

        print(f"[FFMPEG] Command: {' '.join(cmd)}", flush=True)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"[FFMPEG] SUCCESS: Converted to {mp3_path}", flush=True)
            return True

        print(f"[FFMPEG] ERROR: Conversion failed with code {result.returncode}", flush=True)
        print(f"[FFMPEG] stderr: {result.stderr}", flush=True)
        return False

    except subprocess.TimeoutExpired:
        print(f"[FFMPEG] ERROR: Conversion timeout", flush=True)
        return False
    except Exception as e:
        print(f"[FFMPEG] ERROR: {str(e)}", flush=True)
        return False

@app.route('/api/download', methods=['POST'])
def download_track():
    """
    Enqueue a download job with specified settings.
    Expects JSON body with:
    - trackId: integer
    - format: 'original' or 'mp3'
    - downloadType: 'album' or 'loose'
    - fileNaming: string (template for filename, e.g. '{artist}/{album}/{track} - {title}.{ext}')
    - fileNamingAlbum: string (optional override for album downloads)
    - fileNamingLoose: string (optional override for loose track downloads)
    """
    payload = request.get_json(silent=True) or {}
    track_id = payload.get('trackId')
    file_format = payload.get('format', 'original')
    download_type = payload.get('downloadType', 'loose')

    if download_type not in ('album', 'loose'):
        download_type = 'loose'

    settings = get_download_settings()
    file_naming_loose = settings.get('file_naming_loose', DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose'])
    file_naming_album = settings.get('file_naming_album', DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'])

    if download_type == 'album':
        file_naming = payload.get('fileNamingAlbum') or payload.get('fileNaming') or file_naming_album
    else:
        file_naming = payload.get('fileNamingLoose') or payload.get('fileNaming') or file_naming_loose

    if not track_id:
        print(f"[DOWNLOAD] ERROR: trackId is missing", flush=True)
        return jsonify({'error': 'trackId is required'}), 400

    if file_format not in ('original', 'mp3'):
        return jsonify({'error': 'Invalid format value'}), 400

    # Use global setting as fallback if not specified in payload
    ignore_matches = payload.get('ignore_matches')
    if ignore_matches is None:
        ignore_matches = settings.get('ignore_matches', DEFAULT_DOWNLOAD_SETTINGS.get('ignore_matches', False))
    ignore_matches = bool(ignore_matches)

    job_payload = {
        'trackId': track_id,
        'format': file_format,
        'downloadType': download_type,
        'fileNaming': file_naming,
        'fileNamingAlbum': payload.get('fileNamingAlbum') or file_naming_album,
        'fileNamingLoose': payload.get('fileNamingLoose') or file_naming_loose,
        'plex_playlist': payload.get('plex_playlist'),
        'plex_user_id': payload.get('plex_user_id'),
        'ignore_matches': ignore_matches
    }

    job_id = enqueue_job('download_track', job_payload)
    set_last_download_activity_at(datetime.utcnow())

    update_job_id = queue_plex_library_update(trigger='download_enqueue')
    if update_job_id:
        print(f"[DOWNLOAD] Queued plex_library_update job {update_job_id} (download enqueue)", flush=True)
    else:
        print("[DOWNLOAD] plex_library_update already queued/in progress; not queueing another", flush=True)

    sync_job_id = queue_plex_library_sync(trigger='download_enqueue')
    if sync_job_id:
        print(f"[DOWNLOAD] Queued plex_library_sync job {sync_job_id} (download enqueue)", flush=True)
    else:
        print("[DOWNLOAD] plex_library_sync already queued/in progress; not queueing another", flush=True)

    print(f"[DOWNLOAD] Queued download job {job_id} for track {track_id}", flush=True)
    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List jobs with optional filters.
    Query parameters:
    - status: filter by raw job status
    - job_type: filter by job type
    - jobs_filter: one of incomplete|complete|completed_with_errors|failed
    - exclude_plex_playlist_add: default true
    - limit: optional max number of rows (no backend-enforced maximum)
    - offset: pagination offset (default 0)
    """
    status_filter = request.args.get('status')
    job_type_filter = request.args.get('job_type')
    jobs_filter = request.args.get('jobs_filter')
    exclude_plex_playlist_add = request.args.get('exclude_plex_playlist_add', '1').lower() not in ('0', 'false', 'no')

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
    if exclude_plex_playlist_add:
        where_clauses.append('job_type <> %s')
        params.append('plex_playlist_add')

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
            if jobs_filter == 'completed_with_errors':
                return effective_status == 'completed_with_errors'
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

    totals = get_jobs_filter_totals(exclude_plex_playlist_add=exclude_plex_playlist_add)
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

    if stages.get('playlist_added') == 'failed':
        return 'completed_with_errors'

    if status == 'succeeded' and stages.get('playlist_added') == 'queued':
        return 'in_progress'

    return status

def get_jobs_filter_totals(exclude_plex_playlist_add=True):
    conn = get_db_connection()
    cur = conn.cursor()

    where_sql = 'WHERE job_type <> %s' if exclude_plex_playlist_add else ''
    params = ('plex_playlist_add',) if exclude_plex_playlist_add else ()

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
        'completed_with_errors': 0,
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
        elif effective_status == 'completed_with_errors':
            totals['completed_with_errors'] += 1
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
    now = datetime.utcnow().isoformat() + 'Z'
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

    if row is None:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404

    if row['status'] not in ('queued', 'in_progress'):
        conn.close()
        return jsonify({'error': f"Job is not cancellable (status={row['status']})"}), 400

    cur.execute(
        """
        UPDATE jobs
        SET status = 'cancelled',
            updated_at = %s,
            finished_at = %s
        WHERE id = %s
        """,
        (now, now, job_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'job_id': job_id, 'status': 'cancelled'})

@app.route('/api/jobs/cancel-incomplete', methods=['POST'])
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

        if job_type == 'plex_playlist_add':
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

@app.route('/api/jobs/<int:job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """Retry an existing failed/completed-with-errors download job by re-queueing it."""
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

    if row['job_type'] != 'download_track':
        conn.close()
        return jsonify({'error': 'Only download_track jobs can be retried'}), 400

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

    effective_status = _effective_job_status(row['job_type'], row['status'], row.get('result_json'))
    retryable = effective_status in ('failed', 'completed_with_errors')

    if not retryable:
        conn.close()
        return jsonify({'error': f"Job is not retryable (status={row['status']}, effective_status={effective_status})"}), 400

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

@app.route('/api/settings', methods=['GET', 'POST'])
def download_settings():
    """Get or update download settings stored in SQLite."""
    if request.method == 'GET':
        return jsonify(get_download_settings())

    payload = request.get_json(silent=True) or {}
    current = get_download_settings()

    file_naming_loose = (
        payload.get('fileNamingLoose')
        or payload.get('file_naming_loose')
        or payload.get('fileNaming')
        or payload.get('file_naming')
        or current['file_naming_loose']
    )
    file_naming_album = (
        payload.get('fileNamingAlbum')
        or payload.get('file_naming_album')
        or payload.get('fileNaming')
        or payload.get('file_naming')
        or current['file_naming_album']
    )

    updated = {
        'format': payload.get('format', current['format']),
        'parent_folder': current['parent_folder'],  # Keep existing value (no longer editable)
        'file_naming_loose': file_naming_loose,
        'file_naming_album': file_naming_album,
        'jobs_refresh_interval_seconds': payload.get('jobsRefreshIntervalSeconds', payload.get('jobs_refresh_interval_seconds', current.get('jobs_refresh_interval_seconds', DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds']))),
        'ignore_matches': payload.get('ignoreMatches', payload.get('ignore_matches', current.get('ignore_matches', DEFAULT_DOWNLOAD_SETTINGS.get('ignore_matches', False))))
    }

    if updated['format'] not in ('original', 'mp3'):
        return jsonify({'error': 'Invalid format value'}), 400

    if not isinstance(updated['file_naming_loose'], str) or not isinstance(updated['file_naming_album'], str):
        return jsonify({'error': 'Invalid settings payload'}), 400

    try:
        updated['jobs_refresh_interval_seconds'] = int(updated['jobs_refresh_interval_seconds'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid jobs refresh interval'}), 400

    if updated['jobs_refresh_interval_seconds'] < 1:
        return jsonify({'error': 'Jobs refresh interval must be at least 1 second'}), 400

    updated['ignore_matches'] = bool(updated['ignore_matches'])

    save_download_settings(updated)
    return jsonify({
        'format': updated['format'],
        'file_naming': updated['file_naming_loose'],
        'file_naming_loose': updated['file_naming_loose'],
        'file_naming_album': updated['file_naming_album'],
        'jobs_refresh_interval_seconds': updated['jobs_refresh_interval_seconds'],
        'ignore_matches': updated['ignore_matches']
    })

@app.route('/api/endpoints/status', methods=['GET'])
def endpoints_status():
    """Return the current status of all endpoints"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, encoded_url, online, response_time, last_checked
        FROM mirror_endpoints
        ORDER BY name
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
            'lastChecked': row['last_checked']
        })

    mirror_rate_limit_status = {}
    try:
        mirror_rate_limit_status = downloads.get_mirror_rate_limit_status() or {}
    except Exception as e:
        print(f"[ENDPOINTS] Failed to get mirror rate limit status: {e}", flush=True)

    return jsonify({
        'endpoints': endpoints,
        'summary': {
            'total': len(endpoints),
            'online': sum(1 for e in endpoints if e.get('online')),
            'offline': sum(1 for e in endpoints if not e.get('online'))
        },
        'mirrorRateLimitStatus': mirror_rate_limit_status,
    })

@app.route('/api/listenbrainz/config', methods=['GET'])
def get_listenbrainz_config_endpoint():
    """Get the current ListenBrainz configuration"""
    config = get_listenbrainz_config()
    return jsonify({
        'has_token': config['user_token'] is not None
    })

@app.route('/api/listenbrainz/config', methods=['POST'])
def save_listenbrainz_config_endpoint():
    """Save ListenBrainz user token"""
    payload = request.get_json()
    
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400
    
    user_token = payload.get('user_token')
    
    if not user_token:
        return jsonify({'error': 'user_token is required'}), 400
    
    save_listenbrainz_config(user_token)
    return jsonify({
        'success': True
    })

@app.route('/api/listenbrainz/playlists', methods=['GET'])
def get_listenbrainz_playlists():
    """Fetch recommended playlists created for user from ListenBrainz"""
    config = get_listenbrainz_config()
    
    if not config['user_token']:
        return jsonify({'error': 'ListenBrainz token not configured'}), 400
    
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'username parameter is required'}), 400
    
    try:
        headers = {'Authorization': f'Token {config["user_token"]}'}
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
    try:
        url = f'https://api.listenbrainz.org/1/playlist/{playlist_mbid}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return jsonify(data)
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch playlist from ListenBrainz: {str(e)}'}), 500

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

@app.route('/api/plex/sync', methods=['POST'])
def start_plex_sync_endpoint():
    """Queue a manual Plex library sync job."""
    result = start_plex_sync_job(trigger='manual')
    if not result.get('ok'):
        return jsonify({'error': result.get('error')}), result.get('status_code', 500)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202

@app.route('/api/plex/test', methods=['POST'])
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

def normalize_match_text(value: str, strip_trailing_parenthetical: bool = False) -> str:
    text = str(value or '').strip().lower()
    if strip_trailing_parenthetical:
        text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

@app.route('/api/plex/songs/match', methods=['POST'])
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

    for item in tracks:
        if not isinstance(item, dict):
            matches.append({'exists': False, 'variants': []})
            continue

        title = str(item.get('title') or '').strip()
        artist = str(item.get('artist') or '').strip()
        album = str(item.get('album') or '').strip()

        if not title or not artist:
            matches.append({'exists': False, 'variants': []})
            continue

        rows = _lookup_plex_songs(cur, title, artist, album, fuzzy=True)

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

        matches.append({
            'exists': len(rows) > 0,
            'variants': variants
        })

    conn.close()
    return jsonify({'matches': matches})
