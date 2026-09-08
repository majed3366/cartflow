# -*- coding: utf-8 -*-
"""Attach Live Decision Hierarchy V1 after catalog + portfolio (query_delta 0)."""
from __future__ import annotations

from typing import Any

from services.live_decision_hierarchy_v1.compose_v1 import (
    compose_live_decision_hierarchy_v1,
)


def attach_live_decision_hierarchy_to_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str | None = None,
    store: Any = None,
) -> dict[str, Any]:
    """Lab-only. Omit the key for every other tenant (payload unchanged)."""
    if not isinstance(summary, dict):
        return summary
    slug = str(store_slug or summary.get("store_slug") or "").strip()[:191]
    try:
        pkg = compose_live_decision_hierarchy_v1(
            summary, store_slug=slug, store=store
        )
    except Exception:  # noqa: BLE001 — never break Home
        summary.pop("live_decision_hierarchy_v1", None)
        return summary
    if pkg is None:
        summary.pop("live_decision_hierarchy_v1", None)
        return summary
    summary["live_decision_hierarchy_v1"] = pkg
    return summary


__all__ = ["attach_live_decision_hierarchy_to_summary_v1"]
