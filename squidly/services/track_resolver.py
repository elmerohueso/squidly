"""Track resolution to best available hifi ID via ISRC-first pipeline.

Pipeline:
1. If hifi_id provided, fetch track metadata to get ISRC, album info
2. If no ISRC, try MusicBrainz text search
3. If ISRC available, search hifi by ISRC and rank results
4. Return best hifi_id (or original if no ISRC available)

Usage:
    from squidly.services.track_resolver import resolve_track
    result = resolve_track(title, artist, album, year=2024, isrc='US...', hifi_id='123', settings={})
"""

import logging
import re
import time
from typing import Any, Optional

import requests

from squidly.services.hifi import (
    _fetch_hifi_album_payload,
    _fetch_hifi_search_results,
    _fetch_hifi_track_info_payload,
    extract_hifi_track_info,
)
from squidly.services.playlist_matching import _normalize_match_text_for_scoring

logger = logging.getLogger(__name__)

_album_cache: dict = {}

_MUSICBRAINZ_USER_AGENT = 'Squidly/1.0 (https://github.com/elmerohueso/squidly)'

# ── Detection helpers ──

COMPILATION_KEYWORDS = (
    'greatest hits', 'best of', 'mixtape', 'essence', 'classics',
    'hits of', 'throwback', 'anthology', 'collection', 'singles collection',
    'number ones', 'greatest', 'ultimate', 'essential', 'definitive',
    'now that', 'presents', 'the best', 'complete', 'vol. ',
    'direct hits', 'original hits', 'gold', 'chronicles', 'decades',
    'icon', 'playlist', 'b-sides', 'b sides', 'bsides', 'rarities',
    'grandes exitos', 'lo mejor de', 'exitos', 'lo mejor',
)

SOUNDTRACK_KEYWORDS = (
    'soundtrack', 'original motion picture', 'music from',
    'tv series', 'from the motion picture',
)

LIVE_VERSION_KEYWORDS = (
    'live', 'concert', 'unplugged', 'acoustic', 'from ',
)

DELUXE_KEYWORDS = (
    'deluxe', 'expanded', 'remaster', 'anniversary edition',
    'special edition', 'extended', 'collector', 'super deluxe',
    'reissue', 're-master', 'bonus track',
)


def _has_any(texts, keywords):
    t = ' '.join(texts).lower()
    return any(kw in t for kw in keywords)


def _has_live_version_indicator(track_data):
    """Check if the track version indicates a live recording."""
    version = str(track_data.get('version') or '').strip().lower()
    if not version:
        return False
    return any(kw in version for kw in LIVE_VERSION_KEYWORDS)


def _has_deluxe_indicator(album_title, version=''):
    """Check if album title or version suggests a deluxe/remaster edition."""
    combined = f"{album_title} {version}".lower()
    return any(kw in combined for kw in DELUXE_KEYWORDS)


def _parse_release_year(release_date):
    """Extract year from release date string for comparison. Returns '9999' if missing."""
    if not release_date or not isinstance(release_date, str):
        return '9999'
    return release_date[:4] if len(release_date) >= 4 else '9999'


def _is_compilation_from_search_data(item):
    """Lightweight compilation check using only search result data (no album fetch needed)."""
    album = item.get('album') or {}
    album_title = str(album.get('title') or '')
    if _has_any([album_title], COMPILATION_KEYWORDS):
        return True

    # Artist mismatch: track artists vs album artists
    track_artists = set()
    for a in (item.get('artists') or []):
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                track_artists.add(n)

    album_artists_raw = album.get('artists') or []
    if not album_artists_raw and album.get('artist'):
        album_artists_raw = [album['artist']]
    album_artists = set()
    for a in album_artists_raw:
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                album_artists.add(n)

    if track_artists and album_artists:
        if any('various' in n for n in album_artists):
            return True
        if not (track_artists & album_artists):
            return True
        if len(album_artists) >= 3 and track_artists.issubset(album_artists) and len(track_artists) < len(album_artists):
            return True
    return False


def _is_single(track_data, album_data):
    if album_data and album_data.get('type') in ('SINGLE', 'EP'):
        return True
    if album_data and album_data.get('type') == 'ALBUM':
        return False
    num = track_data.get('album', {}).get('numberOfTracks') or (album_data or {}).get('numberOfTracks')
    return num is not None and isinstance(num, (int, float)) and int(num) <= 4


