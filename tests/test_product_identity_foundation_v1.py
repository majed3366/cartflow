# -*- coding: utf-8 -*-
"""Product Identity Foundation Implementation V1 — PI-F1…PI-F5 regression."""
from __future__ import annotations

import uuid

import pytest

from extensions import db
from models import AbandonedCart, CartLineSnapshot, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.business_findings_evidence_v1 import (
    build_demo_rich_evidence_bundle_v1,
    build_empty_evidence_bundle_v1,
)
from services.dashboard_snapshot_normal_carts_slim_v1 import (
    slim_normal_carts_row_for_snapshot,
)
from services.home_commercial_intelligence_v1 import apply_home_commercial_intelligence_v1
from services.product_data.product_cart_snapshots_v1 import (
    CAPTURE_SOURCE_CART_STATE_SYNC,
    persist_cart_line_snapshots_from_payload,
)
from services.product_data.product_identity_authenticity_v1 import (
    is_fixture_loaded_from,
    merchant_package_is_authentic_v1,
    sanitize_findings_package_for_merchant_v1,
    text_has_forbidden_product_placeholder,
)
from services.product_data.product_identity_cart_projection_v1 import (
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    attach_product_identity_cart_projection_v1,
    resolve_product_identity_for_cart_v1,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)


def _reset() -> None:
    for model in (CartLineSnapshot, AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _iso() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


def _seed_store(slug: str | None = None) -> tuple[str, Store]:
    slug = slug or f"pi-{uuid.uuid4().hex[:8]}"
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


# --- PI-F1 authenticity ---


def test_f1_engine_default_is_not_demo_fixture() -> None:
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=False, load_db=False)
    loaded = (pkg.get("evidence") or {}).get("loaded_from")
    assert not is_fixture_loaded_from(loaded)
    assert loaded == "no_evidence_source"
    body = str(pkg)
    assert "منتج X" not in body
    assert "Product X" not in body


def test_f1_merchant_sanitize_blocks_fixture_package() -> None:
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
    assert is_fixture_loaded_from((pkg.get("evidence") or {}).get("loaded_from"))
    safe = sanitize_findings_package_for_merchant_v1(pkg, admit_review_fixtures=False)
    assert safe.get("findings") == []
    assert safe["product_identity_authenticity_v1"]["fixture_blocked"] is True
    assert not merchant_package_is_authentic_v1(pkg)


def test_f1_home_ci_rejects_fixture_on_merchant_path() -> None:
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
    home: dict = {
        "store_understanding": {"items": []},
        "attention_today": {"items": []},
        "biggest_opportunity": {"item": None, "items": []},
        "learning_progress": {"items": []},
        "business_health": {},
        "observability": {},
    }
    apply_home_commercial_intelligence_v1(
        home, store_slug="demo", findings_package=pkg, admit_review_fixtures=False
    )
    und = (home.get("store_understanding") or {}).get("items") or []
    blob = str(und)
    assert "منتج X" not in blob
    assert "Product X" not in blob


def test_f1_forbidden_placeholder_detection() -> None:
    assert text_has_forbidden_product_placeholder("منتج X يجذب")
    assert text_has_forbidden_product_placeholder("Product X was added")
    assert not text_has_forbidden_product_placeholder("TrueSound Air — سماعة خفيفة")


def test_f1_empty_evidence_helper() -> None:
    ev = build_empty_evidence_bundle_v1(store_slug="x")
    assert ev.loaded_from == "no_evidence_source"
    assert ev.products == {}
    demo = build_demo_rich_evidence_bundle_v1()
    assert demo.loaded_from == "demo_rich_fixture_v1"


# --- PI-F2 / F3 snapshots ---


