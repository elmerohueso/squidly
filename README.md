# Squidly

A music downloader via SquidWTF and its mirrors, built with Flask and TypeScript.

## Features

- **Music Search & Download** - Search tracks, albums, artists, and Last.fm playlists
- **Smart Mirror System** - Load balancing across multiple backend mirrors
- **Format Conversion** - Download in original quality or convert to FLAC/MP3
- **Metadata Tagging** - Automatic album art and ID3 tag embedding

## Quick Start

1. **Download the compose file:**
   ```bash
   curl -O https://raw.githubusercontent.com/elmerohueso/squidly/main/docker-compose.yml
   ```

2. **Run the application:**
   ```bash
   docker-compose up
   ```

3. **Access the application:**
   Open your browser to `http://localhost:5000`

## Volume Mounts

- **`data/`** - SQLite database and persistent application data
- **`downloads/full_albums/`** - Downloaded full albums
- **`downloads/loose_tracks/`** - Downloaded individual tracks

## Disclaimer

For personal research use only. Respect copyright laws and service terms. Do not distribute copyrighted content without permission.
