# -*- coding: utf-8 -*-
"""
Purchase Truth Step 4 — platform/checkout purchase reconciles to active recovery.

Proves checkout/webhook recovery_key mismatch (session drift) + shared cart_id
→ reconcile_purchase_with_active_recovery_carts bridges to canonical CartFlow key
→ schedules cancelled → no later WhatsApp send (DB truth after memory clear).
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
    AbandonedCart,
    CartRecoveryLog,
    PurchaseTruthRecord,
    RecoverySchedule,
    Store,
)
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    has_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.purchase_truth import ingest_purchase_truth_payload
from services.recovery_restart_survival import (
    STATUS_CANCELLED,
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
)
from services.recovery_session_phone import recovery_phone_memory_clear
from services import whatsapp_queue
from services.whatsapp_queue import enqueue_recovery_and_wait, start_whatsapp_queue_worker
from services.zid_webhook_purchase_v2 import build_zid_purchase_truth_payload


def _clear_memory_caches_only() -> None:
    reset_purchase_truth_foundation_for_tests()
    recovery_phone_memory_clear()
    with main._recovery_session_lock:
        main._session_recovery_converted.clear()
        main._session_recovery_sent.clear()
        main._session_recovery_started.clear()
        main._session_recovery_returned.clear()


def _reset_db_state() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    _clear_memory_caches_only()
    db.create_all()
    for model in (
        RecoverySchedule,
        PurchaseTruthRecord,
        CartRecoveryLog,
        AbandonedCart,
    ):
        db.session.query(model).delete()
    for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
        db.session.delete(row)
    db.session.commit()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset_db_state()
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
    _reset_db_state()
    db.session.rollback()


@pytest.fixture(autouse=True)
def _avoid_heavy_store_identity_backfill() -> None:
    with patch(
        "services.store_identity_v1.backfill_store_identity_aliases_from_stores",
        return_value=0,
    ):
        with patch(
            "services.store_identity_v1.sync_connected_platform_identities",
            return_value=None,
        ):
            yield


def test_platform_zid_purchase_reconciles_canonical_recovery_and_blocks_send() -> None:
    """
    Abandon session S1 + cart C1 (canonical demo:S1).
    Zid order.paid arrives with checkout session S2 + same cart C1.
    """
    abandon_sid = f"abandon-{uuid.uuid4().hex[:6]}"
    checkout_sid = f"checkout-{uuid.uuid4().hex[:6]}"
    cart_id = f"cart-shared-{uuid.uuid4().hex[:6]}"
    canonical_rk = f"demo:{abandon_sid}"
    webhook_rk = f"demo:{checkout_sid}"
    phone = "+966501112233"
    now = datetime.now(timezone.utc)

    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    assert st is not None

    db.session.add(
        AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cart_id,
            recovery_session_id=abandon_sid,
            customer_phone=phone,
            cart_value=150.0,
            status="abandoned",
            vip_mode=False,
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=abandon_sid,
            cart_id=cart_id,
            phone=phone,
            message="recovery message one",
            status="sent_real",
            step=1,
            created_at=now,
            sent_at=now,
        )
    )
    row = persist_recovery_schedule_durable(
        recovery_key=canonical_rk,
        store_slug="demo",
        session_id=abandon_sid,
        cart_id=cart_id,
        reason_tag="price",
        abandon_event_phone=phone,
        delay_seconds_scheduled=300.0,
        schedule_timing={
            "effective_delay_seconds": 300.0,
            "source": "reason_templates.messages",
            "stage": 2,
        },
        recovery_context={
            "recovery_key": canonical_rk,
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

    assert (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == canonical_rk)
        .count()
        == 0
    )
    assert not has_purchase(canonical_rk)
    assert not has_purchase(webhook_rk)

    zid_raw = {
        "event": "order.paid",
        "store_slug": "demo",
        "session_id": checkout_sid,
        "cart_id": cart_id,
        "order_id": f"ZID-ORD-{uuid.uuid4().hex[:8]}",
        "customer_phone": phone,
    }
    pt_payload = build_zid_purchase_truth_payload(zid_raw)
    assert pt_payload is not None

    returned_key = ingest_purchase_truth_payload(pt_payload)
    assert returned_key == webhook_rk

    assert has_purchase(webhook_rk)
    assert has_purchase(canonical_rk)
    assert is_purchase_lifecycle_closed(canonical_rk)

    canonical_row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == canonical_rk)
        .first()
    )
    assert canonical_row is not None
    assert canonical_row.purchase_detected is True
    assert "reconcile_from" in (canonical_row.evidence_detail or "")

    db.session.expire_all()
    updated_schedule = db.session.get(RecoverySchedule, schedule_id)
    assert updated_schedule is not None
    assert updated_schedule.status == STATUS_CANCELLED
    assert updated_schedule.status != STATUS_SCHEDULED

    db.session.expire_all()
    ac = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.zid_cart_id == cart_id)
        .first()
    )
    assert ac is not None
    assert str(ac.status or "").strip().lower() == "recovered"

    _clear_memory_caches_only()
    assert main._session_recovery_converted.get(canonical_rk) is None
    assert has_purchase(canonical_rk) is True

    statuses: list[str] = []

    def _capture_persist(**kwargs: object) -> None:
        st_status = str(kwargs.get("status") or "").strip()
        if st_status:
            statuses.append(st_status)

    async def _run_queue() -> str:
        await start_whatsapp_queue_worker()
        return await enqueue_recovery_and_wait(
            store_slug="demo",
            session_id=abandon_sid,
            cart_id=cart_id,
            phone=phone,
            message="platform-reconcile-block-test",
            step=2,
            recovery_key=canonical_rk,
            use_real=False,
        )

    with patch.object(whatsapp_queue, "send_whatsapp_mock", return_value={"ok": True}) as mock_send:
        with patch("main._persist_cart_recovery_log", side_effect=_capture_persist):
            queue_result = asyncio.run(_run_queue())

    mock_send.assert_not_called()
    assert queue_result == "stopped"
    assert "stopped_converted" in statuses
