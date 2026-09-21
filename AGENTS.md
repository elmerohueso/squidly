# AGENTS.md — Squidly

Flask + TypeScript + PostgreSQL music downloader via SquidWTF/Tidal mirrors. Downloads tracks/albums, tags metadata (FLAC/M4A/MP3), and syncs to Plex.

## Developer Commands

- **Dev stack**: `docker compose -f docker-compose.dev.yml -f docker-compose.override.yml up --build`
- **Prod stack**: `docker compose up`
- **TypeScript build**: `npm run build` (prod) / `npm run dev` (watch)
- **Type check**: `npm run type-check`
- **Pytest**: `pytest tests/` — tests set `SQUIDLY_SKIP_STARTUP=1` in `conftest.py` to skip DB startup
- **No lint/formatter** — none configured

## Architecture

- **Entry point**: root `app.py` is a one-liner importing `squidly.app.app`
- **Layered architecture**:
  - `squidly/api/` — Flask blueprints (HTTP layer)
  - `squidly/services/` — Business logic (hifi, matching, tag reading)
  - `squidly/jobs/` — Job orchestration (registry, workers, processors)
  - `squidly/infrastructure/` — Core I/O (DB, downloads, Plex, config)
- **Frontend**: `src/app.ts` -> webpack -> `static/dist/bundle.js`
- **Job types**: `download_track`, `bulk_playlist_add`, `plex_library_sync`, `plex_library_update`, `plex_listen_history_sync`, `generate_recommendations`, `automatic_matching`, `fresh_finds_auto_download`

## Database

- PostgreSQL only — no SQLite fallback. `squidly/config.py` raises on missing POSTGRES_* env vars.
- Migrations run at startup via `init_db()` and `init_library_update_status()` in `squidly/app.py` (inline ALTER TABLE for column additions).
- Uses `psycopg2.extras.RealDictCursor` — rows are dict-like, access via `row['column_name']`.
- Job table uses `FOR UPDATE SKIP LOCKED` for worker claiming.
- **Tables**: `jobs`, `mirror_endpoints`, `download_settings`, `plex_config`, `user_settings`, `library_update_status`, `artists`, `albums`, `tracks`, `pending_playlist_adds`, `listen_history`, `listen_history_sync_status`, `recommendation_playlists`, `recommendation_playlist_tracks`

## Startup Sequence

`init_db()` -> `recover_stale_in_progress_jobs(stale_after_minutes=15)` -> `seed_mirrors_from_json()` -> `validate_all_endpoints()` -> `plex_healthcheck()` -> background threads start.

Set `SQUIDLY_SKIP_STARTUP=1` to skip this entire sequence (used by tests).

## Background Threads (10 total)

Defined in `squidly/jobs/workers.py`, spawned by `start_workers()` called from `squidly/app.py`:
1. `download_track_worker` — processes `download_track` jobs (succeeds once `written: done`)
2. `plex_sync_worker` — processes `plex_library_sync` jobs (defers if library update running)
3. `plex_library_update_worker` — processes `plex_library_update` jobs (with download gate)
4. `worker_loop('bulk_playlist_add')` — processes `bulk_playlist_add` jobs (batch-adds from `pending_playlist_adds`)
5. `worker_loop('automatic_matching')` — processes `automatic_matching` jobs (tag analysis + gap-fill)
6. `plex_sync_scheduler_worker` — interval-based Plex sync scheduling
7. `worker_loop('plex_listen_history_sync')` — processes `plex_listen_history_sync` jobs
8. `worker_loop('generate_recommendations')` — processes `generate_recommendations` jobs
9. `nightly_maintenance_scheduler_worker` — daily maintenance scheduling (recommendations + auto-download)
10. `worker_loop('fresh_finds_auto_download')` — processes `fresh_finds_auto_download` jobs

## Docker / Runtime

- **This app runs exclusively in Docker.** There is no local dev server — all code executes inside containers.
- **Dev compose** requires both files: `docker compose -f docker-compose.dev.yml -f docker-compose.override.yml up --build`. The base file defines services; the override adds hardcoded host paths and credentials.
- **Dev override also runs** `squidly-hifi-api` service built from `../hifi-api`.
- **Dev credentials**: user=`squidly`, password=`squidly`, db=`squidly`
- **Container paths**: downloads at `/downloads`, app at `/app`, temp at `/app/temp`. Do NOT call `os.makedirs()` on volume mount points — it shadows them.
- **ffmpeg** is required (installed in Dockerfile). Needed for HLS/DASH downloads and format conversion.
- **Production image**: `ghcr.io/elmerohueso/squidly:latest`, runs gunicorn with 4 workers, `--preload` flag.
- **Dockerfile**: multi-stage build — Node 20 for frontend, Python 3.11-slim for runtime.
- **Timezone**: `TZ` env var (default `UTC`). Controls recommendation scheduler timing and all date display formatting. Set to an IANA timezone like `America/New_York`.

