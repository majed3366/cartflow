# -*- coding: utf-8 -*-
"""
Business Facts Extraction Engine V1.

Transforms validated observations / correlations / operational truth into
merchant-readable business facts. Never invents facts from bare counters.
Never emits recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.business_facts_v1.contract_v1 import (
    BUSINESS_FACTS_VERSION_V1,
    FACT_SCHEMA_V1,
    FACT_TYPE_COMMUNICATION,
    FACT_TYPE_CONVERSION,
    FACT_TYPE_CUSTOMER_BEHAVIOUR,
    FACT_TYPE_PRODUCT_DEMAND,
    FACT_TYPE_RECOVERY,
    FACT_TYPE_STORE_HEALTH,
    IMPACT_COMMUNICATION,
    IMPACT_CONVERSION,
    IMPACT_DEMAND,
    IMPACT_OPERATIONS,
    IMPACT_STORE,
    empty_fact_shell_v1,
    validate_business_fact_v1,
)
from services.business_facts_v1.flag_v1 import business_facts_v1_enabled

# Capability → (fact_type, impact, meaning_ar template, meaning_en, home, workspace)
# Templates use {product}. Evidence-backed only via admitted ORV findings.
_CAPABILITY_FACT_MAP_V1: dict[str, dict[str, Any]] = {
    "high_interest_low_conversion": {
        "fact_type": FACT_TYPE_CONVERSION,
        "impact_category": IMPACT_CONVERSION,
        "meaning_ar": "{product} يحظى باهتمام واضح، لكن التحويل إلى شراء لا يزال ضعيفاً.",
        "meaning_en": "{product} attracts attention but converts poorly.",
        "home": True,
        "workspace": True,
    },
    "shipping_stronger_than_price": {
        "fact_type": FACT_TYPE_CUSTOMER_BEHAVIOUR,
        "impact_category": IMPACT_CONVERSION,
        "meaning_ar": "يبدو أن الشحن يضعف إتمام الشراء لـ {product}.",
        "meaning_en": "Shipping appears to reduce conversion for {product}.",
        "home": True,
        "workspace": True,
    },
    "repeated_return_without_purchase": {
        "fact_type": FACT_TYPE_CUSTOMER_BEHAVIOUR,
        "impact_category": IMPACT_DEMAND,
        "meaning_ar": "العملاء يعودون مراراً إلى {product} قبل إتمام الشراء.",
        "meaning_en": "Customers repeatedly return to {product} before purchasing.",
        "home": True,
        "workspace": True,
    },
    "no_quality_issue_evidence": {
        "fact_type": FACT_TYPE_PRODUCT_DEMAND,
        "impact_category": IMPACT_DEMAND,
        "meaning_ar": "لا توجد أدلة حالية على مشكلة جودة في {product}.",
        "meaning_en": "No quality-issue evidence currently for {product}.",
        "home": True,
        "workspace": False,
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _fact_id(fact_type: str, subject_id: str, capability: str = "") -> str:
    base = f"bf:{fact_type}:{subject_id or 'store'}"
    if capability:
        return f"{base}:{capability}"
    return base


def _from_orv_finding_v1(finding: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    cap = _norm(finding.get("capability_id") or finding.get("capability"))
    spec = _CAPABILITY_FACT_MAP_V1.get(cap)
    if not spec:
        return None
    product = _norm(finding.get("product_name_ar") or finding.get("product_name"))
    if not product:
        return None
    product_key = ""
    details = finding.get("evidence_details")
    if isinstance(details, Mapping):
        product_key = _norm(details.get("product_key"))
    if not product_key:
        diag = finding.get("diagnostics")
        if isinstance(diag, Mapping):
            product_key = _norm(diag.get("product_key"))

    meaning_ar = str(spec["meaning_ar"]).format(product=product)
    meaning_en = str(spec["meaning_en"]).format(product=product)
    corr_kind = ""
    refs: list[Any] = []
    if isinstance(details, Mapping):
        corr_kind = _norm(details.get("correlation_kind"))
        raw_refs = details.get("evidence_refs")
        if isinstance(raw_refs, list):
            refs = [r for r in raw_refs[:12] if isinstance(r, Mapping)]

    fact = empty_fact_shell_v1()
    fact.update(
        {
            "fact_id": _fact_id(spec["fact_type"], product_key or product, cap),
            "fact_type": spec["fact_type"],
            "subject": {
                "kind": "product",
                "id": product_key or product,
                "name_ar": product,
            },
            "business_meaning_ar": meaning_ar,
            "business_meaning_en": meaning_en,
            "evidence": {
                "source_kinds": ["observation", "correlation", "validated_finding"],
                "observation_ids": [_norm(finding.get("observation_id"))]
                if _norm(finding.get("observation_id"))
                else [],
                "correlation_kinds": [corr_kind] if corr_kind else [],
                "capability_ids": [cap],
                "refs": refs,
            },
            "confidence": {
                "level": _norm(finding.get("confidence_level")) or "medium",
                "ar": _norm(finding.get("confidence_ar")) or "متوسط",
                "score": finding.get("confidence_score"),
                "source": _norm(finding.get("confidence_source"))
                or "observation_admission",
            },
            "freshness": {"status": "current", "as_of_utc": _utc_now_iso()},
            "impact_category": spec["impact_category"],
            "recommendation": None,
            "surfaces": {
                "home": bool(spec["home"]),
                "decision_workspace": bool(spec["workspace"]),
            },
            "source_finding_id": _norm(finding.get("finding_id")),
        }
    )
    errors = validate_business_fact_v1(fact)
    if errors:
        return None
    return fact


def _ot_domain_facts_v1(
    *,
    domains_pkg: Mapping[str, Any] | None,
    store_executive_pkg: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Store-level facts from domain attention + executive understanding language.

    Uses business-domain flags (has_attention) and Gate 2F/2X teasers — never
    formats raw waiting_total / no_phone_total into fact text.
    """
    out: list[dict[str, Any]] = []
    domains: Mapping[str, Any] = {}
    if isinstance(domains_pkg, Mapping):
        raw = domains_pkg.get("domains")
        if isinstance(raw, Mapping):
            domains = raw
        elif isinstance(domains_pkg.get("recovery"), Mapping):
            domains = domains_pkg

    teasers: Mapping[str, Any] = {}
    briefing: Mapping[str, Any] = {}
    if isinstance(store_executive_pkg, Mapping):
        t = store_executive_pkg.get("home_teasers")
        if isinstance(t, Mapping):
            teasers = t
        b = store_executive_pkg.get("briefing")
        if isinstance(b, Mapping):
            briefing = b

    def _add(
        *,
        fact_type: str,
        impact: str,
        meaning_ar: str,
        meaning_en: str,
        source: str,
        home: bool = True,
        workspace: bool = False,
    ) -> None:
        meaning_ar = _norm(meaning_ar)
        if not meaning_ar:
            return
        fact = empty_fact_shell_v1()
        fact.update(
            {
                "fact_id": _fact_id(fact_type, "store", source),
                "fact_type": fact_type,
                "subject": {"kind": "store", "id": "store", "name_ar": "المتجر"},
                "business_meaning_ar": meaning_ar,
                "business_meaning_en": meaning_en,
                "evidence": {
                    "source_kinds": ["operational_truth", "business_domain"],
                    "observation_ids": [],
                    "correlation_kinds": [],
                    "capability_ids": [],
                    "refs": [{"source": source}],
                },
                "confidence": {
                    "level": "medium",
                    "ar": "متوسط",
                    "score": 55,
                    "source": "operational_truth_domain",
                },
                "freshness": {"status": "current", "as_of_utc": _utc_now_iso()},
                "impact_category": impact,
                "recommendation": None,
                "surfaces": {"home": home, "decision_workspace": workspace},
            }
        )
        if not validate_business_fact_v1(fact):
            out.append(fact)

    recovery = domains.get("recovery") if isinstance(domains.get("recovery"), Mapping) else {}
    operations = (
        domains.get("operations") if isinstance(domains.get("operations"), Mapping) else {}
    )
    communication = (
        domains.get("communication")
        if isinstance(domains.get("communication"), Mapping)
        else {}
    )

    health_ar = _norm(teasers.get("store_health_ar") or briefing.get("revenue_signal_ar"))
    if recovery.get("has_attention"):
        _add(
            fact_type=FACT_TYPE_RECOVERY,
            impact=IMPACT_OPERATIONS,
            meaning_ar=_norm(briefing.get("recovery_healthy_ar"))
            or "فرص استعادة المبيعات محدودة حالياً.",
            meaning_en="Recovery opportunities are currently limited.",
            source="recovery_attention",
            workspace=True,
        )
    if operations.get("has_attention") or (
        health_ar and "أبطأ" in health_ar
    ):
        _add(
            fact_type=FACT_TYPE_STORE_HEALTH,
            impact=IMPACT_STORE,
            meaning_ar="نشاط إتمام الشراء أبطأ من المعتاد اليوم.",
            meaning_en="Purchase activity slowed today.",
            source="operations_attention",
        )
    if not recovery.get("has_attention") and not operations.get("has_attention"):
        _add(
            fact_type=FACT_TYPE_STORE_HEALTH,
            impact=IMPACT_STORE,
            meaning_ar=_norm(health_ar) or "لا توجد مشكلات تجارية حرجة ظاهرة.",
            meaning_en="No critical business issues detected.",
            source="store_stable",
        )

    comm_ar = _norm(
        teasers.get("communication_ar") or briefing.get("communication_healthy_ar")
    )
    if communication.get("has_attention") or (
        comm_ar and ("انتباهاً" in comm_ar or "مقيدة" in comm_ar)
    ):
        _add(
            fact_type=FACT_TYPE_COMMUNICATION,
            impact=IMPACT_COMMUNICATION,
            meaning_ar="نقص معلومات التواصل يحدّ من متابعة العملاء.",
            meaning_en="Missing contact information limits recovery.",
            source="communication_attention",
            workspace=True,
        )
    else:
        _add(
            fact_type=FACT_TYPE_COMMUNICATION,
            impact=IMPACT_COMMUNICATION,
            meaning_ar=comm_ar or "تواصل العملاء يسير بشكل طبيعي.",
            meaning_en="Customer communication is healthy.",
            source="communication_healthy",
        )
    return out


