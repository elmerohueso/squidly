"""MusicBrainz metadata provider."""

import logging
from typing import Any, Dict, List, Optional

from squidly.services.metadata import MetadataProvider
from squidly.services import musicbrainz as mb

logger = logging.getLogger(__name__)


class MusicBrainzMetadataProvider(MetadataProvider):
    """MusicBrainz metadata provider."""

    def search(self, query: str, search_type: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Search MusicBrainz. search_type: 's'=recordings, 'a'=artists, 'al'=releases, 'p'=release-groups."""
        if search_type == 's':
            result = mb.mb_search_recordings(query, limit=limit, offset=offset)
            recordings = result.get('recordings', [])
            items = [mb.normalize_mb_recording(r) for r in recordings]
            return {'data': {'items': items}, 'count': result.get('count', 0)}
        elif search_type == 'a':
            result = mb.mb_search_artists(query, limit=limit, offset=offset)
            artists = result.get('artists', [])
            items = []
            for a in artists:
                items.append({
                    'id': a.get('id'),
                    'name': a.get('name', ''),
                    'picture': None,
                })
            return {'data': {'artists': {'items': items}}, 'count': result.get('count', 0)}
        elif search_type == 'al':
            result = mb.mb_search_releases(query, limit=limit, offset=offset)
            releases = result.get('releases', [])
            items = []
            for r in releases:
                # Cover art is fetched on-demand in album detail view to avoid N+1 API calls
                items.append({
                    'id': r.get('id'),
                    'title': r.get('title', ''),
                    'cover': None,
                    'releaseDate': r.get('date', ''),
                    'numberOfTracks': None,
                    'artists': mb._extract_artists_array(r.get('artist-credit', [])),
                    'artist': {'id': None, 'name': mb._extract_artist_name(r.get('artist-credit', [])), 'picture': None, 'type': ''},
                    'audioQuality': None,
                    'explicit': False,
                    'numberOfVideos': 0,
                })
            return {'data': {'albums': {'items': items}}, 'count': result.get('count', 0)}
        elif search_type == 'p':
            # MusicBrainz has no playlists — return empty
            return {'data': {'playlists': {'items': []}}, 'count': 0}
        else:
            return {'error': f'Unknown search type: {search_type}'}

    def get_track(self, track_id: str) -> Dict[str, Any]:
        """Get recording by MBID."""
        rec = mb.mb_get_recording(track_id)
        if not rec:
            return {'error': 'Recording not found'}
        return {'track': mb.normalize_mb_recording(rec), 'proxied_via': 'MusicBrainz'}

    def get_album(self, album_id: str) -> Dict[str, Any]:
        """Get release by MBID with recordings."""
        rel = mb.mb_get_release(album_id)
        if not rel:
            return {'error': 'Release not found'}
        cover_url = mb.mb_get_cover_art_url(album_id)
        return {**mb.normalize_mb_release(rel, cover_url), 'proxied_via': 'MusicBrainz'}

    def get_artist(self, artist_id: str) -> Dict[str, Any]:
        """Get artist by MBID with release-groups."""
        artist = mb.mb_get_artist(artist_id)
        if not artist:
            return {'error': 'Artist not found'}
        result = mb.normalize_mb_artist(artist)

        # Fetch cover art from first album release
        release_groups = artist.get('release-groups', [])
        for rg in release_groups:
            if rg.get('type', '').lower() == 'album':
                # Get the first release of this release-group to get a cover
                rg_detail = mb.mb_get_release_group(rg.get('id'))
                releases = rg_detail.get('releases', [])
                if releases:
                    cover_url = mb.mb_get_cover_art_url(releases[0].get('id'))
                    if cover_url:
                        result['artist']['picture'] = cover_url
                        # Also update album covers
                        for album in result['artist'].get('albums', []):
                            if album.get('id') == rg.get('id'):
                                album['cover'] = cover_url
                        break
                break

        return {**result, 'proxied_via': 'MusicBrainz'}

    def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        return {'error': 'Playlists are not supported when using MusicBrainz as the browse source.'}

    def get_similar_tracks(self, track_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        return []

    def get_similar_albums(self, album_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        return []

    def get_similar_artists(self, artist_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        return []

    def get_track_manifest(self, track_id: str, audio_quality: str = 'LOSSLESS') -> Dict[str, Any]:
        return {}

    def get_track_stream_url(self, track_id: str, audio_quality: str = 'LOW') -> Optional[str]:
        return None
