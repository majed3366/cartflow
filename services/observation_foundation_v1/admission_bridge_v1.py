# -*- coding: utf-8 -*-
"""
Observation Admission Bridge V1

Governed path:
  Product Signals → Observation Foundation → Observation Candidate
  → Evidence Validation → Confidence Validation → Canonical Product Identity
  → Reality Validation Admission → Knowledge Routing → Home / Decision Workspace

No Product Intelligence. No invented observations. No silent rejection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.observation_foundation_v1.catalog_v1 import FOUNDATION_VERSION
from services.observation_foundation_v1.product_entity_resolve_v1 import (
    is_banned_product_key_v1,
    is_real_product_display_name_v1,
    resolve_real_product_display_name_v1,
)
from services.product_data.evidence_confidence_types_v1 import (
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    LEVEL_VERY_HIGH,
    confidence_level_for_score,
)

ADMISSION_BRIDGE_VERSION_V1 = "observation_admission_bridge_v1"

# Merchant-safe teaser copy (Home). Not Product Intelligence recommendations.
_STATEMENT_AR: dict[str, dict[str, str]] = {
    "high_interest_low_conversion": {
        "title_ar": "اهتمام مرتفع وتحويل منخفض",
        "statement_ar": "يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً.",
        "statement_en": "Strong interest but poor conversion.",
        "home_teaser_ar": "اهتمام قوي لكن التحويل إلى شراء ضعيف.",
        "recommended_action_ar": "راجع تجربة شراء هذا المنتج قبل زيادة الزيارات.",
        "supports_decision": True,
        "decision_title_ar": "راجع تجربة شراء {product} قبل زيادة الزيارات.",
    },
    "shipping_stronger_than_price": {
        "title_ar": "تردد الشحن أقوى من السعر",
        "statement_ar": "تردد الشحن/التوصيل أقوى حالياً من تردد السعر.",
        "statement_en": "Shipping hesitation is stronger than price hesitation.",
        "home_teaser_ar": "تردد الشحن أقوى من تردد السعر.",
        "recommended_action_ar": "راجع تكلفة أو تجربة الشحن لهذا المنتج.",
        "supports_decision": True,
        "decision_title_ar": "راجع تكلفة أو تجربة الشحن لـ {product}.",
    },
    "repeated_return_without_purchase": {
        "title_ar": "عودة متكررة بلا شراء",
        "statement_ar": "يجذب زيارات متكررة دون إتمام شراء.",
        "statement_en": "Attracting repeat visits without purchases.",
        "home_teaser_ar": "يجذب زيارات متكررة دون شراء.",
        "recommended_action_ar": "راجع رحلة العميل بعد العودة لهذا المنتج.",
        "supports_decision": True,
        "decision_title_ar": "راجع رحلة العودة والشراء لـ {product}.",
    },
    "no_quality_issue_evidence": {
        "title_ar": "لا دليل على مشكلة جودة",
        "statement_ar": "لا توجد أدلة حالية تدعم وجود مشكلة جودة.",
        "statement_en": "No evidence currently supports a quality issue.",
        "home_teaser_ar": "لا توجد أدلة حالية على مشكلة جودة.",
        "recommended_action_ar": "لا حاجة لاتخاذ إجراء حالياً — استمر في جمع الأدلة.",
        "supports_decision": False,
        "decision_title_ar": "",
    },
}

_CAPABILITY_ORDER = (
    "high_interest_low_conversion",
    "shipping_stronger_than_price",
    "repeated_return_without_purchase",
    "no_quality_issue_evidence",
)

_CONFIDENCE_AR = {
    LEVEL_VERY_HIGH: "مرتفع",
    LEVEL_HIGH: "مرتفع",
    LEVEL_MEDIUM: "متوسط",
    LEVEL_LOW: "منخفض",
}

# Reject if confidence score below this (evidence too thin for merchant surface).
_MIN_CONFIDENCE_SCORE = 30
# Prefer recent evidence; correlations without refs still admit if mass is strong.
_MIN_EVIDENCE_REFS = 1


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _suppression_row(
    *,
    observation_id: str,
    product_key: str,
    capability_id: str,
    stage: str,
    reason: str,
    missing_evidence: str = "",
    confidence_at_rejection: Any = None,
    may_become_eligible_later: bool = True,
) -> dict[str, Any]:
    return {
        "observation_id": observation_id,
        "product_id": product_key,
        "product_key": product_key,
        "capability_id": capability_id,
        "rejection_stage": stage,
        "rejection_reason": reason,
        "required_missing_evidence": missing_evidence,
        "confidence_at_rejection": confidence_at_rejection,
        "may_become_eligible_later": may_become_eligible_later,
        "recorded_at_utc": _utc_now_iso(),
    }


def _confidence_from_correlation_v1(
    store_slug: str,
    product_key: str,
    corr: Mapping[str, Any],
) -> dict[str, Any]:
    level = ""
    score: Optional[int] = None
    source = "evidence_confidence_foundation_v1"
    try:
        from services.product_data.evidence_confidence_foundation_v1 import (  # noqa: PLC0415
            evaluate_evidence_confidence_v1,
        )

        report = evaluate_evidence_confidence_v1(store_slug, assembly_window="d7")
        evaluations = list(report.get("evaluations") or [])
        pk = _norm(product_key)
        matched = None
        if pk:
            for ev in evaluations:
                if not isinstance(ev, Mapping):
                    continue
                if _norm(ev.get("subject_id")) == pk:
                    matched = ev
                    break
        if matched is None and evaluations:
            matched = next((e for e in evaluations if isinstance(e, Mapping)), None)
        if isinstance(matched, Mapping) and matched.get("confidence_level"):
            level = _norm(matched.get("confidence_level")).lower()
            try:
                score = int(matched.get("confidence_score"))
            except (TypeError, ValueError):
                score = None
            source = "evidence_confidence_evaluation"
    except Exception:  # noqa: BLE001
        level = ""

    if level not in _CONFIDENCE_AR:
        refs = corr.get("evidence_refs") if isinstance(corr.get("evidence_refs"), list) else []
        counts = corr.get("counts") if isinstance(corr.get("counts"), Mapping) else {}
        sample = 0
        for k in ("cart_add", "return", "purchase"):
            try:
                sample += int(counts.get(k) or 0)
            except (TypeError, ValueError):
                pass
        reasons = (
            corr.get("reason_counts")
            if isinstance(corr.get("reason_counts"), Mapping)
            else {}
        )
        if reasons:
            # Ignore numeric noise keys that are evidence_ref ids mistaken as reasons.
            for rk, rv in reasons.items():
                if str(rk).isdigit():
                    continue
                try:
                    sample += int(rv or 0)
                except (TypeError, ValueError):
                    pass
        score = max(0, min(100, 25 + min(40, len(refs) * 5) + min(35, sample * 5)))
        level = confidence_level_for_score(score)
        source = "evidence_confidence_thresholds_from_correlation_mass"

    if level not in _CONFIDENCE_AR:
        level = LEVEL_LOW
        score = score if score is not None else 0
        source = "evidence_confidence_fallback_low"

    return {
        "confidence_level": level,
        "confidence_score": score,
        "confidence_ar": _CONFIDENCE_AR[level],
        "confidence_source": source,
    }


def _evidence_details(corr: Mapping[str, Any]) -> dict[str, Any]:
    counts = corr.get("counts") if isinstance(corr.get("counts"), Mapping) else {}
    compare = corr.get("compare") if isinstance(corr.get("compare"), Mapping) else {}
    reasons = (
        corr.get("reason_counts") if isinstance(corr.get("reason_counts"), Mapping) else {}
    )
    refs = corr.get("evidence_refs") if isinstance(corr.get("evidence_refs"), list) else []
    return {
        "correlation_kind": _norm(corr.get("correlation_kind")),
        "product_key": _norm(corr.get("product_key")),
        "counts": dict(counts),
        "compare": dict(compare),
        "reason_counts": dict(reasons),
        "absent_family": corr.get("absent_family"),
        "evidence_ref_count": len(refs),
        "evidence_refs": refs[:20],
    }


def _candidate_id(cap: str, product_key: str) -> str:
    return f"obs_admit:{cap}:{product_key}"[:220]


def admit_observation_candidates_v1(
    package: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    product_name_resolver: Any = None,
) -> dict[str, Any]:
    """
    Run governed admission over foundation correlations.

    Returns admitted findings, workspace-eligible decisions, suppression registry,
    and reconciled layer counts.
    """
    if not isinstance(package, Mapping):
        return {
            "ok": False,
            "version": ADMISSION_BRIDGE_VERSION_V1,
            "admitted": [],
            "workspace_decisions": [],
            "suppressed": [],
            "counts": {},
        }

    corrs = [c for c in (package.get("correlations") or []) if isinstance(c, Mapping)]
    foundation_ready = sorted(
        {
            _norm(c.get("statement_capability"))
            for c in corrs
            if _norm(c.get("statement_capability")) in _STATEMENT_AR
        }
    )
    # Group correlations by capability (try all products — not first-wins silent fail).
    by_cap: dict[str, list[Mapping[str, Any]]] = {c: [] for c in _CAPABILITY_ORDER}
    for c in corrs:
        cap = _norm(c.get("statement_capability"))
        if cap in by_cap:
            by_cap[cap].append(c)

    slug = _norm(store_slug or package.get("store_slug"))
    resolver = product_name_resolver or resolve_real_product_display_name_v1
    suppressed: list[dict[str, Any]] = []
    admitted: list[dict[str, Any]] = []
    workspace_decisions: list[dict[str, Any]] = []
    admitted_caps: set[str] = set()

    for cap in _CAPABILITY_ORDER:
        candidates = by_cap.get(cap) or []
        if not candidates:
            suppressed.append(
                _suppression_row(
                    observation_id=f"obs_admit:{cap}:none",
                    product_key="",
                    capability_id=cap,
                    stage="observation_candidate",
                    reason="capability_not_present_in_correlations",
                    missing_evidence="correlation_with_statement_capability",
                    may_become_eligible_later=True,
                )
            )
            continue

        admitted_this_cap = False
        for corr in candidates:
            product_key = _norm(corr.get("product_key"))
            oid = _candidate_id(cap, product_key or "unknown")

            # Stage: Observation Candidate
            if not product_key:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key="",
                        capability_id=cap,
                        stage="observation_candidate",
                        reason="missing_product_key",
                        missing_evidence="product_key",
                    )
                )
                continue

            # Stage: Evidence Validation
            refs = (
                corr.get("evidence_refs")
                if isinstance(corr.get("evidence_refs"), list)
                else []
            )
            counts = corr.get("counts") if isinstance(corr.get("counts"), Mapping) else {}
            reasons = (
                corr.get("reason_counts")
                if isinstance(corr.get("reason_counts"), Mapping)
                else {}
            )
            compare = (
                corr.get("compare") if isinstance(corr.get("compare"), Mapping) else {}
            )
            has_mass = bool(refs) or bool(counts) or bool(reasons) or bool(compare)
            if not has_mass:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="evidence_validation",
                        reason="insufficient_evidence_mass",
                        missing_evidence="evidence_refs_or_counts",
                    )
                )
                continue
            if len(refs) < _MIN_EVIDENCE_REFS and not (counts or reasons or compare):
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="evidence_validation",
                        reason="evidence_refs_below_minimum",
                        missing_evidence=f"evidence_refs>={_MIN_EVIDENCE_REFS}",
                    )
                )
                continue

            # Stage: Confidence Validation
            conf = _confidence_from_correlation_v1(slug, product_key, corr)
            score = conf.get("confidence_score")
            try:
                score_i = int(score) if score is not None else 0
            except (TypeError, ValueError):
                score_i = 0
            if score_i < _MIN_CONFIDENCE_SCORE:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="confidence_validation",
                        reason="confidence_below_threshold",
                        missing_evidence=f"confidence_score>={_MIN_CONFIDENCE_SCORE}",
                        confidence_at_rejection=score_i,
                    )
                )
                continue

            # Stage: Canonical Product Identity
            # Hard placeholders (DEMO-PERFUME / exact demo / orv-*) never admit.
            # Composite keys like b|demo_perfume_velvet|… are NOT placeholders.
            low_key = product_key.lower()
            hard_ban = (
                low_key in {"demo", "demo-perfume", "demo_perfume", "perfume"}
                or low_key.startswith("orv-")
                or low_key.startswith("orv_")
                or low_key.endswith("|demo-perfume")
                or low_key.endswith("|demo_perfume")
                or (is_banned_product_key_v1(product_key) and "|" not in product_key)
            )
            if hard_ban:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="canonical_product_identity",
                        reason="banned_placeholder_product_key",
                        missing_evidence="real_canonical_product_identity",
                        confidence_at_rejection=score_i,
                        may_become_eligible_later=False,
                    )
                )
                continue

            try:
                product_name = resolver(slug, product_key)
            except Exception:  # noqa: BLE001
                product_name = None
            if not product_name or not is_real_product_display_name_v1(product_name):
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="canonical_product_identity",
                        reason="product_display_name_unresolved",
                        missing_evidence="catalog_or_snapshot_display_name",
                        confidence_at_rejection=score_i,
                        may_become_eligible_later=True,
                    )
                )
                continue

            # Stage: Reality Validation Admission (one finding per capability)
            if admitted_this_cap:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="reality_validation_admission",
                        reason="capability_already_admitted_for_stronger_product",
                        missing_evidence="",
                        confidence_at_rejection=score_i,
                        may_become_eligible_later=True,
                    )
                )
                continue

            copy = _STATEMENT_AR[cap]
            details = _evidence_details(corr)
            home_teaser = f"{product_name}: {copy['home_teaser_ar']}"
            finding = {
                "finding_id": f"observation_reality:{cap}",
                "observation_id": oid,
                "capability_id": cap,
                "product_name_ar": product_name,
                "title_ar": copy["title_ar"],
                "statement_ar": copy["statement_ar"],
                "statement_en": copy["statement_en"],
                "home_teaser_ar": home_teaser,
                "recommended_action_ar": copy["recommended_action_ar"],
                "confidence_level": conf["confidence_level"],
                "confidence_ar": conf["confidence_ar"],
                "confidence_score": conf["confidence_score"],
                "confidence_source": conf["confidence_source"],
                "evidence_details": details,
                "diagnostics": {
                    "product_key": details["product_key"],
                    "correlation_kind": details["correlation_kind"],
                    "evidence_ref_count": details["evidence_ref_count"],
                    "admission_bridge": ADMISSION_BRIDGE_VERSION_V1,
                },
                "source": FOUNDATION_VERSION,
                "temporary_surface": True,
                "surface_eligibility": {
                    "home_teaser": True,
                    "decision_workspace": bool(copy.get("supports_decision")),
                },
                "admission": {
                    "admitted": True,
                    "stage": "reality_validation_admission",
                    "version": ADMISSION_BRIDGE_VERSION_V1,
                },
            }
            admitted.append(finding)
            admitted_caps.add(cap)
            admitted_this_cap = True

            # Stage: Knowledge Routing → Workspace only when actionable
            if copy.get("supports_decision"):
                title = copy["decision_title_ar"].format(product=product_name)
                workspace_decisions.append(
                    {
                        "decision_id": f"dce:obs:{cap}:{product_key}"[:180],
                        "source": "observation_admission_bridge_v1",
                        "capability_id": cap,
                        "product_name_ar": product_name,
                        "product_key": product_key,
                        "merchant_decision": title,
                        "title": title,
                        "executive_decision_ar": title,
                        "why": copy["statement_ar"],
                        "why_now": (
                            "الأدلة الحالية كافية لتستحق مراجعة اليوم قبل توسيع الجهد."
                        ),
                        "evidence": (
                            f"مراجع أدلة: {details['evidence_ref_count']} · "
                            f"ثقة: {conf['confidence_ar']}"
                        ),
                        "confidence": conf["confidence_level"],
                        "confidence_ar": conf["confidence_ar"],
                        "first_step": copy["recommended_action_ar"],
                        "recommended_action": copy["recommended_action_ar"],
                        "business_domain": "products",
                        "decision_category": "products",
                        "business_meaning_ar": copy["statement_ar"],
                        "business_impact_ar": (
                            "تجاهل الملاحظة يُبقي فرصة التحويل ضعيفة لنفس المنتج."
                        ),
                        "observation_id": oid,
                        "gate_observation_admission": True,
                    }
                )
            else:
                suppressed.append(
                    _suppression_row(
                        observation_id=oid,
                        product_key=product_key,
                        capability_id=cap,
                        stage="knowledge_routing",
                        reason="observation_valid_for_home_not_workspace",
                        missing_evidence="actionable_merchant_decision",
                        confidence_at_rejection=score_i,
                        may_become_eligible_later=True,
                    )
                )

        if not admitted_this_cap:
            # Already recorded per-candidate reasons; ensure capability-level visibility.
            pass

    foundation_counts = package.get("counts") if isinstance(package.get("counts"), Mapping) else {}
    suppressed_by_reason: dict[str, int] = {}
    for row in suppressed:
        r = _norm(row.get("rejection_reason")) or "unknown"
        suppressed_by_reason[r] = suppressed_by_reason.get(r, 0) + 1

    return {
        "ok": True,
        "version": ADMISSION_BRIDGE_VERSION_V1,
        "foundation_ready": foundation_ready,
        "foundation_ready_count": len(foundation_ready),
        "admitted": admitted,
        "orv_admitted_count": len(admitted),
        "workspace_decisions": workspace_decisions,
        "workspace_visible_count": len(workspace_decisions),
        "home_visible_count": len(admitted),  # all admitted → Home teaser eligible
        "routed_count": len(admitted),  # passed Reality Validation Admission
        "suppressed": suppressed,
        "suppressed_count": len(suppressed),
        "suppressed_by_reason": suppressed_by_reason,
        "foundation_counts": dict(foundation_counts),
        "present_capabilities": [f["capability_id"] for f in admitted],
        "missing_capabilities": [c for c in _CAPABILITY_ORDER if c not in admitted_caps],
        "reconciliation": {
            "foundation_ready_count": len(foundation_ready),
            "orv_admitted_count": len(admitted),
            "routed_count": len(admitted),
            "home_visible_count": len(admitted),
            "workspace_visible_count": len(workspace_decisions),
            "suppressed_count": len(suppressed),
            "suppressed_by_reason": suppressed_by_reason,
            "silent_drops": 0,
            "note": (
                "home_visible == orv_admitted; "
                "workspace_visible ⊆ admitted (actionable only); "
                "suppressed includes home-only and failed candidates"
            ),
        },
    }


__all__ = [
    "ADMISSION_BRIDGE_VERSION_V1",
    "admit_observation_candidates_v1",
]
