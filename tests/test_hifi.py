"""Tests for HiFi metadata parsing — album type splitting for artist explore page.

Tests cover:
- _build_hifi_album_object_from_artist_item includes type field
- _get_hifi_album_dedupe_key uses type in dedup key
- get_hifi_artist_object splits albums by type into albums/singles/eps
"""

import json
import os
from unittest.mock import MagicMock, patch

# Patch logging before importing squidly modules to avoid /logs PermissionError
os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")

from squidly.services.hifi import (
    _build_hifi_album_object_from_artist_item,
    _get_hifi_album_dedupe_key,
    _get_hifi_audio_quality_rank,
    get_hifi_artist_object,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_album_item(overrides=None):
    """Build a minimal raw album item as returned by the HiFi artist endpoint."""
    item = {
        'id': 1001,
        'type': 'ALBUM',
        'title': 'Test Album',
        'version': '',
        'cover': 'cover-uuid-1234',
        'releaseDate': '2024-06-15',
        'numberOfTracks': 10,
        'numberOfVolumes': 1,
        'explicit': False,
        'duration': 3600,
        'copyright': '2024 Test Label',
        'url': 'https://tidal.com/browse/album/1001',
        'artists': [{'id': 42, 'name': 'Test Artist', 'picture': 'pic-uuid'}],
    }
    if overrides:
        item.update(overrides)
    return item


def _make_minimal_artist_response(album_items, track_items=None):
    """Build a minimal artist response payload suitable for mocking _fetch_hifi_artist_payload.

    The response must satisfy extract_hifi_artist_info() — at least one album item
    needs an 'artist' or 'artists' key so that _extract_hifi_artist_identity succeeds.
    """
    if track_items is None:
        track_items = []

    # Ensure at least one item carries artist identity info
    if album_items and not any(
        item.get('artist') or item.get('artists') for item in album_items
    ):
        # Inject artist info into the first item
        album_items[0]['artists'] = [{'id': 42, 'name': 'Test Artist', 'picture': 'pic-uuid'}]

    return {
        'albums': {
            'items': album_items,
        },
        'tracks': track_items,
    }


def _make_track_item(overrides=None):
    item = {
        'id': 5001,
        'title': 'Top Track',
        'version': '',
        'trackNumber': 1,
        'volumeNumber': 1,
        'duration': 240,
        'explicit': False,
        'artists': [{'id': 42, 'name': 'Test Artist', 'picture': 'pic-uuid'}],
        'album': {'id': 1001, 'title': 'Test Album', 'cover': 'cover-uuid'},
    }
    if overrides:
        item.update(overrides)
    return item


# ---------------------------------------------------------------------------
# _build_hifi_album_object_from_artist_item
# ---------------------------------------------------------------------------

class TestBuildHifiAlbumObjectFromArtistItem:

    def test_returns_empty_dict_for_non_dict(self):
        assert _build_hifi_album_object_from_artist_item(None) == {}
        assert _build_hifi_album_object_from_artist_item('string') == {}
        assert _build_hifi_album_object_from_artist_item([]) == {}

    def test_type_album(self):
        raw = _make_album_item({'type': 'ALBUM'})
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result.get('type') == 'ALBUM'
        assert result.get('id') == 1001
        assert result.get('title') == 'Test Album'

    def test_type_single(self):
        raw = _make_album_item({'type': 'SINGLE', 'id': 1002})
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result.get('type') == 'SINGLE'
        assert result.get('id') == 1002

    def test_type_ep(self):
        raw = _make_album_item({'type': 'EP', 'id': 1003})
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result.get('type') == 'EP'
        assert result.get('id') == 1003

    def test_type_none(self):
        raw = _make_album_item({'type': None, 'id': 1004})
        result = _build_hifi_album_object_from_artist_item(raw)
        # type should be None (preserved from the raw item)
        assert result.get('type') is None

    def test_type_missing(self):
        raw = _make_album_item({'id': 1005})
        del raw['type']
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result.get('type') is None

    def test_type_unknown_value(self):
        raw = _make_album_item({'type': 'COMPILATION', 'id': 1006})
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result.get('type') == 'COMPILATION'

    def test_preserves_all_normalized_fields(self):
        raw = _make_album_item()
        result = _build_hifi_album_object_from_artist_item(raw)
        assert result['id'] == raw['id']
        assert result['type'] == raw['type']
        assert result['title'] == raw['title']
        assert result['version'] == raw['version']
        assert result['releaseDate'] == raw['releaseDate']
        assert result['numberOfTracks'] == raw['numberOfTracks']
        assert result['numberOfDiscs'] == raw['numberOfVolumes']
        assert result['explicit'] == raw['explicit']
        assert result['duration'] == raw['duration']
        assert result['copyright'] == raw['copyright']
        assert result['url'] == raw['url']
        assert len(result['artists']) == 1
        assert result['artists'][0]['id'] == 42
        assert result['tracks'] == []

    def test_cover_is_formatted(self):
        raw = _make_album_item({'cover': 'cover-uuid'})
        result = _build_hifi_album_object_from_artist_item(raw)
        # Should be formatted as a Tidal image URL
        cover = result.get('cover')
        assert cover is not None
        assert 'resources.tidal.com' in cover


# ---------------------------------------------------------------------------
# _get_hifi_album_dedupe_key
# ---------------------------------------------------------------------------

class TestGetHifiAlbumDedupeKey:

    def test_returns_none_for_non_dict(self):
        assert _get_hifi_album_dedupe_key(None) is None
        assert _get_hifi_album_dedupe_key('string') is None
        assert _get_hifi_album_dedupe_key([]) is None

    def test_different_types_get_different_keys(self):
        album = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})
        single = _make_album_item({'type': 'SINGLE', 'releaseDate': '2024-01-01'})
        ep = _make_album_item({'type': 'EP', 'releaseDate': '2024-01-01'})

        key_album = _get_hifi_album_dedupe_key(album)
        key_single = _get_hifi_album_dedupe_key(single)
        key_ep = _get_hifi_album_dedupe_key(ep)

        assert key_album is not None
        assert key_single is not None
        assert key_ep is not None

        # All three should be different because type differs
        assert key_album != key_single
        assert key_album != key_ep
        assert key_single != key_ep

    def test_type_none_and_type_album_get_different_keys(self):
        none_type = _make_album_item({'type': None, 'releaseDate': '2024-01-01'})
        album_type = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})

        key_none = _get_hifi_album_dedupe_key(none_type)
        key_album = _get_hifi_album_dedupe_key(album_type)

        assert key_none != key_album

    def test_same_type_same_other_fields_get_same_key(self):
        item1 = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})
        item2 = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})

        key1 = _get_hifi_album_dedupe_key(item1)
        key2 = _get_hifi_album_dedupe_key(item2)

        assert key1 == key2

    def test_compilation_falls_into_same_key_as_album(self):
        # COMPILATION albums should dedupe differently from ALBUM when all else equal
        album = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})
        compilation = _make_album_item({'type': 'COMPILATION', 'releaseDate': '2024-01-01'})

        key_album = _get_hifi_album_dedupe_key(album)
        key_comp = _get_hifi_album_dedupe_key(compilation)

        assert key_album != key_comp

    def test_type_as_last_tuple_element(self):
        """Verify type is the last element of the dedup key tuple."""
        album = _make_album_item({'type': 'ALBUM', 'releaseDate': '2024-01-01'})
        key = _get_hifi_album_dedupe_key(album)
        assert key is not None
        # The last element should be 'ALBUM'
        assert key[-1] == 'ALBUM'

    def test_type_none_in_key(self):
        album = _make_album_item({'type': None, 'releaseDate': '2024-01-01'})
        key = _get_hifi_album_dedupe_key(album)
        assert key is not None
        assert key[-1] is None


