# -*- coding: utf-8 -*-
"""Home teaser parity with composed Decisions (no full evidence on Home)."""
from __future__ import annotations

from typing import Any

from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1


def count_composed_decisions_for_teaser_v1(store_slug: str) -> dict[str, Any]:
    pkg = compose_decisions_v1(store_slug)
    decisions = list(pkg.get("decisions") or [])
    top_title = ""
    if decisions:
        top = decisions[0]
        top_title = str(
            top.get("merchant_decision") or top.get("title") or ""
        ).strip()
    return {
        "count": len(decisions),
        "top_title_ar": top_title,
        "evidence": "decision_composition_engine" if decisions else "none",
        "total_findings": int((pkg.get("counts") or {}).get("candidates_total") or 0),
        "suppressed": int((pkg.get("counts") or {}).get("suppressed") or 0),
        "composition_version": pkg.get("composition_version"),
    }


__all__ = ["count_composed_decisions_for_teaser_v1"]
