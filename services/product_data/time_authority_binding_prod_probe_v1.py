# -*- coding: utf-8 -*-
"""TABF V1 — production probe GET /dev/time-authority."""
from __future__ import annotations

from typing import Any

from services.product_data.time_authority_binding_flag_v1 import (
    ENV_TIME_AUTHORITY_BINDING_V1,
    time_authority_binding_v1_enabled,
)
from services.product_data.time_authority_binding_foundation_v1 import (
    generate_time_authority_binding_v1,
)
from services.product_data.time_authority_binding_types_v1 import TABF_VERSION_V1

_ALLOWED_STORES = frozenset({"demo"})


def build_time_authority_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": time_authority_binding_v1_enabled(),
        "flag_env": ENV_TIME_AUTHORITY_BINDING_V1,
        "tabf_version": TABF_VERSION_V1,
        "assembly_window": window,
        "binding_status": {},
        "canonical_clocks": {},
        "replay_consistency": {},
        "ordering_conflicts": [],
        "chronology_warnings": [],
        "drift_detection": [],
        "stale_interpretations": [],
        "subsystem_bindings": {},
        "scf_binding": {},
        "operational_truth_binding": {},
        "merchant_experience_binding": {},
        "canonical_fingerprint": "",
        "errors": [],
        "no_analytics": True,
        "no_timeline_redesign": True,
        "no_guidance_logic_change": True,
        "no_knowledge_logic_change": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    report = generate_time_authority_binding_v1(slug, assembly_window=window)
    for key in (
        "ok",
        "as_of",
        "binding_status",
        "canonical_clocks",
        "replay_consistency",
        "ordering_conflicts",
        "chronology_warnings",
        "drift_detection",
        "stale_interpretations",
        "binding_audit",
        "scf_binding",
        "operational_truth_binding",
        "merchant_experience_binding",
        "canonical_fingerprint",
        "inventory",
        "registries_valid",
        "enabled",
    ):
        if key in report:
            out[key] = report[key]
    out["subsystem_bindings"] = report.get("binding_audit") or {}
    out["errors"].extend(list(report.get("errors") or []))
    if "store_not_allowlisted" in out["errors"]:
        out["ok"] = False
    return out


__all__ = ["build_time_authority_prod_probe_v1"]
