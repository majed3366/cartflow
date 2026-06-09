# -*- coding: utf-8 -*-
"""Hesitation Mapping v1 — Product ↔ Reason foundation tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import (
    CartLineSnapshot,
    CartRecoveryReason,
    ProductCatalogEntry,
    ProductHesitationMapping,
    Store,
)
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_product_catalog_v1 import reset_product_catalog_schema_guard_for_tests
from schema_product_hesitation_mapping_v1 import (
    reset_product_hesitation_mapping_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_hesitation_mapping_v1 import (
    mapping_count_for_store,
    persist_hesitation_mappings,
    products_for_reason,
    reasons_for_product,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (
        ProductHesitationMapping,
        ProductCatalogEntry,
        CartLineSnapshot,
        CartRecoveryReason,
        Store,
    ):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()
    reset_product_catalog_schema_guard_for_tests()
    reset_product_hesitation_mapping_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_recovery_memory()
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"hes-{uuid.uuid4().hex[:8]}"
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
    return slug


def _add_snapshot(
    slug: str,
    session_id: str,
    cart_id: str,
    *,
    product_id: str,
    name: str,
    variant_id: str | None = None,
    price: float = 50.0,
) -> None:
    line = {
        "product_id": product_id,
        "variant_id": variant_id,
        "name": name,
        "unit_price": price,
        "quantity": 1,
    }
    res = resolve_canonical_identity(catalog_input_from_line(line))
    content = f"{product_id}-{variant_id}-{name}-{price}"
    snap = CartLineSnapshot(
        store_slug=slug,
        session_id=session_id,
        cart_id=cart_id,
        product_id=product_id,
        variant_id=variant_id,
        name=name,
        unit_price=price,
        quantity=1,
        captured_at=datetime.now(timezone.utc).replace(tzinfo=None),
        capture_source="cart_state_sync",
        capture_confidence=res.capture_confidence if res else "low",
        content_hash=content.ljust(64, "0")[:64],
    )
    db.session.add(snap)
    db.session.commit()


class TestMappingPersist:
    def test_maps_present_product_to_reason(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        result = persist_hesitation_mappings(
            slug, sid, cart_id=cid, recovery_key="rk1", reason="price"
        )
        assert result.inserted == 1
        assert mapping_count_for_store(slug) == 1

        rows = products_for_reason(slug, "price")
        assert len(rows) == 1
        row = rows[0]
        assert row["stable_identity_key"] == "a|p1|v1"
        assert row["product_id"] == "p1"
        assert row["reason"] == "price"
        assert row["mapping_confidence"] == "high"

    def test_no_snapshots_skips_empty(self) -> None:
        slug = _seed_store()
        result = persist_hesitation_mappings(
            slug, "no-session", reason="shipping"
        )
        assert result.inserted == 0
        assert result.skipped_empty == 1
        assert mapping_count_for_store(slug) == 0

    def test_blank_reason_is_invalid(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, "c1", product_id="p1", name="Widget")
        result = persist_hesitation_mappings(slug, sid, reason="   ")
        assert result.skipped_invalid == 1
        assert mapping_count_for_store(slug) == 0


class TestMultiProductCarts:
    def test_each_product_gets_its_own_mapping(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="pA", variant_id="vA", name="Alpha")
        _add_snapshot(slug, sid, cid, product_id="pB", variant_id="vB", name="Beta")

        result = persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        assert result.inserted == 2
        rows = products_for_reason(slug, "price")
        keys = {r["stable_identity_key"] for r in rows}
        assert keys == {"a|pA|vA", "a|pB|vB"}


class TestDuplicateSafety:
    def test_same_event_not_duplicated(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        first = persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        second = persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        assert first.inserted == 1
        assert second.inserted == 0
        assert second.skipped_duplicate == 1
        assert mapping_count_for_store(slug) == 1

    def test_different_reason_is_new_fact(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        persist_hesitation_mappings(slug, sid, cart_id=cid, reason="shipping")
        assert mapping_count_for_store(slug) == 2
        reasons = {r["reason"] for r in reasons_for_product(slug, "a|p1|v1")}
        assert reasons == {"price", "shipping"}


class TestImmutability:
    def test_existing_rows_never_overwritten(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")
        persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        original = db.session.query(ProductHesitationMapping).one()
        original_id = original.id
        original_captured = original.captured_at

        persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")
        rows = db.session.query(ProductHesitationMapping).all()
        assert len(rows) == 1
        assert rows[0].id == original_id
        assert rows[0].captured_at == original_captured


class TestReadHelpers:
    def test_reasons_for_product_and_products_for_reason(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="pA", variant_id="vA", name="Alpha")
        _add_snapshot(slug, sid, cid, product_id="pB", variant_id="vB", name="Beta")
        persist_hesitation_mappings(slug, sid, cart_id=cid, reason="price")

        assert len(products_for_reason(slug, "price")) == 2
        assert len(reasons_for_product(slug, "a|pA|vA")) == 1
        assert reasons_for_product(slug, "missing-key") == []


class TestReasonRouteIntegration:
    def test_reason_capture_creates_mapping_via_hook(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        client = TestClient(main.app)
        r = client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": slug,
                "session_id": sid,
                "cart_id": cid,
                "reason_tag": "price_high",
            },
        )
        assert r.status_code == 200, r.text
        assert mapping_count_for_store(slug) == 1
        rows = products_for_reason(slug, "price_high")
        assert len(rows) == 1
        assert rows[0]["stable_identity_key"] == "a|p1|v1"
