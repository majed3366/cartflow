# -*- coding: utf-8 -*-
"""
Decision Workspace Simplification V1.

Merchant face only: Priority → Evidence → Decision → Action.
One Primary + ≤3 Next. Diagnostic Primary for Home continuity.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_workspace_v2.flag_v1 import decision_workspace_v2_enabled
from services.decision_workspace_v2.narrative_v1 import (
    action_is_ready_v1,
    action_wait_lines_ar_v1,
    act_now_ar_v1,
    avoid_ar_v1,
    card_from_diagnostic_publication_v1,
    cartflow_responsibility_ar_v1,
    commitment_ar_v1,
    consequence_ar_v1,
    decision_sentence_ar_v1,
    destination_for_commitment_v1,
    evidence_lines_ar_v1,
    execution_domain_v1,
    execution_readiness_v1,
    expected_outcome_ar_v1,
    how_execute_ar_v1,
    observation_ar_v1,
    operational_meaning_ar_v1,
    priority_rank_label_ar_v1,
    sanitize_merchant_story_text_v1,
    verify_ar_v1,
    where_execute_ar_v1,
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


def hydrate_decision_card_v2(
    card: dict[str, Any],
    *,
    is_primary: bool,
    next_index: int = 0,
) -> dict[str, Any]:
    """Stamp Simplification V1 face fields."""
    out = dict(card)
    observation = observation_ar_v1(out)
    evidence_lines = evidence_lines_ar_v1(out)
    meaning = operational_meaning_ar_v1(out, observation)  # internal only
    readiness = execution_readiness_v1(out)
    domain = execution_domain_v1(out)
    decision = decision_sentence_ar_v1(out)
    consequence = consequence_ar_v1(out)
    outcome = expected_outcome_ar_v1(out, consequence)
    href, label = destination_for_commitment_v1(out)
    where = where_execute_ar_v1(out, domain, readiness)
    how = how_execute_ar_v1(out, domain, readiness)
    action_ready = action_is_ready_v1(readiness)
    rank = priority_rank_label_ar_v1(
        is_primary=is_primary,
        next_index=next_index,
        readiness=readiness,
    )

    if not action_ready:
        href, label = "", ""

    out["observation_ar"] = observation
    out["evidence_lines_ar"] = evidence_lines
    out["evidence_ar"] = "\n".join(evidence_lines)
    out["diagnosis_ar"] = observation
    out["operational_meaning_ar"] = ""  # never merchant-facing
    out["reasoning_ar"] = ""
    out["why_believe_ar"] = ""
    out["confidence_ar"] = ""
    out["ignore_consequence_ar"] = consequence
    out["business_consequence_ar"] = consequence
    out["cartflow_responsibility_ar"] = cartflow_responsibility_ar_v1(out)
    out["execution_readiness"] = readiness
    out["execution_readiness_ar"] = act_now_ar_v1(out, readiness)
    out["act_now_ar"] = act_now_ar_v1(out, readiness)
    out["execution_domain"] = domain
    out["execution_where_ar"] = where if action_ready else ""
    out["execution_how_ar"] = how if action_ready else ""
    out["execution_what_ar"] = decision if action_ready else ""
    out["execution_avoid_ar"] = avoid_ar_v1(out, readiness)
    out["execution_verify_ar"] = verify_ar_v1(out, readiness) if action_ready else ""
    out["decision_sentence_ar"] = decision
    out["operational_guidance_ar"] = decision
    out["commitment_ar"] = decision
    out["first_step_ar"] = decision
    out["required_merchant_action"] = decision
    out["expected_outcome_ar"] = ""
    out["cartflow_continues_ar"] = ""
    out["priority_reason_ar"] = ""  # rank label only on face
    out["priority_rank_label_ar"] = rank
    out["action_wait_lines_ar"] = [] if action_ready else action_wait_lines_ar_v1()
    out["execution_available"] = action_ready
    out["view_details_href"] = href
    out["view_details_ar"] = label
    out["decision_workspace_v2"] = True
    out["decision_workspace_refinement_v1"] = True
    out["decision_workspace_refinement_v2"] = True
    out["decision_workspace_reality_ux_v1"] = True
    out["decision_workspace_operational_language_v1"] = True
    out["decision_workspace_storytelling_face_v1"] = True
    out["decision_workspace_simplification_v1"] = True
    out["is_primary_decision"] = bool(is_primary)
    out["face_mode"] = "primary" if is_primary else "next_compact"
    out["priority_rank_role"] = "primary" if is_primary else "next"
    if not is_primary:
        out["next_stake_ar"] = meaning
    if _norm(out.get("decision_ar")) == decision:
        out["decision_ar"] = observation
    if _norm(out.get("title_ar")) == decision:
        out["title_ar"] = observation
    for key in ("subject_ar", "product_name_ar"):
        if key in out:
            out[key] = sanitize_merchant_story_text_v1(_norm(out.get(key)))
    return out


def _inject_diagnostic_primary(
    constitution: list[dict[str, Any]],
    store_slug: str,
) -> list[dict[str, Any]]:
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
        c2 = dict(c)
        c2["is_primary_decision"] = False
        rest.append(c2)
    return [diag_card] + rest


def apply_decision_workspace_v2_budget(
    projection: dict[str, Any] | None,
    *,
    store_slug: str | None = None,
) -> dict[str, Any]:
    """Enforce 1 Primary + ≤3 Next; Simplification V1 face."""
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
        painted.append(hydrate_decision_card_v2(primary, is_primary=True, next_index=0))
    for i, c in enumerate(next_cards):
        painted.append(hydrate_decision_card_v2(c, is_primary=False, next_index=i))

    projection["zone_a"] = []
    projection["zone_b"] = painted
    projection["quiet"] = not painted
    if painted:
        projection["attention_focus_decision_id"] = painted[0].get("decision_id")
    else:
        projection["attention_focus_decision_id"] = None

    projection["mission_question"] = "ما الذي يحتاج انتباهك الآن؟"
    projection["decision_workspace_v2"] = True
    projection["decision_workspace_refinement_v1"] = True
    projection["decision_workspace_refinement_v2"] = True
    projection["decision_workspace_reality_ux_v1"] = True
    projection["decision_workspace_operational_language_v1"] = True
    projection["decision_workspace_storytelling_face_v1"] = True
    projection["decision_workspace_simplification_v1"] = True
    projection["decision_workspace_v2_budget"] = {
        "primary": 1 if painted else 0,
        "next": max(0, len(painted) - 1),
        "max_next": MAX_NEXT_DECISIONS_V2,
        "future_waiting": max(0, len(rest) - MAX_NEXT_DECISIONS_V2),
        "diagnostic_primary": bool(
            painted and painted[0].get("gate_diagnostic_continuity_v1")
        ),
        "simplification_v1": True,
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