def _is_soundtrack(track_data, album_data):
    """Check album and track for soundtrack indicators."""
    title = str(track_data.get('title') or '')
    version = str(track_data.get('version') or '')
    album_title = str((album_data or track_data.get('album', {})).get('title') or '')
    if _has_any([album_title], SOUNDTRACK_KEYWORDS):
        return True
    if re.search(r'from\s+["\u201c\u201d]', f'{title} {version}'.lower()):
        return True
    if _has_any([title, version], ['soundtrack', 'motion picture']):
        return True
    return False


def _is_compilation(track_data, album_data):
    """True if the track is on a compilation (not a soundtrack)."""
    if _is_soundtrack(track_data, album_data):
        return False
    if album_data and album_data.get('type') in ('SINGLE', 'EP'):
        return False

    album_title = str((album_data or track_data.get('album', {})).get('title') or '')
    if _has_any([album_title], COMPILATION_KEYWORDS):
        return True

    # Artist mismatch: track artist != album artist (various-artists compilations)
    track_artists = set()
    for a in (track_data.get('artists') or []):
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                track_artists.add(n)
    if not track_artists and isinstance(track_data.get('artist'), dict):
        n = str(track_data['artist'].get('name') or '').strip().lower()
        if n:
            track_artists.add(n)

    album_artist_data = (album_data or track_data.get('album', {})).get('artists') or []
    if not album_artist_data and album_data and album_data.get('artist'):
        album_artist_data = [album_data['artist']]
    album_artists = set()
    for a in album_artist_data:
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                album_artists.add(n)

    if track_artists and album_artists:
        if any('various' in n for n in album_artists):
            return True
        if not (track_artists & album_artists):
            return True
        if len(album_artists) >= 3 and track_artists.issubset(album_artists) and len(track_artists) < len(album_artists):
            return True
    return False


def _fetch_album(album_id):
    if album_id not in _album_cache:
        raw = _fetch_hifi_album_payload(album_id)
        _album_cache[album_id] = raw.get('data') if isinstance(raw, dict) and isinstance(raw.get('data'), dict) else None
    return _album_cache[album_id]


# ── New helpers ──

def _extract_primary_artist_name(track_info: dict) -> str:
    """Extract primary artist name from extract_hifi_track_info output."""
    artists = track_info.get('track_artists') or []
    for a in artists:
        if isinstance(a, dict):
            name = str(a.get('name') or '').strip()
            if name:
                return name
    return ''


def _isrc_from_musicbrainz(title: str, artist: str, album: str = "", year: Optional[int] = None) -> Optional[str]:
    """Search MusicBrainz for an ISRC by text. Returns first ISRC or None."""
    query_parts = [f'recording:"{title}"', f'artist:"{artist}"']
    if album:
        query_parts.append(f'release:"{album}"')
    if year:
        query_parts.append(f'firstreleasedate:{year}')
    query = ' AND '.join(query_parts)

    try:
        resp = requests.get(
            'https://musicbrainz.org/ws/2/recording/',
            params={'query': query, 'fmt': 'json', 'limit': 5},
            headers={'User-Agent': _MUSICBRAINZ_USER_AGENT},
            timeout=10,
        )
        if resp.status_code == 429:
            logger.warning("[RESOLVE] MusicBrainz rate limited (429), skipping ISRC lookup for '%s' by '%s'", title, artist)
            return None
        if resp.status_code == 503:
            time.sleep(1)
            resp = requests.get(
                'https://musicbrainz.org/ws/2/recording/',
                params={'query': query, 'fmt': 'json', 'limit': 5},
                headers={'User-Agent': _MUSICBRAINZ_USER_AGENT},
                timeout=10,
            )
        if not resp.ok:
            logger.warning("[RESOLVE] MusicBrainz returned %d for '%s' by '%s'", resp.status_code, title, artist)
            return None

        recordings = resp.json().get('recordings', [])
        for rec in recordings:
            isrcs = rec.get('isrcs') or []
            if isrcs:
                return isrcs[0]
    except requests.exceptions.RequestException as e:
        logger.warning("[RESOLVE] MusicBrainz request failed: %s", e)
    return None


