# Matching Rework Plan

## Goal
Replace the current fuzzy-matching-first approach with a layered pipeline where each layer fills in what it can, starting from the most reliable source of truth.

## Current Architecture Problems
- `matching.py` is 1745 lines of mixed concerns (scoring, DB ops, job orchestration, candidate building)
- HiFi API fuzzy matching runs even when download already knows the `hifi_id`
- Plex sync doesn't fill missing fields on existing records
- No tag-reading layer exists
- Functions are scattered across `matching.py`, `app.py`, and `workers.py`

## Target Architecture: 4 Layers

```
Download → Plex Sync → Tag Analysis → HiFi Gap-Fill
(most reliable)                          (least reliable)
```

Each layer fills in blanks left by the previous layer. No layer overwrites confident data.

---

## Layer 0: Download (enhancement — already mostly done)

**File:** `squidly/matching.py` — `upsert_download_match_hint()`

**What it does now (after disc_number/track_number fix):**
- Inserts/updates artists, albums, tracks with `hifi_id`, `confidence=0.99`, `title`, `path`, `format`, `isrc`, `duration`, `track_number`, `disc_number`

**No changes needed here** — download already seeds everything it knows.

---

## Layer 1: Plex Sync (enhancement)

**File:** `squidly/app.py` — `process_plex_library_sync_job()`

**Current behavior:** Upserts records from Plex inventory. Sets `library_id`, `bitrate`, `format`, `path`, `title`, `artist`, `album`, `track_number`, `disc_number`.

