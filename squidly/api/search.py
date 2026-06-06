"""HiFi search and metadata routes."""

import logging
import re
from urllib.parse import urlencode

import requests
from flask import Blueprint, Response, jsonify, request, stream_with_context

from squidly.infrastructure import downloads
from squidly.services.metadata import get_active_metadata_provider
from squidly.services.hifi import (
    get_hifi_track_object,
    get_hifi_album_object,
    get_hifi_artist_object,
    _build_normalized_hifi_track_object,
    _get_hifi_album_dedupe_key,
    _get_hifi_track_dedupe_key,
    _get_hifi_audio_quality_rank,
    _normalize_hifi_playlist_items,
)
from squidly.infrastructure.downloads import get_squid_urls

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)


@search_bp.route('/api/hifi/search', methods=['GET'])
def search():
    """Unified search endpoint for tracks, albums, artists, playlists."""
    supported_search_types = ('s', 'a', 'al', 'p', 'trackid')
    provided_search_types = [key for key in supported_search_types if key in request.args]

    if not provided_search_types:
        return jsonify({'error': 'No search parameter provided. Use s, a, al, or p'}), 400

    if len(provided_search_types) > 1:
        return jsonify({'error': 'Provide exactly one search parameter: s, a, al, or p'}), 400

    search_type = provided_search_types[0]
    query = request.args.get(search_type)

    if not query:
        return jsonify({'error': 'Query value cannot be empty'}), 400

    provider = get_active_metadata_provider()

    limit = int(request.args.get('limit', 25))
    offset = int(request.args.get('offset', 0))

    if search_type == 'trackid':
        result = provider.get_track(query)
        if 'error' in result:
            return jsonify({'data': {'items': []}})
        return jsonify({'data': {'items': [result.get('track', {})]}})

    result = provider.search(query, search_type, limit=limit, offset=offset)
    return jsonify(result)


@search_bp.route('/api/hifi/tracks/<track_id>', methods=['GET'])
def track_info(track_id=None):
    """Get detailed track metadata."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    provider = get_active_metadata_provider()
    result = provider.get_track(track_id)
    return jsonify(result)


@search_bp.route('/api/hifi/tracks/<track_id>/stream', methods=['GET'])
def track_stream(track_id=None):
    """Proxy a HiFi track stream through the application."""
    track_id = str(track_id or request.args.get('id', '')).strip()
    quality = str(request.args.get('quality', 'LOW')).strip().upper()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    # Check if streaming is supported by current source
    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()
    if settings.get('metadata_source', 'tidal') == 'musicbrainz':
        return jsonify({'error': 'Streaming is not available when using MusicBrainz as the browse source.'}), 501

    valid_qualities = {'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW'}
    if quality not in valid_qualities:
        return jsonify({'error': 'Invalid quality. Must be one of: ' + ', '.join(sorted(valid_qualities))}), 400

    try:
        result = get_hifi_track_object(
            track_id,
            include_streams=True,
            include_album=False,
            audio_quality=quality
        )

        track = result.get('track') if isinstance(result, dict) else None
        if not isinstance(track, dict):
            return jsonify({'error': 'Failed to build track object'}), 500

        streams = track.get('track_streams') if isinstance(track.get('track_streams'), dict) else {}
        stream_entry = streams.get(quality) or next(
            (entry for entry in streams.values() if isinstance(entry, dict) and isinstance(entry.get('url'), str) and entry.get('url')), None
        )

        if not stream_entry or not isinstance(stream_entry.get('url'), str):
            return jsonify({'error': 'No stream URL available for this track'}), 500

        stream_url = stream_entry.get('url')
        headers = {}
        if request.headers.get('Range'):
            headers['Range'] = request.headers.get('Range')

        upstream_response = requests.get(stream_url, headers=headers, stream=True, timeout=20)
        if upstream_response.status_code >= 400:
            return jsonify({
                'error': 'Failed to fetch upstream audio stream',
                'status_code': upstream_response.status_code,
                'details': upstream_response.reason
            }), upstream_response.status_code

        excluded_headers = {
            'content-encoding',
            'transfer-encoding',
            'connection',
            'keep-alive',
            'proxy-authenticate',
            'proxy-authorization',
            'te',
            'trailers',
            'upgrade'
        }

        response_headers = [
            (name, value)
            for name, value in upstream_response.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(
            stream_with_context(upstream_response.iter_content(chunk_size=65536)),
            status=upstream_response.status_code,
            headers=response_headers
        )
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502
    except Exception as e:
        return jsonify({'error': 'Failed to stream track', 'details': str(e)}), 500


@search_bp.route('/api/hifi/albums/<album_id>', methods=['GET'])
def album_object(album_id=None):
    """Get a normalized HiFi album object."""
    album_id = str(album_id or '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID path parameter is required'}), 400

    provider = get_active_metadata_provider()
    result = provider.get_album(album_id)
    return jsonify(result)


@search_bp.route('/api/hifi/artists/<artist_id>', methods=['GET'])
def artist_object(artist_id=None):
    """Get a normalized HiFi artist object."""
    artist_id = str(artist_id or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID path parameter is required'}), 400

    provider = get_active_metadata_provider()
    result = provider.get_artist(artist_id)
    return jsonify(result)


@search_bp.route('/api/hifi/playlists/<playlist_id>', methods=['GET'])
def playlist_object(playlist_id=None):
    """Get a normalized HiFi playlist object."""
    playlist_id = str(playlist_id or '').strip()

    if not playlist_id:
        return jsonify({'error': 'Playlist ID path parameter is required'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/playlists/{playlist_id}",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']

        if isinstance(result, dict) and 'data' in result:
            data = result.get('data')
            if isinstance(data, dict):
                items = data.get('items')
                if isinstance(items, list):
                    normalized_items = _normalize_hifi_playlist_items(items)
                    data['items'] = normalized_items

        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'Proxy error',
            'details': str(e)
        }), 502


@search_bp.route('/api/hifi/tracks/<track_id>/similar', methods=['GET'])
def track_similar(track_id=None):
    """Get similar tracks for a given track ID."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/recommendations/?id={track_id}",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502


