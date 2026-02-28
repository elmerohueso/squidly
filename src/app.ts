// Main TypeScript entry point

interface SearchResult {
    query: string;
    data?: {
        items?: (Track | AlbumSearchItem)[];
        albums?: {
            items: AlbumSearchItem[];
        };
        artists?: {
            items: ArtistSearchItem[];
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
    duration?: number;
    artists?: Artist[];
    artist?: Artist;
    album?: Album;
    quality?: string;
    audioQuality?: string;
    cover?: string;
    trackNumber?: number;
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
    duration?: number;
    audioQuality?: string;
    mediaMetadata?: {
        tags?: string[];
    };
}

interface ArtistSearchItem {
    id: number;
    name: string;
    picture?: string;
    popularity?: number;
    artistTypes?: string[];
}

interface AlbumInfo {
    data?: {
        id: number;
        title: string;
        cover?: string;
        artist?: Artist;
        artists?: Artist[];
        releaseDate?: string;
        numberOfTracks?: number;
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

interface EndpointStatus {
    endpoints: Endpoint[];
    summary: {
        total: number;
        online: number;
        offline: number;
    };
}

interface JobStageMap {
    downloaded?: string;
    id3_tagged?: string;
    converted?: string;
    written?: string;
    playlist_added?: string;
}

interface JobResult {
    artist?: string;
    title?: string;
    album?: string;
    playlist_name?: string | null;
    stages?: JobStageMap;
}

interface JobItem {
    id: number;
    job_type: string;
    status: string;
    payload?: Record<string, any> | null;
    result?: JobResult | null;
    error_message?: string | null;
}

type DownloadFormat = 'original' | 'mp3';
type StreamQuality = 'high' | 'low';

interface DownloadSettings {
    format: DownloadFormat;
    fileNamingLoose: string;
    fileNamingAlbum: string;
}

class App {
    private static readonly NEW_PLEX_PLAYLIST_OPTION = '__new_playlist__';
    private searchInput: HTMLInputElement;
    private searchTypeSelect: HTMLSelectElement;
    private searchButton: HTMLButtonElement;
    private resultsContainer: HTMLElement;
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
    private jobsContent: HTMLElement;
    private settingsButton: HTMLButtonElement;
    private settingsFlyout: HTMLElement;
    private settingsOverlay: HTMLElement;
    private closeSettingsButton: HTMLButtonElement;
    private formatOriginalInput: HTMLInputElement;
    private formatMp3Input: HTMLInputElement;
    private fileNamingAlbumInput: HTMLInputElement;
    private fileNamingLooseInput: HTMLInputElement;
    private streamQualityHighInput: HTMLInputElement;
    private streamQualityLowInput: HTMLInputElement;
    private listenbrainzTokenInput: HTMLInputElement;
    private saveLbConfigButton: HTMLButtonElement;
    private lbConfigStatusEl: HTMLElement;
    private plexServerUrlInput: HTMLInputElement;
    private plexApiTokenInput: HTMLInputElement;
    private plexLibraryNameSelect: HTMLSelectElement;
    private plexPlaylistContainer: HTMLElement;
    private plexPlaylistContainerHomeParent: HTMLElement;
    private plexPlaylistContainerHomeNextSibling: ChildNode | null;
    private plexPlaylistNameInput: HTMLInputElement;
    private plexPlaylistOptions: HTMLSelectElement;
    private plexPlaylistBackButton: HTMLButtonElement;
    private savePlexConfigButton: HTMLButtonElement;
    private testPlexConnectionButton: HTMLButtonElement;
    private plexConfigStatusEl: HTMLElement;
    private downloadSettings: DownloadSettings;
    private streamQuality: StreamQuality = 'high';
    private settingsSaveTimer: number | null = null;
    private readonly settingsSaveDelayMs = 500;
    private statusUpdateInterval: number | null = null;
    private jobStatusInterval: number | null = null;
    private jobStatusPolling = false;
    private activeJobMap = new Map<number, {
        trackCard: HTMLElement;
        downloadBtn: HTMLButtonElement;
        statusEl: HTMLElement;
    }>();
    private jobsUpdateInterval: number | null = null;
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

    constructor() {
        this.searchInput = document.getElementById('searchInput') as HTMLInputElement;
        this.searchTypeSelect = document.getElementById('searchType') as HTMLSelectElement;
        this.searchButton = document.getElementById('searchButton') as HTMLButtonElement;
        this.resultsContainer = document.getElementById('results') as HTMLElement;
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
        this.jobsContent = document.getElementById('jobsContent') as HTMLElement;
        this.settingsButton = document.getElementById('settingsButton') as HTMLButtonElement;
        this.settingsFlyout = document.getElementById('settingsFlyout') as HTMLElement;
        this.settingsOverlay = document.getElementById('settingsOverlay') as HTMLElement;
        this.closeSettingsButton = document.getElementById('closeSettings') as HTMLButtonElement;
        this.formatOriginalInput = document.getElementById('formatOriginal') as HTMLInputElement;
        this.formatMp3Input = document.getElementById('formatMp3') as HTMLInputElement;
        this.fileNamingAlbumInput = document.getElementById('fileNamingAlbum') as HTMLInputElement;
        this.fileNamingLooseInput = document.getElementById('fileNamingLoose') as HTMLInputElement;
        this.streamQualityHighInput = document.getElementById('streamQualityHigh') as HTMLInputElement;
        this.streamQualityLowInput = document.getElementById('streamQualityLow') as HTMLInputElement;
        this.listenbrainzTokenInput = document.getElementById('listenbrainzToken') as HTMLInputElement;
        this.saveLbConfigButton = document.getElementById('saveLbConfig') as HTMLButtonElement;
        this.lbConfigStatusEl = document.getElementById('lbConfigStatus') as HTMLElement;
        this.plexServerUrlInput = document.getElementById('plexServerUrl') as HTMLInputElement;
        this.plexApiTokenInput = document.getElementById('plexApiToken') as HTMLInputElement;
        this.plexLibraryNameSelect = document.getElementById('plexLibraryName') as HTMLSelectElement;
        this.plexPlaylistContainer = document.getElementById('plexPlaylistContainer') as HTMLElement;
        this.plexPlaylistContainerHomeParent = this.plexPlaylistContainer.parentElement as HTMLElement;
        this.plexPlaylistContainerHomeNextSibling = this.plexPlaylistContainer.nextSibling;
        this.plexPlaylistNameInput = document.getElementById('plexPlaylistName') as HTMLInputElement;
        this.plexPlaylistOptions = document.getElementById('plexPlaylistOptions') as HTMLSelectElement;
        this.plexPlaylistBackButton = document.getElementById('plexPlaylistBack') as HTMLButtonElement;
        this.savePlexConfigButton = document.getElementById('savePlexConfig') as HTMLButtonElement;
        this.testPlexConnectionButton = document.getElementById('testPlexConnection') as HTMLButtonElement;
        this.plexConfigStatusEl = document.getElementById('plexConfigStatus') as HTMLElement;
        
        this.initializeEventListeners();
        this.streamQuality = this.loadStreamQualityFromCookie();
        this.downloadSettings = this.defaultDownloadSettings();
        this.applySettingsToForm(this.downloadSettings);
        this.applyStreamQualityToForm();
        void this.fetchDownloadSettingsFromServer();
        void this.loadListenbrainzConfig();
        void this.loadPlexConfig();
        this.updateEndpointStatus(); // Initial load
        
        // Update status every 30 seconds
        this.statusUpdateInterval = window.setInterval(() => {
            this.updateEndpointStatus();
        }, 30000);
    }

    private initializeEventListeners(): void {
        this.searchButton.addEventListener('click', () => this.handleSearch());
        this.searchInput.addEventListener('keypress', (e: KeyboardEvent) => {
            if (e.key === 'Enter') {
                this.handleSearch();
            }
        });

        this.statusButton.addEventListener('click', () => this.openFlyout());
        this.closeFlyoutButton.addEventListener('click', () => this.closeFlyout());
        this.flyoutOverlay.addEventListener('click', () => this.closeFlyout());

        this.jobsButton.addEventListener('click', () => this.openJobsFlyout());
        this.closeJobsButton.addEventListener('click', () => this.closeJobsFlyout());
        this.jobsOverlay.addEventListener('click', () => this.closeJobsFlyout());
        this.jobsFilterSelect.addEventListener('change', () => this.loadJobs());

        this.settingsButton.addEventListener('click', () => this.openSettingsFlyout());
        this.closeSettingsButton.addEventListener('click', () => this.closeSettingsFlyout());
        this.settingsOverlay.addEventListener('click', () => this.closeSettingsFlyout());

        this.formatOriginalInput.addEventListener('change', () => this.updateSettingsFromForm());
        this.formatMp3Input.addEventListener('change', () => this.updateSettingsFromForm());
        this.fileNamingAlbumInput.addEventListener('input', () => this.updateSettingsFromForm());
        this.fileNamingLooseInput.addEventListener('input', () => this.updateSettingsFromForm());
        this.streamQualityHighInput.addEventListener('change', () => this.updateStreamQualityFromForm());
        this.streamQualityLowInput.addEventListener('change', () => this.updateStreamQualityFromForm());
        this.saveLbConfigButton.addEventListener('click', () => this.saveListenbrainzConfig());
        this.savePlexConfigButton.addEventListener('click', () => this.savePlexConfig());
        this.testPlexConnectionButton.addEventListener('click', () => this.testPlexConnection());
        this.plexPlaylistOptions.addEventListener('change', () => {
            const selectedName = this.plexPlaylistOptions.value.trim();
            if (selectedName === App.NEW_PLEX_PLAYLIST_OPTION) {
                this.setPlexPlaylistMode('new');
                this.plexPlaylistNameInput.value = '';
                this.plexPlaylistNameInput.focus();
                return;
            }

            if (selectedName) {
                this.plexPlaylistNameInput.value = selectedName;
            }

            this.setPlexPlaylistMode('existing');
        });
        this.plexPlaylistBackButton.addEventListener('click', () => {
            this.setPlexPlaylistMode('existing');
            this.plexPlaylistOptions.value = '';
            this.plexPlaylistNameInput.value = '';
        });

        // Update placeholder text based on search type
        this.searchTypeSelect.addEventListener('change', () => this.updateSearchPlaceholder());

        // Download button and album card click delegation
        this.resultsContainer.addEventListener('click', (e: MouseEvent) => {
            const target = e.target as HTMLElement;

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
            
            // Check for download button clicks first
            const downloadBtn = target.closest('.track-download-btn');
            if (downloadBtn) {
                const trackCard = downloadBtn.closest('.track-card') as HTMLElement;
                const trackId = trackCard?.getAttribute('data-track-id');
                if (trackId) {
                    void this.handleDownload(parseInt(trackId, 10), trackCard, 'loose');
                }
                return; // Stop here if it was a download button
            }
            
            // Check for artist name clicks within track cards
            const artistName = target.closest('.track-artist-name');
            if (artistName) {
                const trackCard = artistName.closest('.track-card');
                const artistId = trackCard?.getAttribute('data-artist-id');
                if (artistId) {
                    e.stopPropagation();
                    void this.fetchArtistAlbums(parseInt(artistId, 10));
                    return;
                }
            }
            
            // Check for album name clicks within track cards
            const albumName = target.closest('.track-album-name');
            if (albumName) {
                const trackCard = albumName.closest('.track-card');
                const albumId = trackCard?.getAttribute('data-album-id');
                if (albumId) {
                    e.stopPropagation();
                    void this.fetchAlbumTracks(parseInt(albumId, 10));
                    return;
                }
            }
            
            // Check for playlist card clicks
            const playlistCard = target.closest('.playlist-card');
            if (playlistCard) {
                const playlistId = playlistCard.getAttribute('data-playlist-id');
                if (playlistId) {
                    void this.fetchListenbrainzPlaylistTracks(playlistId);
                    return;
                }
            }
            
            // Check for album card clicks (albums have both track-card and album-card classes)
            const clickedCard = target.closest('.track-card') as HTMLElement;
            if (clickedCard && clickedCard.classList.contains('album-card')) {
                const albumId = clickedCard.getAttribute('data-album-id');
                if (albumId) {
                    void this.fetchAlbumTracks(parseInt(albumId, 10));
                }
            }
            
            // Check for artist card clicks
            if (clickedCard && clickedCard.classList.contains('artist-card')) {
                const artistId = clickedCard.getAttribute('data-artist-id');
                if (artistId) {
                    void this.fetchArtistAlbums(parseInt(artistId, 10));
                }
            }
        });
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
        void this.loadJobs();
        if (!this.jobsUpdateInterval) {
            this.jobsUpdateInterval = window.setInterval(() => {
                void this.loadJobs();
            }, 30000);
        }
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

        try {
            const response = await fetch('/api/jobs?job_type=download_track&limit=100');
            if (!response.ok) {
                throw new Error('Failed to fetch jobs');
            }

            const data = await response.json();
            const jobs = Array.isArray(data.jobs) ? (data.jobs as JobItem[]) : [];
            const filtered = this.filterJobsByStatus(jobs, filter);
            this.renderJobs(filtered);
        } catch (error) {
            this.jobsContent.innerHTML = '<p class="loading-text">Failed to load jobs.</p>';
            console.error('Jobs load error:', error);
        }
    }

    private filterJobsByStatus(jobs: JobItem[], filter: string): JobItem[] {
        if (filter === 'complete') {
            return jobs.filter(job => ['succeeded', 'cancelled', 'failed'].includes(job.status));
        }

        return jobs.filter(job => ['queued', 'in_progress'].includes(job.status));
    }

    private renderJobs(jobs: JobItem[]): void {
        if (jobs.length === 0) {
            this.jobsContent.innerHTML = '<p class="loading-text">No jobs found.</p>';
            return;
        }

        this.jobsContent.innerHTML = jobs.map(job => this.renderJobItem(job)).join('');
    }

    private renderJobItem(job: JobItem): string {
        const title = this.getJobDisplayTitle(job);
        const statusLabel = this.formatJobStatus(job.status);
        const statusClass = `status-${job.status.replace('_', '-')}`;
        const stages = job.result?.stages || {};
        const playlistName = job.result?.playlist_name || job.payload?.plex_playlist || null;

        const stageRows = [
            { key: 'downloaded', label: 'Downloaded' },
            { key: 'id3_tagged', label: 'ID3 Tag Created' },
            { key: 'converted', label: 'Converted to MP3' },
            { key: 'written', label: 'Written to Disk' },
            {
                key: 'playlist_added',
                label: playlistName ? `Added to Playlist "${this.escapeHtml(String(playlistName))}"` : 'Added to Playlist'
            }
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
        }).join('');

        return `
            <div class="job-item">
                <div class="job-main">
                    <div class="job-title">${this.escapeHtml(title)}</div>
                    <div class="job-status ${statusClass}">${statusLabel}</div>
                </div>
                <div class="job-stages">
                    ${stageHtml}
                </div>
            </div>
        `;
    }

    private getJobDisplayTitle(job: JobItem): string {
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
        return status.charAt(0).toUpperCase() + status.slice(1);
    }

    private resolveStageStatus(job: JobItem, key: keyof JobStageMap, stages: JobStageMap): string {
        const value = stages[key];
        if (value) {
            return value;
        }

        if (job.status === 'succeeded') {
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
            fileNamingLoose: '{artist}/{album}/{track} - {title}.{ext}',
            fileNamingAlbum: '{artist}/{album}/{track} - {title}.{ext}'
        };
    }

    private normalizeSettings(raw: Partial<DownloadSettings>): DownloadSettings {
        const fallback = this.defaultDownloadSettings();
        const fileNaming = (raw as { file_naming?: string }).file_naming;
        const fileNamingLoose = (raw as { file_naming_loose?: string }).file_naming_loose;
        const fileNamingAlbum = (raw as { file_naming_album?: string }).file_naming_album;
        const legacyFileNaming = (raw as { fileNaming?: string }).fileNaming;

        return {
            format: raw.format === 'mp3' ? 'mp3' : 'original',
            fileNamingLoose: typeof (raw as DownloadSettings).fileNamingLoose === 'string'
                ? (raw as DownloadSettings).fileNamingLoose
                : typeof fileNamingLoose === 'string'
                    ? fileNamingLoose
                    : typeof legacyFileNaming === 'string'
                        ? legacyFileNaming
                        : typeof fileNaming === 'string'
                            ? fileNaming
                            : fallback.fileNamingLoose,
            fileNamingAlbum: typeof (raw as DownloadSettings).fileNamingAlbum === 'string'
                ? (raw as DownloadSettings).fileNamingAlbum
                : typeof fileNamingAlbum === 'string'
                    ? fileNamingAlbum
                    : typeof legacyFileNaming === 'string'
                        ? legacyFileNaming
                        : typeof fileNaming === 'string'
                            ? fileNaming
                            : fallback.fileNamingAlbum
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
        this.fileNamingLooseInput.value = settings.fileNamingLoose;
        this.syncFormatToggleStyles();
    }

    private applyStreamQualityToForm(): void {
        this.streamQualityHighInput.checked = this.streamQuality === 'high';
        this.streamQualityLowInput.checked = this.streamQuality === 'low';
        this.syncStreamQualityToggleStyles();
    }

    private readSettingsFromForm(): DownloadSettings {
        return {
            format: this.formatMp3Input.checked ? 'mp3' : 'original',
            fileNamingAlbum: this.fileNamingAlbumInput.value.trim(),
            fileNamingLoose: this.fileNamingLooseInput.value.trim()
        };
    }

    private updateSettingsFromForm(): void {
        this.downloadSettings = this.readSettingsFromForm();
        this.queueSettingsSave();
        this.syncFormatToggleStyles();
    }

    private updateStreamQualityFromForm(): void {
        this.streamQuality = this.streamQualityHighInput.checked ? 'high' : 'low';
        this.saveStreamQualityToCookie(this.streamQuality);
        this.syncStreamQualityToggleStyles();
    }

    private loadStreamQualityFromCookie(): StreamQuality {
        const value = this.getCookieValue('streamQuality');
        return value === 'low' ? 'low' : 'high';
    }

    private saveStreamQualityToCookie(quality: StreamQuality): void {
        const maxAgeSeconds = 60 * 60 * 24 * 365;
        document.cookie = `streamQuality=${quality}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`;
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

    private syncStreamQualityToggleStyles(): void {
        const highLabel = this.streamQualityHighInput.closest('label');
        const lowLabel = this.streamQualityLowInput.closest('label');

        if (highLabel) {
            highLabel.classList.toggle('active', this.streamQualityHighInput.checked);
        }

        if (lowLabel) {
            lowLabel.classList.toggle('active', this.streamQualityLowInput.checked);
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
                if (data.server_url) {
                    this.plexServerUrlInput.value = data.server_url;
                }
                
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
                
                if (data.has_config) {
                    this.plexApiTokenInput.value = 'Configured';
                }
                this.isPlexConfigured = data.has_config ? true : false;
                this.updatePlexConfigStatus(data.has_config ? '✓ Configured' : '');
                this.updatePlexPlaylistContainerVisibility(false);
                if (this.isPlexConfigured) {
                    void this.loadPlexPlaylists();
                } else {
                    this.populatePlexPlaylistOptions([]);
                }
            }
        } catch (error) {
            console.warn('Failed to load Plex config.', error);
        }
    }

    private async testPlexConnection(): Promise<void> {
        const serverUrl = this.plexServerUrlInput.value.trim();
        const apiToken = this.plexApiTokenInput.value.trim();

        if (!serverUrl || !apiToken) {
            this.updatePlexConfigStatus('⚠ Server URL and X-Plex-Token are required');
            return;
        }

        this.updatePlexConfigStatus('Testing connection...');
        this.testPlexConnectionButton.disabled = true;

        try {
            const response = await fetch('/api/plex/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    server_url: serverUrl,
                    api_token: apiToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.updatePlexConfigStatus('✓ Connection successful!');
                
                // Populate library dropdown
                this.plexLibraryNameSelect.innerHTML = '';
                if (data.libraries && data.libraries.length > 0) {
                    const defaultOption = document.createElement('option');
                    defaultOption.value = '';
                    defaultOption.textContent = 'Select a library...';
                    this.plexLibraryNameSelect.appendChild(defaultOption);
                    
                    data.libraries.forEach((lib: string) => {
                        const option = document.createElement('option');
                        option.value = lib;
                        option.textContent = lib;
                        this.plexLibraryNameSelect.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.value = 'Music';
                    option.textContent = 'Music (default)';
                    this.plexLibraryNameSelect.appendChild(option);
                }
            } else {
                const data = await response.json();
                this.updatePlexConfigStatus(`✗ ${data.message || 'Connection failed'}`);
            }
        } catch (error) {
            console.error('Error testing Plex connection:', error);
            this.updatePlexConfigStatus('✗ Error testing connection');
        } finally {
            this.testPlexConnectionButton.disabled = false;
        }
    }

    private async savePlexConfig(): Promise<void> {
        const serverUrl = this.plexServerUrlInput.value.trim();
        const apiToken = this.plexApiTokenInput.value.trim();
        const libraryName = this.plexLibraryNameSelect.value.trim();

        if (!serverUrl || !apiToken || !libraryName) {
            this.updatePlexConfigStatus('⚠ Server URL, X-Plex-Token, and library name are required');
            return;
        }

        try {
            const response = await fetch('/api/plex/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    server_url: serverUrl,
                    api_token: apiToken,
                    library_name: libraryName
                })
            });

            if (response.ok) {
                this.updatePlexConfigStatus('✓ Configuration saved');
                this.isPlexConfigured = true;
                void this.loadPlexPlaylists();
                this.plexApiTokenInput.value = '';
                setTimeout(() => {
                    this.updatePlexConfigStatus('✓ Configured');
                }, 3000);
            } else {
                this.updatePlexConfigStatus('✗ Failed to save configuration');
            }
        } catch (error) {
            console.error('Error saving Plex config:', error);
            this.updatePlexConfigStatus('✗ Error saving configuration');
        }
    }

    private updatePlexConfigStatus(message: string): void {
        this.plexConfigStatusEl.textContent = message;
        this.plexConfigStatusEl.style.color = message.includes('✓') ? 'var(--accent-primary)' : 'var(--text-secondary)';
    }

    private updatePlexPlaylistContainerVisibility(show: boolean): void {
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
        const downloadAllBtn = this.resultsContainer.querySelector('#downloadAllBtn') as HTMLElement | null;
        if (!downloadAllBtn || !downloadAllBtn.parentElement) {
            return;
        }

        const headerTop = downloadAllBtn.parentElement;
        const header = headerTop.parentElement;
        if (header) {
            header.insertBefore(this.plexPlaylistContainer, headerTop.nextSibling);
        } else {
            headerTop.insertBefore(this.plexPlaylistContainer, downloadAllBtn.nextSibling);
        }
        this.plexPlaylistContainer.style.padding = '0';
        this.plexPlaylistContainer.style.marginTop = '0.75rem';
    }

    private restorePlexPlaylistContainerToHome(): void {
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
        defaultOption.textContent = 'Select existing...';
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

    private async loadPlexPlaylists(): Promise<void> {
        if (!this.isPlexConfigured) {
            this.populatePlexPlaylistOptions([]);
            return;
        }

        try {
            const response = await fetch('/api/plex/playlists');
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

        // Update endpoint list
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
                    </div>
                </div>
            `;
        }).join('');
    }

    private updateSearchPlaceholder(): void {
        const searchType = this.searchTypeSelect.value;
        if (searchType === 'lastfm') {
            this.searchInput.placeholder = 'Enter Last.fm playlist URL...';
        } else if (searchType === 'listenbrainz') {
            this.searchInput.placeholder = 'Enter ListenBrainz username...';
        } else if (searchType === 'a') {
            this.searchInput.placeholder = 'Search for artists...';
        } else if (searchType === 'al') {
            this.searchInput.placeholder = 'Search for albums...';
        } else {
            this.searchInput.placeholder = 'Search for tracks...';
        }
    }

    private async handleSearch(): Promise<void> {
        const searchType = this.searchTypeSelect.value;
        const query = this.searchInput.value.trim();
        
        if (searchType === 'listenbrainz') {
            // Handle ListenBrainz playlists without requiring query
            await this.handleListenbrainzPlaylists();
            return;
        }

        if (!query) {
            this.displayMessage('Please enter a search query');
            return;
        }

        if (searchType === 'lastfm') {
            // Handle Last.fm playlist with progressive search
            await this.handleLastfmPlaylist(query);
            return;
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

    private async handleLastfmPlaylist(playlistUrl: string): Promise<void> {
        this.downloadAllScope = 'loose';
        this.displayMessage('Scraping Last.fm playlist...');

        try {
            // First, scrape the playlist to get track list
            const scrapeResponse = await fetch('/api/lastfm/playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ playlistUrl })
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

            // Set up progress display
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>Last.fm Playlist - "${this.escapeHtml(playlistName)}"</h2>
                    </div>
                    <div class="progress-info">
                        <div class="progress-bar-container">
                            <div class="progress-bar" id="lastfmProgress" style="width: 0%"></div>
                        </div>
                        <p class="progress-text" id="progressText">Searching for tracks: <span id="progressCount">0</span> / ${totalTracks}</p>
                    </div>
                </div>
                <div class="results-list" id="lastfmResultsList"></div>
            `;

            const resultsList = document.getElementById('lastfmResultsList');
            const progressBar = document.getElementById('lastfmProgress');
            const progressCount = document.getElementById('progressCount');
            let foundCount = 0;

            // Search for each track progressively
            for (let i = 0; i < tracks.length; i++) {
                const track = tracks[i];
                const searchQuery = `${track.name} ${track.artist}`;

                try {
                    const searchResponse = await fetch(`/search/?s=${encodeURIComponent(searchQuery)}`);
                    
                    if (searchResponse.ok) {
                        const searchData = await searchResponse.json();
                        const items = searchData.data?.items || [];
                        
                        if (items.length > 0) {
                            // Add the first match to results
                            const trackCard = this.formatTrackCard(items[0]);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackCard);
                            }
                            foundCount++;
                        }
                    }
                } catch (error) {
                    console.error(`Failed to search for ${searchQuery}:`, error);
                }

                // Update progress
                const progress = ((i + 1) / totalTracks) * 100;
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                }
                if (progressCount) {
                    progressCount.textContent = (i + 1).toString();
                }
            }

            // Update final message
            const progressText = document.getElementById('progressText');
            if (progressText) {
                progressText.innerHTML = `Found <strong>${foundCount}</strong> of <strong>${totalTracks}</strong> tracks`;
            }

            // Create and add Download All button after searching is complete
            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement;
            if (resultsHeaderTop) {
                const downloadAllBtn = document.createElement('button');
                downloadAllBtn.id = 'downloadAllBtn';
                downloadAllBtn.className = 'download-all-btn';
                downloadAllBtn.title = 'Download all tracks sequentially';
                downloadAllBtn.textContent = 'Download All';
                downloadAllBtn.addEventListener('click', () => this.downloadAllTracks());
                resultsHeaderTop.appendChild(downloadAllBtn);
                this.movePlexPlaylistContainerBeneathDownloadAll();
            }

        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to process Last.fm playlist'}`);
            console.error('Last.fm playlist error:', error);
        }
    }

    private async handleListenbrainzPlaylists(): Promise<void> {
        const username = this.searchInput.value.trim();
        
        if (!username) {
            this.displayMessage('Please enter ListenBrainz username');
            return;
        }

        this.displayMessage('Loading ListenBrainz playlists...');

        try {
            const response = await fetch(`/api/listenbrainz/playlists?username=${encodeURIComponent(username)}`);
            
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

    private async fetchListenbrainzPlaylistTracks(playlistId: string): Promise<void> {
        this.downloadAllScope = 'loose';
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
            const response = await fetch(`/api/listenbrainz/playlist/${encodeURIComponent(playlistMbid)}`);

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
                    <div class="progress-info">
                        <div class="progress-bar-container">
                            <div class="progress-bar" id="lastfmProgress" style="width: 0%"></div>
                        </div>
                        <p class="progress-text" id="progressText">Searching for tracks: <span id="progressCount">0</span> / ${tracks.length}</p>
                    </div>
                </div>
                <div class="results-list" id="listenbrainzResultsList"></div>
            `;

            const resultsList = document.getElementById('listenbrainzResultsList');
            const progressBar = document.getElementById('lastfmProgress');
            const progressCount = document.getElementById('progressCount');
            let foundCount = 0;

            // Search for each track progressively
            for (let i = 0; i < tracks.length; i++) {
                const lbTrack = tracks[i];
                const artists = lbTrack.creator || 'Unknown';
                const searchQuery = `${lbTrack.title} ${artists}`;

                try {
                    const searchResponse = await fetch(`/search/?s=${encodeURIComponent(searchQuery)}`);
                    
                    if (searchResponse.ok) {
                        const searchData = await searchResponse.json();
                        const items = searchData.data?.items || [];
                        
                        if (items.length > 0) {
                            // Add the first match to results
                            const trackCard = this.formatTrackCard(items[0], false);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackCard);
                            }
                            foundCount++;
                        }
                    }
                } catch (error) {
                    console.error(`Failed to search for ${searchQuery}:`, error);
                }

                // Update progress
                const progress = ((i + 1) / tracks.length) * 100;
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                }
                if (progressCount) {
                    progressCount.textContent = (i + 1).toString();
                }
            }

            // Update final message
            const progressText = document.getElementById('progressText');
            if (progressText) {
                progressText.innerHTML = `Found <strong>${foundCount}</strong> of <strong>${tracks.length}</strong> tracks`;
            }

            // Create and add Download All button after searching is complete
            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement;
            if (resultsHeaderTop) {
                const downloadAllBtn = document.createElement('button');
                downloadAllBtn.id = 'downloadAllBtn';
                downloadAllBtn.className = 'download-all-btn';
                downloadAllBtn.title = 'Download all tracks sequentially';
                downloadAllBtn.textContent = 'Download All';
                downloadAllBtn.addEventListener('click', () => this.downloadAllTracks());
                resultsHeaderTop.appendChild(downloadAllBtn);
                this.movePlexPlaylistContainerBeneathDownloadAll();
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
        this.updatePlexPlaylistContainerVisibility(searchType === 's');
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
                              searchType === 'p' ? 'Playlists' : 'Results';

        this.resultsContainer.innerHTML = `
            <div class="results-header">
                <h2>${searchTypeName} - "${this.escapeHtml(query)}"</h2>
                ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
            </div>
            <div class="results-list">
                ${items.map(item => {
                    if (searchType === 'al') return this.formatAlbumCard(item as AlbumSearchItem);
                    if (searchType === 'a') return this.formatArtistCard(item as ArtistSearchItem);
                    return this.formatTrackCard(item as Track);
                }).join('')}
            </div>
        `;
    }

    private formatTrackCard(track: Track, showTrackNumber: boolean = false): string {
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
            // Prioritize: HIRES_LOSSLESS > LOSSLESS > LOW
            const tags = track.mediaMetadata.tags;
            if (tags.includes('HIRES_LOSSLESS')) {
                quality = 'HIRES_LOSSLESS';
            } else if (tags.includes('LOSSLESS')) {
                quality = 'LOSSLESS';
            } else if (tags.includes('LOW')) {
                quality = 'LOW';
            }
        }
        const qualityDisplay = this.formatQuality(quality);

        // Format track title with optional track number
        const trackTitle = showTrackNumber && track.trackNumber
            ? `${track.trackNumber}. ${this.escapeHtml(track.title)}`
            : this.escapeHtml(track.title);

        return `
            <div class="track-card" data-track-id="${track.id}" ${primaryArtistId ? `data-artist-id="${primaryArtistId}"` : ''} ${albumId ? `data-album-id="${albumId}"` : ''}>
                <button class="track-play-btn" title="Play" aria-label="Play" aria-pressed="false" data-track-id="${track.id}">
                    ${this.getPlayIconSvg()}
                </button>
                <div class="track-artwork">
                    ${albumCover 
                        ? `<img src="${this.formatAlbumCoverUrl(albumCover)}" alt="${track.title}" loading="lazy">`
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
                    </div>
                </div>
                <div class="track-actions">
                    <button class="track-download-btn" title="Download" data-track-id="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
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
        const qualities = this.streamQuality === 'high'
            ? ['HIGH']
            : ['LOW'];

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
        const trackCount = album.numberOfTracks 
            ? `${album.numberOfTracks} track${album.numberOfTracks !== 1 ? 's' : ''}`
            : '';

        // Format audio quality if available - check mediaMetadata.tags for best quality
        let quality = album.audioQuality || '';
        if (album.mediaMetadata?.tags && album.mediaMetadata.tags.length > 0) {
            // Prioritize: HIRES_LOSSLESS > LOSSLESS > LOW
            const tags = album.mediaMetadata.tags;
            if (tags.includes('HIRES_LOSSLESS')) {
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
                        ? `<img src="${this.formatAlbumCoverUrl(album.cover)}" alt="${album.title}" loading="lazy">`
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
                    </div>
                </div>
            </div>
        `;
    }

    private formatArtistCard(artist: ArtistSearchItem): string {
        // Format popularity
        const popularity = artist.popularity ? `Popularity: ${artist.popularity}` : '';

        return `
            <div class="track-card artist-card clickable" data-artist-id="${artist.id}" title="Click to view albums">
                <div class="track-artwork">
                    ${artist.picture 
                        ? `<img src="${this.formatArtistPictureUrl(artist.picture)}" alt="${artist.name}" loading="lazy">`
                        : `<div class="track-artwork-placeholder">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="8" r="4"></circle>
                                <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"></path>
                            </svg>
                           </div>`
                    }
                </div>
                <div class="track-info">
                    <div class="track-title">${this.escapeHtml(artist.name)}</div>
                    <div class="track-artist">Artist</div>
                    <div class="track-metadata">
                        ${popularity ? `<span>${popularity}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    private formatDuration(seconds: number): string {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    private formatQuality(quality: string): string {
        const qualityMap: { [key: string]: string } = {
            'HIRES_LOSSLESS': 'Hi-Res • up to 24-bit/192kHz FLAC',
            'LOSSLESS': 'CD • 16-bit/44.1kHz FLAC',
            'LOW': '320kbps AAC'
        };
        return qualityMap[quality] || quality;
    }

    private formatAlbumCoverUrl(cover: string): string {
        // Convert dashes to forward slashes for Tidal CDN format
        const coverPath = cover.replace(/-/g, '/');
        return `https://resources.tidal.com/images/${coverPath}/1280x1280.jpg`;
    }

    private formatArtistPictureUrl(picture: string): string {
        // Convert dashes to forward slashes for Tidal CDN format
        const picturePath = picture.replace(/-/g, '/');
        return `https://resources.tidal.com/images/${picturePath}/750x750.jpg`;
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
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const response = await fetch(url, options);
                
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

    private async fetchArtistAlbums(artistId: number): Promise<void> {
        this.downloadAllScope = 'loose';
        this.stopPlayback();
        this.displayMessage('Loading artist albums...');

        try {
            const response = await fetch(`/artist/?f=${artistId}`);

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

            // Get artist name from the first album's artist data
            const artistName = albums[0]?.artist?.name || albums[0]?.artists?.[0]?.name || 'Artist';

            // Display albums
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(artistName)} - Albums</h2>
                    </div>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                </div>
                <div class="results-list">
                    ${albums.map((album: AlbumSearchItem) => this.formatAlbumCard(album)).join('')}
                </div>
            `;
        } catch (error) {
            this.displayMessage('Error loading artist albums. Please try again.', () => this.fetchArtistAlbums(artistId));
            console.error('Artist fetch error:', error);
        }
    }

    private async fetchAlbumTracks(albumId: number): Promise<void> {
        this.downloadAllScope = 'album';
        this.stopPlayback();
        this.displayMessage('Loading album tracks...');

        try {
            const response = await fetch(`/album/?id=${albumId}`);

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

            this.updatePlexPlaylistContainerVisibility(true);

            // Get album info for display
            const albumTitle = albumData.title || 'Album';
            const artistNames = albumData.artists && albumData.artists.length > 0
                ? albumData.artists.map(a => a.name).join(', ')
                : albumData.artist?.name || 'Unknown Artist';

            // Display tracks with Download All button
            this.resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="results-header-top">
                        <h2>${this.escapeHtml(albumTitle)} - ${this.escapeHtml(artistNames)}</h2>
                    </div>
                    ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
                    <div class="progress-info" style="display: none;">
                        <div class="progress-bar-container">
                            <div class="progress-bar" id="lastfmProgress" style="width: 0%"></div>
                        </div>
                        <p class="progress-text" id="progressText">Queued <strong>0</strong> of <strong>${tracks.length}</strong> tracks</p>
                    </div>
                </div>
                <div class="results-list">
                    ${tracks.map(track => this.formatTrackCard(track, true)).join('')}
                </div>
            `;

            // Add Download All button
            const resultsHeaderTop = document.querySelector('.results-header-top') as HTMLElement;
            if (resultsHeaderTop) {
                const downloadAllBtn = document.createElement('button');
                downloadAllBtn.id = 'downloadAllBtn';
                downloadAllBtn.className = 'download-all-btn';
                downloadAllBtn.title = 'Download all tracks sequentially';
                downloadAllBtn.textContent = 'Download All';
                downloadAllBtn.addEventListener('click', () => {
                    // Show progress info when download starts
                    const progressInfo = document.querySelector('.progress-info') as HTMLElement;
                    if (progressInfo) {
                        progressInfo.style.display = 'block';
                    }
                    void this.downloadAllTracks();
                });
                resultsHeaderTop.appendChild(downloadAllBtn);
                this.movePlexPlaylistContainerBeneathDownloadAll();
            }
        } catch (error) {
            this.displayMessage('Error loading album tracks. Please try again.', () => this.fetchAlbumTracks(albumId));
            console.error('Album fetch error:', error);
        }
    }

    private async handleDownload(
        trackId: number,
        trackCard: HTMLElement,
        downloadType: 'album' | 'loose' = 'loose'
    ): Promise<void> {
        const downloadBtn = trackCard.querySelector('.track-download-btn') as HTMLButtonElement;
        if (!downloadBtn) {
            console.error('[DOWNLOAD] Download button not found');
            return;
        }

        console.log(`[DOWNLOAD] Starting download for track ${trackId}`);

        const originalContent = downloadBtn.innerHTML;
        const originalDisabled = downloadBtn.disabled;

        if (!downloadBtn.dataset.originalContent) {
            downloadBtn.dataset.originalContent = originalContent;
        }

        downloadBtn.disabled = true;

        try {
            console.log(`[DOWNLOAD] Calling downloadTrack with format: ${this.downloadSettings.format}`);
            const playlistName = this.plexPlaylistNameInput.value.trim() || null;
            const jobId = await this.downloadTrack(trackId, downloadType, playlistName);
            console.log(`[DOWNLOAD] Job queued successfully: ${jobId}`);

            const statusEl = this.ensureJobStatusElement(trackCard);
            this.setJobStatusChip(statusEl, 'queued');
            this.setDownloadButtonCompleted(downloadBtn);
            this.registerActiveJob(jobId, trackCard, downloadBtn, statusEl);
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

    private async downloadTrack(
        trackId: number,
        downloadType: 'album' | 'loose',
        plexPlaylistName: string | null
    ): Promise<number> {
        try {
            console.log(`[DOWNLOAD] Sending download request for track ${trackId}`);
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
                    fileNaming: downloadType === 'album'
                        ? this.downloadSettings.fileNamingAlbum
                        : this.downloadSettings.fileNamingLoose,
                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                    fileNamingLoose: this.downloadSettings.fileNamingLoose,
                    plex_playlist: plexPlaylistName
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
            // Fallback: recreate the download icon
            downloadBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
            `;
        }
    }

    private ensureJobStatusElement(trackCard: HTMLElement): HTMLElement {
        const metadata = trackCard.querySelector('.track-metadata');
        if (!metadata) {
            const fallback = document.createElement('span');
            fallback.className = 'job-status-chip status-queued';
            fallback.textContent = 'Queued';
            trackCard.appendChild(fallback);
            return fallback;
        }

        let statusEl = metadata.querySelector('.job-status-chip') as HTMLElement | null;
        if (!statusEl) {
            statusEl = document.createElement('span');
            statusEl.className = 'job-status-chip status-queued';
            statusEl.textContent = 'Queued';
            metadata.appendChild(statusEl);
        }

        return statusEl;
    }

    private setJobStatusChip(statusEl: HTMLElement, status: string): void {
        const normalized = status.replace('_', '-');
        statusEl.className = `job-status-chip status-${normalized}`;
        statusEl.textContent = this.formatJobStatus(status);
    }

    private registerActiveJob(
        jobId: number,
        trackCard: HTMLElement,
        downloadBtn: HTMLButtonElement,
        statusEl: HTMLElement
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
        context: { trackCard: HTMLElement; downloadBtn: HTMLButtonElement; statusEl: HTMLElement }
    ): void {
        this.setJobStatusChip(context.statusEl, job.status);

        if (job.status === 'succeeded') {
            this.setDownloadButtonCompleted(context.downloadBtn);
            context.downloadBtn.disabled = true;
            this.activeJobMap.delete(job.id);
            return;
        }

        if (job.status === 'failed' || job.status === 'cancelled') {
            this.restoreDownloadButton(context.downloadBtn);
            this.activeJobMap.delete(job.id);
            return;
        }

        context.downloadBtn.disabled = true;
    }

    private setDownloadButtonCompleted(downloadBtn: HTMLButtonElement): void {
        downloadBtn.disabled = true;
        downloadBtn.classList.add('completed');
        downloadBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
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

        const trackCards = Array.from(this.resultsContainer.querySelectorAll('.track-card')) as HTMLElement[];
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
                    const downloadBtn = trackCard.querySelector('.track-download-btn') as HTMLButtonElement;
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
                    const downloadBtn = trackCard.querySelector('.track-download-btn') as HTMLButtonElement;
                    
                    // Directly call handleDownload instead of clicking
                    if (downloadBtn && !downloadBtn.classList.contains('completed')) {
                        // Create abort controller for this download
                        this.currentDownloadController = new AbortController();
                        const currentController = this.currentDownloadController;
                        
                        // Create promise that waits for the download to complete
                        await new Promise<void>((resolve) => {
                            // Call handleDownload directly
                            void this.handleDownload(parseInt(trackId, 10), trackCard, this.downloadAllScope);
                            
                            // Set a temporary handler to detect when download completes
                            const checkCompletion = setInterval(() => {
                                if (this.downloadAllCancelRequested || currentController.signal.aborted) {
                                    clearInterval(checkCompletion);
                                    resolve();
                                    return;
                                }
                                
                                if (downloadBtn.classList.contains('completed')) {
                                    clearInterval(checkCompletion);
                                    downloadedCount++;
                                    
                                    // Update progress bar and text
                                    const progressBar = document.getElementById('lastfmProgress') as HTMLElement;
                                    const progressText = document.getElementById('progressText');
                                    if (progressBar) {
                                        const progress = (downloadedCount / totalTracks) * 100;
                                        progressBar.style.width = `${progress}%`;
                                    }
                                    if (progressText) {
                                        progressText.innerHTML = `Queued <strong>${downloadedCount}</strong> of <strong>${totalTracks}</strong> tracks`;
                                    }
                                    
                                    setTimeout(() => resolve(), 500); // Small delay before next
                                }
                            }, 100);
                            
                            // Set timeout to prevent hanging
                            setTimeout(() => {
                                clearInterval(checkCompletion);
                                if (!downloadBtn.classList.contains('completed') && !this.downloadAllCancelRequested && !currentController.signal.aborted) {
                                    downloadedCount++;
                                    
                                    // Update progress bar and text
                                    const progressBar = document.getElementById('lastfmProgress') as HTMLElement;
                                    const progressText = document.getElementById('progressText');
                                    if (progressBar) {
                                        const progress = (downloadedCount / totalTracks) * 100;
                                        progressBar.style.width = `${progress}%`;
                                    }
                                    if (progressText) {
                                        progressText.innerHTML = `Queued <strong>${downloadedCount}</strong> of <strong>${totalTracks}</strong> tracks`;
                                    }
                                }
                                resolve();
                            }, 120000); // 2 minutes timeout per track
                        });
                    }
                } catch (error) {
                    console.error(`[DOWNLOAD_ALL] Error downloading track ${trackId}:`, error);
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
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
