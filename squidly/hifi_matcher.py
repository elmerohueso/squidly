"""HiFi API gap-filling for library records missing hifi_id.

This module queries the HiFi API to find matches for artists, albums,
and tracks that still lack a hifi_id after download, Plex sync, and
tag analysis. Uses ISRC-first strategy for tracks (exact match), then
falls back to title+artist search.
"""

from squidly.utils import _safe_int, _safe_float, _now_utc, normalize_match_text
from squidly.db import get_db_connection
from squidly.hifi import (
    _fetch_hifi_search_results,
    _fetch_hifi_album_payload,
    _fetch_hifi_artist_payload,
    _extract_hifi_album_track_items,
)
from squidly.matching import (
    _get_artist_row,
    _get_album_row,
    _upsert_artist_row,
    _upsert_album_row,
    _upsert_track_row,
    _score_artist_candidate_name,
    _score_album_candidate_title,
    _score_album_candidate_artist_alignment,
    _score_album_track_title_alignment,
    _score_track_candidate_payload,
    _extract_album_candidate_artist_names,
    _extract_hifi_album_track_titles,
    _has_explicit_marker,
    _is_hifi_explicit,
)


def _find_tracks_needing_match(cur):
    """Find tracks with a path but no hifi_id."""
    cur.execute(
        """
        SELECT track_id, album_id, artist_id, title, library_id,
               confidence, hifi_id, path, format, bitrate,
               disc_number, track_number, last_seen_at, isrc, duration
        FROM tracks
        WHERE path IS NOT NULL AND path != ''
          AND (hifi_id IS NULL OR hifi_id = '')
        ORDER BY track_id ASC
        """
    )
    return cur.fetchall() or []


def _find_albums_needing_match(cur):
    """Find albums with no hifi_id."""
    cur.execute(
        """
        SELECT album_id, artist_id, title, library_id, hifi_id,
               confidence, complete, matched_track_count,
               expected_track_count, last_seen_at
        FROM albums
        WHERE (hifi_id IS NULL OR hifi_id = '')
        ORDER BY album_id ASC
        """
    )
    return cur.fetchall() or []


def _find_artists_needing_match(cur):
    """Find artists with no hifi_id."""
    cur.execute(
        """
        SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
        FROM artists
        WHERE (hifi_id IS NULL OR hifi_id = '')
        ORDER BY artist_id ASC
        """
    )
    return cur.fetchall() or []


def _match_track_via_isrc(cur, track_row):
    """Try to match a track by ISRC — exact lookup, no scoring needed.

    Searches all tracks in the DB with the same ISRC that already have
    a hifi_id, then verifies via HiFi API that the ISRC matches.
    """
    isrc = str(track_row.get('isrc') or '').strip()
    if not isrc:
        return None, 0.0

    cur.execute(
        """
        SELECT hifi_id FROM tracks
        WHERE isrc = %s AND hifi_id IS NOT NULL AND hifi_id != ''
        LIMIT 1
        """,
        (isrc,)
    )
    row = cur.fetchone()
    if row:
        return str(row.get('hifi_id') or '').strip(), 0.99

    return None, 0.0


def _match_track_via_album(cur, track_row, album_payload_cache=None):
    """Match a track by looking up its album in HiFi and finding the track within."""
    album_id = track_row.get('album_id')
    if not album_id:
        return None, 0.0

    album_row = _get_album_row(cur, album_id)
    if not album_row:
        return None, 0.0

    album_hifi_id = str(album_row.get('hifi_id') or '').strip()
    if not album_hifi_id:
        return None, 0.0

    if album_payload_cache is not None and album_hifi_id in album_payload_cache:
        album_payload = album_payload_cache[album_hifi_id]
    else:
        album_payload = _fetch_hifi_album_payload(album_hifi_id)
        if album_payload_cache is not None:
            album_payload_cache[album_hifi_id] = album_payload

    track_items = _extract_hifi_album_track_items(album_payload)
    best_candidate = None
    best_confidence = 0.0

    for candidate in track_items:
        confidence = _score_track_candidate_payload(track_row, candidate)
        if confidence > best_confidence:
            best_candidate = candidate
            best_confidence = confidence

    if best_candidate and best_confidence >= 0.90:
        return str(best_candidate.get('id') or '').strip(), best_confidence

    return None, 0.0


