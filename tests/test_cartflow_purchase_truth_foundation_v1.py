# -*- coding: utf-8 -*-
"""Purchase Truth foundation v1 — durable evidence, stop precedence, persistence."""
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

import main
from extensions import db
from models import PurchaseTruthRecord, RecoverySchedule
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    has_purchase,
    purchase_context,
    record_purchase,
    reset_purchase_truth_foundation_for_tests,
    stop_if_purchased,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.recovery_restart_survival import STATUS_CANCELLED, STATUS_SCHEDULED


def _reset_all() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    main._session_recovery_converted.clear()
    try:
        db.session.query(PurchaseTruthRecord).delete()
        db.session.query(RecoverySchedule).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
    try:
        from tests.test_recovery_isolation import _reset_recovery_memory

        _reset_recovery_memory()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset_all()
    db.create_all()
    yield
    _reset_all()


def test_scenario_no_purchase_recovery_not_stopped_by_truth() -> None:
    rk = "demo:s-no-purchase"
    assert not has_purchase(rk)
    assert stop_if_purchased(rk, session_id="s-no-purchase") is False

    buf = io.StringIO()

    async def _run() -> None:
        with redirect_stdout(buf):
            await main._run_recovery_sequence_after_cart_abandoned_impl(
                rk,
                0.0,
                "demo",
                "s-no-purchase",
                None,
                recovery_context={"recovery_post_delay_only": True, "reason_tag": "price"},
            )

    with patch.object(main.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(_run())
    out = buf.getvalue()
    assert "[PURCHASE STOP]" not in out


def test_scenario_purchase_stops_future_recovery() -> None:
    rk = "demo:s-purchase-stop"
    buf = io.StringIO()
    with redirect_stdout(buf):
        ok = record_purchase(
            recovery_key=rk,
            purchase_source="order_paid",
            store_slug="demo",
            session_id="s-purchase-stop",
            order_id="ord-1",
            evidence_detail="event=order_paid",
        )
    assert ok
    out = buf.getvalue()
    assert "[PURCHASE DETECTED]" in out
    assert "[PURCHASE SOURCE]" in out
    assert "[PURCHASE STOP]" in out
    assert has_purchase(rk)
    assert stop_if_purchased(rk, session_id="s-purchase-stop") is True

    buf2 = io.StringIO()

    async def _run() -> None:
        with redirect_stdout(buf2):
            await main._run_recovery_sequence_after_cart_abandoned_impl(
                rk,
                0.0,
                "demo",
                "s-purchase-stop",
                None,
                recovery_context={"recovery_post_delay_only": True},
            )

    with patch.object(main.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(_run())
    assert "[PURCHASE STOP]" in buf2.getvalue()


def test_scenario_purchase_during_delay_cancels_schedule() -> None:
    rk = "demo:s-delay-cancel"
    now = datetime.now(timezone.utc)
    row = RecoverySchedule(
        recovery_key=rk,
        store_slug="demo",
        session_id="s-delay-cancel",
        cart_id=None,
        reason_tag="price",
        scheduled_at=now,
        due_at=now + timedelta(hours=1),
        effective_delay_seconds=3600.0,
        delay_source="test",
        status=STATUS_SCHEDULED,
        step=1,
        multi_slot_index=-1,
    )
    db.session.add(row)
    db.session.commit()
    schedule_id = int(row.id)

    record_purchase(
        recovery_key=rk,
        purchase_source="checkout_completed",
        store_slug="demo",
        session_id="s-delay-cancel",
        evidence_detail="checkout_completed=true",
    )
    db.session.expire_all()
    updated = db.session.get(RecoverySchedule, schedule_id)
    assert updated is not None
    assert updated.status == STATUS_CANCELLED
    assert "purchase" in (updated.last_error or "").lower()


def test_scenario_restart_purchase_truth_persists() -> None:
    rk = "demo:s-persist"
    record_purchase(
        recovery_key=rk,
        purchase_source="purchase_completed",
        store_slug="demo",
        session_id="s-persist",
        customer_phone="+966500000001",
    )
    reset_purchase_truth_foundation_for_tests()
    assert has_purchase(rk)
    ctx = purchase_context(rk)
    assert ctx is not None
    assert ctx.get("purchase_detected") is True
    assert ctx.get("purchase_source") == "purchase_completed"
    assert ctx.get("customer_phone") == "+966500000001"
    row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == rk)
        .first()
    )
    assert row is not None
    assert row.purchase_detected is True


def test_record_purchase_rejects_fake_without_source() -> None:
    assert (
        record_purchase(
            recovery_key="demo:s-fake",
            purchase_source="",
            store_slug="demo",
            session_id="s-fake",
        )
        is False
    )
    assert not has_purchase("demo:s-fake")
