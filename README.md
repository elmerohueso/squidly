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

## Quick Start with Docker

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Access the application:**
   Open your browser to `http://localhost:5000`

### Volume Mounts
The Docker container mounts:
- `./squidurls.json` - Mirror list seed file
- `./data` - SQLite database and other persistent data
- `./downloads/full_albums` - Downloaded full albums (persisted)
- `./downloads/loose_tracks` - Downloaded individual tracks (persisted)

## Disclaimer

This tool is for personal use only. Respect copyright laws and terms of service of the music platforms. Do not distribute copyrighted content without permission.
