"""Tests for pure matching/scoring functions that require no database access."""

from squidly.matching import (
    normalize_match_text,
    _extract_hifi_item_artists,
    _extract_primary_hifi_artist,
    _track_needs_hifi_match,
    _is_manual_match,
    _merge_match_state,
    _is_hifi_explicit,
    _format_hifi_track_title,
    _extract_hifi_album_track_titles,
    _has_explicit_marker,
    _score_explicit_alignment,
    _score_album_track_title_alignment,
    _score_artist_candidate_name,
    _extract_album_candidate_artist_names,
    _score_album_candidate_artist_alignment,
    _score_album_candidate_title,
    _score_track_candidate_payload,
    _serialize_match_variants,
    _choose_artist_candidate,
    _choose_track_candidate,
)


class TestNormalizeMatchText:
    def test_basic_normalization(self):
        assert normalize_match_text("Hello World") == "hello world"

    def test_strips_special_chars(self):
        assert normalize_match_text("Hello, World!") == "hello world"

    def test_strips_trailing_parenthetical(self):
        result = normalize_match_text("Song Title (Remix)", strip_trailing_parenthetical=True)
        assert result == "song title"

    def test_strips_trailing_brackets(self):
        result = normalize_match_text("Song Title [Explicit]", strip_trailing_parenthetical=True)
        assert result == "song title"

    def test_empty_string(self):
        assert normalize_match_text("") == ""

    def test_none(self):
        assert normalize_match_text(None) == ""


