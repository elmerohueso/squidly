"""Listen history routes."""
from flask import Blueprint, jsonify, request
listen_history_bp = Blueprint("listen_history", __name__)

@listen_history_bp.route('/api/listen-history', methods=['GET'])
def get_listen_history_route():
    from squidly.infrastructure.storage import get_listen_history, get_all_plex_account_mappings
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    history = get_listen_history(plex_account_id)
    return jsonify({'history': history})

@listen_history_bp.route('/api/listen-history/users', methods=['GET'])
def get_listen_history_users():
    from squidly.infrastructure.storage import get_all_plex_account_mappings
    mappings = get_all_plex_account_mappings()
    users = [{'plex_client_id': m.get('plex_client_id'), 'username': m.get('username')} for m in mappings]
    return jsonify({'users': users})

@listen_history_bp.route('/api/listen-history/sync', methods=['POST'])
def sync_listen_history():
    from squidly.jobs.orchestration import queue_plex_listen_history_sync
    from squidly.infrastructure.storage import get_all_plex_account_mappings
    data = request.json if request.is_json else {}
    user_id = data.get('user_id', '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    plex_username = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            plex_username = m.get('username')
            break
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    job_id = queue_plex_listen_history_sync(plex_account_id=plex_account_id, plex_username=plex_username or 'Unknown')
    return jsonify({'ok': True, 'job_id': job_id}), 202

@listen_history_bp.route('/api/listen-history/sync-status', methods=['GET'])
def get_listen_history_sync_status_route():
    from squidly.infrastructure.storage import get_listen_history_sync_status, get_all_plex_account_mappings
    user_id = request.args.get('user_id', '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    mappings = get_all_plex_account_mappings()
    plex_account_id = None
    for m in mappings:
        if str(m.get('plex_client_id') or '') == user_id:
            plex_account_id = m.get('plex_account_id')
            break
    if plex_account_id is None:
        return jsonify({'error': 'User not found'}), 404
    status = get_listen_history_sync_status(plex_account_id)
    return jsonify(status)
