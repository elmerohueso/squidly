"""Verify import chains have no circular dependencies after Phase 3 refactoring."""


def test_import_db():
    from squidly.db import get_db_connection, init_db

    assert callable(get_db_connection)
    assert callable(init_db)


def test_import_storage():
    from squidly.storage import (
        any_download_jobs_running,
        can_start_plex_library_update,
        clear_plex_config,
        clear_plex_user_settings,
        get_download_settings,
        get_download_write_gate_state,
        get_last_download_activity_at,
        get_library_update_status,
        get_listenbrainz_config,
        get_plex_config,
        get_plex_user_settings,
        get_ytm_config,
        normalize_db_timestamp,
        save_download_settings,
        save_listenbrainz_config,
        save_plex_config,
        save_plex_user_setting,
        save_ytm_config,
        set_last_download_activity_at,
        set_last_job_finished_at,
        set_last_library_update_time,
        set_library_update_needed,
    )


def test_import_plex():
    from squidly.plex import (
        _get_plex_server_for_user,
        _is_plex_library_scan_active,
        add_tracks_to_plex_playlist,
        get_all_plex_users,
        get_last_successful_plex_sync_finished_at,
        get_plex_health_status,
        get_plex_music_playlists,
        plex_healthcheck,
        plex_pin_sessions,
        process_plex_library_update_job,
        set_plex_health_status,
        test_plex_connection,
        wait_for_plex_library_scan_completion,
    )


def test_import_jobs():
    from squidly.jobs import (
        RetryableError,
        PermanentError,
        claim_next_job,
        compute_job_backoff_seconds,
        enqueue_job,
        is_job_cancelled,
        mark_job_failed,
        mark_job_in_progress,
        mark_job_retrying,
        mark_job_succeeded,
        mark_job_cancelled,
        recover_stale_in_progress_jobs,
        requeue_claimed_job,
        serialize_job_payload,
        update_job_progress,
    )


def test_import_orchestration():
    from squidly.orchestration import (
        JOB_TYPES,
        any_plex_library_update_jobs_running_or_queued,
        any_plex_listen_history_sync_jobs_running_or_queued,
        any_plex_sync_jobs_running_or_queued,
        count_pending_playlist_adds,
        delete_pending_playlist_adds,
        get_pending_playlist_adds,
        is_job_type_running_or_queued,
        queue_bulk_playlist_add_job,
        queue_fresh_finds_auto_download,
        queue_if_not_running,
        queue_plex_library_sync,
        queue_plex_library_update,
        queue_plex_listen_history_sync,
        queue_pending_playlist_addition,
        queue_recommendation_generation,
        start_plex_library_update_job,
        start_plex_sync_job,
    )


def test_import_downloads():
    from squidly.downloads import (
        ManifestDownloadError,
        PermanentDownloadError,
        TransientDownloadError,
        cleanup_file,
        convert_to_mp3,
        detect_audio_format,
        download_cover_image,
        download_track_all_stages_done,
        format_tidal_image_url,
        make_request_with_retry,
        make_request_with_retry_rotating_mirrors,
        seed_mirrors_from_json,
        validate_all_endpoints,
        validate_endpoint,
    )


def test_import_utils():
    from squidly.utils import (
        _now_utc,
        _safe_float,
        _safe_int,
        clean_path_components,
        extract_year_from_text,
        sanitize_filename_component,
    )


def test_import_matching():
    from squidly.matching import (
        MATCH_REVIEW_ARTWORK_SIZE,
        MATCH_REVIEW_HIFI_ARTWORK_SIZE,
        MATCH_REVIEW_HIFI_ARTIST_ARTWORK_SIZE,
        _extract_hifi_item_artists,
        _extract_primary_hifi_artist,
        _merge_match_state,
        _is_hifi_explicit,
        _format_hifi_track_title,
        _extract_hifi_album_track_titles,
        _has_explicit_marker,
        _score_explicit_alignment,
        _score_album_track_title_alignment,
        _score_artist_candidate_name,
        _extract_album_candidate_artist_names,
        _score_album_candidate_artist_alignment,
        _score_album_candidate_title,
        _score_track_candidate_payload,
        _serialize_match_variants,
        _evaluate_album_candidate,
        _get_artist_row,
        _get_album_row,
        _get_track_row_by_path,
        _upsert_artist_row,
        _upsert_album_row,
        _upsert_track_row,
        _fetch_source_album_track_titles_map,
        _find_hifi_track_search_candidate,
        _cascade_track_confirm_ids,
        _refresh_album_completeness,
        _build_stored_track_match_lookup,
        _build_stored_album_match_lookup,
        _build_stored_artist_match_lookup,
        _fetch_match_review_row,
        _build_artist_match_candidates,
        _build_album_match_candidates,
        _build_track_match_candidates,
        _fetch_hifi_match_coverage_counts,
        _refresh_hifi_match_coverage_progress,
        any_hifi_match_jobs_running_or_queued,
        has_hifi_match_seed_data,
        queue_hifi_match_job,
        start_hifi_match_job,
    )


