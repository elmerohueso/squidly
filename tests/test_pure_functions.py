"""Tests for pure functions that require no database access."""

import json
from datetime import datetime

from squidly.jobs import (
    compute_job_backoff_seconds,
    serialize_job_payload,
)
from squidly.infrastructure.downloads import (
    download_track_all_stages_done,
    detect_audio_format,
    format_tidal_image_url,
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
