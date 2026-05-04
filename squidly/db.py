"""Database helpers for Squidly."""

import psycopg2
import psycopg2.extras

from squidly.config import DATABASE_URL


def get_db_connection():
    """Get a PostgreSQL connection that returns dictionary-like rows."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS plex_songs")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS download_settings (
            id INTEGER PRIMARY KEY,
            format TEXT NOT NULL,
            quality TEXT NOT NULL DEFAULT 'LOSSLESS',
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
    if 'quality' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN quality TEXT NOT NULL DEFAULT 'LOSSLESS'")
    if 'tag_title' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_title BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_artist' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_artist BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_album_artist' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_album_artist BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_album' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_album BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_year' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_year BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_track_number' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_track_number BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_track_total' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_track_total BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_disc_number' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_disc_number BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_disc_total' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_disc_total BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_version' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_version BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_tidal_track_id' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_tidal_track_id BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_tidal_album_id' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_tidal_album_id BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_isrc' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_isrc BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_copyright' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_copyright BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_cover_art' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_cover_art BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_explicit' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_explicit BOOLEAN NOT NULL DEFAULT TRUE")
    if 'tag_explicit_suffix' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN tag_explicit_suffix BOOLEAN NOT NULL DEFAULT TRUE")

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
    if 'ytm_headers' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN ytm_headers TEXT')

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
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_artists_hifi_id
        ON artists (hifi_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_artists_match_status
        ON artists (match_status)
        """
    )

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
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_albums_artist_id
        ON albums (artist_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_albums_hifi_id
        ON albums (hifi_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_albums_match_status
        ON albums (match_status)
        """
    )

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
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_album_id
        ON tracks (album_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_artist_id
        ON tracks (artist_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_hifi_id
        ON tracks (hifi_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tracks_match_status
        ON tracks (match_status)
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

    cur.execute(
        """
        UPDATE jobs
        SET job_type = %s
        WHERE job_type = %s
        """,
        ('plex_playlist_add', 'plex_add')
    )

    cur.execute(
        """
        UPDATE jobs
        SET result_json = regexp_replace(result_json, '"id3_tagged"', '"tagged"', 'g')
        WHERE result_json LIKE '%%id3_tagged%%'
        """
    )

    conn.commit()
    conn.close()
