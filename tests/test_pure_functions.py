"""Tests for pure functions that require no database access."""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

# Patch logging before importing squidly modules to avoid /logs PermissionError
os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")

from squidly.jobs import (
    compute_job_backoff_seconds,
    serialize_job_payload,
)
from squidly.jobs.processors.download import _PERMANENT_ERROR_KEYWORDS
from squidly.infrastructure.downloads import (
    download_track_all_stages_done,
    detect_audio_format,
    format_tidal_image_url,
    load_enabled_mirror_urls,
)
from squidly.infrastructure.utils import (
    clean_path_components,
    extract_year_from_text,
    sanitize_filename_component,
)
from squidly.infrastructure.storage import normalize_db_timestamp


class TestSerializeJobPayload:
    def test_serializes_dict(self):
        payload = {"key": "value", "num": 42}
        result = serialize_job_payload(payload)
        assert isinstance(result, str)
        assert json.loads(result) == payload

    def test_serializes_none(self):
        result = serialize_job_payload(None)
        assert result == "null"

    def test_serializes_string(self):
        result = serialize_job_payload("hello")
        assert result == '"hello"'


class TestComputeJobBackoffSeconds:
    def test_attempt_1(self):
        assert compute_job_backoff_seconds(1) == 30

    def test_attempt_2(self):
        assert compute_job_backoff_seconds(2) == 60

    def test_attempt_3(self):
        assert compute_job_backoff_seconds(3) == 120

    def test_attempt_grows_exponentially(self):
        t1 = compute_job_backoff_seconds(1)
        t5 = compute_job_backoff_seconds(5)
        assert t5 > t1

    def test_attempt_0(self):
        assert compute_job_backoff_seconds(0) == 30


class TestDownloadTrackAllStagesDone:
    def test_all_done(self):
        stages = {
            "downloaded": "done",
            "tagged": "done",
            "written": "done",
            "playlist_added": "done",
        }
        assert download_track_all_stages_done(stages) is True

    def test_playlist_added_skipped(self):
        stages = {
            "downloaded": "done",
            "tagged": "done",
            "written": "done",
            "playlist_added": "skipped",
        }
        assert download_track_all_stages_done(stages) is True

    def test_missing_stage(self):
        stages = {"downloaded": "done", "tagged": "done"}
        assert download_track_all_stages_done(stages) is False

    def test_stage_pending(self):
        stages = {
            "downloaded": "done",
            "tagged": "pending",
            "written": "done",
            "playlist_added": "done",
        }
        assert download_track_all_stages_done(stages) is False

    def test_not_a_dict(self):
        assert download_track_all_stages_done(None) is False
        assert download_track_all_stages_done([]) is False
        assert download_track_all_stages_done("done") is False


class TestFormatTidalImageUrl:
    def test_basic_uuid(self):
        result = format_tidal_image_url("abc123", 640)
        assert result == "https://resources.tidal.com/images/abc123/640x640.jpg"

    def test_replaces_dashes(self):
        result = format_tidal_image_url("a-b-c", 1280)
        assert result == "https://resources.tidal.com/images/a/b/c/1280x1280.jpg"

    def test_empty_string(self):
        assert format_tidal_image_url("", 640) == ""

    def test_none(self):
        assert format_tidal_image_url(None, 640) == ""


class TestDetectAudioFormat:
    def test_flac(self):
        assert detect_audio_format(b"fLaC" + b"\x00" * 100) == "flac"

    def test_m4a(self):
        data = b"\x00\x00\x00\x1cftypM4A " + b"\x00" * 100
        assert detect_audio_format(data) == "m4a"

    def test_m4a_mp42(self):
        data = b"\x00\x00\x00\x1cftypmp42" + b"\x00" * 100
        assert detect_audio_format(data) == "m4a"

    def test_mp3_id3(self):
        assert detect_audio_format(b"ID3" + b"\x00" * 100) == "mp3"

    def test_mp3_mpeg_sync(self):
        data = bytes([0xFF, 0xFB]) + b"\x00" * 100
        assert detect_audio_format(data) == "mp3"

    def test_too_short(self):
        assert detect_audio_format(b"fLa") == "unknown"

    def test_unknown(self):
        assert detect_audio_format(b"RIFF" + b"\x00" * 100) == "unknown"


class TestSanitizeFilenameComponent:
    def test_replaces_slashes(self):
        assert "/" not in sanitize_filename_component("artist/name")
        assert "\\" not in sanitize_filename_component("artist\\name")

    def test_replaces_colon(self):
        result = sanitize_filename_component("title: remix")
        assert ":" not in result

    def test_replaces_pipe(self):
        result = sanitize_filename_component("title | remix")
        assert "|" not in result

    def test_removes_angle_brackets(self):
        result = sanitize_filename_component("file<name>")
        assert "<" not in result
        assert ">" not in result

    def test_passes_through_clean_string(self):
        assert sanitize_filename_component("Clean Title") == "Clean Title"

    def test_returns_empty_for_empty_input(self):
        assert sanitize_filename_component("") == ""
        assert sanitize_filename_component(None) is None


