# -*- coding: utf-8 -*-
"""Commerce Intelligence Synthesis Foundation V1 — governed cross-domain patterns."""
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
from services.product_data.commerce_intelligence_synthesis_flag_v1 import (
    ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1,
)
from services.product_data.commerce_intelligence_synthesis_foundation_v1 import (
    generate_commerce_intelligence_syntheses_v1,
    materialize_commerce_intelligence_syntheses_v1,
    verify_commerce_intelligence_synthesis_determinism_v1,
)
from services.product_data.commerce_intelligence_synthesis_rule_registry_v1 import (
    SYNTHESIS_RULES_V1,
    rule_registry_valid_v1,
)
from services.product_data.commerce_intelligence_synthesis_source_registry_v1 import (
    SOURCE_CONTRACTS_V1,
    source_registry_valid_v1,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    OUTPUT_CONTRACT_VERSION_V1,
    STATE_BLOCKED,
    STATE_FAILED,
    STATE_INSUFFICIENT,
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
    slug = slug or f"cisyn-{uuid.uuid4().hex[:8]}"
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


def _mock_sources(monkeypatch: pytest.MonkeyPatch, *, with_interest: bool = True) -> None:
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    statements = []
    if with_interest:
        statements = [
            {
                "knowledge_id": "k1",
                "store_slug": "demo",
                "subject_type": "product",
                "subject_id": "p|sku1",
                "knowledge_type": "metric_trend_observation",
                "statement": "Cart additions are increasing.",
                "metric_key": "cart_added_count",
                "trend_direction": "increasing",
                "gap_key": "",
                "fingerprint": "f1",
            },
            {
                "knowledge_id": "k2",
                "store_slug": "demo",
                "subject_type": "product",
                "subject_id": "p|sku1",
                "knowledge_type": "evidence_gap",
                "statement": "Evidence does not include purchase_count.",
                "metric_key": "",
                "trend_direction": "",
                "gap_key": "purchase_count",
                "fingerprint": "f2",
            },
            {
                "knowledge_id": "k3",
                "store_slug": "demo",
                "subject_type": "product",
                "subject_id": "p|sku1",
                "knowledge_type": "evidence_conflict_flag",
                "statement": "Conflicting signals were flagged.",
                "metric_key": "",
                "trend_direction": "",
                "gap_key": "",
                "fingerprint": "f3",
            },
        ]

    def fake_load(store_slug, *, time_window_key="d7", as_of=None):
        slug = store_slug
        anchor = as_of or datetime(2026, 7, 21, 12, 0, 0)
        for s in statements:
            s["store_slug"] = slug
        return {
            "ok": True,
            "store_slug": slug,
            "time_window_key": time_window_key,
            "window_start": (anchor - timedelta(days=7)).isoformat(sep=" "),
            "window_end": anchor.isoformat(sep=" "),
            "as_of": anchor.isoformat(sep=" "),
            "knowledge_window": "d7",
            "sources": {
                "knowledge": {
                    "ok": True,
                    "contract_key": "generate_knowledge_v1",
                    "statements": statements,
                    "statement_count": len(statements),
                    "canonical_fingerprint": "kf",
                },
                "product_hesitation": {
                    "ok": True,
                    "contract_key": "product_hesitation_mapping_read_v1",
                    "store_mapping_count": 0,
                    "shipping_hesitation_rows": [],
                    "shipping_hesitation_count": 0,
                },
                "product_purchase": {
                    "ok": True,
                    "contract_key": "product_purchase_mapping_read_v1",
                    "store_purchase_mapping_count": 0,
                },
                "commerce_signals": {
                    "ok": True,
                    "contract_key": "load_store_commerce_signals_v1",
                    "signals": [],
                    "signal_count": 0,
                    "enabled": True,
                },
            },
            "rejected_inputs": [],
            "unsupported_input_reasons": {
                "product_hesitation": "no_mappings",
                "commerce_signals": "no_signals",
            },
            "available_source_domains": ["knowledge"],
            "missing_source_domains": [
                "product_hesitation",
                "product_purchase",
                "commerce_signals",
            ],
            "errors": [],
        }

    monkeypatch.setattr(
        "services.product_data.commerce_intelligence_synthesis_foundation_v1.load_synthesis_sources_v1",
        fake_load,
    )
    monkeypatch.setattr(
        "services.product_data.commerce_intelligence_synthesis_foundation_v1.purchase_count_for_product_v1",
        lambda store, pid: 0,
    )


def test_registries_exist_and_valid() -> None:
    assert source_registry_valid_v1()
    assert rule_registry_valid_v1()
    assert len(SOURCE_CONTRACTS_V1) >= 3
    assert len(SYNTHESIS_RULES_V1) >= 8
    assert OUTPUT_CONTRACT_VERSION_V1 == "commerce_intelligence_synthesis_v1"


def test_deterministic_rerun(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    det = verify_commerce_intelligence_synthesis_determinism_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert det["deterministic"] is True
    a = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    b = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert a["canonical_fingerprint"] == b["canonical_fingerprint"]
    assert a["candidate_count"] == b["candidate_count"]
    assert a["candidate_count"] == a["expected_candidate_count"]


def test_full_candidate_accounting_no_silent_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert report["ok"] is True
    assert report["candidate_count"] >= 8
    states = {s["synthesis_state"] for s in report["syntheses"]}
    assert STATE_INSUFFICIENT in states or STATE_QUALIFIED in states
    # Missing commerce_signals must yield blocked/insufficient, never silent.
    wa = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "whatsapp_return_without_purchase"
    ]
    assert wa
    assert wa[0]["synthesis_state"] in {STATE_BLOCKED, STATE_INSUFFICIENT}


def test_known_unknown_prohibited_and_no_causal_inflation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    interest = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] == "product_interest_without_purchase"
        and s["subject_type"] == "product"
    ]
    assert interest
    row = interest[0]
    assert row["known_facts"]
    assert row["unknown_facts"]
    assert row["prohibited_claims"]
    blob = " ".join(row["known_facts"] + row["unknown_facts"]).lower()
    assert "caused" not in blob
    assert "will increase" not in blob


