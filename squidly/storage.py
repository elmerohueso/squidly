"""Storage and configuration helpers backed by PostgreSQL.

This module contains helpers for storing and reading configuration and
state in the database (e.g., Plex config, download settings, library update
status).
"""

from datetime import datetime

from squidly.config import DEFAULT_DOWNLOAD_SETTINGS
from squidly.db import get_db_connection


def init_db():
    """Create required tables and schema migrations."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Drop plex_songs table (no longer used, all data comes from tracks/albums/artists)
    cur.execute("DROP TABLE IF EXISTS plex_songs")

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
            ignore_matches BOOLEAN NOT NULL DEFAULT FALSE,
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
        CREATE TABLE IF NOT EXISTS user_settings (
            id SERIAL PRIMARY KEY,
            username TEXT,
            plex_client_id TEXT UNIQUE,
            plex_owner BOOLEAN NOT NULL DEFAULT FALSE,
            listenbrainz_key TEXT,
            listenbrainz_username TEXT
        )
        """
    )
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings'
        """
    )
    user_settings_columns = {row['column_name'] for row in cur.fetchall()}
    if 'plex_owner' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN plex_owner BOOLEAN NOT NULL DEFAULT FALSE')
        user_settings_columns.add('plex_owner')
    if 'listenbrainz_key' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN listenbrainz_key TEXT')
    if 'listenbrainz_username' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN listenbrainz_username TEXT')

    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = 'listenbrainz_config'
              AND table_schema = 'public'
        )
        """
    )
    table_exists_row = cur.fetchone()
    if table_exists_row and table_exists_row.get('exists'):
        cur.execute('SELECT user_token FROM listenbrainz_config WHERE id = 1')
        lb_row = cur.fetchone()
        if lb_row and lb_row.get('user_token'):
            token = lb_row['user_token']
            cur.execute(
                """
                SELECT plex_client_id
                FROM user_settings
                WHERE plex_owner = TRUE
                ORDER BY id ASC
                LIMIT 1
                """
            )
            owner_row = cur.fetchone()
            target_client_id = owner_row['plex_client_id'] if owner_row and owner_row.get('plex_client_id') else None
            if not target_client_id:
                cur.execute(
                    """
                    SELECT plex_client_id
                    FROM user_settings
                    ORDER BY id ASC
                    LIMIT 1
                    """
                )
                default_row = cur.fetchone()
                target_client_id = default_row['plex_client_id'] if default_row and default_row.get('plex_client_id') else None
            if target_client_id:
                cur.execute(
                    """
                    UPDATE user_settings
                    SET listenbrainz_key = %s
                    WHERE plex_client_id = %s
                    """,
                    (token, target_client_id)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO user_settings (username, plex_client_id, listenbrainz_key)
                    VALUES (%s, %s, %s)
                    """,
                    ('listenbrainz', 'listenbrainz_default', token)
                )
        cur.execute('DROP TABLE IF EXISTS listenbrainz_config')
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
        CREATE TABLE IF NOT EXISTS artists (
            artist_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            library_id TEXT UNIQUE,
            hifi_id TEXT,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            match_status TEXT NOT NULL DEFAULT 'unmatched',
            match_source TEXT,
            matched_at TIMESTAMP,
            confirmed_at TIMESTAMP,
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT artists_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
            CONSTRAINT artists_match_status_check CHECK (match_status IN ('unmatched', 'proposed', 'confirmed', 'rejected')),
            CONSTRAINT artists_match_source_check CHECK (match_source IS NULL OR match_source IN ('path', 'tags', 'auto_artist', 'auto_album', 'auto_track', 'manual'))
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_artists_hifi_id ON artists (hifi_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_artists_match_status ON artists (match_status)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS albums (
            album_id SERIAL PRIMARY KEY,
            artist_id INTEGER REFERENCES artists(artist_id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            library_id TEXT UNIQUE,
            hifi_id TEXT,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            complete BOOLEAN NOT NULL DEFAULT FALSE,
            matched_track_count INTEGER NOT NULL DEFAULT 0,
            expected_track_count INTEGER NOT NULL DEFAULT 0,
            match_status TEXT NOT NULL DEFAULT 'unmatched',
            match_source TEXT,
            matched_at TIMESTAMP,
            confirmed_at TIMESTAMP,
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT albums_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
            CONSTRAINT albums_match_status_check CHECK (match_status IN ('unmatched', 'proposed', 'confirmed', 'rejected')),
            CONSTRAINT albums_match_source_check CHECK (match_source IS NULL OR match_source IN ('path', 'tags', 'auto_artist', 'auto_album', 'auto_track', 'manual'))
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums (artist_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_albums_hifi_id ON albums (hifi_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_albums_match_status ON albums (match_status)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            track_id SERIAL PRIMARY KEY,
            album_id INTEGER REFERENCES albums(album_id) ON DELETE SET NULL,
            artist_id INTEGER REFERENCES artists(artist_id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            library_id TEXT UNIQUE,
            confidence NUMERIC(4,3) NOT NULL DEFAULT 0,
            hifi_id TEXT,
            path TEXT NOT NULL UNIQUE,
            format TEXT,
            bitrate INTEGER,
            disc_number INTEGER,
            track_number INTEGER,
            match_status TEXT NOT NULL DEFAULT 'unmatched',
            match_source TEXT,
            matched_at TIMESTAMP,
            confirmed_at TIMESTAMP,
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT tracks_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
            CONSTRAINT tracks_match_status_check CHECK (match_status IN ('unmatched', 'proposed', 'confirmed', 'rejected')),
            CONSTRAINT tracks_match_source_check CHECK (match_source IS NULL OR match_source IN ('path', 'tags', 'auto_artist', 'auto_album', 'auto_track', 'manual'))
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks (album_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON tracks (artist_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tracks_hifi_id ON tracks (hifi_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tracks_match_status ON tracks (match_status)")

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

    # Backfill old job type name
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


def get_plex_user_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, plex_client_id, plex_owner, listenbrainz_key
        FROM user_settings
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall() or []
    conn.close()
    return rows


def save_plex_user_setting(username, plex_client_id, plex_owner=False):
    username = str(username or '').strip()
    plex_client_id = str(plex_client_id or '').strip()
    plex_owner = bool(plex_owner)
    if not plex_client_id or not username:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_settings (username, plex_client_id, plex_owner)
        VALUES (%s, %s, %s)
        ON CONFLICT (plex_client_id) DO UPDATE SET
            username = excluded.username,
            plex_owner = excluded.plex_owner
        """,
        (username, plex_client_id, plex_owner)
    )
    conn.commit()
    conn.close()


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


