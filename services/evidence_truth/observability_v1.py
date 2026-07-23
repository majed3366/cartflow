# -*- coding: utf-8 -*-
"""
C-05 Evidence Observability Surface — WP-ET-02 stubs.

Exposes Blueprint §8 signals from accounting (+ stub slots for later WPs).
Ops/admin only — no merchant chrome claims.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from services.evidence_truth.accounting_v1 import (
    STAGE_BUNDLE_PROJECTION_OUT,
    STAGE_EVIDENCE_OUT,
    STAGE_KNOWLEDGE_OUT,
    STAGE_OBSERVATION_OUT,
    STAGE_RAW_IN,
    EvidenceAccountingLedgerV1,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.families_v1 import list_evidence_families
from services.evidence_truth.flags_v1 import evidence_truth_flags_snapshot
from services.evidence_truth.gates_v1 import list_evidence_truth_gates


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_evidence_observability_snapshot_v1(
    *,
    ledger: Optional[EvidenceAccountingLedgerV1] = None,
) -> dict[str, Any]:
    """
    Ops observability payload (Blueprint §8).

    Freshness / coverage / latency are stub zeros until Observation/Evidence
    publishers feed timestamps (WP-ET-03+). Volume and rejects are live from C-04.
    """
    led = ledger or get_evidence_accounting_ledger_v1()
    # Health uses invariant; avoid calling detect_silent_loss here to prevent
    # accidental trip increments on every read — use check_invariants only.
    inv = led.check_invariants()
    snap = led.snapshot()
    if not inv.get("primary_invariant_ok"):
        health_status = "down"
    elif int(snap.get("missing_ownership") or 0) > 0:
        health_status = "degraded"
    elif int(sum((snap.get("contract_violations") or {}).values())) > 0:
        health_status = "degraded"
    else:
        health_status = "up"

    stages = snap.get("stage_counts") or {}
    volume = {
        "raw_in": int(stages.get(STAGE_RAW_IN) or 0),
        "observation_out": int(stages.get(STAGE_OBSERVATION_OUT) or 0),
        "evidence_out": int(stages.get(STAGE_EVIDENCE_OUT) or 0),
        "bundle_projection_out": int(stages.get(STAGE_BUNDLE_PROJECTION_OUT) or 0),
        "knowledge_out": int(stages.get(STAGE_KNOWLEDGE_OUT) or 0),
        "rejected_total": int(snap.get("rejected_total") or 0),
        "in_flight": int(snap.get("in_flight") or 0),
    }

    families = [
        {
            "family": f.family,
            "owner_module": f.owner_module,
            "freshness": {"newest_at": None, "status": "unknown"},
            "coverage": {
                "ready_pct": None,
                "unavailable_pct": None,
                "insufficient_pct": None,
                "status": "stub",
            },
        }
        for f in list_evidence_families()
    ]

    return {
        "schema": "evidence_observability_v1",
        "as_of": _utc_now_iso(),
        "health": {
            "status": health_status,
            "components": {
                "accounting": health_status,
                "observation_normalizer": "dual_write_idle",
                "family_authorities": "stage3_5_dual_write_idle",
                "visitor_truth_authority": "dual_write_idle",
                "bundle_composer": "shadow_idle",
                "knowledge_composer": "shadow_idle",
            },
        },
        "freshness": {
            "status": "stub",
            "note": "Populated when Observation/Evidence publishers exist (WP-ET-03+)",
            "last_accounting_event_at": snap.get("last_event_at") or None,
        },
        "coverage": {
            "status": "stub",
            "families": families,
        },
        "latency": {
            "status": "stub",
            "raw_to_observation_ms": {"p50": None, "p95": None},
            "observation_to_evidence_ms": {"p50": None, "p95": None},
            "evidence_to_bundle_ms": {"p50": None, "p95": None},
        },
        "volume": volume,
        "contract_violations": dict(snap.get("contract_violations") or {}),
        "rejected_evidence": dict(snap.get("rejected_by_reason") or {}),
        "missing_ownership": int(snap.get("missing_ownership") or 0),
        "evidence_accounting": {
            "invariant": inv,
            "silent_loss_trips": int(snap.get("silent_loss_trips") or 0),
        },
        "flags": evidence_truth_flags_snapshot(),
        "gates": [
            {
                "gate_id": g.gate_id,
                "name": g.name,
                "execution_authorized": g.execution_authorized,
            }
            for g in list_evidence_truth_gates()
        ],
        "dashboards": [
            "Evidence Pipeline Health",
            "Family Readiness Map",
            "Bundle Parity Diff",
            "Silent-Loss Detector",
            "Visitor Authority Status",
        ],
        "merchant_visible": False,
    }


def get_evidence_truth_admin_diagnostics_v1(
    *,
    ledger: Optional[EvidenceAccountingLedgerV1] = None,
) -> dict[str, Any]:
    """
    Admin/ops read path (Blueprint WP-ET-02 expected output).

    Library callable — not wired to merchant surfaces. HTTP exposure is optional
    and not required for WP-ET-02 synthetic verification.
    """
    led = ledger or get_evidence_accounting_ledger_v1()
    obs = build_evidence_observability_snapshot_v1(ledger=led)
    return {
        "schema": "evidence_truth_admin_diagnostics_v1",
        "as_of": obs["as_of"],
        "accounting": led.snapshot(),
        "observability": obs,
        "zero_traffic": (
            int((led.snapshot().get("stage_counts") or {}).get(STAGE_RAW_IN) or 0) == 0
            and int(led.snapshot().get("rejected_total") or 0) == 0
        ),
    }
