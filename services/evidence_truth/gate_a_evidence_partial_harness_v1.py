# -*- coding: utf-8 -*-
"""
Gate A partial harness — Observation → Evidence for Stage-3 families.

Covers Purchase/Communication (WP-ET-05) and Cart/Recovery (WP-ET-06).
Synthetic only. Does not authorize Gate F/G or consumer cutover.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.accounting_v1 import (
    STAGE_EVIDENCE_OUT,
    STAGE_OBSERVATION_OUT,
    get_evidence_accounting_ledger_v1,
    reset_evidence_accounting_ledger_v1,
)
from services.evidence_truth.evidence_dual_write_v1 import shadow_dual_write_evidence_v1
from services.evidence_truth.evidence_store_v1 import (
    get_evidence_truth_store_v1,
    reset_evidence_truth_store_v1,
)
from services.evidence_truth.families_v1 import (
    FAMILY_CART,
    FAMILY_COMMUNICATION,
    FAMILY_PURCHASE,
    FAMILY_RECOVERY,
)
from services.evidence_truth.lifecycle_truth_alignment_v1 import (
    CONTRACT_SENT,
    CONTRACT_WAITING_SEND,
)
from services.evidence_truth.observation_store_v1 import reset_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import (
    RAW_KIND_CART_EVENT,
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PURCHASE,
    RAW_KIND_RECOVERY,
)


def run_gate_a_partial_observation_evidence_v1(
    *,
    reset_global: bool = True,
) -> dict[str, Any]:
    """Prove Stage-3 Evidence versions + accounting linkage."""
    if reset_global:
        reset_evidence_accounting_ledger_v1()
        reset_canonical_observation_store_v1()
        reset_evidence_truth_store_v1()

    checks: list[dict[str, Any]] = []

    r1 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "session_id": "s-buy",
            "recovery_key": "demo:s-buy",
            "purchase_completed": True,
        },
        force=True,
        source="gate_a_evidence",
    )
    checks.append(
        {
            "id": "E1_purchase_evidence",
            "ok": bool(r1.get("ok")) and not r1.get("rejected") and r1.get("created"),
        }
    )

    r2 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload={
            "store_slug": "demo",
            "message_sid": "SM_gate_a_1",
            "status": "sent",
            "session_id": "s-msg",
        },
        force=True,
        source="gate_a_evidence",
    )
    checks.append(
        {
            "id": "E2_communication_evidence_sent",
            "ok": bool(r2.get("ok")) and not r2.get("rejected") and r2.get("created"),
        }
    )

    r3 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "demo",
            "session_id": "s-buy",
            "recovery_key": "demo:s-buy",
            "purchase_completed": True,
        },
        force=True,
        observation_id=str(r1.get("observation_id") or ""),
        source="gate_a_evidence",
    )
    checks.append(
        {
            "id": "E3_purchase_idempotent",
            "ok": bool(r3.get("ok")) and bool(r3.get("duplicated")),
        }
    )

    r4 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload={
            "store_slug": "demo",
            "session_id": "s-cart",
            "cart_id": "c1",
            "event": "cart_abandoned",
        },
        force=True,
        source="gate_a_evidence",
    )
    checks.append(
        {
            "id": "E4_cart_evidence",
            "ok": bool(r4.get("ok")) and not r4.get("rejected") and r4.get("created"),
        }
    )

    r5 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:s-rec",
            "session_id": "s-rec",
            "status": "provider_sent",
            "timeline_status": "provider_sent",
        },
        force=True,
        source="gate_a_evidence",
    )
    checks.append(
        {
            "id": "E5_recovery_evidence",
            "ok": bool(r5.get("ok")) and not r5.get("rejected") and r5.get("created"),
        }
    )

    store = get_evidence_truth_store_v1()
    checks.append(
        {
            "id": "E6_versions_exist",
            "ok": (
                store.count(family=FAMILY_PURCHASE) >= 1
                and store.count(family=FAMILY_COMMUNICATION) >= 1
                and store.count(family=FAMILY_CART) >= 1
                and store.count(family=FAMILY_RECOVERY) >= 1
            ),
            "detail": store.snapshot().get("by_family"),
        }
    )

    sent_rec = store.get(str(r2.get("evidence_id") or ""))
    sent_ok = (
        sent_rec is not None
        and bool(sent_rec.envelope.payload.get("sent_claimed"))
        and not bool(sent_rec.envelope.payload.get("delivered_claimed"))
    )
    checks.append({"id": "E7_sent_not_delivered", "ok": sent_ok})

    buy_rec = store.get(str(r1.get("evidence_id") or ""))
    term_ok = (
        buy_rec is not None
        and bool(buy_rec.envelope.payload.get("terminal_for_recovery"))
        and buy_rec.envelope.payload.get("production_stop_authority")
        == "purchase_truth_legacy"
        and buy_rec.consumable is False
    )
    checks.append({"id": "E8_purchase_terminal_parity_meta", "ok": term_ok})

    rec_rec = store.get(str(r5.get("evidence_id") or ""))
    life_ok = (
        rec_rec is not None
        and rec_rec.envelope.payload.get("contract_state") == CONTRACT_SENT
        and bool(rec_rec.envelope.payload.get("sent_claimed"))
        and not bool(rec_rec.envelope.payload.get("purchased_claimed"))
        and bool(rec_rec.envelope.payload.get("must_not_weaken_purchase_stop"))
        and bool(rec_rec.envelope.payload.get("lifecycle_aligned"))
        and rec_rec.consumable is False
    )
    checks.append({"id": "E9_lifecycle_alignment_sent", "ok": life_ok})

    # waiting_send must not claim sent
    r6 = shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload={
            "store_slug": "demo",
            "recovery_key": "demo:s-wait",
            "status": "scheduled",
            "timeline_status": "scheduled",
        },
        force=True,
        source="gate_a_evidence",
    )
    wait_rec = store.get(str(r6.get("evidence_id") or ""))
    wait_ok = (
        wait_rec is not None
        and wait_rec.envelope.payload.get("contract_state") == CONTRACT_WAITING_SEND
        and not bool(wait_rec.envelope.payload.get("sent_claimed"))
    )
    checks.append({"id": "E10_waiting_send_not_sent", "ok": wait_ok})

    snap = get_evidence_accounting_ledger_v1().snapshot()
    obs_out = int(snap["stage_counts"][STAGE_OBSERVATION_OUT])
    ev_out = int(snap["stage_counts"][STAGE_EVIDENCE_OUT])
    checks.append(
        {
            "id": "E11_accounting_evidence_out",
            "ok": obs_out >= 4 and ev_out >= 4,
            "detail": {"observation_out": obs_out, "evidence_out": ev_out},
        }
    )

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "gate": "A_partial_evidence",
        "name": "Observation→Evidence accounting (Stage-3 families)",
        "passed": passed,
        "checks": checks,
        "accounting_snapshot": snap,
        "evidence_store": store.snapshot(),
        "note": "Synthetic force=True; production CARTFLOW_EVIDENCE_DUAL_WRITE remains OFF",
    }
