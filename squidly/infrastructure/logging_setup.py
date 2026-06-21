"""Centralized logging setup for Squidly.

Configures a root logger that writes to both stdout (for Docker logs) and
a rotating file at /logs/squidly.log (7-day retention).  Also configures
gunicorn access/error loggers to write to separate rotating files.

Must be called early during startup, before any module-level print statements
execute.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.environ.get('SQUIDLY_LOG_DIR_OVERRIDE', '/logs')
SQUIDLY_LOG = os.path.join(LOG_DIR, 'squidly.log')
GUNICORN_ACCESS_LOG = os.path.join(LOG_DIR, 'gunicorn_access.log')
GUNICORN_ERROR_LOG = os.path.join(LOG_DIR, 'gunicorn_error.log')

_LOG_FORMAT = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def _make_file_handler(path, level=logging.DEBUG):
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = TimedRotatingFileHandler(
        path,
        when='midnight',
        interval=1,
        backupCount=7,
        utc=True,
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    stream.setLevel(logging.DEBUG)
    stream.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(stream)

    root.addHandler(_make_file_handler(SQUIDLY_LOG))

    gunicorn_access = logging.getLogger('gunicorn.access')
    gunicorn_access.setLevel(logging.INFO)
    gunicorn_access.addHandler(_make_file_handler(GUNICORN_ACCESS_LOG, logging.INFO))
    gunicorn_access.propagate = False

    gunicorn_error = logging.getLogger('gunicorn.error')
    gunicorn_error.setLevel(logging.INFO)
    gunicorn_error.addHandler(_make_file_handler(GUNICORN_ERROR_LOG, logging.INFO))
    gunicorn_error.propagate = False
