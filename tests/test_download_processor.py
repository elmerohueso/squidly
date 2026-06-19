"""Tests for squidly/jobs/processors/download.py — focused on matched path extraction.

When an existing track match is found via _lookup_track_metadata, the
file path from the DB (the `path` column) is joined with DOWNLOADS_ROOT
to produce the absolute path used for playlist queuing. This test suite
validates that extraction logic.
"""

import os
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
        import squidly.jobs.processors.download as download_module

        track_with_isrc = self._make_track_with_isrc('USRC12345678')
        mirror_url = 'https://deezer-mirror.example.com'

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
                    # Mock mirror loading at the source module
                    with patch(
                        'squidly.infrastructure.downloads.load_enabled_mirror_urls',
                        return_value=[
                            {'name': 'deezer-mirror-1', 'url': mirror_url},
                        ],
                    ):
                        # Mock the deezer_mirror download function at source
                        with patch(
                            'squidly.services.deezer_mirror.download_deezer_mirror_track',
                            return_value={
                                'file_path': '/app/temp/temp_987654321_deezer_mirror.flac',
                            },
                        ) as mock_download:
                            # Mock post-download infrastructure
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
                                                    # Mock open() for the format-detection
                                                    # block inside the deezer_mirror branch
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

        # Verify the mirror download was called correctly
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert call_kwargs['isrc'] == 'USRC12345678'
        assert call_kwargs['base_url'] == mirror_url
        assert '/app/temp/' in call_kwargs['output_path']

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
                    # Return empty list for deezer mirrors, then set up tidal
                    with patch(
                        'squidly.infrastructure.downloads.load_enabled_mirror_urls',
                        return_value=[],
                    ):
                        with patch(
                            'squidly.services.deezer_mirror.download_deezer_mirror_track',
                        ):
                            with patch(
                                'squidly.jobs.processors.download.downloads.download_track_manifest',
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
