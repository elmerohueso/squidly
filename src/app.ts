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

interface Endpoint {
    name: string;
    encodedUrl: string;
    online: boolean;
    responseTime: number | null;
    lastChecked: string | null;
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
    id3_tagged?: string;
    converted?: string;
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

type DownloadFormat = 'original' | 'mp3';

interface DownloadSettings {
    format: DownloadFormat;
    fileNamingAlbum: string;
    jobsRefreshIntervalSeconds: number;
    ignoreMatches: boolean;
}

interface AppRouteState {
    view: string;
    searchType?: string;
    query?: string;
    artistId?: number;
    albumId?: number;
    trackId?: number;
    playlistId?: string;
    username?: string;
    playlistUrl?: string;
}

interface AppHistoryState {
    app: 'squidly';
    route: AppRouteState;
}

class App {
    private static readonly NEW_PLEX_PLAYLIST_OPTION = '__new_playlist__';
    private searchInput: HTMLInputElement;
    private searchTypeSelect: HTMLSelectElement;
    private searchButton: HTMLButtonElement;
    private resultsContainer: HTMLElement;
    private libraryResultsContainer: HTMLElement;
    private statusButton: HTMLButtonElement;
    private statusFlyout: HTMLElement;
    private flyoutOverlay: HTMLElement;
    private closeFlyoutButton: HTMLButtonElement;
    private flyoutContent: HTMLElement;
    private jobsButton: HTMLButtonElement;
    private jobsFlyout: HTMLElement;
    private jobsOverlay: HTMLElement;
    private closeJobsButton: HTMLButtonElement;
    private jobsFilterSelect: HTMLSelectElement;
    private cancelPendingJobsButton: HTMLButtonElement;
    private retryAllJobsButton: HTMLButtonElement;
    private jobsContent: HTMLElement;
    private jobsPagination: HTMLElement;
    private settingsButton: HTMLButtonElement;
    private settingsFlyout: HTMLElement;
    private settingsOverlay: HTMLElement;
    private closeSettingsButton: HTMLButtonElement;
    private formatOriginalInput: HTMLInputElement;
    private formatMp3Input: HTMLInputElement;
    private fileNamingAlbumInput: HTMLInputElement;
    private jobsRefreshIntervalSecondsInput: HTMLInputElement;
    private listenbrainzTokenInput: HTMLInputElement;
    private saveLbConfigButton: HTMLButtonElement;
    private lbConfigStatusEl: HTMLElement;
    private plexLoginButton: HTMLButtonElement;
    private plexPinContainer: HTMLElement;
    private plexPinDisplay: HTMLElement;
    private plexPinCopyButton: HTMLButtonElement;
    private plexPinStatus: HTMLElement;
    private plexLibraryConfigContainer: HTMLElement;
    private plexLibraryNameSelect: HTMLSelectElement;
    private plexPlaylistContainer: HTMLElement | null;
    private plexPlaylistContainerHomeParent: HTMLElement | undefined;
    private plexPlaylistContainerHomeNextSibling: ChildNode | null;
    private plexPlaylistNameInput: HTMLInputElement;
    private plexPlaylistOptions: HTMLSelectElement;
    private plexPlaylistBackButton: HTMLButtonElement;
    private savePlexConfigButton: HTMLButtonElement;
    private plexSyncIntervalHoursInput: HTMLInputElement;
    private startPlexSyncButton: HTMLButtonElement;
    private plexSyncStatusEl: HTMLElement;
    private plexConfigStatusEl: HTMLElement;
    private plexConnectedStatusEl: HTMLElement;
    private plexClearCredentialsButton: HTMLButtonElement;
    private plexUserDropdownContainer: HTMLElement;
    private plexUserSelect: HTMLSelectElement;
    private ignoreMatchesCheckbox: HTMLInputElement;
    private userButton: HTMLButtonElement;
    private userDropdownModal: HTMLElement;
    private userDropdownOverlay: HTMLElement;
    private userDropdownList: HTMLElement;
    private userButtonText: HTMLElement;
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
    private currentPlayingTrackId: number | null = null;
    private currentPlayButton: HTMLButtonElement | null = null;
    private currentAudioCleanup: {
        audio: HTMLAudioElement;
        onEnded: () => void;
        onError: () => void;
    } | null = null;
    private lastRetryFunction: (() => Promise<void>) | null = null;
    private isPlexConfigured: boolean = false;
    private isHandlingPopState: boolean = false;
    private currentPage: string = 'explore';
    private pendingRequestController: AbortController | null = null;
    private readonly libraryArtistsPageSize: number = 50;
    private libraryArtistsOffset: number = 0;
    private libraryArtistsTotal: number = 0;
    private libraryCurrentArtist: { id: string; name: string } | null = null;
    private libraryCurrentAlbum: { id: string; title: string; artist?: string } | null = null;
    private libraryLoadedOnce: boolean = false;

