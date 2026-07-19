# -*- coding: utf-8 -*-
"""
Project BusinessFindingV1 → Commerce Intelligence canonical record.

Does not invent findings. Does not call Home. Deterministic; no AI.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import norm
from services.commerce_intelligence.contract_v1 import (
    STATUS_ACTIONABLE,
    STATUS_INSUFFICIENT,
    STATUS_LEARNING,
    STATUS_MONITOR,
    STATUS_READY,
    canonical_record_v1,
    confidence_label_ar_v1,
)
from services.commerce_intelligence.domains_v1 import (
    DOMAIN_GUIDANCE,
    domain_for_dimension_v1,
    is_guidance_eligible_v1,
    source_domains_for_finding_v1,
)
from services.commercial_question_registry_v1 import resolve_question_for_finding_v1

# Merchant-facing guidance templates (only when eligible)
_GUIDANCE_AR = {
    "act_now": "نفّذ إجراءً واضحاً الآن — الأدلة كافية لاتخاذ قرار.",
    "test": "اختبر تغييراً محدوداً قبل تعميمه.",
    "investigate": "راجع صفحة المنتج أو مسار الشراء قبل التوصية بخصم.",
    "monitor": "راقب هذا النمط — لا توصِ بخصم بعد.",
    "no_action": "لا إجراء مطلوب الآن — استمر في المراقبة.",
    "insufficient_evidence": "اجمع أدلة إضافية قبل أي توصية تجارية.",
}


def _map_status_v1(finding: Mapping[str, Any]) -> str:
    st = norm(finding.get("status")).lower()
    rec = norm(finding.get("recommendation_type")).lower()
    conf = norm(finding.get("confidence_level")).lower()
    if st in ("insufficient_evidence",) or conf == "insufficient":
        return STATUS_INSUFFICIENT
    if st == "conflicting_evidence":
        return STATUS_LEARNING
    if rec == "act_now":
        return STATUS_ACTIONABLE
    if rec == "monitor":
        return STATUS_MONITOR
    if st in ("confirmed", "emerging", "strengthening", "weakening"):
        return STATUS_READY
    return STATUS_LEARNING


def _recommendation_ar_v1(finding: Mapping[str, Any], *, guidance_domain: bool) -> dict[str, Any]:
    rec_type = norm(finding.get("recommendation_type")) or "insufficient_evidence"
    directed = norm(finding.get("recommended_direction"))
    conf = norm(finding.get("confidence_level"))
    status = norm(finding.get("status"))
    # Insufficient / conflicting → honest “collect more evidence” (never action-eligible)
    if status in ("insufficient_evidence", "conflicting_evidence") or conf == "insufficient":
        return {
            "text_ar": _GUIDANCE_AR["insufficient_evidence"],
            "type": "insufficient_evidence",
            "eligible": False,
        }
    eligible = is_guidance_eligible_v1(
        confidence=conf, status=status, recommendation_type=rec_type
    )
    if not eligible and guidance_domain:
        return {
            "text_ar": _GUIDANCE_AR["insufficient_evidence"],
            "type": "insufficient_evidence",
            "eligible": False,
        }
    if directed:
        text = directed
    else:
        text = _GUIDANCE_AR.get(rec_type, _GUIDANCE_AR["insufficient_evidence"])
    # Soften action language outside guidance domain — still carry direction
    if not guidance_domain and rec_type == "act_now":
        text = directed or "هذا النمط يستحق انتباه التاجر."
    return {
        "text_ar": text,
        "type": rec_type if eligible or not guidance_domain else "insufficient_evidence",
        "eligible": bool(eligible) if guidance_domain else False,
    }


def project_finding_to_intelligence_record_v1(
    finding: Mapping[str, Any],
    *,
    force_domain: str = "",
) -> Optional[dict[str, Any]]:
    """
    Project one governed finding into a canonical intelligence record.

    Returns None if the finding cannot resolve a commercial question.
    """
    if not isinstance(finding, Mapping):
        return None
    q = resolve_question_for_finding_v1(finding)
    if not q:
        return None
    dim = norm(q.get("dimension"))
    domain = norm(force_domain) or domain_for_dimension_v1(dim)
    sources = source_domains_for_finding_v1(finding, question_dimension=dim)
    if domain not in sources:
        sources = [domain] + [d for d in sources if d != domain]

    finding_id = norm(finding.get("finding_id")) or "finding_unknown"
    record_id = f"ci_{domain}_{finding_id}"[:180]
    conf_level = norm(finding.get("confidence_level")) or "insufficient"
    guidance_domain = domain == DOMAIN_GUIDANCE

    return canonical_record_v1(
        record_id=record_id,
        store_slug=norm(finding.get("store_slug")),
        domain=domain,
        question={
            "id": norm(q.get("question_id")),
            "text_ar": norm(q.get("question_ar")),
            "text_en": norm(q.get("question_en")),
        },
        finding={
            "text_ar": norm(finding.get("merchant_summary"))
            or norm(finding.get("title"))
            or norm(finding.get("commercial_meaning")),
            "text_en": "",
            "finding_id": finding_id,
            "finding_type": norm(finding.get("finding_type")),
        },
        evidence={
            "summary_ar": norm(finding.get("evidence_summary")),
            "refs": list(finding.get("evidence_refs") or [])[:12],
            "sample_size": int(finding.get("sample_size") or 0),
        },
        confidence={
            "level": conf_level,
            "label_ar": confidence_label_ar_v1(conf_level),
        },
        recommendation=_recommendation_ar_v1(finding, guidance_domain=guidance_domain),
        status=_map_status_v1(finding),
        source_domains=sources,
        provenance={
            "finding_id": finding_id,
            "commercial_question_id": norm(q.get("question_id")),
        },
    )


def project_guidance_from_finding_v1(
    finding: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Second projection into Commercial Guidance domain when evidence supports it.

    Product/Customer/Store records remain primary; guidance is additive.
    """
    base = project_finding_to_intelligence_record_v1(
        finding, force_domain=DOMAIN_GUIDANCE
    )
    if not base:
        return None
    rec = base.get("recommendation") or {}
    # Always emit guidance record for insufficient (collect evidence) or eligible actions
    if not rec.get("eligible") and base.get("status") not in (
        STATUS_INSUFFICIENT,
        STATUS_LEARNING,
    ):
        # Non-eligible monitor-only noise — skip duplicate guidance
        if norm(rec.get("type")) not in ("insufficient_evidence", "monitor", "no_action"):
            return None
    # Re-stamp recommendation eligibility for guidance domain
    finding_conf = norm(finding.get("confidence_level"))
    finding_status = norm(finding.get("status"))
    finding_rec = norm(finding.get("recommendation_type"))
    eligible = is_guidance_eligible_v1(
        confidence=finding_conf,
        status=finding_status,
        recommendation_type=finding_rec,
    )
    base["recommendation"] = _recommendation_ar_v1(
        finding, guidance_domain=True
    )
    if not eligible and base["status"] not in (STATUS_INSUFFICIENT, STATUS_LEARNING):
        base["status"] = STATUS_MONITOR
    # Ensure source_domains include guidance + original domains
    src = list(base.get("source_domains") or [])
    if DOMAIN_GUIDANCE not in src:
        src.append(DOMAIN_GUIDANCE)
    # Include product/customer/store provenance from primary mapping
    primary = project_finding_to_intelligence_record_v1(finding)
    if primary:
        for d in primary.get("source_domains") or []:
            if d not in src:
                src.append(d)
    base["source_domains"] = src
    base["domain"] = DOMAIN_GUIDANCE
    base["record_id"] = f"ci_guidance_{norm(finding.get('finding_id'))}"[:180]
    return base


__all__ = [
    "project_finding_to_intelligence_record_v1",
    "project_guidance_from_finding_v1",
]
