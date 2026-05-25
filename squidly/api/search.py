"""HiFi search and metadata routes."""

import re
from urllib.parse import urlencode

import requests
from flask import Blueprint, Response, jsonify, request, stream_with_context

from squidly.infrastructure import downloads
from squidly.services.hifi import (
    get_hifi_track_object,
    get_hifi_album_object,
    get_hifi_artist_object,
    _build_normalized_hifi_track_object,
    _get_hifi_album_dedupe_key,
    _get_hifi_track_dedupe_key,
    _get_hifi_audio_quality_rank,
    _fetch_hifi_search_results,
    _fetch_hifi_track_manifests_payload,
    _normalize_hifi_playlist_items,
)
from squidly.infrastructure.downloads import get_squid_urls

search_bp = Blueprint('search', __name__)


def _get_album_quality_rank(album):
    """Extract audio quality rank from an album object."""
    quality_order = {
        'HI_RES_LOSSLESS': 5,
        'HIRES_LOSSLESS': 5,
        'DOLBY_ATMOS': 5,
        'LOSSLESS': 4,
        'HIGH': 2,
        'LOW': 1
    }
    rank = 0
    media_metadata = album.get('mediaMetadata')
    if isinstance(media_metadata, dict):
        tags = media_metadata.get('tags')
        if isinstance(tags, list):
            for tag in tags:
                if tag in quality_order:
                    rank = max(rank, quality_order[tag])
    audio_quality = album.get('audioQuality')
    if isinstance(audio_quality, str) and audio_quality in quality_order:
        rank = max(rank, quality_order[audio_quality])
    return rank


def _derive_audio_quality_from_tags(album):
    """Derive maxAudioQuality from mediaTags or mediaMetadata.tags."""
    quality_priority = ['DOLBY_ATMOS', 'HIRES_LOSSLESS', 'HI_RES_LOSSLESS', 'LOSSLESS', 'HIGH', 'LOW']
    media_metadata = album.get('mediaMetadata')
    if isinstance(media_metadata, dict):
        tags = media_metadata.get('tags')
        if isinstance(tags, list):
            tags_upper = [t.upper() for t in tags if t]
            for q in quality_priority:
                if q in tags_upper:
                    return q
    media_tags = album.get('mediaTags')
    if isinstance(media_tags, list):
        tags_upper = [t.upper() for t in media_tags if t]
        for q in quality_priority:
            if q in tags_upper:
                return q
    return None


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

    if search_type == 'trackid':
        if not query.isdigit():
            return jsonify({'error': 'Track ID must be numeric'}), 400

        try:
            response, target = downloads.make_request_with_retry_rotating_mirrors(
                f"/info/?{urlencode({'id': query})}",
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

            result = response.json() if response.content else {}
            track_item = None

            if isinstance(result, dict):
                data = result.get('data') or {}
                if isinstance(data, dict) and data.get('track'):
                    track_item = data.get('track')
                elif isinstance(data, dict) and data.get('items'):
                    items = data.get('items')
                    if isinstance(items, list) and items:
                        track_item = items[0]
                elif isinstance(result.get('track'), dict):
                    track_item = result.get('track')
                elif isinstance(result.get('data'), dict):
                    track_item = result.get('data')

            if not track_item:
                return jsonify({
                    'data': {'items': []},
                    'proxied_via': target['name']
                })

            if 'id' not in track_item or not track_item.get('id'):
                track_item['id'] = int(query)

            normalized_track_item = _build_normalized_hifi_track_object(track_item) if isinstance(track_item, dict) else track_item

            return jsonify({
                'data': {'items': [normalized_track_item]},
                'proxied_via': target['name']
            })

        except requests.exceptions.RequestException as e:
            return jsonify({
                'error': 'Proxy error',
                'details': str(e),
                'query': query
            }), 502

    upstream_params = [(search_type, query)]
    for param_name in ('limit', 'offset'):
        param_value = request.args.get(param_name)
        if param_value:
            upstream_params.append((param_name, param_value))

    upstream_query = urlencode(upstream_params)
    
    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/search/?{upstream_query}",
            get_squid_urls(),
            max_retries=3
        )
        
        if not response.ok:
            return jsonify({
                'error': f'Upstream API error via {target["name"]}',
                'status_code': response.status_code
            }), response.status_code
        
        result = response.json()
        result['proxied_via'] = target['name']
        
        if isinstance(result, dict):
            data = result.get('data')
            if isinstance(data, dict):
                if search_type == 'al':
                    albums = data.get('albums')
                    if isinstance(albums, dict):
                        album_items = albums.get('items')
                        if isinstance(album_items, list):
                            best_by_key = {}
                            for album in album_items:
                                if not isinstance(album, dict):
                                    continue
                                key = _get_hifi_album_dedupe_key(album)
                                if key is None:
                                    continue
                                existing = best_by_key.get(key)
                                if existing is None:
                                    best_by_key[key] = album
                                    continue
                                current_rank = _get_hifi_audio_quality_rank(album.get('audioQuality'))
                                existing_rank = _get_hifi_audio_quality_rank(existing.get('audioQuality'))
                                if current_rank > existing_rank:
                                    best_by_key[key] = album

                            deduped_items = []
                            seen_keys = set()
                            for album in album_items:
                                if not isinstance(album, dict):
                                    continue
                                key = _get_hifi_album_dedupe_key(album)
                                if key is None:
                                    deduped_items.append(album)
                                    continue
                                if key in seen_keys:
                                    continue
                                chosen = best_by_key.get(key)
                                if chosen is not None:
                                    deduped_items.append(chosen)
                                    seen_keys.add(key)
                                else:
                                    deduped_items.append(album)
                                    seen_keys.add(key)

                            albums['items'] = deduped_items
                elif search_type == 's':
                    items = data.get('items')
                    if isinstance(items, list):
                        best_by_key = {}
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            key = _get_hifi_track_dedupe_key(item)
                            if key is None:
                                continue
                            existing = best_by_key.get(key)
                            if existing is None:
                                best_by_key[key] = item
                                continue
                            current_rank = _get_hifi_audio_quality_rank(item.get('audioQuality'))
                            existing_rank = _get_hifi_audio_quality_rank(existing.get('audioQuality'))
                            if current_rank > existing_rank:
                                best_by_key[key] = item

                        deduped_items = []
                        seen_keys = set()
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            key = _get_hifi_track_dedupe_key(item)
                            if key is None:
                                deduped_items.append(item)
                                continue
                            if key in seen_keys:
                                continue
                            chosen = best_by_key.get(key)
                            if chosen is not None:
                                deduped_items.append(chosen)
                                seen_keys.add(key)
                            else:
                                deduped_items.append(item)
                                seen_keys.add(key)

                        data['items'] = [_build_normalized_hifi_track_object(item) if isinstance(item, dict) else item for item in deduped_items]

        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': f'Proxy error',
            'details': str(e),
            'query': query
        }), 502


