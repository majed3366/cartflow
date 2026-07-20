# -*- coding: utf-8 -*-
"""
Knowledge Foundation V1 — catalog constants and statement templates.

Factual observations from Evidence Confidence only. No advice or decisions.
"""
from __future__ import annotations

KNOWLEDGE_VERSION_V1 = "kf_v1"
GENERATOR_VERSION_V1 = "kf_v1_gen"

KNOWLEDGE_TYPE_EVIDENCE_QUALITY = "evidence_quality"
KNOWLEDGE_TYPE_METRIC_TREND = "metric_trend_observation"
KNOWLEDGE_TYPE_EVIDENCE_GAP = "evidence_gap"
KNOWLEDGE_TYPE_EVIDENCE_CONFLICT = "evidence_conflict_flag"

KNOWLEDGE_TYPES = frozenset(
    {
        KNOWLEDGE_TYPE_EVIDENCE_QUALITY,
        KNOWLEDGE_TYPE_METRIC_TREND,
        KNOWLEDGE_TYPE_EVIDENCE_GAP,
        KNOWLEDGE_TYPE_EVIDENCE_CONFLICT,
    }
)

HIGH_CONFIDENCE_LEVELS = frozenset({"high", "very_high"})

WINDOW_LABELS: dict[str, str] = {
    "today": "today",
    "d7": "the last 7 days",
    "d30": "the last 30 days",
    "d90": "the last 90 days",
}

METRIC_LABELS: dict[str, str] = {
    "interest_hesitation_count": "Interest hesitation events",
    "cart_added_count": "Cart additions",
    "cart_removed_count": "Cart removals",
    "cart_synced_count": "Cart sync events",
    "cart_abandoned_count": "Cart abandonments",
    "checkout_touched_count": "Checkout touches",
    "purchase_count": "Purchases",
    "recovery_started_count": "Recovery starts",
    "recovery_progressed_count": "Recovery progress events",
    "customer_return_count": "Customer returns",
    "evidence_linked_count": "Evidence-linked events",
}

TREND_TEMPLATES: dict[str, str] = {
    "newly_appeared": "{label} have newly appeared during {window}.",
    "increasing": "{label} are increasing during {window}.",
    "decreasing": "{label} are decreasing during {window}.",
    "disappeared": "{label} have disappeared during {window}.",
    "stable": "{label} are stable during {window}.",
}

WINDOW_LENGTH_DAYS: dict[str, int] = {
    "today": 1,
    "d7": 7,
    "d30": 30,
    "d90": 90,
}


def metric_label(metric_key: str) -> str:
    key = str(metric_key or "").strip()
    return METRIC_LABELS.get(key, key.replace("_", " "))


def window_label(window_code: str) -> str:
    return WINDOW_LABELS.get(str(window_code or "").strip(), "the selected window")


def trend_statement(metric_key: str, trend_direction: str, window_code: str) -> str | None:
    tmpl = TREND_TEMPLATES.get(str(trend_direction or "").strip())
    if not tmpl:
        return None
    return tmpl.format(
        label=metric_label(metric_key),
        window=window_label(window_code),
    )


__all__ = [
    "KNOWLEDGE_VERSION_V1",
    "GENERATOR_VERSION_V1",
    "KNOWLEDGE_TYPE_EVIDENCE_QUALITY",
    "KNOWLEDGE_TYPE_METRIC_TREND",
    "KNOWLEDGE_TYPE_EVIDENCE_GAP",
    "KNOWLEDGE_TYPE_EVIDENCE_CONFLICT",
    "KNOWLEDGE_TYPES",
    "HIGH_CONFIDENCE_LEVELS",
    "WINDOW_LABELS",
    "METRIC_LABELS",
    "TREND_TEMPLATES",
    "WINDOW_LENGTH_DAYS",
    "metric_label",
    "window_label",
    "trend_statement",
]
