# -*- coding: utf-8 -*-
"""WP-ET-04 — C-03 Eligibility & Freshness + Observation constitutional metadata."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.evidence_truth import (
    CONFIDENCE_UNKNOWN,
    READINESS_STATES_V1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    run_gate_a_partial_raw_observation_v1,
    shadow_dual_write_observation_v1,
    validate_readiness_transition_v1,
)
from services.evidence_truth.eligibility_freshness_v1 import (
    EvidenceStampCandidateV1,
    assert_never_fabricate_ready_when_stale_v1,
    clear_family_eligibility_predicates_v1,
    compute_freshness_v1,
    stamp_evidence_eligibility_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PURCHASE
from services.evidence_truth.kernel_v1 import (
    READINESS_INSUFFICIENT,
    READINESS_READY,
    READINESS_TRUSTED,
    READINESS_UNKNOWN,
)
from services.evidence_truth.observation_types_v1 import RAW_KIND_CART_EVENT


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    clear_family_eligibility_predicates_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    clear_family_eligibility_predicates_v1()


def test_readiness_transition_rules_architecture_section_6():
    assert validate_readiness_transition_v1(READINESS_UNKNOWN, READINESS_READY).ok
    assert validate_readiness_transition_v1(READINESS_READY, READINESS_TRUSTED).ok
    assert not validate_readiness_transition_v1(READINESS_TRUSTED, READINESS_READY).ok
    assert READINESS_STATES_V1


def test_stamp_ready_when_eligible():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    stamp = stamp_evidence_eligibility_v1(
        EvidenceStampCandidateV1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_confirmed_v1",
            store_slug="demo",
            subject="cart:1",
            observed_at=now,
            as_of=now,
            source_count=1,
            channel_available=True,
            prior_readiness=READINESS_UNKNOWN,
            ttl_seconds=86400,
        )
    )
    assert stamp.readiness == READINESS_READY
    assert stamp.freshness.is_stale is False


def test_stamp_stale_never_ready():
    old = (datetime.now(timezone.utc) - timedelta(days=10)).replace(microsecond=0).isoformat()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    stamp = stamp_evidence_eligibility_v1(
        EvidenceStampCandidateV1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_confirmed_v1",
            store_slug="demo",
            subject="cart:1",
            observed_at=old,
            as_of=now,
            source_count=1,
            channel_available=True,
            prior_readiness=READINESS_READY,
            ttl_seconds=3600,
        )
    )
    assert stamp.freshness.is_stale is True
    assert stamp.readiness == READINESS_INSUFFICIENT
    assert_never_fabricate_ready_when_stale_v1(stamp)


def test_stamp_unavailable_when_channel_missing():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    stamp = stamp_evidence_eligibility_v1(
        EvidenceStampCandidateV1(
            evidence_family=FAMILY_PURCHASE,
            evidence_type="purchase_confirmed_v1",
            store_slug="demo",
            subject="cart:1",
            observed_at=now,
            as_of=now,
            channel_available=False,
            prior_readiness=READINESS_UNKNOWN,
        )
    )
    assert stamp.readiness == "unavailable"


def test_observation_requires_constitutional_metadata():
    out = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"store_slug": "demo", "session_id": "gov-1", "event": "cart_abandoned"},
        force=True,
    )
    assert out["ok"] is True
    from services.evidence_truth import get_canonical_observation_store_v1

    obs = get_canonical_observation_store_v1().get(out["observation_id"])
    assert obs is not None
    assert obs.owner == "cart_truth_authority"
    assert obs.canonical_family == "cart"
    assert obs.timestamp_authority
    assert obs.version >= 1
    assert obs.confidence_state == CONFIDENCE_UNKNOWN
    assert obs.readiness_state == READINESS_UNKNOWN
    assert obs.accounting_status == "recorded"
    assert obs.observability_status == "ops_visible"


def test_gate_a_partial_still_passes_with_governance():
    report = run_gate_a_partial_raw_observation_v1()
    assert report["passed"] is True, report


def test_consumer_eligibility_unchanged_no_cutover():
    from services.evidence_truth.consumer_eligibility_v1 import list_consumer_eligibility_v1

    rows = list_consumer_eligibility_v1()
    assert "business_findings_engine" in rows[0].prohibited_consumers
    assert "knowledge_layer" in rows[0].prohibited_consumers


def test_compute_freshness_helper():
    fresh = compute_freshness_v1(
        observed_at=datetime.now(timezone.utc).isoformat(),
        ttl_seconds=60,
    )
    assert fresh.is_stale is False
