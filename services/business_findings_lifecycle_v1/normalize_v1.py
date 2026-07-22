# -*- coding: utf-8 -*-
"""Normalize engine finding dict → durable Business Finding record shape."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import (
    REC_ACT_NOW,
    REC_INVESTIGATE,
    REC_TEST,
    STATUS_CONFIRMED,
    STATUS_INSUFFICIENT,
    norm,
)
from services.business_findings_lifecycle_v1.types_v1 import (
    BFL_GENERATION_VERSION_V1,
    BFL_VERSION_V1,
    LS_DETECTED,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_INFO,
    SEV_LOW,
    SEV_MEDIUM,
    VIS_HIDDEN,
)


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_iso(raw: Any) -> Optional[datetime]:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.replace(microsecond=0)
    except ValueError:
        return None


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _severity_from_finding(f: Mapping[str, Any]) -> str:
    rec = norm(f.get("recommendation_type"))
    status = norm(f.get("status"))
    if rec == REC_ACT_NOW or status == STATUS_CONFIRMED:
        return SEV_HIGH
    if rec == REC_INVESTIGATE:
        return SEV_MEDIUM
    if rec == REC_TEST:
        return SEV_MEDIUM
    if status == STATUS_INSUFFICIENT:
        return SEV_INFO
    return SEV_LOW


def _product_id(f: Mapping[str, Any]) -> Optional[str]:
    scope = norm(f.get("finding_scope"))
    ref = norm(f.get("scope_reference"))
    if scope == "product" and ref:
        return ref[:256]
    return None


def normalize_engine_finding_v1(
    finding: Mapping[str, Any],
    *,
    store_slug: str,
    merchant_id: str = "",
    as_of: Optional[datetime] = None,
    engine_version: str = "",
) -> dict[str, Any]:
    """Map BusinessFindingV1 engine dict → BFL durable record (in-memory)."""
    now = _utc_naive_now()
    generated = _parse_iso(finding.get("generated_at")) or now
    anchor = as_of or generated
    expires = generated + timedelta(days=14)
    finding_id = norm(finding.get("finding_id")) or f"finding:unknown:{_sha(dict(finding))[:16]}"
    evidence = {
        "evidence_summary": finding.get("evidence_summary") or "",
        "evidence_refs": list(finding.get("evidence_refs") or []),
        "sample_size": finding.get("sample_size"),
        "observed_period": finding.get("observed_period") or {},
        "comparison_period": finding.get("comparison_period") or {},
    }
    reasoning = {
        "commercial_meaning": finding.get("commercial_meaning") or "",
        "business_impact": finding.get("business_impact") or "",
        "status": finding.get("status") or "",
        "recommendation_type": finding.get("recommendation_type") or "",
        "is_confirmed_cause": bool(finding.get("is_confirmed_cause")),
        "family_key": finding.get("family_key") or "",
    }
    fp = _sha(
        {
            "id": finding_id,
            "type": finding.get("finding_type"),
            "title": finding.get("title"),
            "summary": finding.get("merchant_summary"),
            "evidence": evidence,
            "conf": finding.get("confidence_level"),
        }
    )
    return {
        "finding_id": finding_id[:128],
        "finding_type": norm(finding.get("finding_type"))[:96],
        "store_slug": norm(store_slug)[:255],
        "merchant_id": norm(merchant_id)[:64],
        "product_id": _product_id(finding),
        "category_id": None,
        "evidence": evidence,
        "confidence": norm(finding.get("confidence_level")),
        "confidence_score": str(finding.get("confidence_score") or ""),
        "severity": _severity_from_finding(finding),
        "generated_at": generated,
        "expires_at": expires,
        "lifecycle_state": LS_DETECTED,
        "visibility_state": VIS_HIDDEN,
        "reasoning": reasoning,
        "recommended_action": str(
            finding.get("recommended_direction") or finding.get("recommended_action") or ""
        ),
        "title": str(finding.get("title") or ""),
        "merchant_summary": str(finding.get("merchant_summary") or ""),
        "payload": dict(finding),
        "routing": {},
        "lifecycle_events": [],
        "diagnostics": {
            "generated": True,
            "persisted": False,
            "routed": False,
            "routed_knowledge": False,
            "routed_guidance": False,
            "routed_operational_truth": False,
            "surface_eligible": False,
            "displayed": False,
            "stopped_at": LS_DETECTED,
        },
        "fingerprint": fp,
        "engine_version": engine_version or norm(finding.get("engine_version")),
        "lifecycle_version": BFL_VERSION_V1,
        "generation_version": BFL_GENERATION_VERSION_V1,
        "is_current": True,
        "as_of": anchor,
        "as_of_key": anchor.strftime("%Y%m%d%H%M%S"),
        "home_eligible": bool(finding.get("home_eligible")),
        "authoritative_surface": norm(finding.get("authoritative_surface")),
    }


__all__ = ["normalize_engine_finding_v1"]
