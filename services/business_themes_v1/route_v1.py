# -*- coding: utf-8 -*-
"""
Business Theme Routing V1.

Executive Editorial / Home / Decision Workspace consume Themes — never raw Facts.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.business_themes_v1.contract_v1 import OWNER_DECISION_WORKSPACE


def route_business_themes_v1(package: Mapping[str, Any]) -> dict[str, Any]:
    published = [
        t
        for t in list(package.get("published_themes") or package.get("themes") or [])
        if isinstance(t, Mapping) and t.get("admitted")
    ]
    home = [
        t
        for t in published
        if (t.get("destination_surfaces") or {}).get("home_teaser")
    ]
    workspace = [
        t
        for t in published
        if (t.get("destination_surfaces") or {}).get("decision_workspace")
        or t.get("primary_owner") == OWNER_DECISION_WORKSPACE
    ]
    home.sort(key=lambda t: -int(t.get("priority") or 0))
    workspace.sort(key=lambda t: -int(t.get("priority") or 0))
    top = home[0] if home else None
    return {
        "ok": True,
        "home": {
            "themes": [
                {
                    "theme_id": t.get("theme_id"),
                    "theme_type": t.get("theme_type"),
                    "title_ar": t.get("title_ar"),
                    "executive_summary_ar": t.get("executive_summary_ar"),
                    "subject_name_ar": t.get("subject_name_ar"),
                    "priority": t.get("priority"),
                    "primary_owner": t.get("primary_owner"),
                }
                for t in home
            ],
            "top_theme": (
                {
                    "theme_id": top.get("theme_id"),
                    "theme_type": top.get("theme_type"),
                    "title_ar": top.get("title_ar"),
                    "executive_summary_ar": top.get("executive_summary_ar"),
                    "subject_name_ar": top.get("subject_name_ar"),
                    "source": "business_themes_v1",
                }
                if top
                else None
            ),
            "count": len(home),
        },
        "decision_workspace": {
            "themes": workspace,
            "count": len(workspace),
        },
        "home_teaser": {
            "count": len(home),
            "top": (
                {
                    "product_name_ar": top.get("subject_name_ar")
                    or top.get("title_ar"),
                    "statement_ar": top.get("executive_summary_ar"),
                    "theme_id": top.get("theme_id"),
                    "theme_type": top.get("theme_type"),
                    "title_ar": top.get("title_ar"),
                    "source": "business_themes_v1",
                }
                if top
                else None
            ),
            "evidence": "business_themes" if top else "none",
        },
    }


def workspace_cards_from_business_themes_v1(
    package: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """One Workspace card per admitted decision-owned theme (not per fact)."""
    routed = route_business_themes_v1(package)
    cards: list[dict[str, Any]] = []
    for t in routed["decision_workspace"]["themes"]:
        if not isinstance(t, Mapping):
            continue
        title = str(t.get("title_ar") or "أولوية العمل").strip()
        summary = str(t.get("executive_summary_ar") or "").strip()
        subject = str(t.get("subject_name_ar") or "").strip()
        decision = (
            f"راجع {subject}."
            if subject and subject != "المتجر"
            else f"راجع: {title}."
        )
        fact_n = int((t.get("evidence") or {}).get("fact_count") or 0)
        cards.append(
            {
                "decision_id": f"dce:bt:{t.get('theme_id')}",
                "source": "business_themes_v1",
                "theme_id": t.get("theme_id"),
                "theme_type": t.get("theme_type"),
                "product_name_ar": subject or title,
                "merchant_decision": decision,
                "title": decision,
                "executive_decision_ar": decision,
                "why": summary,
                "why_now": f"موضوع تجاري واحد يجمع {fact_n} حقيقة مدعومة."
                if fact_n
                else "موضوع تجاري مدعوم بأدلة حالية.",
                "evidence": summary,
                "confidence": (t.get("confidence") or {}).get("level")
                if isinstance(t.get("confidence"), Mapping)
                else "medium",
                "confidence_ar": (t.get("confidence") or {}).get("ar")
                if isinstance(t.get("confidence"), Mapping)
                else "متوسط",
                "first_step": "",
                "recommended_action": "",
                "business_domain": "products"
                if t.get("theme_type")
                in (
                    "product_conversion",
                    "product_demand",
                    "shipping_friction",
                    "customer_return_behaviour",
                )
                else "recovery",
                "decision_category": "products",
                "business_meaning_ar": summary,
                "business_impact_ar": (
                    (t.get("business_impact") or {}).get("ar")
                    if isinstance(t.get("business_impact"), Mapping)
                    else summary
                ),
                "gate_business_themes": True,
                "primary_owner": t.get("primary_owner"),
                "supporting_fact_ids": list(t.get("supporting_fact_ids") or []),
            }
        )
    return cards


__all__ = [
    "route_business_themes_v1",
    "workspace_cards_from_business_themes_v1",
]
