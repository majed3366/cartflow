# -*- coding: utf-8 -*-
"""Attach Mission Portfolio V1 after mission_catalog_v1 (query_delta 0)."""
from __future__ import annotations

from typing import Any

from services.mission_portfolio_v1.compose_v1 import (
    compose_mission_portfolio_v1,
    empty_portfolio_package_v1,
)


def attach_mission_portfolio_to_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str | None = None,
) -> dict[str, Any]:
    """Prefer already-attached catalog — no new DB reads."""
    if not isinstance(summary, dict):
        return summary
    slug = str(store_slug or summary.get("store_slug") or "").strip()[:191]
    cat = summary.get("mission_catalog_v1")
    if not isinstance(cat, dict):
        summary["mission_portfolio_v1"] = empty_portfolio_package_v1(
            reason="catalog_missing"
        )
        return summary
    try:
        summary["mission_portfolio_v1"] = compose_mission_portfolio_v1(
            catalog_package=cat,
            store_slug=slug,
        )
    except Exception:  # noqa: BLE001 — never break Home
        pkg = empty_portfolio_package_v1(reason="attach_failed")
        pkg["ok"] = False
        summary["mission_portfolio_v1"] = pkg
    return summary


__all__ = ["attach_mission_portfolio_to_summary_v1"]