# ---------------------------------------------------------------------------
# _get_hifi_audio_quality_rank
# ---------------------------------------------------------------------------

def test_audio_quality_rank_atmos_below_lossless():
    """Atmos is an immersive derivative; must rank below LOSSLESS for dedup correctness.

    Regression test: Tidal has multiple entries for the same album (e.g., a 1999
    LOSSLESS stereo master and a 2024 Dolby Atmos reissue). They share the dedup
    key in _get_hifi_album_dedupe_key, so the rank function must rank the Atmos
    reissue below LOSSLESS to prevent picking the Atmos entry — which has ISRCs
    the other download sources don't carry.
    """
    # --- ordering ---
    assert _get_hifi_audio_quality_rank('DOLBY_ATMOS') < _get_hifi_audio_quality_rank('LOSSLESS')
    assert _get_hifi_audio_quality_rank('LOSSLESS') < _get_hifi_audio_quality_rank('HI_RES_LOSSLESS')
    assert _get_hifi_audio_quality_rank('HIGH') < _get_hifi_audio_quality_rank('LOSSLESS')
    assert _get_hifi_audio_quality_rank('LOW') < _get_hifi_audio_quality_rank('HIGH')

    # --- exact rank values ---
    assert _get_hifi_audio_quality_rank('DOLBY_ATMOS') == 0
    assert _get_hifi_audio_quality_rank('LOW') == 1
    assert _get_hifi_audio_quality_rank('HIGH') == 2
    assert _get_hifi_audio_quality_rank('LOSSLESS') == 3
    assert _get_hifi_audio_quality_rank('HI_RES_LOSSLESS') == 4

    # --- alias spellings must rank the same ---
    assert _get_hifi_audio_quality_rank('HIRES_LOSSLESS') == _get_hifi_audio_quality_rank('HI_RES_LOSSLESS')
    assert _get_hifi_audio_quality_rank('HIRES_LOSSLESS') == 4

    # --- unknown / missing values default to 0 ---
    assert _get_hifi_audio_quality_rank('UNKNOWN') == 0
    assert _get_hifi_audio_quality_rank('') == 0
    assert _get_hifi_audio_quality_rank(None) == 0

    # --- case insensitivity (function calls .upper()) ---
    assert _get_hifi_audio_quality_rank('dolby_atmos') == 0
    assert _get_hifi_audio_quality_rank('lossless') == 3
    assert _get_hifi_audio_quality_rank('hi_res_lossless') == 4
    assert _get_hifi_audio_quality_rank('Lossless') == 3

    # --- whitespace tolerance (function calls .strip()) ---
    assert _get_hifi_audio_quality_rank('  LOSSLESS  ') == 3
    assert _get_hifi_audio_quality_rank(' DOLBY_ATMOS ') == 0
    assert _get_hifi_audio_quality_rank('\tHI_RES_LOSSLESS\n') == 4


