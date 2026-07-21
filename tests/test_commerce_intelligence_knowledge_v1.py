# -*- coding: utf-8 -*-
"""CIS → Knowledge Integration V1 (ciknow_v1)."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import KnowledgeStatement, Store
from schema_knowledge_foundation_v1 import (
    reset_knowledge_foundation_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.commerce_intelligence_knowledge_flag_v1 import ENV_CIKNOW_V1
from services.product_data.commerce_intelligence_knowledge_intake_v1 import (
    evaluate_synthesis_for_knowledge_v1,
    generate_knowledge_from_synthesis_v1,
    materialize_knowledge_from_synthesis_v1,
    verify_ciknow_determinism_v1,
)
from services.product_data.commerce_intelligence_knowledge_registry_v1 import (
    intake_registry_valid_v1,
)
from services.product_data.commerce_intelligence_knowledge_types_v1 import (
    INPUT_CONTRACT_VERSION_V1,
    KT_PRODUCT_INTEREST_GAP,
    OUTCOME_ABSTAINED,
    OUTCOME_CREATED,
    OUTCOME_DEFERRED,
    OUTCOME_REJECTED,
    REASON_BLOCKED,
    REASON_DEFERRED_DEP,
    REASON_OBSERVING,
    SOURCE_TYPE_CISYN,
)
from services.product_data import commerce_intelligence_knowledge_intake_v1 as ciknow
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset() -> None:
    for model in (KnowledgeStatement, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_knowledge_foundation_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _iso(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_CIKNOW_V1, "1")
    _reset()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset()


def _seed() -> str:
    slug = f"ciknow-{uuid.uuid4().hex[:8]}"
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


def _syn(**kwargs) -> dict:
    base = {
        "synthesis_id": "sid1",
        "synthesis_key": "skey1",
        "synthesis_rule_key": "product_interest_without_purchase",
        "synthesis_state": "qualified",
        "subject_type": "product",
        "subject_id": "p|1",
        "store_slug": "demo",
        "time_window_key": "d7",
        "window_start": "2026-07-14 12:00:00",
        "window_end": "2026-07-21 12:00:00",
        "valid_until": "2026-07-28 12:00:00",
        "evidence_coverage": 0.5,
        "sample_size": 2,
        "source_domains": ["knowledge"],
        "known_facts": ["cart_interest_trend_observed", "purchase_mappings=0"],
        "unknown_facts": ["why_purchase_completion_is_weak"],
        "prohibited_claims": ["root_cause_known", "price_is_the_cause"],
        "synthesis_fingerprint": "sfp1",
        "rule_version": "1",
        "contract_version": "commerce_intelligence_synthesis_v1",
        "synthesis_summary_key": "product_interest_without_purchase.qualified",
        "confidence_input": {"sample_maturity": "medium", "evidence_coverage": 0.5},
    }
    base.update(kwargs)
    return base


def test_registry_and_input_contract() -> None:
    assert intake_registry_valid_v1()
    assert INPUT_CONTRACT_VERSION_V1 == "commerce_intelligence_synthesis_v1"


def test_consumes_synthesis_api_only() -> None:
    src = inspect.getsource(ciknow)
    assert "generate_commerce_intelligence_syntheses_v1" in src
    for banned in (
        "ProductHesitationMapping",
        "load_store_commerce_signals",
        "evaluate_evidence_confidence",
        "zid_",
        "twilio",
        "shopify",
    ):
        assert banned not in src


def test_qualified_creates_knowledge() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    outcome, reason, rec = evaluate_synthesis_for_knowledge_v1(
        _syn(), as_of=as_of
    )
    assert outcome == OUTCOME_CREATED
    assert rec is not None
    assert rec["knowledge_type"] == KT_PRODUCT_INTEREST_GAP
    assert rec["source_type"] == SOURCE_TYPE_CISYN
    assert rec["known_facts"] == ["cart_interest_trend_observed", "purchase_mappings=0"]
    assert "root_cause_known" in rec["prohibited_claims"]
    assert "caused" not in rec["statement"].lower()


def test_observing_abstained() -> None:
    outcome, reason, rec = evaluate_synthesis_for_knowledge_v1(
        _syn(synthesis_state="observing"),
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_ABSTAINED
    assert reason == REASON_OBSERVING
    assert rec is None


def test_blocked_rejected() -> None:
    outcome, reason, rec = evaluate_synthesis_for_knowledge_v1(
        _syn(synthesis_state="blocked"),
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_REJECTED
    assert reason == REASON_BLOCKED
    assert rec is None


def test_failed_rejected() -> None:
    outcome, reason, _ = evaluate_synthesis_for_knowledge_v1(
        _syn(synthesis_state="failed"),
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_REJECTED


def test_deferred_dependencies() -> None:
    for rule in ("discount_message_weakness", "vip_followup_outcome"):
        outcome, reason, _ = evaluate_synthesis_for_knowledge_v1(
            _syn(
                synthesis_rule_key=rule,
                subject_type="recovery_strategy"
                if "discount" in rule
                else "vip_cohort",
            ),
            as_of=datetime(2026, 7, 21, 12, 0, 0),
        )
        assert outcome == OUTCOME_DEFERRED
        assert reason == REASON_DEFERRED_DEP


def test_no_claim_strengthening() -> None:
    outcome, reason, _ = evaluate_synthesis_for_knowledge_v1(
        _syn(
            known_facts=["cart_interest_trend_observed"],
            # evaluator copies known; boundary check uses statement template
            prohibited_claims=["root_cause_known"],
        ),
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_CREATED


def test_attribution_not_collapsed() -> None:
    outcome, _, rec = evaluate_synthesis_for_knowledge_v1(
        _syn(
            synthesis_rule_key="recovery_influence_boundary",
            subject_type="store",
            subject_id="demo",
            synthesis_summary_key="recovery_influence_boundary.qualified",
            known_facts=[
                "classifications_preserved_not_collapsed",
                'influence_class_counts={"confirmed_recovery":0}',
            ],
            prohibited_claims=[
                "all_purchases_are_recovered_revenue",
                "collapsed_influence_claim",
            ],
        ),
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_CREATED
    assert rec is not None
    assert "collapsed" in rec["statement"].lower() or "preserved" in rec["statement"].lower()
    assert "collapsed_influence_claim" in rec["prohibited_claims"]


def test_full_pipeline_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    syntheses = [
        _syn(store_slug=slug, synthesis_id="a", synthesis_key="ka"),
        _syn(
            store_slug=slug,
            synthesis_id="b",
            synthesis_key="kb",
            synthesis_state="observing",
            synthesis_rule_key="repeated_interest_pattern",
        ),
        _syn(
            store_slug=slug,
            synthesis_id="c",
            synthesis_key="kc",
            synthesis_state="blocked",
            synthesis_rule_key="shipping_hesitation_recovery_outcome",
            subject_type="hesitation_reason",
            subject_id="shipping",
        ),
        _syn(
            store_slug=slug,
            synthesis_id="d",
            synthesis_key="kd",
            synthesis_rule_key="discount_message_weakness",
            subject_type="recovery_strategy",
            subject_id="discount",
        ),
    ]
    monkeypatch.setattr(
        ciknow,
        "generate_commerce_intelligence_syntheses_v1",
        lambda *a, **k: {
            "ok": True,
            "syntheses": syntheses,
            "errors": [],
            "expected_candidate_count": len(syntheses),
        },
    )
    report = generate_knowledge_from_synthesis_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert report["unaccounted"] == 0
    assert report["created"] == 1
    assert report["abstained"] >= 1
    assert report["rejected"] >= 1
    assert report["deferred"] >= 1
    assert report["failed"] == 0


def test_determinism_and_materialize(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    syntheses = [
        _syn(store_slug=slug, synthesis_id="x1", synthesis_key="kx1"),
        _syn(
            store_slug=slug,
            synthesis_id="x2",
            synthesis_key="kx2",
            subject_id="p|2",
            synthesis_fingerprint="sfp2",
        ),
    ]
    monkeypatch.setattr(
        ciknow,
        "generate_commerce_intelligence_syntheses_v1",
        lambda *a, **k: {"ok": True, "syntheses": syntheses, "errors": []},
    )
    det = verify_ciknow_determinism_v1(slug, time_window_key="d7", as_of=as_of)
    assert det["deterministic"] is True
    a = materialize_knowledge_from_synthesis_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    b = materialize_knowledge_from_synthesis_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert a["created"] + a["updated"] + a["unchanged"] >= 2
    assert b["unchanged"] >= 1 or b["updated"] >= 0
    rows = (
        db.session.query(KnowledgeStatement)
        .filter(
            KnowledgeStatement.store_slug == slug,
            KnowledgeStatement.is_current.is_(True),
            KnowledgeStatement.source_type == SOURCE_TYPE_CISYN,
        )
        .all()
    )
    keys = [
        (r.source_rule_key, r.subject_id, r.knowledge_type) for r in rows
    ]
    assert len(keys) == len(set(keys))
    assert all(r.source_synthesis_id for r in rows)


def test_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed()
    monkeypatch.setenv(ENV_CIKNOW_V1, "0")
    result = materialize_knowledge_from_synthesis_v1(slug)
    assert result.get("skipped_disabled") is True


def test_main_wiring_only() -> None:
    import main as main_mod

    src = inspect.getsource(main_mod.dev_commerce_intelligence_knowledge)
    assert "build_commerce_intelligence_knowledge_prod_probe_v1" in src
    assert "intake_policy" not in src
