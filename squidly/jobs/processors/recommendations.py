"""Recommendations job processor."""

import logging
from datetime import datetime
logger = logging.getLogger(__name__)

from squidly.infrastructure import downloads
from squidly import jobs
from squidly.infrastructure.config import DEFAULT_DOWNLOAD_SETTINGS, app_timezone
from squidly.infrastructure.db import get_db_connection
from squidly.infrastructure.job_queue import enqueue_job
from squidly.jobs.orchestration import is_job_type_running_or_queued
from squidly.jobs.orchestration import queue_plex_listen_history_sync
from squidly.jobs.orchestration import queue_recommendation_generation
from squidly.jobs.workers import _raise_if_job_cancelled
from squidly.services.hifi import _get_hifi_audio_quality_rank
from squidly.infrastructure.storage import get_download_settings
from squidly.infrastructure.storage import get_fresh_finds_auto_download_users
from squidly.infrastructure.storage import (
    get_recommendation_playlist, get_todays_recommendation_playlist,
    get_random_listen_history_seeds,
    get_fresh_finds_track_count, get_fresh_finds_history_days,
    get_existing_fresh_finds_isrcs,
)
from squidly.infrastructure.storage import save_recommendation_playlist
from zoneinfo import ZoneInfo

def process_recommendation_job(job_id, payload):
    from urllib.parse import urlencode

    stages = {
        'syncing_listen_history': 'pending',
        'gathering_seeds': 'pending',
        'fetching_recommendations': 'pending',
        'processing_tracks': 'pending',
        'saving_playlist': 'pending'
    }
    progress = {
        'seeds_found': 0,
        'recommendations_fetched': 0,
        'tracks_after_filter': 0,
        'tracks_saved': 0
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    plex_account_id = payload.get('plex_account_id')
    plex_username = payload.get('plex_username', 'Unknown')
    slug = payload.get('slug', 'fresh-finds')
    trigger = payload.get('trigger', 'manual')

    if plex_account_id is None:
        raise ValueError('plex_account_id is required in payload')

    # Stage 1: Sync listen history
    stages['syncing_listen_history'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s syncing listen history for %s", job_id, plex_username)

    sync_job_id = queue_plex_listen_history_sync('recommendation')
    if sync_job_id:
        from squidly.jobs.orchestration import wait_for_job_type
        wait_for_job_type('plex_listen_history_sync', timeout=120, poll_interval=2, check_cancelled_job_id=job_id)

    stages['syncing_listen_history'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 2: Gather seeds — random from configurable time window
    stages['gathering_seeds'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s gathering seeds for %s", job_id, plex_username)

    track_count = get_fresh_finds_track_count(plex_account_id)
    history_days = get_fresh_finds_history_days(plex_account_id)

    seeds = get_random_listen_history_seeds(plex_account_id, limit=track_count, days=history_days)
    progress['seeds_found'] = len(seeds)
    jobs.update_job_progress(job_id, {'progress': progress})

    if not seeds:
        raise ValueError(f'No listen history seeds found for user {plex_username} (last {history_days} days)')

    stages['gathering_seeds'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 3: Fetch recommendations
    stages['fetching_recommendations'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s fetching recommendations for %d seeds", job_id, len(seeds))

    raw_recommendations = []
    for seed in seeds:
        _raise_if_job_cancelled(job_id)
        hifi_id = seed['hifi_id']
        try:
            response, target = downloads.make_request_with_retry_rotating_mirrors(
                f"/recommendations/?{urlencode({'id': hifi_id})}",
                downloads.get_squid_urls(),
                method='GET',
                timeout=10,
                max_retries=2
            )
            if response.ok:
                data = response.json()
                items = []
                if isinstance(data, dict):
                    data_items = data.get('data', {}).get('items') or data.get('items') or []
                    items = data_items if isinstance(data_items, list) else []
                for item in items:
                    track = item.get('track') or item.get('item') or item
                    if isinstance(track, dict) and track.get('id') and track.get('title'):
                        artists = track.get('artists') or []
                        primary_artist = artists[0] if isinstance(artists, list) and len(artists) > 0 else {}
                        album = track.get('album') if isinstance(track.get('album'), dict) else {}
                        raw_recommendations.append({
                            'hifi_id': int(track['id']),
                            'title': track['title'],
                            'artist': primary_artist.get('name') if isinstance(primary_artist, dict) else '',
                            'artist_id': primary_artist.get('id') if isinstance(primary_artist, dict) else None,
                            'album': album.get('title') if isinstance(album, dict) else '',
                            'album_id': album.get('id') if isinstance(album, dict) else None,
                            'duration': track.get('duration'),
                            'cover': album.get('cover') if isinstance(album, dict) else track.get('cover'),
                            'quality': track.get('maxAudioQuality') or track.get('audioQuality') or '',
                            'seed_hifi_id': hifi_id,
                            'isrc': track.get('isrc'),
                        })
                progress['recommendations_fetched'] = len(raw_recommendations)
                jobs.update_job_progress(job_id, {'progress': progress})
        except Exception as e:
            logger.info("[RECOMMENDATION] Job %s failed to fetch recommendations for seed %s: %s", job_id, hifi_id, e)
            continue

    stages['fetching_recommendations'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 4: Process tracks
    stages['processing_tracks'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s processing %d raw recommendations", job_id, len(raw_recommendations))

    # Step 1: Deduplicate by ISRC, aggregate frequency score
    from squidly.infrastructure.utils import normalize_match_text

    deduped = {}
    for rec in raw_recommendations:
        key = str(rec.get('isrc') or '').strip().upper()
        if not key:
            key = normalize_match_text(rec.get('artist', '')) + '||' + normalize_match_text(rec.get('title', ''))
        if key not in deduped:
            deduped[key] = {**rec, 'score': 1}
        else:
            deduped[key]['score'] += 1

    # Step 2: Dedupe against existing Fresh Finds playlists (by ISRC)
    existing_ff_isrcs = get_existing_fresh_finds_isrcs(plex_account_id)
    before_ff_dedup = len(deduped)
    deduped = {
        key: rec for key, rec in deduped.items()
        if str(rec.get('isrc') or '').strip().upper() not in existing_ff_isrcs
    }
    logger.info("[RECOMMENDATION] Job %s: removed %d tracks already in existing FF playlists",
                job_id, before_ff_dedup - len(deduped))

    settings = get_download_settings()

    # Step 3: Quality filter
    min_quality = settings.get('quality', 'LOSSLESS')
    min_rank = _get_hifi_audio_quality_rank(min_quality)
    quality_filtered = []
    for rec in deduped.values():
        rec_rank = _get_hifi_audio_quality_rank(rec.get('quality', ''))
        if rec_rank >= min_rank:
            quality_filtered.append(rec)
    progress['tracks_after_quality_filter'] = len(quality_filtered)
    jobs.update_job_progress(job_id, {'progress': progress})

    # Step 4: Exclude tracks recently played by this user (30 days, hardcoded)
    from squidly.infrastructure.storage import get_recently_played_isrcs
    recently_played_isrcs = get_recently_played_isrcs(plex_account_id, days=30)
    quality_filtered = [
        rec for rec in quality_filtered
        if str(rec.get('isrc') or '').strip().upper() not in recently_played_isrcs
    ]

    # Step 5: Classify into NEW or LIBRARY candidate pools
    from squidly.infrastructure.storage import get_existing_isrcs, get_existing_artist_titles
    existing_isrcs = get_existing_isrcs()
    existing_artist_titles = get_existing_artist_titles()
    library_candidates = []
    new_candidates = []

    for rec in quality_filtered:
        rec_isrc = str(rec.get('isrc') or '').strip().upper()
        is_library_track = False

        if rec_isrc and rec_isrc in existing_isrcs:
            is_library_track = True
        elif not rec_isrc:
            at = (
                normalize_match_text(rec.get('artist', '')),
                normalize_match_text(rec.get('title', ''), strip_trailing_parenthetical=True)
            )
            if at in existing_artist_titles:
                is_library_track = True

        if is_library_track:
            library_candidates.append(rec)
        else:
            new_candidates.append(rec)

    # Step 6: Sort both pools and calculate distribution
    new_candidates.sort(key=lambda x: x['score'], reverse=True)
    library_candidates.sort(key=lambda x: x['score'], reverse=True)

    from squidly.infrastructure.storage import get_fresh_finds_new_track_pct
    new_track_pct = get_fresh_finds_new_track_pct(plex_account_id)
    n_new = round(track_count * new_track_pct / 100)
    n_library = track_count - n_new

    selected_new = new_candidates[:n_new]
    selected_library = library_candidates[:n_library]

    # Handle overflow: if one pool is too short, fill from the other
    if len(selected_new) < n_new and len(library_candidates) > n_library:
        extra = n_new - len(selected_new)
        selected_library = library_candidates[:n_library + extra]
    elif len(selected_library) < n_library and len(new_candidates) > n_new:
        extra = n_library - len(selected_library)
        selected_new = new_candidates[:n_new + extra]

    progress['tracks_new_candidates'] = len(new_candidates)
    progress['tracks_library_candidates'] = len(library_candidates)
    progress['tracks_selected_new'] = len(selected_new)
    progress['tracks_selected_library'] = len(selected_library)
    jobs.update_job_progress(job_id, {'progress': progress})

    # Step 7: Resolve library picks to local library instance
    from squidly.infrastructure.storage import get_local_track_by_isrc

    for rec in selected_library:
        rec_isrc = str(rec.get('isrc') or '').strip().upper()
        if rec_isrc:
            local = get_local_track_by_isrc(rec_isrc)
            if local:
                rec['library_id'] = local['library_id']
                rec['hifi_id'] = local['hifi_id']

    # Step 8: Combine — new tracks first, then library tracks
    top_tracks = selected_new + selected_library
    top_tracks = top_tracks[:track_count]

    progress['tracks_after_filter'] = len(top_tracks)
    progress['tracks_saved'] = len(top_tracks)
    jobs.update_job_progress(job_id, {'progress': progress})

    # Step 9: Track resolution — only on final selected tracks
    from squidly.services.track_resolver import resolve_track
    from squidly.services.hifi import _fetch_hifi_track_info_payload, extract_hifi_track_info
    resolved_count = 0
    for rec in top_tracks:
        tid = rec.get('hifi_id')
        if not tid:
            continue
        try:
            result = resolve_track(
                title=rec.get('title', ''),
                track_artist=rec.get('artist', ''),
                album=rec.get('album', ''),
                isrc=rec.get('isrc'),
                hifi_id=str(tid),
                settings=settings,
            )
            new_id = result.get('hifi_id')
            if new_id and str(new_id) != str(tid):
                rec['hifi_id'] = int(new_id)
                # Refresh metadata to match the resolved track
                raw = _fetch_hifi_track_info_payload(str(new_id))
                if raw:
                    info = extract_hifi_track_info(raw)
                    if info.get('title'):
                        rec['title'] = info['title']
                    if info.get('track_artists'):
                        first_artist = info['track_artists'][0] if info['track_artists'] else {}
                        rec['artist'] = first_artist.get('name', '') if first_artist else rec.get('artist', '')
                        if first_artist.get('id') is not None:
                            rec['artist_id'] = first_artist['id']
                    if info.get('album'):
                        rec['album'] = info['album']
                    if info.get('album_id'):
                        rec['album_id'] = info['album_id']
                    if info.get('duration'):
                        rec['duration'] = info['duration']
                    if info.get('cover'):
                        rec['cover'] = info['cover']
                    if info.get('isrc'):
                        rec['isrc'] = info['isrc']
                    if info.get('audioQuality'):
                        rec['quality'] = info['audioQuality']
                resolved_count += 1
                logger.info("[RECOMMENDATION] Resolved track %s (%s, source=%s) -> %s",
                            tid, result['reason'], result['source'], new_id)
        except Exception as e:
            logger.warning("[RECOMMENDATION] Failed to resolve track %s: %s", tid, e)
    progress['tracks_resolved'] = resolved_count
    jobs.update_job_progress(job_id, {'progress': {**progress, 'tracks_resolved': resolved_count}})

    stages['processing_tracks'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    # Stage 5: Save playlist
    stages['saving_playlist'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages})
    logger.info("[RECOMMENDATION] Job %s saving %d tracks for %s", job_id, len(top_tracks), plex_username)

    from squidly.infrastructure.config import app_timezone
    from zoneinfo import ZoneInfo
    now_tz = datetime.now(ZoneInfo(app_timezone))
    playlist_name = f"Fresh Finds ({now_tz.strftime('%-m')}-{now_tz.strftime('%-d')})"

    playlist_id = save_recommendation_playlist(
        plex_account_id=plex_account_id,
        slug=slug,
        name=playlist_name,
        strategy='fresh-finds',
        seed_count=len(seeds),
        tracks=top_tracks
    )

    # Stage 6: Cleanup old Fresh Finds playlists
    from squidly.infrastructure.storage import cleanup_old_fresh_finds
    try:
        cleanup_result = cleanup_old_fresh_finds(plex_account_id)
        logger.info(
            "[RECOMMENDATION] Job %s cleanup: deleted %d old DB playlists, %d Plex playlists",
            job_id, cleanup_result.get('deleted_count', 0), cleanup_result.get('plex_deleted', 0)
        )
    except Exception as e:
        logger.info("[RECOMMENDATION] Job %s cleanup failed (non-fatal): %s", job_id, str(e))

    progress['tracks_saved'] = len(top_tracks)
    stages['saving_playlist'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    return {
        'stages': stages,
        'progress': progress,
        'trigger': trigger,
        'plex_username': plex_username,
    }


def process_fresh_finds_auto_download_job(job_id, payload):
    """Process a fresh_finds_auto_download job: read the playlist for each enabled user and queue download_track jobs."""
    from squidly.infrastructure.storage import get_recommendation_playlist, get_download_settings, get_fresh_finds_auto_download_users
    from squidly.jobs.orchestration import is_job_type_running_or_queued
    from squidly.infrastructure.job_queue import enqueue_job, RetryableError

    slug = payload.get('slug', 'fresh-finds')

    # If generate_recommendations jobs are still running, retry later.
    # The scheduler queues this job alongside recommendation jobs, so we need
    # to wait for them to finish before reading the playlists.
    if is_job_type_running_or_queued('generate_recommendations'):
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: generate_recommendations still running, retrying later", job_id)
        raise RetryableError("generate_recommendations jobs still in progress")

    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s processing for all enabled users", job_id)

    # Get all users with auto-download enabled
    auto_download_users = get_fresh_finds_auto_download_users()

    if not auto_download_users:
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: no users with auto-download enabled", job_id)
        return {'tracks_queued': 0, 'reason': 'no_users'}

    # Get global download settings for quality and naming
    settings = get_download_settings()
    quality = settings.get('quality', 'LOSSLESS')
    file_naming = settings.get('file_naming_album', '{artist}/{album}/{track} - {title}.{ext}')
    file_naming_album = settings.get('file_naming_album', '{artist}/{album}/{track} - {title}.{ext}')

    total_tracks_queued = 0
    users_processed = []

    for user in auto_download_users:
        plex_account_id = user.get('plex_account_id')
        plex_username = user.get('username', 'Unknown')

        if plex_account_id is None:
            continue

        # Read the Fresh Finds playlist for this user
        playlist = get_todays_recommendation_playlist(plex_account_id, slug)

        if not playlist:
            logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: no playlist found for user %s (account %s)", job_id, plex_username, plex_account_id)
            continue

        tracks = playlist.get('tracks', [])
        playlist_name = playlist.get('name', 'Fresh Finds')

        if not tracks:
            logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: empty playlist for user %s (account %s)", job_id, plex_username, plex_account_id)
            continue

        # Queue a download_track job for each track
        tracks_queued = 0
        for track in tracks:
            hifi_id = track.get('hifi_id')
            if not hifi_id:
                continue

            plex_client_id = user.get('plex_client_id')
            job_payload = {
                'trackId': hifi_id,
                'fileNaming': file_naming,
                'fileNamingAlbum': file_naming_album,
                'plex_playlist': playlist_name,
                'plex_user_id': plex_client_id if plex_client_id is not None else plex_account_id,
                'downloadQuality': quality,
            }

            artist = track.get('artist')
            title = track.get('title')
            if artist:
                job_payload['artist'] = artist
            if title:
                job_payload['title'] = title

            try:
                download_job_id = enqueue_job('download_track', job_payload)
                if download_job_id:
                    tracks_queued += 1
                    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued download_track %s for track %s - %s (user: %s)",
                                job_id, download_job_id, artist or 'Unknown', title or str(hifi_id), plex_username)
            except Exception as e:
                logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: failed to queue download for track %s: %s",
                            job_id, hifi_id, str(e))

        total_tracks_queued += tracks_queued
        users_processed.append(plex_username)
        logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued %d/%d tracks for %s",
                    job_id, tracks_queued, len(tracks), plex_username)

    logger.info("[FRESH_FINDS_AUTO_DOWNLOAD] Job %s: queued %d total tracks for %d users (%s)",
                job_id, total_tracks_queued, len(users_processed), ', '.join(users_processed))

    return {
        'tracks_queued': total_tracks_queued,
        'users_processed': users_processed,
    }


