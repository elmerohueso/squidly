"""HiFi metadata parsing helpers.

This module centralizes parsing logic for HiFi/Tidal API responses so the
download flow and match flow can share the same extraction behavior.
"""

import base64
import json
import re
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional


def _extract_hifi_image_string(value: Any) -> str:
    """Normalize a HiFi/Tidal image field to a string value."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return str(value.get('id') or value.get('url') or '')
    return ''


def _format_tidal_image_url(image_id_or_path: str, size: int) -> str:
    """Format a Tidal CDN image URL from a UUID/path and requested square size."""
    if not image_id_or_path:
        return ''

    image_path = image_id_or_path.replace('-', '/')
    return f"https://resources.tidal.com/images/{image_path}/{size}x{size}.jpg"


def _normalize_tidal_image_url(normalized_value: str, size: int) -> Optional[str]:
    parsed = urlparse(normalized_value)
    if parsed.scheme not in ('http', 'https') or parsed.netloc.lower() != 'resources.tidal.com':
        return None

    path_parts = [part for part in parsed.path.split('/') if part]
    if not path_parts or path_parts[0] != 'images':
        return None

    image_parts = path_parts[1:]
    if image_parts and re.match(r'^\d+x\d+\.(jpg|jpeg|png)$', image_parts[-1], re.IGNORECASE):
        image_parts = image_parts[:-1]
    if not image_parts:
        return None

    image_path = '/'.join(image_parts)
    return f"https://resources.tidal.com/images/{image_path}/{size}x{size}.jpg"


def _format_hifi_image_value(image_id_or_url: Any, size: int = 640) -> Optional[str]:
    """Format a HiFi/Tidal image string or ID into a URL."""
    raw_value = _extract_hifi_image_string(image_id_or_url)
    if not raw_value:
        return None

    normalized_value = raw_value.strip()
    lowered = normalized_value.lower()
    if lowered in ('none', 'null') or '{' in normalized_value or '}' in normalized_value:
        return None

    normalized_tidal_url = _normalize_tidal_image_url(normalized_value, size)
    if normalized_tidal_url:
        return normalized_tidal_url

    if normalized_value.startswith('http://') or normalized_value.startswith('https://'):
        return normalized_value
    if normalized_value.startswith('//'):
        return f"https:{normalized_value}"
    if normalized_value.startswith('resources.tidal.com/'):
        return f"https://{normalized_value}"
    if normalized_value.startswith('/images/'):
        if normalized_value.endswith('.jpg') or normalized_value.endswith('.jpeg') or normalized_value.endswith('.png'):
            return f"https://resources.tidal.com{normalized_value}"
        normalized_value = normalized_value.strip('/')

    try:
        return _format_tidal_image_url(normalized_value, size)
    except Exception:
        return None


def _normalize_hifi_artist_entry(artist_entry: Any) -> Dict[str, Any]:
    if not isinstance(artist_entry, dict):
        return {
            'id': None,
            'name': None,
            'picture': None,
            'type': None,
        }

    return {
        'id': artist_entry.get('id'),
        'name': artist_entry.get('name'),
        'picture': _format_hifi_image_value(artist_entry.get('picture'), size=750),
        'type': artist_entry.get('type'),
    }


def extract_hifi_track_info(info_response: Any) -> Dict[str, Any]:
    """Normalize HiFi / Tidal track info payload from /info/?id=<trackid>."""
    if not isinstance(info_response, dict):
        return {}

    track_data = info_response.get('data') if isinstance(info_response.get('data'), dict) else {}
    if not isinstance(track_data, dict):
        return {}

    track_id = track_data.get('id')
    title = str(track_data.get('title') or '').strip()
    version = str(track_data.get('version') or '').strip() if track_data.get('version') is not None else ''
    track_number = track_data.get('trackNumber')
    volume_number = track_data.get('volumeNumber')
    duration = track_data.get('duration')
    explicit = bool(track_data.get('explicit'))
    copyright_text = track_data.get('copyright')
    isrc = track_data.get('isrc')
    url = track_data.get('url')
    replay_gain = track_data.get('replayGain')

    audio_quality = track_data.get('audioQuality')
    if not audio_quality:
        media_metadata = track_data.get('mediaMetadata') if isinstance(track_data.get('mediaMetadata'), dict) else {}
        tags = media_metadata.get('tags') if isinstance(media_metadata.get('tags'), list) else []
        if tags:
            audio_quality = str(tags[0] or '').strip() if tags[0] is not None else ''

    artists = []
    if isinstance(track_data.get('artists'), list):
        for artist_item in track_data.get('artists'):
            if not isinstance(artist_item, dict):
                continue
            artist_id = artist_item.get('id')
            artist_type = artist_item.get('type')
            artists.append({
                'id': artist_id,
                'type': artist_type,
                'name': artist_item.get('name'),
                'picture': _format_hifi_image_value(artist_item.get('picture'), size=750),
            })
    elif isinstance(track_data.get('artist'), dict):
        artist_item = track_data.get('artist')
        artists.append({
            'id': artist_item.get('id'),
            'type': artist_item.get('type'),
            'name': artist_item.get('name'),
            'picture': _format_hifi_image_value(artist_item.get('picture'), size=750),
        })

    album_info = track_data.get('album') if isinstance(track_data.get('album'), dict) else {}
    album_id = album_info.get('id') if isinstance(album_info, dict) else None

    return {
        'id': track_id,
        'title': title,
        'version': version,
        'trackNumber': track_number,
        'volumeNumber': volume_number,
        'duration': duration,
        'explicit': explicit,
        'audioQuality': audio_quality,
        'copyright': copyright_text,
        'isrc': isrc,
        'url': url,
        'track_artists': artists,
        'album_id': album_id,
        'replayGain': replay_gain,
    }


def extract_hifi_album_info(album_response: Any) -> Dict[str, Any]:
    """Normalize HiFi / Tidal album page response from an album endpoint."""
    if not isinstance(album_response, dict):
        return {}

    album_data = None
    track_ids: List[Any] = []

    data_payload = album_response.get('data') if isinstance(album_response.get('data'), dict) else None
    if isinstance(data_payload, dict):
        album_data = data_payload
        items = data_payload.get('items')
        if isinstance(items, list):
            for item_wrapper in items:
                if not isinstance(item_wrapper, dict):
                    continue
                if item_wrapper.get('type') != 'track':
                    continue
                item = item_wrapper.get('item')
                if not isinstance(item, dict):
                    continue
                track_id = item.get('id')
                if track_id is not None:
                    track_ids.append(track_id)

    rows = album_response.get('rows') if isinstance(album_response.get('rows'), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        modules = row.get('modules') if isinstance(row.get('modules'), list) else []
        for module in modules:
            if not isinstance(module, dict):
                continue
            module_type = module.get('type')
            if module_type == 'ALBUM_HEADER' and isinstance(module.get('album'), dict):
                album_data = album_data or module.get('album')
            if module_type == 'ALBUM_ITEMS' and isinstance(module.get('pagedList'), dict):
                items = module.get('pagedList', {}).get('items')
                if isinstance(items, list):
                    for item_wrapper in items:
                        if not isinstance(item_wrapper, dict):
                            continue
                        if item_wrapper.get('type') != 'track':
                            continue
                        item = item_wrapper.get('item')
                        if not isinstance(item, dict):
                            continue
                        track_id = item.get('id')
                        if track_id is not None:
                            track_ids.append(track_id)

    if not isinstance(album_data, dict):
        return {}

    cover_url = _format_hifi_image_value(album_data.get('cover'), size=640)
    audio_quality = album_data.get('audioQuality')
    if not audio_quality:
        media_metadata = album_data.get('mediaMetadata') if isinstance(album_data.get('mediaMetadata'), dict) else {}
        tags = media_metadata.get('tags') if isinstance(media_metadata.get('tags'), list) else []
        if tags:
            audio_quality = str(tags[0] or '').strip() if tags[0] is not None else ''

    album_artists: List[Dict[str, Any]] = []
    if isinstance(album_data.get('artists'), list):
        for artist_item in album_data.get('artists'):
            if not isinstance(artist_item, dict):
                continue
            album_artists.append(_normalize_hifi_artist_entry(artist_item))

    return {
        'id': album_data.get('id'),
        'title': str(album_data.get('title') or '').strip(),
        'version': str(album_data.get('version') or '').strip() if album_data.get('version') is not None else '',
        'cover': cover_url,
        'releaseDate': album_data.get('releaseDate'),
        'numberOfTracks': album_data.get('numberOfTracks'),
        'numberOfVolumes': album_data.get('numberOfVolumes'),
        'url': album_data.get('url'),
        'explicit': bool(album_data.get('explicit')),
        'duration': album_data.get('duration'),
        'copyright': album_data.get('copyright'),
        'audioQuality': audio_quality,
        'tracks': track_ids,
        'album_artists': album_artists,
    }


def _extract_hifi_audio_quality(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None

    audio_quality = payload.get('audioQuality')
    if audio_quality:
        return audio_quality

    media_metadata = payload.get('mediaMetadata') if isinstance(payload.get('mediaMetadata'), dict) else {}
    tags = media_metadata.get('tags') if isinstance(media_metadata.get('tags'), list) else []
    if tags:
        return str(tags[0] or '').strip() if tags[0] is not None else None

    return None


def _extract_hifi_album_track_items(album_response: Any) -> List[Dict[str, Any]]:
    track_items: Dict[Any, Dict[str, Any]] = {}

    def _append_track(item_payload: Any) -> None:
        if not isinstance(item_payload, dict):
            return
        track_id = item_payload.get('id')
        if track_id is None:
            return
        if track_id not in track_items:
            track_items[track_id] = item_payload

    data_payload = album_response.get('data') if isinstance(album_response.get('data'), dict) else None
    if isinstance(data_payload, dict):
        items = data_payload.get('items')
        if isinstance(items, list):
            for item_wrapper in items:
                if not isinstance(item_wrapper, dict) or item_wrapper.get('type') != 'track':
                    continue
                _append_track(item_wrapper.get('item'))

    rows = album_response.get('rows') if isinstance(album_response.get('rows'), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        modules = row.get('modules') if isinstance(row.get('modules'), list) else []
        for module in modules:
            if not isinstance(module, dict):
                continue
            if module.get('type') != 'ALBUM_ITEMS':
                continue
            items = module.get('pagedList', {}).get('items')
            if not isinstance(items, list):
                continue
            for item_wrapper in items:
                if not isinstance(item_wrapper, dict) or item_wrapper.get('type') != 'track':
                    continue
                _append_track(item_wrapper.get('item'))

    return list(track_items.values())


def _build_hifi_track_artists(artist_entries: Any, artist_responses: Any) -> List[Dict[str, Any]]:
    entries = []
    if isinstance(artist_entries, list):
        entries = artist_entries
    elif isinstance(artist_entries, dict):
        entries = [artist_entries]

    normalized_artists: List[Dict[str, Any]] = []
    for artist_entry in entries:
        if not isinstance(artist_entry, dict):
            continue
        normalized = _normalize_hifi_artist_entry(artist_entry)
        if normalized.get('name') is not None or normalized.get('picture') is not None:
            normalized_artists.append(normalized)
            continue

        artist_id = normalized.get('id')
        artist_details = _resolve_hifi_artist_details(artist_id, artist_responses)
        normalized_artists.append({
            'id': artist_details.get('id'),
            'name': artist_details.get('name'),
            'picture': artist_details.get('picture'),
            'type': normalized.get('type'),
        })

    return normalized_artists


def _build_hifi_track_object_from_album_item(track_payload: Any, artist_responses: Any, include_streams: bool = False, audio_quality: Any = None) -> Dict[str, Any]:
    if not isinstance(track_payload, dict):
        return {}

    track_info = extract_hifi_track_info({'data': track_payload})
    artist_entries = track_payload.get('artists') if isinstance(track_payload.get('artists'), list) else track_payload.get('artist')
    track_artists = _build_hifi_track_artists(artist_entries, artist_responses)

    track_id = track_info.get('id')
    return {
        'id': track_info.get('id'),
        'title': track_info.get('title'),
        'version': track_info.get('version'),
        'explicit': track_info.get('explicit'),
        'trackNumber': track_info.get('trackNumber'),
        'replayGain': track_info.get('replayGain'),
        'duration': track_info.get('duration'),
        'discNumber': track_info.get('volumeNumber'),
        'copyright': track_info.get('copyright'),
        'url': track_info.get('url'),
        'isrc': track_info.get('isrc'),
        'maxAudioQuality': _extract_hifi_audio_quality(track_payload),
        'artists': track_artists,
        'track_streams': fetch_hifi_track_manifest(
            track_id,
            audio_quality=audio_quality or _extract_hifi_audio_quality(track_payload)
        ).get('track_streams', {}) if include_streams and track_id is not None else {},
    }


def _extract_hifi_artist_identity(artist_response: Any) -> Dict[str, Any]:
    if not isinstance(artist_response, dict):
        return {}

    albums_payload = artist_response.get('albums')
    if isinstance(albums_payload, dict):
        items = albums_payload.get('items')
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                artist_item = item.get('artist') if isinstance(item.get('artist'), dict) else None
                if isinstance(artist_item, dict) and artist_item.get('id') is not None:
                    return {
                        'id': artist_item.get('id'),
                        'name': artist_item.get('name'),
                        'picture': artist_item.get('picture'),
                    }
                artists_list = item.get('artists') if isinstance(item.get('artists'), list) else []
                for artist_item in artists_list:
                    if isinstance(artist_item, dict) and artist_item.get('id') is not None:
                        return {
                            'id': artist_item.get('id'),
                            'name': artist_item.get('name'),
                            'picture': artist_item.get('picture'),
                        }

    tracks_payload = artist_response.get('tracks')
    if isinstance(tracks_payload, list):
        for track_item in tracks_payload:
            if not isinstance(track_item, dict):
                continue
            artist_item = track_item.get('artist') if isinstance(track_item.get('artist'), dict) else None
            if isinstance(artist_item, dict) and artist_item.get('id') is not None:
                return {
                    'id': artist_item.get('id'),
                    'name': artist_item.get('name'),
                    'picture': artist_item.get('picture'),
                }
            artists_list = track_item.get('artists') if isinstance(track_item.get('artists'), list) else []
            for artist_item in artists_list:
                if isinstance(artist_item, dict) and artist_item.get('id') is not None:
                    return {
                        'id': artist_item.get('id'),
                        'name': artist_item.get('name'),
                        'picture': artist_item.get('picture'),
                    }

    return {}


def extract_hifi_artist_info(artist_response: Any) -> Dict[str, Any]:
    """Normalize HiFi / Tidal artist response from /api/hifi/artists/<id>."""
    if not isinstance(artist_response, dict):
        return {}

    artist_identity = _extract_hifi_artist_identity(artist_response)
    if not artist_identity:
        return {}

    album_ids: List[Any] = []
    albums_payload = artist_response.get('albums')
    if isinstance(albums_payload, dict):
        items = albums_payload.get('items')
        if isinstance(items, list):
            for album_item in items:
                if not isinstance(album_item, dict):
                    continue
                album_id = album_item.get('id')
                if album_id is not None:
                    album_ids.append(album_id)

    picture_url = _format_hifi_image_value(artist_identity.get('picture'), size=750)

    return {
        'id': artist_identity.get('id'),
        'name': artist_identity.get('name'),
        'picture': picture_url,
        'albums': album_ids,
    }


def _extract_hifi_artist_album_ids(artist_response: Any) -> List[Any]:
    album_ids: List[Any] = []
    albums_payload = artist_response.get('albums')
    if not isinstance(albums_payload, dict):
        return album_ids

    items = albums_payload.get('items')
    if not isinstance(items, list):
        return album_ids

    seen = set()
    for album_item in items:
        if not isinstance(album_item, dict):
            continue
        album_id = album_item.get('id')
        if album_id is None:
            item_payload = album_item.get('item')
            if isinstance(item_payload, dict):
                album_id = item_payload.get('id')
        if album_id is not None and album_id not in seen:
            seen.add(album_id)
            album_ids.append(album_id)

    return album_ids


def _extract_hifi_album_artists_from_item(album_item: Any) -> List[Dict[str, Any]]:
    artists: List[Dict[str, Any]] = []
    if isinstance(album_item.get('artists'), list):
        for artist_entry in album_item.get('artists'):
            if not isinstance(artist_entry, dict):
                continue
            artists.append(_normalize_hifi_artist_entry(artist_entry))
    elif isinstance(album_item.get('artist'), dict):
        artists.append(_normalize_hifi_artist_entry(album_item.get('artist')))
    return artists


def _build_hifi_album_object_from_artist_item(album_item: Any) -> Dict[str, Any]:
    if not isinstance(album_item, dict):
        return {}

    return {
        'id': album_item.get('id'),
        'title': str(album_item.get('title') or '').strip(),
        'version': str(album_item.get('version') or '').strip() if album_item.get('version') is not None else '',
        'cover': _format_hifi_image_value(album_item.get('cover'), size=640),
        'releaseDate': album_item.get('releaseDate'),
        'numberOfTracks': album_item.get('numberOfTracks'),
        'numberOfDiscs': album_item.get('numberOfVolumes'),
        'explicit': bool(album_item.get('explicit')),
        'duration': album_item.get('duration'),
        'copyright': album_item.get('copyright'),
        'maxAudioQuality': _extract_hifi_audio_quality(album_item),
        'url': album_item.get('url'),
        'artists': _extract_hifi_album_artists_from_item(album_item),
        'tracks': [],
    }


def _normalize_hifi_artist_track_payload(track_payload: Any) -> Dict[str, Any]:
    if not isinstance(track_payload, dict):
        return {}
    if track_payload.get('type') == 'track' and isinstance(track_payload.get('item'), dict):
        return track_payload.get('item')
    if track_payload.get('id') is not None:
        return track_payload
    return {}


def _extract_hifi_artist_top_track_items(artist_response: Any) -> List[Dict[str, Any]]:
    top_tracks: List[Dict[str, Any]] = []
    tracks_payload = artist_response.get('tracks')
    if isinstance(tracks_payload, list):
        for track_item in tracks_payload:
            normalized_track = _normalize_hifi_artist_track_payload(track_item)
            if normalized_track.get('id') is not None:
                top_tracks.append(normalized_track)
        return top_tracks

    if isinstance(tracks_payload, dict):
        items = tracks_payload.get('items')
        if isinstance(items, list):
            for track_item in items:
                normalized_track = _normalize_hifi_artist_track_payload(track_item)
                if normalized_track.get('id') is not None:
                    top_tracks.append(normalized_track)

    return top_tracks


def get_hifi_artist_object(artist_id: Any, include_tracks: bool = True, include_albums: bool = True) -> Dict[str, Any]:
    """Build a normalized artist object using the HiFi artist endpoint."""
    try:
        from .app import _fetch_hifi_artist_payload
    except ImportError:
        from squidly.app import _fetch_hifi_artist_payload

    artist_response = _fetch_hifi_artist_payload(artist_id, skip_tracks=True)
    artist_info = extract_hifi_artist_info(artist_response)
    if not artist_info:
        return {}

    album_objects = []
    if include_albums:
        albums_payload = artist_response.get('albums')
        if isinstance(albums_payload, dict):
            for album_item in albums_payload.get('items', []):
                if not isinstance(album_item, dict):
                    continue
                album_object = _build_hifi_album_object_from_artist_item(album_item)
                if album_object.get('id') is not None:
                    album_objects.append(album_object)

    top_track_items = _extract_hifi_artist_top_track_items(artist_response)

    top_tracks = []
    if include_tracks:
        for track_item in top_track_items:
            track = _build_hifi_track_object_from_album_item(
                track_item,
                {},
                include_streams=False
            )
            if track:
                top_tracks.append(track)
    else:
        top_tracks = [track_item.get('id') for track_item in top_track_items if track_item.get('id') is not None]

    return {
        'artist': {
            'id': artist_info.get('id'),
            'name': artist_info.get('name'),
            'picture': artist_info.get('picture'),
            'albums': album_objects,
            'top_tracks': top_tracks,
        }
    }


def _resolve_hifi_artist_details(artist_id: Any, artist_responses: Any) -> Dict[str, Any]:
    if artist_id is None:
        return {
            'id': None,
            'name': None,
            'picture': None,
        }

    artist_payload = None
    if isinstance(artist_responses, dict):
        artist_payload = artist_responses.get(artist_id)
    elif isinstance(artist_responses, list):
        for candidate in artist_responses:
            if isinstance(candidate, dict) and candidate.get('data', {}).get('id') == artist_id:
                artist_payload = candidate
                break

    if artist_payload is None:
        return {
            'id': artist_id,
            'name': None,
            'picture': None,
        }

    artist_metadata = extract_hifi_artist_info(artist_payload)
    return {
        'id': artist_metadata.get('id'),
        'name': artist_metadata.get('name'),
        'picture': artist_metadata.get('picture'),
    }


def get_hifi_track_object(track_id: Any, include_streams: bool = False, include_album: bool = False, audio_quality: Any = None) -> Dict[str, Any]:
    """Build a normalized track object by fetching HiFi track, album, and artist payloads.

    Args:
        track_id: HiFi track identifier.
        include_streams: If True, include `track_streams` from the manifest fetch.
        include_album: If True, include nested album metadata in the returned track.
        audio_quality: Optional requested audio quality for the manifest fetch.
    """
    try:
        from .app import _fetch_hifi_track_info_payload, _fetch_hifi_album_payload, _fetch_hifi_artist_payload
    except ImportError:
        from squidly.app import _fetch_hifi_track_info_payload, _fetch_hifi_album_payload, _fetch_hifi_artist_payload

    track_response = _fetch_hifi_track_info_payload(track_id)
    track_info = extract_hifi_track_info(track_response)

    album_info = {}
    if include_album:
        album_id = track_info.get('album_id')
        album_response = _fetch_hifi_album_payload(album_id) if album_id is not None else {}
        album_info = extract_hifi_album_info(album_response)

    missing_artist_ids = set()
    for artist_entry in track_info.get('track_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        if artist_id is None:
            continue
        if artist_entry.get('name') is None or artist_entry.get('picture') is None:
            missing_artist_ids.add(artist_id)
    for artist_entry in album_info.get('album_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        if artist_id is None:
            continue
        if artist_entry.get('name') is None or artist_entry.get('picture') is None:
            missing_artist_ids.add(artist_id)

    artist_responses = {}
    for artist_id in missing_artist_ids:
        artist_responses[artist_id] = _fetch_hifi_artist_payload(artist_id)

    track_artists = []
    for artist_entry in track_info.get('track_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        if artist_id is None:
            continue
        if artist_entry.get('name') is not None or artist_entry.get('picture') is not None:
            track_artists.append({
                'id': artist_id,
                'name': artist_entry.get('name'),
                'picture': artist_entry.get('picture'),
                'type': artist_entry.get('type'),
            })
            continue

        artist_details = _resolve_hifi_artist_details(artist_id, artist_responses)
        track_artists.append({
            'id': artist_details.get('id'),
            'name': artist_details.get('name'),
            'picture': artist_details.get('picture'),
            'type': artist_entry.get('type'),
        })

    album_artists = []
    if include_album:
        for artist_entry in album_info.get('album_artists', []):
            if not isinstance(artist_entry, dict):
                continue
            artist_id = artist_entry.get('id')
            if artist_id is None:
                continue
            if artist_entry.get('name') is not None or artist_entry.get('picture') is not None:
                album_artists.append({
                    'id': artist_id,
                    'name': artist_entry.get('name'),
                    'picture': artist_entry.get('picture'),
                    'type': artist_entry.get('type'),
                })
                continue
            artist_details = _resolve_hifi_artist_details(artist_id, artist_responses)
            album_artists.append({
                'id': artist_details.get('id'),
                'name': artist_details.get('name'),
                'picture': artist_details.get('picture'),
                'type': artist_entry.get('type'),
            })

    track_object = {
        'id': track_info.get('id'),
        'title': track_info.get('title'),
        'version': track_info.get('version'),
        'explicit': track_info.get('explicit'),
        'trackNumber': track_info.get('trackNumber'),
        'replayGain': track_info.get('replayGain'),
        'duration': track_info.get('duration'),
        'discNumber': track_info.get('volumeNumber'),
        'copyright': track_info.get('copyright'),
        'url': track_info.get('url'),
        'isrc': track_info.get('isrc'),
        'maxAudioQuality': track_info.get('audioQuality'),
        'artists': track_artists,
        'track_streams': fetch_hifi_track_manifest(
            track_id,
            audio_quality=audio_quality or track_info.get('audioQuality')
        ).get('track_streams', {}) if include_streams else {},
    }

    if include_album:
        track_object['album'] = {
            'id': album_info.get('id'),
            'title': album_info.get('title'),
            'version': album_info.get('version'),
            'cover': album_info.get('cover'),
            'releaseDate': album_info.get('releaseDate'),
            'explicit': album_info.get('explicit'),
            'numberOfDiscs': album_info.get('numberOfVolumes'),
            'numberOfTracks': album_info.get('numberOfTracks'),
            'duration': album_info.get('duration'),
            'copyright': album_info.get('copyright'),
            'maxAudioQuality': album_info.get('audioQuality'),
            'url': album_info.get('url'),
            'artists': album_artists,
        }

    return {'track': track_object}


def get_hifi_album_object(album_id: Any, include_streams: bool = False, audio_quality: Any = None) -> Dict[str, Any]:
    """Build a normalized album object with artists and track objects.

    Args:
        album_id: HiFi album identifier.
        include_streams: If True, include `track_streams` for each track.
        audio_quality: Optional requested audio quality for the manifest fetch.
    """
    try:
        from .app import _fetch_hifi_album_payload, _fetch_hifi_artist_payload
    except ImportError:
        from squidly.app import _fetch_hifi_album_payload, _fetch_hifi_artist_payload

    album_response = _fetch_hifi_album_payload(album_id)
    album_info = extract_hifi_album_info(album_response)
    if not album_info:
        return {}

    artist_details_by_id: Dict[Any, Dict[str, Any]] = {}
    for artist_entry in album_info.get('album_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        if artist_id is None:
            continue
        artist_details_by_id[artist_id] = {
            'id': artist_id,
            'name': artist_entry.get('name'),
            'picture': artist_entry.get('picture'),
            'type': artist_entry.get('type'),
        }

    album_track_items = _extract_hifi_album_track_items(album_response)
    for track_item in album_track_items:
        if not isinstance(track_item, dict):
            continue
        artists_payload = track_item.get('artists') if isinstance(track_item.get('artists'), list) else []
        if isinstance(track_item.get('artist'), dict):
            artists_payload = [track_item.get('artist')]

        for artist_entry in artists_payload:
            if not isinstance(artist_entry, dict):
                continue
            artist_id = artist_entry.get('id')
            if artist_id is None or artist_id in artist_details_by_id:
                continue
            artist_details_by_id[artist_id] = _normalize_hifi_artist_entry(artist_entry)

    missing_artist_ids = [
        artist_id
        for artist_id, artist_details in artist_details_by_id.items()
        if artist_id is not None and (not artist_details.get('name') or not artist_details.get('picture'))
    ]

    artist_responses = {}
    if missing_artist_ids:
        artist_responses = {
            artist_id: _fetch_hifi_artist_payload(artist_id)
            for artist_id in missing_artist_ids
        }
        for artist_id in missing_artist_ids:
            artist_details = _resolve_hifi_artist_details(artist_id, artist_responses.get(artist_id))
            if artist_id in artist_details_by_id:
                artist_details_by_id[artist_id].update({
                    'name': artist_details.get('name'),
                    'picture': artist_details.get('picture'),
                })
            else:
                artist_details_by_id[artist_id] = {
                    'id': artist_details.get('id'),
                    'name': artist_details.get('name'),
                    'picture': artist_details.get('picture'),
                    'type': None,
                }

    album_artists = []
    for artist_entry in album_info.get('album_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        artist_details = artist_details_by_id.get(artist_id) or _resolve_hifi_artist_details(artist_id, artist_responses)
        album_artists.append({
            'id': artist_details.get('id'),
            'name': artist_details.get('name'),
            'picture': artist_details.get('picture'),
            'type': artist_entry.get('type'),
        })

    tracks = []
    for track_item in album_track_items:
        if not isinstance(track_item, dict):
            continue
        track = _build_hifi_track_object_from_album_item(
            track_item,
            artist_details_by_id,
            include_streams=include_streams,
            audio_quality=audio_quality
        )
        if track:
            tracks.append(track)

    album_object = {
        'id': album_info.get('id'),
        'title': album_info.get('title'),
        'version': album_info.get('version'),
        'cover': album_info.get('cover'),
        'releaseDate': album_info.get('releaseDate'),
        'numberOfTracks': album_info.get('numberOfTracks'),
        'numberOfDiscs': album_info.get('numberOfVolumes'),
        'explicit': album_info.get('explicit'),
        'duration': album_info.get('duration'),
        'copyright': album_info.get('copyright'),
        'maxAudioQuality': album_info.get('audioQuality'),
        'artists': album_artists,
        'tracks': tracks,
    }
    return {'album': album_object}


def fetch_hifi_track_manifest(track_id: Any, audio_quality: Any = None) -> Dict[str, Any]:
    """Fetch a single track manifest payload for a track at the requested quality.

    Use the legacy /track/ quality endpoint to return a direct stream URL.
    """
    try:
        from .app import _fetch_hifi_track_payload
    except ImportError:
        from squidly.app import _fetch_hifi_track_payload

    if not audio_quality:
        return {'track_streams': {}}

    track_streams: Dict[str, Any] = {}
    quality = str(audio_quality).strip()

    stream_entry: Dict[str, Any] = {
        'audioMode': None,
        'codec': None,
        'url': None,
        'error': None,
    }
    resolved_audio_quality = None

    try:
        payload = _fetch_hifi_track_payload(track_id, quality=quality)
        if not isinstance(payload, dict):
            raise ValueError(f'Unexpected payload type: {type(payload).__name__}')

        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        stream_entry['audioMode'] = data.get('audioMode') if isinstance(data, dict) else None
        resolved_audio_quality = data.get('audioQuality') if isinstance(data, dict) else None

        manifest_value = None
        if isinstance(data, dict):
            manifest_value = data.get('manifest')
        elif 'manifest' in payload:
            manifest_value = payload.get('manifest')

        if not isinstance(manifest_value, str):
            if manifest_value is None:
                raise ValueError('No manifest field found in payload')
            raise ValueError('Manifest field is not a string')

        normalized = manifest_value.replace('-', '+').replace('_', '/')
        normalized += '=' * (-len(normalized) % 4)
        decoded_bytes = base64.b64decode(normalized)
        decoded_manifest = json.loads(decoded_bytes.decode('utf-8'))

        stream_entry['codec'] = decoded_manifest.get('codecs')

        urls = decoded_manifest.get('urls') if isinstance(decoded_manifest, dict) else None
        if isinstance(urls, list) and urls:
            stream_entry['url'] = urls[0]
        else:
            raise ValueError('No urls found in decoded manifest')

    except Exception as exc:
        stream_entry['error'] = str(exc)

    key = resolved_audio_quality if resolved_audio_quality else quality
    track_streams[key] = stream_entry

    return {'track_streams': track_streams}
