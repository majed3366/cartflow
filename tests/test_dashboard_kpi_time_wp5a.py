# -*- coding: utf-8 -*-
"""
INV-001 WP-5 — Dashboard KPI Time Authority migration tests.

Supersedes WP-5A legacy open-ended golden checks. Rolling windows are half-open
and shared with Knowledge via ``resolve_knowledge_windows``.
"""
from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import event

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, Store
from services.dashboard_kpi_time_v1 import (
    merchant_kpi_today_projection,
    merchant_month_window_projection,
    merchant_reason_counts_store_window,
    resolve_dashboard_rolling_windows,
    resolve_dashboard_today_window,
)
from services.knowledge_time_authority_v1 import resolve_knowledge_windows

FIXED = datetime(2026, 5, 4, 15, 30, 45, tzinfo=timezone.utc)
_STORE = "kpi-wp5-store"


def test_rolling_equals_knowledge() -> None:
    for days in (7, 30):
        d = resolve_dashboard_rolling_windows(window_days=days, now=FIXED)
        k = resolve_knowledge_windows(window_days=days, now=FIXED)
        assert (d.start, d.end, d.prev_start) == (k.start, k.end, k.prev_start)


def test_today_half_open() -> None:
    start, end, _ = resolve_dashboard_today_window(now=FIXED)
    assert end - start == timedelta(days=1)
    assert start.hour == 0


def test_main_py_has_no_extracted_temporal_arithmetic() -> None:
    main_txt = Path("main.py").read_text(encoding="utf-8")
    assert "def _merchant_ref_today_utc_bounds" not in main_txt
    assert "def _merchant_kpi_today_projection" not in main_txt
    assert "from services.dashboard_kpi_time_v1 import" in main_txt


def test_no_wp3_bypass() -> None:
    src = Path("services/dashboard_kpi_time_v1.py").read_text(encoding="utf-8")
    assert "datetime.now" not in src
    assert "resolve_knowledge_windows" in src


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
    assert merchant_kpi_today_projection(store, now=FIXED)["abandoned_today"] == 0
    assert merchant_month_window_projection(store, days=30, now=FIXED)[
        "abandoned_total"
    ] == 0
    assert merchant_reason_counts_store_window(store, days=7, now=FIXED) == {}


def test_kpi_values_boundary_and_store_filter(kpi_db) -> None:
    store = _store()
    start, end = resolve_dashboard_today_window(now=FIXED)[:2]
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
    db.session.add(
        CartRecoveryReason(
            store_slug=_STORE,
            session_id="s1",
            reason="price_high",
            updated_at=FIXED - timedelta(days=1),
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

    # Future-dated row excluded by half-open end (WP-5; was included under WP-5A open-end)
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

    reasons7 = merchant_reason_counts_store_window(store, days=7, now=FIXED)
    assert reasons7.get("price_high") == 1


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

    merchant_kpi_today_projection(store, now=FIXED)
    c1 = _count_calls(lambda: merchant_kpi_today_projection(store, now=FIXED))
    c2 = _count_calls(lambda: merchant_kpi_today_projection(store, now=FIXED))
    assert c1 == c2
    assert 0 < c1 < 20


def test_service_signatures_accept_optional_now() -> None:
    for fn in (
        merchant_kpi_today_projection,
        merchant_month_window_projection,
        merchant_reason_counts_store_window,
    ):
        assert "now" in inspect.signature(fn).parameters
        assert "context" in inspect.signature(fn).parameters
