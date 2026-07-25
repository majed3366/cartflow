# -*- coding: utf-8 -*-
"""Route Commerce Situations to Home / Workspace / supporting surfaces."""
from __future__ import annotations

from typing import Any, Mapping

from services.commerce_situations_v1.contract_v1 import OWNER_DECISION_WORKSPACE


def route_commerce_situations_v1(package: Mapping[str, Any]) -> dict[str, Any]:
    published = [
        s
        for s in list(package.get("published_situations") or package.get("situations") or [])
        if isinstance(s, Mapping) and s.get("admitted")
    ]
    home = [
        s
        for s in published
        if (s.get("destination_surfaces") or {}).get("home_teaser")
    ]
    workspace = [
        s
        for s in published
        if (s.get("destination_surfaces") or {}).get("decision_workspace")
        or s.get("primary_owner") == OWNER_DECISION_WORKSPACE
    ]
    products = [
        s
        for s in published
        if (s.get("destination_surfaces") or {}).get("products")
    ]
    carts = [
        s for s in published if (s.get("destination_surfaces") or {}).get("carts")
    ]
    communication = [
        s
        for s in published
        if (s.get("destination_surfaces") or {}).get("communication")
    ]
    home.sort(key=lambda s: -int(s.get("priority") or 0))
    workspace.sort(key=lambda s: -int(s.get("priority") or 0))
    products.sort(key=lambda s: -int(s.get("priority") or 0))
    carts.sort(key=lambda s: -int(s.get("priority") or 0))
    communication.sort(key=lambda s: -int(s.get("priority") or 0))
    top = home[0] if home else None

    def _home_item(s: Mapping[str, Any]) -> dict[str, Any]:
        subject = (
            (s.get("subject") or {}).get("name_ar")
            if isinstance(s.get("subject"), Mapping)
            else ""
        )
        return {
            "situation_id": s.get("situation_id"),
            "situation_kind": s.get("situation_kind"),
            "title_ar": s.get("title_ar"),
            "statement_ar": s.get("executive_summary_ar")
            or s.get("why_it_matters_ar"),
            "business_question_ar": s.get("business_question_ar"),
            "product_name_ar": subject or s.get("title_ar"),
            "merchant_action_ar": s.get("merchant_action_ar"),
            "affected_products": list(s.get("affected_products") or []),
            "affected_carts": s.get("affected_carts") or {},
            "affected_customers": s.get("affected_customers") or {},
            "href": f"#workspace?situation_id={s.get('situation_id') or ''}",
            "source": "commerce_situations_v1",
        }

    home_items = [_home_item(s) for s in home[:5]]
    return {
        "ok": True,
        "home": {
            "situations": home,
            "top_situation": top,
            "count": len(home),
        },
        "decision_workspace": {"situations": workspace, "count": len(workspace)},
        "products": {"situations": products, "count": len(products)},
        "carts": {"situations": carts, "count": len(carts)},
        "communication": {
            "situations": communication,
            "count": len(communication),
        },
        "home_teaser": {
            "count": len(home_items),
            "situations": home_items,
            "top": home_items[0] if home_items else None,
            "evidence": "commerce_situations" if home_items else "none",
        },
    }


def workspace_cards_from_commerce_situations_v1(
    package: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """One Workspace card per admitted decision-owned situation (not per fact)."""
    routed = route_commerce_situations_v1(package)
    cards: list[dict[str, Any]] = []
    for s in routed["decision_workspace"]["situations"]:
        if not isinstance(s, Mapping):
            continue
        subject = (
            (s.get("subject") or {}).get("name_ar")
            if isinstance(s.get("subject"), Mapping)
            else ""
        )
        sit_title = str(s.get("title_ar") or "").strip()
        why = str(s.get("why_it_matters_ar") or s.get("executive_summary_ar") or "").strip()
        action = str(s.get("merchant_action_ar") or "").strip()
        fact_n = int((s.get("evidence") or {}).get("fact_count") or 0)
        fact_lines = [
            str(f.get("business_meaning_ar") or "").strip()
            for f in list(s.get("supporting_facts") or [])
            if isinstance(f, Mapping) and str(f.get("business_meaning_ar") or "").strip()
        ]
        evidence = " · ".join(fact_lines) if fact_lines else why
        cards.append(
            {
                "decision_id": f"dce:cs:{s.get('situation_id')}",
                "source": "commerce_situations_v1",
                "situation_id": s.get("situation_id"),
                "situation_kind": s.get("situation_kind"),
                "product_name_ar": subject or s.get("title_ar"),
                "merchant_decision": sit_title,
                "title": sit_title,
                "executive_decision_ar": sit_title,
                "why": why,
                "why_now": str(s.get("business_question_ar") or why),
                "evidence": evidence,
                "supporting_facts_ar": fact_lines,
                "confidence": (s.get("confidence") or {}).get("level")
                if isinstance(s.get("confidence"), Mapping)
                else "medium",
                "confidence_ar": (s.get("confidence") or {}).get("ar")
                if isinstance(s.get("confidence"), Mapping)
                else "متوسط",
                "first_step": "",
                "recommended_action": action,
                "business_domain": "products"
                if s.get("situation_kind")
                in (
                    "interest_without_purchase",
                    "shipping_friction",
                    "product_demand",
                )
                else "recovery",
                "decision_category": "products",
                "business_meaning_ar": why,
                "business_impact_ar": s.get("expected_business_impact_ar"),
                "gate_commerce_situations": True,
                "primary_owner": s.get("primary_owner"),
                "supporting_fact_ids": list(s.get("supporting_fact_ids") or []),
                "supporting_fact_count": fact_n,
                "affected_products": list(s.get("affected_products") or []),
                "affected_carts": s.get("affected_carts") or {},
                "affected_customers": s.get("affected_customers") or {},
                "priority": int(s.get("priority") or 60),
            }
        )
    return cards


__all__ = [
    "route_commerce_situations_v1",
    "workspace_cards_from_commerce_situations_v1",
]
