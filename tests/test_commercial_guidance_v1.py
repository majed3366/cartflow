# -*- coding: utf-8 -*-
"""Commercial Guidance Foundation V1 — Guidance Eligibility only."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import CommercialGuidanceRecord, ProductSignalEvent, Store
from schema_commercial_guidance_v1 import (
    reset_commercial_guidance_schema_guard_for_tests,
)
from schema_product_signal_events_v1 import (
    reset_product_signal_events_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data import commercial_guidance_foundation_v1 as cgf_mod
from services.product_data.commercial_guidance_flag_v1 import (
    ENV_COMMERCIAL_GUIDANCE_V1,
)
from services.product_data.commercial_guidance_foundation_v1 import (
    evaluate_subject_guidance_v1,
    generate_commercial_guidance_v1,
    materialize_commercial_guidance_v1,
    verify_commercial_guidance_determinism_v1,
)
from services.product_data.commercial_guidance_registry_v1 import (
    GUIDANCE_REGISTRY_V1,
    get_registry_entry_v1,
    registry_is_valid_v1,
)
from services.product_data.commercial_guidance_types_v1 import (
    GUIDANCE_KEYS,
    KEY_INVESTIGATE_CONVERSION,
    KEY_MONITOR_NEW,
    KEY_NO_GUIDANCE,
    STATUS_ABSTAINED,
    STATUS_ACTIVE,
    STATUS_SUPERSEDED,
)
from services.product_data.guidance_eligibility_flag_v1 import (
    ENV_GUIDANCE_ELIGIBILITY_V1,
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
    for model in (CommercialGuidanceRecord, ProductSignalEvent, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_commercial_guidance_schema_guard_for_tests()
    reset_product_signal_events_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_COMMERCIAL_GUIDANCE_V1, "1")
    monkeypatch.setenv(ENV_GUIDANCE_ELIGIBILITY_V1, "1")
    monkeypatch.setenv(ENV_KNOWLEDGE_FOUNDATION_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"cgf-{uuid.uuid4().hex[:8]}"
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


def _add_signal(
    *,
    store: str,
    identity: str,
    observed_at: datetime,
    dedup: str,
) -> None:
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


def _eligibility(
    *,
    status: str = "eligible",
    subject_type: str = "store",
    subject_id: str = "demo",
    ctx: list | None = None,
    blocking: list | None = None,
) -> dict:
    context = ctx or []
    kids = sorted(str(c.get("knowledge_id") or "") for c in context if c.get("knowledge_id"))
    return {
        "eligibility_id": "elig-test-1",
        "store_slug": "demo",
        "subject_type": subject_type,
        "subject_id": subject_id,
        "eligibility_status": status,
        "eligibility_reason": "test",
        "blocking_conditions": blocking or [],
        "knowledge_ids": kids,
        "knowledge_context": context,
        "fingerprint": "fp-elig",
        "contract_version": "gef_v1_guidance_context",
    }


def test_registry_valid_and_complete() -> None:
    ok, errors = registry_is_valid_v1()
    assert ok is True
    assert errors == []
    assert KEY_NO_GUIDANCE in GUIDANCE_REGISTRY_V1
    assert GUIDANCE_KEYS == frozenset(GUIDANCE_REGISTRY_V1.keys())


def test_consumes_eligibility_only_no_lower_imports() -> None:
    src = inspect.getsource(cgf_mod)
    assert "evaluate_guidance_eligibility_v1" in src
    for banned in (
        "generate_knowledge_v1",
        "evaluate_evidence_confidence",
        "assemble_product_evidence",
        "product_metrics_foundation",
        "product_trends_foundation",
        "product_signal",
    ):
        assert banned not in src


def test_ineligible_abstains() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    rec = evaluate_subject_guidance_v1(
        eligibility=_eligibility(status="insufficient_knowledge"),
        as_of=as_of,
        generated_at=as_of,
    )
    assert rec["guidance_key"] == KEY_NO_GUIDANCE
    assert rec["guidance_status"] == STATUS_ABSTAINED
    assert "insufficient_knowledge" in rec["rationale_code"]
    assert rec["unknown_facts"]
    assert rec["prohibited_claims"]


def test_expired_and_conflict_abstain() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    for status in ("expired_knowledge", "conflicting_knowledge"):
        rec = evaluate_subject_guidance_v1(
            eligibility=_eligibility(status=status),
            as_of=as_of,
            generated_at=as_of,
        )
        assert rec["guidance_key"] == KEY_NO_GUIDANCE
        assert rec["guidance_status"] == STATUS_ABSTAINED


def test_missing_context_abstains() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    rec = evaluate_subject_guidance_v1(
        eligibility=_eligibility(status="eligible", ctx=[]),
        as_of=as_of,
        generated_at=as_of,
    )
    assert rec["guidance_key"] == KEY_NO_GUIDANCE
    assert "missing_knowledge_context" in rec["rationale_code"]


def test_investigate_conversion_from_intent_and_purchase_gap() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    ctx = [
        {
            "knowledge_id": "k1",
            "knowledge_type": "evidence_quality",
            "statement": "Evidence quality is very_high.",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
            "assembly_window": "d7",
            "metric_key": "",
            "trend_direction": "",
            "gap_key": "",
        },
        {
            "knowledge_id": "k2",
            "knowledge_type": "metric_trend_observation",
            "statement": "Cart additions have newly appeared during the last 7 days.",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
            "assembly_window": "d7",
            "metric_key": "cart_added_count",
            "trend_direction": "newly_appeared",
            "gap_key": "",
        },
        {
            "knowledge_id": "k3",
            "knowledge_type": "evidence_gap",
            "statement": "Evidence does not include purchase_count.",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
            "assembly_window": "d7",
            "metric_key": "",
            "trend_direction": "",
            "gap_key": "purchase_count",
        },
    ]
    rec = evaluate_subject_guidance_v1(
        eligibility=_eligibility(ctx=ctx),
        as_of=as_of,
        generated_at=as_of,
    )
    assert rec["guidance_key"] == KEY_INVESTIGATE_CONVERSION
    assert rec["guidance_status"] == STATUS_ACTIVE
    assert any("Cart additions" in f for f in rec["known_facts"])
    blob = " ".join(rec["prohibited_claims"]).lower()
    assert "root cause" in blob


def test_monitor_new_pattern_without_purchase_gap() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    ctx = [
        {
            "knowledge_id": "k1",
            "knowledge_type": "evidence_quality",
            "statement": "Evidence quality is very_high.",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
            "assembly_window": "d7",
            "metric_key": "",
            "trend_direction": "",
            "gap_key": "",
        },
        {
            "knowledge_id": "k2",
            "knowledge_type": "metric_trend_observation",
            "statement": "Cart additions have newly appeared during the last 7 days.",
            "confidence_level": "very_high",
            "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
            "assembly_window": "d7",
            "metric_key": "cart_added_count",
            "trend_direction": "newly_appeared",
            "gap_key": "",
        },
    ]
    rec = evaluate_subject_guidance_v1(
        eligibility=_eligibility(ctx=ctx),
        as_of=as_of,
        generated_at=as_of,
    )
    assert rec["guidance_key"] == KEY_MONITOR_NEW


def test_no_root_cause_or_action_language() -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commercial_guidance_v1("unused-empty", as_of=as_of)
    # empty store still may fail eligibility; force subject path
    rec = evaluate_subject_guidance_v1(
        eligibility=_eligibility(
            ctx=[
                {
                    "knowledge_id": "k1",
                    "knowledge_type": "evidence_quality",
                    "statement": "Evidence quality is high.",
                    "confidence_level": "high",
                    "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
                    "assembly_window": "d7",
                    "metric_key": "",
                    "trend_direction": "",
                    "gap_key": "",
                },
                {
                    "knowledge_id": "k2",
                    "knowledge_type": "metric_trend_observation",
                    "statement": "Cart additions are stable during the last 7 days.",
                    "confidence_level": "high",
                    "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
                    "assembly_window": "d7",
                    "metric_key": "cart_added_count",
                    "trend_direction": "stable",
                    "gap_key": "",
                },
            ]
        ),
        as_of=as_of,
        generated_at=as_of,
    )
    # Prohibited list may name blocked claims; guidance meaning must not assert them.
    meaning = " ".join(
        [
            rec["guidance_key"],
            rec["rationale_summary"],
            " ".join(rec["known_facts"]),
        ]
    ).lower()
    for forbidden in (
        "shipping cost is causing",
        "increase advertising spend",
        "reduce the product price",
        "offer a discount",
        "checkout is broken",
        "customers dislike the price",
    ):
        assert forbidden not in meaning
    assert any("root cause" in p.lower() for p in rec["prohibited_claims"])
    assert report is not None


def test_live_path_determinism_and_materialize() -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|cgf_a",
        observed_at=as_of - timedelta(days=2),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )
    det = verify_commercial_guidance_determinism_v1(store, as_of=as_of)
    assert det["ok"] is True
    assert det["deterministic"] is True
    m1 = materialize_commercial_guidance_v1(store, as_of=as_of)
    m2 = materialize_commercial_guidance_v1(store, as_of=as_of)
    assert m1["ok"] and m2["ok"]
    assert m1["canonical_fingerprint"] == m2["canonical_fingerprint"]
    n = (
        db.session.query(CommercialGuidanceRecord)
        .filter(
            CommercialGuidanceRecord.store_slug == store,
            CommercialGuidanceRecord.is_current.is_(True),
        )
        .count()
    )
    assert n >= 1
    report = generate_commercial_guidance_v1(store, as_of=as_of)
    assert report["inputs"]["guidance_eligibility_only"] is True
    store_recs = [r for r in report["records"] if r["subject_type"] == "store"]
    assert store_recs
    assert store_recs[0]["guidance_key"] in GUIDANCE_KEYS
    assert store_recs[0]["eligibility_id"]
    assert store_recs[0]["known_facts"]
    assert store_recs[0]["unknown_facts"]
    assert store_recs[0]["prohibited_claims"]


def test_flag_off_skips_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    monkeypatch.setenv(ENV_COMMERCIAL_GUIDANCE_V1, "0")
    out = materialize_commercial_guidance_v1(store)
    assert out["ok"] is False
    assert out.get("skipped_disabled") is True


def test_unsupported_key_cannot_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    _add_signal(
        store=store,
        identity="c|cgf_b",
        observed_at=as_of - timedelta(days=1),
        dedup=f"d-{uuid.uuid4().hex[:10]}",
    )

    def _bad_generate(*_a, **_k):
        return {
            "ok": True,
            "as_of": as_of.isoformat(sep=" "),
            "canonical_fingerprint": "x",
            "guidance_count": 1,
            "records": [
                {
                    "guidance_id": "badid",
                    "store_slug": store,
                    "subject_type": "store",
                    "subject_id": store,
                    "guidance_key": "not_a_real_key",
                    "guidance_scope": "commercial_v1",
                    "eligibility_id": "e",
                    "eligibility_status": "eligible",
                    "knowledge_reference_ids": [],
                    "source_contract_version": "gef_v1_guidance_context",
                    "rule_version": "x",
                    "guidance_status": STATUS_ACTIVE,
                    "rationale_code": "x",
                    "rationale_summary": "x",
                    "known_facts": [],
                    "unknown_facts": [],
                    "prohibited_claims": [],
                    "valid_until": (as_of + timedelta(days=7)).isoformat(sep=" "),
                    "input_fingerprint": "i",
                    "guidance_fingerprint": "g",
                }
            ],
        }

    monkeypatch.setattr(cgf_mod, "generate_commercial_guidance_v1", _bad_generate)
    out = materialize_commercial_guidance_v1(store, as_of=as_of)
    assert out["ok"] is False
    assert any("unsupported_guidance_type" in e for e in out["errors"])


def test_registry_entry_lookup() -> None:
    assert get_registry_entry_v1(KEY_INVESTIGATE_CONVERSION) is not None
    assert get_registry_entry_v1("does_not_exist") is None


def test_no_provider_or_ai_dependency() -> None:
    low = inspect.getsource(cgf_mod).lower()
    for banned in ("openai", "anthropic", "langchain", "zid_api", "salla_api", "shopify"):
        assert banned not in low
