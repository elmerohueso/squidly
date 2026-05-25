"""Matching job processor."""

import logging
logger = logging.getLogger(__name__)

from squidly import jobs

def process_automatic_matching_job(job_id, payload):
    """Run the full automatic matching pipeline:
    1. Queue Plex library update
    2. Wait for Plex sync to complete
    3. Run tag analysis to fill missing fields from file tags
    4. Run HiFi gap-fill for remaining unmatched records
    """
    stages = {
        'tag_analysis': 'pending',
        'hifi_gap_fill': 'pending',
    }
    progress = {
        'tag_scanned': 0,
        'tag_filled': 0,
        'hifi_tracks_matched': 0,
        'hifi_albums_matched': 0,
        'hifi_artists_matched': 0,
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    trigger = payload.get('trigger') if isinstance(payload, dict) else 'manual'

    # Stage 1: Tag analysis
    stages['tag_analysis'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[AUTO_MATCH] Job %s running tag analysis", job_id)

    def tag_progress(current, total):
        progress['tag_scanned'] = current
        jobs.update_job_progress(job_id, {'progress': progress})

    tag_result = scan_library_for_tags(progress_callback=tag_progress)
    progress['tag_scanned'] = tag_result.get('total_scanned', 0)
    progress['tag_filled'] = tag_result.get('fields_filled', 0)

    stages['tag_analysis'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
    logger.info("[AUTO_MATCH] Job %s tag analysis complete, scanned=%s, filled=%s", job_id, progress['tag_scanned'], progress['tag_filled'])

    # Stage 2: HiFi gap-fill
    stages['hifi_gap_fill'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[AUTO_MATCH] Job %s running HiFi gap-fill", job_id)

    def hifi_progress(entity_type, current, total):
        jobs.update_job_progress(job_id, {'progress': progress})

    hifi_result = find_missing_hifi_ids(progress_callback=hifi_progress)
    progress['hifi_tracks_matched'] = hifi_result.get('tracks_matched', 0)
    progress['hifi_albums_matched'] = hifi_result.get('albums_matched', 0)
    progress['hifi_artists_matched'] = hifi_result.get('artists_matched', 0)

    stages['hifi_gap_fill'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
    logger.info("[AUTO_MATCH] Job %s HiFi gap-fill complete, tracks=%s, albums=%s, artists=%s", job_id, progress['hifi_tracks_matched'], progress['hifi_albums_matched'], progress['hifi_artists_matched'])

    return {
        'trigger': trigger,
        'stages': stages,
        'progress': progress,
    }


