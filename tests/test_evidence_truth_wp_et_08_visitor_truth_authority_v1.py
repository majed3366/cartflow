# -*- coding: utf-8 -*-
"""WP-ET-08 — Visitor Truth Authority (C-09) + Gate B."""
from __future__ import annotations

from services.evidence_truth import (
    FLAG_EVIDENCE_DUAL_WRITE,
    FLAG_VISITOR_BUNDLE_FIELDS,
    evidence_dual_write_enabled,
    evidence_truth_flag_enabled,
    get_evidence_truth_store_v1,
    list_consumer_eligibility_v1,
    maybe_publish_visitor_evidence_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_truth_store_v1,
    run_bfsv_exp1_class_check_persist_to_evidence_v1,
    run_gate_a_partial_observation_evidence_v1,
    run_gate_a_partial_raw_observation_v1,
    run_gate_b_visitor_truth_v1,
    shadow_dual_write_evidence_v1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.evidence_governance_v1 import LIFECYCLE_ELIGIBLE
from services.evidence_truth.families_v1 import FAMILY_VISITOR
from services.evidence_truth.flags_v1 import EVIDENCE_TRUTH_FLAGS_V1
from services.evidence_truth.kernel_v1 import READINESS_READY, READINESS_UNAVAILABLE
from services.evidence_truth.observation_types_v1 import RAW_KIND_TRAFFIC
from services.evidence_truth.visitor_proxy_detection_v1 import detect_visitor_proxy_v1


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def test_flag_default_off_visitor_no_write():
    assert evidence_truth_flag_enabled(FLAG_EVIDENCE_DUAL_WRITE, environ={}) is False
    assert evidence_dual_write_enabled(environ={}) is False
    assert FLAG_VISITOR_BUNDLE_FIELDS in EVIDENCE_TRUTH_FLAGS_V1
    assert evidence_truth_flag_enabled(FLAG_VISITOR_BUNDLE_FIELDS, environ={}) is False
    out = maybe_publish_visitor_evidence_v1(
        {"store_slug": "demo", "visitor_id": "v1", "session_id": "s1"}
    )
    assert out is not None
    assert out.get("skipped") is True
    assert get_evidence_truth_store_v1().count() == 0


def test_visitor_evidence_ready_not_consumable_bundle_unauthorized():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "visitor_id": "v-ok",
            "session_id": "s-ok",
            "event": "store_visit",
        },
        source_channel="sdk",
        force=True,
    )
    assert out["ok"] is True
    assert out["consumable"] is False
    assert out["lifecycle_state"] == LIFECYCLE_ELIGIBLE
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    validate_evidence_constitutional_metadata_v1(rec)
    assert rec.owner == "visitor_truth_authority"
    assert rec.canonical_family == FAMILY_VISITOR
    assert rec.readiness == READINESS_READY
    assert rec.envelope.payload.get("cart_proxy") is False
    assert rec.envelope.payload.get("bundle_visitor_fields_authorized") is False
    assert rec.envelope.payload.get("has_visitor_truth_for_bundle") is False


def test_unavailable_when_no_channel():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "session_id": "s-unavail",
            "event": "store_visit",
            "channel_available": False,
            "channel_status": "unavailable",
        },
        source_channel="unknown",
        force=True,
    )
    assert out["ok"] is True
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    assert rec.readiness == READINESS_UNAVAILABLE
    assert rec.envelope.payload.get("presence_claimed") is False
    assert rec.envelope.payload.get("has_visitor_truth_for_bundle") is False


def test_proxy_detection_cart_never_visitor():
    assert (
        detect_visitor_proxy_v1(
            {"event": "cart_abandoned", "session_id": "s1"},
            raw_kind=RAW_KIND_TRAFFIC,
        )
        == "proxy_cart_event"
    )
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "session_id": "s-proxy",
            "event": "cart_abandoned",
        },
        force=True,
    )
    assert out.get("rejected") is True
    assert out.get("reason_code") == "conflict_unresolved"
    assert get_evidence_truth_store_v1().count(family=FAMILY_VISITOR) == 0


def test_gate_b_passes():
    report = run_gate_b_visitor_truth_v1()
    assert report["passed"] is True, report
    assert report["bundle_visitor_fields_authorized"] is False


def test_consumer_eligibility_visitor():
    rows = [r for r in list_consumer_eligibility_v1() if "store_visitor_window" in r.artifact]
    assert rows
    assert "bundle_visitor_fields" in rows[0].prohibited_consumers
    assert "business_findings_engine" in rows[0].prohibited_consumers
    assert "evidence_bundle_composer" in rows[0].prohibited_consumers


def test_prior_packages_still_green():
    assert run_gate_a_partial_raw_observation_v1()["passed"] is True
    assert run_gate_a_partial_observation_evidence_v1()["passed"] is True
    assert run_bfsv_exp1_class_check_persist_to_evidence_v1()["passed"] is True
    assert run_bfsv_exp1_class_check_persist_to_evidence_v1()["bfsv_resumed"] is False


def test_rollback_flag_off():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "visitor_id": "v-rb",
            "session_id": "s-rb",
            "event": "store_visit",
        },
        force=True,
    )
    off = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload={
            "store_slug": "demo",
            "visitor_id": "v-rb2",
            "session_id": "s-rb2",
            "event": "store_visit",
        },
        environ={},
        force=False,
    )
    assert off.get("skipped") is True
