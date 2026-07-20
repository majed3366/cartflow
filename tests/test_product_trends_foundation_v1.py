# -*- coding: utf-8 -*-
"""Product Trends Foundation V1 — metrics-only temporal change."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from extensions import db
from models import ProductSignalEvent, ProductTrendValue, Store
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_product_trend_values_v1 import (
    reset_product_trend_values_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.product_data.product_trends_flag_v1 import (
    ENV_PRODUCT_TRENDS_FOUNDATION_V1,
)
from services.product_data.product_trends_foundation_v1 import (
    compute_product_trends_v1,
    materialize_product_trends_v1,
    verify_trends_determinism_v1,
)
from services.product_data.product_trends_types_v1 import (
    TREND_INCREASING,
    TREND_NEWLY_APPEARED,
    TREND_STABLE,
    TREND_WINDOW_D7,
    classify_trend_direction,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (ProductTrendValue, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_product_trend_values_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_PRODUCT_TRENDS_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"ptf-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    return slug


def _add_signal(
    *,
    store: str,
    identity: str,
    observed_at: datetime,
    dedup: str,
) -> None:
    db.session.add(
        ProductSignalEvent(
            store_slug=store,
            session_id=f"s-{dedup[-8:]}",
            cart_id=f"c-{dedup[-6:]}",
            recovery_key=None,
            stable_identity_key=identity,
            identity_tier="C",
            product_id="p1",
            signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
            signal_type=SIGNAL_PRODUCT_CART_ADDED,
            observed_at=observed_at,
            source="cart_state_sync",
            evidence_ref_type="session",
            evidence_ref_id=f"s-{dedup[-8:]}",
            dedup_hash=dedup,
        )
    )
    db.session.commit()


def test_classify_directions() -> None:
    assert classify_trend_direction(0, 3) == TREND_NEWLY_APPEARED
    assert classify_trend_direction(2, 0) == "disappeared"
    assert classify_trend_direction(2, 2) == TREND_STABLE
    assert classify_trend_direction(1, 4) == TREND_INCREASING
    assert classify_trend_direction(4, 1) == "decreasing"


def test_newly_appeared_from_metrics_windows() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 12, 0, 0)
    # Current 7d window only (as_of-3d)
    _add_signal(
        store=store,
        identity="c|trend_a",
        observed_at=as_of - timedelta(days=3),
        dedup=f"d-cur-{uuid.uuid4().hex[:8]}",
    )
    report = compute_product_trends_v1(
        store, trend_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert report["ok"] is True
    cart = next(
        t
        for t in report["store_trends"]
        if t["metric_key"] == "cart_added_count"
    )
    assert cart["current_value"] == 1
    assert cart["previous_value"] == 0
    assert cart["trend_direction"] == TREND_NEWLY_APPEARED


def test_increasing_across_windows() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 12, 0, 0)
    # Previous window: as_of-10d (within [as_of-14, as_of-7))
    _add_signal(
        store=store,
        identity="c|trend_b",
        observed_at=as_of - timedelta(days=10),
        dedup=f"d-prev-{uuid.uuid4().hex[:8]}",
    )
    # Current window: two adds
    _add_signal(
        store=store,
        identity="c|trend_b",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-cur1-{uuid.uuid4().hex[:8]}",
    )
    _add_signal(
        store=store,
        identity="c|trend_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-cur2-{uuid.uuid4().hex[:8]}",
    )
    report = compute_product_trends_v1(
        store, trend_window=TREND_WINDOW_D7, as_of=as_of
    )
    cart = next(
        t
        for t in report["store_trends"]
        if t["metric_key"] == "cart_added_count"
    )
    assert cart["previous_value"] == 1
    assert cart["current_value"] == 2
    assert cart["trend_direction"] == TREND_INCREASING


def test_determinism_fixed_as_of() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|trend_c",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-det-{uuid.uuid4().hex[:8]}",
    )
    det = verify_trends_determinism_v1(
        store, trend_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert det["ok"] is True
    assert det["deterministic"] is True
    assert det["fingerprint_a"] == det["fingerprint_b"]


def test_materialize_and_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|trend_d",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-mat-{uuid.uuid4().hex[:8]}",
    )
    m1 = materialize_product_trends_v1(
        store, trend_window=TREND_WINDOW_D7, as_of=as_of
    )
    m2 = materialize_product_trends_v1(
        store, trend_window=TREND_WINDOW_D7, as_of=as_of
    )
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(ProductTrendValue)
        .filter(ProductTrendValue.store_slug == store)
        .count()
    )
    assert n >= 1
    monkeypatch.setenv(ENV_PRODUCT_TRENDS_FOUNDATION_V1, "0")
    disabled = materialize_product_trends_v1(store, as_of=as_of)
    assert disabled["ok"] is False
    assert disabled.get("skipped_disabled") is True


def test_no_forbidden_fields_in_output() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 20, 12, 0, 0)
    report = compute_product_trends_v1(store, as_of=as_of)
    blob = str(report)
    for forbidden in (
        "recommend",
        "ranking",
        "health_score",
        "opportunity",
        "guidance",
    ):
        assert forbidden not in blob.lower()
