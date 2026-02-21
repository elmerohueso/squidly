from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
import base64
import requests
import sqlite3
from itertools import cycle
from datetime import datetime
import time
import sys
import subprocess
import shutil
import re
import threading
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from io import BytesIO
from plexapi.server import PlexServer

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Create data folder if it doesn't exist
data_dir = '/data'
try:
    os.makedirs(data_dir, exist_ok=True)
except Exception as e:
    # Directory likely already exists (mounted volume)
    pass

# Verify directory is writable
if not os.access(data_dir, os.W_OK):
    print(f"Error: Data directory {data_dir} is not writable!", file=sys.stderr)

DB_PATH = os.path.join(data_dir, 'squidly.db')
DOWNLOADS_ROOT = '/downloads'
DOWNLOADS_FULL_ALBUMS_FOLDER = 'full_albums'
DOWNLOADS_LOOSE_TRACKS_FOLDER = 'loose_tracks'

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
    'file_naming_loose': '{artist} - {title}.{ext}',
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
    
    for attempt in range(max_retries + 1):
        try:
            # Get a new mirror for each attempt
            target = next(url_iterator)
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS download_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            format TEXT NOT NULL,
            parent_folder TEXT NOT NULL,
            file_naming TEXT,
            file_naming_loose TEXT,
            file_naming_album TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {
        row['name']
        for row in cur.execute("PRAGMA table_info(download_settings)").fetchall()
    }
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
            last_checked TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS listenbrainz_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            user_token TEXT,
            username TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plex_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            server_url TEXT,
            api_token TEXT,
            library_name TEXT,
            update_playlist_name TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            artist TEXT NOT NULL,
            album TEXT NOT NULL,
            title TEXT NOT NULL,
            format TEXT,
            download_status TEXT,
            conversion_status TEXT,
            playlist_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_attempt_at TEXT,
            attempt_count INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 20
        )
        """
    )
    
    # Add new columns to existing jobs tables (backward compatibility)
    columns = {
        row['name']
        for row in cur.execute("PRAGMA table_info(jobs)").fetchall()
    }
    if 'track_id' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN track_id TEXT")
    if 'format' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN format TEXT")
    if 'download_status' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN download_status TEXT")
    if 'conversion_status' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN conversion_status TEXT")
    
    conn.commit()
    conn.close()

def get_listenbrainz_config():
    conn = get_db_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT user_token
        FROM listenbrainz_config
        WHERE id = 1
        """
    ).fetchone()
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
        VALUES (1, ?, NULL, ?)
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
    row = cur.execute(
        """
        SELECT server_url, api_token, library_name
        FROM plex_config
        WHERE id = 1
        """
    ).fetchone()
    conn.close()
    
    if row is None:
        return {
            'server_url': None,
            'api_token': None,
            'library_name': None
        }
    
    return {
        'server_url': row['server_url'],
        'api_token': row['api_token'],
        'library_name': row['library_name']
    }