def test_album_dedup_prefers_lossless_over_atmos_reissue():
    """Regression: a 2024 Atmos reissue must not replace the 1999 LOSSLESS original.

    Both albums share the dedup key (title, version, releaseDate, numberOfTracks,
    numberOfDiscs, artists, explicit, type). After the fix, the LOSSLESS one wins
    because _get_hifi_audio_quality_rank('LOSSLESS') > _get_hifi_audio_quality_rank('DOLBY_ATMOS').
    """
    lossless_album = _make_album_item({
        'id': 1001,
        'title': 'Rage Against the Machine',
        'releaseDate': '1992-11-03',
        'numberOfTracks': 10,
        'numberOfVolumes': 1,
        'mediaMetadata': {'tags': ['LOSSLESS']},
    })
    atmos_reissue = _make_album_item({
        'id': 9999,
        'title': 'Rage Against the Machine',
        'releaseDate': '1992-11-03',
        'numberOfTracks': 10,
        'numberOfVolumes': 1,
        'mediaMetadata': {'tags': ['DOLBY_ATMOS']},
    })

    # Verify both produce the same dedup key
    lossless_obj = _build_hifi_album_object_from_artist_item(lossless_album)
    atmos_obj = _build_hifi_album_object_from_artist_item(atmos_reissue)
    assert _get_hifi_album_dedupe_key(lossless_obj) == _get_hifi_album_dedupe_key(atmos_obj)

    # Verify the quality extraction differs
    assert lossless_obj['maxAudioQuality'] == 'LOSSLESS'
    assert atmos_obj['maxAudioQuality'] == 'DOLBY_ATMOS'

    # Run the dedup logic (mirrors get_hifi_artist_object lines 807-820)
    album_objects = [lossless_obj, atmos_obj]
    deduped_albums = {}
    for album_object in album_objects:
        key = _get_hifi_album_dedupe_key(album_object)
        existing = deduped_albums.get(key)
        if existing is None:
            deduped_albums[key] = album_object
            continue
        current_rank = _get_hifi_audio_quality_rank(album_object.get('maxAudioQuality'))
        existing_rank = _get_hifi_audio_quality_rank(existing.get('maxAudioQuality'))
        if current_rank > existing_rank:
            deduped_albums[key] = album_object

    survivors = list(deduped_albums.values())
    assert len(survivors) == 1
    assert survivors[0]['id'] == 1001  # LOSSLESS original wins
    assert survivors[0]['maxAudioQuality'] == 'LOSSLESS'