def test_import_workers():
    from squidly.workers import (
        JobCancelledError,
        _raise_if_job_cancelled,
        start_workers,
        worker_loop,
        download_track_worker,
        plex_sync_worker,
        plex_library_update_worker,
        plex_sync_scheduler_worker,
        recommendation_scheduler_worker,
    )

    assert issubclass(JobCancelledError, Exception)
    assert callable(_raise_if_job_cancelled)
    assert callable(start_workers)
    assert callable(worker_loop)


def test_import_hifi():
    from squidly.hifi import (
        _fetch_hifi_search_results,
        _fetch_hifi_artist_payload,
        _fetch_hifi_album_payload,
        _fetch_hifi_track_payload,
        _fetch_hifi_track_manifests_payload,
        _fetch_hifi_track_info_payload,
        _normalize_hifi_playlist_items,
        _extract_hifi_album_track_items,
        _format_hifi_image_value,
        _extract_hifi_image_string,
        _normalize_tidal_image_url,
        _get_hifi_audio_quality_rank,
        extract_hifi_track_info,
        extract_hifi_album_info,
        extract_hifi_artist_info,
    )


def test_import_app_no_circular():
    """Importing app.py should not raise ImportError from circular deps."""
    from squidly.app import app

    assert app is not None


def test_storage_does_not_import_app():
    """storage.py must not import from app to avoid circular deps."""
    import squidly.storage as storage_module
    import inspect

    source = inspect.getsource(storage_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_plex_does_not_import_app():
    """plex.py must not import from app to avoid circular deps."""
    import squidly.plex as plex_module
    import inspect

    source = inspect.getsource(plex_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_jobs_does_not_import_app():
    """jobs.py must not import from app to avoid circular deps."""
    import squidly.jobs as jobs_module
    import inspect

    source = inspect.getsource(jobs_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_db_does_not_import_app():
    """db.py must not import from app to avoid circular deps."""
    import squidly.db as db_module
    import inspect

    source = inspect.getsource(db_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_matching_does_not_import_app():
    """matching.py must not import from app at top level to avoid circular deps (lazy imports inside functions are allowed)."""
    import squidly.matching as matching_module
    import inspect

    source = inspect.getsource(matching_module)
    lines = source.split('\n')
    top_level_imports = [l for l in lines if l.startswith('from squidly.app') or l.startswith('import squidly.app')]
    assert len(top_level_imports) == 0, f"matching.py has top-level app imports: {top_level_imports}"


def test_workers_does_not_import_app_directly():
    """workers.py should not have top-level imports from app (lazy imports only)."""
    import squidly.workers as workers_module
    import inspect

    source = inspect.getsource(workers_module)
    lines = source.split('\n')
    top_level_imports = [l for l in lines if l.startswith('from squidly.app') or l.startswith('import squidly.app')]
    assert len(top_level_imports) == 0, f"workers.py has top-level app imports: {top_level_imports}"


def test_hifi_does_not_import_app():
    """hifi.py must not import from app to avoid circular deps."""
    import squidly.hifi as hifi_module
    import inspect

    source = inspect.getsource(hifi_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_plex_does_not_import_app():
    """plex.py must not import from app to avoid circular deps."""
    import squidly.plex as plex_module
    import inspect

    source = inspect.getsource(plex_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_jobs_does_not_import_app():
    """jobs.py must not import from app to avoid circular deps."""
    import squidly.jobs as jobs_module
    import inspect

    source = inspect.getsource(jobs_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source


def test_db_does_not_import_app():
    """db.py must not import from app to avoid circular deps."""
    import squidly.db as db_module
    import inspect

    source = inspect.getsource(db_module)
    assert "from squidly.app" not in source
    assert "import squidly.app" not in source
