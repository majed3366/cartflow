# -*- coding: utf-8 -*-
"""
MEH V1 — Capability Gap Register (Category B only).

These cannot be solved without new platform capabilities.
Do not implement workarounds that invent intelligence or expand SCF inputs.
"""
from __future__ import annotations

from typing import Any

CAPABILITY_GAPS_V1: list[dict[str, Any]] = [
    {
        "gap_id": "CG-MEH-01",
        "finding_ids": ["MEV1-H03", "MEV1-K03"],
        "title": "Time-aligned Knowledge vs wall-clock merchant reads",
        "required_future_capability": "Time Authority consumer binding for all merchant Knowledge/Home reads",
        "architectural_reason": (
            "Knowledge and Home semantic composition evaluate wall-clock windows while "
            "Reality history may sit in a different temporal context. MEIF can surface "
            "as_of/window cues but cannot re-anchor Knowledge generation."
        ),
        "why_existing_stack_cannot_solve": (
            "Forbidden to redesign Time Authority or rewrite Knowledge Foundation in MEH. "
            "Existing Time Authority behavior alone does not force merchant-page as_of binding."
        ),
        "affected_layer": "Time Authority → Knowledge → MEIF consumer",
    },
    {
        "gap_id": "CG-MEH-02",
        "finding_ids": ["MEV1-D02", "MEV1-C02", "MEV1-S02"],
        "title": "Operational Truth as Surface Composition input",
        "required_future_capability": (
            "Governed Operational Truth / Merchant Operational State as first-class SCF inputs"
        ),
        "architectural_reason": (
            "SCF V1 consumes Presentation + Knowledge only. Empty-states and decision pressure "
            "cannot see durable carts/WA activity at composition time."
        ),
        "why_existing_stack_cannot_solve": (
            "Explicitly forbidden to expand Surface Composition inputs in MEH. "
            "MEIF may suppress false empty-states at the page bridge, but cannot make SCF compose ops."
        ),
        "affected_layer": "Surface Composition input boundary",
    },
    {
        "gap_id": "CG-MEH-03",
        "finding_ids": ["MEV1-C01", "MEV1-C03"],
        "title": "Durable cart list projection / identity-time window",
        "required_future_capability": (
            "Cart list projection that materializes durable AbandonedCart rows into merchant queue"
        ),
        "architectural_reason": (
            "Dashboard normal-carts API can return empty while AbandonedCart rows exist "
            "(identity/window/projection mismatch)."
        ),
        "why_existing_stack_cannot_solve": (
            "MEIF can forbid false please-wait and show ops counts, but cannot invent a cart "
            "queue without a governed cart projection capability."
        ),
        "affected_layer": "Cart projection / Identity",
    },
    {
        "gap_id": "CG-MEH-04",
        "finding_ids": ["MEV1-M02"],
        "title": "Communication follow-up operations projection",
        "required_future_capability": (
            "Communication ops projection (follow-up queue) distinct from Settings WhatsApp config"
        ),
        "architectural_reason": (
            "Mock sends and schedules are durable facts; no governed follow-up queue surface exists."
        ),
        "why_existing_stack_cannot_solve": (
            "MEIF can show activity counts and SCF communication items, but cannot create a "
            "follow-up work queue without a new Communication projection capability."
        ),
        "affected_layer": "Communication projection / Guidance Routing follow_up scope",
    },
    {
        "gap_id": "CG-MEH-05",
        "finding_ids": ["MEV1-G01", "MEV1-G03"],
        "title": "Operationally useful Commercial Guidance product policy",
        "required_future_capability": (
            "Guidance eligibility/registry policy that emits actionable ops guidance "
            "(not monitor-only) with merchant-facing confidence"
        ),
        "architectural_reason": (
            "Current Guidance may correctly emit monitor_new_pattern while merchants need "
            "shipping/price/recovery operational advice."
        ),
        "why_existing_stack_cannot_solve": (
            "Forbidden to add new Guidance engines or eligibility logic in MEH. "
            "MEIF may demote/label confusing monitor guidance at presentation, not invent actions."
        ),
        "affected_layer": "Commercial Guidance registry / eligibility",
    },
    {
        "gap_id": "CG-MEH-06",
        "finding_ids": ["MEV1-H04"],
        "title": "Setup lifecycle vs lived Reality history",
        "required_future_capability": (
            "Setup/activation lifecycle that yields to durable operational history"
        ),
        "architectural_reason": (
            "Onboarding remaining_setup can remain prominent after Reality history exists."
        ),
        "why_existing_stack_cannot_solve": (
            "MEIF can suppress setup theatre when durable carts exist (presentation), "
            "but cannot rewrite setup lifecycle ownership without a new capability."
        ),
        "affected_layer": "Merchant setup lifecycle",
    },
]


def capability_gaps_v1() -> dict[str, Any]:
    return {
        "version": "meh_gaps_v1",
        "gaps": list(CAPABILITY_GAPS_V1),
        "count": len(CAPABILITY_GAPS_V1),
    }


def finding_to_gap_ids_v1() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for g in CAPABILITY_GAPS_V1:
        for fid in g.get("finding_ids") or []:
            out.setdefault(str(fid), []).append(str(g["gap_id"]))
    return out


__all__ = [
    "CAPABILITY_GAPS_V1",
    "capability_gaps_v1",
    "finding_to_gap_ids_v1",
]
