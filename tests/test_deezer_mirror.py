"""Tests for the Deezer mirror download client (squidly/services/deezer_mirror.py).

Tests validate_deezer_mirror_endpoint and download_deezer_mirror_track
with mocked HTTP requests.
"""

import json
from unittest.mock import MagicMock, patch, mock_open

import pytest

from squidly.services.deezer_mirror import (
    validate_deezer_mirror_endpoint,
    download_deezer_mirror_track,
)


# =============================================================================
# validate_deezer_mirror_endpoint
# =============================================================================


class TestValidateDeezerMirrorEndpoint:
    """Tests for validate_deezer_mirror_endpoint."""

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_successful_health_check_returns_online(self, mock_get):
        """200 response returns online: True with recorded response time."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validate_deezer_mirror_endpoint(
            "https://deezer-mirror.example.com", timeout=5
        )

        assert result["online"] is True
        assert result["error"] is None
        assert result["responseTime"] is not None
        assert isinstance(result["responseTime"], (int, float))
        assert result["responseTime"] >= 0
        assert result["lastChecked"] is not None
        assert result["lastChecked"].endswith("Z")
        # Verify URL construction
        mock_get.assert_called_once_with(
            "https://deezer-mirror.example.com/health",
            timeout=5,
        )

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_health_check_ignores_json_body(self, mock_get):
        """200 response returns online True regardless of JSON body content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "version": "1.0.0"}
        mock_get.return_value = mock_response

        result = validate_deezer_mirror_endpoint("https://deezer-mirror.example.com")

        assert result["online"] is True
        assert result["error"] is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_non_200_response_returns_offline(self, mock_get):
        """Non-200 status returns online: False with HTTP error message."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        result = validate_deezer_mirror_endpoint("https://deezer-mirror.example.com")

        assert result["online"] is False
        assert result["error"] == "HTTP 503"
        assert result["responseTime"] is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_timeout_returns_offline(self, mock_get):
        """Timeout raises Timeout exception; returns online: False."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Connection timed out")

        result = validate_deezer_mirror_endpoint(
            "https://deezer-mirror.example.com", timeout=1
        )

        assert result["online"] is False
        assert result["error"] == "Timeout"
        assert result["responseTime"] is None
        assert result["lastChecked"] is not None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_connection_error_returns_offline(self, mock_get):
        """Connection error returns online: False with error message."""
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("Connection refused")

        result = validate_deezer_mirror_endpoint("https://deezer-mirror.example.com")

        assert result["online"] is False
        assert result["error"] == "Connection refused"
        assert result["responseTime"] is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_response_time_is_positive_float(self, mock_get):
        """responseTime should be a positive float in milliseconds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validate_deezer_mirror_endpoint("https://deezer-mirror.example.com")

        assert result["responseTime"] is not None
        assert isinstance(result["responseTime"], float)
        assert result["responseTime"] > 0

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_url_trailing_slash_stripped(self, mock_get):
        """Trailing slash on base URL is stripped before appending /health."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        validate_deezer_mirror_endpoint("https://deezer-mirror.example.com/")

        mock_get.assert_called_once_with(
            "https://deezer-mirror.example.com/health",
            timeout=5,
        )

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_general_request_exception(self, mock_get):
        """Non-timeout request exceptions return online: False."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("DNS resolution failed")

        result = validate_deezer_mirror_endpoint("https://invalid.example.com")

        assert result["online"] is False
        assert result["error"] == "DNS resolution failed"
        assert result["responseTime"] is None


# =============================================================================
# download_deezer_mirror_track
# =============================================================================


class TestDownloadDeezerMirrorTrack:
    """Tests for download_deezer_mirror_track."""

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_successful_download_returns_file_path(self, mock_get):
        """Streaming download writes file and returns file_path dict."""
        chunk_data = b"fLaC" + b"\x00" * 100  # FLAC header + padding
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [chunk_data]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("squidly.services.deezer_mirror.os.path.getsize",
                       return_value=len(chunk_data)):
                result = download_deezer_mirror_track(
                    base_url="https://deezer-mirror.example.com",
                    isrc="USRC12345678",
                    output_path="/tmp/test_output.flac",
                )

        assert result is not None
        assert result["file_path"] == "/tmp/test_output.flac"

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://deezer-mirror.example.com/stream/"
        assert call_args[1]["params"] == {"isrc": "USRC12345678", "format": "FLAC"}
        assert call_args[1]["stream"] is True
        assert call_args[1]["timeout"] == 120

        # Verify file was written
        mock_file().write.assert_called_once_with(chunk_data)

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_proper_origin_and_referer_headers(self, mock_get):
        """Origin and Referer headers are sent with the request."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()):
            with patch("squidly.services.deezer_mirror.os.path.getsize",
                       return_value=4):
                download_deezer_mirror_track(
                    base_url="https://deezer-mirror.example.com",
                    isrc="USRC12345678",
                    output_path="/tmp/test.flac",
                )

        call_headers = mock_get.call_args[1]["headers"]
        assert call_headers["Origin"] == "https://deezer.com"
        assert call_headers["Referer"] == "https://deezer.com/"

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_custom_timeout_is_passed(self, mock_get):
        """Custom timeout value is passed through to requests.get."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()):
            with patch("squidly.services.deezer_mirror.os.path.getsize",
                       return_value=4):
                download_deezer_mirror_track(
                    base_url="https://deezer-mirror.example.com",
                    isrc="USRC12345678",
                    output_path="/tmp/test.flac",
                    timeout=300,
                )

        assert mock_get.call_args[1]["timeout"] == 300

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_url_trailing_slash_handling(self, mock_get):
        """Base URL with trailing slash is handled correctly (/stream/ not //stream/)."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"data"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()):
            with patch("squidly.services.deezer_mirror.os.path.getsize",
                       return_value=4):
                download_deezer_mirror_track(
                    base_url="https://deezer-mirror.example.com/",
                    isrc="USRC12345678",
                    output_path="/tmp/test.flac",
                )

        call_url = mock_get.call_args[0][0]
        # Should not have double slash
        assert call_url == "https://deezer-mirror.example.com/stream/"
        assert "//stream" not in call_url.replace("://", "XX")

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_network_error_returns_none(self, mock_get):
        """RequestException during streaming download returns None."""
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Connection failed")

        result = download_deezer_mirror_track(
            base_url="https://deezer-mirror.example.com",
            isrc="USRC12345678",
            output_path="/tmp/test.flac",
        )

        assert result is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_http_error_returns_none(self, mock_get):
        """HTTP error via raise_for_status returns None."""
        from requests.exceptions import HTTPError

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = download_deezer_mirror_track(
            base_url="https://deezer-mirror.example.com",
            isrc="USRC12345678",
            output_path="/tmp/test.flac",
        )

        assert result is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_file_write_error_returns_none(self, mock_get):
        """OSError during file write returns None."""
        chunk_data = b"test data"
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [chunk_data]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Make open raise OSError on write
        mo = mock_open()
        mo().write.side_effect = OSError("Disk full")

        with patch("builtins.open", mo):
            result = download_deezer_mirror_track(
                base_url="https://deezer-mirror.example.com",
                isrc="USRC12345678",
                output_path="/tmp/test.flac",
            )

        assert result is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_timeout_during_download_returns_none(self, mock_get):
        """Timeout during streaming download returns None."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Stream timed out")

        result = download_deezer_mirror_track(
            base_url="https://deezer-mirror.example.com",
            isrc="USRC12345678",
            output_path="/tmp/test.flac",
        )

        assert result is None

    @patch("squidly.services.deezer_mirror.requests.get")
    def test_multiple_chunks_written_correctly(self, mock_get):
        """Multiple streaming chunks are concatenated into the output file."""
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        mock_response = MagicMock()
        mock_response.iter_content.return_value = chunks
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        mo = mock_open()
        with patch("builtins.open", mo):
            with patch("squidly.services.deezer_mirror.os.path.getsize",
                       return_value=18):
                result = download_deezer_mirror_track(
                    base_url="https://deezer-mirror.example.com",
                    isrc="USRC12345678",
                    output_path="/tmp/test.flac",
                )

        assert result is not None
        # Each chunk was written
        assert mo().write.call_count == 3
        mo().write.assert_any_call(b"chunk1")
        mo().write.assert_any_call(b"chunk2")
        mo().write.assert_any_call(b"chunk3")
