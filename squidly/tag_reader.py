"""Tag reading and library gap-filling from audio file metadata.

Reads FLAC and M4A tags to fill missing fields in the local database.
MP3 files are not supported.
"""

import logging
import os

from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from squidly.config import DOWNLOADS_ROOT
from squidly.db import get_db_connection
from squidly.utils import _safe_int, _safe_float, _now_utc
from squidly.matching import (
    _get_track_row_by_path,
    _get_album_row,
    _get_artist_row,
    _upsert_track_row,
    _upsert_album_row,
    _upsert_artist_row,
)

logger = logging.getLogger(__name__)


def _resolve_library_file_path(file_path):
    """Resolve a relative or absolute path to an existing file on disk."""
    raw_path = str(file_path or '').strip()
    if not raw_path:
        return ''

    if raw_path.startswith('/'):
        return raw_path if os.path.exists(raw_path) else ''

    return f"{DOWNLOADS_ROOT}/{raw_path}"


def _read_flac_tags(raw_path):
    """Read all relevant tags from a FLAC file."""
    audio = FLAC(raw_path)
    tags = {}

    def first(key):
        values = audio.get(key) or audio.get(key.lower()) or []
        return str(values[0]).strip() if values else None

    tags['title'] = first('TITLE')
    tags['artist'] = first('ARTIST')
    tags['album'] = first('ALBUM')
    tags['album_artist'] = first('ALBUMARTIST')
    tags['track_number'] = _safe_int(first('TRACKNUMBER'))
    tags['disc_number'] = _safe_int(first('DISCNUMBER'))
    tags['isrc'] = first('ISRC')
    tags['tidal_track_id'] = first('TIDAL_TRACK_ID')
    tags['tidal_album_id'] = first('TIDAL_ALBUM_ID')

    if audio.info:
        tags['duration'] = int(audio.info.length) if audio.info.length else None
        tags['bitrate'] = int(audio.info.bitrate // 1000) if audio.info.bitrate else None

    return tags


def _read_m4a_tags(raw_path):
    """Read all relevant tags from an M4A file."""
    audio = MP4(raw_path)
    tags = {}

    def first_text(key):
        values = audio.get(key) or []
        if not values:
            return None
        val = values[0]
        if isinstance(val, bytes):
            val = val.decode('utf-8', errors='ignore')
        return str(val).strip() or None

    def first_int(key):
        values = audio.get(key) or []
        if not values:
            return None
        val = values[0]
        if isinstance(val, tuple):
            return val[0] if val else None
        return _safe_int(val)

    tags['title'] = first_text('\xa9nam')
    tags['artist'] = first_text('\xa9ART')
    tags['album'] = first_text('\xa9alb')
    tags['album_artist'] = first_text('aART')
    tags['track_number'] = first_int('trkn')
    tags['disc_number'] = first_int('disk')
    tags['isrc'] = first_text('----:com.apple.iTunes:isrc')
    tags['tidal_track_id'] = first_text('----:com.apple.iTunes:tidal_track_id')
    tags['tidal_album_id'] = first_text('----:com.apple.iTunes:tidal_album_id')

    if audio.info:
        tags['duration'] = int(audio.info.length) if audio.info.length else None
        tags['bitrate'] = int(audio.info.bitrate // 1000) if audio.info.bitrate else None

    return tags


def read_audio_file_tags(file_path):
    """Read all relevant tags and file info from an audio file.

    Returns a dict with: title, artist, album, album_artist,
    track_number, disc_number, isrc, tidal_track_id, tidal_album_id,
    duration, bitrate. Returns empty dict if file cannot be read.
    """
    raw_path = _resolve_library_file_path(file_path)
    if not raw_path or not os.path.exists(raw_path):
        return {}

    try:
        lower_path = raw_path.lower()
        if lower_path.endswith('.flac'):
            return _read_flac_tags(raw_path)
        elif lower_path.endswith('.m4a'):
            return _read_m4a_tags(raw_path)
    except Exception:
        pass

    return {}


def _find_tracks_needing_tag_fill(cur):
    """Find track rows that have a path but are missing one or more fields."""
    cur.execute(
        """
        SELECT track_id, album_id, artist_id, title, library_id,
               confidence, hifi_id, path, format, bitrate,
               disc_number, track_number, last_seen_at, isrc, duration
        FROM tracks
        WHERE path IS NOT NULL AND path != ''
          AND (
              hifi_id IS NULL
              OR title IS NULL OR title = ''
              OR track_number IS NULL
              OR disc_number IS NULL
              OR isrc IS NULL
              OR duration IS NULL
              OR bitrate IS NULL
              OR format IS NULL OR format = ''
          )
        ORDER BY track_id ASC
        """
    )
    return cur.fetchall() or []


def _fill_track_from_tags(cur, track_row, tags):
    """Update a track row with any missing fields filled from tags.

    Also resolves album and artist hifi_ids from tags if missing.
    """
    if not tags:
        return

    existing_album_id = track_row.get('album_id')
    existing_artist_id = track_row.get('artist_id')
    existing_hifi_id = str(track_row.get('hifi_id') or '').strip() or None
    existing_isrc = str(track_row.get('isrc') or '').strip() or None
    existing_duration = track_row.get('duration')
    existing_bitrate = track_row.get('bitrate')
    existing_format = str(track_row.get('format') or '').strip() or None
    existing_track_number = track_row.get('track_number')
    existing_disc_number = track_row.get('disc_number')
    existing_title = str(track_row.get('title') or '').strip() or None

    new_hifi_id = tags.get('tidal_track_id') or existing_hifi_id
    new_isrc = tags.get('isrc') or existing_isrc
    new_duration = tags.get('duration') if existing_duration is None else existing_duration
    new_bitrate = tags.get('bitrate') if existing_bitrate is None else existing_bitrate

    path = str(track_row.get('path') or '').strip()
    file_ext = os.path.splitext(path)[1].lstrip('.').lower() if path else ''
    new_format = file_ext if (not existing_format and file_ext in ('flac', 'm4a', 'mp3')) else existing_format

    new_track_number = tags.get('track_number') if existing_track_number is None else existing_track_number
    new_disc_number = tags.get('disc_number') if existing_disc_number is None else existing_disc_number
    new_title = tags.get('title') or existing_title

    album_hifi_id = tags.get('tidal_album_id')
    if album_hifi_id and existing_album_id:
        existing_album_row = _get_album_row(cur, existing_album_id)
        existing_album_hifi_id = str((existing_album_row or {}).get('hifi_id') or '').strip() or None
        if not existing_album_hifi_id:
            existing_album_artist_id = (existing_album_row or {}).get('artist_id')
            existing_album_title = str((existing_album_row or {}).get('title') or '').strip() or None
            _upsert_album_row(
                cur,
                artist_id=existing_album_artist_id,
                title=existing_album_title or tags.get('album') or 'Unknown Album',
                hifi_id=album_hifi_id,
                confidence=0.99,
                last_seen_at=(existing_album_row or {}).get('last_seen_at') or _now_utc(),
            )

    artist_name = tags.get('artist') or tags.get('album_artist')
    if artist_name and existing_artist_id:
        existing_artist_row = _get_artist_row(cur, existing_artist_id)
        existing_artist_hifi_id = str((existing_artist_row or {}).get('hifi_id') or '').strip() or None
        artist_hifi_id = new_hifi_id if not existing_artist_hifi_id else None
        _upsert_artist_row(
            cur,
            name=artist_name,
            library_id=(existing_artist_row or {}).get('library_id'),
            hifi_id=artist_hifi_id or existing_artist_hifi_id,
            confidence=0.99 if (artist_hifi_id or existing_artist_hifi_id) else 0.0,
            last_seen_at=(existing_artist_row or {}).get('last_seen_at') or _now_utc(),
        )

    _upsert_track_row(
        cur,
        album_id=existing_album_id,
        artist_id=existing_artist_id,
        title=new_title,
        path=track_row.get('path') or '',
        library_id=track_row.get('library_id'),
        hifi_id=new_hifi_id,
        confidence=max(_safe_float(track_row.get('confidence')), 0.99 if new_hifi_id else 0.0),
        last_seen_at=track_row.get('last_seen_at') or _now_utc(),
        audio_format=new_format,
        bitrate=new_bitrate,
        disc_number=new_disc_number,
        track_number=new_track_number,
        isrc=new_isrc,
        duration=new_duration,
    )


def scan_library_for_tags(progress_callback=None):
    """Scan all tracks with missing fields and fill them from file tags.

    Returns a dict with total_scanned, fields_filled, and errors.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        tracks = _find_tracks_needing_tag_fill(cur)
        total = len(tracks)
        filled = 0
        errors = 0

        for idx, track_row in enumerate(tracks, 1):
            try:
                path = str(track_row.get('path') or '').strip()
                tags = read_audio_file_tags(path)
                if tags:
                    _fill_track_from_tags(cur, track_row, tags)
                    filled += 1
            except Exception as e:
                errors += 1
                logger.info("[TAG_SCAN] Error processing %s: %s", track_row.get('path'), e)

            if progress_callback and idx % 10 == 0:
                progress_callback(idx, total)

        conn.commit()

        if progress_callback:
            progress_callback(total, total)

        return {
            'total_scanned': total,
            'fields_filled': filled,
            'errors': errors,
        }
    finally:
        conn.close()
