"""Plex_Sync job processor."""

import concurrent.futures
import logging
import os
from datetime import datetime
logger = logging.getLogger(__name__)

from plexapi.server import PlexServer
from squidly import jobs
from squidly.db import get_db_connection
from squidly.jobs.workers import _raise_if_job_cancelled
from squidly.services.matching import (
    _get_artist_row,
    _get_album_row,
    _get_track_row_by_path,
    _upsert_artist_row,
    _upsert_album_row,
    _upsert_track_row,
)
from squidly.plex import _plex_call_with_timeout, plex_healthcheck, get_plex_config
from squidly.services.tag_reader import _resolve_library_file_path
from squidly.utils import _safe_int, _safe_float, _now_utc, _normalize_library_track_path, _extract_plex_library_id, _read_embedded_hifi_ids

def process_plex_sync_job(job_id, payload):
    config = get_plex_config()
    server_url = (config.get('server_url') or '').strip()
    api_token = (config.get('api_token') or '').strip()
    library_name = (config.get('library_name') or 'Music').strip()

    if not server_url or not api_token:
        raise ValueError('Plex server_url and api_token must be configured before syncing')

    stages = {
        'reading_plex_library': 'in_progress',
        'updating_local_index': 'pending',
        'labeling_explicit_albums': 'pending',
        'backfilling_track_ids_from_tags': 'pending',
    }
    progress = {
        'processed_tracks': 0,
        'total_tracks': 0,
        'upserted_songs': 0,
        'deleted_songs': 0,
        'explicit_albums_labeled': 0,
        'tags_read': 0,
        'tags_updated': 0,
    }
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    logger.info("[PLEX_SYNC] Job %s connecting to Plex at %s", job_id, server_url)
    plex = PlexServer(server_url.rstrip('/'), api_token, timeout=20)
    jobs.update_job_progress(job_id, {'stages': stages})

    library = None
    sections = _plex_call_with_timeout(plex.library.sections, timeout=30, label="library.sections")
    for section in sections:
        _raise_if_job_cancelled(job_id)
        if section.title == library_name and section.type == 'artist':
            library = section
            break

    if not library:
        raise ValueError(f'Plex music library "{library_name}" not found')

    logger.info("[PLEX_SYNC] Job %s fetching tracks from library '%s'", job_id, library_name)
    tracks = []
    try:
        _raise_if_job_cancelled(job_id)
        tracks = _plex_call_with_timeout(library.all, libtype='track', timeout=120, label="library.all")
    except Exception:
        _raise_if_job_cancelled(job_id)
        tracks = _plex_call_with_timeout(library.search, libtype='track', timeout=120, label="library.search")

    progress['total_tracks'] = len(tracks)
    stages['reading_plex_library'] = 'done'
    stages['updating_local_index'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    conn = get_db_connection()
    cur = conn.cursor()
    now_dt = _now_utc()
    now = now_dt.isoformat() + 'Z'
    seen_paths = set()
    explicit_album_keys = set()
    upserted = 0

    for idx, track in enumerate(tracks, start=1):
        title = getattr(track, 'title', None) or 'Unknown Title'
        artist = getattr(track, 'grandparentTitle', None) or None
        album = getattr(track, 'parentTitle', None) or None
        rating_key = str(getattr(track, 'ratingKey', None) or '').strip() or None
        album_key = _extract_plex_library_id(getattr(track, 'parentRatingKey', None) or getattr(track, 'parentKey', None))
        artist_key = _extract_plex_library_id(getattr(track, 'grandparentRatingKey', None) or getattr(track, 'grandparentKey', None))
        disc_number = _safe_int(getattr(track, 'parentIndex', None))
        track_number = _safe_int(getattr(track, 'trackNumber', None))

        # Track albums with [Explicit] in the name for later labeling
        if album_key and album and '[Explicit]' in album:
            explicit_album_keys.add(album_key)

        media_list = getattr(track, 'media', None) or []
        for media in media_list:
            parts = getattr(media, 'parts', None) or []
            bitrate = _safe_int(getattr(media, 'bitrate', None))
            media_format = (getattr(media, 'container', None) or '').strip().lower() or None

            for part in parts:
                file_path = (getattr(part, 'file', None) or '').strip()
                if not file_path:
                    continue

                if not media_format:
                    _, ext = os.path.splitext(file_path)
                    media_format = ext.replace('.', '').lower() if ext else None

                seen_paths.add(file_path)
                upserted += 1

                relative_path = _normalize_library_track_path(file_path)
                existing_track_row = _get_track_row_by_path(cur, relative_path) if relative_path else None

                album_artist_row = None
                album_row = None
                if existing_track_row and existing_track_row.get('album_id'):
                    album_row = _get_album_row(cur, existing_track_row['album_id'])
                if album_row and album_row.get('artist_id'):
                    album_artist_row = _get_artist_row(cur, album_row['artist_id'])

                if album_artist_row:
                    album_artist_row_id = _upsert_artist_row(
                        cur,
                        name=artist or 'Unknown Artist',
                        library_id=artist_key,
                        hifi_id=album_artist_row.get('hifi_id'),
                        confidence=_safe_float(album_artist_row.get('confidence')),
                        last_seen_at=now_dt,
                    )
                else:
                    album_artist_row_id = _upsert_artist_row(
                        cur,
                        name=artist or 'Unknown Artist',
                        library_id=artist_key,
                        confidence=0.0,
                        last_seen_at=now_dt,
                    )

                track_artist_row_id = album_artist_row_id
                if existing_track_row and existing_track_row.get('artist_id') and existing_track_row.get('artist_id') != album_artist_row_id:
                    track_artist_row = _get_artist_row(cur, existing_track_row['artist_id'])
                    if track_artist_row:
                        track_artist_row_id = _upsert_artist_row(
                            cur,
                            name=artist or 'Unknown Artist',
                            library_id=track_artist_row.get('library_id'),
                            hifi_id=track_artist_row.get('hifi_id'),
                            confidence=_safe_float(track_artist_row.get('confidence')),
                            last_seen_at=now_dt,
                        )

                existing_album_hifi_id = album_row.get('hifi_id') if album_row else None
                existing_album_confidence = _safe_float(album_row.get('confidence')) if album_row else 0.0
                existing_album_complete = album_row.get('complete') if album_row else False
                existing_album_matched_track_count = album_row.get('matched_track_count') if album_row else 0
                existing_album_expected_track_count = album_row.get('expected_track_count') if album_row else 0

                album_row_id = _upsert_album_row(
                    cur,
                    artist_id=album_artist_row_id,
                    title=album or 'Unknown Album',
                    library_id=album_key,
                    hifi_id=existing_album_hifi_id,
                    confidence=existing_album_confidence,
                    complete=existing_album_complete,
                    last_seen_at=now_dt,
                    matched_track_count=existing_album_matched_track_count,
                    expected_track_count=existing_album_expected_track_count,
                )

                existing_track_hifi_id = existing_track_row.get('hifi_id') if existing_track_row else None
                existing_track_confidence = _safe_float(existing_track_row.get('confidence')) if existing_track_row else 0.0

                track_duration = getattr(track, 'duration', None)
                try:
                    track_duration = int(track_duration) if track_duration is not None else None
                except Exception:
                    track_duration = None

                _upsert_track_row(
                    cur,
                    album_id=album_row_id,
                    artist_id=track_artist_row_id,
                    title=title,
                    path=relative_path or file_path.replace('\\', '/').lstrip('/'),
                    library_id=rating_key,
                    hifi_id=existing_track_hifi_id,
                    confidence=existing_track_confidence,
                    last_seen_at=now_dt,
                    audio_format=media_format,
                    bitrate=bitrate,
                    disc_number=disc_number,
                    track_number=track_number,
                    duration=track_duration,
                )

        progress['processed_tracks'] = idx
        progress['upserted_songs'] = upserted
        if idx % 25 == 0 or idx == len(tracks):
            jobs.update_job_progress(job_id, {'progress': progress})

    conn.commit()
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    deleted = 0
    if seen_paths:
        cur.execute(
            """
            DELETE FROM tracks
            WHERE library_id IS NOT NULL
              AND last_seen_at < %s
            """,
            (now_dt,)
        )
        deleted = cur.rowcount or 0
        cur.execute(
            """
            DELETE FROM albums AS albums_to_delete
            WHERE albums_to_delete.library_id IS NOT NULL
              AND albums_to_delete.last_seen_at < %s
              AND NOT EXISTS (
                    SELECT 1
                    FROM tracks
                    WHERE tracks.album_id = albums_to_delete.album_id
                )
            """,
            (now_dt,)
        )
        cur.execute(
            """
            DELETE FROM artists AS artists_to_delete
            WHERE artists_to_delete.library_id IS NOT NULL
              AND artists_to_delete.last_seen_at < %s
              AND NOT EXISTS (
                    SELECT 1
                    FROM albums
                    WHERE albums.artist_id = artists_to_delete.artist_id
                )
              AND NOT EXISTS (
                    SELECT 1
                    FROM tracks
                    WHERE tracks.artist_id = artists_to_delete.artist_id
                )
            """,
            (now_dt,)
        )

        # Clean up download-only orphan tracks that now have a Plex duplicate
        # (same path, different casing, but one has library_id after this sync)
        cur.execute(
            """
            DELETE FROM tracks
            WHERE library_id IS NULL
              AND EXISTS (
                    SELECT 1
                    FROM tracks t2
                    WHERE t2.track_id != tracks.track_id
                      AND t2.library_id IS NOT NULL
                      AND LOWER(t2.path) = LOWER(tracks.path)
                )
            """
        )
        merged = cur.rowcount or 0

    conn.commit()

    if merged:
        logger.info("[PLEX_SYNC] Job %s: Merged %s orphan download tracks into Plex entries", job_id, merged)

    # Add "Explicit" label to albums that contain [Explicit] in their name
    # (explicit_album_keys was populated during the track processing loop above)

    progress['deleted_songs'] = deleted
    stages['updating_local_index'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['labeling_explicit_albums'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    labeled_count = 0
    if explicit_album_keys:
        logger.info("[PLEX_SYNC] Job %s: Adding 'Explicit' label to %s albums", job_id, len(explicit_album_keys))
        for album_key in explicit_album_keys:
            try:
                # album_key format is /library/metadata/ID, extract the ID
                album_id = int(album_key.split('/')[-1])
                album = plex.fetchItem(album_id)
                if album and hasattr(album, 'addLabel'):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(album.addLabel, 'Explicit')
                        future.result(timeout=10)
                    labeled_count += 1
                    logger.info("[PLEX_SYNC] Job %s: Added 'Explicit' label to album %s", job_id, album_key)
            except concurrent.futures.TimeoutError:
                logger.info("[PLEX_SYNC] Job %s: Timed out adding label to album %s", job_id, album_key)
                continue
            except Exception as e:
                logger.info("[PLEX_SYNC] Job %s: Failed to add 'Explicit' label to album %s: %s", job_id, album_key, str(e))
                continue
        logger.info("[PLEX_SYNC] Job %s: Successfully labeled %s albums as Explicit", job_id, labeled_count)

    progress['explicit_albums_labeled'] = labeled_count
    stages['labeling_explicit_albums'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    stages['backfilling_track_ids_from_tags'] = 'in_progress'
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    cur.execute(
        """
        SELECT tracks.track_id, tracks.album_id, tracks.path, tracks.hifi_id, tracks.isrc,
               albums.hifi_id AS album_hifi_id
        FROM tracks
        LEFT JOIN albums ON albums.album_id = tracks.album_id
        WHERE tracks.library_id IS NOT NULL
          AND (
                tracks.hifi_id IS NULL
             OR tracks.isrc IS NULL
             OR albums.hifi_id IS NULL
          )
        ORDER BY tracks.track_id ASC
        """
    )
    tag_rows = cur.fetchall() or []
    tags_read = 0
    tags_updated = 0
    albums_backfilled = set()

    for tag_row in tag_rows:
        _raise_if_job_cancelled(job_id)
        file_path = str(tag_row.get('path') or '').strip()
        if not file_path:
            continue

        embedded = _read_embedded_hifi_ids(file_path)
        embedded_track_id = str(embedded.get('track_id') or '').strip() or None
        embedded_album_id = str(embedded.get('album_id') or '').strip() or None
        embedded_isrc = str(embedded.get('isrc') or '').strip() or None

        if not embedded_track_id and not embedded_album_id and not embedded_isrc:
            continue

        tags_read += 1
        update_fields = []
        update_values = []

        if embedded_track_id and not tag_row.get('hifi_id'):
            update_fields.append('hifi_id = %s')
            update_values.append(embedded_track_id)
            update_fields.append('confidence = 0.99')

        if embedded_isrc and not tag_row.get('isrc'):
            update_fields.append('isrc = %s')
            update_values.append(embedded_isrc)

        if update_fields:
            update_values.append(tag_row['track_id'])
            cur.execute(
                f"UPDATE tracks SET {', '.join(update_fields)} WHERE track_id = %s",
                update_values
            )
            tags_updated += 1

        if embedded_album_id and not tag_row.get('album_hifi_id'):
            album_id_val = int(tag_row.get('album_id') or 0)
            if album_id_val and album_id_val not in albums_backfilled:
                cur.execute(
                    "UPDATE albums SET hifi_id = %s, confidence = 0.99 WHERE album_id = %s AND (hifi_id IS NULL OR hifi_id = '')",
                    (embedded_album_id, album_id_val)
                )
                albums_backfilled.add(album_id_val)

        if tags_read % 50 == 0 or tags_read == len(tag_rows):
            conn.commit()
            progress['tags_read'] = tags_read
            progress['tags_updated'] = tags_updated
            jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})
            logger.info("[PLEX_SYNC] Job %s: Tag backfill progress: read=%s, updated=%s, albums_backfilled=%s", job_id, tags_read, tags_updated, len(albums_backfilled))

    conn.commit()
    logger.info("[PLEX_SYNC] Job %s: Tag backfill complete: read=%s, updated=%s, albums_backfilled=%s", job_id, tags_read, tags_updated, len(albums_backfilled))

    stages['backfilling_track_ids_from_tags'] = 'done'
    progress['tags_read'] = tags_read
    progress['tags_updated'] = tags_updated
    jobs.update_job_progress(job_id, {'stages': stages, 'progress': progress})

    trigger = payload.get('trigger') if isinstance(payload, dict) else None
    logger.info("[PLEX_SYNC] Job %s finished. tracks=%s upserted=%s deleted=%s explicit_albums_labeled=%s tags_read=%s tags_updated=%s", job_id, progress['total_tracks'], upserted, deleted, labeled_count, tags_read, tags_updated)

    return {
        'trigger': trigger or 'unknown',
        'stages': stages,
        'progress': progress,
        'total_tracks': progress['total_tracks'],
        'upserted_songs': upserted,
        'deleted_songs': deleted,
        'explicit_albums_labeled': labeled_count,
        'tags_read': tags_read,
        'tags_updated': tags_updated,
    }

