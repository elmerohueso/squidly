// Main TypeScript entry point

interface SearchResult {
    query: string;
    data?: {
        items: Track[];
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

        // Download button delegation
        this.resultsContainer.addEventListener('click', (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            const downloadBtn = target.closest('.track-download-btn');
            if (downloadBtn) {
                const trackCard = downloadBtn.closest('.track-card') as HTMLElement;
                const trackId = trackCard?.getAttribute('data-track-id');
                if (trackId) {
                    void this.handleDownload(parseInt(trackId, 10), trackCard);
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

    private async handleSearch(): Promise<void> {
        const query = this.searchInput.value.trim();
        const searchType = this.searchTypeSelect.value;
        
        if (!query) {
            this.displayMessage('Please enter a search query');
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

    private displayResults(data: SearchResult, query: string, searchType: string): void {
        if (data.error) {
            this.displayMessage(`Error: ${data.error}${data.details ? ' - ' + data.details : ''}`);
            return;
        }

        const items = data.data?.items || [];
        
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
                <h2>${searchTypeName} - "${query}"</h2>
                ${data.proxied_via ? `<p class="proxy-info">Proxied via: <span class="proxy-name">${data.proxied_via}</span></p>` : ''}
            </div>
            <div class="results-list">
                ${items.map(item => this.formatTrackCard(item)).join('')}
            </div>
        `;
    }

    private formatTrackCard(track: Track): string {
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
                    <div class="track-title">${this.escapeHtml(track.title)}</div>
                    <div class="track-artist">${this.escapeHtml(artistNames)}</div>
                    <div class="track-metadata">
                        <span>${this.escapeHtml(albumTitle)}</span>
                        ${qualityDisplay ? `<span>•</span><span>${qualityDisplay}</span>` : ''}
                    </div>
                </div>
                <div class="track-actions">
                    ${duration ? `<span class="track-duration">${duration}</span>` : ''}
                    <button class="track-download-btn" title="Download" data-track-id="${track.id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </button>
                    <button class="track-more-btn" title="More options">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="1"></circle>
                            <circle cx="12" cy="5" r="1"></circle>
                            <circle cx="12" cy="19" r="1"></circle>
                        </svg>
                    </button>
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
        return `https://resources.tidal.com/images/${coverPath}/640x640.jpg`;
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
            // Restore button on error
            downloadBtn.disabled = originalDisabled;
            downloadBtn.innerHTML = originalContent;
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
                })
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
            console.error('[DOWNLOAD] Error in downloadTrack:', error);
            throw error;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
