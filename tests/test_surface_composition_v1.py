# -*- coding: utf-8 -*-
"""Surface Composition Foundation V1 — governed Presentation + Knowledge only."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import ProductSignalEvent, Store, SurfaceComposition
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from schema_surface_composition_v1 import (
    reset_surface_composition_schema_guard_for_tests,
)
from services.product_data import surface_composition_foundation_v1 as scf_mod
from services.product_data.commercial_guidance_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_V1,
)
from services.product_data.guidance_eligibility_flag_v1 import (
    ENV_GUIDANCE_ELIGIBILITY_V1,
)
from services.product_data.guidance_routing_flag_v1 import ENV_GUIDANCE_ROUTING_V1
from services.product_data.knowledge_foundation_flag_v1 import (
    ENV_KNOWLEDGE_FOUNDATION_V1,
)
from services.product_data.merchant_presentation_flag_v1 import (
    ENV_MERCHANT_PRESENTATION_V1,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.product_data.surface_composition_flag_v1 import (
    ENV_SURFACE_COMPOSITION_V1,
    surface_composition_v1_enabled,
)
from services.product_data.surface_composition_foundation_v1 import (
    evaluate_presentation_composition_v1,
    freshness_state_v1,
    generate_surface_compositions_v1,
    materialize_surface_compositions_v1,
    priority_score_v1,
    verify_surface_composition_determinism_v1,
)
from services.product_data.surface_composition_prod_probe_v1 import (
    build_surface_composition_prod_probe_v1,
)
from services.product_data.surface_composition_registry_v1 import (
    SURFACE_REGISTRY_V1,
    surface_registry_valid_v1,
)
from services.product_data.surface_composition_types_v1 import (
    CLASS_EXECUTIVE_SUMMARY,
    FRESH_AGING,
    FRESH_EXPIRED,
    FRESH_FRESH,
    FRESH_STALE,
    INTENT_HERO,
    SURFACE_HOME,
    SURFACES_V1,
    VIS_COLLAPSED,
    VIS_EXPIRED,
    VIS_SUPPRESSED,
    VIS_VISIBLE,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (SurfaceComposition, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_surface_composition_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_SURFACE_COMPOSITION_V1, "1")
    monkeypatch.setenv(ENV_MERCHANT_PRESENTATION_V1, "1")
    monkeypatch.setenv(ENV_GUIDANCE_ROUTING_V1, "1")
    monkeypatch.setenv(ENV_COMMERCIAL_GUIDANCE_V1, "1")
    monkeypatch.setenv(ENV_GUIDANCE_ELIGIBILITY_V1, "1")
    monkeypatch.setenv(ENV_KNOWLEDGE_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"scf-{uuid.uuid4().hex[:8]}"
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    return slug


def _add_signal(*, store: str, identity: str, observed_at: datetime, dedup: str) -> None:
    db.session.add(
        ProductSignalEvent(
            store_slug=store,
            session_id=f"s-{dedup[-8:]}",
            cart_id=f"c-{dedup[-6:]}",
            recovery_key=None,
            stable_identity_key=identity,
            identity_tier="C",
            product_id="p1",
            signal_family=FAMILY_PRODUCT_CART_ACTIVITY,
            signal_type=SIGNAL_PRODUCT_CART_ADDED,
            observed_at=observed_at,
            source="cart_state_sync",
            evidence_ref_type="session",
            evidence_ref_id=f"s-{dedup[-8:]}",
            dedup_hash=dedup,
        )
    )
    db.session.commit()


def _presentation(
    *,
    surface: str = "home",
    ptype: str = "executive_summary",
    state: str = "ready",
    guidance_id: str = "g1",
    presentation_id: str = "pres1",
    valid_until: datetime | None = None,
    role: str = "awareness",
) -> dict:
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    return {
        "presentation_id": presentation_id,
        "route_id": f"r-{surface}",
        "guidance_id": guidance_id,
        "store_slug": "demo",
        "subject_type": "product",
        "subject_id": "p1",
        "surface_key": surface,
        "route_scope": "summary",
        "route_role": role,
        "guidance_key": "investigate_conversion_path",
        "presentation_type": ptype,
        "presentation_state": state,
        "evidence_state": "sufficient_evidence",
        "merchant_relevance_key": "rel",
        "presentation_fingerprint": "fp-p",
        "valid_until": (valid_until or (as_of + timedelta(days=7))).isoformat(sep=" "),
    }


def test_surface_registry() -> None:
    ok, errors = surface_registry_valid_v1()
    assert ok is True, errors
    assert set(SURFACE_REGISTRY_V1) == set(SURFACES_V1)
    for sid, entry in SURFACE_REGISTRY_V1.items():
        assert entry["owner"] == "surface_composition_foundation_v1"
        assert entry["maximum_cognitive_load"]


def test_governed_inputs_only_no_raw_reads() -> None:
    src = inspect.getsource(scf_mod)
    assert "generate_merchant_presentations_v1" in src
    assert "generate_knowledge_v1" in src
    for banned in (
        "generate_commerce_intelligence_syntheses_v1",
        "ProductSignalEvent",
        "generate_commercial_guidance_v1",
        "evaluate_guidance_eligibility",
        "services.whatsapp",
        "AbandonedCart",
        "PurchaseEvent",
    ):
        assert banned not in src
    assert "no_raw_events" in src


def test_information_classes_and_priority_ordering() -> None:
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    a = evaluate_presentation_composition_v1(
        presentation=_presentation(role="critical", presentation_id="a"),
        as_of=as_of,
        generated_at=as_of,
    )
    b = evaluate_presentation_composition_v1(
        presentation=_presentation(role="awareness", presentation_id="b"),
        as_of=as_of,
        generated_at=as_of,
    )
    assert a["information_class"] == CLASS_EXECUTIVE_SUMMARY
    assert a["priority"] > b["priority"]
    score = priority_score_v1(
        information_class="critical_attention",
        route_role="critical",
        presentation_state="ready",
        freshness="fresh",
        evidence_state="sufficient_evidence",
        presentation_type="decision_prompt",
    )
    assert score > 50


def test_freshness_transitions() -> None:
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    assert (
        freshness_state_v1(valid_until=as_of + timedelta(days=5), as_of=as_of)
        == FRESH_FRESH
    )
    assert (
        freshness_state_v1(valid_until=as_of + timedelta(days=2), as_of=as_of)
        == FRESH_AGING
    )
    assert (
        freshness_state_v1(valid_until=as_of + timedelta(hours=12), as_of=as_of)
        == FRESH_STALE
    )
    assert freshness_state_v1(valid_until=as_of - timedelta(seconds=1), as_of=as_of) == (
        FRESH_EXPIRED
    )
    expired = evaluate_presentation_composition_v1(
        presentation=_presentation(valid_until=as_of - timedelta(hours=1)),
        as_of=as_of,
        generated_at=as_of,
    )
    assert expired["visibility"] == VIS_EXPIRED
    assert expired["accounting_outcome"] == "expired"


def test_duplicate_suppression_and_cognitive_load() -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    for i in range(6):
        _add_signal(
            store=slug,
            identity=f"id-{i}",
            observed_at=as_of - timedelta(hours=i + 1),
            dedup=f"d-{slug}-{i}",
        )
    report = generate_surface_compositions_v1(slug, as_of=as_of)
    assert report["ok"] is True
    home = [c for c in report["compositions"] if c["surface_id"] == SURFACE_HOME]
    visible_exec = [
        c
        for c in home
        if c["visibility"] == VIS_VISIBLE
        and c["information_class"] == CLASS_EXECUTIVE_SUMMARY
    ]
    assert len(visible_exec) <= 4
    heroes = [c for c in home if c.get("presentation_intent") == INTENT_HERO]
    assert len(heroes) <= 1
    # Duplicate groups present
    groups = {c["duplicate_group"] for c in report["compositions"]}
    assert groups


def test_empty_state_composition() -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    report = generate_surface_compositions_v1(slug, as_of=as_of)
    assert report["ok"] is True
    empties = [
        c
        for c in report["compositions"]
        if c["information_class"] == "empty_state" and c["visibility"] == VIS_VISIBLE
    ]
    assert empties
    for e in empties:
        assert e["source_type"] == "empty_state"
        assert e["merchant_value"] in {
            "evidence_still_growing",
            "no_operational_issues",
            "insufficient_evidence",
            "nothing_requiring_action",
        }


def test_deterministic_identity_and_idempotent_rerun() -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    for i in range(3):
        _add_signal(
            store=slug,
            identity=f"id-{i}",
            observed_at=as_of - timedelta(hours=i + 1),
            dedup=f"d-{slug}-{i}",
        )
    det = verify_surface_composition_determinism_v1(slug, as_of=as_of)
    assert det["deterministic"] is True
    a = generate_surface_compositions_v1(slug, as_of=as_of)
    b = generate_surface_compositions_v1(slug, as_of=as_of)
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]
    assert [c["composition_id"] for c in a["compositions"]] == [
        c["composition_id"] for c in b["compositions"]
    ]


def test_lifecycle_no_duplicate_current_and_accounting() -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    for i in range(2):
        _add_signal(
            store=slug,
            identity=f"id-{i}",
            observed_at=as_of - timedelta(hours=i + 1),
            dedup=f"d-{slug}-{i}",
        )
    m1 = materialize_surface_compositions_v1(slug, as_of=as_of)
    assert m1["ok"] is True
    m2 = materialize_surface_compositions_v1(slug, as_of=as_of)
    assert m2["ok"] is True
    currents = (
        db.session.query(SurfaceComposition)
        .filter(
            SurfaceComposition.store_slug == slug,
            SurfaceComposition.is_current.is_(True),
        )
        .all()
    )
    keys = [
        (r.surface_id, r.source_type, r.source_id) for r in currents
    ]
    assert len(keys) == len(set(keys))
    report = generate_surface_compositions_v1(slug, as_of=as_of)
    assert report["accounted_count"] == report["composition_count"]
    assert sum(report["accounting"].values()) == report["composition_count"]


def test_suppression_and_expiry_accounting() -> None:
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    failed = evaluate_presentation_composition_v1(
        presentation=_presentation(state="failed", presentation_id="f1"),
        as_of=as_of,
        generated_at=as_of,
    )
    assert failed["visibility"] == VIS_SUPPRESSED
    assert failed["accounting_outcome"] == "failed"
    deferred = evaluate_presentation_composition_v1(
        presentation=_presentation(state="deferred", presentation_id="d1"),
        as_of=as_of,
        generated_at=as_of,
    )
    assert deferred["visibility"] == VIS_COLLAPSED
    assert deferred["accounting_outcome"] == "deferred"


def test_store_isolation_and_demo_probe() -> None:
    a = _seed_store()
    b = _seed_store()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    _add_signal(
        store=a,
        identity="ia",
        observed_at=as_of - timedelta(hours=1),
        dedup=f"d-{a}-1",
    )
    ra = generate_surface_compositions_v1(a, as_of=as_of)
    rb = generate_surface_compositions_v1(b, as_of=as_of)
    assert ra["store_slug"] == a
    assert rb["store_slug"] == b
    assert ra["canonical_fingerprint"] != rb["canonical_fingerprint"]

    probe_bad = build_surface_composition_prod_probe_v1(
        "not-demo", materialize=False
    )
    assert "store_not_allowlisted" in probe_bad["errors"]


def test_feature_flag() -> None:
    monkey_off = surface_composition_v1_enabled
    assert monkey_off() is True
    import os

    os.environ[ENV_SURFACE_COMPOSITION_V1] = "0"
    try:
        assert surface_composition_v1_enabled() is False
        out = materialize_surface_compositions_v1("demo")
        assert out.get("skipped_disabled") is True
    finally:
        os.environ[ENV_SURFACE_COMPOSITION_V1] = "1"


def test_main_wiring_only() -> None:
    import main as main_mod

    src = inspect.getsource(main_mod.dev_surface_composition)
    assert "build_surface_composition_prod_probe_v1" in src
    assert "generate_surface_compositions_v1" not in src
