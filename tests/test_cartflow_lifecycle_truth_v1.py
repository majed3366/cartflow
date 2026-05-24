# -*- coding: utf-8 -*-
"""
Lifecycle Truth evaluator v1 — canonical precedence + shadow mismatch detection.

Real-log scenarios documented in ``docs/cartflow_lifecycle_truth_v1_examples.md``
(derived from audit matrices and production grep patterns, not synthetic-only).
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import datetime, timezone

import pytest

from extensions import db
from models import CartRecoveryLog, PurchaseTruthRecord
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_lifecycle_truth import (
    CANONICAL_FAILED,
    CANONICAL_PURCHASED,
    CANONICAL_REPLIED,
    CANONICAL_RETURNED,
    CANONICAL_SENT,
    CANONICAL_VIP_MANUAL,
    CANONICAL_WAITING,
    evaluate_lifecycle_truth,
    legacy_canonical_from_intelligence,
    shadow_compare_at_intelligence_observe,
)
from services.cartflow_purchase_truth import reset_purchase_truth_foundation_for_tests
from services.lifecycle_intelligence import (
    BEHAVIOR_CUSTOMER_REPLIED,
    BEHAVIOR_DELAY_WAITING,
    BEHAVIOR_PURCHASE_COMPLETED,
    BEHAVIOR_RETURNED_TO_SITE,
    decide_lifecycle_recovery,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.purchase_truth import ingest_purchase_truth_payload


def _reset() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    import main

    main._session_recovery_converted.clear()
    try:
        db.session.query(PurchaseTruthRecord).delete()
        db.session.query(CartRecoveryLog).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


# --- Precedence (explicit code order) ---


def test_precedence_purchase_beats_reply_and_return() -> None:
    r = evaluate_lifecycle_truth(
        purchased=True,
        replied=True,
        returned=True,
        log_statuses=["skipped_followup_customer_replied", "returned_to_site"],
    )
    assert r.canonical_state == CANONICAL_PURCHASED
    assert r.terminal is True
    assert "تم الشراء" in r.merchant_message


def test_precedence_reply_beats_return() -> None:
    r = evaluate_lifecycle_truth(
        replied=True,
        returned=True,
        log_statuses=["returned_to_site"],
    )
    assert r.canonical_state == CANONICAL_REPLIED


def test_precedence_return_beats_waiting_and_send() -> None:
    r = evaluate_lifecycle_truth(
        returned=True,
        delay_pending=True,
        log_statuses=["mock_sent", "returned_to_site"],
        sent_ct=1,
    )
    assert r.canonical_state == CANONICAL_RETURNED
    assert "عاد العميل" in r.merchant_message


def test_precedence_waiting_beats_send_when_no_behavioral_tier() -> None:
    r = evaluate_lifecycle_truth(
        delay_pending=True,
        log_statuses=["mock_sent"],
        sent_ct=1,
    )
    assert r.canonical_state == CANONICAL_WAITING


def test_precedence_send_when_only_sent_evidence() -> None:
    r = evaluate_lifecycle_truth(log_statuses=["mock_sent"], latest_log_status="mock_sent")
    assert r.canonical_state == CANONICAL_SENT


# --- Real log scenarios (docs/cartflow_lifecycle_truth_v1_examples.md) ---


def test_scenario_b_mock_sent_then_stopped_converted_is_purchased() -> None:
    """Timeline: mock_sent then stopped_converted → purchased wins."""
    r = evaluate_lifecycle_truth(
        log_statuses=["mock_sent", "stopped_converted"],
        latest_log_status="stopped_converted",
        sent_ct=1,
    )
    assert r.canonical_state == CANONICAL_PURCHASED
    assert r.source == "precedence:purchase"


def test_scenario_c_skipped_followup_customer_replied() -> None:
    r = evaluate_lifecycle_truth(
        log_statuses=["mock_sent", "skipped_followup_customer_replied"],
        latest_log_status="skipped_followup_customer_replied",
    )
    assert r.canonical_state == CANONICAL_REPLIED


def test_scenario_d_returned_to_site_log() -> None:
    r = evaluate_lifecycle_truth(
        returned=True,
        log_statuses=["returned_to_site"],
        latest_log_status="returned_to_site",
    )
    assert r.canonical_state == CANONICAL_RETURNED


def test_scenario_e_delay_gate_waiting() -> None:
    r = evaluate_lifecycle_truth(
        delay_pending=True,
        log_statuses=["skipped_delay_gate"],
        latest_log_status="skipped_delay_gate",
    )
    assert r.canonical_state == CANONICAL_WAITING
    assert r.merchant_message == "بانتظار الوقت المناسب"


def test_scenario_f_whatsapp_failed() -> None:
    r = evaluate_lifecycle_truth(
        latest_log_status="whatsapp_failed",
        log_statuses=["whatsapp_failed"],
    )
    assert r.canonical_state == CANONICAL_FAILED


def test_scenario_g_vip_manual_handling() -> None:
    r = evaluate_lifecycle_truth(
        latest_log_status="vip_manual_handling",
        log_statuses=["vip_manual_handling"],
    )
    assert r.canonical_state == CANONICAL_VIP_MANUAL


def test_scenario_a_purchase_truth_chain_ingest() -> None:
    """Matches test_audit_10 / [PURCHASE DETECTED] → [PURCHASE STOP] log chain."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        key = ingest_purchase_truth_payload(
            {
                "store": "demo",
                "session_id": "s-lt-v1-truth",
                "purchase_completed": True,
            }
        )
    assert key == "demo:s-lt-v1-truth"
    out = buf.getvalue()
    assert "[PURCHASE DETECTED]" in out
    assert "[PURCHASE STOP]" in out

    r = evaluate_lifecycle_truth(recovery_key=key)
    assert r.canonical_state == CANONICAL_PURCHASED


