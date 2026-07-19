# -*- coding: utf-8 -*-
"""
Commerce Intelligence canonical record contract V1.

Home (and every future executive surface) must consume this shape.
Surfaces must not invent commercial understanding.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.business_findings_contract_v1 import norm, utc_now_iso

FOUNDATION_VERSION = "commerce_intelligence_foundation_v1"
RECORD_VERSION = "commerce_intelligence_record_v1"

# Record status (merchant-facing lifecycle of the intelligence claim)
STATUS_READY = "ready"
STATUS_INSUFFICIENT = "insufficient_evidence"
STATUS_MONITOR = "monitor"
STATUS_ACTIONABLE = "actionable"
STATUS_LEARNING = "still_learning"

REQUIRED_FIELDS = (
    "question",
    "finding",
    "evidence",
    "confidence",
    "recommendation",
    "status",
    "source_domains",
)


def empty_canonical_record_v1(
    *,
    record_id: str,
    store_slug: str,
    domain: str,
) -> dict[str, Any]:
    return {
        "record_version": RECORD_VERSION,
        "foundation_version": FOUNDATION_VERSION,
        "record_id": norm(record_id) or "ci_unknown",
        "store_slug": norm(store_slug),
        "domain": norm(domain),
        "question": {"id": "", "text_ar": "", "text_en": ""},
        "finding": {"text_ar": "", "text_en": "", "finding_id": "", "finding_type": ""},
        "evidence": {"summary_ar": "", "refs": [], "sample_size": 0},
        "confidence": {"level": "insufficient", "label_ar": "أدلة غير كافية"},
        "recommendation": {
            "text_ar": "",
            "type": "insufficient_evidence",
            "eligible": False,
        },
        "status": STATUS_INSUFFICIENT,
        "source_domains": [norm(domain)] if domain else [],
        "generated_at": utc_now_iso(),
        "ai_used": False,
        # Traceability (not for merchant L0 copy)
        "provenance": {
            "finding_id": "",
            "commercial_question_id": "",
            "engine": FOUNDATION_VERSION,
        },
    }


def canonical_record_v1(
    *,
    record_id: str,
    store_slug: str,
    domain: str,
    question: Mapping[str, Any],
    finding: Mapping[str, Any],
    evidence: Mapping[str, Any],
    confidence: Mapping[str, Any],
    recommendation: Mapping[str, Any],
    status: str,
    source_domains: Sequence[str],
    provenance: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build a validated canonical intelligence record."""
    domains = [norm(d) for d in source_domains if norm(d)]
    if not domains and domain:
        domains = [norm(domain)]
    rec = empty_canonical_record_v1(
        record_id=record_id, store_slug=store_slug, domain=domain
    )
    rec["question"] = {
        "id": norm(question.get("id")),
        "text_ar": norm(question.get("text_ar")),
        "text_en": norm(question.get("text_en")),
    }
    rec["finding"] = {
        "text_ar": norm(finding.get("text_ar")),
        "text_en": norm(finding.get("text_en")),
        "finding_id": norm(finding.get("finding_id")),
        "finding_type": norm(finding.get("finding_type")),
    }
    refs = evidence.get("refs") or []
    if not isinstance(refs, list):
        refs = []
    rec["evidence"] = {
        "summary_ar": norm(evidence.get("summary_ar")),
        "refs": [norm(r) for r in refs if norm(r)][:12],
        "sample_size": int(evidence.get("sample_size") or 0),
    }
    rec["confidence"] = {
        "level": norm(confidence.get("level")) or "insufficient",
        "label_ar": norm(confidence.get("label_ar")) or "أدلة غير كافية",
    }
    rec["recommendation"] = {
        "text_ar": norm(recommendation.get("text_ar")),
        "type": norm(recommendation.get("type")) or "insufficient_evidence",
        "eligible": bool(recommendation.get("eligible")),
    }
    rec["status"] = norm(status) or STATUS_INSUFFICIENT
    rec["source_domains"] = domains
    if provenance:
        rec["provenance"] = {
            "finding_id": norm(provenance.get("finding_id")),
            "commercial_question_id": norm(provenance.get("commercial_question_id")),
            "engine": FOUNDATION_VERSION,
        }
    return rec


def record_is_complete_v1(record: Mapping[str, Any]) -> bool:
    if not isinstance(record, Mapping):
        return False
    for key in REQUIRED_FIELDS:
        if key not in record:
            return False
    q = record.get("question") or {}
    if not norm(q.get("text_ar")) and not norm(q.get("id")):
        return False
    f = record.get("finding") or {}
    if not norm(f.get("text_ar")):
        return False
    domains = record.get("source_domains") or []
    if not isinstance(domains, list) or not domains:
        return False
    return True


def confidence_label_ar_v1(level: str) -> str:
    lv = norm(level).lower()
    if lv in ("high", "confirmed"):
        return "عالية"
    if lv == "medium":
        return "متوسطة"
    if lv == "low":
        return "منخفضة"
    return "أدلة غير كافية"


__all__ = [
    "FOUNDATION_VERSION",
    "RECORD_VERSION",
    "REQUIRED_FIELDS",
    "STATUS_ACTIONABLE",
    "STATUS_INSUFFICIENT",
    "STATUS_LEARNING",
    "STATUS_MONITOR",
    "STATUS_READY",
    "canonical_record_v1",
    "confidence_label_ar_v1",
    "empty_canonical_record_v1",
    "record_is_complete_v1",
]
