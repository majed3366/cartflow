# -*- coding: utf-8 -*-
"""Merchant Presentation Foundation V1 — Guidance Routing only."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import MerchantPresentation, ProductSignalEvent, Store
from schema_merchant_presentation_v1 import (
    reset_merchant_presentation_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data import merchant_presentation_foundation_v1 as mpf_mod
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
from services.product_data.merchant_presentation_foundation_v1 import (
    evaluate_route_presentation_v1,
    generate_merchant_presentations_v1,
    materialize_merchant_presentations_v1,
    verify_merchant_presentation_determinism_v1,
)
from services.product_data.merchant_presentation_registry_v1 import (
    PRESENTATION_RULES_V1,
    presentation_registry_valid_v1,
)
from services.product_data.merchant_presentation_templates_v1 import (
    TEMPLATE_REGISTRY_V1,
    template_registry_valid_v1,
)
from services.product_data.merchant_presentation_types_v1 import (
    AFFORDANCE_NAVIGATE,
    AFFORDANCE_REVIEW,
    STATE_READY,
    TYPE_DECISION_PROMPT,
    TYPE_EXECUTIVE_SUMMARY,
    TYPE_OPERATIONAL_NOTICE,
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
    for model in (MerchantPresentation, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_merchant_presentation_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
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
    slug = slug or f"mpf-{uuid.uuid4().hex[:8]}"
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


def _route(
    *,
    surface: str = "home",
    scope: str = "summary",
    role: str = "awareness",
    status: str = "eligible",
    key: str = "investigate_conversion_path",
    subject_type: str = "product",
) -> dict:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    return {
        "route_id": f"r-{surface}-{key[:8]}",
        "guidance_id": "g1",
        "store_slug": "demo",
        "subject_type": subject_type,
        "subject_id": "p1",
        "surface_key": surface,
        "route_scope": scope,
        "route_role": role,
        "route_status": status,
        "guidance_key": key,
        "route_fingerprint": "fp-r",
        "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
        "presentation_context": {
            "contract_version": "grf_v1_presentation_context",
            "guidance_key": key,
            "guidance_status": "active",
            "known_facts": [
                "Cart additions have newly appeared during the last 7 days.",
                "Evidence does not include purchase_count.",
            ],
            "unknown_facts": [
                "The current evidence does not establish a commercial root cause."
            ],
            "prohibited_claims": ["Do not claim a specific root cause."],
            "evidence_state": "sufficient_evidence",
            "subject_type": subject_type,
        },
    }


def test_registries_valid() -> None:
    assert presentation_registry_valid_v1()[0] is True
    assert template_registry_valid_v1()[0] is True
    assert len(PRESENTATION_RULES_V1) >= 8
    assert len(TEMPLATE_REGISTRY_V1) >= 6


def test_consumes_routing_only() -> None:
    src = inspect.getsource(mpf_mod)
    assert "generate_guidance_routes_v1" in src
    for banned in (
        "generate_commercial_guidance_v1",
        "evaluate_guidance_eligibility",
        "generate_knowledge_v1",
        "evaluate_evidence_confidence",
        "product_metrics_foundation",
    ):
        assert banned not in src


def test_home_executive_summary() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    p = evaluate_route_presentation_v1(
        route=_route(), as_of=as_of, generated_at=as_of
    )
    assert p is not None
    assert p["presentation_type"] == TYPE_EXECUTIVE_SUMMARY
    assert p["presentation_state"] == STATE_READY
    assert p["action_affordance"] == AFFORDANCE_NAVIGATE
    assert "show_on_home" not in p
    assert p["known_fact_items"] == []  # summary slots omit known_facts list
    assert "shipping is expensive" not in p["primary_statement_text"].lower()


def test_decision_full_context_independent() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    p = evaluate_route_presentation_v1(
        route=_route(
            surface="decision_workspace",
            scope="full_context",
            role="investigation",
        ),
        as_of=as_of,
        generated_at=as_of,
    )
    assert p is not None
    assert p["presentation_type"] == TYPE_DECISION_PROMPT
    assert p["action_affordance"] == AFFORDANCE_REVIEW
    assert p["known_fact_items"]
    assert p["unknown_fact_items"]


def test_carts_operational() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    p = evaluate_route_presentation_v1(
        route=_route(
            surface="carts",
            scope="operational",
            role="operational_attention",
        ),
        as_of=as_of,
        generated_at=as_of,
    )
    assert p is not None
    assert p["presentation_type"] == TYPE_OPERATIONAL_NOTICE
    assert p["action_affordance"] == "inspect"


def test_ineligible_produces_none() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    p = evaluate_route_presentation_v1(
        route=_route(status="ineligible", surface="settings"),
        as_of=as_of,
        generated_at=as_of,
    )
    assert p is None


def test_no_causal_or_action_execution_language() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    p = evaluate_route_presentation_v1(
        route=_route(), as_of=as_of, generated_at=as_of
    )
    assert p is not None
    blob = " ".join(
        [
            p["headline_text"],
            p["primary_statement_text"],
            p["supporting_statement_text"],
        ]
    ).lower()
    for banned in (
        "shipping is expensive",
        "lower the shipping",
        "increase advertising",
        "guaranteed",
        "send whatsapp",
    ):
        assert banned not in blob


def test_live_accounting_determinism_materialize() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|mpf_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_merchant_presentation_determinism_v1(store, as_of=as_of)
    assert det["deterministic"] is True
    report = generate_merchant_presentations_v1(store, as_of=as_of)
    assert report["ok"] is True
    assert report["inputs"]["guidance_routing_only"] is True
    assert report["presentation_count"] == report["expected_presentation_count"]
    assert report["eligible_route_count"] > 0
    m1 = materialize_merchant_presentations_v1(store, as_of=as_of)
    m2 = materialize_merchant_presentations_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(MerchantPresentation)
        .filter(
            MerchantPresentation.store_slug == store,
            MerchantPresentation.is_current.is_(True),
        )
        .count()
    )
    assert n == report["presentation_count"]


def test_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_MERCHANT_PRESENTATION_V1, "0")
    out = materialize_merchant_presentations_v1(store)
    assert out.get("skipped_disabled") is True


def test_no_ai_dependency() -> None:
    low = inspect.getsource(mpf_mod).lower()
    for banned in ("openai", "anthropic", "langchain", "llm"):
        assert banned not in low
