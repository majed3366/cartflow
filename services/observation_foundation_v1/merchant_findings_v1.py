# -*- coding: utf-8 -*-
"""
Observation Reality Validation V1 — merchant-readable findings from correlations.

Merchant surface: statement + recommended action + confidence (from Evidence Confidence).
Technical counters live only under evidence_details / diagnostics — never on Home.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.observation_foundation_v1.assemble_v1 import assemble_observation_foundation_v1
from services.observation_foundation_v1.catalog_v1 import FOUNDATION_VERSION
from services.observation_foundation_v1.flag_v1 import observation_foundation_v1_enabled
from services.product_data.evidence_confidence_types_v1 import (
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    LEVEL_VERY_HIGH,
    confidence_level_for_score,
)

ENV_OBSERVATION_REALITY_VALIDATION_V1 = "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1"

_STATEMENT_AR: dict[str, dict[str, str]] = {
    "high_interest_low_conversion": {
        "title_ar": "اهتمام مرتفع وتحويل منخفض",
        "statement_ar": "هذا المنتج يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً.",
        "statement_en": "The product has high interest but low conversion.",
        "recommended_action_ar": "راجع صفحة المنتج وعرض الشحن قبل أي توسعة.",
    },
    "shipping_stronger_than_price": {
        "title_ar": "أدلة الشحن أقوى من السعر",
        "statement_ar": "أدلة التردد بسبب الشحن/التوصيل أقوى حالياً من أدلة السعر.",
        "statement_en": "Shipping evidence is stronger than price evidence.",
        "recommended_action_ar": "اختبر شحنًا مجانيًا أو خفّض تكلفة الشحن.",
    },
    "repeated_return_without_purchase": {
        "title_ar": "عودة متكررة بلا شراء",
        "statement_ar": "عملاء عادوا مراراً إلى المتجر دون إتمام شراء مرتبط بهذا المنتج.",
        "statement_en": "Customers repeatedly return without purchasing.",
        "recommended_action_ar": "راقب رحلة العميل بعد العودة واختبر تحسين صفحة المنتج.",
    },
    "no_quality_issue_evidence": {
        "title_ar": "لا دليل على مشكلة جودة",
        "statement_ar": "لا توجد أدلة حالية تدعم وجود مشكلة جودة في المنتج.",
        "statement_en": "No evidence currently supports a quality issue.",
        "recommended_action_ar": "لا حاجة لاتخاذ إجراء حالياً — استمر في جمع الأدلة.",
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


def observation_reality_validation_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    import os

    env = environ if environ is not None else os.environ
    if not observation_foundation_v1_enabled(environ=env):
        return False
    raw = str(env.get(ENV_OBSERVATION_REALITY_VALIDATION_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _evidence_details(corr: Mapping[str, Any]) -> dict[str, Any]:
    """Technical payload for Evidence Details / Developer View only — not Home."""
    counts = corr.get("counts") if isinstance(corr.get("counts"), Mapping) else {}
    compare = corr.get("compare") if isinstance(corr.get("compare"), Mapping) else {}
    reasons = (
        corr.get("reason_counts") if isinstance(corr.get("reason_counts"), Mapping) else {}
    )
    refs = corr.get("evidence_refs") if isinstance(corr.get("evidence_refs"), list) else []
    return {
        "correlation_kind": str(corr.get("correlation_kind") or ""),
        "product_key": str(corr.get("product_key") or ""),
        "counts": dict(counts),
        "compare": dict(compare),
        "reason_counts": dict(reasons),
        "absent_family": corr.get("absent_family"),
        "evidence_ref_count": len(refs),
        "evidence_refs": refs[:20],
    }


def _confidence_from_evidence_engine_v1(
    store_slug: str,
    product_key: str,
    corr: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Resolve confidence via Evidence Confidence Foundation.

    Prefer product-scoped evaluation; else store-level evaluation;
    else score from evidence-ref mass using engine thresholds.
    """
    level = ""
    score: Optional[int] = None
    source = "evidence_confidence_foundation_v1"
    try:
        from services.product_data.evidence_confidence_foundation_v1 import (  # noqa: PLC0415
            evaluate_evidence_confidence_v1,
        )

        report = evaluate_evidence_confidence_v1(store_slug, assembly_window="d7")
        evaluations = list(report.get("evaluations") or [])
        pk = str(product_key or "").strip()
        matched = None
        if pk:
            for ev in evaluations:
                if not isinstance(ev, Mapping):
                    continue
                if str(ev.get("subject_id") or "").strip() == pk:
                    matched = ev
                    break
        if matched is None and evaluations:
            # Store-level / first evaluation from engine
            matched = next((e for e in evaluations if isinstance(e, Mapping)), None)
        if isinstance(matched, Mapping) and matched.get("confidence_level"):
            level = str(matched.get("confidence_level") or "").strip().lower()
            try:
                score = int(matched.get("confidence_score"))
            except (TypeError, ValueError):
                score = None
            source = "evidence_confidence_evaluation"
    except Exception:  # noqa: BLE001
        level = ""

    if level not in _CONFIDENCE_AR:
        # Engine threshold function — not a merchant hardcode
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
        sample += sum(int(v or 0) for v in reasons.values()) if reasons else 0
        # Map mass → 0..100 then engine bands
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


