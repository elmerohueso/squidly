"""Configuration and constants for Squidly.

This module centralizes environment-derived settings and shared constants so the
rest of the application can import them cleanly.
"""

import os
import socket
from urllib.parse import quote_plus

# PostgreSQL configuration (required)
postgres_host = (os.environ.get('POSTGRES_HOST') or os.environ.get('PORTGRES_HOST') or '').strip()
postgres_db = (os.environ.get('POSTGRES_DB') or '').strip()
postgres_user = (os.environ.get('POSTGRES_USER') or '').strip()
postgres_password = (os.environ.get('POSTGRES_PASSWORD') or '').strip()

missing_postgres_vars = []
if not postgres_host:
    missing_postgres_vars.append('POSTGRES_HOST')
if not postgres_db:
    missing_postgres_vars.append('POSTGRES_DB')
if not postgres_user:
    missing_postgres_vars.append('POSTGRES_USER')
if not postgres_password:
    missing_postgres_vars.append('POSTGRES_PASSWORD')

if missing_postgres_vars:
    raise RuntimeError(
        'Missing required PostgreSQL environment variables: ' + ', '.join(missing_postgres_vars)
    )

DATABASE_URL = (
    f"postgresql://{quote_plus(postgres_user)}:{quote_plus(postgres_password)}"
    f"@{postgres_host}:5432/{postgres_db}"
)

# Download paths
DOWNLOADS_ROOT = '/downloads'

# Worker identifier used for job locking
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}"

# Default download settings (used when database doesn't yet have values)
DEFAULT_DOWNLOAD_SETTINGS = {
    'format': 'original',
    'quality': 'LOSSLESS',
    'parent_folder': '',
    'file_naming_album': '{artist}/{album}/{track} - {title}.{ext}',
    'jobs_refresh_interval_seconds': 30,
    'ignore_matches': False
}

# Temporary scratch directory used during downloads
TEMP_FOLDER = '/app/temp'
