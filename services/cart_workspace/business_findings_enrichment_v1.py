# -*- coding: utf-8 -*-
"""
Gate 2 — enrich Cart Workspace projection with BFL + Finding Decision Engine.

Sole merchant paint path for business Decisions. MEIF Decision root is retired.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

ENV_DECISION_DUAL_STACK_V1 = "CARTFLOW_DECISION_DUAL_STACK_V1"


def decision_dual_stack_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_DECISION_DUAL_STACK_V1, "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _confidence_ar(level: str) -> str:
    raw = (level or "").strip().lower()
    if raw in {"high", "مرتفع", "strong"}:
        return "مرتفع"
    if raw in {"medium", "متوسط", "moderate"}:
        return "متوسط"
    if raw in {"low", "منخفض", "weak"}:
        return "منخفض"
    if raw in {"none", ""}:
        return "غير متاح"
    return level or "غير متاح"


def fde_card_from_contract_v1(contract: Mapping[str, Any]) -> dict[str, Any] | None:
    """Map one MEBF finding contract (+ FDE) into a CW projection card."""
    if not isinstance(contract, Mapping):
        return None
    fid = _norm(contract.get("finding_id"))
    if not fid:
        return None
    dec = contract.get("merchant_decision_v1")
    if not isinstance(dec, Mapping):
        dec = {}
    has_decision = bool(dec.get("has_decision"))
    status = _norm(dec.get("status") or ("DECISION" if has_decision else "NO_DECISION"))
    title = _norm(
        dec.get("decision")
        or contract.get("title")
        or contract.get("merchant_statement_ar")
    )
    why = _norm(dec.get("why") or contract.get("explanation"))
    impact = _norm(dec.get("expected_business_impact"))
    action = _norm(
        dec.get("required_merchant_action") or contract.get("recommended_action")
    )
    evidence = _norm(dec.get("evidence_summary") or contract.get("evidence_summary"))
    conf = _norm(dec.get("decision_confidence") or contract.get("confidence"))
    missing = _norm(dec.get("missing_evidence"))

    if status == "NO_DECISION" or not has_decision:
        sentence = missing or "أدلة غير كافية لإصدار قرار — لا إجراء مُخترع."
        action_label = "مراجعة الأدلة"
        required_action = "review_evidence_only"
    else:
        sentence = why or title or "قرار تجاري يحتاج مراجعتك."
        action_label = action or "راجع القرار"
        required_action = "review_business_decision"

    return {
        "decision_id": f"fde:{fid}",
        "card_kind": "business_finding",
        "finding_id": fid,
        "finding_type": _norm(contract.get("finding_type")),
        "decision_class": "business_finding",
        "required_action": required_action,
        "action_label_ar": action_label,
        "title_ar": title or "قرار تجاري",
        "governing_reason": "finding_decision_engine_v1",
        "admission_rule_id": "gate_2_fde_enrichment",
        "explanation": {
            "why_here": why,
            "cartflow_did": "",
            "why_stopped": missing if status == "NO_DECISION" else "",
            "expected_after": impact,
        },
        "evidence_summary": evidence,
        "evidence_refs": [],
        "decision_confidence": conf,
        "decision_confidence_ar": _confidence_ar(conf),
        "expected_business_impact": impact,
        "required_merchant_action": action,
        "decision_status": status,
        "has_decision": has_decision and status == "DECISION",
        "missing_evidence": missing,
        "merchant_decision_v1": dict(dec) if dec else {},
        "order_key": f"0-fde-{fid}",
        "status": "open",
        "decision_owner": "merchant",
        "execution_owner": "cartflow",
        "commands_enabled": False,
    }


def list_fde_workspace_cards_v1(
    store_slug: str,
    *,
    mark_displayed: bool = False,
) -> list[dict[str, Any]]:
    """Load BFL-bound findings with FDE and project Workspace cards."""
    slug = _norm(store_slug)
    if not slug:
        return []
    try:
        from services.merchant_experience_business_findings_binding_v1 import (  # noqa: PLC0415
            PAGE_DECISION,
            PAGE_HOME,
            load_bound_findings_v1,
        )
    except Exception:  # noqa: BLE001
        return []

    bound = load_bound_findings_v1(slug, mark_displayed=mark_displayed)
    by_surface = bound.get("by_surface") if isinstance(bound, Mapping) else {}
    if not isinstance(by_surface, Mapping):
        by_surface = {}
    # Prefer decision_workspace surface; fall back to all bound findings.
    pool = list(by_surface.get(PAGE_DECISION) or [])
    if not pool:
        pool = list(bound.get("findings") or [])
    if not pool:
        pool = list(by_surface.get(PAGE_HOME) or [])

    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for contract in pool:
        if not isinstance(contract, Mapping):
            continue
        card = fde_card_from_contract_v1(contract)
        if not card:
            continue
        did = card["decision_id"]
        if did in seen:
            continue
        seen.add(did)
        cards.append(card)
    return cards


def enrich_projection_with_fde_v1(
    projection: dict[str, Any] | None,
    store_slug: str,
) -> dict[str, Any]:
    """
    Merge FDE business Decision cards into zone_b (ahead of ops cards).
    Mutates and returns projection dict.
    """
    if not isinstance(projection, dict):
        return {}
    slug = _norm(store_slug) or _norm(projection.get("store_slug"))
    fde_cards = list_fde_workspace_cards_v1(slug, mark_displayed=False)
    zone_a = list(projection.get("zone_a") or [])
    zone_b = list(projection.get("zone_b") or [])
    # Keep ops cards; prepend business findings.
    ops_b = [c for c in zone_b if isinstance(c, dict) and c.get("card_kind") != "business_finding"]
    # Drop prior fde: ids if re-enriching
    ops_b = [c for c in ops_b if not str(c.get("decision_id") or "").startswith("fde:")]
    zone_b = fde_cards + ops_b
    projection["zone_b"] = zone_b
    projection["zone_a"] = zone_a
    quiet = not zone_a and not zone_b
    projection["quiet"] = quiet
    if zone_a:
        projection["attention_focus_decision_id"] = zone_a[0].get("decision_id")
    elif zone_b:
        projection["attention_focus_decision_id"] = zone_b[0].get("decision_id")
    else:
        projection["attention_focus_decision_id"] = None
    projection["mission_question"] = "ماذا يجب أن أقرر الآن، ولماذا؟"
    projection["gate_2_single_decision_owner"] = True
    projection["business_finding_count"] = len(fde_cards)
    labels = dict(projection.get("zone_labels") or {})
    labels["B"] = "ما يحتاج قرارك"
    projection["zone_labels"] = labels
    return projection


def count_fde_decisions_for_teaser_v1(store_slug: str) -> dict[str, Any]:
    """Lightweight Home teaser inputs from FDE without fat MEIF."""
    cards = list_fde_workspace_cards_v1(store_slug, mark_displayed=False)
    decided = [c for c in cards if c.get("has_decision")]
    top_title = ""
    if decided:
        top_title = _norm(decided[0].get("title_ar") or decided[0].get("required_merchant_action"))
    elif cards:
        top_title = ""
    return {
        "count": len(decided),
        "top_title_ar": top_title,
        "evidence": "finding_decision_engine" if decided else "none",
        "total_findings": len(cards),
    }


__all__ = [
    "ENV_DECISION_DUAL_STACK_V1",
    "count_fde_decisions_for_teaser_v1",
    "decision_dual_stack_v1_enabled",
    "enrich_projection_with_fde_v1",
    "fde_card_from_contract_v1",
    "list_fde_workspace_cards_v1",
]