def test_durable_purchase_truth_without_session_memory() -> None:
    rk = "demo:s-lt-db-only"
    now = datetime.now(timezone.utc)
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=rk,
            store_slug="demo",
            session_id="s-lt-db-only",
            purchase_detected=True,
            purchase_time=now,
            purchase_source="test",
        )
    )
    db.session.commit()
    r = evaluate_lifecycle_truth(recovery_key=rk, purchased=False)
    assert r.canonical_state == CANONICAL_PURCHASED


# --- Shadow mode ---


def test_shadow_mismatch_reply_over_return_precedence() -> None:
    intel = decide_lifecycle_recovery(returned=True, replied=True, attempt_count=1)
    assert intel["behavior"] == BEHAVIOR_RETURNED_TO_SITE
    assert legacy_canonical_from_intelligence(intel) == CANONICAL_RETURNED

    buf = io.StringIO()
    with redirect_stdout(buf):
        canonical = shadow_compare_at_intelligence_observe(
            intelligence_result=intel,
            recovery_key="demo:s-shadow",
            returned=True,
            replied=True,
        )
    assert canonical.canonical_state == CANONICAL_REPLIED
    assert "[LIFECYCLE TRUTH MISMATCH]" in buf.getvalue()
    assert "legacy_canonical=returned" in buf.getvalue()
    assert "canonical_canonical=replied" in buf.getvalue()


def test_shadow_no_mismatch_when_intelligence_aligns_purchase() -> None:
    intel = decide_lifecycle_recovery(purchased=True)
    assert intel["behavior"] == BEHAVIOR_PURCHASE_COMPLETED
    buf = io.StringIO()
    with redirect_stdout(buf):
        canonical = shadow_compare_at_intelligence_observe(
            intelligence_result=intel,
            purchased=True,
        )
    assert canonical.canonical_state == CANONICAL_PURCHASED
    assert "[LIFECYCLE TRUTH MISMATCH]" not in buf.getvalue()


def test_shadow_no_mismatch_delay_waiting() -> None:
    intel = decide_lifecycle_recovery(delay_pending=True, reason_tag="price")
    assert intel["behavior"] == BEHAVIOR_DELAY_WAITING
    buf = io.StringIO()
    with redirect_stdout(buf):
        canonical = shadow_compare_at_intelligence_observe(
            intelligence_result=intel,
            delay_pending=True,
        )
    assert canonical.canonical_state == CANONICAL_WAITING
    assert "[LIFECYCLE TRUTH MISMATCH]" not in buf.getvalue()


def test_main_observe_hook_runs_shadow_without_breaking() -> None:
    import main

    buf = io.StringIO()
    with redirect_stdout(buf):
        result = main._observe_lifecycle_intelligence_decision(
            purchased=True,
            session_id="s-hook",
            recovery_key="demo:s-hook",
        )
    assert result["behavior"] == BEHAVIOR_PURCHASE_COMPLETED
    assert "[LIFECYCLE DECISION]" in buf.getvalue()
    assert "[LIFECYCLE TRUTH MISMATCH]" not in buf.getvalue()
