# -*- coding: utf-8 -*-
"""CISYN V1 closure validation — blocked reasons, determinism, boundaries."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import CommerceIntelligenceSynthesis, Store
from schema_commerce_intelligence_synthesis_v1 import (
    reset_commerce_intelligence_synthesis_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data.commerce_intelligence_synthesis_blocked_v1 import (
    CLASS_DEFERRED,
    CLASS_EXPECTED,
    REASON_COMPARISON_COHORT_UNAVAILABLE,
    REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE,
    REASON_SUBJECT_IDENTITY_UNRESOLVED,
    REASON_TEMPORAL_ALIGNMENT_FAILED,
    REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION,
    REASON_UPSTREAM_TRUTH_INCOMPLETE,
    classify_blocked_candidate_v1,
)
from services.product_data.commerce_intelligence_synthesis_flag_v1 import (
    ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1,
)
from services.product_data import commerce_intelligence_synthesis_foundation_v1 as cisyn
from services.product_data.commerce_intelligence_synthesis_foundation_v1 import (
    generate_commerce_intelligence_syntheses_v1,
    materialize_commerce_intelligence_syntheses_v1,
)
from services.product_data.commerce_intelligence_synthesis_sources_v1 import (
    load_synthesis_sources_v1,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    STATE_BLOCKED,
    STATE_FAILED,
    STATE_QUALIFIED,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _reset_tables() -> None:
    for model in (CommerceIntelligenceSynthesis, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_commerce_intelligence_synthesis_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str | None = None) -> str:
    slug = slug or f"cisyn-c-{uuid.uuid4().hex[:8]}"
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


def _base_sources(
    slug: str,
    *,
    available: list[str],
    statements: list[dict] | None = None,
    shipping_rows: list | None = None,
    signals: list | None = None,
) -> dict:
    anchor = datetime(2026, 7, 21, 12, 0, 0)
    return {
        "ok": True,
        "store_slug": slug,
        "time_window_key": "d7",
        "window_start": (anchor - timedelta(days=7)).isoformat(sep=" "),
        "window_end": anchor.isoformat(sep=" "),
        "as_of": anchor.isoformat(sep=" "),
        "knowledge_window": "d7",
        "sources": {
            "knowledge": {
                "ok": "knowledge" in available,
                "contract_key": "generate_knowledge_v1",
                "statements": statements or [],
                "statement_count": len(statements or []),
                "canonical_fingerprint": "kf",
            },
            "product_hesitation": {
                "ok": "product_hesitation" in available,
                "contract_key": "product_hesitation_mapping_read_v1",
                "store_mapping_count": len(shipping_rows or []),
                "shipping_hesitation_rows": shipping_rows or [],
                "shipping_hesitation_count": len(shipping_rows or []),
            },
            "product_purchase": {
                "ok": "product_purchase" in available,
                "contract_key": "product_purchase_mapping_read_v1",
                "store_purchase_mapping_count": 0,
            },
            "commerce_signals": {
                "ok": "commerce_signals" in available,
                "contract_key": "load_store_commerce_signals_v1",
                "signals": signals or [],
                "signal_count": len(signals or []),
                "enabled": True,
            },
        },
        "rejected_inputs": [],
        "unsupported_input_reasons": {},
        "available_source_domains": list(available),
        "missing_source_domains": [
            d
            for d in (
                "knowledge",
                "product_hesitation",
                "product_purchase",
                "commerce_signals",
            )
            if d not in available
        ],
        "errors": [],
    }


def test_missing_required_source_blocked_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, available=["knowledge"]),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    shipping = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "shipping_hesitation_recovery_outcome"
    ]
    assert shipping and shipping[0]["synthesis_state"] == STATE_BLOCKED
    assert shipping[0]["blocked_reason_code"] == REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE
    assert shipping[0]["blocked_classification"] == CLASS_EXPECTED
    assert "product_hesitation" in (shipping[0].get("missing_source_domains") or [])
    assert shipping[0]["synthesis_state"] != STATE_QUALIFIED


def test_temporal_alignment_blocked_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug, available=["knowledge", "commerce_signals", "product_hesitation"]
        ),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    discount = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "discount_message_weakness"
    ]
    assert discount and discount[0]["synthesis_state"] == STATE_BLOCKED
    assert discount[0]["blocked_reason_code"] == REASON_TEMPORAL_ALIGNMENT_FAILED
    assert discount[0]["temporal_alignment_status"] == "window_not_allowed_for_rule"


def test_unsupported_source_version_blocked_reason() -> None:
    classified = classify_blocked_candidate_v1(
        reason_code=REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION,
        synthesis_rule_key="shipping_hesitation_recovery_outcome",
        missing_source_domains=[],
    )
    assert classified["is_defect"] is True
    assert classified["approval"] == "NOT_APPROVABLE_UNTIL_FIXED"


def test_unresolved_subject_identity_blocked_reason() -> None:
    classified = classify_blocked_candidate_v1(
        reason_code=REASON_SUBJECT_IDENTITY_UNRESOLVED,
        synthesis_rule_key="product_interest_without_purchase",
    )
    assert classified["is_defect"] is True


def test_mapping_missing_with_evidence_flagged_defect() -> None:
    classified = classify_blocked_candidate_v1(
        reason_code=REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE,
        synthesis_rule_key="shipping_hesitation_recovery_outcome",
        missing_source_domains=["product_hesitation"],
        evidence_exists_unmapped=True,
    )
    assert classified["is_defect"] is True


def test_runtime_exception_is_failed_not_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, available=["knowledge"]),
    )

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    patched = dict(cisyn._RULE_EVALUATORS)
    patched["high_traffic_weak_conversion"] = boom
    monkeypatch.setattr(cisyn, "_RULE_EVALUATORS", patched)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    failed = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "high_traffic_weak_conversion"
    ]
    assert failed[0]["synthesis_state"] == STATE_FAILED
    assert failed[0]["synthesis_state"] != STATE_BLOCKED
    others = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] != "high_traffic_weak_conversion"
    ]
    assert others and all(s["synthesis_state"] != STATE_FAILED for s in others)


def test_blocked_fully_accounted_with_source_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, available=["knowledge"]),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert report["candidate_count"] == report["expected_candidate_count"]
    blocked = [s for s in report["syntheses"] if s["synthesis_state"] == STATE_BLOCKED]
    assert blocked
    for b in blocked:
        assert b.get("blocked_reason_code")
        assert b.get("missing_source_domains") is not None
        assert b.get("prohibited_claims")


def test_resolving_dependency_unblocks_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)

    def sources_missing(*_a, **_k):
        return _base_sources(slug, available=["knowledge"])

    monkeypatch.setattr(cisyn, "load_synthesis_sources_v1", sources_missing)
    blocked_report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    shipping_blocked = [
        s
        for s in blocked_report["syntheses"]
        if s["synthesis_rule_key"] == "shipping_hesitation_recovery_outcome"
    ][0]
    assert shipping_blocked["synthesis_state"] == STATE_BLOCKED

    rows = [
        {
            "id": 1,
            "reason": "shipping_cost",
            "stable_identity_key": "p|1",
            "captured_at": as_of - timedelta(days=1),
        }
        for _ in range(3)
    ]

    def sources_present(*_a, **_k):
        return _base_sources(
            slug,
            available=["knowledge", "product_hesitation", "commerce_signals"],
            shipping_rows=rows,
            signals=[{"signal_type": "recovery_started"}],
        )

    monkeypatch.setattr(cisyn, "load_synthesis_sources_v1", sources_present)
    next_report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    shipping_next = [
        s
        for s in next_report["syntheses"]
        if s["synthesis_rule_key"] == "shipping_hesitation_recovery_outcome"
    ][0]
    assert shipping_next["synthesis_state"] != STATE_BLOCKED
    assert shipping_next["synthesis_state"] in {"qualified", "observing"}


def test_blocked_rerun_no_duplicate_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, available=["knowledge"]),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    rows = (
        db.session.query(CommerceIntelligenceSynthesis)
        .filter(
            CommerceIntelligenceSynthesis.store_slug == slug,
            CommerceIntelligenceSynthesis.is_current.is_(True),
        )
        .all()
    )
    keys = [r.synthesis_key for r in rows]
    assert len(keys) == len(set(keys))


def test_supersession_when_block_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, available=["knowledge"]),
    )
    materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    blocked_key = (
        db.session.query(CommerceIntelligenceSynthesis)
        .filter(
            CommerceIntelligenceSynthesis.store_slug == slug,
            CommerceIntelligenceSynthesis.synthesis_rule_key
            == "shipping_hesitation_recovery_outcome",
            CommerceIntelligenceSynthesis.is_current.is_(True),
        )
        .one()
        .synthesis_key
    )
    rows = [
        {
            "id": i,
            "reason": "shipping",
            "stable_identity_key": "p|x",
            "captured_at": as_of - timedelta(hours=i + 1),
        }
        for i in range(3)
    ]
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug,
            available=["knowledge", "product_hesitation", "commerce_signals"],
            shipping_rows=rows,
            signals=[{"signal_type": "recovery_started"}],
        ),
    )
    materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    currents = (
        db.session.query(CommerceIntelligenceSynthesis)
        .filter(
            CommerceIntelligenceSynthesis.store_slug == slug,
            CommerceIntelligenceSynthesis.synthesis_key == blocked_key,
            CommerceIntelligenceSynthesis.is_current.is_(True),
        )
        .all()
    )
    assert len(currents) == 1
    assert currents[0].synthesis_state != STATE_BLOCKED


def test_vip_deferred_comparison_cohort(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug, available=["knowledge", "commerce_signals"]
        ),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d14", as_of=as_of
    )
    vip = [
        s for s in report["syntheses"] if s["synthesis_rule_key"] == "vip_followup_outcome"
    ]
    assert vip and vip[0]["synthesis_state"] == STATE_BLOCKED
    assert vip[0]["blocked_reason_code"] == REASON_COMPARISON_COHORT_UNAVAILABLE
    assert vip[0]["blocked_classification"] == CLASS_DEFERRED


def test_discount_deferred_message_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug,
            available=["knowledge", "commerce_signals", "product_hesitation"],
            shipping_rows=[{"id": 1, "reason": "shipping", "captured_at": as_of_safe()}],
        ),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d14", as_of=as_of
    )
    disc = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "discount_message_weakness"
    ]
    assert disc and disc[0]["synthesis_state"] == STATE_BLOCKED
    assert disc[0]["blocked_reason_code"] == REASON_UPSTREAM_TRUTH_INCOMPLETE
    assert disc[0]["blocked_classification"] == CLASS_DEFERRED


def as_of_safe() -> datetime:
    return datetime(2026, 7, 20, 12, 0, 0)


def test_determinism_unchanged_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug,
            available=["knowledge"],
            statements=[
                {
                    "knowledge_id": "k1",
                    "store_slug": slug,
                    "subject_type": "product",
                    "subject_id": "p|1",
                    "knowledge_type": "metric_trend_observation",
                    "statement": "Cart additions increasing",
                    "metric_key": "cart_added_count",
                    "trend_direction": "increasing",
                    "gap_key": "",
                }
            ],
        ),
    )
    monkeypatch.setattr(cisyn, "purchase_count_for_product_v1", lambda *_a, **_k: 0)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    a = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    b = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]
    assert a["candidate_count"] == b["candidate_count"]
    states_a = sorted(
        (s["synthesis_key"], s["synthesis_state"], s["synthesis_fingerprint"])
        for s in a["syntheses"]
    )
    states_b = sorted(
        (s["synthesis_key"], s["synthesis_state"], s["synthesis_fingerprint"])
        for s in b["syntheses"]
    )
    assert states_a == states_b


def test_controlled_input_change_supersedes_affected_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    stmts = [
        {
            "knowledge_id": "k1",
            "store_slug": slug,
            "subject_type": "product",
            "subject_id": "p|1",
            "knowledge_type": "metric_trend_observation",
            "statement": "Cart additions increasing",
            "metric_key": "cart_added_count",
            "trend_direction": "increasing",
            "gap_key": "",
        }
    ]
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug, available=["knowledge"], statements=stmts
        ),
    )
    monkeypatch.setattr(cisyn, "purchase_count_for_product_v1", lambda *_a, **_k: 0)
    first = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    fp_conflict = [
        s["synthesis_fingerprint"]
        for s in first["syntheses"]
        if s["synthesis_rule_key"] == "conflicting_evidence_store"
    ][0]
    stmts2 = stmts + [
        {
            "knowledge_id": "k2",
            "store_slug": slug,
            "subject_type": "product",
            "subject_id": "p|1",
            "knowledge_type": "evidence_conflict_flag",
            "statement": "Conflict",
            "metric_key": "",
            "trend_direction": "",
            "gap_key": "",
        }
    ]
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug, available=["knowledge"], statements=stmts2
        ),
    )
    second = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    conflict2 = [
        s
        for s in second["syntheses"]
        if s["synthesis_rule_key"] == "conflicting_evidence_store"
    ][0]
    assert conflict2["synthesis_fingerprint"] != fp_conflict
    # Unaffected temporal-blocked discount fingerprint identity key stable
    d1 = [
        s["synthesis_key"]
        for s in first["syntheses"]
        if s["synthesis_rule_key"] == "discount_message_weakness"
    ][0]
    d2 = [
        s["synthesis_key"]
        for s in second["syntheses"]
        if s["synthesis_rule_key"] == "discount_message_weakness"
    ][0]
    assert d1 == d2


def test_no_provider_bypass_in_source_adapters() -> None:
    src = inspect.getsource(load_synthesis_sources_v1)
    for banned in (
        "raw_meta",
        "twilio_payload",
        "shopify_order",
        "zid_api",
        "frontend_state",
        "widget_last_beacon",
    ):
        assert banned not in src.lower()


def test_purchase_attribution_not_collapsed(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    signals = [
        {"signal_type": "purchase_confirmed"},
        {"signal_type": "purchase_confirmed", "recovery_classification": "unattributed_purchase"},
        {"signal_type": "purchase_confirmed", "influence_class": "possible_influence"},
    ]
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(
            slug, available=["knowledge", "commerce_signals"], signals=signals
        ),
    )
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    row = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "recovery_influence_boundary"
    ][0]
    assert "collapsed_influence_claim" in row["prohibited_claims"]
    assert "all_purchases_are_recovered_revenue" in row["prohibited_claims"]
    blob = " ".join(row["known_facts"]).lower()
    assert "recovered revenue" not in blob
    assert "influence_class_counts=" in blob


def test_demo_allowlist_blocks_non_demo_writes() -> None:
    from services.product_data.commerce_intelligence_synthesis_prod_probe_v1 import (
        build_commerce_intelligence_synthesis_prod_probe_v1,
    )

    report = build_commerce_intelligence_synthesis_prod_probe_v1(
        "not-demo-store", materialize=False
    )
    assert "store_not_allowlisted" in report["errors"]
    assert report["ok"] is False


def test_main_py_wiring_only() -> None:
    import main as main_mod

    src = inspect.getsource(main_mod.dev_commerce_intelligence_synthesis)
    assert "blocked_reason_code" not in src
    assert "build_commerce_intelligence_synthesis_prod_probe_v1" in src
