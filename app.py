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
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TRCK
from mutagen.mp3 import MP3
from io import BytesIO

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
DEFAULT_DOWNLOAD_SETTINGS = {
    'format': 'original',
    'parent_folder': '',
    'file_naming_loose': '{artist} - {title}.{ext}',
    'file_naming_album': '{artist}/{album}/{track} - {title}.{ext}'
}

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
    conn.commit()
    conn.close()

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

# Create downloads and temp folders if they don't exist
try:
    os.makedirs(DOWNLOADS_ROOT, exist_ok=True)
    os.makedirs(os.path.join(DOWNLOADS_ROOT, DOWNLOADS_FULL_ALBUMS_FOLDER), exist_ok=True)
    os.makedirs(os.path.join(DOWNLOADS_ROOT, DOWNLOADS_LOOSE_TRACKS_FOLDER), exist_ok=True)
    print(f"Downloads folder ready ({DOWNLOADS_ROOT})", flush=True)
    print(
        f"Full albums folder ready ({os.path.join(DOWNLOADS_ROOT, DOWNLOADS_FULL_ALBUMS_FOLDER)})",
        flush=True
    )
    print(
        f"Loose tracks folder ready ({os.path.join(DOWNLOADS_ROOT, DOWNLOADS_LOOSE_TRACKS_FOLDER)})",
        flush=True
    )
except Exception as e:
    print(f"WARNING: Failed to create downloads folder: {str(e)}", flush=True)

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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/search/?{search_type}={query}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/info/?id={track_id}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/album/?id={album_id}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/artist/?f={artist_id}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/playlist/?id={playlist_id}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/track/?id={track_id}&quality={quality}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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
    
    # Get next URL in round-robin
    target = next(url_iterator)
    target_url = f"{target['url']}/search/?s={requests.utils.quote(query)}"
    
    try:
        response = requests.get(target_url, timeout=10)
        
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
            'error': f'Proxy error via {target["name"]}',
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

def clean_path_components(file_path: str) -> str:
    """
    Clean file path by removing trailing periods and spaces from each directory component.
    This prevents invalid folder names on Windows and other filesystems.
    
    Args:
        file_path: File path with potential trailing periods/spaces in components
    
    Returns:
        Cleaned file path
    """
    # Split path into components
    parts = file_path.replace('\\', '/').split('/')
    # Strip trailing periods and spaces from each component
    cleaned_parts = [part.rstrip('. ') for part in parts]
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

def add_id3_tags_to_file(file_path, metadata, cover_image_data=None):
    """
    Add ID3 tags to an audio file (handles both FLAC and MP3).
    
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
        target = next(url_iterator)
        info_url = f"{target['url']}/info/?id={track_id}"
        
        info_response = requests.get(info_url, timeout=10)
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
        
        # Step 2: Get the track manifest for download
        print(f"[DOWNLOAD] Fetching track manifest...", flush=True)
        target = next(url_iterator)
        manifest_url = f"{target['url']}/track/?id={track_id}&quality=LOSSLESS"
        
        manifest_response = requests.get(manifest_url, timeout=10)
        
        if not manifest_response.ok:
            print(f"[DOWNLOAD] ERROR: Failed to get track manifest. Status: {manifest_response.status_code}", flush=True)
            return jsonify({'error': f'Failed to get track manifest. Status: {manifest_response.status_code}'}), 502

        manifest_data = manifest_response.json()
        print(f"[DOWNLOAD] Track info response keys: {manifest_data.keys()}", flush=True)
        
        # Step 3: Extract the base64-encoded manifest from the response
        if 'data' not in manifest_data:
            print(f"[DOWNLOAD] ERROR: No 'data' field in response", flush=True)
            return jsonify({'error': 'Invalid response structure - missing data field'}), 502
        
        data = manifest_data['data']
        print(f"[DOWNLOAD] Data keys: {data.keys()}", flush=True)
        
        if 'manifest' not in data:
            print(f"[DOWNLOAD] ERROR: No 'manifest' field in data", flush=True)
            return jsonify({'error': 'Invalid response structure - missing manifest field'}), 502
        
        manifest_base64 = data['manifest']
        print(f"[DOWNLOAD] Got base64 manifest (length: {len(manifest_base64)})", flush=True)
        
        # Step 4: Decode the base64 manifest to get the actual CDN URLs
        try:
            manifest_json_bytes = base64.b64decode(manifest_base64)
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
        file_ext = 'flac' if file_format == 'original' else 'mp3'
        
        # Replace placeholders in the file naming template
        file_path = file_naming.replace('{artist}', artist_name)
        file_path = file_path.replace('{album}', album_name)
        file_path = file_path.replace('{track}', track_num)
        file_path = file_path.replace('{title}', track_title)
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
        track_response = requests.get(download_url, timeout=30)
        
        if not track_response.ok:
            print(f"[DOWNLOAD] ERROR: Failed to download track. Status: {track_response.status_code}", flush=True)
            return jsonify({'error': f'Failed to download track from CDN. Status: {track_response.status_code}'}), 502
        
        print(f"[DOWNLOAD] Downloaded {len(track_response.content)} bytes", flush=True)
        
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

        temp_flac_path = os.path.join(temp_folder, f'temp_{track_id}.flac')
        temp_mp3_path = os.path.join(temp_folder, f'temp_{track_id}.mp3')
        print(f"[DOWNLOAD] Saving temporary FLAC: {temp_flac_path}", flush=True)

        with open(temp_flac_path, 'wb') as f:
            f.write(track_response.content)

        print(f"[DOWNLOAD] Adding metadata to staged FLAC...", flush=True)
        add_id3_tags_to_file(temp_flac_path, metadata_dict, cover_image_data)

        if file_format == 'mp3':
            print(f"[DOWNLOAD] Format is MP3 - converting staged FLAC", flush=True)

            success = convert_flac_to_mp3(temp_flac_path, temp_mp3_path)

            if not success:
                cleanup_file(temp_flac_path)
                cleanup_file(temp_mp3_path)
                return jsonify({'error': 'Failed to convert FLAC to MP3'}), 500

            try:
                shutil.move(temp_mp3_path, full_path)
            except Exception as e:
                print(f"[DOWNLOAD] ERROR: Failed to move MP3 to destination: {str(e)}", flush=True)
                cleanup_file(temp_flac_path)
                cleanup_file(temp_mp3_path)
                return jsonify({'error': f'Failed to move MP3 to destination: {str(e)}'}), 500

            cleanup_file(temp_flac_path)
            cleanup_file(temp_mp3_path)

            print(f"[DOWNLOAD] SUCCESS: Converted and saved MP3 to {full_path}", flush=True)
        else:
            print(f"[DOWNLOAD] Format is FLAC - moving from temp", flush=True)
            try:
                shutil.move(temp_flac_path, full_path)
            except Exception as e:
                print(f"[DOWNLOAD] ERROR: Failed to move FLAC to destination: {str(e)}", flush=True)
                cleanup_file(temp_flac_path)
                return jsonify({'error': f'Failed to move FLAC to destination: {str(e)}'}), 500

            cleanup_file(temp_flac_path)
            print(f"[DOWNLOAD] SUCCESS: Downloaded and saved to {full_path}", flush=True)
        
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
