# -*- coding: utf-8 -*-
"""Home teaser — Store Executive Understanding only (no why/evidence)."""
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
    Lightweight Home inputs from Store Executive Understanding.

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
    exec_pkg = (
        pkg.get("store_executive_understanding_v1")
        if isinstance(pkg.get("store_executive_understanding_v1"), Mapping)
        else {}
    )
    home_teasers = exec_pkg.get("home_teasers") if isinstance(exec_pkg, Mapping) else {}
    if not isinstance(home_teasers, Mapping):
        domains = pkg.get("business_domains_v1") if isinstance(pkg.get("business_domains_v1"), Mapping) else {}
        home_teasers = domains.get("home_teasers") if isinstance(domains, Mapping) else {}
    if not isinstance(home_teasers, Mapping):
        home_teasers = {}

    top_title = str(home_teasers.get("decisions_top_title_ar") or "").strip()
    top_category = ""
    top_domain = ""
    if decisions:
        top = decisions[0]
        if not top_title:
            top_title = str(
                top.get("executive_decision_ar")
                or top.get("merchant_decision")
                or top.get("title")
                or ""
            ).strip()
        top_category = str(top.get("decision_category") or "").strip()
        top_domain = str(top.get("business_domain") or top_category).strip()

    landscape = list(pkg.get("category_landscape") or [])
    publication = (
        pkg.get("merchant_publication_v1")
        if isinstance(pkg.get("merchant_publication_v1"), Mapping)
        else {}
    )
    if publication.get("primary_business_action"):
        top_title = str(publication.get("primary_business_action") or top_title).strip()
    return {
        "count": 1 if publication.get("highest_priority_decision_id") else len(decisions),
        "top_title_ar": top_title,
        "top_category": top_category,
        "top_domain": top_domain,
        "evidence": "merchant_publication_v1"
        if publication.get("ok")
        else ("store_executive_understanding" if decisions else "none"),
        "total_findings": int((pkg.get("counts") or {}).get("candidates_total") or 0),
        "suppressed": int((pkg.get("counts") or {}).get("suppressed") or 0),
        "composition_version": pkg.get("composition_version"),
        "domain_composition_version": pkg.get("domain_composition_version"),
        "store_executive_version": pkg.get("store_executive_version"),
        "portfolio_version": pkg.get("portfolio_version"),
        "category_landscape": landscape,
        "home_domain_teasers": dict(home_teasers),
        "merchant_publication_v1": dict(publication) if publication else {},
        "highest_priority_decision_id": str(
            publication.get("highest_priority_decision_id") or ""
        ).strip(),
        "highest_priority_situation_id": str(
            publication.get("highest_priority_situation_id") or ""
        ).strip(),
        "truth_version": str(publication.get("truth_version") or "").strip(),
        "executive_briefing": (exec_pkg.get("briefing") if isinstance(exec_pkg, Mapping) else {}),
        "gate_2d": True,
        "gate_2e": True,
        "gate_2f": True,
        "gate_merchant_understanding_repair_v1": True,
        "cache": pkg.get("_cache") or {},
        "timing_ms": pkg.get("timing_ms") or {},
    }


__all__ = ["count_composed_decisions_for_teaser_v1"]
