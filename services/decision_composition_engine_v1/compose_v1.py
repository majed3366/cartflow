# -*- coding: utf-8 -*-
"""
Canonical Decision Composition pipeline:

Truth Inputs → Candidate → Evidence Sufficiency → Business Meaning
→ Priority → Recommended Action → Contract Validation → Cart Workspace
"""
from __future__ import annotations

from typing import Any

from services.decision_composition_engine_v1.compose_finding_v1 import (
    compose_from_finding_contract_v1,
)
from services.decision_composition_engine_v1.compose_recoverability_v1 import (
    compose_recoverability_gap_v1,
)
from services.decision_composition_engine_v1.compose_waiting_v1 import (
    compose_waiting_recovery_v1,
)
from services.decision_composition_engine_v1.contract_v1 import (
    BAND_NEEDS_ACTION,
    COMPOSITION_VERSION_V1,
    SUPPRESS_DUPLICATE,
)
from services.decision_composition_engine_v1.inputs_v1 import (
    load_bound_finding_inputs_v1,
    load_store_counter_inputs_v1,
)
from services.decision_composition_engine_v1.suppress_v1 import (
    apply_contract_gate,
    dedupe_key,
    mark_suppressed,
)


def compose_decisions_v1(store_slug: str) -> dict[str, Any]:
    """
    Run the sole composition path for a store.

    Returns package with published decisions (priority desc) and suppression registry.
    """
    slug = str(store_slug or "").strip()
    counters = load_store_counter_inputs_v1(slug)
    findings = load_bound_finding_inputs_v1(slug)

    registry: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    # 1) Recoverability gap
    rec = compose_recoverability_gap_v1(counters)
    if rec:
        candidates.append(rec)

    # 2) Waiting recovery (merchant-needed only)
    wait = compose_waiting_recovery_v1(counters)
    if wait:
        candidates.append(wait)

    # 3) Verified findings
    for contract in findings:
        composed = compose_from_finding_contract_v1(contract, store_slug=slug)
        if composed:
            candidates.append(composed)

    # Deduplicate + contract gate
    seen: set[str] = set()
    published: list[dict[str, Any]] = []
    for cand in candidates:
        if cand.get("suppressed"):
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": cand.get("suppression_reason"),
                    "decision_type": cand.get("decision_type"),
                }
            )
            continue
        key = dedupe_key(cand)
        if key in seen:
            cand = mark_suppressed(cand, SUPPRESS_DUPLICATE)
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": SUPPRESS_DUPLICATE,
                    "decision_type": cand.get("decision_type"),
                }
            )
            continue
        seen.add(key)
        gated = apply_contract_gate(dict(cand))
        if gated.get("suppressed"):
            registry.append(
                {
                    "decision_id": gated.get("decision_id"),
                    "suppression_reason": gated.get("suppression_reason"),
                    "decision_type": gated.get("decision_type"),
                }
            )
            continue
        published.append(gated)

    published.sort(
        key=lambda d: (
            0 if d.get("priority_band") == BAND_NEEDS_ACTION else 1,
            -int(d.get("priority") or 0),
            str(d.get("decision_id") or ""),
        )
    )

    needs = [d for d in published if d.get("priority_band") == BAND_NEEDS_ACTION]
    monitor = [d for d in published if d.get("priority_band") != BAND_NEEDS_ACTION]

    return {
        "ok": True,
        "store_slug": slug,
        "composition_version": COMPOSITION_VERSION_V1,
        "decisions": published,
        "needs_action_now": needs,
        "monitor": monitor,
        "suppression_registry": registry,
        "counts": {
            "published": len(published),
            "suppressed": len(registry),
            "needs_action_now": len(needs),
            "monitor": len(monitor),
            "candidates_total": len(candidates),
        },
        "no_decision_supported": len(published) == 0,
    }


__all__ = ["compose_decisions_v1"]
