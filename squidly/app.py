
import logging
from squidly.infrastructure.logging_setup import setup_logging
setup_logging()

from flask import Flask
from flask_cors import CORS
import os

from squidly.infrastructure.config import DOWNLOADS_ROOT
from squidly.infrastructure.db import init_db
from squidly.infrastructure.job_queue import recover_stale_in_progress_jobs
from squidly.infrastructure import downloads
from squidly.infrastructure.plex import plex_healthcheck
from squidly.jobs.workers import start_workers

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
    downloads.validate_all_endpoints_from_db()
    plex_healthcheck()
    start_workers()

    try:
        os.makedirs("/app/temp", exist_ok=True)
        logger.info("Temp folder ready (/app/temp)")
    except Exception as e:
        logger.info("Failed to create temp folder: %s", e)
