"""Tests for the Deezer API client (squidly/services/deezer.py)."""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from squidly.services.deezer import (
    calcbfkey,
    decryptfile,
    get_deezer_session,
    get_deezer_stream_url,
    md5hex,
    search_deezer_track,
)


# =============================================================================
# md5hex
# =============================================================================

class TestMd5hex:
    def test_hello(self):
        result = md5hex(b"hello")
        assert result == hashlib.md5(b"hello").hexdigest().encode()

    def test_empty_bytes(self):
        result = md5hex(b"")
        assert result == hashlib.md5(b"").hexdigest().encode()

    def test_always_32_bytes(self):
        """MD5 hex digest is always 32 ASCII bytes (16-byte digest -> 32 hex chars)."""
        for data in [b"a", b"test", b"hello world", b"\x00\x01\x02"]:
            result = md5hex(data)
            assert len(result) == 32
            assert isinstance(result, bytes)


# =============================================================================
# calcbfkey
# =============================================================================

class TestCalcbfkey:
    def test_song_id_3135556_length(self):
        key = calcbfkey("3135556")
        assert len(key) == 16

    def test_song_id_917265_length(self):
        key = calcbfkey("917265")
        assert len(key) == 16

    def test_different_ids_produce_different_keys(self):
        key_a = calcbfkey("3135556")
        key_b = calcbfkey("917265")
        assert key_a != key_b

    def test_key_is_string(self):
        key = calcbfkey("3135556")
        assert isinstance(key, str)


# =============================================================================
# search_deezer_track (mocked)
# =============================================================================

class TestSearchDeezerTrack:
    @patch("squidly.services.deezer.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": 3135556,
            "title": "Test Track",
            "track_token": "abc123",
            "isrc": "USRC12345678",
        }
        mock_get.return_value = mock_resp

        result = search_deezer_track("USRC12345678")

        assert result is not None
        assert result["id"] == 3135556
        assert result["title"] == "Test Track"
        mock_resp.raise_for_status.assert_called_once()

    @patch("squidly.services.deezer.requests.get")
    def test_404_returns_none(self, mock_get):
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")
        mock_get.return_value = mock_resp

        result = search_deezer_track("NONEXISTENT")

        assert result is None

    @patch("squidly.services.deezer.requests.get")
    def test_network_error_returns_none(self, mock_get):
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        result = search_deezer_track("USRC12345678")

        assert result is None

    @patch("squidly.services.deezer.requests.get")
    def test_empty_error_response_returns_none(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": {"message": "not found"}}
        mock_get.return_value = mock_resp

        result = search_deezer_track("USRC12345678")

        assert result is None


# =============================================================================
# get_deezer_session (mocked)
# =============================================================================

class TestGetDeezerSession:
    @patch("squidly.services.deezer.requests.session")
    def test_success(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {
                "USER": {
                    "OPTIONS": {
                        "license_token": "lic_abc123",
                        "web_sound_quality": {"lossless": True},
                    }
                }
            }
        }

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        result = get_deezer_session("test_arl")

        assert result is not None
        assert result["license_token"] == "lic_abc123"
        assert result["lossless"] is True

    @patch("squidly.services.deezer.requests.session")
    def test_missing_lossless_defaults_to_false(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {
                "USER": {
                    "OPTIONS": {
                        "license_token": "lic_abc123",
                        "web_sound_quality": {},
                    }
                }
            }
        }

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        result = get_deezer_session("test_arl")

        assert result is not None
        assert result["lossless"] is False

    @patch("squidly.services.deezer.requests.session")
    def test_network_error_returns_none(self, mock_session_cls):
        import requests
        mock_session = MagicMock()
        mock_session.post.side_effect = requests.RequestException("Connection refused")
        mock_session_cls.return_value = mock_session

        result = get_deezer_session("test_arl")

        assert result is None


# =============================================================================
# get_deezer_stream_url (mocked)
# =============================================================================

class TestGetDeezerStreamUrl:
    @patch("squidly.services.deezer.requests.Session")
    def test_success(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{
                "media": [{
                    "sources": [{
                        "url": "https://media.deezer.com/stream/abc123.flac",
                    }]
                }]
            }]
        }

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        result = get_deezer_stream_url("track_token_abc", "lic_xyz", mock_session)

        assert result == "https://media.deezer.com/stream/abc123.flac"

    @patch("squidly.services.deezer.requests.Session")
    def test_error_response_returns_none(self, mock_session_cls):
        import requests
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("Bad status")

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        result = get_deezer_stream_url("track_token_abc", "lic_xyz", mock_session)

        assert result is None

    @patch("squidly.services.deezer.requests.Session")
    def test_missing_data_returns_none(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_session_cls.return_value = mock_session

        result = get_deezer_stream_url("track_token_abc", "lic_xyz", mock_session)

        assert result is None


# =============================================================================
# decryptfile (mocked)
# =============================================================================

class TestDecryptfile:
    def test_writes_to_file(self, tmp_path):
        # Build a mock response that yields 6 blocks of 2048 bytes each.
        # Block 0 is encrypted (i % 3 == 0), blocks 1 and 2 are plain.
        block = b"\x00" * 2048

        mock_response = MagicMock()
        mock_response.iter_content.return_value = iter([block] * 6)

        key = calcbfkey("3135556")
        output_path = str(tmp_path / "decrypted.flac")

        success = decryptfile(mock_response, key, output_path)

        assert success is True
        with open(output_path, "rb") as f:
            assert len(f.read()) == 6 * 2048

    def test_empty_response(self, tmp_path):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = iter([])

        key = calcbfkey("3135556")
        output_path = str(tmp_path / "decrypted.flac")

        success = decryptfile(mock_response, key, output_path)

        assert success is True
        with open(output_path, "rb") as f:
            assert len(f.read()) == 0

    def test_partial_last_block(self, tmp_path):
        # Last block is smaller than block_size — should pass through unencrypted.
        small_block = b"\xFF" * 1000
        full_block = b"\x00" * 2048

        mock_response = MagicMock()
        mock_response.iter_content.return_value = iter([full_block, small_block])

        key = calcbfkey("3135556")
        output_path = str(tmp_path / "decrypted.flac")

        success = decryptfile(mock_response, key, output_path)

        assert success is True
        with open(output_path, "rb") as f:
            data = f.read()
            assert len(data) == 2048 + 1000