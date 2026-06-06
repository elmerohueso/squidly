"""Metadata provider protocol and implementations."""

import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MetadataProvider(ABC):
    """Protocol for metadata providers (Tidal, Qobuz, etc.)."""
    
    @abstractmethod
    def search(self, query: str, search_type: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Search for tracks, albums, artists, or playlists."""
        pass
    
    @abstractmethod
    def get_track(self, track_id: str) -> Dict[str, Any]:
        """Get track metadata by ID."""
        pass
    
    @abstractmethod
    def get_album(self, album_id: str) -> Dict[str, Any]:
        """Get album metadata by ID."""
        pass
    
    @abstractmethod
    def get_artist(self, artist_id: str) -> Dict[str, Any]:
        """Get artist metadata by ID."""
        pass
    
    @abstractmethod
    def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """Get playlist metadata by ID."""
        pass
    
    @abstractmethod
    def get_similar_tracks(self, track_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar tracks for a given track."""
        pass
    
    @abstractmethod
    def get_similar_albums(self, album_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar albums for a given album."""
        pass
    
    @abstractmethod
    def get_similar_artists(self, artist_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar artists for a given artist."""
        pass
    
    @abstractmethod
    def get_track_manifest(self, track_id: str, audio_quality: str = 'LOSSLESS') -> Dict[str, Any]:
        """Get track manifest (streaming URLs) for a given track."""
        pass
    
    @abstractmethod
    def get_track_stream_url(self, track_id: str, audio_quality: str = 'LOW') -> Optional[str]:
        """Get stream URL for a track."""
        pass


def _stringify_ids(obj):
    """Recursively convert 'id' fields to strings in a response dict."""
    if isinstance(obj, dict):
        for key in ('id', 'artistId', 'albumId', 'trackId', 'album_id', 'artist_id', 'track_id'):
            if key in obj and obj[key] is not None:
                obj[key] = str(obj[key])
        for value in list(obj.values()):
            _stringify_ids(value)
    elif isinstance(obj, list):
        for item in obj:
            _stringify_ids(item)
    return obj


_provider_cache: Dict[str, MetadataProvider] = {}


def get_metadata_provider(source: str = 'tidal') -> MetadataProvider:
    """Get the metadata provider for the given source."""
    if source not in _provider_cache:
        if source == 'musicbrainz':
            from squidly.services.musicbrainz_provider import MusicBrainzMetadataProvider
            _provider_cache[source] = MusicBrainzMetadataProvider()
        else:
            _provider_cache[source] = TidalMetadataProvider()
    return _provider_cache[source]


def get_active_metadata_provider() -> MetadataProvider:
    """Get the metadata provider based on the current database setting."""
    from squidly.infrastructure.storage import get_download_settings
    settings = get_download_settings()
    source = settings.get('metadata_source', 'tidal')
    return get_metadata_provider(source)


class TidalMetadataProvider(MetadataProvider):
    """Tidal metadata provider using hifi.py functions."""
    
    def __init__(self):
        from squidly.services.hifi import (
            get_hifi_track_object,
            get_hifi_album_object,
            get_hifi_artist_object,
            _fetch_hifi_search_results,
            _fetch_hifi_track_manifests_payload,
        )
        self._get_track_object = get_hifi_track_object
        self._get_album_object = get_hifi_album_object
        self._get_artist_object = get_hifi_artist_object
        self._search = _fetch_hifi_search_results
        self._get_manifest = _fetch_hifi_track_manifests_payload
    
    def search(self, query: str, search_type: str, limit: int = 25, offset: int = 0) -> Dict[str, Any]:
        """Search Tidal library."""
        return _stringify_ids(copy.deepcopy(self._search(search_type, query, limit=limit, offset=offset)))
    
    def get_track(self, track_id: str) -> Dict[str, Any]:
        """Get track by ID."""
        return _stringify_ids(copy.deepcopy(self._get_track_object(track_id, include_streams=False, include_album=True)))
    
    def get_album(self, album_id: str) -> Dict[str, Any]:
        """Get album by ID."""
        return _stringify_ids(copy.deepcopy(self._get_album_object(album_id, include_streams=False)))
    
    def get_artist(self, artist_id: str) -> Dict[str, Any]:
        """Get artist by ID."""
        return _stringify_ids(copy.deepcopy(self._get_artist_object(artist_id)))
    
    def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """Get playlist by ID."""
        from squidly.infrastructure.downloads import make_request_with_retry_rotating_mirrors, get_squid_urls
        response, _ = make_request_with_retry_rotating_mirrors(
            f"/playlists/{playlist_id}",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )
        result = response.json() if response.ok else {}
        return _stringify_ids(result)
    
    def get_similar_tracks(self, track_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar tracks."""
        from squidly.infrastructure.downloads import make_request_with_retry_rotating_mirrors, get_squid_urls
        response, _ = make_request_with_retry_rotating_mirrors(
            f"/tracks/{track_id}/similar",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )
        result = response.json() if response.ok else {}
        items = result.get('data', {}).get('items', [])
        return _stringify_ids(items)
    
    def get_similar_albums(self, album_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar albums."""
        from squidly.infrastructure.downloads import make_request_with_retry_rotating_mirrors, get_squid_urls
        response, _ = make_request_with_retry_rotating_mirrors(
            f"/albums/{album_id}/similar",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )
        result = response.json() if response.ok else {}
        items = result.get('data', {}).get('items', [])
        return _stringify_ids(items)
    
    def get_similar_artists(self, artist_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get similar artists."""
        from squidly.infrastructure.downloads import make_request_with_retry_rotating_mirrors, get_squid_urls
        response, _ = make_request_with_retry_rotating_mirrors(
            f"/artists/{artist_id}/similar",
            get_squid_urls(),
            method='GET',
            timeout=10,
            max_retries=3
        )
        result = response.json() if response.ok else {}
        items = result.get('data', {}).get('items', [])
        return _stringify_ids(items)
    
    def get_track_manifest(self, track_id: str, audio_quality: str = 'LOSSLESS') -> Dict[str, Any]:
        """Get track manifest."""
        return self._get_manifest(track_id, audio_quality=audio_quality)
    
    def get_track_stream_url(self, track_id: str, audio_quality: str = 'LOW') -> Optional[str]:
        """Get stream URL for track."""
        manifest = self.get_track_manifest(track_id, audio_quality)
        if isinstance(manifest, dict):
            return manifest.get('url')
        return None
