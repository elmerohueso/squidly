"""Bulk playlist add job processor."""

import logging
import re

from squidly.infrastructure.plex import (
    _plex_call_with_timeout,
    _get_plex_server_for_user,
    _get_or_create_playlist,
    _add_items_to_playlist,
    _playlist_operation_lock,
)
from squidly.infrastructure.storage import get_plex_config, get_todays_recommendation_playlist
from squidly.infrastructure.db import get_db_connection
from squidly import jobs
from squidly.jobs.orchestration import (
    get_pending_playlist_adds,
    delete_pending_playlist_adds,
)

logger = logging.getLogger(__name__)


def bulk_add_tracks_to_playlists(job_id, payload):
    """Process all rows in pending_playlist_adds, grouped by (user_id, playlist_name).

    Returns a result dict with progress fields for the job card.
    """
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()

    if not (server_url and api_token):
        raise ValueError('Plex is not fully configured')

    stages = {
        'resolving_tracks': 'pending',
        'adding_to_playlists': 'pending',
    }
    progress = {
        'total_tracks': 0,
        'tracks_processed': 0,
        'tracks_added': 0,
        'tracks_skipped': 0,
        'tracks_failed': 0,
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    pending = get_pending_playlist_adds()
    total = len(pending)
    progress['total_tracks'] = total
    jobs.update_job_progress(job_id, {'progress': progress})

    logger.info("[BULK_PLAYLIST] Job %s: found %d pending playlist adds", job_id, total)
    for item in pending:
        logger.info("[BULK_PLAYLIST] Job %s: pending add parent_job_id=%s file_path=%s playlist=%s", job_id, item.get('parent_job_id'), item.get('file_path'), item.get('playlist_name'))

    if total == 0:
        stages['resolving_tracks'] = 'skipped'
        stages['adding_to_playlists'] = 'skipped'
        jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
        return {
            'total_tracks': 0,
            'tracks_added': 0,
            'tracks_skipped': 0,
            'tracks_failed': 0,
            'summary': 'No pending tracks',
        }

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT library_id, path
        FROM tracks
        WHERE library_id IS NOT NULL AND library_id <> ''
        """
    )
    rows = cur.fetchall() or []
    conn.close()

    path_index = {}
    for row in rows:
        raw_path = str(row.get('path') or '').strip()
        library_id = str(row.get('library_id') or '').strip()
        if not raw_path or not library_id:
            continue
        path_parts = [p for p in re.split(r'[\\/]+', raw_path) if p]
        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        path_tail = '\\'.join(tail_parts).lower()
        path_index.setdefault(path_tail, []).append(library_id)

    stages['resolving_tracks'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    groups = {}
    for item in pending:
        file_path = str(item.get('file_path') or '').strip()
        playlist_name = str(item.get('playlist_name') or '').strip()
        plex_user_id = item.get('plex_user_id')

        path_parts = [p for p in re.split(r'[\\/]+', file_path) if p]
        tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
        path_tail = '\\'.join(tail_parts).lower()

        library_ids = path_index.get(path_tail, [])
        key = (plex_user_id, playlist_name)
        groups.setdefault(key, {'tracks': [], 'ids': []})
        groups[key]['tracks'].append(item)
        groups[key]['ids'].extend(library_ids)

    # ── Filter stale Fresh Finds tracks ──
    # For recommendation playlists, only add tracks that are still in the current
    # DB playlist. Prevents accumulation in Plex when the DB playlist replaces nightly.
    stale_skipped = 0
    conn = get_db_connection()
    cur = conn.cursor()
    for key, group_data in list(groups.items()):
        plex_user_id, playlist_name = key
        if playlist_name != 'Fresh Finds':
            continue

        # Resolve plex_user_id (which may be plex_client_id) → plex_account_id
        cur.execute(
            "SELECT plex_account_id FROM user_settings WHERE plex_client_id = %s OR plex_account_id = %s LIMIT 1",
            (str(plex_user_id) if plex_user_id else '', str(plex_user_id) if plex_user_id else '')
        )
        row = cur.fetchone()
        if not row:
            logger.info("[BULK_PLAYLIST] No user_settings for plex_user_id=%s, allowing all tracks", plex_user_id)
            continue
        plex_account_id = row['plex_account_id']

        # Get current recommendation playlist hifi_ids
        playlist = get_todays_recommendation_playlist(plex_account_id, 'fresh-finds')
        if not playlist:
            logger.info("[BULK_PLAYLIST] No current Fresh Finds playlist for account %s, allowing all tracks", plex_account_id)
            continue
        current_hifi_ids = {t['hifi_id'] for t in playlist.get('tracks', []) if t.get('hifi_id')}

        # Build path→hifi_id index for these pending tracks
        original_count = len(group_data['tracks'])
        filtered_tracks = []
        filtered_ids = []
        for i, item in enumerate(group_data['tracks']):
            file_path = str(item.get('file_path') or '').strip()
            path_parts = [p for p in re.split(r'[\\/]+', file_path) if p]
            tail_parts = path_parts[-3:] if len(path_parts) >= 3 else path_parts
            trailing_suffix = '/'.join(tail_parts)

            # Look up hifi_id from tracks table (matches SQL replace(path, '\\', '/'))
            cur.execute("SELECT hifi_id FROM tracks WHERE lower(right(replace(path, '\\', '/'), length(%s))) = lower(%s)", (trailing_suffix, trailing_suffix))
            track_row = cur.fetchone()
            hifi_id = track_row['hifi_id'] if track_row and track_row.get('hifi_id') else None

            if hifi_id and hifi_id in current_hifi_ids:
                filtered_tracks.append(item)
                filtered_ids.append(group_data['ids'][i])
            else:
                stale_skipped += 1
                logger.info("[BULK_PLAYLIST] Skipping stale track: %s (hifi_id=%s not in current playlist)", file_path, hifi_id)

        group_data['tracks'] = filtered_tracks
        group_data['ids'] = filtered_ids

        if original_count != len(filtered_tracks):
            logger.info("[BULK_PLAYLIST] Filtered %d → %d tracks for Fresh Finds (user %s)", original_count, len(filtered_tracks), plex_user_id)

    conn.close()

    if stale_skipped:
        logger.info("[BULK_PLAYLIST] Skipped %d stale tracks not in current Fresh Finds playlists", stale_skipped)
        progress['total_tracks'] = total - stale_skipped

    stages['adding_to_playlists'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    successful_ids = []
    plex_cache = {}

    for (plex_user_id, playlist_name), group_data in groups.items():
        user_display = plex_user_id or 'Owner'
        logger.info("[BULK_PLAYLIST] Processing %d tracks for playlist '%s' (user: %s)", len(group_data['tracks']), playlist_name, user_display)

        if plex_user_id not in plex_cache:
            try:
                plex_cache[plex_user_id] = _get_plex_server_for_user(server_url, api_token, plex_user_id)
            except Exception as e:
                logger.info("[BULK_PLAYLIST] Failed to get Plex server for user %s: %s", user_display, str(e))
                for item in group_data['tracks']:
                    progress['tracks_processed'] += 1
                    progress['tracks_failed'] += 1
                    jobs.update_job_progress(job_id, {'progress': progress})
                continue

        plex = plex_cache[plex_user_id]

        unique_library_ids = list(dict.fromkeys(group_data['ids']))
        tracks_to_add = []

        for rating_key in unique_library_ids:
            metadata_key = rating_key if rating_key.startswith('/library/metadata/') else f'/library/metadata/{rating_key}'
            try:
                candidate = _plex_call_with_timeout(plex.fetchItem, metadata_key, timeout=15, label="fetchItem")
                if candidate is not None:
                    tracks_to_add.append(candidate)
            except Exception as e:
                logger.info("[BULK_PLAYLIST] Failed to fetch ratingKey=%s: %s", rating_key, str(e))

        if not tracks_to_add:
            for item in group_data['tracks']:
                progress['tracks_processed'] += 1
                progress['tracks_failed'] += 1
                jobs.update_job_progress(job_id, {'progress': progress})
            continue

        with _playlist_operation_lock:
            playlist, created = _get_or_create_playlist(plex, playlist_name, items=tracks_to_add)
            if created:
                for item in group_data['tracks']:
                    progress['tracks_processed'] += 1
                    progress['tracks_added'] += 1
                    successful_ids.append(item['id'])
                    jobs.update_job_progress(job_id, {'progress': progress})
                continue

            added, skipped, failed = _add_items_to_playlist(playlist, tracks_to_add)
            for item in group_data['tracks']:
                progress['tracks_processed'] += 1
                if added > 0:
                    progress['tracks_added'] += 1
                    successful_ids.append(item['id'])
                elif skipped > 0:
                    progress['tracks_skipped'] += 1
                    successful_ids.append(item['id'])
                else:
                    progress['tracks_failed'] += 1
                jobs.update_job_progress(job_id, {'progress': progress})

    stages['adding_to_playlists'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    if successful_ids:
        delete_pending_playlist_adds(successful_ids)

    # ── Sync Fresh Finds playlists to DB ──
    # After adding tracks, remove any Plex tracks that are no longer in the DB playlist.
    # This ensures the Plex playlist matches the DB (source of truth).
    from squidly.infrastructure.plex import sync_plex_playlist_to_db
    synced_playlists = set()
    conn = get_db_connection()
    cur = conn.cursor()
    for (plex_user_id, playlist_name), group_data in groups.items():
        if playlist_name != 'Fresh Finds':
            continue
        if plex_user_id in synced_playlists:
            continue
        synced_playlists.add(plex_user_id)

        # Resolve plex_user_id → plex_account_id
        cur.execute(
            "SELECT plex_account_id FROM user_settings WHERE plex_client_id = %s OR plex_account_id = %s LIMIT 1",
            (str(plex_user_id) if plex_user_id else '', str(plex_user_id) if plex_user_id else '')
        )
        row = cur.fetchone()
        if not row:
            continue
        plex_account_id = row['plex_account_id']

        # Get current DB playlist
        db_playlist = get_todays_recommendation_playlist(plex_account_id, 'fresh-finds')
        if not db_playlist:
            continue

        desired_hifi_ids = {t['hifi_id'] for t in db_playlist.get('tracks', []) if t.get('hifi_id')}
        removed = sync_plex_playlist_to_db(plex_account_id, playlist_name, desired_hifi_ids)
        if removed:
            logger.info("[BULK_PLAYLIST] Synced Plex playlist '%s' for user %s, removed %d stale tracks",
                        playlist_name, plex_user_id, removed)
    conn.close()

    summary = (
        f"{progress['tracks_processed']}/{total} tracks processed • "
        f"{progress['tracks_added']} added • "
        f"{progress['tracks_skipped']} skipped • "
        f"{progress['tracks_failed']} failed"
    )

    return {
        'stages': stages,
        'progress': progress,
        'total_tracks': total,
        'tracks_processed': progress['tracks_processed'],
        'tracks_added': progress['tracks_added'],
        'tracks_skipped': progress['tracks_skipped'],
        'tracks_failed': progress['tracks_failed'],
        'summary': summary,
    }
