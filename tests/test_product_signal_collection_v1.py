# -*- coding: utf-8 -*-
"""Product Signal Collection V1 — facts-only collection tests."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

from extensions import db
from models import CartLineSnapshot, ProductSignalEvent, Store
from schema_cart_line_snapshots_v1 import reset_cart_line_snapshots_schema_guard_for_tests
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_signal_collection_flag_v1 import (
    ENV_PRODUCT_SIGNAL_COLLECTION_V1,
)
from services.product_data.product_signal_collection_v1 import (
    collect_from_cart_payload,
    collect_from_customer_return,
    collect_from_hesitation,
    collect_from_purchase,
    collect_from_recovery_timeline,
    signal_count_for_store,
    signals_for_store,
)
from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_EVIDENCE_LINKED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
    SIGNAL_PRODUCT_RECOVERY_STARTED,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (ProductSignalEvent, CartLineSnapshot, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_cart_line_snapshots_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_PRODUCT_SIGNAL_COLLECTION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"sig-{uuid.uuid4().hex[:8]}"
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
) -> None:
    line = {
        "product_id": product_id,
        "name": name,
        "unit_price": 40.0,
        "quantity": 1,
    }
    res = resolve_canonical_identity(catalog_input_from_line(line))
    content = f"{product_id}-{name}-40-1"
    snap = CartLineSnapshot(
        store_slug=slug,
        session_id=session_id,
        cart_id=cart_id,
        product_id=product_id,
        name=name,
        unit_price=40.0,
        quantity=1,
        captured_at=datetime.now(timezone.utc).replace(tzinfo=None),
        capture_source="cart_state_sync",
        capture_confidence=res.capture_confidence if res else "low",
        content_hash=content.ljust(64, "0")[:64],
    )
    db.session.add(snap)
    db.session.commit()


class TestProductSignalCollection:
    def test_cart_add_collects_product_signal(self) -> None:
        slug = _seed_store()
        sid = f"s-{uuid.uuid4().hex[:10]}"
        payload = {
            "store": slug,
            "session_id": sid,
            "cart_id": "c1",
            "event": "cart_state_sync",
            "reason": "add",
            "lines": [
                {
                    "product_id": "demo_tea",
                    "name": "Tea Box",
                    "unit_price": 40,
                    "quantity": 1,
                }
            ],
        }
        result = collect_from_cart_payload(payload, event_hint="cart_state_sync")
        assert result.inserted >= 1
        types = {r["signal_type"] for r in signals_for_store(slug)}
        assert SIGNAL_PRODUCT_CART_ADDED in types
        assert SIGNAL_PRODUCT_EVIDENCE_LINKED in types
        assert signal_count_for_store(slug) >= 1

    def test_hesitation_and_purchase_signals(self) -> None:
        slug = _seed_store()
        sid = f"s-{uuid.uuid4().hex[:10]}"
        _add_snapshot(slug, sid, "c1", product_id="demo_oil", name="Argan Oil")
        h = collect_from_hesitation(slug, sid, cart_id="c1")
        assert h.inserted >= 1
        p = collect_from_purchase(
            slug,
            sid,
            cart_id="c1",
            recovery_key=f"{slug}:{sid}",
            order_id="ord-1",
        )
        assert p.inserted >= 1
        types = {r["signal_type"] for r in signals_for_store(slug, limit=50)}
        assert SIGNAL_PRODUCT_INTEREST_HESITATION in types
        assert SIGNAL_PRODUCT_PURCHASED in types

    def test_recovery_and_return_signals(self) -> None:
        slug = _seed_store()
        sid = f"s-{uuid.uuid4().hex[:10]}"
        _add_snapshot(slug, sid, "c1", product_id="demo_soap", name="Soap")
        r = collect_from_recovery_timeline(
            store_slug=slug,
            session_id=sid,
            status="scheduled",
            cart_id="c1",
            recovery_key=f"{slug}:{sid}",
            timeline_event_id=99,
        )
        assert r.inserted >= 1
        ret = collect_from_customer_return(
            {
                "store": slug,
                "session_id": sid,
                "cart_id": "c1",
                "return_context": "cart",
            }
        )
        assert ret.inserted >= 1
        types = {row["signal_type"] for row in signals_for_store(slug)}
        assert SIGNAL_PRODUCT_RECOVERY_STARTED in types
        assert SIGNAL_PRODUCT_CUSTOMER_RETURNED in types

    def test_dedup_skips_identical_signal(self) -> None:
        slug = _seed_store()
        sid = f"s-{uuid.uuid4().hex[:10]}"
        payload = {
            "store": slug,
            "session_id": sid,
            "cart_id": "c1",
            "event": "cart_state_sync",
            "reason": "add",
            "lines": [
                {
                    "product_id": "demo_dup",
                    "name": "Dup Item",
                    "unit_price": 10,
                    "quantity": 1,
                }
            ],
        }
        first = collect_from_cart_payload(payload, event_hint="cart_state_sync")
        second = collect_from_cart_payload(payload, event_hint="cart_state_sync")
        assert first.inserted >= 1
        assert second.inserted == 0
        assert second.skipped_duplicate >= 1

    def test_kill_switch_disables_collection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_PRODUCT_SIGNAL_COLLECTION_V1, "0")
        slug = _seed_store()
        result = collect_from_cart_payload(
            {
                "store": slug,
                "session_id": "s-off",
                "cart_id": "c1",
                "event": "cart_state_sync",
                "reason": "add",
                "lines": [
                    {
                        "product_id": "demo_off",
                        "name": "Off",
                        "unit_price": 1,
                        "quantity": 1,
                    }
                ],
            },
            event_hint="cart_state_sync",
        )
        assert result.skipped_disabled == 1
        assert signal_count_for_store(slug) == 0

    def test_no_products_skips_honestly(self) -> None:
        slug = _seed_store()
        result = collect_from_cart_payload(
            {
                "store": slug,
                "session_id": "s-empty",
                "cart_id": "c1",
                "event": "cart_state_sync",
                "reason": "add",
                "lines": [],
            },
            event_hint="cart_state_sync",
        )
        assert result.skipped_empty == 1 or result.inserted == 0
        assert signal_count_for_store(slug) == 0
