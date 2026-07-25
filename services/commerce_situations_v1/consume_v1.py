# -*- coding: utf-8 -*-
"""
Surface consumers for Commerce Situations.

Same Situation → each surface describes it from its own responsibility.
Never invents a second commercial interpretation.
"""
from __future__ import annotations

from typing import Any, Mapping


def _published(package: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = list(package.get("published_situations") or package.get("situations") or [])
    return [s for s in rows if isinstance(s, Mapping) and s.get("admitted")]


def situations_for_surface_v1(
    package: Mapping[str, Any],
    surface: str,
) -> list[dict[str, Any]]:
    """Return admitted situations flagged for the given consumer surface."""
    key = str(surface or "").strip()
    out: list[dict[str, Any]] = []
    for s in _published(package):
        dest = s.get("destination_surfaces") if isinstance(s.get("destination_surfaces"), Mapping) else {}
        if key == "home" and dest.get("home_teaser"):
            out.append(dict(s))
        elif key == "decision_workspace" and dest.get("decision_workspace"):
            out.append(dict(s))
        elif key == "products" and dest.get("products"):
            out.append(dict(s))
        elif key == "carts" and dest.get("carts"):
            out.append(dict(s))
        elif key == "communication" and dest.get("communication"):
            out.append(dict(s))
    out.sort(key=lambda s: (-int(s.get("priority") or 0), str(s.get("situation_id"))))
    return out


def surface_projection_v1(
    package: Mapping[str, Any],
    surface: str,
) -> dict[str, Any]:
    """
    Responsibility-scoped projection of the same Situation IDs.

    - home: introduce
    - decision_workspace: explain + act
    - products: affected product scope
    - carts: operational cart scope
    - communication: communication coverage scope
    """
    rows = situations_for_surface_v1(package, surface)
    items: list[dict[str, Any]] = []
    for s in rows:
        base = {
            "situation_id": s.get("situation_id"),
            "situation_kind": s.get("situation_kind"),
            "title_ar": s.get("title_ar"),
            "source": "commerce_situations_v1",
            "reinterpretation": False,
        }
        if surface == "home":
            items.append(
                {
                    **base,
                    "role": "introduce",
                    "statement_ar": s.get("executive_summary_ar")
                    or s.get("why_it_matters_ar"),
                    "business_question_ar": s.get("business_question_ar"),
                }
            )
        elif surface == "decision_workspace":
            items.append(
                {
                    **base,
                    "role": "explain",
                    "why_it_matters_ar": s.get("why_it_matters_ar"),
                    "business_question_ar": s.get("business_question_ar"),
                    "merchant_action_ar": s.get("merchant_action_ar"),
                    "expected_business_impact_ar": s.get(
                        "expected_business_impact_ar"
                    ),
                    "supporting_fact_ids": list(s.get("supporting_fact_ids") or []),
                }
            )
        elif surface == "products":
            items.append(
                {
                    **base,
                    "role": "product_scope",
                    "affected_products": list(s.get("affected_products") or []),
                    "why_it_matters_ar": s.get("why_it_matters_ar"),
                }
            )
        elif surface == "carts":
            carts = (
                s.get("affected_carts")
                if isinstance(s.get("affected_carts"), Mapping)
                else {}
            )
            items.append(
                {
                    **base,
                    "role": "cart_ops",
                    "affected_carts": carts,
                    "ops_note_ar": str((carts or {}).get("summary_ar") or ""),
                }
            )
        elif surface == "communication":
            customers = (
                s.get("affected_customers")
                if isinstance(s.get("affected_customers"), Mapping)
                else {}
            )
            items.append(
                {
                    **base,
                    "role": "communication_status",
                    "affected_customers": customers,
                    "why_it_matters_ar": str(
                        (customers or {}).get("summary_ar")
                        or s.get("why_it_matters_ar")
                        or ""
                    ),
                    "merchant_action_ar": s.get("merchant_action_ar"),
                }
            )
        else:
            items.append(base)
    return {
        "ok": True,
        "surface": surface,
        "count": len(items),
        "situation_ids": [i.get("situation_id") for i in items],
        "items": items,
        "canonical_object": "commerce_situation_v1",
        "product_intelligence": False,
    }


__all__ = ["situations_for_surface_v1", "surface_projection_v1"]
