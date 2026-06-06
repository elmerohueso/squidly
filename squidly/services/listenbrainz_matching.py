"""ListenBrainz playlist batch matching service.

Matches ListenBrainz tracks to HiFi catalog using MBID→ISRC lookup
with text search fallback. Reusable by both the API layer and job system.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from squidly.services.hifi import _fetch_hifi_search_results
from squidly.services.playlist_matching import (
    _normalize_match_text_for_scoring,
    _score_track_candidate,
)
from squidly.services.track_resolver import resolve_track

logger = logging.getLogger(__name__)

_MBID_RE = re.compile(r'recording/([a-f0-9-]+)', re.IGNORECASE)
_ISRC_SCORE_THRESHOLD = 0.80
_FALLBACK_SCORE_THRESHOLD = 0.90


def _album_match_bonus(lb_album: str, item_album: str) -> int:
    """Return bonus points for album name match quality.

    Used as a tiebreaker when multiple ISRC candidates have the same score.
    Higher values indicate better album name alignment.
    """
    if not lb_album or not item_album:
        return 0
    norm_lb = _normalize_match_text_for_scoring(lb_album)
    norm_item = _normalize_match_text_for_scoring(item_album)
    if norm_lb == norm_item:
        return 100
    if norm_lb in norm_item or norm_item in norm_lb:
        return 50
    return 0


def match_listenbrainz_tracks(
    tracks: List[Dict[str, Any]],
    settings: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Batch-match ListenBrainz tracks to HiFi catalog.

    Args:
        tracks: List of dicts with keys: 'title', 'artist', 'album', 'identifier'.
        settings: Download settings dict (from get_download_settings()).

    Returns:
        List of result dicts aligned 1:1 with input tracks.
        Each result: { 'title', 'artist', 'match', 'method', 'confidence', 'error' }
    """
    # Step 1: Parallel-fetch all ISRCs from MusicBrainz
    isrc_map = _fetch_isrcs_batch(tracks)

    # Step 2: Match each track sequentially (HiFi mirror rate limits)
    results = []
    for track in tracks:
        title = str(track.get('title') or '').strip()
        artist = str(track.get('artist') or '').strip()
        album = str(track.get('album') or '').strip()
        identifier = str(track.get('identifier') or '').strip()

        result = _match_single_track(title, artist, album, identifier, isrc_map, settings)
        results.append(result)

    return results


def _fetch_isrcs_batch(tracks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Parallel-fetch ISRCs from MusicBrainz for all tracks with recording MBIDs.

    Returns:
        Dict mapping MBID string -> list of ISRC strings.
        Tracks without a valid MBID are skipped.
    """
    # Extract unique MBIDs
    mbid_to_tracks: Dict[str, None] = {}
    for track in tracks:
        identifier = str(track.get('identifier') or '')
        mbid_match = _MBID_RE.search(identifier)
        if mbid_match:
            mbid = mbid_match.group(1)
            if mbid not in mbid_to_tracks:
                mbid_to_tracks[mbid] = None

    if not mbid_to_tracks:
        return {}

    isrc_map: Dict[str, List[str]] = {}
    mbids = list(mbid_to_tracks.keys())

    def _fetch_one_isrc(mbid: str) -> tuple:
        try:
            from squidly.services.musicbrainz import mb_get_recording
            rec = mb_get_recording(mbid)
            return (mbid, rec.get('isrcs') or [])
        except Exception:
            pass
        return (mbid, [])

    # ThreadPoolExecutor is used for convenience; the centralized rate limiter in musicbrainz.py
    # serializes all requests to ~1 req/sec regardless of worker count.
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one_isrc, mbid): mbid for mbid in mbids}
        for future in as_completed(futures):
            mbid, isrcs = future.result()
            isrc_map[mbid] = isrcs

    return isrc_map


def _match_single_track(
    title: str,
    artist: str,
    album: str,
    identifier: str,
    isrc_map: Dict[str, List[str]],
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Match a single ListenBrainz track to HiFi.

    Pipeline: ISRC search -> text search fallback -> score -> resolve.
    """
    if not title or not artist:
        return {
            'title': title, 'artist': artist,
            'match': None, 'method': None, 'confidence': 0.0,
            'error': 'title and artist are required',
        }

    # Look up ISRCs from pre-fetched map
    isrcs: List[str] = []
    mbid_match = _MBID_RE.search(identifier)
    if mbid_match:
        isrcs = isrc_map.get(mbid_match.group(1), [])

    best_match = None
    best_score = 0.0
    method = None

    # ISRC search — collect all candidates, then pick best by score + album match
    if isrcs:
        isrc_candidates: List[tuple] = []
        for isrc in isrcs:
            results = _fetch_hifi_search_results('i', isrc, limit=30)
            for item in results:
                score = _score_track_candidate(title, artist, album, item)
                isrc_candidates.append((score, item))

        if isrc_candidates:
            # Sort by score descending, then by album match bonus for tie-breaking
            isrc_candidates.sort(key=lambda x: (
                x[0],
                _album_match_bonus(album, (x[1].get('album') or {}).get('title') or '')
            ), reverse=True)
            best_score, best_match = isrc_candidates[0]
            method = 'isrc'

    # Conditional text search fallback — only if ISRC search found nothing
    # Use a higher threshold (0.90) to avoid karaoke/covers
    if not best_match and isrcs:
        query = f'{title} {artist}'
        results = _fetch_hifi_search_results('s', query, limit=50)
        for item in results:
            score = _score_track_candidate(title, artist, album, item)
            if score >= _FALLBACK_SCORE_THRESHOLD and score > best_score:
                best_score = score
                best_match = item
                method = 'text'

    if best_match:
        try:
            result = resolve_track(
                title=title,
                track_artist=artist,
                album=album,
                isrc=isrcs[0] if isrcs else None,
                hifi_id=str(best_match.get('id')),
                settings=settings,
            )
            new_id = result.get('hifi_id')
            if new_id and str(new_id) != str(best_match.get('id')):
                logger.info("[LB_MATCH] Resolved %s - %s (%s, source=%s) -> %s",
                            artist, title, result['reason'], result['source'], new_id)
                from squidly.services.hifi import _fetch_hifi_track_info_payload, extract_hifi_track_info
                raw = _fetch_hifi_track_info_payload(new_id)
                if raw:
                    resolved_info = extract_hifi_track_info(raw)
                    if resolved_info:
                        best_match = resolved_info
        except Exception as e:
            logger.warning("[LB_MATCH] resolve_track failed for %s - %s: %s",
                           artist, title, e)

    return {
        'title': title,
        'artist': artist,
        'match': best_match,
        'method': method,
        'confidence': min(best_score, 1.0),
        'error': None,
    }
