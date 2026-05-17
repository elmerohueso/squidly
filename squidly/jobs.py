"""Job queue and worker logic for Squidly."""

import json
import logging
import os
import time
import threading
from datetime import datetime, timedelta

from squidly.config import (
    DEFAULT_DOWNLOAD_SETTINGS,
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
from squidly.storage import (
    normalize_db_timestamp,
    set_last_download_activity_at,
    set_library_update_needed,
    set_last_job_finished_at,
    get_plex_config,
)

logger = logging.getLogger(__name__)


def serialize_job_payload(payload):
    try:
        return json.dumps(payload, separators=(',', ':'), sort_keys=True)
    except (TypeError, ValueError):
        return json.dumps(payload, default=str, separators=(',', ':'), sort_keys=True)


def enqueue_job(job_type, payload, status='queued', priority=0, run_after=None, max_attempts=20):
    import logging
    logger = logging.getLogger(__name__)

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

    track_id = payload.get('trackId') if isinstance(payload, dict) else None
    logger.info("[JOB_ENQUEUE] job_id=%s type=%s track_id=%s", job_id, job_type, track_id)
    return job_id


def queue_pending_playlist_addition(file_path, playlist_name, parent_job_id=None, plex_user_id=None):
    """Insert a row into pending_playlist_adds table. Idempotent via unique index.

    If a duplicate is detected (ON CONFLICT), marks the parent download job's
    playlist_added stage as 'done' since the track is already queued for bulk add.
    """
    import logging
    logger = logging.getLogger(__name__)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO pending_playlist_adds (parent_job_id, file_path, playlist_name, plex_user_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        (parent_job_id, file_path, playlist_name, plex_user_id)
    )

    affected = cur.rowcount
    conn.commit()

    if affected == 0:
        logger.info(
            "[PLAYLIST_QUEUE] Duplicate skipped for file_path=%s playlist=%s (parent_job_id=%s) — already queued",
            file_path, playlist_name, parent_job_id
        )
        if parent_job_id:
            try:
                cur.execute(
                    """
                    SELECT result_json FROM jobs WHERE id = %s AND job_type = 'download_track'
                    """,
                    (parent_job_id,),
                )
                row = cur.fetchone()
                if row and row.get('result_json'):
                    result = json.loads(row['result_json'])
                    if isinstance(result, dict):
                        stages = result.get('stages', {})
                        if isinstance(stages, dict) and stages.get('playlist_added') == 'queued':
                            stages['playlist_added'] = 'done'
                            result['stages'] = stages
                            cur.execute(
                                """
                                UPDATE jobs SET result_json = %s, updated_at = NOW()
                                WHERE id = %s AND status <> 'cancelled'
                                """,
                                (json.dumps(result, separators=(',', ':'), sort_keys=True), parent_job_id),
                            )
                            conn.commit()
                            logger.info("[PLAYLIST_QUEUE] Marked parent job %s playlist_added as done (was duplicate)", parent_job_id)
            except Exception as e:
                logger.info("[PLAYLIST_QUEUE] Failed to update parent job %s for duplicate: %s", parent_job_id, str(e))
    else:
        logger.info(
            "[PLAYLIST_QUEUE] Queued playlist add for file_path=%s playlist=%s (parent_job_id=%s)",
            file_path, playlist_name, parent_job_id
        )

    conn.close()


def count_pending_playlist_adds():
    """Return the number of pending playlist additions."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM pending_playlist_adds")
    row = cur.fetchone() or {}
    count = row.get('count', 0)
    conn.close()
    return count


def get_pending_playlist_adds():
    """Return all rows from pending_playlist_adds, ordered for processing."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, parent_job_id, file_path, playlist_name, plex_user_id
        FROM pending_playlist_adds
        ORDER BY playlist_name, COALESCE(plex_user_id, ''), id
        """
    )
    rows = cur.fetchall() or []
    conn.close()
    return rows


def delete_pending_playlist_adds(ids):
    """Delete successfully processed rows from pending_playlist_adds."""
    if not ids:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(ids))
    cur.execute(
        f"DELETE FROM pending_playlist_adds WHERE id IN ({placeholders})",
        tuple(ids)
    )
    conn.commit()
    conn.close()


def queue_bulk_playlist_add_job(trigger='post_library_sync'):
    """Queue a single bulk_playlist_add job if one is not already queued/in progress."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count FROM jobs
        WHERE job_type = 'bulk_playlist_add'
          AND status IN ('queued', 'in_progress')
        """
    )
    row = cur.fetchone() or {}
    existing = row.get('count', 0) > 0
    conn.close()

    if existing:
        logger.info("[BULK_PLAYLIST_QUEUE] bulk_playlist_add already queued/in progress; not queueing another")
        return None

    pending_count = count_pending_playlist_adds()
    if pending_count == 0:
        logger.info("[BULK_PLAYLIST_QUEUE] No pending playlist adds; not queueing bulk job")
        return None

    payload = {
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    job_id = enqueue_job('bulk_playlist_add', payload, max_attempts=5)
    logger.info("[BULK_PLAYLIST_QUEUE] Queued bulk playlist add job %s (%d pending tracks, trigger=%s)", job_id, pending_count, trigger)
    return job_id


def compute_job_backoff_seconds(attempt_count):
    base = 30
    delay = base * (2 ** max(0, attempt_count - 1))
    return min(delay, 3600)


class ManifestDownloadError(Exception):
    pass


class TransientDownloadError(Exception):
    pass


class PermanentDownloadError(Exception):
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
    job_id = enqueue_job('plex_library_sync', payload, max_attempts=5)
    logger.info("[PLEX_QUEUE] Queued plex_library_sync job %s (trigger=%s)", job_id, trigger)
    return job_id


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


def is_job_cancelled(job_id):
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
    row = cur.fetchone() or {}
    conn.close()
    return str(row.get('status') or '').strip() == 'cancelled'


def mark_job_succeeded(job_id, result):
    now = datetime.utcnow().isoformat() + 'Z'
    result_json = serialize_job_payload(result) if result is not None else None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT job_type
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    type_row = cur.fetchone()

    # Ensure job row is marked finished and unlocked
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
          AND status <> 'cancelled'
        """,
        (result_json, now, now, job_id)
    )
    transitioned = (cur.rowcount or 0) > 0

    conn.commit()
    conn.close()

    if transitioned and type_row and type_row.get('job_type') == 'download_track':
        # Set library_update_needed True and update last_job_finished_at
        set_library_update_needed(True)
        set_last_job_finished_at(datetime.utcnow())


