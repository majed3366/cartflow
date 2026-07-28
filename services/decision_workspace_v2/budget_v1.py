# -*- coding: utf-8 -*-
"""
Decision Workspace Reality UX V1 — Executive Compression face.

Merchant-visible: What → Why → Can I act now → Where (when applicable).
One Primary + ≤3 Next. Diagnostic Primary for Home continuity.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_workspace_v2.flag_v1 import decision_workspace_v2_enabled
from services.decision_workspace_v2.narrative_v1 import (
    act_now_ar_v1,
    avoid_ar_v1,
    card_from_diagnostic_publication_v1,
    cartflow_responsibility_ar_v1,
    commitment_ar_v1,
    confidence_ar_v1,
    consequence_ar_v1,
    destination_for_commitment_v1,
    diagnosis_ar_v1,
    execution_domain_v1,
    execution_readiness_v1,
    expected_outcome_ar_v1,
    how_execute_ar_v1,
    verify_ar_v1,
    where_execute_ar_v1,
    why_believe_ar_v1,
)

MAX_NEXT_DECISIONS_V2 = 3


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _is_constitution_card(card: Mapping[str, Any]) -> bool:
    if card.get("constitution_v1") or card.get("gate_2b_composition") or card.get(
        "gate_commerce_situations"
    ):
        return True
    kind = _norm(card.get("card_kind"))
    return kind in {
        "business_finding",
        "operational_truth",
        "composed_decision",
        "commerce_situation",
    }


def hydrate_decision_card_v2(card: dict[str, Any], *, is_primary: bool) -> dict[str, Any]:
    """Stamp Reality UX compressed fields (internals kept for compat, not painted)."""
    out = dict(card)
    diagnosis = diagnosis_ar_v1(out)
    why = why_believe_ar_v1(out, diagnosis)
    # Trust from precision: prefer store-specific diagnosis when why is generic.
    if why.startswith("لأن ملاحظات المتجر") and diagnosis:
        why = diagnosis
    consequence = consequence_ar_v1(out)
    readiness = execution_readiness_v1(out)
    domain = execution_domain_v1(out)
    commitment = commitment_ar_v1(out)
    outcome = expected_outcome_ar_v1(out, consequence)
    href, label = destination_for_commitment_v1(out)
    act_now = act_now_ar_v1(out, readiness)
    where = where_execute_ar_v1(out, domain, readiness)

    out["diagnosis_ar"] = diagnosis
    out["reasoning_ar"] = why
    out["why_believe_ar"] = why
    out["confidence_ar"] = confidence_ar_v1(out)
    out["ignore_consequence_ar"] = consequence
    out["business_consequence_ar"] = consequence
    out["cartflow_responsibility_ar"] = cartflow_responsibility_ar_v1(out)
    out["execution_readiness"] = readiness
    out["execution_readiness_ar"] = act_now
    out["act_now_ar"] = act_now
    out["execution_domain"] = domain
    out["execution_where_ar"] = where
    out["execution_how_ar"] = how_execute_ar_v1(out, domain, readiness)
    out["execution_avoid_ar"] = avoid_ar_v1(out, readiness)
    out["execution_verify_ar"] = verify_ar_v1(out, readiness)
    out["commitment_ar"] = commitment
    out["first_step_ar"] = commitment
    out["required_merchant_action"] = commitment
    out["expected_outcome_ar"] = outcome
    out["view_details_href"] = href
    out["view_details_ar"] = label
    out["decision_workspace_v2"] = True
    out["decision_workspace_refinement_v1"] = True
    out["decision_workspace_refinement_v2"] = True
    out["decision_workspace_reality_ux_v1"] = True
    out["is_primary_decision"] = bool(is_primary)
    out["face_mode"] = "primary" if is_primary else "next_compact"
    if is_primary:
        out["priority_rank_label_ar"] = "قرارك الآن"
        out["priority_rank_role"] = "primary"
    else:
        out["priority_rank_label_ar"] = "بعده"
        out["priority_rank_role"] = "next"
        out["next_stake_ar"] = consequence
    if _norm(out.get("decision_ar")) == commitment:
        out["decision_ar"] = diagnosis
    if _norm(out.get("title_ar")) == commitment:
        out["title_ar"] = diagnosis
    return out


def _inject_diagnostic_primary(
    constitution: list[dict[str, Any]],
    store_slug: str,
) -> list[dict[str, Any]]:
    """Home continuity: diagnostic publication wins Primary when present."""
    try:
        from services.diagnostic_reasoning_v1.snapshot_store_v1 import (  # noqa: PLC0415
            read_primary_diagnostic_publication_v1,
        )

        pub = read_primary_diagnostic_publication_v1(store_slug)
    except Exception:  # noqa: BLE001
        pub = None
    if not isinstance(pub, Mapping) or not _norm(pub.get("diagnosis_ar") or pub.get("observation_ar")):
        return constitution

    diag_card = card_from_diagnostic_publication_v1(pub)
    diag_id = _norm(diag_card.get("decision_id"))
    rest: list[dict[str, Any]] = []
    for c in constitution:
        cid = _norm(c.get("decision_id"))
        if cid == diag_id:
            continue
        # Avoid duplicate shipping/product story as competing primary.
        c2 = dict(c)
        c2["is_primary_decision"] = False
        rest.append(c2)
    return [diag_card] + rest


def apply_decision_workspace_v2_budget(
    projection: dict[str, Any] | None,
    *,
    store_slug: str | None = None,
) -> dict[str, Any]:
    """Enforce 1 Primary + ≤3 Next; Refinement V1 narrative; diagnostic continuity."""
    if not isinstance(projection, dict):
        return {}
    if not decision_workspace_v2_enabled():
        return projection

    zone_b = [c for c in list(projection.get("zone_b") or []) if isinstance(c, dict)]
    zone_a = [c for c in list(projection.get("zone_a") or []) if isinstance(c, dict)]

    constitution = [c for c in zone_b if _is_constitution_card(c)]
    if not constitution:
        constitution = list(zone_b) or list(zone_a)

    slug = _norm(store_slug or projection.get("store_slug"))
    if slug:
        constitution = _inject_diagnostic_primary(constitution, slug)

    primary: dict[str, Any] | None = None
    rest: list[dict[str, Any]] = []
    for c in constitution:
        if c.get("is_primary_decision") and primary is None:
            primary = c
        else:
            rest.append(c)
    if primary is None and constitution:
        primary = constitution[0]
        rest = constitution[1:]

    next_cards = rest[:MAX_NEXT_DECISIONS_V2]
    painted: list[dict[str, Any]] = []
    if primary is not None:
        painted.append(hydrate_decision_card_v2(primary, is_primary=True))
    for c in next_cards:
        painted.append(hydrate_decision_card_v2(c, is_primary=False))

    projection["zone_a"] = []
    projection["zone_b"] = painted
    projection["quiet"] = not painted
    if painted:
        projection["attention_focus_decision_id"] = painted[0].get("decision_id")
    else:
        projection["attention_focus_decision_id"] = None

    projection["mission_question"] = "ما الذي يجب أن أفعله الآن؟"
    projection["decision_workspace_v2"] = True
    projection["decision_workspace_refinement_v1"] = True
    projection["decision_workspace_refinement_v2"] = True
    projection["decision_workspace_reality_ux_v1"] = True
    projection["decision_workspace_v2_budget"] = {
        "primary": 1 if painted else 0,
        "next": max(0, len(painted) - 1),
        "max_next": MAX_NEXT_DECISIONS_V2,
        "future_waiting": max(0, len(rest) - MAX_NEXT_DECISIONS_V2),
        "diagnostic_primary": bool(
            painted and painted[0].get("gate_diagnostic_continuity_v1")
        ),
    }

    comp = projection.get("decision_composition_v1")
    if isinstance(comp, dict):
        comp = dict(comp)
        comp["category_landscape"] = []
        comp["needs_action_now"] = 1 if painted else 0
        comp["monitor"] = 0
        projection["decision_composition_v1"] = comp
    else:
        projection["decision_composition_v1"] = {
            "category_landscape": [],
            "needs_action_now": 1 if painted else 0,
            "monitor": 0,
        }

    return projection


__all__ = [
    "MAX_NEXT_DECISIONS_V2",
    "apply_decision_workspace_v2_budget",
    "hydrate_decision_card_v2",
]
