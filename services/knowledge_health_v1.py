# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — read-only health endpoint builder.

Runs metrics + insight builders once per request (no duplicate insight execution).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from services.knowledge_insights_v1 import build_all_insights
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_product_metrics_v1 import collect_knowledge_product_metrics
from services.knowledge_time_authority_v1 import knowledge_stamp_now
from services.knowledge_types_v1 import (
    CATEGORY_CONVERSION,
    CATEGORY_HESITATION,
    CATEGORY_RECOVERY,
    CATEGORY_STORE_HEALTH,
    CATEGORY_TRAFFIC,
    CONFIDENCE_INSUFFICIENT,
    KnowledgeInsight,
)

_HEALTH_CATEGORIES = frozenset(
    {
        CATEGORY_TRAFFIC,
        CATEGORY_CONVERSION,
        CATEGORY_HESITATION,
        CATEGORY_RECOVERY,
        CATEGORY_STORE_HEALTH,
    }
)


@dataclass
class KnowledgeHealthReport:
    ok: bool = True
    store_slug: str = ""
    window_days: int = 7
    generated_at: str = ""
    health_status: str = "degraded"
    knowledge_coverage: float = 0.0
    evidence_coverage: float = 0.0
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    stale_knowledge: dict[str, Any] = field(default_factory=dict)
    missing_inputs: list[str] = field(default_factory=list)
    diagnosis_codes: list[str] = field(default_factory=list)
    product_foundation_bridge: dict[str, Any] = field(default_factory=dict)
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "store_slug": self.store_slug,
            "window_days": self.window_days,
            "generated_at": self.generated_at,
            "health_status": self.health_status,
            "knowledge_coverage": round(self.knowledge_coverage, 4),
            "evidence_coverage": round(self.evidence_coverage, 4),
            "confidence_distribution": dict(self.confidence_distribution),
            "stale_knowledge": dict(self.stale_knowledge),
            "missing_inputs": list(self.missing_inputs),
            "diagnosis_codes": list(self.diagnosis_codes),
            "product_foundation_bridge": dict(self.product_foundation_bridge),
            "metrics_snapshot": dict(self.metrics_snapshot),
        }


def _categories_with_evidence(insights: list[KnowledgeInsight]) -> set[str]:
    covered: set[str] = set()
    for ins in insights:
        if ins.confidence != CONFIDENCE_INSUFFICIENT:
            covered.add(ins.category)
    return covered


def _derive_health_status(
    *,
    store_resolved: bool,
    knowledge_coverage: float,
    missing_inputs: list[str],
    all_insights_insufficient: bool,
) -> tuple[str, list[str]]:
    codes: list[str] = []
    if not store_resolved:
        codes.append("KL_STORE_UNRESOLVED")
        return "unhealthy", codes

    if all_insights_insufficient:
        codes.append("KL_ALL_INSIGHTS_INSUFFICIENT")

    critical = {
        "store_unresolved",
    }
    if any(m in critical for m in missing_inputs):
        return "unhealthy", codes + ["KL_CRITICAL_INPUT_MISSING"]

    if knowledge_coverage >= 0.6 and not all_insights_insufficient:
        codes.append("KL_HEALTH_OK")
        return "healthy", codes

    if missing_inputs:
        if "purchase_attribution_unknown" in missing_inputs:
            codes.append("KL_ATTRIBUTION_UNKNOWN")
        if "product_foundation_limited" in missing_inputs:
            codes.append("KL_FOUNDATION_LIMITED")
        if "visitor_data_unavailable" in missing_inputs:
            codes.append("KL_VISITOR_DATA_UNAVAILABLE")
        codes.append("KL_DEGRADED")
        return "degraded", codes

    codes.append("KL_HEALTH_OK")
    return "healthy", codes


def build_knowledge_health(
    db: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
) -> KnowledgeHealthReport:
    """
    Build read-only Knowledge Layer health for one store.

    Insight builders run exactly once inside this function.
    Temporal window / stamp from Time Authority (WP-4).
    """
    generated = knowledge_stamp_now(now=now).isoformat()
    ss = (store_slug or "").strip()[:255]
    metrics = collect_knowledge_metrics(db, ss, window_days=window_days, now=now)
    insights = build_all_insights(metrics)
    product_bridge = collect_knowledge_product_metrics(
        db,
        ss,
        window_days=window_days,
        now=now,
        store_id=metrics.store_id,
    )

    conf_dist = dict(Counter(ins.confidence for ins in insights))
    covered = _categories_with_evidence(insights)
    knowledge_coverage = len(covered) / len(_HEALTH_CATEGORIES)

    evidence_signals = [
        metrics.cart_count > 0,
        metrics.hesitation_total > 0,
        metrics.recovery_messages_sent > 0,
        metrics.purchase_count > 0,
        metrics.lifecycle_closure_rows > 0,
        product_bridge.snapshot_rows > 0 or product_bridge.catalog_rows > 0,
    ]
    evidence_coverage = sum(1 for s in evidence_signals if s) / len(evidence_signals)

    missing: list[str] = []
    if not metrics.store_resolved:
        missing.append("store_unresolved")
    if not metrics.visitor_data_available:
        missing.append("visitor_data_unavailable")
    if not metrics.checkout_data_available and metrics.cart_count > 0:
        missing.append("checkout_data_unavailable")
    if (
        metrics.purchase_count > 0
        and metrics.attributed_recovery_purchase_count == 0
        and metrics.purchase_attribution_evaluated_count > 0
    ):
        missing.append("purchase_attribution_unknown")
    if product_bridge.foundation_readiness != "ready":
        missing.append("product_foundation_limited")
    if metrics.vip_cart_count > 0 and metrics.vip_evidence.get("isolated") is not True:
        missing.append("vip_isolation_failed")

    all_insufficient = bool(insights) and all(
        i.confidence == CONFIDENCE_INSUFFICIENT for i in insights
    )
    stale = {
        "window_end": metrics.window_end.isoformat(),
        "all_insights_insufficient": all_insufficient,
        "product_foundation_readiness": product_bridge.foundation_readiness,
    }

    health_status, diagnosis_codes = _derive_health_status(
        store_resolved=metrics.store_resolved,
        knowledge_coverage=knowledge_coverage,
        missing_inputs=missing,
        all_insights_insufficient=all_insufficient,
    )

    return KnowledgeHealthReport(
        ok=True,
        store_slug=ss,
        window_days=window_days,
        generated_at=generated,
        health_status=health_status,
        knowledge_coverage=knowledge_coverage,
        evidence_coverage=evidence_coverage,
        confidence_distribution=conf_dist,
        stale_knowledge=stale,
        missing_inputs=missing,
        diagnosis_codes=diagnosis_codes,
        product_foundation_bridge=product_bridge.to_dict(),
        metrics_snapshot=metrics.to_dict(),
    )


__all__ = ["KnowledgeHealthReport", "build_knowledge_health"]
