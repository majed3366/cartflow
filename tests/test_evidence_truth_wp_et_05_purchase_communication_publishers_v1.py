# -*- coding: utf-8 -*-
"""WP-ET-05 — Purchase + Communication Evidence publishers (C-13 / C-14)."""
from __future__ import annotations

from services.evidence_truth import (
    FLAG_EVIDENCE_DUAL_WRITE,
    evidence_dual_write_enabled,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
    get_evidence_truth_store_v1,
    list_consumer_eligibility_v1,
    maybe_publish_purchase_evidence_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_truth_store_v1,
    run_gate_a_partial_observation_evidence_v1,
    run_gate_a_partial_raw_observation_v1,
    shadow_dual_write_evidence_v1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.communication_evidence_publisher_v1 import (
    classify_message_lifecycle_stage_v1,
    delivery_claimed_v1,
    sent_claimed_v1,
)
from services.evidence_truth.evidence_governance_v1 import (
    LIFECYCLE_CONSUMABLE,
    LIFECYCLE_ELIGIBLE,
)
from services.evidence_truth.families_v1 import FAMILY_COMMUNICATION, FAMILY_PURCHASE
from services.evidence_truth.kernel_v1 import CONFIDENCE_CONFIRMED, READINESS_READY
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
)


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def test_evidence_flag_default_off_no_write():
    assert evidence_truth_flag_enabled(FLAG_EVIDENCE_DUAL_WRITE, environ={}) is False
    assert evidence_dual_write_enabled(environ={}) is False
    out = maybe_publish_purchase_evidence_v1(
        {"store_slug": "demo", "recovery_key": "demo:s1"}
    )
    assert out is not None
    assert out.get("skipped") is True
    assert out.get("reason") == "flag_off"
    assert get_evidence_truth_store_v1().count() == 0


def test_purchase_evidence_constitutional_metadata_and_lifecycle():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:cart-9",
            "session_id": "sess-9",
            "purchase_completed": True,
        },
        force=True,
    )
    assert out["ok"] is True
    assert out["created"] is True
    assert out["consumable"] is False
    assert out["lifecycle_state"] == LIFECYCLE_ELIGIBLE
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    validate_evidence_constitutional_metadata_v1(rec)
    assert rec.owner == "purchase_truth_authority"
    assert rec.canonical_family == FAMILY_PURCHASE
    assert rec.source_observations
    assert rec.timestamp_authority
    assert rec.accounting_identity
    assert rec.observability_identity
    assert rec.eligibility
    assert rec.version >= 1
    assert rec.readiness == READINESS_READY
    assert rec.confidence == CONFIDENCE_CONFIRMED
    assert rec.lifecycle_state != LIFECYCLE_CONSUMABLE
    assert rec.envelope.payload.get("terminal_for_recovery") is True
    assert (
        rec.envelope.payload.get("production_stop_authority")
        == "purchase_truth_legacy"
    )


def test_delivery_not_equal_sent():
    assert classify_message_lifecycle_stage_v1("sent") == "message_sent"
    assert sent_claimed_v1("message_sent") is True
    assert delivery_claimed_v1("message_sent") is False
    assert delivery_claimed_v1("message_delivered") is True

    sent = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload={
            "store_slug": "demo",
            "message_sid": "SM_sent_only",
            "status": "sent",
        },
        force=True,
    )
    assert sent["ok"] is True
    rec = get_evidence_truth_store_v1().get(sent["evidence_id"])
    assert rec is not None
    assert rec.canonical_family == FAMILY_COMMUNICATION
    assert rec.envelope.payload.get("sent_claimed") is True
    assert rec.envelope.payload.get("delivered_claimed") is False
    assert rec.envelope.payload.get("sent_equals_delivered") is False

    delivered = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload={
            "store_slug": "demo",
            "message_sid": "SM_delivered",
            "status": "delivered",
        },
        force=True,
    )
    drec = get_evidence_truth_store_v1().get(delivered["evidence_id"])
    assert drec is not None
    assert drec.envelope.payload.get("delivered_claimed") is True


def test_purchase_terminal_parity_does_not_activate_consumers():
    """Evidence documents terminal meaning; consumable remains false."""
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:term-1",
            "purchase_completed": True,
        },
        force=True,
    )
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    assert rec.consumable is False
    rows = list_consumer_eligibility_v1()
    purchase_rows = [r for r in rows if "purchase_confirmed" in r.artifact]
    assert purchase_rows
    assert "recovery_terminal_stop" in purchase_rows[0].prohibited_consumers
    assert "business_findings_engine" in purchase_rows[0].prohibited_consumers
    assert "evidence_bundle_composer" in purchase_rows[0].prohibited_consumers


def test_gate_a_evidence_partial_passes():
    report = run_gate_a_partial_observation_evidence_v1()
    assert report["passed"] is True, report


def test_prior_packages_still_green():
    report = run_gate_a_partial_raw_observation_v1()
    assert report["passed"] is True, report


def test_rollback_flag_off_and_flags_snapshot():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={"store_slug": "demo", "recovery_key": "demo:rb"},
        force=True,
    )
    assert get_evidence_truth_store_v1().count(family=FAMILY_PURCHASE) >= 1
    # Flag OFF path is no-op (does not clear store — Blueprint retains versions)
    off = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={"store_slug": "demo", "recovery_key": "demo:rb2"},
        environ={},
        force=False,
    )
    assert off.get("skipped") is True
    snap = evidence_truth_flags_snapshot(environ={})
    assert snap[FLAG_EVIDENCE_DUAL_WRITE] is False


def test_accounting_evidence_out_on_create():
    from services.evidence_truth import evidence_accounting_snapshot_v1

    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={"store_slug": "demo", "recovery_key": "demo:acct"},
        force=True,
    )
    assert out["created"] is True
    snap = evidence_accounting_snapshot_v1()
    assert snap["stage_counts"]["evidence_out"] >= 1
    assert snap["stage_counts"]["observation_out"] >= 1
