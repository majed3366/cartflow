# -*- coding: utf-8 -*-
"""
Purchase Truth Step 2 — verify purchase after first message blocks Message #2.

Proves Message #1 sent + durable PurchaseTruthRecord only (memory cleared) +
Message #2 due → no WhatsApp send; recovery/schedule becomes non-sendable.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import main
from extensions import db
from models import (
    CartRecoveryLog,
    CartRecoveryReason,
    PurchaseTruthRecord,
    RecoverySchedule,
    Store,
)
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    has_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.recovery_restart_survival import (
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_RESUME,
    persist_recovery_schedule_durable,
    resume_one_schedule,
)
from services.recovery_session_phone import recovery_phone_memory_clear
from services import whatsapp_queue
from services.whatsapp_queue import enqueue_recovery_and_wait, start_whatsapp_queue_worker

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


def _seed_step1_sent_and_reason(
    *,
    rk: str,
    sid: str,
    phone: str = "+966501112233",
) -> None:
    db.session.add(
        CartRecoveryReason(
            store_slug="demo",
            session_id=sid,
            reason="price",
            customer_phone=phone,
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id="cart-step2",
            phone=phone,
            message="message-one-sent",
            status="mock_sent",
            step=1,
            created_at=datetime.now(timezone.utc),
            sent_at=datetime.now(timezone.utc),
        )
    )
    db.session.commit()


def _insert_purchase_truth_only(*, rk: str, sid: str) -> None:
    now = datetime.now(timezone.utc)
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            purchase_detected=True,
            purchase_time=now,
            purchase_source="order_paid",
            evidence_detail="step2_db_only_test",
        )
    )
    db.session.commit()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _clear_all_session_caches()
    db.create_all()
    main._ensure_store_widget_schema()
    for model in (
        RecoverySchedule,
        PurchaseTruthRecord,
        CartRecoveryLog,
        CartRecoveryReason,
    ):
        db.session.query(model).delete()
    for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
        db.session.delete(row)
    db.session.commit()
    db.session.add(
        Store(
            zid_store_id="demo",
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
    )
    db.session.commit()
    yield
    _clear_all_session_caches()
    db.session.rollback()


def test_db_purchase_truth_blocks_step2_resume_one_schedule() -> None:
    """Production resume_one_schedule path for due Message #2 after step-1 send."""
    rk = f"demo:sess-step2-resume-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    now = datetime.now(timezone.utc)
    phone = "+966501112233"

    _seed_step1_sent_and_reason(rk=rk, sid=sid, phone=phone)

    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=sid,
        cart_id="cart-step2",
        reason_tag="price",
        abandon_event_phone=phone,
        delay_seconds_scheduled=240.0,
        schedule_timing={
            "effective_delay_seconds": 240.0,
            "source": "reason_templates.messages",
            "stage": 2,
        },
        recovery_context={
            "recovery_key": rk,
            "store_slug": "demo",
            "reason_tag": "price",
            "configured_message_count": 2,
        },
        sequential_attempt_index=2,
    )
    assert row is not None
    schedule_id = int(row.id)
    row.due_at = now - timedelta(seconds=10)
    db.session.commit()

    _insert_purchase_truth_only(rk=rk, sid=sid)
    _clear_all_session_caches()
    assert main._session_recovery_converted.get(rk) is None
    assert has_purchase(rk) is True

    db.session.expire_all()
    schedule = db.session.get(RecoverySchedule, schedule_id)
    assert schedule is not None
    assert schedule.status == STATUS_SCHEDULED
    assert int(schedule.step) == 2

    task_calls: list[object] = []

    def _capture_task(coro):  # noqa: ANN001
        task_calls.append(coro)
        coro.close()
        return None

    with patch("asyncio.create_task", side_effect=_capture_task):
        with patch("main.send_whatsapp") as mock_send:
            result = asyncio.run(resume_one_schedule(schedule, dispatch=True))

    mock_send.assert_not_called()
    assert task_calls == []
    assert result.get("dispatched") is False
    assert result.get("reason") == "purchase_completed"

    db.session.expire_all()
    updated = db.session.get(RecoverySchedule, schedule_id)
    assert updated is not None
    assert updated.status == STATUS_SKIPPED_RESUME
    assert updated.status != STATUS_SCHEDULED
    assert updated.status != STATUS_RUNNING


def test_db_purchase_truth_blocks_step2_whatsapp_queue() -> None:
    """WhatsApp queue worker path for Message #2 — _is_converted reads DB purchase truth."""
    rk = f"demo:sess-step2-wa-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    phone = "+966501112233"

    _seed_step1_sent_and_reason(rk=rk, sid=sid, phone=phone)
    _insert_purchase_truth_only(rk=rk, sid=sid)
    _clear_all_session_caches()
    assert has_purchase(rk) is True
    assert main._session_recovery_converted.get(rk) is None

    statuses: list[str] = []

    def _capture_persist(**kwargs: object) -> None:
        st = str(kwargs.get("status") or "").strip()
        if st:
            statuses.append(st)

    async def _run_queue() -> str:
        await start_whatsapp_queue_worker()
        return await enqueue_recovery_and_wait(
            store_slug="demo",
            session_id=sid,
            cart_id="cart-step2",
            phone=phone,
            message="message-two-would-send",
            step=2,
            recovery_key=rk,
            use_real=False,
        )

    with patch.object(whatsapp_queue, "send_whatsapp_mock", return_value={"ok": True}) as mock_send:
        with patch("main._persist_cart_recovery_log", side_effect=_capture_persist):
            result = asyncio.run(_run_queue())

    mock_send.assert_not_called()
    assert result == "stopped"
    assert "stopped_converted" in statuses
