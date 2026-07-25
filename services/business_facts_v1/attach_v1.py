# -*- coding: utf-8 -*-
"""Attach Business Facts package onto dashboard summary / compose consumers."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.business_facts_v1.extract_v1 import extract_business_facts_v1
from services.business_facts_v1.flag_v1 import business_facts_v1_enabled
from services.business_facts_v1.registry_v1 import register_business_facts_v1
from services.business_facts_v1.route_v1 import route_business_facts_v1


def build_business_facts_package_v1(
    store_slug: str,
    *,
    orv_package: Mapping[str, Any] | None = None,
    domains_pkg: Mapping[str, Any] | None = None,
    store_executive_pkg: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    pkg = extract_business_facts_v1(
        store_slug=store_slug,
        orv_package=orv_package,
        domains_pkg=domains_pkg,
        store_executive_pkg=store_executive_pkg,
        environ=environ,
    )
    if not pkg.get("ok"):
        return pkg
    routing = route_business_facts_v1(pkg)
    pkg["routing"] = routing
    register_business_facts_v1(store_slug, pkg)
    return pkg


def attach_business_facts_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Attach ``business_facts_v1`` after ORV is on the summary.

    Prefer product fact teasers over raw observation framing.
    """
    if not isinstance(summary, dict):
        return summary
    if not business_facts_v1_enabled(environ=environ):
        summary["business_facts_v1"] = {
            "ok": False,
            "enabled": False,
            "facts": [],
        }
        return summary

    slug = (store_slug or "").strip() or str(summary.get("store_slug") or "").strip()
    orv = summary.get("observation_reality_validation_v1")
    domains = summary.get("business_domains_v1")
    exec_pkg = summary.get("store_executive_understanding_v1")
    # DCE may also stash teasers under merchant understanding
    mu = summary.get("merchant_understanding_v1")
    if not isinstance(exec_pkg, Mapping) and isinstance(mu, Mapping):
        exec_pkg = {
            "home_teasers": mu.get("home_teasers") or {},
            "briefing": mu.get("care_about_ar") or {},
        }

    pkg = build_business_facts_package_v1(
        slug,
        orv_package=orv if isinstance(orv, Mapping) else None,
        domains_pkg=domains if isinstance(domains, Mapping) else None,
        store_executive_pkg=exec_pkg if isinstance(exec_pkg, Mapping) else None,
        environ=environ,
    )
    summary["business_facts_v1"] = pkg
    return summary


def home_observation_teaser_from_facts_v1(
    summary: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Return slim observations teaser built from Business Facts when available."""
    pkg = summary.get("business_facts_v1")
    if not isinstance(pkg, Mapping) or not pkg.get("ok"):
        return None
    routing = pkg.get("routing") if isinstance(pkg.get("routing"), Mapping) else {}
    teaser = routing.get("home_teaser") if isinstance(routing, Mapping) else None
    if not isinstance(teaser, Mapping):
        return None
    if int(teaser.get("count") or 0) <= 0 or not teaser.get("top"):
        return None
    return {
        "count": int(teaser.get("count") or 0),
        "top": teaser.get("top"),
        "evidence": "business_facts",
    }


__all__ = [
    "attach_business_facts_to_summary_v1",
    "build_business_facts_package_v1",
    "home_observation_teaser_from_facts_v1",
]
