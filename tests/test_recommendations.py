"""Tests for Fresh Finds recommendation feature."""

import json
import os
import sys
from unittest.mock import MagicMock, patch, call

# Patch logging setup before importing squidly modules
os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")

import pytest

from squidly.jobs.processors.recommendations import _filter_available_tracks


class TestQueueRecommendationGeneration:
    @patch('squidly.jobs.orchestration.enqueue_job')
    @patch('squidly.jobs.orchestration.datetime')
    def test_queues_with_correct_payload(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 42

        from squidly.jobs.orchestration import queue_recommendation_generation

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

    @patch('squidly.jobs.orchestration.enqueue_job')
    @patch('squidly.jobs.orchestration.datetime')
    def test_default_trigger_is_scheduled(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 1

        from squidly.jobs.orchestration import queue_recommendation_generation

        queue_recommendation_generation(
            slug='fresh-finds',
            plex_account_id=1,
            plex_username='test'
        )

        payload = mock_enqueue.call_args[0][1]
        assert payload['trigger'] == 'scheduled'

    @patch('squidly.jobs.orchestration.enqueue_job')
    @patch('squidly.jobs.orchestration.datetime')
    def test_manual_trigger(self, mock_dt, mock_enqueue):
        mock_dt.utcnow.return_value.isoformat.return_value = '2024-01-15T10:30:00'
        mock_enqueue.return_value = 2

        from squidly.jobs.orchestration import queue_recommendation_generation

        queue_recommendation_generation(
            slug='fresh-finds',
            plex_account_id=1,
            plex_username='test',
            trigger='manual'
        )

        payload = mock_enqueue.call_args[0][1]
        assert payload['trigger'] == 'manual'


class TestStorageFunctions:
    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_has_listen_history_true(self, mock_conn):
        from squidly.infrastructure.storage import has_listen_history

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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_has_listen_history_false(self, mock_conn):
        from squidly.infrastructure.storage import has_listen_history

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'has_history': False}
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = has_listen_history(456)

        assert result is False

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_has_listen_history_no_row(self, mock_conn):
        from squidly.infrastructure.storage import has_listen_history

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = has_listen_history(789)

        assert result is False

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_recent_listen_history_seeds(self, mock_conn):
        from squidly.infrastructure.storage import get_recent_listen_history_seeds

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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_existing_isrcs(self, mock_conn):
        from squidly.infrastructure.storage import get_existing_isrcs

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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_existing_isrcs_empty(self, mock_conn):
        from squidly.infrastructure.storage import get_existing_isrcs

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_existing_isrcs()

        assert result == set()

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_list_recommendation_playlists(self, mock_conn):
        from squidly.infrastructure.storage import list_recommendation_playlists

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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_list_recommendation_playlists_empty(self, mock_conn):
        from squidly.infrastructure.storage import list_recommendation_playlists

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = list_recommendation_playlists(456)

        assert result == []

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_recommendation_playlist(self, mock_conn):
        from squidly.infrastructure.storage import get_recommendation_playlist

        from datetime import datetime
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'id': 1, 'name': 'Fresh Finds (1-15)', 'slug': 'fresh-finds', 'strategy': 'fresh-finds', 'seed_count': 20, 'track_count': 2, 'generated_at': datetime(2024, 1, 15)}
        mock_cursor.fetchall.return_value = [
            {'position': 1, 'hifi_id': 100, 'title': 'Track A', 'artist': 'Artist A', 'album': 'Album A', 'duration': 210, 'cover': 'cover1', 'seed_hifi_id': 50, 'score': 3.0, 'quality': 'LOSSLESS', 'artist_id': 1, 'album_id': 1, 'isrc': 'USRC12300001'},
            {'position': 2, 'hifi_id': 200, 'title': 'Track B', 'artist': 'Artist B', 'album': 'Album B', 'duration': 180, 'cover': 'cover2', 'seed_hifi_id': 60, 'score': 2.0, 'quality': 'LOSSLESS', 'artist_id': 2, 'album_id': 2, 'isrc': 'USRC12300002'},
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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_recommendation_playlist_not_found(self, mock_conn):
        from squidly.infrastructure.storage import get_recommendation_playlist

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_recommendation_playlist(123, 'fresh-finds')

        assert result is None


class TestGetRandomListenHistorySeeds:
    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_get_random_listen_history_seeds(self, mock_conn):
        from squidly.infrastructure.storage import get_random_listen_history_seeds
        from datetime import datetime
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'hifi_id': '100', 'title': 'Track 1', 'artist': 'Artist 1', 'album': 'Album 1', 'played_at': datetime(2024, 1, 15)},
            {'hifi_id': '200', 'title': 'Track 2', 'artist': 'Artist 2', 'album': 'Album 2', 'played_at': datetime(2024, 1, 14)},
            {'hifi_id': '300', 'title': 'Track 3', 'artist': 'Artist 3', 'album': 'Album 3', 'played_at': datetime(2024, 1, 13)},
        ]
        mock_connection = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_conn.return_value = mock_connection

        result = get_random_listen_history_seeds(123, limit=2, days=30)

        assert len(result) == 2
        assert result[0]['hifi_id'] == 100 or result[0]['hifi_id'] == 200 or result[0]['hifi_id'] == 300
        assert isinstance(result[0]['hifi_id'], int)
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert call_args[1] == (123, 30)