def _artists_overlap(track_artist: str, item_artists: list) -> bool:
    """Check if the provided track artist overlaps with hifi item artists (normalized)."""
    norm_track = _normalize_match_text_for_scoring(track_artist)
    if not norm_track:
        return True  # no artist provided, don't filter

    for a in (item_artists or []):
        if isinstance(a, dict):
            name = str(a.get('name') or '').strip()
            norm_item = _normalize_match_text_for_scoring(name)
            if norm_item and (norm_track in norm_item or norm_item in norm_track):
                return True
    return False


def _get_hifi_quality_rank(quality: Optional[str]) -> int:
    """Return numeric rank for audio quality (higher = better)."""
    ranks = {
        'HI_RES_LOSSLESS': 5,
        'LOSSLESS': 4,
        'HIGH': 3,
        'LOW': 1,
    }
    return ranks.get(quality, 2)


# ── Filtering and ranking ──

def _filter_and_rank_isrc_results(
    items, title, track_artist, album,
    original_is_soundtrack, original_hifi_id,
    caller_album_data=None, settings=None,
):
    """Filter and rank ISRC search results using tiered tuple scoring.

    Ranking dimensions (lower = better):
      0. compilation_tier: 0=studio, 1=compilation
      1. release_date: earliest wins ('YYYY'), missing='9999'
      2. album_mismatch: 0=title matches caller's album, 1=doesn't
      3. is_deluxe: 0=standard, 1=deluxe/remaster/expanded
      4. is_live: 0=studio, 1=live variant
      5. quality_inv: inverted quality rank (lower = better quality)
    """
    settings = settings or {}
    norm_title = _normalize_match_text_for_scoring(title)
    norm_album = _normalize_match_text_for_scoring(album)

    penalty_comp = settings.get('penalty_compilation', True)
    penalty_live = settings.get('penalty_live', True)
    penalty_single = settings.get('penalty_single', True)

    candidates = []

    for item in items:
        item_id = str(item.get('id'))
        item_title = str(item.get('title') or '')
        item_artists = item.get('artists') or []
        item_album = item.get('album') or {}
        item_album_title = str(item_album.get('title') or '')
        item_version = str(item.get('version') or '')

        # ── Hard filters ──

        # Title must match (normalized)
        norm_item_title = _normalize_match_text_for_scoring(item_title)
        if not norm_item_title or not norm_title:
            continue
        if (norm_item_title != norm_title
                and norm_title not in norm_item_title
                and norm_item_title not in norm_title):
            continue

        # Artist must overlap
        if not _artists_overlap(track_artist, item_artists):
            continue

        # Skip the original track
        if item_id == original_hifi_id:
            continue

        # ── Tier 0: compilation detection ──
        comp_tier = 0
        if penalty_comp and _is_compilation_from_search_data(item):
            comp_tier = 1

        # ── Tier 1: release date (from embedded album data) ──
        release_date = item_album.get('releaseDate') or ''
        release_year = _parse_release_year(release_date)

        # ── Tier 2: album title match ──
        norm_item_album = _normalize_match_text_for_scoring(item_album_title)
        album_mismatch = 1
        if norm_album and norm_item_album and norm_item_album == norm_album:
            album_mismatch = 0

        # ── Tier 3: deluxe/remaster indicator ──
        is_deluxe = 1 if _has_deluxe_indicator(item_album_title, item_version) else 0

        # ── Tier 4: live variant ──
        is_live = 1 if (penalty_live and _has_live_version_indicator(item)) else 0

        # ── Tier 5: audio quality (inverted — lower rank = better quality) ──
        quality = item.get('maxAudioQuality') or item.get('audioQuality')
        quality_inv = 5 - _get_hifi_quality_rank(quality)

        sort_key = (comp_tier, release_year, album_mismatch, is_deluxe, is_live, quality_inv)
        candidates.append((sort_key, item))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])

    # ── Phase 2: Resolve ties with full album data if needed ──
    top_key = candidates[0][0]
    top_items = [(k, it) for k, it in candidates if k == top_key]

    if len(top_items) == 1:
        return top_items[0][1]

    # Multiple candidates tie on all dimensions.
    # Collect distinct album IDs and fetch full album data.
    album_ids_to_fetch = set()
    for _, item in top_items:
        album_id = (item.get('album') or {}).get('id')
        if album_id:
            album_ids_to_fetch.add(album_id)

    for album_id in album_ids_to_fetch:
        _fetch_album(album_id)  # populates _album_cache

    # Re-sort top items using full album data.
    def _refined_key(item):
        album_id = (item.get('album') or {}).get('id')
        full_album = _album_cache.get(album_id) if album_id else None

        # Re-check compilation with full album type info
        refined_comp = 0
        if penalty_comp and full_album:
            if full_album.get('type') in ('SINGLE', 'EP'):
                pass  # single/EP, not a compilation
            elif _is_compilation(item, full_album):
                refined_comp = 1

        # Prefer non-single/EP
        is_single = 1 if (penalty_single and full_album and full_album.get('type') in ('SINGLE', 'EP')) else 0

        # Use numberOfTracks as tiebreaker (more tracks = more likely a real album)
        num_tracks = -(full_album.get('numberOfTracks') or 0) if full_album else 0

        quality = item.get('maxAudioQuality') or item.get('audioQuality')
        quality_inv = 5 - _get_hifi_quality_rank(quality)

        return (refined_comp, is_single, num_tracks, quality_inv)

    top_items.sort(key=lambda x: _refined_key(x[1]))
    return top_items[0][1]