def _finalize_job_stages(result_json, final_stage_status):
    """Mark all incomplete stages as final_stage_status ('failed' or 'cancelled')."""
    try:
        result = json.loads(result_json) if result_json else {}
    except (TypeError, ValueError):
        result = {}
    
    stages = result.get('stages', {}) if isinstance(result.get('stages'), dict) else {}
    if not stages:
        return result_json
    
    for stage_name, stage_status in stages.items():
        if stage_status in ('pending', 'in_progress'):
            stages[stage_name] = final_stage_status
    
    result['stages'] = stages
    return serialize_job_payload(result)


def mark_job_failed(job_id, attempt_count, max_attempts, error_message):
    now = datetime.utcnow()
    now_iso = now.isoformat() + 'Z'
    new_attempt_count = (int(attempt_count or 0) + 1)

    if new_attempt_count < int(max_attempts or 0):
        run_after = (now + timedelta(seconds=compute_job_backoff_seconds(new_attempt_count))).isoformat() + 'Z'
        finished_at = None
    else:
        run_after = None
        finished_at = now_iso

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch current result_json to finalize stages
    cur.execute(
        """
        SELECT result_json
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone() or {}
    finalized_result_json = _finalize_job_stages(row.get('result_json'), 'failed')
    
    cur.execute(
        """
        UPDATE jobs
        SET status = 'failed',
            attempt_count = %s,
            error_message = COALESCE(%s, error_message),
            result_json = %s,
            updated_at = %s,
            run_after = %s,
            finished_at = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
                    AND status <> 'cancelled'
        """,
        (new_attempt_count, error_message, finalized_result_json, now_iso, run_after, finished_at, job_id)
    )
    conn.commit()
    conn.close()


def mark_job_retrying(job_id, attempt_count, error_message):
    now = datetime.utcnow()
    now_iso = now.isoformat() + 'Z'
    new_attempt_count = (int(attempt_count or 0) + 1)
    run_after = (now + timedelta(seconds=compute_job_backoff_seconds(new_attempt_count))).isoformat() + 'Z'

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE jobs
        SET status = 'queued',
            attempt_count = %s,
            error_message = COALESCE(%s, error_message),
            updated_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL,
            finished_at = NULL
        WHERE id = %s
        """,
        (new_attempt_count, error_message, now_iso, run_after, job_id)
    )
    conn.commit()
    conn.close()


