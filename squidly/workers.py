"""Background worker loop functions for Squidly job processing."""

import json
import logging
import time

from squidly.jobs import (
    any_plex_sync_jobs_running_or_queued,
    claim_next_job,
    mark_job_cancelled,
    mark_job_failed,
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
                from squidly.jobs import queue_bulk_playlist_add_job
                bulk_job_id = queue_bulk_playlist_add_job(trigger='post_library_sync')
                if bulk_job_id:
                    logger.info("[PLEX_SYNC_WORKER] Queued bulk playlist add job %s", bulk_job_id)
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


def bulk_playlist_add_job_worker():
    from squidly.jobs import (
        claim_next_job,
        mark_job_succeeded,
        mark_job_failed,
        get_pending_playlist_adds,
        delete_pending_playlist_adds,
    )
    from squidly.plex import bulk_add_tracks_to_playlists
    from squidly.storage import get_plex_config

    logger.info("[BULK_PLAYLIST_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('bulk_playlist_add')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                plex_config = get_plex_config()
                server_url = (plex_config.get('server_url') or '').strip()
                api_token = (plex_config.get('api_token') or '').strip()
                library_name = (plex_config.get('library_name') or 'Music').strip()

                if not (server_url and api_token and library_name):
                    raise ValueError('Plex is not fully configured')

                result = bulk_add_tracks_to_playlists(
                    job['id'],
                    server_url,
                    api_token,
                    library_name,
                )
                mark_job_succeeded(job['id'], result)
                logger.info("[BULK_PLAYLIST_WORKER] Job %s completed: %s", job['id'], result.get('summary', ''))
            except Exception as e:
                logger.info("[BULK_PLAYLIST_WORKER] Job %s failed: %s", job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("[BULK_PLAYLIST_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)


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


def recommendation_job_worker():
    from squidly.app import process_recommendation_job

    logger.info("[RECOMMENDATION_WORKER] Background worker started")

    while True:
        try:
            job = claim_next_job('generate_recommendations')
            if not job:
                time.sleep(5)
                continue

            try:
                payload = json.loads(job['payload_json']) if job['payload_json'] else {}
            except (TypeError, ValueError):
                payload = {}

            try:
                result = process_recommendation_job(job['id'], payload)
                mark_job_succeeded(job['id'], result)
                logger.info("[RECOMMENDATION_WORKER] Job %s completed", job['id'])
            except JobCancelledError:
                mark_job_cancelled(job['id'])
                logger.info("[RECOMMENDATION_WORKER] Job %s cancelled", job['id'])
                time.sleep(1)
            except Exception as e:
                logger.info("[RECOMMENDATION_WORKER] Job %s failed: %s", job['id'], str(e))
                mark_job_failed(job['id'], job['attempt_count'], job['max_attempts'], str(e))
                time.sleep(1)
        except Exception as e:
            logger.info("[RECOMMENDATION_WORKER] Error in background worker: %s", str(e))
            time.sleep(5)


def recommendation_scheduler_worker():
    from squidly.jobs import queue_recommendation_generation
    from squidly.storage import get_all_plex_account_mappings, has_listen_history

    logger.info("[RECOMMENDATION_SCHEDULER] Background scheduler started")

    last_run_date = None

    while True:
        try:
            now = datetime.utcnow()
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

        except Exception as e:
            logger.info("[RECOMMENDATION_SCHEDULER] Error: %s", str(e))

        time.sleep(60)
