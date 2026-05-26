"""Matching and scoring helpers for HiFi/Plex library correlation."""

import re

from squidly.infrastructure.utils import _safe_int, _safe_float, _now_utc, normalize_match_text, _normalize_library_track_path
from squidly.infrastructure.db import get_db_connection
from squidly.infrastructure.job_queue import update_job_progress
from squidly.services.hifi import (
    _extract_hifi_album_track_items,
    _get_hifi_audio_quality_rank,
    _format_hifi_image_value,
    _fetch_hifi_album_payload,
    _fetch_hifi_artist_payload,
    _fetch_hifi_search_results,
)


MATCH_REVIEW_ARTWORK_SIZE = 350
MATCH_REVIEW_HIFI_ARTWORK_SIZE = 640
MATCH_REVIEW_HIFI_ARTIST_ARTWORK_SIZE = 750


def _extract_hifi_item_artists(item):
    if not isinstance(item, dict):
        return []

    candidates = []
    for key in ('primaryArtist', 'artist'):
        value = item.get(key)
        if isinstance(value, dict):
            candidates.append(value)

    artists = item.get('artists')
    if isinstance(artists, list):
        for artist in artists:
            if isinstance(artist, dict):
                candidates.append(artist)

    results = []
    seen = set()
    for candidate in candidates:
        hifi_id = str(candidate.get('id') or '').strip() or None
        name = str(candidate.get('name') or '').strip() or None
        key = (hifi_id, normalize_match_text(name))
        if key in seen:
            continue
        seen.add(key)
        if not hifi_id and not name:
            continue
        results.append({'hifi_id': hifi_id, 'name': name})
    return results


def _extract_primary_hifi_artist(item):
    artists = _extract_hifi_item_artists(item)
    return artists[0] if artists else None


def _is_manual_match(row):
    if not isinstance(row, dict):
        return False
    return _safe_float(row.get('confidence')) == 1.0


def _merge_match_state(existing_row, hifi_id=None, confidence=None):
    if not isinstance(existing_row, dict):
        existing_row = {}

    if _is_manual_match(existing_row):
        return {
            'hifi_id': existing_row.get('hifi_id'),
            'confidence': _safe_float(existing_row.get('confidence')),
        }

    existing_confidence = _safe_float(existing_row.get('confidence'))
    existing_hifi_id = str(existing_row.get('hifi_id') or '').strip() or None

    if not hifi_id:
        return {
            'hifi_id': existing_hifi_id,
            'confidence': existing_confidence,
        }

    incoming_confidence = _safe_float(confidence, default=0.0)
    should_apply = False
    if not existing_hifi_id:
        should_apply = True
    elif existing_hifi_id == hifi_id:
        should_apply = True
    elif confidence is not None and incoming_confidence >= existing_confidence:
        should_apply = True

    if should_apply:
        return {
            'hifi_id': str(hifi_id).strip() if hifi_id else None,
            'confidence': _safe_float(confidence, default=existing_confidence),
        }

    return {
        'hifi_id': existing_hifi_id,
        'confidence': existing_confidence,
    }


def _is_hifi_explicit(item):
    if not isinstance(item, dict):
        return False
    if bool(item.get('explicit')):
        return True

    metadata = item.get('mediaMetadata') if isinstance(item.get('mediaMetadata'), dict) else {}
    tags = []
    metadata_tags = metadata.get('tags')
    if isinstance(metadata_tags, list):
        tags.extend(metadata_tags)
    media_tags = item.get('mediaTags')
    if isinstance(media_tags, list):
        tags.extend(media_tags)

    normalized_tags = {str(tag or '').strip().upper() for tag in tags if str(tag or '').strip()}
    return 'EXPLICIT' in normalized_tags


def _format_hifi_track_title(item):
    if not isinstance(item, dict):
        return ''

    title = str(item.get('title') or '').strip()
    if not title:
        return ''

    version = str(item.get('version') or '').strip()
    if version and normalize_match_text(version) not in normalize_match_text(title):
        return f"{title} ({version})"

    return title


def _extract_hifi_album_track_titles(album_payload, limit=30):
    album_data = album_payload.get('data') if isinstance(album_payload, dict) else {}
    items = album_data.get('items', []) if isinstance(album_data, dict) else []
    track_titles = []

    for entry in items:
        if not isinstance(entry, dict) or entry.get('type') != 'track':
            continue
        item = entry.get('item') if isinstance(entry.get('item'), dict) else None
        if not item:
            continue
        title = _format_hifi_track_title(item)
        if not title:
            continue
        track_titles.append(title)
        if len(track_titles) >= limit:
            break

    return track_titles


def _has_explicit_marker(value):
    text = str(value or '').strip().lower()
    return '[explicit]' in text or '(explicit)' in text


def _score_explicit_alignment(source_is_explicit, candidate_is_explicit):
    if source_is_explicit and candidate_is_explicit:
        return 0.02
    if source_is_explicit != candidate_is_explicit:
        return -0.02
    return 0.0