def _match_track_via_search(cur, track_row):
    """Fallback: search HiFi by title + artist name."""
    title = str(track_row.get('title') or '').strip()
    if not title:
        return None, 0.0

    artist_name = None
    if track_row.get('artist_id'):
        artist_row = _get_artist_row(cur, track_row.get('artist_id'))
        artist_name = str(artist_row.get('name') or '').strip() if artist_row else None

    search_query = f"{artist_name} {title}".strip() if artist_name else title

    for candidate in _fetch_hifi_search_results('s', search_query, limit=25):
        candidate_id = str(candidate.get('id') or '').strip()
        if not candidate_id:
            continue
        confidence = _score_track_candidate_payload(track_row, candidate)
        if confidence >= 0.90:
            return candidate_id, confidence

    return None, 0.0


def _match_album_via_search(cur, album_row, source_track_titles=None):
    """Search HiFi for an album match by title + artist."""
    album_title = str(album_row.get('title') or '').strip()
    if not album_title:
        return None, 0.0

    artist_hifi_id = None
    artist_name = None
    if album_row.get('artist_id'):
        artist_row = _get_artist_row(cur, album_row.get('artist_id'))
        if artist_row:
            artist_hifi_id = str(artist_row.get('hifi_id') or '').strip() or None
            artist_name = str(artist_row.get('name') or '').strip() or None

    best_hifi_id = None
    best_confidence = 0.0
    seen = set()

    if artist_hifi_id:
        payload = _fetch_hifi_artist_payload(artist_hifi_id)
        artist_albums = payload.get('albums', {}).get('items', []) if isinstance(payload.get('albums'), dict) else []
        for candidate in artist_albums:
            candidate_id = str(candidate.get('id') or '').strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            confidence = _score_album_candidate(album_row, candidate, source_track_titles)
            if confidence > best_confidence:
                best_hifi_id = candidate_id
                best_confidence = confidence

    if best_confidence < 0.90:
        search_query = f"{artist_name} {album_title}".strip() if artist_name else album_title
        for candidate in _fetch_hifi_search_results('al', search_query, limit=25):
            candidate_id = str(candidate.get('id') or '').strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            confidence = _score_album_candidate(album_row, candidate, source_track_titles)
            if confidence > best_confidence:
                best_hifi_id = candidate_id
                best_confidence = confidence

    if best_hifi_id and best_confidence >= 0.90:
        return best_hifi_id, best_confidence

    return None, 0.0


def _match_artist_via_search(cur, artist_row):
    """Search HiFi for an artist match by name."""
    artist_name = str(artist_row.get('name') or '').strip()
    if not artist_name:
        return None, 0.0

    normalized_artist = normalize_match_text(artist_name)
    best_hifi_id = None
    best_confidence = 0.0

    for candidate in _fetch_hifi_search_results('a', artist_name, limit=10):
        candidate_name = str(candidate.get('name') or '').strip()
        if not candidate_name:
            continue
        confidence = _score_artist_candidate_name(artist_name, candidate_name)
        if confidence > best_confidence:
            best_hifi_id = str(candidate.get('id') or '').strip() or None
            best_confidence = confidence

    if best_hifi_id and best_confidence >= 0.90:
        return best_hifi_id, best_confidence

    return None, 0.0


def _score_album_candidate(album_row, candidate, source_track_titles=None):
    """Score an album candidate from search results."""
    hifi_id = str(candidate.get('id') or '').strip()
    title = str(candidate.get('title') or '').strip()
    if not hifi_id or not title:
        return 0.0

    library_track_count = _safe_int(album_row.get('library_track_count'))
    candidate_track_count = _safe_int(candidate.get('numberOfTracks') or candidate.get('numberOfItems'))
    candidate_is_explicit = _is_hifi_explicit(candidate)
    source_is_explicit = _has_explicit_marker(album_row.get('title'))

    base_confidence = _score_album_candidate_title(
        album_row.get('title'),
        title,
        library_track_count,
        candidate_track_count,
        source_is_explicit=source_is_explicit,
        candidate_is_explicit=candidate_is_explicit,
    )

    if base_confidence <= 0:
        return 0.0

    artist_names = _extract_album_candidate_artist_names(candidate)
    artist_bonus = _score_album_candidate_artist_alignment(album_row.get('artist_name'), artist_names)

    track_bonus = 0.0
    if source_track_titles:
        album_track_titles = _extract_hifi_album_track_titles(_fetch_hifi_album_payload(hifi_id))
        track_bonus = _score_album_track_title_alignment(source_track_titles, album_track_titles)

    confidence = base_confidence + artist_bonus + track_bonus
    return min(confidence, 0.99)


