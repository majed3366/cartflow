# -*- coding: utf-8 -*-
"""MEIF V1 — governed page integration (no new intelligence)."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import AbandonedCart, ProductSignalEvent, Store
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data import merchant_experience_integration_foundation_v1 as meif_mod
from services.product_data.commercial_guidance_flag_v1 import ENV_COMMERCIAL_GUIDANCE_V1
from services.product_data.guidance_eligibility_flag_v1 import ENV_GUIDANCE_ELIGIBILITY_V1
from services.product_data.guidance_routing_flag_v1 import ENV_GUIDANCE_ROUTING_V1
from services.product_data.knowledge_foundation_flag_v1 import ENV_KNOWLEDGE_FOUNDATION_V1
from services.product_data.merchant_experience_integration_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
    merchant_experience_integration_v1_enabled,
)
from services.product_data.merchant_experience_integration_foundation_v1 import (
    attach_merchant_experience_to_summary_v1,
    generate_merchant_experience_integration_v1,
    read_merchant_operational_state_v1,
)
from services.product_data.merchant_experience_integration_prod_probe_v1 import (
    build_merchant_experience_prod_probe_v1,
)
from services.product_data.merchant_experience_integration_registry_v1 import (
    integration_map_valid_v1,
)
from services.product_data.merchant_experience_knowledge_translation_v1 import (
    translate_knowledge_for_merchant_v1,
)
from services.product_data.merchant_presentation_flag_v1 import ENV_MERCHANT_PRESENTATION_V1
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.product_data.surface_composition_flag_v1 import ENV_SURFACE_COMPOSITION_V1
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (AbandonedCart, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    for env in (
        ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
        ENV_SURFACE_COMPOSITION_V1,
        ENV_MERCHANT_PRESENTATION_V1,
        ENV_GUIDANCE_ROUTING_V1,
        ENV_COMMERCIAL_GUIDANCE_V1,
        ENV_GUIDANCE_ELIGIBILITY_V1,
        ENV_KNOWLEDGE_FOUNDATION_V1,
    ):
        monkeypatch.setenv(env, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> tuple[str, Store]:
    slug = slug or f"meif-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    return slug, store


def _add_cart(store: Store, *, cart_id: str) -> None:
    db.session.add(
        AbandonedCart(
            store_id=int(store.id),
            zid_cart_id=cart_id,
            customer_phone="966500000000",
            status="waiting",
        )
    )
    db.session.commit()


def test_integration_map_and_flag() -> None:
    assert integration_map_valid_v1()[0] is True
    assert merchant_experience_integration_v1_enabled() is True


def test_no_new_intelligence_imports() -> None:
    src = inspect.getsource(meif_mod)
    assert "generate_surface_compositions_v1" in src
    assert "generate_commerce_intelligence_syntheses_v1" not in src
    assert "evaluate_guidance_eligibility" not in src


def test_knowledge_translation_does_not_strengthen() -> None:
    t = translate_knowledge_for_merchant_v1(
        {
            "knowledge_id": "k1",
            "statement": "Evidence does not include cart_abandoned_count.",
            "confidence_level": "very_high",
        }
    )
    assert t["translated"] is True
    assert t["claim_strengthened"] is False
    assert "لا يعني ذلك غياب" in t["merchant_statement_ar"]


def test_home_governed_and_false_empty_prevention() -> None:
    slug, store = _seed_store()
    for i in range(3):
        _add_cart(store, cart_id=f"c-{i}")
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    report = generate_merchant_experience_integration_v1(slug, as_of=as_of)
    assert report["ok"] is True
    home = report["pages"]["home"]
    assert home["governed_consumption"] is True
    assert home["forbid_zero_kpi_theatre"] is True
    assert home["operational_truth"]["abandoned_carts"] == 3
    carts = report["pages"]["carts"]
    assert carts["forbid_please_wait"] is True
    assert carts["false_empty_prevented"] is True


def test_navigation_integrity() -> None:
    slug, _ = _seed_store()
    report = generate_merchant_experience_integration_v1(slug)
    nav = report["navigation"]
    assert nav["communication"] == "#communication"
    assert nav["settings"] == "#settings"
    assert nav["integrity"]["comms_not_settings"] is True
    assert report["pages"]["decision_workspace"]["nav_required"] is True


def test_attach_summary_overrides_zero_theatre() -> None:
    slug, store = _seed_store()
    _add_cart(store, cart_id="c-x")
    summary = {
        "ok": True,
        "merchant_kpi_abandoned_fmt": "0",
        "merchant_store_cart_counts": {"active_total": "0"},
        "merchant_nav_badge_abandoned": 0,
    }
    out = attach_merchant_experience_to_summary_v1(summary, slug)
    assert "merchant_experience_integration_v1" in out
    assert out["merchant_kpi_abandoned_fmt"] != "0"


def test_ops_state_store_isolation() -> None:
    a, sa = _seed_store()
    b, sb = _seed_store()
    _add_cart(sa, cart_id="a1")
    ops_a = read_merchant_operational_state_v1(a)
    ops_b = read_merchant_operational_state_v1(b)
    assert ops_a["abandoned_carts"] == 1
    assert ops_b["abandoned_carts"] == 0


def test_deterministic_rerun() -> None:
    slug, store = _seed_store()
    _add_cart(store, cart_id="d1")
    as_of = datetime(2026, 7, 22, 15, 0, 0)
    a = generate_merchant_experience_integration_v1(slug, as_of=as_of)
    b = generate_merchant_experience_integration_v1(slug, as_of=as_of)
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]


def test_feature_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1, "0")
    slug, _ = _seed_store()
    report = generate_merchant_experience_integration_v1(slug)
    assert report["ok"] is False
    assert "meif_disabled" in report["errors"]


def test_demo_probe_allowlist() -> None:
    bad = build_merchant_experience_prod_probe_v1("not-demo")
    assert "store_not_allowlisted" in bad["errors"]


def test_main_wiring_only() -> None:
    import main as main_mod

    src = inspect.getsource(main_mod.dev_merchant_experience)
    assert "build_merchant_experience_prod_probe_v1" in src
    assert "generate_merchant_experience_integration_v1" not in src
