# -*- coding: utf-8 -*-
"""
Purchase Truth — DB-only cold restart survival verification.

Proves scheduled recovery does not resume/send when only purchase_truth_records
exists (no in-memory conversion flags, no stopped_converted logs).
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import main
from extensions import db
from models import CartRecoveryLog, PurchaseTruthRecord, RecoverySchedule, Store
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    has_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    STATUS_SKIPPED_RESUME,
    evaluate_resume_safety,
    persist_recovery_schedule_durable,
    resume_one_schedule,
)
from services.recovery_session_phone import recovery_phone_memory_clear


def _clear_all_session_caches() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    recovery_phone_memory_clear()
    with main._recovery_session_lock:
        main._session_recovery_converted.clear()
        main._session_recovery_sent.clear()
        main._session_recovery_started.clear()
        main._session_recovery_returned.clear()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _clear_all_session_caches()
    db.create_all()
    main._ensure_store_widget_schema()
    for model in (RecoverySchedule, PurchaseTruthRecord, CartRecoveryLog):
        db.session.query(model).delete()
    for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
        db.session.delete(row)
    db.session.commit()
    db.session.add(
        Store(
            zid_store_id="demo",
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
    )
    db.session.commit()
    yield
    _clear_all_session_caches()
    db.session.rollback()


def test_db_only_purchase_truth_blocks_evaluate_resume_safety() -> None:
    rk = f"demo:sess-db-restart-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    now = datetime.now(timezone.utc)

    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=sid,
        cart_id="cart-db-restart",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=60.0,
        schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    row.due_at = now - timedelta(seconds=5)
    db.session.commit()

    db.session.add(
        PurchaseTruthRecord(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            purchase_detected=True,
            purchase_time=now,
            purchase_source="order_paid",
            evidence_detail="db_only_restart_test",
        )
    )
    db.session.commit()

    _clear_all_session_caches()
    assert main._session_recovery_converted.get(rk) is None
    assert has_purchase(rk) is True
    assert main._is_user_converted(rk) is True

    db.session.expire_all()
    schedule = db.session.get(RecoverySchedule, int(row.id))
    assert schedule is not None
    assert schedule.status == STATUS_SCHEDULED

    ok, reason = evaluate_resume_safety(schedule, trust_durable_schedule=True)
    assert ok is False
    assert reason == "purchase_completed"


def test_db_only_purchase_truth_blocks_resume_one_schedule_no_dispatch() -> None:
    rk = f"demo:sess-db-resume-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    now = datetime.now(timezone.utc)

    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=sid,
        cart_id="cart-db-resume",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=60.0,
        schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    schedule_id = int(row.id)
    row.due_at = now - timedelta(seconds=5)
    db.session.commit()

    db.session.add(
        PurchaseTruthRecord(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            purchase_detected=True,
            purchase_time=now,
            purchase_source="purchase_completed",
        )
    )
    db.session.commit()
    _clear_all_session_caches()
    assert has_purchase(rk) is True
    assert main._session_recovery_converted.get(rk) is None

    db.session.expire_all()
    schedule = db.session.get(RecoverySchedule, schedule_id)
    assert schedule is not None

    task_calls: list[object] = []

    def _capture_task(coro):  # noqa: ANN001
        task_calls.append(coro)
        coro.close()
        return None

    with patch("asyncio.create_task", side_effect=_capture_task):
        with patch("main.send_whatsapp") as mock_send:
            result = asyncio.run(resume_one_schedule(schedule, dispatch=True))

    assert result.get("dispatched") is False
    assert result.get("reason") == "purchase_completed"
    mock_send.assert_not_called()
    assert task_calls == []

    db.session.expire_all()
    updated = db.session.get(RecoverySchedule, schedule_id)
    assert updated is not None
    assert updated.status == STATUS_SKIPPED_RESUME
    assert updated.status != STATUS_SCHEDULED
