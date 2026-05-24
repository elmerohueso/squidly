"""Track detection and replacement for better-quality versions.

Detects tracks that are karaoke, live, singles/EPs, or on compilation
albums, then re-searches for a clean version from a proper studio album.

Usage:
    from squidly.track_resolver import resolve_track

    result = resolve_track(hifi_id, settings)
    # Returns: {'original_id': ..., 'reason': ..., 'replacement': {...} or None}
"""

import logging
import re
from typing import Any, Optional

from squidly.hifi import (
    _fetch_hifi_album_payload,
    _fetch_hifi_search_results,
    _fetch_hifi_track_info_payload,
)
from squidly.utils import normalize_match_text

logger = logging.getLogger(__name__)

# Regex for stripping trailing parenthetical version info
_STRIP_VERSION_RE = re.compile(r'\s*[\(\[].*[\)\]]\s*$')
REMASTER_PATTERN = re.compile(r'\bremaster(?:ed)?(?:\s+\d{4})?\b', re.IGNORECASE)

_album_cache: dict = {}


# ── Compilation keyword list ──
COMPILATION_KEYWORDS = (
    'greatest hits', 'best of', 'mixtape', 'essence', 'classics',
    'hits of', 'throwback', 'anthology', 'collection', 'singles collection',
    'number ones', 'greatest', 'ultimate', 'essential', 'definitive',
    'now that', 'presents', 'the best', 'complete', 'vol. ',
    'direct hits', 'original hits', 'gold', 'chronicles', 'decades',
    'icon', 'playlist',
    'grandes exitos', 'lo mejor de', 'exitos', 'lo mejor',
)


# ── Text helpers ──

def _strip_version_suffixes(title: str) -> str:
    return _STRIP_VERSION_RE.sub('', title).strip()


def _parse_primary_artist(raw_name: str) -> str:
    name = raw_name.strip()
    for sep in (';', ','):
        if sep in name:
            name = name.split(sep)[0].strip()
            break
    return name


def _get_artist_names(track_data: dict) -> set:
    names = set()
    for a in (track_data.get('artists') or []):
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                names.add(n)
    if not names and isinstance(track_data.get('artist'), dict):
        n = str(track_data['artist'].get('name') or '').strip().lower()
        if n:
            names.add(n)
    return names


def _artist_overlap(original: dict, candidate: dict) -> bool:
    orig = _get_artist_names(original)
    cand = _get_artist_names(candidate)
    if not orig or not cand:
        return True
    return bool(orig & cand)


# ── Detection helpers ──

def is_compilation_title(title: str) -> bool:
    t = title.lower()
    for kw in COMPILATION_KEYWORDS:
        if kw in t:
            return True
    return False


def is_karaoke_or_instrumental(title: str, version: str, album_title: str) -> bool:
    for text in (title.lower(), version.lower(), album_title.lower()):
        if 'karaoke' in text or 'instrumental' in text:
            return True
    return False


def is_live(title: str, version: str, album_title: str) -> bool:
    for text in (title.lower(), version.lower(), album_title.lower()):
        if re.search(r'\blive\b', text):
            return True
    return False


def is_remaster(title: str, version: str, album_title: str, album_version: str) -> bool:
    for text in (title, version, album_title, album_version):
        if REMASTER_PATTERN.search(text):
            return True
    return False


def is_single_or_ep(track_data: dict, album_data: Optional[dict] = None) -> bool:
    num = None
    album = track_data.get('album') or {}
    if album.get('numberOfTracks') is not None:
        num = album['numberOfTracks']
    elif album_data and album_data.get('numberOfTracks') is not None:
        num = album_data['numberOfTracks']
    if num is not None and isinstance(num, (int, float)):
        return int(num) <= 4
    return False


def is_compilation(track_data: dict, album_data: Optional[dict] = None) -> bool:
    # Signal 1: album title keywords
    album = track_data.get('album') or {}
    album_title = str(album.get('title') or '')
    if album_data:
        album_title = str(album_data.get('title') or album_title)
    if is_compilation_title(album_title):
        return True

    # Signal 2: track artist != album artist
    track_artists = _get_artist_names(track_data)
    album_artists_data = album_data.get('artists') if album_data else None
    if album_artists_data is None:
        album_artists_data = album.get('artists') or []
    if isinstance(album_data, dict) and album_data.get('artist'):
        if not album_artists_data:
            album_artists_data = [album_data['artist']]

    album_artist_names = set()
    for a in album_artists_data:
        if isinstance(a, dict):
            n = str(a.get('name') or '').strip().lower()
            if n:
                album_artist_names.add(n)

    if track_artists and album_artist_names:
        if any('various' in n for n in album_artist_names):
            return True
        if not (track_artists & album_artist_names):
            return True

    return False


