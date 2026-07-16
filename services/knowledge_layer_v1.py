# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — orchestrator (read-only report builder).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from services.knowledge_insights_v1 import build_all_insights
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_time_authority_v1 import knowledge_stamp_now
from services.knowledge_types_v1 import KnowledgeReport


def build_knowledge_report(
    db: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
) -> KnowledgeReport:
    """
    Build a complete evidence-based knowledge report for one store.

    Read-only — no writes.
    Temporal window / stamp from Time Authority (WP-4).
    """
    metrics = collect_knowledge_metrics(
        db,
        store_slug,
        window_days=window_days,
        now=now,
    )
    insights = build_all_insights(metrics)
    generated = knowledge_stamp_now(now=now).isoformat()
    return KnowledgeReport(
        ok=True,
        store_slug=(store_slug or "").strip()[:255],
        window_days=window_days,
        generated_at=generated,
        insights=insights,
        metrics_snapshot=metrics.to_dict(),
    )
