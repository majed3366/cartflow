# -*- coding: utf-8 -*-
"""TABF V1 — Time Authority Binding Foundation tests."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime

import pytest

from extensions import db
from models import AbandonedCart, Store
from schema_store_identity import ensure_store_identity_schema
from services.product_data.commercial_guidance_flag_v1 import ENV_COMMERCIAL_GUIDANCE_V1
from services.product_data.guidance_eligibility_flag_v1 import ENV_GUIDANCE_ELIGIBILITY_V1
from services.product_data.guidance_routing_flag_v1 import ENV_GUIDANCE_ROUTING_V1
from services.product_data.knowledge_foundation_flag_v1 import ENV_KNOWLEDGE_FOUNDATION_V1
from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1
from services.product_data.merchant_experience_integration_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
)
from services.product_data.merchant_experience_integration_foundation_v1 import (
    generate_merchant_experience_integration_v1,
)
from services.product_data.merchant_presentation_flag_v1 import ENV_MERCHANT_PRESENTATION_V1
from services.product_data.operational_truth_flag_v1 import ENV_OPERATIONAL_TRUTH_V1
from services.product_data.operational_truth_foundation_v1 import (
    generate_operational_truth_v1,
)
from services.product_data.surface_composition_flag_v1 import ENV_SURFACE_COMPOSITION_V1
from services.product_data.surface_composition_foundation_v1 import (
    generate_surface_compositions_v1,
)
from services.product_data.time_authority_binding_flag_v1 import (
    ENV_TIME_AUTHORITY_BINDING_V1,
    time_authority_binding_v1_enabled,
)
from services.product_data.time_authority_binding_foundation_v1 import (
    generate_time_authority_binding_v1,
    verify_replay_ordering_consistency_v1,
)
from services.product_data.time_authority_binding_prod_probe_v1 import (
    build_time_authority_prod_probe_v1,
)
from services.product_data.time_authority_binding_registry_v1 import (
    SUBSYSTEM_BINDINGS_V1,
    TIME_INVENTORY_V1,
    tabf_registry_valid_v1,
)
from services.product_data.time_authority_binding_resolve_v1 import (
    resolve_bound_as_of_v1,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from services.time_authority.context_scope import historical_replay_scope
from services.time_authority.providers import FixedAsOfProvider
from services.time_authority.authority import use_provider
from tests.test_recovery_isolation import _reset_recovery_memory


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    for env in (
        ENV_TIME_AUTHORITY_BINDING_V1,
        ENV_OPERATIONAL_TRUTH_V1,
        ENV_SURFACE_COMPOSITION_V1,
        ENV_MERCHANT_PRESENTATION_V1,
        ENV_GUIDANCE_ROUTING_V1,
        ENV_COMMERCIAL_GUIDANCE_V1,
        ENV_GUIDANCE_ELIGIBILITY_V1,
        ENV_KNOWLEDGE_FOUNDATION_V1,
        ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
    ):
        monkeypatch.setenv(env, "1")
    db.session.query(AbandonedCart).delete()
    db.session.query(Store).delete()
    db.session.commit()
    db.create_all()
    ensure_store_identity_schema(db)
    yield


def _seed(n_carts: int = 3) -> str:
    slug = f"tabf-{uuid.uuid4().hex[:8]}"
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
                zid_cart_id=f"tabf-c-{i}",
                customer_phone="966500000000",
                status="waiting",
            )
        )
    db.session.commit()
    return slug


def test_registry_integrity() -> None:
    ok, errors = tabf_registry_valid_v1()
    assert ok is True
    assert not errors
    assert len(TIME_INVENTORY_V1) >= 10
    assert len(SUBSYSTEM_BINDINGS_V1) >= 8
    assert time_authority_binding_v1_enabled() is True


def test_resolve_explicit_and_authority() -> None:
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    assert resolve_bound_as_of_v1(as_of) == as_of
    with use_provider(FixedAsOfProvider(as_of)):
        assert resolve_bound_as_of_v1(None) == as_of


def test_deterministic_replay_and_historical_ordering() -> None:
    slug = _seed()
    as_of = datetime(2026, 7, 22, 12, 0, 0)
    det = verify_replay_ordering_consistency_v1(slug, as_of=as_of)
    assert det["replay_consistent"] is True
    assert det["deterministic_scf"] is True
    assert det["deterministic_ot"] is True
    assert det["ordering_consistent"] is True

    with historical_replay_scope(as_of=as_of):
        a = generate_surface_compositions_v1(slug)
        b = generate_surface_compositions_v1(slug)
    assert a["as_of"] == b["as_of"] == as_of.isoformat(sep=" ")
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]


def test_scf_ot_knowledge_meif_binding() -> None:
    slug = _seed()
    as_of = datetime(2026, 7, 22, 15, 30, 0)
    scf = generate_surface_compositions_v1(slug, as_of=as_of)
    ot = generate_operational_truth_v1(slug, as_of=as_of)
    kf = generate_knowledge_v1(slug, as_of=as_of)
    me = generate_merchant_experience_integration_v1(slug, as_of=as_of)
    expected = as_of.isoformat(sep=" ")
    assert scf["as_of"] == expected
    assert ot["as_of"] == expected
    assert kf["as_of"] == expected
    assert me["as_of"] == expected
    cue = (me.get("pages") or {}).get("home", {}).get("chronology_cue") or {}
    assert cue.get("as_of") == expected
    assert cue.get("page_owned_freshness") is False
    # Freshness originates from as_of (no page-level calc)
    for c in scf.get("compositions") or []:
        assert "freshness_state" in c


def test_duplicate_timestamp_suppression() -> None:
    slug = _seed()
    as_of = datetime(2026, 7, 22, 16, 0, 0)
    a = generate_time_authority_binding_v1(slug, as_of=as_of)
    b = generate_time_authority_binding_v1(slug, as_of=as_of)
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]
    assert a["ok"] is True


def test_feature_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_TIME_AUTHORITY_BINDING_V1, "0")
    slug = _seed()
    report = generate_time_authority_binding_v1(slug)
    assert report["ok"] is False
    assert "tabf_disabled" in report["errors"]


def test_runtime_probe_and_main_wiring() -> None:
    bad = build_time_authority_prod_probe_v1("not-demo")
    assert "store_not_allowlisted" in bad["errors"]
    slug = _seed()
    # allow any for unit test of generate path via probe allowlist override
    good = build_time_authority_prod_probe_v1(slug, allow_any_store=True)
    assert good.get("replay_consistency", {}).get("replay_consistent") is True
    assert good.get("scf_binding", {}).get("uses_bound_as_of") is True

    import main as main_mod

    src = inspect.getsource(main_mod.dev_time_authority)
    assert "build_time_authority_prod_probe_v1" in src
    assert "generate_time_authority_binding_v1" not in src
    assert "/dev/time-authority" in main_mod._DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT


def test_scheduler_consistency_via_authority_provider() -> None:
    """Processing/observation share FixedAsOf — no wall drift between layers."""
    slug = _seed()
    as_of = datetime(2026, 1, 15, 9, 0, 0)
    with use_provider(FixedAsOfProvider(as_of)):
        scf = generate_surface_compositions_v1(slug)
        ot = generate_operational_truth_v1(slug)
    assert scf["as_of"] == ot["as_of"] == as_of.isoformat(sep=" ")
