"""Track detection and replacement for better-quality versions.

Detects tracks that are karaoke, live, singles/EPs, on compilation albums,
or from soundtracks. Only karaoke, live, single/ep, and compilation trigger
replacement — soundtracks and studio albums are always kept.

Usage:
    from squidly.services.track_resolver import resolve_track
    result = resolve_track(hifi_id, settings)
"""

import logging
import re
from typing import Any, Optional

from squidly.services.hifi import (
    _fetch_hifi_album_payload,
    _fetch_hifi_search_results,
    _fetch_hifi_track_info_payload,
    extract_hifi_track_info,
)

logger = logging.getLogger(__name__)

_album_cache: dict = {}
_STRIP_VERSION_RE = re.compile(r'\s*[\(\[].*[\)\]]\s*$')


# ── Detections ──

def _has_any(texts, keywords):
    t = ' '.join(texts).lower()
    return any(kw in t for kw in keywords)


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


def _is_karaoke(title, version, album_title):
    return _has_any([title, version, album_title], ['karaoke', 'instrumental'])


def _is_live(title, version, album_title):
    return _has_any([title, version, album_title], ['live']) and bool(
        re.search(r'\blive\b', ' '.join([title, version, album_title]).lower()))


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


def detect_problems(track_data, album_data=None):
    """Return list of problem types: karaoke/instrumental, live, single/ep, soundtrack, compilation."""
    title = str(track_data.get('title') or '')
    version = str(track_data.get('version') or '')
    album_title = str((album_data or track_data.get('album', {})).get('title') or '')

    problems = []
    if _is_karaoke(title, version, album_title):
        problems.append('karaoke/instrumental')
    if _is_live(title, version, album_title):
        problems.append('live')
    if _is_single(track_data, album_data):
        problems.append('single/ep')
    if _is_soundtrack(track_data, album_data):
        problems.append('soundtrack')
    elif _is_compilation(track_data, album_data):
        problems.append('compilation')
    return problems


# ── Replacement search ──

def _strip_title(title):
    return _STRIP_VERSION_RE.sub('', title).strip()


def _first_artist(track_data):
    for a in (track_data.get('artists') or []):
        if isinstance(a, dict):
            name = str(a.get('name') or '').strip()
            if name:
                for sep in (';', ','):
                    if sep in name:
                        return name.split(sep)[0].strip()
                return name
    if isinstance(track_data.get('artist'), dict):
        return str(track_data['artist'].get('name') or '').strip()
    return ''


def _artist_overlap(track_data, item):
    def names(d):
        s = set()
        for a in (d.get('artists') or []):
            if isinstance(a, dict):
                n = str(a.get('name') or '').strip().lower()
                if n: s.add(n)
        if not s and isinstance(d.get('artist'), dict):
            n = str(d['artist'].get('name') or '').strip().lower()
            if n: s.add(n)
        return s
    o, c = names(track_data), names(item)
    return not o or not c or bool(o & c)


def _fetch_album(album_id):
    if album_id not in _album_cache:
        raw = _fetch_hifi_album_payload(album_id)
        _album_cache[album_id] = raw.get('data') if isinstance(raw, dict) and isinstance(raw.get('data'), dict) else None
    return _album_cache[album_id]


def _find_track_in_album(album_data, stripped_title):
    """Return list of (track_id, is_clean) for matching tracks in the album."""
    matches = []
    album_title = str(album_data.get('title') or '')
    for entry in (album_data.get('items') or []):
        t = entry.get('item') or entry
        if t.get('id') is None:
            continue
        tt = str(t.get('title') or '').strip()
        if not tt:
            continue
        if _strip_title(tt).lower() != stripped_title.lower():
            continue
        tv = str(t.get('version') or '').strip()
        is_clean = not (_is_karaoke(tt, tv, album_title) or _is_live(tt, tv, album_title))
        matches.append((t['id'], is_clean))
    return matches


