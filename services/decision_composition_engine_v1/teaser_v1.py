# -*- coding: utf-8 -*-
"""Home teaser parity — summarizes canonical decisions only (no why/evidence)."""
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

    Home never creates decisions and never ships why/evidence/reasoning.
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
    top_domain = ""
    if decisions:
        top = decisions[0]
        top_title = str(
            top.get("merchant_decision") or top.get("title") or ""
        ).strip()
        top_category = str(top.get("decision_category") or "").strip()
        top_domain = str(top.get("business_domain") or top_category).strip()

    landscape = list(pkg.get("category_landscape") or [])
    domains = pkg.get("business_domains_v1") if isinstance(pkg.get("business_domains_v1"), Mapping) else {}
    home_teasers = domains.get("home_teasers") if isinstance(domains, Mapping) else {}
    if not isinstance(home_teasers, Mapping):
        home_teasers = {}

    return {
        "count": len(decisions),
        "top_title_ar": top_title,
        "top_category": top_category,
        "top_domain": top_domain,
        "evidence": "decision_composition_engine" if decisions else "none",
        "total_findings": int((pkg.get("counts") or {}).get("candidates_total") or 0),
        "suppressed": int((pkg.get("counts") or {}).get("suppressed") or 0),
        "composition_version": pkg.get("composition_version"),
        "domain_composition_version": pkg.get("domain_composition_version"),
        "portfolio_version": pkg.get("portfolio_version"),
        "category_landscape": landscape,
        "home_domain_teasers": dict(home_teasers),
        "gate_2d": True,
        "cache": pkg.get("_cache") or {},
        "timing_ms": pkg.get("timing_ms") or {},
    }


__all__ = ["count_composed_decisions_for_teaser_v1"]
