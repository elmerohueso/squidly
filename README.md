# Squidly

A music downloader and library manager built with Flask and TypeScript. Downloads tracks from Tidal, Qobuz, and Deezer, then tags and syncs to Plex.

## Features

- **Multi-Source Downloads** — Tidal (hifi-api mirrors), Qobuz (qqdl mirrors), and Deezer (ARL-based)
- **Format Support** — FLAC and M4A output with metadata tagging
- **Plex Integration** — Library sync, automatic scan/update, and playlist management
- **Listen Tracking** — Syncs play history from Plex to power personalized recommendations
- **Fresh Finds** — Auto-generated daily playlists driven by Tidal recommendations and your listening history

## Quick Start

1. **Create environment files:**
   ```bash
   cp .env.example .env
   cp .env.dev.example .env.dev
   ```

2. **Run the production stack:**
   ```bash
   docker compose up
   ```

3. **Or run the development stack:**
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

4. **Access the application:**
   Open your browser to `http://localhost:5000`

## Volume Mounts

- **`data/`** — PostgreSQL database and persistent application data
- **`downloads/`** — Downloaded music files (FLAC/M4A)

## Disclaimer

For personal research use only. Respect copyright laws and service terms. Do not distribute copyrighted content without permission.