def save_plex_config(server_url, api_token, library_name):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO plex_config (id, server_url, api_token, library_name, updated_at)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            server_url = excluded.server_url,
            api_token = excluded.api_token,
            library_name = excluded.library_name,
            updated_at = excluded.updated_at
        """,
        (server_url, api_token, library_name, now)
    )
    conn.commit()
    conn.close()

def queue_pending_playlist_addition(artist, album, title, playlist_name):
    """Add a track to the pending playlist additions queue."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if this track is already queued
    existing = cur.execute(
        """
        SELECT id FROM jobs
        WHERE artist = ? AND album = ? AND title = ? AND playlist_name = ?
        """,
        (artist, album, title, playlist_name)
    ).fetchone()
    
    if existing:
        print(f"[PLEX_QUEUE] Track already in queue: {artist} - {title}", flush=True)
        conn.close()
        return
    
    cur.execute(
        """
        INSERT INTO jobs
        (artist, album, title, playlist_name, created_at, attempt_count)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (artist, album, title, playlist_name, now)
    )
    conn.commit()
    conn.close()
    print(f"[PLEX_QUEUE] Queued for retry: {artist} - {title}", flush=True)

def get_pending_playlist_additions():
    """Get all pending playlist additions that haven't exceeded max attempts."""
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, artist, album, title, playlist_name, attempt_count, max_attempts
        FROM jobs
        WHERE attempt_count < max_attempts
        ORDER BY created_at ASC
        """
    ).fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_pending_addition_attempt(addition_id):
    """Increment the attempt count and update last_attempt_at."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET attempt_count = attempt_count + 1, last_attempt_at = ?
        WHERE id = ?
        """,
        (now, addition_id)
    )
    conn.commit()
    conn.close()

def remove_pending_addition(addition_id):
    """Remove a successfully added track from the queue."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM job_queue WHERE id = ?",
        (addition_id,)
    )
    conn.commit()
    conn.close()

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
                try:
                    track_info = {
                        'artist': addition['artist'],
                        'album': addition['album'],
                        'title': addition['title']
                    }
                    
                    success, message = add_tracks_to_plex_playlist(
                        plex_config['server_url'],
                        plex_config['api_token'],
                        plex_config['library_name'] or 'Music',
                        addition['playlist_name'],
                        track_info
                    )
                    
                    if success:
                        print(f"[PLEX_WORKER] Successfully added: {addition['artist']} - {addition['title']}", flush=True)
                        remove_pending_addition(addition['id'])
                    else:
                        update_pending_addition_attempt(addition['id'])
                        if addition['attempt_count'] + 1 >= addition['max_attempts']:
                            print(f"[PLEX_WORKER] Max attempts reached for: {addition['artist']} - {addition['title']}", flush=True)
                        else:
                            print(f"[PLEX_WORKER] Retry failed (attempt {addition['attempt_count'] + 1}/{addition['max_attempts']}): {message}", flush=True)
                    
                    # Small delay between tracks to avoid hammering Plex
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[PLEX_WORKER] Error processing addition {addition['id']}: {str(e)}", flush=True)
                    update_pending_addition_attempt(addition['id'])
        
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
            VALUES (?, ?, ?, ?, ?)
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
    row = cur.execute(
        """
        SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album
        FROM download_settings
        WHERE id = 1
        """
    ).fetchone()

    if row is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            INSERT INTO download_settings (
                id, format, parent_folder, file_naming, file_naming_loose, file_naming_album, updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?)
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
        row = cur.execute(
            """
            SELECT format, parent_folder, file_naming, file_naming_loose, file_naming_album
            FROM download_settings
            WHERE id = 1
            """
        ).fetchone()

    file_naming_loose = row['file_naming_loose'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_loose']
    file_naming_album = row['file_naming_album'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']

    if row['file_naming_loose'] is None or row['file_naming_album'] is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            UPDATE download_settings
            SET file_naming_loose = ?, file_naming_album = ?, updated_at = ?
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
        VALUES (1, ?, ?, ?, ?, ?, ?)
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
        
        # Try to find the track with intelligent matching
        tracks = []
        try:
            # First, search by title
            search_results = library.search(title=title)
            print(f"[PLEX] Search results count: {len(search_results)}", flush=True)
            
            # Define matching strategies in order of preference
            exact_match = None
            artist_album_match = None
            artist_match = None
            
            # Evaluate each result
            for result in search_results:
                if not (hasattr(result, 'artist') and hasattr(result, 'album')):
                    continue
                
                result_artist = result.artist.title if hasattr(result.artist, 'title') else str(result.artist)
                result_album = result.album.title if hasattr(result.album, 'title') else str(result.album)
                
                artist_match_lower = result_artist.lower() == artist.lower()
                album_match_lower = result_album.lower() == album.lower()
                
                # Strategy 1: Exact match (artist AND album)
                if artist_match_lower and album_match_lower:
                    exact_match = result
                    print(f"[PLEX] Found exact match: {result_artist} - {result_album} - {title}", flush=True)
                    break
                
                # Strategy 2: Artist + Album match (keep first one found)
                if artist_match_lower and album_match_lower and not artist_album_match:
                    artist_album_match = result
                
                # Strategy 3: Artist match only (keep first one found)
                if artist_match_lower and not artist_match:
                    artist_match = result
            
            # Use the best match found
            if exact_match:
                tracks.append(exact_match)
                print(f"[PLEX] Using exact match (artist + album + title)", flush=True)
            elif artist_album_match:
                tracks.append(artist_album_match)
                print(f"[PLEX] Using artist + album match", flush=True)
            elif artist_match:
                tracks.append(artist_match)
                print(f"[PLEX] Using artist match only (album not found in library)", flush=True)
            else:
                print(f"[PLEX] No suitable match found. Artist searched for: '{artist}'", flush=True)
                if search_results:
                    result_artist = search_results[0].artist.title if hasattr(search_results[0].artist, 'title') else str(search_results[0].artist)
                    print(f"[PLEX] First search result was: '{result_artist}' (not matching requested artist)", flush=True)
            
            print(f"[PLEX] Selected track count after filtering: {len(tracks)}", flush=True)
        
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
            SET online = ?, response_time = ?, last_checked = ?
            WHERE name = ?
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
seed_mirrors_from_json()

# Initialize URL list and round-robin iterator
SQUID_URLS = load_squid_urls()
url_iterator = cycle(SQUID_URLS)

# Run validation on startup
# With gunicorn --preload, this runs once before workers are forked
print("Squidly starting up...", flush=True)
validate_all_endpoints()
print("Validation complete, server ready to accept requests.\n", flush=True)

# Start background worker for retrying failed Plex playlist additions
plex_retry_thread = threading.Thread(target=retry_pending_playlist_additions, daemon=True)
plex_retry_thread.start()
print("Plex playlist retry worker started\n", flush=True)

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

def convert_flac_to_mp3(flac_path: str, mp3_path: str) -> bool:
    """
    Convert a FLAC file to 320kbps MP3 using ffmpeg.
    
    Args:
        flac_path: Path to the FLAC file
        mp3_path: Path where the MP3 should be saved
    
    Returns:
        True on success, False on failure
    """
    try:
        print(f"[FFMPEG] Converting FLAC to MP3: {flac_path} -> {mp3_path}", flush=True)
        
        # Create directory if needed
        mp3_dir = os.path.dirname(mp3_path)
        if mp3_dir:
            os.makedirs(mp3_dir, exist_ok=True)
        
        # Run ffmpeg to convert FLAC to 320kbps MP3
        cmd = [
            'ffmpeg',
            '-i', flac_path,
            '-b:a', '320k',
            '-q:a', '0',
            '-y',  # Overwrite output file
            mp3_path
        ]
        
        print(f"[FFMPEG] Command: {' '.join(cmd)}", flush=True)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"[FFMPEG] SUCCESS: Converted to {mp3_path}", flush=True)
            return True
        else:
            print(f"[FFMPEG] ERROR: Conversion failed with code {result.returncode}", flush=True)
            print(f"[FFMPEG] stderr: {result.stderr}", flush=True)
            return False
    
    except subprocess.TimeoutExpired:
        print(f"[FFMPEG] ERROR: Conversion timeout", flush=True)
        return False
    except Exception as e:
        print(f"[FFMPEG] ERROR: {str(e)}", flush=True)
        return False

def convert_m4a_to_mp3(m4a_path: str, mp3_path: str) -> bool:
    """
    Convert an M4A/AAC file to 320kbps MP3 using ffmpeg.
    
    Args:
        m4a_path: Path to the M4A file
        mp3_path: Path where the MP3 should be saved
    
    Returns:
        True on success, False on failure
    """
    try:
        print(f"[FFMPEG] Converting M4A to MP3: {m4a_path} -> {mp3_path}", flush=True)
        
        # Create directory if needed
        mp3_dir = os.path.dirname(mp3_path)
        if mp3_dir:
            os.makedirs(mp3_dir, exist_ok=True)
        
        # Run ffmpeg to convert M4A to 320kbps MP3
        cmd = [
            'ffmpeg',
            '-i', m4a_path,
            '-b:a', '320k',
            '-q:a', '0',
            '-y',  # Overwrite output file
            mp3_path
        ]
        
        print(f"[FFMPEG] Command: {' '.join(cmd)}", flush=True)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"[FFMPEG] SUCCESS: Converted M4A to {mp3_path}", flush=True)
            return True
        else:
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
    Download a track with specified settings.
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

    # Use the mounted downloads volume
    target_folder_name = DOWNLOADS_FULL_ALBUMS_FOLDER if download_type == 'album' else DOWNLOADS_LOOSE_TRACKS_FOLDER
    downloads_folder = os.path.join(DOWNLOADS_ROOT, target_folder_name)

    print(f"\n[DOWNLOAD] Request received for track {track_id}", flush=True)
    print(f"[DOWNLOAD] Format: {file_format}", flush=True)
    print(f"[DOWNLOAD] File naming template: {file_naming}", flush=True)
    print(f"[DOWNLOAD] Download type: {download_type}", flush=True)
    print(f"[DOWNLOAD] Downloads folder: {downloads_folder}", flush=True)

    if not track_id:
        print(f"[DOWNLOAD] ERROR: trackId is missing", flush=True)
        return jsonify({'error': 'trackId is required'}), 400

    if not os.path.exists(downloads_folder):
        print(f"[DOWNLOAD] WARNING: Downloads folder does not exist, creating it: {downloads_folder}", flush=True)
        try:
            os.makedirs(downloads_folder, exist_ok=True)
        except Exception as e:
            print(f"[DOWNLOAD] ERROR: Failed to create downloads folder: {str(e)}", flush=True)
            return jsonify({'error': f'Failed to create downloads folder: {str(e)}'}), 500

    try:
        # Step 1: Get track metadata from /info/ endpoint
        print(f"[DOWNLOAD] Fetching track metadata...", flush=True)
        
        info_response, target = make_request_with_retry_rotating_mirrors(
            f"/info/?id={track_id}",
            url_iterator,
            method='GET',
            timeout=10,
            max_retries=3
        )
        if not info_response.ok:
            print(f"[DOWNLOAD] ERROR: Failed to get track info. Status: {info_response.status_code}", flush=True)
            return jsonify({'error': f'Failed to get track info. Status: {info_response.status_code}'}), 502

        info_data = info_response.json()
        print(f"[DOWNLOAD] Track info response structure: {info_data.keys() if isinstance(info_data, dict) else type(info_data)}", flush=True)
        
        # Extract metadata from different possible response structures
        track_info = info_data.get('data', info_data) if isinstance(info_data, dict) else {}
        track_metadata = track_info.get('track', track_info) if 'track' in track_info else track_info
        
        artist_name = 'Unknown Artist'
        album_name = 'Unknown Album'
        track_title = 'Unknown Track'
        track_num = '01'
        release_year = ''
        cover_url = ''
        album_id = ''
        
        # Try to extract from different possible structures
        if isinstance(track_metadata, dict):
            # Try artist
            if 'artist' in track_metadata and isinstance(track_metadata['artist'], dict):
                artist_name = track_metadata['artist'].get('name', 'Unknown Artist')
            elif 'artists' in track_metadata and isinstance(track_metadata['artists'], list) and len(track_metadata['artists']) > 0:
                artist_name = track_metadata['artists'][0].get('name', 'Unknown Artist')
            elif 'artistName' in track_metadata:
                artist_name = track_metadata['artistName']
            
            # Try album
            if 'album' in track_metadata and isinstance(track_metadata['album'], dict):
                album_name = track_metadata['album'].get('title', 'Unknown Album')
                
                # Get album ID for cover URL construction
                if 'id' in track_metadata['album']:
                    album_id = track_metadata['album']['id']
                
                # Try to get cover from album object
                if 'cover' in track_metadata['album'] and track_metadata['album']['cover']:
                    cover_val = track_metadata['album']['cover']
                    # If cover is a string that looks like an ID (not a full URL), construct the URL
                    if isinstance(cover_val, str) and not cover_val.startswith('http'):
                        cover_url = format_album_cover_url(cover_val)
                    else:
                        cover_url = cover_val
                
                # Try alternative cover field names
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
            
            # Try title
            if 'title' in track_metadata:
                track_title = track_metadata['title']
            
            # Try track number
            if 'trackNumber' in track_metadata:
                track_num = str(track_metadata['trackNumber']).zfill(2)
            
            # Try to get release date
            if 'releaseDate' in track_metadata:
                try:
                    date_str = track_metadata['releaseDate']
                    if isinstance(date_str, str) and len(date_str) >= 4:
                        release_year = date_str[:4]
                except:
                    pass
            elif 'album' in track_metadata and isinstance(track_metadata['album'], dict):
                if 'releaseDate' in track_metadata['album']:
                    try:
                        date_str = track_metadata['album']['releaseDate']
                        if isinstance(date_str, str) and len(date_str) >= 4:
                            release_year = date_str[:4]
                    except:
                        pass
            
            # Fallback to copyright year if release date is unavailable
            if not release_year:
                release_year = extract_year_from_text(track_metadata.get('copyright', ''))
            if not release_year and 'album' in track_metadata and isinstance(track_metadata['album'], dict):
                release_year = extract_year_from_text(track_metadata['album'].get('copyright', ''))
            
            # If still no cover but we have album ID, construct URL from album ID
            if not cover_url and album_id:
                cover_url = format_album_cover_url(str(album_id))
            
            # Try to get cover from track if not already set
            if not cover_url:
                if 'cover' in track_metadata:
                    cover_val = track_metadata['cover']
                    if isinstance(cover_val, str) and not cover_val.startswith('http'):
                        cover_url = format_album_cover_url(cover_val)
                    else:
                        cover_url = cover_val
                
                # Try alternative track cover field names
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
        
        # Step 2: Determine best available quality from track metadata
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

        # Prioritize quality: HI_RES_LOSSLESS/HIRES_LOSSLESS > LOSSLESS > HIGH > LOW
        quality_priority = ['HI_RES_LOSSLESS', 'HIRES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW']
        for quality in quality_priority:
            if quality in media_tags and quality not in quality_candidates:
                quality_candidates.append(quality)

        if not quality_candidates:
            quality_candidates = ['HIGH', 'LOW']

        print(f"[DOWNLOAD] Available quality tags, selected: {quality_candidates}", flush=True)

        # Step 3: Get the track manifest for download (try multiple qualities)
        print(f"[DOWNLOAD] Fetching track manifest...", flush=True)
        manifest_base64 = None
        last_manifest_status = None

        for quality in quality_candidates:
            manifest_response, target = make_request_with_retry_rotating_mirrors(
                f"/track/?id={track_id}&quality={quality}",
                url_iterator,
                method='GET',
                timeout=10,
                max_retries=3
            )
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
            print(f"[DOWNLOAD] ERROR: No manifest returned from upstream.{status_note}", flush=True)
            return jsonify({'error': f'Failed to get track manifest.{status_note}'}), 502

        print(f"[DOWNLOAD] Got base64 manifest (length: {len(manifest_base64)})", flush=True)

        # Step 4: Decode the base64 manifest to get the actual CDN URLs
        try:
            normalized = manifest_base64.replace('-', '+').replace('_', '/')
            padding = '=' * (-len(normalized) % 4)
            manifest_json_bytes = base64.b64decode(normalized + padding)
            manifest_json = manifest_json_bytes.decode('utf-8')
            print(f"[DOWNLOAD] Decoded manifest: {manifest_json}", flush=True)

            manifest = json.loads(manifest_json)
            print(f"[DOWNLOAD] Parsed manifest keys: {manifest.keys()}", flush=True)
        except Exception as e:
            print(f"[DOWNLOAD] ERROR: Failed to decode base64 manifest: {str(e)}", flush=True)
            return jsonify({'error': f'Failed to decode manifest: {str(e)}'}), 502
        
        # Step 5: Extract the CDN download URL from the manifest
        if 'urls' not in manifest or not manifest['urls']:
            print(f"[DOWNLOAD] ERROR: No URLs in manifest", flush=True)
            return jsonify({'error': 'No download URLs found in manifest'}), 502
        
        download_urls = manifest['urls']
        if not isinstance(download_urls, list) or len(download_urls) == 0:
            print(f"[DOWNLOAD] ERROR: URLs is not a non-empty list", flush=True)
            return jsonify({'error': 'Invalid URLs format in manifest'}), 502
        
        download_url = download_urls[0]
        print(f"[DOWNLOAD] Download URL: {download_url}", flush=True)
        
        # Step 6: Build the file path using the naming template
        # Note: For 'original' format, we'll use a placeholder extension that will be
        # corrected after we detect the actual format (FLAC or M4A)
        file_ext = 'flac' if file_format == 'original' else 'mp3'
        
        # Sanitize metadata values before inserting into template
        safe_artist = sanitize_filename_component(artist_name)
        safe_album = sanitize_filename_component(album_name)
        safe_title = sanitize_filename_component(track_title)
        safe_track = sanitize_filename_component(track_num)
        
        # Replace placeholders in the file naming template
        file_path = file_naming.replace('{artist}', safe_artist)
        file_path = file_path.replace('{album}', safe_album)
        file_path = file_path.replace('{track}', safe_track)
        file_path = file_path.replace('{title}', safe_title)
        file_path = file_path.replace('{ext}', file_ext)
        
        # Clean path components to remove trailing periods and spaces
        file_path = clean_path_components(file_path)
        
        print(f"[DOWNLOAD] File path template result: {file_path}", flush=True)
        
        # Build full path and normalize separators
        full_path = os.path.join(downloads_folder, file_path)
        full_path = os.path.normpath(full_path)
        
        print(f"[DOWNLOAD] Full output path: {full_path}", flush=True)
        
        # Create all directories in the path
        output_dir = os.path.dirname(full_path)
        print(f"[DOWNLOAD] Creating directory structure: {output_dir}", flush=True)
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            print(f"[DOWNLOAD] SUCCESS: Directory created/exists: {output_dir}", flush=True)
        except Exception as e:
            print(f"[DOWNLOAD] ERROR: Failed to create directory: {str(e)}", flush=True)
            return jsonify({'error': f'Failed to create directory structure: {str(e)}'}), 500
        
        # Step 7: Download the actual audio file from Tidal CDN
        print(f"[DOWNLOAD] Downloading from CDN...", flush=True)
        track_response = make_request_with_retry(download_url, method='GET', timeout=60, max_retries=3, backoff_factor=2.0)
        
        if not track_response.ok:
            print(f"[DOWNLOAD] ERROR: Failed to download track. Status: {track_response.status_code}", flush=True)
            return jsonify({'error': f'Failed to download track from CDN. Status: {track_response.status_code}'}), 502
        
        print(f"[DOWNLOAD] Downloaded {len(track_response.content)} bytes", flush=True)
        
        # Step 7a: Detect the actual audio format from the downloaded blob
        audio_format = detect_audio_format(track_response.content)
        print(f"[DOWNLOAD] Detected audio format: {audio_format}", flush=True)
        
        if audio_format == 'unknown':
            print(f"[DOWNLOAD] WARNING: Could not detect audio format, assuming FLAC", flush=True)
            audio_format = 'flac'
        
        # Try to download cover image if URL is available
        cover_image_data = None
        if cover_url:
            cover_image_data = download_cover_image(cover_url)
        
        # Prepare metadata for ID3 tags
        metadata_dict = {
            'artist': artist_name,
            'title': track_title,
            'album': album_name,
            'year': release_year,
            'track_number': track_num
        }
        
        # Step 8: Stage to temp, add tags, then convert or move based on format
        temp_folder = '/app/temp'
        try:
            os.makedirs(temp_folder, exist_ok=True)
            print(f"[DOWNLOAD] Temp folder ready: {temp_folder}", flush=True)
        except Exception as e:
            print(f"[DOWNLOAD] ERROR: Failed to create temp folder: {str(e)}", flush=True)
            return jsonify({'error': f'Failed to create temp folder: {str(e)}'}), 500

        # Use appropriate extension based on detected format
        temp_source_ext = audio_format if audio_format in ['flac', 'm4a'] else 'flac'
        temp_source_path = os.path.join(temp_folder, f'temp_{track_id}.{temp_source_ext}')
        temp_mp3_path = os.path.join(temp_folder, f'temp_{track_id}.mp3')
        
        print(f"[DOWNLOAD] Saving temporary {temp_source_ext.upper()}: {temp_source_path}", flush=True)

        with open(temp_source_path, 'wb') as f:
            f.write(track_response.content)

        print(f"[DOWNLOAD] Adding metadata to staged {temp_source_ext.upper()}...", flush=True)
        add_id3_tags_to_file(temp_source_path, metadata_dict, cover_image_data)

        if file_format == 'mp3':
            print(f"[DOWNLOAD] Format is MP3 - converting staged {temp_source_ext.upper()}", flush=True)

            # Convert based on source format
            if audio_format == 'm4a':
                success = convert_m4a_to_mp3(temp_source_path, temp_mp3_path)
            else:  # flac or unknown (assumed flac)
                success = convert_flac_to_mp3(temp_source_path, temp_mp3_path)

            if not success:
                cleanup_file(temp_source_path)
                cleanup_file(temp_mp3_path)
                return jsonify({'error': f'Failed to convert {temp_source_ext.upper()} to MP3'}), 500

            try:
                shutil.move(temp_mp3_path, full_path)
            except Exception as e:
                print(f"[DOWNLOAD] ERROR: Failed to move MP3 to destination: {str(e)}", flush=True)
                cleanup_file(temp_source_path)
                cleanup_file(temp_mp3_path)
                return jsonify({'error': f'Failed to move MP3 to destination: {str(e)}'}), 500

            cleanup_file(temp_source_path)
            cleanup_file(temp_mp3_path)

            print(f"[DOWNLOAD] SUCCESS: Converted and saved MP3 to {full_path}", flush=True)
        else:
            # Original format requested - save with correct extension
            original_ext = 'm4a' if audio_format == 'm4a' else 'flac'
            
            # Update the file path to use the actual extension
            if not full_path.endswith(f'.{original_ext}'):
                full_path = full_path.rsplit('.', 1)[0] + f'.{original_ext}'
                print(f"[DOWNLOAD] Updated output path with correct extension: {full_path}", flush=True)
            
            print(f"[DOWNLOAD] Format is original ({original_ext.upper()}) - moving from temp", flush=True)
            try:
                shutil.move(temp_source_path, full_path)
            except Exception as e:
                print(f"[DOWNLOAD] ERROR: Failed to move {original_ext.upper()} to destination: {str(e)}", flush=True)
                cleanup_file(temp_source_path)
                return jsonify({'error': f'Failed to move {original_ext.upper()} to destination: {str(e)}'}), 500

            cleanup_file(temp_source_path)
            print(f"[DOWNLOAD] SUCCESS: Downloaded and saved to {full_path}", flush=True)
        
        # Try to add track to Plex playlist if configured
        plex_config = get_plex_config()
        playlist_name = payload.get('plex_playlist')
        if plex_config['server_url'] and plex_config['api_token'] and playlist_name:
            try:
                print(
                    "[DOWNLOAD] Plex config OK - attempting playlist update",
                    flush=True
                )
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
                else:
                    print(f"[DOWNLOAD] Plex playlist note: {plex_message}", flush=True)
                    # Queue for retry if track not found
                    if 'not yet indexed' in plex_message.lower() or 'not found' in plex_message.lower():
                        queue_pending_playlist_addition(
                            artist_name,
                            album_name,
                            track_title,
                            playlist_name
                        )
            except Exception as e:
                print(f"[DOWNLOAD] Warning: Failed to update Plex playlist: {str(e)}", flush=True)
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
        
        return jsonify({'success': True, 'message': f'Downloaded to {full_path}'})

    except requests.exceptions.Timeout:
        print(f"[DOWNLOAD] ERROR: Request timeout", flush=True)
        return jsonify({'error': 'Download timeout - endpoint took too long to respond'}), 504
    except requests.exceptions.RequestException as e:
        print(f"[DOWNLOAD] ERROR: Request exception: {str(e)}", flush=True)
        return jsonify({'error': f'Download failed: {str(e)}'}), 502
    except Exception as e:
        print(f"[DOWNLOAD] ERROR: Unexpected exception: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

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
    rows = conn.execute(
        """
        SELECT name, encoded_url, online, response_time, last_checked
        FROM mirror_endpoints
        ORDER BY name
        """
    ).fetchall()
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
        'library_name': config['library_name']
    })

@app.route('/api/plex/config', methods=['POST'])
def save_plex_config_endpoint():
    """Save Plex configuration"""
    payload = request.get_json()
    
    if not payload:
        return jsonify({'error': 'No JSON payload provided'}), 400
    
    server_url = payload.get('server_url', '').strip()
    api_token = payload.get('api_token', '').strip()
    library_name = payload.get('library_name', '')
    
    if not server_url or not api_token:
        return jsonify({'error': 'server_url and api_token are required'}), 400
    
    save_plex_config(server_url, api_token, library_name)
    return jsonify({'success': True})

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
