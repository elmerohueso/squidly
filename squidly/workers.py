"""Generic worker loop and scheduler threads for Squidly job processing."""

import importlib
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from squidly.config import app_timezone
from squidly.jobs import (
    RetryableError,
    PermanentError,
    claim_next_job,
    is_job_cancelled,
    mark_job_cancelled,
    mark_job_failed,
    mark_job_retrying,
    mark_job_succeeded,
    requeue_claimed_job,
    serialize_job_payload,
)
from squidly.orchestration import (
    JOB_TYPES,
    any_plex_library_update_jobs_running_or_queued,
    handle_on_success,
    queue_recommendation_generation,
)
from squidly.plex import get_last_successful_plex_sync_finished_at
from squidly.storage import get_plex_config

logger = logging.getLogger(__name__)


class JobCancelledError(Exception):
    pass


def _raise_if_job_cancelled(job_id):
    if is_job_cancelled(job_id):
        raise JobCancelledError(f'Job {job_id} was cancelled')


# ---------------------------------------------------------------------------
# Process function import cache
# ---------------------------------------------------------------------------

_process_fn_cache = {}


def _import_process_fn(dotted_path):
    """Import and cache a process function by dotted path (e.g. 'squidly.app.process_download_job')."""
    if dotted_path in _process_fn_cache:
        return _process_fn_cache[dotted_path]

    module_path, fn_name = dotted_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, fn_name)
    _process_fn_cache[dotted_path] = fn
    return fn


# ---------------------------------------------------------------------------
# Generic Worker Loop
# ---------------------------------------------------------------------------

def worker_loop(job_type, idle_sleep=None):
    """Generic worker: claim job → dispatch to process_fn → mark result.

    Reads job config from JOB_TYPES registry. Handles:
    - RetryableError → mark_job_retrying
    - PermanentError → mark_job_failed (no retry)
    - JobCancelledError → mark_job_cancelled
    - Other exceptions → mark_job_failed
    - On success → mark_job_succeeded + handle_on_success chaining
    """
    config = JOB_TYPES[job_type]
    if idle_sleep is None:
        idle_sleep = config.get('idle_sleep', 5)
    process_fn = _import_process_fn(config['process_fn'])

    log_prefix = f"[{job_type.upper()}_WORKER]"
    logger.info("%s Background worker started", log_prefix)

    while True:
        try:
            job = claim_next_job(job_type)
            if not job:
                time.sleep(idle_sleep)
                continue

            logger.info("%s Claimed %s job %s", log_prefix, job_type, job['id'])

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_fn(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("%s Job %s completed", log_prefix, job['id'])
                handle_on_success(job_type, result)

            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("%s Job %s cancelled", log_prefix, job['id'])
                time.sleep(1)

            except RetryableError as e:
                logger.info("%s Job %s retrying: %s", log_prefix, job['id'], str(e))
                mark_job_retrying(job['id'], job['attempt_count'], str(e))
                time.sleep(1)

            except PermanentError as e:
                logger.info("%s Job %s failed (permanent): %s", log_prefix, job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)

            except Exception as e:
                logger.info("%s Job %s failed: %s", log_prefix, job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)

        except Exception as e:
            logger.exception("%s Error in background worker: %s", log_prefix, str(e))
            time.sleep(5)


# ---------------------------------------------------------------------------
# Special-case workers with pre-claim logic
# ---------------------------------------------------------------------------

def download_track_worker():
    """Worker for download_track jobs with custom stage validation."""
    from squidly.downloads import download_track_all_stages_done
    from squidly.app import process_download_job

    log_prefix = "[DOWNLOAD_WORKER]"
    logger.info("%s Background worker started", log_prefix)

    while True:
        try:
            job = claim_next_job('download_track')
            if not job:
                time.sleep(2)
                continue

            logger.info("%s Claimed download job %s", log_prefix, job['id'])

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_download_job(job['id'], payload)
                stages = result.get('stages') if isinstance(result, dict) else {}

                if download_track_all_stages_done(stages):
                    mark_job_succeeded(job['id'], result)
                    logger.info("%s Job %s completed", log_prefix, job['id'])
                    handle_on_success('download_track', result)
                else:
                    stage_state = stages if isinstance(stages, dict) else {}
                    error_message = f"Download stages incomplete: {serialize_job_payload(stage_state)}"
                    logger.info("%s Job %s failed: %s", log_prefix, job['id'], error_message)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_message)

            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("%s Job %s cancelled", log_prefix, job['id'])
                time.sleep(1)

            except RetryableError as e:
                logger.info("%s Job %s retrying: %s", log_prefix, job['id'], str(e))
                mark_job_retrying(job['id'], job['attempt_count'], str(e))
                time.sleep(1)

            except PermanentError as e:
                logger.info("%s Job %s failed (permanent): %s", log_prefix, job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)

            except Exception as e:
                logger.info("%s Job %s failed: %s", log_prefix, job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)

        except Exception as e:
            logger.exception("%s Error in background worker: %s", log_prefix, str(e))
            time.sleep(5)


