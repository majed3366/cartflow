# -*- coding: utf-8 -*-
"""Session truth hardening v1 — durable fallback when in-process cache is cold."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

import main
from extensions import db
from models import CartRecoveryLog, PurchaseTruthRecord
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import reset_purchase_truth_foundation_for_tests
from services.cartflow_session_truth import (
    has_conversion_truth,
    has_sent_truth,
    rehydrate_conversion_cache,
    rehydrate_sent_cache,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests


def _reset_all() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    main._session_recovery_sent.clear()
    main._session_recovery_converted.clear()
    try:
        db.session.query(PurchaseTruthRecord).delete()
        db.session.query(CartRecoveryLog).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset_all()
    db.create_all()
    yield
    _reset_all()


def test_scenario_normal_flow_cache_hit_conversion() -> None:
    rk = "demo:s-cache-conv"
    main._session_recovery_converted[rk] = True
    assert has_conversion_truth(rk, rehydrate_cache=False) is True


def test_scenario_normal_flow_cache_hit_sent() -> None:
    rk = "demo:s-cache-sent"
    main._session_recovery_sent[rk] = True
    assert has_sent_truth(rk, rehydrate_cache=False) is True


def test_scenario_restart_purchase_truth_survives_memory_clear() -> None:
    rk = "demo:s-db-purchase"
    sid = "s-db-purchase"
    now = datetime.now(timezone.utc)
    db.session.add(
        PurchaseTruthRecord(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            purchase_detected=True,
            purchase_time=now,
            purchase_source="test",
        )
    )
    db.session.commit()
    assert main._session_recovery_converted.get(rk) is None
    assert has_conversion_truth(rk) is True
    assert main._session_recovery_converted.get(rk) is True
    assert main._is_user_converted(rk) is True


def test_scenario_memory_cleared_sent_log_blocks() -> None:
    rk = "demo:s-db-sent"
    sid = "s-db-sent"
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id="cart-1",
            status="mock_sent",
            step=1,
            message="test",
        )
    )
    db.session.commit()
    assert main._session_recovery_sent.get(rk) is None
    assert has_sent_truth(rk, session_id=sid, cart_id="cart-1") is True
    assert main._session_recovery_sent.get(rk) is True


def test_scenario_multi_worker_stopped_converted_fallback() -> None:
    rk = "demo:s-stopped-conv"
    sid = "s-stopped-conv"
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id="c1",
            status="stopped_converted",
            step=2,
            message="stopped",
        )
    )
    db.session.commit()
    assert has_conversion_truth(rk, session_id=sid) is True


def test_is_user_converted_delegates_to_helper() -> None:
    rk = "demo:s-delegate"
    with patch(
        "services.cartflow_session_truth.has_conversion_truth",
        return_value=True,
    ) as mocked:
        assert main._is_user_converted(rk) is True
    mocked.assert_called_once_with(rk)


def test_rehydrate_helpers_populate_cache() -> None:
    rk = "demo:s-rehydrate"
    rehydrate_conversion_cache(rk)
    rehydrate_sent_cache(rk)
    assert main._session_recovery_converted.get(rk) is True
    assert main._session_recovery_sent.get(rk) is True