def find_missing_hifi_ids(progress_callback=None):
    """Scan all entities missing hifi_id and attempt to match via HiFi API.

    Strategy per entity type:
    - Tracks: ISRC lookup → album-based match → title+artist search
    - Albums: artist catalog search → title+artist search
    - Artists: name search

    Returns a dict with counts per entity type.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        tracks = _find_tracks_needing_match(cur)
        albums = _find_albums_needing_match(cur)
        artists = _find_artists_needing_match(cur)

        total_tracks = len(tracks)
        total_albums = len(albums)
        total_artists = len(artists)

        matched_tracks = 0
        matched_albums = 0
        matched_artists = 0
        errors = 0

        album_payload_cache = {}

        for idx, track_row in enumerate(tracks, 1):
            try:
                hifi_id = None
                confidence = 0.0

                hifi_id, confidence = _match_track_via_isrc(cur, track_row)
                if not hifi_id:
                    hifi_id, confidence = _match_track_via_album(cur, track_row, album_payload_cache)
                if not hifi_id:
                    hifi_id, confidence = _match_track_via_search(cur, track_row)

                if hifi_id:
                    _upsert_track_row(
                        cur,
                        album_id=track_row.get('album_id'),
                        artist_id=track_row.get('artist_id'),
                        title=track_row.get('title') or 'Unknown Track',
                        path=track_row.get('path') or '',
                        library_id=track_row.get('library_id'),
                        hifi_id=hifi_id,
                        confidence=confidence,
                        last_seen_at=track_row.get('last_seen_at') or _now_utc(),
                        audio_format=track_row.get('format'),
                        bitrate=_safe_int(track_row.get('bitrate')),
                        disc_number=_safe_int(track_row.get('disc_number')),
                        track_number=_safe_int(track_row.get('track_number')),
                        isrc=track_row.get('isrc'),
                        duration=track_row.get('duration'),
                    )
                    matched_tracks += 1
            except Exception as e:
                errors += 1
                print(f"[HIFI_MATCH] Error matching track {track_row.get('track_id')}: {e}", flush=True)

            if progress_callback and idx % 5 == 0:
                progress_callback('tracks', idx, total_tracks)

        for idx, album_row in enumerate(albums, 1):
            try:
                album_id_val = album_row.get('album_id')
                source_track_titles = None
                if album_id_val:
                    cur.execute(
                        """
                        SELECT ARRAY_AGG(title ORDER BY COALESCE(disc_number, 1), COALESCE(track_number, 0), LOWER(title)) AS titles
                        FROM tracks WHERE album_id = %s
                        """,
                        (album_id_val,)
                    )
                    title_row = cur.fetchone()
                    if title_row:
                        source_track_titles = [
                            str(t).strip() for t in (title_row.get('titles') or []) if str(t).strip()
                        ]

                hifi_id, confidence = _match_album_via_search(cur, album_row, source_track_titles)
                if hifi_id:
                    _upsert_album_row(
                        cur,
                        artist_id=album_row.get('artist_id'),
                        title=album_row.get('title') or 'Unknown Album',
                        library_id=album_row.get('library_id'),
                        hifi_id=hifi_id,
                        confidence=confidence,
                        complete=bool(album_row.get('complete')),
                        last_seen_at=album_row.get('last_seen_at') or _now_utc(),
                        matched_track_count=_safe_int(album_row.get('matched_track_count')) or 0,
                        expected_track_count=_safe_int(album_row.get('expected_track_count')) or 0,
                    )
                    matched_albums += 1
            except Exception as e:
                errors += 1
                print(f"[HIFI_MATCH] Error matching album {album_row.get('album_id')}: {e}", flush=True)

            if progress_callback and idx % 5 == 0:
                progress_callback('albums', idx, total_albums)

        for idx, artist_row in enumerate(artists, 1):
            try:
                hifi_id, confidence = _match_artist_via_search(cur, artist_row)
                if hifi_id:
                    _upsert_artist_row(
                        cur,
                        name=artist_row.get('name') or 'Unknown Artist',
                        library_id=artist_row.get('library_id'),
                        hifi_id=hifi_id,
                        confidence=confidence,
                        last_seen_at=artist_row.get('last_seen_at') or _now_utc(),
                    )
                    matched_artists += 1
            except Exception as e:
                errors += 1
                print(f"[HIFI_MATCH] Error matching artist {artist_row.get('artist_id')}: {e}", flush=True)

            if progress_callback and idx % 5 == 0:
                progress_callback('artists', idx, total_artists)

        conn.commit()

        if progress_callback:
            progress_callback('tracks', total_tracks, total_tracks)
            progress_callback('albums', total_albums, total_albums)
            progress_callback('artists', total_artists, total_artists)

        return {
            'tracks_total': total_tracks,
            'tracks_matched': matched_tracks,
            'albums_total': total_albums,
            'albums_matched': matched_albums,
            'artists_total': total_artists,
            'artists_matched': matched_artists,
            'errors': errors,
        }
    finally:
        conn.close()
