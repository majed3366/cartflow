# -*- coding: utf-8 -*-
"""Home teaser parity with Decision Portfolio (no full evidence on Home)."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1
from services.decision_composition_engine_v1.inputs_v1 import (
    counters_from_summary_payload_v1,
)


def count_composed_decisions_for_teaser_v1(
    store_slug: str,
    *,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Lightweight Home inputs from Decision Portfolio snapshot.

    Uses summary counters when present so Home never re-scans AbandonedCart.
    """
    counters = counters_from_summary_payload_v1(summary, store_slug=store_slug)
    pkg = compose_decisions_v1(
        store_slug,
        counters=counters,
        use_cache=True,
        allow_sync_miss=True,
    )

    decisions = list(pkg.get("portfolio") or pkg.get("decisions") or [])
    top_title = ""
    top_category = ""
    if decisions:
        top = decisions[0]
        top_title = str(
            top.get("merchant_decision") or top.get("title") or ""
        ).strip()
        top_category = str(top.get("decision_category") or "").strip()

    landscape = list(pkg.get("category_landscape") or [])
    return {
        "count": len(decisions),
        "top_title_ar": top_title,
        "top_category": top_category,
        "evidence": "decision_composition_engine" if decisions else "none",
        "total_findings": int((pkg.get("counts") or {}).get("candidates_total") or 0),
        "suppressed": int((pkg.get("counts") or {}).get("suppressed") or 0),
        "composition_version": pkg.get("composition_version"),
        "portfolio_version": pkg.get("portfolio_version"),
        "category_landscape": landscape,
        "cache": pkg.get("_cache") or {},
        "timing_ms": pkg.get("timing_ms") or {},
    }


__all__ = ["count_composed_decisions_for_teaser_v1"]