class TestSaveRecommendationPlaylist:
    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_save_new_playlist(self, mock_conn):
        from squidly.infrastructure.storage import save_recommendation_playlist

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

    @patch('squidly.infrastructure.storage.get_db_connection')
    def test_save_playlist_rolls_back_on_error(self, mock_conn):
        from squidly.infrastructure.storage import save_recommendation_playlist

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


# ---------------------------------------------------------------------------
# Tests for _filter_available_tracks (ISRC pre-check)
# ---------------------------------------------------------------------------

TRACK_A = {'isrc': 'USRC1230001', 'title': 'Track A', 'artist': 'Artist A'}
TRACK_B = {'isrc': 'USRC1230002', 'title': 'Track B', 'artist': 'Artist B'}
TRACK_C = {'isrc': 'USRC1230003', 'title': 'Track C', 'artist': 'Artist C'}
TRACK_NO_ISRC = {'isrc': None, 'title': 'No ISRC', 'artist': 'Artist X'}
TRACK_EMPTY_ISRC = {'isrc': '', 'title': 'Empty ISRC', 'artist': 'Artist Y'}

TIDAL_MIRROR = {'name': 'tidal-premium', 'url': 'https://tidal.example.com', 'mirror_type': 'tidal'}
QOBUZ_MIRROR = {'name': 'qobuz-mirror', 'url': 'https://qobuz.example.com', 'mirror_type': 'qobuz'}