def project_merchant_observation_findings_v1(
    package: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
) -> list[dict[str, Any]]:
    """Project evidence-backed statement capabilities into merchant findings."""
    if not isinstance(package, Mapping):
        return []
    corrs = package.get("correlations") or []
    by_cap: dict[str, Mapping[str, Any]] = {}
    for c in corrs:
        if not isinstance(c, Mapping):
            continue
        cap = str(c.get("statement_capability") or "").strip()
        if not cap or cap not in _STATEMENT_AR:
            continue
        if cap not in by_cap:
            by_cap[cap] = c

    slug = str(store_slug or package.get("store_slug") or "").strip()
    findings: list[dict[str, Any]] = []
    for cap in _CAPABILITY_ORDER:
        corr = by_cap.get(cap)
        if not corr:
            continue
        copy = _STATEMENT_AR[cap]
        conf = _confidence_from_evidence_engine_v1(
            slug, str(corr.get("product_key") or ""), corr
        )
        details = _evidence_details(corr)
        findings.append(
            {
                "finding_id": f"observation_reality:{cap}",
                "capability_id": cap,
                "title_ar": copy["title_ar"],
                "statement_ar": copy["statement_ar"],
                "statement_en": copy["statement_en"],
                "recommended_action_ar": copy["recommended_action_ar"],
                "confidence_level": conf["confidence_level"],
                "confidence_ar": conf["confidence_ar"],
                "confidence_score": conf["confidence_score"],
                "confidence_source": conf["confidence_source"],
                # Merchant Home must not render these:
                "evidence_details": details,
                "diagnostics": {
                    "product_key": details["product_key"],
                    "correlation_kind": details["correlation_kind"],
                    "evidence_ref_count": details["evidence_ref_count"],
                },
                "source": FOUNDATION_VERSION,
                "temporary_surface": True,
            }
        )
    return findings


def build_observation_reality_validation_v1(
    store_slug: str,
    *,
    signals: Optional[list[Mapping[str, Any]]] = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not observation_reality_validation_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": "observation_reality_validation_v1",
            "findings": [],
            "ui": True,
            "temporary": True,
        }

    pkg = assemble_observation_foundation_v1(
        store_slug, signals=signals, environ=environ
    )
    findings = project_merchant_observation_findings_v1(pkg, store_slug=store_slug)
    required = list(_CAPABILITY_ORDER)
    present = [f["capability_id"] for f in findings]
    return {
        "ok": True,
        "enabled": True,
        "schema": "observation_reality_validation_v1",
        "store_slug": store_slug,
        "temporary": True,
        "ui": True,
        "product_intelligence": False,
        "findings": findings,
        "required_capabilities": required,
        "present_capabilities": present,
        "missing_capabilities": [c for c in required if c not in present],
        "acceptance_all_four": len(present) == 4,
        "foundation_counts": pkg.get("counts") or {},
        "eyebrow_ar": "معرفة من الملاحظة",
        "title_ar": "ماذا نلاحظ في منتجاتك الآن؟",
        "lede_ar": "ملاحظات قصيرة مبنية على أدلة — مع خطوة مقترحة وثقة واضحة.",
    }


def _resolve_observation_store_slug_v1(store_slug: str) -> str:
    """Prefer primary slug; fall back to lab-owned demo when it has observation mass."""
    slug = str(store_slug or "").strip()
    if not slug or slug == "demo":
        return slug or "demo"
    primary = build_observation_reality_validation_v1(slug)
    if primary.get("findings"):
        return slug
    try:
        from extensions import db
        from models import Store

        demo = db.session.query(Store).filter_by(zid_store_id="demo").first()
        primary_row = db.session.query(Store).filter_by(zid_store_id=slug).first()
        if demo is None or primary_row is None:
            return slug
        demo_owner = getattr(demo, "merchant_user_id", None)
        primary_owner = getattr(primary_row, "merchant_user_id", None)
        if not demo_owner or not primary_owner:
            return slug
        if int(demo_owner) != int(primary_owner):
            return slug
        demo_pkg = build_observation_reality_validation_v1("demo")
        if demo_pkg.get("findings"):
            return "demo"
    except Exception:  # noqa: BLE001
        return slug
    return slug


def attach_observation_reality_validation_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    try:
        slug = _resolve_observation_store_slug_v1(str(store_slug or "").strip())
        pkg = build_observation_reality_validation_v1(slug, environ=environ)
        if slug != str(store_slug or "").strip():
            pkg = dict(pkg)
            pkg["store_slug_resolved"] = slug
            pkg["store_slug_requested"] = store_slug
        summary["observation_reality_validation_v1"] = pkg
    except Exception:  # noqa: BLE001
        summary["observation_reality_validation_v1"] = {
            "ok": False,
            "enabled": True,
            "findings": [],
            "error": "attach_failed",
        }
    return summary


__all__ = [
    "ENV_OBSERVATION_REALITY_VALIDATION_V1",
    "attach_observation_reality_validation_to_summary_v1",
    "build_observation_reality_validation_v1",
    "observation_reality_validation_v1_enabled",
    "project_merchant_observation_findings_v1",
]
