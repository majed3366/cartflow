# -*- coding: utf-8 -*-
"""
Gate 2C — Decision Portfolio builder.

Candidates compete; category caps prevent permanent domination.
Healthy categories surface «لا إجراء مطلوب.»
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.category_v1 import (
    ALL_CATEGORIES_V1,
    CATEGORY_LABEL_AR,
    CATEGORY_PRIMARY_CAP_V1,
    NO_ACTION_AR,
    attach_category_v1,
)
from services.decision_composition_engine_v1.contract_v1 import BAND_NEEDS_ACTION


def _rank_key(d: Mapping[str, Any]) -> tuple:
    return (
        0 if d.get("priority_band") == BAND_NEEDS_ACTION else 1,
        -int(d.get("priority") or 0),
        str(d.get("decision_id") or ""),
    )


def build_portfolio_v1(
    published: list[dict[str, Any]],
    *,
    max_visible: int = 6,
) -> dict[str, Any]:
    """
    Apply per-category primary cap, then global rank.

    Returns portfolio (visible ranked decisions), overflow (available but not primary),
    and category_landscape (every category status).
    """
    by_cat: dict[str, list[dict[str, Any]]] = {c: [] for c in ALL_CATEGORIES_V1}
    for raw in published:
        d = attach_category_v1(dict(raw))
        cat = str(d.get("decision_category") or "")
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(d)

    primaries: list[dict[str, Any]] = []
    overflow: list[dict[str, Any]] = []
    for cat in ALL_CATEGORIES_V1:
        items = sorted(by_cat.get(cat) or [], key=_rank_key)
        cap = int(CATEGORY_PRIMARY_CAP_V1.get(cat, 1))
        for i, item in enumerate(items):
            item = dict(item)
            if i < cap:
                item["portfolio_role"] = "primary"
                primaries.append(item)
            else:
                item["portfolio_role"] = "available"
                overflow.append(item)

    primaries.sort(key=_rank_key)
    ranked: list[dict[str, Any]] = []
    for i, item in enumerate(primaries[: max(1, int(max_visible))]):
        item = dict(item)
        item["portfolio_rank"] = i + 1
        ranked.append(item)

    # Remaining primaries beyond max_visible become available
    for item in primaries[max(1, int(max_visible)) :]:
        item = dict(item)
        item["portfolio_role"] = "available"
        overflow.append(item)

    landscape: list[dict[str, Any]] = []
    primary_cats = {str(d.get("decision_category")) for d in ranked}
    for cat in ALL_CATEGORIES_V1:
        items = by_cat.get(cat) or []
        if cat in primary_cats:
            top = next(d for d in ranked if d.get("decision_category") == cat)
            landscape.append(
                {
                    "category": cat,
                    "category_ar": CATEGORY_LABEL_AR[cat],
                    "status": "has_decision",
                    "status_ar": "يوجد قرار",
                    "decision_id": top.get("decision_id"),
                    "summary_ar": top.get("merchant_decision") or top.get("title"),
                    "no_action_required": False,
                }
            )
        elif items:
            landscape.append(
                {
                    "category": cat,
                    "category_ar": CATEGORY_LABEL_AR[cat],
                    "status": "available",
                    "status_ar": "متاح",
                    "decision_id": items[0].get("decision_id"),
                    "summary_ar": items[0].get("merchant_decision") or items[0].get("title"),
                    "no_action_required": False,
                }
            )
        else:
            landscape.append(
                {
                    "category": cat,
                    "category_ar": CATEGORY_LABEL_AR[cat],
                    "status": "healthy",
                    "status_ar": NO_ACTION_AR,
                    "decision_id": None,
                    "summary_ar": NO_ACTION_AR,
                    "no_action_required": True,
                }
            )

    return {
        "portfolio": ranked,
        "overflow": overflow,
        "category_landscape": landscape,
        "portfolio_version": "decision_portfolio_v1",
        "max_visible": max_visible,
        "category_caps": dict(CATEGORY_PRIMARY_CAP_V1),
    }


__all__ = ["build_portfolio_v1"]
