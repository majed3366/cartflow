# -*- coding: utf-8 -*-
"""BFL V1 — production probe GET /dev/business-findings-lifecycle."""
from __future__ import annotations

from typing import Any

from services.business_findings_lifecycle_v1.flag_v1 import (
    ENV_BUSINESS_FINDINGS_LIFECYCLE_V1,
    business_findings_lifecycle_v1_enabled,
)
from services.business_findings_lifecycle_v1.materialize_v1 import (
    materialize_business_findings_lifecycle_v1,
)
from services.business_findings_lifecycle_v1.persistence_v1 import (
    load_current_findings_v1,
)
from services.business_findings_lifecycle_v1.types_v1 import BFL_VERSION_V1

_ALLOWED_STORES = frozenset({"demo"})


def build_business_findings_lifecycle_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    demo_fixture: bool = False,
    admit_review_fixtures: bool = False,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": business_findings_lifecycle_v1_enabled(),
        "flag_env": ENV_BUSINESS_FINDINGS_LIFECYCLE_V1,
        "bfl_version": BFL_VERSION_V1,
        "materialize": {},
        "findings": [],
        "diagnostics": [],
        "errors": [],
        "home_must_not_generate": True,
        "surfaces_consume_only": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    if materialize:
        # Demo probe may use fixture only when explicitly requested (review).
        mat = materialize_business_findings_lifecycle_v1(
            slug,
            load_db=not demo_fixture,
            demo_fixture=bool(demo_fixture),
            admit_review_fixtures=bool(admit_review_fixtures or demo_fixture),
        )
        out["materialize"] = {
            "ok": mat.get("ok"),
            "detected": mat.get("detected"),
            "validated": mat.get("validated"),
            "persisted": mat.get("persisted"),
            "knowledge_routed": mat.get("knowledge_routed"),
            "ot_routed": mat.get("ot_routed"),
            "surface_eligible": mat.get("surface_eligible"),
            "errors": mat.get("errors") or [],
            "stopped_stages": mat.get("stopped_stages") or {},
        }
        out["errors"].extend(list(mat.get("errors") or []))

    rows = load_current_findings_v1(slug)
    for rec in rows:
        diag = dict(rec.get("diagnostics") or {})
        out["findings"].append(
            {
                "finding_id": rec.get("finding_id"),
                "finding_type": rec.get("finding_type"),
                "lifecycle_state": rec.get("lifecycle_state"),
                "visibility_state": rec.get("visibility_state"),
                "confidence": rec.get("confidence"),
                "severity": rec.get("severity"),
                "title": rec.get("title"),
                "diagnostics": {
                    "generated": bool(diag.get("generated")),
                    "persisted": bool(diag.get("persisted")),
                    "routed": bool(
                        diag.get("routed")
                        or (
                            diag.get("routed_knowledge")
                            and diag.get("routed_operational_truth")
                        )
                    ),
                    "routed_knowledge": bool(diag.get("routed_knowledge")),
                    "routed_guidance": bool(diag.get("routed_guidance")),
                    "routed_operational_truth": bool(
                        diag.get("routed_operational_truth")
                    ),
                    "surface_eligible": bool(diag.get("surface_eligible")),
                    "displayed": bool(diag.get("displayed")),
                    "stopped_at": diag.get("stopped_at") or rec.get("lifecycle_state"),
                },
            }
        )
        out["diagnostics"].append(
            {
                "finding_id": rec.get("finding_id"),
                **(out["findings"][-1]["diagnostics"]),
            }
        )

    out["ok"] = bool(
        out["foundation_enabled"]
        and "store_not_allowlisted" not in out["errors"]
        and "bfl_disabled" not in out["errors"]
        and (
            not materialize
            or (out.get("materialize") or {}).get("ok")
        )
    )
    return out


__all__ = ["build_business_findings_lifecycle_prod_probe_v1"]