# ── Detect all problems ──

def detect_problems(track_data: dict, album_data: Optional[dict] = None) -> list:
    title = str(track_data.get('title') or '')
    version = str(track_data.get('version') or '')
    album = track_data.get('album') or {}
    album_title = str(album.get('title') or '')
    if album_data:
        album_title = str(album_data.get('title') or album_title)

    problems = []
    if is_karaoke_or_instrumental(title, version, album_title):
        problems.append('karaoke/instrumental')
    if is_live(title, version, album_title):
        problems.append('live')
    if is_single_or_ep(track_data, album_data):
        problems.append('single/ep')
    if is_compilation(track_data, album_data):
        problems.append('compilation')
    return problems


# ── Album track listing scanning ──

def _extract_album_tracks(album_data: dict) -> list:
    tracks = []
    for entry in (album_data.get('items') or []):
        t = entry.get('item') or entry
        if t.get('id') is not None:
            tracks.append(t)
    return tracks


def _find_track_in_album(album_data: dict, stripped_title: str) -> list:
    """Return list of (track_id, title, version, is_clean) for matches."""
    matches = []
    album_title = str(album_data.get('title') or '')
    for t in _extract_album_tracks(album_data):
        tt = str(t.get('title') or '').strip()
        if not tt:
            continue
        if _strip_version_suffixes(tt).lower() != stripped_title.lower():
            continue
        tv = str(t.get('version') or '').strip()
        tid = t.get('id')
        is_clean = not (
            is_karaoke_or_instrumental(tt, tv, album_title)
            or is_live(tt, tv, album_title)
        )
        matches.append((tid, tt, tv, is_clean))
    return matches


# ── Replacement search ──

def _fetch_album_cached(album_id) -> Optional[dict]:
    if album_id in _album_cache:
        return _album_cache[album_id]
    raw = _fetch_hifi_album_payload(album_id)
    data = raw.get('data') if isinstance(raw, dict) and isinstance(raw.get('data'), dict) else None
    _album_cache[album_id] = data
    return data


def find_replacement(track_data: dict) -> Optional[dict]:
    """Search for a clean version of the track.

    Strategy:
        1. Re-search by primary artist + stripped title
        2. Sort results by promise (exact title, no version, non-compilation)
        3. For each, fetch album and check track listing
        4. Return first clean match (or best fallback)

    Returns normalized track dict or None.
    """
    raw_artist = str((track_data.get('artists') or [{}])[0].get('name') or '')
    if not raw_artist and isinstance(track_data.get('artist'), dict):
        raw_artist = str(track_data['artist'].get('name') or '')
    primary_artist = _parse_primary_artist(raw_artist)
    stripped_title = _strip_version_suffixes(track_data.get('title', ''))
    search_query = f'{primary_artist} {stripped_title}'.strip()

    if not search_query:
        return None

    results = _fetch_hifi_search_results('s', search_query, limit=10)
    if not results:
        return None

    # Sort by promise
    def sort_key(item):
        t = _strip_version_suffixes(str(item.get('title') or '')).lower()
        v = str(item.get('version') or '')
        at = str((item.get('album') or {}).get('title') or '')
        exact = t == stripped_title.lower()
        return (0 if exact else 1, 0 if not v else 1, 0 if not is_compilation_title(at) else 1)

    results.sort(key=sort_key)

    seen_album_ids = set()
    fallback_track = None  # best non-clean if no clean found

    for item in results:
        if item.get('id') == track_data.get('id'):
            continue
        if not _artist_overlap(track_data, item):
            continue

        album_id = (item.get('album') or {}).get('id')
        if not album_id or album_id in seen_album_ids:
            continue
        seen_album_ids.add(album_id)

        album_data = _fetch_album_cached(album_id)
        if not album_data:
            continue

        matches = _find_track_in_album(album_data, stripped_title)
        if not matches:
            continue

        clean_matches = [m for m in matches if m[3]]
        if clean_matches:
            # Found clean match — fetch and return its full track info
            best_id = clean_matches[0][0]
            raw = _fetch_hifi_track_info_payload(best_id)
            if raw:
                info = extract_hifi_track_info(raw)
                if info:
                    info['_resolved_from_album'] = str(album_data.get('title') or '')
                    return info

        # Remember fallback (first non-clean match)
        if fallback_track is None and matches:
            fallback_track = (matches[0][0], str(album_data.get('title') or ''))

    # No clean match — try fallback
    if fallback_track:
        fb_id, fb_album = fallback_track
        raw = _fetch_hifi_track_info_payload(fb_id)
        if raw:
            info = extract_hifi_track_info(raw)
            if info:
                info['_resolved_from_album'] = fb_album
                return info

    return None


