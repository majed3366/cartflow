# -*- coding: utf-8 -*-
"""Cart Line Snapshots v1 — foundation persistence layer tests."""
from __future__ import annotations

import uuid
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import AbandonedCart, CartLineSnapshot, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_cart_snapshots_v1 import (
    CAPTURE_SOURCE_CART_STATE_SYNC,
    _line_content_hash,
    lines_for_cart,
    lines_for_session,
    persist_cart_line_snapshots_from_payload,
    snapshot_count_for_store,
    try_persist_cart_line_snapshots_from_payload,
)
from services.product_data.product_data_types_v1 import CONFIDENCE_HIGH
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory

_SAMPLE_LINES = [
    {
        "product_id": "prod-100",
        "variant_id": "var-10",
        "sku": "SKU-100",
        "name": "Snapshot Product",
        "unit_price": 49.5,
        "quantity": 2,
    }
]


def _reset_tables() -> None:
    for model in (CartLineSnapshot, AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_recovery_memory()
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> tuple[str, Store]:
    slug = slug or f"snap-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    db.session.commit()
    return slug, store


def _payload(*, slug: str, session_id: str, cart_id: str, lines: list) -> dict:
    return {
        "event": "cart_state_sync",
        "store": slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "lines": lines,
    }


def test_persist_inserts_snapshot_row() -> None:
    slug, _ = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    pl = _payload(slug=slug, session_id=sid, cart_id=cid, lines=_SAMPLE_LINES)

    result = persist_cart_line_snapshots_from_payload(
        pl, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
    )
    assert result.inserted == 1
    assert result.skipped_duplicate == 0

    rows = lines_for_cart(slug, cid)
    assert len(rows) == 1
    row = rows[0]
    assert row.store_slug == slug
    assert row.session_id == sid
    assert row.cart_id == cid
    assert row.product_id == "prod-100"
    assert row.variant_id == "var-10"
    assert row.sku == "SKU-100"
    assert row.name == "Snapshot Product"
    assert row.unit_price == 49.5
    assert row.quantity == 2
    assert row.capture_source == CAPTURE_SOURCE_CART_STATE_SYNC
    assert row.capture_confidence == CONFIDENCE_HIGH
    assert row.content_hash == _line_content_hash(_SAMPLE_LINES[0])


def test_duplicate_identical_line_skipped() -> None:
    slug, _ = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    pl = _payload(slug=slug, session_id=sid, cart_id=cid, lines=_SAMPLE_LINES)

    first = persist_cart_line_snapshots_from_payload(
        pl, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
    )
    second = persist_cart_line_snapshots_from_payload(
        pl, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
    )
    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped_duplicate == 1
    assert snapshot_count_for_store(slug) == 1


def test_quantity_change_creates_new_snapshot() -> None:
    slug, _ = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    pl1 = _payload(slug=slug, session_id=sid, cart_id=cid, lines=_SAMPLE_LINES)
    lines_v2 = [dict(_SAMPLE_LINES[0], quantity=3)]
    pl2 = _payload(slug=slug, session_id=sid, cart_id=cid, lines=lines_v2)

    persist_cart_line_snapshots_from_payload(pl1, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC)
    persist_cart_line_snapshots_from_payload(pl2, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC)

    rows = lines_for_session(slug, sid)
    assert len(rows) == 2
    qtys = sorted(r.quantity for r in rows)
    assert qtys == [2, 3]


def test_empty_lines_no_rows() -> None:
    slug, _ = _seed_store()
    pl = _payload(
        slug=slug,
        session_id=f"s_{uuid.uuid4().hex[:8]}",
        cart_id=f"c_{uuid.uuid4().hex[:10]}",
        lines=[],
    )
    result = persist_cart_line_snapshots_from_payload(
        pl, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
    )
    assert result.skipped_empty == 1
    assert snapshot_count_for_store(slug) == 0


def test_try_persist_never_raises_on_failure() -> None:
    slug, _ = _seed_store()
    pl = _payload(
        slug=slug,
        session_id=f"s_{uuid.uuid4().hex[:8]}",
        cart_id=f"c_{uuid.uuid4().hex[:10]}",
        lines=_SAMPLE_LINES,
    )
    with mock.patch(
        "services.product_data.product_cart_snapshots_v1.persist_cart_line_snapshots_from_payload",
        side_effect=RuntimeError("boom"),
    ):
        try_persist_cart_line_snapshots_from_payload(pl, capture_source="cart_state_sync")


def test_cart_state_sync_api_creates_snapshots() -> None:
    _reset_recovery_memory()
    slug, _ = _seed_store()
    client = TestClient(main.app)
    session_id = f"s_api_{uuid.uuid4().hex[:8]}"
    cart_id = f"c_api_{uuid.uuid4().hex[:10]}"
    r = client.post(
        "/api/cart-event",
        json={
            "event": "cart_state_sync",
            "reason": "add",
            "store": slug,
            "session_id": session_id,
            "cart_id": cart_id,
            "cart_total": 99.0,
            "items_count": 1,
            "cart": [],
            "lines": _SAMPLE_LINES,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("cart_state_sync") is True
    rows = lines_for_cart(slug, cart_id)
    assert len(rows) == 1
    assert rows[0].product_id == "prod-100"


def test_widget_product_identity_regression_still_passes() -> None:
    _reset_recovery_memory()
    slug, _ = _seed_store(f"pi-reg-{uuid.uuid4().hex[:6]}")
    client = TestClient(main.app)
    session_id = f"s_pi_{uuid.uuid4().hex[:8]}"
    cart_id = f"c_pi_{uuid.uuid4().hex[:10]}"
    lines = [
        {
            "product_id": "prod-1",
            "variant_id": "var-1",
            "sku": "SKU-1",
            "name": "Test Product",
            "unit_price": 99.0,
            "quantity": 2,
        }
    ]
    r = client.post(
        "/api/cart-event",
        json={
            "event": "cart_state_sync",
            "reason": "add",
            "store": slug,
            "session_id": session_id,
            "cart_id": cart_id,
            "cart_total": 198.0,
            "items_count": 1,
            "cart": [],
            "lines": lines,
        },
    )
    assert r.status_code == 200, r.text
    ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cart_id).first()
    assert ac is not None
    assert snapshot_count_for_store(slug) >= 1
