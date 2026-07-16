# -*- coding: utf-8 -*-
"""
INV-001 WP-5A — Golden behavior for legacy Dashboard KPI time extraction.

Frozen pre-extraction formulas must match ``services/dashboard_kpi_time_v1``.
No WP-3 Time Authority wiring in this path.
"""
from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import event

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, Store
from services.dashboard_kpi_time_v1 import (
    LEGACY_KPI_TIME_OWNER,
    legacy_rolling_start,
    legacy_today_utc_bounds,
    merchant_kpi_today_projection,
    merchant_month_window_projection,
    merchant_reason_counts_store_window,
)

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
_STORE = "kpi-wp5a-store"


def _frozen_legacy_today_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Exact pre-extraction ``_merchant_ref_today_utc_bounds`` formula."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _frozen_legacy_rolling_start(now: datetime, days: int) -> datetime:
    """Exact pre-extraction rolling start formula."""
    return now - timedelta(days=max(1, int(days)))


@pytest.mark.parametrize(
    "now",
    [
        FIXED,
        datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc),
    ],
)
def test_golden_today_bounds(now: datetime) -> None:
    assert legacy_today_utc_bounds(now=now) == _frozen_legacy_today_bounds(now)


@pytest.mark.parametrize("days", [1, 7, 30, 90])
def test_golden_rolling_7_and_30_bounds(days: int) -> None:
    assert legacy_rolling_start(days=days, now=FIXED) == _frozen_legacy_rolling_start(
        FIXED, days
    )


def test_open_ended_semantics_documented_in_source() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "open-ended" in src.lower() or "open_ended" in src or ">= start" in src
    # Month/reason projections must not add exclusive end filter on rolling windows
    assert "last_seen_at <" not in src.split("def merchant_month_window_projection")[1].split(
        "def merchant_reason_counts_store_window"
    )[0]
    reason_body = src.split("def merchant_reason_counts_store_window")[1].split("def ")[0]
    assert "updated_at <" not in reason_body


def test_no_wp3_filtering_wired() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "from services.time_authority" not in src
    assert "import services.time_authority" not in src
    assert "window_for(" not in src
    assert "resolve_knowledge_windows" not in src
    assert LEGACY_KPI_TIME_OWNER == "INV-001 WP-5"


def test_main_py_has_no_extracted_temporal_arithmetic() -> None:
    main_txt = Path("main.py").read_text(encoding="utf-8")
    assert "def _merchant_ref_today_utc_bounds" not in main_txt
    assert "def _merchant_kpi_today_projection" not in main_txt
    assert "def _merchant_month_window_projection" not in main_txt
    assert "def _merchant_reason_counts_store_window" not in main_txt
    assert "def _merchant_ref_non_vip_scoped_base_query" not in main_txt
    # Call-site wiring only
    assert "merchant_kpi_today_projection" in main_txt
    assert "from services.dashboard_kpi_time_v1 import" in main_txt
    # No new Time Authority selection in summary KPI block
    tree = ast.parse(main_txt)
    # Ensure extracted names are not defined as functions
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_merchant_ref_today_utc_bounds",
            "_merchant_kpi_today_projection",
            "_merchant_month_window_projection",
            "_merchant_reason_counts_store_window",
            "_merchant_ref_non_vip_scoped_base_query",
        }:
            pytest.fail(f"extracted function still defined in main.py: {node.name}")