def _score_album_track_title_alignment(source_track_titles, candidate_track_titles):
    normalized_source = [
        normalize_match_text(title, strip_trailing_parenthetical=True)
        for title in (source_track_titles or [])
        if normalize_match_text(title, strip_trailing_parenthetical=True)
    ]
    normalized_candidate = [
        normalize_match_text(title, strip_trailing_parenthetical=True)
        for title in (candidate_track_titles or [])
        if normalize_match_text(title, strip_trailing_parenthetical=True)
    ]

    if len(normalized_source) < 2 or len(normalized_candidate) < 2:
        return 0.0

    compare_count = min(len(normalized_source), len(normalized_candidate), 12)
    if compare_count < 2:
        return 0.0

    matches = sum(1 for idx in range(compare_count) if normalized_source[idx] == normalized_candidate[idx])
    ratio = matches / compare_count
    if ratio >= 0.85:
        return 0.03
    if ratio >= 0.65:
        return 0.015
    return 0.0


def _score_artist_candidate_name(artist_name, candidate_name):
    normalized_artist = normalize_match_text(artist_name)
    normalized_candidate = normalize_match_text(candidate_name)
    if not normalized_artist or not normalized_candidate:
        return 0.0
    if normalized_artist == normalized_candidate:
        return 0.96
    if normalized_candidate in normalized_artist or normalized_artist in normalized_candidate:
        return 0.78
    return 0.0


def _extract_album_candidate_artist_names(candidate):
    names = []
    if isinstance(candidate.get('primaryArtist'), dict):
        name = str(candidate.get('primaryArtist', {}).get('name') or '').strip()
        if name:
            names.append(name)
    if isinstance(candidate.get('artists'), list):
        names.extend(
            str(item.get('name') or '').strip()
            for item in candidate.get('artists')
            if isinstance(item, dict) and str(item.get('name') or '').strip()
        )
    elif isinstance(candidate.get('artist'), dict):
        name = str(candidate.get('artist', {}).get('name') or '').strip()
        if name:
            names.append(name)

    deduped_names = []
    seen = set()
    for name in names:
        normalized = normalize_match_text(name)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_names.append(name)
    return deduped_names


def _score_album_candidate_artist_alignment(source_artist_name, candidate_artist_names):
    source_name = str(source_artist_name or '').strip()
    if not source_name or not candidate_artist_names:
        return 0.0

    best_score = max((_score_artist_candidate_name(source_name, candidate_name) for candidate_name in candidate_artist_names), default=0.0)
    if best_score >= 0.96:
        return 0.04
    if best_score >= 0.78:
        return 0.02
    return 0.0


def _score_album_candidate_title(album_title, candidate_title, library_track_count=None, candidate_track_count=None, source_is_explicit=False, candidate_is_explicit=False):
    normalized_title = normalize_match_text(album_title, strip_trailing_parenthetical=True)
    normalized_candidate = normalize_match_text(candidate_title, strip_trailing_parenthetical=True)
    if not normalized_title or not normalized_candidate:
        return 0.0

    confidence = 0.0
    if normalized_title == normalized_candidate:
        confidence = 0.93
    elif normalized_candidate in normalized_title or normalized_title in normalized_candidate:
        confidence = 0.78

    if confidence <= 0:
        return 0.0

    if library_track_count and candidate_track_count and library_track_count == candidate_track_count:
        confidence += 0.03

    confidence += _score_explicit_alignment(source_is_explicit, candidate_is_explicit)

    return min(confidence, 0.99)


def _score_track_candidate_payload(track_row, candidate):
    normalized_title = normalize_match_text(track_row.get('title'), strip_trailing_parenthetical=True)
    candidate_title = str(candidate.get('title') or '').strip()
    normalized_candidate = normalize_match_text(candidate_title, strip_trailing_parenthetical=True)
    if not normalized_title or not normalized_candidate:
        return 0.0

    confidence = 0.0
    if normalized_title == normalized_candidate:
        confidence = 0.90
    elif normalized_candidate in normalized_title or normalized_title in normalized_candidate:
        confidence = 0.74

    if confidence <= 0:
        return 0.0

    desired_track_number = _safe_int(track_row.get('track_number'))
    desired_disc_number = _safe_int(track_row.get('disc_number'))
    candidate_track_number = _safe_int(candidate.get('trackNumber'))
    candidate_disc_number = _safe_int(candidate.get('volumeNumber'))
    if desired_track_number and candidate_track_number and desired_track_number == candidate_track_number:
        confidence += 0.05
    if desired_disc_number and candidate_disc_number and desired_disc_number == candidate_disc_number:
        confidence += 0.02

    candidate_album = candidate.get('album') if isinstance(candidate.get('album'), dict) else {}
    candidate_album_title = str(candidate_album.get('title') or '').strip()
    if candidate_album_title and normalize_match_text(candidate_album_title, strip_trailing_parenthetical=True) == normalize_match_text(track_row.get('album_title'), strip_trailing_parenthetical=True):
        confidence += 0.02

    confidence += _score_explicit_alignment(_has_explicit_marker(track_row.get('title')), _is_hifi_explicit(candidate))

    return min(confidence, 0.99)


def _serialize_match_variants(rows):
    variants = []
    seen = set()
    for row in rows or []:
        fmt = str(row.get('format') or '').strip().lower() or 'unknown'
        bitrate = _safe_int(row.get('bitrate'))
        file_path = str(row.get('path') or row.get('file_path') or '').strip() or None
        key = (fmt, bitrate, file_path)
        if key in seen:
            continue
        seen.add(key)
        variants.append({
            'format': fmt,
            'bitrate': bitrate,
            'file_path': file_path,
        })
    return variants


