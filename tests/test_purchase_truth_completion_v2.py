# -*- coding: utf-8 -*-
"""Purchase Truth Completion v2 — durable ingest, precedence, dashboard alignment."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import datetime, timezone

import pytest

from extensions import db
from models import LifecycleClosureRecord, PurchaseTruthRecord, RecoverySchedule
from schema_lifecycle_closure import reset_lifecycle_closure_schema_guard_for_tests
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import has_purchase, reset_purchase_truth_foundation_for_tests
from services.lifecycle_closure_records_v1 import (
    CLOSURE_PURCHASE_COMPLETED,
    get_durable_closure,
    reset_lifecycle_closure_records_for_tests,
)
from services.lifecycle_intelligence import (
    BEHAVIOR_CUSTOMER_REPLIED,
    BEHAVIOR_PURCHASE_COMPLETED,
    BEHAVIOR_RETURNED_TO_SITE,
    decide_lifecycle_recovery,
    resolve_lifecycle_behavior,
)
from services.merchant_recovery_lifecycle_truth import build_merchant_recovery_lifecycle_truth
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.purchase_truth import (
    ingest_purchase_truth,
    ingest_purchase_truth_from_reply_claim,
    ingest_purchase_truth_payload,
)
from services.zid_webhook_purchase_v2 import build_zid_purchase_truth_payload


def _reset() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    reset_lifecycle_closure_schema_guard_for_tests()
    reset_lifecycle_closure_records_for_tests()
    import main

    main._session_recovery_converted.clear()
    try:
        db.session.query(LifecycleClosureRecord).delete()
        db.session.query(PurchaseTruthRecord).delete()
        db.session.query(RecoverySchedule).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


class _FakeAc:
    recovery_session_id = "sess-v2"
    zid_cart_id = "cart-v2"
    status = "sent"
    recovered_at = None


def test_scenario_a_purchase_before_send_truth_and_closure() -> None:
    rk = "demo:s-a"
    buf = io.StringIO()
    with redirect_stdout(buf):
        ok = ingest_purchase_truth(
            recovery_key=rk,
            purchase_source="purchase_completed",
            store_slug="demo",
            session_id="s-a",
        )
    assert ok
    assert has_purchase(rk)
    out = buf.getvalue()
    assert "[PURCHASE TRUTH INGESTED]" in out
    assert "truth_written=true" in out
    closure = get_durable_closure(rk)
    assert closure is not None
    assert closure["closure_status"] == CLOSURE_PURCHASE_COMPLETED


def test_scenario_b_purchase_after_send_wins_over_queued() -> None:
    rk = "demo:s-b"
    ingest_purchase_truth(
        recovery_key=rk,
        purchase_source="order_paid",
        store_slug="demo",
        session_id="s-b",
    )
    ac = _FakeAc()
    ac.recovery_session_id = "s-b"
    truth = build_merchant_recovery_lifecycle_truth(
        ac=ac,
        phase_key="pending_send",
        coarse="pending",
        sent_ct=0,
        log_statuses=frozenset(["queued", "sent_real"]),
        behavioral={},
        reason_tag="price",
        has_phone=True,
        latest_log=None,
        store_slug="demo",
    )
    assert truth["purchased"] is True
    assert truth["lifecycle_status"] == "purchased"
    assert "اكتمل الشراء" in (truth["lifecycle_label_ar"] or "")


def test_scenario_c_reply_purchase_claim_low_confidence() -> None:
    rk = "demo:s-c"
    buf = io.StringIO()
    with redirect_stdout(buf):
        ok = ingest_purchase_truth_from_reply_claim(
            recovery_key=rk,
            store_slug="demo",
            session_id="s-c",
            reply_preview="اشتريت",
            confidence="low",
        )
    assert ok
    assert has_purchase(rk)
    out = buf.getvalue()
    assert "[PURCHASE TRUTH FROM REPLY]" in out
    assert "confidence=low" in out
    assert "truth_written=true" in out
    row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == rk)
        .first()
    )
    assert row is not None
    assert row.purchase_source == "reply_purchase_claim"
    assert "confidence=low" in (row.evidence_detail or "")


def test_scenario_d_queued_plus_purchase_dashboard_purchased() -> None:
    rk = "demo:s-d"
    ingest_purchase_truth(
        recovery_key=rk,
        purchase_source="order_paid",
        store_slug="demo",
        session_id="s-d",
    )
    ac = _FakeAc()
    ac.recovery_session_id = "s-d"
    truth = build_merchant_recovery_lifecycle_truth(
        ac=ac,
        phase_key="pending_second_attempt",
        coarse="pending",
        sent_ct=0,
        log_statuses=frozenset(["queued"]),
        behavioral={},
        reason_tag="price",
        has_phone=True,
        store_slug="demo",
    )
    assert truth["purchased"] is True
    assert truth["lifecycle_status"] != "scheduled"


def test_scenario_e_restart_purchase_truth_survives() -> None:
    rk = "demo:s-e"
    ingest_purchase_truth(
        recovery_key=rk,
        purchase_source="user_converted",
        store_slug="demo",
        session_id="s-e",
    )
    reset_purchase_truth_foundation_for_tests()
    assert has_purchase(rk) is True


def test_precedence_reply_beats_return_intelligence() -> None:
    behavior = resolve_lifecycle_behavior(replied=True, returned=True, log_precedence=False)
    assert behavior == BEHAVIOR_CUSTOMER_REPLIED
    buf = io.StringIO()
    with redirect_stdout(buf):
        behavior2 = resolve_lifecycle_behavior(replied=True, returned=True)
    assert behavior2 == BEHAVIOR_CUSTOMER_REPLIED
    assert "[LIFECYCLE PRECEDENCE]" in buf.getvalue()


def test_zid_webhook_payload_builds_ingest() -> None:
    pl = build_zid_purchase_truth_payload(
        {
            "event": "order.paid",
            "store_slug": "demo",
            "session_id": "zid-s1",
            "order_id": "ord-1",
        }
    )
    assert pl is not None
    rk = ingest_purchase_truth_payload(pl)
    assert rk == "demo:zid-s1"
    assert has_purchase(rk)


def test_ingest_payload_canonical_log() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        key = ingest_purchase_truth_payload(
            {
                "store_slug": "demo",
                "session_id": "s-payload",
                "purchase_completed": True,
            }
        )
    assert key == "demo:s-payload"
    assert "[PURCHASE TRUTH INGESTED]" in buf.getvalue()
