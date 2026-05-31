"""Listen history routes."""
from flask import Blueprint, jsonify, request
listen_history_bp = Blueprint("listen_history", __name__)

@listen_history_bp.route('/api/listen-history', methods=['GET'])
def get_listen_history_route():
    from squidly.infrastructure.storage import get_listen_history, resolve_plex_account_id
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    plex_account_id = resolve_plex_account_id(user_id)
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    history = get_listen_history(plex_account_id)
    return jsonify({'history': history})