def _evaluate_album_candidate(row, candidate, source_track_titles=None):
    hifi_id = str(candidate.get('id') or '').strip()
    title = str(candidate.get('title') or '').strip()
    if not hifi_id or not title:
        return None

    library_track_count = _safe_int(row.get('library_track_count'))
    candidate_track_count = _safe_int(candidate.get('numberOfTracks') or candidate.get('numberOfItems'))
    candidate_is_explicit = _is_hifi_explicit(candidate)
    source_is_explicit = _has_explicit_marker(row.get('title'))

    base_confidence = _score_album_candidate_title(
        row.get('title'),
        title,
        library_track_count,
        candidate_track_count,
        source_is_explicit=source_is_explicit,
        candidate_is_explicit=candidate_is_explicit,
    )

    artist_names = _extract_album_candidate_artist_names(candidate)
    artist_bonus = _score_album_candidate_artist_alignment(row.get('artist_name'), artist_names)

    album_track_titles = _extract_hifi_album_track_titles(_fetch_hifi_album_payload(hifi_id))
    track_bonus = _score_album_track_title_alignment(source_track_titles, album_track_titles)

    confidence = base_confidence + artist_bonus + track_bonus
    if base_confidence <= 0:
        explicit_bonus = _score_explicit_alignment(source_is_explicit, candidate_is_explicit)
        if track_bonus >= 0.03 and artist_bonus >= 0.02:
            confidence = 0.72 + artist_bonus + track_bonus + explicit_bonus
        elif track_bonus >= 0.015 and artist_bonus >= 0.04:
            confidence = 0.68 + artist_bonus + track_bonus + explicit_bonus
        else:
            return None

    subtitle_parts = []
    if artist_names:
        subtitle_parts.append(', '.join(artist_names))
    elif row.get('artist_name'):
        subtitle_parts.append(str(row.get('artist_name')).strip())

    return {
        'hifi_id': hifi_id,
        'title': title,
        'subtitle': ' \u2022 '.join(part for part in subtitle_parts if part),
        'confidence': min(confidence, 0.99),
        'image_url': _format_hifi_image_value(candidate.get('cover'), size=MATCH_REVIEW_HIFI_ARTWORK_SIZE),
        'explicit': candidate_is_explicit,
        'track_titles': album_track_titles,
    }


def _get_artist_row(cur, artist_id):
    cur.execute(
        """
        SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
        FROM artists
        WHERE artist_id = %s
        """,
        (artist_id,)
    )
    return cur.fetchone()


def _get_album_row(cur, album_id):
    cur.execute(
        """
        SELECT album_id, artist_id, title, library_id, hifi_id, confidence, complete,
               matched_track_count, expected_track_count, last_seen_at
        FROM albums
        WHERE album_id = %s
        """,
        (album_id,)
    )
    return cur.fetchone()


def _get_track_row_by_path(cur, path):
    cur.execute(
        """
        SELECT track_id, album_id, artist_id, title, library_id, confidence, hifi_id, path,
               format, bitrate, disc_number, track_number, last_seen_at, isrc, duration
        FROM tracks
        WHERE LOWER(path) = LOWER(%s)
        """,
        (path,)
    )
    return cur.fetchone()


def _upsert_artist_row(cur, name, library_id=None, hifi_id=None, confidence=0.0, last_seen_at=None):
    existing = None
    if library_id:
        cur.execute(
            """
            SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
            FROM artists
            WHERE library_id = %s
            """,
            (library_id,)
        )
        existing = cur.fetchone()
    if not existing and hifi_id:
        cur.execute(
            """
            SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
            FROM artists
            WHERE hifi_id = %s
            ORDER BY artist_id ASC
            LIMIT 1
            """,
            (hifi_id,)
        )
        existing = cur.fetchone()
    if not existing:
        cur.execute(
            """
            INSERT INTO artists (name, library_id, hifi_id, confidence, last_seen_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING artist_id
            """,
            (
                name,
                library_id,
                hifi_id,
                confidence,
                last_seen_at or _now_utc(),
            )
        )
        return cur.fetchone()['artist_id']

    match_state = _merge_match_state(existing, hifi_id=hifi_id, confidence=confidence)
    cur.execute(
        """
        UPDATE artists
        SET name = %s,
            library_id = COALESCE(%s, library_id),
            hifi_id = %s,
            confidence = %s,
            last_seen_at = %s
        WHERE artist_id = %s
        """,
        (
            name,
            library_id,
            match_state['hifi_id'],
            match_state['confidence'],
            last_seen_at or existing.get('last_seen_at') or _now_utc(),
            existing['artist_id'],
        )
    )
    return existing['artist_id']


