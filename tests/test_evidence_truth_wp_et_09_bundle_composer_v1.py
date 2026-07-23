# -*- coding: utf-8 -*-
"""WP-ET-09 — Evidence Bundle Composer shadow foundation (C-16)."""
from __future__ import annotations

from pathlib import Path

from services.evidence_truth import (
    FLAG_BUNDLE_COMPOSER_CONSUME,
    FLAG_BUNDLE_COMPOSER_SHADOW,
    FLAG_VISITOR_BUNDLE_FIELDS,
    bundle_composer_shadow_enabled,
    bundle_consume_wired_v1,
    compose_evidence_bundle_v1,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
    get_evidence_bundle_store_v1,
    get_evidence_truth_store_v1,
    list_consumer_eligibility_v1,
    maybe_compose_evidence_bundle_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_bundle_store_v1,
    reset_evidence_truth_store_v1,
    run_gate_a_partial_observation_evidence_v1,
    run_gate_b_visitor_truth_v1,
    run_gate_c_partial_bundle_composer_v1,
    shadow_dual_write_evidence_v1,
    validate_evidence_bundle_constitutional_v1,
)
from services.evidence_truth.bundle_composition_rules_v1 import (
    assert_no_raw_authority_imports_in_module_source_v1,
)
from services.evidence_truth.kernel_v1 import EvidenceValidationError
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
)


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()


def test_bundle_flags_default_off():
    assert evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_SHADOW, environ={}) is False
    assert evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_CONSUME, environ={}) is False
    assert evidence_truth_flag_enabled(FLAG_VISITOR_BUNDLE_FIELDS, environ={}) is False
    assert bundle_composer_shadow_enabled(environ={}) is False
    assert bundle_consume_wired_v1(environ={}) is False
    snap = evidence_truth_flags_snapshot(environ={})
    assert snap[FLAG_BUNDLE_COMPOSER_SHADOW] is False
    assert snap[FLAG_BUNDLE_COMPOSER_CONSUME] is False


def test_maybe_compose_skips_when_flag_off():
    out = maybe_compose_evidence_bundle_v1(store_slug="demo")
    assert out["skipped"] is True
    assert out["reason"] == "flag_off"
    assert get_evidence_bundle_store_v1().count() == 0


def test_compose_fail_closed_without_evidence():
    try:
        compose_evidence_bundle_v1(store_slug="empty", persist=False, environ={})
        assert False, "expected EvidenceValidationError"
    except EvidenceValidationError as exc:
        assert exc.reason_code == "missing_sources"


def test_compose_from_evidence_preserves_trace_and_no_invention():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:b1",
            "session_id": "s1",
            "purchase_completed": True,
        },
        force=True,
    )
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload={
            "store_slug": "demo",
            "message_sid": "SM_b1",
            "status": "sent",
        },
        force=True,
    )
    assert get_evidence_truth_store_v1().count() >= 2

    bundle = compose_evidence_bundle_v1(
        store_slug="demo",
        as_of="2026-07-23T15:00:00+00:00",
        persist=True,
        environ={},
        provenance="synthetic",
    )
    validate_evidence_bundle_constitutional_v1(bundle)
    assert bundle.consumable is False
    assert bundle.composer_owner == "evidence_bundle_composer"
    assert len(bundle.evidence_refs) >= 2
    assert bundle.has_visitor_truth is False
    assert bundle.visitor_total is None
    assert bundle.visitor_bundle_fields_authorized is False
    assert bundle.families["purchase"].present is True
    assert bundle.families["purchase"].evidence_ref is not None
    assert bundle.families["purchase"].evidence_ref.source_observations
    # Missing families are Unavailable — not zero-filled
    assert bundle.families["visitor"].present is False
    assert bundle.families["visitor"].readiness == "unavailable"
    # No guidance invention
    assert "recommendation" not in bundle.families["purchase"].projected_facts
    assert get_evidence_bundle_store_v1().get(bundle.bundle_id) is not None


def test_flag_on_composes_via_maybe():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "flagstore",
            "recovery_key": "flagstore:1",
            "purchase_completed": True,
        },
        force=True,
    )
    out = maybe_compose_evidence_bundle_v1(
        store_slug="flagstore",
        environ={FLAG_BUNDLE_COMPOSER_SHADOW: "1"},
    )
    assert out["ok"] is True
    assert out["consumable"] is False
    assert out["has_visitor_truth"] is False


def test_consumer_eligibility_composer_shadow_not_kl():
    rows = list_consumer_eligibility_v1()
    composer = [r for r in rows if "EvidenceBundleRecordV1" in r.artifact]
    assert composer
    assert "knowledge_layer" in composer[0].prohibited_consumers
    assert "business_findings_engine" in composer[0].prohibited_consumers
    assert "merchant_dashboard_ui" in composer[0].prohibited_consumers
    purchase = [r for r in rows if "purchase_confirmed" in r.artifact]
    assert "evidence_bundle_composer_shadow" in purchase[0].permitted_consumers
    assert "evidence_bundle_composer" in purchase[0].prohibited_consumers


def test_composer_modules_eb7_no_raw_authority():
    et = Path(__file__).resolve().parents[1] / "services" / "evidence_truth"
    for name in (
        "bundle_composer_v1.py",
        "bundle_shadow_compose_v1.py",
        "bundle_model_v1.py",
    ):
        bad = assert_no_raw_authority_imports_in_module_source_v1(
            (et / name).read_text(encoding="utf-8")
        )
        assert not bad, (name, bad)


def test_gate_c_partial_passes():
    report = run_gate_c_partial_bundle_composer_v1()
    assert report["ok"] is True, report
    assert report["consume_authorized"] is False
    assert report["knowledge_connected"] is False
    assert report["findings_connected"] is False


def test_prior_gates_still_green():
    a = run_gate_a_partial_observation_evidence_v1()
    assert a.get("passed") is True or a.get("ok") is True, a
    b = run_gate_b_visitor_truth_v1()
    assert b.get("ok") is True or b.get("passed") is True, b
