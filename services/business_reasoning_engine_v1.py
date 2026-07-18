# -*- coding: utf-8 -*-
"""
Business Reasoning Engine V1.

Transforms multiple validated Business Findings into merchant-ready guidance.
Consumes Findings only — never Truth/Evidence directly. Deterministic. No AI.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.business_findings_contract_v1 import norm
from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.business_reasoning_contract_v1 import (
    ENGINE_VERSION,
    REASONING_VERSION,
    finalize_reasoning,
    is_reasoning_worthy,
    select_approved_findings_v1,
    utc_now_iso,
)
from services.business_reasoning_rules_v1 import evaluate_all_reasoning_rules_v1


def score_reasoning_v1(card: Mapping[str, Any]) -> float:
    base = float(card.get("rank_score") or 0.0)
    conf = float(card.get("confidence_score") or 0.0)
    support = len(card.get("supporting_finding_ids") or [])
    return round(base + (conf * 5.0) + (support * 0.5), 3)


def project_reasoning_to_guidance_brief_v1(card: Mapping[str, Any]) -> dict[str, Any]:
    """Surface-ready brief — merchant fields only."""
    return {
        "reasoning_id": card.get("reasoning_id"),
        "headline": card.get("headline"),
        "business_meaning": card.get("business_meaning"),
        "recommended_priority": card.get("recommended_priority"),
        "expected_impact": card.get("expected_impact"),
        "confidence_level": card.get("confidence_level"),
        "certainty": card.get("certainty"),
        "supporting_finding_labels": list(card.get("supporting_finding_labels") or []),
    }


def project_reasoning_to_knowledge_item_v1(card: Mapping[str, Any]) -> dict[str, Any]:
    """
    Knowledge Routing candidate projection.

    Surfaces may consume later — this phase does not wire Home/Products/etc.
    """
    return {
        "knowledge_id": f"reason:{norm(card.get('reasoning_id'))}",
        "kind": "business_reasoning_v1",
        "title": card.get("headline"),
        "summary": card.get("business_meaning"),
        "recommended_priority": card.get("recommended_priority"),
        "expected_impact": card.get("expected_impact"),
        "confidence_level": card.get("confidence_level"),
        "certainty": card.get("certainty"),
        "supporting_finding_ids": list(card.get("supporting_finding_ids") or []),
        "supporting_finding_labels": list(card.get("supporting_finding_labels") or []),
        "aggregation_key": f"bre:{norm(card.get('reasoning_type'))}:{norm(card.get('store_slug'))}",
        "source_version": ENGINE_VERSION,
        "ai_used": False,
    }


def select_guidance_candidates_v1(cards: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """
    Consume feed for future surfaces (not wired in V1).

    - weekly_priority
    - primary_relationship
    - top_constraint
    - top_opportunity
    - open_conflict
    """
    by_type: dict[str, list[dict[str, Any]]] = {}
    for c in cards:
        by_type.setdefault(norm(c.get("reasoning_type")), []).append(dict(c))

    def _first(*types: str) -> Optional[dict[str, Any]]:
        for t in types:
            items = by_type.get(norm(t)) or []
            if items:
                return project_reasoning_to_guidance_brief_v1(items[0])
        return None

    from services.business_reasoning_contract_v1 import (  # noqa: PLC0415
        TYPE_CONFLICT,
        TYPE_CONSTRAINT,
        TYPE_OPPORTUNITY,
        TYPE_PRIORITY,
        TYPE_RELATIONSHIP,
    )

    return {
        "weekly_priority": _first(TYPE_PRIORITY),
        "primary_relationship": _first(TYPE_RELATIONSHIP),
        "top_constraint": _first(TYPE_CONSTRAINT),
        "top_opportunity": _first(TYPE_OPPORTUNITY),
        "open_conflict": _first(TYPE_CONFLICT),
    }


def run_business_reasoning_engine_v1(
    *,
    store_slug: str = "demo",
    findings: Optional[Sequence[Mapping[str, Any]]] = None,
    findings_package: Optional[Mapping[str, Any]] = None,
    demo_fixture: bool = False,
    window_days: int = 14,
) -> dict[str, Any]:
    """
    Produce reasoning cards from approved findings only.

    Input modes (exclusive preference order):
      1. findings — explicit list
      2. findings_package — output of Business Findings Engine
      3. demo_fixture — run Findings Engine demo, then reason
    """
    slug = norm(store_slug) or "demo"
    source_package: Optional[Mapping[str, Any]] = findings_package
    raw_findings: list[Mapping[str, Any]]

    if findings is not None:
        raw_findings = list(findings)
        findings_source = "explicit_findings"
    elif findings_package is not None:
        raw_findings = list(findings_package.get("findings") or [])
        findings_source = "findings_package"
    elif demo_fixture:
        source_package = run_business_findings_engine_v1(
            store_slug=slug, demo_fixture=True, window_days=window_days
        )
        raw_findings = list(source_package.get("findings") or [])
        findings_source = "findings_engine_demo_fixture"
    else:
        # Safe default for Product demos — never invent findings locally.
        source_package = run_business_findings_engine_v1(
            store_slug=slug, demo_fixture=True, window_days=window_days
        )
        raw_findings = list(source_package.get("findings") or [])
        findings_source = "findings_engine_demo_fixture"

    approved = select_approved_findings_v1(raw_findings)
    raw_cards = evaluate_all_reasoning_rules_v1(slug, approved)

    produced: list[dict[str, Any]] = []
    suppressed = 0
    for item in raw_cards:
        card = finalize_reasoning(item)
        card["rank_score"] = score_reasoning_v1(card)
        if not is_reasoning_worthy(card):
            suppressed += 1
            continue
        produced.append(card)

    produced.sort(key=lambda c: -float(c.get("rank_score") or 0))
    guidance = select_guidance_candidates_v1(produced)
    knowledge_items = [project_reasoning_to_knowledge_item_v1(c) for c in produced]

    types_represented = []
    for c in produced:
        t = norm(c.get("reasoning_type"))
        if t and t not in types_represented:
            types_represented.append(t)

    return {
        "ok": True,
        "engine_version": ENGINE_VERSION,
        "reasoning_version": REASONING_VERSION,
        "store_slug": slug,
        "generated_at": utc_now_iso(),
        "input": {
            "findings_source": findings_source,
            "findings_received": len(raw_findings),
            "findings_approved": len(approved),
            "findings_engine_version": (
                (source_package or {}).get("engine_version")
                if source_package
                else "business_findings_engine_v1"
            ),
        },
        "reasoning_cards": produced,
        "guidance_candidates_v1": guidance,
        "knowledge_items_v1": knowledge_items,
        "observability": {
            "rules_fired": len(raw_cards),
            "cards_produced": len(produced),
            "cards_suppressed": suppressed,
            "reasoning_types_represented": types_represented,
            "bypassed_truth": False,
            "bypassed_evidence": False,
            "bypassed_findings": False,
            "ai_used": False,
            "probabilistic": False,
        },
        "ai_used": False,
        "probabilistic": False,
    }


def render_reasoning_report_markdown_v1(package: Mapping[str, Any]) -> str:
    """Validation report for Product — merchant language on cards."""
    lines = [
        "# Business Reasoning Demo Report V1",
        "",
        f"**Store:** `{package.get('store_slug')}`  ",
        f"**Generated:** {package.get('generated_at')}  ",
        f"**Engine:** {package.get('engine_version')}  ",
        f"**Findings source:** {(package.get('input') or {}).get('findings_source')}  ",
        f"**Approved findings used:** {(package.get('input') or {}).get('findings_approved')}  ",
        "",
        "## Reasoning cards",
        "",
    ]
    for i, c in enumerate(package.get("reasoning_cards") or [], 1):
        lines.extend(
            [
                f"### {i}. {c.get('headline')}",
                "",
                f"- **Business meaning:** {c.get('business_meaning')}",
                f"- **Recommended priority:** {c.get('recommended_priority')}",
                f"- **Expected impact:** {c.get('expected_impact')}",
                f"- **Confidence:** {c.get('confidence_level')} ({c.get('confidence_score')})",
                f"- **Certainty:** {c.get('certainty')}",
                f"- **Supporting:**",
            ]
        )
        for label in c.get("supporting_finding_labels") or []:
            lines.append(f"  - {label}")
        gates = c.get("quality_gates") or {}
        lines.extend(
            [
                f"- **Quality gates passed:** {gates.get('passed')}",
                "",
            ]
        )
    guidance = package.get("guidance_candidates_v1") or {}
    lines.extend(["## Guidance candidates (consume later — no surface wiring)", ""])
    for key in (
        "weekly_priority",
        "primary_relationship",
        "top_constraint",
        "top_opportunity",
        "open_conflict",
    ):
        brief = guidance.get(key)
        if brief:
            lines.append(f"- **{key}:** {brief.get('headline')}")
        else:
            lines.append(f"- **{key}:** _(none)_")
    obs = package.get("observability") or {}
    lines.extend(
        [
            "",
            "## Observability (internal)",
            "",
            f"- rules_fired: {obs.get('rules_fired')}",
            f"- cards_produced: {obs.get('cards_produced')}",
            f"- cards_suppressed: {obs.get('cards_suppressed')}",
            f"- types: {', '.join(obs.get('reasoning_types_represented') or [])}",
            f"- bypassed_truth/evidence/findings: "
            f"{obs.get('bypassed_truth')}/{obs.get('bypassed_evidence')}/{obs.get('bypassed_findings')}",
            f"- ai_used: {obs.get('ai_used')}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