def _upsert_album_row(cur, artist_id, title, library_id=None, hifi_id=None, confidence=0.0, complete=False, last_seen_at=None, matched_track_count=None, expected_track_count=None):
    existing = None
    if library_id:
        cur.execute(
            """
            SELECT album_id, artist_id, title, library_id, hifi_id, confidence, complete,
                   matched_track_count, expected_track_count, last_seen_at
            FROM albums
            WHERE library_id = %s
            """,
            (library_id,)
        )
        existing = cur.fetchone()
    if not existing and hifi_id:
        cur.execute(
            """
            SELECT album_id, artist_id, title, library_id, hifi_id, confidence, complete,
                   matched_track_count, expected_track_count, last_seen_at
            FROM albums
            WHERE hifi_id = %s
              AND (%s IS NULL OR artist_id = %s)
            ORDER BY album_id ASC
            LIMIT 1
            """,
            (hifi_id, artist_id, artist_id)
        )
        existing = cur.fetchone()
    if not existing:
        cur.execute(
            """
            INSERT INTO albums (
                artist_id, title, library_id, hifi_id, confidence, complete,
                matched_track_count, expected_track_count, last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING album_id
            """,
            (
                artist_id,
                title,
                library_id,
                hifi_id,
                confidence,
                complete,
                matched_track_count or 0,
                expected_track_count or 0,
                last_seen_at or _now_utc(),
            )
        )
        return cur.fetchone()['album_id']

    match_state = _merge_match_state(existing, hifi_id=hifi_id, confidence=confidence)
    cur.execute(
        """
        UPDATE albums
        SET artist_id = COALESCE(%s, artist_id),
            title = %s,
            library_id = COALESCE(%s, library_id),
            hifi_id = %s,
            confidence = %s,
            complete = %s,
            matched_track_count = %s,
            expected_track_count = %s,
            last_seen_at = %s
        WHERE album_id = %s
        """,
        (
            artist_id,
            title,
            library_id,
            match_state['hifi_id'],
            match_state['confidence'],
            complete if complete is not None else existing.get('complete') or False,
            matched_track_count if matched_track_count is not None else existing.get('matched_track_count') or 0,
            expected_track_count if expected_track_count is not None else existing.get('expected_track_count') or 0,
            last_seen_at or existing.get('last_seen_at') or _now_utc(),
            existing['album_id'],
        )
    )
    return existing['album_id']


def _upsert_track_row(cur, album_id, artist_id, title, path, library_id=None, hifi_id=None, confidence=0.0, last_seen_at=None, audio_format=None, bitrate=None, disc_number=None, track_number=None, isrc=None, duration=None):
    existing = None
    if library_id:
        cur.execute(
            """
            SELECT track_id, album_id, artist_id, title, library_id, confidence, hifi_id, path,
                   format, bitrate, disc_number, track_number, last_seen_at, isrc, duration
            FROM tracks
            WHERE library_id = %s
            """,
            (library_id,)
        )
        existing = cur.fetchone()
    if not existing:
        existing = _get_track_row_by_path(cur, path)
    if not existing:
        cur.execute(
            """
            INSERT INTO tracks (
                album_id, artist_id, title, library_id, confidence, hifi_id, path,
                format, bitrate, disc_number, track_number, last_seen_at, isrc, duration
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING track_id
            """,
            (
                album_id,
                artist_id,
                title,
                library_id,
                confidence,
                hifi_id,
                path,
                audio_format,
                bitrate,
                disc_number,
                track_number,
                last_seen_at or _now_utc(),
                isrc,
                duration,
            )
        )
        return cur.fetchone()['track_id']

    match_state = _merge_match_state(existing, hifi_id=hifi_id, confidence=confidence)
    cur.execute(
        """
        UPDATE tracks
        SET album_id = COALESCE(%s, album_id),
            artist_id = COALESCE(%s, artist_id),
            title = %s,
            library_id = COALESCE(%s, library_id),
            confidence = %s,
            hifi_id = %s,
            path = %s,
            format = COALESCE(%s, format),
            bitrate = COALESCE(%s, bitrate),
            disc_number = COALESCE(%s, disc_number),
            track_number = COALESCE(%s, track_number),
            last_seen_at = %s,
            isrc = COALESCE(%s, isrc),
            duration = COALESCE(%s, duration)
        WHERE track_id = %s
        """,
        (
            album_id,
            artist_id,
            title,
            library_id,
            match_state['confidence'],
            match_state['hifi_id'],
            path,
            audio_format,
            bitrate,
            disc_number,
            track_number,
            last_seen_at or existing.get('last_seen_at') or _now_utc(),
            isrc,
            duration,
            existing['track_id'],
        )
    )
    return existing['track_id']


def upsert_download_match_hint(track_title, track_artist_name, album_title, album_artist_name, full_path, audio_format, hifi_track_id=None, hifi_album_id=None, track_hifi_artist_id=None, album_hifi_artist_id=None, isrc=None, duration=None, track_number=None, disc_number=None):
    relative_path = _normalize_library_track_path(full_path)
    if not relative_path:
        return

    now = _now_utc()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        album_artist_row_id = _upsert_artist_row(
            cur,
            name=album_artist_name or track_artist_name or 'Unknown Artist',
            hifi_id=album_hifi_artist_id,
            confidence=0.99 if album_hifi_artist_id else 0.0,
            last_seen_at=now,
        )
        track_artist_row_id = _upsert_artist_row(
            cur,
            name=track_artist_name or album_artist_name or 'Unknown Artist',
            hifi_id=track_hifi_artist_id,
            confidence=0.99 if track_hifi_artist_id else 0.0,
            last_seen_at=now,
        )
        album_row_id = _upsert_album_row(
            cur,
            artist_id=album_artist_row_id,
            title=album_title or 'Unknown Album',
            hifi_id=hifi_album_id,
            confidence=0.99 if hifi_album_id else 0.0,
            last_seen_at=now,
        )
        _upsert_track_row(
            cur,
            album_id=album_row_id,
            artist_id=track_artist_row_id,
            title=track_title or 'Unknown Track',
            path=relative_path,
            hifi_id=hifi_track_id,
            confidence=0.99 if hifi_track_id else 0.0,
            last_seen_at=now,
            audio_format=audio_format,
            isrc=isrc,
            duration=duration,
            track_number=track_number,
            disc_number=disc_number,
        )
        conn.commit()
    finally:
        conn.close()


