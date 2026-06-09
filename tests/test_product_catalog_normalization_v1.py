# -*- coding: utf-8 -*-
"""Catalog Normalization v1 — canonical product foundation tests."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import CartLineSnapshot, ProductCatalogEntry, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_product_catalog_v1 import reset_product_catalog_schema_guard_for_tests
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_catalog_types_v1 import (
    CATALOG_SOURCE_CATALOG_JSON,
    CATALOG_SOURCE_PRODUCT_IDENTITY,
    IDENTITY_TIER_A,
    IDENTITY_TIER_B,
    IDENTITY_TIER_C,
    IDENTITY_TIER_E,
    CatalogProductInput,
)
from services.product_data.product_catalog_v1 import (
    catalog_count_for_store,
    catalog_entry_by_identity_key,
    catalog_entries_for_store,
    sync_catalog_from_store_json,
    upsert_catalog_from_lines,
    upsert_catalog_product,
)
from services.product_data.product_data_types_v1 import CONFIDENCE_HIGH, CONFIDENCE_LOW
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (ProductCatalogEntry, CartLineSnapshot, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()
    reset_product_catalog_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db() -> None:
    _reset_recovery_memory()
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None, *, catalog_json: str | None = None) -> str:
    slug = slug or f"cat-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    if catalog_json is not None:
        store.cf_product_catalog_json = catalog_json
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


class TestIdentityPrecedence:
    def test_tier_a_product_id_variant_id(self) -> None:
        product = CatalogProductInput(
            product_id="p1", variant_id="v1", sku="SKU-1", name="Widget"
        )
        res = resolve_canonical_identity(product)
        assert res is not None
        assert res.identity_tier == IDENTITY_TIER_A
        assert res.stable_identity_key == "a|p1|v1"
        assert res.capture_confidence == CONFIDENCE_HIGH

    def test_tier_b_product_id_sku_without_variant(self) -> None:
        product = CatalogProductInput(product_id="p1", sku="SKU-1", name="Widget")
        res = resolve_canonical_identity(product)
        assert res is not None
        assert res.identity_tier == IDENTITY_TIER_B
        assert res.stable_identity_key == "b|p1|sku-1"

    def test_tier_c_product_id_only(self) -> None:
        product = CatalogProductInput(product_id="p1", name="Widget")
        res = resolve_canonical_identity(product)
        assert res is not None
        assert res.identity_tier == IDENTITY_TIER_C
        assert res.stable_identity_key == "c|p1"

    def test_tier_e_name_hash_when_no_ids(self) -> None:
        product = CatalogProductInput(name="TrueSound Pro")
        res = resolve_canonical_identity(product)
        assert res is not None
        assert res.identity_tier == IDENTITY_TIER_E
        assert res.stable_identity_key.startswith("e|")
        assert res.capture_confidence == CONFIDENCE_LOW

    def test_name_hash_not_used_when_product_id_present(self) -> None:
        product = CatalogProductInput(product_id="p1", name="Different Name")
        res = resolve_canonical_identity(product)
        assert res is not None
        assert res.identity_tier == IDENTITY_TIER_C
        assert not res.stable_identity_key.startswith("e|")


class TestCatalogUpsert:
    def test_creates_canonical_entry(self) -> None:
        slug = _seed_store()
        product = CatalogProductInput(
            product_id="prod-100",
            variant_id="var-10",
            sku="SKU-100",
            name="Snapshot Product",
            category="Audio",
            price=49.5,
        )
        result = upsert_catalog_product(
            slug, product, catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY
        )
        assert result.created == 1

        rows = catalog_entries_for_store(slug)
        assert len(rows) == 1
        row = rows[0]
        assert row.product_id == "prod-100"
        assert row.variant_id == "var-10"
        assert row.name == "Snapshot Product"
        assert row.category == "Audio"
        assert row.price == 49.5
        assert row.identity_tier == IDENTITY_TIER_A

    def test_same_product_merges_and_updates_mutable_name(self) -> None:
        slug = _seed_store()
        base = CatalogProductInput(
            product_id="p1", variant_id="v1", name="TrueSound Pro", price=100.0
        )
        upsert_catalog_product(slug, base, catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY)
        updated = CatalogProductInput(
            product_id="p1", variant_id="v1", name="TrueSound Pro Gen 2", price=120.0
        )
        result = upsert_catalog_product(
            slug, updated, catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY
        )
        assert result.updated == 1
        assert catalog_count_for_store(slug) == 1
        row = catalog_entries_for_store(slug)[0]
        assert row.name == "TrueSound Pro Gen 2"
        assert row.price == 120.0

    def test_different_variants_remain_separate(self) -> None:
        slug = _seed_store()
        upsert_catalog_product(
            slug,
            CatalogProductInput(product_id="p1", variant_id="v1", name="Red"),
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
        )
        upsert_catalog_product(
            slug,
            CatalogProductInput(product_id="p1", variant_id="v2", name="Blue"),
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
        )
        assert catalog_count_for_store(slug) == 2

    def test_tier_upgrade_merges_product_id_only_into_variant(self) -> None:
        slug = _seed_store()
        upsert_catalog_product(
            slug,
            CatalogProductInput(product_id="p1", name="Base Product"),
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
        )
        upsert_catalog_product(
            slug,
            CatalogProductInput(product_id="p1", variant_id="v1", name="Variant Product"),
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
        )
        assert catalog_count_for_store(slug) == 1
        row = catalog_entries_for_store(slug)[0]
        assert row.identity_tier == IDENTITY_TIER_A
        assert row.variant_id == "v1"

    def test_sync_from_catalog_json(self) -> None:
        catalog_json = json.dumps(
            {
                "products": [
                    {
                        "id": "json-p1",
                        "name": "JSON Product",
                        "price": 75,
                        "category": "Demo",
                        "sku": "JSON-SKU",
                    }
                ]
            }
        )
        slug = _seed_store(catalog_json=catalog_json)
        result = sync_catalog_from_store_json(slug)
        assert result.created == 1
        row = catalog_entries_for_store(slug)[0]
        assert row.product_id == "json-p1"
        assert row.catalog_source == CATALOG_SOURCE_CATALOG_JSON
        assert row.category == "Demo"

    def test_lookup_by_identity_key(self) -> None:
        slug = _seed_store()
        product = CatalogProductInput(product_id="p9", variant_id="v9", name="Lookup")
        upsert_catalog_product(slug, product, catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY)
        res = resolve_canonical_identity(product)
        assert res is not None
        found = catalog_entry_by_identity_key(slug, res.stable_identity_key)
        assert found is not None
        assert found.name == "Lookup"


class TestCartEventIntegration:
    def test_cart_state_sync_creates_catalog_via_hook(self) -> None:
        slug = _seed_store()
        client = TestClient(main.app)
        session_id = f"s_cat_{uuid.uuid4().hex[:8]}"
        cart_id = f"c_cat_{uuid.uuid4().hex[:10]}"
        lines = [
            {
                "product_id": "hook-prod",
                "variant_id": "hook-var",
                "sku": "HOOK-SKU",
                "name": "Hook Product",
                "unit_price": 88.0,
                "quantity": 1,
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
                "cart_total": 88.0,
                "items_count": 1,
                "cart": [],
                "lines": lines,
            },
        )
        assert r.status_code == 200, r.text
        assert catalog_count_for_store(slug) >= 1
        snaps = db.session.query(CartLineSnapshot).filter_by(store_slug=slug).count()
        assert snaps >= 1

    def test_snapshot_and_catalog_name_divergence(self) -> None:
        slug = _seed_store()
        line_v1 = {
            "product_id": "p-div",
            "variant_id": "v-div",
            "name": "TrueSound Pro",
            "unit_price": 100.0,
            "quantity": 1,
        }
        upsert_catalog_from_lines(
            slug, [line_v1], catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY
        )
        when = datetime.now(timezone.utc).replace(tzinfo=None)
        snap = CartLineSnapshot(
            store_slug=slug,
            session_id="s1",
            cart_id="c1",
            product_id="p-div",
            variant_id="v-div",
            name="TrueSound Pro",
            unit_price=100.0,
            quantity=1,
            captured_at=when,
            capture_source="cart_state_sync",
            capture_confidence="high",
            content_hash="deadbeef" * 4,
        )
        db.session.add(snap)
        db.session.commit()

        upsert_catalog_from_lines(
            slug,
            [{"product_id": "p-div", "variant_id": "v-div", "name": "TrueSound Pro Gen 2"}],
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
        )
        db.session.refresh(snap)
        assert snap.name == "TrueSound Pro"
        catalog = catalog_entries_for_store(slug)[0]
        assert catalog.name == "TrueSound Pro Gen 2"


class TestNormalizerFromLine:
    def test_catalog_input_from_widget_line(self) -> None:
        parsed = catalog_input_from_line(
            {
                "product_id": "w1",
                "variant_id": "wv1",
                "sku": "W-SKU",
                "name": "Widget",
                "unit_price": 10,
            }
        )
        assert parsed is not None
        assert parsed.product_id == "w1"
        assert parsed.price == 10.0