def clear_plex_config():
    """Remove stored Plex configuration (credentials and library selection)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('TRUNCATE TABLE plex_config')
    conn.commit()
    conn.close()


def clear_plex_user_settings():
    """Remove saved Plex user settings."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('TRUNCATE TABLE user_settings')
    conn.commit()
    conn.close()


def get_listenbrainz_config(user_id=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if user_id:
        cur.execute(
            """
            SELECT listenbrainz_key, listenbrainz_username
            FROM user_settings
            WHERE plex_client_id = %s
            """,
            (user_id,)
        )
    else:
        cur.execute(
            """
            SELECT listenbrainz_key, listenbrainz_username
            FROM user_settings
            WHERE listenbrainz_key IS NOT NULL
            ORDER BY id ASC
            LIMIT 1
            """
        )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return {'user_token': None, 'username': None}

    return {
        'user_token': row['listenbrainz_key'],
        'username': row.get('listenbrainz_username')
    }


def save_listenbrainz_config(user_token, user_id=None, listenbrainz_username=None):
    user_token = str(user_token or '').strip()
    listenbrainz_username = str(listenbrainz_username or '').strip()
    if not user_token:
        return

    user_id = str(user_id or '').strip()
    conn = get_db_connection()
    cur = conn.cursor()

    if not user_id:
        cur.execute(
            """
            SELECT plex_client_id
            FROM user_settings
            ORDER BY id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        user_id = row['plex_client_id'] if row and row.get('plex_client_id') else None

    if not user_id:
        conn.close()
        return

    cur.execute(
        """
        INSERT INTO user_settings (username, plex_client_id, listenbrainz_key, listenbrainz_username)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (plex_client_id) DO UPDATE SET
            listenbrainz_key = excluded.listenbrainz_key,
            listenbrainz_username = excluded.listenbrainz_username
        """,
        (None, user_id, user_token, listenbrainz_username)
    )
    conn.commit()
    conn.close()


def get_download_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT format, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches
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
                id, format, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches, updated_at
            )
            VALUES (1, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                DEFAULT_DOWNLOAD_SETTINGS['format'],
                DEFAULT_DOWNLOAD_SETTINGS['parent_folder'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds'],
                DEFAULT_DOWNLOAD_SETTINGS['ignore_matches'],
                now
            )
        )
        conn.commit()
        cur.execute(
            """
            SELECT format, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches
            FROM download_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()

    file_naming_album = row['file_naming_album'] or row['file_naming']
    jobs_refresh_interval_seconds = row['jobs_refresh_interval_seconds']
    if not isinstance(jobs_refresh_interval_seconds, int) or jobs_refresh_interval_seconds < 1:
        jobs_refresh_interval_seconds = None
    
    ignore_matches = bool(row['ignore_matches'])

    if row['file_naming_album'] is None or row['jobs_refresh_interval_seconds'] is None:
        now = datetime.utcnow().isoformat() + 'Z'
        cur.execute(
            """
            UPDATE download_settings
            SET file_naming_album = %s, jobs_refresh_interval_seconds = %s, updated_at = %s
            WHERE id = 1
            """,
            (
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
        'file_naming': file_naming_album,
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
            id, format, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches, updated_at
        )
        VALUES (1, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            format = excluded.format,
            parent_folder = excluded.parent_folder,
            file_naming = excluded.file_naming,
            file_naming_album = excluded.file_naming_album,
            jobs_refresh_interval_seconds = excluded.jobs_refresh_interval_seconds,
            ignore_matches = excluded.ignore_matches,
            updated_at = excluded.updated_at
        """,
        (
            settings['format'],
            settings['parent_folder'],
            settings['file_naming_album'],
            settings['file_naming_album'],
            settings['jobs_refresh_interval_seconds'],
            bool(settings.get('ignore_matches', False)),
            now
        )
    )
    conn.commit()
    conn.close()