def _fetch_source_album_track_titles_map(cur, album_ids):
    normalized_ids = []
    for album_id in album_ids or []:
        try:
            value = int(album_id)
        except Exception:
            continue
        if value > 0:
            normalized_ids.append(value)

    if not normalized_ids:
        return {}

    cur.execute(
        """
        SELECT album_id,
               ARRAY_AGG(title ORDER BY COALESCE(disc_number, 1), COALESCE(track_number, 0), LOWER(title)) AS track_titles
        FROM tracks
        WHERE album_id = ANY(%s)
        GROUP BY album_id
        """,
        (normalized_ids,)
    )

    results = {}
    for row in cur.fetchall() or []:
        try:
            album_id = int(row.get('album_id'))
        except Exception:
            continue
        results[album_id] = [
            str(title or '').strip()
            for title in (row.get('track_titles') or [])
            if str(title or '').strip()
        ]
    return results


def _find_hifi_track_search_candidate(cur, track_row, track_hifi_id):
    if not isinstance(track_row, dict):
        return None

    title = str(track_row.get('title') or '').strip()
    artist_name = None
    if track_row.get('artist_id'):
        artist_row = _get_artist_row(cur, track_row.get('artist_id'))
        artist_name = str(artist_row.get('name') or '').strip() if artist_row else None

    def normalize_search_text(text):
        if not text:
            return ''
        text = re.sub(r'\s*\[[^\]]*\]', '', text)
        text = re.sub(r'\s*\([^\)]*\)', '', text)
        return text.strip()

    normalized_title = normalize_search_text(title)
    normalized_artist = normalize_search_text(artist_name)

    query_candidates = []
    if str(track_hifi_id).strip():
        query_candidates.append(str(track_hifi_id).strip())
    if normalized_artist and normalized_title:
        query_candidates.append(f"{normalized_artist} {normalized_title}".strip())
    if normalized_title:
        query_candidates.append(normalized_title)
    if normalized_artist:
        query_candidates.append(normalized_artist)
    if title and title not in query_candidates:
        query_candidates.append(title)

    seen_queries = set()
    for query in query_candidates:
        query = str(query or '').strip()
        if not query or query in seen_queries:
            continue
        seen_queries.add(query)

        for candidate in _fetch_hifi_search_results('s', query, limit=50):
            if str(candidate.get('id') or '').strip() == str(track_hifi_id).strip():
                return candidate

    return None


def _cascade_track_confirm_ids(cur, track_row, track_hifi_id, now_dt, confidence=1.0, track_artist_hifi_id=None, album_artist_hifi_id=None, album_payload_cache=None):
    from squidly.services.hifi import _fetch_hifi_track_info_payload

    if not isinstance(track_row, dict):
        return track_row.get('album_id') if isinstance(track_row, dict) else None

    existing_album_row = _get_album_row(cur, track_row.get('album_id')) if track_row.get('album_id') else None
    existing_track_artist_row = _get_artist_row(cur, track_row.get('artist_id')) if track_row.get('artist_id') else None
    existing_album_artist_row = _get_artist_row(cur, existing_album_row.get('artist_id')) if existing_album_row and existing_album_row.get('artist_id') else None

    album_hifi_id = (existing_album_row or {}).get('hifi_id')
    album_title = (existing_album_row or {}).get('title')
    existing_isrc = track_row.get('isrc')
    existing_duration = track_row.get('duration')

    needs_track_api = not track_artist_hifi_id or not album_hifi_id or not existing_isrc or not existing_duration

    track_data = {}
    track_artist_info = None
    if needs_track_api:
        track_payload = _fetch_hifi_track_info_payload(track_hifi_id)
        track_data = track_payload.get('data') if isinstance(track_payload, dict) else {}
        if not isinstance(track_data, dict):
            track_data = {}
        track_artist_info = _extract_primary_hifi_artist(track_data)
        if not album_hifi_id:
            album_item = track_data.get('album') if isinstance(track_data.get('album'), dict) else {}
            if isinstance(album_item, dict):
                album_hifi_id = str(album_item.get('id') or '').strip() or None
                album_title = str(album_item.get('title') or '').strip() or None

    if not album_hifi_id:
        candidate = _find_hifi_track_search_candidate(cur, track_row, track_hifi_id)
        if isinstance(candidate, dict):
            album_item = candidate.get('album') if isinstance(candidate.get('album'), dict) else {}
            if isinstance(album_item, dict):
                album_hifi_id = str(album_item.get('id') or '').strip() or None
                album_title = str(album_item.get('title') or '').strip() or None
            if not track_artist_info:
                track_artist_info = _extract_primary_hifi_artist(candidate)

    track_artist_row_id = track_row.get('artist_id')
    if track_artist_info or existing_track_artist_row:
        effective_track_artist_hifi_id = (track_artist_info or {}).get('hifi_id') or (existing_track_artist_row or {}).get('hifi_id') or track_artist_hifi_id
        track_artist_row_id = _upsert_artist_row(
            cur,
            name=(track_artist_info or {}).get('name') or (existing_track_artist_row or {}).get('name') or 'Unknown Artist',
            library_id=(existing_track_artist_row or {}).get('library_id'),
            hifi_id=effective_track_artist_hifi_id,
            confidence=confidence,
            last_seen_at=(existing_track_artist_row or {}).get('last_seen_at') or now_dt,
        )

    album_artist_info = None
    if album_hifi_id and not album_artist_hifi_id:
        if album_payload_cache is not None and album_hifi_id in album_payload_cache:
            album_payload = album_payload_cache[album_hifi_id]
        else:
            album_payload = _fetch_hifi_album_payload(album_hifi_id)
            if album_payload_cache is not None:
                album_payload_cache[album_hifi_id] = album_payload
        album_data = album_payload.get('data') if isinstance(album_payload, dict) else {}
        if isinstance(album_data, dict):
            album_artist_info = _extract_primary_hifi_artist(album_data)

    album_artist_row_id = existing_album_row.get('artist_id') if existing_album_row else track_artist_row_id
    if album_artist_info or existing_album_artist_row:
        effective_album_artist_hifi_id = (album_artist_info or {}).get('hifi_id') or (existing_album_artist_row or {}).get('hifi_id') or album_artist_hifi_id
        album_artist_row_id = _upsert_artist_row(
            cur,
            name=(album_artist_info or {}).get('name') or (existing_album_artist_row or {}).get('name') or (track_artist_info or {}).get('name') or 'Unknown Artist',
            library_id=(existing_album_artist_row or {}).get('library_id'),
            hifi_id=effective_album_artist_hifi_id,
            confidence=confidence,
            last_seen_at=(existing_album_artist_row or {}).get('last_seen_at') or now_dt,
        )

    album_row_id = track_row.get('album_id')
    if existing_album_row or album_hifi_id:
        album_row_id = _upsert_album_row(
            cur,
            artist_id=album_artist_row_id,
            title=album_title or (existing_album_row or {}).get('title') or 'Unknown Album',
            library_id=(existing_album_row or {}).get('library_id'),
            hifi_id=album_hifi_id or (existing_album_row or {}).get('hifi_id'),
            confidence=confidence,
            complete=bool((existing_album_row or {}).get('complete')),
            last_seen_at=(existing_album_row or {}).get('last_seen_at') or now_dt,
            matched_track_count=_safe_int((existing_album_row or {}).get('matched_track_count')) or 0,
            expected_track_count=_safe_int((existing_album_row or {}).get('expected_track_count')) or 0,
        )

    _upsert_track_row(
        cur,
        album_id=album_row_id,
        artist_id=track_artist_row_id,
        title=track_row.get('title') or 'Unknown Track',
        path=track_row.get('path') or '',
        library_id=track_row.get('library_id'),
        hifi_id=track_hifi_id,
        confidence=confidence,
        last_seen_at=track_row.get('last_seen_at') or now_dt,
        audio_format=track_row.get('format'),
        bitrate=_safe_int(track_row.get('bitrate')),
        disc_number=_safe_int(track_row.get('disc_number')),
        track_number=_safe_int(track_row.get('track_number')),
        isrc=track_data.get('isrc') or existing_isrc,
        duration=track_data.get('duration') or existing_duration,
    )

    return album_row_id