class TestExtractHifiItemArtists:
    def test_empty_dict(self):
        assert _extract_hifi_item_artists({}) == []

    def test_not_a_dict(self):
        assert _extract_hifi_item_artists([]) == []
        assert _extract_hifi_item_artists(None) == []

    def test_single_artist(self):
        item = {"artist": {"id": 123, "name": "Test Artist"}}
        result = _extract_hifi_item_artists(item)
        assert len(result) == 1
        assert result[0]["name"] == "Test Artist"

    def test_artists_list(self):
        item = {"artists": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
        result = _extract_hifi_item_artists(item)
        assert len(result) == 2

    def test_deduplicates(self):
        item = {
            "artist": {"id": 1, "name": "Same"},
            "artists": [{"id": 1, "name": "Same"}]
        }
        result = _extract_hifi_item_artists(item)
        assert len(result) == 1


class TestExtractPrimaryHifiArtist:
    def test_returns_first_artist(self):
        item = {"artists": [{"id": 1, "name": "Primary"}, {"id": 2, "name": "Featured"}]}
        result = _extract_primary_hifi_artist(item)
        assert result["name"] == "Primary"

    def test_returns_none_for_empty(self):
        assert _extract_primary_hifi_artist({}) is None


class TestTrackNeedsHifiMatch:
    def test_needs_match_when_no_hifi_id(self):
        assert _track_needs_hifi_match({"hifi_id": "", "confidence": 0.0}) is True

    def test_needs_match_when_unmatched(self):
        assert _track_needs_hifi_match({"hifi_id": "123", "confidence": 0.5}) is True

    def test_does_not_need_match_when_confirmed(self):
        assert _track_needs_hifi_match({"hifi_id": "123", "confidence": 0.99}) is False

    def test_not_a_dict(self):
        assert _track_needs_hifi_match(None) is False


class TestIsManualMatch:
    def test_manual_match(self):
        assert _is_manual_match({"confidence": 1.0, "hifi_id": "456"}) is True

    def test_not_manual(self):
        assert _is_manual_match({"confidence": 0.99, "hifi_id": "456"}) is False

    def test_not_a_dict(self):
        assert _is_manual_match(None) is False


class TestMergeMatchState:
    def test_preserves_manual_match(self):
        existing = {"confidence": 1.0, "hifi_id": "456"}
        result = _merge_match_state(existing, hifi_id="789", confidence=0.5)
        assert result["hifi_id"] == "456"
        assert result["confidence"] == 1.0

    def test_applies_new_hifi_id(self):
        existing = {"confidence": 0.0}
        result = _merge_match_state(existing, hifi_id="123", confidence=0.9)
        assert result["hifi_id"] == "123"
        assert result["confidence"] == 0.9

    def test_preserves_existing_confidence_when_same_hifi_id(self):
        existing = {"confidence": 0.99, "hifi_id": "123"}
        result = _merge_match_state(existing, hifi_id="123")
        assert result["hifi_id"] == "123"
        assert result["confidence"] == 0.99

    def test_not_a_dict_existing(self):
        result = _merge_match_state(None, hifi_id="123", confidence=0.8)
        assert result["hifi_id"] == "123"


class TestIsHifiExplicit:
    def test_explicit_flag(self):
        assert _is_hifi_explicit({"explicit": True}) is True

    def test_explicit_tag(self):
        assert _is_hifi_explicit({"mediaMetadata": {"tags": ["EXPLICIT"]}}) is True

    def test_not_explicit(self):
        assert _is_hifi_explicit({"explicit": False}) is False

    def test_not_a_dict(self):
        assert _is_hifi_explicit(None) is False


class TestFormatHifiTrackTitle:
    def test_title_only(self):
        assert _format_hifi_track_title({"title": "Song"}) == "Song"

    def test_title_with_version(self):
        result = _format_hifi_track_title({"title": "Song", "version": "Remix"})
        assert result == "Song (Remix)"

    def test_version_in_title(self):
        result = _format_hifi_track_title({"title": "Song (Remix)", "version": "Remix"})
        assert result == "Song (Remix)"

    def test_empty_title(self):
        assert _format_hifi_track_title({"title": ""}) == ""

    def test_not_a_dict(self):
        assert _format_hifi_track_title(None) == ""


class TestExtractHifiAlbumTrackTitles:
    def test_extracts_titles(self):
        payload = {
            "data": {
                "items": [
                    {"type": "track", "item": {"title": "Track 1"}},
                    {"type": "track", "item": {"title": "Track 2"}},
                ]
            }
        }
        result = _extract_hifi_album_track_titles(payload)
        assert result == ["Track 1", "Track 2"]

    def test_respects_limit(self):
        items = [{"type": "track", "item": {"title": f"Track {i}"}} for i in range(50)]
        payload = {"data": {"items": items}}
        result = _extract_hifi_album_track_titles(payload, limit=5)
        assert len(result) == 5

    def test_empty_payload(self):
        assert _extract_hifi_album_track_titles({}) == []


class TestHasExplicitMarker:
    def test_bracket_explicit(self):
        assert _has_explicit_marker("Song [Explicit]") is True

    def test_paren_explicit(self):
        assert _has_explicit_marker("Song (Explicit)") is True

    def test_case_insensitive(self):
        assert _has_explicit_marker("Song [explicit]") is True

    def test_no_marker(self):
        assert _has_explicit_marker("Clean Song") is False


class TestScoreExplicitAlignment:
    def test_both_explicit(self):
        assert _score_explicit_alignment(True, True) == 0.02

    def test_mismatch(self):
        assert _score_explicit_alignment(True, False) == -0.02

    def test_both_clean(self):
        assert _score_explicit_alignment(False, False) == 0.0


class TestScoreAlbumTrackTitleAlignment:
    def test_perfect_match(self):
        source = ["Track 1", "Track 2", "Track 3"]
        candidate = ["Track 1", "Track 2", "Track 3"]
        assert _score_album_track_title_alignment(source, candidate) == 0.03

    def test_partial_match(self):
        source = ["Track 1", "Track 2", "Track 3"]
        candidate = ["Track 1", "Different", "Track 3"]
        assert _score_album_track_title_alignment(source, candidate) == 0.015

    def test_no_match(self):
        source = ["A", "B", "C"]
        candidate = ["X", "Y", "Z"]
        assert _score_album_track_title_alignment(source, candidate) == 0.0

    def test_too_few_tracks(self):
        assert _score_album_track_title_alignment(["A"], ["B"]) == 0.0


class TestScoreArtistCandidateName:
    def test_exact_match(self):
        assert _score_artist_candidate_name("The Beatles", "The Beatles") == 0.96

    def test_partial_match(self):
        score = _score_artist_candidate_name("The Beatles", "Beatles")
        assert score == 0.78

    def test_no_match(self):
        assert _score_artist_candidate_name("Artist A", "Artist B") == 0.0


class TestExtractAlbumCandidateArtistNames:
    def test_primary_artist(self):
        candidate = {"primaryArtist": {"name": "Main Artist"}}
        assert _extract_album_candidate_artist_names(candidate) == ["Main Artist"]

    def test_artists_list(self):
        candidate = {"artists": [{"name": "A"}, {"name": "B"}]}
        names = _extract_album_candidate_artist_names(candidate)
        assert len(names) == 2

    def test_deduplicates(self):
        candidate = {
            "primaryArtist": {"name": "Same"},
            "artists": [{"name": "Same"}]
        }
        names = _extract_album_candidate_artist_names(candidate)
        assert len(names) == 1


class TestScoreAlbumCandidateArtistAlignment:
    def test_exact_artist_match(self):
        score = _score_album_candidate_artist_alignment("The Beatles", ["The Beatles"])
        assert score == 0.04

    def test_partial_artist_match(self):
        score = _score_album_candidate_artist_alignment("The Beatles", ["Beatles"])
        assert score == 0.02

    def test_no_match(self):
        assert _score_album_candidate_artist_alignment("A", ["B"]) == 0.0


class TestScoreAlbumCandidateTitle:
    def test_exact_title_match(self):
        score = _score_album_candidate_title("Album", "Album")
        assert score == 0.93

    def test_with_track_count_match(self):
        score = _score_album_candidate_title("Album", "Album", library_track_count=10, candidate_track_count=10)
        assert score > 0.93

    def test_partial_match(self):
        score = _score_album_candidate_title("Album Deluxe", "Album")
        assert score == 0.78

    def test_no_match(self):
        assert _score_album_candidate_title("Album A", "Album B") == 0.0


class TestScoreTrackCandidatePayload:
    def test_exact_title_match(self):
        track_row = {"title": "Song", "track_number": 1, "disc_number": 1}
        candidate = {"title": "Song", "trackNumber": 1, "volumeNumber": 1}
        score = _score_track_candidate_payload(track_row, candidate)
        assert score >= 0.90

    def test_with_track_number_bonus(self):
        track_row = {"title": "Song", "track_number": 3}
        candidate = {"title": "Song", "trackNumber": 3}
        score = _score_track_candidate_payload(track_row, candidate)
        assert score > 0.90

    def test_no_match(self):
        track_row = {"title": "Song A"}
        candidate = {"title": "Song B"}
        assert _score_track_candidate_payload(track_row, candidate) == 0.0


class TestSerializeMatchVariants:
    def test_serializes_variants(self):
        rows = [
            {"format": "flac", "bitrate": 1411, "path": "/path/1"},
            {"format": "mp3", "bitrate": 320, "path": "/path/2"},
        ]
        result = _serialize_match_variants(rows)
        assert len(result) == 2
        assert result[0]["format"] == "flac"

    def test_deduplicates(self):
        rows = [
            {"format": "flac", "bitrate": 1411, "path": "/path/1"},
            {"format": "flac", "bitrate": 1411, "path": "/path/1"},
        ]
        result = _serialize_match_variants(rows)
        assert len(result) == 1

    def test_empty_rows(self):
        assert _serialize_match_variants([]) == []
        assert _serialize_match_variants(None) == []
