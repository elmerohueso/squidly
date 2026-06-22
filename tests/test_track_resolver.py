"""Tests for squidly/services/track_resolver.py — pure helper functions."""

import pytest

import squidly.services.track_resolver as tr


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_album_cache():
    """Clear the module-level album cache before each test."""
    tr._album_cache.clear()
    yield


# ── 1. _parse_release_year ─────────────────────────────────────────────────

class TestParseReleaseYear:
    def test_valid_full_date(self):
        assert tr._parse_release_year('1996-03-15') == '1996'

    def test_valid_date_2018(self):
        assert tr._parse_release_year('2018-01-01') == '2018'

    def test_none_input(self):
        assert tr._parse_release_year(None) == '9999'

    def test_empty_string(self):
        assert tr._parse_release_year('') == '9999'

    def test_non_string_int(self):
        assert tr._parse_release_year(1996) == '9999'

    def test_short_string(self):
        assert tr._parse_release_year('96') == '9999'


# ── 2. _has_live_version_indicator ─────────────────────────────────────────

class TestHasLiveVersionIndicator:
    def test_live_in_version_string(self):
        track = {'version': 'Live at Madison Square Garden'}
        assert tr._has_live_version_indicator(track) is True

    def test_unplugged_version(self):
        track = {'version': 'Unplugged'}
        assert tr._has_live_version_indicator(track) is True

    def test_acoustic_version(self):
        track = {'version': 'Acoustic Version'}
        assert tr._has_live_version_indicator(track) is True

    def test_concert_version(self):
        track = {'version': 'Concert Recording'}
        assert tr._has_live_version_indicator(track) is True

    def test_none_version(self):
        track = {'version': None}
        assert tr._has_live_version_indicator(track) is False

    def test_empty_version(self):
        track = {'version': ''}
        assert tr._has_live_version_indicator(track) is False

    def test_remastered_not_live(self):
        track = {'version': 'Remastered'}
        assert tr._has_live_version_indicator(track) is False

    def test_missing_version_key(self):
        track = {}
        assert tr._has_live_version_indicator(track) is False


# ── 3. _has_deluxe_indicator ───────────────────────────────────────────────

class TestHasDeluxeIndicator:
    def test_deluxe_in_album_title(self):
        assert tr._has_deluxe_indicator('Friction Baby (Deluxe Edition)') is True

    def test_remaster_in_version(self):
        assert tr._has_deluxe_indicator('Good', version='Remastered') is True

    def test_special_edition(self):
        assert tr._has_deluxe_indicator('Special Edition Album') is True

    def test_no_deluxe_indicator_plain_album(self):
        assert tr._has_deluxe_indicator('Friction Baby', version='') is False

    def test_greatest_hits_not_deluxe(self):
        # 'greatest' is a compilation keyword, not a deluxe keyword
        assert tr._has_deluxe_indicator('Greatest Hits') is False


# ── 4. _is_compilation_from_search_data ───────────────────────────────────

