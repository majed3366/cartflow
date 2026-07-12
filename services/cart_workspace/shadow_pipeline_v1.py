# -*- coding: utf-8 -*-
"""Shadow pipeline: candidacy → ownership → admission → decision → projection."""
from __future__ import annotations

from typing import Any, Optional

from services.cart_workspace.admission_v1 import AdmissionCandidate, evaluate_admission
from services.cart_workspace.contracts_v1 import (
    DecisionExplanation,
    DecisionRecord,
    _utc_now_iso,
)
from services.cart_workspace.decision_identity_v1 import allocate_decision_id
from services.cart_workspace.feature_flag_v1 import cart_workspace_v1_flag_state
from services.cart_workspace.ownership_v1 import apply_transition
from services.cart_workspace.projection_v1 import build_workspace_projection
from services.cart_workspace.shadow_store_v1 import SHADOW_STORE, ShadowStoreV1


def _explanation_for_admit(candidate: AdmissionCandidate, result_reason: str, action: str) -> DecisionExplanation:
    from services.cart_workspace.projection_v1 import ACTION_LABELS_AR

    label = ACTION_LABELS_AR.get(action, action)
    return DecisionExplanation(
        why_here=result_reason if result_reason else "يحتاج هذا القرار حكماً بشرياً الآن.",
        cartflow_did="CartFlow تابع الاسترداد تلقائياً حتى وصل إلى نقطة لا يمكن تحسينها بأمان دون قرارك.",
        why_stopped="توقف الأتمتة لأن الحكم البشري هنا يرفع احتمالية الاسترداد (أو بسبب أولوية VIP).",
        expected_after=f"بعد «{label}» تعود المتابعة إلى CartFlow تلقائياً.",
    )


