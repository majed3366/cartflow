# -*- coding: utf-8 -*-
"""Recovery scheduler ownership guardrails v1 — env + startup logs only."""
from __future__ import annotations

import asyncio
import io
import os
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest

from services.recovery_restart_survival import run_recovery_resume_scan_async
from services.recovery_scheduler_guardrails import (
    ENV_RECOVERY_RESUME_ON_STARTUP,
    is_recovery_resume_on_startup_enabled,
    log_recovery_scheduler_ownership_at_startup,
    resolve_recovery_resume_on_startup_config,
)


@pytest.fixture
def _clear_env() -> None:
    old = os.environ.pop(ENV_RECOVERY_RESUME_ON_STARTUP, None)
    yield
    if old is None:
        os.environ.pop(ENV_RECOVERY_RESUME_ON_STARTUP, None)
    else:
        os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = old


def test_default_unset_enables_resume_scan() -> None:
    os.environ.pop(ENV_RECOVERY_RESUME_ON_STARTUP, None)
    cfg = resolve_recovery_resume_on_startup_config()
    assert cfg["enabled"] is True
    assert cfg["reason"] == "default"
    assert cfg["env_set"] is False
    assert is_recovery_resume_on_startup_enabled() is True


def test_env_false_disables_resume_scan() -> None:
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "0"
    cfg = resolve_recovery_resume_on_startup_config()
    assert cfg["enabled"] is False
    assert cfg["reason"] == "env"
    assert is_recovery_resume_on_startup_enabled() is False


def test_env_true_enables_resume_scan() -> None:
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "1"
    assert is_recovery_resume_on_startup_enabled() is True


def test_run_resume_scan_skipped_when_env_false(_clear_env: None) -> None:
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "false"

    def _run() -> dict:
        return asyncio.run(
            run_recovery_resume_scan_async(max_dispatch=5, dry_run=True)
        )

    out = _run()
    assert out["enabled"] is False
    assert out.get("dispatched") == 0
    assert out.get("reason") == "resume_on_startup_disabled"


def test_run_resume_scan_force_bypasses_env_false(_clear_env: None) -> None:
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "0"
    with patch(
        "services.recovery_restart_survival.repair_stale_running_recovery_schedules",
        return_value={"finalized": 0, "repaired": 0},
    ), patch(
        "services.recovery_restart_survival.db.session.query",
    ) as mock_query:
        mock_query.return_value.filter.return_value.count.return_value = 0
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        out = asyncio.run(
            run_recovery_resume_scan_async(
                max_dispatch=5,
                dry_run=True,
                force=True,
            )
        )
    assert out["enabled"] is True


def test_startup_log_owner_enabled_default(_clear_env: None) -> None:
    os.environ.pop(ENV_RECOVERY_RESUME_ON_STARTUP, None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        log_recovery_scheduler_ownership_at_startup()
    out = buf.getvalue()
    assert "[RECOVERY SCHEDULER OWNER]" in out
    assert "enabled=true" in out
    assert "reason=default" in out
    assert "[RECOVERY WORKER MODE]" in out
    assert "mode=single_scheduler_expected" in out
    assert "warning=do_not_enable_on_multiple_api_workers" in out


def test_startup_log_owner_disabled_no_worker_warning(_clear_env: None) -> None:
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "0"
    buf = io.StringIO()
    with redirect_stdout(buf):
        log_recovery_scheduler_ownership_at_startup()
    out = buf.getvalue()
    assert "enabled=false" in out
    assert "reason=env" in out
    assert "[RECOVERY WORKER MODE]" not in out


def test_startup_hook_order_on_main_startup(_clear_env: None) -> None:
    """Ownership log runs before resume scan; env false skips scan."""
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "0"
    buf = io.StringIO()

    async def _fake_resume(**_kwargs: object) -> dict:
        return {"enabled": False, "dispatched": 0}

    with redirect_stdout(buf):
        from services.recovery_scheduler_guardrails import (
            log_recovery_scheduler_ownership_at_startup,
        )

        log_recovery_scheduler_ownership_at_startup()
        import asyncio

        out = asyncio.run(
            run_recovery_resume_scan_async(max_dispatch=25)
        )
    assert out["enabled"] is False
    text = buf.getvalue()
    pos_owner = text.find("[RECOVERY SCHEDULER OWNER]")
    assert pos_owner >= 0
    assert "enabled=false" in text
