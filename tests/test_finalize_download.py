"""Tests for _finalize_download in squidly/jobs/processors/download.py.

Verifies format detection, format mismatch handling, suspicious-file handling,
and the ordering guarantee (format check before duration check).
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from squidly.jobs.processors.download import _finalize_download


# ── Magic bytes for format detection ────────────────────────────────────────
# FLAC: starts with 'fLaC'
# MP3 (ID3): starts with 'ID3'
# MP3 (sync): starts with 0xFF 0xE0 (MPEG frame sync)
# M4A: starts with size (4 bytes) + 'ftyp' + brand (e.g. 'M4A ')
# Unknown: arbitrary bytes that match no known magic

FLAC_HEADER = b"fLaC" + b"\x00" * 28  # 32 bytes, minimum for detect_audio_format
MP3_ID3_HEADER = b"ID3" + b"\x00" * 29  # 32 bytes
MP3_SYNC_HEADER = b"\xff\xe0" + b"\x00" * 30  # 32 bytes
M4A_HEADER = b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 16  # 32 bytes
UNKNOWN_HEADER = b"\x01\x02\x03\x04" + b"\x00" * 28  # 32 bytes


def _write_temp(data: bytes) -> str:
    """Write data to a temp file and return its path. Caller must clean up."""
    fd, path = tempfile.mkstemp(suffix=".bin")
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    return path


class TestFinalizeDownloadFormatPass:
    """Happy path: format matches expected."""

    def test_flac_passes_when_expected_flac(self):
        """FLAC file with expected_format='flac' returns 'flac' without raising."""
        path = _write_temp(FLAC_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration"):
                result = _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
            assert result == "flac"
        finally:
            os.unlink(path)

    def test_m4a_passes_when_expected_m4a(self):
        """M4A file with expected_format='m4a' returns 'm4a' without raising."""
        path = _write_temp(M4A_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration"):
                result = _finalize_download(path, "tidal", expected_duration=180, expected_format="m4a")
            assert result == "m4a"
        finally:
            os.unlink(path)

    def test_mp3_passes_when_expected_mp3(self):
        """MP3 file with expected_format='mp3' returns 'mp3' without raising."""
        path = _write_temp(MP3_ID3_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration"):
                result = _finalize_download(path, "some_source", expected_duration=180, expected_format="mp3")
            assert result == "mp3"
        finally:
            os.unlink(path)


class TestFinalizeDownloadFormatMismatch:
    """The primary bug fix: format mismatch raises ValueError."""

    def test_mp3_raises_when_expected_flac(self):
        """MP3 file with expected_format='flac' raises ValueError.

        This is the exact bug scenario: deezer_mirror serving MP3 instead
        of FLAC must be rejected, not silently accepted."""
        path = _write_temp(MP3_ID3_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration") as mock_validate:
                with pytest.raises(ValueError, match="(?i)expected flac.*detected mp3"):
                    _finalize_download(path, "deezer_mirror", expected_duration=180, expected_format="flac")
                # Format mismatch must be detected BEFORE duration validation
                mock_validate.assert_not_called()
        finally:
            os.unlink(path)

    def test_flac_raises_when_expected_m4a(self):
        """FLAC file with expected_format='m4a' raises ValueError."""
        path = _write_temp(FLAC_HEADER)
        try:
            with pytest.raises(ValueError, match="(?i)expected m4a.*detected flac"):
                _finalize_download(path, "tidal", expected_duration=180, expected_format="m4a")
        finally:
            os.unlink(path)

    def test_mp3_sync_header_raises_when_expected_flac(self):
        """MP3 sync-word header (0xFF 0xE0) with expected_format='flac' raises ValueError."""
        path = _write_temp(MP3_SYNC_HEADER)
        try:
            with pytest.raises(ValueError, match="(?i)expected flac.*detected mp3"):
                _finalize_download(path, "deezer_mirror", expected_duration=180, expected_format="flac")
        finally:
            os.unlink(path)


class TestFinalizeDownloadSuspiciousFile:
    """Edge cases: zero-byte or tiny unidentifiable files."""

    def test_zero_byte_file_raises(self):
        """0-byte file with format='unknown' raises ValueError (suspiciously small)."""
        path = _write_temp(b"")
        try:
            with pytest.raises(ValueError, match="(?i)suspiciously small"):
                _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
        finally:
            os.unlink(path)

    def test_tiny_file_below_1kb_raises(self):
        """File < 1KB with unrecognized magic bytes raises ValueError."""
        path = _write_temp(UNKNOWN_HEADER)  # 32 bytes, unknown format
        try:
            with pytest.raises(ValueError, match="(?i)suspiciously small"):
                _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
        finally:
            os.unlink(path)

    def test_large_unknown_file_defaults_to_expected(self):
        """Large file (> 1KB) with unrecognized magic bytes defaults to
        expected_format and logs a warning (does not raise)."""
        # Create a file > 1KB with unrecognized magic bytes
        data = UNKNOWN_HEADER[:4] + b"\x00" * 2048
        path = _write_temp(data)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration"):
                result = _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
            assert result == "flac"
        finally:
            os.unlink(path)


class TestFinalizeDownloadOrdering:
    """Verify format check runs BEFORE duration check (the ordering fix)."""

    def test_format_mismatch_skips_duration_validation(self):
        """When format mismatches, validate_audio_duration is NEVER called.

        This verifies the ordering fix: format check (cheap) happens before
        duration check (expensive, runs ffmpeg)."""
        path = _write_temp(MP3_ID3_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration") as mock_validate:
                with pytest.raises(ValueError):
                    _finalize_download(path, "deezer_mirror", expected_duration=180, expected_format="flac")
                mock_validate.assert_not_called()
        finally:
            os.unlink(path)

    def test_format_match_calls_duration_validation(self):
        """When format matches, validate_audio_duration IS called."""
        path = _write_temp(FLAC_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration") as mock_validate:
                _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
                mock_validate.assert_called_once_with(path, 180)
        finally:
            os.unlink(path)

    def test_suspiciously_small_file_skips_duration_validation(self):
        """When file is suspiciously small, validate_audio_duration is NEVER called."""
        path = _write_temp(b"")
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration") as mock_validate:
                with pytest.raises(ValueError):
                    _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
                mock_validate.assert_not_called()
        finally:
            os.unlink(path)


class TestFinalizeDownloadLogging:
    """Verify _finalize_download logs file size and format info."""

    def test_logs_file_size_on_success(self):
        """Successful finalize logs the file size and format."""
        path = _write_temp(FLAC_HEADER)
        try:
            with patch("squidly.infrastructure.downloads.validate_audio_duration"):
                with patch("squidly.jobs.processors.download.logger") as mock_logger:
                    _finalize_download(path, "tidal", expected_duration=180, expected_format="flac")
                    # At least one info call should mention the source and format
                    info_calls = [str(c) for c in mock_logger.info.call_args_list]
                    assert any("tidal" in c and "flac" in c for c in info_calls)
        finally:
            os.unlink(path)
