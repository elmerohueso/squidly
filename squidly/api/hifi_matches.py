"""HiFi matches routes."""
import logging
import re

from flask import Blueprint, jsonify, request

from squidly.utils import _safe_float, _safe_int, _now_utc
from squidly.storage import get_plex_config
from squidly.matching import (
    MATCH_REVIEW_ARTWORK_SIZE,
    _fetch_match_review_row,
    _build_artist_match_candidates,
    _build_album_match_candidates,
    _build_track_match_candidates,
    _fetch_source_album_track_titles_map,
    _cascade_track_confirm_ids,
    _refresh_album_completeness,
    _get_album_row,
    _build_stored_track_match_lookup,
    _build_stored_album_match_lookup,
    _build_stored_artist_match_lookup,
)
from squidly.jobs.orchestration import (
    is_job_type_running_or_queued,
    start_plex_library_update_job,
)
from squidly.api.plex_routes import _resolve_plex_library_context
from squidly.db import get_db_connection

logger = logging.getLogger(__name__)

hifi_matches_bp = Blueprint("hifi_matches", __name__)


def _get_match_review_plex_context():
    try:
        config = get_plex_config()
        server_url = str(config.get('server_url') or '').strip()
        api_token = str(config.get('api_token') or '').strip()
        library_name = str(config.get('library_name') or '').strip()
        if not server_url or not api_token or not library_name:
            return None, None, None

        _, library, _ = _resolve_plex_library_context(server_url, api_token, library_name)
        if not library:
            return None, None, None

        return server_url, api_token, library
    except Exception as e:
        logger.info("[MATCH_REVIEW] Unable to resolve Plex context for artwork: %s", str(e))
        return None, None, None


def _fetch_plex_item_image_map(library, server_url, api_token, library_ids, image_size=None):
    from squidly.api.plex_routes import _build_plex_image_url
    
    if not library or not server_url or not api_token:
        return {}

    image_map = {}
    for library_id in library_ids or []:
        normalized_id = str(library_id or '').strip()
        if not normalized_id or normalized_id in image_map:
            continue
        try:
            item = library.fetchItem(f'/library/metadata/{normalized_id}')
            image_map[normalized_id] = _build_plex_image_url(
                server_url,
                api_token,
                getattr(item, 'thumb', None),
                image_size=image_size,
            ) if item else None
        except Exception as e:
            logger.info("[MATCH_REVIEW] Failed to fetch Plex artwork for %s: %s", normalized_id, str(e))
            image_map[normalized_id] = None

    return image_map


@hifi_matches_bp.route('/api/hifi/matches', methods=['POST'])
def start_hifi_match_endpoint():
    """Queue a Plex library update, which chains to sync → automatic matching."""
    result = start_plex_library_update_job(trigger='manual')
    if not result.get('ok'):
        status_code = result.get('status_code', 500)
        return jsonify({'error': result.get('error')}), int(status_code)

    return jsonify({'success': True, 'job_id': result.get('job_id'), 'status': result.get('status')}), 202


@hifi_matches_bp.route('/api/hifi/matches/lookup', methods=['POST'])
def lookup_hifi_matches_endpoint():
    payload = request.get_json(silent=True) or {}
    track_ids = payload.get('track_ids') or []
    album_ids = payload.get('album_ids') or []
    artist_ids = payload.get('artist_ids') or []

    if not isinstance(track_ids, list) or not isinstance(album_ids, list) or not isinstance(artist_ids, list):
        return jsonify({'error': 'track_ids, album_ids, and artist_ids must be arrays'}), 400

    if len(track_ids) > 200 or len(album_ids) > 200 or len(artist_ids) > 200:
        return jsonify({'error': 'track_ids, album_ids, and artist_ids are limited to 200 items each'}), 400

    normalized_track_ids = [str(item).strip() for item in track_ids if str(item).strip()]
    normalized_album_ids = [str(item).strip() for item in album_ids if str(item).strip()]
    normalized_artist_ids = [str(item).strip() for item in artist_ids if str(item).strip()]

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return jsonify({
            'success': True,
            'tracks': _build_stored_track_match_lookup(cur, normalized_track_ids),
            'albums': _build_stored_album_match_lookup(cur, normalized_album_ids),
            'artists': _build_stored_artist_match_lookup(cur, normalized_artist_ids),
        })
    finally:
        conn.close()