def evaluate_candidate(
    candidate: AdmissionCandidate,
    *,
    store: Optional[ShadowStoreV1] = None,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Run one candidacy through P1/P2 and optionally create a Decision on Admit."""
    store = store or SHADOW_STORE
    ownership = store.get_ownership(candidate.store_slug, candidate.recovery_key)
    fp = candidate.resolved_fingerprint()

    # Enrich candidacy from store (idempotency / open Decision)
    candidate.open_decision_same_fingerprint = store.has_open_fingerprint(
        candidate.store_slug, candidate.recovery_key, fp
    )
    candidate.decision_already_open = store.merchant_has_open_decision(
        candidate.store_slug, candidate.recovery_key
    )
    candidate.fingerprint_seen_closed = store.fingerprint_was_closed(fp)

    # T8 before Override Admit when eligible and mode inactive
    audits: list[dict[str, Any]] = []
    if candidate.override_eligible and ownership.override_mode != "active":
        ownership, audit, _changed = apply_transition(
            ownership,
            transition_code="T8",
            evidence_refs=list(candidate.evidence_ids),
            correlation_id=correlation_id,
        )
        store.set_ownership(ownership)
        store.append_transition(audit)
        audits.append(audit.to_dict())
        ownership = store.get_ownership(candidate.store_slug, candidate.recovery_key)

    result = evaluate_admission(candidate, ownership)
    store.append_admission(result.to_dict())

    decision_dict: Optional[dict[str, Any]] = None
    if result.outcome == "admit":
        transition_code = "T2" if result.override_path else "T1"
        ownership, audit, changed = apply_transition(
            ownership,
            transition_code=transition_code,
            evidence_refs=list(candidate.evidence_ids) + [result.admission_id],
            correlation_id=correlation_id,
        )
        store.set_ownership(ownership)
        store.append_transition(audit)
        audits.append(audit.to_dict())

        if changed or not store.has_open_fingerprint(candidate.store_slug, candidate.recovery_key, fp):
            # Create Decision only if no open duplicate
            if not store.has_open_fingerprint(candidate.store_slug, candidate.recovery_key, fp):
                action = result.expected_merchant_action or "primary_action"
                decision = DecisionRecord(
                    decision_id=allocate_decision_id(),
                    recovery_key=candidate.recovery_key,
                    store_slug=candidate.store_slug,
                    admission_id=result.admission_id,
                    admission_rule_id=result.matrix_row_id,
                    governing_reason=result.governing_reason,
                    execution_owner=ownership.execution_owner,
                    decision_owner=ownership.decision_owner,
                    override_mode=ownership.override_mode,
                    decision_class="override" if result.override_path else "normal",
                    required_action=action,
                    explanation=_explanation_for_admit(candidate, result.governing_reason, action),
                    evidence_refs=list(candidate.evidence_ids),
                    evidence_fingerprint=fp,
                    admitted_at=result.evaluated_at,
                    status="open",
                    order_key=result.evaluated_at,
                )
                store.put_decision(decision)
                decision_dict = decision.to_dict()

    # Completion candidacy path (R11) — record rollup side-effect without Decision
    if candidate.journey_completed or (candidate.signal_class or "").lower() == "purchase_completed":
        ownership, audit, changed = apply_transition(
            ownership,
            transition_code="T10",
            evidence_refs=list(candidate.evidence_ids),
            correlation_id=correlation_id,
        )
        store.set_ownership(ownership)
        store.append_transition(audit)
        audits.append(audit.to_dict())
        # Close any open decisions for subject
        for d in list(store.open_decisions(candidate.store_slug)):
            if d.recovery_key == candidate.recovery_key:
                store.close_decision(d.decision_id, resolved_at=_utc_now_iso())
                own2 = store.get_ownership(candidate.store_slug, candidate.recovery_key)
                own2, audit2, _ = apply_transition(
                    own2,
                    transition_code="T5",
                    evidence_refs=list(candidate.evidence_ids),
                    correlation_id=correlation_id,
                )
                store.set_ownership(own2)
                store.append_transition(audit2)
                audits.append(audit2.to_dict())
        store.record_completion(candidate.store_slug, candidate.recovery_key, at=_utc_now_iso())

    projection = build_workspace_projection(candidate.store_slug, store)
    return {
        "admission": result.to_dict(),
        "ownership": store.get_ownership(candidate.store_slug, candidate.recovery_key).to_dict(),
        "decision": decision_dict,
        "transitions": audits,
        "projection": projection.to_dict(),
    }


def shadow_snapshot(store_slug: str, *, store: Optional[ShadowStoreV1] = None) -> dict[str, Any]:
    """Dev endpoint payload — internal operational truth only."""
    store = store or SHADOW_STORE
    projection = build_workspace_projection(store_slug, store)
    decisions = [d.to_dict() for d in store.all_decisions(store_slug)]
    open_ids = {d["decision_id"] for d in decisions if d.get("status") == "open"}
    ownership_rows = []
    # Collect ownership for subjects in decisions + any store keys
    seen = set()
    for d in decisions:
        key = (d["store_slug"], d["recovery_key"])
        if key in seen:
            continue
        seen.add(key)
        ownership_rows.append(store.get_ownership(d["store_slug"], d["recovery_key"]).to_dict())

    zone_assignment = {
        "zone_a": [c["decision_id"] for c in projection.zone_a],
        "zone_b": [c["decision_id"] for c in projection.zone_b],
        "zone_c_visible": bool((projection.zone_c or {}).get("visible")),
        "zone_d_completed_count": (projection.zone_d or {}).get("completed_count"),
        "zone_e": projection.zone_e,
    }
    return {
        "ok": True,
        "mode": "shadow",
        "feature_flag": cart_workspace_v1_flag_state(),
        "store_slug": store_slug,
        "decision_records": decisions,
        "open_decision_ids": sorted(open_ids),
        "ownership": ownership_rows,
        "admission_ledger_tail": store.list_admissions()[-20:],
        "transitions_tail": store.list_transitions(store_slug)[-20:],
        "projection": projection.to_dict(),
        "zone_assignment": zone_assignment,
        "projection_version": projection.projection_version,
        "merchant_surface_active": False,
    }


# Built-in deterministic scenarios for /dev endpoint validation
SCENARIOS: dict[str, list[dict[str, Any]]] = {
    "quiet": [
        {
            "store_slug": "demo",
            "recovery_key": "rk-quiet-1",
            "signal_class": "hesitation",
            "proof_class": "weak",
            "evidence_ids": ["ev-weak-1"],
            "proof_sufficient": False,
            "automation_capable": True,
            "human_gain_exceeds_cost": False,
        }
    ],
    "r03_admit": [
        {
            "store_slug": "demo",
            "recovery_key": "rk-r03-1",
            "signal_class": "hesitation",
            "proof_class": "automation_exhausted",
            "evidence_ids": ["ev-exh-1"],
            "proof_sufficient": True,
            "automation_capable": False,
            "human_gain_exceeds_cost": True,
            "expected_action": "approve_next_step",
        }
    ],
    "r07_override": [
        {
            "store_slug": "demo",
            "recovery_key": "rk-vip-1",
            "signal_class": "vip_detect",
            "proof_class": "override_eligible",
            "evidence_ids": ["ev-vip-1"],
            "proof_sufficient": True,
            "override_eligible": True,
            "automation_capable": True,
            "human_gain_exceeds_cost": True,
            "expected_action": "override_decision_action",
        }
    ],
    "r11_completed": [
        {
            "store_slug": "demo",
            "recovery_key": "rk-done-1",
            "signal_class": "purchase_completed",
            "proof_class": "terminal_completion",
            "evidence_ids": ["ev-purchase-1"],
            "proof_sufficient": True,
            "journey_completed": True,
            "automation_capable": False,
        }
    ],
    "duplicate_fingerprint": [
        {
            "store_slug": "demo",
            "recovery_key": "rk-dup-1",
            "signal_class": "hesitation",
            "proof_class": "automation_exhausted",
            "evidence_ids": ["ev-dup-1"],
            "proof_sufficient": True,
            "automation_capable": False,
            "human_gain_exceeds_cost": True,
            "expected_action": "approve_next_step",
        },
        {
            "store_slug": "demo",
            "recovery_key": "rk-dup-1",
            "signal_class": "refresh",
            "proof_class": "automation_exhausted",
            "evidence_ids": ["ev-dup-1"],
            "proof_sufficient": True,
            "automation_capable": False,
            "human_gain_exceeds_cost": True,
            "is_refresh_same_fingerprint": True,
            "expected_action": "approve_next_step",
        },
    ],
}


def run_scenario(name: str, *, store: Optional[ShadowStoreV1] = None, reset: bool = True) -> dict[str, Any]:
    from services.cart_workspace.admission_v1 import candidate_from_dict

    store = store or SHADOW_STORE
    if reset:
        store.reset()
    steps = SCENARIOS.get(name)
    if not steps:
        return {"ok": False, "error": f"unknown_scenario:{name}", "known": sorted(SCENARIOS.keys())}
    results = []
    store_slug = "demo"
    for step in steps:
        store_slug = str(step.get("store_slug") or store_slug)
        cand = candidate_from_dict(step)
        results.append(evaluate_candidate(cand, store=store))
    snap = shadow_snapshot(store_slug, store=store)
    snap["scenario"] = name
    snap["scenario_steps"] = results
    return snap
