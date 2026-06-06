"""Centralized MusicBrainz API client with rate limiting and caching."""

import functools
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_MUSICBRAINZ_USER_AGENT = 'Squidly/1.0 ( https://github.com/elmerohueso/squidly )'
_MB_BASE_URL = 'https://musicbrainz.org/ws/2'
_CAA_BASE_URL = 'https://coverartarchive.org'

_rate_lock = threading.Lock()
_last_request_ts: float = 0.0
_MIN_INTERVAL_SECONDS: float = 0.02  # 50 req/sec for anonymous MB user agents

_cache_lock = threading.Lock()
_response_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes
_CACHE_MAX_SIZE = 500


def _rate_limited_get(url: str, params: dict = None, headers: dict = None) -> requests.Response:
    global _last_request_ts
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_ts
        if elapsed < _MIN_INTERVAL_SECONDS:
            time.sleep(_MIN_INTERVAL_SECONDS - elapsed)
        _last_request_ts = time.monotonic()

    resp = requests.get(url, params=params, headers=headers or {'User-Agent': _MUSICBRAINZ_USER_AGENT}, timeout=15)

    if resp.status_code == 429:
        retry_after = int(resp.headers.get('Retry-After', '1'))
        time.sleep(retry_after)
        with _rate_lock:
            _last_request_ts = time.monotonic()
        resp = requests.get(url, params=params, headers=headers or {'User-Agent': _MUSICBRAINZ_USER_AGENT}, timeout=15)

    if resp.status_code == 503:
        time.sleep(1)
        with _rate_lock:
            _last_request_ts = time.monotonic()
        resp = requests.get(url, params=params, headers=headers or {'User-Agent': _MUSICBRAINZ_USER_AGENT}, timeout=15)

    return resp


def _cache_get(key: str):
    with _cache_lock:
        if key in _response_cache:
            val, ts = _response_cache[key]
            if time.time() - ts < _CACHE_TTL:
                return val
            del _response_cache[key]
    return None


def _cache_set(key: str, value):
    with _cache_lock:
        if len(_response_cache) >= _CACHE_MAX_SIZE:
            # Evict oldest entry
            oldest_key = min(_response_cache, key=lambda k: _response_cache[k][1])
            del _response_cache[oldest_key]
        _response_cache[key] = (value, time.time())


# ── Search functions ──

def mb_search_recordings(query: str, limit: int = 25, offset: int = 0) -> dict:
    """Search MB for recordings."""
    cache_key = f"rec:{query}:{limit}:{offset}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/recording/', params={'query': query, 'fmt': 'json', 'limit': limit, 'offset': offset})
    if not resp.ok:
        return {'recordings': [], 'count': 0}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_search_releases(query: str, limit: int = 25, offset: int = 0) -> dict:
    """Search MB for releases."""
    cache_key = f"rel:{query}:{limit}:{offset}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/release/', params={'query': query, 'fmt': 'json', 'limit': limit, 'offset': offset})
    if not resp.ok:
        return {'releases': [], 'count': 0}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_search_artists(query: str, limit: int = 25, offset: int = 0) -> dict:
    """Search MB for artists."""
    cache_key = f"art:{query}:{limit}:{offset}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/artist/', params={'query': query, 'fmt': 'json', 'limit': limit, 'offset': offset})
    if not resp.ok:
        return {'artists': [], 'count': 0}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_search_release_groups(query: str, limit: int = 25, offset: int = 0) -> dict:
    """Search MB for release-groups."""
    cache_key = f"rg:{query}:{limit}:{offset}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/release-group/', params={'query': query, 'fmt': 'json', 'limit': limit, 'offset': offset})
    if not resp.ok:
        return {'release-groups': [], 'count': 0}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


# ── Lookup functions ──

def mb_get_recording(mbid: str) -> dict:
    """Get recording by MBID with artist-credits, releases, isrcs."""
    cache_key = f"rec_mbid:{mbid}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/recording/{mbid}', params={'inc': 'artist-credits+releases+isrcs', 'fmt': 'json'})
    if not resp.ok:
        return {}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_get_release(mbid: str) -> dict:
    """Get release by MBID with recordings, artist-credits."""
    cache_key = f"rel_mbid:{mbid}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/release/{mbid}', params={'inc': 'recordings+artist-credits+media+labels', 'fmt': 'json'})
    if not resp.ok:
        return {}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_get_artist(mbid: str) -> dict:
    """Get artist by MBID with release-groups."""
    cache_key = f"art_mbid:{mbid}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/artist/{mbid}', params={'inc': 'release-groups', 'fmt': 'json', 'release-groups-limit': 100})
    if not resp.ok:
        return {}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


def mb_get_release_group(mbid: str) -> dict:
    """Get release-group by MBID with releases."""
    cache_key = f"rg_mbid:{mbid}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    resp = _rate_limited_get(f'{_MB_BASE_URL}/release-group/{mbid}', params={'inc': 'releases', 'fmt': 'json'})
    if not resp.ok:
        return {}
    result = resp.json()
    _cache_set(cache_key, result)
    return result


# ── Cover Art Archive ──

def mb_get_cover_art_url(release_mbid: str, size: int = 500) -> Optional[str]:
    """Get cover art URL from CAA for a release MBID. Returns full URL or None."""
    cache_key = f"caa:{release_mbid}:{size}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    resp = requests.get(f'{_CAA_BASE_URL}/release/{release_mbid}/', timeout=10)
    if not resp.ok or resp.status_code == 404:
        _cache_set(cache_key, None)
        return None

    try:
        data = resp.json()
        images = data.get('images') or []
        for img in images:
            if img.get('front', False):
                thumb = img.get('thumbnails', {})
                url = thumb.get(str(size)) or thumb.get('500') or thumb.get('250') or img.get('image')
                if url:
                    _cache_set(cache_key, url)
                    return url
    except Exception:
        pass

    _cache_set(cache_key, None)
    return None


