# -*- coding: utf-8 -*-
"""
Observation Reality Validation V1 — merchant-readable findings from correlations.

Only emits statements when a correlation carries statement_capability + evidence.
Temporary presentation contract — not Product Intelligence V1.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.observation_foundation_v1.assemble_v1 import assemble_observation_foundation_v1
from services.observation_foundation_v1.catalog_v1 import FOUNDATION_VERSION
from services.observation_foundation_v1.flag_v1 import observation_foundation_v1_enabled

ENV_OBSERVATION_REALITY_VALIDATION_V1 = "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1"

_STATEMENT_AR: dict[str, dict[str, str]] = {
    "high_interest_low_conversion": {
        "title_ar": "اهتمام مرتفع وتحويل منخفض",
        "statement_ar": "هذا المنتج يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال منخفضاً.",
        "statement_en": "The product has high interest but low conversion.",
    },
    "shipping_stronger_than_price": {
        "title_ar": "أدلة الشحن أقوى من السعر",
        "statement_ar": "أدلة التردد بسبب الشحن/التوصيل أقوى حالياً من أدلة السعر.",
        "statement_en": "Shipping evidence is stronger than price evidence.",
    },
    "repeated_return_without_purchase": {
        "title_ar": "عودة متكررة بلا شراء",
        "statement_ar": "عملاء عادوا مراراً إلى المتجر دون إتمام شراء مرتبط بهذا المنتج.",
        "statement_en": "Customers repeatedly return without purchasing.",
    },
    "no_quality_issue_evidence": {
        "title_ar": "لا دليل على مشكلة جودة",
        "statement_ar": "لا توجد أدلة حالية تدعم وجود مشكلة جودة في المنتج.",
        "statement_en": "No evidence currently supports a quality issue.",
    },
}

_CAPABILITY_ORDER = (
    "high_interest_low_conversion",
    "shipping_stronger_than_price",
    "repeated_return_without_purchase",
    "no_quality_issue_evidence",
)


def observation_reality_validation_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    import os

    env = environ if environ is not None else os.environ
    # Default ON for Reality Validation package; requires Observation Foundation.
    if not observation_foundation_v1_enabled(environ=env):
        return False
    raw = str(env.get(ENV_OBSERVATION_REALITY_VALIDATION_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _evidence_line(corr: Mapping[str, Any]) -> str:
    parts: list[str] = []
    counts = corr.get("counts") if isinstance(corr.get("counts"), Mapping) else {}
    if counts:
        for k in ("cart_add", "return", "purchase"):
            if k in counts:
                parts.append(f"{k}={counts[k]}")
    compare = corr.get("compare") if isinstance(corr.get("compare"), Mapping) else {}
    if compare:
        parts.append(
            f"shipping={compare.get('shipping', 0)} price={compare.get('price', 0)}"
        )
    reasons = corr.get("reason_counts") if isinstance(corr.get("reason_counts"), Mapping) else {}
    if reasons and not compare:
        top = sorted(reasons.items(), key=lambda x: (-int(x[1]), str(x[0])))[:3]
        parts.append("reasons=" + ",".join(f"{a}:{b}" for a, b in top))
    if corr.get("absent_family"):
        parts.append(f"absent={corr.get('absent_family')}")
    refs = corr.get("evidence_refs") or []
    if isinstance(refs, list) and refs:
        parts.append(f"evidence_refs={len(refs)}")
    pk = str(corr.get("product_key") or "").strip()
    if pk:
        parts.append(f"product={pk[:48]}")
    return "; ".join(parts) if parts else "correlation_evidence_present"


def project_merchant_observation_findings_v1(
    package: Mapping[str, Any] | None,
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
        # Keep first (strongest product row) per capability
        if cap not in by_cap:
            by_cap[cap] = c

    findings: list[dict[str, Any]] = []
    for cap in _CAPABILITY_ORDER:
        corr = by_cap.get(cap)
        if not corr:
            continue
        copy = _STATEMENT_AR[cap]
        findings.append(
            {
                "finding_id": f"observation_reality:{cap}",
                "capability_id": cap,
                "title_ar": copy["title_ar"],
                "statement_ar": copy["statement_ar"],
                "statement_en": copy["statement_en"],
                "evidence_summary": _evidence_line(corr),
                "product_key": str(corr.get("product_key") or ""),
                "correlation_kind": str(corr.get("correlation_kind") or ""),
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
    findings = project_merchant_observation_findings_v1(pkg)
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
        "eyebrow_ar": "معرفة من الملاحظة (تجريبي)",
        "title_ar": "ماذا نلاحظ في منتجاتك الآن؟",
        "lede_ar": "استنتاجات مبنية على ارتباطات مثبتة فقط — بلا تخمين.",
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