**Changes needed:**
- When a record already exists, fill in any NULL fields from Plex data (don't overwrite existing values)
- Currently the `_upsert_track_row` call passes `COALESCE` for most fields, which is correct — verify this pattern is consistent

**Scope:** Small change to existing sync logic. Verify COALESCE behavior is already correct.

---

## Layer 2: Tag Analysis (NEW)

**New file:** `squidly/tag_reader.py`

**Responsibility:** Scan downloaded files, read tags via mutagen, fill blank DB fields.

**Functions:**
- `read_audio_file_tags(file_path)` → dict of all tag values (FLAC, M4A, MP3)
- `scan_library_for_tags(progress_callback=None)` → iterate all tracks with `path`, read tags, fill blanks
- `_fill_track_from_tags(cur, track_row, tags)` → upsert track with any missing fields filled
- `_resolve_album_hifi_id_from_tags(cur, tags)` → if track has `TIDAL_ALBUM_ID` but no album row `hifi_id`, update album
- `_resolve_artist_hifi_id_from_tags(cur, track_row)` → infer artist `hifi_id` from album's `hifi_id` via HiFi API

**Job type:** `tag_analysis` — enqueued as part of Automatic Matching flow

**Tag mapping:**
| DB Field | FLAC Tag | M4A Tag |
|----------|----------|---------|
| `tracks.hifi_id` | `TIDAL_TRACK_ID` | `----:com.apple.iTunes:tidal_track_id` |
| `albums.hifi_id` | `TIDAL_ALBUM_ID` | `----:com.apple.iTunes:tidal_album_id` |
| `tracks.title` | `TITLE` | `©nam` |
| `tracks.artist` (FK→name) | `ARTIST` | `©ART` |
| `albums.title` | `ALBUM` | `©alb` |
| `tracks.track_number` | `TRACKNUMBER` | `trkn` |
| `tracks.disc_number` | `DISCNUMBER` | `disk` |
| `tracks.isrc` | `ISRC` | `----:com.apple.iTunes:isrc` |
| `tracks.duration` | file analysis | file analysis |
| `tracks.bitrate` | file analysis | file analysis |

**MP3:** Ignored (not supported by this app).

---

## Layer 3: HiFi Gap-Fill (replaces current hifi_match)

**New file:** `squidly/hifi_matcher.py` (extracted from `matching.py`)

**Responsibility:** For records still missing `hifi_id` after layers 0-2, query HiFi API to find matches.

**Functions:**
- `find_missing_hifi_ids(progress_callback=None)` → main entry point
- `_find_tracks_needing_match(cur)` → SELECT where `hifi_id IS NULL AND library_id IS NOT NULL`
- `_find_albums_needing_match(cur)` → same for albums
- `_find_artists_needing_match(cur)` → same for artists
- `_match_track_via_isrc(cur, track_row)` → try ISRC lookup first (most reliable)
- `_match_track_via_search(cur, track_row)` → fall back to title+artist search
- `_match_album_via_search(cur, album_row)` → album title+artist search
- `_match_artist_via_search(cur, artist_row)` → artist name search
- `_upsert_match_result(cur, entity_type, entity_id, hifi_id, confidence)`

**Key difference from current approach:**
- Only runs on records that are genuinely missing `hifi_id`
- Uses ISRC as primary key when available (exact match, no scoring needed)
- Falls back to search only when ISRC isn't available
- Much smaller search space

---

## Layer 4: Automatic Matching Orchestration (NEW)

**File:** `squidly/matching.py` — new orchestration functions

**Functions:**
- `run_automatic_matching()` → sequential pipeline:
  1. Queue Plex library update (if configured)
  2. Wait for Plex sync to complete
  3. Run tag analysis
  4. Run HiFi gap-fill
- `queue_automatic_matching_job(trigger='manual'|'scheduled')`
- `_run_automatic_matching_job(job_id, payload)` → worker function

**Job type:** `automatic_matching` — replaces current ad-hoc flow

---

## File Restructuring

### `squidly/matching.py` (shrink from 1745 lines)

**Keep here:**
- Scoring helpers (`normalize_match_text`, `_score_*`, `compute_playlist_match_penalty`)
- Match review helpers (`_build_*_match_candidates`, `_fetch_match_review_row`)
- Coverage helpers (`_fetch_hifi_match_coverage_counts`)
- Orchestration (`run_automatic_matching`, `queue_automatic_matching_job`)

**Move out:**
- DB upserts → keep here (they're shared across layers)
- HiFi API matching → `squidly/hifi_matcher.py`
- Tag reading → `squidly/tag_reader.py`

### `squidly/tag_reader.py` (NEW)
- All tag-reading logic
- File scanning
- Tag-to-DB field mapping

### `squidly/hifi_matcher.py` (NEW)
- HiFi API search/matching logic
- ISRC lookup
- Title+artist search fallback
- Gap-fill orchestration

### `squidly/workers.py`
- Add `automatic_matching_job_worker`
- Add `tag_analysis_job_worker`
- Keep existing workers

---

## Implementation Order

### Phase 1: Plex sync gap-filling
- Verify `_upsert_track_row` COALESCE behavior
- Small fix if needed
- Test: sync a track with missing fields, confirm they get filled

### Phase 2: Tag reading module
- Create `squidly/tag_reader.py`
- Implement `read_audio_file_tags()` for FLAC and M4A
- Implement `scan_library_for_tags()` with progress tracking
- Test: run against existing downloads, verify fields populated

### Phase 3: HiFi gap-fill module
- Create `squidly/hifi_matcher.py`
- Extract matching logic from `matching.py`
- Implement ISRC-first strategy
- Test: run on records without `hifi_id`, verify matches found

### Phase 4: Automatic Matching orchestration
- Create `run_automatic_matching()` pipeline
- Wire up job types and workers
- Update UI to trigger automatic matching instead of separate sync/match buttons
- Test: full end-to-end pipeline

### Phase 5: Cleanup
- Remove dead code from `matching.py`
- Update imports across `app.py`
- Verify no regressions in existing download/match UI flows

---

## DB Schema Changes

**None required.** All existing columns are sufficient.

**Future consideration (not in scope):**
- `tracks.version` TEXT — raw version string separate from title
- `tracks.release_date` DATE
- `tracks.audio_quality` TEXT
- `tracks.duration` already exists (added via ALTER TABLE)
