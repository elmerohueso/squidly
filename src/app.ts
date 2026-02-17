// Main TypeScript entry point

interface SearchResult {
    query: string;
    data?: {
        items?: (Track | AlbumSearchItem)[];
        albums?: {
            items: AlbumSearchItem[];
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

type DownloadFormat = 'original' | 'mp3';

interface DownloadSettings {
    format: DownloadFormat;
    fileNaming: string;
}

class App {
    private searchInput: HTMLInputElement;
    private searchTypeSelect: HTMLSelectElement;
    private searchButton: HTMLButtonElement;
    private resultsContainer: HTMLElement;
    private statusButton: HTMLButtonElement;
    private statusFlyout: HTMLElement;
    private flyoutOverlay: HTMLElement;
    private closeFlyoutButton: HTMLButtonElement;
    private flyoutContent: HTMLElement;
    private settingsButton: HTMLButtonElement;
    private settingsFlyout: HTMLElement;
    private settingsOverlay: HTMLElement;
    private closeSettingsButton: HTMLButtonElement;
    private formatOriginalInput: HTMLInputElement;
    private formatMp3Input: HTMLInputElement;
    private fileNamingInput: HTMLInputElement;
    private downloadSettings: DownloadSettings;
    private settingsSaveTimer: number | null = null;
    private readonly settingsSaveDelayMs = 500;
    private statusUpdateInterval: number | null = null;
    private isDownloadingAll: boolean = false;
    private downloadAllCancelRequested: boolean = false;
    private currentDownloadController: AbortController | null = null;

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
        this.settingsButton = document.getElementById('settingsButton') as HTMLButtonElement;
        this.settingsFlyout = document.getElementById('settingsFlyout') as HTMLElement;
        this.settingsOverlay = document.getElementById('settingsOverlay') as HTMLElement;
        this.closeSettingsButton = document.getElementById('closeSettings') as HTMLButtonElement;
        this.formatOriginalInput = document.getElementById('formatOriginal') as HTMLInputElement;
        this.formatMp3Input = document.getElementById('formatMp3') as HTMLInputElement;
        this.fileNamingInput = document.getElementById('fileNaming') as HTMLInputElement;
        
        this.initializeEventListeners();
        this.downloadSettings = this.defaultDownloadSettings();
        this.applySettingsToForm(this.downloadSettings);
        void this.fetchDownloadSettingsFromServer();
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

        this.settingsButton.addEventListener('click', () => this.openSettingsFlyout());
        this.closeSettingsButton.addEventListener('click', () => this.closeSettingsFlyout());
        this.settingsOverlay.addEventListener('click', () => this.closeSettingsFlyout());

        this.formatOriginalInput.addEventListener('change', () => this.updateSettingsFromForm());
        this.formatMp3Input.addEventListener('change', () => this.updateSettingsFromForm());
        this.fileNamingInput.addEventListener('input', () => this.updateSettingsFromForm());

        // Update placeholder text based on search type
        this.searchTypeSelect.addEventListener('change', () => this.updateSearchPlaceholder());

        // Download button and album card click delegation
        this.resultsContainer.addEventListener('click', (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            
            // Check for download button clicks first
            const downloadBtn = target.closest('.track-download-btn');
            if (downloadBtn) {
                const trackCard = downloadBtn.closest('.track-card') as HTMLElement;
                const trackId = trackCard?.getAttribute('data-track-id');
                if (trackId) {
                    void this.handleDownload(parseInt(trackId, 10), trackCard);
                }
                return; // Stop here if it was a download button
            }
            
            // Check for album card clicks (albums have both track-card and album-card classes)
            const clickedCard = target.closest('.track-card') as HTMLElement;
            if (clickedCard && clickedCard.classList.contains('album-card')) {
                const albumId = clickedCard.getAttribute('data-album-id');
                if (albumId) {
                    void this.fetchAlbumTracks(parseInt(albumId, 10));
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
            fileNaming: '{artist}/{album}/{track} - {title}.{ext}'
        };
    }

    private normalizeSettings(raw: Partial<DownloadSettings>): DownloadSettings {
        const fallback = this.defaultDownloadSettings();
        const fileNaming = (raw as { file_naming?: string }).file_naming;

        return {
            format: raw.format === 'mp3' ? 'mp3' : 'original',
            fileNaming: typeof raw.fileNaming === 'string'
                ? raw.fileNaming
                : typeof fileNaming === 'string'
                    ? fileNaming
                    : fallback.fileNaming
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
        this.fileNamingInput.value = settings.fileNaming;
        this.syncFormatToggleStyles();
    }

    private readSettingsFromForm(): DownloadSettings {
        return {
            format: this.formatMp3Input.checked ? 'mp3' : 'original',
            fileNaming: this.fileNamingInput.value.trim()
        };
    }

    private updateSettingsFromForm(): void {
        this.downloadSettings = this.readSettingsFromForm();
        this.queueSettingsSave();
        this.syncFormatToggleStyles();
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
        } else if (searchType === 'al') {
            this.searchInput.placeholder = 'Search for albums...';
        } else {
            this.searchInput.placeholder = 'Search for tracks...';
        }
    }

    private async handleSearch(): Promise<void> {
        const query = this.searchInput.value.trim();
        const searchType = this.searchTypeSelect.value;
        
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
            const response = await fetch(`/search/?${searchType}=${encodeURIComponent(query)}`);

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
            }

        } catch (error) {
            this.displayMessage(`Error: ${error instanceof Error ? error.message : 'Failed to process Last.fm playlist'}`);
            console.error('Last.fm playlist error:', error);
        }
    }

    private displayResults(data: SearchResult, query: string, searchType: string): void {
        if (data.error) {
            this.displayMessage(`Error: ${data.error}${data.details ? ' - ' + data.details : ''}`);
            return;
        }

        // Extract items based on search type - albums are nested under data.albums.items
        const items = searchType === 'al' 
            ? (data.data?.albums?.items || [])
            : (data.data?.items || []);
        
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
                ${items.map(item => searchType === 'al' ? this.formatAlbumCard(item as AlbumSearchItem) : this.formatTrackCard(item as Track)).join('')}
            </div>
        `;
    }

    private formatTrackCard(track: Track, showTrackNumber: boolean = false): string {
        // Get artist names
        const artistNames = track.artists && track.artists.length > 0
            ? track.artists.map(a => a.name).join(', ')
            : track.artist?.name || 'Unknown Artist';

        // Get album info
        const albumTitle = track.album?.title || 'Unknown Album';
        const albumCover = track.album?.cover || track.cover;

        // Format duration
        const duration = track.duration 
            ? this.formatDuration(track.duration)
            : '';

        // Get quality info
        const quality = track.audioQuality || track.quality || '';
        const qualityDisplay = this.formatQuality(quality);

        // Format track title with optional track number
        const trackTitle = showTrackNumber && track.trackNumber
            ? `${track.trackNumber}. ${this.escapeHtml(track.title)}`
            : this.escapeHtml(track.title);

        return `
            <div class="track-card" data-track-id="${track.id}">
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
                    <div class="track-artist">${this.escapeHtml(artistNames)}</div>
                    <div class="track-metadata">
                        <span>${this.escapeHtml(albumTitle)}</span>
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

    private formatAlbumCard(album: AlbumSearchItem): string {
        // Get artist names
        const artistNames = album.artists && album.artists.length > 0
            ? album.artists.map(a => a.name).join(', ')
            : album.artist?.name || 'Unknown Artist';

        // Format release year if available
        const releaseYear = album.releaseDate 
            ? new Date(album.releaseDate).getFullYear()
            : '';

        // Format track count
        const trackCount = album.numberOfTracks 
            ? `${album.numberOfTracks} track${album.numberOfTracks !== 1 ? 's' : ''}`
            : '';

        return `
            <div class="track-card album-card clickable" data-album-id="${album.id}" title="Click to view tracks">
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
                    <div class="track-artist">${this.escapeHtml(artistNames)}</div>
                    <div class="track-metadata">
                        ${releaseYear ? `<span>${releaseYear}</span>` : ''}
                        ${releaseYear && trackCount ? `<span>•</span>` : ''}
                        ${trackCount ? `<span>${trackCount}</span>` : ''}
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
            'HI_RES_LOSSLESS': 'Hi-Res • up to 24-bit/192kHz FLAC',
            'LOSSLESS': 'CD • 16-bit/44.1kHz FLAC',
            'HIGH': '320kbps AAC',
            'LOW': '96kbps AAC'
        };
        return qualityMap[quality] || quality;
    }

    private formatAlbumCoverUrl(cover: string): string {
        // Convert dashes to forward slashes for Tidal CDN format
        const coverPath = cover.replace(/-/g, '/');
        return `https://resources.tidal.com/images/${coverPath}/1280x1280.jpg`;
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    private displayMessage(message: string): void {
        this.resultsContainer.innerHTML = `
            <div class="message">
                <p>${message}</p>
            </div>
        `;
    }

    private async fetchAlbumTracks(albumId: number): Promise<void> {
        this.displayMessage('Loading album tracks...');

        try {
            const response = await fetch(`/album/?id=${albumId}`);

            if (!response.ok) {
                throw new Error('Failed to fetch album');
            }

            const data: AlbumInfo = await response.json();

            if (data.error) {
                this.displayMessage(`Error: ${data.error}`);
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
                        <p class="progress-text" id="progressText">Downloaded <strong>0</strong> of <strong>${tracks.length}</strong> tracks</p>
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
            }
        } catch (error) {
            this.displayMessage('Error loading album tracks. Please try again.');
            console.error('Album fetch error:', error);
        }
    }

    private async handleDownload(trackId: number, trackCard: HTMLElement): Promise<void> {
        const downloadBtn = trackCard.querySelector('.track-download-btn') as HTMLButtonElement;
        if (!downloadBtn) {
            console.error('[DOWNLOAD] Download button not found');
            return;
        }

        console.log(`[DOWNLOAD] Starting download for track ${trackId}`);

        // Store original button content
        const originalContent = downloadBtn.innerHTML;
        const originalDisabled = downloadBtn.disabled;
        
        // Disable button and show progress circle
        downloadBtn.disabled = true;
        
        // Create SVG progress circle
        const progressSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        progressSvg.setAttribute('viewBox', '0 0 24 24');
        progressSvg.setAttribute('class', 'track-download-progress');
        
        // Add gradient definition
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', 'progressGradient');
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '100%');
        
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('stop-color', '#00d4ff');
        
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('stop-color', '#0099ff');
        
        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        progressSvg.appendChild(defs);
        
        // Background track circle
        const trackCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        trackCircle.setAttribute('cx', '12');
        trackCircle.setAttribute('cy', '12');
        trackCircle.setAttribute('r', '12');
        trackCircle.setAttribute('class', 'progress-circle-track');
        progressSvg.appendChild(trackCircle);
        
        // Progress fill circle
        const fillCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        fillCircle.setAttribute('cx', '12');
        fillCircle.setAttribute('cy', '12');
        fillCircle.setAttribute('r', '12');
        fillCircle.setAttribute('class', 'progress-circle-fill');
        progressSvg.appendChild(fillCircle);
        
        // Replace button content with progress circle
        downloadBtn.innerHTML = '';
        downloadBtn.appendChild(progressSvg);

        try {
            console.log(`[DOWNLOAD] Calling downloadTrack with format: ${this.downloadSettings.format}`);
            await this.downloadTrack(trackId, fillCircle as SVGCircleElement);
            
            console.log(`[DOWNLOAD] Download completed successfully`);
            
            // Animate to 100%
            (fillCircle as any).style.strokeDashoffset = '0';
            
            // Wait a moment to show completion, then replace with checkmark
            setTimeout(() => {
                downloadBtn.disabled = true;
                downloadBtn.classList.add('completed');
                downloadBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                `;
            }, 300);
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
            }
        }
    }

    private async downloadTrack(trackId: number, progressCircle?: SVGCircleElement): Promise<void> {
        try {
            console.log(`[DOWNLOAD] Sending download request for track ${trackId}`);
            console.log(`[DOWNLOAD] Settings: format=${this.downloadSettings.format}`);
            
            // Animate progress to 50% during request
            if (progressCircle) {
                setTimeout(() => {
                    if (progressCircle) (progressCircle as any).style.strokeDashoffset = '37.7'; // 50%
                }, 200);
            }
            
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trackId,
                    format: this.downloadSettings.format,
                    fileNaming: this.downloadSettings.fileNaming
                }),
                signal: this.currentDownloadController?.signal
            });

            console.log(`[DOWNLOAD] Response status: ${response.status}`);
            
            // Animate progress to 80% while processing response
            if (progressCircle) {
                (progressCircle as any).style.strokeDashoffset = '15.08'; // 80%
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.error || `HTTP ${response.status}`;
                console.error(`[DOWNLOAD] Download failed: ${errorMsg}`);
                throw new Error(errorMsg);
            }

            // Parse the JSON response
            const data = await response.json();
            console.log(`[DOWNLOAD] Server response:`, data);
            
            if (data.success) {
                console.log(`[DOWNLOAD] File saved: ${data.message}`);
                // Progress will be set to 100% by the caller
            } else {
                throw new Error(data.error || 'Download failed');
            }
        } catch (error) {
            // Check if error is due to abort
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[DOWNLOAD] Download was aborted');
                return;
            }
            console.error('[DOWNLOAD] Error in downloadTrack:', error);
            throw error;
        }
    }

    private convertButtonToProgressCircle(downloadBtn: HTMLButtonElement): void {
        // Store original content if not already stored
        if (!downloadBtn.dataset.originalContent) {
            downloadBtn.dataset.originalContent = downloadBtn.innerHTML;
        }
        
        downloadBtn.disabled = true;
        
        // Create SVG progress circle
        const progressSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        progressSvg.setAttribute('viewBox', '0 0 24 24');
        progressSvg.setAttribute('class', 'track-download-progress');
        
        // Add gradient definition
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', 'progressGradient');
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '100%');
        
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('stop-color', '#00d4ff');
        
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('stop-color', '#0099ff');
        
        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        progressSvg.appendChild(defs);
        
        // Background track circle
        const trackCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        trackCircle.setAttribute('cx', '12');
        trackCircle.setAttribute('cy', '12');
        trackCircle.setAttribute('r', '12');
        trackCircle.setAttribute('class', 'progress-circle-track');
        progressSvg.appendChild(trackCircle);
        
        // Progress fill circle
        const fillCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        fillCircle.setAttribute('cx', '12');
        fillCircle.setAttribute('cy', '12');
        fillCircle.setAttribute('r', '12');
        fillCircle.setAttribute('class', 'progress-circle-fill');
        progressSvg.appendChild(fillCircle);
        
        // Replace button content with progress circle
        downloadBtn.innerHTML = '';
        downloadBtn.appendChild(progressSvg);
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

        // Convert all buttons to 0% progress circles
        for (const trackCard of trackCards) {
            const downloadBtn = trackCard.querySelector('.track-download-btn') as HTMLButtonElement;
            if (downloadBtn && !downloadBtn.classList.contains('completed')) {
                this.convertButtonToProgressCircle(downloadBtn);
            }
        }

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
                            void this.handleDownload(parseInt(trackId, 10), trackCard);
                            
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
                                        progressText.innerHTML = `Downloaded <strong>${downloadedCount}</strong> of <strong>${totalTracks}</strong> tracks`;
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
                                        progressText.innerHTML = `Downloaded <strong>${downloadedCount}</strong> of <strong>${totalTracks}</strong> tracks`;
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

        console.log(`[DOWNLOAD_ALL] Batch download complete. Downloaded ${downloadedCount}/${totalTracks} tracks`);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
