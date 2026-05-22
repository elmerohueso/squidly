"""Tests for Fresh Finds recommendation feature."""

import json
import os
import sys
from unittest.mock import MagicMock, patch, call

# Patch logging setup before importing squidly modules
os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")

import pytest


class TestQueueRecommendationGeneration:
    @patch('squidly.orchestration.enqueue_job')
    @patch('squidly.orchestration.datetime')
    def test_queues_with_correct_payload(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 42

        from squidly.orchestration import queue_recommendation_generation

        job_id = queue_recommendation_generation(
            slug='fresh-finds',
            plex_account_id=123,
            plex_username='brendan',
            trigger='scheduled'
        )

        assert job_id == 42
        mock_enqueue.assert_called_once()
        args = mock_enqueue.call_args
        assert args[0][0] == 'generate_recommendations'
        payload = args[0][1]
        assert payload['slug'] == 'fresh-finds'
        assert payload['plex_account_id'] == 123
        assert payload['plex_username'] == 'brendan'
        assert payload['trigger'] == 'scheduled'
        assert 'requested_at' in payload
        assert args[1]['max_attempts'] == 3

    @patch('squidly.orchestration.enqueue_job')
    @patch('squidly.orchestration.datetime')
    def test_default_trigger_is_scheduled(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 1

        from squidly.orchestration import queue_recommendation_generation

        queue_recommendation_generation(
            slug='fresh-finds',
            plex_account_id=1,
            plex_username='test'
        )

        payload = mock_enqueue.call_args[0][1]
        assert payload['trigger'] == 'scheduled'

    @patch('squidly.orchestration.enqueue_job')
    @patch('squidly.orchestration.datetime')
    def test_manual_trigger(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 2

        from squidly.orchestration import queue_recommendation_generation

        queue_recommendation_generation(
            slug='fresh-finds',
            plex_account_id=1,
            plex_username='test',
            trigger='manual'
        )

        payload = mock_enqueue.call_args[0][1]
        assert payload['trigger'] == 'manual'


class TestStorageFunctions:
    @patch('squidly.storage.get_db_connection')
    def test_has_listen_history_true(self, mock_conn):
        from squidly.storage import has_listen_history

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'has_history': True}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = has_listen_history(123)

        assert result is True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'listen_history' in call_args[0]
        assert call_args[1] == (123,)

    @patch('squidly.storage.get_db_connection')
    def test_has_listen_history_false(self, mock_conn):
        from squidly.storage import has_listen_history

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'has_history': False}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = has_listen_history(456)

        assert result is False

    @patch('squidly.storage.get_db_connection')
    def test_has_listen_history_no_row(self, mock_conn):
        from squidly.storage import has_listen_history

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = has_listen_history(789)

        assert result is False

    @patch('squidly.storage.get_db_connection')
    def test_get_recent_listen_history_seeds(self, mock_conn):
        from squidly.storage import get_recent_listen_history_seeds

        from datetime import datetime
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'hifi_id': '100', 'title': 'Track 1', 'artist': 'Artist 1', 'album': 'Album 1', 'played_at': datetime(2024, 1, 15)},
            {'hifi_id': '200', 'title': 'Track 2', 'artist': 'Artist 2', 'album': 'Album 2', 'played_at': datetime(2024, 1, 14)},
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_recent_listen_history_seeds(123, limit=20)

        assert len(result) == 2
        assert result[0]['hifi_id'] == 100
        assert result[0]['title'] == 'Track 1'
        assert result[1]['hifi_id'] == 200
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert 'DISTINCT ON' in call_args[0]
        assert call_args[1] == (123, 20)

    @patch('squidly.storage.get_db_connection')
    def test_get_existing_isrcs(self, mock_conn):
        from squidly.storage import get_existing_isrcs

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'isrc': 'USRC17607839'},
            {'isrc': 'GBUM71505078'},
            {'isrc': 'usrc17607840'},
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_existing_isrcs()

        assert result == {'USRC17607839', 'GBUM71505078', 'USRC17607840'}

    @patch('squidly.storage.get_db_connection')
    def test_get_existing_isrcs_empty(self, mock_conn):
        from squidly.storage import get_existing_isrcs

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_existing_isrcs()

        assert result == set()

    @patch('squidly.storage.get_db_connection')
    def test_list_recommendation_playlists(self, mock_conn):
        from squidly.storage import list_recommendation_playlists

        from datetime import datetime
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'name': 'Fresh Finds (1-15)', 'slug': 'fresh-finds', 'strategy': 'fresh-finds', 'seed_count': 20, 'track_count': 25, 'generated_at': datetime(2024, 1, 15)},
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = list_recommendation_playlists(123)

        assert len(result) == 1
        assert result[0]['slug'] == 'fresh-finds'
        assert result[0]['track_count'] == 25
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1] == (123,)

    @patch('squidly.storage.get_db_connection')
    def test_list_recommendation_playlists_empty(self, mock_conn):
        from squidly.storage import list_recommendation_playlists

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = list_recommendation_playlists(456)

        assert result == []

    @patch('squidly.storage.get_db_connection')
    def test_get_recommendation_playlist(self, mock_conn):
        from squidly.storage import get_recommendation_playlist

        from datetime import datetime
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1, 'name': 'Fresh Finds (1-15)', 'slug': 'fresh-finds', 'strategy': 'fresh-finds', 'seed_count': 20, 'track_count': 2, 'generated_at': datetime(2024, 1, 15)}
        mock_cursor.fetchall.return_value = [
            {'position': 1, 'hifi_id': 100, 'title': 'Track A', 'artist': 'Artist A', 'album': 'Album A', 'duration': 210, 'cover': 'cover1', 'seed_hifi_id': 50, 'score': 3.0, 'quality': 'LOSSLESS', 'artist_id': 1, 'album_id': 1},
            {'position': 2, 'hifi_id': 200, 'title': 'Track B', 'artist': 'Artist B', 'album': 'Album B', 'duration': 180, 'cover': 'cover2', 'seed_hifi_id': 60, 'score': 2.0, 'quality': 'LOSSLESS', 'artist_id': 2, 'album_id': 2},
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_recommendation_playlist(123, 'fresh-finds')

        assert result is not None
        assert result['slug'] == 'fresh-finds'
        assert len(result['tracks']) == 2
        assert result['tracks'][0]['hifi_id'] == 100
        assert result['tracks'][0]['score'] == 3.0

    @patch('squidly.storage.get_db_connection')
    def test_get_recommendation_playlist_not_found(self, mock_conn):
        from squidly.storage import get_recommendation_playlist

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_recommendation_playlist(123, 'fresh-finds')

        assert result is None


class TestSaveRecommendationPlaylist:
    @patch('squidly.storage.get_db_connection')
    def test_save_new_playlist(self, mock_conn):
        from squidly.storage import save_recommendation_playlist

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        tracks = [
            {'hifi_id': 100, 'title': 'Track A', 'artist': 'Artist A', 'album': 'Album A', 'duration': 210, 'cover': 'c1', 'seed_hifi_id': 50, 'score': 3.0},
            {'hifi_id': 200, 'title': 'Track B', 'artist': 'Artist B', 'album': 'Album B', 'duration': 180, 'cover': 'c2', 'seed_hifi_id': 60, 'score': 2.0},
        ]

        result = save_recommendation_playlist(
            plex_account_id=123,
            slug='fresh-finds',
            name='Fresh Finds (1-15)',
            strategy='fresh-finds',
            seed_count=20,
            tracks=tracks
        )

        assert result == 1
        assert mock_cursor.execute.call_count == 5  # SELECT check, UPDATE playlist, DELETE old tracks, INSERT 2 tracks
        mock_connection.commit.assert_called_once()

    @patch('squidly.storage.get_db_connection')
    def test_save_playlist_rolls_back_on_error(self, mock_conn):
        from squidly.storage import save_recommendation_playlist

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1}
        mock_cursor.execute.side_effect = [None, None, Exception('DB error')]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        tracks = [{'hifi_id': 100, 'title': 'Track A'}]

        with pytest.raises(Exception, match='DB error'):
            save_recommendation_playlist(
                plex_account_id=123,
                slug='fresh-finds',
                name='Fresh Finds (1-15)',
                strategy='fresh-finds',
                seed_count=20,
                tracks=tracks
            )

        mock_connection.rollback.assert_called_once()
