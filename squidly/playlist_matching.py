"""Playlist matching helpers for Squidly.

These functions handle matching external playlist tracks (ListenBrainz,
YouTube Music, Last.fm) to the local library. They are separate from
library entity matching (squidly.matching).
"""

from squidly.utils import _safe_int, normalize_match_text


def _lookup_track_metadata(cur, title, artist, album, fuzzy=False):
    """Query local tracks table for rows matching title+artist+album, falling back to title+artist.
    If fuzzy=True, falls back further to normalized text matching when exact matches fail."""
    rows = []

    if album:
        cur.execute(
            """
            SELECT tracks.title, artists.name AS artist, albums.title AS album, tracks.format, tracks.bitrate, tracks.path
            FROM tracks
            JOIN albums ON albums.album_id = tracks.album_id
            LEFT JOIN artists ON artists.artist_id = tracks.artist_id
            WHERE lower(COALESCE(tracks.title, '')) = lower(%s)
              AND lower(COALESCE(artists.name, '')) = lower(%s)
              AND lower(COALESCE(albums.title, '')) = lower(%s)
            ORDER BY tracks.last_seen_at DESC
            """,
            (title, artist, album)
        )
        rows = cur.fetchall() or []

    if not rows:
        cur.execute(
            """
            SELECT tracks.title, artists.name AS artist, albums.title AS album, tracks.format, tracks.bitrate, tracks.path
            FROM tracks
            LEFT JOIN albums ON albums.album_id = tracks.album_id
            LEFT JOIN artists ON artists.artist_id = tracks.artist_id
            WHERE lower(COALESCE(tracks.title, '')) = lower(%s)
              AND lower(COALESCE(artists.name, '')) = lower(%s)
            ORDER BY tracks.last_seen_at DESC
            """,
            (title, artist)
        )
        rows = cur.fetchall() or []

    if not rows and fuzzy:
        normalized_title = normalize_match_text(title, strip_trailing_parenthetical=True)
        normalized_artist = normalize_match_text(artist)
        normalized_album = normalize_match_text(album, strip_trailing_parenthetical=True) if album else ''

        artist_candidates = [normalized_artist]
        split_parts = []
        for sep in [';', ',']:
            if sep in artist:
                split_parts = [normalize_match_text(a.strip()) for a in artist.split(sep) if a.strip()]
                if split_parts:
                    break
        if len(split_parts) > 1:
            artist_candidates.extend(split_parts)

        seen_file_paths = set()
        for candidate_artist in artist_candidates:
            cur.execute(
                """
                SELECT tracks.title, artists.name AS artist, albums.title AS album, tracks.format, tracks.bitrate, tracks.path
                FROM tracks
                LEFT JOIN albums ON albums.album_id = tracks.album_id
                LEFT JOIN artists ON artists.artist_id = tracks.artist_id
                WHERE trim(regexp_replace(regexp_replace(lower(COALESCE(artists.name, '')), '[^a-z0-9]+', ' ', 'g'), '\\s+', ' ', 'g')) = %s
                """,
                (candidate_artist,)
            )
            candidates_found = cur.fetchall() or []

            for candidate in candidates_found:
                fp = candidate.get('path')
                if fp in seen_file_paths:
                    continue
                candidate_title = normalize_match_text(candidate.get('title'), strip_trailing_parenthetical=True)
                candidate_album = normalize_match_text(candidate.get('album'), strip_trailing_parenthetical=True)

                title_match = candidate_title == normalized_title
                album_match = (not normalized_album) or (candidate_album == normalized_album)

                if not title_match:
                    continue

                if normalized_album and not album_match:
                    continue

                seen_file_paths.add(fp)
                rows.append(candidate)

    return rows
