# -*- coding: utf-8 -*-
"""Attach Business Themes onto summary / compose consumers."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.business_themes_v1.compose_v1 import compose_business_themes_v1
from services.business_themes_v1.flag_v1 import business_themes_v1_enabled
from services.business_themes_v1.route_v1 import route_business_themes_v1


def build_business_themes_package_v1(
    store_slug: str,
    *,
    facts_package: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    pkg = compose_business_themes_v1(
        facts_package, store_slug=store_slug, environ=environ
    )
    if not pkg.get("ok"):
        return pkg
    pkg["routing"] = route_business_themes_v1(pkg)
    return pkg


def attach_business_themes_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Attach themes after Business Facts are on the summary."""
    if not isinstance(summary, dict):
        return summary
    if not business_themes_v1_enabled(environ=environ):
        summary["business_themes_v1"] = {
            "ok": False,
            "enabled": False,
            "themes": [],
            "published_themes": [],
        }
        return summary
    slug = (store_slug or "").strip() or str(summary.get("store_slug") or "").strip()
    facts = summary.get("business_facts_v1")
    pkg = build_business_themes_package_v1(
        slug,
        facts_package=facts if isinstance(facts, Mapping) else None,
        environ=environ,
    )
    summary["business_themes_v1"] = pkg
    return summary


def home_teaser_from_themes_v1(
    summary: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    pkg = summary.get("business_themes_v1")
    if not isinstance(pkg, Mapping) or not pkg.get("ok"):
        return None
    routing = pkg.get("routing") if isinstance(pkg.get("routing"), Mapping) else {}
    teaser = routing.get("home_teaser") if isinstance(routing, Mapping) else None
    if not isinstance(teaser, Mapping) or not teaser.get("top"):
        return None
    return {
        "count": int(teaser.get("count") or 0),
        "top": teaser.get("top"),
        "evidence": "business_themes",
    }


__all__ = [
    "attach_business_themes_to_summary_v1",
    "build_business_themes_package_v1",
    "home_teaser_from_themes_v1",
]