    constructor() {
        // New page navigation elements
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e: Event) => {
                e.preventDefault();
                const page = (item as HTMLElement).getAttribute('data-page');
                if (page) {
                    this.switchPage(page);
                }
            });
        });

        this.searchInput = document.getElementById('searchInput') as HTMLInputElement;
        this.searchTypeSelect = document.getElementById('searchType') as HTMLSelectElement;
        this.searchButton = document.getElementById('searchButton') as HTMLButtonElement;
        this.resultsContainer = document.getElementById('results') as HTMLElement;
        this.libraryResultsContainer = document.getElementById('libraryResults') as HTMLElement;
        
        // Old flyout elements (may not exist in new layout)
        this.statusButton = document.getElementById('statusButton') as HTMLButtonElement;
        this.statusFlyout = document.getElementById('statusFlyout') as HTMLElement;
        this.flyoutOverlay = document.getElementById('flyoutOverlay') as HTMLElement;
        this.closeFlyoutButton = document.getElementById('closeFlyout') as HTMLButtonElement;
        this.flyoutContent = document.getElementById('flyoutContent') as HTMLElement;
        this.jobsButton = document.getElementById('jobsButton') as HTMLButtonElement;
        this.jobsFlyout = document.getElementById('jobsFlyout') as HTMLElement;
        this.jobsOverlay = document.getElementById('jobsOverlay') as HTMLElement;
        this.closeJobsButton = document.getElementById('closeJobs') as HTMLButtonElement;
        this.jobsFilterSelect = document.getElementById('jobsFilter') as HTMLSelectElement;
        this.cancelPendingJobsButton = document.getElementById('cancelPendingJobs') as HTMLButtonElement;
        this.retryAllJobsButton = document.getElementById('retryAllJobs') as HTMLButtonElement;
        this.jobsContent = document.getElementById('jobsContent') as HTMLElement;
        this.jobsPagination = document.getElementById('jobsPagination') as HTMLElement;
        this.settingsButton = document.getElementById('settingsButton') as HTMLButtonElement;
        this.settingsFlyout = document.getElementById('settingsFlyout') as HTMLElement;
        this.settingsOverlay = document.getElementById('settingsOverlay') as HTMLElement;
        this.closeSettingsButton = document.getElementById('closeSettings') as HTMLButtonElement;
        this.formatOriginalInput = document.getElementById('formatOriginal') as HTMLInputElement;
        this.formatMp3Input = document.getElementById('formatMp3') as HTMLInputElement;
        this.fileNamingAlbumInput = document.getElementById('fileNamingAlbum') as HTMLInputElement;
        this.jobsRefreshIntervalSecondsInput = document.getElementById('jobsRefreshIntervalSeconds') as HTMLInputElement;
        this.listenbrainzTokenInput = document.getElementById('listenbrainzToken') as HTMLInputElement;
        this.saveLbConfigButton = document.getElementById('saveLbConfig') as HTMLButtonElement;
        this.lbConfigStatusEl = document.getElementById('lbConfigStatus') as HTMLElement;
        this.plexLoginButton = document.getElementById('plexLoginButton') as HTMLButtonElement;
        this.plexPinContainer = document.getElementById('plexPinContainer') as HTMLElement;
        this.plexPinDisplay = document.getElementById('plexPinDisplay') as HTMLElement;
        this.plexPinCopyButton = document.getElementById('plexPinCopy') as HTMLButtonElement;
        this.plexPinStatus = document.getElementById('plexPinStatus') as HTMLElement;
        this.plexLibraryConfigContainer = document.getElementById('plexLibraryConfig') as HTMLElement;
        this.plexLibraryNameSelect = document.getElementById('plexLibraryName') as HTMLSelectElement;
        this.plexPlaylistContainer = document.getElementById('plexPlaylistContainer') as HTMLElement;
        this.plexPlaylistContainerHomeParent = this.plexPlaylistContainer?.parentElement as HTMLElement | undefined;
        this.plexPlaylistContainerHomeNextSibling = this.plexPlaylistContainer?.nextSibling || null;
        this.plexPlaylistNameInput = document.getElementById('plexPlaylistName') as HTMLInputElement;
        this.plexPlaylistOptions = document.getElementById('plexPlaylistOptions') as HTMLSelectElement;
        this.plexPlaylistBackButton = document.getElementById('plexPlaylistBack') as HTMLButtonElement;
        this.savePlexConfigButton = document.getElementById('savePlexConfig') as HTMLButtonElement;
        this.plexSyncIntervalHoursInput = document.getElementById('plexSyncIntervalHours') as HTMLInputElement;
        this.startPlexSyncButton = document.getElementById('startPlexSync') as HTMLButtonElement;
        this.plexSyncStatusEl = document.getElementById('plexSyncStatus') as HTMLElement;
        this.plexConfigStatusEl = document.getElementById('plexConfigStatus') as HTMLElement;
        this.plexConnectedStatusEl = document.getElementById('plexConnectedStatus') as HTMLElement;
        this.plexClearCredentialsButton = document.getElementById('plexClearCredentialsButton') as HTMLButtonElement;
        this.plexUserDropdownContainer = document.getElementById('plexUserDropdownContainer') as HTMLElement;
        this.plexUserSelect = document.getElementById('plexUserSelect') as HTMLSelectElement;
        this.ignoreMatchesCheckbox = document.getElementById('ignoreMatchesCheckbox') as HTMLInputElement;
        
        // User dropdown for top bar
        this.userButton = document.getElementById('userButton') as HTMLButtonElement;
        this.userDropdownModal = document.getElementById('userDropdownModal') as HTMLElement;
        this.userDropdownOverlay = document.getElementById('userDropdownOverlay') as HTMLElement;
        this.userDropdownList = document.getElementById('userDropdownList') as HTMLElement;
        this.userButtonText = document.getElementById('userButtonText') as HTMLElement;
        
        this.initializeEventListeners();
        this.downloadSettings = this.defaultDownloadSettings();
        this.applySettingsToForm(this.downloadSettings);
        
        // Initialize page navigation (start with Explore page)
        this.switchPage('explore');
        
        this.initializeHistoryNavigation();
        void this.fetchDownloadSettingsFromServer();
        void this.loadListenbrainzConfig();
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
                void this.cancelAllPendingJobs();
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

        if (this.settingsButton) {
            this.settingsButton.addEventListener('click', () => this.openSettingsFlyout());
        }
        if (this.closeSettingsButton) {
            this.closeSettingsButton.addEventListener('click', () => this.closeSettingsFlyout());
        }
        if (this.settingsOverlay) {
            this.settingsOverlay.addEventListener('click', () => this.closeSettingsFlyout());
        }

        if (this.formatOriginalInput) {
            this.formatOriginalInput.addEventListener('change', () => this.updateSettingsFromForm());
        }
        if (this.formatMp3Input) {
            this.formatMp3Input.addEventListener('change', () => this.updateSettingsFromForm());
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
        if (this.saveLbConfigButton) {
            this.saveLbConfigButton.addEventListener('click', () => this.saveListenbrainzConfig());
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

                    window.localStorage.removeItem('plexSelectedUserId');
                    await this.loadPlexConfig();
                    void this.updatePlexClearCredentialsButton();
                }
            });
        }

        if (this.plexUserSelect) {
            this.plexUserSelect.addEventListener('change', async () => {
                window.localStorage.setItem('plexSelectedUserId', this.plexUserSelect.value);
                await this.loadPlexPlaylists();
            });
        }

        if (this.plexPinCopyButton) {
            this.plexPinCopyButton.addEventListener('click', () => {
                const pin = this.plexPinDisplay?.textContent || '';
                if (pin) {
                    navigator.clipboard.writeText(pin);
                    if (this.plexPinStatus) {
                        this.plexPinStatus.textContent = 'PIN copied!';
                        setTimeout(() => { 
                            if (this.plexPinStatus) {
                                this.plexPinStatus.textContent = ''; 
                            }
                        }, 1500);
                    }
                }
            });
        }
        if (this.startPlexSyncButton) {
            this.startPlexSyncButton.addEventListener('click', () => this.startPlexSync());
        }
        if (this.plexPlaylistOptions) {
            this.plexPlaylistOptions.addEventListener('change', () => {
                const selectedName = this.plexPlaylistOptions.value.trim();
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
                    void this.navigateToRoute({ view: 'listenbrainz_playlist_tracks', playlistId }, true);
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

                const breadcrumbButton = target.closest('[data-library-crumb]') as HTMLButtonElement | null;
                if (breadcrumbButton) {
                    e.preventDefault();
                    const crumb = breadcrumbButton.getAttribute('data-library-crumb');
                    if (crumb === 'library') {
                        void this.loadLibraryArtists(0);
                        return;
                    }
                    if (crumb === 'artist' && this.libraryCurrentArtist) {
                        void this.loadLibraryArtistAlbums(this.libraryCurrentArtist.id, this.libraryCurrentArtist.name);
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
                if (albumRow) {
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

    private switchPage(pageName: string): void {
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
        const selectedPage = document.getElementById(`${pageName}Page`);
        if (selectedPage) {
            selectedPage.classList.add('active');
        }

        // Update active nav item
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.classList.remove('active');
            if ((item as HTMLElement).getAttribute('data-page') === pageName) {
                item.classList.add('active');
            }
        });

        // Update current page
        this.currentPage = pageName;

        // Update top bar title based on page
        const topBarLeft = document.querySelector('.top-bar-left');
        if (topBarLeft) {
            const pageNames: Record<string, string> = {
                explore: 'Explore',
                library: 'Library',
                settings: 'Settings',
                mirrors: 'Hi-Fi Mirrors',
                jobs: 'Jobs'
            };
            const h2 = topBarLeft.querySelector('h2') || document.createElement('h2');
            h2.textContent = pageNames[pageName] || 'Squidly';
            if (!topBarLeft.querySelector('h2')) {
                topBarLeft.appendChild(h2);
            }
        }

        // Refresh mirrors data when switching to mirrors page
        if (pageName === 'mirrors') {
            void this.updateEndpointStatus();
        }

        // Load jobs when switching to jobs page
        if (pageName === 'jobs') {
            this.currentJobsPage = 1;
            void this.loadJobs();
        }

        if (pageName === 'library' && !this.libraryLoadedOnce) {
            void this.loadLibraryArtists(0);
        }
    }

    private setLibraryMessage(message: string): void {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryResultsContainer.innerHTML = `
            <div class="library-placeholder">
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    private formatLibraryBreadcrumb(): string {
        const artist = this.libraryCurrentArtist;
        const album = this.libraryCurrentAlbum;

        let trail = '<button class="library-crumb-btn" data-library-crumb="library">Library</button>';

        if (artist) {
            if (album) {
                trail += `<span class="library-crumb-separator">&gt;</span><button class="library-crumb-btn" data-library-crumb="artist">${this.escapeHtml(artist.name)}</button>`;
            } else {
                trail += `<span class="library-crumb-separator">&gt;</span><span class="library-crumb-current">${this.escapeHtml(artist.name)}</span>`;
            }
        }

        if (album) {
            trail += `<span class="library-crumb-separator">&gt;</span><span class="library-crumb-current">${this.escapeHtml(album.title)}</span>`;
        }

        return `<div class="library-breadcrumb">${trail}</div>`;
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

    private formatLibraryAlbumRow(album: PlexLibraryAlbum): string {
        const title = this.escapeHtml(album.title || 'Unknown Album');
        const artist = this.escapeHtml(album.artist || this.libraryCurrentArtist?.name || 'Unknown Artist');
        const year = album.year ? String(album.year) : '—';
        const trackCount = typeof album.track_count === 'number' ? String(album.track_count) : '—';

        return `
            <div class="albums-grid-row library-clickable-row" data-library-album-id="${this.escapeHtml(album.id)}" data-library-album-title="${title}" data-library-artist-name="${artist}">
                <div class="grid-cell grid-col-artwork">
                    ${album.cover
                        ? `<img src="${album.cover}" alt="${title}" loading="lazy">`
                        : `<div class="grid-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                           </div>`
                    }
                </div>
                <div class="grid-cell grid-col-title"><div class="track-title-with-badge">${title}</div></div>
                <div class="grid-cell grid-col-artist"><span class="library-album-artist-name">${artist}</span></div>
                <div class="grid-cell grid-col-year">${year}</div>
                <div class="grid-cell grid-col-track-count">${trackCount}</div>
            </div>
        `;
    }

    private formatLibraryTrackRow(track: PlexLibraryTrack, showDiscPrefix: boolean): string {
        const title = this.escapeHtml(track.title || 'Unknown Track');
        const artist = this.escapeHtml(track.artist || this.libraryCurrentArtist?.name || 'Unknown Artist');
        const artistId = this.escapeHtml(track.artist_id || this.libraryCurrentArtist?.id || '');
        const trackNumber = typeof track.track_number === 'number' ? track.track_number : null;
        const discNumber = typeof track.disc_number === 'number' ? track.disc_number : 1;
        const numberLabel = trackNumber !== null
            ? (showDiscPrefix ? `${discNumber}-${String(trackNumber).padStart(2, '0')}` : String(trackNumber))
            : '—';
        const durationSeconds = typeof track.duration === 'number' ? Math.max(0, Math.round(track.duration / 1000)) : null;
        const durationLabel = durationSeconds !== null ? this.formatDuration(durationSeconds) : '—';
        const qualityFormat = (track.quality_format || '').trim().toUpperCase();
        const qualityBitrate = typeof track.quality_bitrate_kbps === 'number' ? `${track.quality_bitrate_kbps} kbps` : '';
        const qualityLabel = [qualityFormat, qualityBitrate].filter(Boolean).join(' • ') || '—';

        return `
            <div class="tracks-grid-row" data-plex-library-row="true">
                <div class="grid-cell grid-col-track-number">${numberLabel}</div>
                <div class="grid-cell grid-col-title"><div class="track-title-with-badge">${title}</div></div>
                <div class="grid-cell grid-col-artist"><span class="track-artist-name library-track-artist-name" data-library-artist-id="${artistId}" data-library-artist-name="${artist}" title="View albums by ${artist}">${artist}</span></div>
                <div class="grid-cell grid-col-quality">${durationLabel}</div>
                <div class="grid-cell grid-col-quality">${qualityLabel}</div>
            </div>
        `;
    }

    private renderLibraryArtists(artists: PlexLibraryArtist[]): void {
        this.libraryLoadedOnce = true;
        const currentPage = Math.floor(this.libraryArtistsOffset / this.libraryArtistsPageSize) + 1;
        const totalPages = Math.max(1, Math.ceil(this.libraryArtistsTotal / this.libraryArtistsPageSize));
        const prevOffset = Math.max(0, this.libraryArtistsOffset - this.libraryArtistsPageSize);
        const nextOffset = this.libraryArtistsOffset + this.libraryArtistsPageSize;
        const hasPrev = this.libraryArtistsOffset > 0;
        const hasNext = nextOffset < this.libraryArtistsTotal;

        this.libraryResultsContainer.innerHTML = `
            ${this.formatLibraryBreadcrumb()}
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
                <button class="library-page-btn" data-library-offset="${prevOffset}" ${hasPrev ? '' : 'disabled'}>Previous</button>
                <span class="library-page-text">Page ${currentPage} of ${totalPages}</span>
                <button class="library-page-btn" data-library-offset="${nextOffset}" ${hasNext ? '' : 'disabled'}>Next</button>
            </div>
        `;
    }

    private renderLibraryArtistAlbums(artistName: string, albums: PlexLibraryAlbum[], artistPicture?: string): void {
        this.libraryLoadedOnce = true;
        this.libraryResultsContainer.innerHTML = `
            ${this.formatLibraryBreadcrumb()}
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
            </div>
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Albums</h2>
                </div>
            </div>
            <div class="albums-grid-wrapper" data-view-mode="library-albums">
                <div class="albums-grid">
                    <div class="albums-grid-header">
                        <div class="grid-cell grid-col-artwork"></div>
                        <div class="grid-cell grid-col-title">ALBUM</div>
                        <div class="grid-cell grid-col-artist">ARTIST</div>
                        <div class="grid-cell grid-col-year">YEAR</div>
                        <div class="grid-cell grid-col-track-count">TRACKS</div>
                    </div>
                    ${albums.length > 0
                        ? albums.map((album) => this.formatLibraryAlbumRow(album)).join('')
                        : '<div class="library-placeholder"><p>No albums found for this artist.</p></div>'}
                </div>
            </div>
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

        this.libraryResultsContainer.innerHTML = `
            ${this.formatLibraryBreadcrumb()}
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
            </div>
            <div class="results-header">
                <div class="results-header-top">
                    <h2>Tracks</h2>
                </div>
            </div>
            <div class="tracks-grid-wrapper" data-view-mode="library-tracks">
                <div class="tracks-grid">
                    <div class="tracks-grid-header">
                        <div class="grid-cell grid-col-track-number">#</div>
                        <div class="grid-cell grid-col-title">Title</div>
                        <div class="grid-cell grid-col-artist">Artist</div>
                        <div class="grid-cell grid-col-quality">Duration</div>
                        <div class="grid-cell grid-col-quality">QUALITY</div>
                    </div>
                    ${tracks.length > 0
                        ? tracks.map((track) => this.formatLibraryTrackRow(track, maxDisc > 1)).join('')
                        : '<div class="library-placeholder"><p>No tracks found for this album.</p></div>'}
                </div>
            </div>
        `;
    }

    private async loadLibraryArtists(offset: number = 0): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(false);
        this.libraryCurrentArtist = null;
        this.libraryCurrentAlbum = null;
        this.libraryArtistsOffset = Math.max(0, offset);
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

    private async loadLibraryArtistAlbums(artistId: string, artistName: string): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryCurrentArtist = { id: artistId, name: artistName };
        this.libraryCurrentAlbum = null;
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

    private async loadLibraryAlbumTracks(albumId: string, albumTitle: string, artistName?: string): Promise<void> {
        if (!this.libraryResultsContainer) {
            return;
        }

        this.libraryCurrentAlbum = { id: albumId, title: albumTitle, artist: artistName };
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

    private async loadPlexUsersForDropdown(): Promise<void> {
        if (!this.userDropdownList) {
            return;
        }

        try {
            const response = await fetch('/api/plex/users', { cache: 'no-store' });
            if (!response.ok) {
                this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">Failed to load users</li>';
                return;
            }

            const data = await response.json();
            const users = Array.isArray(data.users) ? data.users : [];

            if (users.length === 0) {
                this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">No users found</li>';
                return;
            }

            const savedId = window.localStorage.getItem('plexSelectedUserId') || '';
            this.userDropdownList.innerHTML = '';

            users.forEach((user: any) => {
                const id = String(user.client_id ?? user.id ?? user.username ?? user.title ?? '');
                const label = String(user.username || user.title || id);
                const isSelected = id === savedId;

                const li = document.createElement('li');
                li.className = `user-dropdown-item ${isSelected ? 'selected' : ''}`;
                li.addEventListener('click', () => this.selectPlexUser(id, label));

                // User icon
                const icon = document.createElement('div');
                icon.className = 'user-dropdown-icon';
                icon.textContent = label.charAt(0).toUpperCase();
                li.appendChild(icon);

                // User name
                const nameSpan = document.createElement('span');
                nameSpan.textContent = label;
                li.appendChild(nameSpan);

                // Checkmark if selected
                if (isSelected) {
                    const checkmark = document.createElement('span');
                    checkmark.className = 'user-dropdown-checkmark';
                    checkmark.textContent = '✓';
                    li.appendChild(checkmark);
                }

                this.userDropdownList.appendChild(li);
            });
        } catch (error) {
            console.warn('Failed to load users:', error);
            this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">Error loading users</li>';
        }
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
            void this.loadLibraryArtists(0);
        }
    }

    private async updateSidebarPlaylists(): Promise<void> {
        try {
            const userId = window.localStorage.getItem('plexSelectedUserId');
            const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';

            const response = await fetch(`/api/plex/playlists${query}`, { cache: 'no-store' });
            if (!response.ok) {
                this.populateSidebarPlaylists([]);
                return;
            }

            const data = await response.json();
            const playlists = Array.isArray(data.playlists) ? data.playlists : [];
            this.populateSidebarPlaylists(playlists);
        } catch (error) {
            console.warn('Failed to load playlists:', error);
            this.populateSidebarPlaylists([]);
        }
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
                    console.log('[USER_INIT] Found selected user:', userName);
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
                            await this.updateSidebarPlaylists();
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

    private populateSidebarPlaylists(playlists: string[]): void {
        const playlistNavItems = document.getElementById('playlistNavItems');
        if (!playlistNavItems) {
            return;
        }

        playlistNavItems.innerHTML = '';

        if (playlists.length === 0) {
            const li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.875rem';
            li.textContent = 'No playlists';
            playlistNavItems.appendChild(li);
            return;
        }

        playlists.forEach((playlistName: string) => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = '#';
            a.className = 'nav-item';
            a.textContent = playlistName;
            a.style.fontSize = '0.875rem';
            a.addEventListener('click', (e: Event) => {
                e.preventDefault();
                // Playlist click handling could be added here
            });
            li.appendChild(a);
            playlistNavItems.appendChild(li);
        });
    }

    private initializeHistoryNavigation(): void {
        window.addEventListener('popstate', (event: PopStateEvent) => {
            void this.handlePopState(event);
        });

        const historyRoute = this.parseHistoryState(window.history.state);
        const initialRoute = historyRoute || this.parseRouteFromUrl() || { view: 'home' };
        this.replaceHistoryRoute(initialRoute);

        if (initialRoute.view !== 'home') {
            void this.navigateToRoute(initialRoute, false);
        }
    }

    private async handlePopState(event: PopStateEvent): Promise<void> {
        const route = this.parseHistoryState(event.state) || this.parseRouteFromUrl() || { view: 'home' };
        this.isHandlingPopState = true;
        try {
            await this.navigateToRoute(route, false);
        } finally {
            this.isHandlingPopState = false;
        }
    }

    private parseHistoryState(rawState: unknown): AppRouteState | null {
        if (!rawState || typeof rawState !== 'object') {
            return null;
        }

        const state = rawState as Partial<AppHistoryState>;
        if (state.app !== 'squidly' || !state.route || typeof state.route !== 'object') {
            return null;
        }

        const route = state.route as AppRouteState;
        return route.view ? route : null;
    }

    private parseRouteFromUrl(): AppRouteState | null {
        const params = new URLSearchParams(window.location.search);
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
            return playlistId ? { view, playlistId } : null;
        }

        if (view === 'lastfm_playlist' || view === 'youtube_music_playlist') {
            const playlistUrl = params.get('url') || '';
            return playlistUrl ? { view, playlistUrl } : null;
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

        return view === 'home' ? { view: 'home' } : null;
    }

    private buildRouteUrl(route: AppRouteState): string {
        if (route.view === 'home') {
            return window.location.pathname;
        }

        const params = new URLSearchParams();
        params.set('view', route.view);

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

        if ((route.view === 'lastfm_playlist' || route.view === 'youtube_music_playlist') && route.playlistUrl) {
            params.set('url', route.playlistUrl);
        }

        if (route.view === 'similar_artists' && route.artistId) {
            params.set('id', String(route.artistId));
        }

        return `${window.location.pathname}?${params.toString()}`;
    }

    private pushHistoryRoute(route: AppRouteState): void {
        if (this.isHandlingPopState) {
            return;
        }

        const state: AppHistoryState = { app: 'squidly', route };
        window.history.pushState(state, '', this.buildRouteUrl(route));
    }

    private replaceHistoryRoute(route: AppRouteState): void {
        const state: AppHistoryState = { app: 'squidly', route };
        window.history.replaceState(state, '', this.buildRouteUrl(route));
    }

    private async navigateToRoute(route: AppRouteState, updateHistory: boolean): Promise<void> {
        // Abort all pending requests from the previous route
        if (this.pendingRequestController) {
            this.pendingRequestController.abort();
        }

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
            await this.handleListenbrainzPlaylists(route.username, updateHistory);
            return;
        }

        if (route.view === 'listenbrainz_playlist_tracks' && route.playlistId) {
            await this.fetchListenbrainzPlaylistTracks(route.playlistId, updateHistory);
            return;
        }

        if (route.view === 'lastfm_playlist' && route.playlistUrl) {
            this.searchTypeSelect.value = 'lastfm';
            this.searchInput.value = route.playlistUrl;
            this.updateSearchPlaceholder();
            await this.handleLastfmPlaylist(route.playlistUrl, updateHistory);
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
                jobs_filter: filter,
                exclude_plex_playlist_add: '1'
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
        const showCancelIncomplete = filter === 'incomplete';
        this.cancelPendingJobsButton.classList.toggle('hidden', !showCancelIncomplete);

        if (!showCancelIncomplete) {
            this.cancelPendingJobsButton.disabled = true;
            this.cancelPendingJobsButton.textContent = 'Cancel all incomplete';
        } else {
            this.cancelPendingJobsButton.disabled = incompleteCount === 0;
            this.cancelPendingJobsButton.textContent = incompleteCount > 0
                ? `Cancel all incomplete (${incompleteCount})`
                : 'Cancel all incomplete';
        }

        const showRetryAll = filter === 'completed_with_errors' || filter === 'failed';
        this.retryAllJobsButton.classList.toggle('hidden', !showRetryAll);

        if (!showRetryAll) {
            this.retryAllJobsButton.disabled = true;
            this.retryAllJobsButton.textContent = 'Retry all';
            return;
        }

        this.retryAllJobsButton.disabled = retryableCount === 0;
        this.retryAllJobsButton.textContent = retryableCount > 0
            ? `Retry all (${retryableCount})`
            : 'Retry all';
    }

    private async cancelAllPendingJobs(): Promise<void> {
        const pendingCountLabel = this.cancelPendingJobsButton.textContent || 'Cancel all incomplete';
        if (this.cancelPendingJobsButton.disabled) {
            return;
        }

        const shouldProceed = window.confirm('Cancel and remove all incomplete jobs from the queue?');
        if (!shouldProceed) {
            return;
        }

        this.cancelPendingJobsButton.disabled = true;
        this.cancelPendingJobsButton.textContent = 'Cancelling...';

        try {
            const response = await fetch('/api/jobs/cancel-incomplete', { method: 'POST' });
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
            this.cancelPendingJobsButton.textContent = pendingCountLabel;
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

        if (failures.length > 0 || skippedExistingCount > 0) {
            const retriedCount = retryableJobs.length - failures.length - skippedExistingCount;
            const summary = failures.length <= 3 ? failures.join('\n') : `${failures.slice(0, 3).join('\n')}\n...`;
            const skipLine = skippedExistingCount > 0
                ? `\nSkipped ${skippedExistingCount} job${skippedExistingCount === 1 ? '' : 's'} (already exists in Plex).`
                : '';
            const failureLine = failures.length > 0 ? `\n${summary}` : '';
            window.alert(`Retried ${retriedCount} of ${retryableJobs.length} jobs.${skipLine}${failureLine}`);
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

        if (job.status === 'succeeded' && stages?.playlist_added === 'queued') {
            return 'in_progress';
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

        if (job.job_type === 'plex_library_sync') {
            const stageRows = [
                { key: 'reading_plex_library', label: 'Reading Plex Library' },
                { key: 'updating_local_index', label: 'Updating Local Index' }
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

            const progress = job.result?.progress || {};
            const processed = Number(progress.processed_tracks || 0);
            const total = Number(progress.total_tracks || 0);
            const upserted = Number(progress.upserted_songs || 0);
            const deleted = Number(progress.deleted_songs || 0);
            const progressText = total > 0
                ? `${processed}/${total} tracks processed • ${upserted} songs upserted • ${deleted} removed`
                : `${upserted} songs upserted • ${deleted} removed`;

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

        const stageRows = [
            { key: 'downloaded', label: 'Downloaded' },
            { key: 'id3_tagged', label: 'ID3 Tag Created' },
            { key: 'converted', label: 'Converted to MP3' },
            { key: 'written', label: 'Written to Disk' },
            ...(upgradedExisting ? [{ key: 'upgraded_existing', label: 'Upgraded Existing File' }] : []),
            {
                key: 'playlist_added',
                label: playlistName ? `Added to Playlist "${this.escapeHtml(String(playlistName))}"` : 'Added to Playlist'
            }
        ];

        const stageHtml = stageRows.map(stage => {
            const status = this.resolveStageStatus(job, stage.key as keyof JobStageMap, stages);
            const stageLabel = this.formatStageStatus(status);
            let stageDisplayLabel = stage.label;
            if (stage.key === 'converted' && status === 'skipped') {
                stageDisplayLabel = 'Conversion not required';
            }
            if (stage.key === 'playlist_added' && status === 'skipped') {
                stageDisplayLabel = 'Playlist add not requested';
            }
            return `
                <div class="job-stage">
                    <span>${stageDisplayLabel}</span>
                    <span class="job-stage-status status-${status}">${stageLabel}</span>
                </div>
            `;
        }).join('');

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

        const artist = job.result?.artist;
        const title = job.result?.title;

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
            if (key === 'converted') {
                const requestedFormat = String(job.result?.format || job.payload?.format || 'original').toLowerCase();
                return requestedFormat === 'mp3' ? 'done' : 'skipped';
            }
            return key === 'playlist_added' ? 'skipped' : 'done';
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
            format: 'original',
            fileNamingAlbum: '{artist}/{album}/{track} - {title}.{ext}',
            jobsRefreshIntervalSeconds: 30,
            ignoreMatches: false
        };
    }

    private normalizeSettings(raw: Partial<DownloadSettings>): DownloadSettings {
        const fallback = this.defaultDownloadSettings();
        const fileNaming = (raw as { file_naming?: string }).file_naming;
        const fileNamingAlbum = (raw as { file_naming_album?: string }).file_naming_album;
        const legacyFileNaming = (raw as { fileNaming?: string }).fileNaming;
        const jobsRefreshIntervalSecondsRaw = (raw as { jobs_refresh_interval_seconds?: number | string }).jobs_refresh_interval_seconds;
        const jobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds(
            (raw as { jobsRefreshIntervalSeconds?: number | string }).jobsRefreshIntervalSeconds
            ?? jobsRefreshIntervalSecondsRaw
        );

        return {
            format: raw.format === 'mp3' ? 'mp3' : 'original',
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
                : Boolean((raw as { ignore_matches?: boolean | string }).ignore_matches)
        };
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
        this.formatOriginalInput.checked = settings.format === 'original';
        this.formatMp3Input.checked = settings.format === 'mp3';
        this.fileNamingAlbumInput.value = settings.fileNamingAlbum;
        this.jobsRefreshIntervalSecondsInput.value = String(settings.jobsRefreshIntervalSeconds);
        this.ignoreMatchesCheckbox.checked = settings.ignoreMatches === true;
        this.syncFormatToggleStyles();
    }

    private readSettingsFromForm(): DownloadSettings {
        const fallbackIntervalSeconds = this.downloadSettings?.jobsRefreshIntervalSeconds ?? this.defaultDownloadSettings().jobsRefreshIntervalSeconds;
        const parsedJobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds(this.jobsRefreshIntervalSecondsInput.value);

        return {
            format: this.formatMp3Input.checked ? 'mp3' : 'original',
            fileNamingAlbum: this.fileNamingAlbumInput.value.trim(),
            jobsRefreshIntervalSeconds: parsedJobsRefreshIntervalSeconds ?? fallbackIntervalSeconds,
            ignoreMatches: this.ignoreMatchesCheckbox.checked
        };
    }

    private updateSettingsFromForm(): void {
        this.downloadSettings = this.readSettingsFromForm();
        this.jobsRefreshIntervalSecondsInput.value = String(this.downloadSettings.jobsRefreshIntervalSeconds);
        this.queueSettingsSave();
        this.syncFormatToggleStyles();

        if (this.jobsFlyout.classList.contains('active')) {
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

    private syncFormatToggleStyles(): void {
        const originalLabel = this.formatOriginalInput.closest('label');
        const mp3Label = this.formatMp3Input.closest('label');

        if (originalLabel) {
            originalLabel.classList.toggle('active', this.formatOriginalInput.checked);
        }

        if (mp3Label) {
            mp3Label.classList.toggle('active', this.formatMp3Input.checked);
        }
    }

    private async loadListenbrainzConfig(): Promise<void> {
        try {
            const response = await fetch('/api/listenbrainz/config');
            if (response.ok) {
                const data = await response.json();
                this.lbConfigStatusEl.textContent = data.has_token ? '✓ Token configured' : '';
                this.lbConfigStatusEl.style.color = data.has_token ? 'var(--accent-primary)' : '';
            }
        } catch (error) {
            console.warn('Failed to load ListenBrainz config.', error);
        }
    }

    private async saveListenbrainzConfig(): Promise<void> {
        const userToken = this.listenbrainzTokenInput.value.trim();

        if (!userToken) {
            this.lbConfigStatusEl.textContent = '⚠ User token is required';
            this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
            return;
        }

        try {
            const response = await fetch('/api/listenbrainz/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_token: userToken
                })
            });

            if (response.ok) {
                this.lbConfigStatusEl.textContent = '✓ Configuration saved';
                this.lbConfigStatusEl.style.color = 'var(--accent-primary)';
                this.listenbrainzTokenInput.value = '';
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

    private async loadPlexConfig(): Promise<void> {
        try {
            const response = await fetch('/api/plex/config');
            if (response.ok) {
                const data = await response.json();
                // Populate library dropdown with saved library
                this.plexLibraryNameSelect.innerHTML = '';
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = 'Select a library...';
                this.plexLibraryNameSelect.appendChild(defaultOption);
                if (data.library_name) {
                    const option = document.createElement('option');
                    option.value = data.library_name;
                    option.textContent = data.library_name;
                    this.plexLibraryNameSelect.appendChild(option);
                    this.plexLibraryNameSelect.value = data.library_name;
                }
                const intervalHours = Number(data.sync_interval_hours);
                this.plexSyncIntervalHoursInput.value = Number.isFinite(intervalHours) && intervalHours > 0
                    ? String(intervalHours)
                    : '24';
                this.isPlexConfigured = data.has_config ? true : false;
                this.updatePlexConfigStatus(data.has_config ? '✓ Configured' : '');

                // Show library selector only when Plex is configured (server+token exist) and a library hasn't been saved yet.
                const shouldShowLibraryConfig = Boolean(data.has_config) && !Boolean(data.library_name);
                if (this.plexLibraryConfigContainer) {
                    this.plexLibraryConfigContainer.style.display = shouldShowLibraryConfig ? '' : 'none';
                }

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

    private async loadPlexLibraries(): Promise<void> {
        try {
            const response = await fetch('/api/plex/libraries');
            if (!response.ok) {
                throw new Error('Failed to fetch Plex libraries');
            }
            const data = await response.json();
            const libraries = Array.isArray(data.libraries) ? data.libraries : [];
            const current = this.plexLibraryNameSelect.value || '';

            this.plexLibraryNameSelect.innerHTML = '';
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select a library...';
            this.plexLibraryNameSelect.appendChild(defaultOption);

            libraries.forEach((library: string) => {
                const option = document.createElement('option');
                option.value = library;
                option.textContent = library;
                this.plexLibraryNameSelect.appendChild(option);
            });

            if (current) {
                this.plexLibraryNameSelect.value = current;
            }
        } catch (error) {
            console.warn('Failed to load Plex libraries.', error);
        }
    }

    private async savePlexConfig(): Promise<void> {
        const libraryName = this.plexLibraryNameSelect.value.trim();
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
            const library = this.plexLibraryNameSelect.value.trim();
            if (this.plexConnectedStatusEl) {
                const serverLabel = this.plexConnectedStatusEl.textContent?.replace(/^Connected to\s*/, '') || '';
                const serverName = serverLabel || '';
                const libraryText = library ? ` (library: ${library})` : '';
                this.plexConnectedStatusEl.textContent = `Connected to ${serverName}${libraryText}`.trim();
                this.plexConnectedStatusEl.style.display = 'block';
            }
            if (this.plexLibraryConfigContainer) {
                this.plexLibraryConfigContainer.style.display = 'none';
            }

            window.alert('Plex configuration saved.');
        } catch (error) {
            console.error('Failed to save Plex config:', error);
            window.alert((error as Error).message || 'Failed to save Plex configuration');
        }
    }




    // --- PIN OAuth logic ---
    private async startPlexPinLogin(): Promise<void> {
        console.debug('[PLEX_UI] startPlexPinLogin called');
        // Prepare UI for PIN-based login flow
        if (this.plexLoginButton) {
            this.plexLoginButton.disabled = true;
            this.plexLoginButton.style.display = 'none';
        }
        if (this.plexLibraryConfigContainer) {
            this.plexLibraryConfigContainer.style.display = 'none';
        }
        if (this.plexConnectedStatusEl) {
            this.plexConnectedStatusEl.style.display = 'none';
        }

        this.plexPinStatus.textContent = '';
        this.plexPinDisplay.textContent = '';
        this.plexPinContainer.style.display = 'block';
        this.plexPinStatus.textContent = 'Requesting PIN...';
        try {
            const resp = await fetch('/api/plex/pin/start', { method: 'POST' });
            console.debug('[PLEX_UI] /api/plex/pin/start response', resp.status);
            const data = await resp.json();
            console.debug('[PLEX_UI] /api/plex/pin/start data', data);
            if (!data.ok) throw new Error(data.error || 'Failed to start PIN login');
            this.plexPinDisplay.textContent = data.pin;
            this.plexPinStatus.textContent = '';
            await this.pollPlexPinStatus(data.client_id, data.pin, 300);
        } catch (e) {
            console.debug('[PLEX_UI] startPlexPinLogin error', e);
            this.plexPinStatus.textContent = 'Failed to start PIN login.';
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
                    this.plexPinStatus.textContent = '✓ Plex login successful!';
                    this.plexPinDisplay.textContent = '';
                    this.plexPinContainer.style.display = 'none';
                    this.isPlexConfigured = true;
                    this.updatePlexConfigStatus('✓ Configured');
                    await this.loadPlexConfig();

                    // Refresh cached health status so the UI can update properly
                    await fetch('/api/plex/healthcheck', { cache: 'no-store' }).catch(() => null);
                    return;
                } else if (data.expired) {
                    this.plexPinStatus.textContent = 'PIN expired. Please try again.';
                    this.plexPinDisplay.textContent = '';
                    if (this.plexLoginButton) {
                        this.plexLoginButton.disabled = false;
                        this.plexLoginButton.style.display = '';
                    }
                    return;
                }
            } catch (e) {
                console.debug('[PLEX_UI] pollPlexPinStatus error', e);
                this.plexPinStatus.textContent = 'Error polling PIN status.';
                if (this.plexLoginButton) {
                    this.plexLoginButton.disabled = false;
                    this.plexLoginButton.style.display = '';
                }
                return;
            }
        }
        console.debug('[PLEX_UI] pollPlexPinStatus timed out');
        this.plexPinStatus.textContent = 'Login timed out. Please try again.';
        this.plexPinDisplay.textContent = '';
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
            // First, trigger the library update
            const libUpdateResponse = await fetch('/api/plex/library-update', {
                method: 'POST'
            });

            if (libUpdateResponse.status !== 202) {
                const data = await libUpdateResponse.json().catch(() => ({}));
                this.plexSyncStatusEl.textContent = `✗ ${data.error || 'Failed to start library update'}`;
                this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
                return;
            }

            // Then, trigger the sync
            this.plexSyncStatusEl.textContent = 'Starting Plex sync...';

            const syncResponse = await fetch('/api/plex/sync', {
                method: 'POST'
            });

            if (syncResponse.status === 202) {
                this.plexSyncStatusEl.textContent = '✓ Plex library update and sync jobs queued';
                this.plexSyncStatusEl.style.color = 'var(--accent-primary)';
                if (this.jobsFlyout.classList.contains('active')) {
                    await this.loadJobs();
                }
            } else {
                const data = await syncResponse.json().catch(() => ({}));
                this.plexSyncStatusEl.textContent = `✗ ${data.error || 'Failed to start sync'}`;
                this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
            }
        } catch (error) {
            console.error('Error starting Plex sync:', error);
            this.plexSyncStatusEl.textContent = '✗ Error starting update/sync';
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
                    const library = this.plexLibraryNameSelect?.value?.trim() || '';
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

    private async loadPlexUsers(): Promise<void> {
        if (!this.plexUserSelect) {
            return;
        }

        try {
            const response = await fetch('/api/plex/users', { cache: 'no-store' });
            if (!response.ok) {
                throw new Error('Failed to fetch Plex users');
            }

            const data = await response.json();
            const users = Array.isArray(data.users) ? data.users : [];

            this.plexUserSelect.innerHTML = '';
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = users.length ? 'Select a user...' : '(no users found)';
            placeholder.disabled = users.length === 0;
            this.plexUserSelect.appendChild(placeholder);

            const savedId = window.localStorage.getItem('plexSelectedUserId') || '';
            let selectedSet = false;

            users.forEach((user: any) => {
                const id = String(user.client_id ?? user.id ?? user.username ?? user.title ?? '');
                const label = String(user.username || user.title || id);
                const option = document.createElement('option');
                option.value = id;
                option.textContent = label;
                this.plexUserSelect.appendChild(option);

                if (!selectedSet && savedId && id === savedId) {
                    option.selected = true;
                    selectedSet = true;
                }
            });

            if (!selectedSet && users.length > 0) {
                const owner = users.find((u: any) => u.is_owner);
                const ownerId = owner ? String(owner.id ?? owner.username ?? '') : '';
                if (ownerId) {
                    const ownerOption = Array.from(this.plexUserSelect.options).find((opt) => opt.value === ownerId);
                    if (ownerOption) {
                        ownerOption.selected = true;
                        window.localStorage.setItem('plexSelectedUserId', ownerId);
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to load Plex users:', error);
        }
    }

    private updatePlexPlaylistContainerVisibility(show: boolean): void {
        if (!this.plexPlaylistContainer) return;
        if (this.isPlexConfigured && show) {
            this.restorePlexPlaylistContainerToHome();
            this.plexPlaylistContainer.style.display = 'flex';
            void this.loadPlexPlaylists();
        } else {
            this.restorePlexPlaylistContainerToHome();
            this.plexPlaylistContainer.style.display = 'none';
        }
    }

    private movePlexPlaylistContainerBeneathDownloadAll(): void {
        if (!this.plexPlaylistContainer) return;
        const buttonsContainer = this.resultsContainer.querySelector('.add-all-buttons-container') as HTMLElement | null;
        if (!buttonsContainer || !buttonsContainer.parentElement) {
            return;
        }

        const headerTop = buttonsContainer.parentElement;
        const header = headerTop.parentElement;
        if (header) {
            header.insertBefore(this.plexPlaylistContainer, headerTop.nextSibling);
        } else {
            headerTop.insertBefore(this.plexPlaylistContainer, buttonsContainer.nextSibling);
        }
        this.plexPlaylistContainer.style.padding = '0';
        this.plexPlaylistContainer.style.marginTop = '0.75rem';
    }

    private restorePlexPlaylistContainerToHome(): void {
        if (!this.plexPlaylistContainer || !this.plexPlaylistContainerHomeParent) return;
        if (this.plexPlaylistContainer.parentElement !== this.plexPlaylistContainerHomeParent) {
            if (
                this.plexPlaylistContainerHomeNextSibling &&
                this.plexPlaylistContainerHomeNextSibling.parentNode === this.plexPlaylistContainerHomeParent
            ) {
                this.plexPlaylistContainerHomeParent.insertBefore(
                    this.plexPlaylistContainer,
                    this.plexPlaylistContainerHomeNextSibling
                );
            } else {
                this.plexPlaylistContainerHomeParent.appendChild(this.plexPlaylistContainer);
            }
        }

        this.plexPlaylistContainer.style.padding = '1rem';
        this.plexPlaylistContainer.style.marginTop = '0';
    }

    private populatePlexPlaylistOptions(playlists: string[], showEmptyPlaceholder: boolean = true): void {
        const currentInputValue = this.plexPlaylistNameInput.value;
        const currentMode = this.plexPlaylistNameInput.style.display === 'none' ? 'existing' : 'new';
        this.plexPlaylistOptions.innerHTML = '';

        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'No Playlist';
        this.plexPlaylistOptions.appendChild(defaultOption);

        if (playlists.length === 0 && showEmptyPlaceholder) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '(no existing playlists found)';
            emptyOption.disabled = true;
            this.plexPlaylistOptions.appendChild(emptyOption);
        }

        playlists.forEach((playlistName) => {
            const option = document.createElement('option');
            option.value = playlistName;
            option.textContent = playlistName;
            this.plexPlaylistOptions.appendChild(option);
        });

        const newOption = document.createElement('option');
        newOption.value = App.NEW_PLEX_PLAYLIST_OPTION;
        newOption.textContent = 'New playlist...';
        this.plexPlaylistOptions.appendChild(newOption);

        this.plexPlaylistNameInput.value = currentInputValue;

        if (currentMode === 'new') {
            this.setPlexPlaylistMode('new');
            this.plexPlaylistOptions.value = App.NEW_PLEX_PLAYLIST_OPTION;
            return;
        }

        const hasMatchingExisting = playlists.includes(currentInputValue);
        this.plexPlaylistOptions.value = hasMatchingExisting ? currentInputValue : '';
        this.setPlexPlaylistMode('existing');
    }

    private setPlexPlaylistMode(mode: 'existing' | 'new'): void {
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
        } catch (error) {
            console.error('Error fetching endpoint status:', error);
        }
    }

    private displayEndpointStatus(data: EndpointStatus): void {
        // Update button
        const statusCount = document.querySelector('.status-count');
        if (statusCount) {
            statusCount.textContent = `${data.summary.online}/${data.summary.total}`;
        }

        // Update summary
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

        // Update endpoint list
        if (!this.flyoutContent) {
            console.warn('Flyout content element not found');
            return;
        }

        this.flyoutContent.innerHTML = data.endpoints.map(endpoint => {
            const url = atob(endpoint.encodedUrl);
            const statusClass = endpoint.online ? 'online' : 'offline';
            const statusText = endpoint.online ? 'Online' : 'Offline';
            const responseTime = endpoint.responseTime 
                ? `${endpoint.responseTime.toFixed(0)}ms` 
                : 'N/A';
            const lastChecked = endpoint.lastChecked 
                ? new Date(endpoint.lastChecked).toLocaleTimeString()
                : 'Never';

            return `
                <div class="endpoint-item">
                    <div class="endpoint-header">
                        <span class="endpoint-name">${endpoint.name}</span>
                        <div class="endpoint-status ${statusClass}">
                            <span class="status-indicator ${statusClass}"></span>
                            ${statusText}
                        </div>
                    </div>
                    <div class="endpoint-url">${url}</div>
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
        }).join('');
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

        this.displayMessage('Searching...');

        try {
            const response = await this.fetchWithRetry(`/search/?${searchType}=${encodeURIComponent(query)}`);

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
            const tracks = scrapeData.tracks || [];
            const totalTracks = tracks.length;

            if (totalTracks === 0) {
                this.displayMessage('No tracks found in playlist');
                return;
            }

            this.updatePlexPlaylistContainerVisibility(true);

            // Set up progress display with grid structure
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>Last.fm Playlist - "${this.escapeHtml(playlistName)}"</h2>
                    </div>
                </div>
                <div class="results-list">
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            <div class="tracks-grid-header">
                                <div class="grid-cell grid-col-artwork"></div>
                                <div class="grid-cell grid-col-title">Title</div>
                                <div class="grid-cell grid-col-artist">Artist</div>
                                <div class="grid-cell grid-col-album">Album</div>
                                <div class="grid-cell grid-col-quality">Quality</div>
                                <div class="grid-cell grid-col-actions">Actions</div>
                            </div>
                            <div id="lastfmResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const resultsList = document.getElementById('lastfmResultsList');
            let foundCount = 0;
            const matchedTracks: Track[] = [];
            const notFoundTracks: Array<{ artist: string; name: string }> = [];

            // Search for each track progressively
            for (let i = 0; i < tracks.length; i++) {
                const track = tracks[i];
                const searchQuery = `${track.name} ${track.artist}`;

                try {
                    const searchResponse = await fetch(`/search/?s=${encodeURIComponent(searchQuery)}`, {
                        signal: this.pendingRequestController?.signal
                    });
                    
                    if (searchResponse.ok) {
                        const searchData = await searchResponse.json();
                        const items = searchData.data?.items || [];
                        
                        if (items.length > 0) {
                            // Add the first match to results
                            const trackRow = this.formatTrackGridRow(items[0] as Track, false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0] as Track);
                            foundCount++;
                        } else {
                            notFoundTracks.push({
                                artist: track.artist,
                                name: track.name
                            });
                        }
                    } else {
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                    }
                } catch (error) {
                    console.error(`Failed to search for ${searchQuery}:`, error);
                    notFoundTracks.push({
                        artist: track.artist,
                        name: track.name
                    });
                }

            }

            // Create and add Add All buttons after searching is complete
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
                            <div class="tracks-grid-header">
                                <div class="grid-cell grid-col-artwork"></div>
                                <div class="grid-cell grid-col-title">Title</div>
                                <div class="grid-cell grid-col-artist">Artist</div>
                                <div class="grid-cell grid-col-album">Album</div>
                                <div class="grid-cell grid-col-quality">Quality</div>
                                <div class="grid-cell grid-col-actions">Actions</div>
                            </div>
                            <div id="lastfmResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const resultsList = document.getElementById('lastfmResultsList');
            let foundCount = 0;
            const matchedTracks: Track[] = [];
            const notFoundTracks: Array<{ artist: string; name: string }> = [];

            for (let i = 0; i < tracks.length; i++) {
                const track = tracks[i];
                const searchQuery = `${track.name} ${track.artist}`;

                try {
                    const searchResponse = await fetch(`/search/?s=${encodeURIComponent(searchQuery)}`, {
                        signal: this.pendingRequestController?.signal
                    });

                    if (searchResponse.ok) {
                        const searchData = await searchResponse.json();
                        const items = searchData.data?.items || [];

                        if (items.length > 0) {
                            const trackRow = this.formatTrackGridRow(items[0] as Track, false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0] as Track);
                            foundCount++;
                        } else {
                            notFoundTracks.push({
                                artist: track.artist,
                                name: track.name
                            });
                        }
                    } else {
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                    }
                } catch (error) {
                    console.error(`Failed to search for ${searchQuery}:`, error);
                    notFoundTracks.push({
                        artist: track.artist,
                        name: track.name
                    });
                }

            }

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

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }

        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to process YouTube Music playlist'}`);
            console.error('YouTube Music playlist error:', error);
        }
    }

    private async handleListenbrainzPlaylists(usernameOverride?: string, updateHistory: boolean = true): Promise<void> {
        const username = (usernameOverride ?? this.searchInput.value).trim();
        
        if (!username) {
            this.displayMessage('Please enter ListenBrainz username');
            return;
        }

        if (updateHistory) {
            this.pushHistoryRoute({ view: 'listenbrainz_playlists', username });
        }

        this.displayMessage('Loading ListenBrainz playlists...');

        try {
            const response = await fetch(`/api/listenbrainz/playlists?username=${encodeURIComponent(username)}`, {
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

            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <h2>ListenBrainz Playlists (${playlists.length})</h2>
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

    private async fetchListenbrainzPlaylistTracks(playlistId: string, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'listenbrainz_playlist_tracks', playlistId });
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
            const response = await fetch(`/api/listenbrainz/playlist/${encodeURIComponent(playlistMbid)}`, {
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

            // Set up initial display with progress bar for searching
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(playlistTitle)}</h2>
                        <p class="playlist-creator-display">by ${this.escapeHtml(playlistCreator)}</p>
                    </div>
                </div>
                <div class="results-list">
                    <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                        <div class="tracks-grid">
                            <div class="tracks-grid-header">
                                <div class="grid-cell grid-col-artwork"></div>
                                <div class="grid-cell grid-col-title">Title</div>
                                <div class="grid-cell grid-col-artist">Artist</div>
                                <div class="grid-cell grid-col-album">Album</div>
                                <div class="grid-cell grid-col-quality">Quality</div>
                                <div class="grid-cell grid-col-actions">Actions</div>
                            </div>
                            <div id="listenbrainzResultsList"></div>
                        </div>
                    </div>
                </div>
            `;

            const resultsList = document.getElementById('listenbrainzResultsList');
            let foundCount = 0;
            const matchedTracks: Track[] = [];
            const notFoundTracks: Array<{ artist: string; name: string }> = [];

            // Search for each track progressively
            for (let i = 0; i < tracks.length; i++) {
                const lbTrack = tracks[i];
                const artists = lbTrack.creator || 'Unknown';
                const searchQuery = `${lbTrack.title} ${artists}`;

                try {
                    const searchResponse = await fetch(`/search/?s=${encodeURIComponent(searchQuery)}`, {
                        signal: this.pendingRequestController?.signal
                    });
                    
                    if (searchResponse.ok) {
                        const searchData = await searchResponse.json();
                        const items = searchData.data?.items || [];
                        
                        if (items.length > 0) {
                            // Add the first match to results
                            const trackRow = this.formatTrackGridRow(items[0] as Track, false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0] as Track);
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
                    console.error(`Failed to search for ${searchQuery}:`, error);
                    notFoundTracks.push({
                        artist: artists,
                        name: lbTrack.title || 'Unknown'
                    });
                }

            }

            // Create and add Add All buttons after searching is complete
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

            if (matchedTracks.length > 0) {
                void this.annotateTrackCardsWithPlexStatus(matchedTracks);
            }
        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to load ListenBrainz playlist'}`);
            console.error('ListenBrainz playlist error:', error);
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
                ? this.formatAlbumsGrid(items as AlbumSearchItem[])
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
        }
    }

    private async annotateTrackCardsWithPlexStatus(tracks: Track[]): Promise<void> {
        if (!Array.isArray(tracks) || tracks.length === 0) {
            return;
        }

        // Use the route's abort signal
        const signal = this.pendingRequestController?.signal;

        // Try to find grid rows first (new grid layout)
        const gridRows = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row')) as HTMLElement[];
        if (gridRows.length > 0) {
            await this.annotateGridRowsWithPlexStatus(tracks, gridRows, signal);
            return;
        }

        // Fall back to old track-card logic
        const cards = Array.from(this.resultsContainer.querySelectorAll('.results-list .track-card')) as HTMLElement[];
        if (cards.length === 0) {
            return;
        }

        const payloadTracks = tracks.map((track) => {
            const artist = track.artists && track.artists.length > 0
                ? track.artists.map(a => a.name).join(', ')
                : track.artist?.name || '';
            const album = track.album?.title || '';
            return {
                title: track.title || '',
                artist,
                album
            };
        });

        try {
            const response = await fetch('/api/plex/songs/match', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ tracks: payloadTracks }),
                signal
            });

            if (!response.ok) {
                return;
            }

            const data = await response.json() as { matches?: PlexTrackMatch[] };
            const matches = Array.isArray(data.matches) ? data.matches : [];
            const max = Math.min(cards.length, matches.length);

            for (let i = 0; i < max; i += 1) {
                const match = matches[i];
                if (!match || !match.exists) {
                    continue;
                }

                const metadataEl = cards[i].querySelector('.track-metadata') as HTMLElement | null;
                if (!metadataEl || metadataEl.querySelector('.plex-existing-chip')) {
                    continue;
                }

                if (metadataEl.children.length > 0) {
                    const sep = document.createElement('span');
                    sep.className = 'plex-chip-separator';
                    sep.textContent = '•';
                    metadataEl.appendChild(sep);
                }

                const allLowQualityMp3 = Array.isArray(match.variants) && match.variants.length > 0 &&
                    match.variants.every(v =>
                        (v.format === 'mp3' || v.format === 'mpeg') &&
                        typeof v.bitrate === 'number' && v.bitrate <= 192
                    );
                const chip = document.createElement('span');
                chip.className = allLowQualityMp3
                    ? 'plex-existing-chip plex-existing-chip--low-quality'
                    : 'plex-existing-chip';
                chip.textContent = allLowQualityMp3 ? 'In Plex · low quality' : 'In Plex';
                chip.title = this.buildPlexExistingTooltip(match.variants || []);
                metadataEl.appendChild(chip);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate Plex inventory matches.', error);
        }
    }

    private async annotateGridRowsWithPlexStatus(tracks: Track[], gridRows: HTMLElement[], signal?: AbortSignal): Promise<void> {
        const payloadTracks = tracks.map((track) => {
            const artist = track.artists && track.artists.length > 0
                ? track.artists.map(a => a.name).join(', ')
                : track.artist?.name || '';
            const album = track.album?.title || '';
            return {
                title: track.title || '',
                artist,
                album
            };
        });

        try {
            const response = await fetch('/api/plex/songs/match', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ tracks: payloadTracks }),
                signal
            });

            if (!response.ok) {
                return;
            }

            const data = await response.json() as { matches?: PlexTrackMatch[] };
            const matches = Array.isArray(data.matches) ? data.matches : [];
            const max = Math.min(gridRows.length, matches.length);

            const allRowsInPlex = gridRows.length > 0
                && matches.length >= gridRows.length
                && gridRows.every((_, index) => Boolean(matches[index] && matches[index].exists));

            if (allRowsInPlex) {
                this.replaceAddAllLibraryWithPlexBadge(matches.slice(0, gridRows.length));
            }

            for (let i = 0; i < max; i += 1) {
                const match = matches[i];
                if (!match || !match.exists) {
                    continue;
                }

                // Mark row as having Plex existence
                gridRows[i].setAttribute('data-plex-exists', 'true');

                // Replace Add to Library button with Plex badge in the actions area
                const actionsCell = gridRows[i].querySelector('.grid-col-actions') as HTMLElement | null;
                if (!actionsCell) {
                    continue;
                }

                const addLibraryBtn = actionsCell.querySelector('.grid-add-library-btn') as HTMLElement | null;
                if (!addLibraryBtn) {
                    continue;
                }

                const allLowQualityMp3 = Array.isArray(match.variants) && match.variants.length > 0 &&
                    match.variants.every(v =>
                        (v.format === 'mp3' || v.format === 'mpeg') &&
                        typeof v.bitrate === 'number' && v.bitrate <= 192
                    );

                const chip = document.createElement('span');
                chip.className = allLowQualityMp3
                    ? 'plex-existing-chip plex-existing-chip--in-actions plex-existing-chip--low-quality'
                    : 'plex-existing-chip plex-existing-chip--in-actions';
                chip.textContent = allLowQualityMp3 ? 'In Plex · low quality' : 'In Plex';
                chip.title = this.buildPlexExistingTooltip(match.variants || []);

                addLibraryBtn.replaceWith(chip);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate grid rows with Plex status.', error);
        }
    }

    private async annotateAlbumGridsWithPlexStatus(albums: AlbumSearchItem[]): Promise<void> {
        if (!Array.isArray(albums) || albums.length === 0) {
            return;
        }

        // Use the route's abort signal, or create a local one if not available
        const signal = this.pendingRequestController?.signal;

        try {
            const gridRows = Array.from(this.resultsContainer.querySelectorAll('.albums-grid-row')) as HTMLElement[];

            // For each album, fetch its tracks and check if they're all in Plex
            for (let i = 0; i < gridRows.length && i < albums.length; i++) {
                // Check if aborted before each iteration
                if (signal?.aborted) {
                    return;
                }

                const gridRow = gridRows[i];
                const albumId = gridRow.getAttribute('data-album-id');
                if (!albumId) {
                    continue;
                }

                try {
                    // Fetch album tracks with abort signal
                    const albumResponse = await fetch(`/album/?id=${albumId}`, {
                        signal
                    });
                    if (!albumResponse.ok) {
                        continue;
                    }

                    const albumData: AlbumInfo = await albumResponse.json();
                    const trackItems = albumData.data?.items || [];
                    const tracks = trackItems
                        .filter(item => item.type === 'track')
                        .map(item => item.item)
                        .filter(t => t && t.id);

                    if (tracks.length === 0) {
                        continue;
                    }

                    // Check these tracks against Plex
                    const payloadTracks = tracks.map((track: Track) => {
                        const artist = track.artists?.[0]?.name || track.artist?.name || '';
                        const album = track.album?.title || '';
                        return {
                            title: track.title || '',
                            artist,
                            album
                        };
                    });

                    const matchResponse = await fetch('/api/plex/songs/match', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tracks: payloadTracks }),
                        signal
                    });

                    if (!matchResponse.ok) {
                        continue;
                    }

                    const matchData = await matchResponse.json();
                    const matches = Array.isArray(matchData.matches) ? matchData.matches : [];

                    // Check if ALL tracks from this album are in Plex
                    const allInPlex = matches.length === tracks.length &&
                        matches.every((m: any) => m && m.exists);

                    if (!allInPlex) {
                        continue;
                    }

                    gridRow.setAttribute('data-plex-exists', 'true');

                    // Replace Add to Library button with Plex badge
                    const actionsCell = gridRow.querySelector('.grid-col-actions') as HTMLElement | null;
                    if (!actionsCell) {
                        continue;
                    }

                    const addLibraryBtn = actionsCell.querySelector('.grid-add-library-btn') as HTMLElement | null;
                    if (!addLibraryBtn) {
                        continue;
                    }

                    // Check if all are low quality MP3s
                    const allLowQualityMp3 = matches.every((m: any) =>
                        Array.isArray(m.variants) && m.variants.length > 0 &&
                        m.variants.every((v: any) =>
                            (v.format === 'mp3' || v.format === 'mpeg') &&
                            typeof v.bitrate === 'number' && v.bitrate <= 192
                        )
                    );

                    const chip = document.createElement('span');
                    chip.className = allLowQualityMp3
                        ? 'plex-existing-chip plex-existing-chip--in-actions plex-existing-chip--low-quality'
                        : 'plex-existing-chip plex-existing-chip--in-actions';
                    chip.textContent = allLowQualityMp3 ? 'In Plex · low quality' : 'In Plex';
                    chip.title = this.buildPlexExistingTooltip(matches.flatMap((m: any) => m.variants || []));

                    addLibraryBtn.replaceWith(chip);
                } catch (error) {
                    // Ignore abort errors and continue with next album
                    if (error instanceof Error && error.name === 'AbortError') {
                        return;
                    }
                    continue;
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                return;
            }
            console.warn('Failed to annotate album grid rows with Plex status.', error);
        }
    }

    private replaceAddAllLibraryWithPlexBadge(matches: PlexTrackMatch[]): void {
        const addAllLibraryBtn = document.getElementById('addAllLibraryBtn') as HTMLButtonElement | null;
        if (!addAllLibraryBtn || !addAllLibraryBtn.parentElement) {
            return;
        }

        const allLowQualityMp3 = matches.length > 0 && matches.every((match) =>
            Array.isArray(match.variants)
            && match.variants.length > 0
            && match.variants.every(v =>
                (v.format === 'mp3' || v.format === 'mpeg')
                && typeof v.bitrate === 'number' && v.bitrate <= 192
            )
        );

        const badge = document.createElement('span');
        badge.className = allLowQualityMp3
            ? 'plex-existing-chip plex-existing-chip--in-actions plex-existing-chip--bulk plex-existing-chip--low-quality'
            : 'plex-existing-chip plex-existing-chip--in-actions plex-existing-chip--bulk';
        badge.textContent = allLowQualityMp3 ? 'In Plex · low quality' : 'In Plex';
        badge.title = this.buildPlexExistingTooltip(matches.flatMap((m: PlexTrackMatch) => m.variants || []));

        addAllLibraryBtn.replaceWith(badge);
    }

    private buildPlexExistingTooltip(variants: PlexSongVariant[]): string {
        if (!Array.isArray(variants) || variants.length === 0) {
            return 'Exists in Plex';
        }

        const details = variants.map((variant) => {
            const bitrate = typeof variant.bitrate === 'number' && Number.isFinite(variant.bitrate)
                ? ` (${variant.bitrate} kbps)`
                : '';
            const path = variant.file_path
                ? `  ${variant.file_path}${bitrate}`
                : `  ${(variant.format || 'unknown').toUpperCase()}${bitrate}`;
            return path;
        });

        return `Exists in Plex\n${details.join('\n')}`;
    }

    private formatSearchPlaylistCard(playlist: PlaylistSearchItem): string {
        const playlistId = this.escapeHtml(this.getPlaylistId(playlist));
        const playlistName = this.escapeHtml(playlist.title || 'Unknown Playlist');
        const playlistDescription = this.escapeHtml((playlist.description || '').trim());
        const trackTotal = playlist.numberOfTracks ?? playlist.numberOfItems;
        const trackCount = typeof trackTotal === 'number'
            ? `${trackTotal} track${trackTotal !== 1 ? 's' : ''}`
            : '';

        let quality = playlist.audioQuality || '';
        if (playlist.mediaMetadata?.tags && playlist.mediaMetadata.tags.length > 0) {
            const tags = playlist.mediaMetadata.tags;
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('DOLBY_ATMOS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
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

        if (rawCover.startsWith('http://') || rawCover.startsWith('https://')) {
            return rawCover;
        }

        return this.formatTidalImageUrl(rawCover, 640);
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
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'playlist', playlistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading playlist tracks...');

        try {
            const normalizedPlaylistId = this.normalizePlaylistId(playlistId) || playlistId;
            const response = await fetch(`/playlist/?id=${encodeURIComponent(normalizedPlaylistId)}`, {
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

        // Get quality info - check mediaMetadata.tags for best quality
        let quality = track.audioQuality || track.quality || '';
        if (track.mediaMetadata?.tags && track.mediaMetadata.tags.length > 0) {
            // Prioritize: HIRES_LOSSLESS > DOLBY_ATMOS > LOSSLESS > LOW
            const tags = track.mediaMetadata.tags;
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('DOLBY_ATMOS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
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

    private allTracksFromSameAlbum(tracks: Track[]): boolean {
        if (tracks.length <= 1) return true;
        const firstAlbumId = tracks[0].album?.id;
        return tracks.every(track => track.album?.id === firstAlbumId);
    }

    private formatTracksGrid(tracks: Track[], numberOfVolumes?: number): string {
        const isSingleAlbum = this.allTracksFromSameAlbum(tracks);
        
        if (isSingleAlbum) {
            // Single album view - show track number column, hide album column
            return `
                <div class="tracks-grid-wrapper" data-view-mode="single-album">
                    <div class="tracks-grid">
                        <div class="tracks-grid-header">
                            <div class="grid-cell grid-col-track-number">#</div>
                            <div class="grid-cell grid-col-title">Title</div>
                            <div class="grid-cell grid-col-artist">Artist</div>
                            <div class="grid-cell grid-col-duration">Duration</div>
                            <div class="grid-cell grid-col-quality">Quality</div>
                            <div class="grid-cell grid-col-actions">Actions</div>
                        </div>
                        ${tracks.map((track) => this.formatTrackGridRow(track, true, numberOfVolumes, false, false)).join('')}
                    </div>
                </div>
            `;
        } else {
            // Multi-album view - hide track number column, show album column
            return `
                <div class="tracks-grid-wrapper" data-view-mode="multi-album">
                    <div class="tracks-grid">
                        <div class="tracks-grid-header">
                            <div class="grid-cell grid-col-artwork"></div>
                            <div class="grid-cell grid-col-title">Title</div>
                            <div class="grid-cell grid-col-artist">Artist</div>
                            <div class="grid-cell grid-col-album">Album</div>
                            <div class="grid-cell grid-col-duration">Duration</div>
                            <div class="grid-cell grid-col-quality">Quality</div>
                            <div class="grid-cell grid-col-actions">Actions</div>
                        </div>
                        ${tracks.map((track) => this.formatTrackGridRow(track, false, numberOfVolumes, true, true)).join('')}
                    </div>
                </div>
            `;
        }
    }

    private formatTrackGridRow(track: Track, showTrackNumber: boolean, numberOfVolumes: number | undefined, showAlbumColumn: boolean, showArtwork: boolean): string {
        // Get artist names and IDs
        const artistNames = track.artists && track.artists.length > 0
            ? track.artists.map(a => a.name).join(', ')
            : track.artist?.name || 'Unknown Artist';
        const primaryArtistId = track.artists?.[0]?.id || track.artist?.id;

        // Get album info
        const albumTitle = track.album?.title || 'Unknown Album';
        const albumCover = track.album?.cover || track.cover;
        const albumId = track.album?.id;

        // Get quality info
        let quality = track.audioQuality || track.quality || '';
        if (track.mediaMetadata?.tags && track.mediaMetadata.tags.length > 0) {
            const tags = track.mediaMetadata.tags;
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('DOLBY_ATMOS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
        const qualityDisplay = this.formatQuality(quality);
        const durationDisplay = track.duration ? this.formatDuration(track.duration) : '—';

        // Format track title with optional version
        let trackTitle = this.escapeHtml(track.title);
        if (track.version && typeof track.version === 'string' && track.version.trim()) {
            trackTitle += ` (${this.escapeHtml(track.version)})`;
        }

        // Format track number if needed
        let trackNumberDisplay = '';
        if (showTrackNumber && track.trackNumber) {
            const volumeNumber = track.volumeNumber || 1;
            trackNumberDisplay = numberOfVolumes && numberOfVolumes > 1
                ? `${volumeNumber}-${String(track.trackNumber).padStart(2, '0')}`
                : String(track.trackNumber);
        }

        return `
            <div class="tracks-grid-row" data-track-id="${track.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''} ${albumId ? `data-album-id="${albumId}"` : ''}>
                ${showArtwork ? `<div class="grid-cell grid-col-artwork">
                    ${albumCover 
                        ? `<img src="${this.formatTidalImageUrl(albumCover, 1280)}" alt="${track.title}" loading="lazy">`
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
                    <span class="track-artist-name" ${primaryArtistId ? `title="View albums by ${this.escapeHtml(artistNames)}"` : ''}>${this.escapeHtml(artistNames)}</span>
                </div>
                ${showAlbumColumn ? `<div class="grid-cell grid-col-album">
                    <span class="track-album-name" ${albumId ? `title="View tracks on ${this.escapeHtml(albumTitle)}"` : ''}>${this.escapeHtml(albumTitle)}</span>
                </div>` : ''}
                <div class="grid-cell grid-col-duration">${durationDisplay}</div>
                <div class="grid-cell grid-col-quality">${qualityDisplay || '—'}</div>
                <div class="grid-cell grid-col-actions">
                    <button class="grid-play-btn" title="Play" aria-label="Play" data-track-id="${track.id}">
                        ${this.getPlayIconSvg()}
                    </button>
                    <button class="grid-more-btn" title="Find Similar" aria-label="Find Similar">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                    <button class="grid-add-playlist-btn" title="Add to Playlist" data-track-id="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14"></path>
                            <path d="M5 12h14"></path>
                        </svg>
                    </button>
                    <button class="grid-add-library-btn" title="Add to Library" data-track-id="${track.id}">
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
        if (this.currentPlayingTrackId === trackId) {
            this.stopPlayback();
            return;
        }

        this.stopPlayback();
        this.setPlayButtonState(playButton, true);
        this.setPlayButtonLoading(playButton, true);
        this.currentPlayingTrackId = trackId;
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
        const qualities = ['LOSSLESS'];

        for (const quality of qualities) {
            try {
                const response = await fetch(`/track/?id=${trackId}&quality=${quality}`);
                if (!response.ok) {
                    continue;
                }

                const data = await response.json();
                const manifestBase64 = data?.data?.manifest || data?.manifest;
                if (typeof manifestBase64 !== 'string') {
                    continue;
                }

                const manifest = this.decodeManifest(manifestBase64);
                const urls = manifest?.urls;
                if (Array.isArray(urls) && typeof urls[0] === 'string') {
                    return urls[0];
                }
            } catch (error) {
                console.warn(`[PLAYBACK] Failed to fetch ${quality} stream:`, error);
            }
        }

        throw new Error('No playable stream found');
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

        // Format audio quality if available - check mediaMetadata.tags for best quality
        let quality = album.audioQuality || '';
        const tags = album.mediaMetadata?.tags || (album as any).mediaTags;
        if (tags && tags.length > 0) {
            // Prioritize: HIRES_LOSSLESS > DOLBY_ATMOS > LOSSLESS > LOW
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('DOLBY_ATMOS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
        const qualityDisplay = this.formatQuality(quality);

        return `
            <div class="track-card album-card clickable" data-album-id="${album.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''} title="Click to view tracks">
                <div class="track-artwork">
                    ${album.cover 
                        ? `<img src="${this.formatTidalImageUrl(album.cover, 1280)}" alt="${album.title}" loading="lazy">`
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

    private formatAlbumGridRow(album: AlbumSearchItem, hideArtist: boolean = false): string {
        // Get artist names and IDs
        const artistNames = album.artists && album.artists.length > 0
            ? album.artists.map(a => a.name).join(', ')
            : album.artist?.name || 'Unknown Artist';
        const primaryArtistId = album.artists?.[0]?.id || album.artist?.id;

        // Format release year if available
        const releaseYear = album.releaseDate 
            ? new Date(album.releaseDate).getFullYear()
            : '';

        // Format track count - just the number
        const trackCount = (album.numberOfTracks ?? album.numberOfItems)
            ? `${album.numberOfTracks ?? album.numberOfItems}`
            : '';

        // Format audio quality if available - check mediaMetadata.tags for best quality
        let quality = album.audioQuality || '';
        const tags = album.mediaMetadata?.tags || (album as any).mediaTags;
        if (tags && tags.length > 0) {
            // Prioritize: HIRES_LOSSLESS > DOLBY_ATMOS > LOSSLESS > LOW
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('DOLBY_ATMOS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
        const qualityDisplay = this.formatQuality(quality);

        const albumCover = album.cover;

        return `
            <div class="albums-grid-row ${hideArtist ? 'hide-artist' : ''}" data-album-id="${album.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''}>
                <div class="grid-cell grid-col-artwork">
                    ${albumCover 
                        ? `<img src="${this.formatTidalImageUrl(albumCover, 1280)}" alt="${album.title}" loading="lazy">`
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
                    <span class="album-artist-name" ${primaryArtistId ? `title="View albums by ${this.escapeHtml(artistNames)}"` : ''}>${this.escapeHtml(artistNames)}</span>
                </div>` : ''}
                <div class="grid-cell grid-col-year">${releaseYear || '—'}</div>
                <div class="grid-cell grid-col-track-count">${trackCount || '—'}</div>
                <div class="grid-cell grid-col-quality">${qualityDisplay || '—'}</div>
                <div class="grid-cell grid-col-actions">
                    <button class="grid-play-btn" title="View Tracks" aria-label="View Tracks" data-album-id="${album.id}">
                        ${this.getPlayIconSvg()}
                    </button>
                    <button class="grid-more-btn" title="Find Similar" aria-label="Find Similar">
                        ${this.getMoreLikeIconSvg()}
                    </button>
                    <button class="grid-add-playlist-btn" title="Add to Playlist" data-album-id="${album.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14"></path>
                            <path d="M5 12h14"></path>
                        </svg>
                    </button>
                    <button class="grid-add-library-btn" title="Add to Library" data-album-id="${album.id}">
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

    private formatArtistCard(artist: ArtistSearchItem): string {
        return `
            <div class="artist-card-compact clickable" data-artist-id="${artist.id}" title="Click to view albums">
                <div class="artist-card-name">${this.escapeHtml(artist.name)}</div>
                <div class="artist-card-image">
                    ${artist.picture 
                        ? `<img src="${this.formatTidalImageUrl(artist.picture, 750)}" alt="${this.escapeHtml(artist.name)}" loading="lazy">`
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
            'HI_RES_LOSSLESS': 'HI-RES FLAC',
            'HIRES_LOSSLESS': 'HI-RES FLAC',
            'LOSSLESS': 'LOSSLESS FLAC',
            'HIGH': 'HIGH AAC',
            'LOW': 'LOW AAC'
        };
        return qualityMap[quality] || quality;
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
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'artist', artistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading artist albums...');

        try {
            const response = await fetch(`/artist/?f=${artistId}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch artist');
            }

            const data: any = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchArtistAlbums(artistId));
                return;
            }

            // Extract albums from data.albums.items
            const albums = data.albums?.items || [];

            if (albums.length === 0) {
                this.displayMessage('No albums found for this artist');
                return;
            }

            // Get artist name and picture from the first album's artist data
            const artistName = albums[0]?.artist?.name || albums[0]?.artists?.[0]?.name || 'Artist';
            const artistPictureId = albums[0]?.artist?.picture || albums[0]?.artists?.[0]?.picture || null;
            const artistPictureUrl = artistPictureId ? this.formatTidalImageUrl(artistPictureId, 750) : null;

            // Display albums with hero card (matching album hero structure)
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
                        <button class="album-action-btn primary" id="artistPlayBtn" title="Play artist" ${albums.length === 0 ? 'disabled' : ''}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"></path></svg>
                        </button>
                        <button class="album-action-btn hero-bottom-right" id="findSimilarArtistBtn" title="Find similar artists" data-artist-id="${artistId}">
                            ${this.getMoreLikeIconSvg()}
                        </button>
                    </div>
                </div>
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>Albums</h2>
                    </div>
                </div>
                <div class="albums-grid-wrapper" data-view-mode="artist-albums">
                    <div class="albums-grid">
                        <div class="albums-grid-header hide-artist">
                            <div class="grid-cell grid-col-artwork"></div>
                            <div class="grid-cell grid-col-title">ALBUM</div>
                            <div class="grid-cell grid-col-year">YEAR</div>
                            <div class="grid-cell grid-col-track-count">TRACKS</div>
                            <div class="grid-cell grid-col-quality">QUALITY</div>
                            <div class="grid-cell grid-col-actions">ACTIONS</div>
                        </div>
                        ${albums.map((album: AlbumSearchItem) => this.formatAlbumGridRow(album, true)).join('')}
                    </div>
                </div>
            `;

            // Attach event listener to play button
            const playBtn = document.getElementById('artistPlayBtn') as HTMLButtonElement;
            if (playBtn) {
                playBtn.addEventListener('click', async () => {
                    // Play the first track from the first album
                    if (albums.length > 0) {
                        const firstAlbumId = albums[0].id;
                        try {
                            const response = await fetch(`/album/?id=${firstAlbumId}`, {
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
        } catch (error) {
            this.displayMessage('Error loading artist albums. Please try again.', () => this.fetchArtistAlbums(artistId));
            console.error('Artist fetch error:', error);
        }
    }

    private async fetchAlbumTracks(albumId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'album';
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'album', albumId });
        }
        this.stopPlayback();
        this.displayMessage('Loading album tracks...');

        try {
            const response = await fetch(`/album/?id=${albumId}`, {
                signal: this.pendingRequestController?.signal
            });

            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }

            const data: AlbumInfo = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`, () => this.fetchAlbumTracks(albumId));
                return;
            }

            // Extract album metadata from data root
            const albumData = data.data;
            if (!albumData) {
                this.displayMessage('No album data found');
                return;
            }

            // Extract tracks from items array
            const trackItems = albumData.items || [];
            const tracks = trackItems
                .filter(item => item.type === 'track')
                .map(item => item.item);

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
                ? this.formatTidalImageUrl(albumData.cover, 1280)
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
        } catch (error) {
            this.displayMessage('Error loading album tracks. Please try again.', () => this.fetchAlbumTracks(albumId));
            console.error('Album fetch error:', error);
        }
    }

    private async fetchSimilarTracks(trackId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_tracks', trackId });
        }
        this.stopPlayback();
        this.displayMessage('Loading track recommendations...');

        try {
            const response = await fetch(`/recommendations/?id=${encodeURIComponent(String(trackId))}`, {
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

    private async fetchSimilarAlbums(albumId: number, updateHistory: boolean = true): Promise<void> {
        this.downloadAllScope = 'loose';
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_albums', albumId });
        }
        this.stopPlayback();
        this.displayMessage('Loading similar albums...');

        try {
            const response = await fetch(`/album/similar/?id=${encodeURIComponent(String(albumId))}`, {
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
                <div class="albums-grid-wrapper" data-view-mode="similar-albums">
                    <div class="albums-grid">
                        <div class="albums-grid-header">
                            <div class="grid-cell grid-col-artwork"></div>
                            <div class="grid-cell grid-col-title">ALBUM</div>
                            <div class="grid-cell grid-col-artist">ARTIST</div>
                            <div class="grid-cell grid-col-year">YEAR</div>
                            <div class="grid-cell grid-col-track-count">TRACKS</div>
                            <div class="grid-cell grid-col-quality">QUALITY</div>
                            <div class="grid-cell grid-col-actions">ACTIONS</div>
                        </div>
                        ${albums.map((album: AlbumSearchItem) => this.formatAlbumGridRow(album, false)).join('')}
                    </div>
                </div>
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
        if (updateHistory) {
            this.pushHistoryRoute({ view: 'similar_artists', artistId });
        }
        this.stopPlayback();
        this.displayMessage('Loading similar artists...');

        try {
            const response = await fetch(`/artist/similar/?id=${encodeURIComponent(String(artistId))}`, {
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
            console.log(`[DOWNLOAD] Calling downloadTrackToLibrary with format: ${this.downloadSettings.format}`);
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
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || `HTTP ${response.status}`;
                console.error(`[PLAYLIST] Failed to fetch playlists: ${errorMsg}`);
                throw new Error(errorMsg);
            }

            const data = await response.json();
            return data.playlists || [];
        } catch (error) {
            console.error('[PLAYLIST] Error fetching playlists:', error);
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
            console.log(`[PLAYLIST] Settings: format=${this.downloadSettings.format}`);
            console.log(`[PLAYLIST] Download type: ${downloadType}, Playlist: ${playlistName}`);
            
            const plexUserId = this.getSelectedPlexUserId();
            const response = await this.fetchWithRetry('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trackId,
                    format: this.downloadSettings.format,
                    downloadType,
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
            const response = await fetch(`/album/?id=${albumId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }
            const albumData: AlbumInfo = await response.json();
            const trackItems = albumData.data?.items || [];
            const tracks = trackItems.filter(item => item.type === 'track').map(item => item.item);

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
            const response = await fetch(`/album/?id=${albumId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }
            const albumData: AlbumInfo = await response.json();
            const trackItems = albumData.data?.items || [];
            const tracks = trackItems.filter(item => item.type === 'track').map(item => item.item);

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
            const response = await fetch(`/album/?id=${albumId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }
            const albumData: AlbumInfo = await response.json();
            const trackItems = albumData.data?.items || [];
            const tracks = trackItems.filter(item => item.type === 'track').map(item => item.item);

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

    private formatAlbumsGrid(albums: AlbumSearchItem[]): string {
        return `
            <div class="albums-grid-wrapper" data-view-mode="search-albums">
                <div class="albums-grid">
                    <div class="albums-grid-header">
                        <div class="grid-cell grid-col-artwork"></div>
                        <div class="grid-cell grid-col-title">ALBUM</div>
                        <div class="grid-cell grid-col-artist">ARTIST</div>
                        <div class="grid-cell grid-col-year">YEAR</div>
                        <div class="grid-cell grid-col-track-count">TRACKS</div>
                        <div class="grid-cell grid-col-quality">QUALITY</div>
                        <div class="grid-cell grid-col-actions">ACTIONS</div>
                    </div>
                    ${albums.map((album: AlbumSearchItem) => this.formatAlbumGridRow(album, false)).join('')}
                </div>
            </div>
        `;
    }

private async downloadTrackToLibrary(
        trackId: number,
        downloadType: 'album' | 'loose'
    ): Promise<number> {
        try {
            console.log(`[DOWNLOAD] Sending download-to-library request for track ${trackId}`);
            console.log(`[DOWNLOAD] Settings: format=${this.downloadSettings.format}`);
            console.log(`[DOWNLOAD] Download type: ${downloadType}`);
            
            const response = await this.fetchWithRetry('/api/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            trackId,
                            format: this.downloadSettings.format,
                            downloadType,
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
            console.log(`[DOWNLOAD] Settings: format=${this.downloadSettings.format}`);
            console.log(`[DOWNLOAD] Download type: ${downloadType}`);
            
            const plexUserId = this.getSelectedPlexUserId();
            const response = await this.fetchWithRetry('/api/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            trackId,
                            format: this.downloadSettings.format,
                            downloadType,
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
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
