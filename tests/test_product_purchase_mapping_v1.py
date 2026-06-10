# -*- coding: utf-8 -*-
"""Purchase Mapping v1 — Product ↔ Purchase foundation tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from extensions import db
from models import CartLineSnapshot, ProductPurchaseMapping, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_product_purchase_mapping_v1 import (
    reset_product_purchase_mapping_schema_guard_for_tests,
)
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from schema_store_identity import ensure_store_identity_schema
from services.cartflow_purchase_truth import (
    record_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_purchase_mapping_v1 import (
    persist_purchase_mappings,
    products_for_purchase,
    purchase_mapping_count,
    purchases_for_product,
)
from services.purchase_lifecycle_closure import reset_purchase_lifecycle_closure_for_tests
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    reset_purchase_lifecycle_closure_for_tests()
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    for model in (ProductPurchaseMapping, CartLineSnapshot, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()
    reset_product_purchase_mapping_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_recovery_memory()
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"pur-{uuid.uuid4().hex[:8]}"
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
    quantity: int = 2,
) -> None:
    line = {
        "product_id": product_id,
        "variant_id": variant_id,
        "name": name,
        "unit_price": price,
        "quantity": quantity,
    }
    res = resolve_canonical_identity(catalog_input_from_line(line))
    content = f"{product_id}-{variant_id}-{name}-{price}-{quantity}"
    snap = CartLineSnapshot(
        store_slug=slug,
        session_id=session_id,
        cart_id=cart_id,
        product_id=product_id,
        variant_id=variant_id,
        name=name,
        unit_price=price,
        quantity=quantity,
        captured_at=datetime.now(timezone.utc).replace(tzinfo=None),
        capture_source="cart_state_sync",
        capture_confidence=res.capture_confidence if res else "low",
        content_hash=content.ljust(64, "0")[:64],
    )
    db.session.add(snap)
    db.session.commit()


class TestPurchaseMappingPersist:
    def test_maps_present_product_to_purchase(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        result = persist_purchase_mappings(
            slug,
            sid,
            cart_id=cid,
            recovery_key="rk1",
            order_id="ord-100",
            purchase_source="order_paid",
        )
        assert result.inserted == 1
        assert purchase_mapping_count(slug) == 1

        rows = products_for_purchase(slug, order_id="ord-100")
        assert len(rows) == 1
        row = rows[0]
        assert row["stable_identity_key"] == "a|p1|v1"
        assert row["product_id"] == "p1"
        assert row["quantity"] == 2
        assert row["unit_price"] == 50.0
        assert row["purchase_source"] == "order_paid"

    def test_no_snapshots_skips_empty(self) -> None:
        slug = _seed_store()
        result = persist_purchase_mappings(
            slug, "no-session", purchase_source="order_paid"
        )
        assert result.inserted == 0
        assert result.skipped_empty == 1
        assert purchase_mapping_count(slug) == 0


class TestMultiProductPurchases:
    def test_each_product_gets_its_own_mapping(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="pA", variant_id="vA", name="Alpha")
        _add_snapshot(slug, sid, cid, product_id="pB", variant_id="vB", name="Beta")

        result = persist_purchase_mappings(
            slug,
            sid,
            cart_id=cid,
            order_id="ord-multi",
            purchase_source="checkout_completed",
        )
        assert result.inserted == 2
        rows = products_for_purchase(slug, order_id="ord-multi")
        keys = {r["stable_identity_key"] for r in rows}
        assert keys == {"a|pA|vA", "a|pB|vB"}


class TestDuplicateSafety:
    def test_same_purchase_not_duplicated(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        first = persist_purchase_mappings(
            slug,
            sid,
            cart_id=cid,
            order_id="ord-dup",
            purchase_source="order_paid",
        )
        second = persist_purchase_mappings(
            slug,
            sid,
            cart_id=cid,
            order_id="ord-dup",
            purchase_source="order_paid",
        )
        assert first.inserted == 1
        assert second.inserted == 0
        assert second.skipped_duplicate == 1
        assert purchase_mapping_count(slug) == 1


class TestImmutability:
    def test_existing_rows_never_overwritten(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")
        persist_purchase_mappings(
            slug, sid, cart_id=cid, order_id="ord-1", purchase_source="order_paid"
        )
        original = db.session.query(ProductPurchaseMapping).one()
        original_id = original.id
        original_purchased = original.purchased_at

        persist_purchase_mappings(
            slug, sid, cart_id=cid, order_id="ord-1", purchase_source="order_paid"
        )
        rows = db.session.query(ProductPurchaseMapping).all()
        assert len(rows) == 1
        assert rows[0].id == original_id
        assert rows[0].purchased_at == original_purchased


class TestReadHelpers:
    def test_purchases_for_product_and_products_for_purchase(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        _add_snapshot(slug, sid, cid, product_id="pA", variant_id="vA", name="Alpha")
        persist_purchase_mappings(
            slug, sid, cart_id=cid, order_id="ord-rd", purchase_source="order_paid"
        )
        assert len(products_for_purchase(slug, order_id="ord-rd")) == 1
        assert len(purchases_for_product(slug, "a|pA|vA")) == 1
        assert purchases_for_product(slug, "missing-key") == []


class TestPurchaseTruthIntegration:
    def test_record_purchase_creates_mapping_via_hook(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        cid = f"c_{uuid.uuid4().hex[:8]}"
        rk = f"{slug}:{sid}"
        _add_snapshot(slug, sid, cid, product_id="p1", variant_id="v1", name="Widget")

        ok = record_purchase(
            recovery_key=rk,
            purchase_source="order_paid",
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
            order_id="ord-hook",
        )
        assert ok
        assert purchase_mapping_count(slug) == 1
        rows = products_for_purchase(slug, order_id="ord-hook")
        assert rows[0]["stable_identity_key"] == "a|p1|v1"


class TestFailureIsolation:
    def test_mapping_failure_does_not_block_purchase_truth(self) -> None:
        slug = _seed_store()
        sid = f"s_{uuid.uuid4().hex[:8]}"
        rk = f"{slug}:{sid}"
        with patch(
            "services.product_data.product_purchase_mapping_v1.persist_purchase_mappings",
            side_effect=RuntimeError("mapping boom"),
        ):
            ok = record_purchase(
                recovery_key=rk,
                purchase_source="order_paid",
                store_slug=slug,
                session_id=sid,
                order_id="ord-fail",
            )
        assert ok
