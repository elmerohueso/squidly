"""Health check and root route handlers."""

from flask import Blueprint, render_template, jsonify

from squidly.plex import plex_healthcheck

health_bp = Blueprint('health', __name__)


def _get_plex_credentials_valid():
    """Check if Plex credentials are valid."""
    ok, _ = plex_healthcheck()
    return ok


@health_bp.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html', plex_credentials_valid=_get_plex_credentials_valid())


@health_bp.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})
