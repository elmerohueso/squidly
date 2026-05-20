"""Job orchestration: type registry, chaining rules, dedup guards, schedulers, and playlist side-channel."""

import json
import logging
import time
from datetime import datetime

from squidly.db import get_db_connection
from squidly.jobs import enqueue_job, is_job_cancelled, serialize_job_payload
from squidly.storage import get_plex_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job Type Registry
# ---------------------------------------------------------------------------

JOB_TYPES = {
    'download_track': {
        'max_attempts': 20,
        'idle_sleep': 2,
        'process_fn': 'squidly.app.process_download_job',
    },
    'plex_library_sync': {
        'max_attempts': 5,
        'idle_sleep': 5,
        'process_fn': 'squidly.app.process_plex_sync_job',
        'on_success': ['plex_listen_history_sync', 'bulk_playlist_add'],
    },
    'plex_library_update': {
        'max_attempts': 5,
        'idle_sleep': 5,
        'process_fn': 'squidly.plex.process_plex_library_update_job',
        'on_success': ['plex_library_sync'],
    },
    'bulk_playlist_add': {
        'max_attempts': 5,
        'idle_sleep': 5,
        'process_fn': 'squidly.plex.bulk_add_tracks_to_playlists',
    },
    'plex_listen_history_sync': {
        'max_attempts': 5,
        'idle_sleep': 5,
        'process_fn': 'squidly.app.process_plex_listen_history_sync',
    },
    'generate_recommendations': {
        'max_attempts': 3,
        'idle_sleep': 5,
        'process_fn': 'squidly.app.process_recommendation_job',
    },
    'automatic_matching': {
        'max_attempts': 1,
        'idle_sleep': 5,
        'process_fn': 'squidly.app.process_automatic_matching_job',
    },
    'fresh_finds_auto_download': {
        'max_attempts': 10,
        'idle_sleep': 5,
        'process_fn': 'squidly.app.process_fresh_finds_auto_download_job',
    },
}


# ---------------------------------------------------------------------------
# Generic Dedup Guards
# ---------------------------------------------------------------------------

def is_job_type_running_or_queued(job_type):
    """Check if any job of the given type is queued or in progress."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM jobs
        WHERE job_type = %s
          AND status IN ('queued', 'in_progress')
        """,
        (job_type,)
    )
    row = cur.fetchone() or {}
    conn.close()
    return (row.get('count') or 0) > 0


def wait_for_job_type(job_type, timeout=300, poll_interval=5, check_cancelled_job_id=None):
    """Block until no jobs of the given type are running or queued, or timeout.

    Args:
        job_type: The job type string to wait for (e.g. 'plex_library_update').
        timeout: Maximum seconds to wait (default 300). Raises TimeoutError on expiry.
        poll_interval: Seconds between polls (default 5).
        check_cancelled_job_id: If set, check if this job ID was cancelled and raise
            JobCancelledError if so.

    Returns True when no more jobs of the type are running/queued.
    Raises TimeoutError if timeout expires, JobCancelledError if the caller job is cancelled.
    """
    deadline = time.time() + timeout
    while is_job_type_running_or_queued(job_type):
        if check_cancelled_job_id and is_job_cancelled(check_cancelled_job_id):
            from squidly.workers import JobCancelledError
            raise JobCancelledError(f'Job {check_cancelled_job_id} was cancelled while waiting for {job_type}')
        if time.time() > deadline:
            raise TimeoutError(f'Timed out waiting for {job_type} jobs to complete after {timeout}s')
        time.sleep(poll_interval)
    return True


def queue_if_not_running(job_type, payload, max_attempts=None, priority=0, run_after=None):
    """Enqueue a job only if no job of this type is already queued or in progress.

    Returns the job ID if enqueued, or None if a job of this type is already active.
    """
    if is_job_type_running_or_queued(job_type):
        return None

    if max_attempts is None:
        max_attempts = JOB_TYPES.get(job_type, {}).get('max_attempts', 5)

    return enqueue_job(job_type, payload, max_attempts=max_attempts, priority=priority, run_after=run_after)


# ---------------------------------------------------------------------------
# Specific Queue Functions (with additional pre-conditions beyond dedup)
# ---------------------------------------------------------------------------

def queue_plex_library_sync(trigger='manual'):
    """Queue a plex_library_sync job if one is not already queued/in progress."""
    job_id = queue_if_not_running(
        'plex_library_sync',
        {'trigger': trigger, 'requested_at': datetime.utcnow().isoformat() + 'Z'},
        max_attempts=5,
    )
    if job_id:
        logger.info("[PLEX_QUEUE] Queued plex_library_sync job %s (trigger=%s)", job_id, trigger)
    return job_id


def start_plex_sync_job(trigger='manual'):
    """Queue a Plex library sync job if one is not already queued/in progress.

    Validates Plex config before enqueuing.
    """
    config = get_plex_config()
    if not config.get('server_url') or not config.get('api_token') or not config.get('library_name'):
        return {'ok': False, 'status_code': 400, 'error': 'Plex is not fully configured'}

    job_id = queue_plex_library_sync(trigger=trigger)
    if job_id is None:
        return {'ok': False, 'status_code': 409, 'error': 'A Plex sync job is already queued or in progress'}

    return {'ok': True, 'status_code': 202, 'job_id': job_id, 'status': 'queued'}