## Debugging / Logs

- **Persistent logs are mounted at `logs/`** (when the override volume is configured) — always check these first before using `docker logs`. They contain the full history, not just the tail.
  - `logs/squidly.log` — main application log (all prefixes: `[DOWNLOAD]`, `[PLEX]`, `[JOB_RECOVERY]`, etc.)
  - `logs/gunicorn_access.log` — HTTP access log
  - `logs/gunicorn_error.log` — gunicorn worker errors, tracebacks
  - Rotated logs: `logs/squidly.log.2026-05-16`, `logs/gunicorn_error.log.2026-05-14`, etc.
  - Use `grep` on these files for historical events. `docker logs` is only for recent output not yet rotated.
- **Running containers**: `docker ps` — the dev container is named `squidly-dev`, not `squidly`

## Database Access

- **Connect to the dev database**: `docker exec -it squidly-postgres-dev psql -U squidly -d squidly`
- **Run a query**: `docker exec -it squidly-postgres-dev psql -U squidly -d squidly -c "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 5;"`
- **Database must be accessed from inside the container.** Never connect from the host directly — always use `docker exec` into `squidly-postgres-dev`.
- **Dev credentials**: user=`squidly`, password=`squidly`, db=`squidly`

## Conventions

- Logging uses bracketed prefixes: `[DOWNLOAD]`, `[PLEX]`, `[JOB_RECOVERY]`, `[LIBRARY_UPDATE]`, `[MATCH]`, etc.
- Timestamps stored as UTC in database (`datetime.utcnow().isoformat() + 'Z'`). Display uses `TZ` env var (default `UTC`).
- Parameterized SQL only (`%s` placeholders), never string interpolation.
- Job stages in `result_json`: `downloaded` -> `tagged` -> `converted` -> `written` -> `playlist_added` (note: `tagged`, not `id3_tagged` — migration renames it). `playlist_added: queued` means the track was inserted into `pending_playlist_adds` table; a `bulk_playlist_add` job processes the queue after Plex sync completes.
- `pending_playlist_adds` table: queue for tracks awaiting playlist addition. Columns: `id`, `parent_job_id`, `file_path`, `playlist_name`, `plex_user_id`, `created_at`. Unique index on `(file_path, playlist_name, COALESCE(plex_user_id, ''))`. Rows deleted on successful add; failures remain for next bulk job run.
- Download jobs succeed immediately after `written: done` — no longer wait for playlist adds to complete.
- Mirror URLs in `squidurls.json` (base64-encoded). Seeded into `mirror_endpoints` table at startup.
- Rate limit state is in-memory per process.
- Fresh Finds playlist name is static: `Fresh Finds`. Generated nightly; listened tracks are removed and replaced with new recommendations.

## Git / Notable Exclusions

- `docker-compose.override.yml` — gitignored (developer-specific host paths)
- `package-lock.json` — gitignored
- `.opencode/` — gitignored (local OpenCode config)
- `test_scripts/` — gitignored (manual helper scripts)
- `static/dist/` — gitignored (webpack output)
- `downloads/`, `temp/`, `data/` — gitignored

## CI

- `main` branch -> `ghcr.io/elmerohueso/squidly:latest`
- `test` branch -> `ghcr.io/elmerohueso/squidly:test`
- No lint, formatter, or test steps in CI — only Docker build and push.

## Code Quality Rules

- **Commits** — When user says "commit", commit all unstaged changes related to the current task. Group related changes into logical commits with descriptive messages. Don't commit unrelated changes unless explicitly asked.

- **Always ask first** — Prompt for clarification on any ambiguity before implementing. Never assume intent.
- **Extract before duplicating** — If a pattern appears twice, pull it into a helper immediately
- **Check existing code first** — Search for similar methods/utilities before writing new logic; reuse or extend
- **Thin wrappers only** — Handler methods should do the minimum unique work and delegate shared concerns (confirm dialogs, state management, error handling) to a common primitive
- **Call it out** — If about to write something resembling existing code, flag and consolidate instead
- **Don't touch working code** — Unused but harmless params, dead code paths, or cosmetic issues in otherwise-functional methods should be left alone. Rewriting working code to "clean it up" introduces bugs. Only edit what the task explicitly requires.
- **Surgical edits only** — When removing a param or field, change only the signature and its call sites. Don't restructure method bodies, reorder methods, or touch unrelated logic.
- **Never restart containers** — Do not run `docker restart` or any container restart command without explicit permission. Ask the user to restart instead.
- **Never copy files directly to containers** — Do not use `docker cp` to copy files into running containers without explicit permission. Ask the user to restart the container so volume-mounted changes take effect.

## Reference Files

- **`.opencode/memory.md`** — Hifi-API route reference. Consult when working with Tidal mirror endpoints, track/album downloads, or any hifi-api integration.

## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical roles. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — `CONTEXT.md` + `docs/adr/` at repo root. See `docs/agents/domain.md`.
