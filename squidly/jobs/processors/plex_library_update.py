"""Plex library update job processor."""

import json
import logging
import time
from datetime import datetime

from squidly import jobs
from squidly.infrastructure.plex import (
    _plex_call_with_timeout,
    _is_plex_library_scan_active,
    wait_for_plex_library_scan_completion,
)
from squidly.infrastructure.storage import (
    can_start_plex_library_update,
    get_plex_config,
    set_last_library_update_time,
)

logger = logging.getLogger(__name__)


def process_plex_library_update_job(job_id, payload, gate_snapshot=None):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or '').strip()

    if not server_url or not api_token or not library_name:
        raise ValueError('Plex server_url, api_token, and library_name must be configured before updating library')

    stages = {
        'scanning_plex_library': 'pending'
    }
    progress = {
        'download_gate_status': 'pending',
        'download_gate_checks': 0,
        'download_gate_blocking_count': 0,
        'download_gate_idle_seconds': 0,
        'download_gate_required_idle_seconds': 180,
        'download_gate_last_activity_at': None,
        'scan_detected': False,
        'scan_completed': False,
        'sync_job_id': None,
        'sync_queue_status': 'pending'
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    gate = gate_snapshot or can_start_plex_library_update(required_idle_seconds=180)
    gate_state = gate.get('gate_state') or {}
    progress['download_gate_checks'] = 1
    progress['download_gate_blocking_count'] = gate_state.get('blocking_count') or 0
    progress['download_gate_idle_seconds'] = gate.get('idle_seconds') or 0
    progress['download_gate_required_idle_seconds'] = gate.get('required_idle_seconds') or 180
    progress['download_gate_last_activity_at'] = gate.get('last_activity_at')
    progress['download_gate_status'] = 'ready'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['scanning_plex_library'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    from plexapi.server import PlexServer
    logger.info("[LIBRARY_UPDATE_JOB] Job %s connecting to Plex at %s", job_id, server_url)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)

    library = None
    sections = _plex_call_with_timeout(plex.library.sections, timeout=30, label="library.sections")
    for section in sections:
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    logger.info("[LIBRARY_UPDATE_JOB] Job %s triggering scan on library '%s'", job_id, library_name)
    _plex_call_with_timeout(library.update, timeout=30, label="library.update")

    completed, saw_active = wait_for_plex_library_scan_completion(
        plex,
        library,
        timeout_seconds=600,
        poll_interval_seconds=5,
        startup_grace_seconds=30
    )

    progress['scan_detected'] = bool(saw_active)
    progress['scan_completed'] = bool(completed)
    stages['scanning_plex_library'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    set_last_library_update_time(datetime.utcnow())

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    scan_outcome = 'completed' if completed else ('started_but_timeout' if saw_active else 'not_observed')
    logger.info(
        "[LIBRARY_UPDATE_JOB] Job %s finished. scan_outcome=%s",
        job_id,
        scan_outcome,
    )

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'scan_outcome': scan_outcome,
    }