def _reset() -> None:
    for model in (CartRecoveryReason, CartRecoveryLog, AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture()
def kpi_db():
    _reset()
    db.create_all()
    yield
    _reset()


def _store() -> Store:
    row = Store(zid_store_id=_STORE, access_token="t", is_active=True)
    db.session.add(row)
    db.session.commit()
    db.session.refresh(row)
    return row


def test_empty_data_kpi_outputs(kpi_db) -> None:
    store = _store()
    assert merchant_kpi_today_projection(store, now=FIXED) == {
        "abandoned_today": 0,
        "recovered_today": 0,
        "whatsapp_sent_today": 0,
        "recovered_revenue_today": 0.0,
    }
    assert merchant_month_window_projection(store, days=30, now=FIXED)[
        "abandoned_total"
    ] == 0
    assert merchant_reason_counts_store_window(store, days=7, now=FIXED) == {}


def test_kpi_values_boundary_and_store_filter(kpi_db) -> None:
    store = _store()
    start, end = legacy_today_utc_bounds(now=FIXED)
    # In today window
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="kpi-in",
            status="abandoned",
            first_seen_at=start + timedelta(hours=1),
            last_seen_at=start + timedelta(hours=1),
            vip_mode=False,
            cart_value=10.0,
        )
    )
    # Exactly at end → excluded from today
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="kpi-end",
            status="abandoned",
            first_seen_at=end,
            last_seen_at=end,
            vip_mode=False,
            cart_value=10.0,
        )
    )
    # Other store — must not count
    other = Store(zid_store_id="kpi-wp5a-other", access_token="t", is_active=True)
    db.session.add(other)
    db.session.commit()
    db.session.add(
        AbandonedCart(
            store_id=other.id,
            zid_cart_id="kpi-other",
            status="abandoned",
            first_seen_at=start + timedelta(hours=2),
            last_seen_at=start + timedelta(hours=2),
            vip_mode=False,
            cart_value=99.0,
        )
    )
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE,
            session_id="s1",
            reason="price_high",
            updated_at=FIXED - timedelta(days=1),
        )
    )
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE,
            session_id="s2",
            reason="shipping",
            updated_at=FIXED - timedelta(days=40),
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug=_STORE,
            session_id="s1",
            status="sent_real",
            message="m",
            created_at=start + timedelta(hours=3),
        )
    )
    db.session.commit()

    today = merchant_kpi_today_projection(store, now=FIXED)
    assert today["abandoned_today"] == 1
    assert today["whatsapp_sent_today"] == 1

    month = merchant_month_window_projection(store, days=30, now=FIXED)
    # Open-ended: both today carts with last_seen >= start-30d count (in-window + at end)
    assert month["abandoned_total"] >= 1

    reasons7 = merchant_reason_counts_store_window(store, days=7, now=FIXED)
    assert reasons7.get("price_high") == 1
    assert "shipping" not in reasons7

    reasons30 = merchant_reason_counts_store_window(store, days=30, now=FIXED)
    assert reasons30.get("price_high") == 1
    assert "shipping" not in reasons30


def test_open_ended_includes_future_dated_row(kpi_db) -> None:
    """Legacy rolling windows have no upper bound — future last_seen still counts."""
    store = _store()
    future = FIXED + timedelta(days=10)
    db.session.add(
        AbandonedCart(
            store_id=store.id,
            zid_cart_id="kpi-future",
            status="abandoned",
            first_seen_at=future,
            last_seen_at=future,
            vip_mode=False,
        )
    )
    db.session.commit()
    month = merchant_month_window_projection(store, days=30, now=FIXED)
    assert month["abandoned_total"] == 1


def test_query_count_stable(kpi_db) -> None:
    store = _store()
    engine = db.session.get_bind()

    def _count_calls(fn) -> int:  # noqa: ANN001
        n = {"c": 0}

        def before(*_a, **_k):  # noqa: ANN001
            n["c"] += 1

        event.listen(engine, "before_cursor_execute", before)
        try:
            fn()
        finally:
            event.remove(engine, "before_cursor_execute", before)
        return n["c"]

    # Warm lazy imports / mapper configuration once
    merchant_kpi_today_projection(store, now=FIXED)
    c1 = _count_calls(lambda: merchant_kpi_today_projection(store, now=FIXED))
    c2 = _count_calls(lambda: merchant_kpi_today_projection(store, now=FIXED))
    assert c1 == c2
    assert c1 > 0
    assert c1 < 20


def test_no_scheduler_or_pool_imports() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "scheduler" not in src.lower()
    assert "pool" not in src.lower()
    assert "create_engine" not in src


def test_service_signatures_accept_optional_now() -> None:
    for fn in (
        merchant_kpi_today_projection,
        merchant_month_window_projection,
        merchant_reason_counts_store_window,
    ):
        assert "now" in inspect.signature(fn).parameters
