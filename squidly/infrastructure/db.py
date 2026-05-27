"""Database helpers for Squidly."""

import psycopg2
import psycopg2.extras

from squidly.infrastructure.config import DATABASE_URL


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
    if 'penalty_compilation' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN penalty_compilation BOOLEAN NOT NULL DEFAULT TRUE")
    if 'penalty_single' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN penalty_single BOOLEAN NOT NULL DEFAULT TRUE")
    if 'penalty_karaoke' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN penalty_karaoke BOOLEAN NOT NULL DEFAULT TRUE")
    if 'penalty_live' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN penalty_live BOOLEAN NOT NULL DEFAULT TRUE")
    if 'download_source' not in columns:
        cur.execute("ALTER TABLE download_settings ADD COLUMN download_source TEXT NOT NULL DEFAULT 'tidal'")

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
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'mirror_endpoints'
        """
    )
    mirror_columns = {row['column_name'] for row in cur.fetchall()}
    if 'enabled' not in mirror_columns:
        cur.execute("ALTER TABLE mirror_endpoints ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
    if 'mirror_type' not in mirror_columns:
        cur.execute("ALTER TABLE mirror_endpoints ADD COLUMN mirror_type TEXT NOT NULL DEFAULT 'tidal'")
    if 'downloads_enabled' not in mirror_columns:
        cur.execute("ALTER TABLE mirror_endpoints ADD COLUMN downloads_enabled INTEGER NOT NULL DEFAULT 1")
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
    if 'plex_account_id' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN plex_account_id INTEGER')
    if 'auto_download_fresh_finds' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN auto_download_fresh_finds BOOLEAN NOT NULL DEFAULT FALSE')
    if 'fresh_finds_retention_days' not in user_settings_columns:
        cur.execute('ALTER TABLE user_settings ADD COLUMN fresh_finds_retention_days INTEGER')

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
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT artists_confidence_check CHECK (confidence >= 0 AND confidence <= 1)
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
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT albums_confidence_check CHECK (confidence >= 0 AND confidence <= 1)
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
            last_seen_at TIMESTAMP NOT NULL,
            CONSTRAINT tracks_confidence_check CHECK (confidence >= 0 AND confidence <= 1)
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
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'tracks' AND column_name = 'isrc'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE tracks ADD COLUMN isrc TEXT")

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'tracks' AND column_name = 'duration'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE tracks ADD COLUMN duration INTEGER")

    for table in ('artists', 'albums', 'tracks'):
        for col in ('match_status', 'match_source', 'matched_at', 'confirmed_at'):
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                (table, col)
            )
            if cur.fetchone():
                cur.execute(f"ALTER TABLE {table} DROP COLUMN {col}")

    for table, col in [('artists', 'match_status'), ('albums', 'match_status'), ('tracks', 'match_status')]:
        cur.execute(
            """
            SELECT conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = %s AND c.conname LIKE %s
            """,
            (table, f'%{col}%')
        )
        for row in cur.fetchall():
            cur.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {row['conname']}")

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

    cur.execute('SELECT id FROM library_update_status WHERE id = 1')
    if not cur.fetchone():
        cur.execute('INSERT INTO library_update_status (id, library_update_needed) VALUES (1, FALSE)')

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS listen_history (
            id SERIAL PRIMARY KEY,
            plex_account_id INTEGER NOT NULL,
            plex_username TEXT,
            track_library_id TEXT,
            hifi_id TEXT,
            title TEXT NOT NULL,
            artist TEXT,
            album TEXT,
            duration INTEGER,
            played_at TIMESTAMP NOT NULL,
            view_offset INTEGER,
            view_count INTEGER,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (plex_account_id, track_library_id, played_at)
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_listen_history_account
        ON listen_history (plex_account_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_listen_history_played_at
        ON listen_history (played_at DESC)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_listen_history_hifi_id
        ON listen_history (hifi_id)
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS listen_history_sync_status (
            plex_account_id INTEGER PRIMARY KEY,
            last_synced_at TIMESTAMP,
            sync_status TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_playlists (
            id SERIAL PRIMARY KEY,
            plex_account_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            strategy TEXT NOT NULL,
            seed_count INTEGER NOT NULL,
            track_count INTEGER NOT NULL,
            generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (plex_account_id, slug)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_playlist_tracks (
            id SERIAL PRIMARY KEY,
            playlist_id INTEGER REFERENCES recommendation_playlists(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            hifi_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            artist TEXT,
            album TEXT,
            duration INTEGER,
            cover TEXT,
            seed_hifi_id INTEGER,
            score FLOAT
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rec_playlist_tracks_playlist_id
        ON recommendation_playlist_tracks (playlist_id)
        """
    )

    # Migration: add playlist_date for history retention
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlists' AND column_name = 'playlist_date'
        """
    )
    if not cur.fetchone():
        cur.execute(
            "ALTER TABLE recommendation_playlists DROP CONSTRAINT IF EXISTS recommendation_playlists_plex_account_id_slug_key"
        )
        cur.execute("ALTER TABLE recommendation_playlists ADD COLUMN playlist_date DATE")
        cur.execute("UPDATE recommendation_playlists SET playlist_date = DATE(generated_at) WHERE playlist_date IS NULL")
        cur.execute("ALTER TABLE recommendation_playlists ALTER COLUMN playlist_date SET NOT NULL")
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_rec_playlists_unique ON recommendation_playlists (plex_account_id, slug, playlist_date)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_rec_playlists_history ON recommendation_playlists (plex_account_id, generated_at DESC)"
        )

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlist_tracks' AND column_name = 'quality'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE recommendation_playlist_tracks ADD COLUMN quality TEXT")

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlist_tracks' AND column_name = 'artist_id'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE recommendation_playlist_tracks ADD COLUMN artist_id INTEGER")

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlist_tracks' AND column_name = 'album_id'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE recommendation_playlist_tracks ADD COLUMN album_id INTEGER")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_playlist_adds (
            id SERIAL PRIMARY KEY,
            parent_job_id INTEGER,
            file_path TEXT NOT NULL,
            playlist_name TEXT NOT NULL,
            plex_user_id TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_playlist_unique
        ON pending_playlist_adds (file_path, playlist_name, COALESCE(plex_user_id, ''))
        """
    )

    # Migration: replace fresh_finds_retention_days with fresh_finds_retention_count
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings' AND column_name = 'fresh_finds_retention_days'
        """
    )
    if cur.fetchone():
        cur.execute("ALTER TABLE user_settings DROP COLUMN fresh_finds_retention_days")

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings' AND column_name = 'fresh_finds_retention_count'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN fresh_finds_retention_count INTEGER NOT NULL DEFAULT 10")

    # Migration: add fresh_finds_new_track_pct to user_settings
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings' AND column_name = 'fresh_finds_new_track_pct'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN fresh_finds_new_track_pct INTEGER NOT NULL DEFAULT 50")

    # Migration: add fresh_finds_track_count to user_settings
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings' AND column_name = 'fresh_finds_track_count'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN fresh_finds_track_count INTEGER NOT NULL DEFAULT 25")

    # Migration: add fresh_finds_history_days to user_settings
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_settings' AND column_name = 'fresh_finds_history_days'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE user_settings ADD COLUMN fresh_finds_history_days INTEGER NOT NULL DEFAULT 30")

    # Migration: add library_id to recommendation_playlist_tracks
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlist_tracks' AND column_name = 'library_id'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE recommendation_playlist_tracks ADD COLUMN library_id TEXT")

    # Migration: add plex_playlist_key to recommendation_playlists
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'recommendation_playlists' AND column_name = 'plex_playlist_key'
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE recommendation_playlists ADD COLUMN plex_playlist_key TEXT")

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rec_playlists_plex_key
        ON recommendation_playlists (plex_account_id, plex_playlist_key)
        WHERE plex_playlist_key IS NOT NULL
        """
    )

    conn.commit()
    conn.close()
