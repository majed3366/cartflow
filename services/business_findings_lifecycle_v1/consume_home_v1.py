# -*- coding: utf-8 -*-
"""
Home consumption of persisted Business Findings.

Home must never call the Business Findings engine.
"""
from __future__ import annotations

from typing import Any, Optional

from services.business_findings_lifecycle_v1.flag_v1 import (
    business_findings_lifecycle_v1_enabled,
)
from services.business_findings_lifecycle_v1.lifecycle_v1 import advance_state
from services.business_findings_lifecycle_v1.persistence_v1 import (
    load_current_findings_v1,
    save_record_fields_v1,
)
from services.business_findings_lifecycle_v1.types_v1 import (
    BFL_VERSION_V1,
    LS_DISPLAYED,
    LS_SURFACE_ELIGIBLE,
    VIS_DISPLAYED,
)


def load_current_findings_package_v1(
    store_slug: str,
    *,
    mark_displayed: bool = True,
) -> dict[str, Any]:
    """
    Build a findings_package compatible with apply_home_commercial_intelligence_v1.

    Only surface-eligible current findings are included.
    """
    slug = (store_slug or "").strip()[:255]
    empty = {
        "findings": [],
        "engine_version": "business_findings_lifecycle_v1",
        "bfl_version": BFL_VERSION_V1,
        "evidence": {"loaded_from": "business_findings_table"},
        "ok": False,
        "source": "lifecycle_consume",
    }
    if not slug or not business_findings_lifecycle_v1_enabled():
        empty["errors"] = ["bfl_disabled_or_empty_slug"]
        return empty

    rows = load_current_findings_v1(slug, lifecycle_min=LS_SURFACE_ELIGIBLE)
    findings: list[dict[str, Any]] = []
    for rec in rows:
        routing = rec.get("routing") or {}
        surface = routing.get("surface") or {}
        if not surface.get("eligible") and not rec.get("home_eligible"):
            # Prefer payload home_eligible from original engine dict
            payload = rec.get("payload") or {}
            if not payload.get("home_eligible"):
                continue
        payload = dict(rec.get("payload") or {})
        if not payload.get("finding_id"):
            payload["finding_id"] = rec.get("finding_id")
        if not payload.get("finding_type"):
            payload["finding_type"] = rec.get("finding_type")
        if not payload.get("title"):
            payload["title"] = rec.get("title")
        if not payload.get("merchant_summary"):
            payload["merchant_summary"] = rec.get("merchant_summary")
        if not payload.get("confidence_level"):
            payload["confidence_level"] = rec.get("confidence")
        if not payload.get("recommended_direction"):
            payload["recommended_direction"] = rec.get("recommended_action")
        payload["lifecycle_state"] = rec.get("lifecycle_state")
        payload["bfl_version"] = BFL_VERSION_V1
        findings.append(payload)

        if mark_displayed and rec.get("lifecycle_state") == LS_SURFACE_ELIGIBLE:
            ok, _ = advance_state(
                rec, LS_DISPLAYED, reason="home_consume_package"
            )
            if ok:
                rec["visibility_state"] = VIS_DISPLAYED
                diag = dict(rec.get("diagnostics") or {})
                diag["displayed"] = True
                diag["stopped_at"] = LS_DISPLAYED
                rec["diagnostics"] = diag
                save_record_fields_v1(rec)

    return {
        "findings": findings,
        "engine_version": "business_findings_lifecycle_v1",
        "bfl_version": BFL_VERSION_V1,
        "evidence": {"loaded_from": "business_findings_table"},
        "ok": True,
        "source": "lifecycle_consume",
        "count": len(findings),
    }


__all__ = ["load_current_findings_package_v1"]