def test_f3_items_fallback_persists_snapshot_name() -> None:
    slug, _ = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    pl = {
        "event": "cart_state_sync",
        "store": slug,
        "session_id": sid,
        "cart_id": cid,
        "items": [
            {
                "product_id": "demo_hp_air",
                "name": "TrueSound Air — سماعة خفيفة",
                "price": 119.0,
                "qty": 1,
            }
        ],
    }
    result = persist_cart_line_snapshots_from_payload(
        pl, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
    )
    assert result.inserted == 1
    rows = (
        db.session.query(CartLineSnapshot)
        .filter(CartLineSnapshot.store_slug == slug, CartLineSnapshot.cart_id == cid)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].name == "TrueSound Air — سماعة خفيفة"
    assert rows[0].product_id == "demo_hp_air"


# --- PI-F5 projection ---


def test_f5_cart_projection_resolved_from_snapshot() -> None:
    slug, store = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    persist_cart_line_snapshots_from_payload(
        {
            "event": "cart_state_sync",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "lines": [
                {
                    "product_id": "p1",
                    "name": "Amber Oud — عطر مركز",
                    "unit_price": 289.0,
                    "quantity": 1,
                }
            ],
        },
        capture_source=CAPTURE_SOURCE_CART_STATE_SYNC,
    )
    identity = resolve_product_identity_for_cart_v1(
        store_slug=slug, cart_id=cid, session_id=sid, db_session=db.session
    )
    assert identity["status"] == STATUS_RESOLVED
    assert identity["product_name"] == "Amber Oud — عطر مركز"

    ac = AbandonedCart(
        store_id=int(store.id),
        zid_cart_id=cid,
        status="abandoned",
        cart_value=289.0,
        recovery_session_id=sid,
    )
    db.session.add(ac)
    db.session.commit()
    row: dict = {"store_slug": slug, "zid_cart_id": cid, "session_id": sid}
    attach_product_identity_cart_projection_v1(row, abandoned_cart=ac)
    assert row["merchant_product_identity_status"] == STATUS_RESOLVED
    assert row["merchant_product_name"] == "Amber Oud — عطر مركز"
    slim = slim_normal_carts_row_for_snapshot(row)
    assert slim.get("merchant_product_name") == "Amber Oud — عطر مركز"
    assert "product_identity_v1" in slim


def test_f5_cart_projection_unresolved_honest() -> None:
    identity = resolve_product_identity_for_cart_v1(
        store_slug="missing", cart_id="none", session_id="none", db_session=db.session
    )
    assert identity["status"] == STATUS_UNRESOLVED
    assert identity["unresolved"] is True
    assert "غير متوفر" in identity["display_name_ar"]
    assert not text_has_forbidden_product_placeholder(identity["display_name_ar"])


def test_f5_rejects_key_as_display_name() -> None:
    identity = resolve_product_identity_for_cart_v1(
        store_slug="x",
        cart_id="c1",
        raw_payload={"items": [{"id": "demo_hp_air", "name": "hp_air", "price": 1}]},
        db_session=db.session,
    )
    assert identity["status"] == STATUS_UNRESOLVED


def test_f4_simulator_catalog_display_name_not_key() -> None:
    """PI-F4: catalog display names (no ingress_adapter import — keeps tests light)."""
    from services.store_reality_simulator.behavior_catalog_v1 import catalog_product

    cat = catalog_product("hp_air")
    assert "TrueSound" in str(cat.get("name") or "")
    assert cat.get("name") != "hp_air"
    # Same shape SRS writes into lines[] / items[]
    line = {
        "product_id": cat["id"],
        "sku": cat.get("sku") or "",
        "name": cat["name"],
        "unit_price": cat["price"],
        "quantity": 1,
    }
    slug, _ = _seed_store()
    sid = f"s_{uuid.uuid4().hex[:8]}"
    cid = f"c_{uuid.uuid4().hex[:10]}"
    result = persist_cart_line_snapshots_from_payload(
        {
            "event": "cart_state_sync",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "lines": [line],
        },
        capture_source=CAPTURE_SOURCE_CART_STATE_SYNC,
    )
    assert result.inserted == 1
    row = (
        db.session.query(CartLineSnapshot)
        .filter(CartLineSnapshot.cart_id == cid)
        .first()
    )
    assert row is not None
    assert row.name == cat["name"]
    assert " " in (row.name or "") or "—" in (row.name or "")