class TestIsCompilationFromSearchData:
    def test_keyword_greatest_hits(self):
        item = {
            'title': 'Desperately Wanting',
            'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 1,
                'title': 'Greatest Hits',
                'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            },
        }
        assert tr._is_compilation_from_search_data(item) is True

    def test_va_match_album_artists(self):
        item = {
            'title': 'Desperately Wanting',
            'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 2,
                'title': '90s Rock',
                'artists': [{'id': 99999, 'name': 'Various Artists'}],
            },
        }
        assert tr._is_compilation_from_search_data(item) is True

    def test_va_in_album_artists(self):
        item = {
            'title': 'Desperately Wanting',
            'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 3,
                'title': '90s Rock',
                'artists': [
                    {'id': 99999, 'name': 'Various Artists'},
                    {'id': 99998, 'name': 'Various Artists'},
                ],
            },
        }
        assert tr._is_compilation_from_search_data(item) is True

    def test_artist_match_no_compilation(self):
        # Track artist matches album artist — not a compilation
        item = {
            'title': 'Desperately Wanting',
            'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 4,
                'title': 'Friction Baby',
                'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            },
        }
        assert tr._is_compilation_from_search_data(item) is False

    def test_best_of_keyword(self):
        item = {
            'title': 'Song',
            'artists': [{'id': 1, 'name': 'Artist'}],
            'album': {
                'id': 5,
                'title': 'Best of the 90s',
                'artists': [{'id': 1, 'name': 'Artist'}],
            },
        }
        assert tr._is_compilation_from_search_data(item) is True

    def test_artist_mismatch_three_album_artists(self):
        # Artist mismatch + 3+ album artists → compilation
        item = {
            'title': 'Song',
            'artists': [{'id': 1, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 6,
                'title': 'Grunge and Beyond',
                'artists': [
                    {'id': 88881, 'name': 'Nirvana'},
                    {'id': 88882, 'name': 'Pearl Jam'},
                    {'id': 88883, 'name': 'Soundgarden'},
                ],
            },
        }
        assert tr._is_compilation_from_search_data(item) is True

    def test_artist_match_single_album_artist_not_compilation(self):
        item = {
            'title': 'Desperately Wanting',
            'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            'album': {
                'id': 7,
                'title': 'Muskoka Sunset',
                'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
            },
        }
        assert tr._is_compilation_from_search_data(item) is False


# ── 5. _filter_and_rank_isrc_results ──────────────────────────────────────

SEARCH_ITEMS = [
    # [0] "90s Rock" — compilation by keyword, 2018
    {
        'id': 92925712, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 92925707, 'title': '90s Rock', 'releaseDate': '2018-06-01', 'artists': [{'id': 99999, 'name': 'Various Artists'}]},
        'audioQuality': 'LOSSLESS',
    },
    # [1] "Muskoka Sunset" — non-compilation, 2020
    {
        'id': 374411717, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 374411682, 'title': 'Muskoka Sunset', 'releaseDate': '2020-01-01', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
        'audioQuality': 'LOSSLESS',
    },
    # [2] "Grunge and Beyond" — non-compilation, 2015, VA album artist
    {
        'id': 185046379, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 185046368, 'title': 'Grunge and Beyond', 'releaseDate': '2015-03-01', 'artists': [{'id': 88888, 'name': 'Various Artists'}]},
        'audioQuality': 'LOSSLESS',
    },
    # [3] "90s HITS - 100 Greatest Songs" — compilation by keyword
    {
        'id': 326227610, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 326227487, 'title': '90s HITS - 100 Greatest Songs of the 1990s', 'releaseDate': '2019-01-01', 'artists': [{'id': 99999, 'name': 'Various Artists'}]},
        'audioQuality': 'LOSSLESS',
    },
    # [4] "Friction Baby" — original studio album, 1996, non-compilation
    {
        'id': 3466926, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 3466918, 'title': 'Friction Baby', 'releaseDate': '1996-09-17', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
        'audioQuality': 'LOSSLESS',
    },
    # [5] "Friction Baby (Remastered)" — deluxe/remaster, 2006
    {
        'id': 3466999, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 3466918, 'title': 'Friction Baby', 'releaseDate': '2006-01-01', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
        'version': 'Remastered',
        'audioQuality': 'LOSSLESS',
    },
    # [6] "Friction Baby (Live)" — live version
    {
        'id': 3466888, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 3466918, 'title': 'Friction Baby', 'releaseDate': '1996-09-17', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
        'version': "Live at Tipitina's",
        'audioQuality': 'LOSSLESS',
    },
    # [7] Original track — should be skipped
    {
        'id': 218160, 'title': 'Desperately Wanting',
        'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
        'album': {'id': 218152, 'title': 'Greatest Hits', 'releaseDate': '2005-03-15', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
        'audioQuality': 'LOSSLESS',
    },
]


