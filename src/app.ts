// Main TypeScript entry point

interface SearchResult {
    query: string;
    data?: {
        items?: (Track | AlbumSearchItem | PlaylistSearchItem)[];
        albums?: {
            items: AlbumSearchItem[];
        };
        artists?: {
            items: ArtistSearchItem[];
        };
        playlists?: {
            items: PlaylistSearchItem[];
        };
    };
    results?: any[];
    proxied_via?: string;
    error?: string;
    details?: string;
}

interface Track {
    id: number;
    title: string;
    version?: string;
    duration?: number;
    artists?: Artist[];
    artist?: Artist;
    album?: Album;
    quality?: string;
    audioQuality?: string;
    maxAudioQuality?: string;
    cover?: string;
    trackNumber?: number;
    volumeNumber?: number;
    explicit?: boolean;
    mediaMetadata?: {
        tags?: string[];
    };
}

interface Artist {
    id: number;
    name: string;
}

interface Album {
    id: number;
    title: string;
    cover?: string;
}

interface AlbumSearchItem {
    id: number;
    title: string;
    cover?: string;
    artists?: Artist[];
    artist?: Artist;
    releaseDate?: string;
    numberOfTracks?: number;
    numberOfItems?: number;
    numberOfVolumes?: number;
    duration?: number;
    audioQuality?: string;
    maxAudioQuality?: string;
    explicit?: boolean;
    mediaMetadata?: {
        tags?: string[];
    };
    mediaTags?: string[];
}

interface ArtistSearchItem {
    id: number;
    name: string;
    picture?: string;
    popularity?: number;
    artistTypes?: string[];
}

interface PlexLibraryArtist {
    id: string;
    name: string;
    picture?: string;
}

interface PlexLibraryAlbum {
    id: string;
    title: string;
    artist?: string;
    year?: number;
    track_count?: number;
    cover?: string;
}

interface NormalizedAlbum {
    id: string;
    title: string;
    artist: string;
    artistId?: number;
    year: number | null;
    trackCount: number | null;
    quality: string;
    explicit: boolean;
    cover?: string;
}

interface AlbumGridOptions {
    viewMode: 'search-albums' | 'artist-albums' | 'similar-albums' | 'library-albums';
    hideArtist?: boolean;
    includeQuality?: boolean;
    dataAttr?: string;
    extraRowClass?: string;
    actions?: 'full' | 'play-only';
    rowDataAttrs?: (album: NormalizedAlbum) => Record<string, string>;
    emptyMessage?: string;
}

interface NormalizedTrack {
    id: string;
    title: string;
    version?: string;
    artist: string;
    artistId?: number;
    album: string;
    albumId?: number;
    albumCover?: string;
    trackNumber: number | null;
    volumeNumber: number;
    duration: number | null;
    quality: string;
    explicit: boolean;
    qualityFormat?: string;
    qualityBitrate?: string;
}

interface TrackGridOptions {
    viewMode: 'single-album' | 'multi-album' | 'library-tracks';
    showTrackNumber?: boolean;
    showAlbumColumn?: boolean;
    showArtwork?: boolean;
    numberOfVolumes?: number;
    dataAttr?: string;
    extraRowClass?: string;
    actions?: 'full' | 'play-only';
    qualityStyle?: 'tier' | 'format-bitrate';
    rowDataAttrs?: (track: NormalizedTrack) => Record<string, string>;
    emptyMessage?: string;
}

interface PlaylistTrackInput {
    name: string;
    artist: string;
}

interface PlexLibraryTrack {
    id: string;
    title: string;
    artist?: string;
    artist_id?: string;
    album?: string;
    duration?: number;
    track_number?: number;
    disc_number?: number;
    quality_format?: string;
    quality_bitrate_kbps?: number;
    cover?: string;
}

interface PlexLibraryArtistsResponse {
    success?: boolean;
    server_name?: string;
    library_name?: string;
    artists?: PlexLibraryArtist[];
    total?: number;
    offset?: number;
    limit?: number;
    error?: string;
}

interface PlexLibraryArtistAlbumsResponse {
    success?: boolean;
    artist?: {
        id: string;
        name: string;
        picture?: string;
    };
    albums?: PlexLibraryAlbum[];
    error?: string;
}

interface PlexLibraryAlbumTracksResponse {
    success?: boolean;
    album?: {
        id: string;
        title: string;
        artist?: string;
        year?: number;
        track_count?: number;
        cover?: string;
    };
    tracks?: PlexLibraryTrack[];
    error?: string;
}

interface PlexPlaylist {
    name: string;
    ratingKey: string | null;
}

interface YtmPlaylist {
    title: string;
    playlistId: string;
    count: number | string;
}

interface PlexPlaylistTracksResponse {
    success?: boolean;
    playlist?: {
        id: string;
        title: string;
        track_count?: number;
        cover?: string;
    };
    tracks?: PlexLibraryTrack[];
    error?: string;
}

interface PlaylistSearchItem {
    id?: number | string;
    uuid?: string;
    url?: string;
    title: string;
    description?: string;
    customImageUrl?: string | null;
    squareImage?: string;
    image?: string;
    cover?: string;
    numberOfTracks?: number;
    numberOfItems?: number;
    type?: string;
    audioQuality?: string;
    mediaMetadata?: {
        tags?: string[];
    };
    mediaTags?: string[];
    promotedArtists?: Array<{
        id?: number | string;
        name?: string;
    }>;
    creator?: {
        id?: number | string;
        name?: string;
    } | string;
}

interface AlbumInfo {
    data?: {
        id: number;
        title: string;
        cover?: string;
        explicit?: boolean;
        mediaMetadata?: {
            tags?: string[];
        };
        artist?: Artist;
        artists?: Artist[];
        releaseDate?: string;
        numberOfTracks?: number;
        numberOfVolumes?: number;
        items?: Array<{
            type: string;
            item: Track;
        }>;
    };
    proxied_via?: string;
    error?: string;
}

interface AlbumObject extends AlbumSearchItem {
    version?: string;
    numberOfDiscs?: number;
    duration?: number;
    copyright?: string;
    artists?: Artist[];
    tracks?: Track[];
}

interface AlbumObjectResponse {
    album?: AlbumObject;
    proxied_via?: string;
    error?: string;
}

interface ArtistObject {
    artist?: {
        id?: number;
        name?: string;
        picture?: string;
        albums?: AlbumSearchItem[];
        top_tracks?: Track[] | number[];
    };
    proxied_via?: string;
    error?: string;
}

interface Endpoint {
    name: string;
    encodedUrl: string;
    online: boolean;
    responseTime: number | null;
    lastChecked: string | null;
    enabled: boolean;
    mirrorType: string;
}

interface MirrorRateLimitStatus {
    safe_interval: number;
    safe_rps: number;
    safe_rpm: number;
    error_rate_429: number;
    sample_size: number;
}

interface EndpointStatus {
    endpoints: Endpoint[];
    summary: {
        total: number;
        online: number;
        offline: number;
    };
    mirrorRateLimitStatus?: MirrorRateLimitStatus;
}

interface JobStageMap {
    downloaded?: string;
    tagged?: string;
    written?: string;
    playlist_added?: string;
    upgraded_existing?: string;
}

interface JobResult {
    artist?: string;
    title?: string;
    album?: string;
    format?: string;
    playlist_name?: string | null;
    trigger?: string;
    progress?: {
        processed_tracks?: number;
        total_tracks?: number;
        upserted_songs?: number;
        deleted_songs?: number;
    };
    stages?: JobStageMap;
}

interface PlexSongVariant {
    format?: string;
    bitrate?: number | null;
    file_path?: string | null;
}

interface PlexTrackMatch {
    exists: boolean;
    variants?: PlexSongVariant[];
    confidence?: number | null;
}

interface HifiTrackLookupMatch extends PlexTrackMatch {
    track_id: string;
}

interface HifiAlbumLookupMatch {
    album_id: string;
    exists: boolean;
    complete: boolean;
    confidence?: number | null;
    matched_track_count?: number;
    expected_track_count?: number;
    variants?: PlexSongVariant[];
}

interface HifiArtistLookupMatch {
    artist_id: string;
    exists: boolean;
    complete: boolean;
    confidence?: number | null;
    variants?: PlexSongVariant[];
}

interface HifiMatchLookupResponse {
    success?: boolean;
    tracks?: HifiTrackLookupMatch[];
    albums?: HifiAlbumLookupMatch[];
    artists?: HifiArtistLookupMatch[];
    error?: string;
}

interface HifiReviewArtist {
    artist_id: number;
    name: string;
    library_id?: string;
    hifi_id?: string;
    picture?: string;
    confidence?: number;
}

interface HifiReviewAlbum {
    album_id: number;
    artist_id?: number;
    title: string;
    artist_name?: string;
    library_id?: string;
    hifi_id?: string;
    cover?: string;
    track_titles?: string[];
    confidence?: number;
    complete?: boolean;
    matched_track_count?: number;
    expected_track_count?: number;
}

interface HifiReviewTrack {
    track_id: number;
    album_id?: number;
    artist_id?: number;
    title: string;
    artist_name?: string;
    album_title?: string;
    cover?: string;
    album_library_id?: string;
    artist_library_id?: string;
    library_id?: string;
    hifi_id?: string;
    confidence?: number;
    path?: string;
    format?: string;
    bitrate?: number;
    disc_number?: number;
    track_number?: number;
}

interface HifiMatchReviewResponse {
    success?: boolean;
    summary?: {
        artists?: number;
        albums?: number;
        tracks?: number;
    };
    artists?: HifiReviewArtist[];
    albums?: HifiReviewAlbum[];
    tracks?: HifiReviewTrack[];
    error?: string;
}

interface HifiMatchCandidate {
    hifi_id: string;
    title: string;
    subtitle?: string;
    confidence?: number;
    image_url?: string;
    explicit?: boolean;
    track_titles?: string[];
}

interface HifiMatchCandidatesResponse {
    success?: boolean;
    candidates?: HifiMatchCandidate[];
    error?: string;
}

interface JobItem {
    id: number;
    job_type: string;
    status: string;
    payload?: Record<string, any> | null;
    result?: JobResult | null;
    error_message?: string | null;
}

interface JobFilterTotals {
    incomplete: number;
    complete: number;
    completed_with_errors: number;
    failed: number;
}

type DownloadQuality = 'LOSSLESS' | 'HIGH' | 'LOW';

interface DownloadSettings {
    downloadSource: string;
    quality: DownloadQuality;
    fileNamingAlbum: string;
    jobsRefreshIntervalSeconds: number;
    ignoreMatches: boolean;
    tagTitle: boolean;
    tagArtist: boolean;
    tagAlbumArtist: boolean;
    tagAlbum: boolean;
    tagYear: boolean;
    tagTrackNumber: boolean;
    tagTrackTotal: boolean;
    tagDiscNumber: boolean;
    tagDiscTotal: boolean;
    tagVersion: boolean;
    tagTidalTrackId: boolean;
    tagTidalAlbumId: boolean;
    tagIsrc: boolean;
    tagCopyright: boolean;
    tagCoverArt: boolean;
    tagExplicit: boolean;
    tagExplicitSuffix: boolean;
    penaltyCompilation: boolean;
    penaltyKaraoke: boolean;
    penaltyLive: boolean;
}

interface AppRouteState {
    view: string;
    searchType?: string;
    query?: string;
    artistId?: number;
    albumId?: number;
    trackId?: number;
    playlistId?: string;
    playlistTitle?: string;
    username?: string;
    playlistUrl?: string;
    playlistType?: string;
    freshFindsPlaylistId?: number;
}

type AppPage = 'explore' | 'library' | 'settings' | 'mirrors' | 'matches' | 'jobs' | 'history';

interface ListenHistoryEntry {
    id: number;
    plex_account_id: number;
    plex_username: string;
    track_library_id: string | null;
    hifi_id: string | null;
    title: string;
    artist: string | null;
    album: string | null;
    duration: number | null;
    played_at: string;
    view_offset: number | null;
    view_count: number | null;
    synced_at: string;
}

interface LibraryRouteState {
    view: 'artists' | 'artist_albums' | 'album_tracks' | 'playlist_tracks';
    offset?: number;
    artistId?: string;
    artistName?: string;
    albumId?: string;
    albumTitle?: string;
    albumArtist?: string;
    playlistRatingKey?: string;
    playlistName?: string;
}

interface AppHistoryState {
    app: 'squidly';
    tab: AppPage;
    route: AppRouteState;
    libraryRoute: LibraryRouteState;
}

class App {
    private static readonly NEW_PLEX_PLAYLIST_OPTION = '__new_playlist__';
    private searchInput: HTMLInputElement;
    private searchTypeSelect: HTMLSelectElement;
    private searchButton: HTMLButtonElement;
    private exploreBreadcrumbContainer: HTMLElement | null;
    private libraryBreadcrumbContainer: HTMLElement | null;
    private resultsContainer: HTMLElement;
    private libraryResultsContainer: HTMLElement;
    private statusButton: HTMLButtonElement;
    private statusFlyout: HTMLElement;
    private flyoutOverlay: HTMLElement;
    private closeFlyoutButton: HTMLButtonElement;
    private flyoutContent: HTMLElement;
    private addMirrorButton: HTMLButtonElement;
    private jobsButton: HTMLButtonElement;
    private jobsFlyout: HTMLElement;
    private jobsOverlay: HTMLElement;
    private closeJobsButton: HTMLButtonElement;
    private jobsFilterSelect: HTMLSelectElement;
    private cancelPendingJobsButton: HTMLButtonElement;
    private retryAllJobsButton: HTMLButtonElement;
    private jobsContent: HTMLElement;
    private jobsPagination: HTMLElement;
    private matchReviewRunScanButton: HTMLButtonElement;
    private matchReviewRefreshButton: HTMLButtonElement;
    private matchReviewEntityFilter: HTMLSelectElement;
    private matchReviewMaxConfidenceInput: HTMLInputElement;
    private matchReviewStatusEl: HTMLElement;
    private matchReviewActivity: HTMLElement;
    private matchReviewSummary: HTMLElement;
    private matchReviewContent: HTMLElement;
    private settingsButton: HTMLButtonElement;
    private settingsFlyout: HTMLElement;
    private settingsOverlay: HTMLElement;
    private closeSettingsButton: HTMLButtonElement;
    private qualityLosslessInput: HTMLInputElement;
    private qualityHighInput: HTMLInputElement;
    private qualityLowInput: HTMLInputElement;
    private downloadSourceTidalInput: HTMLInputElement;
    private downloadSourceQobuzInput: HTMLInputElement;
    private fileNamingAlbumInput: HTMLInputElement;
    private jobsRefreshIntervalSecondsInput: HTMLInputElement;
    private listenbrainzTokenInput: HTMLInputElement;
    private listenbrainzUsernameInput: HTMLInputElement;
    private saveLbConfigButton: HTMLButtonElement;
    private lbConfigStatusEl: HTMLElement;
    private ytmCookieInput: HTMLInputElement;
    private saveYtmConfigButton: HTMLButtonElement;
    private ytmConfigStatusEl: HTMLElement;
    private autoDownloadFreshFindsCheckbox: HTMLInputElement;
    private freshFindsAutoDownloadStatusEl: HTMLElement;
    private freshFindsRetentionInput: HTMLInputElement;
    private freshFindsRetentionStatusEl: HTMLElement;
    private plexLoginButton: HTMLButtonElement;
    private plexPinContainer: HTMLElement;
    private plexPinDisplay: HTMLElement;
    private plexPinCopyButton: HTMLButtonElement;
    private plexPinStatus: HTMLElement;
    private plexLoginOnlyContainer: HTMLElement;
    private plexLoginOnlyButton: HTMLButtonElement;
    private plexLoginOnlyPinContainer: HTMLElement;
    private plexLoginOnlyPinDisplay: HTMLElement;
    private plexLoginOnlyPinStatus: HTMLElement;
    private plexLoginOnlyLibraryContainer: HTMLElement;
    private plexLoginOnlyLibraryNameSelect: HTMLSelectElement;
    private plexLoginOnlySaveButton: HTMLButtonElement;
    private plexLoginOnlyUserContainer: HTMLElement;
    private plexLoginOnlyUserList: HTMLElement;
    private appWrapper: HTMLElement;
    private plexPlaylistNameInput: HTMLInputElement | null;
    private plexPlaylistOptions: HTMLSelectElement | null;
    private plexPlaylistBackButton: HTMLButtonElement | null;
    private savePlexConfigButton: HTMLButtonElement;
    private plexSyncIntervalHoursInput: HTMLInputElement;
    private startPlexSyncButton: HTMLButtonElement;
    private plexSyncStatusEl: HTMLElement;
    private plexConfigStatusEl: HTMLElement;
    private plexConnectedStatusEl: HTMLElement;
    private plexClearCredentialsButton: HTMLButtonElement;
    private plexUserDropdownContainer: HTMLElement;
    private ignoreMatchesCheckbox: HTMLInputElement;
    private tagTitleCheckbox: HTMLInputElement;
    private tagArtistCheckbox: HTMLInputElement;
    private tagAlbumArtistCheckbox: HTMLInputElement;
    private tagAlbumCheckbox: HTMLInputElement;
    private tagYearCheckbox: HTMLInputElement;
    private tagTrackNumberCheckbox: HTMLInputElement;
    private tagTrackTotalCheckbox: HTMLInputElement;
    private tagDiscNumberCheckbox: HTMLInputElement;
    private tagDiscTotalCheckbox: HTMLInputElement;
    private tagVersionCheckbox: HTMLInputElement;
    private tagTidalTrackIdCheckbox: HTMLInputElement;
    private tagTidalAlbumIdCheckbox: HTMLInputElement;
    private tagIsrcCheckbox: HTMLInputElement;
    private tagCopyrightCheckbox: HTMLInputElement;
    private tagCoverArtCheckbox: HTMLInputElement;
    private tagExplicitCheckbox: HTMLInputElement;
    private tagExplicitSuffixCheckbox: HTMLInputElement;
    private penaltyCompilationCheckbox: HTMLInputElement;
    private penaltyKaraokeCheckbox: HTMLInputElement;
    private penaltyLiveCheckbox: HTMLInputElement;
    private userButton: HTMLButtonElement;
    private userDropdownModal: HTMLElement;
    private userDropdownOverlay: HTMLElement;
    private userDropdownList: HTMLElement;
    private userButtonText: HTMLElement;
    private mobileMenuToggle: HTMLButtonElement | null;
    private mobileMenuOverlay: HTMLElement | null;
    private downloadSettings: DownloadSettings;
    private settingsSaveTimer: number | null = null;
    private readonly settingsSaveDelayMs = 500;
    private statusUpdateInterval: number | null = null;
    private jobStatusInterval: number | null = null;
    private jobStatusPolling = false;
    private activeJobMap = new Map<number, {
        trackCard: HTMLElement;
        downloadBtn: HTMLButtonElement;
        statusEl: HTMLButtonElement;
    }>();
    private jobsUpdateInterval: number | null = null;
    private currentJobsPage: number = 1;
    private readonly jobsPageSize = 20;
    private jobsListCache: JobItem[] = [];
    private jobsTotalCountCache: number = 0;
    private isDownloadingAll: boolean = false;
    private downloadAllCancelRequested: boolean = false;
    private currentDownloadController: AbortController | null = null;
    private downloadAllScope: 'album' | 'loose' = 'loose';
    private currentAudio: HTMLAudioElement | null = null;
    private isPlexSelectedUserOwner: boolean = false;
    private currentPlayingTrackId: string | null = null;
    private currentPlayButton: HTMLButtonElement | null = null;
    private currentAudioCleanup: {
        audio: HTMLAudioElement;
        onEnded: () => void;
        onError: () => void;
    } | null = null;
    private lastRetryFunction: (() => Promise<void>) | null = null;
    private isPlexConfigured: boolean = false;
    private isHandlingPopState: boolean = false;
    private currentPage: AppPage = 'explore';
    private pendingRequestController: AbortController | null = null;
    private readonly libraryArtistsPageSize: number = 50;
    private libraryArtistsOffset: number = 0;
    private libraryArtistsTotal: number = 0;
    private libraryCurrentArtist: { id: string; name: string } | null = null;
    private libraryCurrentAlbum: { id: string; title: string; artist?: string } | null = null;
    private libraryCurrentPlaylist: string | null = null;
    private libraryLoadedOnce: boolean = false;
    private matchReviewPollingInterval: number | null = null;
    private lastMatchActivityJobId: number | null = null;
    private lastMatchActivityStatus: string | null = null;
    private activeMatchActivityJobId: number | null = null;
    private matchCandidateCache = new Map<string, HifiMatchCandidate[]>();
    private matchCandidateSearchTerms = new Map<string, string>();
    private matchCandidateRequestsInFlight = new Set<string>();
    private currentExploreRoute: AppRouteState = { view: 'home' };
    private exploreBreadcrumbRoutes: AppRouteState[] = [];
    private exploreSearchRoute: AppRouteState | null = null;
    private exploreParentRoute: AppRouteState | null = null;
    private exploreArtistName: string | null = null;
    private exploreAlbumTitle: string | null = null;
    private explorePlaylistTitle: string | null = null;
    private exploreLastfmPlaylistName: string | null = null;
    private exploreYoutubePlaylistName: string | null = null;
    private listenbrainzCurrentUsername: string | null = null;
    private listenbrainzCurrentPlaylist: { id: string; title: string } | null = null;
    private freshFindsPlaylistName: string | null = null;

    private historyTableContainer: HTMLElement;
    private historyEntries: ListenHistoryEntry[] = [];
    private historyLoading: boolean = false;

    private timezone: string = 'UTC';

    private getSearchTypeName(searchType?: string): string {
        const normalized = (searchType || 's').toLowerCase();
        const labels: Record<string, string> = {
            s: 'Tracks',
            a: 'Artists',
            al: 'Albums',
            p: 'Playlists',
            trackid: 'Track ID',
            lastfm: 'Last.fm',
            youtube_music: 'YouTube Music',
            listenbrainz: 'ListenBrainz'
        };
        return labels[normalized] || 'Results';
    }

    private renderExploreTopBarBreadcrumb(route: AppRouteState = this.currentExploreRoute): void {
        if (!this.exploreBreadcrumbContainer) {
            return;
        }

        const crumbs: Array<{ label: string; route?: AppRouteState }> = [];
        const username = route.username || this.listenbrainzCurrentUsername || '';
        const playlistTitle = this.listenbrainzCurrentPlaylist?.title || this.explorePlaylistTitle || '';

        if (route.view === 'home') {
            crumbs.push({ label: 'Explore' });
        } else if (route.view === 'search') {
            const query = route.query || this.searchInput?.value?.trim() || '';
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: query ? `${this.getSearchTypeName(route.searchType)} - "${query}"` : this.getSearchTypeName(route.searchType) });
        } else if (route.view === 'artist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (this.exploreSearchRoute?.view === 'search') {
                const query = this.exploreSearchRoute.query || '';
                const label = query ? `${this.getSearchTypeName(this.exploreSearchRoute.searchType)} - "${query}"` : this.getSearchTypeName(this.exploreSearchRoute.searchType);
                crumbs.push({ label, route: { ...this.exploreSearchRoute } });
            }
            crumbs.push({ label: this.exploreArtistName || 'Artist' });
        } else if (route.view === 'album') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (this.exploreSearchRoute?.view === 'search') {
                const query = this.exploreSearchRoute.query || '';
                const label = query ? `${this.getSearchTypeName(this.exploreSearchRoute.searchType)} - "${query}"` : this.getSearchTypeName(this.exploreSearchRoute.searchType);
                crumbs.push({ label, route: { ...this.exploreSearchRoute } });
            }
            if (this.exploreParentRoute?.view === 'artist') {
                crumbs.push({ label: this.exploreArtistName || 'Artist', route: { ...this.exploreParentRoute } });
            }
            crumbs.push({ label: this.exploreAlbumTitle || 'Album' });
        } else if (route.view === 'playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: this.explorePlaylistTitle || 'Playlist' });
        } else if (route.view === 'listenbrainz_playlists') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'ListenBrainz' });
            if (username) {
                crumbs.push({ label: username });
            }
        } else if (route.view === 'listenbrainz_playlist_tracks') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (username) {
                crumbs.push({ label: 'ListenBrainz', route: { view: 'listenbrainz_playlists', username } });
                crumbs.push({ label: username, route: { view: 'listenbrainz_playlists', username } });
            } else {
                crumbs.push({ label: 'ListenBrainz' });
            }
            crumbs.push({ label: playlistTitle || 'Playlist' });
        } else if (route.view === 'lastfm_playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Last.fm' });
            crumbs.push({ label: this.exploreLastfmPlaylistName || 'Playlist' });
        } else if (route.view === 'youtube_music_playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'YouTube Music' });
            const title = route.playlistTitle || this.exploreYoutubePlaylistName || 'Playlist';
            crumbs.push({ label: title });
        } else if (route.view === 'similar_tracks') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Tracks' });
        } else if (route.view === 'similar_albums') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Albums' });
        } else if (route.view === 'similar_artists') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Artists' });
        } else if (route.view === 'fresh_finds') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Squidly' });
            crumbs.push({ label: this.freshFindsPlaylistName || 'Fresh Finds' });
        } else {
            crumbs.push({ label: 'Explore' });
        }

        this.exploreBreadcrumbRoutes = [];
        const parts: string[] = [];

        for (let index = 0; index < crumbs.length; index += 1) {
            const crumb = crumbs[index];
            const isLast = index === crumbs.length - 1;
            const safeLabel = this.escapeHtml(crumb.label);

            if (isLast || !crumb.route) {
                parts.push(`<span class="library-crumb-current">${safeLabel}</span>`);
            } else {
                const routeIndex = this.exploreBreadcrumbRoutes.push({ ...crumb.route }) - 1;
                parts.push(`<button class="library-crumb-btn" data-explore-route-index="${routeIndex}">${safeLabel}</button>`);
            }

            if (!isLast) {
                parts.push('<span class="library-crumb-separator">&gt;</span>');
            }
        }

        this.exploreBreadcrumbContainer.innerHTML = parts.join('');
        this.exploreBreadcrumbContainer.style.display = parts.length > 0 ? 'flex' : 'none';
    }

    private renderTopBarTitle(title: string): void {
        const topBarLeft = document.querySelector('.top-bar-left');
        if (!topBarLeft) {
            return;
        }

        topBarLeft.innerHTML = `<h2>${this.escapeHtml(title)}</h2>`;
    }

    constructor() {
        // New page navigation elements
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e: Event) => {
                e.preventDefault();
                const page = (item as HTMLElement).getAttribute('data-page');
                if (page) {
                    this.switchPage(page);
                    this.closeMobileMenu();
                }
            });
        });

        this.searchInput = document.getElementById('searchInput') as HTMLInputElement;
        this.searchTypeSelect = document.getElementById('searchType') as HTMLSelectElement;
        this.searchButton = document.getElementById('searchButton') as HTMLButtonElement;
        this.exploreBreadcrumbContainer = document.getElementById('exploreBreadcrumb');
        this.libraryBreadcrumbContainer = document.getElementById('libraryBreadcrumb');
        this.resultsContainer = document.getElementById('results') as HTMLElement;
        this.libraryResultsContainer = document.getElementById('libraryResults') as HTMLElement;

        // Old flyout elements (may not exist in new layout)
        this.statusButton = document.getElementById('statusButton') as HTMLButtonElement;
        this.statusFlyout = document.getElementById('statusFlyout') as HTMLElement;
        this.flyoutOverlay = document.getElementById('flyoutOverlay') as HTMLElement;
        this.closeFlyoutButton = document.getElementById('closeFlyout') as HTMLButtonElement;
        this.flyoutContent = document.getElementById('flyoutContent') as HTMLElement;
        this.addMirrorButton = document.getElementById('addMirrorButton') as HTMLButtonElement;
        this.jobsButton = document.getElementById('jobsButton') as HTMLButtonElement;
        this.jobsFlyout = document.getElementById('jobsFlyout') as HTMLElement;
        this.jobsOverlay = document.getElementById('jobsOverlay') as HTMLElement;
        this.closeJobsButton = document.getElementById('closeJobs') as HTMLButtonElement;
        this.jobsFilterSelect = document.getElementById('jobsFilter') as HTMLSelectElement;
        this.cancelPendingJobsButton = document.getElementById('cancelPendingJobs') as HTMLButtonElement;
        this.retryAllJobsButton = document.getElementById('retryAllJobs') as HTMLButtonElement;
        this.jobsContent = document.getElementById('jobsContent') as HTMLElement;
        this.jobsPagination = document.getElementById('jobsPagination') as HTMLElement;
        this.matchReviewRunScanButton = document.getElementById('startHifiMatchScan') as HTMLButtonElement;
        this.matchReviewRefreshButton = document.getElementById('refreshHifiMatchReview') as HTMLButtonElement;
        this.matchReviewEntityFilter = document.getElementById('matchReviewEntityFilter') as HTMLSelectElement;
        this.matchReviewMaxConfidenceInput = document.getElementById('matchReviewMaxConfidence') as HTMLInputElement;
        this.matchReviewStatusEl = document.getElementById('matchReviewStatus') as HTMLElement;
        this.matchReviewActivity = document.getElementById('matchReviewActivity') as HTMLElement;
        this.matchReviewSummary = document.getElementById('matchReviewSummary') as HTMLElement;
        this.matchReviewContent = document.getElementById('matchReviewContent') as HTMLElement;
        this.historyTableContainer = document.getElementById('historyTableContainer') as HTMLElement;
        this.settingsButton = document.getElementById('settingsButton') as HTMLButtonElement;
        this.settingsFlyout = document.getElementById('settingsFlyout') as HTMLElement;
        this.settingsOverlay = document.getElementById('settingsOverlay') as HTMLElement;
        this.closeSettingsButton = document.getElementById('closeSettings') as HTMLButtonElement;
        this.qualityLosslessInput = document.getElementById('qualityLossless') as HTMLInputElement;
        this.qualityHighInput = document.getElementById('qualityHigh') as HTMLInputElement;
        this.qualityLowInput = document.getElementById('qualityLow') as HTMLInputElement;
        this.downloadSourceTidalInput = document.getElementById('downloadSourceTidal') as HTMLInputElement;
        this.downloadSourceQobuzInput = document.getElementById('downloadSourceQobuz') as HTMLInputElement;
        this.fileNamingAlbumInput = document.getElementById('fileNamingAlbum') as HTMLInputElement;
        this.jobsRefreshIntervalSecondsInput = document.getElementById('jobsRefreshIntervalSeconds') as HTMLInputElement;
        this.listenbrainzTokenInput = document.getElementById('listenbrainzToken') as HTMLInputElement;
        this.listenbrainzUsernameInput = document.getElementById('listenbrainzUsername') as HTMLInputElement;
        this.saveLbConfigButton = document.getElementById('saveLbConfig') as HTMLButtonElement;
        this.lbConfigStatusEl = document.getElementById('lbConfigStatus') as HTMLElement;
        this.ytmCookieInput = document.getElementById('ytmCookie') as HTMLInputElement;
        this.saveYtmConfigButton = document.getElementById('saveYtmConfig') as HTMLButtonElement;
        this.ytmConfigStatusEl = document.getElementById('ytmConfigStatus') as HTMLElement;
        this.autoDownloadFreshFindsCheckbox = document.getElementById('autoDownloadFreshFinds') as HTMLInputElement;
        this.freshFindsAutoDownloadStatusEl = document.getElementById('freshFindsAutoDownloadStatus') as HTMLElement;
        this.freshFindsRetentionInput = document.getElementById('freshFindsRetentionCount') as HTMLInputElement;
        this.freshFindsRetentionStatusEl = document.getElementById('freshFindsRetentionStatus') as HTMLElement;
        this.plexLoginButton = document.getElementById('plexLoginButton') as HTMLButtonElement;
        this.plexPinContainer = document.getElementById('plexPinContainer') as HTMLElement;
        this.plexPinDisplay = document.getElementById('plexPinDisplay') as HTMLElement;
        this.plexPinCopyButton = document.getElementById('plexPinCopy') as HTMLButtonElement;
        this.plexPinStatus = document.getElementById('plexPinStatus') as HTMLElement;
        this.plexLoginOnlyContainer = document.getElementById('plexLoginOnlyContainer') as HTMLElement;
        this.plexLoginOnlyButton = document.getElementById('plexLoginOnlyButton') as HTMLButtonElement;
        this.plexLoginOnlyPinContainer = document.getElementById('plexLoginOnlyPinContainer') as HTMLElement;
        this.plexLoginOnlyPinDisplay = document.getElementById('plexLoginOnlyPinDisplay') as HTMLElement;
        this.plexLoginOnlyPinStatus = document.getElementById('plexLoginOnlyPinStatus') as HTMLElement;
        this.plexLoginOnlyLibraryContainer = document.getElementById('plexLoginOnlyLibraryContainer') as HTMLElement;
        this.plexLoginOnlyLibraryNameSelect = document.getElementById('plexLoginOnlyLibraryName') as HTMLSelectElement;
        this.plexLoginOnlySaveButton = document.getElementById('plexLoginOnlySaveButton') as HTMLButtonElement;
        this.plexLoginOnlyUserContainer = document.getElementById('plexLoginOnlyUserContainer') as HTMLElement;
        this.plexLoginOnlyUserList = document.getElementById('plexLoginOnlyUserList') as HTMLElement;
        this.appWrapper = document.querySelector('.app-wrapper') as HTMLElement;
        this.plexPlaylistNameInput = document.getElementById('plexPlaylistName') as HTMLInputElement | null;
        this.plexPlaylistOptions = document.getElementById('plexPlaylistOptions') as HTMLSelectElement | null;
        this.plexPlaylistBackButton = document.getElementById('plexPlaylistBack') as HTMLButtonElement | null;
        this.savePlexConfigButton = document.getElementById('savePlexConfig') as HTMLButtonElement;
        this.plexSyncIntervalHoursInput = document.getElementById('plexSyncIntervalHours') as HTMLInputElement;
        this.startPlexSyncButton = document.getElementById('startPlexSync') as HTMLButtonElement;
        this.plexSyncStatusEl = document.getElementById('plexSyncStatus') as HTMLElement;
        this.plexConfigStatusEl = document.getElementById('plexConfigStatus') as HTMLElement;
        this.plexConnectedStatusEl = document.getElementById('plexConnectedStatus') as HTMLElement;
        this.plexClearCredentialsButton = document.getElementById('plexClearCredentialsButton') as HTMLButtonElement;
        this.plexUserDropdownContainer = document.getElementById('plexUserDropdownContainer') as HTMLElement;
        this.ignoreMatchesCheckbox = document.getElementById('ignoreMatchesCheckbox') as HTMLInputElement;
        this.tagTitleCheckbox = document.getElementById('tagTitle') as HTMLInputElement;
        this.tagArtistCheckbox = document.getElementById('tagArtist') as HTMLInputElement;
        this.tagAlbumArtistCheckbox = document.getElementById('tagAlbumArtist') as HTMLInputElement;
        this.tagAlbumCheckbox = document.getElementById('tagAlbum') as HTMLInputElement;
        this.tagYearCheckbox = document.getElementById('tagYear') as HTMLInputElement;
        this.tagTrackNumberCheckbox = document.getElementById('tagTrackNumber') as HTMLInputElement;
        this.tagTrackTotalCheckbox = document.getElementById('tagTrackTotal') as HTMLInputElement;
        this.tagDiscNumberCheckbox = document.getElementById('tagDiscNumber') as HTMLInputElement;
        this.tagDiscTotalCheckbox = document.getElementById('tagDiscTotal') as HTMLInputElement;
        this.tagVersionCheckbox = document.getElementById('tagVersion') as HTMLInputElement;
        this.tagTidalTrackIdCheckbox = document.getElementById('tagTidalTrackId') as HTMLInputElement;
        this.tagTidalAlbumIdCheckbox = document.getElementById('tagTidalAlbumId') as HTMLInputElement;
        this.tagIsrcCheckbox = document.getElementById('tagIsrc') as HTMLInputElement;
        this.tagCopyrightCheckbox = document.getElementById('tagCopyright') as HTMLInputElement;
        this.tagCoverArtCheckbox = document.getElementById('tagCoverArt') as HTMLInputElement;
        this.tagExplicitCheckbox = document.getElementById('tagExplicit') as HTMLInputElement;
        this.tagExplicitSuffixCheckbox = document.getElementById('tagExplicitSuffix') as HTMLInputElement;
        this.penaltyCompilationCheckbox = document.getElementById('penaltyCompilation') as HTMLInputElement;
        this.penaltyKaraokeCheckbox = document.getElementById('penaltyKaraoke') as HTMLInputElement;
        this.penaltyLiveCheckbox = document.getElementById('penaltyLive') as HTMLInputElement;

        // User dropdown for top bar
        this.userButton = document.getElementById('userButton') as HTMLButtonElement;
        this.userDropdownModal = document.getElementById('userDropdownModal') as HTMLElement;
        this.userDropdownOverlay = document.getElementById('userDropdownOverlay') as HTMLElement;
        this.userDropdownList = document.getElementById('userDropdownList') as HTMLElement;
        this.userButtonText = document.getElementById('userButtonText') as HTMLElement;

        // Mobile menu
        this.mobileMenuToggle = document.getElementById('mobileMenuToggle') as HTMLButtonElement | null;
        this.mobileMenuOverlay = document.getElementById('mobileMenuOverlay') as HTMLElement | null;

        this.initializeEventListeners();
        this.downloadSettings = this.defaultDownloadSettings();
        this.applySettingsToForm(this.downloadSettings);

        // Initialize page navigation (start with Explore page)
        this.switchPage('explore', false);

        this.initializeHistoryNavigation();
        this.initializeHistoryControls();
        void this.fetchAppConfig();
        void this.fetchDownloadSettingsFromServer();
        void this.loadListenbrainzConfig();
        void this.loadYtmConfig();
        void this.loadFreshFindsAutoDownload();
        void this.loadFreshFindsRetention();
        void this.loadPlexConfig();
        void this.updatePlexClearCredentialsButton();

        // Initialize user button and sidebar playlists
        void this.initializeUserButton();

        this.updateEndpointStatus(); // Initial load

        // Update status every 30 seconds
        this.statusUpdateInterval = window.setInterval(() => {
            this.updateEndpointStatus();
        }, 30000);
    }

    private initializeEventListeners(): void {
        if (this.searchButton) {
            this.searchButton.addEventListener('click', () => this.handleSearch());
        }
        if (this.searchInput) {
            this.searchInput.addEventListener('keypress', (e: KeyboardEvent) => {
                if (e.key === 'Enter') {
                    this.handleSearch();
                }
            });
        }

        if (this.exploreBreadcrumbContainer) {
            this.exploreBreadcrumbContainer.addEventListener('click', (e: Event) => {
                const target = e.target as HTMLElement;
                const button = target.closest('[data-explore-route-index]') as HTMLElement | null;
                if (button) {
                    e.preventDefault();
                    e.stopPropagation();
                    const routeIndex = Number(button.getAttribute('data-explore-route-index') || '-1');
                    if (Number.isInteger(routeIndex) && routeIndex >= 0 && routeIndex < this.exploreBreadcrumbRoutes.length) {
                        void this.navigateToRoute({ ...this.exploreBreadcrumbRoutes[routeIndex] }, true);
                    }
                }
            });
        }

        if (this.libraryBreadcrumbContainer) {
            this.libraryBreadcrumbContainer.addEventListener('click', (e: MouseEvent) => {
                const target = e.target as HTMLElement;
                const breadcrumbButton = target.closest('[data-library-crumb]') as HTMLButtonElement | null;
                if (!breadcrumbButton) {
                    return;
                }

                e.preventDefault();
                const crumb = breadcrumbButton.getAttribute('data-library-crumb');
                if (crumb === 'library') {
                    void this.loadLibraryArtists(0);
                    return;
                }
                if (crumb === 'artist' && this.libraryCurrentArtist) {
                    void this.loadLibraryArtistAlbums(this.libraryCurrentArtist.id, this.libraryCurrentArtist.name);
                }
            });
        }

        // User dropdown listeners
        if (this.userButton) {
            console.log('[DEBUG] Attaching user button listener');
            this.userButton.addEventListener('click', () => {
                console.log('[DEBUG] User button clicked');
                this.openUserDropdown();
            });
        } else {
            console.error('[DEBUG] userButton element not found');
        }
        if (this.userDropdownOverlay) {
            this.userDropdownOverlay.addEventListener('click', () => this.closeUserDropdown());
        }
        const userDropdownClose = document.getElementById('userDropdownClose');
        if (userDropdownClose) {
            userDropdownClose.addEventListener('click', () => this.closeUserDropdown());
        }

        // Mobile menu listeners
        if (this.mobileMenuToggle) {
            this.mobileMenuToggle.addEventListener('click', () => this.toggleMobileMenu());
        }
        if (this.mobileMenuOverlay) {
            this.mobileMenuOverlay.addEventListener('click', () => this.closeMobileMenu());
        }

        // Old flyout listeners (safe if elements don't exist)
        if (this.statusButton) {
            this.statusButton.addEventListener('click', () => this.openFlyout());
        }
        if (this.closeFlyoutButton) {
            this.closeFlyoutButton.addEventListener('click', () => this.closeFlyout());
        }
        if (this.flyoutOverlay) {
            this.flyoutOverlay.addEventListener('click', () => this.closeFlyout());
        }
        if (this.flyoutContent) {
            this.flyoutContent.addEventListener('click', (e: MouseEvent) => {
                void this.handleFlyoutContentClick(e);
            });
        }

        if (this.addMirrorButton) {
            this.addMirrorButton.addEventListener('click', () => this.openAddMirrorModal());
        }

        if (this.jobsButton) {
            this.jobsButton.addEventListener('click', () => this.openJobsFlyout());
        }
        if (this.closeJobsButton) {
            this.closeJobsButton.addEventListener('click', () => this.closeJobsFlyout());
        }
        if (this.jobsOverlay) {
            this.jobsOverlay.addEventListener('click', () => this.closeJobsFlyout());
        }
        if (this.jobsFilterSelect) {
            this.jobsFilterSelect.addEventListener('change', () => {
                this.currentJobsPage = 1;
                this.updateJobsActionButtons(0, this.jobsFilterSelect.value, 0);
                void this.loadJobs();
            });
        }
        if (this.cancelPendingJobsButton) {
            this.cancelPendingJobsButton.addEventListener('click', () => {
                void this.cancelAllJobs();
            });
        }
        if (this.retryAllJobsButton) {
            this.retryAllJobsButton.addEventListener('click', () => {
                void this.retryAllFilteredJobs();
            });
        }
        if (this.jobsContent) {
            this.jobsContent.addEventListener('click', (e: MouseEvent) => {
                void this.handleJobsContentClick(e);
            });
        }
        if (this.matchReviewRunScanButton) {
            this.matchReviewRunScanButton.addEventListener('click', () => {
                if (this.activeMatchActivityJobId) {
                    void this.cancelLibraryUpdate(this.activeMatchActivityJobId);
                    return;
                }

                void this.startLibraryUpdate();
            });
        }
        if (this.matchReviewRefreshButton) {
            this.matchReviewRefreshButton.addEventListener('click', () => {
                this.matchCandidateCache.clear();
                void this.loadMatchReview();
            });
        }
        if (this.matchReviewEntityFilter) {
            this.matchReviewEntityFilter.addEventListener('change', () => {
                this.matchCandidateCache.clear();
                void this.loadMatchReview();
            });
        }
        if (this.matchReviewMaxConfidenceInput) {
            this.matchReviewMaxConfidenceInput.addEventListener('change', () => {
                this.matchCandidateCache.clear();
                void this.loadMatchReview();
            });
        }
        if (this.matchReviewContent) {
            this.matchReviewContent.addEventListener('click', (e: MouseEvent) => {
                void this.handleMatchReviewClick(e);
            });
            this.matchReviewContent.addEventListener('keydown', (e: KeyboardEvent) => {
                void this.handleMatchReviewKeydown(e);
            });
        }

        if (this.settingsButton) {
            this.settingsButton.addEventListener('click', () => this.openSettingsFlyout());
        }
        if (this.closeSettingsButton) {
            this.closeSettingsButton.addEventListener('click', () => this.closeSettingsFlyout());
        }
        if (this.settingsOverlay) {
            this.settingsOverlay.addEventListener('click', () => this.closeSettingsFlyout());
        }

        if (this.qualityLosslessInput) {
            this.qualityLosslessInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.qualityHighInput) {
            this.qualityHighInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.qualityLowInput) {
            this.qualityLowInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.downloadSourceTidalInput) {
            this.downloadSourceTidalInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.downloadSourceQobuzInput) {
            this.downloadSourceQobuzInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.fileNamingAlbumInput) {
            this.fileNamingAlbumInput.addEventListener('input', () => this.updateSettingsFromForm());
        }
        if (this.jobsRefreshIntervalSecondsInput) {
            this.jobsRefreshIntervalSecondsInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.ignoreMatchesCheckbox) {
            this.ignoreMatchesCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagTitleCheckbox) {
            this.tagTitleCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagArtistCheckbox) {
            this.tagArtistCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagAlbumArtistCheckbox) {
            this.tagAlbumArtistCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagAlbumCheckbox) {
            this.tagAlbumCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagYearCheckbox) {
            this.tagYearCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagTrackNumberCheckbox) {
            this.tagTrackNumberCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagTrackTotalCheckbox) {
            this.tagTrackTotalCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagDiscNumberCheckbox) {
            this.tagDiscNumberCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagDiscTotalCheckbox) {
            this.tagDiscTotalCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagVersionCheckbox) {
            this.tagVersionCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagTidalTrackIdCheckbox) {
            this.tagTidalTrackIdCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagTidalAlbumIdCheckbox) {
            this.tagTidalAlbumIdCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagIsrcCheckbox) {
            this.tagIsrcCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagCopyrightCheckbox) {
            this.tagCopyrightCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagCoverArtCheckbox) {
            this.tagCoverArtCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagExplicitCheckbox) {
            this.tagExplicitCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.tagExplicitSuffixCheckbox) {
            this.tagExplicitSuffixCheckbox.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.saveLbConfigButton) {
            this.saveLbConfigButton.addEventListener('click', () => this.saveListenbrainzConfig());
        }
        if (this.saveYtmConfigButton) {
            this.saveYtmConfigButton.addEventListener('click', () => this.saveYtmConfig());
        }
        if (this.autoDownloadFreshFindsCheckbox) {
            this.autoDownloadFreshFindsCheckbox.addEventListener('change', () => this.saveFreshFindsAutoDownload());
        }
        if (this.freshFindsRetentionInput) {
            this.freshFindsRetentionInput.addEventListener('change', () => this.saveFreshFindsRetention());
        }
        if (this.savePlexConfigButton) {
            this.savePlexConfigButton.addEventListener('click', () => {
                void this.savePlexConfig();
            });
        }
        // Remove save/test config listeners, add PIN login logic
        if (this.plexLoginButton) {
            this.plexLoginButton.addEventListener('click', async () => {
                await this.startPlexPinLogin();
                void this.updatePlexClearCredentialsButton();
                void this.loadPlexLibraries();
            });
        }

        if (this.plexLoginOnlyButton) {
            this.plexLoginOnlyButton.addEventListener('click', async () => {
                this.plexLoginOnlyButton.style.display = 'none';
                await this.startPlexPinLogin();
                void this.updatePlexClearCredentialsButton();
                void this.loadPlexLibraries();
            });
        }

        if (this.plexLoginOnlySaveButton) {
            this.plexLoginOnlySaveButton.addEventListener('click', async () => {
                await this.savePlexConfigFromLoginOnly();
            });
        }

        if (this.plexClearCredentialsButton) {
            this.plexClearCredentialsButton.addEventListener('click', async () => {
                try {
                    const resp = await fetch('/api/plex/clear_credentials', { method: 'POST' });
                    if (!resp.ok) {
                        throw new Error('Failed to clear Plex credentials');
                    }

                    // Ensure the cached health status is updated (server sets ok=false when credentials are cleared)
                    await fetch('/api/plex/health', { cache: 'no-store' });
                } catch (e) {
                    console.warn('Failed to clear Plex credentials:', e);
                } finally {
                    // Immediately reflect cleared state in the UI, regardless of timing
                    if (this.plexClearCredentialsButton) {
                        this.plexClearCredentialsButton.style.display = 'none';
                    }
                    if (this.plexLoginButton) {
                        this.plexLoginButton.style.display = '';
                        this.plexLoginButton.disabled = false;
                    }
                    if (this.userButtonText) {
                        this.userButtonText.textContent = 'User';
                    }

                    window.localStorage.removeItem('plexSelectedUserId');
                    window.localStorage.removeItem('plexSelectedUserName');
                    window.localStorage.removeItem('plexSelectedUserIsOwner');
                    this.isPlexSelectedUserOwner = false;
                    await this.loadPlexConfig();
                    void this.updatePlexClearCredentialsButton();
                }
            });
        }

        // User selection is handled via buttons rendered in the Plex login-only overlay.

        const copyPlexPin = (): void => {
            const pin = this.plexPinDisplay?.textContent || this.plexLoginOnlyPinDisplay?.textContent || '';
            if (pin) {
                navigator.clipboard.writeText(pin);
                const statusEl = this.plexPinStatus || this.plexLoginOnlyPinStatus;
                if (statusEl) {
                    statusEl.textContent = 'PIN copied!';
                    setTimeout(() => {
                        if (statusEl) {
                            statusEl.textContent = '';
                        }
                    }, 1500);
                }
            }
        };

        if (this.plexPinCopyButton) {
            this.plexPinCopyButton.addEventListener('click', copyPlexPin);
        }
        if (this.startPlexSyncButton) {
            this.startPlexSyncButton.addEventListener('click', () => this.startPlexSync());
        }
        if (this.plexPlaylistOptions) {
            const playlistOptions = this.plexPlaylistOptions;
            this.plexPlaylistOptions.addEventListener('change', () => {
                const selectedName = playlistOptions.value.trim();
                if (selectedName === App.NEW_PLEX_PLAYLIST_OPTION) {
                    this.setPlexPlaylistMode('new');
                    if (this.plexPlaylistNameInput) {
                        this.plexPlaylistNameInput.value = '';
                        this.plexPlaylistNameInput.focus();
                    }
                    return;
                }

                if (selectedName && this.plexPlaylistNameInput) {
                    this.plexPlaylistNameInput.value = selectedName;
                } else if (this.plexPlaylistNameInput) {
                    this.plexPlaylistNameInput.value = '';
                }

                this.setPlexPlaylistMode('existing');
            });
        }
        if (this.plexPlaylistBackButton) {
            this.plexPlaylistBackButton.addEventListener('click', () => {
                this.setPlexPlaylistMode('existing');
                if (this.plexPlaylistOptions) {
                    this.plexPlaylistOptions.value = '';
                }
                if (this.plexPlaylistNameInput) {
                    this.plexPlaylistNameInput.value = '';
                }
            });
        }

        // Update placeholder text based on search type
        if (this.searchTypeSelect) {
            this.searchTypeSelect.addEventListener('change', () => this.updateSearchPlaceholder());
        }

        // Download button and album card click delegation
        if (this.resultsContainer) {
            this.resultsContainer.addEventListener('click', (e: MouseEvent) => {
                const target = e.target as HTMLElement;

                // Check for grid play button clicks
                const gridPlayBtn = target.closest('.grid-play-btn') as HTMLButtonElement | null;
                if (gridPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const trackRow = gridPlayBtn.closest('.tracks-grid-row') as HTMLElement;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void this.handlePlayToggle(parseInt(trackId, 10), trackRow, gridPlayBtn);
                            return;
                        }
                    }

                    // Check for album grid play button
                    const albumRow = gridPlayBtn.closest('.albums-grid-row') as HTMLElement;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-album-id');
                        if (albumId) {
                            void this.handlePlayAlbum(parseInt(albumId, 10), gridPlayBtn);
                            return;
                        }
                    }
                    return;
                }

                // Check for album row clicks (anywhere except actions column)
                const albumRow = target.closest('.albums-grid-row') as HTMLElement | null;
                if (albumRow && !target.closest('.grid-cell.grid-col-actions')) {
                    e.preventDefault();
                    e.stopPropagation();
                    const albumId = albumRow.getAttribute('data-album-id');
                    if (albumId) {
                        void this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                    }
                    return;
                }

                // Check for grid add to playlist button clicks
                const gridAddPlaylistBtn = target.closest('.grid-add-playlist-btn');
                if (gridAddPlaylistBtn) {
                    const trackRow = gridAddPlaylistBtn.closest('.tracks-grid-row') as HTMLElement;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void this.handleAddToPlaylist(parseInt(trackId, 10), trackRow, 'loose');
                            return;
                        }
                    }

                    // Check for album grid
                    const albumRow = gridAddPlaylistBtn.closest('.albums-grid-row') as HTMLElement;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-album-id');
                        if (albumId) {
                            void this.handleAddAlbumToPlaylist(parseInt(albumId, 10), albumRow);
                            return;
                        }
                    }
                    return;
                }

                // Check for Plex existing chip clicks (re-download prompt)
                const plexChip = target.closest('.plex-existing-chip');
                if (plexChip) {
                    e.preventDefault();
                    e.stopPropagation();

                    const trackRow = plexChip.closest('.tracks-grid-row') as HTMLElement;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void this.handleRedownloadTrack(parseInt(trackId, 10), trackRow, plexChip as HTMLElement);
                        }
                        return;
                    }

                    const albumRow = plexChip.closest('.albums-grid-row') as HTMLElement;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-album-id');
                        if (albumId) {
                            void this.handleRedownloadAlbum(parseInt(albumId, 10), albumRow, plexChip as HTMLElement);
                        }
                        return;
                    }
                }

                // Check for grid add to library button clicks
                const gridAddLibraryBtn = target.closest('.grid-add-library-btn');
                if (gridAddLibraryBtn) {
                    const trackRow = gridAddLibraryBtn.closest('.tracks-grid-row') as HTMLElement;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void this.handleDownload(parseInt(trackId, 10), trackRow, 'loose');
                            return;
                        }
                    }

                    // Check for album grid
                    const albumRow = gridAddLibraryBtn.closest('.albums-grid-row') as HTMLElement;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-album-id');
                        if (albumId) {
                            void this.handleDownloadAlbum(parseInt(albumId, 10), albumRow);
                            return;
                        }
                    }
                    return;
                }

                // Check for grid "More Like This" button clicks
                const gridMoreBtn = target.closest('.grid-more-btn') as HTMLButtonElement | null;
                if (gridMoreBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const trackRow = gridMoreBtn.closest('.tracks-grid-row') as HTMLElement | null;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void this.navigateToRoute({ view: 'similar_tracks', trackId: parseInt(trackId, 10) }, true);
                            return;
                        }
                    }

                    // Check for album grid
                    const albumRow = gridMoreBtn.closest('.albums-grid-row') as HTMLElement | null;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-album-id');
                        if (albumId) {
                            void this.navigateToRoute({ view: 'similar_albums', albumId: parseInt(albumId, 10) }, true);
                            return;
                        }
                    }
                }

                // Check for play button clicks first
                const playBtn = target.closest('.track-play-btn') as HTMLButtonElement | null;
                if (playBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const trackCard = playBtn.closest('.track-card') as HTMLElement;
                    const trackId = trackCard?.getAttribute('data-track-id');
                    if (trackId) {
                        void this.handlePlayToggle(parseInt(trackId, 10), trackCard, playBtn);
                    }
                    return;
                }

                // Check for add to playlist button clicks
                const addPlaylistBtn = target.closest('.track-add-playlist-btn');
                if (addPlaylistBtn) {
                    const trackCard = addPlaylistBtn.closest('.track-card') as HTMLElement;
                    const trackId = trackCard?.getAttribute('data-track-id');
                    if (trackId) {
                        void this.handleAddToPlaylist(parseInt(trackId, 10), trackCard, 'loose');
                    }
                    return;
                }

                // Check for download button clicks
                const downloadBtn = target.closest('.track-download-btn');
                if (downloadBtn) {
                    const trackCard = downloadBtn.closest('.track-card') as HTMLElement;
                    const trackId = trackCard?.getAttribute('data-track-id');
                    if (trackId) {
                        void this.handleDownload(parseInt(trackId, 10), trackCard, 'loose');
                    }
                    return; // Stop here if it was a download button
                }

                // Check for "More Like This" actions before generic card click handlers
                const moreLikeBtn = target.closest('.track-more-btn') as HTMLButtonElement | null;
                if (moreLikeBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const card = moreLikeBtn.closest('.track-card') as HTMLElement | null;
                    if (!card) {
                        return;
                    }

                    const trackId = card.getAttribute('data-track-id');
                    if (trackId) {
                        void this.navigateToRoute({ view: 'similar_tracks', trackId: parseInt(trackId, 10) }, true);
                        return;
                    }

                    if (card.classList.contains('album-card')) {
                        const albumId = card.getAttribute('data-album-id');
                        if (albumId) {
                            void this.navigateToRoute({ view: 'similar_albums', albumId: parseInt(albumId, 10) }, true);
                        }
                        return;
                    }

                    if (card.classList.contains('artist-card')) {
                        const artistId = card.getAttribute('data-artist-id');
                        if (artistId) {
                            void this.navigateToRoute({ view: 'similar_artists', artistId: parseInt(artistId, 10) }, true);
                        }
                        return;
                    }
                }

                // Check for artist card compact button clicks (Find Similar)
                const artistCardBtn = target.closest('.artist-card-btn') as HTMLButtonElement | null;
                if (artistCardBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const artistCard = artistCardBtn.closest('.artist-card-compact') as HTMLElement | null;
                    if (artistCard) {
                        const artistId = artistCard.getAttribute('data-artist-id');
                        if (artistId) {
                            void this.navigateToRoute({ view: 'similar_artists', artistId: parseInt(artistId, 10) }, true);
                        }
                    }
                    return;
                }

                // Check for artist card compact clicks (view artist albums)
                const artistCardCompact = target.closest('.artist-card-compact.clickable') as HTMLElement | null;
                if (artistCardCompact && !target.closest('.artist-card-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    const artistId = artistCardCompact.getAttribute('data-artist-id');
                    if (artistId) {
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                    }
                    return;
                }

                // Check for artist name clicks within grid rows
                const gridArtistName = target.closest('.tracks-grid-row .track-artist-name');
                if (gridArtistName) {
                    const trackRow = gridArtistName.closest('.tracks-grid-row');
                    const artistId = trackRow?.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }

                // Check for artist name clicks within album hero header
                const heroArtistName = target.closest('.album-hero-content .track-artist-name') as HTMLElement | null;
                if (heroArtistName) {
                    const artistId = heroArtistName.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }

                // Check for album name clicks within grid rows
                const gridAlbumName = target.closest('.tracks-grid-row .track-album-name');
                if (gridAlbumName) {
                    const trackRow = gridAlbumName.closest('.tracks-grid-row');
                    const albumId = trackRow?.getAttribute('data-album-id');
                    if (albumId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                        return;
                    }
                }

                // Check for artist name clicks within album grid rows
                const gridAlbumArtistName = target.closest('.albums-grid-row .album-artist-name');
                if (gridAlbumArtistName) {
                    const albumRow = gridAlbumArtistName.closest('.albums-grid-row');
                    const artistId = albumRow?.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }

                // Check for artist name clicks within track cards
                const artistName = target.closest('.track-card .track-artist-name');
                if (artistName) {
                    const trackCard = artistName.closest('.track-card');
                    const artistId = trackCard?.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }

                // Check for album name clicks within track cards
                const albumName = target.closest('.track-card .track-album-name');
                if (albumName) {
                    const trackCard = albumName.closest('.track-card');
                    const albumId = trackCard?.getAttribute('data-album-id');
                    if (albumId) {
                        e.stopPropagation();
                        void this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                        return;
                    }
                }

                // Check for playlist card clicks
                const playlistCard = target.closest('.playlist-card');
                if (playlistCard) {
                    const playlistId = playlistCard.getAttribute('data-playlist-id');
                    if (playlistId) {
                        void this.navigateToRoute({ view: 'listenbrainz_playlist_tracks', playlistId, username: this.listenbrainzCurrentUsername || undefined }, true);
                        return;
                    }
                }

                // Check for search playlist card clicks
                const searchPlaylistCard = target.closest('.playlist-search-card') as HTMLElement | null;
                if (searchPlaylistCard) {
                    const playlistId = searchPlaylistCard.getAttribute('data-playlist-id');
                    if (playlistId) {
                        void this.navigateToRoute({ view: 'playlist', playlistId }, true);
                        return;
                    }
                }

                // Check for album card clicks (albums have both track-card and album-card classes)
                const clickedCard = target.closest('.track-card') as HTMLElement;
                if (clickedCard && clickedCard.classList.contains('album-card')) {
                    const albumId = clickedCard.getAttribute('data-album-id');
                    if (albumId) {
                        void this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                    }
                }

                // Check for artist card clicks
                if (clickedCard && clickedCard.classList.contains('artist-card')) {
                    const artistId = clickedCard.getAttribute('data-artist-id');
                    if (artistId) {
                        void this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                    }
                }
            });
        }

        if (this.libraryResultsContainer) {
            this.libraryResultsContainer.addEventListener('click', (e: MouseEvent) => {
                const target = e.target as HTMLElement;

                const artistHeroPlayBtn = target.closest('.library-artist-hero-play-btn') as HTMLButtonElement | null;
                if (artistHeroPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const artistId = artistHeroPlayBtn.getAttribute('data-library-artist-id') || this.libraryCurrentArtist?.id || '';
                    if (artistId) {
                        void this.handlePlayLibraryArtist(artistId, artistHeroPlayBtn);
                    }
                    return;
                }

                const albumHeroPlayBtn = target.closest('.library-album-hero-play-btn') as HTMLButtonElement | null;
                if (albumHeroPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const albumId = albumHeroPlayBtn.getAttribute('data-library-album-id') || this.libraryCurrentAlbum?.id || '';
                    if (albumId) {
                        void this.handlePlayLibraryAlbum(albumId, albumHeroPlayBtn);
                    }
                    return;
                }

                const gridPlayBtn = target.closest('.grid-play-btn') as HTMLButtonElement | null;
                if (gridPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();

                    const trackRow = gridPlayBtn.closest('[data-library-track-id]') as HTMLElement | null;
                    if (trackRow) {
                        const trackId = trackRow.getAttribute('data-library-track-id') || '';
                        if (trackId) {
                            void this.handlePlayLibraryToggle(trackId, gridPlayBtn);
                        }
                        return;
                    }

                    const albumRow = gridPlayBtn.closest('[data-library-album-id]') as HTMLElement | null;
                    if (albumRow) {
                        const albumId = albumRow.getAttribute('data-library-album-id') || '';
                        if (albumId) {
                            void this.handlePlayLibraryAlbum(albumId, gridPlayBtn);
                        }
                        return;
                    }
                }

                const paginationButton = target.closest('[data-library-offset]') as HTMLButtonElement | null;
                if (paginationButton) {
                    e.preventDefault();
                    if (paginationButton.disabled) {
                        return;
                    }
                    const offset = Number(paginationButton.getAttribute('data-library-offset') || '0');
                    if (Number.isFinite(offset) && offset >= 0) {
                        void this.loadLibraryArtists(offset);
                    }
                    return;
                }

                const artistCard = target.closest('[data-library-artist-id]') as HTMLElement | null;
                if (artistCard) {
                    e.preventDefault();
                    const artistId = artistCard.getAttribute('data-library-artist-id') || '';
                    const artistName = artistCard.getAttribute('data-library-artist-name') || 'Artist';
                    if (artistId) {
                        void this.loadLibraryArtistAlbums(artistId, artistName);
                    }
                    return;
                }

                const trackArtistName = target.closest('.tracks-grid-row .library-track-artist-name') as HTMLElement | null;
                if (trackArtistName) {
                    e.preventDefault();
                    e.stopPropagation();
                    const artistId = trackArtistName.getAttribute('data-library-artist-id') || this.libraryCurrentArtist?.id || '';
                    const artistName = trackArtistName.getAttribute('data-library-artist-name') || this.libraryCurrentArtist?.name || 'Artist';
                    if (artistId) {
                        void this.loadLibraryArtistAlbums(artistId, artistName);
                    }
                    return;
                }

                const albumRow = target.closest('[data-library-album-id]') as HTMLElement | null;
                if (albumRow && !target.closest('.grid-cell.grid-col-actions')) {
                    e.preventDefault();
                    const albumId = albumRow.getAttribute('data-library-album-id') || '';
                    const albumTitle = albumRow.getAttribute('data-library-album-title') || 'Album';
                    const artistName = albumRow.getAttribute('data-library-artist-name') || this.libraryCurrentArtist?.name || '';
                    if (albumId) {
                        void this.loadLibraryAlbumTracks(albumId, albumTitle, artistName || undefined);
                    }
                    return;
                }

                const albumHeroArtist = target.closest('.album-hero-content .track-artist-name') as HTMLElement | null;
                if (albumHeroArtist && this.libraryCurrentArtist) {
                    e.preventDefault();
                    void this.loadLibraryArtistAlbums(this.libraryCurrentArtist.id, this.libraryCurrentArtist.name);
                }
            });
        }
    }

    private switchPage(pageName: string, updateHistory: boolean = true): void {
        const normalizedPage = this.normalizePage(pageName);
        const previousPage = this.currentPage;

        // Cancel any pending requests when switching pages
        if (this.pendingRequestController) {
            this.pendingRequestController.abort();
            this.pendingRequestController = null;
        }

        // Hide all pages
        const allPages = document.querySelectorAll('.page');
        allPages.forEach(page => {
            page.classList.remove('active');
        });

        // Show the selected page
        const selectedPage = document.getElementById(`${normalizedPage}Page`);
        if (selectedPage) {
            selectedPage.classList.add('active');
        }

        // Update active nav item
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.classList.remove('active');
            if ((item as HTMLElement).getAttribute('data-page') === normalizedPage) {
                item.classList.add('active');
            }
        });

        // Update current page
        this.currentPage = normalizedPage;

        // Update top bar title based on page
        const pageNames: Record<string, string> = {
            explore: 'Explore',
            library: 'Library',
            settings: 'Settings',
            mirrors: 'Hi-Fi Mirrors',
            matches: 'Match Review',
            jobs: 'Jobs',
            history: 'Listen History'
        };
        if (normalizedPage === 'explore') {
            this.renderTopBarTitle('Explore');
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            this.hideLibraryBreadcrumb();
        } else if (normalizedPage === 'library') {
            this.renderTopBarTitle('Library');
            if (this.exploreBreadcrumbContainer) {
                this.exploreBreadcrumbContainer.style.display = 'none';
                this.exploreBreadcrumbContainer.innerHTML = '';
            }
            this.renderLibraryBreadcrumb();
        } else {
            this.renderTopBarTitle(pageNames[normalizedPage] || 'Squidly');
            if (this.exploreBreadcrumbContainer) {
                this.exploreBreadcrumbContainer.style.display = 'none';
                this.exploreBreadcrumbContainer.innerHTML = '';
            }
            this.hideLibraryBreadcrumb();
        }

        // Refresh mirrors data when switching to mirrors page
        if (normalizedPage === 'mirrors') {
            void this.updateEndpointStatus();
        }

        // Load jobs when switching to jobs page
        if (normalizedPage === 'jobs') {
            this.currentJobsPage = 1;
            void this.loadJobs();
        }

        if (normalizedPage === 'matches') {
            void this.loadMatchActivity().then(() => {
                if (this.currentPage !== 'matches') {
                    return;
                }
                if (!this.isMatchScanActive()) {
                    void this.loadMatchReview();
                }
            });
        } else {
            this.stopMatchReviewPollingInterval();
        }

        if (normalizedPage === 'library' && !this.libraryLoadedOnce && updateHistory) {
            void this.loadLibraryArtists(0, false);
        }

        if (normalizedPage === 'history') {
            void this.loadListenHistory();
        }

        if (updateHistory && !this.isHandlingPopState && previousPage !== normalizedPage) {
            this.pushHistoryTab(normalizedPage);
        }
    }

    private setLibraryMessage(message: string): void {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.renderLibraryBreadcrumb();

        this.libraryResultsContainer.innerHTML = `
            <div class="library-placeholder">
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    private formatLibraryBreadcrumb(): string {
        const artist = this.libraryCurrentArtist;
        const album = this.libraryCurrentAlbum;
        const playlistTitle = this.libraryCurrentPlaylist;

        let trail = '<button class="library-crumb-btn" data-library-crumb="library">Library</button>';

        if (playlistTitle) {
            trail += `<span class="library-crumb-separator">&gt;</span><span class="library-crumb-current">${this.escapeHtml(playlistTitle)}</span>`;
        } else if (artist) {
            if (album) {
                trail += `<span class="library-crumb-separator">&gt;</span><button class="library-crumb-btn" data-library-crumb="artist">${this.escapeHtml(artist.name)}</button>`;
            } else {
                trail += `<span class="library-crumb-separator">&gt;</span><span class="library-crumb-current">${this.escapeHtml(artist.name)}</span>`;
            }
        }

        if (album) {
            trail += `<span class="library-crumb-separator">&gt;</span><span class="library-crumb-current">${this.escapeHtml(album.title)}</span>`;
        }

        return trail;
    }

    private renderLibraryBreadcrumb(): void {
        if (!this.libraryBreadcrumbContainer) {
            return;
        }

        const trail = this.formatLibraryBreadcrumb();
        this.libraryBreadcrumbContainer.innerHTML = trail;
        this.libraryBreadcrumbContainer.style.display = trail ? 'flex' : 'none';
    }

    private hideLibraryBreadcrumb(): void {
        if (!this.libraryBreadcrumbContainer) {
            return;
        }

        this.libraryBreadcrumbContainer.innerHTML = '';
        this.libraryBreadcrumbContainer.style.display = 'none';
    }

    private formatLibraryArtistCard(artist: PlexLibraryArtist): string {
        const artistName = this.escapeHtml(artist.name || 'Unknown Artist');
        return `
            <div class="artist-card-compact clickable" data-library-artist-id="${this.escapeHtml(artist.id)}" data-library-artist-name="${artistName}" title="View albums by ${artistName}">
                <div class="artist-card-name">${artistName}</div>
                <div class="artist-card-image">
                    ${artist.picture
                ? `<img src="${artist.picture}" alt="${artistName}" loading="lazy">`
                : `<div class="artist-card-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="8" r="4"></circle>
                                <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"></path>
                            </svg>
                           </div>`
            }
                </div>
            </div>
        `;
    }

    private getLibraryArtistPageWindow(currentPage: number, totalPages: number): number[] {
        if (totalPages <= 1) {
            return [1];
        }

        const pages = new Set<number>([1, totalPages]);
        const windowRadius = 2;

        for (let page = currentPage - windowRadius; page <= currentPage + windowRadius; page += 1) {
            if (page >= 1 && page <= totalPages) {
                pages.add(page);
            }
        }

        return Array.from(pages).sort((a, b) => a - b);
    }

    private formatLibraryArtistPageButtons(currentPage: number, totalPages: number): string {
        const pages = this.getLibraryArtistPageWindow(currentPage, totalPages);
        const parts: string[] = [];

        for (let idx = 0; idx < pages.length; idx += 1) {
            const page = pages[idx];
            const prev = idx > 0 ? pages[idx - 1] : null;

            if (prev !== null && page - prev > 1) {
                parts.push('<span class="library-page-gap" aria-hidden="true">...</span>');
            }

            const offset = (page - 1) * this.libraryArtistsPageSize;
            const isCurrent = page === currentPage;
            parts.push(`
                <button
                    class="library-page-btn library-page-number${isCurrent ? ' is-active' : ''}"
                    data-library-offset="${offset}"
                    ${isCurrent ? 'disabled aria-current="page"' : ''}
                >${page}</button>
            `);
        }

        return parts.join('');
    }

    private renderLibraryArtists(artists: PlexLibraryArtist[]): void {
        this.libraryLoadedOnce = true;
        this.renderLibraryBreadcrumb();
        const currentPage = Math.floor(this.libraryArtistsOffset / this.libraryArtistsPageSize) + 1;
        const totalPages = Math.max(1, Math.ceil(this.libraryArtistsTotal / this.libraryArtistsPageSize));
        const firstOffset = 0;
        const lastOffset = Math.max(0, (totalPages - 1) * this.libraryArtistsPageSize);
        const prevOffset = Math.max(0, this.libraryArtistsOffset - this.libraryArtistsPageSize);
        const nextOffset = this.libraryArtistsOffset + this.libraryArtistsPageSize;
        const hasPrev = this.libraryArtistsOffset > 0;
        const hasNext = nextOffset < this.libraryArtistsTotal;

        this.libraryResultsContainer.innerHTML = `
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Artists</h2>
                </div>
            </div>
            <div class="results-list artist-results">
                ${artists.length > 0
                ? artists.map((artist) => this.formatLibraryArtistCard(artist)).join('')
                : '<div class="library-placeholder"><p>No artists found in Plex library.</p></div>'}
            </div>
            <div class="library-pagination">
                <button class="library-page-btn" data-library-offset="${firstOffset}" ${hasPrev ? '' : 'disabled'}>First</button>
                <button class="library-page-btn" data-library-offset="${prevOffset}" ${hasPrev ? '' : 'disabled'}>Previous</button>
                <span class="library-page-text">Page ${currentPage} of ${totalPages}</span>
                <div class="library-page-numbers" aria-label="Library artist page navigation">
                    ${this.formatLibraryArtistPageButtons(currentPage, totalPages)}
                </div>
                <button class="library-page-btn" data-library-offset="${nextOffset}" ${hasNext ? '' : 'disabled'}>Next</button>
                <button class="library-page-btn" data-library-offset="${lastOffset}" ${hasNext ? '' : 'disabled'}>Last</button>
            </div>
        `;
    }

    private renderLibraryArtistAlbums(artistName: string, albums: PlexLibraryAlbum[], artistPicture?: string): void {
        this.libraryLoadedOnce = true;
        this.renderLibraryBreadcrumb();
        this.libraryResultsContainer.innerHTML = `
            <div class="artist-hero-section">
                <div class="artist-hero-content">
                    <div class="artist-cover-container">
                        ${artistPicture
                ? `<img src="${artistPicture}" alt="${this.escapeHtml(artistName)}" class="artist-cover">`
                : '<div class="artist-cover-placeholder"></div>'}
                    </div>
                    <div class="artist-info">
                        <h1 class="artist-hero-name">${this.escapeHtml(artistName)}</h1>
                    </div>
                </div>
                <div class="artist-actions">
                    <button class="album-action-btn primary library-artist-hero-play-btn" data-library-artist-id="${this.escapeHtml(this.libraryCurrentArtist?.id || '')}" title="Play artist" aria-label="Play artist" ${albums.length === 0 ? 'disabled' : ''}>
                        ${this.getPlayIconSvg()}
                    </button>
                </div>
            </div>
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Albums</h2>
                </div>
            </div>
            ${this.renderAlbumGrid(albums, {
                viewMode: 'library-albums',
                includeQuality: false,
                dataAttr: 'data-library-album-id',
                extraRowClass: 'library-clickable-row',
                actions: 'play-only',
                emptyMessage: '<div class="library-placeholder"><p>No albums found for this artist.</p></div>',
                rowDataAttrs: (album) => ({
                    'data-library-album-title': album.title,
                    'data-library-artist-name': album.artist,
                }),
            })}
        `;
    }

    private renderLibraryAlbumTracks(
        albumTitle: string,
        tracks: PlexLibraryTrack[],
        albumArtist?: string,
        albumYear?: number,
        albumCover?: string
    ): void {
        this.libraryLoadedOnce = true;
        const maxDisc = tracks.reduce((maxValue, track) => {
            const disc = typeof track.disc_number === 'number' ? track.disc_number : 1;
            return Math.max(maxValue, disc);
        }, 1);

        const totalDurationSeconds = tracks.reduce((sum, track) => {
            const millis = typeof track.duration === 'number' ? track.duration : 0;
            return sum + Math.max(0, Math.round(millis / 1000));
        }, 0);
        const totalDurationMinutes = Math.floor(totalDurationSeconds / 60);
        const totalDurationHours = Math.floor(totalDurationMinutes / 60);
        const remainingMinutes = totalDurationMinutes % 60;
        const durationStr = totalDurationHours > 0
            ? `${totalDurationHours}h ${remainingMinutes}m`
            : `${totalDurationMinutes}m`;

        this.renderLibraryBreadcrumb();
        this.libraryResultsContainer.innerHTML = `
            <div class="album-hero-section">
                <div class="album-hero-content">
                    <div class="album-cover-container">
                        ${albumCover
                ? `<img src="${albumCover}" alt="${this.escapeHtml(albumTitle)}" class="album-cover">`
                : '<div class="album-cover-placeholder"></div>'}
                    </div>
                    <div class="album-info">
                        <h1 class="album-title">${this.escapeHtml(albumTitle)}</h1>
                        <p class="album-artist"><span class="track-artist-name" title="View albums by ${this.escapeHtml(albumArtist || this.libraryCurrentArtist?.name || 'Unknown Artist')}">${this.escapeHtml(albumArtist || this.libraryCurrentArtist?.name || 'Unknown Artist')}</span></p>
                        <div class="album-metadata">
                            ${albumYear ? `<span class="metadata-item">${albumYear}</span>` : ''}
                            <span class="metadata-item">${tracks.length} ${tracks.length === 1 ? 'track' : 'tracks'}</span>
                            <span class="metadata-item">${durationStr}</span>
                        </div>
                    </div>
                </div>
                <div class="album-actions">
                    <button class="album-action-btn primary library-album-hero-play-btn" data-library-album-id="${this.escapeHtml(this.libraryCurrentAlbum?.id || '')}" title="Play album" aria-label="Play album" ${tracks.length === 0 ? 'disabled' : ''}>
                        ${this.getPlayIconSvg()}
                    </button>
                </div>
            </div>
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Tracks</h2>
                </div>
            </div>
            ${this.renderTrackGrid(tracks, {
                viewMode: 'library-tracks',
                showTrackNumber: true,
                numberOfVolumes: maxDisc > 1 ? maxDisc : undefined,
                showAlbumColumn: false,
                showArtwork: false,
                dataAttr: 'data-library-track-id',
                actions: 'play-only',
                qualityStyle: 'format-bitrate',
                rowDataAttrs: (track) => ({
                    'data-plex-library-row': 'true',
                    'data-library-artist-id': String(track.artistId || ''),
                    'data-library-artist-name': track.artist,
                }),
                emptyMessage: '<div class="library-placeholder"><p>No tracks found for this album.</p></div>',
            })}
        `;
    }

    private async loadLibraryArtists(offset: number = 0, updateHistory: boolean = true): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(false);
        this.libraryCurrentArtist = null;
        this.libraryCurrentAlbum = null;
        this.libraryCurrentPlaylist = null;
        this.libraryArtistsOffset = Math.max(0, offset);

        if (updateHistory) {
            this.pushHistoryLibraryRoute({
                view: 'artists',
                offset: this.libraryArtistsOffset
            });
        }

        this.setLibraryMessage('Loading Plex artists...');

        try {
            const params = new URLSearchParams();
            params.set('offset', String(this.libraryArtistsOffset));
            params.set('limit', String(this.libraryArtistsPageSize));

            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/library/artists?${params.toString()}`, {
                cache: 'no-store',
                signal: this.pendingRequestController?.signal
            });

            const data = await response.json().catch(() => ({} as PlexLibraryArtistsResponse));
            if (!response.ok) {
                this.setLibraryMessage(data.error || 'Failed to load Plex artists.');
                return;
            }

            this.libraryArtistsTotal = typeof data.total === 'number' ? data.total : 0;
            this.libraryArtistsOffset = typeof data.offset === 'number' ? data.offset : this.libraryArtistsOffset;
            this.renderLibraryArtists(Array.isArray(data.artists) ? data.artists : []);
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                return;
            }
            console.error('[LIBRARY] Failed to load artists:', error);
            this.setLibraryMessage('Failed to load Plex artists.');
        }
    }

    private async loadLibraryArtistAlbums(artistId: string, artistName: string, updateHistory: boolean = true): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryCurrentArtist = { id: artistId, name: artistName };
        this.libraryCurrentAlbum = null;
        this.libraryCurrentPlaylist = null;

        if (updateHistory) {
            this.pushHistoryLibraryRoute({
                view: 'artist_albums',
                artistId,
                artistName
            });
        }

        this.setLibraryMessage(`Loading albums for ${artistName}...`);

        try {
            const params = new URLSearchParams();
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/library/artists/${encodeURIComponent(artistId)}/albums?${params.toString()}`, {
                cache: 'no-store',
                signal: this.pendingRequestController?.signal
            });

            const data = await response.json().catch(() => ({} as PlexLibraryArtistAlbumsResponse));
            if (!response.ok) {
                this.setLibraryMessage(data.error || 'Failed to load artist albums.');
                return;
            }

            const resolvedArtistName = data.artist?.name || artistName;
            this.libraryCurrentArtist = { id: artistId, name: resolvedArtistName };
            this.renderLibraryArtistAlbums(
                resolvedArtistName,
                Array.isArray(data.albums) ? data.albums : [],
                data.artist?.picture
            );
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                return;
            }
            console.error('[LIBRARY] Failed to load artist albums:', error);
            this.setLibraryMessage('Failed to load artist albums.');
        }
    }

    private async loadLibraryAlbumTracks(albumId: string, albumTitle: string, artistName?: string, updateHistory: boolean = true): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryCurrentAlbum = { id: albumId, title: albumTitle, artist: artistName };
        this.libraryCurrentPlaylist = null;

        if (updateHistory) {
            this.pushHistoryLibraryRoute({
                view: 'album_tracks',
                albumId,
                albumTitle,
                albumArtist: artistName,
                artistId: this.libraryCurrentArtist?.id,
                artistName: this.libraryCurrentArtist?.name
            });
        }

        this.setLibraryMessage(`Loading tracks for ${albumTitle}...`);

        try {
            const params = new URLSearchParams();
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/library/albums/${encodeURIComponent(albumId)}/tracks?${params.toString()}`, {
                cache: 'no-store',
                signal: this.pendingRequestController?.signal
            });

            const data = await response.json().catch(() => ({} as PlexLibraryAlbumTracksResponse));
            if (!response.ok) {
                this.setLibraryMessage(data.error || 'Failed to load album tracks.');
                return;
            }

            const resolvedArtist = data.album?.artist || artistName || this.libraryCurrentArtist?.name || '';
            if (this.libraryCurrentArtist && resolvedArtist) {
                this.libraryCurrentArtist = {
                    ...this.libraryCurrentArtist,
                    name: resolvedArtist
                };
            }
            const resolvedAlbumTitle = data.album?.title || albumTitle;
            this.libraryCurrentAlbum = { id: albumId, title: resolvedAlbumTitle, artist: resolvedArtist };
            this.renderLibraryAlbumTracks(
                resolvedAlbumTitle,
                Array.isArray(data.tracks) ? data.tracks : [],
                resolvedArtist,
                data.album?.year,
                data.album?.cover
            );
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                return;
            }
            console.error('[LIBRARY] Failed to load album tracks:', error);
            this.setLibraryMessage('Failed to load album tracks.');
        }
    }

    private async navigateToLibraryPlaylistTracks(playlistRatingKey: string, playlistName: string): Promise<void> {
        this.switchPage('library', false);
        await this.fetchPlexPlaylistTracks(playlistRatingKey, playlistName, true);
    }

    private async fetchPlexPlaylistTracks(playlistRatingKey: string, playlistTitle: string, updateHistory: boolean = true): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryCurrentAlbum = null;
        this.libraryCurrentArtist = null;

        if (updateHistory) {
            this.pushHistoryLibraryRoute({
                view: 'playlist_tracks',
                playlistRatingKey,
                playlistName: playlistTitle
            });
        }

        this.setLibraryMessage(`Loading tracks for ${playlistTitle}...`);

        try {
            const params = new URLSearchParams();
            params.set('rating_key', playlistRatingKey);
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/playlist/tracks?${params.toString()}`, {
                cache: 'no-store',
                signal: this.pendingRequestController?.signal
            });

            const data: PlexPlaylistTracksResponse = await response.json().catch(() => ({}) as PlexPlaylistTracksResponse);
            if (!response.ok) {
                this.setLibraryMessage(data.error || 'Failed to load playlist tracks.');
                return;
            }

            const resolvedTitle = data.playlist?.title || playlistTitle;
            this.libraryCurrentPlaylist = resolvedTitle;
            this.libraryLoadedOnce = true;
            this.renderLibraryBreadcrumb();
            const tracks = Array.isArray(data.tracks) ? data.tracks : [];

            this.libraryResultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(resolvedTitle)}</h2>
                    </div>
                </div>
                ${this.renderTrackGrid(tracks, {
                    viewMode: 'multi-album',
                    showTrackNumber: false,
                    showAlbumColumn: true,
                    showArtwork: true,
                    dataAttr: 'data-library-track-id',
                    actions: 'play-only',
                    qualityStyle: 'format-bitrate',
                    rowDataAttrs: (track) => ({
                        'data-plex-library-row': 'true',
                        'data-library-artist-id': String(track.artistId || ''),
                        'data-library-artist-name': track.artist,
                    }),
                    emptyMessage: '<div class="library-placeholder"><p>No tracks found in this playlist.</p></div>',
                })}
            `;
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                return;
            }
            console.error('[LIBRARY] Failed to load playlist tracks:', error);
            this.setLibraryMessage('Failed to load playlist tracks.');
        }
    }

    private async openUserDropdown(): Promise<void> {
        if (!this.userDropdownModal || !this.userDropdownOverlay) {
            console.error('User dropdown elements not found');
            return;
        }

        // Show the dropdown
        this.userDropdownModal.style.display = 'block';
        this.userDropdownOverlay.style.display = 'block';

        // Load users
        await this.loadPlexUsersForDropdown();
    }

    private closeUserDropdown(): void {
        if (!this.userDropdownModal || !this.userDropdownOverlay) {
            return;
        }

        this.userDropdownModal.style.display = 'none';
        this.userDropdownOverlay.style.display = 'none';
    }

    private toggleMobileMenu(): void {
        const sidebar = document.getElementById('leftSidebar');
        if (!sidebar) {
            return;
        }

        const isOpen = sidebar.classList.contains('mobile-menu-open');
        if (isOpen) {
            this.closeMobileMenu();
        } else {
            sidebar.classList.add('mobile-menu-open');
            if (this.mobileMenuOverlay) {
                this.mobileMenuOverlay.classList.add('active');
            }
            document.body.style.overflow = 'hidden';
        }
    }

    private closeMobileMenu(): void {
        const sidebar = document.getElementById('leftSidebar');
        if (sidebar) {
            sidebar.classList.remove('mobile-menu-open');
        }
        if (this.mobileMenuOverlay) {
            this.mobileMenuOverlay.classList.remove('active');
        }
        document.body.style.overflow = '';
    }

    private logoutPlexUser(): void {
        window.localStorage.removeItem('plexSelectedUserId');
        window.localStorage.removeItem('plexSelectedUserName');
        window.localStorage.removeItem('plexSelectedUserIsOwner');
        this.isPlexSelectedUserOwner = false;

        if (this.userButtonText) {
            this.userButtonText.textContent = 'User';
        }

        this.closeUserDropdown();
        void this.updateSidebarPlaylists();
        void this.updatePlexLoginOnlyState();
        this.updateUserTypeAccess();

        if (this.currentPage === 'history') {
            void this.loadListenHistory();
        }
    }

    private async loadPlexUsersForDropdown(): Promise<void> {
        if (!this.userDropdownList) {
            return;
        }

        this.userDropdownList.innerHTML = '';

        const li = document.createElement('li');
        li.className = 'user-dropdown-item logout-item';

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'save-button user-dropdown-logout-button';
        button.textContent = 'Logout';
        button.style.width = '100%';
        button.style.margin = '0';
        button.addEventListener('click', () => this.logoutPlexUser());

        li.appendChild(button);
        this.userDropdownList.appendChild(li);
    }

    private selectPlexUser(userId: string, userName: string): void {
        // Save user selection (both ID and name for better restoration)
        window.localStorage.setItem('plexSelectedUserId', userId);
        window.localStorage.setItem('plexSelectedUserName', userName);

        // Update button text
        if (this.userButtonText) {
            this.userButtonText.textContent = userName;
        }

        // Close dropdown
        this.closeUserDropdown();

        // Update sidebar playlists
        void this.updateSidebarPlaylists();

        if (this.currentPage === 'library') {
            void this.loadLibraryArtists(0, false);
        }

        if (this.currentPage === 'history') {
            void this.loadListenHistory();
        }

        void this.loadFreshFindsAutoDownload();
        void this.loadFreshFindsRetention();
    }

    private async updateSidebarPlaylists(): Promise<void> {
        let plexPlaylists: PlexPlaylist[] = [];
        const userId = window.localStorage.getItem('plexSelectedUserId') || '';

        try {
            const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
            const response = await fetch(`/api/plex/playlists${query}`, { cache: 'no-store' });
            if (response.ok) {
                const data = await response.json();
                plexPlaylists = Array.isArray(data.playlists) ? data.playlists : [];
            }
        } catch (error) {
            console.warn('Failed to load Plex playlists:', error);
        }

        this.populateSidebarPlaylists({ plex: plexPlaylists, listenbrainz: null, ytm: null });

        if (!userId) return;

        // Fetch LB playlists
        let lbData: any = null;
        try {
            let username = this.listenbrainzUsernameInput.value.trim();
            if (!username) {
                const configResp = await fetch(`/api/listenbrainz/config?user_id=${encodeURIComponent(userId)}`);
                if (configResp.ok) {
                    const configData = await configResp.json();
                    if (configData.username) username = configData.username;
                }
            }

            if (username) {
                lbData = { username, user: [], collaborator: [], createdfor: [] };
                const types = ['user', 'collaborator', 'createdfor'];

                await Promise.all(types.map(async (type) => {
                    try {
                        const query = `?username=${encodeURIComponent(username)}&user_id=${encodeURIComponent(userId)}&type=${type}`;
                        const response = await fetch(`/api/listenbrainz/playlists${query}`);
                        if (response.ok) {
                            const data = await response.json();
                            if (data.playlists) {
                                lbData[type] = data.playlists.map((item: any) => item.playlist).filter(Boolean);
                            }
                        }
                    } catch (e) {
                        console.warn(`Failed to fetch LB playlist type ${type}`, e);
                    }
                }));

                const createdForIds = new Set(lbData.createdfor.map((p: any) => p.identifier));
                lbData.collaborator = lbData.collaborator.filter((p: any) => !createdForIds.has(p.identifier));
            }
        } catch (error) {
            console.warn('Failed to load ListenBrainz sidebar playlists', error);
        }

        // Fetch YTM playlists
        let ytmPlaylists: YtmPlaylist[] | null = null;
        try {
            const configResp = await fetch(`/api/youtube_music/config?user_id=${encodeURIComponent(userId)}`);
            if (configResp.ok) {
                const configData = await configResp.json();
                if (configData.has_headers) {
                    const plResp = await fetch(`/api/youtube_music/playlists?user_id=${encodeURIComponent(userId)}`);
                    if (plResp.ok) {
                        const plData = await plResp.json();
                        ytmPlaylists = Array.isArray(plData.playlists) ? plData.playlists : [];
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to load YouTube Music sidebar playlists', error);
        }

        this.populateSidebarPlaylists({ plex: plexPlaylists, listenbrainz: lbData, ytm: ytmPlaylists });
    }

    private async initializeUserButton(): Promise<void> {
        // Load users to get the selected user's name
        try {
            console.log('[USER_INIT] Starting user button initialization');
            const savedId = window.localStorage.getItem('plexSelectedUserId') || '';
            const savedName = window.localStorage.getItem('plexSelectedUserName') || '';
            console.log('[USER_INIT] Saved user:', { savedId, savedName });

            const response = await fetch('/api/plex/users', { cache: 'no-store' });
            if (response.ok) {
                const data = await response.json();
                const users = Array.isArray(data.users) ? data.users : [];
                console.log('[USER_INIT] Fetched users:', users.length, users);

                // Try to find the currently selected user by ID
                let selectedUser = users.find((u: any) => {
                    const id = String(u.client_id ?? u.id ?? u.username ?? u.title ?? '');
                    console.log('[USER_INIT] Checking user ID:', id, 'against saved:', savedId);
                    return id === savedId;
                });

                // If not found by ID, try matching by name as fallback
                if (!selectedUser && savedName) {
                    console.log('[USER_INIT] ID match failed, trying name match for:', savedName);
                    selectedUser = users.find((u: any) => {
                        const name = String(u.username || u.title || '');
                        return name === savedName;
                    });
                }

                if (selectedUser) {
                    const userName = String(selectedUser.username || selectedUser.title || 'User');
                    const isOwner = Boolean(selectedUser.is_owner);
                    this.isPlexSelectedUserOwner = isOwner;
                    window.localStorage.setItem('plexSelectedUserIsOwner', String(isOwner));
                    console.log('[USER_INIT] Found selected user:', userName, { isOwner });
                    if (this.userButtonText) {
                        this.userButtonText.textContent = userName;
                        console.log('[USER_INIT] Updated button text to:', userName);
                    } else {
                        console.error('[USER_INIT] userButtonText element not found!');
                    }
                    // Update saved name in case it was looked up by ID
                    window.localStorage.setItem('plexSelectedUserName', userName);
                    // Load playlists for this user
                    console.log('[USER_INIT] Loading playlists for user');
                    await this.updateSidebarPlaylists();
                    this.updateUserTypeAccess();
                    await this.updatePlexLoginOnlyState();
                } else {
                    console.log('[USER_INIT] No selected user found, checking for owner');
                    if (users.length > 0) {
                        // Use the owner if no user is saved
                        const owner = users.find((u: any) => u.is_owner);
                        const ownerName = String(owner?.username || owner?.title || 'User');
                        const ownerId = String(owner?.id ?? owner?.username ?? '');
                        console.log('[USER_INIT] Using owner:', { ownerId, ownerName });
                        if (ownerId && this.userButtonText) {
                            this.userButtonText.textContent = ownerName;
                            window.localStorage.setItem('plexSelectedUserId', ownerId);
                            window.localStorage.setItem('plexSelectedUserName', ownerName);
                            window.localStorage.setItem('plexSelectedUserIsOwner', 'true');
                            this.isPlexSelectedUserOwner = true;
                            await this.updateSidebarPlaylists();
                            this.updateUserTypeAccess();
                            await this.updatePlexLoginOnlyState();
                        }
                    }
                }
            } else {
                console.error('[USER_INIT] Failed to fetch users:', response.status);
            }
        } catch (error) {
            console.error('[USER_INIT] Error during initialization:', error);
        }
    }

    private populateSidebarPlaylists(data: { plex: PlexPlaylist[], listenbrainz: any | null, ytm: YtmPlaylist[] | null }): void {
        const playlistNavItems = document.getElementById('playlistNavItems');
        if (!playlistNavItems) {
            return;
        }

        playlistNavItems.innerHTML = '';

        const getCollapsedState = (key: string): boolean => {
            const stored = localStorage.getItem(key);
            return stored !== null ? stored === 'true' : true;
        };

        const createSection = (title: string, storageKey: string): { header: HTMLLIElement, container: HTMLUListElement, toggle: () => void } => {
            const isCollapsed = getCollapsedState(storageKey);

            const header = document.createElement('li');
            header.className = 'nav-section-header collapsible';
            header.style.fontSize = '0.5rem';

            const titleSpan = document.createElement('span');
            titleSpan.className = 'nav-section-title';
            titleSpan.textContent = title;

            const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            chevron.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
            chevron.setAttribute('width', '16');
            chevron.setAttribute('height', '16');
            chevron.setAttribute('viewBox', '0 0 24 24');
            chevron.setAttribute('fill', 'none');
            chevron.setAttribute('stroke', 'currentColor');
            chevron.setAttribute('stroke-width', '2');
            chevron.setAttribute('stroke-linecap', 'round');
            chevron.setAttribute('stroke-linejoin', 'round');
            chevron.innerHTML = '<polyline points="6 9 12 15 18 9"></polyline>';
            chevron.setAttribute('class', 'section-chevron' + (isCollapsed ? ' collapsed' : ''));

            header.appendChild(titleSpan);
            header.appendChild(chevron);

            const container = document.createElement('ul');
            container.className = 'section-items' + (isCollapsed ? ' collapsed' : '');

            const toggle = () => {
                const newState = !container.classList.contains('collapsed');
                container.classList.toggle('collapsed');
                chevron.classList.toggle('collapsed');
                localStorage.setItem(storageKey, String(newState));
            };

            header.addEventListener('click', toggle);

            return { header, container, toggle };
        };

        // --- SQUIDLY Playlists (first) ---
        const squidlySection = createSection('SQUIDLY', 'sidebar_section_squidly');
        playlistNavItems.appendChild(squidlySection.header);
        playlistNavItems.appendChild(squidlySection.container);

        // --- Plex Playlists ---
        const plexSection = createSection('Plex', 'sidebar_section_plex');
        playlistNavItems.appendChild(plexSection.header);

        if (data.plex.length === 0) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.875rem';
            li.textContent = 'No playlists';
            plexSection.container.appendChild(li);
        } else {
            data.plex.forEach((playlist: PlexPlaylist) => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.className = 'nav-item';
                a.textContent = playlist.name;
                a.style.fontSize = '0.875rem';
                a.style.paddingTop = '0.25rem';
                a.style.paddingBottom = '0.25rem';
                a.addEventListener('click', (e: Event) => {
                    e.preventDefault();
                    if (playlist.ratingKey) {
                        this.closeMobileMenu();
                        void this.navigateToLibraryPlaylistTracks(playlist.ratingKey, playlist.name);
                    }
                });
                li.appendChild(a);
                plexSection.container.appendChild(li);
            });
        }
        playlistNavItems.appendChild(plexSection.container);

        // --- ListenBrainz Playlists ---
        const lbSection = createSection('ListenBrainz', 'sidebar_section_listenbrainz');
        playlistNavItems.appendChild(lbSection.header);

        if (!data.listenbrainz) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.75rem';
            li.textContent = 'Loading or not configured...';
            lbSection.container.appendChild(li);
        } else {
            const renderLbSection = (title: string, items: any[], username: string) => {
                if (!items || items.length === 0) return;
                const subHeader = document.createElement('li');
                subHeader.className = 'nav-section-title';
                subHeader.style.fontSize = '0.5rem';
                subHeader.style.color = 'var(--text-muted)';
                subHeader.style.paddingLeft = '1.5rem';
                subHeader.textContent = title;
                lbSection.container.appendChild(subHeader);

                items.forEach((playlist: any) => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = '#';
                    a.className = 'nav-item';
                    a.textContent = playlist.title || 'Unknown';
                    a.style.fontSize = '0.875rem';
                    a.style.paddingLeft = '2.25rem';
                    a.style.paddingTop = '0.25rem';
                    a.style.paddingBottom = '0.25rem';
                    a.addEventListener('click', (e: Event) => {
                        e.preventDefault();
                        if (playlist.identifier) {
                            this.closeMobileMenu();
                            this.switchPage('explore');
                            this.pushHistoryRoute({ view: 'listenbrainz_playlist_tracks', playlistId: playlist.identifier, username });
                            void this.fetchListenbrainzPlaylistTracks(playlist.identifier, false, username);
                        }
                    });
                    li.appendChild(a);
                    lbSection.container.appendChild(li);
                });
            };

            renderLbSection('User Playlists', data.listenbrainz.user, data.listenbrainz.username);
            renderLbSection('Collaborator Playlists', data.listenbrainz.collaborator, data.listenbrainz.username);
            renderLbSection('Recommendation Playlists', data.listenbrainz.createdfor, data.listenbrainz.username);

            const lbTotal = (data.listenbrainz.user?.length || 0) + (data.listenbrainz.collaborator?.length || 0) + (data.listenbrainz.createdfor?.length || 0);
            if (lbTotal === 0) {
                const li = document.createElement('li');
                li.style.padding = '0.5rem 0.75rem';
                li.style.color = 'var(--text-muted)';
                li.style.fontSize = '0.875rem';
                li.textContent = 'No playlists found';
                lbSection.container.appendChild(li);
            }
        }
        playlistNavItems.appendChild(lbSection.container);

        // --- YouTube Music Playlists ---
        const ytmSection = createSection('YTM', 'sidebar_section_ytm');
        playlistNavItems.appendChild(ytmSection.header);

        if (data.ytm === null) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.75rem';
            li.textContent = 'Loading or not configured...';
            ytmSection.container.appendChild(li);
        } else if (data.ytm.length === 0) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.875rem';
            li.textContent = 'No playlists';
            ytmSection.container.appendChild(li);
        } else {
            data.ytm.forEach((playlist: YtmPlaylist) => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.className = 'nav-item';
                a.textContent = playlist.title;
                a.style.fontSize = '0.875rem';
                a.style.paddingTop = '0.25rem';
                a.style.paddingBottom = '0.25rem';
                a.addEventListener('click', (e: Event) => {
                    e.preventDefault();
                    this.closeMobileMenu();
                    this.switchPage('explore');
                    void this.fetchYtmPlaylistTracks(playlist.playlistId, playlist.title);
                });
                li.appendChild(a);
                ytmSection.container.appendChild(li);
            });
        }
        playlistNavItems.appendChild(ytmSection.container);

        void this.loadSquidlySection(squidlySection.container);
    }

    private async loadSquidlySection(container: HTMLUListElement): Promise<void> {
        const userId = this.getSelectedPlexUserId();
        if (!userId) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.75rem';
            li.textContent = 'Not enough listen history to generate recommendations';
            container.appendChild(li);
            return;
        }

        try {
            const response = await fetch(`/api/recommendations/playlists?user_id=${encodeURIComponent(userId)}`);
            if (!response.ok) {
                throw new Error('Failed to load recommendations');
            }
            const data = await response.json();
            const hasHistory = data.has_history as boolean;
            const playlists = Array.isArray(data.playlists) ? data.playlists : [];

            if (!hasHistory) {
                const li = document.createElement('li');
                li.style.padding = '0.5rem 0.75rem';
                li.style.color = 'var(--text-muted)';
                li.style.fontSize = '0.75rem';
                li.textContent = 'Not enough listen history to generate recommendations';
                container.appendChild(li);
                return;
            }

            if (playlists.length === 0) {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.className = 'nav-item';
                a.textContent = 'Fresh Finds';
                a.style.fontSize = '0.875rem';
                a.style.paddingTop = '0.25rem';
                a.style.paddingBottom = '0.25rem';
                a.addEventListener('click', (e: Event) => {
                    e.preventDefault();
                    this.closeMobileMenu();
                    this.switchPage('explore');
                    void this.fetchFreshFindsPlaylist();
                });
                li.appendChild(a);
                container.appendChild(li);
            } else {
                for (const playlist of playlists) {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = '#';
                    a.className = 'nav-item';
                    a.textContent = playlist.name || 'Fresh Finds';
                    a.style.fontSize = '0.875rem';
                    a.style.paddingTop = '0.25rem';
                    a.style.paddingBottom = '0.25rem';
                    a.addEventListener('click', (e: Event) => {
                        e.preventDefault();
                        this.closeMobileMenu();
                        this.switchPage('explore');
                        void this.fetchFreshFindsPlaylist(false, playlist.id);
                    });
                    li.appendChild(a);
                    container.appendChild(li);
                }
            }
        } catch {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.75rem';
            li.textContent = 'Not enough listen history to generate recommendations';
            container.appendChild(li);
        }
    }

    private initializeHistoryControls(): void {
    }

    private initializeHistoryNavigation(): void {
        window.addEventListener('popstate', (event: PopStateEvent) => {
            void this.handlePopState(event);
        });

        const historyState = this.parseHistoryState(window.history.state);
        const initialState = historyState || this.parseStateFromUrl() || this.buildCurrentHistoryState('explore');
        this.replaceHistoryState(initialState);
        void this.applyHistoryState(initialState);
    }

    private async handlePopState(event: PopStateEvent): Promise<void> {
        const state = this.parseHistoryState(event.state) || this.parseStateFromUrl() || this.buildCurrentHistoryState(this.currentPage);
        this.isHandlingPopState = true;
        try {
            await this.applyHistoryState(state);
        } finally {
            this.isHandlingPopState = false;
        }
    }

    private normalizePage(page: string | null | undefined): AppPage {
        if (page === 'library' || page === 'settings' || page === 'mirrors' || page === 'matches' || page === 'jobs' || page === 'history') {
            return page;
        }
        return 'explore';
    }

    private getCurrentLibraryRoute(): LibraryRouteState {
        if (this.libraryCurrentAlbum) {
            return {
                view: 'album_tracks',
                albumId: this.libraryCurrentAlbum.id,
                albumTitle: this.libraryCurrentAlbum.title,
                albumArtist: this.libraryCurrentAlbum.artist,
                artistId: this.libraryCurrentArtist?.id,
                artistName: this.libraryCurrentArtist?.name
            };
        }

        if (this.libraryCurrentArtist) {
            return {
                view: 'artist_albums',
                artistId: this.libraryCurrentArtist.id,
                artistName: this.libraryCurrentArtist.name
            };
        }

        return {
            view: 'artists',
            offset: this.libraryArtistsOffset
        };
    }

    private buildCurrentHistoryState(tab: AppPage): AppHistoryState {
        return {
            app: 'squidly',
            tab,
            route: { ...this.currentExploreRoute },
            libraryRoute: { ...this.getCurrentLibraryRoute() }
        };
    }

    private parseHistoryState(rawState: unknown): AppHistoryState | null {
        if (!rawState || typeof rawState !== 'object') {
            return null;
        }

        const state = rawState as Partial<AppHistoryState>;
        if (state.app !== 'squidly' || !state.route || typeof state.route !== 'object') {
            return null;
        }

        const route = state.route as AppRouteState;
        if (!route.view) {
            return null;
        }

        const libraryRouteRaw = state.libraryRoute as Partial<LibraryRouteState> | undefined;
        const libraryRoute: LibraryRouteState = libraryRouteRaw && typeof libraryRouteRaw === 'object' && libraryRouteRaw.view
            ? {
                view: libraryRouteRaw.view,
                offset: libraryRouteRaw.offset,
                artistId: libraryRouteRaw.artistId,
                artistName: libraryRouteRaw.artistName,
                albumId: libraryRouteRaw.albumId,
                albumTitle: libraryRouteRaw.albumTitle,
                albumArtist: libraryRouteRaw.albumArtist
            }
            : this.getCurrentLibraryRoute();

        return {
            app: 'squidly',
            tab: this.normalizePage(state.tab),
            route,
            libraryRoute
        };
    }

    private parseRouteFromUrl(params: URLSearchParams): AppRouteState | null {
        const view = params.get('view');
        if (!view) {
            return null;
        }

        if (view === 'search') {
            const searchType = params.get('type') || 's';
            const query = params.get('q') || '';
            return { view, searchType, query };
        }

        if (view === 'artist') {
            const artistId = Number(params.get('id') || '0');
            return Number.isFinite(artistId) && artistId > 0 ? { view, artistId } : null;
        }

        if (view === 'album') {
            const albumId = Number(params.get('id') || '0');
            return Number.isFinite(albumId) && albumId > 0 ? { view, albumId } : null;
        }

        if (view === 'playlist') {
            const playlistId = params.get('id') || '';
            return playlistId ? { view, playlistId } : null;
        }

        if (view === 'listenbrainz_playlists') {
            const username = params.get('username') || '';
            return username ? { view, username } : null;
        }

        if (view === 'listenbrainz_playlist_tracks') {
            const playlistId = params.get('id') || '';
            const username = params.get('username') || undefined;
            return playlistId ? { view, playlistId, username } : null;
        }

        if (view === 'lastfm_playlist') {
            const playlistUrl = params.get('url') || '';
            return playlistUrl ? { view, playlistUrl } : null;
        }

        if (view === 'youtube_music_playlist') {
            const playlistUrl = params.get('url') || '';
            if (playlistUrl) {
                return { view, playlistUrl };
            }
            const playlistId = params.get('id') || '';
            const playlistTitle = params.get('title') || '';
            if (playlistId && playlistTitle) {
                return { view, playlistId, playlistTitle };
            }
            return null;
        }

        if (view === 'similar_tracks') {
            const trackId = Number(params.get('id') || '0');
            return Number.isFinite(trackId) && trackId > 0 ? { view, trackId } : null;
        }

        if (view === 'similar_albums') {
            const albumId = Number(params.get('id') || '0');
            return Number.isFinite(albumId) && albumId > 0 ? { view, albumId } : null;
        }

        if (view === 'similar_artists') {
            const artistId = Number(params.get('id') || '0');
            return Number.isFinite(artistId) && artistId > 0 ? { view, artistId } : null;
        }

        if (view === 'fresh_finds') {
            const playlistIdParam = params.get('playlist_id');
            const playlistId = playlistIdParam ? Number(playlistIdParam) : undefined;
            return playlistId && Number.isFinite(playlistId) && playlistId > 0
                ? { view: 'fresh_finds', freshFindsPlaylistId: playlistId }
                : { view: 'fresh_finds' };
        }

        return view === 'home' ? { view: 'home' } : null;
    }

    private parseLibraryRouteFromUrl(params: URLSearchParams): LibraryRouteState | null {
        const view = params.get('lib_view');
        if (!view) {
            return null;
        }

        if (view === 'artists') {
            const offset = Number(params.get('lib_offset') || '0');
            return {
                view,
                offset: Number.isFinite(offset) && offset >= 0 ? Math.floor(offset) : 0
            };
        }

        if (view === 'artist_albums') {
            const artistId = params.get('lib_artist_id') || '';
            if (!artistId) {
                return null;
            }
            return {
                view,
                artistId,
                artistName: params.get('lib_artist_name') || 'Artist'
            };
        }

        if (view === 'album_tracks') {
            const albumId = params.get('lib_album_id') || '';
            if (!albumId) {
                return null;
            }
            const artistId = params.get('lib_artist_id') || undefined;
            const artistName = params.get('lib_artist_name') || undefined;
            return {
                view,
                albumId,
                albumTitle: params.get('lib_album_title') || 'Album',
                albumArtist: params.get('lib_album_artist') || undefined,
                artistId,
                artistName
            };
        }

        return null;
    }

    private parseStateFromUrl(): AppHistoryState | null {
        const params = new URLSearchParams(window.location.search);
        const exploreRoute = this.parseRouteFromUrl(params) || { view: 'home' };
        const libraryRoute = this.parseLibraryRouteFromUrl(params) || this.getCurrentLibraryRoute();
        const tab = this.normalizePage(params.get('tab') || 'explore');

        const hasTab = params.has('tab');
        const hasExplore = params.has('view');
        const hasLibrary = params.has('lib_view');
        if (!hasTab && !hasExplore && !hasLibrary) {
            return null;
        }

        return {
            app: 'squidly',
            tab,
            route: exploreRoute,
            libraryRoute
        };
    }

    private buildHistoryUrl(state: AppHistoryState): string {
        const tab = this.normalizePage(state.tab);
        const route = state.route;
        const libraryRoute = state.libraryRoute;
        const params = new URLSearchParams();

        if (tab === 'explore') {
            if (route.view !== 'home') {
                params.set('view', route.view);
            }

            if (route.view === 'search') {
                params.set('type', route.searchType || 's');
                if (route.query) {
                    params.set('q', route.query);
                }
            }

            if (route.view === 'artist' && route.artistId) {
                params.set('id', String(route.artistId));
            }

            if ((route.view === 'album' || route.view === 'similar_albums') && route.albumId) {
                params.set('id', String(route.albumId));
            }

            if (route.view === 'similar_tracks' && route.trackId) {
                params.set('id', String(route.trackId));
            }

            if ((route.view === 'playlist' || route.view === 'listenbrainz_playlist_tracks') && route.playlistId) {
                params.set('id', route.playlistId);
            }

            if (route.view === 'listenbrainz_playlists' && route.username) {
                params.set('username', route.username);
            }

            if (route.view === 'listenbrainz_playlist_tracks' && route.username) {
                params.set('username', route.username);
            }

            if (route.view === 'lastfm_playlist' && route.playlistUrl) {
                params.set('url', route.playlistUrl);
            }

            if (route.view === 'youtube_music_playlist' && route.playlistUrl) {
                params.set('url', route.playlistUrl);
            }

            if (route.view === 'youtube_music_playlist' && route.playlistId && !route.playlistUrl) {
                params.set('id', route.playlistId);
                if (route.playlistTitle) {
                    params.set('title', route.playlistTitle);
                }
            }

            if (route.view === 'similar_artists' && route.artistId) {
                params.set('id', String(route.artistId));
            }

            if (route.view === 'fresh_finds' && route.freshFindsPlaylistId) {
                params.set('playlist_id', String(route.freshFindsPlaylistId));
            }
        } else {
            params.set('tab', tab);
            if (tab === 'library') {
                params.set('lib_view', libraryRoute.view);

                if (libraryRoute.view === 'artists') {
                    params.set('lib_offset', String(Math.max(0, Math.floor(libraryRoute.offset || 0))));
                }

                if (libraryRoute.artistId) {
                    params.set('lib_artist_id', libraryRoute.artistId);
                }
                if (libraryRoute.artistName) {
                    params.set('lib_artist_name', libraryRoute.artistName);
                }
                if (libraryRoute.albumId) {
                    params.set('lib_album_id', libraryRoute.albumId);
                }
                if (libraryRoute.albumTitle) {
                    params.set('lib_album_title', libraryRoute.albumTitle);
                }
                if (libraryRoute.albumArtist) {
                    params.set('lib_album_artist', libraryRoute.albumArtist);
                }
            }
        }

        const query = params.toString();
        return query ? `${window.location.pathname}?${query}` : window.location.pathname;
    }

    private pushHistoryRoute(route: AppRouteState): void {
        if (this.isHandlingPopState) {
            return;
        }

        const state: AppHistoryState = {
            ...this.buildCurrentHistoryState('explore'),
            route: { ...route },
            tab: 'explore'
        };
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    }

    private pushHistoryLibraryRoute(route: LibraryRouteState): void {
        if (this.isHandlingPopState) {
            return;
        }

        const state: AppHistoryState = {
            ...this.buildCurrentHistoryState('library'),
            libraryRoute: { ...route },
            tab: 'library'
        };
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    }

    private pushHistoryTab(tab: AppPage): void {
        if (this.isHandlingPopState) {
            return;
        }

        const state = this.buildCurrentHistoryState(tab);
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    }

    private buildExploreHref(route: AppRouteState): string {
        const state: AppHistoryState = {
            ...this.buildCurrentHistoryState('explore'),
            route: { ...route },
            tab: 'explore'
        };
        return this.buildHistoryUrl(state);
    }

    private buildLibraryHref(route: LibraryRouteState): string {
        const state: AppHistoryState = {
            ...this.buildCurrentHistoryState('library'),
            libraryRoute: { ...route },
            tab: 'library'
        };
        return this.buildHistoryUrl(state);
    }

    private replaceHistoryState(state: AppHistoryState): void {
        window.history.replaceState(state, '', this.buildHistoryUrl(state));
    }

    private async applyHistoryState(state: AppHistoryState): Promise<void> {
        const tab = this.normalizePage(state.tab);
        const exploreRoute = state.route?.view ? state.route : { view: 'home' };
        const libraryRoute = state.libraryRoute?.view ? state.libraryRoute : this.getCurrentLibraryRoute();

        this.currentExploreRoute = { ...exploreRoute };
        if (tab !== this.currentPage) {
            this.switchPage(tab, false);
        }

        if (tab === 'explore') {
            await this.navigateToRoute(exploreRoute, false);
            return;
        }

        if (tab === 'library') {
            await this.navigateLibraryToRoute(libraryRoute, false);
        }
    }

    private async navigateLibraryToRoute(route: LibraryRouteState, updateHistory: boolean): Promise<void> {
        if (route.view === 'artist_albums' && route.artistId) {
            await this.loadLibraryArtistAlbums(route.artistId, route.artistName || 'Artist', updateHistory);
            return;
        }

        if (route.view === 'album_tracks' && route.albumId) {
            await this.loadLibraryAlbumTracks(
                route.albumId,
                route.albumTitle || 'Album',
                route.albumArtist,
                updateHistory
            );
            return;
        }

        if (route.view === 'playlist_tracks' && route.playlistRatingKey) {
            await this.fetchPlexPlaylistTracks(
                route.playlistRatingKey,
                route.playlistName || 'Playlist',
                updateHistory
            );
            return;
        }

        await this.loadLibraryArtists(route.offset || 0, updateHistory);
    }

    private async navigateToRoute(route: AppRouteState, updateHistory: boolean): Promise<void> {
        // Abort all pending requests from the previous route
        if (this.pendingRequestController) {
            this.pendingRequestController.abort();
        }

        const previousExploreRoute = { ...this.currentExploreRoute };
        if (route.view === 'album' && previousExploreRoute.view === 'artist' && previousExploreRoute.artistId) {
            this.exploreParentRoute = { ...previousExploreRoute };
        } else if (route.view !== 'album') {
            this.exploreParentRoute = null;
        } else {
            this.exploreParentRoute = null;
        }

        this.currentExploreRoute = { ...route };
        if (route.view === 'search') {
            this.exploreSearchRoute = { ...route };
        }
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

        // Create a new controller for this route's requests
        this.pendingRequestController = new AbortController();
        const signal = this.pendingRequestController.signal;

        if (route.view === 'home') {
            this.stopPlayback();
            this.updatePlexPlaylistContainerVisibility(false);
            this.resultsContainer.innerHTML = '';
            if (updateHistory) {
                this.pushHistoryRoute({ view: 'home' });
            }
            return;
        }

        if (route.view === 'search') {
            this.searchTypeSelect.value = route.searchType || 's';
            this.searchInput.value = route.query || '';
            this.updateSearchPlaceholder();
            await this.handleSearch(updateHistory);
            return;
        }

        if (route.view === 'artist' && route.artistId) {
            await this.fetchArtistAlbums(route.artistId, updateHistory);
            return;
        }

        if (route.view === 'album' && route.albumId) {
            await this.fetchAlbumTracks(route.albumId, updateHistory);
            return;
        }

        if (route.view === 'playlist' && route.playlistId) {
            await this.fetchPlaylistTracks(route.playlistId, updateHistory);
            return;
        }

        if (route.view === 'listenbrainz_playlists' && route.username) {
            this.searchTypeSelect.value = 'listenbrainz';
            this.searchInput.value = route.username;
            this.updateSearchPlaceholder();
            await this.handleListenbrainzPlaylists(route.username, updateHistory, route.playlistType);
            return;
        }

        if (route.view === 'listenbrainz_playlist_tracks' && route.playlistId) {
            await this.fetchListenbrainzPlaylistTracks(route.playlistId, updateHistory, route.username);
            return;
        }

        if (route.view === 'lastfm_playlist' && route.playlistUrl) {
            this.searchTypeSelect.value = 'lastfm';
            this.searchInput.value = route.playlistUrl;
            this.updateSearchPlaceholder();
            await this.handleLastfmPlaylist(route.playlistUrl, updateHistory);
            return;
        }

        if (route.view === 'youtube_music_playlist' && route.playlistId && route.playlistTitle) {
            await this.fetchYtmPlaylistTracks(route.playlistId, route.playlistTitle, updateHistory);
            return;
        }

        if (route.view === 'youtube_music_playlist' && route.playlistUrl) {
            this.searchTypeSelect.value = 'youtube_music';
            this.searchInput.value = route.playlistUrl;
            this.updateSearchPlaceholder();
            await this.handleYoutubeMusicPlaylist(route.playlistUrl, updateHistory);
            return;
        }

        if (route.view === 'similar_tracks' && route.trackId) {
            await this.fetchSimilarTracks(route.trackId, updateHistory);
            return;
        }

        if (route.view === 'similar_albums' && route.albumId) {
            await this.fetchSimilarAlbums(route.albumId, updateHistory);
            return;
        }

        if (route.view === 'similar_artists' && route.artistId) {
            await this.fetchSimilarArtists(route.artistId, updateHistory);
            return;
        }

        if (route.view === 'fresh_finds') {
            await this.fetchFreshFindsPlaylist(updateHistory, route.freshFindsPlaylistId);
            return;
        }
    }

    private openFlyout(): void {
        this.statusFlyout.classList.add('active');
        this.flyoutOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.updateEndpointStatus(); // Refresh on open
    }

    private closeFlyout(): void {
        this.statusFlyout.classList.remove('active');
        this.flyoutOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    private openJobsFlyout(): void {
        this.jobsFlyout.classList.add('active');
        this.jobsOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.currentJobsPage = 1;
        this.updateJobsActionButtons(0, this.jobsFilterSelect.value, 0);
        void this.loadJobs();
        this.startJobsPollingInterval();
    }

    private closeJobsFlyout(): void {
        this.jobsFlyout.classList.remove('active');
        this.jobsOverlay.classList.remove('active');
        document.body.style.overflow = '';
        if (this.jobsUpdateInterval) {
            window.clearInterval(this.jobsUpdateInterval);
            this.jobsUpdateInterval = null;
        }
    }

    private async loadJobs(): Promise<void> {
        const filter = this.jobsFilterSelect.value;
        this.jobsContent.innerHTML = '<p class="loading-text">Loading jobs...</p>';
        this.clearJobsPagination();

        try {
            const params = new URLSearchParams({
                jobs_filter: filter
            });
            const response = await fetch(`/api/jobs?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Failed to fetch jobs');
            }

            const data = await response.json();
            const jobs = Array.isArray(data.jobs) ? (data.jobs as JobItem[]) : [];
            const totals = this.normalizeJobFilterTotals(data.totals, jobs);
            const totalCount = typeof data.total_count === 'number' && Number.isFinite(data.total_count)
                ? Math.max(0, Math.floor(data.total_count))
                : jobs.length;
            const retryableCount = (filter === 'completed_with_errors' || filter === 'failed')
                ? jobs.length
                : 0;
            this.jobsListCache = jobs;
            this.jobsTotalCountCache = totalCount;
            this.updateJobsFilterCounts(totals);
            this.updateJobsActionButtons(totals.incomplete, filter, retryableCount);
            this.renderJobs(jobs, totalCount);
        } catch (error) {
            this.jobsListCache = [];
            this.jobsTotalCountCache = 0;
            this.jobsContent.innerHTML = '<p class="loading-text">Failed to load jobs.</p>';
            this.clearJobsPagination();
            this.updateJobsActionButtons(0, filter, 0);
            console.error('Jobs load error:', error);
        }
    }

    private updateJobsActionButtons(incompleteCount: number, filter: string, retryableCount: number): void {
        let cancelCount = 0;
        if (filter === 'incomplete') {
            cancelCount = incompleteCount;
        } else if (filter === 'failed' || filter === 'completed_with_errors') {
            cancelCount = this.jobsListCache.length;
        }

        const showCancel = cancelCount > 0;
        const showRetry = retryableCount > 0;

        // Cancel all button
        this.cancelPendingJobsButton.classList.toggle('hidden', !showCancel);
        if (showCancel) {
            this.cancelPendingJobsButton.disabled = cancelCount === 0;
            this.cancelPendingJobsButton.textContent = cancelCount > 0
                ? `Cancel all (${cancelCount})`
                : 'Cancel all';
        } else {
            this.cancelPendingJobsButton.disabled = true;
            this.cancelPendingJobsButton.textContent = 'Cancel all';
        }

        // Retry all button
        this.retryAllJobsButton.classList.toggle('hidden', !showRetry);
        if (showRetry) {
            this.retryAllJobsButton.disabled = retryableCount === 0;
            this.retryAllJobsButton.textContent = retryableCount > 0
                ? `Retry all (${retryableCount})`
                : 'Retry all';
        } else {
            this.retryAllJobsButton.disabled = true;
            this.retryAllJobsButton.textContent = 'Retry all';
        }
    }

    private async cancelAllJobs(): Promise<void> {
        if (this.cancelPendingJobsButton.disabled) {
            return;
        }

        const selectedFilter = this.jobsFilterSelect.value;

        if (selectedFilter === 'incomplete') {
            await this.cancelIncompleteJobs();
        } else if (selectedFilter === 'failed' || selectedFilter === 'completed_with_errors') {
            await this.cancelFailedJobs();
        }
    }

    private async cancelIncompleteJobs(): Promise<void> {
        const shouldProceed = window.confirm('Cancel and remove all incomplete jobs from the queue?');
        if (!shouldProceed) {
            return;
        }

        const originalText = this.cancelPendingJobsButton.textContent || 'Cancel all';
        this.cancelPendingJobsButton.disabled = true;
        this.cancelPendingJobsButton.textContent = 'Cancelling...';

        try {
            const response = await fetch('/api/jobs/cancel-pending', { method: 'POST' });
            if (!response.ok) {
                let message = 'Failed to cancel incomplete jobs';
                try {
                    const data = await response.json() as { error?: string };
                    if (data?.error) {
                        message = data.error;
                    }
                } catch {
                    // Ignore parse errors and keep fallback message
                }
                throw new Error(message);
            }

            await this.loadJobs();
        } catch (error) {
            console.error('Cancel incomplete jobs failed:', error);
            window.alert((error as Error).message || 'Failed to cancel incomplete jobs');
            this.cancelPendingJobsButton.disabled = false;
            this.cancelPendingJobsButton.textContent = originalText;
        }
    }

    private async cancelFailedJobs(): Promise<void> {
        const shouldProceed = window.confirm('Cancel all failed jobs? They will be superseded by retried downloads or nightly runs.');
        if (!shouldProceed) {
            return;
        }

        const originalText = this.cancelPendingJobsButton.textContent || 'Cancel all';
        this.cancelPendingJobsButton.disabled = true;
        this.cancelPendingJobsButton.textContent = 'Cancelling...';

        try {
            const response = await fetch('/api/jobs/cancel-failed', { method: 'POST' });
            if (!response.ok) {
                let message = 'Failed to cancel jobs';
                try {
                    const data = await response.json() as { error?: string };
                    if (data?.error) {
                        message = data.error;
                    }
                } catch {
                    // Ignore parse errors and keep fallback message
                }
                throw new Error(message);
            }

            const data = await response.json() as { cancelled_count?: number };
            const cancelledCount = data?.cancelled_count ?? 0;
            if (cancelledCount > 0) {
                window.alert(`Cancelled ${cancelledCount} job${cancelledCount === 1 ? '' : 's'}.`);
            }
            await this.loadJobs();
        } catch (error) {
            console.error('Cancel failed jobs failed:', error);
            window.alert((error as Error).message || 'Failed to cancel jobs');
            this.cancelPendingJobsButton.disabled = false;
            this.cancelPendingJobsButton.textContent = originalText;
        }
    }

    private async retryAllFilteredJobs(): Promise<void> {
        const selectedFilter = this.jobsFilterSelect.value;
        if (selectedFilter !== 'completed_with_errors' && selectedFilter !== 'failed') {
            return;
        }

        const retryableJobs = this.jobsListCache;

        if (retryableJobs.length === 0 || this.retryAllJobsButton.disabled) {
            return;
        }

        const shouldProceed = window.confirm(`Retry all ${retryableJobs.length} jobs in ${selectedFilter.replace(/_/g, ' ')}?`);
        if (!shouldProceed) {
            return;
        }

        const originalText = this.retryAllJobsButton.textContent || 'Retry all';
        this.retryAllJobsButton.disabled = true;
        this.retryAllJobsButton.textContent = 'Retrying...';

        const failures: string[] = [];
        let skippedExistingCount = 0;

        for (const job of retryableJobs) {
            try {
                const response = await fetch(`/api/jobs/${job.id}/retry`, { method: 'POST' });
                if (!response.ok) {
                    let message = `Job ${job.id}`;
                    try {
                        const data = await response.json() as { error?: string; status?: string };
                        if (response.status === 409 && data?.status === 'already_exists_in_plex') {
                            skippedExistingCount += 1;
                            continue;
                        }
                        if (data?.error) {
                            message = `Job ${job.id}: ${data.error}`;
                        }
                    } catch {
                        // Ignore parse errors and keep fallback message
                    }
                    failures.push(message);
                }
            } catch {
                failures.push(`Job ${job.id}: request failed`);
            }
        }

        await this.loadJobs();

        const retriedCount = retryableJobs.length - failures.length - skippedExistingCount;
        const parts: string[] = [`Retried ${retriedCount} of ${retryableJobs.length} jobs.`];

        if (skippedExistingCount > 0) {
            parts.push(`Skipped ${skippedExistingCount} job${skippedExistingCount === 1 ? '' : 's'} (already exists in Plex).`);
        }

        if (failures.length > 0) {
            const summary = failures.length <= 3 ? failures.join('\n') : `${failures.slice(0, 3).join('\n')}\n...`;
            parts.push(summary);
        }

        if (parts.length > 1 || failures.length > 0 || skippedExistingCount > 0) {
            window.alert(parts.join('\n'));
            this.retryAllJobsButton.disabled = false;
            this.retryAllJobsButton.textContent = originalText;
        }
    }

    private getEffectiveJobStatus(job: JobItem): string {
        if (job.job_type !== 'download_track') {
            return job.status;
        }

        const stages = job.result?.stages;
        if (stages?.written === 'failed') {
            return 'failed';
        }

        if (stages?.playlist_added === 'failed') {
            return 'completed_with_errors';
        }

        return job.status;
    }

    private filterJobsByStatus(jobs: JobItem[], filter: string): JobItem[] {
        if (filter === 'failed') {
            return jobs.filter(job => this.getEffectiveJobStatus(job) === 'failed');
        }

        if (filter === 'completed_with_errors') {
            return jobs.filter(job => this.getEffectiveJobStatus(job) === 'completed_with_errors');
        }

        if (filter === 'complete') {
            return jobs.filter(job => ['succeeded'].includes(this.getEffectiveJobStatus(job)));
        }

        return jobs.filter(job => ['queued', 'in_progress'].includes(this.getEffectiveJobStatus(job)));
    }

    private renderJobs(jobs: JobItem[], totalJobs: number): void {
        if (totalJobs === 0 || jobs.length === 0) {
            this.jobsContent.innerHTML = '<p class="loading-text">No jobs found.</p>';
            this.clearJobsPagination();
            return;
        }

        const totalPages = Math.max(1, Math.ceil(totalJobs / this.jobsPageSize));
        this.currentJobsPage = Math.min(this.currentJobsPage, totalPages);
        const startIndex = (this.currentJobsPage - 1) * this.jobsPageSize;
        const endIndex = startIndex + this.jobsPageSize;
        const pageItems = jobs.slice(startIndex, endIndex);
        this.jobsContent.innerHTML = pageItems.map(job => this.renderJobItem(job)).join('');
        this.renderJobsPagination(totalJobs, totalPages);
    }

    private renderJobsPagination(totalJobs: number, totalPages: number): void {
        if (totalPages <= 1) {
            this.clearJobsPagination();
            return;
        }

        const start = (this.currentJobsPage - 1) * this.jobsPageSize + 1;
        const end = Math.min(this.currentJobsPage * this.jobsPageSize, totalJobs);

        this.jobsPagination.innerHTML = `
            <button type="button" class="jobs-pagination-button" data-page-action="prev" ${this.currentJobsPage === 1 ? 'disabled' : ''}>Previous</button>
            <span class="jobs-pagination-info">${start}-${end} of ${totalJobs}</span>
            <button type="button" class="jobs-pagination-button" data-page-action="next" ${this.currentJobsPage === totalPages ? 'disabled' : ''}>Next</button>
        `;

        this.jobsPagination.classList.add('active');

        const prevButton = this.jobsPagination.querySelector('[data-page-action="prev"]') as HTMLButtonElement | null;
        if (prevButton) {
            prevButton.addEventListener('click', () => {
                if (this.currentJobsPage > 1) {
                    this.currentJobsPage -= 1;
                    this.renderJobs(this.jobsListCache, this.jobsTotalCountCache);
                }
            });
        }

        const nextButton = this.jobsPagination.querySelector('[data-page-action="next"]') as HTMLButtonElement | null;
        if (nextButton) {
            nextButton.addEventListener('click', () => {
                if (this.currentJobsPage < totalPages) {
                    this.currentJobsPage += 1;
                    this.renderJobs(this.jobsListCache, this.jobsTotalCountCache);
                }
            });
        }
    }

    private clearJobsPagination(): void {
        this.jobsPagination.classList.remove('active');
        this.jobsPagination.innerHTML = '';
    }

    private setMatchReviewStatus(message: string, isError: boolean = false): void {
        if (!this.matchReviewStatusEl) {
            return;
        }

        this.matchReviewStatusEl.textContent = message;
        this.matchReviewStatusEl.style.color = isError ? '#ff9ab0' : 'var(--text-secondary)';
    }

    private updateMatchReviewRunScanButton(isActive: boolean): void {
        if (!this.matchReviewRunScanButton) {
            return;
        }

        this.matchReviewRunScanButton.disabled = false;
        this.matchReviewRunScanButton.classList.toggle('is-cancel', isActive);
        this.matchReviewRunScanButton.textContent = isActive
            ? 'Cancel Update & Sync'
            : 'Update & Sync Library';
    }

    private startMatchReviewPollingInterval(): void {
        if (this.matchReviewPollingInterval) {
            return;
        }

        this.matchReviewPollingInterval = window.setInterval(() => {
            if (this.currentPage !== 'matches') {
                this.stopMatchReviewPollingInterval();
                return;
            }

            void this.loadMatchActivity();
        }, 5000);
    }

    private stopMatchReviewPollingInterval(): void {
        if (this.matchReviewPollingInterval) {
            window.clearInterval(this.matchReviewPollingInterval);
            this.matchReviewPollingInterval = null;
        }
    }

    private isMatchScanActive(): boolean {
        return Boolean(
            this.activeMatchActivityJobId
            || this.lastMatchActivityStatus === 'queued'
            || this.lastMatchActivityStatus === 'in_progress'
        );
    }

    private renderMatchReviewBlockedByActiveScan(): void {
        if (!this.matchReviewContent || !this.matchReviewSummary) {
            return;
        }

        this.matchReviewSummary.innerHTML = '';
        this.matchReviewContent.innerHTML = `
            <div class="match-review-empty">Library update is currently running. Review cards will load after it completes.</div>
        `;
    }

    private getMatchCoverageFromProgress(progress: Record<string, unknown>, entity: 'artists' | 'albums' | 'tracks'): { total: number; missing: number; matched: number } {
        const total = Number(progress[`${entity}_total`] || 0);
        const missing = Number(progress[`${entity}_missing_current`] || progress[`${entity}_processed`] || 0);
        const matchedCurrent = Number(progress[`${entity}_matched_current_job`] || progress[`${entity}_matched`] || 0);
        return {
            total: Number.isFinite(total) ? total : 0,
            missing: Number.isFinite(missing) ? missing : 0,
            matched: Number.isFinite(matchedCurrent) ? matchedCurrent : 0,
        };
    }

    private renderMatchActivityCard(job: JobItem): string {
        const effectiveStatus = this.getEffectiveJobStatus(job);
        const statusLabel = this.formatJobStatus(effectiveStatus);
        const statusClass = `status-${effectiveStatus.replace(/_/g, '-')}`;
        const stages = (job.result?.stages || {}) as Record<string, string>;
        const progress = (job.result?.progress || {}) as Record<string, unknown>;
        const hasResult = job.result !== null && job.result !== undefined;
        const stageRows = [
            { key: 'plex_library_update', label: 'Plex Library Update' },
            { key: 'plex_sync', label: 'Plex Sync' },
            { key: 'tag_analysis', label: 'Tag Analysis' },
            { key: 'hifi_gap_fill', label: 'HiFi Gap Fill' }
        ];

        const jobTypeLabel = this.formatJobTypeLabel(job.job_type);

        if (!hasResult) {
            return `
                <div class="match-activity-card">
                    <div class="match-activity-header">
                        <div>
                            <h3 class="match-activity-title">Latest Match Scan</h3>
                        </div>
                        <span class="match-review-status ${statusClass}">${statusLabel}</span>
                    </div>
                    <div class="match-activity-meta">
                        <span class="match-activity-meta-item">${jobTypeLabel} #${job.id}</span>
                        <span class="match-activity-meta-item">Waiting to start...</span>
                    </div>
                    <div class="match-activity-stages">
                        ${stageRows.map(stage => `
                            <div class="job-stage">
                                <span>${stage.label}</span>
                                <span class="job-stage-status status-pending">Pending</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        const plexSyncTracks = typeof progress.plex_sync_tracks === 'number' ? progress.plex_sync_tracks : 0;
        const tagScanned = typeof progress.tag_scanned === 'number' ? progress.tag_scanned : 0;
        const tagFilled = typeof progress.tag_filled === 'number' ? progress.tag_filled : 0;
        const hifiTracks = typeof progress.hifi_tracks_matched === 'number' ? progress.hifi_tracks_matched : 0;
        const hifiAlbums = typeof progress.hifi_albums_matched === 'number' ? progress.hifi_albums_matched : 0;
        const hifiArtists = typeof progress.hifi_artists_matched === 'number' ? progress.hifi_artists_matched : 0;

        return `
            <div class="match-activity-card">
                <div class="match-activity-header">
                    <div>
                        <h3 class="match-activity-title">Latest Match Scan</h3>
                    </div>
                    <span class="match-review-status ${statusClass}">${statusLabel}</span>
                </div>
                <div class="match-activity-meta">
                    <span class="match-activity-meta-item">${jobTypeLabel} #${job.id}</span>
                    <span class="match-activity-meta-item">Plex: ${plexSyncTracks} tracks synced</span>
                    <span class="match-activity-meta-item">Tags: ${tagScanned} scanned • ${tagFilled} filled</span>
                    <span class="match-activity-meta-item">HiFi: ${hifiTracks} tracks • ${hifiAlbums} albums • ${hifiArtists} artists matched</span>
                </div>
                <div class="match-activity-stages">
                    ${stageRows.map(stage => {
            const stageStatus = this.resolvePlexSyncStageStatus(job, stage.key, stages);
            return `
                            <div class="job-stage">
                                <span>${stage.label}</span>
                                <span class="job-stage-status status-${stageStatus}">${this.formatStageStatus(stageStatus)}</span>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    }

    private formatJobTypeLabel(jobType: string): string {
        switch (jobType) {
            case 'automatic_matching':
                return 'Automatic Matching';
            case 'hifi_match':
                return 'HiFi Match (Legacy)';
            case 'plex_library_sync':
                return 'Plex Sync';
            case 'plex_library_update':
                return 'Plex Update';
            case 'plex_listen_history_sync':
                return 'Listen History Sync';
            case 'generate_recommendations':
                return 'Fresh Finds';
            case 'bulk_playlist_add':
                return 'Playlist Update';
            case 'download_track':
                return 'Download';
            default:
                return jobType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        }
    }

    private async loadMatchActivity(): Promise<void> {
        if (!this.matchReviewActivity || !this.matchReviewRunScanButton) {
            return;
        }

        try {
            const params = new URLSearchParams({
                job_type: 'automatic_matching',
                limit: '1'
            });
            const response = await fetch(`/api/jobs?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Failed to load library update activity');
            }

            const data = await response.json() as { jobs?: JobItem[] };
            const jobs = Array.isArray(data.jobs) ? data.jobs : [];
            const latestJob = jobs[0] || null;

            if (!latestJob) {
                this.matchReviewActivity.innerHTML = '<div class="match-activity-empty">No library updates have been run yet.</div>';
                this.activeMatchActivityJobId = null;
                this.updateMatchReviewRunScanButton(false);
                this.lastMatchActivityJobId = null;
                this.lastMatchActivityStatus = null;
                this.stopMatchReviewPollingInterval();
                return;
            }

            const previousJobId = this.lastMatchActivityJobId;
            const previousStatus = this.lastMatchActivityStatus;
            const currentStatus = this.getEffectiveJobStatus(latestJob);
            const isActive = currentStatus === 'queued' || currentStatus === 'in_progress';

            this.matchReviewActivity.innerHTML = this.renderMatchActivityCard(latestJob);
            this.activeMatchActivityJobId = isActive ? latestJob.id : null;
            this.updateMatchReviewRunScanButton(isActive);
            if (isActive) {
                this.startMatchReviewPollingInterval();
                this.setMatchReviewStatus(`Library update ${currentStatus === 'queued' ? 'queued' : 'running'}...`);
                if (this.currentPage === 'matches') {
                    this.renderMatchReviewBlockedByActiveScan();
                }
            } else {
                this.stopMatchReviewPollingInterval();
            }

            this.lastMatchActivityJobId = latestJob.id;
            this.lastMatchActivityStatus = currentStatus;

            const completedNow = previousJobId === latestJob.id
                && (previousStatus === 'queued' || previousStatus === 'in_progress')
                && currentStatus !== 'queued'
                && currentStatus !== 'in_progress';

            if (completedNow) {
                if (currentStatus === 'succeeded') {
                    this.setMatchReviewStatus(`Library update completed for job ${latestJob.id}. Review results updated.`);
                } else {
                    this.setMatchReviewStatus(`Library update finished with status ${currentStatus}.`, currentStatus === 'failed');
                }
                await this.loadMatchReview();
            }
        } catch (error) {
            console.error('Failed to load match activity:', error);
            this.matchReviewActivity.innerHTML = '<div class="match-activity-empty">Failed to load library update activity.</div>';
            this.stopMatchReviewPollingInterval();
        }
    }

    private formatMatchConfidence(confidence?: number | null): string {
        if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
            return '—';
        }
        return `${Math.round(confidence * 100)}%`;
    }

    private formatMatchStatusLabel(confidence?: number | null): string {
        const c = typeof confidence === 'number' ? confidence : 0;
        if (c >= 0.95) {
            return 'Matched';
        }
        if (c > 0) {
            return 'Needs Review';
        }
        return 'Unmatched';
    }

    private renderMatchSummaryCard(label: string, value: number): string {
        return `
            <div class="matches-summary-card">
                <span class="matches-summary-value">${value}</span>
                <span class="matches-summary-label">${this.escapeHtml(label)}</span>
            </div>
        `;
    }

    private escapeAttribute(text: string): string {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '&#10;');
    }

    private renderMatchTrackList(trackTitles?: string[], emptyLabel: string = 'Track list unavailable.'): string {
        const normalizedTitles = (trackTitles || [])
            .map(title => String(title || '').trim())
            .filter(Boolean);

        if (normalizedTitles.length === 0) {
            return `<div class="match-review-track-list is-empty">${this.escapeHtml(emptyLabel)}</div>`;
        }

        return `
            <div class="match-review-track-list">
                <div class="match-review-track-list-label">Track List</div>
                <ol class="match-review-track-list-items">
                    ${normalizedTitles.map(title => `<li>${this.escapeHtml(title)}</li>`).join('')}
                </ol>
            </div>
        `;
    }

    private renderMatchReviewArtwork(imageUrl: string | undefined, altText: string, kind: 'artist' | 'album' | 'track' = 'album'): string {
        if (imageUrl) {
            return `
                <div class="match-review-artwork match-review-artwork--${kind}">
                    <img src="${this.escapeAttribute(imageUrl)}" alt="${this.escapeAttribute(altText)}" loading="lazy" width="350" height="350">
                </div>
            `;
        }

        const placeholderSvg = kind === 'artist'
            ? `
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="8" r="4"></circle>
                    <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"></path>
                </svg>
            `
            : `
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
            `;

        return `
            <div class="match-review-artwork match-review-artwork--${kind} is-placeholder" aria-hidden="true">
                ${placeholderSvg}
            </div>
        `;
    }

    private renderMatchReviewTitle(title: string, options: { explicit?: boolean; className?: string; href?: string | null } = {}): string {
        const className = options.className || 'match-review-pane-title';
        const titleContent = options.href
            ? `<a class="match-review-title-link" href="${this.escapeAttribute(options.href)}">${this.escapeHtml(title)}</a>`
            : `<span class="match-review-title-text">${this.escapeHtml(title)}</span>`;

        return `
            <div class="${className}">
                ${titleContent}
                ${options.explicit ? '<span class="explicit-badge" title="Explicit content">E</span>' : ''}
            </div>
        `;
    }

    private getMatchCandidateSearchPlaceholder(entityType: 'artist' | 'album' | 'track'): string {
        if (entityType === 'artist') {
            return 'Search artists in Explore';
        }
        if (entityType === 'album') {
            return 'Search albums in Explore';
        }
        return 'Search tracks in Explore';
    }

    private renderMatchCandidateSearchControls(entityType: 'artist' | 'album' | 'track', reviewId: number): string {
        const cacheKey = `${entityType}:${reviewId}`;
        const previousSearch = this.matchCandidateSearchTerms.get(cacheKey) || '';

        return `
            <div class="match-review-candidate-search">
                <label class="match-review-candidate-search-label" for="matchCandidateSearch-${entityType}-${reviewId}">Search candidates</label>
                <div class="match-review-candidate-search-controls">
                    <input
                        id="matchCandidateSearch-${entityType}-${reviewId}"
                        type="text"
                        class="settings-input match-review-candidate-search-input"
                        data-match-search-input="${entityType}:${reviewId}"
                        placeholder="${this.escapeAttribute(this.getMatchCandidateSearchPlaceholder(entityType))}"
                        value="${this.escapeAttribute(previousSearch)}"
                        spellcheck="false"
                    >
                    <button
                        type="button"
                        class="match-review-button"
                        data-match-action="search-candidates"
                        data-entity-type="${entityType}"
                        data-review-id="${reviewId}"
                    >Search</button>
                </div>
            </div>
        `;
    }

    private renderMatchCandidateList(entityType: 'artist' | 'album' | 'track', reviewId: number): string {
        const cacheKey = `${entityType}:${reviewId}`;
        const candidates = this.matchCandidateCache.get(cacheKey);
        if (!candidates) {
            return '<div class="match-review-inline-status">Candidates load automatically when you open this card.</div>';
        }

        if (candidates.length === 0) {
            return '<div class="match-review-empty">No candidates found for this item.</div>';
        }

        return `
            <div class="match-review-candidate-list">
                ${candidates.map(candidate => `
                    <div class="match-review-candidate">
                        <div class="match-review-candidate-meta">
                            <span class="match-review-confidence">${this.formatMatchConfidence(candidate.confidence)}</span>
                            <button
                                type="button"
                                class="match-review-button primary"
                                data-match-action="confirm-candidate"
                                data-entity-type="${entityType}"
                                data-review-id="${reviewId}"
                                data-hifi-id="${this.escapeHtml(candidate.hifi_id)}"
                            >Use This Match</button>
                        </div>
                        <div class="match-review-candidate-main">
                            ${entityType === 'album'
                ? `
                                    <div class="match-review-album-header">
                                        ${this.renderMatchReviewTitle(candidate.title, {
                    explicit: candidate.explicit,
                    className: 'match-review-candidate-title',
                    href: this.getMatchExploreHref(entityType, candidate.hifi_id)
                })}
                                        <div class="match-review-album-artist">${this.escapeHtml(candidate.subtitle || 'Unknown Artist')}</div>
                                    </div>
                                    <div class="match-review-album-body">
                                        ${this.renderMatchReviewArtwork(candidate.image_url, candidate.title, 'album')}
                                        ${this.renderMatchTrackList(candidate.track_titles, 'Track list unavailable for this candidate.')}
                                    </div>
                                `
                : `
                                    ${this.renderMatchReviewArtwork(candidate.image_url, candidate.title, entityType === 'artist' ? 'artist' : 'album')}
                                    <div class="match-review-candidate-copy">
                                        ${this.renderMatchReviewTitle(candidate.title, {
                    explicit: candidate.explicit,
                    className: 'match-review-candidate-title',
                    href: this.getMatchExploreHref(entityType, candidate.hifi_id)
                })}
                                        ${candidate.subtitle ? `<div class="match-review-candidate-subtitle">${this.escapeHtml(candidate.subtitle)}</div>` : ''}
                                    </div>
                                `}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    private renderMatchWorkflowCard(
        entityType: 'artist' | 'album' | 'track',
        reviewId: number,
        entityLabel: string,
        title: string,
        subtitle: string,
        confidence: number | undefined,
        summaryHtml: string,
        sourcePaneHtml: string,
        candidatePaneHtml: string,
        actionsHtml: string,
    ): string {
        const statusLabel = this.formatMatchStatusLabel(confidence);
        const normalizedStatus = confidence && confidence >= 0.95 ? 'confirmed' : confidence && confidence > 0 ? 'proposed' : 'unmatched';

        return `
            <div class="match-review-card" data-entity-type="${entityType}" data-review-id="${reviewId}">
                <div class="match-review-card-header">
                    <div class="match-review-card-summary">
                        <div class="match-review-title-wrap">
                            <span class="match-review-entity">${this.escapeHtml(entityLabel)}</span>
                            <h4 class="match-review-title">${this.escapeHtml(title)}</h4>
                            <div class="match-review-subtitle">${this.escapeHtml(subtitle)}</div>
                        </div>
                        <div class="match-review-meta">${summaryHtml}</div>
                    </div>
                    <div class="match-review-card-controls">
                        <span class="match-review-status status-${this.escapeHtml(normalizedStatus)}">${this.escapeHtml(statusLabel)}</span>
                        <button
                            type="button"
                            class="match-review-toggle"
                            data-match-toggle="true"
                            aria-expanded="false"
                        >Review</button>
                    </div>
                </div>
                <div class="match-review-card-body">
                    <div class="match-review-workflow">
                        ${sourcePaneHtml}
                        ${candidatePaneHtml}
                    </div>
                    <div class="match-review-actions">
                        ${actionsHtml}
                    </div>
                </div>
            </div>
        `;
    }

    private getMatchSourceHref(item: HifiReviewArtist | HifiReviewAlbum | HifiReviewTrack, entityType: 'artist' | 'album' | 'track'): string | null {
        if (entityType === 'artist') {
            const artist = item as HifiReviewArtist;
            if (!artist.library_id) {
                return null;
            }
            return this.buildLibraryHref({
                view: 'artist_albums',
                artistId: artist.library_id,
                artistName: artist.name || 'Artist'
            });
        }

        if (entityType === 'album') {
            const album = item as HifiReviewAlbum;
            if (!album.library_id) {
                return null;
            }
            return this.buildLibraryHref({
                view: 'album_tracks',
                albumId: album.library_id,
                albumTitle: album.title || 'Album',
                albumArtist: album.artist_name || 'Artist'
            });
        }

        const track = item as HifiReviewTrack;
        if (track.album_library_id) {
            return this.buildLibraryHref({
                view: 'album_tracks',
                albumId: track.album_library_id,
                albumTitle: track.album_title || 'Album',
                albumArtist: track.artist_name || 'Artist'
            });
        }

        if (track.artist_library_id) {
            return this.buildLibraryHref({
                view: 'artist_albums',
                artistId: track.artist_library_id,
                artistName: track.artist_name || 'Artist'
            });
        }

        return null;
    }

    private getMatchExploreHref(entityType: 'artist' | 'album' | 'track', hifiId?: string): string | null {
        const normalizedHifiId = String(hifiId || '').trim();
        if (!normalizedHifiId) {
            return null;
        }

        if (entityType === 'track') {
            return this.buildExploreHref({
                view: 'search',
                searchType: 'trackid',
                query: normalizedHifiId
            });
        }

        const parsedId = Number.parseInt(normalizedHifiId, 10);
        if (!Number.isFinite(parsedId) || parsedId <= 0) {
            return null;
        }

        return this.buildExploreHref({
            view: entityType,
            ...(entityType === 'artist' ? { artistId: parsedId } : { albumId: parsedId })
        });
    }

    private getManualMatchIdHint(entityType: 'artist' | 'album' | 'track'): string {
        if (entityType === 'artist') {
            return 'Paste the Explore artist ID if search found nothing useful.';
        }
        if (entityType === 'album') {
            return 'Paste the Explore album ID to confirm this library album manually.';
        }
        return 'Paste the Explore track ID to confirm this library track manually.';
    }

    private renderManualMatchEntry(entityType: 'artist' | 'album' | 'track', reviewId: number): string {
        return `
            <div class="match-review-manual-entry">
                <label class="match-review-manual-label" for="manualMatchId-${entityType}-${reviewId}">Manual HiFi ID</label>
                <div class="match-review-manual-controls">
                    <input
                        id="manualMatchId-${entityType}-${reviewId}"
                        type="text"
                        class="settings-input match-review-manual-input"
                        data-match-manual-id="${entityType}:${reviewId}"
                        placeholder="Enter ${entityType} ID"
                        spellcheck="false"
                    >
                    <button
                        type="button"
                        class="match-review-button"
                        data-match-action="confirm-manual"
                        data-entity-type="${entityType}"
                        data-review-id="${reviewId}"
                    >Use ID</button>
                </div>
                <div class="match-review-manual-hint">${this.escapeHtml(this.getManualMatchIdHint(entityType))}</div>
            </div>
        `;
    }

    private renderMatchCurrentCandidate(entityType: 'artist' | 'album' | 'track', hifiId?: string, extraLabel?: string): string {
        if (!this.getMatchExploreHref(entityType, hifiId)) {
            return '';
        }

        return `
            <div class="match-review-current">
                <span>Current candidate selected${extraLabel ? ` • ${this.escapeHtml(extraLabel)}` : ''}</span>
            </div>
        `;
    }

    private renderArtistReviewCard(item: HifiReviewArtist): string {
        const reviewId = item.artist_id;
        const currentMatch = this.renderMatchCurrentCandidate('artist', item.hifi_id);
        const sourceHref = this.getMatchSourceHref(item, 'artist');

        return this.renderMatchWorkflowCard(
            'artist',
            reviewId,
            'Artist',
            item.name || 'Unknown Artist',
            'Compare the Plex library artist against Explore artist candidates.',
            item.confidence,
            `<span class="match-review-meta-item">Confidence ${this.formatMatchConfidence(item.confidence)}</span>`,
            `
                <section class="match-review-pane source-pane">
                    <div class="match-review-pane-label">Library Source</div>
                    <div class="match-review-pane-header">
                        ${this.renderMatchReviewArtwork(item.picture, item.name || 'Unknown Artist', 'artist')}
                        <div class="match-review-pane-stack">
                            ${this.renderMatchReviewTitle(item.name || 'Unknown Artist', { href: sourceHref })}
                            <div class="match-review-pane-copy">This is the artist currently indexed from your Plex library.</div>
                        </div>
                    </div>
                </section>
            `,
            `
                <section class="match-review-pane candidate-pane">
                    <div class="match-review-pane-label">Explore Candidates</div>
                    ${currentMatch}
                    ${this.renderMatchCandidateSearchControls('artist', reviewId)}
                    <div class="match-review-candidates" data-match-candidates-key="artist:${reviewId}">
                        ${this.renderMatchCandidateList('artist', reviewId)}
                    </div>
                    ${this.renderManualMatchEntry('artist', reviewId)}
                </section>
            `,
            [
                item.hifi_id ? `<button type="button" class="match-review-button primary" data-match-action="confirm-current" data-entity-type="artist" data-review-id="${reviewId}">Confirm Current</button>` : '',
                `<button type="button" class="match-review-button danger" data-match-action="reject" data-entity-type="artist" data-review-id="${reviewId}">Reject</button>`
            ].filter(Boolean).join('')
        );
    }

    private renderAlbumReviewCard(item: HifiReviewAlbum): string {
        const reviewId = item.album_id;
        const currentMatch = this.renderMatchCurrentCandidate('album', item.hifi_id, item.complete ? 'complete in library' : undefined);
        const sourceHref = this.getMatchSourceHref(item, 'album');

        return this.renderMatchWorkflowCard(
            'album',
            reviewId,
            'Album',
            item.title || 'Unknown Album',
            `${item.artist_name || 'Unknown Artist'} • Review the library album against Explore releases.`,
            item.confidence,
            [
                `<span class="match-review-meta-item">Confidence ${this.formatMatchConfidence(item.confidence)}</span>`,
                `<span class="match-review-meta-item">Tracks ${item.matched_track_count || 0}/${item.expected_track_count || 0}</span>`
            ].join(''),
            `
                <section class="match-review-pane source-pane">
                    <div class="match-review-pane-label">Library Source</div>
                    <div class="match-review-pane-header">
                        <div class="match-review-album-header">
                            ${this.renderMatchReviewTitle(item.title || 'Unknown Album', { href: sourceHref })}
                            <div class="match-review-album-artist">${this.escapeHtml(item.artist_name || 'Unknown Artist')}</div>
                        </div>
                        <div class="match-review-album-body">
                            ${this.renderMatchReviewArtwork(item.cover, item.title || 'Unknown Album', 'album')}
                            ${this.renderMatchTrackList(item.track_titles, 'Track list unavailable for this library album.')}
                        </div>
                    </div>
                </section>
            `,
            `
                <section class="match-review-pane candidate-pane">
                    <div class="match-review-pane-label">Explore Candidates</div>
                    ${currentMatch}
                    ${this.renderMatchCandidateSearchControls('album', reviewId)}
                    <div class="match-review-candidates" data-match-candidates-key="album:${reviewId}">
                        ${this.renderMatchCandidateList('album', reviewId)}
                    </div>
                    ${this.renderManualMatchEntry('album', reviewId)}
                </section>
            `,
            [
                item.hifi_id ? `<button type="button" class="match-review-button primary" data-match-action="confirm-current" data-entity-type="album" data-review-id="${reviewId}">Confirm Current</button>` : '',
                `<button type="button" class="match-review-button danger" data-match-action="reject" data-entity-type="album" data-review-id="${reviewId}">Reject</button>`
            ].filter(Boolean).join('')
        );
    }

    private renderTrackReviewCard(item: HifiReviewTrack): string {
        const reviewId = item.track_id;
        const subtitleParts = [item.artist_name, item.album_title].filter(Boolean);
        const currentMatch = this.renderMatchCurrentCandidate('track', item.hifi_id);
        const sourceHref = this.getMatchSourceHref(item, 'track');

        return this.renderMatchWorkflowCard(
            'track',
            reviewId,
            'Track',
            item.title || 'Unknown Track',
            `${subtitleParts.join(' • ') || 'Unknown'} • Compare the library file against Explore tracks.`,
            item.confidence,
            [
                `<span class="match-review-meta-item">Confidence ${this.formatMatchConfidence(item.confidence)}</span>`,
                `<span class="match-review-meta-item">Format ${this.escapeHtml((item.format || '—').toUpperCase())}</span>`,
                `<span class="match-review-meta-item">Bitrate ${typeof item.bitrate === 'number' ? `${item.bitrate} kbps` : '—'}</span>`
            ].join(''),
            `
                <section class="match-review-pane source-pane">
                    <div class="match-review-pane-label">Library Source</div>
                    <div class="match-review-pane-header">
                        ${this.renderMatchReviewArtwork(item.cover, item.album_title || item.title || 'Unknown Track', 'album')}
                        <div class="match-review-pane-stack">
                            ${this.renderMatchReviewTitle(item.title || 'Unknown Track', { href: sourceHref })}
                            <div class="match-review-pane-copy">${this.escapeHtml(subtitleParts.join(' • ') || 'Unknown')}</div>
                            <div class="match-review-pane-copy">Path: ${this.escapeHtml(item.path || '—')}</div>
                        </div>
                    </div>
                </section>
            `,
            `
                <section class="match-review-pane candidate-pane">
                    <div class="match-review-pane-label">Explore Candidates</div>
                    ${currentMatch}
                    ${this.renderMatchCandidateSearchControls('track', reviewId)}
                    <div class="match-review-candidates" data-match-candidates-key="track:${reviewId}">
                        ${this.renderMatchCandidateList('track', reviewId)}
                    </div>
                    ${this.renderManualMatchEntry('track', reviewId)}
                </section>
            `,
            [
                item.hifi_id ? `<button type="button" class="match-review-button primary" data-match-action="confirm-current" data-entity-type="track" data-review-id="${reviewId}">Confirm Current</button>` : '',
                `<button type="button" class="match-review-button danger" data-match-action="reject" data-entity-type="track" data-review-id="${reviewId}">Reject</button>`
            ].filter(Boolean).join('')
        );
    }

    private renderMatchReviewSection(title: string, count: number, itemsHtml: string): string {
        if (count === 0) {
            return '';
        }

        return `
            <section class="match-review-section">
                <div class="match-review-section-header">
                    <h3>${this.escapeHtml(title)}</h3>
                    <span class="match-review-count">${count} item${count === 1 ? '' : 's'}</span>
                </div>
                <div class="match-review-list">${itemsHtml}</div>
            </section>
        `;
    }

    private async loadMatchReview(): Promise<void> {
        if (!this.matchReviewContent || !this.matchReviewSummary) {
            return;
        }

        if (this.isMatchScanActive()) {
            this.renderMatchReviewBlockedByActiveScan();
            return;
        }

        const entityType = this.matchReviewEntityFilter?.value || 'all';
        const maxConfidence = this.matchReviewMaxConfidenceInput?.value || '0.94';
        const loadingMessage = 'Loading match review items...';
        this.matchReviewContent.innerHTML = `<p class="loading-text">${this.escapeHtml(loadingMessage)}</p>`;
        this.matchReviewSummary.innerHTML = '';
        this.setMatchReviewStatus('');

        try {
            const params = new URLSearchParams({
                entity_type: entityType,
                max_confidence: maxConfidence,
                limit: '100'
            });
            const response = await fetch(`/api/hifi/matches/review?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Failed to fetch match review items');
            }

            const data = await response.json() as HifiMatchReviewResponse;
            const artists = Array.isArray(data.artists) ? data.artists : [];
            const albums = Array.isArray(data.albums) ? data.albums : [];
            const tracks = Array.isArray(data.tracks) ? data.tracks : [];
            const artistTotal = typeof data.summary?.artists === 'number' ? data.summary.artists : artists.length;
            const albumTotal = typeof data.summary?.albums === 'number' ? data.summary.albums : albums.length;
            const trackTotal = typeof data.summary?.tracks === 'number' ? data.summary.tracks : tracks.length;

            this.matchReviewSummary.innerHTML = [
                this.renderMatchSummaryCard('Artists to review', artistTotal),
                this.renderMatchSummaryCard('Albums to review', albumTotal),
                this.renderMatchSummaryCard('Tracks to review', trackTotal)
            ].join('');

            const content = [
                this.renderMatchReviewSection('Artists', artists.length, artists.map(item => this.renderArtistReviewCard(item)).join('')),
                this.renderMatchReviewSection('Albums', albums.length, albums.map(item => this.renderAlbumReviewCard(item)).join('')),
                this.renderMatchReviewSection('Tracks', tracks.length, tracks.map(item => this.renderTrackReviewCard(item)).join(''))
            ].filter(Boolean).join('');

            this.matchReviewContent.innerHTML = content || '<div class="match-review-empty">No review items found for the current filters.</div>';
            this.openInitialMatchReviewCards();
        } catch (error) {
            console.error('Failed to load match review items:', error);
            this.matchReviewContent.innerHTML = '<div class="match-review-empty">Failed to load match review items.</div>';
            this.setMatchReviewStatus((error as Error).message || 'Failed to load match review items', true);
        }
    }

    private async startLibraryUpdate(): Promise<void> {
        if (!this.matchReviewRunScanButton) {
            return;
        }

        const originalText = this.matchReviewRunScanButton.textContent || 'Update & Sync Library';
        this.matchReviewRunScanButton.disabled = true;
        this.matchReviewRunScanButton.textContent = 'Queueing...';
        this.setMatchReviewStatus('');
        let queuedJobIsActive = false;

        try {
            const response = await fetch('/api/plex/library-updates', { method: 'POST' });
            const data = await response.json().catch(() => ({} as { error?: string; job_id?: number | string; status?: string }));
            if (!response.ok) {
                throw new Error(data.error || 'Failed to queue library update');
            }

            const queuedJobId = Number(data.job_id);
            const queuedStatus = String(data.status || '').trim().toLowerCase();
            queuedJobIsActive = !queuedStatus || queuedStatus === 'queued' || queuedStatus === 'in_progress';
            if (queuedJobIsActive && Number.isFinite(queuedJobId) && queuedJobId > 0) {
                this.activeMatchActivityJobId = queuedJobId;
                this.updateMatchReviewRunScanButton(true);
            }

            this.setMatchReviewStatus(`Library update queued as job ${data.job_id || 'unknown'}. Sync and matching will follow automatically.`);
            await this.loadMatchActivity();
            await this.loadJobs();
        } catch (error) {
            console.error('Failed to queue library update:', error);
            this.setMatchReviewStatus((error as Error).message || 'Failed to queue library update', true);
        } finally {
            if (queuedJobIsActive || this.activeMatchActivityJobId) {
                this.updateMatchReviewRunScanButton(true);
            } else {
                this.matchReviewRunScanButton.disabled = false;
                this.matchReviewRunScanButton.textContent = originalText;
            }
        }
    }

    private async cancelLibraryUpdate(jobId: number): Promise<void> {
        if (!this.matchReviewRunScanButton) {
            return;
        }

        const originalText = this.matchReviewRunScanButton.textContent || 'Cancel Update & Sync';
        this.matchReviewRunScanButton.disabled = true;
        this.matchReviewRunScanButton.textContent = 'Cancelling...';

        try {
            const response = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
            if (!response.ok) {
                let message = 'Failed to cancel library update';
                try {
                    const data = await response.json() as { error?: string };
                    if (data?.error) {
                        message = data.error;
                    }
                } catch {
                    // Ignore parse errors and keep fallback message
                }
                throw new Error(message);
            }

            this.activeMatchActivityJobId = null;
            this.updateMatchReviewRunScanButton(false);
            this.setMatchReviewStatus(`Library update cancelled for job ${jobId}.`);
            await this.loadMatchActivity();
            await this.loadJobs();
        } catch (error) {
            console.error('Failed to cancel library update:', error);
            this.matchReviewRunScanButton.disabled = false;
            this.matchReviewRunScanButton.textContent = originalText;
            this.setMatchReviewStatus((error as Error).message || 'Failed to cancel library update', true);
        }
    }

    private async loadMatchCandidates(entityType: 'artist' | 'album' | 'track', reviewId: number, container: HTMLElement, queryOverride?: string): Promise<void> {
        const cacheKey = `${entityType}:${reviewId}`;
        const normalizedQuery = String(queryOverride || '').trim();
        const isManualSearch = normalizedQuery.length > 0;

        if (!isManualSearch && this.matchCandidateCache.has(cacheKey)) {
            container.innerHTML = this.renderMatchCandidateList(entityType, reviewId);
            return;
        }

        if (!isManualSearch && this.matchCandidateRequestsInFlight.has(cacheKey)) {
            return;
        }

        this.matchCandidateRequestsInFlight.add(cacheKey);
        container.innerHTML = isManualSearch
            ? `<div class="match-review-inline-status">Searching for "${this.escapeHtml(normalizedQuery)}"...</div>`
            : '<div class="match-review-inline-status">Searching candidates...</div>';

        try {
            const params = new URLSearchParams({
                entity_type: entityType,
                id: String(reviewId),
                limit: '3'
            });
            if (normalizedQuery) {
                params.set('query', normalizedQuery);
            }
            const response = await fetch(`/api/hifi/matches/candidates?${params.toString()}`);
            const data = await response.json() as HifiMatchCandidatesResponse;
            if (!response.ok) {
                throw new Error(data.error || 'Failed to search candidates');
            }

            if (isManualSearch) {
                this.matchCandidateSearchTerms.set(cacheKey, normalizedQuery);
            }
            this.matchCandidateCache.set(cacheKey, Array.isArray(data.candidates) ? data.candidates : []);
            container.innerHTML = this.renderMatchCandidateList(entityType, reviewId);
        } catch (error) {
            console.error('Failed to load match candidates:', error);
            container.innerHTML = `<div class="match-review-empty">${this.escapeHtml((error as Error).message || 'Failed to search candidates')}</div>`;
        } finally {
            this.matchCandidateRequestsInFlight.delete(cacheKey);
        }
    }

    private async toggleMatchReviewCard(card: HTMLElement, forceOpen?: boolean): Promise<void> {
        const isOpen = card.classList.contains('is-open');
        const nextOpen = typeof forceOpen === 'boolean' ? forceOpen : !isOpen;
        const toggleButton = card.querySelector('[data-match-toggle]') as HTMLButtonElement | null;
        const entityType = String(card.getAttribute('data-entity-type') || '').trim() as 'artist' | 'album' | 'track';
        const reviewId = Number(card.getAttribute('data-review-id') || '0');
        const candidatesContainer = card.querySelector(`[data-match-candidates-key="${entityType}:${reviewId}"]`) as HTMLElement | null;

        card.classList.toggle('is-open', nextOpen);
        if (toggleButton) {
            toggleButton.setAttribute('aria-expanded', String(nextOpen));
            toggleButton.textContent = nextOpen ? 'Hide' : 'Review';
        }

        if (nextOpen && candidatesContainer && entityType && Number.isFinite(reviewId) && reviewId > 0) {
            await this.loadMatchCandidates(entityType, reviewId, candidatesContainer);
        }
    }

    private openInitialMatchReviewCards(): void {
        if (!this.matchReviewContent) {
            return;
        }

        const firstCards = Array.from(this.matchReviewContent.querySelectorAll('.match-review-section .match-review-card:first-child')) as HTMLElement[];
        firstCards.slice(0, 3).forEach(card => {
            void this.toggleMatchReviewCard(card, true);
        });
    }

    private async submitMatchReviewAction(entityType: 'artist' | 'album' | 'track', reviewId: number, action: 'confirm' | 'reject', hifiId?: string): Promise<void> {
        const response = await fetch('/api/hifi/matches/review', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                entity_type: entityType,
                id: reviewId,
                action,
                hifi_id: hifiId
            })
        });

        const data = await response.json().catch(() => ({} as { error?: string }));
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update review item');
        }
    }

    private async reloadMatchReviewPreserveScroll(): Promise<void> {
        const previousScrollY = window.scrollY;
        await this.loadMatchReview();
        window.scrollTo({ top: previousScrollY, behavior: 'auto' });
    }

    private async handleMatchReviewClick(e: MouseEvent): Promise<void> {
        const target = e.target as HTMLElement;
        const toggleButton = target.closest('[data-match-toggle]') as HTMLButtonElement | null;
        if (toggleButton) {
            const card = toggleButton.closest('.match-review-card') as HTMLElement | null;
            if (card) {
                await this.toggleMatchReviewCard(card);
            }
            return;
        }

        const actionButton = target.closest('[data-match-action]') as HTMLButtonElement | null;
        if (!actionButton) {
            return;
        }

        const action = String(actionButton.getAttribute('data-match-action') || '').trim();
        const entityType = String(actionButton.getAttribute('data-entity-type') || '').trim() as 'artist' | 'album' | 'track';
        const reviewId = Number(actionButton.getAttribute('data-review-id') || '0');
        const hifiId = String(actionButton.getAttribute('data-hifi-id') || '').trim() || undefined;
        if (!entityType || !Number.isFinite(reviewId) || reviewId <= 0) {
            return;
        }

        const card = actionButton.closest('.match-review-card') as HTMLElement | null;
        const candidatesContainer = card?.querySelector(`[data-match-candidates-key="${entityType}:${reviewId}"]`) as HTMLElement | null;
        const manualIdInput = card?.querySelector(`[data-match-manual-id="${entityType}:${reviewId}"]`) as HTMLInputElement | null;
        const candidateSearchInput = card?.querySelector(`[data-match-search-input="${entityType}:${reviewId}"]`) as HTMLInputElement | null;

        if (action === 'search-candidates') {
            if (!candidatesContainer) {
                return;
            }

            const query = String(candidateSearchInput?.value || '').trim();
            if (!query) {
                this.setMatchReviewStatus('Enter a search query to find candidates.', true);
                return;
            }

            try {
                actionButton.disabled = true;
                await this.loadMatchCandidates(entityType, reviewId, candidatesContainer, query);
                this.setMatchReviewStatus('Search complete. Showing up to 3 candidates.');
            } catch (error) {
                console.error('Failed to search match candidates:', error);
                this.setMatchReviewStatus((error as Error).message || 'Failed to search candidates', true);
            } finally {
                actionButton.disabled = false;
            }
            return;
        }

        try {
            actionButton.disabled = true;

            if (action === 'reject') {
                const confirmed = window.confirm('Reject this match candidate?');
                if (!confirmed) {
                    actionButton.disabled = false;
                    return;
                }
                await this.submitMatchReviewAction(entityType, reviewId, 'reject');
                this.setMatchReviewStatus('Match rejected.');
            } else if (action === 'confirm-current') {
                await this.submitMatchReviewAction(entityType, reviewId, 'confirm');
                this.setMatchReviewStatus('Match confirmed.');
            } else if (action === 'confirm-manual') {
                const manualId = String(manualIdInput?.value || '').trim();
                if (!manualId) {
                    throw new Error('Enter a HiFi ID before confirming manually.');
                }
                await this.submitMatchReviewAction(entityType, reviewId, 'confirm', manualId);
                this.setMatchReviewStatus(`Manual ${entityType} ID confirmed.`);
            } else if (action === 'confirm-candidate') {
                await this.submitMatchReviewAction(entityType, reviewId, 'confirm', hifiId);
                this.setMatchReviewStatus('Candidate selected and confirmed.');
            }

            this.matchCandidateCache.delete(`${entityType}:${reviewId}`);
            await this.reloadMatchReviewPreserveScroll();
        } catch (error) {
            console.error('Failed to update match review item:', error);
            this.setMatchReviewStatus((error as Error).message || 'Failed to update match review item', true);
            actionButton.disabled = false;
        }
    }

    private async handleMatchReviewKeydown(e: KeyboardEvent): Promise<void> {
        if (e.key !== 'Enter') {
            return;
        }

        const target = e.target as HTMLElement;
        const input = target.closest('[data-match-search-input]') as HTMLInputElement | null;
        if (!input) {
            return;
        }

        const key = String(input.getAttribute('data-match-search-input') || '').trim();
        const [entityTypeRaw, reviewIdRaw] = key.split(':');
        const entityType = entityTypeRaw as 'artist' | 'album' | 'track';
        const reviewId = Number(reviewIdRaw || '0');
        if (!entityType || !Number.isFinite(reviewId) || reviewId <= 0) {
            return;
        }

        const card = input.closest('.match-review-card') as HTMLElement | null;
        const searchButton = card?.querySelector(`[data-match-action="search-candidates"][data-entity-type="${entityType}"][data-review-id="${reviewId}"]`) as HTMLButtonElement | null;
        if (!searchButton) {
            return;
        }

        e.preventDefault();
        searchButton.click();
    }

    private async handleJobsContentClick(e: MouseEvent): Promise<void> {
        const target = e.target as HTMLElement;
        const cancelButton = target.closest('.job-cancel-button') as HTMLButtonElement | null;
        if (cancelButton) {
            const jobId = Number(cancelButton.getAttribute('data-job-id') || '0');
            if (!Number.isFinite(jobId) || jobId <= 0) {
                return;
            }

            await this.cancelJob(jobId, cancelButton);
            return;
        }

        const retryButton = target.closest('.job-retry-button') as HTMLButtonElement | null;
        if (!retryButton) {
            return;
        }

        const jobId = Number(retryButton.getAttribute('data-job-id') || '0');
        if (!Number.isFinite(jobId) || jobId <= 0) {
            return;
        }

        await this.retryJob(jobId, retryButton);
    }

    private async cancelJob(jobId: number, button: HTMLButtonElement): Promise<void> {
        const originalText = button.textContent || 'Cancel';
        button.disabled = true;
        button.textContent = 'Cancelling...';

        try {
            const response = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
            if (!response.ok) {
                let message = 'Failed to cancel job';
                try {
                    const data = await response.json() as { error?: string };
                    if (data?.error) {
                        message = data.error;
                    }
                } catch {
                    // Ignore parse errors and keep fallback message
                }
                throw new Error(message);
            }

            await this.loadJobs();
        } catch (error) {
            console.error('Cancel job failed:', error);
            window.alert((error as Error).message || 'Failed to cancel job');
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    private async retryJob(jobId: number, button: HTMLButtonElement): Promise<void> {
        const originalText = button.textContent || 'Retry';
        button.disabled = true;
        button.textContent = 'Retrying...';

        try {
            const response = await fetch(`/api/jobs/${jobId}/retry`, { method: 'POST' });
            if (!response.ok) {
                let message = 'Failed to retry job';
                try {
                    const data = await response.json() as { error?: string; status?: string };
                    if (response.status === 409 && data?.status === 'already_exists_in_plex') {
                        window.alert('Retry skipped: track already exists in Plex for the selected format.');
                        await this.loadJobs();
                        return;
                    }
                    if (data?.error) {
                        message = data.error;
                    }
                } catch {
                    // Ignore parse errors and keep fallback message
                }
                throw new Error(message);
            }

            await this.loadJobs();
        } catch (error) {
            console.error('Retry job failed:', error);
            window.alert((error as Error).message || 'Failed to retry job');
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    private renderJobItem(job: JobItem): string {
        const title = this.getJobDisplayTitle(job);
        const effectiveStatus = this.getEffectiveJobStatus(job);
        const statusLabel = this.formatJobStatus(effectiveStatus);
        const statusClass = `status-${effectiveStatus.replace(/_/g, '-')}`;
        const showCancelButton = effectiveStatus === 'queued' || effectiveStatus === 'in_progress';
        const showRetryButton = job.job_type === 'download_track' && (effectiveStatus === 'failed' || effectiveStatus === 'completed_with_errors');
        const actionsClass = `job-main-actions${showCancelButton ? ' cancel-on-hover' : ''}`;
        const stages = job.result?.stages || {};
        const playlistName = job.result?.playlist_name || job.payload?.plex_playlist || null;
        const skippedExisting = job.job_type === 'download_track' && Boolean(job.result && (job.result as Record<string, unknown>).download_skipped_existing);
        const upgradedExisting = job.job_type === 'download_track' && Boolean(job.result && (job.result as Record<string, unknown>).download_upgraded_existing);
        const upgradedFromBitrate = upgradedExisting ? ((job.result as Record<string, unknown>)?.upgraded_from_bitrate as number | null ?? null) : null;
        const downloadMirror = job.job_type === 'download_track' ? ((job.result as Record<string, unknown>)?.download_mirror as string | null ?? null) : null;

        if (job.job_type === 'plex_library_sync') {
            const stageRows = [
                { key: 'reading_plex_library', label: 'Reading Plex Library' },
                { key: 'updating_local_index', label: 'Updating Local Index' },
                { key: 'labeling_explicit_albums', label: 'Labeling Explicit Albums' },
                { key: 'backfilling_track_ids_from_tags', label: 'Backfilling Track IDs from Tags' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexSyncStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = job.result?.progress as Record<string, unknown> || {};
            const processed = Number(progress.processed_tracks || 0);
            const total = Number(progress.total_tracks || 0);
            const upserted = Number(progress.upserted_songs || 0);
            const deleted = Number(progress.deleted_songs || 0);
            const tagsRead = Number(progress.tags_read || 0);
            const tagsUpdated = Number(progress.tags_updated || 0);
            const syncText = total > 0
                ? `${processed}/${total} tracks processed • ${upserted} upserted • ${deleted} removed`
                : `${upserted} upserted • ${deleted} removed`;
            const tagText = `${tagsRead} tags read • ${tagsUpdated} updated`;

            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                            ${showRetryButton ? `<button type="button" class="job-retry-button" data-job-id="${job.id}">Retry</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(syncText)}</div>
                    <div class="job-sync-progress">${this.escapeHtml(tagText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        if (job.job_type === 'plex_library_update') {
            const stageRows = [
                { key: 'scanning_plex_library', label: 'Scanning Plex Library' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexLibraryUpdateStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = (job.result?.progress || {}) as Record<string, unknown>;
            const scanCompleted = progress.scan_completed === true;
            const syncQueueStatus = String(progress.sync_queue_status || 'pending');
            const syncJobId = Number(progress.sync_job_id || 0);

            const progressText = scanCompleted ? 'Library scan completed' : '';


            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                            ${showRetryButton ? `<button type="button" class="job-retry-button" data-job-id="${job.id}">Retry</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        if (job.job_type === 'automatic_matching') {
            const stageRows = [
                { key: 'plex_library_update', label: 'Plex Library Update' },
                { key: 'plex_sync', label: 'Plex Sync' },
                { key: 'tag_analysis', label: 'Tag Analysis' },
                { key: 'hifi_gap_fill', label: 'HiFi Gap Fill' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexSyncStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = (job.result?.progress || {}) as Record<string, unknown>;
            const plexSyncTracks = typeof progress.plex_sync_tracks === 'number' ? progress.plex_sync_tracks : 0;
            const tagScanned = typeof progress.tag_scanned === 'number' ? progress.tag_scanned : 0;
            const tagFilled = typeof progress.tag_filled === 'number' ? progress.tag_filled : 0;
            const hifiTracks = typeof progress.hifi_tracks_matched === 'number' ? progress.hifi_tracks_matched : 0;
            const hifiAlbums = typeof progress.hifi_albums_matched === 'number' ? progress.hifi_albums_matched : 0;
            const hifiArtists = typeof progress.hifi_artists_matched === 'number' ? progress.hifi_artists_matched : 0;
            const progressText = `Plex: ${plexSyncTracks} tracks synced • Tags: ${tagScanned} scanned • ${tagFilled} filled • HiFi: ${hifiTracks} tracks • ${hifiAlbums} albums • ${hifiArtists} artists matched`;

            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                            ${showRetryButton ? `<button type="button" class="job-retry-button" data-job-id="${job.id}">Retry</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        if (job.job_type === 'plex_listen_history_sync') {
            const stageRows = [
                { key: 'resolving_accounts', label: 'Resolving Accounts' },
                { key: 'fetching_history', label: 'Fetching History' },
                { key: 'storing_entries', label: 'Storing Entries' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexSyncStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = (job.result?.progress || {}) as Record<string, unknown>;
            const usersProcessed = Number(progress.users_processed || 0);
            const totalUsers = Number(progress.total_users || 0);
            const entriesFetched = Number(progress.entries_fetched || 0);
            const entriesStored = Number(progress.entries_stored || 0);
            const resultData = (job.result || {}) as Record<string, unknown>;
            const totalFetched = Number(resultData.total_entries_fetched || 0);
            const totalStored = Number(resultData.total_entries_stored || 0);
            const progressText = totalFetched > 0
                ? `${usersProcessed}/${totalUsers} users • ${totalFetched} entries fetched • ${totalStored} stored`
                : `${usersProcessed}/${totalUsers} users processed`;

            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                            ${showRetryButton ? `<button type="button" class="job-retry-button" data-job-id="${job.id}">Retry</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        if (job.job_type === 'generate_recommendations') {
            const stageRows = [
                { key: 'syncing_listen_history', label: 'Syncing Listen History' },
                { key: 'gathering_seeds', label: 'Gathering Seeds' },
                { key: 'fetching_recommendations', label: 'Fetching Recommendations' },
                { key: 'processing_tracks', label: 'Processing Tracks' },
                { key: 'saving_playlist', label: 'Saving Playlist' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexSyncStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = (job.result?.progress || {}) as Record<string, unknown>;
            const seedsFound = Number(progress.seeds_found || 0);
            const recsFetched = Number(progress.recommendations_fetched || 0);
            const afterFilter = Number(progress.tracks_after_filter || 0);
            const saved = Number(progress.tracks_saved || 0);
            const progressText = seedsFound > 0
                ? `${seedsFound} seeds • ${recsFetched} recommendations fetched • ${afterFilter} after filter • ${saved} tracks saved`
                : 'Waiting to start...';

            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        if (job.job_type === 'bulk_playlist_add') {
            const stageRows = [
                { key: 'resolving_tracks', label: 'Resolving Tracks' },
                { key: 'adding_to_playlists', label: 'Adding to Playlists' }
            ];

            const stageHtml = stageRows.map(stage => {
                const status = this.resolvePlexSyncStageStatus(job, stage.key, stages as Record<string, string>);
                const stageLabel = this.formatStageStatus(status);
                return `
                    <div class="job-stage">
                        <span>${stage.label}</span>
                        <span class="job-stage-status status-${status}">${stageLabel}</span>
                    </div>
                `;
            }).join('');

            const progress = (job.result || {}) as Record<string, unknown>;
            const total = Number(progress.total_tracks || 0);
            const processed = Number(progress.tracks_processed || 0);
            const added = Number(progress.tracks_added || 0);
            const skipped = Number(progress.tracks_skipped || 0);
            const failed = Number(progress.tracks_failed || 0);
            const progressText = total > 0
                ? `Processing ${processed}/${total} tracks • ${added} added • ${skipped} skipped • ${failed} failed`
                : 'Waiting to start...';

            return `
                <div class="job-item">
                    <div class="job-main">
                        <div class="job-title">${this.escapeHtml(title)}</div>
                        <div class="${actionsClass}">
                            <div class="job-status ${statusClass}">${statusLabel}</div>
                            ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                        </div>
                    </div>
                    <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                    <div class="job-stages">
                        ${stageHtml}
                    </div>
                </div>
            `;
        }

        const stageRows = [
            { key: 'downloaded', label: 'Downloaded' },
            { key: 'tagged', label: 'Tagged' },
            { key: 'written', label: 'Written to Disk' },
            ...(upgradedExisting ? [{ key: 'upgraded_existing', label: 'Upgraded Existing File' }] : []),
            ...(playlistName ? [{
key: 'playlist_added',
                 label: `Staged for Playlist "${this.escapeHtml(String(playlistName))}"`
            }] : []),
        ];

        const stageHtml = stageRows.map(stage => {
            const status = this.resolveStageStatus(job, stage.key as keyof JobStageMap, stages);
            const stageLabel = this.formatStageStatus(status);
            return `
                <div class="job-stage">
                    <span>${stage.label}</span>
                    <span class="job-stage-status status-${status}">${stageLabel}</span>
                </div>
            `;
        }).filter(Boolean).join('');

        return `
            <div class="job-item">
                <div class="job-main">
                    <div class="job-title">${this.escapeHtml(title)}</div>
                    <div class="${actionsClass}">
                        <div class="job-status ${statusClass}">${statusLabel}</div>
                        ${showCancelButton ? `<button type="button" class="job-cancel-button" data-job-id="${job.id}">Cancel</button>` : ''}
                        ${showRetryButton ? `<button type="button" class="job-retry-button" data-job-id="${job.id}">Retry</button>` : ''}
                    </div>
                </div>
                ${skippedExisting ? '<div class="job-sync-progress">Used existing file (download skipped)</div>' : ''}
                ${upgradedExisting ? `<div class="job-sync-progress">Upgraded existing file${upgradedFromBitrate ? ` (was ${upgradedFromBitrate} kbps)` : ''}</div>` : ''}
                ${downloadMirror ? `<div class="job-sync-progress">Discovered via <span class="mirror-url">${this.escapeHtml(downloadMirror)}</span></div>` : ''}
                <div class="job-stages">
                    ${stageHtml}
                </div>
            </div>
        `;
    }

    private getJobDisplayTitle(job: JobItem): string {
        if (job.job_type === 'plex_library_update') {
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'scheduled') {
                return 'Plex Library Update (Scheduled)';
            }
            if (trigger === 'manual') {
                return 'Plex Library Update (Manual)';
            }
            return 'Plex Library Update';
        }

        if (job.job_type === 'plex_library_sync') {
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'interval') {
                return 'Plex Library Sync (Interval)';
            }
            if (trigger === 'manual') {
                return 'Plex Library Sync (Manual)';
            }
            return 'Plex Library Sync';
        }

        if (job.job_type === 'hifi_match') {
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'manual') {
                return 'HiFi Match (Legacy, Manual)';
            }
            return 'HiFi Match (Legacy)';
        }

        if (job.job_type === 'automatic_matching') {
            const trigger = String(job.payload?.trigger || '').trim();
            if (trigger === 'manual') {
                return `Automatic Matching (Manual) #${job.id}`;
            }
            return `Automatic Matching #${job.id}`;
        }

        if (job.job_type === 'plex_listen_history_sync') {
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'post_library_sync') {
                return `Listen History Sync (Auto) #${job.id}`;
            }
            if (trigger === 'manual') {
                return `Listen History Sync (Manual) #${job.id}`;
            }
            return `Listen History Sync #${job.id}`;
        }

        if (job.job_type === 'generate_recommendations') {
            const username = job.payload?.plex_username || 'Unknown';
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'scheduled') return `Fresh Finds - ${username} (Scheduled) #${job.id}`;
            if (trigger === 'manual') return `Fresh Finds - ${username} (Manual) #${job.id}`;
            return `Fresh Finds - ${username} #${job.id}`;
        }

        if (job.job_type === 'bulk_playlist_add') {
            const trigger = String(job.result?.trigger || job.payload?.trigger || '').trim();
            if (trigger === 'post_library_sync') return `Playlist Update (Auto) #${job.id}`;
            if (trigger === 'manual') return `Playlist Update (Manual) #${job.id}`;
            return `Playlist Update #${job.id}`;
        }

        const artist = job.result?.artist || job.payload?.artist;
        const title = job.result?.title || job.payload?.title;

        if (artist && title) {
            return `${artist} - ${title}`;
        }

        const trackId = job.payload?.trackId;
        if (trackId) {
            return `Track ${trackId}`;
        }

        return `Job ${job.id}`;
    }

    private formatJobStatus(status: string): string {
        if (status === 'in_progress') {
            return 'In-Progress';
        }
        if (status === 'completed_with_errors') {
            return 'Completed with errors';
        }
        return status.charAt(0).toUpperCase() + status.slice(1);
    }

    private resolveStageStatus(job: JobItem, key: keyof JobStageMap, stages: JobStageMap): string {
        const value = stages[key];
        if (value) {
            return value;
        }

        if (job.status === 'succeeded') {
            return 'done';
        }

        if (job.status === 'cancelled') {
            return 'skipped';
        }

        return 'pending';
    }

    private formatStageStatus(status: string): string {
        if (!status) {
            return 'Pending';
        }

        return status.replace('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
    }

    private resolvePlexSyncStageStatus(job: JobItem, key: string, stages: Record<string, string>): string {
        const value = stages[key];
        if (value) {
            return value;
        }

        if (job.status === 'succeeded') {
            return 'done';
        }

        if (job.status === 'cancelled') {
            return 'skipped';
        }

        return 'pending';
    }

    private resolvePlexLibraryUpdateStageStatus(job: JobItem, key: string, stages: Record<string, string>): string {
        const value = stages[key];
        if (value) {
            return value;
        }

        if (job.status === 'succeeded') {
            return 'done';
        }

        if (job.status === 'cancelled') {
            return 'skipped';
        }

        return 'pending';
    }

    private openSettingsFlyout(): void {
        this.settingsFlyout.classList.add('active');
        this.settingsOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    private closeSettingsFlyout(): void {
        this.settingsFlyout.classList.remove('active');
        this.settingsOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    private defaultDownloadSettings(): DownloadSettings {
        return {
            downloadSource: 'tidal',
            quality: 'LOSSLESS',
            fileNamingAlbum: '{artist}/{album}/{track} - {title}.{ext}',
            jobsRefreshIntervalSeconds: 30,
            ignoreMatches: false,
            tagTitle: true,
            tagArtist: true,
            tagAlbumArtist: true,
            tagAlbum: true,
            tagYear: true,
            tagTrackNumber: true,
            tagTrackTotal: true,
            tagDiscNumber: true,
            tagDiscTotal: true,
            tagVersion: true,
            tagTidalTrackId: true,
            tagTidalAlbumId: true,
            tagIsrc: true,
            tagCopyright: true,
            tagCoverArt: true,
            tagExplicit: true,
            tagExplicitSuffix: true,
            penaltyCompilation: true,
            penaltyKaraoke: true,
            penaltyLive: true,
        };
    }

    private normalizeSettings(raw: Partial<DownloadSettings> & { format?: string; quality?: string }): DownloadSettings {
        const fallback = this.defaultDownloadSettings();
        const fileNaming = (raw as { file_naming?: string }).file_naming;
        const fileNamingAlbum = (raw as { file_naming_album?: string }).file_naming_album;
        const legacyFileNaming = (raw as { fileNaming?: string }).fileNaming;
        const jobsRefreshIntervalSecondsRaw = (raw as { jobs_refresh_interval_seconds?: number | string }).jobs_refresh_interval_seconds;
        const jobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds(
            (raw as { jobsRefreshIntervalSeconds?: number | string }).jobsRefreshIntervalSeconds
            ?? jobsRefreshIntervalSecondsRaw
        );

        let quality: DownloadQuality = fallback.quality;
        const rawQuality = String(raw.quality || raw.format || '').trim().toUpperCase();
        if (['LOSSLESS', 'HIGH', 'LOW'].includes(rawQuality)) {
            quality = rawQuality as DownloadQuality;
        } else if (String(raw.format).trim().toLowerCase() === 'original') {
            quality = 'LOSSLESS';
        } else if (String(raw.format).trim().toLowerCase() === 'mp3') {
            quality = 'HIGH';
        }

        return {
            downloadSource: typeof (raw as DownloadSettings).downloadSource === 'string'
                ? (raw as DownloadSettings).downloadSource
                : typeof (raw as { download_source?: string }).download_source === 'string'
                    ? (raw as { download_source?: string }).download_source!
                    : fallback.downloadSource,
            quality,
            fileNamingAlbum: typeof (raw as DownloadSettings).fileNamingAlbum === 'string'
                ? (raw as DownloadSettings).fileNamingAlbum
                : typeof fileNamingAlbum === 'string'
                    ? fileNamingAlbum
                    : typeof legacyFileNaming === 'string'
                        ? legacyFileNaming
                        : typeof fileNaming === 'string'
                            ? fileNaming
                            : fallback.fileNamingAlbum,
            jobsRefreshIntervalSeconds: jobsRefreshIntervalSeconds ?? fallback.jobsRefreshIntervalSeconds,
            ignoreMatches: typeof (raw as DownloadSettings).ignoreMatches === 'boolean'
                ? (raw as DownloadSettings).ignoreMatches
                : Boolean((raw as { ignore_matches?: boolean | string }).ignore_matches),
            tagTitle: typeof (raw as DownloadSettings).tagTitle === 'boolean' ? (raw as DownloadSettings).tagTitle : fallback.tagTitle,
            tagArtist: typeof (raw as DownloadSettings).tagArtist === 'boolean' ? (raw as DownloadSettings).tagArtist : fallback.tagArtist,
            tagAlbumArtist: typeof (raw as DownloadSettings).tagAlbumArtist === 'boolean' ? (raw as DownloadSettings).tagAlbumArtist : fallback.tagAlbumArtist,
            tagAlbum: typeof (raw as DownloadSettings).tagAlbum === 'boolean' ? (raw as DownloadSettings).tagAlbum : fallback.tagAlbum,
            tagYear: typeof (raw as DownloadSettings).tagYear === 'boolean' ? (raw as DownloadSettings).tagYear : fallback.tagYear,
            tagTrackNumber: typeof (raw as DownloadSettings).tagTrackNumber === 'boolean' ? (raw as DownloadSettings).tagTrackNumber : fallback.tagTrackNumber,
            tagTrackTotal: typeof (raw as DownloadSettings).tagTrackTotal === 'boolean' ? (raw as DownloadSettings).tagTrackTotal : fallback.tagTrackTotal,
            tagDiscNumber: typeof (raw as DownloadSettings).tagDiscNumber === 'boolean' ? (raw as DownloadSettings).tagDiscNumber : fallback.tagDiscNumber,
            tagDiscTotal: typeof (raw as DownloadSettings).tagDiscTotal === 'boolean' ? (raw as DownloadSettings).tagDiscTotal : fallback.tagDiscTotal,
            tagVersion: typeof (raw as DownloadSettings).tagVersion === 'boolean' ? (raw as DownloadSettings).tagVersion : fallback.tagVersion,
            tagTidalTrackId: typeof (raw as DownloadSettings).tagTidalTrackId === 'boolean' ? (raw as DownloadSettings).tagTidalTrackId : fallback.tagTidalTrackId,
            tagTidalAlbumId: typeof (raw as DownloadSettings).tagTidalAlbumId === 'boolean' ? (raw as DownloadSettings).tagTidalAlbumId : fallback.tagTidalAlbumId,
            tagIsrc: typeof (raw as DownloadSettings).tagIsrc === 'boolean' ? (raw as DownloadSettings).tagIsrc : fallback.tagIsrc,
            tagCopyright: typeof (raw as DownloadSettings).tagCopyright === 'boolean' ? (raw as DownloadSettings).tagCopyright : fallback.tagCopyright,
            tagCoverArt: typeof (raw as DownloadSettings).tagCoverArt === 'boolean' ? (raw as DownloadSettings).tagCoverArt : fallback.tagCoverArt,
            tagExplicit: typeof (raw as DownloadSettings).tagExplicit === 'boolean' ? (raw as DownloadSettings).tagExplicit : fallback.tagExplicit,
            tagExplicitSuffix: typeof (raw as DownloadSettings).tagExplicitSuffix === 'boolean' ? (raw as DownloadSettings).tagExplicitSuffix : fallback.tagExplicitSuffix,
            penaltyCompilation: typeof (raw as DownloadSettings).penaltyCompilation === 'boolean' ? (raw as DownloadSettings).penaltyCompilation : fallback.penaltyCompilation,
            penaltyKaraoke: typeof (raw as DownloadSettings).penaltyKaraoke === 'boolean' ? (raw as DownloadSettings).penaltyKaraoke : fallback.penaltyKaraoke,
            penaltyLive: typeof (raw as DownloadSettings).penaltyLive === 'boolean' ? (raw as DownloadSettings).penaltyLive : fallback.penaltyLive,
        };
    }

    private async fetchAppConfig(): Promise<void> {
        try {
            const response = await fetch('/api/app/config');
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            if (data.timezone) {
                this.timezone = data.timezone;
            }
        } catch (error) {
            console.warn('Failed to load app config.', error);
        }
    }

    private async fetchDownloadSettingsFromServer(): Promise<void> {
        try {
            const response = await fetch('/api/settings');
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            this.downloadSettings = this.normalizeSettings(data);
            this.applySettingsToForm(this.downloadSettings);
        } catch (error) {
            console.warn('Failed to load download settings.', error);
        }
    }

    private applySettingsToForm(settings: DownloadSettings): void {
        this.qualityLosslessInput.checked = settings.quality === 'LOSSLESS';
        this.qualityHighInput.checked = settings.quality === 'HIGH';
        this.qualityLowInput.checked = settings.quality === 'LOW';
        if (this.downloadSourceTidalInput) {
            this.downloadSourceTidalInput.checked = settings.downloadSource === 'tidal';
        }
        if (this.downloadSourceQobuzInput) {
            this.downloadSourceQobuzInput.checked = settings.downloadSource === 'qobuz';
        }
        this.fileNamingAlbumInput.value = settings.fileNamingAlbum;
        this.jobsRefreshIntervalSecondsInput.value = String(settings.jobsRefreshIntervalSeconds);
        this.ignoreMatchesCheckbox.checked = settings.ignoreMatches === true;
        this.tagTitleCheckbox.checked = settings.tagTitle;
        this.tagArtistCheckbox.checked = settings.tagArtist;
        this.tagAlbumArtistCheckbox.checked = settings.tagAlbumArtist;
        this.tagAlbumCheckbox.checked = settings.tagAlbum;
        this.tagYearCheckbox.checked = settings.tagYear;
        this.tagTrackNumberCheckbox.checked = settings.tagTrackNumber;
        this.tagTrackTotalCheckbox.checked = settings.tagTrackTotal;
        this.tagDiscNumberCheckbox.checked = settings.tagDiscNumber;
        this.tagDiscTotalCheckbox.checked = settings.tagDiscTotal;
        this.tagVersionCheckbox.checked = settings.tagVersion;
        this.tagTidalTrackIdCheckbox.checked = settings.tagTidalTrackId;
        this.tagTidalAlbumIdCheckbox.checked = settings.tagTidalAlbumId;
        this.tagIsrcCheckbox.checked = settings.tagIsrc;
        this.tagCopyrightCheckbox.checked = settings.tagCopyright;
        this.tagCoverArtCheckbox.checked = settings.tagCoverArt;
        this.tagExplicitCheckbox.checked = settings.tagExplicit;
        this.tagExplicitSuffixCheckbox.checked = settings.tagExplicitSuffix;
        this.penaltyCompilationCheckbox.checked = settings.penaltyCompilation;
        this.penaltyKaraokeCheckbox.checked = settings.penaltyKaraoke;
        this.penaltyLiveCheckbox.checked = settings.penaltyLive;
        this.syncQualityToggleStyles();
    }

    private readSettingsFromForm(): DownloadSettings {
        const fallbackIntervalSeconds = this.downloadSettings?.jobsRefreshIntervalSeconds ?? this.defaultDownloadSettings().jobsRefreshIntervalSeconds;
        const parsedJobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds(this.jobsRefreshIntervalSecondsInput.value);

        let quality: DownloadQuality = 'LOSSLESS';
        if (this.qualityHighInput.checked) {
            quality = 'HIGH';
        } else if (this.qualityLowInput.checked) {
            quality = 'LOW';
        }

        return {
            downloadSource: this.downloadSourceTidalInput?.checked ? 'tidal' : this.downloadSourceQobuzInput?.checked ? 'qobuz' : (this.downloadSettings?.downloadSource ?? 'tidal'),
            quality,
            fileNamingAlbum: this.fileNamingAlbumInput.value.trim(),
            jobsRefreshIntervalSeconds: parsedJobsRefreshIntervalSeconds ?? fallbackIntervalSeconds,
            ignoreMatches: this.ignoreMatchesCheckbox.checked,
            tagTitle: this.tagTitleCheckbox.checked,
            tagArtist: this.tagArtistCheckbox.checked,
            tagAlbumArtist: this.tagAlbumArtistCheckbox.checked,
            tagAlbum: this.tagAlbumCheckbox.checked,
            tagYear: this.tagYearCheckbox.checked,
            tagTrackNumber: this.tagTrackNumberCheckbox.checked,
            tagTrackTotal: this.tagTrackTotalCheckbox.checked,
            tagDiscNumber: this.tagDiscNumberCheckbox.checked,
            tagDiscTotal: this.tagDiscTotalCheckbox.checked,
            tagVersion: this.tagVersionCheckbox.checked,
            tagTidalTrackId: this.tagTidalTrackIdCheckbox.checked,
            tagTidalAlbumId: this.tagTidalAlbumIdCheckbox.checked,
            tagIsrc: this.tagIsrcCheckbox.checked,
            tagCopyright: this.tagCopyrightCheckbox.checked,
            tagCoverArt: this.tagCoverArtCheckbox.checked,
            tagExplicit: this.tagExplicitCheckbox.checked,
            tagExplicitSuffix: this.tagExplicitSuffixCheckbox.checked,
            penaltyCompilation: this.penaltyCompilationCheckbox.checked,
            penaltyKaraoke: this.penaltyKaraokeCheckbox.checked,
            penaltyLive: this.penaltyLiveCheckbox.checked,
        };
    }

    private updateSettingsFromForm(): void {
        this.downloadSettings = this.readSettingsFromForm();
        this.jobsRefreshIntervalSecondsInput.value = String(this.downloadSettings.jobsRefreshIntervalSeconds);
        this.queueSettingsSave();
        this.syncQualityToggleStyles();

        if (this.jobsFlyout?.classList.contains('active')) {
            this.startJobsPollingInterval();
        }
    }

    private normalizeJobsRefreshIntervalSeconds(value: unknown): number | null {
        if (typeof value === 'number' && Number.isFinite(value)) {
            const parsed = Math.floor(value);
            return parsed >= 1 ? parsed : null;
        }

        if (typeof value === 'string') {
            const parsed = parseInt(value, 10);
            return Number.isFinite(parsed) && parsed >= 1 ? parsed : null;
        }

        return null;
    }

    private startJobsPollingInterval(): void {
        if (this.jobsUpdateInterval) {
            window.clearInterval(this.jobsUpdateInterval);
            this.jobsUpdateInterval = null;
        }

        const intervalSeconds = this.downloadSettings?.jobsRefreshIntervalSeconds ?? this.defaultDownloadSettings().jobsRefreshIntervalSeconds;
        this.jobsUpdateInterval = window.setInterval(() => {
            void this.loadJobs();
        }, intervalSeconds * 1000);
    }

    private normalizeJobFilterTotals(totals: unknown, fallbackJobs: JobItem[]): JobFilterTotals {
        const fallback: JobFilterTotals = {
            incomplete: this.filterJobsByStatus(fallbackJobs, 'incomplete').length,
            complete: this.filterJobsByStatus(fallbackJobs, 'complete').length,
            completed_with_errors: this.filterJobsByStatus(fallbackJobs, 'completed_with_errors').length,
            failed: this.filterJobsByStatus(fallbackJobs, 'failed').length
        };

        if (!totals || typeof totals !== 'object') {
            return fallback;
        }

        const raw = totals as Record<string, unknown>;
        const parseCount = (value: unknown, fallbackValue: number): number => {
            if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
                return Math.floor(value);
            }
            return fallbackValue;
        };

        return {
            incomplete: parseCount(raw.incomplete, fallback.incomplete),
            complete: parseCount(raw.complete, fallback.complete),
            completed_with_errors: parseCount(raw.completed_with_errors, fallback.completed_with_errors),
            failed: parseCount(raw.failed, fallback.failed)
        };
    }

    private updateJobsFilterCounts(totals: JobFilterTotals): void {
        const incompleteCount = totals.incomplete;
        const completeCount = totals.complete;
        const completedWithErrorsCount = totals.completed_with_errors;
        const failedCount = totals.failed;

        const incompleteOption = this.jobsFilterSelect.querySelector('option[value="incomplete"]');
        if (incompleteOption) {
            incompleteOption.textContent = `Incomplete (${incompleteCount})`;
        }

        const completeOption = this.jobsFilterSelect.querySelector('option[value="complete"]');
        if (completeOption) {
            completeOption.textContent = `Complete (${completeCount})`;
        }

        const completedWithErrorsOption = this.jobsFilterSelect.querySelector('option[value="completed_with_errors"]');
        if (completedWithErrorsOption) {
            completedWithErrorsOption.textContent = `Completed with errors (${completedWithErrorsCount})`;
        }

        const failedOption = this.jobsFilterSelect.querySelector('option[value="failed"]');
        if (failedOption) {
            failedOption.textContent = `Failed (${failedCount})`;
        }
    }

    private getCookieValue(name: string): string | null {
        const match = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}=([^;]*)`));
        return match ? decodeURIComponent(match[1]) : null;
    }

    private queueSettingsSave(): void {
        if (this.settingsSaveTimer) {
            window.clearTimeout(this.settingsSaveTimer);
        }

        this.settingsSaveTimer = window.setTimeout(() => {
            void this.saveSettingsToServer(this.downloadSettings);
        }, this.settingsSaveDelayMs);
    }

    private async saveSettingsToServer(settings: DownloadSettings): Promise<void> {
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
        } catch (error) {
            console.warn('Failed to save download settings.', error);
        }
    }

    private syncQualityToggleStyles(): void {
        const losslessLabel = this.qualityLosslessInput.closest('label');
        const highLabel = this.qualityHighInput.closest('label');
        const lowLabel = this.qualityLowInput.closest('label');

        const isQobuz = this.downloadSourceQobuzInput?.checked ?? false;

        if (losslessLabel) {
            losslessLabel.classList.toggle('active', this.qualityLosslessInput.checked);
        }
        if (highLabel) {
            highLabel.classList.toggle('active', this.qualityHighInput.checked);
        }
        if (lowLabel) {
            const lowInput = this.qualityLowInput;
            if (isQobuz) {
                lowInput.disabled = true;
                lowInput.title = 'Qobuz does not support LOW quality';
                lowLabel.title = 'Qobuz does not support LOW quality';
                lowLabel.classList.add('disabled');
                if (lowInput.checked) {
                    this.qualityLosslessInput.checked = true;
                    lowInput.checked = false;
                    if (losslessLabel) losslessLabel.classList.add('active');
                    lowLabel.classList.remove('active');
                }
            } else {
                lowInput.disabled = false;
                lowInput.title = '';
                lowLabel.title = '';
                lowLabel.classList.remove('disabled');
            }
            lowLabel.classList.toggle('active', this.qualityLowInput.checked);
        }

        const tidalLabel = this.downloadSourceTidalInput?.closest('label');
        const qobuzLabel = this.downloadSourceQobuzInput?.closest('label');
        if (tidalLabel) tidalLabel.classList.toggle('active', this.downloadSourceTidalInput?.checked ?? false);
        if (qobuzLabel) qobuzLabel.classList.toggle('active', this.downloadSourceQobuzInput?.checked ?? false);
    }

    private async loadListenbrainzConfig(): Promise<void> {
        try {
            const userId = this.getSelectedPlexUserId();
            const response = await fetch(`/api/listenbrainz/config${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`);
            if (response.ok) {
                const data = await response.json();
                this.lbConfigStatusEl.textContent = data.has_token ? '✓ Token configured' : '';
                this.lbConfigStatusEl.style.color = data.has_token ? 'var(--accent-primary)' : '';
                if (data.username) {
                    this.listenbrainzUsernameInput.value = data.username;
                } else {
                    this.listenbrainzUsernameInput.value = '';
                }
            }
        } catch (error) {
            console.warn('Failed to load ListenBrainz config.', error);
        }
    }

    private async saveListenbrainzConfig(): Promise<void> {
        const userToken = this.listenbrainzTokenInput.value.trim();
        const username = this.listenbrainzUsernameInput.value.trim();

        if (!userToken) {
            this.lbConfigStatusEl.textContent = '⚠ User token is required';
            this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
            return;
        }

        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                this.lbConfigStatusEl.textContent = '⚠ Select a Plex user before saving ListenBrainz settings';
                this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
                return;
            }

            const response = await fetch('/api/listenbrainz/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_token: userToken,
                    username: username,
                    user_id: userId
                })
            });

            if (response.ok) {
                this.lbConfigStatusEl.textContent = '✓ Configuration saved';
                this.lbConfigStatusEl.style.color = 'var(--accent-primary)';
                this.listenbrainzTokenInput.value = '';
                void this.updateSidebarPlaylists();
                // Clear status message after 3 seconds
                setTimeout(() => {
                    this.lbConfigStatusEl.textContent = '';
                }, 3000);
            } else {
                this.lbConfigStatusEl.textContent = '✗ Failed to save configuration';
                this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
            }
        } catch (error) {
            console.error('Error saving ListenBrainz config:', error);
            this.lbConfigStatusEl.textContent = '✗ Error saving configuration';
            this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
        }
    }

    private async loadFreshFindsAutoDownload(): Promise<void> {
        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                this.autoDownloadFreshFindsCheckbox.checked = false;
                return;
            }
            const response = await fetch(`/api/fresh-finds/auto-download?user_id=${encodeURIComponent(userId)}`);
            if (response.ok) {
                const data = await response.json();
                this.autoDownloadFreshFindsCheckbox.checked = data.enabled;
            }
        } catch (error) {
            console.warn('Failed to load Fresh Finds auto-download setting.', error);
        }
    }

    private async saveFreshFindsAutoDownload(): Promise<void> {
        const enabled = this.autoDownloadFreshFindsCheckbox.checked;
        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                this.freshFindsAutoDownloadStatusEl.textContent = '⚠ Select a Plex user first';
                this.freshFindsAutoDownloadStatusEl.style.color = 'var(--text-secondary)';
                return;
            }

            const response = await fetch('/api/fresh-finds/auto-download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    enabled: enabled
                })
            });

            if (response.ok) {
                this.freshFindsAutoDownloadStatusEl.textContent = enabled ? '✓ Auto-download enabled' : '✓ Auto-download disabled';
                this.freshFindsAutoDownloadStatusEl.style.color = 'var(--accent-primary)';
                setTimeout(() => {
                    this.freshFindsAutoDownloadStatusEl.textContent = '';
                }, 3000);
            } else {
                this.freshFindsAutoDownloadStatusEl.textContent = '✗ Failed to save setting';
                this.freshFindsAutoDownloadStatusEl.style.color = 'var(--text-secondary)';
                // Revert checkbox on failure
                this.autoDownloadFreshFindsCheckbox.checked = !enabled;
            }
        } catch (error) {
            console.error('Error saving Fresh Finds auto-download setting:', error);
            this.freshFindsAutoDownloadStatusEl.textContent = '✗ Error saving setting';
            this.freshFindsAutoDownloadStatusEl.style.color = 'var(--text-secondary)';
            this.autoDownloadFreshFindsCheckbox.checked = !enabled;
        }
    }

    private async loadFreshFindsRetention(): Promise<void> {
        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                if (this.freshFindsRetentionInput) {
                    this.freshFindsRetentionInput.value = '7';
                }
                return;
            }
            const response = await fetch(`/api/fresh-finds/retention?user_id=${encodeURIComponent(userId)}`);
            if (response.ok) {
                const data = await response.json();
                if (this.freshFindsRetentionInput && data.count) {
                    this.freshFindsRetentionInput.value = String(data.count);
                    this.freshFindsRetentionInput.dispatchEvent(new Event('change'));
                }
            } else {
                if (this.freshFindsRetentionStatusEl) {
                    this.freshFindsRetentionStatusEl.textContent = '✗ Failed to load retention setting';
                    this.freshFindsRetentionStatusEl.style.color = 'var(--text-secondary)';
                }
            }
        } catch (error) {
            console.warn('Failed to load Fresh Finds retention setting.', error);
            if (this.freshFindsRetentionStatusEl) {
                this.freshFindsRetentionStatusEl.textContent = '✗ Error loading retention setting';
                this.freshFindsRetentionStatusEl.style.color = 'var(--text-secondary)';
            }
        }
    }

    private async saveFreshFindsRetention(): Promise<void> {
        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                if (this.freshFindsRetentionStatusEl) {
                    this.freshFindsRetentionStatusEl.textContent = '⚠ Select a Plex user first';
                    this.freshFindsRetentionStatusEl.style.color = 'var(--text-secondary)';
                }
                return;
            }

            const count = parseInt(this.freshFindsRetentionInput.value, 10);
            const response = await fetch('/api/fresh-finds/retention', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    count: count
                })
            });

            if (response.ok) {
                this.freshFindsRetentionStatusEl.textContent = `✓ Retention set to ${count} playlists`;
                this.freshFindsRetentionStatusEl.style.color = 'var(--accent-primary)';
                setTimeout(() => {
                    this.freshFindsRetentionStatusEl.textContent = '';
                }, 3000);
            } else {
                this.freshFindsRetentionStatusEl.textContent = '✗ Failed to save setting';
                this.freshFindsRetentionStatusEl.style.color = 'var(--text-secondary)';
            }
        } catch (error) {
            console.error('Error saving Fresh Finds retention setting:', error);
            this.freshFindsRetentionStatusEl.textContent = '✗ Error saving setting';
            this.freshFindsRetentionStatusEl.style.color = 'var(--text-secondary)';
        }
    }

    private async loadYtmConfig(): Promise<void> {
        try {
            const userId = this.getSelectedPlexUserId();
            const response = await fetch(`/api/youtube_music/config${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`);
            if (response.ok) {
                const data = await response.json();
                this.ytmConfigStatusEl.textContent = data.has_headers ? '✓ Cookie configured' : '';
                this.ytmConfigStatusEl.style.color = data.has_headers ? 'var(--accent-primary)' : '';
            }
        } catch (error) {
            console.warn('Failed to load YouTube Music config.', error);
        }
    }

    private async saveYtmConfig(): Promise<void> {
        const cookie = this.ytmCookieInput.value.trim();

        if (!cookie) {
            this.ytmConfigStatusEl.textContent = '⚠ Cookie is required';
            this.ytmConfigStatusEl.style.color = 'var(--text-secondary)';
            return;
        }

        try {
            const userId = this.getSelectedPlexUserId();
            if (!userId) {
                this.ytmConfigStatusEl.textContent = '⚠ Select a Plex user before saving YouTube Music settings';
                this.ytmConfigStatusEl.style.color = 'var(--text-secondary)';
                return;
            }

            const response = await fetch('/api/youtube_music/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cookie, user_id: userId })
            });

            if (response.ok) {
                this.ytmConfigStatusEl.textContent = '✓ Configuration saved';
                this.ytmConfigStatusEl.style.color = 'var(--accent-primary)';
                this.ytmCookieInput.value = '';
                void this.updateSidebarPlaylists();
                setTimeout(() => {
                    this.ytmConfigStatusEl.textContent = '';
                }, 3000);
            } else {
                const errorData = await response.json().catch(() => ({}));
                this.ytmConfigStatusEl.textContent = `✗ ${errorData.error || 'Failed to save'}`;
                this.ytmConfigStatusEl.style.color = 'var(--text-secondary)';
            }
        } catch (error) {
            console.error('Error saving YouTube Music config:', error);
            this.ytmConfigStatusEl.textContent = '✗ Error saving configuration';
            this.ytmConfigStatusEl.style.color = 'var(--text-secondary)';
        }
    }

    private async loadPlexConfig(): Promise<void> {
        try {
            const response = await fetch('/api/plex/config');
            if (response.ok) {
                const data = await response.json();
                // Populate the login-only library dropdown with saved library
                if (this.plexLoginOnlyLibraryNameSelect) {
                    this.plexLoginOnlyLibraryNameSelect.innerHTML = '';
                    const defaultOption = document.createElement('option');
                    defaultOption.value = '';
                    defaultOption.textContent = 'Select a library...';
                    this.plexLoginOnlyLibraryNameSelect.appendChild(defaultOption);
                    if (data.library_name) {
                        const option = document.createElement('option');
                        option.value = data.library_name;
                        option.textContent = data.library_name;
                        this.plexLoginOnlyLibraryNameSelect.appendChild(option);
                        this.plexLoginOnlyLibraryNameSelect.value = data.library_name;
                    }
                }
                const intervalHours = Number(data.sync_interval_hours);
                this.plexSyncIntervalHoursInput.value = Number.isFinite(intervalHours) && intervalHours > 0
                    ? String(intervalHours)
                    : '24';
                this.isPlexConfigured = data.has_config ? true : false;
                this.updatePlexConfigStatus(data.has_config ? '✓ Configured' : '');

                const configuredLibraryName = String(data.library_name || '').trim();
                const savedUserId = window.localStorage.getItem('plexSelectedUserId') || '';
                const libraryConfigured = Boolean(configuredLibraryName);
                const shouldShowPlexLoginOnly = !data.has_config || !libraryConfigured || !savedUserId;

                if (this.plexLoginOnlyContainer) {
                    this.plexLoginOnlyContainer.style.display = shouldShowPlexLoginOnly ? 'flex' : 'none';
                }
                if (this.appWrapper) {
                    this.appWrapper.style.display = shouldShowPlexLoginOnly ? 'none' : '';
                }

                if (this.plexLoginOnlyLibraryNameSelect) {
                    this.plexLoginOnlyLibraryNameSelect.value = configuredLibraryName;
                }

                this.updatePlexLoginOnlyState();

                this.updatePlexPlaylistContainerVisibility(false);
                if (this.isPlexConfigured) {
                    void this.loadPlexLibraries();
                } else {
                    this.populatePlexPlaylistOptions([]);
                }
            }
        } catch (error) {
            console.warn('Failed to load Plex config.', error);
        }
    }

    private async updatePlexLoginOnlyState(): Promise<void> {
        if (!this.plexLoginOnlyContainer || !this.appWrapper) {
            return;
        }

        const savedUserId = window.localStorage.getItem('plexSelectedUserId') || '';
        const libraryName = this.plexLoginOnlyLibraryNameSelect?.value?.trim() || '';
        const libraryConfigured = Boolean(libraryName);
        const needsLogin = !this.isPlexConfigured;
        const needsLibrary = this.isPlexConfigured && !libraryConfigured;
        const needsUser = this.isPlexConfigured && libraryConfigured && !savedUserId;
        const shouldShowOverlay = needsLogin || needsLibrary || needsUser;

        this.plexLoginOnlyContainer.style.display = shouldShowOverlay ? 'flex' : 'none';
        this.appWrapper.style.display = shouldShowOverlay ? 'none' : '';

        if (this.plexLoginOnlyButton) {
            this.plexLoginOnlyButton.style.display = needsLogin ? '' : 'none';
            this.plexLoginOnlyButton.disabled = needsLogin ? false : true;
        }

        if (this.plexLoginOnlyLibraryContainer) {
            this.plexLoginOnlyLibraryContainer.style.display = needsLibrary ? 'flex' : 'none';
        }

        if (this.plexLoginOnlyUserContainer) {
            this.plexLoginOnlyUserContainer.style.display = needsUser ? 'flex' : 'none';
        }


        if (needsLibrary && this.plexLoginOnlyLibraryNameSelect) {
            await this.loadPlexLibraries();
        }

        if (needsUser) {
            await this.loadPlexUsers(false, true);
        }
    }

    private async loadPlexLibraries(): Promise<void> {
        try {
            const response = await fetch('/api/plex/libraries');
            if (!response.ok) {
                throw new Error('Failed to fetch Plex libraries');
            }
            const data = await response.json();
            const libraries = Array.isArray(data.libraries) ? data.libraries : [];
            const current = this.plexLoginOnlyLibraryNameSelect?.value || '';

            if (this.plexLoginOnlyLibraryNameSelect) {
                this.plexLoginOnlyLibraryNameSelect.innerHTML = '';
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Select a library...';
                this.plexLoginOnlyLibraryNameSelect.appendChild(defaultOption);
            }

            libraries.forEach((library: string) => {
                const option = document.createElement('option');
                option.value = library;
                option.textContent = library;
                if (this.plexLoginOnlyLibraryNameSelect) {
                    const cloneOption = document.createElement('option');
                    cloneOption.value = library;
                    cloneOption.textContent = library;
                    this.plexLoginOnlyLibraryNameSelect.appendChild(cloneOption);
                }
            });

            if (current && this.plexLoginOnlyLibraryNameSelect) {
                this.plexLoginOnlyLibraryNameSelect.value = current;
            }
        } catch (error) {
            console.warn('Failed to load Plex libraries.', error);
        }
    }

    private async savePlexConfig(): Promise<void> {
        const libraryName = this.plexLoginOnlyLibraryNameSelect?.value?.trim() || '';
        if (!libraryName) {
            window.alert('Please select a library before saving.');
            return;
        }

        try {
            const payload = {
                library_name: libraryName
            };

            const response = await fetch('/api/plex/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || 'Failed to save Plex configuration');
            }

            await this.loadPlexConfig();
            void this.updatePlexClearCredentialsButton();

            // Show saved state and hide config controls
            const library = this.plexLoginOnlyLibraryNameSelect?.value.trim() || '';
            if (this.plexConnectedStatusEl) {
                const serverLabel = this.plexConnectedStatusEl.textContent?.replace(/^Connected to\s*/, '') || '';
                const serverName = serverLabel || '';
                const libraryText = library ? ` (library: ${library})` : '';
                this.plexConnectedStatusEl.textContent = `Connected to ${serverName}${libraryText}`.trim();
                this.plexConnectedStatusEl.style.display = 'block';
            }

            window.alert('Plex configuration saved.');
        } catch (error) {
            console.error('Failed to save Plex config:', error);
            window.alert((error as Error).message || 'Failed to save Plex configuration');
        }
    }




    private async savePlexConfigFromLoginOnly(): Promise<void> {
        const libraryName = this.plexLoginOnlyLibraryNameSelect?.value?.trim() || '';
        if (!libraryName) {
            window.alert('Please select a library before saving.');
            return;
        }

        try {
            const payload = {
                library_name: libraryName
            };

            const response = await fetch('/api/plex/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || 'Failed to save Plex configuration');
            }

            await this.loadPlexConfig();
            void this.updatePlexClearCredentialsButton();
            await this.updatePlexLoginOnlyState();

            window.alert('Plex configuration saved.');
        } catch (error) {
            console.error('Failed to save Plex config (overlay):', error);
            window.alert((error as Error).message || 'Failed to save Plex configuration');
        }
    }

    // --- PIN OAuth logic ---
    private async startPlexPinLogin(): Promise<void> {
        console.debug('[PLEX_UI] startPlexPinLogin called');
        if (this.plexLoginOnlyContainer) {
            this.plexLoginOnlyContainer.style.display = 'flex';
        }
        if (this.appWrapper) {
            this.appWrapper.style.display = 'none';
        }

        // Prepare UI for PIN-based login flow
        if (this.plexLoginButton) {
            this.plexLoginButton.disabled = true;
            this.plexLoginButton.style.display = 'none';
        }
        if (this.plexLoginOnlyLibraryContainer) {
            this.plexLoginOnlyLibraryContainer.style.display = 'none';
        }
        if (this.plexConnectedStatusEl) {
            this.plexConnectedStatusEl.style.display = 'none';
        }

        if (this.plexLoginOnlyPinContainer) {
            this.plexLoginOnlyPinContainer.style.display = 'block';
        }
        if (this.plexLoginOnlyPinStatus) {
            this.plexLoginOnlyPinStatus.textContent = 'Requesting PIN...';
        }
        if (this.plexLoginOnlyPinDisplay) {
            this.plexLoginOnlyPinDisplay.textContent = '';
        }
        try {
            const resp = await fetch('/api/plex/pin/start', { method: 'POST' });
            console.debug('[PLEX_UI] /api/plex/pin/start response', resp.status);
            const data = await resp.json();
            console.debug('[PLEX_UI] /api/plex/pin/start data', data);
            if (!data.ok) throw new Error(data.error || 'Failed to start PIN login');
            if (this.plexLoginOnlyPinDisplay) {
                this.plexLoginOnlyPinDisplay.textContent = data.pin;
            }
            if (this.plexLoginOnlyPinStatus) {
                this.plexLoginOnlyPinStatus.textContent = '';
            }
            await this.pollPlexPinStatus(data.client_id, data.pin, 300);
        } catch (e) {
            console.debug('[PLEX_UI] startPlexPinLogin error', e);
            if (this.plexLoginOnlyPinStatus) {
                this.plexLoginOnlyPinStatus.textContent = 'Failed to start PIN login.';
            }
            if (this.plexLoginOnlyButton) {
                this.plexLoginOnlyButton.style.display = '';
            }
            // Restore login button so user can retry
            if (this.plexLoginButton) {
                this.plexLoginButton.disabled = false;
                this.plexLoginButton.style.display = '';
            }
        }
    }

    private async pollPlexPinStatus(client_id: string, pin: string, timeoutSeconds: number): Promise<void> {
        console.debug('[PLEX_UI] pollPlexPinStatus started', { client_id, pin });
        let elapsed = 0;
        const pollInterval = 2000;
        while (elapsed < timeoutSeconds * 1000) {
            await new Promise(r => setTimeout(r, pollInterval));
            elapsed += pollInterval;
            try {
                const resp = await fetch('/api/plex/pin/status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id, pin })
                });
                console.debug('[PLEX_UI] /api/plex/pin/status response', resp.status);
                const data = await resp.json();
                console.debug('[PLEX_UI] /api/plex/pin/status data', data);
                if (data.ok && data.token && data.baseurl) {
                    if (this.plexLoginOnlyPinStatus) {
                        this.plexLoginOnlyPinStatus.textContent = '✓ Plex login successful!';
                    }
                    if (this.plexLoginOnlyPinDisplay) {
                        this.plexLoginOnlyPinDisplay.textContent = '';
                    }
                    if (this.plexLoginOnlyPinContainer) {
                        this.plexLoginOnlyPinContainer.style.display = 'none';
                    }
                    this.isPlexConfigured = true;
                    this.updatePlexConfigStatus('✓ Configured');
                    await this.loadPlexConfig();
                    await this.loadPlexLibraries();
                    await this.loadPlexUsers(false, true);
                    await this.updatePlexLoginOnlyState();

                    // Refresh cached health status so the UI can update properly
                    await fetch('/api/plex/healthcheck', { cache: 'no-store' }).catch(() => null);
                    return;
                } else if (data.expired) {
                    if (this.plexLoginOnlyPinStatus) {
                        this.plexLoginOnlyPinStatus.textContent = 'PIN expired. Please try again.';
                    }
                    if (this.plexLoginOnlyPinDisplay) {
                        this.plexLoginOnlyPinDisplay.textContent = '';
                    }
                    if (this.plexLoginButton) {
                        this.plexLoginButton.disabled = false;
                        this.plexLoginButton.style.display = '';
                    }
                    return;
                }
            } catch (e) {
                console.debug('[PLEX_UI] pollPlexPinStatus error', e);
                if (this.plexLoginOnlyPinStatus) {
                    this.plexLoginOnlyPinStatus.textContent = 'Error polling PIN status.';
                }
                if (this.plexLoginOnlyPinDisplay) {
                    this.plexLoginOnlyPinDisplay.textContent = '';
                }
                if (this.plexLoginOnlyButton) {
                    this.plexLoginOnlyButton.style.display = '';
                }
                if (this.plexLoginButton) {
                    this.plexLoginButton.disabled = false;
                    this.plexLoginButton.style.display = '';
                }
                return;
            }
        }
        console.debug('[PLEX_UI] pollPlexPinStatus timed out');
        if (this.plexLoginOnlyPinStatus) {
            this.plexLoginOnlyPinStatus.textContent = 'Login timed out. Please try again.';
        }
        if (this.plexLoginOnlyPinDisplay) {
            this.plexLoginOnlyPinDisplay.textContent = '';
        }
        if (this.plexLoginOnlyButton) {
            this.plexLoginOnlyButton.style.display = '';
        }
        if (this.plexLoginButton) {
            this.plexLoginButton.disabled = false;
            this.plexLoginButton.style.display = '';
        }
    }

    private async startPlexSync(): Promise<void> {
        this.plexSyncStatusEl.textContent = 'Starting library update...';
        this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
        this.startPlexSyncButton.disabled = true;

        try {
            const libUpdateResponse = await fetch('/api/plex/library-updates', {
                method: 'POST'
            });

            if (libUpdateResponse.status !== 202) {
                const data = await libUpdateResponse.json().catch(() => ({}));
                this.plexSyncStatusEl.textContent = `✗ ${data.error || 'Failed to start library update'}`;
                this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
                return;
            }

            this.plexSyncStatusEl.textContent = '✓ Plex library update queued; sync will follow automatically';
            this.plexSyncStatusEl.style.color = 'var(--accent-primary)';

            if (this.jobsFlyout && this.jobsFlyout.classList.contains('active')) {
                await this.loadJobs();
            }
        } catch (error) {
            console.error('Error starting Plex sync:', error);
            this.plexSyncStatusEl.textContent = '✗ Error starting library update';
            this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
        } finally {
            this.startPlexSyncButton.disabled = false;
        }
    }

    private updatePlexConfigStatus(message: string): void {
        if (!this.plexConfigStatusEl) {
            console.debug('[PLEX_UI] updatePlexConfigStatus: plexConfigStatusEl not found');
            return;
        }
        this.plexConfigStatusEl.textContent = message;
        this.plexConfigStatusEl.style.color = message.includes('✓') ? 'var(--accent-primary)' : 'var(--text-secondary)';
    }

    private async updatePlexClearCredentialsButton(): Promise<void> {
        if (!this.plexClearCredentialsButton) {
            console.debug('[PLEX_UI] plexClearCredentialsButton not found in DOM');
            return;
        }

        try {
            // First check whether the app has a configured Plex credential set.
            const configResp = await fetch('/api/plex/config', { cache: 'no-store' });
            const configData = configResp.ok ? await configResp.json() : { has_config: false };
            const hasConfig = Boolean(configData && configData.has_config);
            const hasLibrary = Boolean(configData && configData.library_name);

            // Show the Login button when Plex has not been configured yet.
            if (this.plexLoginButton) {
                this.plexLoginButton.disabled = false;
                this.plexLoginButton.style.display = hasConfig ? 'none' : '';
            }

            // Only show Clear Credentials and the playlist controls after the library has been selected (full configuration).
            const showPlexControls = hasConfig && hasLibrary;
            if (showPlexControls) {
                this.plexClearCredentialsButton.style.display = 'inline-block';
                this.updatePlexPlaylistContainerVisibility(true);
                await this.loadPlexUsers();
            } else {
                this.plexClearCredentialsButton.style.display = 'none';
                this.updatePlexPlaylistContainerVisibility(false);
            }

            // Update connected-server label only if health is good.
            const healthResp = await fetch('/api/plex/healthcheck', { cache: 'no-store' });
            const healthData = healthResp.ok ? await healthResp.json() : { ok: false };
            const healthOk = Boolean(healthData && healthData.ok);

            if (this.plexConnectedStatusEl) {
                if (healthOk && typeof healthData.server_name === 'string' && healthData.server_name.trim()) {
                    const library = this.plexLoginOnlyLibraryNameSelect?.value?.trim() || '';
                    const libraryText = library ? ` (library: ${library})` : '';
                    this.plexConnectedStatusEl.textContent = `Connected to ${healthData.server_name}${libraryText}`;
                    this.plexConnectedStatusEl.style.display = 'block';
                } else {
                    this.plexConnectedStatusEl.textContent = '';
                    this.plexConnectedStatusEl.style.display = 'none';
                }
            }
        } catch (err) {
            console.debug('[PLEX_UI] updatePlexClearCredentialsButton error', err);
            if (this.plexConnectedStatusEl) {
                this.plexConnectedStatusEl.textContent = '';
                this.plexConnectedStatusEl.style.display = 'none';
            }
            this.plexClearCredentialsButton.style.display = 'none';
            this.updatePlexPlaylistContainerVisibility(false);
            if (this.plexLoginButton) {
                this.plexLoginButton.disabled = false;
                this.plexLoginButton.style.display = '';
            }
        }
    }

    private async loadPlexUsers(defaultToOwner: boolean = true, syncRemote: boolean = false): Promise<void> {
        if (!this.plexLoginOnlyUserList) {
            return;
        }

        try {
            const url = syncRemote ? '/api/plex/users?sync=true' : '/api/plex/users';
            const response = await fetch(url, { cache: 'no-store' });
            if (!response.ok) {
                throw new Error('Failed to fetch Plex users');
            }

            const data = await response.json();
            const users = Array.isArray(data.users) ? data.users : [];

            this.plexLoginOnlyUserList.innerHTML = '';
            if (users.length === 0) {
                const emptyMessage = document.createElement('div');
                emptyMessage.textContent = '(no users found)';
                emptyMessage.className = 'settings-note';
                this.plexLoginOnlyUserList.appendChild(emptyMessage);
                return;
            }

            const savedId = window.localStorage.getItem('plexSelectedUserId') || '';

            users.forEach((user: any) => {
                const id = String(user.client_id ?? user.id ?? user.username ?? user.title ?? '');
                const label = String(user.username || user.title || id);
                const isOwner = Boolean(user.is_owner);
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'save-button plex-login-only-user-button';
                button.style.width = '100%';
                button.style.textAlign = 'left';
                button.textContent = label;
                button.dataset.userId = id;
                button.dataset.userIsOwner = String(isOwner);

                if (savedId && id === savedId) {
                    button.classList.add('active');
                }

                button.addEventListener('click', async () => {
                    window.localStorage.setItem('plexSelectedUserId', id);
                    window.localStorage.setItem('plexSelectedUserName', label);
                    window.localStorage.setItem('plexSelectedUserIsOwner', String(isOwner));
                    this.isPlexSelectedUserOwner = isOwner;
                    if (this.userButtonText) {
                        this.userButtonText.textContent = label;
                    }
                    await this.updateSidebarPlaylists();
                    await this.loadPlexPlaylists();
                    this.updateUserTypeAccess();
                    await this.updatePlexLoginOnlyState();
                    void this.loadFreshFindsAutoDownload();
                    void this.loadFreshFindsRetention();
                });
                this.plexLoginOnlyUserList.appendChild(button);
            });

            if (!savedId && defaultToOwner && users.length > 0) {
                const owner = users.find((u: any) => u.is_owner);
                if (owner) {
                    const ownerId = String(owner.client_id ?? owner.id ?? owner.username ?? owner.title ?? '');
                    const ownerName = String(owner.username || owner.title || ownerId);
                    if (ownerId) {
                        window.localStorage.setItem('plexSelectedUserId', ownerId);
                        window.localStorage.setItem('plexSelectedUserName', ownerName);
                        window.localStorage.setItem('plexSelectedUserIsOwner', 'true');
                        this.isPlexSelectedUserOwner = true;
                        this.updateUserTypeAccess();
                        await this.updatePlexLoginOnlyState();
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to load Plex users:', error);
        }
    }

    private updatePlexPlaylistContainerVisibility(show: boolean): void {
        // Plex playlist container has been removed; no-op.
    }

    private updateUserTypeAccess(): void {
        const isOwner = this.isPlexSelectedUserOwner || window.localStorage.getItem('plexSelectedUserIsOwner') === 'true';
        this.isPlexSelectedUserOwner = isOwner;

        const hidePages = ['mirrors', 'matches', 'jobs'];
        hidePages.forEach(page => {
            const navItem = document.querySelector(`.nav-item[data-page="${page}"]`) as HTMLElement | null;
            if (navItem) {
                navItem.style.display = isOwner ? '' : 'none';
            }
        });

        const settingsSections = document.querySelectorAll('#settingsPage .settings-section');
        settingsSections.forEach(section => {
            const sectionEl = section as HTMLElement;
            if (sectionEl.id === 'integrationsSettings') {
                // Always show integrations section — it contains per-user integration groups
                sectionEl.style.display = '';
            } else {
                sectionEl.style.display = isOwner ? '' : 'none';
            }
        });

        // Within integrations, hide Plex settings from non-owners
        const plexSettingsGroup = document.querySelector('#integrationsSettings #plexSettings') as HTMLElement | null;
        if (plexSettingsGroup) {
            plexSettingsGroup.style.display = isOwner ? '' : 'none';
        }

        if (!isOwner && hidePages.includes(this.currentPage)) {
            this.switchPage('explore', false);
        }
    }

    private movePlexPlaylistContainerBeneathDownloadAll(): void {
        // Plex playlist container has been removed; no-op.
    }

    private restorePlexPlaylistContainerToHome(): void {
        // Plex playlist container has been removed; no-op.
    }

    private populatePlexPlaylistOptions(playlists: (string | { name: string, ratingKey?: string })[], showEmptyPlaceholder: boolean = true): void {
        const playlistNameInput = this.plexPlaylistNameInput;
        const playlistOptions = this.plexPlaylistOptions;
        if (!playlistNameInput || !playlistOptions) {
            return;
        }

        const currentInputValue = playlistNameInput.value;
        const currentMode = playlistNameInput.style.display === 'none' ? 'existing' : 'new';
        playlistOptions.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'No Playlist';
        playlistOptions.appendChild(defaultOption);

        if (playlists.length === 0 && showEmptyPlaceholder) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '(no existing playlists found)';
            emptyOption.disabled = true;
            playlistOptions.appendChild(emptyOption);
        }

        playlists.forEach((playlist) => {
            const playlistName = typeof playlist === 'string' ? playlist : playlist.name;
            const option = document.createElement('option');
            option.value = playlistName;
            option.textContent = playlistName;
            playlistOptions.appendChild(option);
        });

        const newOption = document.createElement('option');
        newOption.value = App.NEW_PLEX_PLAYLIST_OPTION;
        newOption.textContent = 'New playlist...';
        playlistOptions.appendChild(newOption);

        playlistNameInput.value = currentInputValue;

        if (currentMode === 'new') {
            this.setPlexPlaylistMode('new');
            playlistOptions.value = App.NEW_PLEX_PLAYLIST_OPTION;
            return;
        }

        const hasMatchingExisting = playlists.includes(currentInputValue);
        playlistOptions.value = hasMatchingExisting ? currentInputValue : '';
        this.setPlexPlaylistMode('existing');
    }

    private setPlexPlaylistMode(mode: 'existing' | 'new'): void {
        if (!this.plexPlaylistOptions || !this.plexPlaylistNameInput || !this.plexPlaylistBackButton) {
            return;
        }

        if (mode === 'new') {
            this.plexPlaylistOptions.style.display = 'none';
            this.plexPlaylistNameInput.style.display = 'block';
            this.plexPlaylistBackButton.style.display = 'inline-flex';
            return;
        }

        this.plexPlaylistOptions.style.display = 'block';
        this.plexPlaylistNameInput.style.display = 'none';
        this.plexPlaylistBackButton.style.display = 'none';
    }

    private getSelectedPlexUserId(): string | null {
        const stored = window.localStorage.getItem('plexSelectedUserId');
        if (stored && stored.trim()) {
            return stored.trim();
        }
        return null;
    }

    private async loadPlexPlaylists(): Promise<void> {
        if (!this.isPlexConfigured) {
            this.populatePlexPlaylistOptions([]);
            return;
        }

        const userId = this.getSelectedPlexUserId();
        const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';

        try {
            const response = await fetch(`/api/plex/playlists${query}`, { cache: 'no-store' });
            if (!response.ok) {
                this.populatePlexPlaylistOptions([], false);
                return;
            }

            const data = await response.json();
            const playlists = Array.isArray(data.playlists) ? data.playlists : [];
            this.populatePlexPlaylistOptions(playlists);
        } catch (error) {
            console.warn('Failed to load Plex playlists.', error);
            this.populatePlexPlaylistOptions([], false);
        }
    }

    private async updateEndpointStatus(): Promise<void> {
        try {
            const response = await fetch('/api/endpoints/status');
            if (!response.ok) {
                throw new Error('Failed to fetch status');
            }

            const data: EndpointStatus = await response.json();
            this.displayEndpointStatus(data);

            const hasQobuzMirrors = data.endpoints.some(e => e.mirrorType === 'qobuz');
            if (this.downloadSourceQobuzInput) {
                this.downloadSourceQobuzInput.disabled = !hasQobuzMirrors;
                this.downloadSourceQobuzInput.title = hasQobuzMirrors ? '' : 'No online Qobuz mirrors found';
                const qobuzLabel = this.downloadSourceQobuzInput.closest('label');
                if (qobuzLabel) {
                    qobuzLabel.classList.toggle('disabled', !hasQobuzMirrors);
                    qobuzLabel.title = hasQobuzMirrors ? '' : 'No online Qobuz mirrors found';
                }
                if (!hasQobuzMirrors && this.downloadSourceQobuzInput.checked) {
                    this.downloadSourceTidalInput.checked = true;
                    this.downloadSourceQobuzInput.checked = false;
                    this.updateSettingsFromForm();
                }
            }
        } catch (error) {
            console.error('Error fetching endpoint status:', error);
        }
    }

    private displayEndpointStatus(data: EndpointStatus): void {
        // Split endpoints by type
        const tidalEndpoints = data.endpoints.filter(e => e.mirrorType !== 'qobuz');
        const qobuzEndpoints = data.endpoints.filter(e => e.mirrorType === 'qobuz');

        // Compute separate stats
        const tidalOnline = tidalEndpoints.filter(e => e.online).length;
        const qobuzOnline = qobuzEndpoints.filter(e => e.online).length;

        // Update per-type stat elements
        const tidalOnlineCount = document.getElementById('tidalOnlineCount');
        const tidalTotalCount = document.getElementById('tidalTotalCount');
        const qobuzOnlineCount = document.getElementById('qobuzOnlineCount');
        const qobuzTotalCount = document.getElementById('qobuzTotalCount');

        if (tidalOnlineCount) tidalOnlineCount.textContent = tidalOnline.toString();
        if (tidalTotalCount) tidalTotalCount.textContent = tidalEndpoints.length.toString();
        if (qobuzOnlineCount) qobuzOnlineCount.textContent = qobuzOnline.toString();
        if (qobuzTotalCount) qobuzTotalCount.textContent = qobuzEndpoints.length.toString();

        // Legacy: update old stat elements if they still exist
        const totalCount = document.getElementById('totalCount');
        const onlineCount = document.getElementById('onlineCount');
        const offlineCount = document.getElementById('offlineCount');

        if (totalCount) totalCount.textContent = data.summary.total.toString();
        if (onlineCount) onlineCount.textContent = data.summary.online.toString();
        if (offlineCount) offlineCount.textContent = data.summary.offline.toString();

        const rateLimit = data.mirrorRateLimitStatus;
        const safeRateLabel = rateLimit
            ? `${rateLimit.safe_rpm.toFixed(2)} RPM (${rateLimit.safe_rps.toFixed(2)} RPS)`
            : 'Unknown';
        const rateLimitState = !rateLimit
            ? 'Unknown'
            : rateLimit.safe_interval >= 30 || rateLimit.error_rate_429 > 0.05
                ? 'Backoff active'
                : rateLimit.safe_interval > 0.5 || rateLimit.error_rate_429 > 0
                    ? 'Recovering'
                    : 'Normal';
        const rateLimit429Percent = rateLimit
            ? `${(rateLimit.error_rate_429 * 100).toFixed(2)}%`
            : 'Unknown';
        const currentIntervalLabel = rateLimit
            ? `${rateLimit.safe_interval.toFixed(2)}s`
            : 'Unknown';

        // Update endpoint list
        if (!this.flyoutContent) {
            console.warn('Flyout content element not found');
            return;
        }

        const rateLimitSummary = rateLimit
            ? `
                <div class="endpoint-item">
                    <div class="endpoint-header">
                        <span class="endpoint-name">Mirror Rate Limiter</span>
                        <div class="endpoint-status ${rateLimitState === 'Normal' ? 'online' : 'offline'}">
                            <span class="status-indicator ${rateLimitState === 'Normal' ? 'online' : 'offline'}"></span>
                            ${rateLimitState}
                        </div>
                    </div>
                    <div class="endpoint-details">
                        <div class="endpoint-detail">
                            <span class="detail-label">Current Interval</span>
                            <span class="detail-value">${currentIntervalLabel}</span>
                        </div>
                        <div class="endpoint-detail">
                            <span class="detail-label">Current Safe Rate</span>
                            <span class="detail-value">${safeRateLabel}</span>
                        </div>
                        <div class="endpoint-detail">
                            <span class="detail-label">429 Rate</span>
                            <span class="detail-value">${rateLimit429Percent}</span>
                        </div>
                        <div class="endpoint-detail">
                            <span class="detail-label">Sample Size</span>
                            <span class="detail-value">${rateLimit.sample_size}</span>
                        </div>
                    </div>
                </div>
            `
            : '';

        const renderEndpointItem = (endpoint: Endpoint): string => {
            const url = atob(endpoint.encodedUrl);
            const statusClass = endpoint.online ? 'online' : 'offline';
            const statusText = endpoint.online ? 'Online' : 'Offline';
            const responseTime = endpoint.responseTime
                ? `${endpoint.responseTime.toFixed(0)}ms`
                : 'N/A';
            const lastChecked = endpoint.lastChecked
                ? new Date(endpoint.lastChecked).toLocaleTimeString(undefined, { timeZone: this.timezone })
                : 'Never';
            const disabledClass = endpoint.enabled ? '' : ' disabled';

            return `
                <div class="endpoint-item${disabledClass}">
                    <div class="endpoint-header">
                        <span class="endpoint-name">${this.escapeHtml(endpoint.name)}</span>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <div class="endpoint-status ${statusClass}">
                                <span class="status-indicator ${statusClass}"></span>
                                ${statusText}
                            </div>
                            <label class="endpoint-toggle" title="${endpoint.enabled ? 'Disable mirror' : 'Enable mirror'}">
                                <input type="checkbox" data-endpoint-toggle="${this.escapeHtml(endpoint.name)}" ${endpoint.enabled ? 'checked' : ''}>
                                <span class="endpoint-toggle-slider"></span>
                            </label>
                            <button type="button" class="endpoint-remove-btn" data-endpoint-name="${this.escapeHtml(endpoint.name)}" title="Remove mirror">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                            </button>
                        </div>
                    </div>
                    <div class="endpoint-url">${this.escapeHtml(url)}</div>
                    <div class="endpoint-details">
                        <div class="endpoint-detail">
                            <span class="detail-label">Response Time</span>
                            <span class="detail-value response-time">${responseTime}</span>
                        </div>
                        <div class="endpoint-detail">
                            <span class="detail-label">Last Checked</span>
                            <span class="detail-value">${lastChecked}</span>
                        </div>
                        <div class="endpoint-detail">
                            <span class="detail-label">Safe Rate</span>
                            <span class="detail-value">${safeRateLabel}</span>
                        </div>
                    </div>
                </div>
            `;
        };

        const renderMirrorGroup = (label: string, endpoints: Endpoint[], emptyMessage: string): string => {
            if (endpoints.length === 0) {
                return `
                    <div class="mirror-group">
                        <div class="mirror-group-header">${this.escapeHtml(label)}</div>
                        <div class="mirror-group-empty">${this.escapeHtml(emptyMessage)}</div>
                    </div>
                `;
            }
            const items = endpoints.map(renderEndpointItem).join('');
            return `
                <div class="mirror-group">
                    <div class="mirror-group-header">${this.escapeHtml(label)}</div>
                    <div class="mirror-group-list">${items}</div>
                </div>
            `;
        };

        const tidalGroup = renderMirrorGroup('Tidal Mirrors', tidalEndpoints, 'No Tidal mirrors configured');
        const qobuzGroup = renderMirrorGroup('Qobuz Mirrors', qobuzEndpoints, 'No Qobuz mirrors configured');

        this.flyoutContent.innerHTML = `${rateLimitSummary}${tidalGroup}${qobuzGroup}`;
    }

    private openAddMirrorModal(): void {
        const overlay = document.createElement('div');
        overlay.className = 'playlist-modal-overlay';

        const modal = document.createElement('div');
        modal.className = 'playlist-modal';

        const header = document.createElement('div');
        header.className = 'playlist-modal-header';

        const title = document.createElement('h3');
        title.textContent = 'Add Mirror';
        header.appendChild(title);

        const closeBtn = document.createElement('button');
        closeBtn.className = 'playlist-modal-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(overlay);
        });
        header.appendChild(closeBtn);

        const content = document.createElement('div');
        content.className = 'playlist-modal-content';

        const mirrorTypeGroup = document.createElement('div');
        mirrorTypeGroup.className = 'settings-group';
        const mirrorTypeLabel = document.createElement('label');
        mirrorTypeLabel.className = 'settings-label';
        mirrorTypeLabel.textContent = 'Mirror Type';
        const mirrorTypeToggle = document.createElement('div');
        mirrorTypeToggle.className = 'format-toggle';
        mirrorTypeToggle.setAttribute('role', 'radiogroup');
        mirrorTypeToggle.setAttribute('aria-label', 'Mirror type');

        const tidalLabel = document.createElement('label');
        tidalLabel.className = 'toggle-option';
        const tidalRadio = document.createElement('input');
        tidalRadio.type = 'radio';
        tidalRadio.name = 'mirrorType';
        tidalRadio.value = 'tidal';
        tidalRadio.id = 'mirrorTypeTidal';
        tidalRadio.checked = true;
        const tidalSpan = document.createElement('span');
        tidalSpan.textContent = 'Tidal';
        tidalLabel.appendChild(tidalRadio);
        tidalLabel.appendChild(tidalSpan);

        const qobuzLabel = document.createElement('label');
        qobuzLabel.className = 'toggle-option';
        const qobuzRadio = document.createElement('input');
        qobuzRadio.type = 'radio';
        qobuzRadio.name = 'mirrorType';
        qobuzRadio.value = 'qobuz';
        qobuzRadio.id = 'mirrorTypeQobuz';
        const qobuzSpan = document.createElement('span');
        qobuzSpan.textContent = 'Qobuz';
        qobuzLabel.appendChild(qobuzRadio);
        qobuzLabel.appendChild(qobuzSpan);

        mirrorTypeToggle.appendChild(tidalLabel);
        mirrorTypeToggle.appendChild(qobuzLabel);
        mirrorTypeGroup.appendChild(mirrorTypeLabel);
        mirrorTypeGroup.appendChild(mirrorTypeToggle);

        const urlGroup = document.createElement('div');
        urlGroup.className = 'settings-group';
        const urlLabel = document.createElement('label');
        urlLabel.className = 'settings-label';
        urlLabel.textContent = 'Mirror URL';
        const urlInput = document.createElement('input');
        urlInput.type = 'text';
        urlInput.className = 'settings-input';
        urlInput.placeholder = 'http://mirror.example.com:8000';
        urlGroup.appendChild(urlLabel);
        urlGroup.appendChild(urlInput);

        content.appendChild(mirrorTypeGroup);
        content.appendChild(urlGroup);

        const footer = document.createElement('div');
        footer.className = 'playlist-modal-footer';

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'playlist-modal-cancel';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(overlay);
        });

        const submitBtn = document.createElement('button');
        submitBtn.className = 'save-button';
        submitBtn.textContent = 'Add';
        submitBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                return;
            }
            const mirrorType = tidalRadio.checked ? 'tidal' : 'qobuz';
            submitBtn.disabled = true;
            submitBtn.textContent = 'Adding...';
            try {
                const resp = await fetch('/api/endpoints', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, mirrorType }),
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    throw new Error(err.error || 'Failed to add mirror');
                }
                document.body.removeChild(overlay);
                void this.updateEndpointStatus();
            } catch (e) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Add';
                alert(e instanceof Error ? e.message : 'Failed to add mirror');
            }
        });

        footer.appendChild(cancelBtn);
        footer.appendChild(submitBtn);

        modal.appendChild(header);
        modal.appendChild(content);
        modal.appendChild(footer);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
            }
        });

        urlInput.focus();
    }

    private async handleFlyoutContentClick(e: MouseEvent): Promise<void> {
        const target = e.target as HTMLElement;

        const toggleInput = target.closest('[data-endpoint-toggle]') as HTMLInputElement | null;
        if (toggleInput) {
            const name = toggleInput.getAttribute('data-endpoint-toggle');
            if (!name) {
                return;
            }
            const prevState = toggleInput.checked;
            toggleInput.disabled = true;
            try {
                const resp = await fetch(`/api/endpoints/${encodeURIComponent(name)}/toggle`, {
                    method: 'POST',
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    throw new Error(err.error || 'Failed to toggle mirror');
                }
                void this.updateEndpointStatus();
            } catch (err) {
                toggleInput.checked = prevState;
                toggleInput.disabled = false;
                alert(err instanceof Error ? err.message : 'Failed to toggle mirror');
            }
            return;
        }

        const removeBtn = target.closest('.endpoint-remove-btn') as HTMLButtonElement | null;
        if (!removeBtn) {
            return;
        }

        const name = removeBtn.getAttribute('data-endpoint-name');
        if (!name) {
            return;
        }

        if (!window.confirm(`Remove mirror "${name}"?`)) {
            return;
        }

        removeBtn.disabled = true;
        try {
            const resp = await fetch(`/api/endpoints/${encodeURIComponent(name)}`, {
                method: 'DELETE',
            });
            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error || 'Failed to remove mirror');
            }
            void this.updateEndpointStatus();
        } catch (err) {
            removeBtn.disabled = false;
            alert(err instanceof Error ? err.message : 'Failed to remove mirror');
        }
    }

    private updateSearchPlaceholder(): void {
        const searchType = this.searchTypeSelect.value;
        if (searchType === 'lastfm') {
            this.searchInput.placeholder = 'Enter Last.fm playlist URL...';
        } else if (searchType === 'youtube_music') {
            this.searchInput.placeholder = 'Enter YouTube Music playlist URL...';
        } else if (searchType === 'listenbrainz') {
            this.searchInput.placeholder = 'Enter ListenBrainz username...';
        } else if (searchType === 'a') {
            this.searchInput.placeholder = 'Search for artists...';
        } else if (searchType === 'al') {
            this.searchInput.placeholder = 'Search for albums...';
        } else if (searchType === 'p') {
            this.searchInput.placeholder = 'Search for playlists...';
        } else if (searchType === 'trackid') {
            this.searchInput.placeholder = 'Enter numeric Track ID...';
        } else {
            this.searchInput.placeholder = 'Search for tracks...';
        }
    }

    private async handleSearch(updateHistory: boolean = true): Promise<void> {
        const searchType = this.searchTypeSelect.value;
        const query = this.searchInput.value.trim();

        this.switchPage('explore', false);

        if (searchType === 'listenbrainz') {
            // Handle ListenBrainz playlists without requiring query
            await this.handleListenbrainzPlaylists(undefined, updateHistory);
            return;
        }

        if (!query) {
            this.displayMessage('Please enter a search query');
            return;
        }

        if (searchType === 'trackid' && !/^[0-9]+$/.test(query)) {
            this.displayMessage('Track ID must be a numeric value');
            return;
        }

        if (searchType === 'lastfm') {
            // Handle Last.fm playlist with progressive search
            await this.handleLastfmPlaylist(query, updateHistory);
            return;
        }

        if (searchType === 'youtube_music') {
            // Handle YouTube Music playlist with progressive search
            await this.handleYoutubeMusicPlaylist(query, updateHistory);
            return;
        }

        if (updateHistory) {
            this.pushHistoryRoute({
                view: 'search',
                searchType,
                query
            });
        }

        this.currentExploreRoute = { view: 'search', searchType, query };
        this.exploreSearchRoute = { ...this.currentExploreRoute };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

        this.displayMessage('Searching...');

        try {
            const response = await this.fetchWithRetry(`/api/hifi/search?${searchType}=${encodeURIComponent(query)}`);

            if (!response.ok) {
                throw new Error('Search failed');
            }

            const data: SearchResult = await response.json();
            this.displayResults(data, query, searchType);
        } catch (error) {
            this.displayMessage('Error performing search. Please try again.');
            console.error('Search error:', error);
        }
    }

    private async handleLastfmPlaylist(playlistUrl: string, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'lastfm_playlist', playlistUrl };
        this.exploreLastfmPlaylistName = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'lastfm_playlist', playlistUrl });
        }
        this.displayMessage('Scraping Last.fm playlist...');

        try {
            // First, scrape the playlist to get track list
            const scrapeResponse = await fetch('/api/lastfm/playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ playlistUrl }),
                signal: this.pendingRequestController?.signal
            });

            if (!scrapeResponse.ok) {
                const errorData = await scrapeResponse.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to scrape playlist');
            }

            const scrapeData = await scrapeResponse.json();
            const playlistName = scrapeData.playlistName || 'Last.fm Playlist';
            this.exploreLastfmPlaylistName = playlistName;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            const tracks = scrapeData.tracks || [];
            const totalTracks = tracks.length;

            if (totalTracks === 0) {
                this.displayMessage('No tracks found in playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>Last.fm Playlist - "${this.escapeHtml(playlistName)}"</h2>
                    </div>
                </div>
                <div class="results-list">
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            ${this.formatTrackGridHeader(false, true, true)}
                            <div id="lastfmResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const { matched: matchedTracks, notFound: notFoundTracks } = await this.renderProgressiveTrackGrid(tracks, {
                viewMode: 'multi-album',
                showTrackNumber: false,
                showAlbumColumn: true,
                showArtwork: true,
                resultsContainerId: 'lastfmResultsList',
                playlistName,
            });

            this.createAddAllButtons();

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }

        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to process Last.fm playlist'}`);
            console.error('Last.fm playlist error:', error);
        }
    }

    private async handleYoutubeMusicPlaylist(playlistUrl: string, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'youtube_music_playlist', playlistUrl };
        this.exploreYoutubePlaylistName = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'youtube_music_playlist', playlistUrl });
        }
        this.displayMessage('Loading YouTube Music playlist...');

        try {
            const scrapeResponse = await fetch('/api/youtube_music/playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ playlistUrl }),
                signal: this.pendingRequestController?.signal
            });

            if (!scrapeResponse.ok) {
                const errorData = await scrapeResponse.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to load playlist');
            }

            const scrapeData = await scrapeResponse.json();
            const playlistName = scrapeData.playlistName || 'YouTube Music Playlist';
            this.exploreYoutubePlaylistName = playlistName;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            const tracks = scrapeData.tracks || [];
            const totalTracks = tracks.length;

            if (totalTracks === 0) {
                this.displayMessage('No tracks found in playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>YouTube Music Playlist - "${this.escapeHtml(playlistName)}"</h2>
                    </div>
                </div>
                <div class="results-list">
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            ${this.formatTrackGridHeader(false, true, true)}
                            <div id="lastfmResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const { matched: matchedTracks, notFound: notFoundTracks } = await this.renderProgressiveTrackGrid(tracks, {
                viewMode: 'multi-album',
                showTrackNumber: false,
                showAlbumColumn: true,
                showArtwork: true,
                resultsContainerId: 'lastfmResultsList',
                playlistName,
            });

            this.createAddAllButtons();

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }

        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to process YouTube Music playlist'}`);
            console.error('YouTube Music playlist error:', error);
        }
    }

    private async handleListenbrainzPlaylists(usernameOverride?: string, updateHistory: boolean = true, type?: string): Promise<void> {
        let username = (usernameOverride ?? this.searchInput.value).trim();

        if (!username) {
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                try {
                    const response = await fetch(`/api/listenbrainz/config?user_id=${encodeURIComponent(userId)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.username) {
                            username = data.username;
                        }
                    }
                } catch (e) {
                    console.error('Failed to fetch listenbrainz config for username', e);
                }
            }
        }

        if (!username) {
            this.displayMessage('Please enter ListenBrainz username or configure it in Settings');
            return;
        }

        if (updateHistory) {
            this.pushHistoryRoute({ view: 'listenbrainz_playlists', username, playlistType: type });
        }

        this.currentExploreRoute = { view: 'listenbrainz_playlists', username, playlistType: type };
        this.listenbrainzCurrentUsername = username;
        this.listenbrainzCurrentPlaylist = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

        this.displayMessage('Loading ListenBrainz playlists...');

        try {
            const userId = this.getSelectedPlexUserId();
            const userIdQuery = userId ? `&user_id=${encodeURIComponent(userId)}` : '';
            const typeQuery = type ? `&type=${encodeURIComponent(type)}` : '';
            const response = await fetch(`/api/listenbrainz/playlists?username=${encodeURIComponent(username)}${userIdQuery}${typeQuery}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to fetch playlists' }));
                throw new Error(errorData.error || 'Failed to fetch ListenBrainz playlists');
            }

            const data = await response.json();
            const playlistsData = data.playlists || [];

            if (playlistsData.length === 0) {
                this.displayMessage('No recommended playlists found on ListenBrainz');
                return;
            }

            // Extract playlist objects from the response structure
            const playlists = playlistsData
                .map((item: any) => item.playlist)
                .filter((playlist: any) => playlist && playlist.title);
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

            let displayTitle = 'ListenBrainz Playlists';
            if (type === 'user') displayTitle = 'User Playlists';
            if (type === 'collaborator') displayTitle = 'Collaborator Playlists';
            if (type === 'createdfor') displayTitle = 'Recommendation Playlists';

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <h2>${displayTitle} (${playlists.length})</h2>
                </div>
                <div class="results-list">
                    ${playlists.map((playlist: any) => this.formatPlaylistCard(playlist)).join('')}
                </div>
            `;
        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to load ListenBrainz playlists'}`);
            console.error('ListenBrainz playlists error:', error);
        }
    }

    private formatPlaylistCard(playlist: any): string {
        const title = this.escapeHtml(playlist.title || 'Unknown');
        const creator = this.escapeHtml(playlist.creator || 'Unknown');
        const annotation = this.escapeHtml(playlist.annotation || '');

        // Extract public status from extension
        const isPublic = playlist.extension?.['https://musicbrainz.org/doc/jspf#playlist']?.public || false;

        // Extract identifier (which is the full URL)
        const playlistId = playlist.identifier ? playlist.identifier : '';

        return `
            <div class="playlist-card" data-playlist-id="${this.escapeHtml(playlistId)}">
                <div class="playlist-info">
                    <h3 class="playlist-title">${title}</h3>
                    <p class="playlist-creator">by ${creator}</p>
                    ${annotation ? `<p class="playlist-description">${annotation}</p>` : ''}
                    ${isPublic ? '<span class="playlist-badge">Public</span>' : ''}
                </div>
            </div>
        `;
    }

    private async fetchListenbrainzPlaylistTracks(playlistId: string, updateHistory: boolean = true, usernameOverride?: string): Promise<void> {
        this.downloadAllScope = 'loose';
        const username = (usernameOverride || this.listenbrainzCurrentUsername || '').trim();
        if (username) {
            this.listenbrainzCurrentUsername = username;
        }
        this.currentExploreRoute = { view: 'listenbrainz_playlist_tracks', playlistId, username: this.listenbrainzCurrentUsername || undefined };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'listenbrainz_playlist_tracks', playlistId, username: this.listenbrainzCurrentUsername || undefined });
        }
        this.stopPlayback();
        this.displayMessage('Loading ListenBrainz playlist tracks...');

        try {
            // Extract MBID from identifier URL
            // The identifier is like "https://listenbrainz.org/playlist/048c5c53-f62d-4b47-abcc-8c6992f69445"
            const mbidMatch = playlistId.match(/playlist\/([a-f0-9-]+)$/i);
            if (!mbidMatch || !mbidMatch[1]) {
                throw new Error('Invalid playlist identifier format');
            }

            const playlistMbid = mbidMatch[1];
            const userId = this.getSelectedPlexUserId();
            const userIdQuery = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
            const response = await fetch(`/api/listenbrainz/playlist/${encodeURIComponent(playlistMbid)}${userIdQuery}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to fetch playlist' }));
                throw new Error(errorData.error || 'Failed to fetch ListenBrainz playlist');
            }

            const data = await response.json();
            const playlist = data.playlist;

            if (!playlist) {
                this.displayMessage('No playlist data found');
                return;
            }

            // Extract tracks from the playlist
            const tracks = playlist.track || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            // Get playlist info for display
            const playlistTitle = playlist.title || 'Untitled Playlist';
            const playlistCreator = playlist.creator || 'Unknown';
            this.listenbrainzCurrentPlaylist = { id: playlistId, title: playlistTitle };
            this.explorePlaylistTitle = playlistTitle;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

            // Set up initial display with progress bar for searching
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(playlistTitle)}</h2>
                        <p class="playlist-creator-display">by ${this.escapeHtml(playlistCreator)}</p>
                    </div>
                </div>
                <div class="results-list">
                    <div id="lbMatchProgress" style="padding: 12px 16px; font-size: 14px; color: #888;"></div>
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            ${this.formatTrackGridHeader(false, true, true)}
                            <div id="listenbrainzResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const resultsList = document.getElementById('listenbrainzResultsList');
            const progressEl = document.getElementById('lbMatchProgress');
            let foundCount = 0;
            const matchedTracks: Track[] = [];
            const notFoundTracks: Array<{ artist: string; name: string }> = [];

            // Search for each track progressively
            for (let i = 0; i < tracks.length; i++) {
                const lbTrack = tracks[i];
                const artists = lbTrack.creator || 'Unknown';

                if (progressEl) {
                    progressEl.textContent = `Processing track ${i + 1} of ${tracks.length}`;
                }

                try {
                    const matchResponse = await fetch('/api/listenbrainz/match', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: lbTrack.title,
                            artist: artists,
                            album: lbTrack.album || '',
                            identifier: lbTrack.identifier || ''
                        }),
                        signal: this.pendingRequestController?.signal
                    });

                    if (matchResponse.ok) {
                        const matchData = await matchResponse.json();

                        if (matchData.match) {
                            const trackRow = this.formatTrackGridRow(this.normalizeTrack(matchData.match as Track), {
                                viewMode: 'multi-album',
                                showTrackNumber: false,
                                showAlbumColumn: true,
                                showArtwork: true,
                            });
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(matchData.match as Track);
                            foundCount++;
                        } else {
                            notFoundTracks.push({
                                artist: artists,
                                name: lbTrack.title || 'Unknown'
                            });
                        }
                    } else {
                        notFoundTracks.push({
                            artist: artists,
                            name: lbTrack.title || 'Unknown'
                        });
                    }
                } catch (error) {
                    console.error(`Failed to match ${lbTrack.title} by ${artists}:`, error);
                    notFoundTracks.push({
                        artist: artists,
                        name: lbTrack.title || 'Unknown'
                    });
                }

            }

            if (progressEl) {
                progressEl.textContent = `${foundCount} of ${tracks.length} tracks found`;
            }

            this.createAddAllButtons();

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }
        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to load ListenBrainz playlist'}`);
            console.error('ListenBrainz playlist error:', error);
        }
    }

    private async fetchYtmPlaylistTracks(playlistId: string, playlistTitle: string, updateHistory: boolean = true): Promise<void> {
        this.currentExploreRoute = { view: 'youtube_music_playlist', playlistId, playlistTitle };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'youtube_music_playlist', playlistId, playlistTitle });
        }
        this.stopPlayback();
        this.displayMessage('Loading YouTube Music playlist tracks...');

        try {
            const userId = this.getSelectedPlexUserId();
            const userIdQuery = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
            const response = await fetch(`/api/youtube_music/playlist/${encodeURIComponent(playlistId)}${userIdQuery}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to fetch playlist' }));
                throw new Error(errorData.error || 'Failed to fetch YouTube Music playlist');
            }

            const data = await response.json();
            const tracks = data.tracks || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            const resolvedTitle = data.title || playlistTitle;
            const trackCount = data.trackCount || tracks.length;

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(resolvedTitle)}</h2>
                        <p class="playlist-creator-display">${trackCount} tracks</p>
                    </div>
                </div>
                <div class="results-list">
                    <div id="ytmMatchProgress" style="padding: 12px 16px; font-size: 14px; color: #888;"></div>
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            ${this.formatTrackGridHeader(false, true, true)}
                            <div id="ytmResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const resultsList = document.getElementById('ytmResultsList');
            const progressEl = document.getElementById('ytmMatchProgress');
            let foundCount = 0;
            const matchedTracks: Track[] = [];

            for (let i = 0; i < tracks.length; i++) {
                const ytmTrack = tracks[i];
                const artists = (ytmTrack.artists || []).map((a: any) => a.name).filter(Boolean).join(', ') || 'Unknown';
                const albumName = (ytmTrack.album && ytmTrack.album.name) || '';

                if (progressEl) {
                    progressEl.textContent = `Processing track ${i + 1} of ${tracks.length}`;
                }

                try {
                    const matchResponse = await fetch('/api/youtube_music/match', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: ytmTrack.title,
                            artist: artists,
                            album: albumName
                        }),
                        signal: this.pendingRequestController?.signal
                    });

                    if (matchResponse.ok) {
                        const matchData = await matchResponse.json();

                        if (matchData.match) {
                            const trackRow = this.formatTrackGridRow(this.normalizeTrack(matchData.match as Track), {
                                viewMode: 'multi-album',
                                showTrackNumber: false,
                                showAlbumColumn: true,
                                showArtwork: true,
                            });
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(matchData.match as Track);
                            foundCount++;
                        }
                    }
                } catch (error) {
                    console.error(`Failed to match ${ytmTrack.title} by ${artists}:`, error);
                }
            }

            if (progressEl) {
                progressEl.textContent = `${foundCount} of ${tracks.length} tracks found`;
            }

            this.createAddAllButtons();

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }
        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to load YouTube Music playlist'}`);
            console.error('YouTube Music playlist error:', error);
        }
    }

    private convertListenbrainzTrackToTrack(lbTrack: any): Track | null {
        // ListenBrainz track format from JSPF
        // Example: { identifier: "https://musicbrainz.org/track/...", title: "...", creator: "...", duration: ... }
        if (!lbTrack.title) {
            return null;
        }

        return {
            id: Math.random() * 1000000, // Generate a temporary ID since ListenBrainz doesn't provide numeric IDs
            title: lbTrack.title || 'Unknown',
            duration: lbTrack.duration ? Math.floor(lbTrack.duration / 1000) : undefined,
            artists: lbTrack.creator
                ? [{ id: 0, name: lbTrack.creator }]
                : [],
            artist: lbTrack.creator
                ? { id: 0, name: lbTrack.creator }
                : undefined,
            album: undefined,
            quality: undefined,
            audioQuality: undefined,
            cover: undefined,
            trackNumber: undefined
        };
    }

    private displayResults(data: SearchResult, query: string, searchType: string): void {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'search', searchType, query };
        this.exploreSearchRoute = { ...this.currentExploreRoute };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(true);
        if (data.error) {
            this.displayMessage(`Error: ${data.error}${data.details ? ' - ' + data.details : ''}`);
            return;
        }

        // Extract items based on search type
        let items: any[] = [];
        if (searchType === 'al') {
            items = data.data?.albums?.items || [];
        } else if (searchType === 'a') {
            items = data.data?.artists?.items || [];
        } else if (searchType === 'p') {
            items = data.data?.playlists?.items || data.data?.items || [];
        } else {
            items = data.data?.items || [];
        }

        if (items.length === 0) {
            this.displayMessage(`No results found for "${query}"${data.proxied_via ? ' (via ' + data.proxied_via + ')' : ''}`);
            return;
        }

        // Display results with proxy info
        const searchTypeName = searchType === 's' ? 'Tracks' :
            searchType === 'a' ? 'Artists' :
                searchType === 'al' ? 'Albums' :
                    searchType === 'p' ? 'Playlists' :
                        searchType === 'trackid' ? 'Track ID' :
                            'Results';

        this.resultsContainer.innerHTML = `
            <div class="results-header">
                <h2>${searchTypeName} - "${this.escapeHtml(query)}"</h2>
                ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
            </div>
            ${searchType === 'al'
                ? this.renderAlbumGrid(items as AlbumSearchItem[], { viewMode: 'search-albums' })
                : searchType === 's' || searchType === 'trackid'
                    ? this.formatTracksGrid(items as Track[])
                    : `<div class="results-list${searchType === 'a' ? ' artist-results' : ''}">
                    ${items.map(item => {
                        if (searchType === 'a') return this.formatArtistCard(item as ArtistSearchItem);
                        if (searchType === 'p') return this.formatSearchPlaylistCard(item as PlaylistSearchItem);
                        return this.formatTrackCard(item as Track);
                    }).join('')}
                </div>`
            }
        `;

        if (searchType === 's' || searchType === 'trackid') {
            void this.annotateTrackCardsWithPlexStatus(items as Track[]);
        } else if (searchType === 'al') {
            void this.annotateAlbumGridsWithPlexStatus(items as AlbumSearchItem[]);
        } else if (searchType === 'a') {
            void this.annotateArtistCardsWithPlexStatus(items as ArtistSearchItem[]);
        }
    }

    private async lookupStoredMatches(trackIds: Array<number | string>, albumIds: Array<number | string>, artistIds: Array<number | string>, signal?: AbortSignal): Promise<HifiMatchLookupResponse> {
        const normalizedTrackIds = trackIds
            .map(trackId => String(trackId).trim())
            .filter(Boolean);
        const normalizedAlbumIds = albumIds
            .map(albumId => String(albumId).trim())
            .filter(Boolean);
        const normalizedArtistIds = artistIds
            .map(artistId => String(artistId).trim())
            .filter(Boolean);

        if (normalizedTrackIds.length === 0 && normalizedAlbumIds.length === 0 && normalizedArtistIds.length === 0) {
            return { tracks: [], albums: [], artists: [] };
        }

        const response = await fetch('/api/hifi/matches/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                track_ids: normalizedTrackIds,
                album_ids: normalizedAlbumIds,
                artist_ids: normalizedArtistIds
            }),
            signal
        });

        if (!response.ok) {
            throw new Error('Failed to look up stored matches');
        }

        return await response.json() as HifiMatchLookupResponse;
    }

    private isLowQualityPlexMatch(variants: PlexSongVariant[] = []): boolean {
        return Array.isArray(variants)
            && variants.length > 0
            && variants.every(variant =>
                (variant.format === 'mp3' || variant.format === 'mpeg')
                && typeof variant.bitrate === 'number'
                && variant.bitrate <= 192
            );
    }

    private createPlexMatchChip(match: { [key: string]: any; confidence?: number | null; variants?: PlexSongVariant[] }, options?: { inActions?: boolean; bulk?: boolean; incomplete?: boolean; hero?: boolean }): HTMLSpanElement {
        const chip = document.createElement('span');
        const lowQuality = this.isLowQualityPlexMatch(match.variants || []);
        const incomplete = options?.incomplete === true;

        const classNames = ['plex-existing-chip'];
        if (options?.inActions) {
            classNames.push('plex-existing-chip--in-actions');
        }
        if (options?.bulk) {
            classNames.push('plex-existing-chip--bulk');
        }
        if (lowQuality) {
            classNames.push('plex-existing-chip--low-quality');
        }
        if (options?.hero) {
            classNames.push('plex-existing-chip--hero');
        }
        if (incomplete) {
            classNames.push('plex-existing-chip--incomplete');
        }
        chip.className = classNames.join(' ');

        let label = 'In Plex';
        if (lowQuality) {
            label += ' · low quality';
        }
        chip.textContent = label;
        chip.title = this.buildStoredMatchTooltip(match.variants || [], incomplete);
        return chip;
    }

    private buildStoredMatchTooltip(variants: PlexSongVariant[] = [], incomplete: boolean = false): string {
        const heading = incomplete ? 'Exists in Plex (incomplete)' : 'Exists in Plex';

        if (!Array.isArray(variants) || variants.length === 0) {
            return heading;
        }

        const details = variants.map((variant) => {
            const bitrate = typeof variant.bitrate === 'number' && Number.isFinite(variant.bitrate)
                ? ` (${variant.bitrate} kbps)`
                : '';
            return variant.file_path
                ? `  ${variant.file_path}${bitrate}`
                : `  ${(variant.format || 'unknown').toUpperCase()}${bitrate}`;
        });

        return `${heading}\n${details.join('\n')}`;
    }

    private async annotateTrackCardsWithPlexStatus(tracks: Track[]): Promise<void> {
        if (!Array.isArray(tracks) || tracks.length === 0) {
            return;
        }

        const signal = this.pendingRequestController?.signal;
        const trackIds = tracks.map(track => track.id).filter(trackId => Number.isFinite(trackId));
        if (trackIds.length === 0) {
            return;
        }

        try {
            const lookup = await this.lookupStoredMatches(trackIds, [], [], signal);
            const trackMatches = Array.isArray(lookup.tracks) ? lookup.tracks : [];
            const matchById = new Map(trackMatches.map(match => [String(match.track_id), match]));

            const gridRows = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row')) as HTMLElement[];
            if (gridRows.length > 0) {
                await this.annotateGridRowsWithPlexStatus(gridRows, matchById);
                return;
            }

            const cards = Array.from(this.resultsContainer.querySelectorAll('.results-list .track-card')) as HTMLElement[];
            for (const card of cards) {
                const trackId = String(card.getAttribute('data-track-id') || '').trim();
                const match = matchById.get(trackId);
                if (!match || !match.exists) {
                    continue;
                }

                const metadataEl = card.querySelector('.track-metadata') as HTMLElement | null;
                if (!metadataEl || metadataEl.querySelector('.plex-existing-chip')) {
                    continue;
                }

                if (metadataEl.children.length > 0) {
                    const sep = document.createElement('span');
                    sep.className = 'plex-chip-separator';
                    sep.textContent = '•';
                    metadataEl.appendChild(sep);
                }

                metadataEl.appendChild(this.createPlexMatchChip(match));
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate Plex inventory matches.', error);
        }
    }

    private async annotateGridRowsWithPlexStatus(gridRows: HTMLElement[], matchById: Map<string, HifiTrackLookupMatch>): Promise<void> {
        const resolvedMatches: HifiTrackLookupMatch[] = [];

        for (const row of gridRows) {
            const trackId = String(row.getAttribute('data-track-id') || '').trim();
            const match = matchById.get(trackId);
            if (!match || !match.exists) {
                continue;
            }

            resolvedMatches.push(match);
            row.setAttribute('data-plex-exists', 'true');

            const actionsCell = row.querySelector('.grid-col-actions') as HTMLElement | null;
            const addLibraryBtn = actionsCell?.querySelector('.grid-add-library-btn') as HTMLElement | null;
            if (!actionsCell || !addLibraryBtn) {
                continue;
            }

            addLibraryBtn.replaceWith(this.createPlexMatchChip(match, { inActions: true }));
        }

        const allRowsInPlex = gridRows.length > 0 && resolvedMatches.length === gridRows.length;
        if (allRowsInPlex) {
            this.replaceAddAllLibraryWithPlexBadge(resolvedMatches);
        }
    }

    private async annotateAlbumGridsWithPlexStatus(albums: AlbumSearchItem[]): Promise<void> {
        if (!Array.isArray(albums) || albums.length === 0) {
            return;
        }

        const signal = this.pendingRequestController?.signal;
        const albumIds = albums.map(album => album.id).filter(albumId => Number.isFinite(albumId));
        if (albumIds.length === 0) {
            return;
        }

        try {
            const lookup = await this.lookupStoredMatches([], albumIds, [], signal);
            const albumMatches = Array.isArray(lookup.albums) ? lookup.albums : [];
            const matchById = new Map(albumMatches.map(match => [String(match.album_id), match]));
            const gridRows = Array.from(this.resultsContainer.querySelectorAll('.albums-grid-row')) as HTMLElement[];

            for (const row of gridRows) {
                const albumId = String(row.getAttribute('data-album-id') || '').trim();
                const match = matchById.get(albumId);
                if (!match || !match.exists) {
                    continue;
                }

                row.setAttribute('data-plex-exists', 'true');

                const actionsCell = row.querySelector('.grid-col-actions') as HTMLElement | null;
                const addLibraryBtn = actionsCell?.querySelector('.grid-add-library-btn') as HTMLElement | null;
                if (!actionsCell || !addLibraryBtn) {
                    continue;
                }

                addLibraryBtn.replaceWith(this.createPlexMatchChip(match, { inActions: true, incomplete: match.complete === false }));
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate album grid rows with Plex status.', error);
        }
    }

    private insertHeroPlexChip(container: HTMLElement | null, match: { exists: boolean; complete?: boolean }, options?: { inActions?: boolean; bulk?: boolean; hero?: boolean }): void {
        if (!container || !match || !match.exists) {
            return;
        }
        if (container.querySelector('.plex-existing-chip')) {
            return;
        }

        const chip = this.createPlexMatchChip(match, {
            inActions: options?.inActions,
            bulk: options?.bulk,
            incomplete: match.complete === false,
            hero: options?.hero
        });

        if (options?.hero) {
            container.appendChild(chip);
            return;
        }

        const heading = container.querySelector('h1, .artist-hero-name, .album-title') as HTMLElement | null;
        if (heading) {
            heading.insertAdjacentElement('afterend', chip);
            return;
        }

        container.appendChild(chip);
    }

    private async annotateArtistCardsWithPlexStatus(artists: ArtistSearchItem[]): Promise<void> {
        if (!Array.isArray(artists) || artists.length === 0) {
            return;
        }

        const signal = this.pendingRequestController?.signal;
        const artistIds = artists.map(artist => artist.id).filter(artistId => Number.isFinite(artistId));
        if (artistIds.length === 0) {
            return;
        }

        try {
            const lookup = await this.lookupStoredMatches([], [], artistIds, signal);
            const artistMatches = Array.isArray(lookup.artists) ? lookup.artists : [];
            const matchById = new Map(artistMatches.map(match => [String(match.artist_id), match]));
            const cards = Array.from(this.resultsContainer.querySelectorAll('.artist-card-compact')) as HTMLElement[];

            for (const card of cards) {
                const artistId = String(card.getAttribute('data-artist-id') || '').trim();
                const match = matchById.get(artistId);
                if (!match || !match.exists || card.querySelector('.plex-existing-chip')) {
                    continue;
                }

                const nameEl = card.querySelector('.artist-card-name') as HTMLElement | null;
                if (!nameEl) {
                    continue;
                }

                const chip = this.createPlexMatchChip(match, { inActions: true, incomplete: match.complete === false });
                nameEl.insertAdjacentElement('afterend', chip);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate artist cards with Plex status.', error);
        }
    }

    private async annotateAlbumHeroWithPlexStatus(albumId: number): Promise<void> {
        if (!Number.isFinite(albumId)) {
            return;
        }

        const signal = this.pendingRequestController?.signal;
        try {
            const lookup = await this.lookupStoredMatches([], [albumId], [], signal);
            const albumMatch = Array.isArray(lookup.albums) ? lookup.albums[0] : undefined;
            if (!albumMatch || !albumMatch.exists) {
                return;
            }

            const container = document.querySelector('.album-actions') as HTMLElement | null;
            this.insertHeroPlexChip(container, albumMatch, { inActions: true, bulk: true });
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate album hero with Plex status.', error);
        }
    }

    private async annotateArtistHeroWithPlexStatus(artistId: number): Promise<void> {
        if (!Number.isFinite(artistId)) {
            return;
        }

        const signal = this.pendingRequestController?.signal;
        try {
            const lookup = await this.lookupStoredMatches([], [], [artistId], signal);
            const artistMatch = Array.isArray(lookup.artists) ? lookup.artists[0] : undefined;
            if (!artistMatch || !artistMatch.exists) {
                return;
            }

            const container = document.querySelector('.artist-actions') as HTMLElement | null;
            this.insertHeroPlexChip(container, artistMatch, { inActions: true, bulk: true });
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate artist hero with Plex status.', error);
        }
    }

    private replaceAddAllLibraryWithPlexBadge(matches: PlexTrackMatch[]): void {
        const addAllLibraryBtn = document.getElementById('addAllLibraryBtn') as HTMLButtonElement | null;
        if (!addAllLibraryBtn || !addAllLibraryBtn.parentElement) {
            return;
        }

        const albumActions = document.querySelector('.album-actions') as HTMLElement | null;
        if (albumActions?.querySelector('.plex-existing-chip')) {
            addAllLibraryBtn.remove();
            return;
        }

        const aggregateMatch: PlexTrackMatch = {
            exists: true,
            confidence: matches.reduce((highest, match) => Math.max(highest, typeof match.confidence === 'number' ? match.confidence : 0), 0),
            variants: matches.flatMap(match => match.variants || [])
        };

        if (albumActions) {
            addAllLibraryBtn.remove();
            albumActions.appendChild(this.createPlexMatchChip(aggregateMatch, { inActions: true, bulk: true }));
            return;
        }

        addAllLibraryBtn.replaceWith(this.createPlexMatchChip(aggregateMatch, { inActions: true, bulk: true }));
    }

    private formatSearchPlaylistCard(playlist: PlaylistSearchItem): string {
        const playlistId = this.escapeHtml(this.getPlaylistId(playlist));
        const playlistName = this.escapeHtml(playlist.title || 'Unknown Playlist');
        const playlistDescription = this.escapeHtml((playlist.description || '').trim());
        const trackTotal = playlist.numberOfTracks ?? playlist.numberOfItems;
        const trackCount = typeof trackTotal === 'number'
            ? `${trackTotal} track${trackTotal !== 1 ? 's' : ''}`
            : '';

        const quality = playlist.audioQuality || '';
        const qualityDisplay = this.formatQuality(quality);
        const coverImage = this.getPlaylistCoverUrl(playlist);

        return `
            <div class="track-card album-card playlist-search-card clickable" data-playlist-id="${playlistId}" title="Click to view tracks">
                <div class="track-artwork">
                    ${coverImage
                ? `<img src="${coverImage}" alt="${playlistName}" loading="lazy">`
                : `<div class="track-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <path d="M9 9h6"></path>
                                <path d="M9 13h6"></path>
                                <path d="M9 17h4"></path>
                            </svg>
                           </div>`
            }
                </div>
                <div class="track-info">
                    <div class="track-title">${playlistName}</div>
                    ${playlistDescription ? `<div class="track-artist"><span class="playlist-description-text">${playlistDescription}</span></div>` : ''}
                    <div class="track-metadata">
                        ${trackCount ? `<span>${trackCount}</span>` : ''}
                        ${trackCount && qualityDisplay ? `<span>•</span>` : ''}
                        ${qualityDisplay ? `<span>${qualityDisplay}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    private getPlaylistId(playlist: PlaylistSearchItem): string {
        if (typeof playlist.uuid === 'string' && playlist.uuid.trim()) {
            return playlist.uuid.trim();
        }

        if (typeof playlist.id === 'string' && playlist.id.trim()) {
            const normalized = this.normalizePlaylistId(playlist.id.trim());
            return normalized || playlist.id.trim();
        }

        if (typeof playlist.id === 'number' && Number.isFinite(playlist.id)) {
            return String(playlist.id);
        }

        if (typeof playlist.url === 'string' && playlist.url.trim()) {
            const normalized = this.normalizePlaylistId(playlist.url.trim());
            return normalized || playlist.url.trim();
        }

        return '';
    }

    private getPlaylistAuthorName(playlist: PlaylistSearchItem): string {
        if (typeof playlist.creator === 'string' && playlist.creator.trim()) {
            return playlist.creator;
        }

        if (playlist.creator && typeof playlist.creator === 'object' && playlist.creator.name?.trim()) {
            return playlist.creator.name;
        }

        const promotedArtistName = playlist.promotedArtists?.find(artist => artist?.name?.trim())?.name;
        if (promotedArtistName) {
            return promotedArtistName;
        }

        if (playlist.type === 'EDITORIAL') {
            return 'TIDAL';
        }

        return 'Unknown';
    }

    private getAddAllPlaylistIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <g transform="translate(2,1)">
                    <path d="M5 0v10"></path>
                    <path d="M0 5h10"></path>
                </g>
                <g transform="translate(8,7)" opacity="0.7">
                    <path d="M5 0v10"></path>
                    <path d="M0 5h10"></path>
                </g>
            </svg>
        `;
    }

    private getAddAllLibraryIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="2" y="2" width="14" height="4" rx="1"></rect>
                <path d="M3 6v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6"></path>
                <rect x="6" y="10" width="14" height="4" rx="1" opacity="0.6"></rect>
                <path d="M7 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" opacity="0.6"></path>
            </svg>
        `;
    }

    private setBulkActionButtonState(
        button: HTMLButtonElement | null,
        buttonType: 'playlist' | 'library',
        state: 'idle' | 'loading' | 'success' | 'failed'
    ): void {
        if (!button) {
            return;
        }

        button.classList.remove('queued', 'in-progress', 'completed', 'failed');

        if (state === 'loading') {
            button.disabled = true;
            button.classList.add('in-progress');
            button.innerHTML = this.getSpinnerIconSvg();
            return;
        }

        button.disabled = false;

        if (state === 'success') {
            button.classList.add('completed');
            button.innerHTML = this.getCheckmarkIconSvg();
            return;
        }

        if (state === 'failed') {
            button.classList.add('failed');
            button.innerHTML = this.getExclamationIconSvg();
            return;
        }

        button.innerHTML = buttonType === 'playlist'
            ? this.getAddAllPlaylistIconSvg()
            : this.getAddAllLibraryIconSvg();
    }

    private getPlaylistCoverUrl(playlist: PlaylistSearchItem): string {
        const rawCover = playlist.customImageUrl || playlist.squareImage || playlist.image || playlist.cover || '';
        if (!rawCover) {
            return '';
        }

        return this.getHifiImageUrl(rawCover, 640);
    }

    private normalizePlaylistId(value: string): string {
        const trimmed = value.trim();
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(trimmed)) {
            return trimmed;
        }

        const match = trimmed.match(/playlist\/([0-9a-f-]{36})/i);
        if (match && match[1]) {
            return match[1];
        }

        return '';
    }

    private async fetchPlaylistTracks(playlistId: string, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'playlist', playlistId };
        this.explorePlaylistTitle = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'playlist', playlistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading playlist tracks...');

        try {
            const normalizedPlaylistId = this.normalizePlaylistId(playlistId) || playlistId;
            const response = await fetch(`/api/hifi/playlists/${encodeURIComponent(normalizedPlaylistId)}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch playlist');
            }

            const data: any = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchPlaylistTracks(normalizedPlaylistId));
                return;
            }

            const payload = data?.data && typeof data.data === 'object' ? data.data : data;
            if (!payload || typeof payload !== 'object') {
                this.displayMessage('No playlist data found');
                return;
            }

            const playlistMeta = payload.playlist && typeof payload.playlist === 'object'
                ? payload.playlist
                : payload;

            const rawItems = Array.isArray(payload.items)
                ? payload.items
                : Array.isArray(payload.tracks)
                    ? payload.tracks
                    : Array.isArray(playlistMeta.items)
                        ? playlistMeta.items
                        : Array.isArray(playlistMeta.tracks)
                            ? playlistMeta.tracks
                            : [];

            const tracks = rawItems
                .map((item: any) => {
                    if (
                        item &&
                        typeof item === 'object' &&
                        item.item &&
                        typeof item.item === 'object' &&
                        'id' in item.item &&
                        'title' in item.item
                    ) {
                        return item.item as Track;
                    }

                    if (item && typeof item === 'object' && 'id' in item && 'title' in item) {
                        return item as Track;
                    }

                    return null;
                })
                .filter((track: Track | null): track is Track => track !== null);

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            const playlistTitle = playlistMeta.title || playlistMeta.name || 'Playlist';
            this.explorePlaylistTitle = playlistTitle;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(playlistTitle)}</h2>
                    </div>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                </div>
                <div class="results-list">
                    ${this.formatTracksGrid(tracks)}
                </div>
            `;

            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement;
            if (resultsHeaderTop) {
                const buttonsContainer = document.createElement('div');
                buttonsContainer.className = 'add-all-buttons-container';
                const addPlaylistBtn = document.createElement('button');
                addPlaylistBtn.id = 'addAllPlaylistBtn';
                addPlaylistBtn.className = 'add-all-btn';
                addPlaylistBtn.title = 'Add all tracks to a playlist';
                addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                addPlaylistBtn.addEventListener('click', () => this.addAllToPlaylist());
                buttonsContainer.appendChild(addPlaylistBtn);
                const addLibraryBtn = document.createElement('button');
                addLibraryBtn.id = 'addAllLibraryBtn';
                addLibraryBtn.className = 'add-all-btn';
                addLibraryBtn.title = 'Add all tracks to library';
                addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                addLibraryBtn.addEventListener('click', () => this.addAllToLibrary());
                buttonsContainer.appendChild(addLibraryBtn);
                resultsHeaderTop.appendChild(buttonsContainer);
                this.movePlexPlaylistContainerBeneathDownloadAll();
            }

            void this.annotateTrackCardsWithPlexStatus(tracks);
        } catch (error) {
            this.displayMessage('Error loading playlist tracks. Please try again.', () => this.fetchPlaylistTracks(playlistId));
            console.error('Playlist fetch error:', error);
        }
    }

    private formatTrackCard(track: Track, showTrackNumber: boolean = false, numberOfVolumes?: number): string {
        // Get artist names and IDs
        const artistNames = track.artists && track.artists.length > 0
            ? track.artists.map(a => a.name).join(', ')
            : track.artist?.name || 'Unknown Artist';
        const primaryArtistId = track.artists?.[0]?.id || track.artist?.id;

        // Get album info
        const albumTitle = track.album?.title || 'Unknown Album';
        const albumCover = track.album?.cover || track.cover;
        const albumId = track.album?.id;

        // Format duration
        const duration = track.duration
            ? this.formatDuration(track.duration)
            : '';

        // Get quality info - prefer the normalized maxAudioQuality field
        const quality = track.maxAudioQuality || track.audioQuality || track.quality || '';
        const qualityDisplay = this.formatQuality(quality);

        // Format track title with optional track number and version
        // For multi-disc albums, prepend disc number (e.g., "1-03" for disc 1, track 3)
        let trackTitle = this.escapeHtml(track.title);

        // Append version info if available
        if (track.version && typeof track.version === 'string' && track.version.trim()) {
            trackTitle += ` (${this.escapeHtml(track.version)})`;
        }

        if (showTrackNumber && track.trackNumber) {
            const volumeNumber = track.volumeNumber || 1;
            const displayTrackNumber = numberOfVolumes && numberOfVolumes > 1
                ? `${volumeNumber}-${String(track.trackNumber).padStart(2, '0')}`
                : String(track.trackNumber);
            trackTitle = `${displayTrackNumber}. ${trackTitle}`;
        }

        return `
            <div class="track-card" data-track-id="${track.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''} ${albumId ? `data-album-id="${albumId}"` : ''}>
                <button class="track-play-btn" title="Play" aria-label="Play" aria-pressed="false" data-track-id="${track.id}">
                    ${this.getPlayIconSvg()}
                </button>
                <div class="track-artwork">
                    ${albumCover
                ? `<img src="${this.formatTidalImageUrl(albumCover, 1280)}" alt="${track.title}" loading="lazy">`
                : `<div class="track-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"></circle>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                           </div>`
            }
                </div>
                <div class="track-info">
                    <div class="track-title">${trackTitle}</div>
                    <div class="track-artist">
                        <span class="track-artist-name" ${primaryArtistId ? `title="View albums by ${this.escapeHtml(artistNames)}"` : ''}>${this.escapeHtml(artistNames)}</span>
                    </div>
                    <div class="track-metadata">
                        <span class="track-album-name" ${albumId ? `title="View tracks on ${this.escapeHtml(albumTitle)}"` : ''}>${this.escapeHtml(albumTitle)}</span>
                        ${qualityDisplay ? `<span>•</span><span>${qualityDisplay}</span>` : ''}
                        ${track.explicit ? `<span>•</span><span class="explicit-badge" title="Explicit content">E</span>` : ''}
                    </div>
                </div>
                <div class="track-actions">
                    <button class="track-more-btn" title="More Like This" aria-label="More Like This">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                    <button class="track-add-playlist-btn" title="Add to Playlist" data-track-id="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14"></path>
                            <path d="M5 12h14"></path>
                        </svg>
                    </button>
                    <button class="track-download-btn" title="Download to Library" data-track-id="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="5" rx="1"></rect>
                            <path d="M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path>
                            <rect x="8" y="12" width="8" height="1"></rect>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    private normalizeTrack(track: Track | PlexLibraryTrack): NormalizedTrack {
        if ('artists' in track || 'artist' in track && typeof (track as Track).artist === 'object') {
            const t = track as Track;
            const artistNames = t.artists && t.artists.length > 0
                ? t.artists.map(a => a.name).join(', ')
                : (typeof t.artist === 'object' ? t.artist?.name : undefined) || 'Unknown Artist';
            const primaryArtistId = t.artists?.[0]?.id ?? (typeof t.artist === 'object' ? t.artist?.id : undefined);
            const quality = t.maxAudioQuality || t.audioQuality || t.quality || '';
            return {
                id: String(t.id),
                title: t.title,
                version: t.version,
                artist: artistNames,
                artistId: primaryArtistId,
                album: t.album?.title || 'Unknown Album',
                albumId: t.album?.id,
                albumCover: t.album?.cover || t.cover,
                trackNumber: t.trackNumber ?? null,
                volumeNumber: t.volumeNumber || 1,
                duration: t.duration ?? null,
                quality,
                explicit: t.explicit || false,
            };
        }
        const p = track as PlexLibraryTrack;
        const qualityFormat = (p.quality_format || '').trim().toUpperCase();
        const qualityBitrate = typeof p.quality_bitrate_kbps === 'number' ? `${p.quality_bitrate_kbps} kbps` : undefined;
        return {
            id: p.id,
            title: p.title || 'Unknown Track',
            artist: p.artist || this.libraryCurrentArtist?.name || 'Unknown Artist',
            artistId: p.artist_id ? parseInt(p.artist_id, 10) : undefined,
            album: p.album || 'Unknown Album',
            albumCover: p.cover,
            trackNumber: typeof p.track_number === 'number' ? p.track_number : null,
            volumeNumber: typeof p.disc_number === 'number' ? p.disc_number : 1,
            duration: typeof p.duration === 'number' ? Math.max(0, Math.round(p.duration / 1000)) : null,
            quality: '',
            explicit: false,
            qualityFormat: qualityFormat || undefined,
            qualityBitrate,
        };
    }

    private allTracksFromSameAlbum(tracks: Track[]): boolean {
        if (tracks.length <= 1) return true;
        const firstAlbumId = tracks[0].album?.id;
        return tracks.every(track => track.album?.id === firstAlbumId);
    }

    private renderTrackGrid(tracks: (Track | PlexLibraryTrack)[], options: TrackGridOptions): string {
        const normalized = tracks.map(t => this.normalizeTrack(t));
        const emptyMessage = options.emptyMessage || '<div class="library-placeholder"><p>No tracks found.</p></div>';

        return `
            <div class="tracks-grid-wrapper" data-view-mode="${options.viewMode}">
                <div class="tracks-grid">
                    ${this.formatTrackGridHeader(options.showTrackNumber || false, options.showAlbumColumn || false, options.showArtwork || false)}
                    ${normalized.length > 0
                ? normalized.map(track => this.formatTrackGridRow(track, options)).join('')
                : emptyMessage}
                </div>
            </div>
        `;
    }

    private formatTracksGrid(tracks: Track[], numberOfVolumes?: number, includeTrackNumbers: boolean = true): string {
        const isSingleAlbum = this.allTracksFromSameAlbum(tracks);
        const showTrackNumberColumn = includeTrackNumbers && isSingleAlbum;
        const showArtworkInSingleAlbum = !includeTrackNumbers && isSingleAlbum;

        if (isSingleAlbum) {
            return this.renderTrackGrid(tracks, {
                viewMode: 'single-album',
                showTrackNumber: showTrackNumberColumn,
                numberOfVolumes,
                showAlbumColumn: false,
                showArtwork: showArtworkInSingleAlbum,
            });
        } else {
            return this.renderTrackGrid(tracks, {
                viewMode: 'multi-album',
                showTrackNumber: false,
                showAlbumColumn: true,
                showArtwork: true,
            });
        }
    }

    private formatTrackGridRow(track: NormalizedTrack, options: TrackGridOptions): string {
        const showTrackNumber = options.showTrackNumber || false;
        const showAlbumColumn = options.showAlbumColumn || false;
        const showArtwork = options.showArtwork || false;
        const dataAttr = options.dataAttr || 'data-track-id';
        const extraRowClass = options.extraRowClass || '';
        const actions = options.actions || 'full';
        const qualityStyle = options.qualityStyle || 'tier';
        const rowClasses = ['tracks-grid-row', ...(extraRowClass ? [extraRowClass] : [])].join(' ');
        const extraAttrs = options.rowDataAttrs
            ? Object.entries(options.rowDataAttrs(track)).map(([k, v]) => `${k}="${this.escapeHtml(v)}"`).join(' ')
            : '';

        let trackTitle = this.escapeHtml(track.title);
        if (track.version && typeof track.version === 'string' && track.version.trim()) {
            trackTitle += ` (${this.escapeHtml(track.version)})`;
        }

        let trackNumberDisplay = '';
        if (showTrackNumber && track.trackNumber) {
            const vn = track.volumeNumber || 1;
            trackNumberDisplay = options.numberOfVolumes && options.numberOfVolumes > 1
                ? `${vn}-${String(track.trackNumber).padStart(2, '0')}`
                : String(track.trackNumber);
        }

        const artworkSrc = track.albumCover
            ? (track.albumCover.startsWith('http') ? track.albumCover : this.getHifiImageUrl(track.albumCover, 1280))
            : null;

        const durationDisplay = track.duration ? this.formatDuration(track.duration) : '—';

        let qualityDisplay = '—';
        if (qualityStyle === 'format-bitrate') {
            const parts = [track.qualityFormat, track.qualityBitrate].filter(Boolean);
            qualityDisplay = parts.length > 0 ? parts.join(' • ') : '—';
        } else {
            qualityDisplay = track.quality ? this.formatQuality(track.quality) : '—';
        }

        return `
            <div class="${rowClasses}" ${dataAttr}="${track.id}" ${track.artistId ? `data-artist-id="${track.artistId}"` : ''} ${track.albumId ? `data-album-id="${track.albumId}"` : ''} ${extraAttrs}>
                ${showArtwork ? `<div class="grid-cell grid-col-artwork">
                    ${artworkSrc
                    ? `<img src="${artworkSrc}" alt="${this.escapeHtml(track.title)}" loading="lazy">`
                    : `<div class="grid-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"></circle>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                           </div>`
                }
                </div>` : ''}
                ${showTrackNumber ? `<div class="grid-cell grid-col-track-number">${trackNumberDisplay}</div>` : ''}
                <div class="grid-cell grid-col-title">
                    <div class="track-title-with-badge">
                        ${trackTitle}
                        ${track.explicit ? `<span class="explicit-badge" title="Explicit content">E</span>` : ''}
                    </div>
                </div>
                <div class="grid-cell grid-col-artist">
                    <span class="track-artist-name" ${track.artistId ? `title="View albums by ${this.escapeHtml(track.artist)}"` : ''}>${this.escapeHtml(track.artist)}</span>
                </div>
                ${showAlbumColumn ? `<div class="grid-cell grid-col-album">
                    <span class="track-album-name" ${track.albumId ? `title="View tracks on ${this.escapeHtml(track.album)}"` : ''}>${this.escapeHtml(track.album)}</span>
                </div>` : ''}
                <div class="grid-cell grid-col-duration">${durationDisplay}</div>
                <div class="grid-cell grid-col-quality">${qualityDisplay}</div>
                <div class="grid-cell grid-col-actions">
                    <button class="grid-play-btn" title="Play" aria-label="Play" ${dataAttr}="${track.id}">
                        ${this.getPlayIconSvg()}
                    </button>
                    ${actions === 'full' ? `
                    <button class="grid-more-btn" title="Find Similar" aria-label="Find Similar">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                    <button class="grid-add-playlist-btn" title="Add to Playlist" ${dataAttr}="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14"></path>
                            <path d="M5 12h14"></path>
                        </svg>
                    </button>
                    <button class="grid-add-library-btn" title="Add to Library" ${dataAttr}="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="5" rx="1"></rect>
                            <path d="M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path>
                            <rect x="8" y="12" width="8" height="1"></rect>
                        </svg>
                    </button>` : ''}
                </div>
            </div>
        `;
    }

    private formatTrackGridHeader(showTrackNumber: boolean, showAlbumColumn: boolean, showArtwork: boolean): string {
        return `
            <div class="tracks-grid-header">
                ${showTrackNumber ? '<div class="grid-cell grid-col-track-number">#</div>' : ''}
                ${showArtwork ? '<div class="grid-cell grid-col-artwork"></div>' : ''}
                <div class="grid-cell grid-col-title">Title</div>
                <div class="grid-cell grid-col-artist">Artist</div>
                ${showAlbumColumn ? '<div class="grid-cell grid-col-album">Album</div>' : ''}
                <div class="grid-cell grid-col-duration">Duration</div>
                <div class="grid-cell grid-col-quality">MAX QUALITY</div>
                <div class="grid-cell grid-col-actions">Actions</div>
            </div>
        `;
    }

    private async renderProgressiveTrackGrid(
        tracks: PlaylistTrackInput[],
        options: TrackGridOptions & { resultsContainerId: string; playlistName: string }
    ): Promise<{ matched: Track[]; notFound: PlaylistTrackInput[] }> {
        const resultsList = document.getElementById(options.resultsContainerId);
        const matchedTracks: Track[] = [];
        const notFoundTracks: PlaylistTrackInput[] = [];

        for (const track of tracks) {
            const searchQuery = `${track.name} ${track.artist}`;
            try {
                const response = await fetch(`/api/hifi/search?s=${encodeURIComponent(searchQuery)}`, {
                    signal: this.pendingRequestController?.signal
                });
                if (response.ok) {
                    const data = await response.json();
                    const items = data.data?.items || [];
                    if (items.length > 0) {
                        const matched = items[0] as Track;
                        const normalized = this.normalizeTrack(matched);
                        const rowHtml = this.formatTrackGridRow(normalized, options);
                        resultsList?.insertAdjacentHTML('beforeend', rowHtml);
                        matchedTracks.push(matched);
                    } else {
                        notFoundTracks.push(track);
                    }
                } else {
                    notFoundTracks.push(track);
                }
            } catch {
                notFoundTracks.push(track);
            }
        }

        return { matched: matchedTracks, notFound: notFoundTracks };
    }

    private createAddAllButtons(): void {
        const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement;
        if (!resultsHeaderTop || resultsHeaderTop.querySelector('.add-all-buttons-container')) {
            return;
        }
        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'add-all-buttons-container';

        const addPlaylistBtn = document.createElement('button');
        addPlaylistBtn.id = 'addAllPlaylistBtn';
        addPlaylistBtn.className = 'add-all-btn';
        addPlaylistBtn.title = 'Add all tracks to a playlist';
        addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
        addPlaylistBtn.addEventListener('click', () => this.addAllToPlaylist());
        buttonsContainer.appendChild(addPlaylistBtn);

        const addLibraryBtn = document.createElement('button');
        addLibraryBtn.id = 'addAllLibraryBtn';
        addLibraryBtn.className = 'add-all-btn';
        addLibraryBtn.title = 'Add all tracks to library';
        addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
        addLibraryBtn.addEventListener('click', () => this.addAllToLibrary());
        buttonsContainer.appendChild(addLibraryBtn);

        resultsHeaderTop.appendChild(buttonsContainer);
        this.movePlexPlaylistContainerBeneathDownloadAll();
    }

    private normalizeAlbum(album: AlbumSearchItem | PlexLibraryAlbum): NormalizedAlbum {
        if ('maxAudioQuality' in album || 'audioQuality' in album || 'releaseDate' in album || 'numberOfTracks' in album || 'numberOfItems' in album || 'explicit' in album) {
            const a = album as AlbumSearchItem;
            const artistNames = a.artists && a.artists.length > 0
                ? a.artists.map(ar => ar.name).join(', ')
                : (typeof a.artist === 'object' ? (a.artist as Artist)?.name : a.artist) || 'Unknown Artist';
            const primaryArtistId = a.artists?.[0]?.id ?? (typeof a.artist === 'object' ? (a.artist as Artist)?.id : undefined);
            const quality = a.maxAudioQuality || a.audioQuality || '';
            return {
                id: String(a.id),
                title: a.title,
                artist: artistNames,
                artistId: primaryArtistId,
                year: a.releaseDate ? new Date(a.releaseDate).getFullYear() : null,
                trackCount: a.numberOfTracks ?? a.numberOfItems ?? null,
                quality,
                explicit: a.explicit || false,
                cover: a.cover,
            };
        }
        const p = album as PlexLibraryAlbum;
        return {
            id: p.id,
            title: p.title || 'Unknown Album',
            artist: p.artist || this.libraryCurrentArtist?.name || 'Unknown Artist',
            year: p.year ?? null,
            trackCount: typeof p.track_count === 'number' ? p.track_count : null,
            quality: '',
            explicit: false,
            cover: p.cover,
        };
    }

    private formatAlbumGridHeader(hideArtist: boolean = false, includeQuality: boolean = true): string {
        return `
            <div class="albums-grid-header${hideArtist ? ' hide-artist' : ''}">
                <div class="grid-cell grid-col-artwork"></div>
                <div class="grid-cell grid-col-title">ALBUM</div>
                ${!hideArtist ? '<div class="grid-cell grid-col-artist">ARTIST</div>' : ''}
                <div class="grid-cell grid-col-year">YEAR</div>
                <div class="grid-cell grid-col-track-count">TRACKS</div>
                ${includeQuality ? '<div class="grid-cell grid-col-quality">MAX QUALITY</div>' : ''}
                <div class="grid-cell grid-col-actions">ACTIONS</div>
            </div>
        `;
    }

    private getPlayIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <polygon points="6 4 20 12 6 20"></polygon>
            </svg>
        `;
    }

    private getStopIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <rect x="6" y="6" width="12" height="12"></rect>
            </svg>
        `;
    }

    private getSpinnerIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                <circle cx="12" cy="12" r="10" opacity="0.2"></circle>
                <path d="M22 12a10 10 0 0 1-10 10" stroke-linecap="round">
                    <animateTransform attributeName="transform" attributeType="XML" type="rotate" values="0 12 12;360 12 12" dur="1s" repeatCount="indefinite"></animateTransform>
                </path>
            </svg>
        `;
    }

    private getCheckmarkIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
    }

    private getExclamationIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 2v20"></path>
                <circle cx="12" cy="20" r="1"></circle>
            </svg>
        `;
    }

    private setPlayButtonState(button: HTMLButtonElement, isPlaying: boolean): void {
        button.classList.toggle('is-playing', isPlaying);
        button.classList.remove('is-loading');
        button.setAttribute('aria-pressed', isPlaying ? 'true' : 'false');
        button.title = isPlaying ? 'Stop' : 'Play';
        button.innerHTML = isPlaying ? this.getStopIconSvg() : this.getPlayIconSvg();
    }

    private setPlayButtonLoading(button: HTMLButtonElement, isLoading: boolean): void {
        button.classList.toggle('is-loading', isLoading);
        button.disabled = isLoading;
    }

    private stopPlayback(): void {
        if (this.currentAudioCleanup) {
            const { audio, onEnded, onError } = this.currentAudioCleanup;
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('error', onError);
            this.currentAudioCleanup = null;
        }

        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.src = '';
            this.currentAudio.load();
        }

        if (this.currentPlayButton) {
            this.setPlayButtonState(this.currentPlayButton, false);
        }

        this.currentAudio = null;
        this.currentPlayingTrackId = null;
        this.currentPlayButton = null;
    }

    private async handlePlayToggle(
        trackId: number,
        trackCard: HTMLElement,
        playButton: HTMLButtonElement
    ): Promise<void> {
        const playbackTrackId = `deezer:${trackId}`;
        if (this.currentPlayingTrackId === playbackTrackId) {
            this.stopPlayback();
            return;
        }

        this.stopPlayback();
        this.setPlayButtonState(playButton, true);
        this.setPlayButtonLoading(playButton, true);
        this.currentPlayingTrackId = playbackTrackId;
        this.currentPlayButton = playButton;

        const audio = new Audio();
        audio.preload = 'none';
        audio.crossOrigin = 'anonymous';
        this.currentAudio = audio;

        const onEnded = () => {
            if (this.currentAudio === audio) {
                this.stopPlayback();
            }
        };
        const onError = () => {
            if (this.currentAudio === audio) {
                this.stopPlayback();
            }
        };
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('error', onError);
        this.currentAudioCleanup = { audio, onEnded, onError };

        try {
            const streamUrl = await this.fetchTrackStreamUrl(trackId);
            audio.src = streamUrl;
            this.setPlayButtonLoading(playButton, false);
            await audio.play();
        } catch (error) {
            console.warn('[PLAYBACK] Failed to start playback:', error);
            this.setPlayButtonLoading(playButton, false);
            this.stopPlayback();
        }
    }

    private async fetchTrackStreamUrl(trackId: number): Promise<string> {
        return `/api/hifi/tracks/${encodeURIComponent(String(trackId))}/stream?quality=LOW`;
    }

    private async handlePlayLibraryToggle(trackId: string, playButton: HTMLButtonElement): Promise<void> {
        const playbackTrackId = `plex:${trackId}`;
        if (this.currentPlayingTrackId === playbackTrackId) {
            this.stopPlayback();
            return;
        }

        this.stopPlayback();
        this.setPlayButtonState(playButton, true);
        this.setPlayButtonLoading(playButton, true);
        this.currentPlayingTrackId = playbackTrackId;
        this.currentPlayButton = playButton;

        const audio = new Audio();
        audio.preload = 'none';
        audio.crossOrigin = 'anonymous';
        this.currentAudio = audio;

        const onEnded = () => {
            if (this.currentAudio === audio) {
                this.stopPlayback();
            }
        };
        const onError = () => {
            if (this.currentAudio === audio) {
                this.stopPlayback();
            }
        };
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('error', onError);
        this.currentAudioCleanup = { audio, onEnded, onError };

        try {
            const streamUrl = await this.fetchLibraryTrackStreamUrl(trackId);
            audio.src = streamUrl;
            this.setPlayButtonLoading(playButton, false);
            await audio.play();
        } catch (error) {
            console.warn('[PLAYBACK] Failed to start Plex library playback:', error);
            this.setPlayButtonLoading(playButton, false);
            this.stopPlayback();
        }
    }

    private async fetchLibraryTrackStreamUrl(trackId: string): Promise<string> {
        const params = new URLSearchParams();
        const userId = this.getSelectedPlexUserId();
        if (userId) {
            params.set('user_id', userId);
        }

        const query = params.toString();
        const response = await fetch(`/api/plex/library/tracks/${encodeURIComponent(trackId)}/stream${query ? `?${query}` : ''}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch Plex library stream URL (HTTP ${response.status})`);
        }

        const data = await response.json().catch(() => ({} as { stream_url?: string }));
        const streamUrl = (data as { stream_url?: string }).stream_url;
        if (typeof streamUrl !== 'string' || !streamUrl) {
            throw new Error('Plex library stream URL missing from response');
        }

        return streamUrl;
    }

    private decodeManifest(manifestBase64: string): { urls?: string[] } | null {
        try {
            const normalized = manifestBase64.replace(/-/g, '+').replace(/_/g, '/');
            const manifestJson = atob(normalized);
            return JSON.parse(manifestJson);
        } catch (error) {
            console.warn('[PLAYBACK] Failed to decode manifest:', error);
            return null;
        }
    }

    private formatAlbumCard(album: AlbumSearchItem): string {
        // Get artist names and IDs
        const artistNames = album.artists && album.artists.length > 0
            ? album.artists.map(a => a.name).join(', ')
            : album.artist?.name || 'Unknown Artist';
        const primaryArtistId = album.artists?.[0]?.id || album.artist?.id;

        // Format release year if available
        const releaseYear = album.releaseDate
            ? new Date(album.releaseDate).getFullYear()
            : '';

        // Format track count
        const trackCount = (album.numberOfTracks ?? album.numberOfItems)
            ? `${album.numberOfTracks ?? album.numberOfItems} track${(album.numberOfTracks ?? album.numberOfItems) !== 1 ? 's' : ''}`
            : '';

        // Format audio quality if available - prefer the normalized maxAudioQuality field
        const quality = album.maxAudioQuality || album.audioQuality || '';
        const qualityDisplay = this.formatQuality(quality);

        return `
            <div class="track-card album-card clickable" data-album-id="${album.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''} title="Click to view tracks">
                <div class="track-artwork">
                    ${album.cover
                ? `<img src="${this.getHifiImageUrl(album.cover, 1280)}" alt="${album.title}" loading="lazy">`
                : `<div class="track-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                           </div>`
            }
                </div>
                <div class="track-info">
                    <div class="track-title">${this.escapeHtml(album.title)}</div>
                    <div class="track-artist">
                        <span class="track-artist-name" ${primaryArtistId ? `title="View albums by ${this.escapeHtml(artistNames)}"` : ''}>${this.escapeHtml(artistNames)}</span>
                    </div>
                    <div class="track-metadata">
                        ${releaseYear ? `<span>${releaseYear}</span>` : ''}
                        ${releaseYear && trackCount ? `<span>•</span>` : ''}
                        ${trackCount ? `<span>${trackCount}</span>` : ''}
                        ${trackCount && qualityDisplay ? `<span>•</span>` : ''}
                        ${qualityDisplay ? `<span>${qualityDisplay}</span>` : ''}
                        ${album.explicit ? `<span>•</span><span class="explicit-badge" title="Explicit content">E</span>` : ''}
                    </div>
                </div>
                <div class="track-actions">
                    <button class="track-more-btn" title="More Like This" aria-label="More Like This">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                </div>
            </div>
        `;
    }

    private formatAlbumGridRow(album: NormalizedAlbum, options: AlbumGridOptions): string {
        const hideArtist = options.hideArtist || false;
        const includeQuality = options.includeQuality !== false;
        const dataAttr = options.dataAttr || 'data-album-id';
        const extraRowClass = options.extraRowClass || '';
        const actions = options.actions || 'full';
        const rowClasses = ['albums-grid-row', ...(hideArtist ? ['hide-artist'] : []), ...(extraRowClass ? [extraRowClass] : [])].join(' ');
        const extraAttrs = options.rowDataAttrs
            ? Object.entries(options.rowDataAttrs(album)).map(([k, v]) => `${k}="${this.escapeHtml(v)}"`).join(' ')
            : '';

        const artworkSrc = album.cover
            ? (album.cover.startsWith('http') ? album.cover : this.getHifiImageUrl(album.cover, 1280))
            : null;

        const year = album.year ? String(album.year) : '—';
        const trackCount = album.trackCount ? String(album.trackCount) : '—';
        const qualityDisplay = album.quality ? this.formatQuality(album.quality) : '—';

        return `
            <div class="${rowClasses}" ${dataAttr}="${album.id}" ${album.artistId ? `data-artist-id="${album.artistId}"` : ''} ${extraAttrs}>
                <div class="grid-cell grid-col-artwork">
                    ${artworkSrc
                ? `<img src="${artworkSrc}" alt="${this.escapeHtml(album.title)}" loading="lazy">`
                : `<div class="grid-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                           </div>`
            }
                </div>
                <div class="grid-cell grid-col-title">
                    <div class="track-title-with-badge">
                        ${this.escapeHtml(album.title)}
                        ${album.explicit ? `<span class="explicit-badge" title="Explicit content">E</span>` : ''}
                    </div>
                </div>
                ${!hideArtist ? `<div class="grid-cell grid-col-artist">
                    <span class="album-artist-name" ${album.artistId ? `title="View albums by ${this.escapeHtml(album.artist)}"` : ''}>${this.escapeHtml(album.artist)}</span>
                </div>` : ''}
                <div class="grid-cell grid-col-year">${year}</div>
                <div class="grid-cell grid-col-track-count">${trackCount}</div>
                ${includeQuality ? `<div class="grid-cell grid-col-quality">${qualityDisplay}</div>` : ''}
                <div class="grid-cell grid-col-actions">
                    <button class="grid-play-btn" title="View Tracks" aria-label="View Tracks" ${dataAttr}="${album.id}">
                        ${this.getPlayIconSvg()}
                    </button>
                    ${actions === 'full' ? `
                    <button class="grid-more-btn" title="Find Similar" aria-label="Find Similar">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                    <button class="grid-add-playlist-btn" title="Add to Playlist" ${dataAttr}="${album.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14"></path>
                            <path d="M5 12h14"></path>
                        </svg>
                    </button>
                    <button class="grid-add-library-btn" title="Add to Library" ${dataAttr}="${album.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="5" rx="1"></rect>
                            <path d="M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path>
                            <rect x="8" y="12" width="8" height="1"></rect>
                        </svg>
                    </button>` : ''}
                </div>
            </div>
        `;
    }

    private renderAlbumGrid(albums: (AlbumSearchItem | PlexLibraryAlbum)[], options: AlbumGridOptions): string {
        const normalized = albums.map(a => this.normalizeAlbum(a));
        const emptyMessage = options.emptyMessage || '<div class="library-placeholder"><p>No albums found.</p></div>';

        return `
            <div class="albums-grid-wrapper" data-view-mode="${options.viewMode}">
                <div class="albums-grid">
                    ${this.formatAlbumGridHeader(options.hideArtist || false, options.includeQuality !== false)}
                    ${normalized.length > 0
                ? normalized.map(album => this.formatAlbumGridRow(album, options)).join('')
                : emptyMessage}
                </div>
            </div>
        `;
    }

    private formatArtistCard(artist: ArtistSearchItem): string {
        return `
            <div class="artist-card-compact clickable" data-artist-id="${artist.id}" title="Click to view albums">
                <div class="artist-card-name">${this.escapeHtml(artist.name)}</div>
                <div class="artist-card-image">
                    ${artist.picture
                ? `<img src="${this.getHifiImageUrl(artist.picture, 750)}" alt="${this.escapeHtml(artist.name)}" loading="lazy">`
                : `<div class="artist-card-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="8" r="4"></circle>
                                <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"></path>
                            </svg>
                           </div>`
            }
                </div>
                <button class="artist-card-btn" title="Find Similar Artists" aria-label="Find Similar Artists">
                    ${this.getMoreLikeIconSvg()}
                </button>
            </div>
        `;
    }

    private getMoreLikeIconSvg(): string {
        return `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M12 2v6"></path>
                <path d="M12 16v6"></path>
                <path d="M4.93 4.93l4.24 4.24"></path>
                <path d="M14.83 14.83l4.24 4.24"></path>
                <path d="M2 12h6"></path>
                <path d="M16 12h6"></path>
                <path d="M4.93 19.07l4.24-4.24"></path>
                <path d="M14.83 9.17l4.24-4.24"></path>
            </svg>
        `;
    }

    private formatDuration(seconds: number): string {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    private formatQuality(quality: string): string {
        const qualityMap: { [key: string]: string } = {
            'DOLBY_ATMOS': 'DOLBY ATMOS',
            'HI_RES_LOSSLESS': 'HI-RES FLAC',
            'HIRES_LOSSLESS': 'HI-RES FLAC',
            'LOSSLESS': 'LOSSLESS FLAC',
            'HIGH': 'HIGH AAC',
            'LOW': 'LOW AAC'
        };
        return qualityMap[quality] || quality;
    }

    private getHifiImageUrl(imageIdOrPath: string | undefined, size: number): string {
        if (!imageIdOrPath) {
            return '';
        }

        const normalized = imageIdOrPath.trim();
        if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
            return normalized;
        }

        if (normalized.startsWith('//')) {
            return `https:${normalized}`;
        }

        if (normalized.startsWith('resources.tidal.com/')) {
            return `https://${normalized}`;
        }

        if (normalized.startsWith('/images/')) {
            return `https://resources.tidal.com${normalized}`;
        }

        return this.formatTidalImageUrl(normalized, size);
    }

    private formatTidalImageUrl(imageIdOrPath: string, size: number): string {
        const imagePath = imageIdOrPath.replace(/-/g, '/');
        return `https://resources.tidal.com/images/${imagePath}/${size}x${size}.jpg`;
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    private async fetchWithRetry(
        url: string,
        options?: RequestInit,
        maxRetries: number = 3
    ): Promise<Response> {
        let lastError: Error | null = null;

        // Ensure abort signal is included if not already provided
        const finalOptions = {
            ...options,
            signal: options?.signal || this.pendingRequestController?.signal
        };

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const response = await fetch(url, finalOptions);

                // Only retry on 5xx errors or connection issues
                if (response.status < 500) {
                    return response;
                }

                // 5xx error - log and retry
                lastError = new Error(`HTTP ${response.status}`);
                if (attempt < maxRetries) {
                    const delay = 1000 * Math.pow(2, attempt);
                    console.log(`[RETRY] HTTP ${response.status} on attempt ${attempt + 1}/${maxRetries + 1}. Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }

                // Last attempt, return the response
                return response;
            } catch (error) {
                lastError = error as Error;
                if (attempt < maxRetries) {
                    const delay = 1000 * Math.pow(2, attempt);
                    console.log(`[RETRY] ${(error as Error).message} on attempt ${attempt + 1}/${maxRetries + 1}. Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }
                // Last attempt, throw the error
                throw error;
            }
        }

        throw lastError || new Error('Fetch failed');
    }

    private displayMessage(message: string, retryFn?: () => Promise<void>): void {
        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(false);
        this.lastRetryFunction = retryFn || null;

        const retryButton = retryFn
            ? `<button class="retry-button" id="retryButton">Retry</button>`
            : '';

        this.resultsContainer.innerHTML = `
            <div class="message">
                <p>${message}</p>
                ${retryButton}
            </div>
        `;

        if (retryFn) {
            const retryBtn = document.getElementById('retryButton');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    void retryFn();
                });
            }
        }
    }

    private async fetchArtistAlbums(artistId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'artist', artistId };
        this.exploreArtistName = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'artist', artistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading artist albums...');

        try {
            const response = await fetch(`/api/hifi/artists/${encodeURIComponent(String(artistId))}?include_albums=true&include_tracks=true`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch artist');
            }

            const data: ArtistObject = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchArtistAlbums(artistId));
                return;
            }

            const artistData = data.artist || {};
            const albums = Array.isArray(artistData.albums) ? artistData.albums : [];
            const topTracks = Array.isArray(artistData.top_tracks) ? (artistData.top_tracks as Track[]).slice(0, 5) : [];

            if (albums.length === 0 && topTracks.length === 0) {
                this.displayMessage('No albums or top tracks found for this artist');
                return;
            }

            const artistName = artistData.name || 'Artist';
            const artistPictureUrl = artistData.picture || null;
            this.exploreArtistName = artistName;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);

            // Display artist hero with top tracks and albums
            this.resultsContainer.innerHTML = `
                <div class="artist-hero-section">
                    <div class="artist-hero-content">
                        <div class="artist-cover-container">
                            ${artistPictureUrl ? `<img src="${artistPictureUrl}" alt="${this.escapeHtml(artistName)}" class="artist-cover">` : '<div class="artist-cover-placeholder"></div>'}
                        </div>
                        <div class="artist-info">
                            <h1 class="artist-hero-name">${this.escapeHtml(artistName)}</h1>
                            ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                        </div>
                    </div>
                    <div class="artist-actions">
                        <button class="album-action-btn primary" id="artistPlayBtn" title="Play artist" ${topTracks.length === 0 && albums.length === 0 ? 'disabled' : ''}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>
                        </button>
                        <button class="album-action-btn hero-bottom-right" id="findSimilarArtistBtn" title="Find similar artists" data-artist-id="${artistId}">
                            ${this.getMoreLikeIconSvg()}
                        </button>
                    </div>
                </div>
                ${topTracks.length > 0 ? `
                    <div class="results-header">
                        <div class="results-header-top">
                            <h2>Top Tracks</h2>
                        </div>
                    </div>
                    ${this.formatTracksGrid(topTracks, undefined, false)}
                ` : ''}
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>Albums</h2>
                    </div>
                </div>
                ${this.renderAlbumGrid(albums, { viewMode: 'artist-albums', hideArtist: true })}
            `;

            // Attach event listener to play button
            const playBtn = document.getElementById('artistPlayBtn') as HTMLButtonElement;
            if (playBtn) {
                playBtn.addEventListener('click', async () => {
                    if (topTracks.length > 0) {
                        void this.handlePlayToggle(topTracks[0].id, undefined as any, playBtn);
                        return;
                    }

                    // Fallback to the first track from the first album when no top tracks are available.
                    if (albums.length > 0) {
                        const firstAlbumId = albums[0].id;
                        try {
                            const response = await fetch(`/api/hifi/albums/${encodeURIComponent(String(firstAlbumId))}`, {
                                signal: this.pendingRequestController?.signal
                            });
                            if (!response.ok) {
                                throw new Error('Failed to fetch album');
                            }
                            const albumData: AlbumInfo = await response.json();
                            const trackItems = albumData.data?.items || [];
                            const tracks = trackItems.filter(item => item.type === 'track').map(item => item.item);
                            if (tracks.length > 0) {
                                void this.handlePlayToggle(tracks[0].id, undefined as any, playBtn);
                            }
                        } catch (error) {
                            console.error('Error playing artist:', error);
                        }
                    }
                });
            }

            const findSimilarArtistBtn = document.getElementById('findSimilarArtistBtn') as HTMLButtonElement;
            if (findSimilarArtistBtn) {
                findSimilarArtistBtn.addEventListener('click', () => {
                    void this.navigateToRoute({ view: 'similar_artists', artistId }, true);
                });
            }

            // Annotate with Plex status
            void this.annotateAlbumGridsWithPlexStatus(albums);
            void this.annotateArtistHeroWithPlexStatus(artistId);
        } catch (error) {
            this.displayMessage('Error loading artist albums. Please try again.', () => this.fetchArtistAlbums(artistId));
            console.error('Artist fetch error:', error);
        }
    }

    private async fetchAlbumTracks(albumId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'album';
        this.currentExploreRoute = { view: 'album', albumId };
        this.exploreAlbumTitle = null;
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'album', albumId });
        }
        this.stopPlayback();
        this.displayMessage('Loading album tracks...');

        try {
            const response = await fetch(`/api/hifi/albums/${encodeURIComponent(String(albumId))}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }

            const data: AlbumObjectResponse = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchAlbumTracks(albumId));
                return;
            }

            const albumData = data.album;
            if (!albumData) {
                this.displayMessage('No album data found');
                return;
            }

            const tracks = albumData.tracks || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this album');
                return;
            }

            // Calculate numberOfVolumes by finding unique volumeNumbers
            const volumeNumbers = new Set<number>();
            tracks.forEach(track => {
                if (track.volumeNumber !== undefined && track.volumeNumber !== null) {
                    volumeNumbers.add(track.volumeNumber);
                }
            });
            const numberOfVolumes = volumeNumbers.size > 0 ? volumeNumbers.size : 1;

            this.updatePlexPlaylistContainerVisibility(true);

            // Get album info for display
            const albumTitle = albumData.title || 'Album';
            this.exploreAlbumTitle = albumTitle;
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            const artistNames = albumData.artists && albumData.artists.length > 0
                ? albumData.artists.map(a => a.name).join(', ')
                : albumData.artist?.name || 'Unknown Artist';
            const primaryArtistId = albumData.artists?.[0]?.id || albumData.artist?.id;

            // Calculate total duration
            const totalDurationSeconds = tracks.reduce((sum, track) => {
                return sum + (track.duration || 0);
            }, 0);
            const totalDurationMinutes = Math.floor(totalDurationSeconds / 60);
            const totalDurationHours = Math.floor(totalDurationMinutes / 60);
            const remainingMinutes = totalDurationMinutes % 60;
            const durationStr = totalDurationHours > 0
                ? `${totalDurationHours}h ${remainingMinutes}m`
                : `${totalDurationMinutes}m`;

            const releaseDate = albumData.releaseDate
                ? new Date(albumData.releaseDate).getFullYear()
                : '';

            const albumIsExplicit = Boolean(
                albumData.explicit ||
                albumData.mediaMetadata?.tags?.includes('EXPLICIT') ||
                tracks.some(track => track.explicit)
            );

            const coverArt = albumData.cover
                ? this.getHifiImageUrl(albumData.cover, 1280)
                : '';

            // Display tracks with TIDAL-style album header
            this.resultsContainer.innerHTML = `
                <div class="album-hero-section">
                    <div class="album-hero-content">
                        <div class="album-cover-container">
                            ${coverArt ? `<img src="${coverArt}" alt="${this.escapeHtml(albumTitle)}" class="album-cover">` : '<div class="album-cover-placeholder"></div>'}
                        </div>
                        <div class="album-info">
                            <h1 class="album-title">
                                ${this.escapeHtml(albumTitle)}
                                ${albumIsExplicit ? `<span class="explicit-badge" title="Explicit content">E</span>` : ''}
                            </h1>
                            <p class="album-artist">
                                <span class="track-artist-name" ${primaryArtistId ? `data-artist-id="${primaryArtistId}" title="View albums by ${this.escapeHtml(artistNames)}"` : ''}>${this.escapeHtml(artistNames)}</span>
                            </p>
                            <div class="album-metadata">
                                ${releaseDate ? `<span class="metadata-item">${releaseDate}</span>` : ''}
                                <span class="metadata-item">${tracks.length} ${tracks.length === 1 ? 'track' : 'tracks'}</span>
                                <span class="metadata-item">${durationStr}</span>
                            </div>
                            ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                        </div>
                    </div>
                    <div class="album-actions">
                        <button class="album-action-btn primary" id="albumPlayBtn" title="Play album">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>
                        </button>
                        <button class="album-action-btn" id="findSimilarAlbumBtn" title="Find similar albums" data-album-id="${albumId}">
                            ${this.getMoreLikeIconSvg()}
                        </button>
                        <button class="album-action-btn" id="addAllPlaylistBtn" title="Add all tracks to a playlist">
                            ${this.getAddAllPlaylistIconSvg()}
                        </button>
                        <button class="album-action-btn" id="addAllLibraryBtn" title="Add all tracks to library">
                            ${this.getAddAllLibraryIconSvg()}
                        </button>
                    </div>
                </div>
                <div class="results-list">
                    ${this.formatTracksGrid(tracks, numberOfVolumes)}
                </div>
            `;
            // Attach event listeners to action buttons
            const addPlaylistBtn = document.getElementById('addAllPlaylistBtn') as HTMLButtonElement;
            if (addPlaylistBtn) {
                addPlaylistBtn.addEventListener('click', () => this.addAllToPlaylist());
            }

            const addLibraryBtn = document.getElementById('addAllLibraryBtn') as HTMLButtonElement;
            if (addLibraryBtn) {
                addLibraryBtn.addEventListener('click', () => this.addAllToLibrary());
            }

            const findSimilarBtn = document.getElementById('findSimilarAlbumBtn') as HTMLButtonElement;
            if (findSimilarBtn) {
                findSimilarBtn.addEventListener('click', () => {
                    void this.navigateToRoute({ view: 'similar_albums', albumId }, true);
                });
            }

            const playBtn = document.getElementById('albumPlayBtn') as HTMLButtonElement;
            if (playBtn) {
                playBtn.addEventListener('click', () => {
                    // Play the first track from the album
                    if (tracks.length > 0) {
                        void this.handlePlayToggle(tracks[0].id, undefined as any, playBtn);
                    }
                });
            }

            this.movePlexPlaylistContainerBeneathDownloadAll();

            void this.annotateTrackCardsWithPlexStatus(tracks);
            void this.annotateAlbumHeroWithPlexStatus(albumId);
        } catch (error) {
            this.displayMessage('Error loading album tracks. Please try again.', () => this.fetchAlbumTracks(albumId));
            console.error('Album fetch error:', error);
        }
    }

    private async fetchAlbumObject(albumId: number): Promise<AlbumObject> {
        const response = await fetch(`/api/hifi/albums/${encodeURIComponent(String(albumId))}`);
        if (!response.ok) {
            throw new Error('Failed to fetch album');
        }

        const data: AlbumObjectResponse = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        if (!data.album) {
            throw new Error('No album data found');
        }

        return data.album;
    }

    private async fetchSimilarTracks(trackId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'similar_tracks', trackId };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_tracks', trackId });
        }
        this.stopPlayback();
        this.displayMessage('Loading track recommendations...');

        try {
            const response = await fetch(`/api/hifi/tracks/${encodeURIComponent(String(trackId))}/similar`, {
                signal: this.pendingRequestController?.signal
            });
            if (!response.ok) {
                throw new Error('Failed to fetch recommendations');
            }

            const data: any = await response.json();
            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchSimilarTracks(trackId));
                return;
            }

            const recommendationItems = Array.isArray(data?.data?.items) ? data.data.items : [];
            const tracks = recommendationItems
                .map((item: any) => item?.track || item?.item || item)
                .filter((track: any) => track && typeof track === 'object' && 'id' in track && 'title' in track) as Track[];

            if (tracks.length === 0) {
                this.displayMessage('No recommendations found for this track');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>More Like This - Similar Tracks</h2>
                    </div>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                </div>
                <div class="results-list">
                    ${this.formatTracksGrid(tracks)}
                </div>
            `;

            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement | null;
            if (resultsHeaderTop) {
                const buttonsContainer = document.createElement('div');
                buttonsContainer.className = 'add-all-buttons-container';
                const addPlaylistBtn = document.createElement('button');
                addPlaylistBtn.id = 'addAllPlaylistBtn';
                addPlaylistBtn.className = 'add-all-btn';
                addPlaylistBtn.title = 'Add all tracks to a playlist';
                addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                addPlaylistBtn.addEventListener('click', () => this.addAllToPlaylist());
                buttonsContainer.appendChild(addPlaylistBtn);
                const addLibraryBtn = document.createElement('button');
                addLibraryBtn.id = 'addAllLibraryBtn';
                addLibraryBtn.className = 'add-all-btn';
                addLibraryBtn.title = 'Add all tracks to library';
                addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                addLibraryBtn.addEventListener('click', () => this.addAllToLibrary());
                buttonsContainer.appendChild(addLibraryBtn);
                resultsHeaderTop.appendChild(buttonsContainer);
                this.movePlexPlaylistContainerBeneathDownloadAll();
            }

            void this.annotateTrackCardsWithPlexStatus(tracks);
        } catch (error) {
            this.displayMessage('Error loading recommendations. Please try again.', () => this.fetchSimilarTracks(trackId));
            console.error('Recommendations fetch error:', error);
        }
    }

    private async fetchFreshFindsPlaylist(updateHistory: boolean = true, playlistId?: number): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'fresh_finds', freshFindsPlaylistId: playlistId };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'fresh_finds', freshFindsPlaylistId: playlistId });
        }
        this.stopPlayback();

        if (playlistId) {
            await this.renderFreshFindsTracks(this.getSelectedPlexUserId() || '', playlistId);
            return;
        }

        this.displayMessage('Loading Fresh Finds...');

        const userId = this.getSelectedPlexUserId();
        if (!userId) {
            this.displayMessage('Not enough listen history to generate recommendations');
            return;
        }

        try {
            const playlistsResponse = await fetch(`/api/recommendations/playlists?user_id=${encodeURIComponent(userId)}`);
            if (!playlistsResponse.ok) {
                throw new Error('Failed to check playlists');
            }
            const playlistsData = await playlistsResponse.json();
            const hasHistory = playlistsData.has_history as boolean;
            const playlists = Array.isArray(playlistsData.playlists) ? playlistsData.playlists : [];
            const existing = playlists.find((p: any) => p.slug === 'fresh-finds');

            if (!hasHistory) {
                this.displayMessage('Not enough listen history to generate recommendations');
                return;
            }

            if (existing) {
                const generatedAt = new Date(existing.generated_at);
                const hoursSince = (Date.now() - generatedAt.getTime()) / (1000 * 60 * 60);
                if (hoursSince > 24) {
                    void this.triggerFreshFindsGeneration(userId);
                }
                await this.renderFreshFindsTracks(userId);
            } else {
                await this.triggerFreshFindsGeneration(userId);
            }
        } catch (error) {
            this.displayMessage('Error loading Fresh Finds. Please try again.', () => this.fetchFreshFindsPlaylist());
            console.error('Fresh Finds fetch error:', error);
        }
    }

    private async triggerFreshFindsGeneration(userId: string): Promise<void> {
        try {
            const response = await fetch('/api/recommendations/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ slug: 'fresh-finds', user_id: userId })
            });
            if (!response.ok) {
                const data = await response.json();
                if (response.status === 409) {
                    await this.pollForFreshFindsCompletion(userId);
                    return;
                }
                throw new Error(data.error || 'Failed to start generation');
            }
            await this.pollForFreshFindsCompletion(userId);
        } catch (error) {
            console.error('Fresh Finds generation error:', error);
        }
    }

    private async pollForFreshFindsCompletion(userId: string): Promise<void> {
        const poll = async (): Promise<void> => {
            try {
                const response = await fetch(`/api/jobs?jobs_filter=incomplete&exclude_bulk_playlist_add=0`);
                if (!response.ok) throw new Error('Failed to check job status');
                const data = await response.json();
                const jobs = Array.isArray(data.jobs) ? data.jobs : [];
                const activeJob = jobs.find((j: any) => j.job_type === 'generate_recommendations' && (j.status === 'queued' || j.status === 'in_progress'));
                if (activeJob) {
                    this.renderFreshFindsProgress(activeJob);
                    setTimeout(poll, 3000);
                } else {
                    await this.renderFreshFindsTracks(userId);
                }
            } catch {
                setTimeout(poll, 3000);
            }
        };
        await poll();
    }

    private renderFreshFindsProgress(job: any): void {
        const stages = (job.result?.stages || {}) as Record<string, string>;
        const progress = (job.result?.progress || {}) as Record<string, number>;
        const stageList = [
            { key: 'syncing_listen_history', label: 'Syncing Listen History' },
            { key: 'gathering_seeds', label: 'Gathering Seeds' },
            { key: 'fetching_recommendations', label: 'Fetching Recommendations' },
            { key: 'processing_tracks', label: 'Processing Tracks' },
            { key: 'saving_playlist', label: 'Saving Playlist' }
        ];

        const statusLabel = job.status === 'queued' ? 'Queued' : 'In Progress';
        const seedsFound = progress.seeds_found || 0;
        const recsFetched = progress.recommendations_fetched || 0;
        const afterFilter = progress.tracks_after_filter || 0;

        const stageHtml = stageList.map(s => {
            const status = stages[s.key] || (job.status === 'succeeded' ? 'done' : 'pending');
            const statusClass = `status-${status}`;
            const label = status.replace('_', ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
            return `
                <div class="job-stage">
                    <span>${s.label}</span>
                    <span class="job-stage-status ${statusClass}">${label}</span>
                </div>
            `;
        }).join('');

        const progressText = seedsFound > 0
            ? `${seedsFound} seeds • ${recsFetched} recommendations fetched • ${afterFilter} after filter`
            : 'Waiting to start...';

        this.resultsContainer.innerHTML = `
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Fresh Finds</h2>
                </div>
            </div>
            <div class="job-item" style="margin-top: 1rem;">
                <div class="job-main">
                    <div class="job-title">Generating Fresh Finds</div>
                    <div class="job-status status-${job.status === 'queued' ? 'queued' : 'in-progress'}">${statusLabel}</div>
                </div>
                <div class="job-sync-progress">${this.escapeHtml(progressText)}</div>
                <div class="job-stages">
                    ${stageHtml}
                </div>
            </div>
        `;
    }

    private async renderFreshFindsTracks(userId: string, playlistId?: number): Promise<void> {
        try {
            let url = `/api/recommendations/fresh-finds?user_id=${encodeURIComponent(userId)}`;
            if (playlistId) {
                url += `&playlist_id=${playlistId}`;
            }
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Failed to fetch Fresh Finds tracks');
            }
            const data = await response.json();
            const tracks = Array.isArray(data.tracks) ? data.tracks as Track[] : [];
            const playlist = data.playlist || {};

            if (tracks.length === 0) {
                this.displayMessage('No new recommendations found. Try again later.');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);
            const playlistName = playlist.name || 'Fresh Finds';
            this.freshFindsPlaylistName = playlistName;
            this.currentExploreRoute = { view: 'fresh_finds', freshFindsPlaylistId: playlistId };
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(playlistName)}</h2>
                    </div>
                </div>
                <div class="results-list">
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            ${this.formatTrackGridHeader(false, true, true)}
                            <div id="freshFindsResultsList">
                                ${tracks.map(track => this.formatTrackGridRow(this.normalizeTrack(track), {
                                    viewMode: 'multi-album',
                                    showTrackNumber: false,
                                    showAlbumColumn: true,
                                    showArtwork: true,
                                })).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement | null;
            if (resultsHeaderTop) {
                const buttonsContainer = document.createElement('div');
                buttonsContainer.className = 'add-all-buttons-container';

                const generatedAt = playlist.generated_at as string | undefined;
                const isToday = this.isPlaylistFromToday(generatedAt);
                if (isToday) {
                    const refreshBtn = document.createElement('button');
                    refreshBtn.id = 'refreshFreshFindsBtn';
                    refreshBtn.className = 'add-all-btn';
                    refreshBtn.title = 'Refresh Fresh Finds';
                    refreshBtn.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <polyline points="1 20 1 14 7 14"></polyline>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                        </svg>
                    `;
                    refreshBtn.addEventListener('click', () => void this.refreshFreshFindsPlaylist(userId));
                    buttonsContainer.appendChild(refreshBtn);
                }

                const addPlaylistBtn = document.createElement('button');
                addPlaylistBtn.id = 'addAllPlaylistBtn';
                addPlaylistBtn.className = 'add-all-btn';
                addPlaylistBtn.title = 'Add all tracks to a playlist';
                addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                addPlaylistBtn.addEventListener('click', () => this.addAllToPlaylist());
                buttonsContainer.appendChild(addPlaylistBtn);
                const addLibraryBtn = document.createElement('button');
                addLibraryBtn.id = 'addAllLibraryBtn';
                addLibraryBtn.className = 'add-all-btn';
                addLibraryBtn.title = 'Add all tracks to library';
                addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                addLibraryBtn.addEventListener('click', () => this.addAllToLibrary());
                buttonsContainer.appendChild(addLibraryBtn);
                resultsHeaderTop.appendChild(buttonsContainer);
                this.movePlexPlaylistContainerBeneathDownloadAll();
            }

            void this.annotateTrackCardsWithPlexStatus(tracks);
        } catch (error) {
            this.displayMessage('Error loading Fresh Finds tracks. Please try again.', () => this.fetchFreshFindsPlaylist());
            console.error('Fresh Finds tracks fetch error:', error);
        }
    }

    private async refreshFreshFindsPlaylist(userId: string): Promise<void> {
        this.stopPlayback();
        this.resultsContainer.innerHTML = `
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Fresh Finds</h2>
                </div>
            </div>
            <div class="job-item" style="margin-top: 1rem;">
                <div class="job-main">
                    <div class="job-title">Generating Fresh Finds</div>
                    <div class="job-status status-in-progress">Starting...</div>
                </div>
            </div>
        `;
        await this.triggerFreshFindsGeneration(userId);
        await this.renderFreshFindsTracks(userId);
    }

    private async fetchSimilarAlbums(albumId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'similar_albums', albumId };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_albums', albumId });
        }
        this.stopPlayback();
        this.displayMessage('Loading similar albums...');

        try {
            const response = await fetch(`/api/hifi/albums/${encodeURIComponent(String(albumId))}/similar`, {
                signal: this.pendingRequestController?.signal
            });
            if (!response.ok) {
                throw new Error('Failed to fetch similar albums');
            }

            const data: any = await response.json();
            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchSimilarAlbums(albumId));
                return;
            }

            const albums = Array.isArray(data?.albums) ? data.albums : [];
            if (albums.length === 0) {
                this.displayMessage('No similar albums found');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <h2>More Like This - Similar Albums</h2>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                </div>
                ${this.renderAlbumGrid(albums, { viewMode: 'similar-albums' })}
            `;

            // Annotate with Plex status
            void this.annotateAlbumGridsWithPlexStatus(albums);
        } catch (error) {
            this.displayMessage('Error loading similar albums. Please try again.', () => this.fetchSimilarAlbums(albumId));
            console.error('Similar albums fetch error:', error);
        }
    }

    private async fetchSimilarArtists(artistId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'similar_artists', artistId };
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_artists', artistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading similar artists...');

        try {
            const response = await fetch(`/api/hifi/artists/${encodeURIComponent(String(artistId))}/similar`, {
                signal: this.pendingRequestController?.signal
            });
            if (!response.ok) {
                throw new Error('Failed to fetch similar artists');
            }

            const data: any = await response.json();
            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchSimilarArtists(artistId));
                return;
            }

            const artists = Array.isArray(data?.artists) ? data.artists : [];
            if (artists.length === 0) {
                this.displayMessage('No similar artists found');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <h2>More Like This - Similar Artists</h2>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                </div>
                <div class="results-list artist-results">
                    ${artists.map((artist: ArtistSearchItem) => this.formatArtistCard(artist)).join('')}
                </div>
            `;
        } catch (error) {
            this.displayMessage('Error loading similar artists. Please try again.', () => this.fetchSimilarArtists(artistId));
            console.error('Similar artists fetch error:', error);
        }
    }

    private async withRedownloadContext(
        chip: HTMLElement,
        message: string,
        action: () => Promise<void>
    ): Promise<void> {
        if (!window.confirm(message)) {
            return;
        }

        const originalContent = chip.textContent;
        const originalClassName = chip.className;
        const originalTitle = chip.title;

        chip.innerHTML = this.getSpinnerIconSvg();
        chip.title = 'Re-downloading...';

        const originalIgnoreMatches = this.downloadSettings.ignoreMatches;
        this.downloadSettings.ignoreMatches = true;

        const restoreChip = (): void => {
            chip.textContent = originalContent || 'In Plex';
            chip.className = originalClassName;
            chip.title = originalTitle;
        };

        try {
            await action();
        } catch (error) {
            console.error('[RE-DOWNLOAD] Error:', error);
            restoreChip();
            throw error;
        } finally {
            this.downloadSettings.ignoreMatches = originalIgnoreMatches;
        }
    }

    private async handleRedownloadTrack(
        trackId: number,
        trackRow: HTMLElement,
        chip: HTMLElement
    ): Promise<void> {
        console.log(`[RE-DOWNLOAD] Re-downloading track ${trackId}`);

        await this.withRedownloadContext(chip, 'This track is already in your Plex library. Re-download it?', async () => {
            const jobId = await this.downloadTrackToLibrary(trackId, 'loose');
            console.log(`[RE-DOWNLOAD] Job queued: ${jobId}`);

            chip.innerHTML = this.getSpinnerIconSvg();
            chip.classList.add('plex-existing-chip--downloading');

            const pollJob = async (): Promise<void> => {
                try {
                    const resp = await fetch(`/api/jobs/${jobId}`);
                    if (!resp.ok) {
                        chip.textContent = 'In Plex';
                        chip.className = chip.className.replace('plex-existing-chip--downloading', '').trim();
                        return;
                    }
                    const job = await resp.json();
                    if (job.status === 'succeeded') {
                        chip.textContent = 'In Plex';
                        chip.className = chip.className.replace('plex-existing-chip--downloading', '').trim();
                        chip.title = 'Re-downloaded successfully';
                    } else if (job.status === 'failed') {
                        chip.textContent = 'Failed';
                        chip.className = chip.className.replace('plex-existing-chip--downloading', '').trim();
                        chip.title = 'Re-download failed';
                    } else {
                        setTimeout(pollJob, 2000);
                    }
                } catch {
                    chip.textContent = 'In Plex';
                    chip.className = chip.className.replace('plex-existing-chip--downloading', '').trim();
                }
            };

            setTimeout(pollJob, 2000);
        });
    }

    private async handleRedownloadAlbum(
        albumId: number,
        albumRow: HTMLElement,
        chip: HTMLElement
    ): Promise<void> {
        console.log(`[RE-DOWNLOAD] Re-downloading album ${albumId}`);

        try {
            await this.withRedownloadContext(chip, 'This album is already in your Plex library. Re-download it?', async () => {
                const albumData = await this.fetchAlbumObject(albumId);
                const tracks = albumData.tracks || [];

                if (tracks.length === 0) {
                    this.displayMessage('No tracks found in this album');
                    throw new Error('No tracks found');
                }

                const jobIds: number[] = [];
                for (const track of tracks) {
                    try {
                        const jobId = await this.downloadTrackToLibrary(track.id, 'album');
                        jobIds.push(jobId);
                    } catch (error) {
                        console.error(`[RE-DOWNLOAD] Failed to queue track ${track.id}:`, error);
                    }
                }

                if (jobIds.length === 0) {
                    throw new Error('No jobs were queued');
                }

                console.log(`[RE-DOWNLOAD] Queued ${jobIds.length} tracks`);
                chip.textContent = 'In Plex';
                chip.title = `Re-downloading ${jobIds.length} tracks...`;
            });
        } catch {
            this.displayMessage('Error re-downloading album. Please try again.');
        }
    }

    private async handleDownload(
        trackId: number,
        trackCard: HTMLElement,
        downloadType: 'album' | 'loose' = 'loose'
    ): Promise<void> {
        const downloadBtn = trackCard.querySelector('.grid-add-library-btn') as HTMLButtonElement;
        if (!downloadBtn) {
            console.error('[DOWNLOAD] Download button not found');
            return;
        }

        console.log(`[DOWNLOAD] Starting download to library for track ${trackId}`);

        const originalContent = downloadBtn.innerHTML;
        const originalDisabled = downloadBtn.disabled;

        if (!downloadBtn.dataset.originalContent) {
            downloadBtn.dataset.originalContent = originalContent;
        }

        downloadBtn.disabled = true;

        try {
            console.log(`[DOWNLOAD] Calling downloadTrackToLibrary with quality: ${this.downloadSettings.quality}`);
            const jobId = await this.downloadTrackToLibrary(trackId, downloadType);
            console.log(`[DOWNLOAD] Job queued successfully: ${jobId}`);

            this.setDownloadButtonQueued(downloadBtn);
            this.registerActiveJob(jobId, trackCard, downloadBtn, downloadBtn);
        } catch (error) {
            console.error('[DOWNLOAD] Download error:', error);
            // Check if this was an abort
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[DOWNLOAD] Download was aborted, restoring button');
                this.restoreDownloadButton(downloadBtn);
            } else {
                // Restore button on error
                downloadBtn.disabled = originalDisabled;
                downloadBtn.innerHTML = originalContent;
                if (downloadBtn.dataset.originalContent) {
                    delete downloadBtn.dataset.originalContent;
                }
            }
        }
    }

    private async handleAddToPlaylist(
        trackId: number,
        trackCard: HTMLElement,
        downloadType: 'album' | 'loose' = 'loose'
    ): Promise<void> {
        const addPlaylistBtn = trackCard.querySelector('.grid-add-playlist-btn') as HTMLButtonElement;
        if (!addPlaylistBtn) {
            console.error('[PLAYLIST] Add to playlist button not found');
            return;
        }

        console.log(`[PLAYLIST] Fetching playlists for track ${trackId}`);

        try {
            const playlists = await this.fetchPlaylists();
            if (!playlists || playlists.length === 0) {
                this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                return;
            }

            await this.showPlaylistSelector(playlists, trackId, trackCard, downloadType);
        } catch (error) {
            console.error('[PLAYLIST] Error handling add to playlist:', error);
            this.displayMessage('Error fetching playlists. Please try again.');
        }
    }

    private async fetchPlaylists(): Promise<string[]> {
        try {
            const userId = this.getSelectedPlexUserId();
            const queryParam = userId ? `?user_id=${userId}` : '';
            const response = await this.fetchWithRetry(`/api/plex/playlists${queryParam}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            }, 3);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Failed to fetch playlists' }));
                throw new Error(errorData.error || 'Failed to fetch Plex playlists');
            }

            const data = await response.json();
            const playlists = data.playlists || [];
            // Map objects to names if necessary
            return playlists.map((p: any) => typeof p === 'string' ? p : p.name);
        } catch (error) {
            console.error('[PLEX] Error fetching playlists:', error);
            throw error;
        }
    }

    private async showPlaylistSelector(
        playlists: string[],
        trackId: number,
        trackCard: HTMLElement,
        downloadType: 'album' | 'loose'
    ): Promise<void> {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'playlist-modal-overlay';

            const modal = document.createElement('div');
            modal.className = 'playlist-modal';

            // Header
            const header = document.createElement('div');
            header.className = 'playlist-modal-header';
            const title = document.createElement('h3');
            title.textContent = 'Select a Playlist';
            const closeBtn = document.createElement('button');
            closeBtn.className = 'playlist-modal-close';
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', () => {
                overlay.remove();
                resolve();
            });
            header.appendChild(title);
            header.appendChild(closeBtn);

            // Content
            const content = document.createElement('div');
            content.className = 'playlist-modal-content';

            // Existing playlists
            if (playlists.length > 0) {
                playlists.forEach((playlistName: string) => {
                    const button = document.createElement('button');
                    button.className = 'playlist-item-btn';
                    button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg><span>${playlistName}</span>`;
                    button.addEventListener('click', async () => {
                        overlay.remove();
                        await this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType);
                        resolve();
                    });
                    content.appendChild(button);
                });
            }

            // Create new playlist section
            const createSection = document.createElement('div');
            createSection.className = 'playlist-create-section';

            const divider = document.createElement('div');
            divider.className = 'playlist-create-divider';
            divider.textContent = 'or';

            const inputGroup = document.createElement('div');
            inputGroup.className = 'playlist-create-inline-group';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'playlist-create-inline-input';
            input.placeholder = 'New playlist name...';

            const okBtn = document.createElement('button');
            okBtn.className = 'playlist-create-inline-btn';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', async () => {
                const playlistName = input.value.trim();
                if (playlistName) {
                    overlay.remove();
                    await this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType);
                    resolve();
                }
            });

            input.addEventListener('keypress', (e: KeyboardEvent) => {
                if (e.key === 'Enter') {
                    const playlistName = input.value.trim();
                    if (playlistName) {
                        overlay.remove();
                        void this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType);
                        resolve();
                    }
                }
            });

            inputGroup.appendChild(input);
            inputGroup.appendChild(okBtn);

            if (playlists.length > 0) {
                createSection.appendChild(divider);
            }
            createSection.appendChild(inputGroup);
            content.appendChild(createSection);

            // Footer
            const footer = document.createElement('div');
            footer.className = 'playlist-modal-footer';
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'playlist-modal-cancel';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', () => {
                overlay.remove();
                resolve();
            });
            footer.appendChild(cancelBtn);

            modal.appendChild(header);
            modal.appendChild(content);
            modal.appendChild(footer);
            overlay.appendChild(modal);

            overlay.addEventListener('click', (e: Event) => {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve();
                }
            });

            document.body.appendChild(overlay);
            input.focus();
        });
    }

    private async handlePlaylistSelected(
        playlistName: string,
        trackId: number,
        trackCard: HTMLElement,
        downloadType: 'album' | 'loose'
    ): Promise<void> {
        const addPlaylistBtn = trackCard.querySelector('.track-add-playlist-btn') as HTMLButtonElement;
        if (!addPlaylistBtn) {
            console.error('[PLAYLIST] Add to playlist button not found');
            return;
        }

        console.log(`[PLAYLIST] Selected playlist: ${playlistName} for track ${trackId}`);

        const originalContent = addPlaylistBtn.innerHTML;
        const originalDisabled = addPlaylistBtn.disabled;

        if (!addPlaylistBtn.dataset.originalContent) {
            addPlaylistBtn.dataset.originalContent = originalContent;
        }

        addPlaylistBtn.disabled = true;

        try {
            const jobId = await this.downloadTrackWithPlaylist(trackId, downloadType, playlistName);
            console.log(`[PLAYLIST] Job queued successfully: ${jobId}`);

            this.setDownloadButtonQueued(addPlaylistBtn);
            this.registerActiveJob(jobId, trackCard, addPlaylistBtn, addPlaylistBtn);
        } catch (error) {
            console.error('[PLAYLIST] Error downloading with playlist:', error);
            // Restore button on error
            addPlaylistBtn.disabled = originalDisabled;
            addPlaylistBtn.innerHTML = originalContent;
            if (addPlaylistBtn.dataset.originalContent) {
                delete addPlaylistBtn.dataset.originalContent;
            }
            this.displayMessage('Error adding track to playlist. Please try again.');
        }
    }

    private async downloadTrackWithPlaylist(
        trackId: number,
        downloadType: 'album' | 'loose',
        playlistName: string
    ): Promise<number> {
        try {
            console.log(`[PLAYLIST] Sending download with playlist request for track ${trackId}`);
            console.log(`[PLAYLIST] Settings: quality=${this.downloadSettings.quality}`);
            console.log(`[PLAYLIST] Download type: ${downloadType}, Playlist: ${playlistName}`);

            const plexUserId = this.getSelectedPlexUserId();
            const response = await this.fetchWithRetry('/api/downloads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trackId,
                    quality: this.downloadSettings.quality,
                    fileNaming: this.downloadSettings.fileNamingAlbum,
                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                    plex_playlist: playlistName,
                    plex_user_id: plexUserId,
                    ignore_matches: this.downloadSettings.ignoreMatches
                }),
                signal: this.currentDownloadController?.signal
            }, 3);

            console.log(`[PLAYLIST] Response status: ${response.status}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || `HTTP ${response.status}`;
                console.error(`[PLAYLIST] Download failed: ${errorMsg}`);
                throw new Error(errorMsg);
            }

            const data = await response.json();
            console.log(`[PLAYLIST] Server response:`, data);

            if (!data.success) {
                throw new Error(data.error || 'Download failed');
            }

            if (!data.job_id) {
                throw new Error('Download job id missing from response');
            }

            console.log(`[PLAYLIST] Playlist download job queued: ${data.job_id}`);
            return data.job_id as number;
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[PLAYLIST] Download was aborted');
                throw error;
            }
            console.error('[PLAYLIST] Error in downloadTrackWithPlaylist:', error);
            throw error;
        }
    }

    private async handleAddAlbumToPlaylist(albumId: number, albumRow: HTMLElement): Promise<void> {
        const addPlaylistBtn = albumRow.querySelector('.grid-add-playlist-btn') as HTMLButtonElement;
        if (!addPlaylistBtn) {
            console.error('[ALBUM_PLAYLIST] Add to playlist button not found');
            return;
        }

        const originalContent = addPlaylistBtn.innerHTML;
        const originalDisabled = addPlaylistBtn.disabled;

        try {
            const albumData = await this.fetchAlbumObject(albumId);
            const tracks = albumData.tracks || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this album');
                return;
            }

            // Fetch playlists once
            try {
                const playlists = await this.fetchPlaylists();
                if (!playlists || playlists.length === 0) {
                    this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                    return;
                }

                // Show playlist selector and handle selection
                const selectedPlaylist = await this.showPlaylistSelectorForAlbum(playlists, tracks, albumRow, addPlaylistBtn);
                if (!selectedPlaylist) {
                    // User cancelled, restore button
                    addPlaylistBtn.disabled = originalDisabled;
                    addPlaylistBtn.innerHTML = originalContent;
                }
            } catch (error) {
                console.error('[ALBUM_PLAYLIST] Error handling add to playlist:', error);
                addPlaylistBtn.disabled = originalDisabled;
                addPlaylistBtn.innerHTML = originalContent;
                this.displayMessage('Error fetching playlists. Please try again.');
            }
        } catch (error) {
            console.error('[ALBUM_PLAYLIST] Error adding album to playlist:', error);
            addPlaylistBtn.disabled = originalDisabled;
            addPlaylistBtn.innerHTML = originalContent;
            this.displayMessage('Error adding album to playlist. Please try again.');
        }
    }

    private showPlaylistSelectorForAlbum(
        playlists: string[],
        tracks: Track[],
        albumRow: HTMLElement,
        addPlaylistBtn: HTMLButtonElement
    ): Promise<string | null> {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'playlist-modal-overlay';

            const modal = document.createElement('div');
            modal.className = 'playlist-modal';

            // Header
            const header = document.createElement('div');
            header.className = 'playlist-modal-header';
            const title = document.createElement('h3');
            title.textContent = 'Select a Playlist';
            const closeBtn = document.createElement('button');
            closeBtn.className = 'playlist-modal-close';
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', () => {
                overlay.remove();
                resolve(null);
            });
            header.appendChild(title);
            header.appendChild(closeBtn);

            // Content
            const content = document.createElement('div');
            content.className = 'playlist-modal-content';

            // Existing playlists
            if (playlists.length > 0) {
                playlists.forEach((playlistName: string) => {
                    const button = document.createElement('button');
                    button.className = 'playlist-item-btn';
                    button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg><span>${playlistName}</span>`;
                    button.addEventListener('click', async () => {
                        overlay.remove();
                        await this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn);
                        resolve(playlistName);
                    });
                    content.appendChild(button);
                });
            }

            // Create new playlist section
            const createSection = document.createElement('div');
            createSection.className = 'playlist-create-section';

            const divider = document.createElement('div');
            divider.className = 'playlist-create-divider';
            divider.textContent = 'or';

            const inputGroup = document.createElement('div');
            inputGroup.className = 'playlist-create-inline-group';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'playlist-create-inline-input';
            input.placeholder = 'New playlist name...';

            const okBtn = document.createElement('button');
            okBtn.className = 'playlist-create-inline-btn';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', async () => {
                const playlistName = input.value.trim();
                if (playlistName) {
                    overlay.remove();
                    await this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn);
                    resolve(playlistName);
                }
            });

            input.addEventListener('keypress', (e: KeyboardEvent) => {
                if (e.key === 'Enter') {
                    const playlistName = input.value.trim();
                    if (playlistName) {
                        overlay.remove();
                        void this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn);
                        resolve(playlistName);
                    }
                }
            });

            inputGroup.appendChild(input);
            inputGroup.appendChild(okBtn);

            if (playlists.length > 0) {
                createSection.appendChild(divider);
            }
            createSection.appendChild(inputGroup);
            content.appendChild(createSection);

            // Footer
            const footer = document.createElement('div');
            footer.className = 'playlist-modal-footer';
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'playlist-modal-cancel';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', () => {
                overlay.remove();
                resolve(null);
            });
            footer.appendChild(cancelBtn);

            modal.appendChild(header);
            modal.appendChild(content);
            modal.appendChild(footer);
            overlay.appendChild(modal);

            overlay.addEventListener('click', (e: Event) => {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve(null);
                }
            });

            document.body.appendChild(overlay);
            input.focus();
        });
    }

    private async handlePlaylistSelectedForAlbum(
        playlistName: string,
        tracks: Track[],
        albumRow: HTMLElement,
        addPlaylistBtn: HTMLButtonElement
    ): Promise<void> {
        const originalContent = addPlaylistBtn.innerHTML;
        const originalDisabled = addPlaylistBtn.disabled;

        // Show spinner on button
        this.setDownloadButtonQueued(addPlaylistBtn);

        try {
            const jobIds: number[] = [];

            // Queue all tracks for adding to playlist
            for (const track of tracks) {
                try {
                    const jobId = await this.downloadTrackWithPlaylist(track.id, 'album', playlistName);
                    jobIds.push(jobId);
                } catch (error) {
                    console.error(`[PLAYLIST] Failed to queue track ${track.id}:`, error);
                    // Continue with next track
                }
            }

            if (jobIds.length === 0) {
                throw new Error('No jobs were queued');
            }

            console.log(`[PLAYLIST] Queued ${jobIds.length} tracks to playlist: ${playlistName}`);

            // Register all jobs for polling, but track them all under the button
            // We'll monitor the first one for now and mark success when all are done
            jobIds.forEach((jobId, index) => {
                if (index === 0) {
                    // Register first job with the button for visual feedback
                    this.registerActiveJob(jobId, albumRow, addPlaylistBtn, addPlaylistBtn);
                } else {
                    // Register other jobs but don't update button - they're tracked internally
                    this.activeJobMap.set(jobId, { trackCard: albumRow, downloadBtn: addPlaylistBtn, statusEl: addPlaylistBtn });
                }
            }
            );
            this.startJobStatusPolling();
        } catch (error) {
            console.error('[PLAYLIST] Error adding tracks to playlist:', error);
            addPlaylistBtn.disabled = originalDisabled;
            addPlaylistBtn.innerHTML = originalContent;
            this.setDownloadButtonFailed(addPlaylistBtn);
            this.displayMessage('Error adding album to playlist. Please try again.');
        }
    }

    private async handleDownloadAlbum(albumId: number, albumRow: HTMLElement): Promise<void> {
        const addLibraryBtn = albumRow.querySelector('.grid-add-library-btn') as HTMLButtonElement;
        if (!addLibraryBtn) {
            console.error('[ALBUM_DOWNLOAD] Add to library button not found');
            return;
        }

        const originalContent = addLibraryBtn.innerHTML;
        const originalDisabled = addLibraryBtn.disabled;

        try {
            const albumData = await this.fetchAlbumObject(albumId);
            const tracks = albumData.tracks || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this album');
                return;
            }

            // Show spinner on button
            this.setDownloadButtonQueued(addLibraryBtn);

            const jobIds: number[] = [];

            // Queue all tracks for download to library
            for (const track of tracks) {
                try {
                    const jobId = await this.downloadTrackToLibrary(track.id, 'album');
                    jobIds.push(jobId);
                } catch (error) {
                    console.error(`[ALBUM_DOWNLOAD] Failed to queue track ${track.id}:`, error);
                    // Continue with next track
                }
            }

            if (jobIds.length === 0) {
                throw new Error('No jobs were queued');
            }

            console.log(`[ALBUM_DOWNLOAD] Queued ${jobIds.length} tracks to library`);

            // Register all jobs for polling, tracking them all under the button
            jobIds.forEach((jobId, index) => {
                if (index === 0) {
                    // Register first job with the button for visual feedback
                    this.registerActiveJob(jobId, albumRow, addLibraryBtn, addLibraryBtn);
                } else {
                    // Register other jobs but don't update button - they're tracked internally
                    this.activeJobMap.set(jobId, { trackCard: albumRow, downloadBtn: addLibraryBtn, statusEl: addLibraryBtn });
                }
            });
            this.startJobStatusPolling();
        } catch (error) {
            console.error('[ALBUM_DOWNLOAD] Error downloading album to library:', error);
            addLibraryBtn.disabled = originalDisabled;
            addLibraryBtn.innerHTML = originalContent;
            this.setDownloadButtonFailed(addLibraryBtn);
            this.displayMessage('Error adding album to library. Please try again.');
        }
    }

    private async handlePlayAlbum(albumId: number, playButton: HTMLButtonElement): Promise<void> {
        try {
            const albumData = await this.fetchAlbumObject(albumId);
            const tracks = albumData.tracks || [];

            if (tracks.length === 0) {
                this.displayMessage('No tracks found in this album');
                return;
            }

            // Play the first track from the album
            const albumRow = playButton.closest('.albums-grid-row') as HTMLElement;
            void this.handlePlayToggle(tracks[0].id, albumRow, playButton);
        } catch (error) {
            console.error('[ALBUM_PLAYBACK] Error playing album:', error);
            this.displayMessage('Error playing album. Please try again.');
        }
    }

    private async handlePlayLibraryAlbum(albumId: string, playButton: HTMLButtonElement): Promise<void> {
        try {
            const params = new URLSearchParams();
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/library/albums/${encodeURIComponent(albumId)}/tracks?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Failed to fetch Plex album tracks');
            }

            const data = await response.json().catch(() => ({} as PlexLibraryAlbumTracksResponse));
            const tracks = Array.isArray(data.tracks) ? data.tracks : [];
            if (tracks.length === 0 || !tracks[0].id) {
                this.displayMessage('No tracks found in this album');
                return;
            }

            void this.handlePlayLibraryToggle(tracks[0].id, playButton);
        } catch (error) {
            console.error('[ALBUM_PLAYBACK] Error playing Plex library album:', error);
            this.displayMessage('Error playing album. Please try again.');
        }
    }

    private async handlePlayLibraryArtist(artistId: string, playButton: HTMLButtonElement): Promise<void> {
        try {
            const params = new URLSearchParams();
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/plex/library/artists/${encodeURIComponent(artistId)}/albums?${params.toString()}`);
            if (!response.ok) {
                throw new Error('Failed to fetch Plex artist albums');
            }

            const data = await response.json().catch(() => ({} as PlexLibraryArtistAlbumsResponse));
            const albums = Array.isArray(data.albums) ? data.albums : [];
            if (albums.length === 0 || !albums[0].id) {
                this.displayMessage('No albums found for this artist');
                return;
            }

            await this.handlePlayLibraryAlbum(albums[0].id, playButton);
        } catch (error) {
            console.error('[ARTIST_PLAYBACK] Error playing Plex library artist:', error);
            this.displayMessage('Error playing artist. Please try again.');
        }
    }

    private async downloadTrackToLibrary(
        trackId: number,
        downloadType: 'album' | 'loose'
    ): Promise<number> {
        try {
            console.log(`[DOWNLOAD] Sending download-to-library request for track ${trackId}`);
            console.log(`[DOWNLOAD] Settings: quality=${this.downloadSettings.quality}`);
            console.log(`[DOWNLOAD] Download type: ${downloadType}`);

            const response = await this.fetchWithRetry('/api/downloads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trackId,
                    quality: this.downloadSettings.quality,
                    fileNaming: this.downloadSettings.fileNamingAlbum,
                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                    ignore_matches: this.downloadSettings.ignoreMatches
                }),
                signal: this.currentDownloadController?.signal
            }, 3);

            console.log(`[DOWNLOAD] Response status: ${response.status}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || `HTTP ${response.status}`;
                console.error(`[DOWNLOAD] Download failed: ${errorMsg}`);
                throw new Error(errorMsg);
            }

            // Parse the JSON response
            const data = await response.json();
            console.log(`[DOWNLOAD] Server response:`, data);

            if (!data.success) {
                throw new Error(data.error || 'Download failed');
            }

            if (!data.job_id) {
                throw new Error('Download job id missing from response');
            }

            console.log(`[DOWNLOAD] Library download job queued: ${data.job_id}`);
            return data.job_id as number;
        } catch (error) {
            // Check if error is due to abort
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[DOWNLOAD] Download was aborted');
                throw error;
            }
            console.error('[DOWNLOAD] Error in downloadTrackToLibrary:', error);
            throw error;
        }
    }

    private async downloadTrack(
        trackId: number,
        downloadType: 'album' | 'loose',
        plexPlaylistName: string | null
    ): Promise<number> {
        try {
            console.log(`[DOWNLOAD] Sending download request for track ${trackId}`);
            console.log(`[DOWNLOAD] Settings: quality=${this.downloadSettings.quality}`);
            console.log(`[DOWNLOAD] Download type: ${downloadType}`);

            const plexUserId = this.getSelectedPlexUserId();
            const response = await this.fetchWithRetry('/api/downloads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trackId,
                    quality: this.downloadSettings.quality,
                    fileNaming: this.downloadSettings.fileNamingAlbum,
                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                    plex_playlist: plexPlaylistName,
                    plex_user_id: plexUserId,
                    ignore_matches: this.downloadSettings.ignoreMatches
                }),
                signal: this.currentDownloadController?.signal
            }, 3);

            console.log(`[DOWNLOAD] Response status: ${response.status}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || `HTTP ${response.status}`;
                console.error(`[DOWNLOAD] Download failed: ${errorMsg}`);
                throw new Error(errorMsg);
            }

            // Parse the JSON response
            const data = await response.json();
            console.log(`[DOWNLOAD] Server response:`, data);

            if (!data.success) {
                throw new Error(data.error || 'Download failed');
            }

            if (!data.job_id) {
                throw new Error('Download job id missing from response');
            }

            console.log(`[DOWNLOAD] Job queued: ${data.job_id}`);
            return data.job_id as number;
        } catch (error) {
            // Check if error is due to abort
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[DOWNLOAD] Download was aborted');
                throw error;
            }
            console.error('[DOWNLOAD] Error in downloadTrack:', error);
            throw error;
        }
    }

    private restoreDownloadButton(downloadBtn: HTMLButtonElement): void {
        downloadBtn.disabled = false;
        downloadBtn.classList.remove('completed');
        if (downloadBtn.dataset.originalContent) {
            downloadBtn.innerHTML = downloadBtn.dataset.originalContent;
            delete downloadBtn.dataset.originalContent;
        } else {
            // Fallback: recreate the archive icon
            downloadBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2" y="3" width="20" height="5" rx="1"></rect>
                    <path d="M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path>
                    <rect x="8" y="12" width="8" height="1"></rect>
                </svg>
            `;
        }
    }

    private setJobStatusIcon(downloadBtn: HTMLButtonElement, status: string): void {
        const effectiveStatus = status.replace('_', '-');
        downloadBtn.classList.remove('queued', 'in-progress', 'completed', 'failed');
        downloadBtn.classList.add(effectiveStatus);

        if (effectiveStatus === 'queued' || effectiveStatus === 'in-progress') {
            downloadBtn.innerHTML = this.getSpinnerIconSvg();
        } else if (effectiveStatus === 'succeeded' || effectiveStatus === 'completed-with-errors') {
            downloadBtn.innerHTML = this.getCheckmarkIconSvg();
        } else if (effectiveStatus === 'failed') {
            downloadBtn.innerHTML = this.getExclamationIconSvg();
            downloadBtn.disabled = false;
        }
    }

    private registerActiveJob(
        jobId: number,
        trackCard: HTMLElement,
        downloadBtn: HTMLButtonElement,
        statusEl: HTMLButtonElement
    ): void {
        this.activeJobMap.set(jobId, { trackCard, downloadBtn, statusEl });
        this.startJobStatusPolling();
    }

    private startJobStatusPolling(): void {
        if (this.jobStatusInterval) {
            return;
        }

        this.jobStatusInterval = window.setInterval(() => {
            void this.pollActiveJobs();
        }, 4000);
    }

    private stopJobStatusPolling(): void {
        if (this.jobStatusInterval && this.activeJobMap.size === 0) {
            window.clearInterval(this.jobStatusInterval);
            this.jobStatusInterval = null;
        }
    }

    private async pollActiveJobs(): Promise<void> {
        if (this.jobStatusPolling) {
            return;
        }

        if (this.activeJobMap.size === 0) {
            this.stopJobStatusPolling();
            return;
        }

        this.jobStatusPolling = true;
        const entries = Array.from(this.activeJobMap.entries());

        try {
            await Promise.all(entries.map(async ([jobId, context]) => {
                try {
                    const response = await fetch(`/api/jobs/${jobId}`);
                    if (!response.ok) {
                        return;
                    }
                    const job = await response.json() as JobItem;
                    this.updateJobStatusForCard(job, context);
                } catch (error) {
                    console.warn('Job status fetch failed:', error);
                }
            }));
        } finally {
            this.jobStatusPolling = false;
            this.stopJobStatusPolling();
        }
    }

    private updateJobStatusForCard(
        job: JobItem,
        context: { trackCard: HTMLElement; downloadBtn: HTMLButtonElement; statusEl: HTMLButtonElement }
    ): void {
        const effectiveStatus = this.getEffectiveJobStatus(job);
        this.setJobStatusIcon(context.downloadBtn, effectiveStatus);

        if (effectiveStatus === 'succeeded' || effectiveStatus === 'completed_with_errors') {
            this.setDownloadButtonCompleted(context.downloadBtn);
            context.downloadBtn.disabled = true;
            this.activeJobMap.delete(job.id);
            return;
        }

        if (effectiveStatus === 'failed' || effectiveStatus === 'cancelled') {
            this.restoreDownloadButton(context.downloadBtn);
            this.activeJobMap.delete(job.id);
            return;
        }

        if (job.status === 'succeeded') {
            this.setDownloadButtonCompleted(context.downloadBtn);
            context.downloadBtn.disabled = true;
            this.activeJobMap.delete(job.id);
            return;
        }

        context.downloadBtn.disabled = true;
    }

    private setDownloadButtonCompleted(downloadBtn: HTMLButtonElement): void {
        downloadBtn.disabled = true;
        downloadBtn.classList.add('completed');
        downloadBtn.innerHTML = this.getCheckmarkIconSvg();
    }

    private setDownloadButtonQueued(downloadBtn: HTMLButtonElement): void {
        downloadBtn.disabled = true;
        downloadBtn.classList.add('queued');
        downloadBtn.innerHTML = this.getSpinnerIconSvg();
    }

    private setDownloadButtonFailed(downloadBtn: HTMLButtonElement): void {
        downloadBtn.disabled = false;
        downloadBtn.classList.add('failed');
        downloadBtn.innerHTML = this.getExclamationIconSvg();
    }

    private async downloadAllTracks(): Promise<void> {
        if (this.isDownloadingAll) {
            // Cancel the download all process immediately
            this.downloadAllCancelRequested = true;
            // Abort the current download
            if (this.currentDownloadController) {
                this.currentDownloadController.abort();
            }
            return;
        }

        this.isDownloadingAll = true;
        this.downloadAllCancelRequested = false;

        const downloadAllBtn = document.getElementById('downloadAllBtn') as HTMLButtonElement;
        if (downloadAllBtn) {
            downloadAllBtn.textContent = 'Cancel';
            downloadAllBtn.classList.add('cancelling');
            downloadAllBtn.disabled = false;
        }

        const trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]')) as HTMLElement[];
        const totalTracks = trackCards.length;
        let downloadedCount = 0;

        console.log(`[DOWNLOAD_ALL] Starting batch download of ${totalTracks} tracks`);

        for (let i = 0; i < trackCards.length; i++) {
            // Check if cancel was requested
            if (this.downloadAllCancelRequested) {
                console.log('[DOWNLOAD_ALL] Download all cancelled by user');

                // Restore buttons for incomplete downloads
                for (let j = i; j < trackCards.length; j++) {
                    const trackCard = trackCards[j];
                    const downloadBtn = trackCard.querySelector('.grid-add-library-btn') as HTMLButtonElement;
                    if (downloadBtn && !downloadBtn.classList.contains('completed')) {
                        this.restoreDownloadButton(downloadBtn);
                    }
                }
                break;
            }

            const trackCard = trackCards[i];
            const trackId = trackCard.getAttribute('data-track-id');

            if (trackId) {
                try {
                    console.log(`[DOWNLOAD_ALL] Downloading track ${i + 1}/${totalTracks}`);
                    const downloadBtn = trackCard.querySelector('.grid-add-library-btn') as HTMLButtonElement;

                    if (downloadBtn && !downloadBtn.classList.contains('completed')) {
                        this.currentDownloadController = new AbortController();

                        try {
                            await this.handleDownload(parseInt(trackId, 10), trackCard, this.downloadAllScope);
                        } catch (error) {
                            console.error(`[DOWNLOAD_ALL] Download error for track ${trackId}:`, error);
                        }
                    }

                    // Count as queued whether processed or not (including skipped/already completed)
                    downloadedCount++;

                } catch (error) {
                    console.error(`[DOWNLOAD_ALL] Error processing track ${trackId}:`, error);
                }
            }
        }

        // Reset button state
        this.isDownloadingAll = false;
        this.downloadAllCancelRequested = false;
        this.currentDownloadController = null;

        if (downloadAllBtn) {
            downloadAllBtn.textContent = 'Download All';
            downloadAllBtn.classList.remove('cancelling');
            downloadAllBtn.disabled = false;
        }

        console.log(`[DOWNLOAD_ALL] Queued ${downloadedCount}/${totalTracks} tracks`);
    }

    private async addAllToLibrary(): Promise<void> {
        if (this.isDownloadingAll) {
            return;
        }

        this.isDownloadingAll = true;
        this.downloadAllCancelRequested = false;

        const addAllLibraryBtn = document.getElementById('addAllLibraryBtn') as HTMLButtonElement;
        this.setBulkActionButtonState(addAllLibraryBtn, 'library', 'loading');

        const trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]')) as HTMLElement[];
        const totalTracks = trackCards.length;
        let addedCount = 0;
        let failedCount = 0;

        console.log(`[ADD_ALL_LIBRARY] Starting batch add to library of ${totalTracks} tracks`);

        for (let i = 0; i < trackCards.length; i++) {
            const trackCard = trackCards[i];
            const trackId = trackCard.getAttribute('data-track-id');

            if (trackId) {
                try {
                    console.log(`[ADD_ALL_LIBRARY] Adding to library ${i + 1}/${totalTracks}`);
                    const libraryBtn = trackCard.querySelector('.grid-add-library-btn') as HTMLButtonElement;

                    if (libraryBtn && !libraryBtn.classList.contains('completed')) {
                        const wasQueued = libraryBtn.classList.contains('queued');
                        await this.handleDownload(parseInt(trackId, 10), trackCard, this.downloadAllScope);
                        const isQueued = libraryBtn.classList.contains('queued');

                        if (!wasQueued && isQueued) {
                            addedCount++;
                        } else if (!isQueued && !libraryBtn.classList.contains('completed')) {
                            failedCount++;
                        }
                    }

                } catch (error) {
                    console.error(`[ADD_ALL_LIBRARY] Error processing track ${trackId}:`, error);
                    failedCount++;
                }
            }
        }

        this.isDownloadingAll = false;
        this.downloadAllCancelRequested = false;
        this.currentDownloadController = null;

        this.setBulkActionButtonState(addAllLibraryBtn, 'library', failedCount > 0 ? 'failed' : 'success');

        console.log(`[ADD_ALL_LIBRARY] Queued ${addedCount}/${totalTracks} tracks`);
    }

    private async addAllToPlaylist(): Promise<void> {
        if (this.isDownloadingAll) {
            return;
        }

        try {
            const playlists = await this.fetchPlaylists();
            if (!playlists || playlists.length === 0) {
                this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                return;
            }
            await this.showPlaylistSelectorForAll(playlists);
        } catch (error) {
            console.error('[PLAYLIST_ALL] Error handling add all to playlist:', error);
            this.displayMessage('Error fetching playlists. Please try again.');
        }
    }

    private async showPlaylistSelectorForAll(playlists: string[]): Promise<void> {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'playlist-modal-overlay';
            const modal = document.createElement('div');
            modal.className = 'playlist-modal';
            const header = document.createElement('div');
            header.className = 'playlist-modal-header';
            const title = document.createElement('h3');
            title.textContent = 'Add All Tracks to Playlist';
            const closeBtn = document.createElement('button');
            closeBtn.className = 'playlist-modal-close';
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', () => {
                overlay.remove();
                resolve();
            });
            header.appendChild(title);
            header.appendChild(closeBtn);
            const content = document.createElement('div');
            content.className = 'playlist-modal-content';
            if (playlists.length > 0) {
                playlists.forEach((playlistName: string) => {
                    const button = document.createElement('button');
                    button.className = 'playlist-item-btn';
                    button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg><span>${playlistName}</span>`;
                    button.addEventListener('click', async () => {
                        overlay.remove();
                        await this.handleAddAllToPlaylist(playlistName);
                        resolve();
                    });
                    content.appendChild(button);
                });
            }
            const createSection = document.createElement('div');
            createSection.className = 'playlist-create-section';
            const divider = document.createElement('div');
            divider.className = 'playlist-create-divider';
            divider.textContent = 'or';
            const inputGroup = document.createElement('div');
            inputGroup.className = 'playlist-create-inline-group';
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'playlist-create-inline-input';
            input.placeholder = 'New playlist name...';
            const okBtn = document.createElement('button');
            okBtn.className = 'playlist-create-inline-btn';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', async () => {
                const playlistName = input.value.trim();
                if (playlistName) {
                    overlay.remove();
                    await this.handleAddAllToPlaylist(playlistName);
                    resolve();
                }
            });
            input.addEventListener('keypress', (e: KeyboardEvent) => {
                if (e.key === 'Enter') {
                    const playlistName = input.value.trim();
                    if (playlistName) {
                        overlay.remove();
                        void this.handleAddAllToPlaylist(playlistName);
                        resolve();
                    }
                }
            });
            inputGroup.appendChild(input);
            inputGroup.appendChild(okBtn);
            if (playlists.length > 0) {
                createSection.appendChild(divider);
            }
            createSection.appendChild(inputGroup);
            content.appendChild(createSection);
            const footer = document.createElement('div');
            footer.className = 'playlist-modal-footer';
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'playlist-modal-cancel';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', () => {
                overlay.remove();
                resolve();
            });
            footer.appendChild(cancelBtn);
            modal.appendChild(header);
            modal.appendChild(content);
            modal.appendChild(footer);
            overlay.appendChild(modal);
            overlay.addEventListener('click', (e: Event) => {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve();
                }
            });
            document.body.appendChild(overlay);
            input.focus();
        });
    }

    private async handleAddAllToPlaylist(playlistName: string): Promise<void> {
        if (this.isDownloadingAll) {
            return;
        }

        this.isDownloadingAll = true;
        const addAllPlaylistBtn = document.getElementById('addAllPlaylistBtn') as HTMLButtonElement;
        this.setBulkActionButtonState(addAllPlaylistBtn, 'playlist', 'loading');

        const trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]')) as HTMLElement[];
        const totalTracks = trackCards.length;
        let addedCount = 0;
        let failedCount = 0;
        console.log(`[PLAYLIST_ALL] Adding all ${totalTracks} tracks to playlist: ${playlistName}`);
        for (let i = 0; i < trackCards.length; i++) {
            const trackCard = trackCards[i];
            const trackId = trackCard.getAttribute('data-track-id');
            if (trackId) {
                try {
                    console.log(`[PLAYLIST_ALL] Adding track ${i + 1}/${totalTracks}`);
                    const addPlaylistBtn = trackCard.querySelector('.grid-add-playlist-btn') as HTMLButtonElement;
                    if (addPlaylistBtn && !addPlaylistBtn.classList.contains('completed')) {
                        const originalContent = addPlaylistBtn.innerHTML;
                        const originalDisabled = addPlaylistBtn.disabled;
                        if (!addPlaylistBtn.dataset.originalContent) {
                            addPlaylistBtn.dataset.originalContent = originalContent;
                        }
                        addPlaylistBtn.disabled = true;
                        try {
                            const jobId = await this.downloadTrackWithPlaylist(parseInt(trackId, 10), this.downloadAllScope, playlistName);
                            console.log(`[PLAYLIST_ALL] Job queued successfully: ${jobId}`);
                            this.setDownloadButtonQueued(addPlaylistBtn);
                            this.registerActiveJob(jobId, trackCard, addPlaylistBtn, addPlaylistBtn);
                            addedCount++;
                        } catch (error) {
                            console.error('[PLAYLIST_ALL] Error adding track to playlist:', error);
                            addPlaylistBtn.disabled = originalDisabled;
                            addPlaylistBtn.innerHTML = originalContent;
                            if (addPlaylistBtn.dataset.originalContent) {
                                delete addPlaylistBtn.dataset.originalContent;
                            }
                            failedCount++;
                        }
                    }

                } catch (error) {
                    console.error(`[PLAYLIST_ALL] Error processing track ${trackId}:`, error);
                    failedCount++;
                }
            }
        }
        this.isDownloadingAll = false;
        this.setBulkActionButtonState(addAllPlaylistBtn, 'playlist', failedCount > 0 ? 'failed' : 'success');
        console.log(`[PLAYLIST_ALL] Queued ${addedCount}/${totalTracks} tracks`);
    }

    private async loadListenHistory(): Promise<void> {
        if (this.historyLoading) return;
        this.historyLoading = true;

        if (!this.historyTableContainer) {
            this.historyLoading = false;
            return;
        }

        this.historyTableContainer.innerHTML = '<p class="loading-text">Loading listen history...</p>';

        try {
            this.pendingRequestController = new AbortController();
            const params = new URLSearchParams();
            params.set('limit', '200');
            const userId = this.getSelectedPlexUserId();
            if (userId) {
                params.set('user_id', userId);
            }

            const response = await fetch(`/api/listen-history?${params.toString()}`, {
                cache: 'no-store',
                signal: this.pendingRequestController.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch listen history');
            }

            const data = await response.json();
            this.historyEntries = data.history || [];
            this.renderListenHistory();
        } catch (error) {
            if (error instanceof DOMException && error.name === 'AbortError') {
                return;
            }
            if (this.historyTableContainer) {
                this.historyTableContainer.innerHTML = `<p class="loading-text">Error loading listen history: ${error instanceof Error ? error.message : 'Unknown error'}</p>`;
            }
        } finally {
            this.historyLoading = false;
        }
    }

    private renderListenHistory(): void {
        if (!this.historyTableContainer) return;

        if (this.historyEntries.length === 0) {
            this.historyTableContainer.innerHTML = '<p class="loading-text">No listen history found. Run a Plex library sync to populate history.</p>';
            return;
        }

        const rows = this.historyEntries.map(entry => {
            const playedDate = this.formatHistoryDate(entry.played_at);
            const duration = entry.duration ? this.formatHistoryDuration(entry.duration) : '';
            const hifiBadge = entry.hifi_id ? `<span class="hifi-badge" title="HiFi ID">${this.escapeHtml(entry.hifi_id)}</span>` : '';

            return `<tr>
                <td>${this.escapeHtml(playedDate)}</td>
                <td>${this.escapeHtml(entry.title)}</td>
                <td>${this.escapeHtml(entry.artist || '')}</td>
                <td>${this.escapeHtml(entry.album || '')}</td>
                <td>${this.escapeHtml(duration)}</td>
                <td>${hifiBadge}</td>
            </tr>`;
        }).join('');

        this.historyTableContainer.innerHTML = `
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Played</th>
                        <th>Track</th>
                        <th>Artist</th>
                        <th>Album</th>
                        <th>Duration</th>
                        <th>HiFi</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    private isPlaylistFromToday(generatedAt?: string): boolean {
        if (!generatedAt) return false;
        const genDate = new Date(generatedAt);
        const genDay = genDate.toLocaleDateString('en-US', { timeZone: this.timezone });
        const nowDay = new Date().toLocaleDateString('en-US', { timeZone: this.timezone });
        return genDay === nowDay;
    }

    private formatHistoryDate(isoString: string): string {
        try {
            const date = new Date(isoString);
            const now = new Date();
            const diffMs = now.getTime() - date.getTime();
            const diffHours = diffMs / (1000 * 60 * 60);
            const diffDays = diffMs / (1000 * 60 * 60 * 24);

            if (diffHours < 1) {
                const mins = Math.floor(diffMs / (1000 * 60));
                return `${mins}m ago`;
            }
            if (diffHours < 24) {
                return `${Math.floor(diffHours)}h ago`;
            }
            if (diffDays < 7) {
                return `${Math.floor(diffDays)}d ago`;
            }
            return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: this.timezone });
        } catch {
            return isoString;
        }
    }

    private formatHistoryDuration(ms: number): string {
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
