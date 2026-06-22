"""Tests for squidly/jobs/processors/download.py — focused on matched path extraction.

When an existing track match is found via _lookup_track_metadata, the
file path from the DB (the `path` column) is joined with DOWNLOADS_ROOT
to produce the absolute path used for playlist queuing. This test suite
validates that extraction logic.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest

from squidly.infrastructure.config import DOWNLOADS_ROOT


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_mock_hifi_track_object(track_title="Test Track", album_title="Test Album",
                                  artist_name="Test Artist"):
    """Build a normalized hifi track object matching the shape
    expected by process_download_job."""
    return {
        'track': {
            'title': track_title,
            'artists': [{'id': '123', 'name': artist_name}],
            'album': {
                'title': album_title,
                'id': '456',
                'artists': [{'id': '123', 'name': artist_name}],
                'releaseDate': '2024-01-15',
            },
            'trackNumber': 1,
            'duration': 180,
            'explicit': False,
            'copyright': '2024 Test Label',
        }
    }


# ── Test: matched_path extraction ──────────────────────────────────────────

class TestMatchedPathExistingMatchExtraction:
    """Tests for the matched_path extraction in process_download_job."""
    """Verify that when a matching row exists, the path is correctly
    extracted from the `path` column and joined with DOWNLOADS_ROOT."""

    def _run_with_mock_metadata(self, metadata_rows):
        """Helper: invoke process_download_job with metadata_rows
        controlled via _lookup_track_metadata mock.

        NOTE: Does NOT mock queue_pending_playlist_addition or
        upsert_download_match_hint — individual tests that need to
        assert on those functions should patch them in their own
        context managers wrapping this call."""
        with patch.multiple(
            'squidly.jobs.processors.download',
            # Disable external calls we don't need
            get_hifi_track_object=MagicMock(
                return_value=_make_mock_hifi_track_object(),
            ),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=metadata_rows),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            # Make os.path.exists return True for the downloads folder
            # and os.makedirs a no-op to avoid PermissionError on /downloads
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    from squidly.jobs.processors.download import process_download_job
                    process_download_job(
                        'test-job-123',
                        {
                            'trackId': '987654321',
                            'downloadQuality': 'LOSSLESS',
                            'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                            'ignore_matches': False,
                            'plex_playlist': 'Test Playlist',
                        },
                    )

    def test_matched_path_extraction_from_db_row(self):
        """When matched_row has a `path` key, the path is extracted,
        stripped, and joined with DOWNLOADS_ROOT."""
        metadata_rows = [
            {
                'path': 'Test Artist/Test Album/01 - Test Track.flac',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.os.path.join',
            wraps=os.path.join,
        ) as mock_join:
            with patch(
                'squidly.jobs.processors.download.queue_pending_playlist_addition',
            ) as mock_queue:
                self._run_with_mock_metadata(metadata_rows)

                # Verify os.path.join was called with DOWNLOADS_ROOT and the relative path
                expected_rel = 'Test Artist/Test Album/01 - Test Track.flac'
                mock_join.assert_any_call(DOWNLOADS_ROOT, expected_rel)

                # Verify the queue was called with the joined absolute path
                expected_abs = os.path.join(DOWNLOADS_ROOT, expected_rel)
                call_path = mock_queue.call_args[0][0]
                assert call_path == expected_abs

    def test_path_with_extra_whitespace(self):
        """Whitespace around path values is stripped before joining."""
        metadata_rows = [
            {
                'path': '  Artist/Album/Track.flac  ',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            expected_abs = os.path.join(DOWNLOADS_ROOT, 'Artist/Album/Track.flac')
            call_path = mock_queue.call_args[0][0]
            assert call_path == expected_abs

    def test_empty_path_falls_back_to_computed_path(self):
        """When path is empty string, matched_path should be '' and
        the full_path should fall back to DOWNLOADS_ROOT + computed naming."""
        metadata_rows = [
            {
                'path': '',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            # The fallback path is computed from file_naming:
            # {artist}/{album}/{track} - {title}.{ext}
            # → Test Artist/Test Album/01 - Test Track.flac
            call_path = mock_queue.call_args[0][0]
            expected = os.path.normpath(
                os.path.join(DOWNLOADS_ROOT, 'Test Artist/Test Album/01 - Test Track.flac')
            )
            assert call_path == expected

    def test_none_path_falls_back_to_computed_path(self):
        """When path is None, matched_path should be '' and
        the full_path should fall back to the computed naming."""
        metadata_rows = [
            {
                'path': None,
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            call_path = mock_queue.call_args[0][0]
            expected = os.path.normpath(
                os.path.join(DOWNLOADS_ROOT, 'Test Artist/Test Album/01 - Test Track.flac')
            )
            assert call_path == expected

    def test_missing_path_key_falls_back_to_computed_path(self):
        """When the matched row has no 'path' key at all, the behaviour
        should be the same as a None/empty path (fallback to computed)."""
        metadata_rows = [
            {
                # No 'path' key
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            call_path = mock_queue.call_args[0][0]
            expected = os.path.normpath(
                os.path.join(DOWNLOADS_ROOT, 'Test Artist/Test Album/01 - Test Track.flac')
            )
            assert call_path == expected

    def test_original_file_path_key_not_used(self):
        """Verify that if the row has the old 'file_path' key but no 'path'
        key, it falls back to the computed path (does NOT use 'file_path')."""
        metadata_rows = [
            {
                'file_path': 'Old/Path/That/Should/Not/Be/Used.flac',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            call_path = mock_queue.call_args[0][0]
            expected = os.path.normpath(
                os.path.join(DOWNLOADS_ROOT, 'Test Artist/Test Album/01 - Test Track.flac')
            )
            # Should NOT contain the old file_path value
            assert 'Old/Path/That/Should/Not/Be/Used.flac' not in call_path
            assert call_path == expected

    def test_non_string_path_coerced_to_string(self):
        """When path is a non-string (e.g. int), str() coercion prevents crash."""
        metadata_rows = [
            {
                'path': 12345,
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            call_path = mock_queue.call_args[0][0]
            # str(12345) = '12345' → after strip it's non-empty
            expected = os.path.normpath(os.path.join(DOWNLOADS_ROOT, '12345'))
            assert call_path == expected

    def test_relative_path_produces_absolute(self):
        """The joined path should start with DOWNLOADS_ROOT (/downloads),
        confirming the relative path is correctly absolutified."""
        metadata_rows = [
            {
                'path': 'Artist/Album/Track.flac',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'Test Album',
            }
        ]
        with patch(
            'squidly.jobs.processors.download.queue_pending_playlist_addition',
        ) as mock_queue:
            self._run_with_mock_metadata(metadata_rows)
            call_path = mock_queue.call_args[0][0]
            assert call_path.startswith(DOWNLOADS_ROOT)
            assert os.path.isabs(call_path)
            assert call_path.endswith('Artist/Album/Track.flac')


# =============================================================================
# Deezer Mirror source branch in the download pipeline
# =============================================================================


class TestDeezerMirrorSource:
    """Tests for the deezer_mirror source branch in process_download_job.

    Validates:
    - Early-continue when track has no ISRC
    - Full download path when ISRC is available and mirror succeeds
    """

    @staticmethod
    def _make_track_with_isrc(isrc="USRC12345678"):
        """Build a hifi track object that includes an ISRC."""
        track = _make_mock_hifi_track_object()
        track['track']['isrc'] = isrc
        return track

    def test_skipped_when_no_isrc(self):
        """deezer_mirror is skipped (early-continue) when track has no ISRC,
        resulting in a PermanentDownloadError since no source succeeded."""
        from squidly.jobs.processors.download import process_download_job
        from squidly.infrastructure.downloads import PermanentDownloadError

        with patch.multiple(
            'squidly.jobs.processors.download',
            # No ISRC in the track data
            get_hifi_track_object=MagicMock(
                return_value=_make_mock_hifi_track_object(),
            ),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'deezer_mirror',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with pytest.raises(PermanentDownloadError) as excinfo:
                        process_download_job(
                            'test-job-no-isrc',
                            {
                                'trackId': '987654321',
                                'downloadQuality': 'LOSSLESS',
                                'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                'ignore_matches': False,
                                'plex_playlist': 'Test Playlist',
                            },
                        )
                    error_msg = str(excinfo.value).lower()
                    assert 'isrc' in error_msg or 'deezer' in error_msg

    def test_download_attempted_when_isrc_available(self):
        """deezer_mirror downloads successfully when ISRC is present."""
        from squidly.jobs.processors.download import process_download_job

        track_with_isrc = self._make_track_with_isrc('USRC12345678')
        mirror_url = 'https://deezer-mirror.example.com'
        temp_path = '/app/temp/temp_USRC12345678_deezer_mirror.flac'

        mock_handler = MagicMock(return_value={
            'file_path': temp_path,
            'source': mirror_url,
        })

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'deezer_mirror',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {'deezer_mirror': mock_handler},
                    ):
                        with patch(
                            'squidly.infrastructure.downloads.detect_audio_format',
                            return_value='flac',
                        ):
                            with patch(
                                'squidly.infrastructure.downloads.validate_audio_duration',
                            ):
                                with patch(
                                    'squidly.infrastructure.downloads.add_id3_tags_to_file',
                                ):
                                    with patch(
                                        'squidly.jobs.processors.download.os.path.getsize',
                                        return_value=2048,
                                    ):
                                        with patch(
                                            'squidly.jobs.processors.download.shutil.move',
                                        ):
                                            with patch(
                                                'squidly.jobs.processors.download.queue_pending_playlist_addition',
                                            ):
                                                with patch(
                                                    'builtins.open',
                                                    mock_open(
                                                        read_data=b'fLaC\x00\x00\x00\x00'
                                                    ),
                                                ):
                                                    result = process_download_job(
                                                        'test-job-isrc',
                                                        {
                                                            'trackId': '987654321',
                                                            'downloadQuality': 'LOSSLESS',
                                                            'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                                            'ignore_matches': False,
                                                            'plex_playlist': 'Test Playlist',
                                                        },
                                                    )

        # Verify the handler was called with ISRC and quality
        mock_handler.assert_called_once_with('USRC12345678', 'LOSSLESS')

        # Verify overall success
        assert result['stages']['downloaded'] == 'done'
        assert result['stages']['tagged'] == 'done'
        assert result['stages']['written'] == 'done'
        assert result['file_path'] is not None

    def test_skipped_when_no_mirrors_available(self):
        """deezer_mirror raises PermanentDownloadError when no mirrors are
        enabled/online/premium for the deezer type."""
        from squidly.jobs.processors.download import process_download_job
        from squidly.infrastructure.downloads import PermanentDownloadError

        track_with_isrc = self._make_track_with_isrc('USRC12345678')

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'deezer_mirror',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    # Return empty mirror list (no enabled mirrors)
                    with patch(
                        'squidly.infrastructure.downloads.load_enabled_mirror_urls',
                        return_value=[],
                    ):
                        with pytest.raises(PermanentDownloadError) as excinfo:
                            process_download_job(
                                'test-job-no-mirrors',
                                {
                                    'trackId': '987654321',
                                    'downloadQuality': 'LOSSLESS',
                                    'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                    'ignore_matches': False,
                                    'plex_playlist': 'Test Playlist',
                                },
                            )
                        error_msg = str(excinfo.value).lower()
                        assert 'deezer' in error_msg or 'mirror' in error_msg

    def test_fallback_from_deezer_mirror_to_tidal(self):
        """When deezer_mirror fails (no mirrors), the processor falls back to
        tidal if it is in the priority list."""
        from squidly.jobs.processors.download import process_download_job

        track_with_isrc = self._make_track_with_isrc('USRC12345678')

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'deezer_mirror,tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    # Return empty list for deezer mirrors, then tidal fails too
                    with patch(
                        'squidly.infrastructure.downloads.load_enabled_mirror_urls',
                        return_value=[],
                    ):
                        with patch(
                            'squidly.infrastructure.downloads.download_track_manifest',
                            side_effect=ValueError(
                                "No configured mirror"
                            ),
                        ):
                            from squidly.infrastructure.downloads import (
                                PermanentDownloadError,
                            )
                            with pytest.raises(PermanentDownloadError):
                                process_download_job(
                                    'test-job-fallback',
                                    {
                                        'trackId': '987654321',
                                        'downloadQuality': 'LOSSLESS',
                                        'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                        'ignore_matches': False,
                                        'plex_playlist': 'Test Playlist',
                                    },
                                )

    def test_format_mismatch_triggers_fallback(self):
        """If deezer_mirror returns MP3 instead of FLAC, the dispatch should
        raise ValueError to trigger fallback to the next source (NOT silently
        accept the MP3).

        This is the primary bug fix test: the old code accepted any HTTP 200
        regardless of actual audio format.
        """
        import os
        import tempfile
        from squidly.jobs.processors.download import process_download_job

        track_with_isrc = self._make_track_with_isrc('USRC12345678')

        # Create temp files with real magic bytes
        mp3_fd, mp3_path = tempfile.mkstemp(suffix='.flac')  # deezer_mirror writes .flac but content is MP3
        flac_fd, flac_path = tempfile.mkstemp(suffix='.flac')
        try:
            # Write MP3 ID3 header to the "deezer_mirror" file
            os.write(mp3_fd, b'ID3' + b'\x00' * 100)
            # Write real FLAC header to the "tidal" file
            os.write(flac_fd, b'fLaC' + b'\x00' * 100)
        finally:
            os.close(mp3_fd)
            os.close(flac_fd)

        # deezer_mirror handler returns the MP3 file
        mock_deezer_handler = MagicMock(return_value={
            'file_path': mp3_path,
            'source': 'https://deezer-mirror.example.com',
        })
        # tidal handler returns the FLAC file
        mock_tidal_handler = MagicMock(return_value={
            'file_path': flac_path,
            'source': 'https://tidal-mirror.example.com',
        })

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'deezer_mirror,tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {
                            'deezer_mirror': mock_deezer_handler,
                            'tidal': mock_tidal_handler,
                        },
                    ):
                        with patch(
                            'squidly.infrastructure.downloads.validate_audio_duration',
                        ):
                            with patch(
                                'squidly.infrastructure.downloads.add_id3_tags_to_file',
                            ):
                                with patch(
                                    'squidly.jobs.processors.download.shutil.move',
                                ):
                                    with patch(
                                        'squidly.jobs.processors.download.queue_pending_playlist_addition',
                                    ):
                                        result = process_download_job(
                                            'test-job-format-mismatch',
                                            {
                                                'trackId': '987654321',
                                                'downloadQuality': 'LOSSLESS',
                                                'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                                'ignore_matches': False,
                                                'plex_playlist': 'Test Playlist',
                                            },
                                        )

        # deezer_mirror was called first
        mock_deezer_handler.assert_called_once()
        # tidal was called as fallback after deezer_mirror format mismatch
        mock_tidal_handler.assert_called_once()
        # Overall success via tidal
        assert result['stages']['downloaded'] == 'done'
        assert result['mirror_type'] == 'tidal'


# =============================================================================
# Registry pattern tests
# =============================================================================


class TestDownloadSourceRegistry:
    """Tests for the _DOWNLOAD_SOURCE_HANDLERS registry and dispatch."""

    @staticmethod
    def _make_track_with_isrc(isrc="USRC12345678"):
        track = _make_mock_hifi_track_object()
        track['track']['isrc'] = isrc
        return track

    def test_dispatch_calls_correct_handler(self):
        """Verify each registered source calls its specific handler function."""
        from squidly.jobs.processors.download import (
            process_download_job,
            _DOWNLOAD_SOURCE_HANDLERS,
        )

        track_with_isrc = self._make_track_with_isrc('USRC12345678')
        flac_fd, flac_path = tempfile.mkstemp(suffix='.flac')
        try:
            os.write(flac_fd, b'fLaC' + b'\x00' * 100)
        finally:
            os.close(flac_fd)

        mock_handler = MagicMock(return_value={
            'file_path': flac_path,
            'source': 'https://example.com',
        })

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {'tidal': mock_handler},
                    ):
                        with patch(
                            'squidly.infrastructure.downloads.validate_audio_duration',
                        ):
                            with patch(
                                'squidly.infrastructure.downloads.add_id3_tags_to_file',
                            ):
                                with patch(
                                    'squidly.jobs.processors.download.shutil.move',
                                ):
                                    with patch(
                                        'squidly.jobs.processors.download.queue_pending_playlist_addition',
                                    ):
                                        process_download_job(
                                            'test-job-dispatch',
                                            {
                                                'trackId': '987654321',
                                                'downloadQuality': 'LOSSLESS',
                                                'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                                'ignore_matches': False,
                                                'plex_playlist': 'Test Playlist',
                                            },
                                        )

        mock_handler.assert_called_once()

    def test_unknown_source_logs_and_skips(self):
        """A source not in the registry logs a warning and continues to next source."""
        from squidly.jobs.processors.download import process_download_job
        from squidly.infrastructure.downloads import PermanentDownloadError

        track_with_isrc = self._make_track_with_isrc('USRC12345678')

        # Patch the download_sources parsing to include an unknown source
        # by using a download_source setting that passes the filter.
        # The filter only allows ('tidal', 'qobuz', 'deezer', 'deezer_mirror'),
        # so unknown sources are filtered out at the parsing stage.
        # Instead, test that when registry is empty for a valid source, it skips.
        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=[]),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    # Remove tidal from registry to simulate unknown source
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {},
                        clear=True,
                    ):
                        with pytest.raises(PermanentDownloadError) as excinfo:
                            process_download_job(
                                'test-job-unknown',
                                {
                                    'trackId': '987654321',
                                    'downloadQuality': 'LOSSLESS',
                                    'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                    'ignore_matches': False,
                                    'plex_playlist': 'Test Playlist',
                                },
                            )
                        # Should fail because no handlers available
                        assert 'failed' in str(excinfo.value).lower() or 'unknown' in str(excinfo.value).lower()


# =============================================================================
# ISRC-based library match skip (Fix 2 end-to-end)
# =============================================================================


class TestIsrcBasedLibraryMatchSkip:
    """End-to-end tests for the ISRC-based library match skip in
    process_download_job.

    When _lookup_track_metadata returns rows (because the ISRC matched an
    existing library track), the download pipeline is skipped and the
    matched path is queued for playlist addition.
    """

    @staticmethod
    def _make_track_with_isrc(isrc="US56V0507710"):
        track = _make_mock_hifi_track_object()
        track['track']['isrc'] = isrc
        return track

    def test_isrc_match_skips_download_and_queues_playlist(self):
        """When _lookup_track_metadata returns a row with a path (ISRC
        matched an existing library track), the download is skipped and
        queue_pending_playlist_addition is called with the matched path.
        No download source handler is invoked."""
        from squidly.jobs.processors.download import process_download_job

        track_with_isrc = self._make_track_with_isrc('US56V0507710')

        metadata_rows = [
            {
                'path': 'Panic! At The Disco/A Fever You Sweat Out/01 - I Write Sins.flac',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'A Fever You Sweat Out',
            }
        ]

        mock_handler = MagicMock()

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=metadata_rows),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'tidal,qobuz,deezer,deezer_mirror',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {
                            'tidal': mock_handler,
                            'qobuz': mock_handler,
                            'deezer': mock_handler,
                            'deezer_mirror': mock_handler,
                        },
                    ):
                        with patch(
                            'squidly.jobs.processors.download.queue_pending_playlist_addition',
                        ) as mock_queue:
                            result = process_download_job(
                                'test-job-isrc-match',
                                {
                                    'trackId': '987654321',
                                    'downloadQuality': 'LOSSLESS',
                                    'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                    'ignore_matches': False,
                                    'plex_playlist': 'Test Playlist',
                                },
                            )

        # Download handler was NOT called (skip path)
        mock_handler.assert_not_called()
        # queue_pending_playlist_addition was called with the matched path
        mock_queue.assert_called_once()
        call_path = mock_queue.call_args[0][0]
        assert 'Panic! At The Disco' in call_path
        assert call_path.endswith('.flac')
        # Result indicates download was skipped
        assert result.get('download_skipped_existing') is True
        assert result['stages']['downloaded'] == 'done'
        assert result['stages']['written'] == 'done'

    def test_ignore_matches_bypasses_isrc_skip(self):
        """When ignore_matches=True, the download proceeds even if
        _lookup_track_metadata returns rows."""
        from squidly.jobs.processors.download import process_download_job

        track_with_isrc = self._make_track_with_isrc('US56V0507710')

        metadata_rows = [
            {
                'path': 'Panic! At The Disco/A Fever You Sweat Out/01 - I Write Sins.flac',
                'format': 'flac',
                'bitrate': 1411,
                'album': 'A Fever You Sweat Out',
            }
        ]

        flac_fd, flac_path = tempfile.mkstemp(suffix='.flac')
        try:
            os.write(flac_fd, b'fLaC' + b'\x00' * 100)
        finally:
            os.close(flac_fd)

        mock_handler = MagicMock(return_value={
            'file_path': flac_path,
            'source': 'https://tidal-mirror.example.com',
        })

        with patch.multiple(
            'squidly.jobs.processors.download',
            get_hifi_track_object=MagicMock(return_value=track_with_isrc),
            get_db_connection=MagicMock(),
            _lookup_track_metadata=MagicMock(return_value=metadata_rows),
            jobs=MagicMock(),
            upsert_download_match_hint=MagicMock(),
            get_download_settings=MagicMock(return_value={
                'download_source': 'tidal',
                'tag_explicit_suffix': False,
            }),
            set_last_download_activity_at=MagicMock(),
            plex_healthcheck=MagicMock(return_value=True),
            get_plex_config=MagicMock(return_value=MagicMock()),
        ):
            with patch('squidly.jobs.processors.download.os.path.exists',
                       return_value=True):
                with patch('squidly.jobs.processors.download.os.makedirs'):
                    with patch.dict(
                        'squidly.jobs.processors.download._DOWNLOAD_SOURCE_HANDLERS',
                        {'tidal': mock_handler},
                    ):
                        with patch(
                            'squidly.infrastructure.downloads.detect_audio_format',
                            return_value='flac',
                        ):
                            with patch(
                                'squidly.infrastructure.downloads.validate_audio_duration',
                            ):
                                with patch(
                                    'squidly.infrastructure.downloads.add_id3_tags_to_file',
                                ):
                                    with patch(
                                        'squidly.jobs.processors.download.os.path.getsize',
                                        return_value=2048,
                                    ):
                                        with patch(
                                            'squidly.jobs.processors.download.shutil.move',
                                        ):
                                            with patch(
                                                'squidly.jobs.processors.download.queue_pending_playlist_addition',
                                            ) as mock_queue:
                                                with patch(
                                                    'builtins.open',
                                                    mock_open(read_data=b'fLaC\x00\x00\x00\x00'),
                                                ):
                                                    result = process_download_job(
                                                        'test-job-ignore-matches',
                                                        {
                                                            'trackId': '987654321',
                                                            'downloadQuality': 'LOSSLESS',
                                                            'fileNaming': '{artist}/{album}/{track} - {title}.{ext}',
                                                            'ignore_matches': True,
                                                            'plex_playlist': 'Test Playlist',
                                                        },
                                                    )

        # Download handler WAS called (ignore_matches bypassed the skip)
        mock_handler.assert_called_once()
        # Result does NOT indicate download was skipped
        assert result.get('download_skipped_existing') is None or result.get('download_skipped_existing') is False
        assert result['stages']['downloaded'] == 'done'
