# -*- coding: utf-8 -*-
"""Guidance Routing Foundation V1 — Commercial Guidance only."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import GuidanceRoute, ProductSignalEvent, Store
from schema_guidance_routing_v1 import reset_guidance_routing_schema_guard_for_tests
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data import guidance_routing_foundation_v1 as grf_mod
from services.product_data.commercial_guidance_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_V1,
)
from services.product_data.guidance_eligibility_flag_v1 import (
    ENV_GUIDANCE_ELIGIBILITY_V1,
)
from services.product_data.guidance_routing_flag_v1 import ENV_GUIDANCE_ROUTING_V1
from services.product_data.guidance_routing_foundation_v1 import (
    evaluate_guidance_surface_route_v1,
    generate_guidance_routes_v1,
    materialize_guidance_routes_v1,
    verify_guidance_routing_determinism_v1,
)
from services.product_data.guidance_routing_registry_v1 import (
    ROUTING_RULES_V1,
    routing_registry_valid_v1,
)
from services.product_data.guidance_routing_types_v1 import (
    ROUTE_ELIGIBLE,
    ROUTE_INELIGIBLE,
    SCOPE_FULL,
    SCOPE_SUMMARY,
    SURFACE_CARTS,
    SURFACE_COMMUNICATION,
    SURFACE_DECISION,
    SURFACE_HOME,
    SURFACE_SETTINGS,
    SURFACES_V1,
)
from services.product_data.guidance_surface_registry_v1 import (
    SURFACE_REGISTRY_V1,
    list_active_surfaces_v1,
    surface_registry_valid_v1,
)
from services.product_data.knowledge_foundation_flag_v1 import (
    ENV_KNOWLEDGE_FOUNDATION_V1,
)
from services.product_data.product_signal_types_v1 import (
    FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ADDED,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (GuidanceRoute, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_guidance_routing_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
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
    slug = slug or f"grf-{uuid.uuid4().hex[:8]}"
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


def _guidance(
    *,
    key: str = "investigate_conversion_path",
    status: str = "active",
    subject_type: str = "product",
    cart_related: bool = True,
    valid_until: datetime | None = None,
) -> dict:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    until = valid_until or (as_of + timedelta(days=7))
    return {
        "guidance_id": "g-test-1",
        "store_slug": "demo",
        "subject_type": subject_type,
        "subject_id": "p1",
        "guidance_key": key,
        "guidance_status": status,
        "guidance_fingerprint": "fp-g",
        "valid_until": until.isoformat(sep=" "),
        "routing_context": {
            "guidance_key": key,
            "guidance_status": status,
            "subject_type": subject_type,
            "guidance_scope": "commercial_v1",
            "cart_related": cart_related,
            "contract_version": "cgf_v1_routing_context",
        },
    }


def test_registries_valid() -> None:
    ok_s, err_s = surface_registry_valid_v1()
    ok_r, err_r = routing_registry_valid_v1()
    assert ok_s and err_s == []
    assert ok_r and err_r == []
    assert set(list_active_surfaces_v1()) == SURFACES_V1
    assert len(ROUTING_RULES_V1) >= 10
    assert set(SURFACE_REGISTRY_V1.keys()) == SURFACES_V1


def test_consumes_commercial_guidance_only() -> None:
    src = inspect.getsource(grf_mod)
    assert "generate_commercial_guidance_v1" in src
    for banned in (
        "generate_knowledge_v1",
        "evaluate_guidance_eligibility",
        "evaluate_evidence_confidence",
        "assemble_product_evidence",
        "product_metrics_foundation",
        "product_signal",
    ):
        assert banned not in src


def test_no_home_presentation_fields() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    route = evaluate_guidance_surface_route_v1(
        guidance=_guidance(),
        surface_key=SURFACE_HOME,
        as_of=as_of,
        generated_at=as_of,
    )
    for banned in ("show_on_home", "home_card_title", "home_priority"):
        assert banned not in route
        for entry in SURFACE_REGISTRY_V1.values():
            assert banned not in entry


def test_home_summary_and_decision_full_independent() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    g = _guidance()
    home = evaluate_guidance_surface_route_v1(
        guidance=g, surface_key=SURFACE_HOME, as_of=as_of, generated_at=as_of
    )
    decision = evaluate_guidance_surface_route_v1(
        guidance=g, surface_key=SURFACE_DECISION, as_of=as_of, generated_at=as_of
    )
    assert home["route_status"] == ROUTE_ELIGIBLE
    assert home["route_scope"] == SCOPE_SUMMARY
    assert decision["route_status"] == ROUTE_ELIGIBLE
    assert decision["route_scope"] == SCOPE_FULL
    assert home["route_id"] != decision["route_id"]


def test_carts_requires_cart_related_for_investigate() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    ok = evaluate_guidance_surface_route_v1(
        guidance=_guidance(cart_related=True, subject_type="product"),
        surface_key=SURFACE_CARTS,
        as_of=as_of,
        generated_at=as_of,
    )
    bad = evaluate_guidance_surface_route_v1(
        guidance=_guidance(cart_related=False, subject_type="store"),
        surface_key=SURFACE_CARTS,
        as_of=as_of,
        generated_at=as_of,
    )
    assert ok["route_status"] == ROUTE_ELIGIBLE
    assert bad["route_status"] == ROUTE_INELIGIBLE


def test_communication_and_settings_ineligible_for_investigate() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    for surface in (SURFACE_COMMUNICATION, SURFACE_SETTINGS):
        r = evaluate_guidance_surface_route_v1(
            guidance=_guidance(),
            surface_key=surface,
            as_of=as_of,
            generated_at=as_of,
        )
        assert r["route_status"] == ROUTE_INELIGIBLE


def test_not_every_surface_eligible() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    statuses = [
        evaluate_guidance_surface_route_v1(
            guidance=_guidance(key="continue_observing"),
            surface_key=s,
            as_of=as_of,
            generated_at=as_of,
        )["route_status"]
        for s in list_active_surfaces_v1()
    ]
    assert ROUTE_ELIGIBLE in statuses
    assert ROUTE_INELIGIBLE in statuses


def test_expired_guidance_expires_routes() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    r = evaluate_guidance_surface_route_v1(
        guidance=_guidance(valid_until=as_of - timedelta(days=1)),
        surface_key=SURFACE_HOME,
        as_of=as_of,
        generated_at=as_of,
    )
    assert r["route_status"] == "expired"


def test_live_accounting_determinism_materialize() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|grf_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_guidance_routing_determinism_v1(store, as_of=as_of)
    assert det["deterministic"] is True
    report = generate_guidance_routes_v1(store, as_of=as_of)
    assert report["ok"] is True
    assert report["inputs"]["commercial_guidance_only"] is True
    assert report["route_count"] == report["expected_route_pairs"]
    assert report["expected_route_pairs"] == report["guidance_count"] * 5
    m1 = materialize_guidance_routes_v1(store, as_of=as_of)
    m2 = materialize_guidance_routes_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    current = (
        db.session.query(GuidanceRoute)
        .filter(
            GuidanceRoute.store_slug == store,
            GuidanceRoute.is_current.is_(True),
        )
        .count()
    )
    assert current == report["route_count"]


def test_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_GUIDANCE_ROUTING_V1, "0")
    out = materialize_guidance_routes_v1(store)
    assert out.get("skipped_disabled") is True


def test_no_ai_or_provider() -> None:
    low = inspect.getsource(grf_mod).lower()
    for banned in ("openai", "anthropic", "zid_api", "salla_api", "shopify"):
        assert banned not in low


def test_no_merchant_wording_in_routes() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    r = evaluate_guidance_surface_route_v1(
        guidance=_guidance(),
        surface_key=SURFACE_HOME,
        as_of=as_of,
        generated_at=as_of,
    )
    for banned in ("you should", "card title", "priority badge", "cta"):
        assert banned not in str(r).lower()
