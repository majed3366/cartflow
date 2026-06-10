# -*- coding: utf-8 -*-
"""Product Data Health v1 — read-only readiness layer tests."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import (
    AbandonedCart,
    CartLineSnapshot,
    CartRecoveryReason,
    ProductCatalogEntry,
    ProductHesitationMapping,
    ProductPurchaseMapping,
    PurchaseTruthRecord,
    Store,
)
from services.product_data.product_data_health_v1 import build_product_data_health_report
from services.product_data.product_data_types_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    READINESS_LIMITED,
    READINESS_PARTIAL,
    READINESS_READY,
    ProductDataHealthThresholds,
    classify_confidence,
    classify_readiness,
)
from services.product_data.product_identity_coverage_v1 import IDENTITY_STATUS_FAILING

_ROOT = Path(__file__).resolve().parent.parent
_STORE_SLUG = "pd-health-test"
_NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


def _reset_db() -> None:
    for model in (
        CartLineSnapshot,
        ProductHesitationMapping,
        ProductPurchaseMapping,
        ProductCatalogEntry,
        CartRecoveryReason,
        PurchaseTruthRecord,
        AbandonedCart,
        Store,
    ):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_db()
    db.create_all()
    yield
    _reset_db()


def _ensure_store(*, slug: str = _STORE_SLUG, catalog: bool = False) -> Store:
    catalog_json = None
    if catalog:
        catalog_json = json.dumps(
            {
                "products": [
                    {"id": "p1", "name": "منتج تجريبي", "price": 100, "category": "اختبار"}
                ]
            },
            ensure_ascii=False,
        )
    row = Store(
        zid_store_id=slug,
        access_token="t",
        is_active=True,
        cf_product_catalog_json=catalog_json,
    )
    db.session.add(row)
    db.session.commit()
    return row


def _cart(
    store: Store,
    *,
    zid_id: str,
    payload: dict,
    days_ago: int = 1,
    recovery_session_id: str | None = None,
) -> AbandonedCart:
    seen = _NOW - timedelta(days=days_ago)
    ac = AbandonedCart(
        zid_cart_id=zid_id,
        store_id=store.id,
        cart_value=100.0,
        status="abandoned",
        first_seen_at=seen.replace(tzinfo=None),
        last_seen_at=seen.replace(tzinfo=None),
        recovery_session_id=recovery_session_id,
    )
    AbandonedCart.set_raw(ac, payload)
    db.session.add(ac)
    db.session.commit()
    return ac


def _snapshot(
    *,
    slug: str,
    session_id: str,
    cart_id: str,
    days_ago: int = 1,
) -> CartLineSnapshot:
    captured = (_NOW - timedelta(days=days_ago)).replace(tzinfo=None)
    row = CartLineSnapshot(
        store_slug=slug,
        session_id=session_id,
        cart_id=cart_id,
        product_id="p1",
        variant_id="v1",
        name="Snap Product",
        unit_price=10.0,
        quantity=1,
        captured_at=captured,
        capture_source="cart_state_sync",
        capture_confidence=CONFIDENCE_HIGH,
        content_hash=f"hash-{session_id}-{cart_id}",
    )
    db.session.add(row)
    db.session.commit()
    return row


def test_classify_readiness_and_confidence_thresholds() -> None:
    th = ProductDataHealthThresholds()
    assert classify_readiness(0.85, thresholds=th) == READINESS_READY
    assert classify_readiness(0.55, thresholds=th) == READINESS_PARTIAL
    assert classify_readiness(0.20, thresholds=th) == READINESS_LIMITED
    assert classify_confidence(0.85, 0.70, thresholds=th) == CONFIDENCE_HIGH
    assert classify_confidence(0.50, 0.10, thresholds=th) == CONFIDENCE_MEDIUM
    assert classify_confidence(0.10, 0.05, thresholds=th) == CONFIDENCE_LOW


def test_empty_store_limited_readiness() -> None:
    _ensure_store()
    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.ok is True
    assert report.readiness == READINESS_LIMITED
    assert report.coverage == 0.0
    assert report.confidence == CONFIDENCE_LOW
    assert report.catalog_available is False
    assert report.cart_sample_size == 0


def test_store_without_catalog_sparse_carts_partial() -> None:
    store = _ensure_store(catalog=False)
    _cart(store, zid_id="sparse-1", payload={"cart_total": 50, "items_count": 1})
    _cart(store, zid_id="sparse-2", payload={"cart_total": 80, "items_count": 2})
    _cart(
        store,
        zid_id="named-1",
        payload={"cart": [{"name": "قميص", "price": 120}]},
    )
    _cart(
        store,
        zid_id="named-2",
        payload={"cart": [{"name": "حذاء", "price": 200}]},
    )

    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.catalog_available is False
    assert report.cart_sample_size == 4
    assert report.coverage == 0.5
    assert report.product_name_coverage == 0.5
    assert report.product_id_coverage == 0.0
    assert report.readiness == READINESS_PARTIAL
    assert report.confidence == CONFIDENCE_MEDIUM


def test_rich_product_data_ready_with_catalog() -> None:
    store = _ensure_store(catalog=True)
    for i in range(4):
        _cart(
            store,
            zid_id=f"rich-{i}",
            payload={
                "line_items": [
                    {
                        "product_id": f"prod-{i}",
                        "variant_id": f"var-{i}",
                        "name": f"منتج {i}",
                        "unit_price": 150.0,
                    }
                ]
            },
        )
    _cart(
        store,
        zid_id="rich-name-only",
        payload={"cart": [{"name": "بدون معرف", "price": 90}]},
    )

    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.catalog_available is True
    assert report.cart_sample_size == 5
    assert report.coverage == 1.0
    assert report.product_name_coverage == 1.0
    assert report.product_id_coverage == 0.8
    assert report.variant_coverage == 0.8
    assert report.readiness == READINESS_READY
    assert report.confidence == CONFIDENCE_HIGH


def test_health_module_performs_no_writes() -> None:
    store = _ensure_store()
    _cart(store, zid_id="w1", payload={"cart": [{"name": "x", "price": 1}]})

    with mock.patch.object(db.session, "add", wraps=db.session.add) as add_mock:
        with mock.patch.object(db.session, "commit", wraps=db.session.commit) as commit_mock:
            build_product_data_health_report(
                db.session, _STORE_SLUG, window_days=7, now=_NOW
            )
            assert add_mock.call_count == 0
            assert commit_mock.call_count == 0


def test_api_unauthorized_without_auth() -> None:
    client = TestClient(main.app)
    r = client.get("/api/product-data/health")
    assert r.status_code == 401


def test_api_route_registered_and_no_writes_in_route() -> None:
    paths = {getattr(r, "path", "") for r in main.app.routes}
    assert "/api/product-data/health" in paths

    route_src = (_ROOT / "routes" / "product_data.py").read_text(encoding="utf-8")
    assert "build_product_data_health_report" in route_src
    assert "db.session.add" not in route_src
    assert "db.session.commit" not in route_src

    main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
    assert "product_data_router" in main_src
    assert "build_product_data_health_report" not in main_src
    assert "product_data_health_v1" not in main_src


def test_api_authenticated_sample_response_shape() -> None:
    store = _ensure_store(catalog=True)
    _cart(
        store,
        zid_id="api-1",
        payload={"line_items": [{"product_id": "p1", "name": "Test", "unit_price": 10}]},
    )

    client = TestClient(main.app)
    with mock.patch(
        "services.merchant_test_widget_store_v1.merchant_authenticated_store_slug",
        return_value=_STORE_SLUG,
    ):
        r = client.get("/api/product-data/health")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["store_slug"] == _STORE_SLUG
    assert body["readiness"] == READINESS_READY
    assert body["coverage"] == 1.0
    assert body["product_name_coverage"] == 1.0
    assert body["product_id_coverage"] == 1.0
    assert body["catalog_available"] is True
    assert body["confidence"] == CONFIDENCE_HIGH
    for key in (
        "readiness",
        "coverage",
        "product_name_coverage",
        "product_id_coverage",
        "variant_coverage",
        "catalog_available",
        "confidence",
    ):
        assert key in body


def test_payload_ready_foundation_limited_divergence() -> None:
    store = _ensure_store(catalog=True)
    sid = "sess-payload-ready"
    _cart(
        store,
        zid_id="foundation-gap-1",
        recovery_session_id=sid,
        payload={
            "line_items": [
                {"product_id": "p1", "variant_id": "v1", "name": "Test", "unit_price": 10}
            ]
        },
    )

    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.readiness == READINESS_READY
    assert report.coverage == 1.0
    assert report.foundation is not None
    assert report.foundation.readiness == READINESS_LIMITED
    assert report.foundation.snapshot_coverage == 0.0
    assert report.foundation.snapshot_rows == 0


def test_identity_failing_when_payload_has_lines_without_snapshots() -> None:
    store = _ensure_store()
    _cart(
        store,
        zid_id="identity-fail-1",
        recovery_session_id="sess-fail-1",
        payload={
            "data": {
                "lines": [{"product_id": "p1", "name": "Widget Line", "unit_price": 5}]
            }
        },
    )

    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.identity_coverage is not None
    assert report.identity_coverage.carts_with_payload_lines == 1
    assert report.identity_coverage.carts_with_foundation_snapshots == 0
    assert report.identity_coverage.identity_capture_status == IDENTITY_STATUS_FAILING


def test_identity_ok_when_snapshots_present() -> None:
    store = _ensure_store()
    sid = "sess-identity-ok"
    cid = "cart-identity-ok"
    _cart(
        store,
        zid_id=cid,
        recovery_session_id=sid,
        payload={
            "line_items": [{"product_id": "p1", "name": "Test", "unit_price": 10}]
        },
    )
    _snapshot(slug=_STORE_SLUG, session_id=sid, cart_id=cid)

    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    assert report.identity_coverage is not None
    assert report.identity_coverage.carts_with_lines == 1
    assert report.identity_coverage.carts_without_lines == 0
    assert report.identity_coverage.lines_capture_rate == 1.0
    assert report.identity_coverage.identity_capture_status == "ok"


def test_no_activity_identity_status_when_no_carts() -> None:
    _ensure_store()
    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    body = report.to_dict()
    assert body["identity_coverage"]["identity_capture_status"] == "no_activity"
    assert body["identity_coverage"]["cart_sample_size"] == 0


def test_to_dict_additive_blocks_preserve_legacy_fields() -> None:
    store = _ensure_store()
    _cart(
        store,
        zid_id="dict-1",
        payload={"cart": [{"name": "x", "price": 1}]},
    )
    report = build_product_data_health_report(
        db.session, _STORE_SLUG, window_days=7, now=_NOW
    )
    body = report.to_dict()

    assert body["readiness"] == body["payload_health"]["readiness"]
    assert body["coverage"] == body["payload_health"]["coverage"]
    assert "foundation_health" in body
    assert "snapshot_coverage" in body["foundation_health"]
    assert "hesitation_mapping_coverage" in body["foundation_health"]
    assert "purchase_mapping_coverage" in body["foundation_health"]
    assert "identity_coverage" in body
    assert "carts_with_lines" in body["identity_coverage"]
    assert "lines_capture_rate" in body["identity_coverage"]


def test_api_includes_foundation_and_identity_blocks() -> None:
    store = _ensure_store(catalog=True)
    _cart(
        store,
        zid_id="api-ext-1",
        payload={"line_items": [{"product_id": "p1", "name": "Test", "unit_price": 10}]},
    )

    client = TestClient(main.app)
    with mock.patch(
        "services.merchant_test_widget_store_v1.merchant_authenticated_store_slug",
        return_value=_STORE_SLUG,
    ):
        r = client.get("/api/product-data/health")

    assert r.status_code == 200, r.text
    body = r.json()
    assert "payload_health" in body
    assert "foundation_health" in body
    assert "identity_coverage" in body
    assert body["foundation_health"]["readiness"] == READINESS_LIMITED
    assert body["identity_coverage"]["identity_capture_status"] == IDENTITY_STATUS_FAILING
