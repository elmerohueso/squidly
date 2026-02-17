# Squidly

A modern music downloader and search interface built with Flask and TypeScript, featuring a clean, Tidal-inspired design and intelligent mirror management.

## Features

- 🎵 **Music Search & Download** - Search for tracks, albums, artists, and Last.fm playlists
- 🔄 **Smart Mirror System** - Automatic round-robin load balancing across multiple backend mirrors
- 💾 **Format Options** - Download in original quality or convert to FLAC/MP3
- 🎨 **Modern UI** - Clean, dark-themed design with smooth animations
- 📊 **Mirror Status Monitoring** - Real-time health checks and response time tracking
- ⚙️ **Configurable Downloads** - Customizable file naming patterns and folder organization
- 🏷️ **Metadata Tagging** - Automatic album art and ID3 tag embedding
- 🐳 **Docker Ready** - Fully containerized for easy deployment

## Prerequisites

- Docker and Docker Compose (recommended)
- OR:
  - Python 3.11+
  - Node.js 20+

## Quick Start with Docker

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   Open your browser to `http://localhost:5000`

## Development Setup (Without Docker)

### Backend Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. **Install Node dependencies:**
   ```bash
   npm install
   ```

2. **Build TypeScript:**
   ```bash
   npm run build
   ```

   Or for development with watch mode:
   ```bash
   npm run dev
   ```

### Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
squidly/
├── app.py                  # Flask backend with download logic
├── squidurls.json         # Mirror endpoints (base64-encoded)
├── requirements.txt        # Python dependencies (Flask, mutagen, etc.)
├── package.json           # Node dependencies
├── tsconfig.json          # TypeScript configuration
├── webpack.config.js      # Webpack bundler config
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker orchestration
├── data/
│   └── squidly.db        # SQLite database (settings & mirror status)
├── downloads/
│   ├── full_albums/      # Album downloads
│   └── loose_tracks/     # Individual track downloads
├── src/
│   └── app.ts            # TypeScript frontend logic
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── styles.css        # Central stylesheet
    └── dist/             # Built assets (generated)
```

## Mirror Management

Squidly uses a smart mirror system to distribute requests across multiple music API backends:

- **Round-Robin Load Balancing** - Automatically cycles through available mirrors
- **Health Monitoring** - Periodic health checks with response time tracking
- **Automatic Failover** - Skips offline mirrors and retries with healthy ones
- **Status Dashboard** - View real-time mirror status and performance metrics

Mirror endpoints are stored in [squidurls.json](squidurls.json) as base64-encoded URLs. The system tracks each mirror's status in a SQLite database and intelligently routes requests to maintain optimal performance.

## API Endpoints

### Main Routes
- `GET /` - Main web interface
- `GET /api/health` - Application health check
- `GET /api/settings/download` - Get download settings
- `POST /api/settings/download` - Update download settings

### Search & Browse
- `POST /api/search` - Search for tracks, albums, or artists
  - Request body: `{"query": "search term", "type": "s|a|al"}`
- `POST /api/search/lastfm` - Import Last.fm playlist
  - Request body: `{"url": "lastfm_playlist_url"}`

### Downloads
- `POST /api/download/track` - Download individual track
- `POST /api/download/album` - Download full album
- `GET /api/download/status` - Check download progress
- `GET /api/download/list` - List downloaded files

### Mirror Management
- `GET /api/mirrors/status` - Get all mirror statuses
- `POST /api/mirrors/check` - Trigger health check for all mirrors

## Download Configuration

Customize your downloads through the settings interface:

### Output Format
- **Original** - Keep source format (FLAC/AAC/etc.)
- **FLAC** - Convert to lossless FLAC
- **MP3** - Convert to MP3 (320kbps)

### File Naming Patterns
Supports template variables:
- `{artist}` - Artist name
- `{title}` - Track title
- `{album}` - Album name
- `{track}` - Track number
- `{ext}` - File extension

**Default patterns:**
- Loose tracks: `{artist} - {title}.{ext}`
- Album tracks: `{artist}/{album}/{track} - {title}.{ext}`

### Download Locations
- `downloads/full_albums/` - Complete album downloads
- `downloads/loose_tracks/` - Individual tracks
- Custom parent folders can be configured in settings

## Styling

The interface features a modern, dark-themed design inspired by Tidal:

- Dark theme with modern color palette (`#1a1a1a` base)
- Smooth transitions and hover effects
- Responsive grid layouts for search results
- Custom scrollbar styling
- Real-time status indicators for mirrors
- Album art display with fallback icons

All styles are centralized in [static/styles.css](static/styles.css).

## Development

- **TypeScript:** Edit files in `src/` and run `npm run dev` for auto-compilation with watch mode
- **Python:** Flask runs in debug mode by default during local development
- **Styles:** Edit `static/styles.css` for styling changes (changes apply immediately)
- **Database:** SQLite database at `data/squidly.db` stores settings and mirror status
- **Downloads:** Downloaded files appear in `downloads/` directory

## Production Deployment

The Docker setup uses a multi-stage build process:

1. Builds TypeScript assets with Webpack
2. Creates optimized Python runtime environment
3. Installs dependencies (Flask, Mutagen, FFmpeg, etc.)
4. Runs with Gunicorn for production performance

To deploy:

```bash
docker-compose up -d
```

### Volume Mounts
The Docker container mounts:
- `./downloads` - Downloaded music files (persisted)
- `./data` - SQLite database (persisted)

## Technical Stack

### Backend
- **Flask** - Web framework
- **Mutagen** - Audio metadata tagging (ID3, FLAC tags)
- **FFmpeg** - Audio format conversion
- **SQLite** - Settings and mirror status storage
- **Requests** - HTTP client for mirror communication

### Frontend
- **TypeScript** - Type-safe development
- **Webpack** - Module bundling
- **Vanilla JS** - No framework dependencies, lightweight

### Infrastructure
- **Docker** - Containerization
- **Gunicorn** - WSGI server for production
- **CORS** - Cross-origin resource sharing support

## Usage

1. **Search for Music**
   - Select search type: Tracks, Artists, Albums, or Last.fm Playlist
   - Enter search query and press Enter or click Search
   - Browse results with album art and metadata

2. **Download Music**
   - Click on any search result to download
   - Individual tracks download to `loose_tracks/`
   - Album downloads preserve folder structure in `full_albums/`
   - Monitor download progress in real-time

3. **Configure Settings**
   - Click the Settings button (⚙️) in the header
   - Choose output format: Original, FLAC, or MP3
   - Customize file naming patterns
   - Set parent folder for organized downloads

4. **Monitor Mirrors**
   - Click the Status button (🌐) to view mirror health
   - See response times and online/offline status
   - Manually trigger health checks if needed

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Guidelines
- Follow existing code style and patterns
- Test changes with Docker before submitting
- Update README for new features or API changes
- Ensure TypeScript compiles without errors

## Disclaimer

This tool is for personal use only. Respect copyright laws and terms of service of the music platforms. Do not distribute copyrighted content without permission.
