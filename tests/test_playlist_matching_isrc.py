"""Tests for Fix 2: download pipeline ISRC check in _lookup_track_metadata.

Covers:
- ISRC match returns rows immediately.
- ISRC no match falls through to title+artist+album query.
- ISRC=None / '' / whitespace-only are treated as no ISRC.
- ISRC is uppercased and trimmed before the query.
- ISRC query WHERE clause guards against NULL/empty library_id.
- ISRC query SELECT includes fields the download pipeline consumes.
"""

import os
from unittest.mock import MagicMock

os.environ.setdefault("SQUIDLY_LOG_DIR_OVERRIDE", "/tmp/squidly_test_logs")

from squidly.services.playlist_matching import _lookup_track_metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cursor():
    """Build a MagicMock cursor with fetchall returning [] by default."""
    cur = MagicMock()
    cur.fetchall.return_value = []
    return cur


def _executed_sqls(cur):
    """Return a list of (sql, params) tuples from every cur.execute call."""
    return [call.args for call in cur.execute.call_args_list]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLookupTrackMetadataIsrc:
    """Tests for the ISRC short-circuit in _lookup_track_metadata."""

    def test_isrc_match_returns_rows(self):
        """When the ISRC query returns rows, the function returns them
        immediately without running title+artist queries."""
        cur = _make_cursor()
        isrc_rows = [
            {'title': 'I Write Sins', 'artist': 'Panic!', 'album': 'Fever',
             'format': 'flac', 'bitrate': 1411, 'path': 'P/F/file.flac'}
        ]
        cur.fetchall.return_value = isrc_rows

        result = _lookup_track_metadata(
            cur,
            title='I Write Sins Not Tragedies',
            artist='Panic! At The Disco',
            album='Back to the 00s [Explicit]',
            isrc='US56V0507710',
        )

        # Only one execute call (the ISRC query)
        assert cur.execute.call_count == 1
        sql, params = _executed_sqls(cur)[0]
        assert 'UPPER(TRIM(tracks.isrc))' in sql
        assert "library_id IS NOT NULL" in sql
        assert "library_id <> ''" in sql
        assert params == ('US56V0507710',)
        assert result == isrc_rows

    def test_isrc_no_match_falls_through(self):
        """When the ISRC query returns 0 rows, the function falls through
        to the title+artist+album query."""
        cur = _make_cursor()

        # First call (ISRC) -> empty; second call (title+artist+album) -> rows
        title_rows = [
            {'title': 'I Write Sins', 'artist': 'Panic!', 'album': 'Fever',
             'format': 'flac', 'bitrate': 1411, 'path': 'P/F/file.flac'}
        ]
        cur.fetchall.side_effect = [[], title_rows]

        result = _lookup_track_metadata(
            cur,
            title='I Write Sins Not Tragedies',
            artist='Panic! At The Disco',
            album='Back to the 00s [Explicit]',
            isrc='US56V0507710',
        )

        # ISRC query + title+artist+album query = 2 calls
        assert cur.execute.call_count == 2
        assert result == title_rows

    def test_isrc_none_skips_isrc_query(self):
        """When isrc=None, the ISRC query is NOT executed; the
        title+artist+album query runs instead."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc=None,
        )

        # No ISRC query; only title+artist+album and title+artist fallback
        for sql, _params in _executed_sqls(cur):
            assert 'UPPER(TRIM(tracks.isrc))' not in sql
        assert cur.execute.call_count == 2

    def test_isrc_empty_string_skips_isrc_query(self):
        """When isrc='', the ISRC query is NOT executed."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc='',
        )

        for sql, _params in _executed_sqls(cur):
            assert 'UPPER(TRIM(tracks.isrc))' not in sql
        assert cur.execute.call_count == 2

    def test_isrc_whitespace_only_skips_isrc_query(self):
        """When isrc='   ' (whitespace only), the ISRC query is NOT executed
        because strip() yields an empty string."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc='   ',
        )

        for sql, _params in _executed_sqls(cur):
            assert 'UPPER(TRIM(tracks.isrc))' not in sql
        assert cur.execute.call_count == 2

    def test_isrc_is_uppercased_and_trimmed(self):
        """The ISRC parameter is uppercased and trimmed before being
        passed to the SQL query."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc=' us56v0507710 ',
        )

        # The first execute call is the ISRC query
        sql, params = _executed_sqls(cur)[0]
        assert 'UPPER(TRIM(tracks.isrc))' in sql
        assert params == ('US56V0507710',)

    def test_isrc_query_guards_null_library_id(self):
        """The ISRC query's WHERE clause contains both guards:
        library_id IS NOT NULL AND library_id <> ''
        (verifying the SQL contract — NULL/empty library_id rows are excluded)."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc='US56V0507710',
        )

        sql, _params = _executed_sqls(cur)[0]
        assert "library_id IS NOT NULL" in sql
        assert "library_id <> ''" in sql

    def test_isrc_query_select_shape(self):
        """The ISRC query SELECT includes the fields the download pipeline
        consumes: tracks.title, artists.name AS artist, albums.title AS album,
        tracks.format, tracks.bitrate, tracks.path."""
        cur = _make_cursor()
        cur.fetchall.return_value = []

        _lookup_track_metadata(
            cur,
            title='Title',
            artist='Artist',
            album='Album',
            isrc='US56V0507710',
        )

        sql, _params = _executed_sqls(cur)[0]
        assert 'tracks.title' in sql
        assert 'artists.name AS artist' in sql
        assert 'albums.title AS album' in sql
        assert 'tracks.format' in sql
        assert 'tracks.bitrate' in sql
        assert 'tracks.path' in sql
