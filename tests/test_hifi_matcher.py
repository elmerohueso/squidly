"""Tests for HiFi matcher gap-filling functions."""

from squidly.services.hifi_matcher import (
    _score_album_candidate,
)


class TestScoreAlbumCandidate:
    def test_empty_candidate(self):
        album_row = {'title': 'Test Album'}
        assert _score_album_candidate(album_row, {}) == 0.0

    def test_empty_candidate_id(self):
        album_row = {'title': 'Test Album'}
        candidate = {'title': 'Test Album', 'id': ''}
        assert _score_album_candidate(album_row, candidate) == 0.0

    def test_none_candidate_id(self):
        album_row = {'title': 'Test Album'}
        candidate = {'title': 'Test Album', 'id': None}
        assert _score_album_candidate(album_row, candidate) == 0.0
