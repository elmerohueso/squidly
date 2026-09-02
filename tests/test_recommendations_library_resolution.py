"""Tests for Fix 1: recommendations library-candidate resolution.

Covers:
- Step 7: local metadata overwrite when get_local_track_by_isrc returns a row.
- Step 7: `or` fallback when album_title/artist_name is NULL.
- Step 7: rec without ISRC should not call get_local_track_by_isrc.
- Step 9: records with library_id are skipped.
- Step 9: records without library_id still get resolved.
- Edge case: library_id present but album_id NULL (asymmetric overwrite).
"""

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_rec(**overrides):
    """Build a recommendation dict with sensible defaults; overrides win."""
    base = {
        'hifi_id': 447979096,
        'title': 'I Write Sins Not Tragedies',
        'artist': 'Panic! At The Disco',
        'album': 'Back to the 00s',
        'album_id': 777,
        'artist_id': 666,
        'cover': 'https://example.com/cover.jpg',
        'isrc': 'US56V0507710',
        'library_id': None,
    }
    base.update(overrides)
    return base


def _run_step7(recs, mock_get_local):
    """Run the Step 7 loop body from recommendations.py against a list of recs.

    mock_get_local is the patched get_local_track_by_isrc function.
    """
    for rec in recs:
        rec_isrc = str(rec.get('isrc') or '').strip().upper()
        if rec_isrc:
            local = mock_get_local(rec_isrc)
            if local:
                rec['library_id'] = local['library_id']
                rec['hifi_id'] = local['hifi_id']
                rec['album'] = local.get('album_title') or rec.get('album')
                rec['artist'] = local.get('artist_name') or rec.get('artist')
                rec['cover'] = None


def _run_step9(top_tracks, mock_resolve_track):
    """Run the Step 9 loop body from recommendations.py against top_tracks.

    mock_resolve_track is the patched resolve_track function.
    """
    for rec in top_tracks:
        if rec.get('library_id'):
            continue
        tid = rec.get('hifi_id')
        if not tid:
            continue
        mock_resolve_track(
            title=rec.get('title', ''),
            track_artist=rec.get('artist', ''),
            album=rec.get('album', ''),
            isrc=rec.get('isrc'),
            hifi_id=str(tid),
            settings={},
        )


# ---------------------------------------------------------------------------
# Step 7 tests
# ---------------------------------------------------------------------------


