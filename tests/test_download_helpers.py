"""Tests for download helper functions in squidly/infrastructure/downloads.py.

Covers expected_download_format() and make_temp_download_path().
"""

import os

import pytest

from squidly.infrastructure.downloads import (
    expected_download_format,
    make_temp_download_path,
)


# =============================================================================
# expected_download_format
# =============================================================================


class TestExpectedDownloadFormat:
    """Tests for expected_download_format(source, quality)."""

    # Deezer / deezer_mirror always return FLAC regardless of quality.
    @pytest.mark.parametrize("quality", ["LOSSLESS", "HIGH", "LOW", "DOLBY_ATMOS", "HIRES_LOSSLESS"])
    def test_deezer_always_flac(self, quality):
        """deezer source always returns 'flac' regardless of quality."""
        assert expected_download_format("deezer", quality) == "flac"

    @pytest.mark.parametrize("quality", ["LOSSLESS", "HIGH", "LOW", "DOLBY_ATMOS", "HIRES_LOSSLESS"])
    def test_deezer_mirror_always_flac(self, quality):
        """deezer_mirror source always returns 'flac' regardless of quality."""
        assert expected_download_format("deezer_mirror", quality) == "flac"

    # Tidal / Qobuz: HIGH, LOW, DOLBY_ATMOS -> m4a
    @pytest.mark.parametrize("source", ["tidal", "qobuz"])
    @pytest.mark.parametrize("quality", ["HIGH", "LOW", "DOLBY_ATMOS"])
    def test_tidal_qobuz_lossy_returns_m4a(self, source, quality):
        """tidal/qobuz with lossy quality presets return 'm4a'."""
        assert expected_download_format(source, quality) == "m4a"

    # Tidal / Qobuz: LOSSLESS, HIRES_LOSSLESS -> flac
    @pytest.mark.parametrize("source", ["tidal", "qobuz"])
    @pytest.mark.parametrize("quality", ["LOSSLESS", "HIRES_LOSSLESS"])
    def test_tidal_qobuz_lossless_returns_flac(self, source, quality):
        """tidal/qobuz with lossless quality presets return 'flac'."""
        assert expected_download_format(source, quality) == "flac"

    def test_unknown_quality_defaults_to_flac(self):
        """An unrecognized quality string defaults to 'flac' (the safe path)."""
        assert expected_download_format("tidal", "WEIRD_QUALITY") == "flac"

    def test_unknown_source_defaults_to_flac(self):
        """An unrecognized source defaults to 'flac' (the safe path)."""
        assert expected_download_format("unknown_source", "HIGH") == "m4a"
        assert expected_download_format("unknown_source", "LOSSLESS") == "flac"


# =============================================================================
# make_temp_download_path
# =============================================================================


class TestMakeTempDownloadPath:
    """Tests for make_temp_download_path(identifier, source, quality)."""

    def test_deezer_mirror_uses_flac_extension(self):
        """deezer_mirror temp path ends with .flac."""
        path = make_temp_download_path("USRC12345678", "deezer_mirror", "LOSSLESS")
        assert path.endswith(".flac")
        assert "deezer_mirror" in path
        assert "USRC12345678" in path

    def test_deezer_uses_flac_extension(self):
        """deezer temp path ends with .flac."""
        path = make_temp_download_path("USRC12345678", "deezer", "HIGH")
        assert path.endswith(".flac")

    def test_tidal_high_uses_m4a_extension(self):
        """tidal with HIGH quality uses .m4a extension."""
        path = make_temp_download_path("USRC12345678", "tidal", "HIGH")
        assert path.endswith(".m4a")

    def test_tidal_lossless_uses_flac_extension(self):
        """tidal with LOSSLESS quality uses .flac extension."""
        path = make_temp_download_path("USRC12345678", "tidal", "LOSSLESS")
        assert path.endswith(".flac")

    def test_qobuz_low_uses_m4a_extension(self):
        """qobuz with LOW quality uses .m4a extension."""
        path = make_temp_download_path("USRC12345678", "qobuz", "LOW")
        assert path.endswith(".m4a")

    def test_custom_temp_folder(self):
        """Custom temp_folder parameter is respected."""
        path = make_temp_download_path("ABC", "tidal", "LOSSLESS", temp_folder="/custom/tmp")
        assert path.startswith("/custom/tmp/")

    def test_default_temp_folder(self):
        """Default temp_folder is /app/temp."""
        path = make_temp_download_path("ABC", "tidal", "LOSSLESS")
        assert path.startswith("/app/temp/")

    def test_extension_matches_expected_format(self):
        """For every source+quality combination, the path extension matches
        expected_download_format."""
        sources = ["tidal", "qobuz", "deezer", "deezer_mirror"]
        qualities = ["LOSSLESS", "HIGH", "LOW", "DOLBY_ATMOS", "HIRES_LOSSLESS"]
        for source in sources:
            for quality in qualities:
                path = make_temp_download_path("ID", source, quality)
                expected_ext = expected_download_format(source, quality)
                assert path.endswith(f".{expected_ext}"), (
                    f"source={source}, quality={quality}: path={path}, "
                    f"expected_ext={expected_ext}"
                )
