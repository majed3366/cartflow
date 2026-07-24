# -*- coding: utf-8 -*-
"""
Observation Foundation V1 — readiness for Product Intelligence V1.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.observation_foundation_v1.assemble_v1 import assemble_observation_foundation_v1
from services.observation_foundation_v1.catalog_v1 import (
    FOUNDATION_VERSION,
    OBSERVATION_MODEL_V1,
)
from services.observation_foundation_v1.correlation_v1 import STATEMENT_CAPABILITIES_V1
from services.observation_foundation_v1.flag_v1 import observation_foundation_v1_enabled

# Product Intelligence V1 blockers (must be resolved before PI claims)
_PI_BLOCKERS = (
    "product_view_observed_v1 unavailable (no durable PDP views)",
    "time_spent_observed_v1 unavailable (no dwell persist)",
    "return_to_product_observed_v1 unavailable (returns are store-scoped)",
    "product_open_observed_v1 unavailable",
)


def assess_product_intelligence_readiness_v1(
    store_slug: str = "",
    *,
    package: Optional[Mapping[str, Any]] = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Readiness assessment for Product Intelligence V1.

    GO only when observation coverage + correlation chain can support
    interest/conversion, reason strength, repeat-return, and absence claims
    without inventing views/dwell.
    """
    if not observation_foundation_v1_enabled(environ=environ):
        return {
            "ok": False,
            "ready_for_product_intelligence_v1": False,
            "verdict": "NO-GO",
            "reason": "Observation Foundation V1 disabled",
            "schema": FOUNDATION_VERSION,
        }

    pkg = dict(package) if isinstance(package, Mapping) else assemble_observation_foundation_v1(
        store_slug, environ=environ
    )
    counts = pkg.get("counts") or {}
    catalog_counts = (pkg.get("observation_model") or {}).get("counts") or {}
    caps_ready = list(pkg.get("statement_capabilities_ready") or [])
    wired = int(catalog_counts.get("wired") or 0)
    unavailable = int(catalog_counts.get("unavailable") or 0)

    # Structural readiness (model) vs store data readiness
    structural_ok = wired >= 5 and unavailable <= 4
    data_ok = int(counts.get("observations") or 0) >= 1
    chain_ok = int(counts.get("correlations") or 0) >= 1
    statement_floor = len(caps_ready) >= 1

    ready = bool(structural_ok and data_ok and chain_ok)
    verdict = "GO" if ready and statement_floor else ("CONDITIONAL" if structural_ok else "NO-GO")

    gaps = [
        e["observation_type"] + ": " + (e.get("gap") or e["evidence_status"])
        for e in OBSERVATION_MODEL_V1
        if e["evidence_status"] in {"unavailable", "partial"}
    ]

    return {
        "ok": True,
        "schema": FOUNDATION_VERSION,
        "layer": "product_intelligence_readiness_v1",
        "ready_for_product_intelligence_v1": ready and statement_floor,
        "verdict": verdict,
        "structural": {
            "wired_observation_types": wired,
            "unavailable_observation_types": unavailable,
            "structural_ok": structural_ok,
        },
        "store": {
            "store_slug": pkg.get("store_slug"),
            "observations": counts.get("observations"),
            "correlations": counts.get("correlations"),
            "statement_capabilities_ready": caps_ready,
            "data_ok": data_ok,
            "chain_ok": chain_ok,
        },
        "statement_capabilities_defined": [
            s["capability_id"] for s in STATEMENT_CAPABILITIES_V1
        ],
        "blockers_for_full_pi_v1": list(_PI_BLOCKERS),
        "evidence_gaps": gaps,
        "assessment": (
            "Observation Foundation can correlate cart/hesitation/return/purchase today. "
            "Product Intelligence V1 must not claim view/dwell/quality without those observations. "
            + (
                "Store has enough correlated observations for limited PI statements."
                if ready and statement_floor
                else "Store lacks correlated observation mass for PI statements yet."
                if structural_ok
                else "Catalog coverage insufficient."
            )
        ),
        "ui": False,
    }


__all__ = ["assess_product_intelligence_readiness_v1"]
