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
            })
    elif isinstance(track_data.get('artist'), dict):
        artist_item = track_data.get('artist')
        artists.append({
            'id': artist_item.get('id'),
            'type': artist_item.get('type'),
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
            artist_id = artist_item.get('id')
            artist_type = artist_item.get('type')
            album_artists.append({
                'id': artist_id,
                'type': artist_type,
            })

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


def get_hifi_track_object(track_id: Any, include_streams: bool = False, include_album: bool = False) -> Dict[str, Any]:
    """Build a normalized track object by fetching HiFi track, album, and artist payloads.

    Args:
        track_id: HiFi track identifier.
        include_streams: If True, include `track_streams` from the manifest fetch.
        include_album: If True, include nested album metadata in the returned track.
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

    artist_ids = set()
    for artist_entry in track_info.get('track_artists', []):
        if isinstance(artist_entry, dict) and artist_entry.get('id') is not None:
            artist_ids.add(artist_entry.get('id'))
    for artist_entry in album_info.get('album_artists', []):
        if isinstance(artist_entry, dict) and artist_entry.get('id') is not None:
            artist_ids.add(artist_entry.get('id'))

    artist_responses = {}
    for artist_id in artist_ids:
        artist_responses[artist_id] = _fetch_hifi_artist_payload(artist_id)

    track_artists = []
    for artist_entry in track_info.get('track_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
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
        'track_streams': fetch_hifi_track_manifests(track_id).get('track_streams', {}) if include_streams else {},
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


def get_hifi_album_object(album_id: Any, include_streams: bool = False) -> Dict[str, Any]:
    """Build a normalized album object with artists and track objects.

    Args:
        album_id: HiFi album identifier.
        include_streams: If True, include `track_streams` for each track.
    """
    try:
        from .app import _fetch_hifi_album_payload, _fetch_hifi_artist_payload
    except ImportError:
        from squidly.app import _fetch_hifi_album_payload, _fetch_hifi_artist_payload

    album_response = _fetch_hifi_album_payload(album_id)
    album_info = extract_hifi_album_info(album_response)
    if not album_info:
        return {}

    artist_ids = {
        artist_entry.get('id')
        for artist_entry in album_info.get('album_artists', [])
        if isinstance(artist_entry, dict) and artist_entry.get('id') is not None
    }
    artist_responses = {
        artist_id: _fetch_hifi_artist_payload(artist_id)
        for artist_id in artist_ids
    }

    album_artists = []
    for artist_entry in album_info.get('album_artists', []):
        if not isinstance(artist_entry, dict):
            continue
        artist_id = artist_entry.get('id')
        artist_details = _resolve_hifi_artist_details(artist_id, artist_responses)
        album_artists.append({
            'id': artist_details.get('id'),
            'name': artist_details.get('name'),
            'picture': artist_details.get('picture'),
            'type': artist_entry.get('type'),
        })

    tracks = []
    for track_id in album_info.get('tracks', []):
        if track_id is None:
            continue
        track_payload = get_hifi_track_object(
            track_id,
            include_streams=include_streams,
            include_album=False,
        )
        track = track_payload.get('track', {})
        if track:
            tracks.append(track)

    return {
        'id': album_info.get('id'),
        'title': album_info.get('title'),
        'version': album_info.get('version'),
        'cover': album_info.get('cover'),
        'releaseDate': album_info.get('releaseDate'),
        'numberOfTracks': album_info.get('numberOfTracks'),
        'numberOfDiscs': album_info.get('numberOfVolumes'),
        'explicit': album_info.get('explicit'),
        'duration': album_info.get('duration'),
        'artists': album_artists,
        'tracks': tracks,
    }


def fetch_hifi_track_manifests(track_id: Any) -> Dict[str, Any]:
    """Fetch track manifest payloads for a track.

    Prefer the newer /trackManifests/ endpoint for a single adaptive manifest
    response, falling back to legacy /track/ quality requests if needed.
    """
    try:
        from .app import _fetch_hifi_track_manifests_payload, _fetch_hifi_track_payload
    except ImportError:
        from squidly.app import _fetch_hifi_track_manifests_payload, _fetch_hifi_track_payload

    track_streams: Dict[str, Any] = {}

    try:
        payload = _fetch_hifi_track_manifests_payload(
            track_id,
            formats=['HEAACV1', 'AACLC', 'FLAC', 'FLAC_HIRES'],
        )
        if isinstance(payload, dict):
            attributes = (
                payload.get('data', {})
                .get('data', {})
                .get('attributes', {})
                if isinstance(payload.get('data'), dict)
                else {}
            )
            uri = attributes.get('uri')
            formats = attributes.get('formats')
            if isinstance(uri, str) and isinstance(formats, list) and formats:
                for fmt in formats:
                    if not isinstance(fmt, str):
                        continue
                    track_streams[fmt] = {
                        'audioMode': None,
                        'codec': None,
                        'url': uri,
                        'error': None,
                    }
                return {'track_streams': track_streams}
    except Exception:
        pass

    # Fallback to legacy per-quality /track/ requests when trackManifests is unavailable.
    qualities = ['HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW']
    for quality in qualities:
        stream_entry: Dict[str, Any] = {
            'audioMode': None,
            'codec': None,
            'url': None,
            'error': None,
        }
        audio_quality = None

        try:
            payload = _fetch_hifi_track_payload(track_id, quality=quality)
            if not isinstance(payload, dict):
                raise ValueError(f'Unexpected payload type: {type(payload).__name__}')

            data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
            stream_entry['audioMode'] = data.get('audioMode') if isinstance(data, dict) else None
            audio_quality = data.get('audioQuality') if isinstance(data, dict) else None

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

        key = audio_quality if audio_quality else quality
        track_streams[key] = stream_entry

    return {'track_streams': track_streams}
