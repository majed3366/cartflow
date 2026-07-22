# -*- coding: utf-8 -*-
"""OTIF V1 — production probe GET /dev/operational-truth."""
from __future__ import annotations

from typing import Any

from services.product_data.operational_truth_flag_v1 import (
    ENV_OPERATIONAL_TRUTH_V1,
    operational_truth_v1_enabled,
)
from services.product_data.operational_truth_foundation_v1 import (
    generate_operational_truth_v1,
    verify_operational_truth_determinism_v1,
)
from services.product_data.operational_truth_registry_v1 import (
    operational_truth_registry_valid_v1,
)
from services.product_data.operational_truth_types_v1 import OT_VERSION_V1
from services.product_data.surface_composition_foundation_v1 import (
    generate_surface_compositions_v1,
)
from services.product_data.surface_composition_types_v1 import (
    SOURCE_OPERATIONAL_TRUTH,
    VIS_VISIBLE,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_operational_truth_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = operational_truth_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": operational_truth_v1_enabled(),
        "flag_env": ENV_OPERATIONAL_TRUTH_V1,
        "ot_version": OT_VERSION_V1,
        "assembly_window": window,
        "operational_truths": [],
        "severity": {},
        "routed_surfaces": {},
        "freshness": {},
        "stability": {},
        "suppressed_truths": [],
        "orphan_truths": [],
        "visibility_decisions": {},
        "scf_integration": {},
        "deterministic": False,
        "canonical_fingerprint": "",
        "errors": list(reg_errors),
        "registries_valid": bool(reg_ok),
        "no_recommendations": True,
        "no_guidance": True,
        "no_knowledge_generation": True,
        "non_demo_writes": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    report = generate_operational_truth_v1(slug, assembly_window=window)
    out["as_of"] = report.get("as_of")
    out["canonical_fingerprint"] = report.get("canonical_fingerprint") or ""
    out["errors"].extend(list(report.get("errors") or []))
    out["operational_truths"] = [
        {
            "truth_id": p.get("truth_id"),
            "severity": p.get("severity"),
            "count": p.get("count"),
            "visibility": p.get("visibility"),
            "stability": p.get("stability"),
            "freshness": p.get("freshness"),
            "requires_merchant_attention": p.get("requires_merchant_attention"),
            "destination_surfaces": p.get("destination_surfaces"),
            "explainability": p.get("explainability"),
        }
        for p in (report.get("packages") or [])
    ]
    out["severity"] = dict(report.get("severity_counts") or {})
    out["suppressed_truths"] = [
        p.get("truth_id")
        for p in (report.get("suppressed_packages") or [])
    ]
    out["orphan_truths"] = [
        p.get("truth_id")
        for p in (report.get("packages") or [])
        if not (p.get("destination_surfaces") or [])
    ]
    routed: dict[str, list[str]] = {}
    freshness: dict[str, int] = {}
    stability: dict[str, int] = {}
    visibility_decisions: dict[str, int] = {}
    for p in report.get("packages") or []:
        for s in p.get("destination_surfaces") or []:
            routed.setdefault(str(s), []).append(str(p.get("truth_id")))
        freshness[str(p.get("freshness") or "unknown")] = (
            freshness.get(str(p.get("freshness") or "unknown"), 0) + 1
        )
        stability[str(p.get("stability") or "unknown")] = (
            stability.get(str(p.get("stability") or "unknown"), 0) + 1
        )
        visibility_decisions[str(p.get("visibility") or "unknown")] = (
            visibility_decisions.get(str(p.get("visibility") or "unknown"), 0) + 1
        )
    out["routed_surfaces"] = routed
    out["freshness"] = freshness
    out["stability"] = stability
    out["visibility_decisions"] = visibility_decisions

    from datetime import datetime

    anchor = None
    if report.get("as_of"):
        try:
            anchor = datetime.fromisoformat(str(report["as_of"]))
        except ValueError:
            anchor = None
    det = verify_operational_truth_determinism_v1(
        slug, assembly_window=window, as_of=anchor
    )
    out["deterministic"] = bool(det.get("deterministic"))

    # SCF integration: OT compositions visible on Home / Decision / Carts.
    scf = generate_surface_compositions_v1(
        slug, assembly_window=window, as_of=anchor
    )
    ot_comps = [
        c
        for c in (scf.get("compositions") or [])
        if c.get("source_type") == SOURCE_OPERATIONAL_TRUTH
    ]
    ot_visible = [c for c in ot_comps if c.get("visibility") == VIS_VISIBLE]
    by_surface: dict[str, int] = {}
    for c in ot_visible:
        sid = str(c.get("surface_id") or "")
        by_surface[sid] = by_surface.get(sid, 0) + 1
    out["scf_integration"] = {
        "ok": bool(scf.get("ok")),
        "operational_truth_compositions": len(ot_comps),
        "visible_operational_truth": len(ot_visible),
        "visible_by_surface": by_surface,
        "home_has_ot": by_surface.get("home", 0) > 0,
        "decision_has_ot": by_surface.get("decision_workspace", 0) > 0,
        "inputs_include_ot": bool(
            (scf.get("inputs") or {}).get("operational_truth")
        ),
    }

    out["ok"] = bool(
        report.get("ok")
        and out["registries_valid"]
        and out["deterministic"]
        and out["orphan_truths"] == []
        and out["scf_integration"].get("inputs_include_ot")
        and "store_not_allowlisted" not in out["errors"]
        and out["no_recommendations"]
        and out["no_guidance"]
    )
    return out


__all__ = ["build_operational_truth_prod_probe_v1"]
