# -*- coding: utf-8 -*-
"""
Gate A harness — Evidence accounting (Blueprint §9).

Synthetic verification only. Does not authorize or execute Gate F/G.
Does not wire production ingress.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.accounting_v1 import (
    STAGE_BUNDLE_PROJECTION_OUT,
    STAGE_EVIDENCE_OUT,
    STAGE_OBSERVATION_OUT,
    STAGE_RAW_IN,
    EvidenceAccountingLedgerV1,
)
from services.evidence_truth.contracts_v1 import OE_1_SOURCES
from services.evidence_truth.kernel_v1 import (
    REJECT_MISSING_SOURCES,
    REJECT_UNKNOWN_TYPE,
)
from services.evidence_truth.observability_v1 import (
    build_evidence_observability_snapshot_v1,
    get_evidence_truth_admin_diagnostics_v1,
)


def run_gate_a_harness_v1(*, ledger: EvidenceAccountingLedgerV1 | None = None) -> dict[str, Any]:
    """
    Execute synthetic increments and assert Gate A accounting properties.

    Returns a pass/fail report suitable for WP-ET-02 verification artifacts.
    Uses an isolated ledger by default (does not pollute process-global counters).
    """
    led = ledger if ledger is not None else EvidenceAccountingLedgerV1()
    led.reset()
    checks: list[dict[str, Any]] = []

    # Zero-traffic baseline
    zero = led.snapshot()
    checks.append(
        {
            "id": "A0_zero_traffic",
            "ok": zero["rejected_total"] == 0
            and zero["stage_counts"][STAGE_RAW_IN] == 0
            and zero["silent_loss_trips"] == 0,
            "detail": "admin counters exist at zero",
        }
    )

    # Happy path: raw → observation → evidence → bundle
    led.increment_stage(STAGE_RAW_IN, n=10)
    led.increment_stage(STAGE_OBSERVATION_OUT, n=8)
    led.record_reject(REJECT_MISSING_SOURCES, detail="synthetic")
    led.record_reject(REJECT_UNKNOWN_TYPE, detail="synthetic")
    led.set_in_flight(0)
    # 10 >= 8 + 2 + 0
    inv1 = led.check_invariants()
    checks.append(
        {
            "id": "A1_primary_invariant_after_rejects",
            "ok": bool(inv1.get("ok")),
            "detail": inv1,
        }
    )

    led.increment_stage(STAGE_EVIDENCE_OUT, n=7)
    led.increment_stage(STAGE_BUNDLE_PROJECTION_OUT, n=7)
    inv2 = led.check_invariants()
    checks.append(
        {
            "id": "A2_stage_chain_ok",
            "ok": bool(inv2.get("ok")),
            "detail": inv2,
        }
    )

    led.record_contract_violation(OE_1_SOURCES, detail="synthetic")
    led.record_missing_ownership(detail="synthetic")
    snap = led.snapshot()
    checks.append(
        {
            "id": "A3_rejects_audited_by_reason",
            "ok": snap["rejected_by_reason"][REJECT_MISSING_SOURCES] == 1
            and snap["rejected_by_reason"][REJECT_UNKNOWN_TYPE] == 1
            and any(a.get("kind") == "reject" for a in snap["audit_samples"]),
            "detail": "reject reason codes incremented and audited",
        }
    )

    # Silent loss: force invariant break
    led.increment_stage(STAGE_OBSERVATION_OUT, n=100)
    loss = led.detect_silent_loss()
    checks.append(
        {
            "id": "A4_silent_loss_detector",
            "ok": bool(loss.get("tripped")) and loss.get("alert_class") == "P0",
            "detail": loss,
        }
    )

    # Observability + admin read path consume accounting
    obs = build_evidence_observability_snapshot_v1(ledger=led)
    admin = get_evidence_truth_admin_diagnostics_v1(ledger=led)
    checks.append(
        {
            "id": "A5_observability_surface",
            "ok": obs.get("schema") == "evidence_observability_v1"
            and obs.get("merchant_visible") is False
            and "volume" in obs
            and "rejected_evidence" in obs,
            "detail": "C-05 stub snapshot shaped",
        }
    )
    checks.append(
        {
            "id": "A6_admin_read_path",
            "ok": admin.get("schema") == "evidence_truth_admin_diagnostics_v1"
            and "accounting" in admin
            and "observability" in admin,
            "detail": "admin diagnostics payload available",
        }
    )

    # Gate F/G must remain unauthorized in harness context
    gates = {g["gate_id"]: g for g in obs.get("gates") or []}
    checks.append(
        {
            "id": "A7_gates_f_g_not_authorized",
            "ok": gates.get("F", {}).get("execution_authorized") is False
            and gates.get("G", {}).get("execution_authorized") is False,
            "detail": "harness does not authorize F/G",
        }
    )

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "gate": "A",
        "name": "Evidence accounting",
        "passed": passed,
        "checks": checks,
        "accounting_snapshot": led.snapshot(),
        "execution_authorized": True,  # Gate A harness itself may run in WP-ET-02
        "note": "Synthetic only — no production ingress; Gate F/G not executed",
    }