def test_album_dedup_prefers_hires_over_lossless():
    """HI_RES_LOSSLESS should beat LOSSLESS in dedup (both are preferred over Atmos)."""
    hires_album = _make_album_item({
        'id': 2001,
        'title': 'Some Album',
        'releaseDate': '2024-01-01',
        'mediaMetadata': {'tags': ['HIRES_LOSSLESS']},
    })
    lossless_album = _make_album_item({
        'id': 2002,
        'title': 'Some Album',
        'releaseDate': '2024-01-01',
        'mediaMetadata': {'tags': ['LOSSLESS']},
    })

    hires_obj = _build_hifi_album_object_from_artist_item(hires_album)
    lossless_obj = _build_hifi_album_object_from_artist_item(lossless_album)
    assert _get_hifi_album_dedupe_key(hires_obj) == _get_hifi_album_dedupe_key(lossless_obj)

    # Dedup: LOSSLESS first, then HI_RES — HI_RES should replace it
    deduped = {}
    for album_object in [lossless_obj, hires_obj]:
        key = _get_hifi_album_dedupe_key(album_object)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = album_object
            continue
        current_rank = _get_hifi_audio_quality_rank(album_object.get('maxAudioQuality'))
        existing_rank = _get_hifi_audio_quality_rank(existing.get('maxAudioQuality'))
        if current_rank > existing_rank:
            deduped[key] = album_object

    survivors = list(deduped.values())
    assert len(survivors) == 1
    assert survivors[0]['id'] == 2001  # HI_RES_LOSSLESS wins


# ---------------------------------------------------------------------------
# get_hifi_artist_object — splitting and backward compatibility
# ---------------------------------------------------------------------------

