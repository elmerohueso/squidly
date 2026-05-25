"""Job management routes."""

import json
from datetime import datetime

from flask import Blueprint, jsonify, request

from squidly import jobs
from squidly.db import get_db_connection
from squidly.storage import get_download_settings

jobs_bp = Blueprint('jobs', __name__)


def _requested_download_format(file_format):
    """Normalize requested download format."""
    normalized = str(file_format or '').strip().lower()
    if normalized in ('m4a', 'aac', 'mp4'):
        return 'm4a'
    if normalized == 'flac':
        return 'flac'
    return 'm4a'


def _matches_requested_format(file_format, candidate_format):
    """Check if candidate format matches requested format."""
    normalized_request = _requested_download_format(file_format)
    normalized_candidate = str(candidate_format or '').strip().lower()

    if normalized_request == 'flac':
        return normalized_candidate == 'flac'

    return normalized_candidate in ('m4a', 'aac', 'mp4')


def _download_job_exists_in_plex(cur, result_payload, job_payload):
    """Check if a download job result already exists in Plex library."""
    if not isinstance(result_payload, dict):
        return False

    artist = str(result_payload.get('artist') or '').strip()
    title = str(result_payload.get('title') or '').strip()
    album = str(result_payload.get('album') or '').strip()

    if not artist or not title:
        return False

    requested_format = _requested_download_format(
        job_payload.get('format') if isinstance(job_payload, dict) else None
    )

    rows = _lookup_track_metadata(cur, title, artist, album)
    exists = any(_matches_requested_format(requested_format, row.get('format')) for row in rows)
    return exists


def _lookup_track_metadata(cur, title, artist, album):
    """Look up track metadata from database."""
    from squidly.services.playlist_matching import _lookup_track_metadata as lookup
    return lookup(cur, title, artist, album)


def _effective_job_status(job_type, status, result_json):
    """Compute effective job status for download_track jobs."""
    if job_type != 'download_track':
        return status

    try:
        result = json.loads(result_json) if result_json else {}
    except (TypeError, ValueError):
        result = {}

    stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}

    if stages.get('written') == 'failed':
        return 'failed'

    return status