@search_bp.route('/api/hifi/artists/<artist_id>/similar', methods=['GET'])
def artist_similar(artist_id=None):
    """Get similar artists for a given artist ID."""
    artist_id = str(artist_id or request.args.get('id') or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/artist/similar/?id={artist_id}",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502


@search_bp.route('/api/hifi/albums/<album_id>/similar', methods=['GET'])
def album_similar(album_id=None):
    """Get similar albums for a given album ID."""
    album_id = str(album_id or request.args.get('id') or '').strip()

    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/album/similar/?id={album_id}",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )

        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code

        result = response.json()
        result['proxied_via'] = target['name']
        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Proxy error', 'details': str(e)}), 502


@search_bp.route('/api/source', methods=['GET'])
def get_source_info():
    """Get current browse source and its capabilities."""
    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()
    source = settings.get('metadata_source', 'tidal')

    capabilities = {
        'tidal': {
            'source': 'tidal',
            'supports_similar': True,
            'supports_streaming': True,
            'supports_quality_badges': True,
            'supports_playlists': True,
            'supports_artist_images': True,
        },
        'musicbrainz': {
            'source': 'musicbrainz',
            'supports_similar': False,
            'supports_streaming': False,
            'supports_quality_badges': False,
            'supports_playlists': False,
            'supports_artist_images': False,
        },
    }

    return jsonify(capabilities.get(source, capabilities['tidal']))


@search_bp.route('/api/lastfm/playlist', methods=['POST'])
def lastfm_playlist():
    """Scrape a Last.fm playlist and return the track list."""
    import re
    data = request.get_json()
    playlist_url = data.get('playlistUrl', '')

    if not playlist_url:
        return jsonify({'error': 'Playlist URL is required'}), 400

    try:
        response = requests.get(playlist_url, timeout=10)
        response.raise_for_status()
        html = response.text

        playlist_name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        playlist_name = playlist_name_match.group(1).strip() if playlist_name_match else 'Last.fm Playlist'

        tracks = []
        seen_tracks = set()

        track_pattern = re.compile(
            r'<a[^>]*href="/music/[^/]+/_/[^/]+/([^"]+)"[^>]*>\s*<span[^>]*class="link-block-target"[^>]*>([^<]+)</span>',
            re.MULTILINE
        )

        for match in track_pattern.finditer(html):
            artist_name = match.group(1).strip()
            track_name = match.group(2).strip()

            if not artist_name or not track_name:
                continue

            track_key = f"{artist_name.casefold()}|{track_name.casefold()}"
            if track_key in seen_tracks:
                continue

            seen_tracks.add(track_key)
            tracks.append({
                'name': track_name,
                'artist': artist_name
            })

        if len(tracks) == 0:
            return jsonify({
                'error': 'No tracks found. The playlist may be private, empty, or unavailable.'
            }), 400

        return jsonify({
            'playlistName': playlist_name,
            'trackCount': len(tracks),
            'tracks': tracks
        })

    except Exception as e:
        logger.info("Last.fm scraping error: %s", e)
        return jsonify({
            'error': 'Failed to process Last.fm playlist',
            'details': str(e)
        }), 500