# ── Normalization functions ──

def _extract_artist_name(artist_credit: list) -> str:
    """Extract artist name from MB artist-credit array."""
    if not artist_credit:
        return 'Unknown Artist'
    names = []
    for credit in artist_credit:
        artist = credit.get('artist', {})
        name = artist.get('name', '').strip()
        if name:
            names.append(name)
    return '; '.join(names) if names else 'Unknown Artist'


def _extract_artists_array(artist_credit: list) -> list:
    """Extract artists array in Tidal shape from MB artist-credit."""
    if not artist_credit:
        return []
    result = []
    for credit in artist_credit:
        artist = credit.get('artist', {})
        result.append({
            'id': artist.get('id'),
            'name': artist.get('name', ''),
            'picture': None,
            'type': artist.get('type', ''),
        })
    return result


def normalize_mb_recording(rec: dict) -> dict:
    """Normalize a MusicBrainz recording to the Track-shaped dict the frontend expects."""
    artist_credit = rec.get('artist-credit', [])
    artists = _extract_artists_array(artist_credit)
    artist_name = _extract_artist_name(artist_credit)

    # Get release info if available
    releases = rec.get('releases', [])
    album_info = {}
    if releases:
        rel = releases[0]
        album_info = {
            'id': rel.get('id'),
            'title': rel.get('title', 'Unknown Album'),
            'cover': None,  # Will be filled by provider
        }

    # Duration: MB gives milliseconds, convert to seconds
    length_ms = rec.get('length')
    duration = length_ms // 1000 if length_ms else None

    isrcs = rec.get('isrcs') or []

    return {
        'id': rec.get('id'),
        'title': rec.get('title', 'Unknown Track'),
        'version': '',
        'explicit': False,
        'trackNumber': None,
        'duration': duration,
        'isrc': isrcs[0] if isrcs else None,
        'maxAudioQuality': None,
        'artists': artists,
        'artist': {'id': artists[0]['id'] if artists else None, 'name': artist_name, 'picture': None, 'type': 'Artist'},
        'album': album_info,
        'discNumber': None,
        'volumeNumber': None,
        'numberOfVolumes': None,
        'url': '',
        'copyright': '',
        'replayGain': None,
        'track_streams': {},
    }


def normalize_mb_release(rel: dict, cover_url: str = None) -> dict:
    """Normalize a MusicBrainz release to the Album-shaped dict."""
    artist_credit = rel.get('artist-credit', [])
    artists = _extract_artists_array(artist_credit)

    media = rel.get('media', [])
    total_tracks = sum(m.get('track-count', 0) for m in media)
    num_discs = len(media) if media else 1

    # Build tracks from media
    tracks = []
    for medium in media:
        disc_num = medium.get('position', 1)
        for track in medium.get('tracks', []):
            recording = track.get('recording', {})
            track_artists = _extract_artists_array(track.get('artist-credit', artist_credit))
            isrcs = recording.get('isrcs') or []
            length_ms = recording.get('length')

            tracks.append({
                'id': recording.get('id'),
                'title': track.get('title') or recording.get('title', 'Unknown Track'),
                'version': '',
                'explicit': False,
                'trackNumber': track.get('number'),
                'duration': length_ms // 1000 if length_ms else None,
                'isrc': isrcs[0] if isrcs else None,
                'maxAudioQuality': None,
                'artists': track_artists,
                'artist': {'id': track_artists[0]['id'] if track_artists else None, 'name': _extract_artist_name(track_artists), 'picture': None, 'type': 'Artist'},
                'album': {'id': rel.get('id'), 'title': rel.get('title', ''), 'cover': cover_url},
                'discNumber': disc_num,
                'volumeNumber': disc_num,
                'numberOfVolumes': num_discs,
                'url': '',
                'copyright': '',
                'replayGain': None,
                'track_streams': {},
            })

    return {
        'album': {
            'id': rel.get('id'),
            'title': rel.get('title', 'Unknown Album'),
            'version': '',
            'cover': cover_url,
            'releaseDate': rel.get('date', ''),
            'numberOfTracks': total_tracks,
            'numberOfDiscs': num_discs,
            'explicit': False,
            'duration': None,
            'copyright': '',
            'maxAudioQuality': None,
            'artists': artists,
            'tracks': tracks,
        }
    }


def normalize_mb_artist(artist: dict) -> dict:
    """Normalize a MusicBrainz artist to the Artist-shaped dict."""
    release_groups = artist.get('release-groups', [])

    # Group release-groups as "albums" (only album type)
    albums = []
    for rg in release_groups:
        rg_type = rg.get('primary-type', '').lower()
        if rg_type == 'album':
            first_release = rg.get('first-release-date', '')
            albums.append({
                'id': rg.get('id'),
                'title': rg.get('title', 'Unknown Album'),
                'cover': None,
                'releaseDate': first_release,
                'numberOfTracks': None,
                'artists': [{'id': artist.get('id'), 'name': artist.get('name', ''), 'picture': None, 'type': artist.get('type', '')}],
                'artist': {'id': artist.get('id'), 'name': artist.get('name', ''), 'picture': None, 'type': artist.get('type', '')},
                'audioQuality': None,
            })

    return {
        'artist': {
            'id': artist.get('id'),
            'name': artist.get('name', 'Unknown Artist'),
            'picture': None,
            'albums': albums,
            'top_tracks': [],  # MB doesn't have top tracks concept
        }
    }
