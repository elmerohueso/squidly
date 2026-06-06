"""Downloads routes."""
from flask import Blueprint
downloads_bp = Blueprint("downloads", __name__)

@downloads_bp.route('/api/downloads', methods=['POST'])
def download_track():
    """Enqueue a download job."""
    from flask import request, jsonify
    from squidly.infrastructure.storage import get_download_settings, set_last_download_activity_at
    from squidly.infrastructure.job_queue import enqueue_job
    from squidly.services.hifi import get_hifi_track_object
    from squidly.infrastructure.config import DEFAULT_DOWNLOAD_SETTINGS
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    payload = request.get_json(silent=True) or {}
    track_id = payload.get('trackId')
    mbid = payload.get('mbid')
    isrc = payload.get('isrc')
    settings = get_download_settings()
    file_naming_album = settings.get('file_naming_album', DEFAULT_DOWNLOAD_SETTINGS['file_naming_album'])
    file_naming = payload.get('fileNamingAlbum') or payload.get('fileNaming') or file_naming_album
    
    if not track_id and not mbid and not isrc:
        logger.info("[DOWNLOAD] ERROR: trackId, mbid, or isrc is required")
        return jsonify({'error': 'trackId, mbid, or isrc is required'}), 400
    
    quality_choice = str(payload.get('downloadQuality', payload.get('quality', 'LOSSLESS'))).strip().upper()
    if quality_choice not in ('LOSSLESS', 'HIGH', 'LOW'):
        quality_choice = 'LOSSLESS'
    
    ignore_matches = payload.get('ignore_matches')
    if ignore_matches is None:
        ignore_matches = settings.get('ignore_matches', DEFAULT_DOWNLOAD_SETTINGS.get('ignore_matches', False))
    ignore_matches = bool(ignore_matches)
    
    plex_playlist = payload.get('plex_playlist')
    plex_user_id = payload.get('plex_user_id')
    
    logger.info("[DOWNLOAD_ENQUEUE] track_id=%s quality=%s playlist=%s user_id=%s ignore_matches=%s mbid=%s isrc=%s",
                track_id, quality_choice, plex_playlist, plex_user_id, ignore_matches, mbid, isrc)
    
    artist_name = payload.get('artist')
    title_name = payload.get('title')
    
    # If mbid is provided but no track_id, try to resolve ISRC from MusicBrainz
    if mbid and not isrc:
        from squidly.services.musicbrainz import mb_get_recording
        rec = mb_get_recording(mbid)
        if rec:
            isrcs = rec.get('isrcs') or []
            if isrcs:
                isrc = isrcs[0]
            if not title_name:
                title_name = rec.get('title')
            if not artist_name:
                artist_credit = rec.get('artist-credit', [])
                artist_name = '; '.join(c.get('artist', {}).get('name', '') for c in artist_credit if c.get('artist'))
    
    # If ISRC available but no track_id, try to resolve to a Tidal ID
    if not track_id and isrc:
        from squidly.services.track_resolver import resolve_track
        result = resolve_track(
            title=title_name or '',
            track_artist=artist_name or '',
            isrc=isrc,
            settings=settings,
        )
        resolved_id = result.get('hifi_id')
        if resolved_id:
            track_id = str(resolved_id)
    
    if not track_id:
        logger.info("[DOWNLOAD] ERROR: could not resolve trackId from mbid/isrc")
        return jsonify({'error': 'Could not resolve track ID from provided identifier'}), 400
    
    if not title_name or not artist_name:
        try:
            track_obj = get_hifi_track_object(track_id, include_streams=False, include_album=False, audio_quality=quality_choice)
            track_data = track_obj.get('track') if isinstance(track_obj, dict) else {}
            if isinstance(track_data, dict):
                if not title_name:
                    title_name = track_data.get('title')
                if not artist_name:
                    artists = track_data.get('artists')
                    if isinstance(artists, list) and artists:
                        names = [str(a.get('name', '')).strip() for a in artists if isinstance(a, dict) and a.get('name')]
                        artist_name = '; '.join(names) if names else None
                    elif isinstance(artists, dict) and artists.get('name'):
                        artist_name = str(artists.get('name')).strip()
        except Exception as e:
            logger.info("[DOWNLOAD] Failed to prefetch track metadata for job payload: %s", e)
    
    job_payload = {
        'trackId': track_id,
        'fileNaming': file_naming,
        'fileNamingAlbum': payload.get('fileNamingAlbum') or file_naming_album,
        'plex_playlist': plex_playlist,
        'plex_user_id': plex_user_id,
        'ignore_matches': ignore_matches,
        'downloadQuality': quality_choice,
    }
    
    if mbid:
        job_payload['mbid'] = mbid
    if isrc:
        job_payload['isrc'] = isrc
    if artist_name:
        job_payload['artist'] = artist_name
    if title_name:
        job_payload['title'] = title_name
    
    job_id = enqueue_job('download_track', job_payload)
    set_last_download_activity_at(datetime.utcnow())
    logger.info("[DOWNLOAD_ENQUEUE] Queued download job %s for track %s", job_id, track_id)
    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202