class TestCleanPathComponents:
    def test_filters_dot_components(self):
        result = clean_path_components("./Artist/Album/./Track")
        assert "." not in result.split("/")

    def test_filters_dotdot_components(self):
        result = clean_path_components("Artist/../Album/Track")
        assert ".." not in result.split("/")

    def test_preserves_valid_components(self):
        result = clean_path_components("Artist/Album/Track.flac")
        assert result == "Artist/Album/Track.flac"

    def test_strips_trailing_period(self):
        result = clean_path_components("Artist./Album./Track.")
        assert result == "Artist/Album/Track"

    def test_strips_trailing_space(self):
        result = clean_path_components("Artist /Album /Track ")
        assert result == "Artist/Album/Track"


class TestExtractYearFromText:
    def test_finds_year(self):
        assert extract_year_from_text("(P) 2023 Record Label") == "2023"

    def test_finds_1900s_year(self):
        assert extract_year_from_text("1985") == "1985"

    def test_no_year(self):
        assert extract_year_from_text("No year here") == ""

    def test_empty_string(self):
        assert extract_year_from_text("") == ""

    def test_none(self):
        assert extract_year_from_text(None) == ""

    def test_ignores_non_year_numbers(self):
        assert extract_year_from_text("34567") == ""


class TestNormalizeDbTimestamp:
    def test_datetime_object(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = normalize_db_timestamp(dt)
        assert result.year == 2024
        assert result.month == 1

    def test_iso_string(self):
        result = normalize_db_timestamp("2024-01-15T10:30:00")
        assert result.year == 2024

    def test_utc_z_string(self):
        result = normalize_db_timestamp("2024-01-15T10:30:00Z")
        assert result.year == 2024

    def test_none(self):
        assert normalize_db_timestamp(None) is None

    def test_empty_string(self):
        assert normalize_db_timestamp("") is None

    def test_invalid_string(self):
        assert normalize_db_timestamp("not-a-date") is None


class TestPermanentErrorKeywords:
    """Tests for permanent error keyword matching in download processor."""

    def test_new_qobuz_message_matches(self):
        error_str = "No Qobuz mirrors available (need enabled, online, premium)"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_similar_but_different_message_does_not_match(self):
        """Old keyword 'no qobuz mirrors configured' was replaced with 'no qobuz mirrors available',
        so the old error wording no longer matches the new keywords."""
        error_str = "no qobuz mirrors configured"
        assert not any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_none_keyword_still_matches(self):
        error_str = "no configured mirror"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_unrelated_error_does_not_match(self):
        error_str = "Some other error occurred"
        assert not any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_each_keyword_matches_itself(self):
        for keyword in _PERMANENT_ERROR_KEYWORDS:
            assert any(kw in keyword.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_case_insensitive_matching(self):
        error_str = "NO QOBUZ MIRRORS AVAILABLE"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_not_found_in_qobuz_catalog_matches(self):
        error_str = "not found in Qobuz catalog"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_not_found_on_deezer_matches(self):
        error_str = "not found on Deezer"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_not_available_in_flac_on_deezer_matches(self):
        error_str = "not available in FLAC on Deezer"
        assert any(kw in error_str.lower() for kw in _PERMANENT_ERROR_KEYWORDS)

    def test_permanent_error_keywords_contains_new_entries(self):
        assert 'not found in qobuz catalog' in _PERMANENT_ERROR_KEYWORDS
        assert 'not found on deezer' in _PERMANENT_ERROR_KEYWORDS
        assert 'not available in flac on deezer' in _PERMANENT_ERROR_KEYWORDS


class TestLoadEnabledMirrorUrls:
    """Tests for load_enabled_mirror_urls SQL construction."""

    @patch('squidly.infrastructure.downloads.get_db_connection')
    def test_accepts_for_download_keyword_arg(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        result = load_enabled_mirror_urls(for_download=True)
        assert result == []

    @patch('squidly.infrastructure.downloads.get_db_connection')
    def test_default_no_premium_filter(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        load_enabled_mirror_urls()
        sql = mock_cur.execute.call_args[0][0]
        assert 'AND online = 1 AND is_premium = 1' not in sql

    @patch('squidly.infrastructure.downloads.get_db_connection')
    def test_for_download_adds_premium_filter(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        load_enabled_mirror_urls(for_download=True)
        sql = mock_cur.execute.call_args[0][0]
        assert 'AND online = 1 AND is_premium = 1' in sql

    @patch('squidly.infrastructure.downloads.get_db_connection')
    def test_for_download_with_mirror_type(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        load_enabled_mirror_urls(mirror_type='qobuz', for_download=True)
        sql = mock_cur.execute.call_args[0][0]
        assert 'AND online = 1 AND is_premium = 1' in sql
        assert 'mirror_type = %s' in sql

    @patch('squidly.infrastructure.downloads.get_db_connection')
    def test_default_no_premium_with_mirror_type(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_get_db.return_value = mock_conn
        load_enabled_mirror_urls(mirror_type='tidal')
        sql = mock_cur.execute.call_args[0][0]
        assert 'AND online = 1 AND is_premium = 1' not in sql
        assert 'mirror_type = %s' in sql