def queue_plex_library_update(trigger='scheduled'):
    """Queue a plex_library_update job if one is not already queued/in progress."""
    job_id = queue_if_not_running(
        'plex_library_update',
        {'trigger': trigger, 'requested_at': datetime.utcnow().isoformat() + 'Z'},
        max_attempts=5,
    )
    if job_id:
        logger.info("[LIBRARY_UPDATE_QUEUE] Queued plex_library_update job %s (trigger=%s)", job_id, trigger)
    return job_id


def start_plex_library_update_job(trigger='scheduled'):
    """Queue a Plex library update job if one is not already queued/in progress.

    Validates Plex config before enqueuing.
    """
    config = get_plex_config()
    if not config.get('server_url') or not config.get('api_token') or not config.get('library_name'):
        return {'ok': False, 'status_code': 400, 'error': 'Plex is not fully configured'}

    job_id = queue_plex_library_update(trigger=trigger)
    if job_id is None:
        return {'ok': False, 'status_code': 409, 'error': 'A Plex library update job is already queued or in progress'}

    return {'ok': True, 'status_code': 202, 'job_id': job_id, 'status': 'queued'}


def queue_plex_listen_history_sync(trigger='scheduled'):
    """Queue a plex_listen_history_sync job if one is not already queued/in progress."""
    job_id = queue_if_not_running(
        'plex_listen_history_sync',
        {'trigger': trigger, 'requested_at': datetime.utcnow().isoformat() + 'Z'},
        max_attempts=5,
    )
    if job_id:
        logger.info("[LISTEN_HISTORY_QUEUE] Queued plex_listen_history_sync job %s (trigger=%s)", job_id, trigger)
    return job_id


def queue_bulk_playlist_add_job(trigger='post_library_sync'):
    """Queue a bulk_playlist_add job if one is not already queued/in progress
    and there are pending playlist additions.
    """
    if is_job_type_running_or_queued('bulk_playlist_add'):
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


def queue_recommendation_generation(slug, plex_account_id, plex_username, trigger='scheduled'):
    """Queue a generate_recommendations job."""
    payload = {
        'slug': slug,
        'plex_account_id': plex_account_id,
        'plex_username': plex_username,
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('generate_recommendations', payload, max_attempts=3)


def queue_fresh_finds_auto_download(trigger='scheduled'):
    """Queue a fresh_finds_auto_download job if one is not already queued/in progress.

    Processes all users with auto-download enabled — no per-user parameters needed.
    """
    if is_job_type_running_or_queued('fresh_finds_auto_download'):
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job already queued/in progress; not queueing another")
        return None

    payload = {
        'slug': 'fresh-finds',
        'trigger': trigger,
        'requested_at': datetime.utcnow().isoformat() + 'Z'
    }
    return enqueue_job('fresh_finds_auto_download', payload, max_attempts=3)


# ---------------------------------------------------------------------------
# Convenience aliases (matching old function names for backward compat)
# ---------------------------------------------------------------------------

# These are the same as the generic function but kept as explicit aliases
# for readability at call sites that check specific job types.
any_plex_sync_jobs_running_or_queued = lambda: is_job_type_running_or_queued('plex_library_sync')
any_plex_listen_history_sync_jobs_running_or_queued = lambda: is_job_type_running_or_queued('plex_listen_history_sync')
any_plex_library_update_jobs_running_or_queued = lambda: is_job_type_running_or_queued('plex_library_update')


# ---------------------------------------------------------------------------
# Playlist Side-Channel (pending_playlist_adds table)
# ---------------------------------------------------------------------------

def queue_pending_playlist_addition(file_path, playlist_name, parent_job_id=None, plex_user_id=None):
    """Insert a row into pending_playlist_adds table. Idempotent via unique index.

    If a duplicate is detected (ON CONFLICT), marks the parent download job's
    playlist_added stage as 'done' since the track is already queued for bulk add.
    """
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


# ---------------------------------------------------------------------------
# Post-Success Chaining
# ---------------------------------------------------------------------------

def handle_on_success(job_type, result):
    """Enqueue follow-up jobs after a job succeeds, based on JOB_TYPES on_success rules.

    Called by the generic worker loop after mark_job_succeeded.
    """
    config = JOB_TYPES.get(job_type, {})
    on_success = config.get('on_success', [])
    if not on_success:
        return

    for followup_type in on_success:
        if followup_type == 'plex_listen_history_sync':
            job_id = queue_plex_listen_history_sync(trigger=f'post_{job_type}')
            if job_id:
                logger.info("[ON_SUCCESS] %s → queued plex_listen_history_sync job %s", job_type, job_id)

        elif followup_type == 'bulk_playlist_add':
            job_id = queue_bulk_playlist_add_job(trigger=f'post_{job_type}')
            if job_id:
                logger.info("[ON_SUCCESS] %s → queued bulk_playlist_add job %s", job_type, job_id)

        elif followup_type == 'plex_library_sync':
            job_id = queue_plex_library_sync(trigger=f'post_{job_type}')
            if job_id:
                logger.info("[ON_SUCCESS] %s → queued plex_library_sync job %s", job_type, job_id)

        else:
            logger.warning("[ON_SUCCESS] Unknown follow-up job type: %s", followup_type)