class TestGetHifiArtistObject:

    # ---- happy path ----

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_splits_by_type(self, mock_fetch):
        """Albums, singles, and EPs are each placed in the correct list."""
        albums = [
            _make_album_item({'id': 1, 'type': 'ALBUM', 'title': 'Album A'}),
            _make_album_item({'id': 2, 'type': 'SINGLE', 'title': 'Single A'}),
            _make_album_item({'id': 3, 'type': 'EP', 'title': 'EP A'}),
            _make_album_item({'id': 4, 'type': 'ALBUM', 'title': 'Album B'}),
            _make_album_item({'id': 5, 'type': 'SINGLE', 'title': 'Single B'}),
            _make_album_item({'id': 6, 'type': 'EP', 'title': 'EP B'}),
        ]
        tracks = [_make_track_item({'id': 101})]
        mock_fetch.return_value = _make_minimal_artist_response(albums, tracks)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 2
        assert artist['albums'][0]['type'] == 'ALBUM'
        assert artist['albums'][1]['type'] == 'ALBUM'

        assert len(artist['singles']) == 2
        assert artist['singles'][0]['type'] == 'SINGLE'
        assert artist['singles'][1]['type'] == 'SINGLE'

        assert len(artist['eps']) == 2
        assert artist['eps'][0]['type'] == 'EP'
        assert artist['eps'][1]['type'] == 'EP'

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_top_tracks_unchanged(self, mock_fetch):
        """Top tracks are still present and unaffected by album splitting."""
        albums = [_make_album_item({'id': 1, 'type': 'ALBUM'})]
        tracks = [
            _make_track_item({'id': 201, 'title': 'Track 1'}),
            _make_track_item({'id': 202, 'title': 'Track 2'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(albums, tracks)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['top_tracks']) == 2
        assert artist['top_tracks'][0]['id'] == 201
        assert artist['top_tracks'][1]['id'] == 202

    # ---- backward compatibility ----

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_artist_albums_key_still_exists(self, mock_fetch):
        """The 'albums' key in artist still contains only ALBUM-type items."""
        items = [
            _make_album_item({'id': 1, 'type': 'ALBUM', 'title': 'Album'}),
            _make_album_item({'id': 2, 'type': 'SINGLE', 'title': 'Single'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert 'albums' in artist
        assert len(artist['albums']) == 1
        assert artist['albums'][0]['type'] == 'ALBUM'

    # ---- edge cases ----

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_type_none_falls_to_albums(self, mock_fetch):
        """Albums with type=None end up in the albums list."""
        items = [
            _make_album_item({'id': 1, 'type': None}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 1
        assert artist['albums'][0]['id'] == 1
        assert len(artist['singles']) == 0
        assert len(artist['eps']) == 0

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_type_missing_falls_to_albums(self, mock_fetch):
        """Albums with no type key at all end up in the albums list."""
        raw = _make_album_item({'id': 1})
        del raw['type']
        items = [raw]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 1
        assert artist['albums'][0]['id'] == 1

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_compilation_type_falls_to_albums(self, mock_fetch):
        """COMPILATION type albums fall into the albums list (not singles/eps)."""
        items = [
            _make_album_item({'id': 1, 'type': 'COMPILATION'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 1
        assert artist['albums'][0]['type'] == 'COMPILATION'
        assert len(artist['singles']) == 0
        assert len(artist['eps']) == 0

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_empty_singles_and_eps(self, mock_fetch):
        """Artist with only albums returns empty singles and eps arrays."""
        items = [
            _make_album_item({'id': 1, 'type': 'ALBUM', 'title': 'Album One', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 2, 'type': 'ALBUM', 'title': 'Album Two', 'releaseDate': '2024-06-15'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 2
        assert artist['singles'] == []
        assert artist['eps'] == []

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_only_singles_no_albums_or_eps(self, mock_fetch):
        """Artist with only singles — albums and eps are empty."""
        items = [
            _make_album_item({'id': 1, 'type': 'SINGLE', 'title': 'Single A', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 2, 'type': 'SINGLE', 'title': 'Single B', 'releaseDate': '2024-06-15'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert artist['albums'] == []
        assert len(artist['singles']) == 2
        assert artist['eps'] == []

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_only_eps_no_albums_or_singles(self, mock_fetch):
        """Artist with only EPs — albums and singles are empty."""
        items = [
            _make_album_item({'id': 1, 'type': 'EP', 'title': 'EP A', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 2, 'type': 'EP', 'title': 'EP B', 'releaseDate': '2024-06-15'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert artist['albums'] == []
        assert artist['singles'] == []
        assert len(artist['eps']) == 2

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_all_types_mixed(self, mock_fetch):
        """A realistic mix of all types is split correctly."""
        items = [
            _make_album_item({'id': 1, 'type': 'ALBUM', 'title': 'Album 1', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 2, 'type': 'SINGLE', 'title': 'Single 1', 'releaseDate': '2024-02-01'}),
            _make_album_item({'id': 3, 'type': 'EP', 'title': 'EP 1', 'releaseDate': '2024-03-01'}),
            _make_album_item({'id': 4, 'type': 'ALBUM', 'title': 'Album 2', 'releaseDate': '2024-04-01'}),
            _make_album_item({'id': 5, 'type': 'SINGLE', 'title': 'Single 2', 'releaseDate': '2024-05-01'}),
            _make_album_item({'id': 6, 'type': 'EP', 'title': 'EP 2', 'releaseDate': '2024-06-01'}),
            _make_album_item({'id': 7, 'type': 'COMPILATION', 'title': 'Comp', 'releaseDate': '2024-07-01'}),
            _make_album_item({'id': 8, 'type': None, 'title': 'No Type', 'releaseDate': '2024-08-01'}),
        ]
        tracks = [_make_track_item({'id': 301})]
        mock_fetch.return_value = _make_minimal_artist_response(items, tracks)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['albums']) == 4   # 2 ALBUM + 1 COMPILATION + 1 None
        assert len(artist['singles']) == 2
        assert len(artist['eps']) == 2
        assert len(artist['top_tracks']) == 1

        # Verify each list has correct types
        for a in artist['albums']:
            assert a['type'] in ('ALBUM', 'COMPILATION', None)
        for s in artist['singles']:
            assert s['type'] == 'SINGLE'
        for e in artist['eps']:
            assert e['type'] == 'EP'

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_empty_artist_response(self, mock_fetch):
        """Empty artist response returns empty result."""
        mock_fetch.return_value = {}

        result = get_hifi_artist_object('42')
        assert result == {}

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_no_albums_only_tracks(self, mock_fetch):
        """Artist with only top tracks and no albums."""
        tracks = [_make_track_item({'id': 401})]
        mock_fetch.return_value = _make_minimal_artist_response([], tracks)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert artist['albums'] == []
        assert artist['singles'] == []
        assert artist['eps'] == []
        assert len(artist['top_tracks']) == 1

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_album_type_case_sensitivity(self, mock_fetch):
        """Mixed case types like 'single', 'Single', 'ep', 'Ep' should still match."""
        items = [
            _make_album_item({'id': 1, 'type': 'single', 'title': 'Single A', 'releaseDate': '2024-01-01'}),   # lowercase
            _make_album_item({'id': 2, 'type': 'Single', 'title': 'Single B', 'releaseDate': '2024-02-01'}),   # capitalized
            _make_album_item({'id': 3, 'type': 'ep', 'title': 'EP A', 'releaseDate': '2024-03-01'}),        # lowercase
            _make_album_item({'id': 4, 'type': 'EP', 'title': 'EP B', 'releaseDate': '2024-04-01'}),        # uppercase
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        assert len(artist['singles']) == 2
        assert len(artist['eps']) == 2

    # ---- dedup across type groups ----

    @patch('squidly.services.hifi._fetch_hifi_artist_payload')
    def test_dedup_within_type_group(self, mock_fetch):
        """Deduplication still works within each type group."""
        # Two identical ALBUM items should dedup to one
        items = [
            _make_album_item({'id': 1, 'type': 'ALBUM', 'title': 'Same Album', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 2, 'type': 'ALBUM', 'title': 'Same Album', 'releaseDate': '2024-01-01'}),
            _make_album_item({'id': 3, 'type': 'SINGLE', 'title': 'Same Album', 'releaseDate': '2024-01-01'}),
        ]
        mock_fetch.return_value = _make_minimal_artist_response(items)

        result = get_hifi_artist_object('42')
        artist = result.get('artist', {})

        # Two ALBUMS with same metadata + type should dedup to one
        assert len(artist['albums']) == 1
        # The SINGLE with same metadata but different type stays separate
        assert len(artist['singles']) == 1
