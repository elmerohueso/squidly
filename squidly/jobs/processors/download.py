"""Download job processor."""

import logging
import os
import shutil
from datetime import datetime
import requests
logger = logging.getLogger(__name__)

from squidly.infrastructure import downloads
from squidly import jobs
from squidly.services import deezer
from squidly.services import deezer_mirror
from squidly.services import qobuz
from squidly.services import hifi
from squidly.infrastructure.config import DEFAULT_DOWNLOAD_SETTINGS
from squidly.infrastructure.config import DOWNLOADS_ROOT
from squidly.infrastructure.db import get_db_connection
from squidly.jobs.orchestration import queue_pending_playlist_addition
from squidly.jobs.workers import _raise_if_job_cancelled
from squidly.services.matching import upsert_download_match_hint
from squidly.services.playlist_matching import _lookup_track_metadata
from squidly.infrastructure.plex import plex_healthcheck, get_plex_config
from squidly.services.hifi import get_hifi_track_object
from squidly.infrastructure.storage import get_download_settings, set_last_download_activity_at
from squidly.infrastructure.utils import (
    _safe_int,
    clean_path_components,
    extract_year_from_text,
    sanitize_filename_component,
)

_PERMANENT_ERROR_KEYWORDS = (
    'no configured mirror',
    'no qobuz mirrors available',
    'no deezer mirrors available',
    'no arl configured',
    'deezer requires isrc',
    'not found in qobuz catalog',
    'not found on deezer',
    'not available in flac on deezer',
)

_DOWNLOAD_SOURCE_HANDLERS = {
    'qobuz': qobuz.download_track_by_isrc,
    'deezer': deezer.download_track_by_isrc,
    'deezer_mirror': deezer_mirror.download_track_by_isrc,
    'tidal': hifi.download_track_by_isrc,
}


def _finalize_download(
    temp_path: str,
    source: str,
    expected_duration,
    expected_format: str = 'flac',
) -> str:
    """Detect format, log size, validate duration. Raise on format mismatch.

    Returns the detected audio format. Order: format check first (cheap),
    duration check second (expensive, runs ffmpeg).

    Raises:
        ValueError: detected format does not match expected_format.
        ValueError: file is suspiciously small (< 1KB) and unidentifiable.
        RuntimeError: duration validation fails (from validate_audio_duration).
    """
    file_size = 0
    try:
        file_size = os.path.getsize(temp_path)
    except OSError:
        pass

    with open(temp_path, 'rb') as tmp_file:
        audio_format = downloads.detect_audio_format(tmp_file.read(32))

    if audio_format == 'unknown':
        if file_size < 1024:
            raise ValueError(
                f"Expected {expected_format} format from {source}, but file is "
                f"suspiciously small ({file_size} bytes) and unidentifiable"
            )
        logger.warning(
            "[DOWNLOAD] Could not detect format of %d-byte file from %s, "
            "assuming %s",
            file_size, source, expected_format,
        )
        audio_format = expected_format

    try:
        temp_size = file_size if file_size else os.path.getsize(temp_path)
        logger.info(
            "[DOWNLOAD] %s temp file: %d bytes, format=%s (%s)",
            source, temp_size, audio_format, temp_path,
        )
    except OSError:
        pass

    if audio_format != expected_format:
        raise ValueError(
            f"Expected {expected_format} format from {source}, but detected "
            f"{audio_format} ({file_size} bytes)"
        )

    downloads.validate_audio_duration(temp_path, expected_duration)

    return audio_format