class TestFilterAvailableTracks:
    """Unit tests for _filter_available_tracks."""

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_skip_check_tidal_only_mirrors_online(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='tidal', Tidal premium mirrors online -> all tracks pass, no API calls."""
        mock_downloads.load_enabled_mirror_urls.return_value = [TIDAL_MIRROR]

        tracks = [TRACK_A, TRACK_B]
        settings = {'download_source': 'tidal'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 2
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_not_called()
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_skip_check_no_isrc_pass_through(self, mock_deezer, mock_qobuz, mock_downloads):
        """Tracks with no ISRC (None or empty) pass through regardless of source."""
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]  # qobuz mirror but not tidal
        mock_qobuz.search_qobuz_track.return_value = (None, 'not_found')
        mock_deezer.search_deezer_track.return_value = None

        tracks = [TRACK_NO_ISRC, TRACK_EMPTY_ISRC]
        # No tidal, no qobuz (only deezer which will fail), so deezer will be called
        settings = {'download_source': 'deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 2
        assert removed == 0
        # Deezer should NOT have been called since both tracks have no ISRC
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_tidal_available_heuristic(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='tidal,qobuz', Tidal mirrors online -> track passes without Qobuz API call."""
        mock_downloads.load_enabled_mirror_urls.return_value = [TIDAL_MIRROR]

        tracks = [TRACK_A]
        settings = {'download_source': 'tidal,qobuz'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 1
        assert removed == 0
        # Should have been satisfied by Tidal heuristic, no Qobuz call needed
        mock_qobuz.search_qobuz_track.assert_not_called()
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_qobuz_confirms_availability(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='qobuz,deezer', Tidal mirrors offline. Qobuz returns track -> track passes."""
        mock_downloads.load_enabled_mirror_urls.side_effect = lambda mirror_type, for_download=True: (
            [] if mirror_type == 'tidal' else [QOBUZ_MIRROR]
        )
        # Make a better side_effect using kwargs
        mock_downloads.load_enabled_mirror_urls.side_effect = None
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]

        mock_qobuz.search_qobuz_track.return_value = ({'id': 999, 'isrc': 'USRC1230001'}, None)

        tracks = [TRACK_A]
        settings = {'download_source': 'qobuz,deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 1
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_called_once()
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_qobuz_not_found_deezer_confirms(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='qobuz,deezer'. Qobuz not_found -> Deezer finds it -> track passes."""
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]

        mock_qobuz.search_qobuz_track.return_value = (None, 'not_found')
        mock_deezer.search_deezer_track.return_value = {'id': 456, 'isrc': 'USRC1230001'}

        tracks = [TRACK_A]
        settings = {'download_source': 'qobuz,deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 1
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_called_once()
        mock_deezer.search_deezer_track.assert_called_once()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_all_sources_not_found(self, mock_deezer, mock_qobuz, mock_downloads):
        """All sources return not_found -> track is removed, removed_count=1."""
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]

        mock_qobuz.search_qobuz_track.return_value = (None, 'not_found')
        mock_deezer.search_deezer_track.return_value = None

        tracks = [TRACK_A]
        settings = {'download_source': 'qobuz,deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 0
        assert removed == 1

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_qobuz_api_error_continues(self, mock_deezer, mock_qobuz, mock_downloads):
        """Qobuz raises exception -> non-fatal, continues to Deezer which finds it."""
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]

        mock_qobuz.search_qobuz_track.side_effect = ConnectionError('Qobuz down')
        mock_deezer.search_deezer_track.return_value = {'id': 789, 'isrc': 'USRC1230001'}

        tracks = [TRACK_A]
        settings = {'download_source': 'qobuz,deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 1
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_called_once()
        mock_deezer.search_deezer_track.assert_called_once()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_no_usable_sources_all_pass(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='tidal', no Tidal mirrors online, no other sources -> all tracks pass through."""
        mock_downloads.load_enabled_mirror_urls.return_value = []  # No premium Tidal mirrors

        tracks = [TRACK_A, TRACK_B, TRACK_C]
        settings = {'download_source': 'tidal'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 3
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_not_called()
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_mixed_availability(self, mock_deezer, mock_qobuz, mock_downloads):
        """3 tracks: one available on Qobuz, one on Deezer, one not found anywhere."""
        mock_downloads.load_enabled_mirror_urls.return_value = [QOBUZ_MIRROR]

        def qobuz_side_effect(url, isrc, timeout=15):
            if isrc == 'USRC1230001':
                return ({'id': 1}, None)
            return (None, 'not_found')

        def deezer_side_effect(isrc, timeout=15):
            if isrc == 'USRC1230002':
                return {'id': 2}
            return None

        mock_qobuz.search_qobuz_track.side_effect = qobuz_side_effect
        mock_deezer.search_deezer_track.side_effect = deezer_side_effect

        track_a = {'isrc': 'USRC1230001', 'title': 'On Qobuz', 'artist': 'A'}
        track_b = {'isrc': 'USRC1230002', 'title': 'On Deezer', 'artist': 'B'}
        track_c = {'isrc': 'USRC1230003', 'title': 'Nowhere', 'artist': 'C'}

        tracks = [track_a, track_b, track_c]
        settings = {'download_source': 'qobuz,deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 2
        assert removed == 1
        assert available[0]['isrc'] == 'USRC1230001'
        assert available[1]['isrc'] == 'USRC1230002'

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_multiple_tracks_all_available(self, mock_deezer, mock_qobuz, mock_downloads):
        """5 tracks, all available on Tidal -> all pass."""
        mock_downloads.load_enabled_mirror_urls.return_value = [TIDAL_MIRROR]

        tracks = [
            {'isrc': f'USRC123{i:04d}', 'title': f'Track {i}', 'artist': f'Artist {i}'}
            for i in range(1, 6)
        ]
        settings = {'download_source': 'tidal'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 5
        assert removed == 0
        mock_qobuz.search_qobuz_track.assert_not_called()
        mock_deezer.search_deezer_track.assert_not_called()

    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.qobuz')
    @patch('squidly.jobs.processors.recommendations.deezer')
    def test_deezer_no_arl_needed(self, mock_deezer, mock_qobuz, mock_downloads):
        """download_source='deezer'. No ARL in settings. Deezer public API finds track -> passes."""
        mock_downloads.load_enabled_mirror_urls.return_value = []  # No tidal mirrors
        # load_enabled_mirror_urls with mirror_type='qobuz' not called since qobuz not in sources
        # But the code only calls load_enabled_mirror_urls for sources in the sources list
        # deezer is always callable, no mirror check needed

        mock_deezer.search_deezer_track.return_value = {'id': 101, 'isrc': 'USRC1230001'}

        tracks = [TRACK_A]
        settings = {'download_source': 'deezer'}
        available, removed = _filter_available_tracks(tracks, settings)

        assert len(available) == 1
        assert removed == 0
        mock_deezer.search_deezer_track.assert_called_once_with('USRC1230001', timeout=15)
        mock_qobuz.search_qobuz_track.assert_not_called()


class TestProcessRecommendationJobIsrcSection:
    """Test the ISRC pre-check call site in process_recommendation_job.

    These tests mock _filter_available_tracks to verify the integration
    code path doesn't break when tracks pass/fail the ISRC check.
    """

    @patch('squidly.jobs.processors.recommendations._filter_available_tracks')
    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.jobs.update_job_progress')
    @patch('squidly.jobs.processors.recommendations.queue_plex_listen_history_sync')
    @patch('squidly.jobs.orchestration.wait_for_job_type')
    @patch('squidly.jobs.processors.recommendations.get_random_listen_history_seeds')
    @patch('squidly.jobs.processors.recommendations.get_existing_fresh_finds_isrcs')
    @patch('squidly.jobs.processors.recommendations.get_download_settings')
    @patch('squidly.jobs.processors.recommendations._get_hifi_audio_quality_rank')
    @patch('squidly.infrastructure.storage.get_recently_played_isrcs')
    @patch('squidly.infrastructure.storage.get_existing_isrcs')
    @patch('squidly.infrastructure.storage.get_existing_artist_titles')
    @patch('squidly.infrastructure.storage.get_fresh_finds_new_track_pct')
    @patch('squidly.jobs.processors.recommendations.get_fresh_finds_track_count')
    @patch('squidly.jobs.processors.recommendations.get_fresh_finds_history_days')
    @patch('squidly.services.track_resolver.resolve_track')
    @patch('squidly.services.hifi._fetch_hifi_track_info_payload')
    @patch('squidly.services.hifi.extract_hifi_track_info')
    @patch('squidly.jobs.processors.recommendations.save_recommendation_playlist')
    @patch('squidly.infrastructure.storage.cleanup_old_fresh_finds')
    @patch('squidly.jobs.processors.recommendations._raise_if_job_cancelled')
    def test_isrc_check_does_not_break_when_all_pass(
        self,
        mock_raise_cancelled,
        mock_cleanup,
        mock_save_playlist,
        mock_extract_info,
        mock_fetch_payload,
        mock_resolve_track,
        mock_history_days,
        mock_track_count,
        mock_new_track_pct,
        mock_existing_artist_titles,
        mock_existing_isrcs,
        mock_recently_played,
        mock_quality_rank,
        mock_dl_settings,
        mock_existing_ff_isrcs,
        mock_get_seeds,
        mock_wait,
        mock_queue_sync,
        mock_update_progress,
        mock_downloads,
        mock_filter,
    ):
        """When _filter_available_tracks passes all tracks through (no removals),
        the job should complete normally with no refill logic triggered."""
        from squidly.jobs.processors.recommendations import process_recommendation_job

        # Mock _filter_available_tracks to return all tracks unchanged
        mock_filter.side_effect = lambda tracks, settings: (list(tracks), 0)

        # Mock listen history sync
        mock_wait.return_value = None
        mock_queue_sync.return_value = None  # No sync needed

        # Mock seeds
        mock_get_seeds.return_value = [
            {'hifi_id': 100, 'title': 'Seed 1', 'artist': 'Artist 1', 'album': 'Album 1'},
        ]

        # Mock settings
        mock_dl_settings.return_value = {
            'download_source': 'tidal',
            'quality': 'LOSSLESS',
            'file_naming_album': '{artist}/{album}/{track} - {title}.{ext}',
        }

        # Mock quality rank: HI_RES > LOSSLESS > HIGH
        mock_quality_rank.side_effect = lambda q: {
            'HI_RES_LOSSLESS': 3, 'LOSSLESS': 2, 'HIGH': 1, '': 0,
        }.get(q, 0)

        # Mock recommendations API response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'data': {
                'items': [{
                    'track': {
                        'id': 200,
                        'title': 'Rec Track',
                        'artists': [{'id': 10, 'name': 'Rec Artist'}],
                        'album': {'id': 20, 'title': 'Rec Album'},
                        'duration': 240,
                        'maxAudioQuality': 'LOSSLESS',
                        'isrc': 'USRC1230001',
                    }
                }]
            }
        }
        mock_downloads.make_request_with_retry_rotating_mirrors.return_value = (mock_response, 'test-mirror')

        # Mock existing data
        mock_existing_ff_isrcs.return_value = set()
        mock_recently_played.return_value = set()
        mock_existing_isrcs.return_value = set()
        mock_existing_artist_titles.return_value = set()
        mock_new_track_pct.return_value = 70
        mock_track_count.return_value = 20
        mock_history_days.return_value = 90

        # Mock track resolution (no-op)
        mock_resolve_track.return_value = {'hifi_id': '200', 'reason': 'exact', 'source': 'hifi_id'}
        mock_fetch_payload.return_value = None

        # Mock playlist save
        mock_save_playlist.return_value = 42

        # Mock cleanup
        mock_cleanup.return_value = {'deleted_count': 0, 'plex_deleted': 0}

        # Mock get_squid_urls via the mocked downloads module
        mock_downloads.get_squid_urls.return_value = []

        # Execute
        result = process_recommendation_job(1, {
            'plex_account_id': 123,
            'plex_username': 'testuser',
            'slug': 'fresh-finds',
            'trigger': 'manual',
        })

        # Verify the result has expected structure
        assert result is not None
        assert 'stages' in result
        assert 'progress' in result
        assert result['progress']['tracks_removed_by_isrc'] == 0
        assert result['progress']['tracks_saved'] > 0
        assert result['trigger'] == 'manual'
        assert result['plex_username'] == 'testuser'

    @patch('squidly.jobs.processors.recommendations._filter_available_tracks')
    @patch('squidly.jobs.processors.recommendations.downloads')
    @patch('squidly.jobs.processors.recommendations.jobs.update_job_progress')
    @patch('squidly.jobs.processors.recommendations.queue_plex_listen_history_sync')
    @patch('squidly.jobs.orchestration.wait_for_job_type')
    @patch('squidly.jobs.processors.recommendations.get_random_listen_history_seeds')
    @patch('squidly.jobs.processors.recommendations.get_existing_fresh_finds_isrcs')
    @patch('squidly.jobs.processors.recommendations.get_download_settings')
    @patch('squidly.jobs.processors.recommendations._get_hifi_audio_quality_rank')
    @patch('squidly.infrastructure.storage.get_recently_played_isrcs')
    @patch('squidly.infrastructure.storage.get_existing_isrcs')
    @patch('squidly.infrastructure.storage.get_existing_artist_titles')
    @patch('squidly.infrastructure.storage.get_fresh_finds_new_track_pct')
    @patch('squidly.jobs.processors.recommendations.get_fresh_finds_track_count')
    @patch('squidly.jobs.processors.recommendations.get_fresh_finds_history_days')
    @patch('squidly.services.track_resolver.resolve_track')
    @patch('squidly.services.hifi._fetch_hifi_track_info_payload')
    @patch('squidly.services.hifi.extract_hifi_track_info')
    @patch('squidly.jobs.processors.recommendations.save_recommendation_playlist')
    @patch('squidly.infrastructure.storage.cleanup_old_fresh_finds')
    @patch('squidly.jobs.processors.recommendations._raise_if_job_cancelled')
    def test_isrc_check_removals_logged_and_refilled(
        self,
        mock_raise_cancelled,
        mock_cleanup,
        mock_save_playlist,
        mock_extract_info,
        mock_fetch_payload,
        mock_resolve_track,
        mock_history_days,
        mock_track_count,
        mock_new_track_pct,
        mock_existing_artist_titles,
        mock_existing_isrcs,
        mock_recently_played,
        mock_quality_rank,
        mock_dl_settings,
        mock_existing_ff_isrcs,
        mock_get_seeds,
        mock_wait,
        mock_queue_sync,
        mock_update_progress,
        mock_downloads,
        mock_filter,
    ):
        """When _filter_available_tracks removes some tracks, the refill
        logic runs and the job should still complete with the right counts."""
        from squidly.jobs.processors.recommendations import process_recommendation_job

        call_count = [0]

        def filter_side_effect(tracks, settings):
            call_count[0] += 1
            # First two calls (new pool + library pool) remove 1 track each
            if call_count[0] <= 2:
                return (tracks[:-1], 1)  # Remove the last track
            # Subsequent calls (refill) pass everything
            return (list(tracks), 0)

        mock_filter.side_effect = filter_side_effect

        # Mock listen history sync
        mock_wait.return_value = None
        mock_queue_sync.return_value = None

        # Mock seeds
        mock_get_seeds.return_value = [
            {'hifi_id': 100, 'title': 'Seed 1', 'artist': 'Artist 1', 'album': 'Album 1'},
        ]

        # Mock settings
        mock_dl_settings.return_value = {
            'download_source': 'tidal',
            'quality': 'LOSSLESS',
            'file_naming_album': '{artist}/{album}/{track} - {title}.{ext}',
        }

        # Mock quality rank
        mock_quality_rank.side_effect = lambda q: {
            'HI_RES_LOSSLESS': 3, 'LOSSLESS': 2, 'HIGH': 1, '': 0,
        }.get(q, 0)

        # Mock recommendations - return 3 tracks so there's a pool to refill from
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'data': {
                'items': [
                    {
                        'track': {
                            'id': 200, 'title': 'Rec 1',
                            'artists': [{'id': 10, 'name': 'Artist 1'}],
                            'album': {'id': 20, 'title': 'Album 1'},
                            'duration': 240,
                            'maxAudioQuality': 'LOSSLESS',
                            'isrc': 'USRC1230001',
                        }
                    },
                    {
                        'track': {
                            'id': 201, 'title': 'Rec 2',
                            'artists': [{'id': 11, 'name': 'Artist 2'}],
                            'album': {'id': 21, 'title': 'Album 2'},
                            'duration': 241,
                            'maxAudioQuality': 'LOSSLESS',
                            'isrc': 'USRC1230002',
                        }
                    },
                    {
                        'track': {
                            'id': 202, 'title': 'Rec 3',
                            'artists': [{'id': 12, 'name': 'Artist 3'}],
                            'album': {'id': 22, 'title': 'Album 3'},
                            'duration': 242,
                            'maxAudioQuality': 'LOSSLESS',
                            'isrc': 'USRC1230003',
                        }
                    },
                ]
            }
        }
        mock_downloads.make_request_with_retry_rotating_mirrors.return_value = (mock_response, 'test-mirror')

        # Mock existing data
        mock_existing_ff_isrcs.return_value = set()
        mock_recently_played.return_value = set()
        mock_existing_isrcs.return_value = set()
        mock_existing_artist_titles.return_value = set()
        mock_new_track_pct.return_value = 70
        mock_track_count.return_value = 20
        mock_history_days.return_value = 90

        # Mock track resolution
        mock_resolve_track.return_value = {'hifi_id': '200', 'reason': 'exact', 'source': 'hifi_id'}
        mock_fetch_payload.return_value = None

        # Mock playlist save
        mock_save_playlist.return_value = 42

        # Mock cleanup
        mock_cleanup.return_value = {'deleted_count': 0, 'plex_deleted': 0}

        # Mock get_squid_urls via the mocked downloads module
        mock_downloads.get_squid_urls.return_value = []

        # Execute
        result = process_recommendation_job(1, {
            'plex_account_id': 123,
            'plex_username': 'testuser',
            'slug': 'fresh-finds',
            'trigger': 'scheduled',
        })

        # Verify the result
        assert result is not None
        assert 'stages' in result
        assert 'progress' in result
        # The removal and refill should have happened
        assert result['progress']['tracks_removed_by_isrc'] > 0
        assert result['progress']['tracks_saved'] > 0
