"""Tests for search API routes — mirror_type parameter verification."""

import os
from unittest.mock import MagicMock, patch


def test_track_similar_passes_mirror_type_tidal():
    """Verify that track_similar endpoint calls make_request_with_retry_rotating_mirrors
    with mirror_type='tidal'."""
    from squidly.app import app

    with (
        patch('squidly.api.search.downloads.make_request_with_retry_rotating_mirrors') as mock_make_request,
        patch('squidly.api.search.get_squid_urls') as mock_get_squid_urls,
    ):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'data': {'items': []}}
        mock_make_request.return_value = (mock_response, {'name': 'test-mirror'})
        mock_get_squid_urls.return_value = []

        with app.test_client() as client:
            response = client.get('/api/hifi/tracks/123/similar')

        assert response.status_code == 200

        # Verify mirror_type='tidal' was passed to make_request_with_retry_rotating_mirrors
        mock_make_request.assert_called_once()
        _args, kwargs = mock_make_request.call_args
        assert kwargs.get('mirror_type') == 'tidal', (
            f"Expected mirror_type='tidal' in call kwargs, got: {kwargs}"
        )


def test_track_similar_requires_numeric_id():
    """Verify that track_similar rejects non-numeric track IDs."""
    from squidly.app import app

    with app.test_client() as client:
        response = client.get('/api/hifi/tracks/abc/similar')
        assert response.status_code == 400
