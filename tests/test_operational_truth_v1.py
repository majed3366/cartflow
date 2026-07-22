# -*- coding: utf-8 -*-
"""OTIF V1 — Operational Truth Integration Foundation tests."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime

import pytest

from extensions import db
from models import AbandonedCart, Store
from schema_store_identity import ensure_store_identity_schema
from services.product_data.operational_truth_flag_v1 import (
    ENV_OPERATIONAL_TRUTH_V1,
    operational_truth_v1_enabled,
)
from services.product_data.operational_truth_foundation_v1 import (
    generate_operational_truth_v1,
    verify_operational_truth_determinism_v1,
)
from services.product_data.operational_truth_prod_probe_v1 import (
    build_operational_truth_prod_probe_v1,
)
from services.product_data.operational_truth_registry_v1 import (
    OPERATIONAL_TRUTH_REGISTRY_V1,
    operational_truth_registry_valid_v1,
)
from services.product_data.surface_composition_flag_v1 import ENV_SURFACE_COMPOSITION_V1
from services.product_data.surface_composition_foundation_v1 import (
    generate_surface_compositions_v1,
)
from services.product_data.surface_composition_types_v1 import SOURCE_OPERATIONAL_TRUTH
from services.product_data.merchant_presentation_flag_v1 import ENV_MERCHANT_PRESENTATION_V1
from services.product_data.guidance_routing_flag_v1 import ENV_GUIDANCE_ROUTING_V1
from services.product_data.commercial_guidance_flag_v1 import ENV_COMMERCIAL_GUIDANCE_V1
from services.product_data.guidance_eligibility_flag_v1 import ENV_GUIDANCE_ELIGIBILITY_V1
from services.product_data.knowledge_foundation_flag_v1 import ENV_KNOWLEDGE_FOUNDATION_V1
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    for env in (
        ENV_OPERATIONAL_TRUTH_V1,
        ENV_SURFACE_COMPOSITION_V1,
        ENV_MERCHANT_PRESENTATION_V1,
        ENV_GUIDANCE_ROUTING_V1,
        ENV_COMMERCIAL_GUIDANCE_V1,
        ENV_GUIDANCE_ELIGIBILITY_V1,
        ENV_KNOWLEDGE_FOUNDATION_V1,
    ):
        monkeypatch.setenv(env, "1")
    db.session.query(AbandonedCart).delete()
    db.session.query(Store).delete()
    db.session.commit()
    db.create_all()
    ensure_store_identity_schema(db)
    yield


def _seed(n_carts: int = 0) -> tuple[str, Store]:
    slug = f"ot-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    for i in range(n_carts):
        db.session.add(
            AbandonedCart(
                store_id=int(store.id),
                zid_cart_id=f"ot-c-{i}",
                customer_phone="966500000000",
                status="waiting",
            )
        )
    db.session.commit()
    return slug, store


def test_registry_integrity() -> None:
    ok, errors = operational_truth_registry_valid_v1()
    assert ok is True
    assert not errors
    assert len(OPERATIONAL_TRUTH_REGISTRY_V1) >= 5
    assert operational_truth_v1_enabled() is True


def test_deterministic_generation() -> None:
    slug, _ = _seed(n_carts=5)
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    det = verify_operational_truth_determinism_v1(slug, as_of=as_of)
    assert det["deterministic"] is True
    a = generate_operational_truth_v1(slug, as_of=as_of)
    assert a["ok"] is True
    assert a["package_count"] == len(OPERATIONAL_TRUTH_REGISTRY_V1)


def test_stability_and_severity_routing() -> None:
    slug, _ = _seed(n_carts=12)
    report = generate_operational_truth_v1(slug)
    waiting = next(
        p for p in report["packages"] if p["truth_id"] == "ot_waiting_carts"
    )
    assert waiting["visibility"] == "expose"
    assert waiting["severity"] == "critical"
    assert waiting["requires_merchant_attention"] is True
    assert waiting["stability"] in {"stable", "forming"}
    assert "home" in waiting["destination_surfaces"]
    assert waiting["explainability"]["what_happened_ar"]
    assert waiting["explainability"]["why_true_ar"]
    assert waiting["explainability"]["evidence_ar"]
    assert waiting["no_recommendation"] is True


def test_duplicate_suppression_below_threshold() -> None:
    slug, _ = _seed(n_carts=0)
    report = generate_operational_truth_v1(slug)
    waiting = next(
        p for p in report["packages"] if p["truth_id"] == "ot_waiting_carts"
    )
    assert waiting["visibility"] == "suppress"
    assert waiting["visibility_reason"] == "below_evidence_threshold"


def test_surface_composition_integration() -> None:
    slug, _ = _seed(n_carts=8)
    as_of = datetime(2026, 7, 22, 14, 0, 0)
    scf = generate_surface_compositions_v1(slug, as_of=as_of)
    assert scf["inputs"].get("operational_truth") is True
    ot = [
        c
        for c in scf["compositions"]
        if c.get("source_type") == SOURCE_OPERATIONAL_TRUTH
    ]
    assert ot
    surfaces = {c.get("surface_id") for c in ot if c.get("visibility") == "visible"}
    assert "home" in surfaces or "carts" in surfaces or "decision_workspace" in surfaces
    # No false empty on carts when OT waiting carts exposed
    carts_empty = [
        c
        for c in scf["compositions"]
        if c.get("surface_id") == "carts"
        and c.get("information_class") == "empty_state"
        and c.get("visibility") == "visible"
    ]
    assert not carts_empty or any(
        c.get("source_type") == SOURCE_OPERATIONAL_TRUTH
        and c.get("surface_id") == "carts"
        and c.get("visibility") == "visible"
        for c in scf["compositions"]
    )


def test_explainability_and_no_page_owned_logic() -> None:
    import services.product_data.operational_truth_foundation_v1 as ot_mod

    src = inspect.getsource(ot_mod)
    assert "read_operational_state_snapshot_v1" in src
    assert "generate_commercial_guidance" not in src
    assert "generate_knowledge_v1" not in src


def test_feature_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_OPERATIONAL_TRUTH_V1, "0")
    slug, _ = _seed(n_carts=3)
    report = generate_operational_truth_v1(slug)
    assert report["ok"] is False
    assert "otif_disabled" in report["errors"]


def test_probe_allowlist_and_main_wiring() -> None:
    bad = build_operational_truth_prod_probe_v1("not-demo")
    assert "store_not_allowlisted" in bad["errors"]
    import main as main_mod

    src = inspect.getsource(main_mod.dev_operational_truth)
    assert "build_operational_truth_prod_probe_v1" in src
    assert "generate_operational_truth_v1" not in src


def test_failure_isolation_registry() -> None:
    slug, _ = _seed(n_carts=2)
    report = generate_operational_truth_v1(slug)
    assert report["orphan_count"] == 0
    assert report["registries_valid"] is True