def mark_job_cancelled(job_id):
    """Mark a job as cancelled and finalize its stages."""
    now_iso = datetime.utcnow().isoformat() + 'Z'
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Fetch current result_json to finalize stages
    cur.execute(
        """
        SELECT result_json
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone() or {}
    finalized_result_json = _finalize_job_stages(row.get('result_json'), 'cancelled')
    
    cur.execute(
        """
        UPDATE jobs
        SET status = 'cancelled',
            result_json = %s,
            updated_at = %s,
            finished_at = %s,
            locked_at = NULL,
            locked_by = NULL
        WHERE id = %s
        """,
        (finalized_result_json, now_iso, now_iso, job_id)
    )
    conn.commit()
    conn.close()



def _download_track_all_stages_done(stages):
    if not isinstance(stages, dict):
        return False

    required_stages = (
        'downloaded',
        'tagged',
        'written'
    )
    if not all(stages.get(stage_name) == 'done' for stage_name in required_stages):
        return False

    if stages.get('converted') not in ('done', 'skipped'):
        return False

    return True


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


def recover_stale_in_progress_jobs():
    now = datetime.utcnow()
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

    for row in rows:
        job_id = row.get('id')
        job_type = str(row.get('job_type') or '').strip()

        lock_time = normalize_db_timestamp(row.get('locked_at'))
        started_at = normalize_db_timestamp(row.get('started_at'))
        updated_at = normalize_db_timestamp(row.get('updated_at'))

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
            (
                'Recovered stale in_progress job on startup',
                now_iso,
                now_iso,
                job_id
            )
        )
        recovered += 1

    conn.commit()
    conn.close()

    logger.info(
        "[JOB_RECOVERY] recovered=%d exhausted=%d",
        recovered,
        exhausted,
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
          AND status <> 'cancelled'
        """,
        (result_json, now, job_id)
    )
    conn.commit()
    conn.close()


def any_plex_listen_history_sync_jobs_running_or_queued():
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
    return (row.get('count') or 0) > 0


def queue_plex_listen_history_sync(trigger='scheduled'):
    if any_plex_listen_history_sync_jobs_running_or_queued():
        return None

    payload = {
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    job_id = enqueue_job('plex_listen_history_sync', payload, max_attempts=5)
    logger.info("[LISTEN_HISTORY_QUEUE] Queued plex_listen_history_sync job %s (trigger=%s)", job_id, trigger)
    return job_id


def queue_recommendation_generation(slug, plex_account_id, plex_username, trigger='scheduled'):
    payload = {
        'slug': slug,
        'plex_account_id': plex_account_id,
        'plex_username': plex_username,
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('generate_recommendations', payload, max_attempts=3)
