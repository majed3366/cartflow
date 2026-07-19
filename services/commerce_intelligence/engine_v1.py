# -*- coding: utf-8 -*-
"""
Commerce Intelligence Foundation engine V1.

Builds a store package of canonical intelligence records from Business Findings
(and optional Reasoning guidance metadata). Home must consume this package —
Home must never calculate intelligence.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence

from services.business_findings_contract_v1 import norm, utc_now_iso
from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.commerce_intelligence.contract_v1 import (
    FOUNDATION_VERSION,
    record_is_complete_v1,
)
from services.commerce_intelligence.domains_v1 import (
    DOMAIN_CUSTOMER,
    DOMAIN_GUIDANCE,
    DOMAIN_PRODUCT,
    DOMAIN_STORE,
    DOMAIN_QUESTIONS_EN,
    all_domains_v1,
)
from services.commerce_intelligence.project_from_finding_v1 import (
    project_finding_to_intelligence_record_v1,
    project_guidance_from_finding_v1,
)

log = logging.getLogger("cartflow")


def _index_by_domain_v1(records: Sequence[Mapping[str, Any]]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {d: [] for d in all_domains_v1()}
    for rec in records:
        if not isinstance(rec, Mapping):
            continue
        domain = norm(rec.get("domain"))
        if domain not in idx:
            idx[domain] = []
        idx[domain].append(dict(rec))
    return idx


def build_commerce_intelligence_package_v1(
    *,
    store_slug: str,
    findings_package: Optional[Mapping[str, Any]] = None,
    include_guidance_projections: bool = True,
) -> dict[str, Any]:
    """
    Project an existing findings package into Commerce Intelligence records.

    Does not redesign Home. Does not mutate findings_package.
    """
    slug = norm(store_slug)
    pkg = findings_package if isinstance(findings_package, Mapping) else {}
    findings = list(pkg.get("findings") or [])
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        rec = project_finding_to_intelligence_record_v1(finding)
        if not rec or not record_is_complete_v1(rec):
            continue
        rid = norm(rec.get("record_id"))
        if rid in seen:
            continue
        seen.add(rid)
        records.append(rec)

        if include_guidance_projections:
            g = project_guidance_from_finding_v1(finding)
            if g and record_is_complete_v1(g):
                gid = norm(g.get("record_id"))
                if gid and gid not in seen:
                    seen.add(gid)
                    records.append(g)

    by_domain = _index_by_domain_v1(records)
    return {
        "ok": True,
        "foundation_version": FOUNDATION_VERSION,
        "store_slug": slug,
        "generated_at": utc_now_iso(),
        "ai_used": False,
        "domains": list(all_domains_v1()),
        "domain_questions_en": {
            DOMAIN_PRODUCT: list(DOMAIN_QUESTIONS_EN[DOMAIN_PRODUCT]),
            DOMAIN_CUSTOMER: list(DOMAIN_QUESTIONS_EN[DOMAIN_CUSTOMER]),
            DOMAIN_STORE: list(DOMAIN_QUESTIONS_EN[DOMAIN_STORE]),
            DOMAIN_GUIDANCE: list(DOMAIN_QUESTIONS_EN[DOMAIN_GUIDANCE]),
        },
        "records": records,
        "by_domain": by_domain,
        "counts": {
            "records": len(records),
            DOMAIN_PRODUCT: len(by_domain.get(DOMAIN_PRODUCT) or []),
            DOMAIN_CUSTOMER: len(by_domain.get(DOMAIN_CUSTOMER) or []),
            DOMAIN_STORE: len(by_domain.get(DOMAIN_STORE) or []),
            DOMAIN_GUIDANCE: len(by_domain.get(DOMAIN_GUIDANCE) or []),
        },
        "source": {
            "findings_engine": norm((pkg.get("engine_version"))),
            "findings_count": len(findings),
            "evidence_loaded_from": norm(
                ((pkg.get("evidence") or {}) if isinstance(pkg.get("evidence"), Mapping) else {}).get(
                    "loaded_from"
                )
            ),
        },
        "home_consumption_contract": {
            "rule": "Home consumes canonical records only — never calculates intelligence",
            "required_fields": [
                "question",
                "finding",
                "evidence",
                "confidence",
                "recommendation",
                "status",
                "source_domains",
            ],
            "surfaces": ("merchant_home",),
            "executive_bands_may_map_later": (
                "E1",
                "E2",
                "E3",
                "E4",
                "E5",
                "E6",
            ),
        },
        "observability": {
            "complete_records": sum(1 for r in records if record_is_complete_v1(r)),
            "incomplete_dropped": 0,
        },
    }


def run_commerce_intelligence_foundation_v1(
    *,
    store_slug: str,
    load_db: bool = True,
    dash_store: Any = None,
    demo_fixture: bool = False,
    window_days: int = 14,
    findings_package: Optional[Mapping[str, Any]] = None,
    include_guidance_projections: bool = True,
) -> dict[str, Any]:
    """
    End-to-end foundation run: Findings Engine → Intelligence package.

    Home is not invoked.
    """
    slug = norm(store_slug)
    if findings_package is None:
        findings_package = run_business_findings_engine_v1(
            store_slug=slug,
            load_db=bool(load_db),
            dash_store=dash_store,
            demo_fixture=bool(demo_fixture),
            window_days=int(window_days or 14),
        )
    try:
        return build_commerce_intelligence_package_v1(
            store_slug=slug,
            findings_package=findings_package,
            include_guidance_projections=include_guidance_projections,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("commerce intelligence foundation failed: %s", exc)
        return {
            "ok": False,
            "foundation_version": FOUNDATION_VERSION,
            "store_slug": slug,
            "generated_at": utc_now_iso(),
            "records": [],
            "by_domain": {d: [] for d in all_domains_v1()},
            "counts": {"records": 0},
            "error": type(exc).__name__,
            "ai_used": False,
        }


__all__ = [
    "build_commerce_intelligence_package_v1",
    "run_commerce_intelligence_foundation_v1",
]
