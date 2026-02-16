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
        
        this.initializeEventListeners();
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
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new App();
});