def _refresh_album_completeness(cur, album_row):
    album_hifi_id = str(album_row.get('hifi_id') or '').strip()
    if not album_hifi_id:
        cur.execute(
            """
            UPDATE albums
            SET complete = FALSE,
                matched_track_count = 0,
                expected_track_count = 0
            WHERE album_id = %s
            """,
            (album_row['album_id'],)
        )
        return

    payload = _fetch_hifi_album_payload(album_hifi_id)
    album_data = payload.get('data') if isinstance(payload, dict) else {}
    items = album_data.get('items', []) if isinstance(album_data, dict) else []
    expected_track_ids = []
    for entry in items:
        if not isinstance(entry, dict) or entry.get('type') != 'track':
            continue
        candidate = entry.get('item') if isinstance(entry.get('item'), dict) else None
        if not candidate:
            continue
        candidate_id = str(candidate.get('id') or '').strip()
        if candidate_id:
            expected_track_ids.append(candidate_id)

    expected_track_count = len(expected_track_ids)
    if expected_track_ids:
        cur.execute(
            """
            SELECT COUNT(DISTINCT hifi_id) AS matched_count
            FROM tracks
            WHERE album_id = %s
              AND hifi_id = ANY(%s)
              AND hifi_id IS NOT NULL
            """,
            (album_row['album_id'], expected_track_ids)
        )
        row = cur.fetchone() or {}
        matched_track_count = _safe_int(row.get('matched_count')) or 0
    else:
        matched_track_count = 0

    complete = expected_track_count > 0 and matched_track_count >= expected_track_count
    cur.execute(
        """
        UPDATE albums
        SET complete = %s,
            matched_track_count = %s,
            expected_track_count = %s
        WHERE album_id = %s
        """,
        (complete, matched_track_count, expected_track_count, album_row['album_id'])
    )


def _build_stored_track_match_lookup(cur, track_ids):
    requested_ids = [str(track_id).strip() for track_id in (track_ids or []) if str(track_id).strip()]
    if not requested_ids:
        return []

    cur.execute(
        """
        SELECT hifi_id, confidence, format, bitrate, path
        FROM tracks
        WHERE hifi_id = ANY(%s)
          AND library_id IS NOT NULL
        ORDER BY hifi_id ASC,
                 confidence DESC,
                 bitrate DESC NULLS LAST,
                 path ASC
        """,
        (requested_ids,)
    )
    rows = cur.fetchall() or []

    grouped = {}
    for row in rows:
        hifi_id = str(row.get('hifi_id') or '').strip()
        if not hifi_id:
            continue
        grouped.setdefault(hifi_id, []).append(row)

    results = []
    for requested_id in requested_ids:
        matched_rows = grouped.get(requested_id, [])
        best_row = matched_rows[0] if matched_rows else None
        results.append({
            'track_id': requested_id,
            'exists': bool(matched_rows),
            'confidence': _safe_float(best_row.get('confidence')) if best_row else None,
            'variants': _serialize_match_variants(matched_rows),
        })

    return results


