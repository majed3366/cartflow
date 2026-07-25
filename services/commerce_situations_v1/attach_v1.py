# -*- coding: utf-8 -*-
"""Attach Commerce Situations onto summary / consumers."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.commerce_situations_v1.compose_v1 import compose_commerce_situations_v1
from services.commerce_situations_v1.flag_v1 import commerce_situations_v1_enabled
from services.commerce_situations_v1.route_v1 import route_commerce_situations_v1


def build_commerce_situations_package_v1(
    store_slug: str,
    *,
    facts_package: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if facts_package is None:
        from services.business_facts_v1 import (  # noqa: PLC0415
            build_business_facts_package_v1,
        )

        facts_package = build_business_facts_package_v1(store_slug)
    pkg = compose_commerce_situations_v1(
        facts_package, store_slug=store_slug, environ=environ
    )
    if not pkg.get("ok"):
        return pkg
    pkg["routing"] = route_commerce_situations_v1(pkg)
    return pkg


def attach_commerce_situations_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    if not commerce_situations_v1_enabled(environ=environ):
        summary["commerce_situations_v1"] = {
            "ok": False,
            "enabled": False,
            "situations": [],
            "published_situations": [],
        }
        return summary
    slug = (store_slug or "").strip() or str(summary.get("store_slug") or "").strip()
    facts = summary.get("business_facts_v1")
    pkg = build_commerce_situations_package_v1(
        slug,
        facts_package=facts if isinstance(facts, Mapping) else None,
        environ=environ,
    )
    if pkg.get("ok"):
        from services.commerce_situations_v1.consume_v1 import (  # noqa: PLC0415
            surface_projection_v1,
        )

        pkg["consumers"] = {
            "home": surface_projection_v1(pkg, "home"),
            "decision_workspace": surface_projection_v1(pkg, "decision_workspace"),
            "products": surface_projection_v1(pkg, "products"),
            "carts": surface_projection_v1(pkg, "carts"),
            "communication": surface_projection_v1(pkg, "communication"),
        }
        # Bind Living Store identity onto the package every surface reads.
        try:
            from services.reality_validation_context_v1 import (  # noqa: PLC0415
                latest_living_store_run_v1,
            )

            sim = latest_living_store_run_v1(slug)
            pkg["simulation_run_id"] = sim.get("simulation_run_id")
            pkg["living_store_profile"] = sim.get("living_store_profile")
            pkg["last_simulation_timestamp"] = sim.get("last_simulation_timestamp")
        except Exception:  # noqa: BLE001
            pass
    summary["commerce_situations_v1"] = pkg
    return summary


def home_teaser_from_situations_v1(
    summary: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    pkg = summary.get("commerce_situations_v1")
    if not isinstance(pkg, Mapping) or not pkg.get("ok"):
        return None
    routing = pkg.get("routing") if isinstance(pkg.get("routing"), Mapping) else {}
    teaser = routing.get("home_teaser") if isinstance(routing, Mapping) else None
    if not isinstance(teaser, Mapping):
        return None
    situations = list(teaser.get("situations") or [])
    top = teaser.get("top") if isinstance(teaser.get("top"), Mapping) else None
    if not situations and not top:
        return None
    return {
        "count": int(teaser.get("count") or len(situations) or 0),
        "situations": situations,
        "top": top or (situations[0] if situations else None),
        "evidence": "commerce_situations",
    }


__all__ = [
    "attach_commerce_situations_to_summary_v1",
    "build_commerce_situations_package_v1",
    "home_teaser_from_situations_v1",
]
