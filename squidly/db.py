"""Database helpers for Squidly."""

import psycopg2
import psycopg2.extras

from squidly.config import DATABASE_URL


def get_db_connection():
    """Get a PostgreSQL connection that returns dictionary-like rows."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