@search_bp.route('/api/hifi/tracks/<track_id>', methods=['GET'])
def track_info(track_id=None):
    """Get detailed track metadata."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    upstream_query = urlencode({'id': track_id})
    
    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/info/?{upstream_query}",
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
        return jsonify({
            'error': f'Proxy error',
            'details': str(e)
        }), 502


@search_bp.route('/api/hifi/tracks/<track_id>/object', methods=['GET'])
def track_object(track_id=None):
    """Get a normalized HiFi track object."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

    include_streams = str(request.args.get('include_streams', 'false')).strip().lower() in ('1', 'true', 'yes')
    include_album = str(request.args.get('include_album', 'false')).strip().lower() in ('1', 'true', 'yes')
    audio_quality = str(request.args.get('audio_quality', '')).strip() or None

    try:
        result = get_hifi_track_object(
            track_id,
            include_streams=include_streams,
            include_album=include_album,
            audio_quality=audio_quality
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build track object', 'details': str(e)}), 500


@search_bp.route('/api/hifi/tracks/<track_id>/stream', methods=['GET'])
def track_stream(track_id=None):
    """Proxy a HiFi track stream through the application."""
    track_id = str(track_id or request.args.get('id', '')).strip()
    quality = str(request.args.get('quality', 'LOW')).strip().upper()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID parameter must be a numeric Tidal track ID'}), 400

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

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID path parameter must be a numeric Tidal album ID'}), 400

    include_streams = str(request.args.get('include_streams', 'false')).strip().lower() in ('1', 'true', 'yes')
    audio_quality = str(request.args.get('audio_quality', '')).strip() or None

    try:
        result = get_hifi_album_object(
            album_id,
            include_streams=include_streams,
            audio_quality=audio_quality
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build album object', 'details': str(e)}), 500


@search_bp.route('/api/hifi/artists/<artist_id>', methods=['GET'])
def artist_object(artist_id=None):
    """Get a normalized HiFi artist object."""
    artist_id = str(artist_id or '').strip()

    if not artist_id:
        return jsonify({'error': 'Artist ID path parameter is required'}), 400

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID path parameter must be a numeric Tidal artist ID'}), 400

    try:
        result = get_hifi_artist_object(artist_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to build artist object', 'details': str(e)}), 500


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


@search_bp.route('/api/hifi/tracks/<track_id>/manifest', methods=['GET'])
def track_manifest(track_id=None):
    """Get the manifest (streaming URLs) for a track."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID must be numeric'}), 400

    audio_quality = str(request.args.get('audio_quality', 'LOSSLESS')).strip().upper()

    try:
        result = _fetch_hifi_track_manifests_payload(track_id, audio_quality=audio_quality)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch track manifest', 'details': str(e)}), 500


@search_bp.route('/api/hifi/tracks/<track_id>/similar', methods=['GET'])
def track_similar(track_id=None):
    """Get similar tracks for a given track ID."""
    track_id = str(track_id or request.args.get('id') or '').strip()

    if not track_id:
        return jsonify({'error': 'Track ID parameter is required'}), 400

    if not track_id.isdigit():
        return jsonify({'error': 'Track ID must be numeric'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/tracks/{track_id}/similar",
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

    if not artist_id.isdigit():
        return jsonify({'error': 'Artist ID must be numeric'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/artists/{artist_id}/similar",
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

    if not album_id.isdigit():
        return jsonify({'error': 'Album ID must be numeric'}), 400

    try:
        response, target = downloads.make_request_with_retry_rotating_mirrors(
            f"/albums/{album_id}/similar",
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
        from squidly.app import logger
        logger.info("Last.fm scraping error: %s", e)
        return jsonify({
            'error': 'Failed to process Last.fm playlist',
            'details': str(e)
        }), 500
