"""Job queue and worker logic for Squidly."""

import json
import os
import time
import threading
from datetime import datetime, timedelta

from squidly.config import (
    DEFAULT_DOWNLOAD_SETTINGS,
    DOWNLOADS_FULL_ALBUMS_FOLDER,
    DOWNLOADS_LOOSE_TRACKS_FOLDER,
    DOWNLOADS_ROOT,
    WORKER_ID,
)
from squidly.db import get_db_connection
from squidly.downloads import (
    clean_path_components,
    convert_to_mp3,
    detect_audio_format,
    download_cover_image,
    format_tidal_image_url,
    make_request_with_retry,
    make_request_with_retry_rotating_mirrors,
    sanitize_filename_component,
    extract_year_from_text,
)
from squidly.plex import add_tracks_to_plex_playlist
from squidly.storage import (
    normalize_db_timestamp,
    set_last_download_activity_at,
    set_library_update_needed,
    set_last_job_finished_at,
    get_plex_config,
)


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


def queue_pending_playlist_addition(artist, album, title, file_path, playlist_name, parent_job_id=None, plex_user_id=None):
    """Add a track to the pending playlist additions queue."""
    payload = {
        'artist': artist,
        'album': album,
        'title': title,
        'file_path': file_path,
        'playlist_name': playlist_name,
        'parent_job_id': parent_job_id,
        'plex_user_id': plex_user_id
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
        ('plex_playlist_add', payload_json)
    )
    existing = cur.fetchone()

    if existing:
        print(f"[PLEX_QUEUE] Track already in queue: {artist} - {title}", flush=True)
        conn.close()
        return
    conn.close()
    job_id = enqueue_job('plex_playlist_add', payload)
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

    if playlist_stage_status == 'done' and _download_track_all_stages_done(stages):
        now = datetime.utcnow().isoformat() + 'Z'
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE jobs
            SET status = 'succeeded',
                error_message = NULL,
                updated_at = %s,
                finished_at = %s,
                locked_at = NULL,
                locked_by = NULL
            WHERE id = %s
              AND job_type = 'download_track'
              AND status <> 'cancelled'
            """,
            (now, now, parent_job_id)
        )
        transitioned = (cur.rowcount or 0) > 0
        conn.commit()
        conn.close()

        if transitioned:
            set_library_update_needed(True)
            set_last_job_finished_at(datetime.utcnow())

    if playlist_stage_status == 'failed':
        now = datetime.utcnow().isoformat() + 'Z'
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE jobs
            SET status = 'failed',
                error_message = COALESCE(error_message, %s),
                updated_at = %s,
                finished_at = %s,
                locked_at = NULL,
                locked_by = NULL
            WHERE id = %s
              AND job_type = 'download_track'
              AND status <> 'cancelled'
            """,
            ('playlist_added stage failed', now, now, parent_job_id)
        )
        conn.commit()
        conn.close()


def backfill_plex_playlist_add_parent_links():
    """One-time repair for legacy plex_playlist_add jobs missing parent_job_id in payload."""
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
        ('plex_playlist_add',)
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
            (serialize_job_payload(payload), now, addition['id'], 'plex_playlist_add')
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
        ('plex_playlist_add', now)
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
        (now, now, error_message, addition_id, 'plex_playlist_add')
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
        (now, now, addition_id, 'plex_playlist_add')
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


def queue_plex_library_sync(trigger='manual'):
    if any_plex_sync_jobs_running_or_queued():
        return None

    payload = {
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('plex_library_sync', payload, max_attempts=5)


def start_plex_sync_job(trigger='manual'):
    """Queue a Plex library sync job if one is not already queued/in progress."""
    config = get_plex_config()
    if not config.get('server_url') or not config.get('api_token') or not config.get('library_name'):
        return {'ok': False, 'status_code': 400, 'error': 'Plex is not fully configured'}

    job_id = queue_plex_library_sync(trigger=trigger)
    if job_id is None:
        return {'ok': False, 'status_code': 409, 'error': 'A Plex sync job is already queued or in progress'}

    return {'ok': True, 'status_code': 202, 'job_id': job_id, 'status': 'queued'}


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
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'in_progress',
            updated_at = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
        """,
        (now, job_id)
    )
    conn.commit()
    conn.close()


def requeue_claimed_job(job_id, delay_seconds=30, error_message=None):
    now = datetime.utcnow()
    now_iso = now.isoformat() + 'Z'
    run_after = (now + timedelta(seconds=max(1, int(delay_seconds)))).isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'queued',
            updated_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL,
            error_message = COALESCE(%s, error_message)
        WHERE id = %s
        """,
        (now_iso, run_after, error_message, job_id)
    )
    conn.commit()
    conn.close()


def recover_stale_in_progress_jobs(stale_after_minutes=15):
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(minutes=max(1, int(stale_after_minutes)))
    now_iso = now.isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, job_type, attempt_count, max_attempts, result_json, locked_at, started_at, updated_at
        FROM jobs
        WHERE status = 'in_progress'
        """
    )
    rows = cur.fetchall() or []

    recovered = 0
    exhausted = 0
    skipped_waiting_playlist = 0

    for row in rows:
        job_id = row.get('id')
        job_type = str(row.get('job_type') or '').strip()

        # download_track jobs can intentionally stay in_progress while waiting on queued playlist_add.
        if job_type == 'download_track':
            try:
                result = json.loads(row.get('result_json')) if row.get('result_json') else {}
            except (TypeError, ValueError):
                result = {}
            stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}
            if stages.get('playlist_added') == 'queued':
                skipped_waiting_playlist += 1
                continue

        lock_time = normalize_db_timestamp(row.get('locked_at'))
        started_at = normalize_db_timestamp(row.get('started_at'))
        updated_at = normalize_db_timestamp(row.get('updated_at'))
        reference_ts = lock_time or started_at or updated_at

        if reference_ts and reference_ts > stale_cutoff:
            continue

        attempt_count = int(row.get('attempt_count') or 0)
        max_attempts = int(row.get('max_attempts') or 0)

        if attempt_count >= max_attempts:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    error_message = COALESCE(error_message, %s),
                    updated_at = %s,
                    finished_at = %s,
                    locked_at = NULL,
                    locked_by = NULL
                WHERE id = %s
                """,
                ('Recovered stale in_progress job reached max attempts', now_iso, now_iso, job_id)
            )
            exhausted += 1
            continue

        cur.execute(
            """
            UPDATE jobs
            SET status = 'queued',
                error_message = COALESCE(error_message, %s),
                updated_at = %s,
                run_after = %s,
                locked_at = NULL,
                locked_by = NULL
            WHERE id = %s
            """,
            ('Recovered stale in_progress job on startup', now_iso, now_iso, job_id)
        )
        recovered += 1

    conn.commit()
    conn.close()

    print(
        (
            f"[JOB_RECOVERY] stale_cutoff_minutes={max(1, int(stale_after_minutes))} "
            f"recovered={recovered} exhausted={exhausted} "
            f"skipped_waiting_playlist={skipped_waiting_playlist}"
        ),
        flush=True
    )


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
