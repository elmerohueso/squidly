"""Storage and configuration helpers backed by PostgreSQL.

This module contains helpers for storing and reading configuration and
state in the database (e.g., Plex config, download settings, library update
status).
"""

from datetime import datetime
import json

from squidly.config import DEFAULT_DOWNLOAD_SETTINGS
from squidly.db import get_db_connection


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

    is_idle = idle_seconds is None or idle_seconds >= required_idle_seconds
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


def get_ytm_config(user_id=None):
    conn = get_db_connection()
    cur = conn.cursor()

    if user_id:
        cur.execute(
            """
            SELECT ytm_headers
            FROM user_settings
            WHERE plex_client_id = %s
            """,
            (user_id,)
        )
    else:
        cur.execute(
            """
            SELECT ytm_headers
            FROM user_settings
            WHERE ytm_headers IS NOT NULL
            ORDER BY id ASC
            LIMIT 1
            """
        )

    row = cur.fetchone()
    conn.close()

    return {'has_headers': row is not None and row.get('ytm_headers') is not None}


def save_ytm_config(cookie, user_id=None):
    import hashlib
    import time
    from http.cookies import SimpleCookie

    cookie = str(cookie or '').strip()
    if not cookie:
        return

    if '__Secure-3PAPISID' not in cookie:
        raise ValueError('Cookie is missing __Secure-3PAPISID')

    c = SimpleCookie()
    c.load(cookie.replace('"', ''))
    sapisid = c['__Secure-3PAPISID'].value
    timestamp = str(int(time.time()))
    sha1 = hashlib.sha1()
    sha1.update(f'{timestamp} {sapisid} https://music.youtube.com'.encode('utf-8'))
    authorization = f'SAPISIDHASH {timestamp}_{sha1.hexdigest()}'

    headers = {
        'cookie': cookie,
        'origin': 'https://music.youtube.com',
        'authorization': authorization,
    }
    headers_json = json.dumps(headers)

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
        INSERT INTO user_settings (username, plex_client_id, ytm_headers)
        VALUES (%s, %s, %s)
        ON CONFLICT (plex_client_id) DO UPDATE SET
            ytm_headers = excluded.ytm_headers
        """,
        (None, user_id, headers_json)
    )
    conn.commit()
    conn.close()


def get_download_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT format, quality, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches,
               tag_title, tag_artist, tag_album_artist, tag_album, tag_year,
               tag_track_number, tag_track_total, tag_disc_number, tag_disc_total, tag_version,
               tag_tidal_track_id, tag_tidal_album_id, tag_isrc, tag_copyright, tag_cover_art,
               tag_explicit, tag_explicit_suffix,
               penalty_compilation, penalty_karaoke, penalty_live
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
                id, format, quality, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches,
                tag_title, tag_artist, tag_album_artist, tag_album, tag_year,
                tag_track_number, tag_track_total, tag_disc_number, tag_disc_total, tag_version,
                tag_tidal_track_id, tag_tidal_album_id, tag_isrc, tag_copyright, tag_cover_art,
                tag_explicit, tag_explicit_suffix,
                penalty_compilation, penalty_karaoke, penalty_live,
                updated_at
            )
            VALUES (1, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s)
            """,
            (
                DEFAULT_DOWNLOAD_SETTINGS['format'],
                DEFAULT_DOWNLOAD_SETTINGS['quality'],
                DEFAULT_DOWNLOAD_SETTINGS['parent_folder'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'],
                DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds'],
                DEFAULT_DOWNLOAD_SETTINGS['ignore_matches'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_title'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_artist'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_album_artist'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_album'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_year'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_track_number'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_track_total'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_disc_number'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_disc_total'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_version'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_track_id'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_album_id'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_isrc'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_copyright'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_cover_art'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_explicit'],
                DEFAULT_DOWNLOAD_SETTINGS['tag_explicit_suffix'],
                DEFAULT_DOWNLOAD_SETTINGS['penalty_compilation'],
                DEFAULT_DOWNLOAD_SETTINGS['penalty_karaoke'],
                DEFAULT_DOWNLOAD_SETTINGS['penalty_live'],
                now
            )
        )
        conn.commit()
        cur.execute(
            """
            SELECT format, quality, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches,
                   tag_title, tag_artist, tag_album_artist, tag_album, tag_year,
                   tag_track_number, tag_track_total, tag_disc_number, tag_disc_total, tag_version,
                   tag_tidal_track_id, tag_tidal_album_id, tag_isrc, tag_copyright, tag_cover_art,
                   tag_explicit, tag_explicit_suffix,
                   penalty_compilation, penalty_karaoke, penalty_live
            FROM download_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()

    file_naming_album = row['file_naming_album'] or row['file_naming'] or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']
    jobs_refresh_interval_seconds = row['jobs_refresh_interval_seconds']
    if not isinstance(jobs_refresh_interval_seconds, int) or jobs_refresh_interval_seconds < 1:
        jobs_refresh_interval_seconds = DEFAULT_DOWNLOAD_SETTINGS['jobs_refresh_interval_seconds']

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
        'quality': row.get('quality') or DEFAULT_DOWNLOAD_SETTINGS['quality'],
        'parent_folder': row['parent_folder'],
        'file_naming': file_naming_album,
        'file_naming_album': file_naming_album,
        'jobs_refresh_interval_seconds': jobs_refresh_interval_seconds,
        'ignore_matches': ignore_matches,
        'tag_title': bool(row.get('tag_title', DEFAULT_DOWNLOAD_SETTINGS['tag_title'])),
        'tag_artist': bool(row.get('tag_artist', DEFAULT_DOWNLOAD_SETTINGS['tag_artist'])),
        'tag_album_artist': bool(row.get('tag_album_artist', DEFAULT_DOWNLOAD_SETTINGS['tag_album_artist'])),
        'tag_album': bool(row.get('tag_album', DEFAULT_DOWNLOAD_SETTINGS['tag_album'])),
        'tag_year': bool(row.get('tag_year', DEFAULT_DOWNLOAD_SETTINGS['tag_year'])),
        'tag_track_number': bool(row.get('tag_track_number', DEFAULT_DOWNLOAD_SETTINGS['tag_track_number'])),
        'tag_track_total': bool(row.get('tag_track_total', DEFAULT_DOWNLOAD_SETTINGS['tag_track_total'])),
        'tag_disc_number': bool(row.get('tag_disc_number', DEFAULT_DOWNLOAD_SETTINGS['tag_disc_number'])),
        'tag_disc_total': bool(row.get('tag_disc_total', DEFAULT_DOWNLOAD_SETTINGS['tag_disc_total'])),
        'tag_version': bool(row.get('tag_version', DEFAULT_DOWNLOAD_SETTINGS['tag_version'])),
        'tag_tidal_track_id': bool(row.get('tag_tidal_track_id', DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_track_id'])),
        'tag_tidal_album_id': bool(row.get('tag_tidal_album_id', DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_album_id'])),
        'tag_isrc': bool(row.get('tag_isrc', DEFAULT_DOWNLOAD_SETTINGS['tag_isrc'])),
        'tag_copyright': bool(row.get('tag_copyright', DEFAULT_DOWNLOAD_SETTINGS['tag_copyright'])),
        'tag_cover_art': bool(row.get('tag_cover_art', DEFAULT_DOWNLOAD_SETTINGS['tag_cover_art'])),
        'tag_explicit': bool(row.get('tag_explicit', DEFAULT_DOWNLOAD_SETTINGS['tag_explicit'])),
        'tag_explicit_suffix': bool(row.get('tag_explicit_suffix', DEFAULT_DOWNLOAD_SETTINGS['tag_explicit_suffix'])),
        'penalty_compilation': bool(row.get('penalty_compilation', DEFAULT_DOWNLOAD_SETTINGS['penalty_compilation'])),
        'penalty_karaoke': bool(row.get('penalty_karaoke', DEFAULT_DOWNLOAD_SETTINGS['penalty_karaoke'])),
        'penalty_live': bool(row.get('penalty_live', DEFAULT_DOWNLOAD_SETTINGS['penalty_live'])),
    }


def save_download_settings(settings):
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO download_settings (
            id, format, quality, parent_folder, file_naming, file_naming_album, jobs_refresh_interval_seconds, ignore_matches,
            tag_title, tag_artist, tag_album_artist, tag_album, tag_year,
            tag_track_number, tag_track_total, tag_disc_number, tag_disc_total, tag_version,
            tag_tidal_track_id, tag_tidal_album_id, tag_isrc, tag_copyright, tag_cover_art,
            tag_explicit, tag_explicit_suffix,
            penalty_compilation, penalty_karaoke, penalty_live,
            updated_at
        )
        VALUES (1, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s)
        ON CONFLICT(id) DO UPDATE SET
            format = excluded.format,
            quality = excluded.quality,
            parent_folder = excluded.parent_folder,
            file_naming = excluded.file_naming,
            file_naming_album = excluded.file_naming_album,
            jobs_refresh_interval_seconds = excluded.jobs_refresh_interval_seconds,
            ignore_matches = excluded.ignore_matches,
            tag_title = excluded.tag_title,
            tag_artist = excluded.tag_artist,
            tag_album_artist = excluded.tag_album_artist,
            tag_album = excluded.tag_album,
            tag_year = excluded.tag_year,
            tag_track_number = excluded.tag_track_number,
            tag_track_total = excluded.tag_track_total,
            tag_disc_number = excluded.tag_disc_number,
            tag_disc_total = excluded.tag_disc_total,
            tag_version = excluded.tag_version,
            tag_tidal_track_id = excluded.tag_tidal_track_id,
            tag_tidal_album_id = excluded.tag_tidal_album_id,
            tag_isrc = excluded.tag_isrc,
            tag_copyright = excluded.tag_copyright,
            tag_cover_art = excluded.tag_cover_art,
            tag_explicit = excluded.tag_explicit,
            tag_explicit_suffix = excluded.tag_explicit_suffix,
            penalty_compilation = excluded.penalty_compilation,
            penalty_karaoke = excluded.penalty_karaoke,
            penalty_live = excluded.penalty_live,
            updated_at = excluded.updated_at
        """,
        (
            settings['format'],
            settings.get('quality', DEFAULT_DOWNLOAD_SETTINGS['quality']),
            settings['parent_folder'],
            settings['file_naming_album'],
            settings['file_naming_album'],
            settings['jobs_refresh_interval_seconds'],
            bool(settings.get('ignore_matches', False)),
            bool(settings.get('tag_title', DEFAULT_DOWNLOAD_SETTINGS['tag_title'])),
            bool(settings.get('tag_artist', DEFAULT_DOWNLOAD_SETTINGS['tag_artist'])),
            bool(settings.get('tag_album_artist', DEFAULT_DOWNLOAD_SETTINGS['tag_album_artist'])),
            bool(settings.get('tag_album', DEFAULT_DOWNLOAD_SETTINGS['tag_album'])),
            bool(settings.get('tag_year', DEFAULT_DOWNLOAD_SETTINGS['tag_year'])),
            bool(settings.get('tag_track_number', DEFAULT_DOWNLOAD_SETTINGS['tag_track_number'])),
            bool(settings.get('tag_track_total', DEFAULT_DOWNLOAD_SETTINGS['tag_track_total'])),
            bool(settings.get('tag_disc_number', DEFAULT_DOWNLOAD_SETTINGS['tag_disc_number'])),
            bool(settings.get('tag_disc_total', DEFAULT_DOWNLOAD_SETTINGS['tag_disc_total'])),
            bool(settings.get('tag_version', DEFAULT_DOWNLOAD_SETTINGS['tag_version'])),
            bool(settings.get('tag_tidal_track_id', DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_track_id'])),
            bool(settings.get('tag_tidal_album_id', DEFAULT_DOWNLOAD_SETTINGS['tag_tidal_album_id'])),
            bool(settings.get('tag_isrc', DEFAULT_DOWNLOAD_SETTINGS['tag_isrc'])),
            bool(settings.get('tag_copyright', DEFAULT_DOWNLOAD_SETTINGS['tag_copyright'])),
            bool(settings.get('tag_cover_art', DEFAULT_DOWNLOAD_SETTINGS['tag_cover_art'])),
            bool(settings.get('tag_explicit', DEFAULT_DOWNLOAD_SETTINGS['tag_explicit'])),
            bool(settings.get('tag_explicit_suffix', DEFAULT_DOWNLOAD_SETTINGS['tag_explicit_suffix'])),
            bool(settings.get('penalty_compilation', DEFAULT_DOWNLOAD_SETTINGS['penalty_compilation'])),
            bool(settings.get('penalty_karaoke', DEFAULT_DOWNLOAD_SETTINGS['penalty_karaoke'])),
            bool(settings.get('penalty_live', DEFAULT_DOWNLOAD_SETTINGS['penalty_live'])),
            now
        )
    )
    conn.commit()
    conn.close()


def save_plex_account_id(plex_client_id, plex_account_id):
    plex_client_id = str(plex_client_id or '').strip()
    if not plex_client_id:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE user_settings
        SET plex_account_id = %s
        WHERE plex_client_id = %s
        """,
        (plex_account_id, plex_client_id)
    )
    conn.commit()
    conn.close()


def get_all_plex_account_mappings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, plex_client_id, plex_account_id, plex_owner
        FROM user_settings
        WHERE plex_client_id IS NOT NULL
        ORDER BY plex_owner DESC, username ASC
        """
    )
    rows = cur.fetchall() or []
    conn.close()
    return rows


def get_listen_history(plex_account_id=None, limit=100, since=None):
    conn = get_db_connection()
    cur = conn.cursor()

    conditions = []
    params = []
    if plex_account_id is not None:
        conditions.append('plex_account_id = %s')
        params.append(plex_account_id)
    if since is not None:
        conditions.append('played_at >= %s')
        params.append(since)

    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
    params.append(limit)

    cur.execute(
        f"""
        SELECT id, plex_account_id, plex_username, track_library_id, hifi_id,
               title, artist, album, duration, played_at, view_offset, view_count, synced_at
        FROM listen_history
        {where_clause}
        ORDER BY played_at DESC
        LIMIT %s
        """,
        params
    )
    rows = cur.fetchall() or []
    conn.close()
    return rows


def upsert_listen_history_entries(entries, plex_account_id, plex_username):
    if not entries:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    inserted = 0
    for entry in entries:
        cur.execute(
            """
            INSERT INTO listen_history (
                plex_account_id, plex_username, track_library_id, hifi_id,
                title, artist, album, duration, played_at, view_offset, view_count
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (plex_account_id, track_library_id, played_at) DO UPDATE SET
                plex_username = excluded.plex_username,
                hifi_id = COALESCE(excluded.hifi_id, listen_history.hifi_id),
                title = excluded.title,
                artist = excluded.artist,
                album = excluded.album,
                duration = excluded.duration,
                view_offset = excluded.view_offset,
                view_count = excluded.view_count,
                synced_at = NOW()
            """,
            (
                plex_account_id,
                plex_username,
                entry.get('track_library_id'),
                entry.get('hifi_id'),
                entry.get('title', ''),
                entry.get('artist'),
                entry.get('album'),
                entry.get('duration'),
                entry.get('played_at'),
                entry.get('view_offset'),
                entry.get('view_count'),
            )
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


def get_listen_history_sync_status(plex_account_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT last_synced_at, sync_status
        FROM listen_history_sync_status
        WHERE plex_account_id = %s
        """,
        (plex_account_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return {'last_synced_at': None, 'sync_status': None}
    return {
        'last_synced_at': row['last_synced_at'],
        'sync_status': row['sync_status']
    }


def set_listen_history_sync_status(plex_account_id, last_synced_at, status=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO listen_history_sync_status (plex_account_id, last_synced_at, sync_status)
        VALUES (%s, %s, %s)
        ON CONFLICT (plex_account_id) DO UPDATE SET
            last_synced_at = excluded.last_synced_at,
            sync_status = excluded.sync_status
        """,
        (plex_account_id, last_synced_at, status)
    )
    conn.commit()
    conn.close()


def has_listen_history(plex_account_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT EXISTS(SELECT 1 FROM listen_history WHERE plex_account_id = %s)",
        (plex_account_id,)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else False


def get_recent_listen_history_seeds(plex_account_id, limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT ON (hifi_id)
            hifi_id, title, artist, album, played_at
        FROM listen_history
        WHERE plex_account_id = %s AND hifi_id IS NOT NULL
        ORDER BY hifi_id, played_at DESC
        LIMIT %s
        """,
        (plex_account_id, limit)
    )
    rows = cur.fetchall() or []
    conn.close()
    return [
        {
            'hifi_id': int(row['hifi_id']),
            'title': row['title'],
            'artist': row['artist'],
            'album': row['album'],
            'played_at': row['played_at'],
        }
        for row in rows
    ]


def get_existing_hifi_ids():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT hifi_id FROM tracks WHERE hifi_id IS NOT NULL")
    rows = cur.fetchall() or []
    conn.close()
    return {int(row['hifi_id']) for row in rows}


def save_recommendation_playlist(plex_account_id, slug, name, strategy, seed_count, tracks):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO recommendation_playlists (plex_account_id, name, slug, strategy, seed_count, track_count, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (plex_account_id, slug) DO UPDATE SET
                name = excluded.name,
                strategy = excluded.strategy,
                seed_count = excluded.seed_count,
                track_count = excluded.track_count,
                generated_at = NOW()
            RETURNING id
            """,
            (plex_account_id, name, slug, strategy, seed_count, len(tracks))
        )
        playlist_id = cur.fetchone()['id']

        cur.execute(
            "DELETE FROM recommendation_playlist_tracks WHERE playlist_id = %s",
            (playlist_id,)
        )

        for i, track in enumerate(tracks):
            cur.execute(
                """
                INSERT INTO recommendation_playlist_tracks
                    (playlist_id, position, hifi_id, title, artist, album, duration, cover, seed_hifi_id, score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    playlist_id,
                    i + 1,
                    track['hifi_id'],
                    track['title'],
                    track.get('artist'),
                    track.get('album'),
                    track.get('duration'),
                    track.get('cover'),
                    track.get('seed_hifi_id'),
                    track.get('score'),
                )
            )

        conn.commit()
        return playlist_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_recommendation_playlist(plex_account_id, slug):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, slug, strategy, seed_count, track_count, generated_at
        FROM recommendation_playlists
        WHERE plex_account_id = %s AND slug = %s
        """,
        (plex_account_id, slug)
    )
    playlist = cur.fetchone()
    if not playlist:
        conn.close()
        return None

    cur.execute(
        """
        SELECT position, hifi_id, title, artist, album, duration, cover, seed_hifi_id, score
        FROM recommendation_playlist_tracks
        WHERE playlist_id = %s
        ORDER BY position
        """,
        (playlist['id'],)
    )
    tracks = cur.fetchall() or []
    conn.close()

    return {
        'id': playlist['id'],
        'name': playlist['name'],
        'slug': playlist['slug'],
        'strategy': playlist['strategy'],
        'seed_count': playlist['seed_count'],
        'track_count': playlist['track_count'],
        'generated_at': playlist['generated_at'],
        'tracks': [
            {
                'position': t['position'],
                'hifi_id': t['hifi_id'],
                'title': t['title'],
                'artist': t['artist'],
                'album': t['album'],
                'duration': t['duration'],
                'cover': t['cover'],
                'seed_hifi_id': t['seed_hifi_id'],
                'score': t['score'],
            }
            for t in tracks
        ]
    }


def list_recommendation_playlists(plex_account_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, slug, strategy, seed_count, track_count, generated_at
        FROM recommendation_playlists
        WHERE plex_account_id = %s
        ORDER BY generated_at DESC
        """,
        (plex_account_id,)
    )
    rows = cur.fetchall() or []
    conn.close()
    return [
        {
            'id': row['id'],
            'name': row['name'],
            'slug': row['slug'],
            'strategy': row['strategy'],
            'seed_count': row['seed_count'],
            'track_count': row['track_count'],
            'generated_at': row['generated_at'],
        }
        for row in rows
    ]
