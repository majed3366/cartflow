# -*- coding: utf-8 -*-
"""
Lifecycle Truth Completion v1 — audit matrix (read-only).

Verifies decision layer outputs and cross-layer wiring without changing behavior.
See ``docs/audit_lifecycle_truth_completion_v1.md`` for the full report.
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

import pytest

from services.lifecycle_intelligence import (
    BEHAVIOR_CUSTOMER_REPLIED,
    BEHAVIOR_DELAY_WAITING,
    BEHAVIOR_IGNORED,
    BEHAVIOR_PURCHASE_COMPLETED,
    BEHAVIOR_RETURNED_TO_SITE,
    BEHAVIOR_UNKNOWN,
    DECISION_CONTINUE,
    DECISION_FALLBACK,
    DECISION_HANDOFF,
    DECISION_STOP,
    DECISION_WAIT,
    decide_lifecycle_recovery,
)
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests,
)
from services.purchase_truth import extract_purchase_truth_evidence, ingest_purchase_truth_payload
from services.reply_intent_handling import (
    INTENT_PURCHASE,
    INTENT_STOP,
    _ACTION_CLOSE_LIFECYCLE,
    _ACTION_STOP_RECOVERY,
    classify_reply_lifecycle_intent_v1,
    lifecycle_decision_for_reply_intent,
)

_TAM_ALTALIB = "\u062a\u0645 \u0627\u0644\u0637\u0644\u0628"
_LA_UREED = "\u0644\u0627 \u0623\u0631\u064a\u062f"


@pytest.fixture(autouse=True)
def _reset_closure() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    import main
    from tests.test_recovery_isolation import _reset_recovery_memory

    _reset_recovery_memory()
    main._session_recovery_converted.clear()
    yield
    reset_purchase_lifecycle_closure_for_tests()


def _decide(**kwargs: object) -> dict:
    return decide_lifecycle_recovery(**kwargs)  # type: ignore[arg-type]


# --- Lifecycle Intelligence v1 (pure layer) ---


def test_audit_01_returned_to_site() -> None:
    r = _decide(returned=True, attempt_count=1)
    assert r["behavior"] == BEHAVIOR_RETURNED_TO_SITE
    assert r["decision"] == DECISION_STOP
    assert r["action"] == "no_send"


def test_audit_02_purchase_completed_lifecycle_layer() -> None:
    r = _decide(purchased=True, attempt_count=2)
    assert r["behavior"] == BEHAVIOR_PURCHASE_COMPLETED
    assert r["decision"] == DECISION_STOP
    assert r["action"] == "close_lifecycle"


def test_audit_03_customer_replied_handoff() -> None:
    r = _decide(replied=True, attempt_count=1)
    assert r["behavior"] == BEHAVIOR_CUSTOMER_REPLIED
    assert r["decision"] == DECISION_HANDOFF
    assert r["action"] == "handoff_continuation"


def test_audit_04_reply_intent_stop() -> None:
    assert classify_reply_lifecycle_intent_v1(_LA_UREED) == INTENT_STOP
    decision, action = lifecycle_decision_for_reply_intent(INTENT_STOP)
    assert decision == DECISION_STOP
    assert action == _ACTION_STOP_RECOVERY


def test_audit_05_reply_intent_purchase_close() -> None:
    assert classify_reply_lifecycle_intent_v1(_TAM_ALTALIB) == INTENT_PURCHASE
    decision, action = lifecycle_decision_for_reply_intent(INTENT_PURCHASE)
    assert decision == DECISION_STOP
    assert action == _ACTION_CLOSE_LIFECYCLE


def test_audit_06_ignored_continue() -> None:
    r = _decide(ignored=True, attempt_count=1)
    assert r["behavior"] == BEHAVIOR_IGNORED
    assert r["decision"] == DECISION_CONTINUE
    assert r["next_step"] == "attempt_2"
    assert r["action"] == "proceed_recovery"


def test_audit_07_delay_waiting() -> None:
    r = _decide(delay_pending=True, reason_tag="price")
    assert r["behavior"] == BEHAVIOR_DELAY_WAITING
    assert r["decision"] == DECISION_WAIT
    assert r["action"] == "wait_schedule"


def test_audit_08_unknown_fallback() -> None:
    r = _decide(reason_tag="shipping")
    assert r["behavior"] == BEHAVIOR_UNKNOWN
    assert r["decision"] == DECISION_FALLBACK
    assert r["action"] == "reason_then_delay"


def test_audit_09_checkout_started_not_in_lifecycle_intelligence() -> None:
    """checkout_started is widget trigger suppression only — no behavior enum."""
    from services.lifecycle_intelligence import resolve_lifecycle_behavior

    assert resolve_lifecycle_behavior() == BEHAVIOR_UNKNOWN
    assert "checkout_started" not in {
        BEHAVIOR_PURCHASE_COMPLETED,
        BEHAVIOR_RETURNED_TO_SITE,
        BEHAVIOR_CUSTOMER_REPLIED,
        BEHAVIOR_IGNORED,
        BEHAVIOR_DELAY_WAITING,
        BEHAVIOR_UNKNOWN,
    }


def test_audit_10_purchase_truth_chain() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        key = ingest_purchase_truth_payload(
            {
                "store": "demo",
                "session_id": "s-audit-truth",
                "purchase_completed": True,
            }
        )
    assert key == "demo:s-audit-truth"
    out = buf.getvalue()
    assert "[PURCHASE TRUTH]" in out
    assert "verified=true" in out
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "terminal_state=closed_purchase" in out
    assert "future_recovery_allowed=false" in out
    assert is_purchase_lifecycle_closed(key)


def test_audit_purchase_truth_evidence_flags() -> None:
    assert extract_purchase_truth_evidence({"order_paid": True}) == (
        "order_paid",
        "order_paid=true",
    )
    assert extract_purchase_truth_evidence({"event": "checkout_completed"}) == (
        "checkout_completed",
        "event=checkout_completed",
    )