@hifi_matches_bp.route('/api/hifi/matches/review', methods=['GET'])
def get_hifi_match_review_endpoint():
    entity_type = str(request.args.get('entity_type') or 'all').strip().lower()
    limit = _safe_int(request.args.get('limit')) or 50
    limit = max(1, min(limit, 200))
    max_confidence = _safe_float(request.args.get('max_confidence'), default=0.94)

    include_artists = entity_type in ('all', 'artist', 'artists')
    include_albums = entity_type in ('all', 'album', 'albums')
    include_tracks = entity_type in ('all', 'track', 'tracks')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        response = {
            'success': True,
            'summary': {
                'artists': 0,
                'albums': 0,
                'tracks': 0,
            }
        }
        server_url, api_token, library = _get_match_review_plex_context()

        if include_artists:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM artists
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['artists'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT artist_id, name, library_id, hifi_id, confidence, last_seen_at
                FROM artists
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                ORDER BY confidence ASC, artist_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            artists = cur.fetchall() or []
            artist_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in artists],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in artists:
                item['picture'] = artist_image_map.get(str(item.get('library_id') or '').strip())
            response['artists'] = artists

        if include_albums:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM albums
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['albums'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT albums.album_id, albums.artist_id, albums.title, albums.library_id, albums.hifi_id,
                       albums.confidence, albums.complete, albums.matched_track_count,
                       albums.expected_track_count, albums.last_seen_at,
                       artists.name AS artist_name
                FROM albums
                LEFT JOIN artists ON artists.artist_id = albums.artist_id
                WHERE albums.library_id IS NOT NULL
                  AND (albums.hifi_id IS NULL OR albums.confidence < %s)
                ORDER BY albums.confidence ASC, albums.album_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            albums = cur.fetchall() or []
            album_track_titles_map = _fetch_source_album_track_titles_map(cur, [item.get('album_id') for item in albums])
            album_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in albums],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in albums:
                item['track_titles'] = album_track_titles_map.get(int(item.get('album_id')), []) if item.get('album_id') is not None else []
                item['cover'] = album_image_map.get(str(item.get('library_id') or '').strip())
            response['albums'] = albums

        if include_tracks:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM tracks
                WHERE library_id IS NOT NULL
                  AND (hifi_id IS NULL OR confidence < %s)
                """,
                (max_confidence,)
            )
            response['summary']['tracks'] = _safe_int((cur.fetchone() or {}).get('count')) or 0

            cur.execute(
                """
                SELECT tracks.track_id, tracks.album_id, tracks.artist_id, tracks.title, tracks.library_id,
                       tracks.hifi_id, tracks.confidence, tracks.path, tracks.format, tracks.bitrate,
                       tracks.disc_number, tracks.track_number, tracks.last_seen_at, tracks.isrc, tracks.duration,
                       albums.title AS album_title,
                       albums.library_id AS album_library_id,
                       artists.name AS artist_name,
                       artists.library_id AS artist_library_id
                FROM tracks
                LEFT JOIN albums ON albums.album_id = tracks.album_id
                LEFT JOIN artists ON artists.artist_id = tracks.artist_id
                WHERE tracks.library_id IS NOT NULL
                  AND (tracks.hifi_id IS NULL OR tracks.confidence < %s)
                ORDER BY tracks.confidence ASC, tracks.track_id ASC
                LIMIT %s
                """,
                (max_confidence, limit)
            )
            tracks = cur.fetchall() or []
            track_album_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('album_library_id') for item in tracks],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            track_image_map = _fetch_plex_item_image_map(
                library,
                server_url,
                api_token,
                [item.get('library_id') for item in tracks],
                image_size=MATCH_REVIEW_ARTWORK_SIZE,
            )
            for item in tracks:
                album_library_id = str(item.get('album_library_id') or '').strip()
                track_library_id = str(item.get('library_id') or '').strip()
                item['cover'] = track_album_image_map.get(album_library_id) or track_image_map.get(track_library_id)
            response['tracks'] = tracks

        return jsonify(response)
    finally:
        conn.close()


@hifi_matches_bp.route('/api/hifi/matches/candidates', methods=['GET'])
def get_hifi_match_candidates_endpoint():
    entity_type = str(request.args.get('entity_type') or '').strip().lower()
    entity_id = _safe_int(request.args.get('id'))
    limit = _safe_int(request.args.get('limit')) or 3
    limit = max(1, min(limit, 20))
    query_override = str(request.args.get('query') or '').strip() or None

    if entity_type not in ('artist', 'album', 'track'):
        return jsonify({'error': 'entity_type must be one of artist, album, or track'}), 400
    if not entity_id:
        return jsonify({'error': 'id is required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        row = _fetch_match_review_row(cur, entity_type, entity_id)
        if not row:
            return jsonify({'error': f'{entity_type} not found'}), 404

        if entity_type == 'artist':
            candidates = _build_artist_match_candidates(row, limit=limit, query_override=query_override)
        elif entity_type == 'album':
            source_track_titles_map = _fetch_source_album_track_titles_map(cur, [row.get('album_id')])
            source_track_titles = source_track_titles_map.get(int(row.get('album_id')), []) if row.get('album_id') is not None else []
            candidates = _build_album_match_candidates(row, limit=limit, query_override=query_override, source_track_titles=source_track_titles)
            if not candidates and not query_override:
                album_title = str(row.get('title') or '').strip()
                artist_name = str(row.get('artist_name') or '').strip()
                stripped_title = re.sub(r'\s*\([^)]*\)', '', album_title).strip()

                fallback_queries = []
                for value in (
                    artist_name,
                    stripped_title,
                    f"{artist_name} {stripped_title}".strip() if artist_name and stripped_title else '',
                    f"{artist_name} {album_title}".strip() if artist_name and album_title else '',
                ):
                    query = str(value or '').strip()
                    if query and query not in fallback_queries:
                        fallback_queries.append(query)

                merged = []
                seen_hifi_ids = set()
                for fallback_query in fallback_queries:
                    fallback_candidates = _build_album_match_candidates(
                        row,
                        limit=limit,
                        query_override=fallback_query,
                        source_track_titles=source_track_titles,
                    )
                    for candidate in fallback_candidates:
                        hifi_id = str(candidate.get('hifi_id') or '').strip()
                        if not hifi_id or hifi_id in seen_hifi_ids:
                            continue
                        seen_hifi_ids.add(hifi_id)
                        merged.append(candidate)
                    if len(merged) >= limit:
                        break

                if merged:
                    merged.sort(key=lambda candidate: (-_safe_float(candidate.get('confidence')), str(candidate.get('title') or '').lower()))
                    candidates = merged[:limit]
        else:
            candidates = _build_track_match_candidates(row, limit=limit, query_override=query_override)

        return jsonify({'success': True, 'candidates': candidates})
    finally:
        conn.close()


@hifi_matches_bp.route('/api/hifi/matches/review', methods=['POST'])
def update_hifi_match_review_endpoint():
    payload = request.get_json(silent=True) or {}
    entity_type = str(payload.get('entity_type') or '').strip().lower()
    action = str(payload.get('action') or '').strip().lower()
    raw_hifi_id = str(payload.get('hifi_id') or '').strip() or None
    entity_id = _safe_int(payload.get('id'))

    if entity_type not in ('artist', 'album', 'track'):
        return jsonify({'error': 'entity_type must be one of artist, album, or track'}), 400
    if action not in ('confirm', 'reject'):
        return jsonify({'error': 'action must be confirm or reject'}), 400
    if not entity_id:
        return jsonify({'error': 'id is required'}), 400

    if is_job_type_running_or_queued('hifi_match'):
        return jsonify({'error': 'Manual matching is disabled while Hifi Match is running. Please wait for the current scan to finish.'}), 409

    table_name = {'artist': 'artists', 'album': 'albums', 'track': 'tracks'}[entity_type]
    id_column = {'artist': 'artist_id', 'album': 'album_id', 'track': 'track_id'}[entity_type]
    now_dt = _now_utc()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT * FROM {table_name} WHERE {id_column} = %s",
            (entity_id,)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'error': f'{entity_type} not found'}), 404

        if action == 'confirm':
            effective_hifi_id = raw_hifi_id or (str(row.get('hifi_id') or '').strip() or None)
            if not effective_hifi_id:
                return jsonify({'error': 'hifi_id is required to confirm an unmatched row'}), 400
            if entity_type == 'track':
                updated_track_album_id = _cascade_track_confirm_ids(cur, row, effective_hifi_id, now_dt)
            else:
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = %s,
                        confidence = 1.0
                    WHERE {id_column} = %s
                    """,
                    (effective_hifi_id, entity_id)
                )
        else:
            if entity_type == 'album':
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = NULL,
                        confidence = 0,
                        complete = FALSE,
                        matched_track_count = 0,
                        expected_track_count = 0
                    WHERE {id_column} = %s
                    """,
                    (entity_id,)
                )
            else:
                cur.execute(
                    f"""
                    UPDATE {table_name}
                    SET hifi_id = NULL,
                        confidence = 0
                    WHERE {id_column} = %s
                    """,
                    (entity_id,)
                )

        if entity_type == 'album':
            album_row = _get_album_row(cur, entity_id)
            if album_row:
                _refresh_album_completeness(cur, album_row)
        elif entity_type == 'track':
            album_id = updated_track_album_id or row.get('album_id')
            if album_id:
                album_row = _get_album_row(cur, album_id)
                if album_row:
                    _refresh_album_completeness(cur, album_row)

        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()
