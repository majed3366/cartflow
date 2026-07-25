# -*- coding: utf-8 -*-
"""
Canonical Decision Composition pipeline (Gate 2B/2C/2D).

Operational Truth → Business Domains → Candidate Decisions
→ Decision Deduplication → Priority → Contract Validation
→ Category Balance → Decision Portfolio → Cart Workspace
"""
from __future__ import annotations

import time
from typing import Any, Mapping

from services.decision_composition_engine_v1.business_domains_v1 import (
    DOMAIN_COMPOSITION_VERSION_V1,
    normalize_business_domains_v1,
)
from services.decision_composition_engine_v1.category_v1 import attach_category_v1
from services.decision_composition_engine_v1.compose_finding_v1 import (
    compose_from_finding_contract_v1,
)
from services.decision_composition_engine_v1.compose_recoverability_v1 import (
    compose_recoverability_gap_v1,
)
from services.decision_composition_engine_v1.compose_waiting_v1 import (
    compose_waiting_recovery_v1,
)
from services.decision_composition_engine_v1.contract_v1 import (
    BAND_NEEDS_ACTION,
    COMPOSITION_VERSION_V1,
)
from services.decision_composition_engine_v1.dedupe_v1 import dedupe_candidates_v1
from services.decision_composition_engine_v1.inputs_v1 import (
    load_bound_finding_inputs_v1,
    load_store_counter_inputs_v1,
)
from services.decision_composition_engine_v1.portfolio_v1 import build_portfolio_v1
from services.decision_composition_engine_v1.suppress_v1 import apply_contract_gate


