# -*- coding: utf-8 -*-
"""
Gate A partial harness — Raw ≈ Observation (WP-ET-03 / Blueprint Stage 2 exit).

Synthetic only. Does not authorize Gate F/G.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.accounting_v1 import (
    STAGE_OBSERVATION_OUT,
    STAGE_RAW_IN,
    EvidenceAccountingLedgerV1,
    get_evidence_accounting_ledger_v1,
    reset_evidence_accounting_ledger_v1,
)
from services.evidence_truth.observation_shadow_dual_write_v1 import (
    shadow_dual_write_observation_v1,
)
from services.evidence_truth.observation_store_v1 import (
    get_canonical_observation_store_v1,
    reset_canonical_observation_store_v1,
)
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_CART_EVENT,
    RAW_KIND_PURCHASE,
)


def run_gate_a_partial_raw_observation_v1(
    *,
    tolerance: int = 0,
    reset_global: bool = True,
) -> dict[str, Any]:
    """
    Prove accounting linkage: after shadow dual-writes, raw_in ≈ observation_out
    within tolerance (accounting for audited rejects).

    Formula checked:
      raw_in - rejected - observation_out <= tolerance
      and observation_out <= raw_in
    """
    if reset_global:
        reset_evidence_accounting_ledger_v1()
        reset_canonical_observation_store_v1()

    checks: list[dict[str, Any]] = []

    # Happy path cart + purchase
    r1 = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={
            "store_slug": "demo",
            "session_id": "s1",
            "cart_id": "c1",
            "event": "cart_abandoned",
        },
        source_channel="widget",
        source="gate_a_partial",
        force=True,
    )
    r2 = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "session_id": "s2",
            "purchase_completed": True,
            "recovery_key": "demo:s2",
        },
        source_channel="api",
        source="gate_a_partial",
        force=True,
    )
    checks.append({"id": "P1_cart_ok", "ok": bool(r1.get("ok")) and not r1.get("rejected")})
    checks.append({"id": "P2_purchase_ok", "ok": bool(r2.get("ok")) and not r2.get("rejected")})

    # Identity fail-closed
    r3 = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={"session_id": "orphan"},  # no store
        force=True,
    )
    checks.append(
        {
            "id": "P3_identity_fail_closed",
            "ok": bool(r3.get("rejected")) and r3.get("reason_code") == "identity_mismatch",
        }
    )

    # Idempotent duplicate
    r4 = shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={
            "store_slug": "demo",
            "session_id": "s1",
            "cart_id": "c1",
            "event": "cart_abandoned",
        },
        force=True,
    )
    checks.append({"id": "P4_idempotent", "ok": bool(r4.get("duplicated"))})

    snap = get_evidence_accounting_ledger_v1().snapshot()
    raw_in = int(snap["stage_counts"][STAGE_RAW_IN])
    obs_out = int(snap["stage_counts"][STAGE_OBSERVATION_OUT])
    rejected = int(snap["rejected_total"])
    # Expected synthetic: 4 raw (cart, purchase, fail, dup), 2 observations, 1 reject
    # Idempotent dup accounts for raw_in - observation_out - rejected (== 1 here)
    unaccounted = raw_in - obs_out - rejected
    approx_ok = (
        obs_out <= raw_in
        and unaccounted >= 0
        and unaccounted <= max(1, int(tolerance))  # allow idempotent re-delivery
        and obs_out == 2
        and rejected == 1
    )
    checks.append(
        {
            "id": "P5_raw_approx_observation",
            "ok": approx_ok,
            "detail": {
                "raw_in": raw_in,
                "observation_out": obs_out,
                "rejected": rejected,
                "unaccounted_raw": unaccounted,
                "tolerance": tolerance,
            },
        }
    )

    inv = get_evidence_accounting_ledger_v1().check_invariants()
    checks.append({"id": "P6_primary_invariant", "ok": bool(inv.get("primary_invariant_ok"))})

    store_count = get_canonical_observation_store_v1().count()
    checks.append({"id": "P7_store_has_observations", "ok": store_count >= 2})

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "gate": "A_partial",
        "name": "Raw≈Observation accounting linkage",
        "passed": passed,
        "checks": checks,
        "accounting_snapshot": snap,
        "observation_store": get_canonical_observation_store_v1().snapshot(),
        "note": "Synthetic force=True; production flag remains OFF by default",
    }
