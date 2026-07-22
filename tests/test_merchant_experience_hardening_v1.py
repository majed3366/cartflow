# -*- coding: utf-8 -*-
"""MEH V1 — merchant experience hardening (no new platform capabilities)."""
from __future__ import annotations

import uuid

import pytest

from extensions import db
from models import AbandonedCart, Store
from schema_store_identity import ensure_store_identity_schema
from services.product_data.merchant_experience_capability_gaps_v1 import (
    capability_gaps_v1,
)
from services.product_data.merchant_experience_hardening_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_HARDENING_V1,
)
from services.product_data.merchant_experience_hardening_v1 import (
    FINDINGS_CLASSIFICATION_V1,
    findings_classification_v1,
)
from services.product_data.merchant_experience_integration_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
)
from services.product_data.merchant_experience_integration_foundation_v1 import (
    generate_merchant_experience_integration_v1,
)
from services.product_data.merchant_experience_integration_prod_probe_v1 import (
    build_merchant_experience_prod_probe_v1,
)
from services.product_data.merchant_presentation_flag_v1 import ENV_MERCHANT_PRESENTATION_V1
from services.product_data.surface_composition_flag_v1 import ENV_SURFACE_COMPOSITION_V1
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
        ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
        ENV_MERCHANT_EXPERIENCE_HARDENING_V1,
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


def _seed() -> tuple[str, Store]:
    slug = f"meh-{uuid.uuid4().hex[:8]}"
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


def test_every_finding_classified() -> None:
    classif = findings_classification_v1()
    assert classif["unclassified_count"] == 0
    assert classif["category_a_count"] >= 1
    assert classif["category_b_count"] >= 1
    for f in FINDINGS_CLASSIFICATION_V1:
        assert f["category"] in {"A", "B"}
        assert f.get("root_cause")
        assert f.get("existing_owner")
        assert f.get("affected_layer")
        assert "solvable_now" in f


def test_capability_gaps_cover_category_b() -> None:
    gaps = capability_gaps_v1()
    assert gaps["count"] >= 1
    covered = set()
    for g in gaps["gaps"]:
        covered.update(g.get("finding_ids") or [])
    for f in FINDINGS_CLASSIFICATION_V1:
        if f["category"] == "B":
            assert f["finding_id"] in covered or f.get("gap_ids")


def test_trust_labeling_and_ops_facts() -> None:
    slug, store = _seed()
    db.session.add(
        AbandonedCart(
            store_id=int(store.id),
            zid_cart_id="meh-c1",
            customer_phone="966500000001",
            status="waiting",
        )
    )
    db.session.commit()
    report = generate_merchant_experience_integration_v1(slug)
    assert report["ok"] is True
    hard = report.get("hardening") or {}
    assert hard.get("enabled") is True
    home = report["pages"]["home"]
    assert home.get("trust_labeling") is True
    assert home.get("suppress_setup_theatre") is True
    crit = (home.get("sections") or {}).get("critical_attention") or []
    assert crit
    assert crit[0].get("trust_class") == "fact"
    assert home.get("chronology_cue", {}).get("as_of")
    carts = report["pages"]["carts"]
    assert carts.get("attention_answered") is True
    assert hard.get("legacy_leakage_count") == 0
    assert int(hard.get("readiness_score") or 0) >= 85
    assert hard.get("chapter_outcome") == "chapter_closed"
    unresolved = hard.get("unresolved_findings") or []
    assert unresolved
    assert all(u.get("category") == "B" for u in unresolved)


def test_monitor_guidance_demoted_not_as_recommendation() -> None:
    slug, store = _seed()
    db.session.add(
        AbandonedCart(
            store_id=int(store.id),
            zid_cart_id="meh-c2",
            customer_phone="966500000002",
            status="waiting",
        )
    )
    db.session.commit()
    report = generate_merchant_experience_integration_v1(slug)
    home = report["pages"]["home"]
    sections = home.get("sections") or {}
    for item in sections.get("commercial_guidance_highlights") or []:
        key = str((item.get("source_lineage") or {}).get("guidance_key") or "").lower()
        assert "monitor" not in key
        assert item.get("trust_class") == "recommendation"
    for item in sections.get("monitoring_observations") or []:
        assert item.get("trust_class") == "observation"


def test_probe_exposes_hardening_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MERCHANT_EXPERIENCE_HARDENING_V1, "1")
    slug, store = _seed()
    db.session.add(
        AbandonedCart(
            store_id=int(store.id),
            zid_cart_id="meh-c3",
            customer_phone="966500000003",
            status="waiting",
        )
    )
    db.session.commit()
    # Probe allowlist is demo-only; exercise generator path via allow_any for unit.
    from services.product_data import merchant_experience_integration_prod_probe_v1 as probe_mod

    monkeypatch.setattr(probe_mod, "_ALLOWED_STORES", frozenset({slug, "demo"}))
    probe = build_merchant_experience_prod_probe_v1(slug)
    assert "readiness_score" in probe
    assert "unresolved_findings" in probe
    assert "capability_gaps" in probe
    assert "legacy_leakage_count" in probe
    assert "hardening_status" in probe
    assert probe["legacy_leakage_count"] == 0
    assert int(probe["readiness_score"] or 0) >= 85