def _compose_uncached_v1(
    store_slug: str,
    *,
    counters: Mapping[str, Any] | None = None,
    findings: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    slug = str(store_slug or "").strip()
    t0 = time.perf_counter()
    timing: dict[str, float] = {}

    t = time.perf_counter()
    if counters is not None and isinstance(counters, Mapping) and counters.get("available"):
        ctr = dict(counters)
        ctr.setdefault("store_slug", slug)
        timing["counters_ms"] = 0.0
        timing["counters_source"] = "payload"
    else:
        ctr = load_store_counter_inputs_v1(slug)
        timing["counters_ms"] = round((time.perf_counter() - t) * 1000.0, 2)
        timing["counters_source"] = "db_scan"

    t = time.perf_counter()
    if findings is not None:
        finds = [dict(f) for f in findings if isinstance(f, Mapping)]
        timing["findings_ms"] = 0.0
        timing["findings_source"] = "payload"
    else:
        finds = load_bound_finding_inputs_v1(slug)
        timing["findings_ms"] = round((time.perf_counter() - t) * 1000.0, 2)
        timing["findings_source"] = "db"

    # Gate 2D — normalize into business domains before composing decisions.
    t = time.perf_counter()
    domains_pkg = normalize_business_domains_v1(ctr, finds, store_slug=slug)
    timing["domains_ms"] = round((time.perf_counter() - t) * 1000.0, 2)

    t = time.perf_counter()
    candidates: list[dict[str, Any]] = []

    # Compose only when domain signals warrant a candidate (not raw counters).
    recovery_signals = (
        (domains_pkg.get("domains") or {}).get("recovery") or {}
    ).get("signals") or []
    if any(s.get("kind") == "recoverability_gap" for s in recovery_signals):
        rec = compose_recoverability_gap_v1(ctr)
        if rec:
            candidates.append(attach_category_v1(rec))

    ops_signals = (
        (domains_pkg.get("domains") or {}).get("operations") or {}
    ).get("signals") or []
    if any(s.get("kind") == "waiting_recovery_work" for s in ops_signals):
        wait = compose_waiting_recovery_v1(ctr)
        if wait:
            candidates.append(attach_category_v1(wait))

    for contract in finds:
        composed = compose_from_finding_contract_v1(contract, store_slug=slug)
        if composed:
            candidates.append(attach_category_v1(composed))

    timing["compose_candidates_ms"] = round((time.perf_counter() - t) * 1000.0, 2)

    t = time.perf_counter()
    survivors, registry = dedupe_candidates_v1(candidates, domain_pkg=domains_pkg)
    published: list[dict[str, Any]] = []
    for cand in survivors:
        gated = apply_contract_gate(dict(cand))
        if gated.get("suppressed"):
            registry.append(
                {
                    "decision_id": gated.get("decision_id"),
                    "suppression_reason": gated.get("suppression_reason"),
                    "decision_type": gated.get("decision_type"),
                    "decision_category": gated.get("decision_category"),
                    "root_cause_key": gated.get("root_cause_key"),
                    "business_domain": gated.get("business_domain"),
                }
            )
            continue
        published.append(attach_category_v1(gated))

    published.sort(
        key=lambda d: (
            0 if d.get("priority_band") == BAND_NEEDS_ACTION else 1,
            -int(d.get("priority") or 0),
            str(d.get("decision_id") or ""),
        )
    )
    timing["dedupe_validate_ms"] = round((time.perf_counter() - t) * 1000.0, 2)

    t = time.perf_counter()
    portfolio_pkg = build_portfolio_v1(published, max_visible=6)
    timing["portfolio_ms"] = round((time.perf_counter() - t) * 1000.0, 2)
    timing["total_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    portfolio = list(portfolio_pkg.get("portfolio") or [])
    needs = [d for d in portfolio if d.get("priority_band") == BAND_NEEDS_ACTION]
    monitor = [d for d in portfolio if d.get("priority_band") != BAND_NEEDS_ACTION]

    return {
        "ok": True,
        "store_slug": slug,
        "composition_version": COMPOSITION_VERSION_V1,
        "domain_composition_version": DOMAIN_COMPOSITION_VERSION_V1,
        "gate_2c_decision_portfolio": True,
        "gate_2d_business_domains": True,
        "gate_2d_decision_dedupe": True,
        "business_domains_v1": {
            "domains": domains_pkg.get("domains"),
            "home_teasers": domains_pkg.get("home_teasers"),
            "signals": domains_pkg.get("signals"),
            "root_causes": domains_pkg.get("root_causes"),
        },
        "decisions": portfolio,
        "all_published": published,
        "needs_action_now": needs,
        "monitor": monitor,
        "portfolio": portfolio,
        "overflow": portfolio_pkg.get("overflow"),
        "category_landscape": portfolio_pkg.get("category_landscape"),
        "portfolio_version": portfolio_pkg.get("portfolio_version"),
        "suppression_registry": registry,
        "timing_ms": timing,
        "counts": {
            "published": len(portfolio),
            "all_published": len(published),
            "suppressed": len(registry),
            "needs_action_now": len(needs),
            "monitor": len(monitor),
            "candidates_total": len(candidates),
            "root_causes": len(domains_pkg.get("root_causes") or []),
            "categories_healthy": sum(
                1
                for x in (portfolio_pkg.get("category_landscape") or [])
                if x.get("no_action_required")
            ),
        },
        "no_decision_supported": len(portfolio) == 0,
    }


def compose_decisions_v1(
    store_slug: str,
    *,
    counters: Mapping[str, Any] | None = None,
    findings: list[Mapping[str, Any]] | None = None,
    use_cache: bool = True,
    allow_sync_miss: bool = True,
) -> dict[str, Any]:
    """
    Sole composition entry. When use_cache=True, serves snapshot first.
    """
    slug = str(store_slug or "").strip()

    def _run() -> dict[str, Any]:
        return _compose_uncached_v1(slug, counters=counters, findings=findings)

    if not use_cache:
        return _run()

    from services.decision_composition_engine_v1.snapshot_cache_v1 import (  # noqa: PLC0415
        cache_get,
        cache_set,
        get_or_compose_package_v1,
    )

    # Fresh snapshot wins — never re-compose on every Home paint.
    cached = cache_get(slug)
    if cached is not None and not (cached.get("_cache") or {}).get("stale"):
        return cached

    # Stale or miss: prefer payload counters (no AbandonedCart scan).
    if counters is not None and isinstance(counters, Mapping) and counters.get("available"):

        def _run_payload() -> dict[str, Any]:
            return _compose_uncached_v1(
                slug, counters=counters, findings=findings
            )

        if cached is not None:
            return get_or_compose_package_v1(
                slug, composer=_run_payload, allow_sync_miss=False
            )
        pkg = _run_payload()
        cache_set(slug, pkg)
        out = dict(pkg)
        out["_cache"] = {
            "hit": False,
            "fresh": True,
            "payload_counters": True,
            "sync_miss_ms": (pkg.get("timing_ms") or {}).get("total_ms"),
        }
        return out

    return get_or_compose_package_v1(
        slug, composer=_run, allow_sync_miss=allow_sync_miss
    )


__all__ = ["compose_decisions_v1"]