def _build_stored_album_match_lookup(cur, album_ids):
    requested_ids = [str(album_id).strip() for album_id in (album_ids or []) if str(album_id).strip()]
    if not requested_ids:
        return []

    cur.execute(
        """
        SELECT albums.hifi_id,
               albums.complete,
               albums.matched_track_count,
               albums.expected_track_count,
               albums.confidence,
               tracks.format,
               tracks.bitrate,
               tracks.path
        FROM albums
        LEFT JOIN tracks
          ON tracks.album_id = albums.album_id
         AND tracks.library_id IS NOT NULL
        WHERE albums.hifi_id = ANY(%s)
          AND albums.library_id IS NOT NULL
        ORDER BY albums.hifi_id ASC,
                 albums.confidence DESC,
                 tracks.track_id ASC
        """,
        (requested_ids,)
    )
    rows = cur.fetchall() or []

    grouped = {}
    for row in rows:
        hifi_id = str(row.get('hifi_id') or '').strip()
        if not hifi_id:
            continue
        grouped.setdefault(hifi_id, []).append(row)

    results = []
    for requested_id in requested_ids:
        matched_rows = grouped.get(requested_id, [])
        best_row = matched_rows[0] if matched_rows else None
        complete = any(bool(row.get('complete')) for row in matched_rows)
        results.append({
            'album_id': requested_id,
            'exists': bool(matched_rows),
            'complete': complete,
            'confidence': _safe_float(best_row.get('confidence')) if best_row else None,
            'matched_track_count': max((_safe_int(row.get('matched_track_count')) or 0) for row in matched_rows) if matched_rows else 0,
            'expected_track_count': max((_safe_int(row.get('expected_track_count')) or 0) for row in matched_rows) if matched_rows else 0,
            'variants': _serialize_match_variants(matched_rows),
        })

    return results


def _build_stored_artist_match_lookup(cur, artist_ids):
    requested_ids = [str(artist_id).strip() for artist_id in (artist_ids or []) if str(artist_id).strip()]
    if not requested_ids:
        return []

    cur.execute(
        """
        SELECT artists.hifi_id,
               COALESCE(bool_and(albums.complete), TRUE) AS complete
        FROM artists
        LEFT JOIN albums
          ON albums.artist_id = artists.artist_id
        WHERE artists.hifi_id = ANY(%s)
          AND artists.library_id IS NOT NULL
        GROUP BY artists.hifi_id
        """,
        (requested_ids,)
    )
    rows = cur.fetchall() or []

    grouped = {}
    for row in rows:
        hifi_id = str(row.get('hifi_id') or '').strip()
        if not hifi_id:
            continue
        grouped[hifi_id] = row

    results = []
    for requested_id in requested_ids:
        row = grouped.get(requested_id)
        results.append({
            'artist_id': requested_id,
            'exists': bool(row),
            'complete': bool(row.get('complete')) if row else False,
            'confidence': None,
            'variants': []
        })

    return results


def _fetch_match_review_row(cur, entity_type, entity_id):
    if entity_type == 'artist':
        cur.execute(
            """
            SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
            FROM artists
            WHERE artist_id = %s
            """,
            (entity_id,)
        )
        return cur.fetchone()

    if entity_type == 'album':
        cur.execute(
            """
            SELECT albums.album_id, albums.artist_id, albums.title, albums.library_id, albums.hifi_id,
                   albums.confidence, albums.complete, albums.matched_track_count,
                   albums.expected_track_count, albums.last_seen_at,
                   artists.name AS artist_name,
                   artists.hifi_id AS artist_hifi_id,
                   COUNT(tracks.track_id) AS library_track_count
            FROM albums
            LEFT JOIN artists ON artists.artist_id = albums.artist_id
            LEFT JOIN tracks ON tracks.album_id = albums.album_id AND tracks.library_id IS NOT NULL
            WHERE albums.album_id = %s
            GROUP BY albums.album_id, artists.name, artists.hifi_id
            """,
            (entity_id,)
        )
        return cur.fetchone()

    if entity_type == 'track':
        cur.execute(
            """
            SELECT tracks.track_id, tracks.album_id, tracks.artist_id, tracks.title, tracks.library_id,
                   tracks.hifi_id, tracks.confidence, tracks.path, tracks.format, tracks.bitrate,
                   tracks.disc_number, tracks.track_number, tracks.last_seen_at, tracks.isrc, tracks.duration,
                   albums.title AS album_title,
                   albums.hifi_id AS album_hifi_id,
                   artists.name AS artist_name
            FROM tracks
            LEFT JOIN albums ON albums.album_id = tracks.album_id
            LEFT JOIN artists ON artists.artist_id = tracks.artist_id
            WHERE tracks.track_id = %s
            """,
            (entity_id,)
        )
        return cur.fetchone()

    return None


