# -*- coding: utf-8 -*-
"""Attach Mission Catalog V1 to dashboard summary (after COL + CDC)."""
from __future__ import annotations

from typing import Any, Mapping

from services.mission_catalog_v1.compose_v1 import (
    compose_mission_catalog_v1,
    empty_catalog_package_v1,
)


def attach_mission_catalog_to_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str | None = None,
) -> dict[str, Any]:
    """
    Prefer already-attached COL + CDC maps — query_delta 0.

    Safe no-op when COL missing.
    """
    if not isinstance(summary, dict):
        return summary
    slug = str(store_slug or summary.get("store_slug") or "").strip()[:191]
    col = summary.get("commercial_opportunity_layer_v1")
    if not isinstance(col, Mapping):
        summary["mission_catalog_v1"] = empty_catalog_package_v1(reason="col_missing")
        return summary

    cdc = summary.get("commercial_decision_commitment_v1")
    by_key: dict[str, Any] = {}
    if isinstance(cdc, Mapping):
        raw = cdc.get("by_opportunity_key")
        if isinstance(raw, dict):
            by_key = {str(k): v for k, v in raw.items() if isinstance(v, Mapping)}

    try:
        pkg = compose_mission_catalog_v1(
            col_package=col,
            commitments_by_key=by_key,
            store_slug=slug,
        )
        summary["mission_catalog_v1"] = pkg
    except Exception:  # noqa: BLE001 — never break Home
        summary["mission_catalog_v1"] = empty_catalog_package_v1(reason="attach_failed")
        summary["mission_catalog_v1"]["ok"] = False
    return summary


__all__ = ["attach_mission_catalog_to_summary_v1"]