def extract_business_facts_v1(
    *,
    store_slug: str,
    orv_package: Mapping[str, Any] | None = None,
    domains_pkg: Mapping[str, Any] | None = None,
    store_executive_pkg: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Extract Business Facts from validated ORV findings + OT domain understanding.

    Does not read bare counters into merchant text.
    """
    slug = _norm(store_slug)
    if not business_facts_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": BUSINESS_FACTS_VERSION_V1,
            "store_slug": slug,
            "facts": [],
            "counts": {"total": 0},
        }

    facts: list[dict[str, Any]] = []
    seen: set[str] = set()

    orv = orv_package if isinstance(orv_package, Mapping) else {}
    for finding in list(orv.get("findings") or []):
        if not isinstance(finding, Mapping):
            continue
        fact = _from_orv_finding_v1(finding)
        if fact is None:
            continue
        fid = str(fact["fact_id"])
        if fid in seen:
            continue
        seen.add(fid)
        facts.append(fact)

    for fact in _ot_domain_facts_v1(
        domains_pkg=domains_pkg, store_executive_pkg=store_executive_pkg
    ):
        fid = str(fact["fact_id"])
        if fid in seen:
            continue
        seen.add(fid)
        facts.append(fact)

    by_type: dict[str, int] = {}
    for f in facts:
        ft = str(f.get("fact_type") or "")
        by_type[ft] = by_type.get(ft, 0) + 1

    return {
        "ok": True,
        "enabled": True,
        "schema": BUSINESS_FACTS_VERSION_V1,
        "version": BUSINESS_FACTS_VERSION_V1,
        "store_slug": slug,
        "fact_schema": FACT_SCHEMA_V1,
        "facts": facts,
        "counts": {
            "total": len(facts),
            "by_type": by_type,
            "from_observations": sum(
                1
                for f in facts
                if "observation" in (f.get("evidence") or {}).get("source_kinds") or []
            ),
            "from_operational_truth": sum(
                1
                for f in facts
                if "operational_truth"
                in (f.get("evidence") or {}).get("source_kinds") or []
            ),
        },
        "recommendation": None,
        "product_intelligence": False,
        "extracted_at_utc": _utc_now_iso(),
    }


__all__ = ["extract_business_facts_v1"]
