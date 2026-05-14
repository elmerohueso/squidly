"""Background worker loop functions for Squidly job processing."""

import json
import logging
import time

from squidly.jobs import (
    any_plex_sync_jobs_running_or_queued,
    claim_next_job,
    mark_job_cancelled,
    mark_job_failed,
    mark_job_in_progress,
    mark_job_retrying,
    mark_job_succeeded,
    queue_plex_listen_history_sync,
    requeue_claimed_job,
    serialize_job_payload,
)
from squidly.plex import any_plex_library_update_jobs_running_or_queued, get_last_successful_plex_sync_finished_at
from squidly.storage import get_plex_config
from squidly.jobs import (
    queue_plex_library_sync,
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class JobCancelledError(Exception):
    pass


def _raise_if_job_cancelled(job_id):
    from squidly.jobs import is_job_cancelled
    if is_job_cancelled(job_id):
        raise JobCancelledError(f'Job {job_id} was cancelled')


def download_job_worker():
    from squidly.app import process_download_job

    logger.info("[DOWNLOAD_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('download_track')
            if not job:
                time.sleep(2)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_download_job(job['id'], payload)
                stages = result.get('stages') if isinstance(result, dict) else {}

                from squidly.jobs import _download_track_all_stages_done
                if _download_track_all_stages_done(stages):
                    mark_job_succeeded(job['id'], result)
                    logger.info("[DOWNLOAD_WORKER] Job %s completed", job['id'])
                elif isinstance(stages, dict) and stages.get('playlist_added') == 'queued':
                    mark_job_in_progress(job['id'])
                    logger.info("[DOWNLOAD_WORKER] Job %s waiting for playlist_add completion", job['id'])
                else:
                    stage_state = stages if isinstance(stages, dict) else {}
                    error_message = f"Download stages incomplete: {serialize_job_payload(stage_state)}"
                    logger.info("[DOWNLOAD_WORKER] Job %s failed: %s", job['id'], error_message)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_message)
            except Exception as e:
                error_str = str(e)
                if 'permanent' in error_str.lower():
                    logger.info("[DOWNLOAD_WORKER] Job %s failed (permanent): %s", job['id'], error_str)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_str)
                elif 'manifest' in error_str.lower() or 'transient' in error_str.lower():
                    if job['attempt_count'] + 1 >= job['max_attempts']:
                        logger.info("[DOWNLOAD_WORKER] Job %s failed: %s", job['id'], error_str)
                        mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_str)
                    else:
                        logger.info("[DOWNLOAD_WORKER] Job %s retrying (manifest fetch): %s", job['id'], error_str)
                        mark_job_retrying(job['id'], job['attempt_count'], error_str)
                else:
                    logger.info("[DOWNLOAD_WORKER] Job %s failed: %s", job['id'], error_str)
                    mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], error_str)
                time.sleep(1)
        except Exception as e:
            logger.info("[DOWNLOAD_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)


def plex_sync_job_worker():
    from squidly.app import process_plex_sync_job

    logger.info("[PLEX_SYNC_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('plex_library_sync')
            if not job:
                time.sleep(5)
                continue

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
                logger.info("[PLEX_SYNC_WORKER] Job %s deferred until library update completes", job['id'])
                time.sleep(1)
                continue

            try:
                result = process_plex_sync_job(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("[PLEX_SYNC_WORKER] Job %s completed", job['id'])
                queue_plex_listen_history_sync(trigger='post_library_sync')
            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("[PLEX_SYNC_WORKER] Job %s cancelled", job['id'])
                time.sleep(1)
            except Exception as e:
                logger.info("[PLEX_SYNC_WORKER] Job %s failed: %s", job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("[PLEX_SYNC_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)


def automatic_matching_job_worker():
    from squidly.app import process_automatic_matching_job

    logger.info("[AUTO_MATCH_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('automatic_matching')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_automatic_matching_job(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("[AUTO_MATCH_WORKER] Job %s completed", job['id'])
            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("[AUTO_MATCH_WORKER] Job %s cancelled", job['id'])
                time.sleep(1)
            except Exception as e:
                logger.info("[AUTO_MATCH_WORKER] Job %s failed: %s", job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("[AUTO_MATCH_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)


def retry_pending_playlist_additions():
    from squidly.jobs import (
        get_pending_playlist_additions,
        remove_pending_addition,
        update_parent_playlist_stage,
        update_pending_addition_attempt,
    )
    from squidly.plex import add_tracks_to_plex_playlist

    """Background worker that periodically retries failed playlist additions."""
    logger.info("[PLEX_WORKER] Background worker started")

    while True:
        try:
            time.sleep(300)

            plex_config = get_plex_config()

            if not (plex_config['server_url'] and plex_config['api_token']):
                continue

            pending = get_pending_playlist_additions()

            if not pending:
                continue

            logger.info("[PLEX_WORKER] Found %d pending playlist additions to retry", len(pending))

            for addition in pending:
                parent_job_id = None
                try:
                    payload = addition.get('payload') or {}
                    parent_job_id = payload.get('parent_job_id')
                    artist = payload.get('artist', 'Unknown Artist')
                    title = payload.get('title', 'Unknown Track')
                    file_path = str(payload.get('file_path') or '').strip()
                    playlist_name = payload.get('playlist_name')

                    success, message = add_tracks_to_plex_playlist(
                        plex_config['server_url'],
                        plex_config['api_token'],
                        plex_config['library_name'] or 'Music',
                        playlist_name,
                        file_path,
                        payload.get('plex_user_id')
                    )

                    if success:
                        logger.info("[PLEX_WORKER] Successfully added: %s - %s", artist, title)
                        remove_pending_addition(addition['id'])
                        update_parent_playlist_stage(parent_job_id, 'done')
                    else:
                        update_pending_addition_attempt(addition['id'], message)
                        if addition['attempt_count'] + 1 >= addition['max_attempts']:
                            update_parent_playlist_stage(parent_job_id, 'failed')
                            logger.info("[PLEX_WORKER] Max attempts reached for: %s - %s", artist, title)
                        else:
                            logger.info("[PLEX_WORKER] Retry failed (attempt %d/%d): %s", addition['attempt_count'] + 1, addition['max_attempts'], message)

                    time.sleep(2)

                except Exception as e:
                    logger.info("[PLEX_WORKER] Error processing addition %s: %s", addition['id'], str(e))
                    update_pending_addition_attempt(addition['id'], str(e))
                    if addition['attempt_count'] + 1 >= addition['max_attempts']:
                        update_parent_playlist_stage(parent_job_id, 'failed')

        except Exception as e:
            logger.info("[PLEX_WORKER] Error in background worker: %s", str(e))
            time.sleep(60)


def plex_sync_scheduler_worker():
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

            if any_plex_sync_jobs_running_or_queued():
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
                queued = queue_plex_library_sync(trigger='interval')
                if queued:
                    logger.info("[PLEX_SYNC_SCHEDULER] Queued interval sync job %s", queued)

        except Exception as e:
            logger.info("[PLEX_SYNC_SCHEDULER] Error: %s", str(e))

        time.sleep(60)


def listen_history_sync_worker():
    from squidly.app import process_plex_listen_history_sync

    logger.info("[HISTORY_SYNC_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('plex_listen_history_sync')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_plex_listen_history_sync(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("[HISTORY_SYNC_WORKER] Job %s completed", job['id'])
            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("[HISTORY_SYNC_WORKER] Job %s cancelled", job['id'])
                time.sleep(1)
            except Exception as e:
                logger.info("[HISTORY_SYNC_WORKER] Job %s failed: %s", job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("[HISTORY_SYNC_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)
