def init_library_update_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS library_update_status (
            id INTEGER PRIMARY KEY,
            last_update_time TIMESTAMP,
            library_update_needed BOOLEAN NOT NULL DEFAULT FALSE,
            last_job_finished_at TIMESTAMP
        )
        '''
    )
    # Ensure a single row exists
    cur.execute('SELECT id FROM library_update_status WHERE id = 1')
    if not cur.fetchone():
        cur.execute('INSERT INTO library_update_status (id, library_update_needed) VALUES (1, FALSE)')
    conn.commit()
    conn.close()

def get_library_update_status():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT last_update_time, library_update_needed, last_job_finished_at FROM library_update_status WHERE id = 1')
    row = cur.fetchone()
    conn.close()
    return row

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

def any_download_jobs_running():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM jobs WHERE job_type = 'download_track' AND status IN ('queued', 'in_progress')")
    row = cur.fetchone() or {}
    count = row.get('count', 0)
    conn.close()
    return count > 0

def trigger_plex_library_update():
    print('[LIBRARY UPDATE] Triggering Plex library update...', flush=True)
    plex_config = get_plex_config()
    server_url = plex_config.get('server_url')
    api_token = plex_config.get('api_token')
    library_name = plex_config.get('library_name')
    if not (server_url and api_token and library_name):
        print('[LIBRARY UPDATE] Plex config missing, cannot update library.', flush=True)
        return
    try:
        plex = PlexServer(server_url, api_token, timeout=20)
        print(f'[LIBRARY UPDATE] Connected to Plex server at {server_url}', flush=True)
        # Find the music library by name
        library = None
        for section in plex.library.sections():
            if section.title == library_name and section.type == 'artist':
                library = section
                break
        if not library:
            print(f'[LIBRARY UPDATE] Library "{library_name}" not found or not a music library.', flush=True)
            return
        print(f'[LIBRARY UPDATE] Triggering scan on library: {library_name}', flush=True)
        library.update()
        print(f'[LIBRARY UPDATE] Library scan triggered successfully.', flush=True)
    except Exception as e:
        print(f'[LIBRARY UPDATE] Error triggering Plex library update: {e}', flush=True)

def library_update_worker():
    print('[LIBRARY UPDATE WORKER] Started', flush=True)
    while True:
        try:
            status = get_library_update_status()
            if not status:
                time.sleep(30)
                continue
            last_update_time, library_update_needed, last_job_finished_at = status
            now = datetime.utcnow()
            # Convert timestamps if not None and not already datetime
            if last_update_time and not isinstance(last_update_time, datetime):
                try:
                    last_update_time = datetime.fromisoformat(str(last_update_time))
                except Exception:
                    last_update_time = None
            if last_update_time and hasattr(last_update_time, 'replace'):
                last_update_time = last_update_time.replace(tzinfo=None)
            if last_job_finished_at and not isinstance(last_job_finished_at, datetime):
                try:
                    last_job_finished_at = datetime.fromisoformat(str(last_job_finished_at))
                except Exception:
                    last_job_finished_at = None
            if last_job_finished_at and hasattr(last_job_finished_at, 'replace'):
                last_job_finished_at = last_job_finished_at.replace(tzinfo=None)
            # Scenario 1
            if library_update_needed and not any_download_jobs_running():
                # 15 min since last job finished and last update
                if last_job_finished_at and last_update_time:
                    if (now - last_job_finished_at >= timedelta(minutes=15)) and (now - last_update_time >= timedelta(minutes=15)):
                        trigger_plex_library_update()
                        set_library_update_needed(False)
                        set_last_library_update_time(now)
                        print('[LIBRARY UPDATE WORKER] Library updated (scenario 1)', flush=True)
                elif last_job_finished_at and not last_update_time:
                    if (now - last_job_finished_at >= timedelta(minutes=15)):
                        trigger_plex_library_update()
                        set_library_update_needed(False)
                        set_last_library_update_time(now)
                        print('[LIBRARY UPDATE WORKER] Library updated (scenario 1, no prev update)', flush=True)
            # Scenario 2
            elif library_update_needed and any_download_jobs_running():
                if last_update_time and (now - last_update_time >= timedelta(minutes=60)):
                    trigger_plex_library_update()
                    set_library_update_needed(False)
                    set_last_library_update_time(now)
                    print('[LIBRARY UPDATE WORKER] Library updated (scenario 2)', flush=True)
                elif not last_update_time:
                    trigger_plex_library_update()
                    set_library_update_needed(False)
                    set_last_library_update_time(now)
                    print('[LIBRARY UPDATE WORKER] Library updated (scenario 2, no prev update)', flush=True)
        except Exception as e:
            print(f'[LIBRARY UPDATE WORKER] Error: {e}', flush=True)
        time.sleep(60)
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
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
from urllib.parse import urlparse, parse_qs
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from io import BytesIO
from plexapi.server import PlexServer
from ytmusicapi import YTMusic

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://squidly:squidly@localhost:5432/squidly')
DOWNLOADS_ROOT = '/downloads'
DOWNLOADS_FULL_ALBUMS_FOLDER = 'full_albums'
DOWNLOADS_LOOSE_TRACKS_FOLDER = 'loose_tracks'
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

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
DEFAULT_DOWNLOAD_SETTINGS = {
    'format': 'original',
    'parent_folder': '',
    'file_naming_loose': '{artist}/{album}/{track} - {title}.{ext}',
    'file_naming_album': '{artist}/{album}/{track} - {title}.{ext}'
}

def make_request_with_retry(url, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    """
    Make HTTP request with exponential backoff retry logic (for non-mirror URLs like CDN).
    Retries on 5xx errors and connection errors on the same URL.
    
    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts (total attempts = max_retries + 1)
        backoff_factor: Multiplier for exponential backoff (delay = backoff_factor * 2^attempt)
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        Response object
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, timeout=timeout, **kwargs)
            else:
                response = requests.request(method, url, timeout=timeout, **kwargs)
            
            # Return on success (2xx) or client errors (4xx), only retry on 5xx
            if response.status_code < 500:
                return response
            
            # 5xx error - log and retry
            last_exception = Exception(f"HTTP {response.status_code}")
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                print(f"[RETRY] HTTP {response.status_code} on attempt {attempt + 1}/{max_retries + 1}. Retrying in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            
            # Last attempt failed with 5xx
            return response
        
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                print(f"[RETRY] Timeout on attempt {attempt + 1}/{max_retries + 1}. Retrying in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            raise
        
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                print(f"[RETRY] Connection error on attempt {attempt + 1}/{max_retries + 1}. Retrying in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            raise
        
        except requests.exceptions.RequestException as e:
            # Don't retry on other request exceptions
            raise
    
    # If we got here, all retries were exhausted
    if last_exception:
        raise last_exception
    return None

def make_request_with_retry_rotating_mirrors(url_base, url_iterator, method='GET', timeout=10, max_retries=3, backoff_factor=1.0, **kwargs):
    """
    Make HTTP request with exponential backoff retry logic and mirror rotation.
    Each retry attempt uses a different mirror from the round-robin iterator.
    
    Args:
        url_base: The base URL path to append to mirror URLs (e.g., "/search/?s=query")
        url_iterator: Round-robin iterator that yields mirror info dicts with 'url' and 'name'
        method: HTTP method (GET, POST, etc.)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts (total attempts = max_retries + 1)
        backoff_factor: Multiplier for exponential backoff (delay = backoff_factor * 2^attempt)
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        (response, target_mirror) tuple - successful response and mirror info used
    """
    last_exception = None
    last_target = None
    allowed_names = get_online_mirror_names()
    if not allowed_names:
        allowed_names = None
    total_count = len(SQUID_URLS) if 'SQUID_URLS' in globals() else 0
    
    for attempt in range(max_retries + 1):
        try:
            # Get a new mirror for each attempt, skipping known-offline entries
            target = select_next_mirror(url_iterator, allowed_names, total_count)
            last_target = target
            target_url = f"{target['url']}{url_base}"
            
            if method.upper() == 'GET':
                response = requests.get(target_url, timeout=timeout, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(target_url, timeout=timeout, **kwargs)
            else:
                response = requests.request(method, target_url, timeout=timeout, **kwargs)
            
            # Return on success (2xx) or client errors (4xx), only retry on 5xx
            if response.status_code < 500:
                return response, target
            
            # 5xx error - log and retry with different mirror
            last_exception = Exception(f"HTTP {response.status_code}")
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                print(f"[RETRY] HTTP {response.status_code} from {target['name']} on attempt {attempt + 1}/{max_retries + 1}. Trying different mirror in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            
            # Last attempt failed with 5xx, return the failed response
            return response, target
        
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                mirror_name = last_target['name'] if last_target else 'unknown'
                print(f"[RETRY] Timeout from {mirror_name} on attempt {attempt + 1}/{max_retries + 1}. Trying different mirror in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            raise
        
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt)
                mirror_name = last_target['name'] if last_target else 'unknown'
                print(f"[RETRY] Connection error from {mirror_name} on attempt {attempt + 1}/{max_retries + 1}. Trying different mirror in {delay}s...", flush=True)
                time.sleep(delay)
                continue
            raise
        
        except requests.exceptions.RequestException as e:
            # Don't retry on other request exceptions
            raise
    
    # If we got here, all retries were exhausted
    if last_exception:
        raise last_exception
    return None

def get_db_connection():
    """Get a database connection that returns dictionary-like rows"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def get_online_mirror_names():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM mirror_endpoints
        WHERE online = 1
        """
    )
    rows = cur.fetchall()
    conn.close()
    return {row['name'] for row in rows}

def select_next_mirror(url_iterator, allowed_names, total_count):
    if not allowed_names:
        return next(url_iterator)

    for _ in range(total_count):
        candidate = next(url_iterator)
        if candidate['name'] in allowed_names:
            return candidate

    return next(url_iterator)

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
            format TEXT,
            bitrate INTEGER,
            updated_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL
        )
        """
    )
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
    
    conn.commit()
    conn.close()

def get_listenbrainz_config():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_token
        FROM listenbrainz_config
        WHERE id = 1
        """
    )
    row = cur.fetchone()
    conn.close()
    
    if row is None:
        return {'user_token': None}
    
    return {
        'user_token': row['user_token']
    }

def save_listenbrainz_config(user_token):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO listenbrainz_config (id, user_token, username, updated_at)
        VALUES (1, %s, NULL, %s)
        ON CONFLICT(id) DO UPDATE SET
            user_token = excluded.user_token,
            updated_at = excluded.updated_at
        """,
        (user_token, now)
    )
    conn.commit()
    conn.close()

def get_plex_config():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT server_url, api_token, library_name, sync_interval_hours
        FROM plex_config
        WHERE id = 1
        """
    )
    row = cur.fetchone()
    conn.close()
    
    if row is None:
        return {
            'server_url': None,
            'api_token': None,
            'library_name': None,
            'sync_interval_hours': 24
        }
    
    return {
        'server_url': row['server_url'],
        'api_token': row['api_token'],
        'library_name': row['library_name'],
        'sync_interval_hours': row.get('sync_interval_hours') if row.get('sync_interval_hours') is not None else 24
    }

def save_plex_config(server_url, api_token, library_name, sync_interval_hours=24):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO plex_config (id, server_url, api_token, library_name, sync_interval_hours, updated_at)
        VALUES (1, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            server_url = excluded.server_url,
            api_token = excluded.api_token,
            library_name = excluded.library_name,
            sync_interval_hours = excluded.sync_interval_hours,
            updated_at = excluded.updated_at
        """,
        (server_url, api_token, library_name, sync_interval_hours, now)
    )
    conn.commit()
    conn.close()

def any_plex_sync_jobs_running_or_queued():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM jobs
        WHERE job_type = 'plex_library_sync'
          AND status IN ('queued', 'in_progress')
        """
    )
    row = cur.fetchone() or {}
    conn.close()
    return (row.get('count') or 0) > 0

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
    if any_plex_sync_jobs_running_or_queued():
        return None

    payload = {
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('plex_library_sync', payload, max_attempts=5)

def process_plex_sync_job(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or 'Music').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured before syncing')

    stages = {
        'connect': 'pending',
        'fetch_tracks': 'pending',
        'sync_songs': 'pending',
        'cleanup': 'pending'
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
    stages['connect'] = 'done'
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
    stages['fetch_tracks'] = 'done'
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
                    INSERT INTO plex_songs (title, artist, album, file_path, format, bitrate, updated_at, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(file_path) DO UPDATE SET
                        title = excluded.title,
                        artist = excluded.artist,
                        album = excluded.album,
                        format = excluded.format,
                        bitrate = excluded.bitrate,
                        updated_at = excluded.updated_at,
                        last_seen_at = excluded.last_seen_at
                    """,
                    (title, artist, album, file_path, media_format, bitrate, now, now)
                )
                seen_paths.add(file_path)
                upserted += 1

        progress['processed_tracks'] = idx
        progress['upserted_songs'] = upserted
        if idx % 25 == 0 or idx == len(tracks):
            update_job_progress(job_id, {'progress': progress})

    conn.commit()
    stages['sync_songs'] = 'done'
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
    stages['cleanup'] = 'done'
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
    try:
        return json.dumps(payload, separators=(',', ':'), sort_keys=True)
    except (TypeError, ValueError):
        return json.dumps(payload, default=str, separators=(',', ':'), sort_keys=True)

def enqueue_job(job_type, payload, status='queued', priority=0, run_after=None, max_attempts=20):
    now = datetime.utcnow().isoformat() + 'Z'
    payload_json = serialize_job_payload(payload)
    scheduled_at = run_after or now

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs (
            job_type,
            status,
            payload_json,
            result_json,
            error_message,
            attempt_count,
            max_attempts,
            created_at,
            updated_at,
            run_after,
            locked_at,
            locked_by,
            started_at,
            finished_at,
            priority
        )
        VALUES (%s, %s, %s, NULL, NULL, 0, %s, %s, %s, %s, NULL, NULL, NULL, NULL, %s)
        RETURNING id
        """,
        (
            job_type,
            status,
            payload_json,
            max_attempts,
            now,
            now,
            scheduled_at,
            priority
        )
    )
    job_id = cur.fetchone()['id']
    conn.commit()
    conn.close()
    return job_id

def queue_pending_playlist_addition(artist, album, title, playlist_name, parent_job_id=None):
    """Add a track to the pending playlist additions queue."""
    payload = {
        'artist': artist,
        'album': album,
        'title': title,
        'playlist_name': playlist_name,
        'parent_job_id': parent_job_id
    }
    payload_json = serialize_job_payload(payload)
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if this track is already queued
    cur.execute(
        """
        SELECT id FROM jobs
        WHERE job_type = %s
          AND payload_json = %s
                    AND (
                                status IN ('queued', 'in_progress')
                                OR (status = 'failed' AND attempt_count < max_attempts)
                            )
        """,
        ('plex_add', payload_json)
    )
    existing = cur.fetchone()
    
    if existing:
        print(f"[PLEX_QUEUE] Track already in queue: {artist} - {title}", flush=True)
        conn.close()
        return
    conn.close()
    job_id = enqueue_job('plex_add', payload)
    print(f"[PLEX_QUEUE] Queued for retry (job {job_id}, parent {parent_job_id}): {artist} - {title}", flush=True)

def update_parent_playlist_stage(parent_job_id, playlist_stage_status):
    """Update playlist_added stage on a parent download_track job."""
    if parent_job_id is None:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT job_type, result_json
        FROM jobs
        WHERE id = %s
        """,
        (parent_job_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row or row['job_type'] != 'download_track':
        return

    try:
        current = json.loads(row['result_json']) if row['result_json'] else {}
    except (TypeError, ValueError):
        current = {}

    if not isinstance(current, dict):
        current = {}

    stages = current.get('stages') if isinstance(current.get('stages'), dict) else {}
    stages['playlist_added'] = playlist_stage_status
    update_job_progress(parent_job_id, {'stages': stages})

def backfill_plex_add_parent_links():
    """One-time repair for legacy plex_add jobs missing parent_job_id in payload."""
    print("[PLEX_REPAIR] Starting parent link backfill", flush=True)
    now = datetime.utcnow().isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, payload_json, status, attempt_count, max_attempts, created_at
        FROM jobs
        WHERE job_type = %s
        ORDER BY created_at ASC
        """,
        ('plex_add',)
    )
    additions = cur.fetchall()

    cur.execute(
        """
        SELECT id, result_json, created_at
        FROM jobs
        WHERE job_type = %s
          AND result_json IS NOT NULL
        ORDER BY created_at ASC
        """,
        ('download_track',)
    )
    parents = cur.fetchall()

    parent_index = {}
    for row in parents:
        try:
            result = json.loads(row['result_json']) if row['result_json'] else {}
        except (TypeError, ValueError):
            continue
        if not isinstance(result, dict):
            continue

        artist = str(result.get('artist') or '').strip().casefold()
        album = str(result.get('album') or '').strip().casefold()
        title = str(result.get('title') or '').strip().casefold()
        playlist = str(result.get('playlist_name') or '').strip().casefold()
        stages = result.get('stages') if isinstance(result.get('stages'), dict) else {}
        playlist_stage = str(stages.get('playlist_added') or '').strip().casefold()

        if not artist or not title or not playlist:
            continue
        if playlist_stage not in ('queued', 'done', 'failed'):
            continue

        key = (artist, album, title, playlist)
        parent_index.setdefault(key, []).append({
            'id': row['id'],
            'created_at': row['created_at'] or '',
            'playlist_stage': playlist_stage
        })

    linked_count = 0
    reconciled_count = 0

    for addition in additions:
        try:
            payload = json.loads(addition['payload_json']) if addition['payload_json'] else {}
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get('parent_job_id'):
            continue

        artist = str(payload.get('artist') or '').strip().casefold()
        album = str(payload.get('album') or '').strip().casefold()
        title = str(payload.get('title') or '').strip().casefold()
        playlist = str(payload.get('playlist_name') or '').strip().casefold()
        if not artist or not title or not playlist:
            continue

        key = (artist, album, title, playlist)
        candidates = parent_index.get(key, [])
        if not candidates:
            continue

        addition_created = addition['created_at'] or ''
        best = None
        for candidate in candidates:
            candidate_created = candidate['created_at']
            if not candidate_created or candidate_created <= addition_created:
                best = candidate
        if best is None:
            best = candidates[0]

        payload['parent_job_id'] = best['id']
        cur.execute(
            """
            UPDATE jobs
            SET payload_json = %s,
                updated_at = %s
            WHERE id = %s AND job_type = %s
            """,
            (serialize_job_payload(payload), now, addition['id'], 'plex_add')
        )
        linked_count += 1

        if addition['status'] == 'succeeded':
            update_parent_playlist_stage(best['id'], 'done')
            reconciled_count += 1
        elif addition['status'] == 'failed' and addition['attempt_count'] >= addition['max_attempts']:
            update_parent_playlist_stage(best['id'], 'failed')
            reconciled_count += 1

    conn.commit()
    conn.close()
    print(
        f"[PLEX_REPAIR] Backfill complete: linked={linked_count}, reconciled={reconciled_count}",
        flush=True
    )

def get_pending_playlist_additions():
    """Get all pending playlist additions that haven't exceeded max attempts."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, payload_json, attempt_count, max_attempts
        FROM jobs
        WHERE job_type = %s
          AND status IN ('queued', 'failed')
          AND attempt_count < max_attempts
          AND (run_after IS NULL OR run_after <= %s)
        ORDER BY created_at ASC
        """,
        ('plex_add', now)
    )
    rows = cur.fetchall()
    conn.close()

    additions = []
    for row in rows:
        try:
            payload = json.loads(row['payload_json'])
        except (TypeError, ValueError):
            payload = {}
        additions.append({
            'id': row['id'],
            'attempt_count': row['attempt_count'],
            'max_attempts': row['max_attempts'],
            'payload': payload
        })

    return additions

def update_pending_addition_attempt(addition_id, error_message=None):
    """Increment the attempt count and update last_attempt_at."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET attempt_count = attempt_count + 1,
            status = 'failed',
            updated_at = %s,
            run_after = %s,
            error_message = COALESCE(%s, error_message)
        WHERE id = %s AND job_type = %s
        """,
        (now, now, error_message, addition_id, 'plex_add')
    )
    conn.commit()
    conn.close()

def remove_pending_addition(addition_id):
    """Remove a successfully added track from the queue."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'succeeded',
            updated_at = %s,
            finished_at = %s
        WHERE id = %s AND job_type = %s
        """,
        (now, now, addition_id, 'plex_add')
    )
    conn.commit()
    conn.close()

def compute_job_backoff_seconds(attempt_count):
    base = 30
    delay = base * (2 ** max(0, attempt_count - 1))
    return min(delay, 3600)

class ManifestDownloadError(Exception):
    pass

class TransientDownloadError(Exception):
    pass

def claim_next_job(job_type):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    # psycopg2 automatically starts transactions; FOR UPDATE SKIP LOCKED provides row-level locking
    cur.execute(
        """
        SELECT id, payload_json, attempt_count, max_attempts
        FROM jobs
        WHERE job_type = %s
          AND status IN ('queued', 'failed')
          AND attempt_count < max_attempts
          AND (run_after IS NULL OR run_after <= %s)
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """,
        (job_type, now)
    )
    row = cur.fetchone()

    if row is None:
        conn.commit()
        conn.close()
        return None

    cur.execute(
        """
        UPDATE jobs
        SET status = 'in_progress',
            locked_at = %s,
            locked_by = %s,
            started_at = COALESCE(started_at, %s),
            updated_at = %s
        WHERE id = %s AND status IN ('queued', 'failed')
        """,
        (now, WORKER_ID, now, now, row['id'])
    )
    conn.commit()
    conn.close()

    return {
        'id': row['id'],
        'payload_json': row['payload_json'],
        'attempt_count': row['attempt_count'],
        'max_attempts': row['max_attempts']
    }

def mark_job_succeeded(job_id, result):
    now = datetime.utcnow().isoformat() + 'Z'
    result_json = serialize_job_payload(result) if result is not None else None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'succeeded',
            result_json = %s,
            error_message = NULL,
            updated_at = %s,
            finished_at = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
        """,
        (result_json, now, now, job_id)
    )

    cur.execute(
        """
        SELECT job_type
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    type_row = cur.fetchone()

    conn.commit()
    conn.close()

    if type_row and type_row.get('job_type') == 'download_track':
        # Set library_update_needed True and update last_job_finished_at
        set_library_update_needed(True)
        set_last_job_finished_at(datetime.utcnow())

def update_job_progress(job_id, updates):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT result_json
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()

    try:
        current = json.loads(row['result_json']) if row and row['result_json'] else {}
    except (TypeError, ValueError):
        current = {}

    if not isinstance(current, dict):
        current = {}

    merged = {**current, **updates}
    result_json = serialize_job_payload(merged)

    cur.execute(
        """
        UPDATE jobs
        SET result_json = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (result_json, now, job_id)
    )
    conn.commit()
    conn.close()

def mark_job_failed(job_id, attempt_count, max_attempts, error_message):
    now = datetime.utcnow().isoformat() + 'Z'
    next_attempt = attempt_count + 1
    finished_at = None
    run_after = None

    if next_attempt >= max_attempts:
        finished_at = now
    else:
        delay_seconds = compute_job_backoff_seconds(next_attempt)
        run_after = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'failed',
            attempt_count = %s,
            error_message = %s,
            updated_at = %s,
            finished_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
        """,
        (next_attempt, error_message, now, finished_at, run_after, job_id)
    )
    conn.commit()
    conn.close()

def mark_job_retrying(job_id, attempt_count, error_message):
    now = datetime.utcnow().isoformat() + 'Z'
    next_attempt = attempt_count + 1
    delay_seconds = compute_job_backoff_seconds(next_attempt)
    run_after = (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'queued',
            attempt_count = %s,
            error_message = %s,
            updated_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
        """,
        (next_attempt, error_message, now, run_after, job_id)
    )
    conn.commit()
    conn.close()

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
            url_iterator,
            method='GET',
            timeout=10,
            max_retries=3
        )
    except requests.exceptions.RequestException as e:
        raise TransientDownloadError(f"Failed to fetch track info: {str(e)}") from e

    if not info_response.ok:
        raise TransientDownloadError(f"Failed to get track info. Status: {info_response.status_code}")

    info_data = info_response.json()
    print(f"[DOWNLOAD] Track info response structure: {info_data.keys() if isinstance(info_data, dict) else type(info_data)}", flush=True)

    track_info = info_data.get('data', info_data) if isinstance(info_data, dict) else {}
    track_metadata = track_info.get('track', track_info) if 'track' in track_info else track_info

    artist_name = 'Unknown Artist'
    album_name = 'Unknown Album'
    track_title = 'Unknown Track'
    track_num = '01'
    release_year = ''
    cover_url = ''
    album_id = ''

    if isinstance(track_metadata, dict):
        if 'artist' in track_metadata and isinstance(track_metadata['artist'], dict):
            artist_name = track_metadata['artist'].get('name', 'Unknown Artist')
        elif 'artists' in track_metadata and isinstance(track_metadata['artists'], list) and len(track_metadata['artists']) > 0:
            artist_name = track_metadata['artists'][0].get('name', 'Unknown Artist')
        elif 'artistName' in track_metadata:
            artist_name = track_metadata['artistName']

        if 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            album_name = track_metadata['album'].get('title', 'Unknown Album')

            if 'id' in track_metadata['album']:
                album_id = track_metadata['album']['id']

            if 'cover' in track_metadata['album'] and track_metadata['album']['cover']:
                cover_val = track_metadata['album']['cover']
                if isinstance(cover_val, str) and not cover_val.startswith('http'):
                    cover_url = format_album_cover_url(cover_val)
                else:
                    cover_url = cover_val

            if not cover_url:
                for cover_field in ['coverUri', 'imageUri', 'image']:
                    if cover_field in track_metadata['album']:
                        cover_val = track_metadata['album'][cover_field]
                        if isinstance(cover_val, str):
                            if not cover_val.startswith('http'):
                                cover_url = format_album_cover_url(cover_val)
                            else:
                                cover_url = cover_val
                            break

        elif 'albumTitle' in track_metadata:
            album_name = track_metadata['albumTitle']

        if 'title' in track_metadata:
            track_title = track_metadata['title']

        if 'trackNumber' in track_metadata:
            track_num = str(track_metadata['trackNumber']).zfill(2)

        if 'releaseDate' in track_metadata:
            date_str = track_metadata['releaseDate']
            if isinstance(date_str, str) and len(date_str) >= 4:
                release_year = date_str[:4]
        elif 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            date_str = track_metadata['album'].get('releaseDate')
            if isinstance(date_str, str) and len(date_str) >= 4:
                release_year = date_str[:4]

        if not release_year:
            release_year = extract_year_from_text(track_metadata.get('copyright', ''))
        if not release_year and 'album' in track_metadata and isinstance(track_metadata['album'], dict):
            release_year = extract_year_from_text(track_metadata['album'].get('copyright', ''))

        if not cover_url and album_id:
            cover_url = format_album_cover_url(str(album_id))

        if not cover_url:
            if 'cover' in track_metadata:
                cover_val = track_metadata['cover']
                if isinstance(cover_val, str) and not cover_val.startswith('http'):
                    cover_url = format_album_cover_url(cover_val)
                else:
                    cover_url = cover_val

            if not cover_url:
                for cover_field in ['coverUri', 'imageUri', 'image']:
                    if cover_field in track_metadata:
                        cover_val = track_metadata[cover_field]
                        if isinstance(cover_val, str):
                            if not cover_val.startswith('http'):
                                cover_url = format_album_cover_url(cover_val)
                            else:
                                cover_url = cover_val
                            break

    print(f"[DOWNLOAD] Extracted metadata: Artist='{artist_name}', Album='{album_name}', Title='{track_title}', TrackNum='{track_num}', Year='{release_year}', Cover='{cover_url}'", flush=True)

    file_ext = 'flac' if file_format == 'original' else 'mp3'

    safe_artist = sanitize_filename_component(artist_name)
    safe_album = sanitize_filename_component(album_name)
    safe_title = sanitize_filename_component(track_title)
    safe_track = sanitize_filename_component(track_num)

    file_path = file_naming.replace('{artist}', safe_artist)
    file_path = file_path.replace('{album}', safe_album)
    file_path = file_path.replace('{track}', safe_track)
    file_path = file_path.replace('{title}', safe_title)
    file_path = file_path.replace('{ext}', file_ext)

    file_path = clean_path_components(file_path)

    full_path = os.path.join(downloads_folder, file_path)
    full_path = os.path.normpath(full_path)

    print(
        f"[DOWNLOAD_DECISION] Job {job_id}: selected_format='{file_format}', title='{track_title}', artist='{artist_name}', album='{album_name}'",
        flush=True
    )

    metadata_rows = []
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, artist, album, format, bitrate, file_path
        FROM plex_songs
        WHERE lower(COALESCE(title, '')) = lower(%s)
          AND lower(COALESCE(artist, '')) = lower(%s)
          AND lower(COALESCE(album, '')) = lower(%s)
        ORDER BY updated_at DESC
        """,
        (track_title, artist_name, album_name)
    )
    metadata_rows = cur.fetchall() or []

    if not metadata_rows:
        cur.execute(
            """
            SELECT title, artist, album, format, bitrate, file_path
            FROM plex_songs
            WHERE lower(COALESCE(title, '')) = lower(%s)
              AND lower(COALESCE(artist, '')) = lower(%s)
            ORDER BY updated_at DESC
            """,
            (track_title, artist_name)
        )
        metadata_rows = cur.fetchall() or []
    conn.close()

    def format_matches_selected(row_format):
        fmt = str(row_format or '').strip().lower()
        if file_format == 'mp3':
            return fmt in ('mp3', 'mpeg')
        return fmt not in ('', 'mp3', 'mpeg')

    matching_rows = [row for row in metadata_rows if format_matches_selected(row.get('format'))]

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

    if matching_rows:
        matched_row = matching_rows[0]
        matched_path = str(matched_row.get('file_path') or '').strip()
        if matched_path:
            full_path = matched_path
        print(
            f"[DOWNLOAD_DECISION] Job {job_id}: skipping download because existing Plex inventory metadata matches selected format (format='{matched_row.get('format')}', bitrate='{matched_row.get('bitrate')}')",
            flush=True
        )
        print(f"[DOWNLOAD] Existing metadata match found - skipping download pipeline", flush=True)
        stages['downloaded'] = 'done'
        stages['id3_tagged'] = 'done'
        stages['converted'] = 'done'
        stages['written'] = 'done'
        update_job_progress(job_id, {'stages': stages})

        plex_config = get_plex_config()
        playlist_name = payload.get('plex_playlist')
        if plex_config['server_url'] and plex_config['api_token'] and playlist_name:
            try:
                print("[DOWNLOAD] Plex config OK - attempting playlist update for existing file", flush=True)
                track_info = {
                    'artist': artist_name,
                    'album': album_name,
                    'title': track_title
                }
                success, plex_message = add_tracks_to_plex_playlist(
                    plex_config['server_url'],
                    plex_config['api_token'],
                    plex_config['library_name'] or 'Music',
                    playlist_name,
                    track_info
                )

                if success:
                    print(f"[DOWNLOAD] Plex playlist updated: {plex_message}", flush=True)
                    stages['playlist_added'] = 'done'
                    update_job_progress(job_id, {'stages': stages})
                else:
                    print(f"[DOWNLOAD] Plex playlist note: {plex_message}", flush=True)
                    if 'not yet indexed' in plex_message.lower() or 'not found' in plex_message.lower():
                        queue_pending_playlist_addition(
                            artist_name,
                            album_name,
                            track_title,
                            playlist_name,
                            parent_job_id=job_id
                        )
                        stages['playlist_added'] = 'queued'
                        update_job_progress(job_id, {'stages': stages})
                    else:
                        stages['playlist_added'] = 'failed'
                        update_job_progress(job_id, {'stages': stages})
            except Exception as e:
                print(f"[DOWNLOAD] Warning: Failed to update Plex playlist: {str(e)}", flush=True)
                stages['playlist_added'] = 'failed'
                update_job_progress(job_id, {'stages': stages})
        else:
            missing = []
            if not plex_config['server_url']:
                missing.append('server_url')
            if not plex_config['api_token']:
                missing.append('api_token')
            if not playlist_name:
                missing.append('playlist_name')
            if missing:
                print(f"[DOWNLOAD] Plex playlist update skipped. Missing: {', '.join(missing)}", flush=True)
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

    for quality in quality_candidates:
        try:
            manifest_response, target = make_request_with_retry_rotating_mirrors(
                f"/track/?id={track_id}&quality={quality}",
                url_iterator,
                method='GET',
                timeout=10,
                max_retries=3
            )
        except requests.exceptions.RequestException as e:
            raise TransientDownloadError(f"Failed to fetch track manifest: {str(e)}") from e
        last_manifest_status = manifest_response.status_code

        if not manifest_response.ok:
            continue

        manifest_data = manifest_response.json()
        print(f"[DOWNLOAD] Track info response keys: {manifest_data.keys()}", flush=True)

        if isinstance(manifest_data, dict):
            data = manifest_data.get('data')
            if isinstance(data, dict):
                manifest_base64 = data.get('manifest') or data.get('manifestBase64')

            if not manifest_base64:
                manifest_base64 = manifest_data.get('manifest') or manifest_data.get('manifestBase64')

        if isinstance(manifest_base64, str) and manifest_base64:
            break

    if not isinstance(manifest_base64, str) or not manifest_base64:
        status_note = f" Status: {last_manifest_status}" if last_manifest_status is not None else ""
        raise ManifestDownloadError(f"Failed to get track manifest.{status_note}")

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
        'title': track_title,
        'album': album_name,
        'year': release_year,
        'track_number': track_num
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
        stages['converted'] = 'done'
        stages['written'] = 'done'
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
        update_job_progress(job_id, {'stages': stages})
        cleanup_file(temp_source_path)
        print(f"[DOWNLOAD] SUCCESS: Downloaded and saved to {full_path}", flush=True)

    plex_config = get_plex_config()
    playlist_name = payload.get('plex_playlist')
    if plex_config['server_url'] and plex_config['api_token'] and playlist_name:
        try:
            print("[DOWNLOAD] Plex config OK - attempting playlist update", flush=True)
            track_info = {
                'artist': artist_name,
                'album': album_name,
                'title': track_title
            }
            success, plex_message = add_tracks_to_plex_playlist(
                plex_config['server_url'],
                plex_config['api_token'],
                plex_config['library_name'] or 'Music',
                playlist_name,
                track_info
            )

            if success:
                print(f"[DOWNLOAD] Plex playlist updated: {plex_message}", flush=True)
                stages['playlist_added'] = 'done'
                update_job_progress(job_id, {'stages': stages})
            else:
                print(f"[DOWNLOAD] Plex playlist note: {plex_message}", flush=True)
                if 'not yet indexed' in plex_message.lower() or 'not found' in plex_message.lower():
                    queue_pending_playlist_addition(
                        artist_name,
                        album_name,
                        track_title,
                        playlist_name,
                        parent_job_id=job_id
                    )
                    stages['playlist_added'] = 'queued'
                    update_job_progress(job_id, {'stages': stages})
                else:
                    stages['playlist_added'] = 'failed'
                    update_job_progress(job_id, {'stages': stages})
        except Exception as e:
            print(f"[DOWNLOAD] Warning: Failed to update Plex playlist: {str(e)}", flush=True)
            stages['playlist_added'] = 'failed'
            update_job_progress(job_id, {'stages': stages})
    else:
        missing = []
        if not plex_config['server_url']:
            missing.append('server_url')
        if not plex_config['api_token']:
            missing.append('api_token')
        if not playlist_name:
            missing.append('playlist_name')
        if missing:
            print(f"[DOWNLOAD] Plex playlist update skipped. Missing: {', '.join(missing)}", flush=True)
        stages['playlist_added'] = 'skipped'
        update_job_progress(job_id, {'stages': stages})

    return {
        'file_path': full_path,
        'format': file_format,
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': playlist_name,
        'stages': stages
    }

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
                mark_job_succeeded(job['id'], result)
                print(f"[DOWNLOAD_WORKER] Job {job['id']} completed", flush=True)
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
                    track_info = {
                        'artist': payload.get('artist', 'Unknown Artist'),
                        'album': payload.get('album', 'Unknown Album'),
                        'title': payload.get('title', 'Unknown Track')
                    }
                    playlist_name = payload.get('playlist_name')
                    
                    success, message = add_tracks_to_plex_playlist(
                        plex_config['server_url'],
                        plex_config['api_token'],
                        plex_config['library_name'] or 'Music',
                        playlist_name,
                        track_info
                    )
                    
                    if success:
                        print(f"[PLEX_WORKER] Successfully added: {track_info['artist']} - {track_info['title']}", flush=True)
                        remove_pending_addition(addition['id'])
                        update_parent_playlist_stage(parent_job_id, 'done')
                    else:
                        update_pending_addition_attempt(addition['id'], message)
                        if addition['attempt_count'] + 1 >= addition['max_attempts']:
                            update_parent_playlist_stage(parent_job_id, 'failed')
                            print(f"[PLEX_WORKER] Max attempts reached for: {track_info['artist']} - {track_info['title']}", flush=True)
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
        SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album
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
                id, format, parent_folder, file_naming, file_naming_loose, file_naming_album, updated_at
            )
            VALUES (1, %s, %s, %s, %s, %s, %s)
            """,
            (
                DEFAULT_DOWNLOAD_SETTINGS['format'],
                DEFAULT_DOWNLOAD_SETTINGS['parent_folder'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                now
            )
        )
        conn.commit()
        cur.execute(
            """
            SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album
            FROM download_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()

    file_naming_loose = row['file_naming_loose'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose']
    file_naming_album = row['file_naming_album'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']

    if row['file_naming_loose'] is None or row['file_naming_album'] is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            UPDATE download_settings
            SET file_naming_loose = %s, file_naming_album = %s, updated_at = %s
            WHERE id = 1
            """,
            (
                file_naming_loose,
                file_naming_album,
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
        'file_naming_album': file_naming_album
    }

def save_download_settings(settings):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO download_settings (
            id, format, parent_folder, file_naming, file_naming_loose, file_naming_album, updated_at
        )
        VALUES (1, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            format = excluded.format,
            parent_folder = excluded.parent_folder,
            file_naming = excluded.file_naming,
            file_naming_loose = excluded.file_naming_loose,
            file_naming_album = excluded.file_naming_album,
            updated_at = excluded.updated_at
        """,
        (
            settings['format'],
            settings['parent_folder'],
            settings['file_naming_loose'],
            settings['file_naming_loose'],
            settings['file_naming_album'],
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

def get_plex_music_playlists(server_url, api_token):
    """
    Get existing Plex music playlists, excluding smart playlists.

    Returns:
        tuple: (success: bool, playlists: list[str], error: str | None)
    """
    try:
        plex = PlexServer(server_url.rstrip('/'), api_token, timeout=10)
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

def add_tracks_to_plex_playlist(server_url, api_token, library_name, playlist_name, track_info):
    """
    Add downloaded tracks to a Plex playlist.
    
    Args:
        server_url: Plex server URL
        api_token: Plex API token
        library_name: Name of the music library (e.g., "Music")
        playlist_name: Name of the playlist to add to
        track_info: Dict with 'artist', 'album', 'title' of the downloaded track
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        server_url = server_url.rstrip('/')
        token_len = len(api_token) if isinstance(api_token, str) else 0
        print(
            f"[PLEX] Add-to-playlist start: url={server_url}, library='{library_name}', playlist='{playlist_name}', token_len={token_len}",
            flush=True
        )
        plex = PlexServer(server_url, api_token, timeout=10)
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
        
        # Search for the track in the library
        artist = track_info.get('artist', 'Unknown')
        album = track_info.get('album', 'Unknown')
        title = track_info.get('title', 'Unknown')
        
        print(f"[PLEX] Searching for track: {artist} - {album} - {title}", flush=True)
        
        # Try to find the track with multiple search strategies
        tracks = []
        try:
            # Strategy 1: Search with title + artist + album filters (most precise)
            print(f"[PLEX] Trying search with title + artist + album filters", flush=True)
            search_results = library.search(
                title=title,
                filters={'artist.title': artist, 'album.title': album},
                libtype='track'
            )
            print(f"[PLEX] Search with all filters found {len(search_results)} results", flush=True)
            
            if search_results:
                tracks = search_results
                print(f"[PLEX] Using result from artist + album + title search", flush=True)
            else:
                # Strategy 2: Search with title + artist only (if album didn't match)
                print(f"[PLEX] Trying search with title + artist filter only", flush=True)
                search_results = library.search(
                    title=title,
                    filters={'artist.title': artist},
                    libtype='track'
                )
                print(f"[PLEX] Search with artist filter found {len(search_results)} results", flush=True)
                
                if search_results:
                    tracks = search_results
                    print(f"[PLEX] Using result from artist + title search (album may not match)", flush=True)
                else:
                    # Strategy 3: Basic title search as last resort
                    print(f"[PLEX] Trying basic title search", flush=True)
                    search_results = library.search(title=title, libtype='track')
                    print(f"[PLEX] Basic title search found {len(search_results)} results", flush=True)
                    
                    # Filter manually for artist match
                    for result in search_results:
                        if hasattr(result, 'artist'):
                            result_artist = result.artist().title if callable(result.artist) else result.artist.title
                            if result_artist.lower() == artist.lower():
                                tracks.append(result)
                                print(f"[PLEX] Found matching artist in basic search: {result_artist}", flush=True)
                                break
                    
                    if tracks:
                        print(f"[PLEX] Using artist-matched result from basic title search", flush=True)
                    else:
                        print(f"[PLEX] No matching tracks found with any search strategy", flush=True)
        
        except Exception as e:
            print(f"[PLEX] Error searching for track: {str(e)}", flush=True)
            return False, f'Error searching for track: {str(e)}'
        
        if not tracks:
            print(f"[PLEX] Track not found in Plex library: {artist} - {title}", flush=True)
            return False, f'Track "{title}" by {artist} not found in {library_name} library. Please ensure the album and tracks have been added to your Plex library and scanned.'
        
        track = tracks[0]
        
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
                return True, f'Track already in playlist "{playlist_name}"'
            print(f"[PLEX] Error adding track to playlist: {str(e)}", flush=True)
            return False, f'Error adding to playlist: {str(e)}'
    
    except Exception as e:
        print(f"[PLEX] Unexpected error: {str(e)}", flush=True)
        return False, f'Unexpected error: {str(e)}'

# Validation Functions
def validate_endpoint(url, name, test_query="22 by Taylor Swift", timeout=5):
    """
    Validate a single endpoint by performing a search query.
    Records response time, checks if endpoint is online, and optionally validates search results.
    
    Args:
        url: Base URL of the endpoint
        name: Name of the endpoint
        test_query: Query to search for (default: "22 by Taylor Swift")
        timeout: Request timeout in seconds
    
    Returns:
        Dict with validation results including online status, response time, and search validation
    """
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    try:
        start_time = time.time()
        response = requests.get(
            f"{url}/search/?s={requests.utils.quote(test_query)}",
            timeout=timeout
        )
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Check if endpoint is online and returning valid data
        online = False
        search_working = False
        song_found = False
        results_count = 0
        error = None
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Valid squid.wtf response should have 'data' field
                if 'data' in data:
                    online = True
                    items = data.get('data', {}).get('items', [])
                    results_count = len(items)
                    
                    if results_count > 0:
                        search_working = True
                        
                        # Look for "22" by Taylor Swift in the results
                        for track in items:
                            title = track.get('title', '').lower()
                            
                            # Check artists array
                            artists = track.get('artists', [])
                            artist_names = ' '.join([a.get('name', '').lower() for a in artists])
                            
                            # Also check singular artist field as fallback
                            if not artist_names and 'artist' in track:
                                artist_names = track.get('artist', {}).get('name', '').lower()
                            
                            # Check if this is the song we're looking for
                            if '22' in title and 'taylor swift' in artist_names:
                                song_found = True
                                break
                else:
                    error = 'Invalid response structure'
                    
            except json.JSONDecodeError:
                error = 'Invalid JSON response'
        else:
            error = f'HTTP {response.status_code}'
        
        return {
            'online': online,
            'responseTime': round(response_time, 2) if online else None,
            'lastChecked': timestamp,
            'searchWorking': search_working,
            'songFound': song_found,
            'resultsCount': results_count,
            'error': error
        }
        
    except requests.exceptions.Timeout:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'searchWorking': False,
            'songFound': False,
            'resultsCount': 0,
            'error': 'Timeout'
        }
    except requests.exceptions.RequestException as e:
        return {
            'online': False,
            'responseTime': None,
            'lastChecked': timestamp,
            'searchWorking': False,
            'songFound': False,
            'resultsCount': 0,
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
    search_working_count = 0
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Validate each endpoint
    for entry in urls_data:
        name = entry['name']
        decoded_url = base64.b64decode(entry['encodedUrl']).decode('utf-8')
        
        print(f"\n[{name}] Checking {decoded_url}...", flush=True)
        
        # Validate endpoint (ping + search test in one call)
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
            
            if result['searchWorking']:
                if result['songFound']:
                    search_working_count += 1
                    print(f"  ✓ Search working - Found '22 by Taylor Swift' ({result['resultsCount']} results)", flush=True)
                else:
                    print(f"  ⚠ Search working but song not found ({result['resultsCount']} results)", flush=True)
            else:
                print(f"  ✗ Search failed - {result.get('error', 'No results')}", flush=True)
        else:
            offline_count += 1
            error_msg = result.get('error', 'Unknown error')
            print(f"  ✗ OFFLINE - {error_msg}", flush=True)
    
    conn.commit()
    conn.close()
    
    # Print summary
    print("\n" + "="*60, flush=True)
    print("Validation Complete", flush=True)
    print("="*60, flush=True)
    print(f"Total endpoints: {len(urls_data)}", flush=True)
    print(f"Online: {online_count}", flush=True)
    print(f"Offline: {offline_count}", flush=True)
    print(f"Search functionality working: {search_working_count}", flush=True)
    print("="*60 + "\n", flush=True)
    
    return {
        'total': len(urls_data),
        'online': online_count,
        'offline': offline_count,
        'search_working': search_working_count
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
seed_mirrors_from_json()

# Initialize URL list and round-robin iterator
SQUID_URLS = load_squid_urls()
url_iterator = cycle(SQUID_URLS)

# Run validation on startup
# With gunicorn --preload, this runs once before workers are forked
print("Squidly starting up...", flush=True)
validate_all_endpoints()
backfill_plex_add_parent_links()
print("Validation complete, server ready to accept requests.\n", flush=True)

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

# Start scheduler for interval-based Plex sync jobs
plex_sync_scheduler_thread = threading.Thread(target=plex_sync_scheduler_worker, daemon=True)
plex_sync_scheduler_thread.start()
print("Plex library sync scheduler started\n", flush=True)

# Start background worker for library update
library_update_thread = threading.Thread(target=library_update_worker, daemon=True)
library_update_thread.start()
print("Library update worker started\n", flush=True)

# Download folders already created and validated at module level above

try:
    os.makedirs('/app/temp', exist_ok=True)
    print("Temp folder ready (/app/temp)", flush=True)
except Exception as e:
    print(f"WARNING: Failed to create temp folder: {str(e)}", flush=True)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/search/', methods=['GET'])
def search():
    """
    Unified search endpoint for tracks, albums, artists, and playlists.
    Query parameters:
    - s={query}  : Search tracks
    - a={query}  : Search artists
    - al={query} : Search albums
    - p={query}  : Search playlists
    """
    # Determine search type based on query parameters
    search_type = None
    query = None
    
    if 's' in request.args:
        search_type = 's'
        query = request.args.get('s')
    elif 'a' in request.args:
        search_type = 'a'
        query = request.args.get('a')
    elif 'al' in request.args:
        search_type = 'al'
        query = request.args.get('al')
    elif 'p' in request.args:
        search_type = 'p'
        query = request.args.get('p')
    else:
        return jsonify({'error': 'No search parameter provided. Use s, a, al, or p'}), 400
    
    if not query:
        return jsonify({'error': 'Query value cannot be empty'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/search/?{search_type}={query}",
            url_iterator,
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
    track_id = request.args.get('id')
    
    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/info/?id={track_id}",
            url_iterator,
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
    album_id = request.args.get('id')
    
    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/album/?id={album_id}",
            url_iterator,
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
    artist_id = request.args.get('f')
    
    if not artist_id:
        return jsonify({'error': 'Artist ID parameter (f) is required'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/artist/?f={artist_id}",
            url_iterator,
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
    playlist_id = request.args.get('id')
    
    if not playlist_id:
        return jsonify({'error': 'Playlist ID parameter is required'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/playlist/?id={playlist_id}",
            url_iterator,
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
    track_id = request.args.get('id')
    quality = request.args.get('quality', 'HIGH')
    
    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/track/?id={track_id}&quality={quality}",
            url_iterator,
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

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Legacy POST endpoint for backward compatibility with the UI.
    Accepts JSON body with 'query' field and searches for tracks.
    """
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        response, target = make_request_with_retry_rotating_mirrors(
            f"/search/?s={requests.utils.quote(query)}",
            url_iterator,
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
            'details': str(e),
            'query': query
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

def format_album_cover_url(cover: str) -> str:
    """
    Format album cover URL for Tidal CDN.
    Converts dashes to forward slashes in the cover path.
    
    Args:
        cover: Cover ID or path (may contain dashes)
    
    Returns:
        Full URL to the cover image
    """
    if not cover:
        return ''
    
    # Convert dashes to forward slashes for Tidal CDN format
    cover_path = cover.replace('-', '/')
    return f"https://resources.tidal.com/images/{cover_path}/1280x1280.jpg"

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
        metadata: Dict with keys: artist, title, album, year, track_number
        cover_image_data: Binary image data to embed as cover art
    """
    try:
        artist = metadata.get('artist', 'Unknown Artist')
        title = metadata.get('title', 'Unknown Track')
        album = metadata.get('album', 'Unknown Album')
        year = metadata.get('year', '')
        track_num = metadata.get('track_number', '1')
        
        # Handle FLAC files
        if file_path.lower().endswith('.flac'):
            try:
                audio = FLAC(file_path)
                audio['TITLE'] = title
                audio['ARTIST'] = artist
                audio['ALBUM'] = album
                if year:
                    audio['DATE'] = str(year)
                audio['TRACKNUMBER'] = str(track_num)
                
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
                audio['\xa9alb'] = album
                
                if year:
                    audio['\xa9day'] = str(year)
                
                if track_num:
                    try:
                        track_number = int(track_num)
                        audio['trkn'] = [(track_number, 0)]
                    except ValueError:
                        pass
                
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
                audio['TALB'] = TALB(encoding=3, text=album)
                if year:
                    audio['TDRC'] = TDRC(encoding=3, text=str(year))
                audio['TRCK'] = TRCK(encoding=3, text=str(track_num))
                
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

    job_payload = {
        'trackId': track_id,
        'format': file_format,
        'downloadType': download_type,
        'fileNaming': file_naming,
        'fileNamingAlbum': payload.get('fileNamingAlbum') or file_naming_album,
        'fileNamingLoose': payload.get('fileNamingLoose') or file_naming_loose,
        'plex_playlist': payload.get('plex_playlist')
    }

    job_id = enqueue_job('download_track', job_payload)
    print(f"[DOWNLOAD] Queued download job {job_id} for track {track_id}", flush=True)
    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List jobs with optional filters.
    Query parameters:
    - status: filter by job status
    - job_type: filter by job type
    - limit: max number of rows (default 50, max 200)
    """
    status_filter = request.args.get('status')
    job_type_filter = request.args.get('job_type')
    try:
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 200))

    where_clauses = []
    params = []
    if status_filter:
        where_clauses.append('status = %s')
        params.append(status_filter)
    if job_type_filter:
        where_clauses.append('job_type = %s')
        params.append(job_type_filter)

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
        LIMIT %s
        """,
        (*params, limit)
    )
    rows = cur.fetchall()
    conn.close()

    jobs = []
    for row in rows:
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

    return jsonify({'jobs': jobs})

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

@app.route('/api/jobs/cancel-pending', methods=['POST'])
def cancel_all_pending_jobs():
    """Delete all pending (queued) jobs from the queue/table."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM jobs
        WHERE status = 'queued'
        """
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
        SELECT job_type, status, result_json
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

    retryable = row['status'] == 'failed'

    if not retryable and row['status'] == 'succeeded':
        try:
            result = json.loads(row['result_json']) if row['result_json'] else {}
        except (TypeError, ValueError):
            result = {}

        stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}
        retryable = stages.get('playlist_added') == 'failed'

    if not retryable:
        conn.close()
        return jsonify({'error': f"Job is not retryable (status={row['status']})"}), 400

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
        'file_naming_album': file_naming_album
    }

    if updated['format'] not in ('original', 'mp3'):
        return jsonify({'error': 'Invalid format value'}), 400

    if not isinstance(updated['file_naming_loose'], str) or not isinstance(updated['file_naming_album'], str):
        return jsonify({'error': 'Invalid settings payload'}), 400

    save_download_settings(updated)
    return jsonify({
        'format': updated['format'],
        'file_naming': updated['file_naming_loose'],
        'file_naming_loose': updated['file_naming_loose'],
        'file_naming_album': updated['file_naming_album']
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

    return jsonify({
        'endpoints': endpoints,
        'summary': {
            'total': len(endpoints),
            'online': sum(1 for e in endpoints if e.get('online')),
            'offline': sum(1 for e in endpoints if not e.get('online'))
        }
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
    config = get_plex_config()
    if not config.get('server_url') or not config.get('api_token') or not config.get('library_name'):
        return jsonify({'error': 'Plex is not fully configured'}), 400

    job_id = queue_plex_library_sync(trigger='manual')
    if job_id is None:
        return jsonify({'error': 'A Plex sync job is already queued or in progress'}), 409

    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202

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

    success, playlists, message = get_plex_music_playlists(server_url, api_token)
    if not success:
        return jsonify({'error': f'Failed to fetch Plex playlists: {message}'}), 500

    return jsonify({'playlists': playlists})

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

        rows = []

        if album:
            cur.execute(
                """
                SELECT format, bitrate
                FROM plex_songs
                WHERE lower(title) = lower(%s)
                  AND lower(COALESCE(artist, '')) = lower(%s)
                  AND lower(COALESCE(album, '')) = lower(%s)
                """,
                (title, artist, album)
            )
            rows = cur.fetchall() or []

        if not rows:
            cur.execute(
                """
                SELECT format, bitrate
                FROM plex_songs
                WHERE lower(title) = lower(%s)
                  AND lower(COALESCE(artist, '')) = lower(%s)
                """,
                (title, artist)
            )
            rows = cur.fetchall() or []

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
                'bitrate': bitrate_int
            })

        matches.append({
            'exists': len(rows) > 0,
            'variants': variants
        })

    conn.close()
    return jsonify({'matches': matches})
