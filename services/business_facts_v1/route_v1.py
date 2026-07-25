# -*- coding: utf-8 -*-
"""
Business Fact Routing V1 — Home teasers + Decision Workspace evidence.

No recommendations. Routing only.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.business_facts_v1.contract_v1 import (
    FACT_TYPE_CONVERSION,
    FACT_TYPE_CUSTOMER_BEHAVIOUR,
    FACT_TYPE_PRODUCT_DEMAND,
)


def route_business_facts_v1(package: Mapping[str, Any]) -> dict[str, Any]:
    facts = [f for f in list(package.get("facts") or []) if isinstance(f, Mapping)]
    home_product: list[dict[str, Any]] = []
    home_store: list[dict[str, Any]] = []
    workspace: list[dict[str, Any]] = []

    for f in facts:
        surfaces = f.get("surfaces") if isinstance(f.get("surfaces"), Mapping) else {}
        subject = f.get("subject") if isinstance(f.get("subject"), Mapping) else {}
        row = {
            "fact_id": f.get("fact_id"),
            "fact_type": f.get("fact_type"),
            "subject_name_ar": (subject or {}).get("name_ar"),
            "business_meaning_ar": f.get("business_meaning_ar"),
            "confidence_ar": (f.get("confidence") or {}).get("ar")
            if isinstance(f.get("confidence"), Mapping)
            else "",
            "impact_category": f.get("impact_category"),
        }
        if surfaces.get("home"):
            if (subject or {}).get("kind") == "product" or f.get("fact_type") in (
                FACT_TYPE_PRODUCT_DEMAND,
                FACT_TYPE_CONVERSION,
                FACT_TYPE_CUSTOMER_BEHAVIOUR,
            ):
                if (subject or {}).get("kind") == "product":
                    home_product.append(row)
                else:
                    home_store.append(row)
            else:
                home_store.append(row)
        if surfaces.get("decision_workspace"):
            workspace.append(row)

    top_product = home_product[0] if home_product else None
    return {
        "ok": True,
        "home": {
            "product_facts": home_product,
            "store_facts": home_store,
            "top_product_fact": top_product,
            "product_fact_count": len(home_product),
        },
        "decision_workspace": {
            "evidence_facts": workspace,
            "count": len(workspace),
        },
        "home_teaser": {
            "count": len(home_product),
            "top": (
                {
                    "product_name_ar": top_product.get("subject_name_ar"),
                    "statement_ar": top_product.get("business_meaning_ar"),
                    "fact_id": top_product.get("fact_id"),
                    "fact_type": top_product.get("fact_type"),
                    "source": "business_facts_v1",
                }
                if top_product
                else None
            ),
            "evidence": "business_facts" if home_product else "none",
        },
    }


def workspace_cards_from_business_facts_v1(
    package: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Project workspace-eligible facts into DCE-compatible decision card dicts."""
    routed = route_business_facts_v1(package)
    cards: list[dict[str, Any]] = []
    facts_by_id = {
        str(f.get("fact_id")): f
        for f in list(package.get("facts") or [])
        if isinstance(f, Mapping) and f.get("fact_id")
    }
    for row in routed["decision_workspace"]["evidence_facts"]:
        full = facts_by_id.get(str(row.get("fact_id")) or "") or {}
        name = str(row.get("subject_name_ar") or "المنتج").strip()
        meaning = str(row.get("business_meaning_ar") or "").strip()
        cards.append(
            {
                "decision_id": f"dce:bf:{row.get('fact_id')}",
                "source": "business_facts_v1",
                "fact_id": row.get("fact_id"),
                "fact_type": row.get("fact_type"),
                "product_name_ar": name,
                "merchant_decision": f"راجع {name}.",
                "title": f"راجع {name}.",
                "executive_decision_ar": f"راجع {name}.",
                "why": meaning,
                "why_now": "حقيقة تجارية مدعومة بأدلة حالية.",
                "evidence": meaning,
                "confidence": (full.get("confidence") or {}).get("level")
                if isinstance(full.get("confidence"), Mapping)
                else "medium",
                "confidence_ar": row.get("confidence_ar") or "متوسط",
                "first_step": "",
                "recommended_action": "",
                "business_domain": "products",
                "decision_category": "products",
                "business_meaning_ar": meaning,
                "business_impact_ar": str(row.get("impact_category") or ""),
                "gate_business_facts": True,
                "observation_id": (
                    ((full.get("evidence") or {}).get("observation_ids") or [None])[0]
                ),
            }
        )
    return cards


__all__ = [
    "route_business_facts_v1",
    "workspace_cards_from_business_facts_v1",
]