def test_materialize_idempotent_and_current_unique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    a = materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    b = materialize_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=as_of
    )
    assert a["upserted"] > 0
    assert b["upserted"] > 0
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


def test_flag_off_skips_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    monkeypatch.setenv(ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1, "0")
    result = materialize_commerce_intelligence_syntheses_v1(slug, time_window_key="d7")
    assert result.get("skipped_disabled") is True
    assert result["upserted"] == 0


def test_rule_scoped_and_subject_scoped_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)
    as_of = datetime(2026, 7, 21, 12, 0, 0)
    report = generate_commerce_intelligence_syntheses_v1(
        slug,
        time_window_key="d7",
        as_of=as_of,
        rule_keys=["high_traffic_weak_conversion"],
    )
    assert report["candidate_count"] >= 1
    assert all(
        s["synthesis_rule_key"] == "high_traffic_weak_conversion"
        for s in report["syntheses"]
    )
    scoped = generate_commerce_intelligence_syntheses_v1(
        slug,
        time_window_key="d7",
        as_of=as_of,
        rule_keys=["product_interest_without_purchase"],
        subject_type="product",
        subject_id="p|sku1",
    )
    assert scoped["candidate_count"] >= 1
    assert all(s["subject_id"] == "p|sku1" for s in scoped["syntheses"])


def test_failed_differs_from_insufficient(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = _seed_store()
    _mock_sources(monkeypatch)

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    import services.product_data.commerce_intelligence_synthesis_foundation_v1 as cisyn

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
    assert failed and failed[0]["synthesis_state"] == STATE_FAILED
    # Other rules still accounted (failure isolation)
    assert report["candidate_count"] >= 8
    others = [
        s
        for s in report["syntheses"]
        if s["synthesis_rule_key"] != "high_traffic_weak_conversion"
    ]
    assert others
    assert all(s["synthesis_state"] != STATE_FAILED for s in others)
    # Truthful abstention / blocked remains distinct from technical failure
    assert any(
        s["synthesis_state"] in {STATE_INSUFFICIENT, STATE_BLOCKED, STATE_QUALIFIED}
        for s in others
    )


def test_no_main_py_business_logic_growth() -> None:
    import main as main_mod

    src = inspect.getsource(main_mod.dev_commerce_intelligence_synthesis)
    assert "synthesis_rule_key" not in src
    assert "source_contributions" not in src
    assert "build_commerce_intelligence_synthesis_prod_probe_v1" in src


def test_consumes_canonical_adapters_only() -> None:
    src = inspect.getsource(
        __import__(
            "services.product_data.commerce_intelligence_synthesis_sources_v1",
            fromlist=["load_synthesis_sources_v1"],
        ).load_synthesis_sources_v1
    )
    assert "generate_knowledge_v1" in src
    assert "zid_" not in src.lower() or "zid_store" not in src
    assert "shopify" not in src.lower()
    assert "twilio" not in src.lower()
    assert "meta webhook" not in src.lower()
