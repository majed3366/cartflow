# -*- coding: utf-8 -*-
"""
Gate 2 — enrich Cart Workspace projection with BFL + Finding Decision Engine.

Sole merchant paint path for business Decisions. MEIF Decision root is retired.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

ENV_DECISION_DUAL_STACK_V1 = "CARTFLOW_DECISION_DUAL_STACK_V1"
INSUFFICIENT_EVIDENCE_AR = "لا توجد أدلة كافية لإصدار قرار."


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

    decided = has_decision and status == "DECISION"
    evidence_out = evidence if evidence else (INSUFFICIENT_EVIDENCE_AR if not decided else "")
    return {
        "decision_id": f"fde:{fid}",
        "card_kind": "business_finding",
        "finding_id": fid,
        "finding_type": _norm(contract.get("finding_type")),
        "decision_class": "business_finding",
        "constitution_v1": True,
        "required_action": required_action,
        "action_label_ar": action_label,
        "title_ar": title or "قرار تجاري",
        "decision_ar": title or "قرار تجاري",
        "why_ar": why or (missing if not decided else ""),
        "governing_reason": "finding_decision_engine_v1",
        "admission_rule_id": "gate_2_fde_enrichment",
        "explanation": {
            "why_here": why,
            "cartflow_did": "",
            "why_stopped": missing if status == "NO_DECISION" else "",
            "expected_after": impact,
        },
        "evidence_summary": evidence_out,
        "evidence_refs": [],
        "decision_confidence": conf if decided else "",
        "decision_confidence_ar": _confidence_ar(conf) if decided and conf else "",
        "expected_business_impact": impact,
        "required_merchant_action": action or ("لا إجراء مطلوب حالياً" if not decided else action_label),
        "view_details_href": "",
        "view_details_ar": "عرض التفاصيل",
        "decision_status": status,
        "has_decision": decided,
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


def _normalize_constitution_fields(card: dict[str, Any]) -> dict[str, Any]:
    """Ensure Decision / Why / Evidence / Confidence / Action face fields."""
    if not isinstance(card, dict):
        return card
    card["constitution_v1"] = True
    if not _norm(card.get("decision_ar")):
        card["decision_ar"] = _norm(card.get("title_ar") or card.get("action_label_ar"))
    why = _norm(card.get("why_ar"))
    ex = card.get("explanation")
    if not why and isinstance(ex, Mapping):
        why = _norm(ex.get("why_here"))
    if why:
        card["why_ar"] = why
    if not _norm(card.get("evidence_summary")):
        missing = _norm(card.get("missing_evidence"))
        if missing or card.get("has_decision") is False:
            card["evidence_summary"] = INSUFFICIENT_EVIDENCE_AR
    conf = _norm(card.get("decision_confidence"))
    if conf and conf.lower() not in {"none", "unknown"}:
        card["decision_confidence_ar"] = _confidence_ar(conf)
    else:
        card.pop("decision_confidence_ar", None)
    if not _norm(card.get("required_merchant_action")):
        card["required_merchant_action"] = _norm(
            card.get("action_label_ar") or "لا إجراء مطلوب حالياً"
        )
    if not _norm(card.get("view_details_href")):
        # Default destination for business findings: stay on Workspace detail.
        if card.get("card_kind") == "business_finding":
            card["view_details_href"] = ""
    if not _norm(card.get("view_details_ar")) and _norm(card.get("view_details_href")):
        card["view_details_ar"] = "عرض التفاصيل"
    return card


def enrich_projection_with_fde_v1(
    projection: dict[str, Any] | None,
    store_slug: str,
) -> dict[str, Any]:
    """
    Sole merchant Decision paint path.

    Gate 2B: Decision Composition Engine composes validated Decisions.
    Falls back to Gate 2A FDE+OT path when DCE flag is OFF.
    """
    if not isinstance(projection, dict):
        return {}
    slug = _norm(store_slug) or _norm(projection.get("store_slug"))

    try:
        from services.decision_composition_engine_v1.flag_v1 import (  # noqa: PLC0415
            decision_composition_engine_v1_enabled,
        )

        dce_on = decision_composition_engine_v1_enabled()
    except Exception:  # noqa: BLE001
        dce_on = False

    if dce_on:
        return _enrich_via_composition_engine_v1(projection, slug)

    return _enrich_legacy_gate_2a_v1(projection, slug)


def _enrich_via_composition_engine_v1(
    projection: dict[str, Any],
    slug: str,
) -> dict[str, Any]:
    from services.decision_composition_engine_v1.compose_v1 import (  # noqa: PLC0415
        compose_decisions_v1,
    )
    from services.decision_composition_engine_v1.project_workspace_v1 import (  # noqa: PLC0415
        decisions_to_workspace_cards_v1,
    )

    pkg = compose_decisions_v1(slug, use_cache=True, allow_sync_miss=True)
    portfolio = list(pkg.get("portfolio") or pkg.get("decisions") or [])
    composed_cards = decisions_to_workspace_cards_v1(portfolio)

    zone_a = list(projection.get("zone_a") or [])
    zone_b_existing = list(projection.get("zone_b") or [])
    ops_b = [
        c
        for c in zone_b_existing
        if isinstance(c, dict)
        and c.get("card_kind")
        not in {"business_finding", "operational_truth", "composed_decision"}
        and not str(c.get("decision_id") or "").startswith("fde:")
        and not str(c.get("decision_id") or "").startswith("ops-truth:")
        and not str(c.get("decision_id") or "").startswith("dce:")
    ]
    # Shadow VIP ops remain secondary to composed business decisions.
    zone_b = [_normalize_constitution_fields(dict(c)) for c in (composed_cards + ops_b)]
    zone_a = [
        _normalize_constitution_fields(dict(c)) for c in zone_a if isinstance(c, dict)
    ]

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
    projection["gate_2a_decision_workspace_completion"] = True
    projection["gate_2b_decision_composition_engine"] = True
    projection["gate_2c_decision_portfolio"] = True
    projection["decisions_only"] = True
    projection["decision_composition_v1"] = {
        "version": pkg.get("composition_version"),
        "counts": pkg.get("counts"),
        "suppression_registry": pkg.get("suppression_registry"),
        "no_decision_supported": pkg.get("no_decision_supported"),
        "needs_action_now": len(pkg.get("needs_action_now") or []),
        "monitor": len(pkg.get("monitor") or []),
        "category_landscape": pkg.get("category_landscape"),
        "portfolio_version": pkg.get("portfolio_version"),
        "cache": pkg.get("_cache"),
        "timing_ms": pkg.get("timing_ms"),
    }
    projection["decision_portfolio_v1"] = {
        "portfolio": portfolio,
        "category_landscape": pkg.get("category_landscape"),
        "overflow": pkg.get("overflow"),
    }
    projection["business_finding_count"] = int(
        (pkg.get("counts") or {}).get("candidates_total") or 0
    )
    projection["operational_truth_count"] = 0
    projection["decision_card_count"] = len(zone_a) + len(zone_b)
    labels = dict(projection.get("zone_labels") or {})
    labels["B"] = "ما يحتاج قرارك"
    projection["zone_labels"] = labels
    projection["zone_c"] = {"visible": False, "summary": ""}
    projection["zone_d"] = {"visible": False, "completed_count": 0}
    return projection


def _enrich_legacy_gate_2a_v1(
    projection: dict[str, Any],
    slug: str,
) -> dict[str, Any]:
    """Rollback path when CARTFLOW_DECISION_COMPOSITION_ENGINE_V1=0."""
    fde_cards = list_fde_workspace_cards_v1(slug, mark_displayed=False)
    fde_decided = [c for c in fde_cards if c.get("has_decision")]
    fde_no = [c for c in fde_cards if not c.get("has_decision")]

    zone_a = list(projection.get("zone_a") or [])
    zone_b = list(projection.get("zone_b") or [])
    ops_b = [
        c
        for c in zone_b
        if isinstance(c, dict)
        and c.get("card_kind") not in {"business_finding", "operational_truth"}
        and not str(c.get("decision_id") or "").startswith("fde:")
        and not str(c.get("decision_id") or "").startswith("ops-truth:")
    ]

    try:
        from services.cart_workspace.operational_truth_decision_cards_v1 import (  # noqa: PLC0415
            list_operational_truth_decision_cards_v1,
        )

        ops_truth = list_operational_truth_decision_cards_v1(
            slug, existing_cards=fde_decided + fde_no + ops_b
        )
    except Exception:  # noqa: BLE001
        ops_truth = []

    primary = fde_decided + ops_truth
    if not primary and fde_no:
        primary = fde_no
    zone_b = [_normalize_constitution_fields(dict(c)) for c in (primary + ops_b)]
    zone_a = [
        _normalize_constitution_fields(dict(c)) for c in zone_a if isinstance(c, dict)
    ]

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
    projection["gate_2a_decision_workspace_completion"] = True
    projection["gate_2b_decision_composition_engine"] = False
    projection["decisions_only"] = True
    projection["business_finding_count"] = len(fde_cards)
    projection["operational_truth_count"] = len(ops_truth)
    projection["decision_card_count"] = len(zone_a) + len(zone_b)
    labels = dict(projection.get("zone_labels") or {})
    labels["B"] = "ما يحتاج قرارك"
    projection["zone_labels"] = labels
    projection["zone_c"] = {"visible": False, "summary": ""}
    projection["zone_d"] = {"visible": False, "completed_count": 0}
    return projection


def count_fde_decisions_for_teaser_v1(
    store_slug: str,
    *,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Home teaser — composed portfolio when DCE ON; else FDE-only legacy."""
    try:
        from services.decision_composition_engine_v1.flag_v1 import (  # noqa: PLC0415
            decision_composition_engine_v1_enabled,
        )
        from services.decision_composition_engine_v1.teaser_v1 import (  # noqa: PLC0415
            count_composed_decisions_for_teaser_v1,
        )

        if decision_composition_engine_v1_enabled():
            return count_composed_decisions_for_teaser_v1(
                store_slug, summary=summary
            )
    except Exception:  # noqa: BLE001
        pass

    cards = list_fde_workspace_cards_v1(store_slug, mark_displayed=False)
    decided = [c for c in cards if c.get("has_decision")]
    top_title = ""
    if decided:
        top_title = _norm(
            decided[0].get("title_ar") or decided[0].get("required_merchant_action")
        )
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
