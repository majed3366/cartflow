# -*- coding: utf-8 -*-
"""Commercial Guidance Integration V1 (cguide_v1) — Knowledge → Guidance."""
from __future__ import annotations

import inspect
import json
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import CommercialGuidanceRecord, KnowledgeStatement, Store
from schema_commercial_guidance_v1 import (
    reset_commercial_guidance_schema_guard_for_tests,
)
from schema_knowledge_foundation_v1 import (
    reset_knowledge_foundation_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.commercial_guidance_knowledge_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1,
)
from services.product_data.commercial_guidance_knowledge_intake_v1 import (
    evaluate_knowledge_for_guidance_v1,
    generate_commercial_guidance_from_knowledge_v1,
    materialize_commercial_guidance_from_knowledge_v1,
    verify_cguide_determinism_v1,
)
from services.product_data import commercial_guidance_knowledge_intake_v1 as cguide
from services.product_data.commercial_guidance_knowledge_registry_v1 import (
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_knowledge_types_v1 import (
    INPUT_CONTRACT_VERSION_V1,
    KT_EVIDENCE_CONFLICT,
    KT_EVIDENCE_GAP,
    KT_PRODUCT_INTEREST_GAP,
    KT_RECOVERY_INFLUENCE,
    OUTCOME_CONFLICTING,
    OUTCOME_CREATED,
    OUTCOME_EVIDENCE_GAP,
    OUTCOME_EXPIRED,
    OUTCOME_OBSERVE_ONLY,
    OUTCOME_REJECTED,
    REASON_POLICY_MISSING,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset() -> None:
    for model in (CommercialGuidanceRecord, KnowledgeStatement, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_commercial_guidance_schema_guard_for_tests()
    reset_knowledge_foundation_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _iso(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1, "1")
    _reset()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset()


def _seed_store() -> str:
    slug = f"cguide-{uuid.uuid4().hex[:8]}"
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


def _add_knowledge(
    slug: str,
    *,
    ktype: str = KT_PRODUCT_INTEREST_GAP,
    kid: str | None = None,
    subject_type: str = "product",
    subject_id: str = "p|1",
    valid_until: datetime | None = None,
    known: list[str] | None = None,
    unknown: list[str] | None = None,
    prohibited: list[str] | None = None,
    confidence: str = "medium",
) -> KnowledgeStatement:
    now = datetime(2026, 7, 21, 12, 0, 0)
    row = KnowledgeStatement(
        knowledge_id=kid or uuid.uuid4().hex[:32],
        store_slug=slug,
        subject_type=subject_type,
        subject_id=subject_id,
        knowledge_type=ktype,
        statement="Governed knowledge statement.",
        evidence_confidence_id="",
        confidence_level=confidence,
        assembly_window="d7",
        valid_from=now - timedelta(days=1),
        valid_until=valid_until or (now + timedelta(days=7)),
        generated_at=now,
        as_of=now,
        as_of_key="20260721120000",
        knowledge_version="ciknow_v1",
        fingerprint=uuid.uuid4().hex,
        source_type="commerce_intelligence_synthesis",
        source_contract_version="commerce_intelligence_synthesis_v1",
        source_synthesis_id="syn1",
        source_synthesis_key="skey1",
        source_rule_key="product_interest_without_purchase",
        source_rule_version="1",
        source_fingerprint="sfp1",
        known_facts_json=json.dumps(
            known
            or ["cart_interest_trend_observed", "purchase_mappings=0"]
        ),
        unknown_facts_json=json.dumps(
            unknown or ["why_purchase_completion_is_weak"]
        ),
        prohibited_claims_json=json.dumps(
            prohibited or ["root_cause_known", "price_is_the_cause"]
        ),
        is_current=True,
    )
    db.session.add(row)
    db.session.commit()
    return row


def test_registry_and_input_contract() -> None:
    assert registry_is_valid_v1()[0]
    assert INPUT_CONTRACT_VERSION_V1 == "knowledge_statements_current_v1"


def test_consumes_knowledge_only_no_raw_domain() -> None:
    src = inspect.getsource(cguide)
    assert "KnowledgeStatement" in src
    assert "from services.product_data.commerce_intelligence_synthesis" not in src
    assert "evaluate_guidance_eligibility_v1" not in src
    assert "from services.product_data.commercial_guidance_foundation_v1" not in src
    for banned in (
        "ProductHesitationMapping",
        "WhatsAppDeliveryTruth",
        "AbandonedCart",
        "PurchaseEvent",
    ):
        assert banned not in src


def test_qualified_knowledge_creates_guidance() -> None:
    slug = _seed_store()
    kn = _add_knowledge(slug)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    outcome, reason, rec = evaluate_knowledge_for_guidance_v1(
        {
            "knowledge_id": kn.knowledge_id,
            "store_slug": slug,
            "subject_type": kn.subject_type,
            "subject_id": kn.subject_id,
            "knowledge_type": kn.knowledge_type,
            "statement": kn.statement,
            "confidence_level": kn.confidence_level,
            "valid_until": kn.valid_until.isoformat(sep=" "),
            "fingerprint": kn.fingerprint,
            "knowledge_version": kn.knowledge_version,
            "source_type": kn.source_type,
            "source_synthesis_id": kn.source_synthesis_id,
            "source_rule_key": kn.source_rule_key,
            "source_fingerprint": kn.source_fingerprint,
            "known_facts": json.loads(kn.known_facts_json),
            "unknown_facts": json.loads(kn.unknown_facts_json),
            "prohibited_claims": json.loads(kn.prohibited_claims_json),
            "is_current": True,
        },
        as_of=as_of,
    )
    assert outcome == OUTCOME_CREATED
    assert reason == ""
    assert rec is not None
    assert rec["merchant_objective"].startswith("Review why this product")
    assert "lower_the_price" in rec["forbidden_actions"]
    assert rec["confidence_level"] == "medium"
    assert set(json.loads(kn.unknown_facts_json)).issubset(set(rec["unknown_facts"]))
    assert set(json.loads(kn.prohibited_claims_json)).issubset(
        set(rec["prohibited_claims"])
    )


def test_observe_gap_conflict_expired() -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)

    def _eval(row: KnowledgeStatement):
        return evaluate_knowledge_for_guidance_v1(
            {
                "knowledge_id": row.knowledge_id,
                "store_slug": slug,
                "subject_type": row.subject_type,
                "subject_id": row.subject_id,
                "knowledge_type": row.knowledge_type,
                "statement": row.statement,
                "confidence_level": row.confidence_level,
                "valid_until": row.valid_until.isoformat(sep=" "),
                "fingerprint": row.fingerprint,
                "knowledge_version": row.knowledge_version,
                "source_type": row.source_type,
                "source_synthesis_id": row.source_synthesis_id,
                "source_rule_key": row.source_rule_key,
                "source_fingerprint": row.source_fingerprint,
                "known_facts": json.loads(row.known_facts_json),
                "unknown_facts": json.loads(row.unknown_facts_json),
                "prohibited_claims": json.loads(row.prohibited_claims_json),
                "is_current": True,
            },
            as_of=as_of,
        )

    o1, _, r1 = _eval(
        _add_knowledge(
            slug, ktype=KT_RECOVERY_INFLUENCE, subject_type="store", subject_id=slug
        )
    )
    assert o1 == OUTCOME_OBSERVE_ONLY
    assert r1 is not None

    o2, _, r2 = _eval(
        _add_knowledge(
            slug, ktype=KT_EVIDENCE_GAP, subject_type="store", subject_id=slug + "-gap"
        )
    )
    assert o2 == OUTCOME_EVIDENCE_GAP
    assert r2 is not None

    o3, _, r3 = _eval(
        _add_knowledge(
            slug,
            ktype=KT_EVIDENCE_CONFLICT,
            subject_type="store",
            subject_id=slug + "-cf",
        )
    )
    assert o3 == OUTCOME_CONFLICTING
    assert r3 is not None

    expired = _add_knowledge(
        slug,
        subject_id="p|exp",
        valid_until=as_of - timedelta(hours=1),
    )
    o4, reason, r4 = _eval(expired)
    assert o4 == OUTCOME_EXPIRED
    assert r4 is None
    assert reason


def test_missing_policy_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    kn = _add_knowledge(slug, ktype="totally_unknown_type_x")
    # Force type into evaluate path via dict override.
    outcome, reason, rec = evaluate_knowledge_for_guidance_v1(
        {
            "knowledge_id": kn.knowledge_id,
            "store_slug": slug,
            "subject_type": "product",
            "subject_id": "p|x",
            "knowledge_type": "totally_unknown_type_x",
            "statement": "x",
            "confidence_level": "low",
            "valid_until": (datetime(2026, 7, 28)).isoformat(sep=" "),
            "fingerprint": "fp",
            "knowledge_version": "ciknow_v1",
            "known_facts": [],
            "unknown_facts": [],
            "prohibited_claims": [],
            "is_current": True,
        },
        as_of=datetime(2026, 7, 21, 12, 0, 0),
    )
    assert outcome == OUTCOME_REJECTED
    assert rec is None
    assert reason in {
        REASON_POLICY_MISSING,
        "knowledge_type_unsupported",
    }


def test_no_causal_inflation_or_stronger_claims() -> None:
    slug = _seed_store()
    kn = _add_knowledge(slug)
    report = generate_commercial_guidance_from_knowledge_v1(
        slug, as_of=datetime(2026, 7, 21, 12, 0, 0)
    )
    assert report["ok"]
    assert report["claim_boundary_ok"] is True
    for rec in report["records"]:
        blob = (
            rec["merchant_objective"]
            + " "
            + " ".join(rec["eligible_actions"])
        ).lower()
        assert "lower the price" not in blob
        assert "caused" not in blob
        assert set(json.loads(kn.prohibited_claims_json)).issubset(
            set(rec["prohibited_claims"])
        )


def test_deterministic_identity_and_idempotent_rerun() -> None:
    slug = _seed_store()
    _add_knowledge(slug)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    det = verify_cguide_determinism_v1(slug, as_of=as_of)
    assert det["deterministic"] is True
    m1 = materialize_commercial_guidance_from_knowledge_v1(slug, as_of=as_of)
    assert m1["ok"]
    assert m1["created"] >= 1
    m2 = materialize_commercial_guidance_from_knowledge_v1(slug, as_of=as_of)
    assert m2["ok"]
    assert m2["unchanged"] >= 1
    assert m2["created"] == 0
    currents = (
        db.session.query(CommercialGuidanceRecord)
        .filter(
            CommercialGuidanceRecord.store_slug == slug,
            CommercialGuidanceRecord.is_current.is_(True),
            CommercialGuidanceRecord.generation_version == "cguide_v1_gen",
        )
        .all()
    )
    keys = {(c.subject_type, c.subject_id, c.guidance_scope) for c in currents}
    assert len(keys) == len(currents)


def test_full_accounting_and_failure_isolation() -> None:
    slug = _seed_store()
    _add_knowledge(slug, subject_id="p|1")
    _add_knowledge(slug, subject_id="p|2")
    _add_knowledge(
        slug,
        ktype=KT_EVIDENCE_GAP,
        subject_type="store",
        subject_id=slug,
        known=[],
        unknown=["need_more_evidence"],
        prohibited=["invent_conclusion"],
    )
    report = generate_commercial_guidance_from_knowledge_v1(
        slug, as_of=datetime(2026, 7, 21, 12, 0, 0)
    )
    total = (
        report["created"]
        + report["updated"]
        + report["unchanged"]
        + report["observe_only"]
        + report["evidence_gap"]
        + report["conflicting"]
        + report["abstained"]
        + report["rejected"]
        + report["expired"]
        + report["failed"]
    )
    assert report["unaccounted"] == 0
    assert total == report["eligible_knowledge_count"] + report[
        "ineligible_knowledge_count"
    ]


def test_store_isolation_and_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    a = _seed_store()
    b = _seed_store()
    _add_knowledge(a, subject_id="p|a")
    _add_knowledge(b, subject_id="p|b")
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    mat_a = materialize_commercial_guidance_from_knowledge_v1(a, as_of=as_of)
    assert mat_a["ok"]
    other = (
        db.session.query(CommercialGuidanceRecord)
        .filter(CommercialGuidanceRecord.store_slug == b)
        .count()
    )
    assert other == 0

    monkeypatch.setenv(ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1, "0")
    skipped = materialize_commercial_guidance_from_knowledge_v1(a, as_of=as_of)
    assert skipped.get("skipped_disabled") is True


def test_main_wiring_only_import() -> None:
    import main as app_main

    src = inspect.getsource(app_main.dev_commercial_guidance)
    assert "build_commercial_guidance_knowledge_prod_probe_v1" in src
    assert "generate_commercial_guidance_from_knowledge_v1" not in src