# ── Main entry point ──

def resolve_track(
    title: str,
    track_artist: str,
    album: str = "",
    year: Optional[int] = None,
    isrc: Optional[str] = None,
    hifi_id: Optional[str] = None,
    settings: Optional[dict] = None,
) -> dict:
    """Resolve a track to the best available hifi ID.

    Pipeline:
    1. If hifi_id provided, fetch track metadata to get ISRC, album info
    2. If no ISRC, try MusicBrainz text search
    3. If ISRC available, search hifi by ISRC and rank results
    4. Return best hifi_id (or original if no ISRC available)

    Returns:
        {
            'hifi_id': str | None,
            'reason': str,
            'source': 'isrc' | 'original' | 'fetch_error',
        }
    """
    settings = settings or {}
    original_hifi_id = str(hifi_id) if hifi_id else None

    # Step 1: If hifi_id provided, fetch track metadata
    track_info = None
    album_data = None
    if original_hifi_id:
        raw = _fetch_hifi_track_info_payload(original_hifi_id)
        if raw:
            track_info = extract_hifi_track_info(raw)

        if track_info:
            if not isrc and track_info.get('isrc'):
                isrc = track_info['isrc']
            if not title and track_info.get('title'):
                title = track_info['title']
            if not track_artist:
                track_artist = _extract_primary_artist_name(track_info)

            # Fetch album data for soundtrack detection
            album_id = track_info.get('album_id')
            if album_id:
                album_data = _fetch_album(album_id)

    # Step 2: If no ISRC, try MusicBrainz
    if not isrc and title and track_artist:
        isrc = _isrc_from_musicbrainz(title, track_artist, album, year)
        if isrc:
            logger.info("[RESOLVE] MusicBrainz resolved ISRC %s for '%s' by '%s'", isrc, title, track_artist)

    # Step 3: Determine if original album is a soundtrack
    original_is_soundtrack = False
    if track_info and album_data:
        original_is_soundtrack = _is_soundtrack(track_info, album_data)

    # Step 4: ISRC search path
    if isrc:
        items = _fetch_hifi_search_results('i', isrc, limit=50)
        if items:
            best = _filter_and_rank_isrc_results(
                items, title, track_artist, album,
                original_is_soundtrack, original_hifi_id,
                caller_album_data=album_data, settings=settings,
            )
            if best:
                best_id = str(best.get('id'))
                if best_id == original_hifi_id:
                    return {'hifi_id': best_id, 'reason': 'isrc_match_original', 'source': 'original'}
                logger.info("[RESOLVE] ISRC %s: %s (%s) -> %s", isrc, title, track_artist, best_id)
                logger.info(
                    "[RESOLVE] ISRC %s ranked %d candidates, selected %s from album '%s'",
                    isrc, len(items), best_id,
                    (best.get('album') or {}).get('title', 'unknown')
                )
                return {'hifi_id': best_id, 'reason': 'isrc_match', 'source': 'isrc'}

    # No ISRC available — log and return original (or None)
    if not isrc:
        label = f"'{title}' by '{track_artist}'" if title and track_artist else f"hifi_id={original_hifi_id}"
        logger.info("[RESOLVE] No ISRC for %s, skipping resolution", label)

    if original_hifi_id:
        return {'hifi_id': original_hifi_id, 'reason': 'no_isrc', 'source': 'original'}
    return {'hifi_id': None, 'reason': 'no_isrc', 'source': 'original'}