def plex_sync_worker():
    """Worker for plex_library_sync jobs with pre-claim deferral logic."""
    from squidly.app import process_plex_sync_job

    log_prefix = "[PLEX_SYNC_WORKER]"
    logger.info("%s Background worker started", log_prefix)

    while True:
        try:
            job = claim_next_job('plex_library_sync')
            if not job:
                time.sleep(5)
                continue

            logger.info("%s Claimed plex_library_sync job %s", log_prefix, job['id'])

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            if any_plex_library_update_jobs_running_or_queued():
                requeue_claimed_job(
                    job['id'],
                    delay_seconds=20,
                    error_message='Waiting for plex_library_update jobs to finish before sync'
                )
                logger.info("%s Job %s deferred until library update completes", log_prefix, job['id'])
                time.sleep(1)
                continue

            try:
                result = process_plex_sync_job(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("%s Job %s completed", log_prefix, job['id'])
                handle_on_success('plex_library_sync', result)
            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("%s Job %s cancelled", log_prefix, job['id'])
                time.sleep(1)
            except Exception as e:
                logger.info("%s Job %s failed: %s", log_prefix, job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("%s Error in background worker: %s", log_prefix, str(e))
            time.sleep(5)


def plex_library_update_worker():
    """Worker for plex_library_update jobs with download gate logic."""
    from squidly.plex import process_plex_library_update_job
    from squidly.storage import can_start_plex_library_update
    from squidly import jobs as jobs_module

    log_prefix = "[LIBRARY_UPDATE_WORKER]"
    logger.info("%s Background worker started", log_prefix)
    gate_poll_seconds = 15

    while True:
        try:
            gate = can_start_plex_library_update(required_idle_seconds=180)
            if not gate.get('can_start'):
                if any_plex_library_update_jobs_running_or_queued():
                    gate_state = gate.get('gate_state') or {}
                    blocking_count = gate_state.get('blocking_count') or 0
                    idle_seconds = gate.get('idle_seconds')
                    required_idle = gate.get('required_idle_seconds') or 180
                    logger.info(
                        "%s Waiting to claim update job: blocking=%d idle_seconds=%s required_idle=%s",
                        log_prefix, blocking_count, idle_seconds, required_idle,
                    )
                time.sleep(gate_poll_seconds)
                continue

            job = claim_next_job('plex_library_update')
            if not job:
                time.sleep(5)
                continue

            logger.info("%s Claimed plex_library_update job %s", log_prefix, job['id'])

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                gate_after_claim = can_start_plex_library_update(required_idle_seconds=180)
                if not gate_after_claim.get('can_start'):
                    jobs_module.requeue_claimed_job(
                        job['id'],
                        delay_seconds=gate_poll_seconds,
                        error_message='Waiting for downloads gate before starting Plex library update'
                    )
                    logger.info("%s Job %s deferred until downloads gate is ready", log_prefix, job['id'])
                    time.sleep(1)
                    continue

                result = process_plex_library_update_job(job['id'], payload, gate_snapshot=gate_after_claim)
                jobs_module.mark_job_succeeded(job['id'], result)
                logger.info("%s Job %s completed", log_prefix, job['id'])
                handle_on_success('plex_library_update', result)
            except Exception as e:
                logger.info("%s Job %s failed: %s", log_prefix, job['id'], str(e))
                jobs_module.mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("%s Error in background worker: %s", log_prefix, str(e))
            time.sleep(5)


# ---------------------------------------------------------------------------
# Scheduler Threads
# ---------------------------------------------------------------------------

def plex_sync_scheduler_worker():
    """Periodically queue plex_library_update jobs based on configured interval.

    The update chains to plex_library_sync → automatic_matching → bulk_playlist_add
    via on_success rules.
    """
    from squidly.orchestration import queue_plex_library_update

    logger.info("[PLEX_SYNC_SCHEDULER] Background scheduler started")

    while True:
        try:
            config = get_plex_config()
            server_url = (config.get('server_url') or '').strip()
            api_token = (config.get('api_token') or '').strip()
            library_name = (config.get('library_name') or '').strip()

            if not (server_url and api_token and library_name):
                time.sleep(60)
                continue

            interval_hours = config.get('sync_interval_hours')
            try:
                interval_hours = int(interval_hours)
            except Exception:
                interval_hours = 24
            if interval_hours < 1:
                interval_hours = 1

            if any_plex_library_update_jobs_running_or_queued():
                time.sleep(60)
                continue

            last_finished = get_last_successful_plex_sync_finished_at()
            should_enqueue = False
            now = datetime.utcnow()
            if not last_finished:
                should_enqueue = True
            else:
                should_enqueue = now - last_finished >= timedelta(hours=interval_hours)

            if should_enqueue:
                queued = queue_plex_library_update(trigger='interval')
                if queued:
                    logger.info("[PLEX_SYNC_SCHEDULER] Queued interval library update job %s", queued)

        except Exception as e:
            logger.info("[PLEX_SYNC_SCHEDULER] Error: %s", str(e))

        time.sleep(60)


def recommendation_scheduler_worker():
    """Queue Fresh Finds recommendation generation daily at midnight."""
    from squidly.storage import get_all_plex_account_mappings, has_listen_history

    logger.info("[RECOMMENDATION_SCHEDULER] Background scheduler started")

    last_run_date = None
    tz = ZoneInfo(app_timezone)

    while True:
        try:
            now = datetime.now(tz)
            today = now.date()

            if last_run_date == today:
                time.sleep(60)
                continue

            if now.hour != 0:
                time.sleep(60)
                continue

            last_run_date = today
            logger.info("[RECOMMENDATION_SCHEDULER] Running daily recommendation generation")

            mappings = get_all_plex_account_mappings()
            for mapping in mappings:
                plex_account_id = mapping.get('plex_account_id')
                plex_username = mapping.get('username')
                if plex_account_id is None or plex_username is None:
                    continue

                if not has_listen_history(plex_account_id):
                    continue

                try:
                    job_id = queue_recommendation_generation(
                        slug='fresh-finds',
                        plex_account_id=plex_account_id,
                        plex_username=plex_username,
                        trigger='scheduled'
                    )
                    if job_id:
                        logger.info("[RECOMMENDATION_SCHEDULER] Queued Fresh Finds for %s (job %s)", plex_username, job_id)
                except Exception as e:
                    logger.info("[RECOMMENDATION_SCHEDULER] Failed to queue for %s: %s", plex_username, e)

            # Queue a single auto-download job after all recommendation jobs.
            # The auto-download job will wait for recommendations to finish before processing.
            try:
                from squidly.orchestration import queue_fresh_finds_auto_download
                auto_job_id = queue_fresh_finds_auto_download(trigger='scheduled')
                if auto_job_id:
                    logger.info("[RECOMMENDATION_SCHEDULER] Queued Fresh Finds auto-download (job %s)", auto_job_id)
            except Exception as e:
                logger.info("[RECOMMENDATION_SCHEDULER] Failed to queue auto-download: %s", e)

        except Exception as e:
            logger.info("[RECOMMENDATION_SCHEDULER] Error: %s", str(e))

        time.sleep(60)


# ---------------------------------------------------------------------------
# Worker Startup
# ---------------------------------------------------------------------------

# Job types that use the generic worker_loop (no special pre-claim logic)
_GENERIC_WORKER_TYPES = [
    'automatic_matching',
    'bulk_playlist_add',
    'plex_listen_history_sync',
    'generate_recommendations',
    'fresh_finds_auto_download',
]


def start_workers():
    """Start all background worker and scheduler threads.

    Uses the generic worker_loop for standard job types,
    and dedicated worker functions for types with special pre-claim logic.
    """
    threads = []

    # Generic workers — one thread per job type
    for job_type in _GENERIC_WORKER_TYPES:
        t = threading.Thread(
            target=worker_loop,
            args=(job_type,),
            daemon=True,
            name=f'{job_type}_worker',
        )
        t.start()
        threads.append(t)
        logger.info("%s worker started", job_type)

    # Special-case workers with pre-claim logic
    special_workers = [
        (download_track_worker, 'download_track_worker'),
        (plex_sync_worker, 'plex_library_sync_worker'),
        (plex_library_update_worker, 'plex_library_update_worker'),
    ]
    for fn, name in special_workers:
        t = threading.Thread(target=fn, daemon=True, name=name)
        t.start()
        threads.append(t)
        logger.info("%s started", name)

    # Scheduler threads
    schedulers = [
        (plex_sync_scheduler_worker, 'plex_sync_scheduler'),
        (recommendation_scheduler_worker, 'recommendation_scheduler'),
    ]
    for fn, name in schedulers:
        t = threading.Thread(target=fn, daemon=True, name=name)
        t.start()
        threads.append(t)
        logger.info("%s started", name)

    return threads