"""Listen_History job processor."""

import logging
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

from plexapi.server import PlexServer
from squidly import jobs
from squidly.db import get_db_connection
from squidly.jobs.orchestration import queue_plex_listen_history_sync
from squidly.jobs.workers import _raise_if_job_cancelled
from squidly.plex import plex_healthcheck, get_plex_config
from squidly.storage import get_all_plex_account_mappings, get_listen_history, get_recent_listen_history_seeds
from squidly.storage import get_listen_history_sync_status, save_plex_account_id, set_listen_history_sync_status
from squidly.storage import upsert_listen_history_entries

def process_plex_listen_history_sync(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured')

    stages = {
        'resolving_accounts': 'pending',
        'fetching_history': 'pending',
        'storing_entries': 'pending'
    }
    progress = {
        'users_processed': 0,
        'total_users': 0,
        'entries_fetched': 0,
        'entries_stored': 0
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)

    accounts = plex.systemAccounts() or []
    account_name_to_id = {}
    for acc in accounts:
        name = str(getattr(acc, 'name', '') or '').strip()
        acc_id = getattr(acc, 'id', None)
        if name and acc_id is not None:
            account_name_to_id[name] = int(acc_id)

    user_mappings = get_all_plex_account_mappings()
    progress['total_users'] = len(user_mappings)
    jobs.update_job_progress(job_id, {'progress': progress})

    stages['resolving_accounts'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    resolved_users = []
    for mapping in user_mappings:
        username = str(mapping.get('username') or '').strip()
        plex_client_id = str(mapping.get('plex_client_id') or '').strip()
        plex_account_id = mapping.get('plex_account_id')
        plex_owner = bool(mapping.get('plex_owner'))

        if plex_account_id is None:
            resolved_id = account_name_to_id.get(username)
            if resolved_id is not None:
                save_plex_account_id(plex_client_id, resolved_id)
                plex_account_id = resolved_id

        if plex_account_id is not None:
            resolved_users.append({
                'username': username,
                'plex_account_id': int(plex_account_id),
                'plex_client_id': plex_client_id,
                'plex_owner': plex_owner
            })

    stages['resolving_accounts'] = 'done'
    stages['fetching_history'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    global_status = get_listen_history_sync_status(0)
    last_synced = global_status.get('last_synced_at')
    mindate = None
    if last_synced:
        if isinstance(last_synced, datetime):
            dt = last_synced
        else:
            try:
                dt = datetime.fromisoformat(str(last_synced).replace('Z', '+00:00'))
                dt = dt.replace(tzinfo=None)
            except Exception:
                dt = None
        if dt:
            mindate = dt - timedelta(hours=1)
    else:
        mindate = datetime.utcnow() - timedelta(days=30)
        logger.info("[HISTORY_SYNC] Initial sync — limiting to last 30 days (mindate=%s)", mindate.isoformat())

    logger.info("[HISTORY_SYNC] Fetching Plex history (mindate=%s, maxresults=50000)...", mindate)
    try:
        history_items = plex.history(mindate=mindate, maxresults=50000)
    except Exception as e:
        raise ValueError(f'Failed to fetch Plex history: {e}')
    logger.info("[HISTORY_SYNC] Fetched %s history items", len(history_items))

    account_id_to_users = {}
    for u in resolved_users:
        account_id_to_users.setdefault(u['plex_account_id'], []).append(u)

    entries_by_account = {}
    for item in history_items:
        item_account_id = getattr(item, 'accountID', None)
        if item_account_id not in account_id_to_users:
            continue

        item_type = str(getattr(item, 'type', '') or '').strip().lower()
        if item_type != 'track':
            continue

        rating_key = str(getattr(item, 'ratingKey', '') or '').strip()
        title = str(getattr(item, 'title', '') or '').strip()
        grandparent = str(getattr(item, 'grandparentTitle', '') or '').strip()
        parent = str(getattr(item, 'parentTitle', '') or '').strip()
        duration = getattr(item, 'duration', None)
        last_viewed = getattr(item, 'viewedAt', None) or getattr(item, 'lastViewedAt', None)
        view_offset = getattr(item, 'viewOffset', None)
        view_count = getattr(item, 'viewCount', None)

        if not title or not last_viewed:
            continue

        if isinstance(last_viewed, datetime):
            played_at = last_viewed.replace(tzinfo=None)
        else:
            try:
                played_at = datetime.fromisoformat(str(last_viewed).replace('Z', '+00:00'))
                played_at = played_at.replace(tzinfo=None)
            except Exception:
                continue

        entry = {
            'track_library_id': rating_key or None,
            'title': title,
            'artist': grandparent or None,
            'album': parent or None,
            'duration': int(duration) if duration else None,
            'played_at': played_at,
            'view_offset': int(view_offset) if view_offset else None,
            'view_count': int(view_count) if view_count else None,
        }
        entries_by_account.setdefault(item_account_id, []).append(entry)

    total_entries_fetched = sum(len(v) for v in entries_by_account.values())
    progress['entries_fetched'] = total_entries_fetched
    jobs.update_job_progress(job_id, {'progress': progress})

    stages['fetching_history'] = 'done'
    stages['storing_entries'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})

    all_library_ids = []
    for entries in entries_by_account.values():
        all_library_ids.extend([e['track_library_id'] for e in entries if e.get('track_library_id')])

    hifi_lookup = {}
    duration_lookup = {}
    if all_library_ids:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT library_id, hifi_id, duration FROM tracks WHERE library_id = ANY(%s)",
            (list(set(all_library_ids)),)
        )
        for row in cur.fetchall():
            lib_id = str(row['library_id'])
            if row.get('hifi_id'):
                hifi_lookup[lib_id] = str(row['hifi_id'])
            if row.get('duration'):
                duration_lookup[lib_id] = int(row['duration'])
        conn.close()

    total_entries_stored = 0
    global_max_played = None

    for account_id, entries in entries_by_account.items():
        _raise_if_job_cancelled(job_id)

        for e in entries:
            if e['track_library_id']:
                e['hifi_id'] = hifi_lookup.get(e['track_library_id'])
                if e['duration'] is None:
                    e['duration'] = duration_lookup.get(e['track_library_id'])

        users_for_account = account_id_to_users.get(account_id, [])
        for user_info in users_for_account:
            stored = upsert_listen_history_entries(entries, account_id, user_info['username'])
            total_entries_stored += stored

            if entries:
                max_played = max(e['played_at'] for e in entries)
                set_listen_history_sync_status(account_id, max_played, 'success')
                if global_max_played is None or max_played > global_max_played:
                    global_max_played = max_played

        progress['users_processed'] += len(users_for_account)
        progress['entries_stored'] = total_entries_stored
        jobs.update_job_progress(job_id, {'progress': progress})

    set_listen_history_sync_status(0, global_max_played or datetime.utcnow(), 'success')

    stages['fetching_history'] = 'done'
    stages['storing_entries'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    return {
        'trigger': payload.get('trigger') if isinstance(payload, dict) else 'unknown',
        'stages': stages,
        'progress': progress,
        'total_entries_fetched': total_entries_fetched,
        'total_entries_stored': total_entries_stored
    }

