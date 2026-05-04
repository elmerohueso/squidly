"""Shared fixtures for Squidly tests.

Sets dummy POSTGRES_* env vars before any squidly imports so that
config.py does not raise RuntimeError. Tests in this suite do not
require a running database or Docker containers.
"""

import os

# Set required env vars BEFORE any squidly module imports.
# These are only needed to satisfy config.py's startup validation.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "squidly_test")
os.environ.setdefault("POSTGRES_USER", "squidly_test")
os.environ.setdefault("POSTGRES_PASSWORD", "squidly_test")

# Skip the module-level startup sequence (init_db, workers, etc.)
# so tests can import squidly modules without a live database.
os.environ.setdefault("SQUIDLY_SKIP_STARTUP", "1")

import pytest
