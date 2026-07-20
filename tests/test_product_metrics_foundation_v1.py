# -*- coding: utf-8 -*-
"""Product Metrics Foundation V1 — signal-only deterministic metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from extensions import db
from models import ProductMetricValue, ProductSignalEvent, Store
from schema_product_metric_values_v1 import (
    reset_product_metric_values_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_metrics_flag_v1 import (
    ENV_PRODUCT_METRICS_FOUNDATION_V1,
)
from services.product_data.product_metrics_foundation_v1 import (
    compute_product_metrics_v1,
    materialize_product_metrics_v1,
    verify_metrics_determinism_v1,
)
from services.product_data.product_metrics_types_v1 import (
    METRIC_CART_ADDED_COUNT,
    METRIC_EVIDENCE_LINKED_COUNT,
    WINDOW_ALL,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    FAMILY_PRODUCT_EVIDENCE,
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_EVIDENCE_LINKED,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (ProductMetricValue, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_product_metric_values_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_PRODUCT_METRICS_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"pmf-{uuid.uuid4().hex[:8]}"
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
    signal_type: str,
    signal_family: str,
    identity: str,
    session_id: str,
    dedup: str,
) -> None:
    db.session.add(
        ProductSignalEvent(
            store_slug=store,
            session_id=session_id,
            cart_id=f"cart-{session_id[-6:]}",
            recovery_key=None,
            stable_identity_key=identity,
            identity_tier="C",
            product_id="p1",
            signal_family=signal_family,
            signal_type=signal_type,
            observed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            source="cart_state_sync",
            evidence_ref_type="session",
            evidence_ref_id=session_id,
            dedup_hash=dedup,
        )
    )
    db.session.commit()


def test_compute_counts_from_signals_only() -> None:
    store = _seed_store()
    sid = f"s-{uuid.uuid4().hex[:8]}"
    _add_signal(
        store=store,
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
        identity="c|demo_a",
        session_id=sid,
        dedup=f"d1-{sid}",
    )
    _add_signal(
        store=store,
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
        identity="c|demo_a",
        session_id=sid + "b",
        dedup=f"d2-{sid}",
    )
    _add_signal(
        store=store,
        signal_type=SIGNAL_PRODUCT_EVIDENCE_LINKED,
        signal_family=FAMILY_PRODUCT_EVIDENCE,
        identity="c|demo_a",
        session_id=sid + "c",
        dedup=f"d3-{sid}",
    )
    report = compute_product_metrics_v1(store, window_code=WINDOW_ALL)
    assert report["ok"] is True
    assert report["signal_row_count"] == 3
    assert report["by_metric_key"][METRIC_CART_ADDED_COUNT] == 2
    assert report["by_metric_key"][METRIC_EVIDENCE_LINKED_COUNT] == 1
    assert all(
        m["metric_key"] != "trend" for m in report["store_metrics"]
    )


def test_determinism_two_computes_identical() -> None:
    store = _seed_store()
    sid = f"s-{uuid.uuid4().hex[:8]}"
    _add_signal(
        store=store,
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
        identity="c|demo_b",
        session_id=sid,
        dedup=f"d-{sid}",
    )
    det = verify_metrics_determinism_v1(store)
    assert det["ok"] is True
    assert det["deterministic"] is True
    assert det["fingerprint_a"] == det["fingerprint_b"]
    assert len(det["fingerprint_a"]) == 64


def test_store_isolation() -> None:
    a = _seed_store()
    b = _seed_store()
    sid = f"s-{uuid.uuid4().hex[:8]}"
    _add_signal(
        store=a,
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
        identity="c|only_a",
        session_id=sid,
        dedup=f"da-{sid}",
    )
    ra = compute_product_metrics_v1(a)
    rb = compute_product_metrics_v1(b)
    assert ra["by_metric_key"].get(METRIC_CART_ADDED_COUNT) == 1
    assert rb["signal_row_count"] == 0
    assert METRIC_CART_ADDED_COUNT not in rb["by_metric_key"]


def test_materialize_upsert_idempotent() -> None:
    store = _seed_store()
    sid = f"s-{uuid.uuid4().hex[:8]}"
    _add_signal(
        store=store,
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
        identity="c|demo_m",
        session_id=sid,
        dedup=f"dm-{sid}",
    )
    m1 = materialize_product_metrics_v1(store)
    m2 = materialize_product_metrics_v1(store)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(ProductMetricValue)
        .filter(ProductMetricValue.store_slug == store)
        .count()
    )
    assert n >= 1
    cart_rows = (
        db.session.query(ProductMetricValue)
        .filter(
            ProductMetricValue.store_slug == store,
            ProductMetricValue.metric_key == METRIC_CART_ADDED_COUNT,
        )
        .all()
    )
    assert sum(int(r.value) for r in cart_rows) >= 1


def test_disabled_flag_skips_materialize(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_PRODUCT_METRICS_FOUNDATION_V1, "0")
    out = materialize_product_metrics_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True
