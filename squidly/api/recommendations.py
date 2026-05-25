"""Recommendation routes."""
from flask import Blueprint, jsonify, request
recommendations_bp = Blueprint("recommendations", __name__)

@recommendations_bp.route('/api/recommendations/playlists', methods=['GET'])
def list_recommendation_playlists_route():
    from squidly.storage import list_recommendation_playlists, has_listen_history, get_all_plex_account_mappings
    from datetime import datetime
    user_id = request.args.get('user_id', '').strip() or None
    plex_account_id = None
    if user_id:
        mappings = get_all_plex_account_mappings()
        for m in mappings:
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break
    if plex_account_id is None:
        return jsonify({'playlists': [], 'has_history': False})
    has_history = has_listen_history(plex_account_id)
    playlists = list_recommendation_playlists(plex_account_id)
    result = []
    for p in playlists:
        generated_at = p.get('generated_at')
        result.append({
            'id': p['id'], 'name': p['name'], 'slug': p['slug'], 'strategy': p['strategy'],
            'seed_count': p['seed_count'], 'track_count': p['track_count'],
            'generated_at': generated_at.isoformat() + 'Z' if isinstance(generated_at, datetime) else str(generated_at),
        })
    return jsonify({'playlists': result, 'has_history': has_history})

@recommendations_bp.route('/api/recommendations/generate', methods=['POST'])
def generate_recommendation_playlist():
    from squidly.jobs.orchestration import queue_recommendation_generation
    from squidly.storage import get_all_plex_account_mappings
    data = request.json if request.is_json else {}
    slug = data.get('slug', 'fresh-finds')
    user_id = data.get('user_id', '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    plex_account_id = None
    plex_username = None
    mappings = get_all_plex_account_mappings()
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            plex_username = m.get('username')
            break
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    job_id = queue_recommendation_generation(slug=slug, plex_account_id=plex_account_id, plex_username=plex_username or 'Unknown', trigger='manual')
    if job_id is None:
        return jsonify({'error': 'A recommendation generation job is already queued or in progress'}), 409
    return jsonify({'ok': True, 'job_id': job_id, 'status': 'queued'}), 202

@recommendations_bp.route('/api/recommendations/<slug>', methods=['GET'])
def get_recommendation_playlist_route(slug):
    from squidly.storage import get_recommendation_playlist, get_all_plex_account_mappings
    from datetime import datetime
    user_id = request.args.get('user_id', '').strip() or None
    plex_account_id = None
    if user_id:
        mappings = get_all_plex_account_mappings()
        for m in mappings:
            if str(m.get('plex_client_id') or '') == user_id:
                plex_account_id = m.get('plex_account_id')
                break
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    playlist_id_param = request.args.get('playlist_id', '').strip()
    playlist_id = int(playlist_id_param) if playlist_id_param.isdigit() else None
    playlist_data = get_recommendation_playlist(plex_account_id, slug, playlist_id=playlist_id)
    if not playlist_data:
        return jsonify({'error': 'Playlist not found'}), 404
    generated_at = playlist_data.get('generated_at')
    tracks = []
    for t in playlist_data['tracks']:
        artist_id = t.get('artist_id')
        album_id = t.get('album_id')
        tracks.append({
            'id': t['hifi_id'], 'title': t['title'],
            'artists': [{'id': artist_id, 'name': t['artist'] or 'Unknown Artist'}] if t['artist'] else [],
            'album': {'id': album_id, 'title': t['album'] or '', 'cover': t['cover']} if t['album'] or t['cover'] else {},
            'duration': t['duration'], 'explicit': False, 'maxAudioQuality': t.get('quality') or '',
        })
    return jsonify({
        'playlist': {
            'slug': playlist_data['slug'], 'name': playlist_data['name'],
            'track_count': playlist_data['track_count'],
            'generated_at': generated_at.isoformat() + 'Z' if isinstance(generated_at, datetime) else str(generated_at),
        },
        'tracks': tracks
    })
