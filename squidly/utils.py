"""Shared utility helpers for Squidly."""

import re
from datetime import datetime


def _safe_int(value):
    """Convert a value to int, returning None on failure."""
    try:
        if value is None or value == '':
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _safe_float(value, default=0.0):
    """Convert a value to float, returning default on failure."""
    try:
        if value is None or value == '':
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _now_utc():
    """Return the current UTC datetime."""
    return datetime.utcnow()


def sanitize_filename_component(value: str) -> str:
    """Sanitize a single filename or folder name component.

    Replaces slashes, removes Windows-invalid characters, normalizes
    Unicode quotes, strips control characters and trailing periods/spaces.
    Returns ``'_'`` if the result would be empty.
    """
    if not value:
        return value

    sanitized = value.replace('/', '-').replace('\\', '-')
    sanitized = sanitized.replace('<', '').replace('>', '')
    sanitized = sanitized.replace(':', '-').replace('"', "'")
    sanitized = sanitized.replace('|', '-').replace('?', '')
    sanitized = sanitized.replace('*', '')

    sanitized = sanitized.replace('\u2018', "'").replace('\u2019', "'")
    sanitized = sanitized.replace('\u201c', '"').replace('\u201d', '"')
    sanitized = sanitized.replace('\u2013', '-').replace('\u2014', '-')

    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    sanitized = sanitized.rstrip('. ')
    sanitized = sanitized.lstrip(' ')

    if not sanitized:
        sanitized = '_'

    return sanitized


def clean_path_components(file_path: str) -> str:
    """Strip trailing periods and spaces from each path component."""
    parts = file_path.replace('\\', '/').split('/')
    cleaned_parts = [part.rstrip('. ') if part else part for part in parts]
    return '/'.join(cleaned_parts)


def extract_year_from_text(text: str) -> str:
    """Extract a 4-digit year from arbitrary text.

    Returns an empty string if no year is found.
    """
    if not text or not isinstance(text, str):
        return ''
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else ''
