# -*- coding: utf-8 -*-
"""Purchase Attribution v1 — confidence levels after Purchase Truth closure."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from services.purchase_attribution_v1 import (
    DEFAULT_ATTRIBUTION_WINDOW_HOURS,
    LEVEL_ASSISTED,
    LEVEL_CONFIRMED,
    LEVEL_LIKELY,
    LEVEL_NOT_ATTRIBUTED,
    LEVEL_ORGANIC,
    AttributionInputs,
    compute_attribution_decision,
)
from services.purchase_lifecycle_closure import (
    reset_purchase_lifecycle_closure_for_tests as reset_closure,
)
from services.purchase_truth import ingest_purchase_truth_payload


def _utc(y: int, m: int, d: int, h: int = 0) -> datetime:
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def _inp(**kwargs: object) -> AttributionInputs:
    base: dict[str, object] = {
        "recovery_key": "demo:s1",
        "store_slug": "demo",
        "session_id": "s1",
        "cart_id": "c1",
        "attribution_window_hours": DEFAULT_ATTRIBUTION_WINDOW_HOURS,
        "purchase_completed_at": _utc(2026, 5, 20, 12),
    }
    base.update(kwargs)
    return AttributionInputs(**base)  # type: ignore[arg-type]


def test_confirmed_recovery_reply_after_send() -> None:
    sent = _utc(2026, 5, 19, 10)
    purchase = sent + timedelta(hours=2)
    d = compute_attribution_decision(
        _inp(
            recovery_sent_at=sent,
            purchase_completed_at=purchase,
            recovery_sent=True,
            customer_replied=True,
        )
    )
    assert d.attribution_level == LEVEL_CONFIRMED
    assert d.confidence == "high"
    assert "reply" in d.reason
    assert d.purchase_after_recovery is True


def test_likely_recovery_within_72h_no_engagement() -> None:
    sent = _utc(2026, 5, 18, 10)
    purchase = sent + timedelta(hours=24)
    d = compute_attribution_decision(
        _inp(
            recovery_sent_at=sent,
            purchase_completed_at=purchase,
            recovery_sent=True,
        )
    )
    assert d.attribution_level == LEVEL_LIKELY
    assert d.confidence == "medium"
    assert "72" in d.reason or "purchase_within" in d.reason


def test_assisted_recovery_widget_reason_only() -> None:
    d = compute_attribution_decision(
        _inp(
            reason_captured=True,
            reason_tag="price",
            recovery_sent=False,
            recovery_sent_at=None,
        )
    )
    assert d.attribution_level == LEVEL_ASSISTED
    assert d.confidence == "low"


def test_organic_or_unknown_no_evidence() -> None:
    d = compute_attribution_decision(
        _inp(
            recovery_sent=False,
            recovery_sent_at=None,
            reason_captured=False,
        )
    )
    assert d.attribution_level == LEVEL_ORGANIC
    assert d.reason == "no_recovery_evidence"


def test_not_attributed_purchase_before_recovery() -> None:
    sent = _utc(2026, 5, 20, 10)
    purchase = _utc(2026, 5, 19, 10)
    d = compute_attribution_decision(
        _inp(
            recovery_sent_at=sent,
            purchase_completed_at=purchase,
            recovery_sent=True,
        )
    )
    assert d.attribution_level == LEVEL_NOT_ATTRIBUTED
    assert d.reason == "purchase_before_recovery"
    assert d.purchase_after_recovery is False


def test_not_attributed_outside_window() -> None:
    sent = _utc(2026, 5, 1, 10)
    purchase = sent + timedelta(hours=100)
    d = compute_attribution_decision(
        _inp(
            recovery_sent_at=sent,
            purchase_completed_at=purchase,
            recovery_sent=True,
        )
    )
    assert d.attribution_level == LEVEL_NOT_ATTRIBUTED
    assert d.reason == "outside_attribution_window"


def test_attribution_failure_does_not_block_purchase_closure() -> None:
    reset_closure()
    import main

    main._session_recovery_converted.clear()
    buf = io.StringIO()
    with patch(
        "services.purchase_attribution_v1.run_purchase_attribution_after_truth_closure",
        side_effect=RuntimeError("attribution boom"),
    ):
        with redirect_stdout(buf):
            key = ingest_purchase_truth_payload(
                {
                    "store": "demo",
                    "session_id": "s-attrib-fail",
                    "order_paid": True,
                }
            )
    assert key == "demo:s-attrib-fail"
    out = buf.getvalue()
    assert "[PURCHASE LIFECYCLE CLOSED]" in out


def test_ingest_logs_attribution_decision_when_gather_succeeds() -> None:
    reset_closure()
    import main

    main._session_recovery_converted.clear()
    sent = datetime.now(timezone.utc) - timedelta(hours=1)
    purchase = datetime.now(timezone.utc)
    fake_inputs = _inp(
        recovery_sent_at=sent,
        purchase_completed_at=purchase,
        recovery_sent=True,
        customer_replied=True,
    )
    buf = io.StringIO()
    with patch(
        "services.purchase_attribution_v1.gather_attribution_inputs",
        return_value=fake_inputs,
    ):
        with redirect_stdout(buf):
            ingest_purchase_truth_payload(
                {
                    "store": "demo",
                    "session_id": "s-attrib-ok",
                    "purchase_completed": True,
                }
            )
    assert "[ATTRIBUTION DECISION]" in buf.getvalue()
    assert "confirmed_recovery" in buf.getvalue()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
