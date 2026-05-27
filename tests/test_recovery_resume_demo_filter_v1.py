# -*- coding: utf-8 -*-
"""Production startup resume scan — sandbox demo filter."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_IGNORED_DEMO_STARTUP,
    STATUS_SCHEDULED,
    ignore_sandbox_schedules_for_production_startup,
    is_sandbox_recovery_schedule,
    persist_recovery_schedule_durable,
    production_startup_demo_filter_active,
    run_recovery_resume_scan_sync,
)


@pytest.fixture
def _env_prod() -> None:
    old = os.environ.get("ENV")
    os.environ["ENV"] = "production"
    os.environ.pop("CARTFLOW_RESUME_FILTER_DEMO", None)
    yield
    if old is None:
        os.environ.pop("ENV", None)
    else:
        os.environ["ENV"] = old


@pytest.fixture
def _env_dev() -> None:
    old = os.environ.get("ENV")
    os.environ["ENV"] = "development"
    yield
    if old is None:
        os.environ.pop("ENV", None)
    else:
        os.environ["ENV"] = old


@pytest.fixture(autouse=True)
def _db_tables() -> None:
    db.create_all()
    yield
    db.session.rollback()


def _rk(tag: str) -> str:
    return f"demo:filter-{tag}-{uuid.uuid4().hex[:8]}"


def test_filter_active_on_production_env(_env_prod: None) -> None:
    assert production_startup_demo_filter_active() is True
    assert production_startup_demo_filter_active(force=True) is False


def test_filter_inactive_on_development(_env_dev: None) -> None:
    assert production_startup_demo_filter_active() is False


def test_ignores_demo_scheduled_on_production_startup(_env_prod: None) -> None:
    rk = _rk("demo")
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id="sess-demo-filter",
        cart_id="cart-demo-filter",
        reason_tag="price",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=60.0,
        schedule_timing={
            "effective_delay_seconds": 60.0,
            "source": "test",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    row.due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.session.commit()
    assert is_sandbox_recovery_schedule(row)

    out = ignore_sandbox_schedules_for_production_startup(dry_run=False)
    assert out.get("active") is True
    assert int(out.get("ignored") or 0) >= 1

    db.session.expire_all()
    refreshed = db.session.get(RecoverySchedule, int(row.id))
    assert refreshed is not None
    assert refreshed.status == STATUS_IGNORED_DEMO_STARTUP


def test_cartflow3_schedule_not_sandbox(_env_prod: None) -> None:
    rk = f"cartflow3:filter-{uuid.uuid4().hex[:8]}"
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="cartflow3",
        session_id="sess-merchant",
        cart_id="cart-merchant",
        reason_tag="price",
        abandon_event_phone="+966501112234",
        delay_seconds_scheduled=60.0,
        schedule_timing={
            "effective_delay_seconds": 60.0,
            "source": "test",
        },
        recovery_context={"recovery_key": rk, "store_slug": "cartflow3"},
    )
    assert row is not None
    assert not is_sandbox_recovery_schedule(row)

    ignore_sandbox_schedules_for_production_startup(dry_run=False)
    db.session.expire_all()
    refreshed = db.session.get(RecoverySchedule, int(row.id))
    assert refreshed is not None
    assert refreshed.status == STATUS_SCHEDULED


def test_resume_scan_skips_demo_without_force(_env_prod: None) -> None:
    rk = _rk("scan")
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo2",
        session_id="sess-scan",
        cart_id="cart-scan",
        reason_tag="price",
        abandon_event_phone="+966501112235",
        delay_seconds_scheduled=30.0,
        schedule_timing={
            "effective_delay_seconds": 30.0,
            "source": "test",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo2"},
    )
    assert row is not None
    row.due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.session.commit()

    with patch(
        "services.recovery_restart_survival.resume_one_schedule",
        new_callable=AsyncMock,
    ) as mock_resume:
        mock_resume.return_value = {"recovery_key": rk, "dispatched": True}
        scan = run_recovery_resume_scan_sync(max_dispatch=10, dry_run=False)

    assert scan.get("enabled") is True
    assert int(scan.get("demo_startup_filter", {}).get("ignored") or 0) >= 1
    resumed_keys = [
        str(c.args[0].recovery_key or "")
        for c in mock_resume.call_args_list
        if c.args
    ]
    assert rk not in resumed_keys
    db.session.expire_all()
    refreshed = db.session.get(RecoverySchedule, int(row.id))
    assert refreshed is not None
    assert refreshed.status == STATUS_IGNORED_DEMO_STARTUP
