// Main TypeScript entry point

interface SearchResult {
    query: string;
    results: any[];
}

class App {
    private searchInput: HTMLInputElement;
    private searchButton: HTMLButtonElement;
    private resultsContainer: HTMLElement;

    constructor() {
        this.searchInput = document.getElementById('searchInput') as HTMLInputElement;
        this.searchButton = document.getElementById('searchButton') as HTMLButtonElement;
        this.resultsContainer = document.getElementById('results') as HTMLElement;
        
        this.initializeEventListeners();
    }

    private initializeEventListeners(): void {
        this.searchButton.addEventListener('click', () => this.handleSearch());
        this.searchInput.addEventListener('keypress', (e: KeyboardEvent) => {
            if (e.key === 'Enter') {
                this.handleSearch();
            }
        });
    }

    private async handleSearch(): Promise<void> {
        const query = this.searchInput.value.trim();
        
        if (!query) {
            this.displayMessage('Please enter a search query');
            return;
        }

        this.displayMessage('Searching...');

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                throw new Error('Search failed');
            }

            const data: SearchResult = await response.json();
            this.displayResults(data);
        } catch (error) {
            this.displayMessage('Error performing search. Please try again.');
            console.error('Search error:', error);
        }
    }

    private displayResults(data: SearchResult): void {
        if (data.results.length === 0) {
            this.displayMessage(`No results found for "${data.query}"`);
            return;
        }

        // TODO: Implement actual results display
        this.resultsContainer.innerHTML = `
            <div class="results-header">
                <h2>Results for "${data.query}"</h2>
            </div>
            <div class="results-list">
                ${data.results.map(result => `
                    <div class="result-item">
                        ${JSON.stringify(result)}
                    </div>
                `).join('')}
            </div>
        `;
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