def get_jobs_filter_totals(exclude_bulk_playlist_add=False):
    """Get job count totals by status."""
    where_sql = 'WHERE job_type <> %s' if exclude_bulk_playlist_add else ''
    params = ('bulk_playlist_add',) if exclude_bulk_playlist_add else ()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT job_type, status, result_json
        FROM jobs
        {where_sql}
        """,
        params
    )
    rows = cur.fetchall() or []
    conn.close()

    totals = {
        'incomplete': 0,
        'complete': 0,
        'failed': 0
    }

    for row in rows:
        effective_status = _effective_job_status(
            row.get('job_type'),
            row.get('status'),
            row.get('result_json')
        )

        if effective_status in ('queued', 'in_progress'):
            totals['incomplete'] += 1
        elif effective_status == 'succeeded':
            totals['complete'] += 1
        elif effective_status == 'failed':
            totals['failed'] += 1

    return totals


@jobs_bp.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List jobs with optional filters."""
    status_filter = request.args.get('status')
    job_type_filter = request.args.get('job_type')
    jobs_filter = request.args.get('jobs_filter')
    exclude_bulk_playlist_add = request.args.get('exclude_bulk_playlist_add', '0').lower() in ('1', 'true', 'yes')

    limit = None
    limit_raw = request.args.get('limit')
    if limit_raw is not None:
        try:
            parsed_limit = int(limit_raw)
            if parsed_limit >= 1:
                limit = parsed_limit
        except ValueError:
            limit = None

    try:
        offset = int(request.args.get('offset', '0'))
    except ValueError:
        offset = 0
    offset = max(0, offset)

    where_clauses = []
    params = []
    if status_filter:
        where_clauses.append('status = %s')
        params.append(status_filter)
    if job_type_filter:
        where_clauses.append('job_type = %s')
        params.append(job_type_filter)
    if exclude_bulk_playlist_add:
        where_clauses.append('job_type <> %s')
        params.append('bulk_playlist_add')

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT id, job_type, status, payload_json, result_json, error_message,
               attempt_count, max_attempts, created_at, updated_at, run_after,
               locked_at, locked_by, started_at, finished_at, priority
        FROM jobs
        {where_sql}
        ORDER BY created_at DESC
        """,
        tuple(params)
    )
    rows = cur.fetchall() or []

    if jobs_filter:
        def matches_jobs_filter(row):
            effective_status = _effective_job_status(
                row.get('job_type'),
                row.get('status'),
                row.get('result_json')
            )

            if jobs_filter == 'failed':
                return effective_status == 'failed'
            if jobs_filter == 'complete':
                return effective_status == 'succeeded'
            if jobs_filter == 'incomplete':
                return effective_status in ('queued', 'in_progress')
            return True

        rows = [row for row in rows if matches_jobs_filter(row)]

    if jobs_filter == 'complete':
        rows.sort(
            key=lambda row: (
                row.get('finished_at') is not None,
                row.get('finished_at') or row.get('created_at')
            ),
            reverse=True
        )

    total_count = len(rows)
    if limit is None:
        paged_rows = rows[offset:]
    else:
        paged_rows = rows[offset:offset + limit]
    conn.close()

    jobs_list = []
    for row in paged_rows:
        try:
            payload = json.loads(row['payload_json'])
        except (TypeError, ValueError):
            payload = None
        try:
            result = json.loads(row['result_json']) if row['result_json'] else None
        except (TypeError, ValueError):
            result = None

        jobs_list.append({
            'id': row['id'],
            'job_type': row['job_type'],
            'status': row['status'],
            'payload': payload,
            'result': result,
            'error_message': row['error_message'],
            'attempt_count': row['attempt_count'],
            'max_attempts': row['max_attempts'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'run_after': row['run_after'],
            'locked_at': row['locked_at'],
            'locked_by': row['locked_by'],
            'started_at': row['started_at'],
            'finished_at': row['finished_at'],
            'priority': row['priority']
        })

    totals = get_jobs_filter_totals(exclude_bulk_playlist_add=exclude_bulk_playlist_add)
    return jsonify({'jobs': jobs_list, 'totals': totals, 'total_count': total_count})


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get job by id."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, job_type, status, payload_json, result_json, error_message,
               attempt_count, max_attempts, created_at, updated_at, run_after,
               locked_at, locked_by, started_at, finished_at, priority
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': 'Job not found'}), 404

    try:
        payload = json.loads(row['payload_json'])
    except (TypeError, ValueError):
        payload = None
    try:
        result = json.loads(row['result_json']) if row['result_json'] else None
    except (TypeError, ValueError):
        result = None

    return jsonify({
        'id': row['id'],
        'job_type': row['job_type'],
        'status': row['status'],
        'payload': payload,
        'result': result,
        'error_message': row['error_message'],
        'attempt_count': row['attempt_count'],
        'max_attempts': row['max_attempts'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
        'run_after': row['run_after'],
        'locked_at': row['locked_at'],
        'locked_by': row['locked_by'],
        'started_at': row['started_at'],
        'finished_at': row['finished_at'],
        'priority': row['priority']
    })


@jobs_bp.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel a queued or in-progress job."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT status
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return jsonify({'error': 'Job not found'}), 404

    if row['status'] not in ('queued', 'in_progress'):
        return jsonify({'error': f"Job is not cancellable (status={row['status']})"}), 400

    jobs.mark_job_cancelled(job_id)
    return jsonify({'success': True, 'job_id': job_id, 'status': 'cancelled'})


@jobs_bp.route('/api/jobs/cancel-pending', methods=['POST'])
def cancel_all_pending_jobs():
    """Delete user-visible incomplete jobs from the queue/table."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, job_type, status, result_json
        FROM jobs
        """
    )
    rows = cur.fetchall() or []

    delete_ids = []
    for row in rows:
        status = row.get('status')
        job_type = row.get('job_type')

        if job_type == 'bulk_playlist_add':
            continue

        if status in ('queued', 'in_progress'):
            delete_ids.append(row['id'])
            continue

        if job_type != 'download_track' or status != 'succeeded':
            continue

        try:
            result = json.loads(row['result_json']) if row.get('result_json') else {}
        except (TypeError, ValueError):
            result = {}

        stages = result.get('stages') if isinstance(result, dict) and isinstance(result.get('stages'), dict) else {}
        if stages.get('playlist_added') == 'queued':
            delete_ids.append(row['id'])

    if not delete_ids:
        conn.close()
        return jsonify({'success': True, 'deleted_count': 0})

    placeholders = ','.join(['%s'] * len(delete_ids))
    cur.execute(
        f"DELETE FROM jobs WHERE id IN ({placeholders})",
        tuple(delete_ids)
    )
    deleted_count = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'deleted_count': deleted_count})


@jobs_bp.route('/api/jobs/cancel-failed', methods=['POST'])
def cancel_failed_jobs():
    """Cancel all failed jobs."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status = 'cancelled',
            updated_at = %s,
            finished_at = %s
        WHERE status = 'failed'
        """,
        (datetime.utcnow().isoformat() + 'Z', datetime.utcnow().isoformat() + 'Z')
    )
    cancelled_count = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'cancelled_count': cancelled_count})


@jobs_bp.route('/api/jobs/<int:job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """Retry an existing failed/completed-with-errors job by re-queueing it."""
    now = datetime.utcnow().isoformat() + 'Z'
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT job_type, status, result_json, payload_json
        FROM jobs
        WHERE id = %s
        """,
        (job_id,)
    )
    row = cur.fetchone()

    if row is None:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404

    effective_status = _effective_job_status(row['job_type'], row['status'], row.get('result_json'))
    retryable = effective_status == 'failed'

    if not retryable:
        conn.close()
        return jsonify({'error': f"Job is not retryable (status={row['status']}, effective_status={effective_status})"}), 400

    # For download_track jobs, check if the track already exists in Plex
    if row['job_type'] == 'download_track':
        try:
            result = json.loads(row['result_json']) if row['result_json'] else {}
        except (TypeError, ValueError):
            result = {}

        try:
            payload = json.loads(row['payload_json']) if row.get('payload_json') else {}
        except (TypeError, ValueError):
            payload = {}

        playlist_name = ''
        if isinstance(payload, dict):
            playlist_name = str(payload.get('plex_playlist') or '').strip()
        if not playlist_name and isinstance(result, dict):
            playlist_name = str(result.get('playlist_name') or '').strip()

        if not playlist_name and _download_job_exists_in_plex(cur, result, payload):
            conn.close()
            return jsonify({
                'error': 'Track already exists in Plex for the selected format. Retry skipped.',
                'job_id': job_id,
                'status': 'already_exists_in_plex'
            }), 409

    cur.execute(
        """
        UPDATE jobs
        SET status = 'queued',
            attempt_count = 0,
            result_json = NULL,
            error_message = NULL,
            updated_at = %s,
            run_after = %s,
            locked_at = NULL,
            locked_by = NULL,
            started_at = NULL,
            finished_at = NULL
        WHERE id = %s
        """,
        (now, now, job_id)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'})
