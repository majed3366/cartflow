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
from models import AbandonedCart, Store
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

_ROOT = Path(__file__).resolve().parent.parent
_STORE_SLUG = "pd-health-test"
_NOW = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)


def _reset_db() -> None:
    for model in (AbandonedCart, Store):
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
) -> AbandonedCart:
    seen = _NOW - timedelta(days=days_ago)
    ac = AbandonedCart(
        zid_cart_id=zid_id,
        store_id=store.id,
        cart_value=100.0,
        status="abandoned",
        first_seen_at=seen.replace(tzinfo=None),
        last_seen_at=seen.replace(tzinfo=None),
    )
    AbandonedCart.set_raw(ac, payload)
    db.session.add(ac)
    db.session.commit()
    return ac


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
