# -*- coding: utf-8 -*-
"""WP-ET-03 — Observation Normalizer shadow dual-write + Gate A partial."""
from __future__ import annotations

from services.evidence_truth import (
    FLAG_OBSERVATION_DUAL_WRITE,
    evidence_truth_flag_enabled,
    evidence_truth_flags_snapshot,
    list_consumer_eligibility_v1,
    observation_dual_write_enabled,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    run_gate_a_partial_raw_observation_v1,
    shadow_dual_write_observation_v1,
)
from services.evidence_truth.observation_shadow_dual_write_v1 import (
    maybe_shadow_cart_event_observation_v1,
)
from services.evidence_truth.observation_types_v1 import RAW_KIND_CART_EVENT


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()


def test_flag_default_off_no_write():
    assert evidence_truth_flag_enabled(FLAG_OBSERVATION_DUAL_WRITE, environ={}) is False
    assert observation_dual_write_enabled(environ={}) is False
    out = maybe_shadow_cart_event_observation_v1(
        {"store_slug": "demo", "session_id": "s1"}
    )
    assert out is not None
    assert out.get("skipped") is True
    assert out.get("reason") == "flag_off"


def test_force_dual_write_stores_observation_and_accounts():
    out = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"store_slug": "demo", "session_id": "sess-a", "event": "cart_abandoned"},
        force=True,
    )
    assert out["ok"] is True
    assert out["rejected"] is False
    assert out["observation_id"]
    from services.evidence_truth import evidence_accounting_snapshot_v1

    snap = evidence_accounting_snapshot_v1()
    assert snap["stage_counts"]["raw_in"] == 1
    assert snap["stage_counts"]["observation_out"] == 1


def test_identity_fail_closed_no_observation():
    out = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"session_id": "no-store"},
        force=True,
    )
    assert out["rejected"] is True
    assert out["reason_code"] == "identity_mismatch"
    from services.evidence_truth import get_canonical_observation_store_v1

    assert get_canonical_observation_store_v1().count() == 0


def test_gate_a_partial_harness_passes():
    report = run_gate_a_partial_raw_observation_v1()
    assert report["passed"] is True, report


def test_consumer_eligibility_matrix_present():
    rows = list_consumer_eligibility_v1()
    assert len(rows) >= 1
    row = rows[0]
    assert "CanonicalObservation" in row.artifact
    assert "knowledge_layer" in row.prohibited_consumers
    assert "business_findings_engine" in row.prohibited_consumers


def test_flags_snapshot_still_all_off_by_default():
    snap = evidence_truth_flags_snapshot(environ={})
    assert all(v is False for v in snap.values())