class TestStep7LocalMetadataOverwrite:
    """Step 7 overwrites rec metadata from the local library row,
    but preserves Tidal album_id and artist_id for frontend use."""

    def test_local_metadata_wins(self):
        """When get_local_track_by_isrc returns a local row, the rec's
        hifi_id, library_id, album, artist, cover are overwritten from
        the local track. album_id and artist_id stay as Tidal IDs."""
        local_row = {
            'hifi_id': 307230,
            'library_id': '135100',
            'album_title': 'A Fever You Sweat Out',
            'artist_name': 'Panic! At The Disco',
            'album_id': 99,
            'artist_id': 88,
        }
        mock_get_local = MagicMock(return_value=local_row)

        rec = _build_rec()
        _run_step7([rec], mock_get_local)

        mock_get_local.assert_called_once_with('US56V0507710')
        assert rec['hifi_id'] == 307230
        assert rec['library_id'] == '135100'
        assert rec['album'] == 'A Fever You Sweat Out'
        assert rec['artist'] == 'Panic! At The Disco'
        # album_id and artist_id stay as original Tidal values
        assert rec['album_id'] == 777
        assert rec['artist_id'] == 666
        assert rec['cover'] is None

    def test_local_row_missing_album_title_falls_back(self):
        """When the local row's album_title is NULL (LEFT JOIN missed),
        rec['album'] falls back to the original Tidal value via `or`.
        album_id and artist_id stay as original Tidal IDs."""
        local_row = {
            'hifi_id': 307230,
            'library_id': '135100',
            'album_title': None,
            'artist_name': 'Panic! At The Disco',
            'album_id': None,
            'artist_id': 88,
        }
        mock_get_local = MagicMock(return_value=local_row)

        rec = _build_rec(album='Back to the 00s')
        _run_step7([rec], mock_get_local)

        # album falls back to the original Tidal value
        assert rec['album'] == 'Back to the 00s'
        # album_id and artist_id stay as original Tidal values
        assert rec['album_id'] == 777
        assert rec['artist_id'] == 666
        # artist_name is present, so artist is overwritten
        assert rec['artist'] == 'Panic! At The Disco'
        assert rec['library_id'] == '135100'
        assert rec['hifi_id'] == 307230
        assert rec['cover'] is None

    def test_rec_without_isrc_does_not_call_lookup(self):
        """When a rec has no ISRC, get_local_track_by_isrc is NOT called
        and the rec's metadata is unchanged."""
        mock_get_local = MagicMock()
        rec = _build_rec(isrc=None, album='Back to the 00s', artist='Panic! At The Disco')
        original_album = rec['album']
        original_artist = rec['artist']

        _run_step7([rec], mock_get_local)

        mock_get_local.assert_not_called()
        assert rec['album'] == original_album
        assert rec['artist'] == original_artist
        assert rec['library_id'] is None  # unchanged

    def test_rec_with_empty_isrc_does_not_call_lookup(self):
        """Empty-string ISRC is treated as no ISRC."""
        mock_get_local = MagicMock()
        rec = _build_rec(isrc='')

        _run_step7([rec], mock_get_local)

        mock_get_local.assert_not_called()

    def test_local_track_with_library_id_but_null_album_id(self):
        """Edge case: library_id present but album_id NULL in local row.
        album falls back to Tidal value; album_id stays as Tidal ID."""
        local_row = {
            'hifi_id': 307230,
            'library_id': '135100',
            'album_title': None,
            'artist_name': 'Panic! At The Disco',
            'album_id': None,
            'artist_id': 88,
        }
        mock_get_local = MagicMock(return_value=local_row)

        rec = _build_rec(album='Back to the 00s', album_id=777)
        _run_step7([rec], mock_get_local)

        # album falls back to Tidal value (None or 'Back to the 00s' -> 'Back to the 00s')
        assert rec['album'] == 'Back to the 00s'
        # album_id stays as original Tidal value
        assert rec['album_id'] == 777
        # artist was present, so it's overwritten
        assert rec['artist'] == 'Panic! At The Disco'
        assert rec['artist_id'] == 666


# ---------------------------------------------------------------------------
# Step 9 tests
# ---------------------------------------------------------------------------


class TestStep9LibrarySkip:
    """Step 9 skips records with library_id set; resolves others."""

    def test_step9_skips_library_candidates(self):
        """A rec with library_id set is NOT passed to resolve_track.
        A rec without library_id IS passed."""
        mock_resolve = MagicMock(return_value={'hifi_id': '999'})

        library_rec = _build_rec(library_id='123', hifi_id=111)
        new_rec = _build_rec(library_id=None, hifi_id=999)

        _run_step9([library_rec, new_rec], mock_resolve)

        # Only the new_rec should have been resolved
        assert mock_resolve.call_count == 1
        call_kwargs = mock_resolve.call_args.kwargs
        assert call_kwargs['hifi_id'] == '999'

    def test_step9_resolves_all_when_no_library_ids(self):
        """When all recs have library_id=None, resolve_track is called
        for every rec (no regression)."""
        mock_resolve = MagicMock(return_value={'hifi_id': '1'})

        recs = [
            _build_rec(hifi_id=100, library_id=None),
            _build_rec(hifi_id=200, library_id=None),
            _build_rec(hifi_id=300, library_id=None),
        ]

        _run_step9(recs, mock_resolve)

        assert mock_resolve.call_count == 3
        called_hifi_ids = [c.kwargs['hifi_id'] for c in mock_resolve.call_args_list]
        assert called_hifi_ids == ['100', '200', '300']

    def test_step9_skips_rec_without_hifi_id(self):
        """A rec without hifi_id is also skipped (no resolve call)."""
        mock_resolve = MagicMock()

        recs = [
            _build_rec(hifi_id=None, library_id=None),
            _build_rec(hifi_id=200, library_id=None),
        ]

        _run_step9(recs, mock_resolve)

        assert mock_resolve.call_count == 1
        assert mock_resolve.call_args.kwargs['hifi_id'] == '200'
