# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — shared types and constants.

Read-only insight foundation; no DB access in this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

# --- Categories ---
CATEGORY_TRAFFIC = "traffic"
CATEGORY_CONVERSION = "conversion"
CATEGORY_HESITATION = "hesitation"
CATEGORY_RECOVERY = "recovery"
CATEGORY_STORE_HEALTH = "store_health"

# --- Severity ---
SEVERITY_INFO = "info"
SEVERITY_NOTICE = "notice"
SEVERITY_WARNING = "warning"

# --- Confidence ---
CONFIDENCE_INSUFFICIENT = "insufficient"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

# --- Sample thresholds ---
MIN_HESITATION_SAMPLE = 3
MIN_RECOVERY_SAMPLE = 2
MIN_CART_SAMPLE = 1

# --- Hesitation buckets (evidence-based reason groups) ---
HESITATION_BUCKETS = frozenset(
    {"price", "shipping", "quality", "delivery", "warranty", "other"}
)

# --- Marketing / unsupported advice (safety guard for tests) ---
FORBIDDEN_ADVICE_PHRASES = frozenset(
    {
        "زد الإعلانات",
        "غيّر أسعارك",
        "منتجاتك سيئة",
        "منتجاتك غير مناسبة",
        "العملاء لا يثقون",
        "عملاؤك لا يثقون",
        "ROI غير مدعوم",
    }
)


@dataclass
class KnowledgeInsight:
    insight_key: str
    category: str
    severity: str
    title_ar: str
    message_ar: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: str = CONFIDENCE_INSUFFICIENT
    data_window: dict[str, Any] = field(default_factory=dict)
    sample_size: int = 0
    source_tables: list[str] = field(default_factory=list)
    recommended_action_ar: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeReport:
    ok: bool
    store_slug: str
    window_days: int
    generated_at: str
    insights: list[KnowledgeInsight] = field(default_factory=list)
    metrics_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "store_slug": self.store_slug,
            "window_days": self.window_days,
            "generated_at": self.generated_at,
            "insights": [i.to_dict() for i in self.insights],
            "metrics_snapshot": self.metrics_snapshot,
        }


def insufficient_insight(
    *,
    insight_key: str,
    category: str,
    title_ar: str,
    message_ar: str,
    evidence: Optional[dict[str, Any]] = None,
    data_window: Optional[dict[str, Any]] = None,
    sample_size: int = 0,
    source_tables: Optional[list[str]] = None,
    recommended_action_ar: str = "تأكد أن بيانات المتجر تصل بشكل صحيح.",
    severity: str = SEVERITY_NOTICE,
) -> KnowledgeInsight:
    """Build a cautious insight when data is missing or sample is too small."""
    return KnowledgeInsight(
        insight_key=insight_key,
        category=category,
        severity=severity,
        title_ar=title_ar,
        message_ar=message_ar,
        evidence=evidence or {},
        confidence=CONFIDENCE_INSUFFICIENT,
        data_window=data_window or {},
        sample_size=sample_size,
        source_tables=source_tables or [],
        recommended_action_ar=recommended_action_ar,
    )


def data_window_payload(
    *,
    window_days: int,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any]:
    return {
        "days": window_days,
        "start": window_start.isoformat(),
        "end": window_end.isoformat(),
    }


def confidence_from_sample(sample_size: int, *, minimum: int) -> str:
    if sample_size < minimum:
        return CONFIDENCE_INSUFFICIENT
    if sample_size < minimum * 2:
        return CONFIDENCE_LOW
    if sample_size < minimum * 5:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_HIGH