def process_download_job(job_id, payload):
    track_id = payload.get('trackId')
    quality_choice = str(payload.get('downloadQuality', payload.get('quality'))).strip().upper()
    if quality_choice not in ('LOSSLESS', 'HIGH', 'LOW'):
        quality_choice = 'LOSSLESS'

    stages = {
        'downloaded': 'pending',
        'tagged': 'pending',
        'written': 'pending',
        'playlist_added': 'pending'
    }

    if not track_id:
        raise ValueError('trackId is required')

    logger.info("[DOWNLOAD] Fetching track metadata from normalized HiFi object for quality=%s", quality_choice)
    try:
        track_object = get_hifi_track_object(
            track_id,
            include_streams=False,
            include_album=True,
            audio_quality=quality_choice,
            mirror_type='tidal',
        )
    except Exception as e:
        raise downloads.TransientDownloadError(f"Failed to fetch download track object: {str(e)}") from e

    if not isinstance(track_object, dict):
        raise downloads.TransientDownloadError("Failed to build normalized track object")

    file_naming = payload.get('fileNaming')
    if not file_naming:
        file_naming = payload.get('fileNamingAlbum') or DEFAULT_DOWNLOAD_SETTINGS['file_naming_album']

    tag_settings = get_download_settings()

    download_source = tag_settings.get('download_source', 'tidal').lower()

    downloads_folder = DOWNLOADS_ROOT

    if not os.path.exists(downloads_folder):
        logger.warning("[DOWNLOAD] Downloads folder does not exist, creating it: %s", downloads_folder)
        os.makedirs(downloads_folder, exist_ok=True)

    track_data = track_object.get('track') if isinstance(track_object.get('track'), dict) else {}
    album_data = track_data.get('album') if isinstance(track_data.get('album'), dict) else {}

    # --- Extract metadata before downloading (needed for match check and file naming) ---

    track_artist_name = 'Unknown Artist'
    track_artist_id = None
    album_artist_name = None
    album_artist_id = None
    album_name = 'Unknown Album'
    track_title = 'Unknown Track'
    track_version = ''
    track_num = '01'
    disc_num = ''
    release_year = ''
    copyright_text = ''
    cover_url = ''
    album_id = ''
    album_disc_count = 1
    album_has_multiple_discs = False
    track_artists = []

    if isinstance(track_data, dict):
        if isinstance(track_data.get('artists'), list) and track_data['artists']:
            artist_names = [str(a.get('name', '')).strip() for a in track_data['artists'] if isinstance(a, dict) and a.get('name')]
            track_artist_name = '; '.join(artist_names) if artist_names else 'Unknown Artist'
            track_artists = artist_names
            first_artist = track_data['artists'][0] if isinstance(track_data['artists'][0], dict) else None
            if first_artist and first_artist.get('id') is not None:
                track_artist_id = str(first_artist.get('id')).strip() or None
        elif isinstance(track_data.get('artists'), dict):
            artist = track_data['artists']
            track_artist_name = str(artist.get('name', 'Unknown Artist'))
            if artist.get('name'):
                track_artists = [track_artist_name]
            if artist.get('id') is not None:
                track_artist_id = str(artist.get('id')).strip() or None

        track_title = str(track_data.get('title') or track_title)
        track_version = str(track_data.get('version') or '').strip()
        if track_data.get('explicit') and tag_settings.get('tag_explicit_suffix', True) and '[Explicit]' not in track_title:
            track_title += ' [Explicit]'
        if track_version:
            track_title = f"{track_title} ({track_version})"

        track_number = track_data.get('trackNumber')
        if track_number is not None:
            track_num = str(track_number).zfill(2)

        disc_value = track_data.get('discNumber')
        if disc_value is None:
            disc_value = track_data.get('volumeNumber')
        if disc_value is not None:
            try:
                parsed_disc_num = int(str(disc_value).strip())
                if parsed_disc_num > 0:
                    disc_num = str(parsed_disc_num)
            except (TypeError, ValueError):
                disc_num = ''

        if isinstance(track_data.get('copyright'), str) and track_data.get('copyright').strip():
            copyright_text = str(track_data.get('copyright')).strip()

    if isinstance(album_data, dict):
        album_name = str(album_data.get('title') or album_name)
        album_id = str(album_data.get('id')) if album_data.get('id') is not None else ''
        cover_url = str(album_data.get('cover') or '')
        if album_data.get('explicit') and tag_settings.get('tag_explicit_suffix', True) and '[Explicit]' not in album_name:
            album_name += ' [Explicit]'

        if isinstance(album_data.get('releaseDate'), str) and len(album_data.get('releaseDate')) >= 4:
            release_year = album_data.get('releaseDate')[:4]

        album_artists = []
        main_album_artist_name = None
        if isinstance(album_data.get('artists'), list):
            for artist in album_data['artists']:
                if isinstance(artist, dict) and artist.get('name'):
                    artist_name = str(artist.get('name')).strip()
                    album_artists.append(artist_name)
                    if main_album_artist_name is None and str(artist.get('type') or '').upper() == 'MAIN':
                        main_album_artist_name = artist_name
                    if album_artist_id is None and artist.get('id') is not None:
                        album_artist_id = str(artist.get('id')).strip() or None
        elif isinstance(album_data.get('artists'), dict):
            artist = album_data['artists']
            if isinstance(artist, dict) and artist.get('name'):
                artist_name = str(artist.get('name')).strip()
                album_artists.append(artist_name)
                if str(artist.get('type') or '').upper() == 'MAIN':
                    main_album_artist_name = artist_name
                if artist.get('id') is not None:
                    album_artist_id = str(artist.get('id')).strip() or None

        if main_album_artist_name:
            album_artist_name = main_album_artist_name
        elif album_artists:
            album_artist_name = album_artists[0]

        try:
            album_disc_count = int(album_data.get('numberOfDiscs') or album_data.get('numberOfVolumes') or 1)
        except (TypeError, ValueError):
            album_disc_count = 1
        album_has_multiple_discs = album_disc_count > 1

    if not release_year and copyright_text:
        release_year = extract_year_from_text(copyright_text)

    if not cover_url and album_id:
        cover_url = downloads.format_tidal_image_url(str(album_id), 1280)

    if not album_artist_name:
        album_artist_name = track_artist_name

    artist_name = track_artist_name
    effective_artist_name = album_artist_name or track_artist_name

    logger.info("[DOWNLOAD] Extracted metadata: TrackArtist='%s', AlbumArtist='%s', EffectiveArtistForPath='%s', Album='%s', Title='%s', TrackNum='%s', DiscNum='%s', Year='%s', Cover='%s'", track_artist_name, album_artist_name or '', effective_artist_name, album_name, track_title, track_num, disc_num, release_year, cover_url)

    # --- Compute file path (shared by both match-found and download branches) ---

    file_ext = 'flac'

    safe_artist = sanitize_filename_component(effective_artist_name)
    safe_album = sanitize_filename_component(album_name)
    safe_title = sanitize_filename_component(track_title)
    safe_track = sanitize_filename_component(track_num)

    if album_has_multiple_discs and disc_num:
        prefixed_track = f"{disc_num}-{safe_track}"
        safe_track = sanitize_filename_component(prefixed_track)

    file_path = file_naming.replace('{artist}', safe_artist)
    file_path = file_path.replace('{album}', safe_album)
    file_path = file_path.replace('{track}', safe_track)
    file_path = file_path.replace('{title}', safe_title)
    file_path = file_path.replace('{ext}', file_ext)
    file_path = clean_path_components(file_path)

    # --- Check for existing matches before downloading ---

    conn = get_db_connection()
    cur = conn.cursor()
    metadata_rows = _lookup_track_metadata(cur, track_title, artist_name, album_name)
    conn.close()

    ignore_matches = bool(payload.get('ignore_matches', False))
    matching_rows = []
    if not ignore_matches:
        matching_rows = list(metadata_rows)

    summary_rows = [
        {
            'format': str(row.get('format') or '').strip().lower() or 'unknown',
            'bitrate': row.get('bitrate'),
            'album': row.get('album')
        }
        for row in metadata_rows[:8]
    ]
    logger.info("[DOWNLOAD_DECISION] Job %s: metadata_candidates=%s, matching_selected_format=%s, candidate_summary=%s", job_id, len(metadata_rows), len(matching_rows), summary_rows)
    if matching_rows:
        matched_row = matching_rows[0]
        matched_path = str(matched_row.get('path') or '').strip()
        matched_path = os.path.join(downloads_folder, matched_path) if matched_path else ''

        file_ext = matched_row.get('format', 'flac')
        file_path = file_naming.replace('{artist}', safe_artist)
        file_path = file_path.replace('{album}', safe_album)
        file_path = file_path.replace('{track}', safe_track)
        file_path = file_path.replace('{title}', safe_title)
        file_path = file_path.replace('{ext}', file_ext)
        file_path = clean_path_components(file_path)

        full_path = matched_path if matched_path else os.path.join(downloads_folder, file_path)
        full_path = os.path.normpath(full_path)

        logger.info("[DOWNLOAD_DECISION] Job %s: skipping download because existing Plex inventory metadata matches selected format and quality (format='%s', bitrate='%s')", job_id, matched_row.get('format'), matched_row.get('bitrate'))
        logger.info("[DOWNLOAD] Existing metadata match found - skipping download pipeline")
        stages['downloaded'] = 'done'
        stages['tagged'] = 'done'
        stages['written'] = 'done'
        set_last_download_activity_at(datetime.utcnow())
        jobs.update_job_progress(job_id, {
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': payload.get('plex_playlist'),
            'stages': stages
        })

        playlist_name = payload.get('plex_playlist')
        if playlist_name:
            stages['playlist_added'] = 'done'
            jobs.update_job_progress(job_id, {'stages': stages})
            logger.info("[DOWNLOAD] Job %s: queuing playlist add (existing match) for path=%s playlist=%s", job_id, full_path, playlist_name)
            queue_pending_playlist_addition(
                full_path,
                playlist_name,
                parent_job_id=job_id,
                plex_user_id=payload.get('plex_user_id')
            )
            logger.info("[DOWNLOAD] Playlist requested - queued for bulk playlist add")
        else:
            logger.info("[DOWNLOAD] Plex playlist update skipped. No playlist requested.")
            stages['playlist_added'] = 'skipped'
            jobs.update_job_progress(job_id, {'stages': stages})

        upsert_download_match_hint(
            track_title=track_title,
            track_artist_name=track_artist_name,
            album_title=album_name,
            album_artist_name=album_artist_name or track_artist_name,
            full_path=full_path,
            audio_format=matched_row.get('format', 'unknown'),
            hifi_track_id=str(track_id),
            hifi_album_id=str(album_id) if album_id else None,
            track_hifi_artist_id=track_artist_id,
            album_hifi_artist_id=album_artist_id or track_artist_id,
            isrc=track_data.get('isrc'),
            duration=track_data.get('duration'),
            track_number=track_number,
            disc_number=_safe_int(disc_num) if disc_num else None,
        )

        return {
            'file_path': full_path,
            'format': matched_row.get('format', 'unknown'),
            'artist': artist_name,
            'album': album_name,
            'title': track_title,
            'playlist_name': playlist_name,
            'download_skipped_existing': True,
            'stages': stages
        }

    logger.info("[DOWNLOAD_DECISION] Job %s: downloading because no existing Plex inventory metadata matched", job_id)

    full_path = os.path.join(downloads_folder, file_path)
    full_path = os.path.normpath(full_path)

    logger.debug("[DOWNLOAD] file_naming='%s' template -> file_path='%s'", file_naming, file_path)
    logger.debug("[DOWNLOAD] resolved full_path='%s' downloads_folder='%s'", full_path, downloads_folder)
    logger.info("[DOWNLOAD_DECISION] Job %s: title='%s', artist='%s', album='%s', effective_artist='%s'", job_id, track_title, artist_name, album_name, effective_artist_name)

    # --- Download track to temp ---

    temp_folder = '/app/temp'
    os.makedirs(temp_folder, exist_ok=True)

    download_mirror = None  # Track which mirror was used

    # --- Download track with source fallback ---
    # Build priority order from comma-separated download_source (e.g. "tidal,qobuz")
    download_sources = [s.strip() for s in download_source.split(',') if s.strip() in ('tidal', 'qobuz', 'deezer', 'deezer_mirror')]
    if not download_sources:
        download_sources = ['tidal']

    last_download_error = None
    any_source_had_mirrors = False  # Track if any source had eligible mirrors to try
    per_source_errors = {}
    audio_format = None
    expected_duration = track_data.get('duration')
    logger.info("[DOWNLOAD] Pre-download: quality=%s, expected_duration=%s, download_sources=%s, track_id=%s",
                quality_choice, expected_duration, download_sources, track_id)

    for current_source in download_sources:
        if current_source == 'qobuz' and not track_data.get('isrc'):
            logger.info("[DOWNLOAD] Skipping Qobuz: track has no ISRC")
            last_download_error = "Qobuz requires ISRC (permanent)"
            continue

        if current_source == 'deezer' and not tag_settings.get('deezer_arl'):
            logger.info("[DOWNLOAD] Skipping Deezer: no ARL configured")
            last_download_error = "Deezer ARL not configured (permanent)"
            continue

        if current_source == 'deezer_mirror' and not track_data.get('isrc'):
            logger.info("[DOWNLOAD] Skipping Deezer Mirror: track has no ISRC")
            last_download_error = "Deezer Mirror requires ISRC (permanent)"
            continue

        temp_source_path = ''

        try:
            handler = _DOWNLOAD_SOURCE_HANDLERS.get(current_source)
            if handler is None:
                logger.warning("[DOWNLOAD] Unknown source '%s', skipping", current_source)
                last_download_error = f"Unknown source '{current_source}' (permanent)"
                continue

            isrc = track_data.get('isrc')
            if handler is hifi.download_track_by_isrc:
                result = handler(isrc, quality_choice, track_id=track_id)
            else:
                result = handler(isrc, quality_choice)

            temp_source_path = result['file_path']
            download_mirror = result['source']

            expected_format = downloads.expected_download_format(current_source, quality_choice)
            audio_format = _finalize_download(
                temp_source_path,
                current_source,
                expected_duration,
                expected_format,
            )
            break

        except (ValueError, downloads.TransientDownloadError, RuntimeError, requests.exceptions.RequestException) as e:
            error_str = str(e)
            last_download_error = error_str
            per_source_errors[current_source] = error_str
            download_mirror = None
            # If this source had eligible mirrors to try (even if they failed),
            # the failure might be transient — keep the door open for retry.
            # "No mirror" errors are permanent per-source, but other sources
            # may still work via fallback.
            _is_permanent_no_mirror = any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)
            if not _is_permanent_no_mirror:
                any_source_had_mirrors = True
            logger.info("[DOWNLOAD] Source '%s' failed: %s — %s", current_source, error_str,
                        "trying next source..." if len(download_sources) > 1 else "no more sources")
            downloads.cleanup_file(temp_source_path)
            continue

    if download_mirror is None:
        if per_source_errors:
            error_summary = '; '.join(
                f"{src}: {err}" for src, err in per_source_errors.items()
            )
        else:
            error_summary = last_download_error or 'unknown error'
        if any_source_had_mirrors:
            raise downloads.TransientDownloadError(f"All download sources failed: {error_summary}")
        raise downloads.PermanentDownloadError(f"All download sources failed: {error_summary}")

    logger.info("[DOWNLOAD] Job %s starting for track %s", job_id, track_id)

    jobs.update_job_progress(job_id, {
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': payload.get('plex_playlist'),
        'stages': stages
    })

    media_tags = []
    audio_quality = None
    if isinstance(track_data, dict):
        audio_quality = track_data.get('maxAudioQuality') or track_data.get('audioQuality')
        if isinstance(audio_quality, str) and audio_quality:
            media_tags.append(audio_quality)

    # Treat DOLBY_ATMOS as HIRES_LOSSLESS since it requires high-quality audio
    if 'DOLBY_ATMOS' in media_tags and 'HIRES_LOSSLESS' not in media_tags:
        media_tags.append('HIRES_LOSSLESS')

    logger.info("[DOWNLOAD] File path template result: %s", file_path)

    logger.info("[DOWNLOAD] Full output path: %s", full_path)

    output_dir = os.path.dirname(full_path)
    logger.info("[DOWNLOAD] Creating directory structure: %s", output_dir)

    os.makedirs(output_dir, exist_ok=True)
    logger.info("[DOWNLOAD] Directory created/exists: %s", output_dir)

    logger.info("[DOWNLOAD] Download complete. Using temporary source file: %s", temp_source_path)

    cover_image_data = None
    if cover_url:
        cover_image_data = downloads.download_cover_image(cover_url)

    album_track_count = None
    if isinstance(album_data.get('numberOfTracks'), int):
        album_track_count = album_data.get('numberOfTracks')
    elif isinstance(album_data.get('numberOfTracks'), str) and album_data.get('numberOfTracks').isdigit():
        album_track_count = int(album_data.get('numberOfTracks'))

    album_disc_count = None
    if isinstance(album_data.get('numberOfDiscs'), int):
        album_disc_count = album_data.get('numberOfDiscs')
    elif isinstance(album_data.get('numberOfDiscs'), str) and album_data.get('numberOfDiscs').isdigit():
        album_disc_count = int(album_data.get('numberOfDiscs'))

    metadata_dict = {
        'artist': track_artist_name,
        'track_artists': track_artists or [track_artist_name],
        'album_artist': album_artist_name,
        'album_artists': album_artists or ([album_artist_name] if album_artist_name else []),
        'title': track_title,
        'album': album_name,
        'year': release_year,
        'track_number': track_num,
        'disc_number': disc_num,
        'track_total': album_track_count,
        'disc_total': album_disc_count,
        'version': track_version,
        'copyright': copyright_text,
        'track_explicit': bool(track_data.get('explicit')),
        'album_explicit': bool(album_data.get('explicit')),
        'explicit': bool(track_data.get('explicit') or album_data.get('explicit')),
        'tidal_track_id': track_id,
        'tidal_album_id': album_id,
        'isrc': track_data.get('isrc'),
        'audio_quality': track_data.get('maxAudioQuality') or track_data.get('audioQuality'),
    }

    logger.debug("[DOWNLOAD] cover_url='%s' cover_bytes=%s", cover_url, len(cover_image_data) if cover_image_data else 0)
    logger.debug("[DOWNLOAD] metadata_dict=%s", metadata_dict)

    logger.info("[DOWNLOAD] Using temporary source file: %s", temp_source_path)

    stages['downloaded'] = 'done'
    set_last_download_activity_at(datetime.utcnow())
    jobs.update_job_progress(job_id, {'stages': stages})

    logger.info("[DOWNLOAD] Adding metadata to staged file: %s", temp_source_path)
    logger.debug("[DOWNLOAD] tagging temp_source_path='%s'", temp_source_path)
    downloads.add_id3_tags_to_file(temp_source_path, metadata_dict, cover_image_data, tag_settings)
    logger.debug("[DOWNLOAD] tagging complete for temp_source_path='%s'", temp_source_path)
    try:
        tagged_size = os.path.getsize(temp_source_path)
        logger.info("[DOWNLOAD] Tagged temp file size: %d bytes (%s)", tagged_size, temp_source_path)
    except OSError:
        logger.info("[DOWNLOAD] Tagged temp file size: unknown (%s)", temp_source_path)
    stages['tagged'] = 'done'
    jobs.update_job_progress(job_id, {'stages': stages})

    audio_format = audio_format or 'flac'
    if not full_path.endswith(f'.{audio_format}'):
        full_path = full_path.rsplit('.', 1)[0] + f'.{audio_format}'
        logger.info("[DOWNLOAD] Updated output path with correct extension: %s", full_path)

    logger.info("[DOWNLOAD] Moving %s to final destination", audio_format.upper())
    shutil.move(temp_source_path, full_path)
    try:
        final_size = os.path.getsize(full_path)
        logger.info("[DOWNLOAD] Final file: %d bytes, format=%s (%s)", final_size, audio_format, full_path)
    except OSError:
        logger.info("[DOWNLOAD] Final file: size unknown (%s)", full_path)

    stages['written'] = 'done'
    set_last_download_activity_at(datetime.utcnow())
    jobs.update_job_progress(job_id, {'stages': stages})

    downloads.cleanup_file(temp_source_path)

    logger.info("[DOWNLOAD] Downloaded and saved to %s", full_path)

    playlist_name = payload.get('plex_playlist')
    if playlist_name:
        stages['playlist_added'] = 'done'
        jobs.update_job_progress(job_id, {'stages': stages})
        logger.info("[DOWNLOAD] Job %s: queuing playlist add for path=%s playlist=%s", job_id, full_path, playlist_name)
        queue_pending_playlist_addition(
            full_path,
            playlist_name,
            parent_job_id=job_id,
            plex_user_id=payload.get('plex_user_id')
        )
        logger.info("[DOWNLOAD] Playlist requested - queued for bulk playlist add")
    else:
        logger.info("[DOWNLOAD] Plex playlist update skipped. No playlist requested.")
        stages['playlist_added'] = 'skipped'
        jobs.update_job_progress(job_id, {'stages': stages})

    upsert_download_match_hint(
        track_title=track_title,
        track_artist_name=track_artist_name,
        album_title=album_name,
        album_artist_name=album_artist_name or track_artist_name,
        full_path=full_path,
        audio_format=audio_format or 'flac',
        hifi_track_id=str(track_id),
        hifi_album_id=str(album_id) if album_id else None,
        track_hifi_artist_id=track_artist_id,
        album_hifi_artist_id=album_artist_id or track_artist_id,
        isrc=track_data.get('isrc'),
        duration=track_data.get('duration'),
        track_number=track_number,
        disc_number=_safe_int(disc_num) if disc_num else None,
    )

    result = {
        'file_path': full_path,
        'format': audio_format or 'flac',
        'artist': artist_name,
        'album': album_name,
        'title': track_title,
        'playlist_name': playlist_name,
        'download_mirror': download_mirror,
        'mirror_type': current_source,
        'stages': stages
    }
    return result


