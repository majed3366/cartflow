# -*- coding: utf-8 -*-
"""
Purchase Truth Step 3 — inbound WhatsApp purchase reply → durable truth → no continuation.

Proves full chain:
  webhook reply → reply intent PURCHASE → ingest_purchase_truth_from_reply_claim
  → PurchaseTruthRecord + lifecycle closure → Message #2 / queue blocked (DB truth).
"""
from __future__ import annotations

import asyncio
import io
import os
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import main
from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryLog,
    LifecycleClosureRecord,
    PurchaseTruthRecord,
    RecoverySchedule,
    Store,
)
from schema_lifecycle_closure import reset_lifecycle_closure_schema_guard_for_tests
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    has_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.lifecycle_closure_records_v1 import (
    CLOSURE_PURCHASE_COMPLETED,
    get_durable_closure,
    reset_lifecycle_closure_records_for_tests,
)
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.recovery_restart_survival import (
    STATUS_CANCELLED,
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
)
from services.recovery_session_phone import recovery_phone_memory_clear
from services import whatsapp_queue
from services.reply_intent_handling import run_inbound_whatsapp_reply_intent_hook
from services.whatsapp_queue import enqueue_recovery_and_wait, start_whatsapp_queue_worker


def _clear_memory_caches_only() -> None:
    """Clear in-memory conversion/sent flags; durable DB purchase truth remains."""
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
    reset_lifecycle_closure_schema_guard_for_tests()
    reset_lifecycle_closure_records_for_tests()
    _clear_memory_caches_only()
    db.create_all()
    for model in (
        RecoverySchedule,
        PurchaseTruthRecord,
        LifecycleClosureRecord,
        CartRecoveryLog,
        AbandonedCart,
    ):
        db.session.query(model).delete()
    for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
        db.session.delete(row)
    db.session.commit()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    os.environ["CARTFLOW_CONTINUATION_AUTO_REPLY"] = "0"
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


@pytest.fixture(autouse=True)
def _avoid_heavy_store_identity_backfill() -> None:
    """Test-only: skip slow identity backfill on shared dev DB (hook path stays real)."""
    with patch(
        "services.store_identity_v1.backfill_store_identity_aliases_from_stores",
        return_value=0,
    ):
        with patch(
            "services.store_identity_v1.sync_connected_platform_identities",
            return_value=None,
        ):
            yield


@pytest.fixture(autouse=True)
def _teardown() -> None:
    yield
    _reset_db_state()
    db.session.rollback()


@pytest.mark.parametrize("reply_body", ["تم الطلب", "اشتريت", "خلاص طلبت"])
def test_inbound_purchase_reply_creates_truth_and_blocks_continuation(
    reply_body: str,
) -> None:
    sid = f"s-inbound-{uuid.uuid4().hex[:6]}"
    cid = f"c-inbound-{uuid.uuid4().hex[:6]}"
    phone = "966501112244"
    rk = f"demo:{sid}"
    now = datetime.now(timezone.utc)

    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    assert st is not None

    db.session.add(
        AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone=f"+{phone}",
            cart_value=120.0,
            status="abandoned",
            vip_mode=False,
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
            phone=phone,
            message="recovery message one",
            status="sent_real",
            step=1,
            created_at=now,
            sent_at=now,
        )
    )
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=sid,
        cart_id=cid,
        reason_tag="price",
        abandon_event_phone=f"+{phone}",
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
    row.due_at = now - timedelta(seconds=5)
    db.session.commit()

    assert (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == rk)
        .count()
        == 0
    )
    assert not has_purchase(rk)

    buf = io.StringIO()
    with redirect_stdout(buf):
        run_inbound_whatsapp_reply_intent_hook(
            reply_body,
            f"whatsapp:+{phone}",
        )
    hook_out = buf.getvalue()
    assert "[REPLY INTENT HOOK]" in hook_out
    assert "[REPLY INTENT]" in hook_out
    assert "intent=PURCHASE" in hook_out
    assert "[PURCHASE TRUTH FROM REPLY]" in hook_out
    assert "truth_written=true" in hook_out

    db.session.expire_all()
    truth_row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == rk)
        .first()
    )
    assert truth_row is not None
    assert truth_row.purchase_detected is True
    assert truth_row.purchase_source == "reply_purchase_claim"
    assert "confidence=" in (truth_row.evidence_detail or "")
    assert has_purchase(rk)

    assert is_purchase_lifecycle_closed(rk)
    closure = get_durable_closure(rk)
    assert closure is not None
    assert closure.get("closure_status") == CLOSURE_PURCHASE_COMPLETED

    updated = db.session.get(RecoverySchedule, schedule_id)
    assert updated is not None
    assert updated.status == STATUS_CANCELLED
    assert updated.status != STATUS_SCHEDULED

    _clear_memory_caches_only()
    assert main._session_recovery_converted.get(rk) is None
    assert has_purchase(rk) is True

    statuses: list[str] = []

    def _capture_persist(**kwargs: object) -> None:
        st_status = str(kwargs.get("status") or "").strip()
        if st_status:
            statuses.append(st_status)

    async def _run_queue() -> str:
        await start_whatsapp_queue_worker()
        return await enqueue_recovery_and_wait(
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
            phone=f"+{phone}",
            message="continuation-would-send",
            step=2,
            recovery_key=rk,
            use_real=False,
        )

    with patch.object(whatsapp_queue, "send_whatsapp_mock", return_value={"ok": True}) as mock_send:
        with patch("main._persist_cart_recovery_log", side_effect=_capture_persist):
            queue_result = asyncio.run(_run_queue())

    mock_send.assert_not_called()
    assert queue_result == "stopped"
    assert "stopped_converted" in statuses