def _build_artist_match_candidates(row, limit=10, query_override=None):
    search_query = str(query_override or row.get('name') or '').strip()
    if not search_query:
        return []

    candidates = _fetch_hifi_search_results('a', search_query, limit=limit)
    scored = []
    seen = set()
    for candidate in candidates:
        hifi_id = str(candidate.get('id') or '').strip()
        candidate_name = str(candidate.get('name') or '').strip()
        if not hifi_id or not candidate_name or hifi_id in seen:
            continue
        seen.add(hifi_id)
        confidence = _score_artist_candidate_name(row.get('name'), candidate_name)
        if confidence <= 0:
            continue
        scored.append({
            'hifi_id': hifi_id,
            'title': candidate_name,
            'subtitle': 'Artist',
            'confidence': confidence,
            'image_url': _format_hifi_image_value(candidate.get('picture'), size=MATCH_REVIEW_HIFI_ARTIST_ARTWORK_SIZE),
        })

    scored.sort(key=lambda candidate: (-candidate['confidence'], candidate['title'].lower()))
    return scored[:limit]


def _build_album_match_candidates(row, limit=10, query_override=None, source_track_titles=None):
    candidates = []
    seen = set()
    search_query = str(query_override or row.get('title') or '').strip()
    artist_hifi_id = str(row.get('artist_hifi_id') or '').strip()
    artist_name = str(row.get('artist_name') or '').strip()

    def build_search_queries():
        base_title = search_query
        stripped_title = re.sub(r'\s*\([^)]*\)', '', base_title).strip()

        ordered = []
        for query in (
            base_title,
            f"{artist_name} {base_title}".strip() if artist_name else '',
            stripped_title,
            f"{artist_name} {stripped_title}".strip() if artist_name and stripped_title else '',
        ):
            query = str(query or '').strip()
            if query and query not in ordered:
                ordered.append(query)
        return ordered

    def collect_candidates(source_candidates):
        added_any = False
        for candidate in source_candidates:
            evaluated = _evaluate_album_candidate(row, candidate, source_track_titles=source_track_titles)
            if not evaluated:
                continue
            hifi_id = evaluated.get('hifi_id')
            if not hifi_id or hifi_id in seen:
                continue
            seen.add(hifi_id)
            candidates.append(evaluated)
            added_any = True
        return added_any

    if artist_hifi_id and not query_override:
        payload = _fetch_hifi_artist_payload(artist_hifi_id)
        artist_albums = payload.get('albums', {}).get('items', []) if isinstance(payload.get('albums'), dict) else []
        found_from_artist = collect_candidates(artist_albums)
        if not found_from_artist:
            for candidate_query in build_search_queries():
                collect_candidates(_fetch_hifi_search_results('al', candidate_query, limit=max(limit * 2, 20)))
    else:
        for candidate_query in build_search_queries():
            collect_candidates(_fetch_hifi_search_results('al', candidate_query, limit=max(limit * 2, 20)))

    candidates.sort(key=lambda candidate: (-candidate['confidence'], candidate['title'].lower()))
    return candidates[:limit]


def _build_track_match_candidates(row, limit=10, query_override=None):
    candidates = []
    seen = set()
    album_hifi_id = str(row.get('album_hifi_id') or '').strip()
    artist_name = str(row.get('artist_name') or '').strip()
    track_title = str(row.get('title') or '').strip()
    search_query = str(query_override or f"{artist_name} {track_title}".strip() or track_title).strip()

    if album_hifi_id and not query_override:
        payload = _fetch_hifi_album_payload(album_hifi_id)
        items = payload.get('data', {}).get('items', []) if isinstance(payload.get('data'), dict) else []
        source_candidates = []
        for entry in items:
            if not isinstance(entry, dict) or entry.get('type') != 'track':
                continue
            candidate = entry.get('item') if isinstance(entry.get('item'), dict) else None
            if candidate:
                source_candidates.append(candidate)
    else:
        source_candidates = _fetch_hifi_search_results('s', search_query, limit=limit)

    for candidate in source_candidates:
        hifi_id = str(candidate.get('id') or '').strip()
        title = str(candidate.get('title') or '').strip()
        if not hifi_id or not title or hifi_id in seen:
            continue
        seen.add(hifi_id)

        confidence = _score_track_candidate_payload(row, candidate)
        if confidence <= 0:
            continue

        artist_names = []
        if isinstance(candidate.get('artists'), list):
            artist_names = [str(item.get('name') or '').strip() for item in candidate.get('artists') if isinstance(item, dict) and str(item.get('name') or '').strip()]
        elif isinstance(candidate.get('artist'), dict):
            name = str(candidate.get('artist', {}).get('name') or '').strip()
            if name:
                artist_names = [name]

        album_title = ''
        if isinstance(candidate.get('album'), dict):
            album_title = str(candidate.get('album', {}).get('title') or '').strip()

        subtitle_parts = []
        if artist_names:
            subtitle_parts.append(', '.join(artist_names))
        elif row.get('artist_name'):
            subtitle_parts.append(str(row.get('artist_name')).strip())
        if album_title:
            subtitle_parts.append(album_title)

        track_number = _safe_int(candidate.get('trackNumber'))
        if track_number:
            subtitle_parts.append(f"Track {track_number}")

        album_data = candidate.get('album') if isinstance(candidate.get('album'), dict) else {}

        candidates.append({
            'hifi_id': hifi_id,
            'title': title,
            'subtitle': ' \u2022 '.join(part for part in subtitle_parts if part),
            'confidence': confidence,
            'image_url': _format_hifi_image_value(album_data.get('cover') or candidate.get('cover'), size=MATCH_REVIEW_HIFI_ARTWORK_SIZE),
            'explicit': _is_hifi_explicit(candidate),
        })

    candidates.sort(key=lambda candidate: (-candidate['confidence'], candidate['title'].lower()))
    return candidates[:limit]



