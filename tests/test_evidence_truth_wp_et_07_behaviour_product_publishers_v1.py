# -*- coding: utf-8 -*-
"""WP-ET-07 — Behaviour + Product Evidence publishers (C-15 / C-10)."""
from __future__ import annotations

from services.evidence_truth import (
    FLAG_EVIDENCE_DUAL_WRITE,
    evidence_dual_write_enabled,
    evidence_truth_flag_enabled,
    get_evidence_truth_store_v1,
    list_consumer_eligibility_v1,
    maybe_publish_product_evidence_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_truth_store_v1,
    run_bfsv_exp1_class_check_persist_to_evidence_v1,
    run_gate_a_partial_observation_evidence_v1,
    run_gate_a_partial_raw_observation_v1,
    shadow_dual_write_evidence_v1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.evidence_governance_v1 import LIFECYCLE_ELIGIBLE
from services.evidence_truth.families_v1 import FAMILY_BEHAVIOUR, FAMILY_PRODUCT
from services.evidence_truth.kernel_v1 import READINESS_UNAVAILABLE
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_BEHAVIOUR,
    RAW_KIND_PRODUCT_SIGNAL,
)
from services.evidence_truth.product_signal_classification_v1 import (
    SIGNAL_ATC,
    SIGNAL_CART_LINE,
    SIGNAL_VIEW,
    classify_product_signal_v1,
)


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()


def test_flag_default_off_product_no_write():
    assert evidence_truth_flag_enabled(FLAG_EVIDENCE_DUAL_WRITE, environ={}) is False
    assert evidence_dual_write_enabled(environ={}) is False
    out = maybe_publish_product_evidence_v1(
        {"store_slug": "demo", "session_id": "s1", "product_id": "p1"}
    )
    assert out is not None
    assert out.get("skipped") is True
    assert get_evidence_truth_store_v1().count() == 0


def test_atc_is_not_view_classification():
    assert (
        classify_product_signal_v1(
            {"event": "cart_state_sync", "capture_source": "cart_state_sync"}
        )
        == SIGNAL_CART_LINE
    )
    assert classify_product_signal_v1({"event": "add_to_cart"}) == SIGNAL_ATC
    assert classify_product_signal_v1({"event": "product_view"}) == SIGNAL_VIEW


def test_product_evidence_no_atc_as_view():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload={
            "store_slug": "demo",
            "session_id": "s-atc",
            "product_id": "sku-atc",
            "event": "cart_abandoned",
            "capture_source": "cart_abandoned",
        },
        force=True,
    )
    assert out["ok"] is True
    assert out["consumable"] is False
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    validate_evidence_constitutional_metadata_v1(rec)
    assert rec.owner == "product_truth_authority"
    assert rec.canonical_family == FAMILY_PRODUCT
    assert rec.envelope.payload.get("view_claimed") is False
    assert rec.envelope.payload.get("has_product_views_ready") is False
    assert rec.envelope.payload.get("atc_is_not_view") is True
    assert rec.envelope.payload.get("purchase_invented") is False


def test_product_view_signal_claims_view():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload={
            "store_slug": "demo",
            "session_id": "s-view",
            "product_id": "sku-v",
            "event": "product_view",
            "signal_class": SIGNAL_VIEW,
        },
        force=True,
    )
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    assert rec.envelope.payload.get("view_claimed") is True
    assert rec.envelope.payload.get("has_product_views_ready") is True


def test_behaviour_evidence_no_cause_invention_widget_unavailable():
    out = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_BEHAVIOUR,
        payload={
            "store_slug": "demo",
            "session_id": "s-hes",
            "reason": "shipping_cost",
            "sub_reason": "too_high",
            "event": "hesitation_reason_selected",
        },
        force=True,
    )
    assert out["ok"] is True
    assert out["lifecycle_state"] == LIFECYCLE_ELIGIBLE
    rec = get_evidence_truth_store_v1().get(out["evidence_id"])
    assert rec is not None
    validate_evidence_constitutional_metadata_v1(rec)
    assert rec.owner == "behaviour_truth_authority"
    assert rec.canonical_family == FAMILY_BEHAVIOUR
    assert rec.envelope.payload.get("reason_captured") is True
    assert rec.envelope.payload.get("confirmed_cause_invented") is False
    assert rec.envelope.payload.get("widget_shown_readiness") == READINESS_UNAVAILABLE
    assert rec.envelope.payload.get("absence_as_negative") is False
    assert rec.consumable is False


def test_bfsv_exp1_class_check_passes_without_resuming_bfsv():
    report = run_bfsv_exp1_class_check_persist_to_evidence_v1()
    assert report["passed"] is True, report
    assert report["bfsv_resumed"] is False


def test_consumer_eligibility_product_behaviour():
    rows = list_consumer_eligibility_v1()
    prod = [r for r in rows if "product_interest_window" in r.artifact]
    beh = [r for r in rows if "hesitation_reason_v1" in r.artifact]
    assert prod and beh
    assert "business_findings_engine" in prod[0].prohibited_consumers
    assert "bfsv_harness" in prod[0].prohibited_consumers
    assert "evidence_bundle_composer" in beh[0].prohibited_consumers


def test_prior_packages_still_green():
    assert run_gate_a_partial_raw_observation_v1()["passed"] is True
    assert run_gate_a_partial_observation_evidence_v1()["passed"] is True


def test_rollback_flag_off():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload={
            "store_slug": "demo",
            "session_id": "rb",
            "product_id": "p-rb",
            "event": "product_view",
        },
        force=True,
    )
    off = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload={
            "store_slug": "demo",
            "session_id": "rb2",
            "product_id": "p-rb2",
            "event": "product_view",
        },
        environ={},
        force=False,
    )
    assert off.get("skipped") is True
