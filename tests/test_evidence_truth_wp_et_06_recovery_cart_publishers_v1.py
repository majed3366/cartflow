# -*- coding: utf-8 -*-
"""WP-ET-06 — Recovery + Cart Evidence publishers (C-12 / C-11)."""
from __future__ import annotations

from services.evidence_truth import (
    FLAG_EVIDENCE_DUAL_WRITE,
    evidence_dual_write_enabled,
    evidence_truth_flag_enabled,
    get_evidence_truth_store_v1,
    list_consumer_eligibility_v1,
    maybe_publish_cart_evidence_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_truth_store_v1,
    run_gate_a_partial_observation_evidence_v1,
    run_gate_a_partial_raw_observation_v1,
    shadow_dual_write_evidence_v1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.evidence_governance_v1 import LIFECYCLE_ELIGIBLE
from services.evidence_truth.families_v1 import FAMILY_CART, FAMILY_RECOVERY
from services.evidence_truth.lifecycle_truth_alignment_v1 import (
    CONTRACT_REPLIED,
    CONTRACT_SENT,
    CONTRACT_WAITING_SEND,
    assert_lifecycle_alignment_invariants_v1,
    map_timeline_status_to_contract_state_v1,
)
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_CART_EVENT,
    RAW_KIND_RECOVERY,
)


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def test_flag_default_off_cart_no_write():
    assert evidence_truth_flag_enabled(FLAG_EVIDENCE_DUAL_WRITE, environ={}) is False
    assert evidence_dual_write_enabled(environ={}) is False
    out = maybe_publish_cart_evidence_v1(
        {"store_slug": "demo", "session_id": "s1", "event": "cart_abandoned"}
    )
    assert out is not None
    assert out.get("skipped") is True
    assert get_evidence_truth_store_v1().count() == 0


def test_cart_evidence_constitutional_and_not_consumable():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={
            "store_slug": "demo",
            "session_id": "sess-cart",
            "cart_id": "c9",
            "event": "cart_abandoned",
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
    assert rec.owner == "cart_truth_authority"
    assert rec.canonical_family == FAMILY_CART
    assert rec.envelope.payload.get("abandon_signal") is True
    assert rec.envelope.payload.get("purchase_invented") is False


def test_lifecycle_truth_contract_mapping():
    assert map_timeline_status_to_contract_state_v1("scheduled") == CONTRACT_WAITING_SEND
    assert map_timeline_status_to_contract_state_v1("provider_sent") == CONTRACT_SENT
    assert map_timeline_status_to_contract_state_v1("webhook_delivered") == CONTRACT_SENT
    assert map_timeline_status_to_contract_state_v1("customer_reply") == CONTRACT_REPLIED
    # F3: sent claim without provider_sent
    v = assert_lifecycle_alignment_invariants_v1(
        timeline_status="scheduled",
        contract_state=CONTRACT_WAITING_SEND,
        sent_claimed=True,
        replied_claimed=False,
        purchased_claimed=False,
    )
    assert "F3_sent_without_provider_sent" in v
    # F2: replied without customer_reply
    v2 = assert_lifecycle_alignment_invariants_v1(
        timeline_status="provider_sent",
        contract_state=CONTRACT_SENT,
        sent_claimed=True,
        replied_claimed=True,
        purchased_claimed=False,
    )
    assert "F2_replied_without_customer_reply" in v2


def test_recovery_evidence_lifecycle_aligned_and_no_purchase_weaken():
    sent = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:rk-1",
            "status": "provider_sent",
            "timeline_status": "provider_sent",
        },
        force=True,
    )
    assert sent["ok"] is True
    rec = get_evidence_truth_store_v1().get(sent["evidence_id"])
    assert rec is not None
    validate_evidence_constitutional_metadata_v1(rec)
    assert rec.owner == "recovery_truth_authority"
    assert rec.canonical_family == FAMILY_RECOVERY
    assert rec.envelope.payload.get("contract_state") == CONTRACT_SENT
    assert rec.envelope.payload.get("sent_claimed") is True
    assert rec.envelope.payload.get("replied_claimed") is False
    assert rec.envelope.payload.get("purchased_claimed") is False
    assert rec.envelope.payload.get("must_not_weaken_purchase_stop") is True
    assert (
        rec.envelope.payload.get("production_stop_authority") == "purchase_truth_legacy"
    )
    assert rec.envelope.payload.get("lifecycle_aligned") is True
    assert rec.consumable is False

    # Delivery signal must not invent replied
    delivered = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:rk-2",
            "status": "webhook_delivered",
            "timeline_status": "webhook_delivered",
        },
        force=True,
    )
    drec = get_evidence_truth_store_v1().get(delivered["evidence_id"])
    assert drec is not None
    assert drec.envelope.payload.get("contract_state") == CONTRACT_SENT
    assert drec.envelope.payload.get("delivery_signal") is True
    assert drec.envelope.payload.get("replied_claimed") is False
    assert drec.envelope.payload.get("delivered_claimed") is False


def test_consumer_eligibility_cart_recovery_prohibited():
    rows = list_consumer_eligibility_v1()
    cart_rows = [r for r in rows if "cart_state_v1" in r.artifact]
    rec_rows = [r for r in rows if "recovery_progression_v1" in r.artifact]
    assert cart_rows and rec_rows
    for row in cart_rows + rec_rows:
        assert "business_findings_engine" in row.prohibited_consumers
        assert "evidence_bundle_composer" in row.prohibited_consumers
        assert "recovery_terminal_stop" in row.prohibited_consumers


def test_gate_a_stage3_evidence_partial_passes():
    report = run_gate_a_partial_observation_evidence_v1()
    assert report["passed"] is True, report


def test_prior_packages_still_green():
    report = run_gate_a_partial_raw_observation_v1()
    assert report["passed"] is True, report


def test_rollback_flag_off():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"store_slug": "demo", "session_id": "rb", "event": "cart_abandoned"},
        force=True,
    )
    off = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"store_slug": "demo", "session_id": "rb2", "event": "cart_abandoned"},
        environ={},
        force=False,
    )
    assert off.get("skipped") is True
