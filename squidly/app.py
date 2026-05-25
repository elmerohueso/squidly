
import logging
from squidly.logging_setup import setup_logging
setup_logging()

from plexapi.myplex import MyPlexAccount, MyPlexPinLogin
from plexapi.server import PlexServer


from flask import Flask, render_template, jsonify, request, session, Response, stream_with_context
from flask_cors import CORS
import threading
import os
import json
import base64
import requests
import concurrent.futures
import psycopg2
import psycopg2.extras
from squidly.config import DOWNLOADS_ROOT
from squidly.db import init_db
from squidly.job_queue import recover_stale_in_progress_jobs

from squidly.utils import (
    _now_utc,
    _safe_float,
    _safe_int,
    clean_path_components,
    extract_year_from_text,
    normalize_match_text,
    sanitize_filename_component,
)
from squidly.services.hifi import (
    get_hifi_album_object,
    get_hifi_artist_object,
    get_hifi_track_object,
    _build_normalized_hifi_track_object,
    _get_hifi_album_dedupe_key,
    _get_hifi_track_dedupe_key,
    _get_hifi_audio_quality_rank,
)
from itertools import cycle
from datetime import datetime, timedelta
import time
import sys
import subprocess
import shutil
import re
import threading
import socket
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus
from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCOP, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from io import BytesIO

from squidly.plex import (
    _get_plex_server_for_user,
    _is_plex_library_scan_active,
    _plex_call_with_timeout,
    get_all_plex_users,
    get_plex_health_status,
    get_plex_music_playlists,
    plex_healthcheck,
    plex_pin_sessions,
    process_plex_library_update_job,
    set_plex_health_status,
    test_plex_connection,
    wait_for_plex_library_scan_completion,
)

from squidly.services.hifi import (
    _fetch_hifi_search_results,
    _fetch_hifi_artist_payload,
    _fetch_hifi_album_payload,
    _fetch_hifi_track_payload,
    _fetch_hifi_track_manifests_payload,
    _fetch_hifi_track_info_payload,
    _normalize_hifi_playlist_items,
    _extract_hifi_album_track_items,
)

from squidly.jobs.workers import (
    JobCancelledError,
    _raise_if_job_cancelled,
    start_workers,
)

from ytmusicapi import YTMusic

from squidly import downloads
from squidly.services import qobuz
from squidly import jobs

from squidly.jobs.orchestration import (
    is_job_type_running_or_queued,
    queue_pending_playlist_addition,
    queue_plex_listen_history_sync,
    queue_recommendation_generation,
    start_plex_library_update_job,
    wait_for_job_type,
)

from squidly.storage import (
    any_download_jobs_running,
    can_start_plex_library_update,
    clear_plex_config,
    clear_plex_user_settings,
    get_all_plex_account_mappings,
    get_download_settings,
    get_download_write_gate_state,
    get_existing_artist_titles,
    get_existing_isrcs,
    get_last_download_activity_at,
    get_library_update_status,
    get_listen_history,
    get_listen_history_sync_status,
    get_listenbrainz_config,
    get_plex_config,
    get_plex_user_settings,
    get_recent_listen_history_seeds,
    get_recommendation_playlist,
    get_todays_recommendation_playlist,
    get_ytm_config,
    has_listen_history,
    list_recommendation_playlists,
    normalize_db_timestamp,
    save_download_settings,
    save_listenbrainz_config,
    save_plex_account_id,
    save_plex_config,
    save_plex_user_setting,
    save_ytm_config,
    set_last_download_activity_at,
    set_last_job_finished_at,
    set_last_library_update_time,
    set_listen_history_sync_status,
    upsert_listen_history_entries,
    set_library_update_needed,
    save_recommendation_playlist,
)

logger = logging.getLogger(__name__)

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(
    __name__,
    static_folder=os.path.join(base_dir, 'static'),
    template_folder=os.path.join(base_dir, 'templates')
)
CORS(app)

from squidly.api.health import health_bp
app.register_blueprint(health_bp)

from squidly.api.jobs import jobs_bp
app.register_blueprint(jobs_bp)

from squidly.api.settings import settings_bp
app.register_blueprint(settings_bp)

from squidly.api.search import search_bp
app.register_blueprint(search_bp)

from squidly.api.plex_routes import plex_bp
app.register_blueprint(plex_bp)

from squidly.api.downloads import downloads_bp
app.register_blueprint(downloads_bp)

from squidly.api.recommendations import recommendations_bp
app.register_blueprint(recommendations_bp)

from squidly.api.listen_history import listen_history_bp
app.register_blueprint(listen_history_bp)

from squidly.api.hifi_matches import hifi_matches_bp
app.register_blueprint(hifi_matches_bp)

# ...existing code...

# Verify downloads directory
if not os.path.exists(DOWNLOADS_ROOT):
    logger.error("Error: Downloads directory does not exist: %s", DOWNLOADS_ROOT)
elif not os.access(DOWNLOADS_ROOT, os.W_OK):
    logger.error("Error: Downloads directory is not writable: %s", DOWNLOADS_ROOT)
else:
    logger.info("Downloads directory ready: %s", DOWNLOADS_ROOT)

# Startup sequence
if os.environ.get("SQUIDLY_SKIP_STARTUP") != "1":
    init_db()
    recover_stale_in_progress_jobs()
    downloads.seed_mirrors_from_json()
    downloads.refresh_squid_urls()
    logger.info("Squidly starting up...")
    downloads.validate_all_endpoints()
    plex_healthcheck()
    start_workers()

    try:
        os.makedirs("/app/temp", exist_ok=True)
        logger.info("Temp folder ready (/app/temp)")
    except Exception as e:
        logger.info("Failed to create temp folder: %s", e)
