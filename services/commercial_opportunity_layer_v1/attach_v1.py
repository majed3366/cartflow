# -*- coding: utf-8 -*-
"""Attach Commercial Opportunity Layer V1 to dashboard summary (flag-gated)."""
from __future__ import annotations

from typing import Any, Mapping

from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.commercial_opportunity_layer_v1.contract_v1 import empty_package_v1
from services.commercial_opportunity_layer_v1.flag_v1 import (
    commercial_opportunity_layer_v1_enabled,
)


def attach_commercial_opportunity_layer_to_summary_v1(
    summary: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    if not commercial_opportunity_layer_v1_enabled(environ=environ):
        # Do not leave a stale package when flag is OFF.
        summary.pop("commercial_opportunity_layer_v1", None)
        return summary
    try:
        pkg = compose_commercial_opportunity_layer_v1(
            summary,
            store_slug=str(summary.get("store_slug") or ""),
        )
        summary["commercial_opportunity_layer_v1"] = pkg
    except Exception:  # noqa: BLE001 — fail closed: operational Home still renders
        summary["commercial_opportunity_layer_v1"] = empty_package_v1(
            enabled=True, reason="attach_failed"
        )
        summary["commercial_opportunity_layer_v1"]["ok"] = False
    return summary


__all__ = ["attach_commercial_opportunity_layer_to_summary_v1"]
