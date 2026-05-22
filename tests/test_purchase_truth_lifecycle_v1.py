# -*- coding: utf-8 -*-
"""Purchase Truth v1 — evidence-based lifecycle closure."""
from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from services.purchase_truth import (
    extract_purchase_truth_evidence,
    ingest_purchase_truth_payload,
)
from services.purchase_lifecycle_closure import (
    is_purchase_lifecycle_closed,
    reset_purchase_lifecycle_closure_for_tests as reset_closure,
)


def _reset() -> None:
    reset_closure()
    from tests.test_recovery_isolation import _reset_recovery_memory

    _reset_recovery_memory()
    main._session_recovery_converted.clear()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    yield
    _reset()


def test_extract_purchase_completed_flag() -> None:
    got = extract_purchase_truth_evidence({"purchase_completed": True})
    assert got == ("purchase_completed", "purchase_completed=true")


def test_extract_order_paid_event() -> None:
    got = extract_purchase_truth_evidence({"event": "order_paid", "session_id": "s1"})
    assert got == ("order_paid", "event=order_paid")


def test_extract_purchase_event_field() -> None:
    got = extract_purchase_truth_evidence(
        {"purchase_event": "checkout_completed", "session_id": "s1"}
    )
    assert got == ("checkout_completed", "event=checkout_completed")


def test_ingest_logs_truth_and_closes_lifecycle() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        key = ingest_purchase_truth_payload(
            {
                "store": "demo",
                "session_id": "s-truth-1",
                "purchase_completed": True,
            }
        )
    assert key == "demo:s-truth-1"
    out = buf.getvalue()
    assert "[PURCHASE TRUTH]" in out
    assert "source=purchase_completed" in out
    assert "verified=true" in out
    assert "[PURCHASE LIFECYCLE CLOSED]" in out
    assert "terminal_state=closed_purchase" in out
    assert "future_recovery_allowed=false" in out
    assert is_purchase_lifecycle_closed("demo:s-truth-1")


def test_api_conversion_purchase_completed_chain() -> None:
    _reset()
    client = TestClient(main.app)
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = client.post(
            "/api/conversion",
            json={
                "store_slug": "demo",
                "session_id": "s-api-truth",
                "purchase_completed": True,
            },
        )
    assert r.status_code == 200
    j = r.json()
    assert j.get("ok") is True
    assert j.get("purchase_truth_source") == "purchase_completed"
    out = buf.getvalue()
    assert "[PURCHASE TRUTH]" in out
    assert "[PURCHASE LIFECYCLE CLOSED]" in out


def test_dev_purchase_truth_order_paid() -> None:
    _reset()
    client = TestClient(main.app)
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = client.post(
            "/dev/purchase-truth-test",
            json={
                "store_slug": "demo",
                "session_id": "s-dev-paid",
                "order_paid": True,
            },
        )
    assert r.status_code == 200
    assert r.json().get("purchase_truth_source") == "order_paid"
    out = buf.getvalue()
    assert "[PURCHASE TRUTH]" in out
    assert "source=order_paid" in out


def test_recovery_blocked_after_purchase_truth() -> None:
    ingest_purchase_truth_payload(
        {
            "store": "demo",
            "session_id": "s-block-truth",
            "purchase_completed": True,
        }
    )
    buf = io.StringIO()

    async def _run() -> None:
        with redirect_stdout(buf):
            await main._run_recovery_sequence_after_cart_abandoned_impl(
                "demo:s-block-truth",
                0.0,
                "demo",
                "s-block-truth",
                None,
                recovery_context={"recovery_post_delay_only": True, "reason_tag": "price"},
            )

    with patch.object(main.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(_run())
    out = buf.getvalue()
    assert "[RECOVERY BLOCKED]" in out
    assert "lifecycle_closed_purchase" in out
