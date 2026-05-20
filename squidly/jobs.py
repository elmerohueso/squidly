"""Job queue infrastructure for Squidly — state transitions, claiming, recovery, and progress tracking."""

import json
import logging
from datetime import datetime, timedelta

from squidly.config import WORKER_ID
from squidly.db import get_db_connection
from squidly.storage import (
    normalize_db_timestamp,
    set_library_update_needed,
    set_last_job_finished_at,
)

logger = logging.getLogger(__name__)


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

    track_id = payload.get('trackId') if isinstance(payload, dict) else None
    logger.info("[JOB_ENQUEUE] job_id=%s type=%s track_id=%s", job_id, job_type, track_id)
    return job_id


def compute_job_backoff_seconds(attempt_count):
    base = 30
    delay = base * (2 ** max(0, attempt_count - 1))
    return min(delay, 3600)


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