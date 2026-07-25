# -*- coding: utf-8 -*-
"""Project composed Decision contracts → Cart Workspace constitution cards."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import confidence_ar


def _norm(v: Any) -> str:
    return str(v or "").strip()


def decision_to_workspace_card_v1(decision: Mapping[str, Any]) -> dict[str, Any]:
    conf = _norm(decision.get("confidence"))
    return {
        "decision_id": _norm(decision.get("decision_id")),
        "card_kind": "composed_decision",
        "decision_class": _norm(decision.get("decision_type")) or "composed_decision",
        "constitution_v1": True,
        "gate_2b_composition": True,
        "has_decision": True,
        "decision_status": "DECISION",
        "title_ar": _norm(decision.get("title") or decision.get("merchant_decision")),
        "decision_ar": _norm(decision.get("merchant_decision") or decision.get("title")),
        "why_ar": _norm(decision.get("why")),
        "why_now_ar": _norm(decision.get("why_now")),
        "evidence_summary": _norm(decision.get("evidence_summary")),
        "evidence_refs": list(decision.get("evidence_refs") or []),
        "ignore_consequence_ar": _norm(decision.get("ignore_consequence")),
        "required_merchant_action": _norm(decision.get("recommended_action")),
        "action_label_ar": _norm(decision.get("recommended_action")),
        "first_step_ar": _norm(decision.get("first_step")),
        "expected_outcome_ar": _norm(decision.get("expected_outcome")),
        "expected_business_impact": _norm(decision.get("expected_outcome")),
        "decision_confidence": conf,
        "decision_confidence_ar": confidence_ar(conf),
        "priority": int(decision.get("priority") or 0),
        "priority_band": _norm(decision.get("priority_band")),
        "portfolio_rank": int(decision.get("portfolio_rank") or 0) or None,
        "decision_category": _norm(decision.get("decision_category")),
        "decision_category_ar": _norm(decision.get("decision_category_ar")),
        "business_domain": _norm(
            decision.get("business_domain") or decision.get("decision_category")
        ),
        "root_cause_key": _norm(decision.get("root_cause_key")),
        "gate_2d_deduped": True,
        "view_details_href": _norm(decision.get("view_details_href")),
        "view_details_ar": "عرض التفاصيل",
        "explanation": {
            "why_here": _norm(decision.get("why")),
            "cartflow_did": "",
            "why_stopped": "",
            "expected_after": _norm(decision.get("expected_outcome")),
        },
        "commands_enabled": False,
        "composition_version": _norm(decision.get("composition_version")),
        "source_truth_types": list(decision.get("source_truth_types") or []),
        "order_key": f"0-{int(decision.get('priority') or 0):03d}-{_norm(decision.get('decision_id'))}",
        "status": "open",
    }


def decisions_to_workspace_cards_v1(
    decisions: list[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in decisions or []:
        if isinstance(d, Mapping) and d.get("published") is not False:
            if d.get("suppressed"):
                continue
            out.append(decision_to_workspace_card_v1(d))
    return out


__all__ = [
    "decision_to_workspace_card_v1",
    "decisions_to_workspace_cards_v1",
]