def find_replacement(track_data):
    stripped = _strip_title(track_data.get('title', ''))
    query = f"{_first_artist(track_data)} {stripped}".strip()
    if not query:
        return None

    results = _fetch_hifi_search_results('s', query, limit=10)
    if not results:
        return None

    results.sort(key=lambda r: (
        0 if _strip_title(str(r.get('title') or '')).lower() == stripped.lower() else 1,
        0 if not r.get('version') else 1,
        0 if not _has_any([str((r.get('album') or {}).get('title') or '')], COMPILATION_KEYWORDS) else 1,
    ))

    seen = set()
    fallback = None
    for item in results:
        if item.get('id') == track_data.get('id') or not _artist_overlap(track_data, item):
            continue
        aid = (item.get('album') or {}).get('id')
        if not aid or aid in seen:
            continue
        seen.add(aid)

        album_data = _fetch_album(aid)
        if not album_data:
            continue

        matches = _find_track_in_album(album_data, stripped)
        if not matches:
            continue

        clean = [m for m in matches if m[1]]
        if clean:
            raw = _fetch_hifi_track_info_payload(clean[0][0])
            if raw:
                info = extract_hifi_track_info(raw)
                if info:
                    return info
        if fallback is None:
            fallback = (matches[0][0], str(album_data.get('title') or ''))

    if fallback:
        raw = _fetch_hifi_track_info_payload(fallback[0])
        if raw:
            info = extract_hifi_track_info(raw)
            if info:
                return info
    return None


# ── Main entry point ──

_REASON_LOG = {
    'karaoke/instrumental': 'is Karaoke/Instrumental, will search for a replacement',
    'live': 'is Live, will search for a replacement',
    'single/ep': 'is from a Single/EP, will search for a replacement',
    'compilation': 'is from a Compilation, will search for a replacement',
    'soundtrack': 'is from a Soundtrack, keeping track',
    'none': 'is from a Studio Album, keeping track',
}


def resolve_track(hifi_id: Any, settings: Optional[dict] = None) -> dict:
    if settings is None:
        settings = {}

    raw = _fetch_hifi_track_info_payload(hifi_id)
    if not raw:
        return {'original_id': hifi_id, 'reason': 'fetch_error', 'replacement': None}
    track_info = extract_hifi_track_info(raw)
    if not track_info:
        return {'original_id': hifi_id, 'reason': 'parse_error', 'replacement': None}

    album_id = track_info.get('album_id') or (track_info.get('album') or {}).get('id')
    album_data = _fetch_album(album_id) if album_id else None

    all_problems = detect_problems(track_info, album_data)

    # Soundtracks are never replaced
    active = [p for p in all_problems if p != 'soundtrack' or settings.get('penalty_soundtrack', False)]
    active_setting = [p for p in all_problems if p == 'soundtrack' or settings.get(
        {'karaoke/instrumental': 'penalty_karaoke', 'live': 'penalty_live',
         'single/ep': 'penalty_single', 'compilation': 'penalty_compilation'}.get(p, ''), True)]

    # Wait, this is getting convoluted. Let me simplify:
    # Soundtrack → never replace (regardless of settings)
    # Everything else → check settings toggle
    active_problems = []
    for p in all_problems:
        if p == 'soundtrack':
            continue  # never replace soundtracks
        key = {'karaoke/instrumental': 'penalty_karaoke', 'live': 'penalty_live',
               'single/ep': 'penalty_single', 'compilation': 'penalty_compilation'}.get(p)
        if key is None or settings.get(key, True):
            active_problems.append(p)

    label = f"track {hifi_id} ({track_info.get('title', '')})"

    # Log
    for p in all_problems + (['none'] if not all_problems else []):
        msg = _REASON_LOG.get(p)
        if msg:
            logger.info("%s %s", label, msg)

    reason = '; '.join(all_problems) if all_problems else 'none'

    if not active_problems:
        return {'original_id': hifi_id, 'reason': reason, 'replacement': None}

    replacement = find_replacement(track_info)
    if replacement:
        logger.info("%s → replaced by %s", label, replacement.get('id'))
    else:
        logger.info("no replacement found for %s, keeping track", label)

    return {'original_id': hifi_id, 'reason': reason, 'replacement': replacement}


# ── Shared helpers for callers ──

def resolve_best_match(best_item: Optional[dict], settings: dict, log_label: str = "") -> Optional[dict]:
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
    rec['hifi_id'] = replacement['id']
    rec['title'] = replacement.get('title', rec['title'])
    rec['isrc'] = replacement.get('isrc', rec.get('isrc'))
    rec['duration'] = replacement.get('duration', rec.get('duration'))
    if replacement.get('album_id'):
        rec['album_id'] = replacement['album_id']
    album_val = replacement.get('album_title') or (
        replacement['album'] if isinstance(replacement.get('album'), str)
        else (replacement.get('album') or {}).get('title'))
    if album_val:
        rec['album'] = album_val
    artists = replacement.get('track_artists') or replacement.get('artists') or []
    if artists and isinstance(artists[0], dict):
        rec['artist'] = artists[0].get('name', rec.get('artist', ''))
        rec['artist_id'] = artists[0].get('id', rec.get('artist_id'))
    if replacement.get('audioQuality'):
        rec['quality'] = replacement['audioQuality']
    return rec