class TestFilterAndRankIsrcResults:
    def test_friction_baby_is_best_pick(self):
        """Friction Baby (1996, non-compilation) should be ranked best."""
        result = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',  # skip original
            settings={},
        )
        assert result is not None
        assert result['id'] == 3466926
        assert result['album']['title'] == 'Friction Baby'

    def test_friction_baby_remastered_below_original(self):
        """Friction Baby Remastered ranks below original (same album/year, is_deluxe=1)."""
        # Both 3466926 and 3466999 should be candidates
        results = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',
            settings={},
        )
        # Result should be 3466926, not 3466999
        assert results['id'] == 3466926

    def test_live_version_ranked_below_studio(self):
        """Live version (id 3466888) should rank below all studio versions."""
        results = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',
            settings={},
        )
        # Should not be the Live version
        assert results['id'] != 3466888

    def test_compilations_ranked_below_non_compilations(self):
        """Compilations (90s Rock, 90s HITS) should rank below non-compilations."""
        results = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',
            settings={},
        )
        # Best pick should NOT be a compilation
        assert results['album']['title'] not in ('90s Rock', '90s HITS - 100 Greatest Songs of the 1990s')

    def test_original_track_skipped(self):
        """Original track (id 218160) should be excluded from results."""
        results = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='218160',
            settings={},
        )
        assert results is None or results['id'] != 218160

    def test_empty_items_returns_none(self):
        result = tr._filter_and_rank_isrc_results(
            [],
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id=None,
            settings={},
        )
        assert result is None

    def test_no_title_match_returns_none(self):
        result = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Completely Different Song',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id=None,
            settings={},
        )
        assert result is None

    def test_penalty_compilation_false_equalizes_compilations(self):
        """When penalty_compilation=False, compilations share tier 0 with non-compilations."""
        # With penalty_compilation=False, release year becomes primary differentiator.
        # 90s Rock (2018) is later than Friction Baby (1996), so Friction Baby still wins.
        # But compilations shouldn't be demoted to tier 1.
        result = tr._filter_and_rank_isrc_results(
            SEARCH_ITEMS,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',
            settings={'penalty_compilation': False},
        )
        # Friction Baby should still be best due to earliest release year
        assert result['id'] == 3466926

    def test_penalty_live_false_prevents_live_penalty(self):
        """When penalty_live=False, the live version is not penalized with is_live=1.

        This test uses items with different release years so they never tie on
        phase-1 sort key, avoiding the phase-2 tiebreaker that would require DB access.
        """
        items = [
            # Friction Baby live (1996) — with penalty_live=False, should not be penalized
            {
                'id': 3466888, 'title': 'Desperately Wanting',
                'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
                'album': {'id': 3466918, 'title': 'Friction Baby', 'releaseDate': '1996-09-17', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
                'version': "Live at Tipitina's",
                'audioQuality': 'LOSSLESS',
            },
            # Muskoka Sunset (2020) — non-compilation, later year, ranks below live's studio
            {
                'id': 374411717, 'title': 'Desperately Wanting',
                'artists': [{'id': 13763, 'name': 'Better Than Ezra'}],
                'album': {'id': 374411682, 'title': 'Muskoka Sunset', 'releaseDate': '2020-01-01', 'artists': [{'id': 13763, 'name': 'Better Than Ezra'}]},
                'audioQuality': 'LOSSLESS',
            },
        ]
        result = tr._filter_and_rank_isrc_results(
            items,
            title='Desperately Wanting',
            track_artist='Better Than Ezra',
            album='',
            original_hifi_id='999999',
            settings={'penalty_live': False},
        )
        # Without live penalty, 1996 live < 2020 non-live, so live wins
        assert result is not None
        assert result['id'] == 3466888


# ── 6. _artists_overlap ────────────────────────────────────────────────────

class TestArtistsOverlap:
    def test_exact_match(self):
        assert tr._artists_overlap('Better Than Ezra', [{'name': 'Better Than Ezra'}]) is True

    def test_no_match(self):
        assert tr._artists_overlap('Better Than Ezra', [{'name': 'Nirvana'}]) is False

    def test_empty_track_artist_returns_true(self):
        # Empty track artist = "don't filter"
        assert tr._artists_overlap('', [{'name': 'Nirvana'}]) is True

    def test_empty_item_artists_returns_false(self):
        assert tr._artists_overlap('Better Than Ezra', []) is False