def _fetch_album_for_track(track_data: dict) -> Optional[dict]:
    """Fetch album detail for a track, caching the result."""
    album_id = track_data.get('album_id') or (track_data.get('album') or {}).get('id')
    if not album_id:
        return None
    return _fetch_album_cached(album_id)


# ── Main entry point ──

def resolve_track(hifi_id: Any, settings: Optional[dict] = None) -> dict:
    """Check a track for problems and find a replacement if needed.

    Args:
        hifi_id: Tidal/hifi track ID
        settings: Download settings dict (uses penalty_* keys as enable/disable toggles)

    Returns:
        dict with:
            'original_id': the input hifi_id
            'reason': str like 'compilation', 'live;single/ep', or 'none'
            'replacement': normalized track dict or None (if no replacement was needed/found)
    """
    if settings is None:
        settings = {}

    # Fetch track info
    raw = _fetch_hifi_track_info_payload(hifi_id)
    if not raw:
        return {'original_id': hifi_id, 'reason': 'fetch_error', 'replacement': None}

    track_info = extract_hifi_track_info(raw)
    if not track_info:
        return {'original_id': hifi_id, 'reason': 'parse_error', 'replacement': None}

    # Fetch album detail for single/EP and compilation detection
    album_data = _fetch_album_for_track(track_info)

    # Detect problems (respect settings toggles)
    all_problems = detect_problems(track_info, album_data)
    active_problems = []
    for p in all_problems:
        setting_key = {
            'karaoke/instrumental': 'penalty_karaoke',
            'live': 'penalty_live',
            'single/ep': 'penalty_single',
            'compilation': 'penalty_compilation',
        }.get(p)
        if setting_key is None or settings.get(setting_key, True):
            active_problems.append(p)

    reason = '; '.join(active_problems) if active_problems else 'none'

    if not active_problems:
        return {'original_id': hifi_id, 'reason': 'none', 'replacement': None}

    # Find replacement
    replacement = find_replacement(track_info)

    return {
        'original_id': hifi_id,
        'reason': reason,
        'replacement': replacement,
    }


from squidly.hifi import extract_hifi_track_info  # noqa: E402


# ── Shared helpers for callers (LB matching, YTM matching, Fresh Finds) ──

def resolve_best_match(best_item: Optional[dict], settings: dict, log_label: str = "") -> Optional[dict]:
    """Pipe a best-match candidate through the resolver and return the replacement (or original).

    Callers: match_listenbrainz_track, match_ytm_track, etc.

    Args:
        best_item: The matched track dict (must have 'id' key)
        settings: Download settings dict
        log_label: Optional label for log messages (e.g. 'LB_MATCH', 'YTM_MATCH')

    Returns:
        The replacement track dict, or the original best_item if no replacement needed/found.
    """
    if not best_item:
        return best_item
    result = resolve_track(best_item.get('id'), settings)
    if result.get('replacement'):
        logger.info("[%s] Resolved %s (%s) → track %s",
                    log_label or 'RESOLVE', best_item.get('id'), result['reason'],
                    result['replacement'].get('id'))
        return result['replacement']
    return best_item


def merge_replacement_into_rec(rec: dict, replacement: dict) -> dict:
    """Merge fields from a resolver replacement dict into a recommendation rec dict.

    Callers: process_recommendation_job, etc.

    The replacement dict comes from extract_hifi_track_info() and has keys like
    'id', 'title', 'isrc', 'duration', 'album_id', 'track_artists', etc.
    The rec dict has keys like 'hifi_id', 'title', 'isrc', 'duration', etc.
    """
    rec['hifi_id'] = replacement['id']
    rec['title'] = replacement.get('title', rec['title'])
    rec['isrc'] = replacement.get('isrc', rec.get('isrc'))
    rec['duration'] = replacement.get('duration', rec.get('duration'))
    if replacement.get('album_id'):
        rec['album_id'] = replacement['album_id']
    # album title — could be at different keys in the replacement
    album_val = replacement.get('album_title') or (
        replacement['album'] if isinstance(replacement.get('album'), str)
        else (replacement.get('album') or {}).get('title')
    )
    if album_val:
        rec['album'] = album_val
    # artist info
    artists = replacement.get('track_artists') or replacement.get('artists') or []
    if isinstance(artists, list) and artists and isinstance(artists[0], dict):
        rec['artist'] = artists[0].get('name', rec.get('artist', ''))
        rec['artist_id'] = artists[0].get('id', rec.get('artist_id'))
    # quality
    if replacement.get('audioQuality'):
        rec['quality'] = replacement['audioQuality']
    return rec
