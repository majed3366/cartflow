# -*- coding: utf-8 -*-
"""WP-ET-10 — Knowledge Composer shadow foundation (C-18)."""
from __future__ import annotations

from pathlib import Path

from services.evidence_truth import (
    FLAG_FINDINGS_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    FLAG_KNOWLEDGE_COMPOSER_SHADOW,
    compose_evidence_bundle_v1,
    compose_knowledge_record_v1,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
    get_knowledge_record_store_v1,
    knowledge_composer_shadow_enabled,
    knowledge_consume_wired_v1,
    list_consumer_eligibility_v1,
    maybe_compose_knowledge_record_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_bundle_store_v1,
    reset_evidence_truth_store_v1,
    reset_knowledge_record_store_v1,
    run_gate_c_partial_bundle_composer_v1,
    run_gate_d_partial_knowledge_composer_v1,
    shadow_dual_write_evidence_v1,
    validate_knowledge_record_constitutional_v1,
)
from services.evidence_truth.kernel_v1 import EvidenceValidationError
from services.evidence_truth.knowledge_composition_rules_v1 import (
    assert_no_evidence_write_imports_in_module_source_v1,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KNOWLEDGE_TYPE_READY_FAMILY_SET,
)
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
)


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()


def _seed_bundle(store_slug: str = "demo") -> str:
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": store_slug,
            "recovery_key": f"{store_slug}:k1",
            "session_id": "s1",
            "purchase_completed": True,
        },
        force=True,
    )
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload={
            "store_slug": store_slug,
            "message_sid": "SM_k1",
            "status": "sent",
        },
        force=True,
    )
    bundle = compose_evidence_bundle_v1(
        store_slug=store_slug,
        as_of="2026-07-24T01:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    return bundle.bundle_id


def test_knowledge_flags_default_off():
    assert evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_SHADOW, environ={}) is False
    assert evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_INPUT, environ={}) is False
    assert evidence_truth_flag_enabled(FLAG_FINDINGS_COMPOSER_INPUT, environ={}) is False
    assert knowledge_composer_shadow_enabled(environ={}) is False
    assert knowledge_consume_wired_v1(environ={}) is False
    snap = evidence_truth_flags_snapshot(environ={})
    assert snap[FLAG_KNOWLEDGE_COMPOSER_SHADOW] is False
    assert FLAG_KNOWLEDGE_COMPOSER_SHADOW in snap


def test_maybe_compose_skips_when_flag_off():
    out = maybe_compose_knowledge_record_v1(store_slug="demo")
    assert out["skipped"] is True
    assert out["reason"] == "flag_off"
    assert get_knowledge_record_store_v1().count() == 0


def test_compose_fail_closed_without_bundle():
    try:
        compose_knowledge_record_v1(store_slug="empty", persist=False, environ={})
        assert False, "expected EvidenceValidationError"
    except EvidenceValidationError as exc:
        assert exc.reason_code == "missing_sources"


def test_compose_from_bundle_preserves_trace_no_findings():
    _seed_bundle("demo")
    rec = compose_knowledge_record_v1(
        store_slug="demo",
        knowledge_type=KNOWLEDGE_TYPE_FAMILY_PRESENCE,
        as_of="2026-07-24T01:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    validate_knowledge_record_constitutional_v1(rec)
    assert rec.consumable is False
    assert rec.composer_owner == "knowledge_composer"
    assert len(rec.bundle_refs) >= 1
    assert len(rec.evidence_refs) >= 1
    assert all(c.evidence_ids for c in rec.claims)
    assert "recommendation" not in rec.pattern_summary
    assert "business_meaning" not in rec.pattern_summary
    assert rec.composition_notes.get("findings_connected") is False
    assert rec.composition_notes.get("home_connected") is False
    assert get_knowledge_record_store_v1().get(rec.knowledge_id) is not None


def test_ready_family_set_pattern():
    _seed_bundle("ready")
    rec = compose_knowledge_record_v1(
        store_slug="ready",
        knowledge_type=KNOWLEDGE_TYPE_READY_FAMILY_SET,
        persist=True,
        environ={},
        provenance="synthetic",
    )
    assert rec.knowledge_type == KNOWLEDGE_TYPE_READY_FAMILY_SET
    assert rec.consumable is False
    assert "ready_families" in rec.pattern_summary


def test_flag_on_composes_via_maybe():
    _seed_bundle("flagkn")
    out = maybe_compose_knowledge_record_v1(
        store_slug="flagkn",
        environ={FLAG_KNOWLEDGE_COMPOSER_SHADOW: "1"},
    )
    assert out["ok"] is True
    assert out["consumable"] is False


def test_consumer_eligibility_knowledge_not_home_findings():
    rows = list_consumer_eligibility_v1()
    kn = [r for r in rows if "KnowledgeRecordV1" in r.artifact]
    assert kn
    assert "business_findings_engine" in kn[0].prohibited_consumers
    assert "merchant_dashboard_ui" in kn[0].prohibited_consumers
    assert "home_daily_brief" in kn[0].prohibited_consumers
    bundle = [r for r in rows if "EvidenceBundleRecordV1" in r.artifact]
    assert "knowledge_composer_shadow" in bundle[0].permitted_consumers
    assert "knowledge_layer" in bundle[0].prohibited_consumers


def test_bk4_no_evidence_write_imports():
    et = Path(__file__).resolve().parents[1] / "services" / "evidence_truth"
    for name in ("knowledge_composer_v1.py", "knowledge_shadow_compose_v1.py"):
        bad = assert_no_evidence_write_imports_in_module_source_v1(
            (et / name).read_text(encoding="utf-8")
        )
        assert not bad, (name, bad)


def test_gate_d_partial_passes():
    report = run_gate_d_partial_knowledge_composer_v1()
    assert report["ok"] is True, report
    assert report["consume_authorized"] is False
    assert report["findings_connected"] is False
    assert report["home_connected"] is False


def test_prior_gate_c_still_green():
    report = run_gate_c_partial_bundle_composer_v1()
    assert report["ok"] is True, report
