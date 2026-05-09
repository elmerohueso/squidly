"""Tests for tag reading functions."""

import os
import tempfile
import struct

from squidly.tag_reader import (
    _resolve_library_file_path,
    _read_flac_tags,
    _read_m4a_tags,
    read_audio_file_tags,
)


class TestResolveLibraryFilePath:
    def test_empty_path(self):
        assert _resolve_library_file_path('') == ''
        assert _resolve_library_file_path(None) == ''

    def test_nonexistent_path(self):
        result = _resolve_library_file_path('/nonexistent/path.flac')
        assert result == ''


class TestReadAudioFileTags:
    def test_nonexistent_file(self):
        assert read_audio_file_tags('/nonexistent/file.flac') == {}

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            f.write(b'\x00' * 128)
            f.flush()
            assert read_audio_file_tags(f.name) == {}
            os.unlink(f.name)

    def test_invalid_flac_file(self):
        with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as f:
            f.write(b'\x00' * 128)
            f.flush()
            assert read_audio_file_tags(f.name) == {}
            os.unlink(f.name)

    def test_invalid_m4a_file(self):
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as f:
            f.write(b'\x00' * 128)
            f.flush()
            assert read_audio_file_tags(f.name) == {}
            os.unlink(f.name)
