# -*- coding: utf-8 -*-
"""Scheduler deployment verification — build info startup logs."""
from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest

from services.deploy_build_info_v1 import normalize_git_sha, resolve_deploy_git_sha
from services.runtime_startup_v1 import log_runtime_startup_banner


def test_normalize_git_sha_shortens_full_commit() -> None:
    assert normalize_git_sha("18d46ad1234567890abcdef1234567890abcdef") == "18d46ad"


def test_resolve_deploy_git_sha_from_env() -> None:
    with patch.dict(os.environ, {"CARTFLOW_GIT_SHA": "18d46ad"}, clear=False):
        assert resolve_deploy_git_sha() == "18d46ad"


def test_scheduler_startup_logs_build_and_archive_config() -> None:
    os.environ["ENV"] = "production"
    os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
    os.environ["CARTFLOW_GIT_SHA"] = "18d46ad"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED"] = "1"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS"] = "30"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE"] = "100"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS"] = "60"
    os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
    os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"

    buf = io.StringIO()
    with redirect_stdout(buf):
        log_runtime_startup_banner()
    text = buf.getvalue()
    assert "[SCHEDULER BUILD INFO]" in text
    assert "git_sha=18d46ad" in text
    assert "process_role=scheduler" in text
    assert "[DASHBOARD SNAPSHOT ARCHIVE CONFIG]" in text
    assert "archive_enabled=true" in text

    for key in (
        "CARTFLOW_GIT_SHA",
        "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED",
        "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_RETENTION_DAYS",
        "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_BATCH_SIZE",
        "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_TICK_MAX_SECONDS",
    ):
        os.environ.pop(key, None)
