"""Shared utility helpers for Squidly."""

import logging
import re
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


def _run_async(fn):
    """Run a callable in a background daemon thread."""
    def _wrapper():
        try:
            fn()
        except Exception:
            logger.exception("[ASYNC] Background task failed")
    threading.Thread(target=_wrapper, daemon=True).start()


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


def normalize_match_text(value: str, strip_trailing_parenthetical: bool = False) -> str:
    """Normalize text for fuzzy matching.

    Lowercases, strips trailing parenthetical/bracketed text if requested,
    replaces non-alphanumeric runs with single spaces, and trims.
    """
    text = str(value or '').strip().lower()
    if strip_trailing_parenthetical:
        text = re.sub(r'\s*[\(\[].*[\)\]]\s*$', '', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_year_from_text(text: str) -> str:
    """Extract a 4-digit year from arbitrary text.

    Returns an empty string if no year is found.
    """
    if not text or not isinstance(text, str):
        return ''
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else ''


def _normalize_library_track_path(file_path: str, root: str | list[str]) -> str:
    """Normalize a library track file path to a relative path.

    Strips the given root prefix (or longest matching root from a list),
    normalizes slashes, and returns the relative path.
    Returns empty string if path is invalid.
    """
    if not file_path or not isinstance(file_path, str):
        return ''

    normalized = file_path.replace('\\', '/').lstrip('/')

    if root:
        roots = root if isinstance(root, list) else [root]
        roots = sorted(
            [r.replace('\\', '/').lstrip('/').rstrip('/') for r in roots if r],
            key=len,
            reverse=True,
        )
        for r in roots:
            if normalized.startswith(r + '/'):
                normalized = normalized[len(r) + 1:]
                break

    return normalized


def _extract_plex_library_id(value) -> str | None:
    """Extract a Plex library ID from a ratingKey or key attribute.

    Handles both integer ratingKey and string key paths like '/library/metadata/123'.
    Returns the ID as a string, or None if not extractable.
    """
    if value is None:
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.startswith('/library/metadata/'):
            return value.split('/')[-1] or None
        if value.isdigit():
            return value

    return None


def _read_embedded_hifi_ids(file_path: str) -> dict:
    """Read embedded Tidal HiFi IDs from audio file tags.

    Returns a dict with 'track_id', 'album_id', and 'isrc' keys.
    Returns empty dict if file cannot be read or tags not found.
    """
    import os
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4

    if not file_path or not os.path.exists(file_path):
        return {}

    try:
        lower_path = file_path.lower()
        if lower_path.endswith('.flac'):
            audio = FLAC(file_path)
            def first_tag(key):
                values = audio.get(key)
                if not values:
                    return ''
                return str(values[0]) if values else ''
            return {
                'track_id': first_tag('TIDAL_TRACK_ID').strip() or None,
                'album_id': first_tag('TIDAL_ALBUM_ID').strip() or None,
                'isrc': first_tag('ISRC').strip() or None,
            }
        elif lower_path.endswith('.m4a'):
            audio = MP4(file_path)

            def first_text(key):
                values = audio.get(key) or []
                if not values:
                    return None
                val = values[0]
                if isinstance(val, bytes):
                    val = val.decode('utf-8', errors='ignore')
                return str(val).strip() or None

            return {
                'track_id': first_text('----:com.apple.iTunes:tidal_track_id'),
                'album_id': first_text('----:com.apple.iTunes:tidal_album_id'),
                'isrc': first_text('----:com.apple.iTunes:isrc'),
            }
    except Exception:
        pass

    return {}
