# -*- coding: utf-8 -*-
"""
Merchant Product Language V1 — presentation-language layer.

Formats Merchant Insight output into merchant-facing narrative structure.
Meaning is owned by Merchant Insight Layer; MPL owns wording and display only.

Legacy ``compose_page_narrative_v1()`` remains for non-migrated pages only.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional, TypedDict

from services.merchant_product_language_templates import (
    CARTFLOW_ACTION_BY_KEY,
    DEFAULT_CARTFLOW_ACTION_BY_PAGE,
    EVIDENCE_CARTS_ATTENTION_MANY,
    EVIDENCE_CARTS_ATTENTION_ONE,
    EVIDENCE_CARTS_AUTOMATIC,
    EVIDENCE_CARTS_ALL_NEED_DECISION_MANY,
    EVIDENCE_CARTS_ALL_NEED_DECISION_ONE,
    EVIDENCE_CARTS_MONITORING,
    EVIDENCE_HOME_ATTENTION,
    EVIDENCE_HOME_CALM,
    EVIDENCE_MESSAGES_HEALTHY,
    EVIDENCE_MESSAGES_NEEDS_REVIEW,
    EVIDENCE_PLANS_ACTIVE,
    EVIDENCE_PLANS_TRIAL,
    EVIDENCE_SETTINGS_COMPLETE,
    EVIDENCE_SETTINGS_INCOMPLETE,
    EVIDENCE_WHATSAPP_NOT_READY,
    EVIDENCE_WHATSAPP_READY,
    EVIDENCE_WIDGET_ACTIVE,
    EVIDENCE_WIDGET_INACTIVE,
    HEADLINE_SELECTOR_BY_PAGE,
)

LANGUAGE_VERSION = "v1"
AUTHORITY = "merchant_product_language_v1"

SECTION_HEADLINE = "headline"
SECTION_REASON = "reason"
SECTION_EVIDENCE = "evidence"
SECTION_CARTFLOW_ACTION = "cartflow_action"
SECTION_DETAILS = "details"

INSIGHT_AUTHORITY = "merchant_insight_layer_v1"

VALID_PAGE_KEYS = frozenset(
    {"home", "carts", "messages", "whatsapp", "widget", "settings", "plans"}
)

# ---------------------------------------------------------------------------
# Page intent registry — exactly one primary question per page
# ---------------------------------------------------------------------------

PAGE_INTENT_REGISTRY: dict[str, dict[str, str]] = {
    "home": {
        "page_key": "home",
        "primary_question_ar": "ماذا يحتاج متجري اليوم؟",
    },
    "carts": {
        "page_key": "carts",
        "primary_question_ar": "أي السلال تستحق الانتباه الآن؟",
    },
    "messages": {
        "page_key": "messages",
        "primary_question_ar": "هل التواصل مع العملاء سليم؟",
    },
    "whatsapp": {
        "page_key": "whatsapp",
        "primary_question_ar": "هل قناة التواصل جاهزة؟",
    },
    "widget": {
        "page_key": "widget",
        "primary_question_ar": "هل CartFlow يفهم تردد العملاء؟",
    },
    "settings": {
        "page_key": "settings",
        "primary_question_ar": "هل إعدادات متجري صحيحة؟",
    },
    "plans": {
        "page_key": "plans",
        "primary_question_ar": "ما حالة اشتراكي الحالية؟",
    },
}


class NarrativeBlock(TypedDict):
    text_ar: str
    source_refs: list[str]


class EvidenceBlock(TypedDict):
    lines_ar: list[str]
    source_refs: list[str]


class PageNarrativeSections(TypedDict, total=False):
    headline: NarrativeBlock
    evidence: EvidenceBlock
    cartflow_action: NarrativeBlock


class PageLanguageEvidence(TypedDict, total=False):
    """Explicit upstream facts — optional per page; never inferred."""

    attention_count: int
    monitored_count: int
    automatic_count: int
    needs_review_count: int
    channel_ready: bool
    widget_active: bool
    setup_complete: bool
    incomplete_count: int
    subscription_needs_attention: bool
    subscription_status: str
    plan_label_ar: str
    days_remaining: int
    cartflow_action_key: str


def _norm(value: Any) -> str:
    return str(value or "").strip()


def list_page_intents_v1() -> list[dict[str, str]]:
    """Return the governed page intent registry (read-only)."""
    return [
        dict(PAGE_INTENT_REGISTRY[key])
        for key in ("home", "carts", "messages", "whatsapp", "widget", "settings", "plans")
    ]


def get_page_intent_v1(page_key: str) -> dict[str, str]:
    key = _norm(page_key).lower()
    if key not in PAGE_INTENT_REGISTRY:
        raise ValueError(f"unknown merchant page key: {page_key!r}")
    return dict(PAGE_INTENT_REGISTRY[key])


def _block(text_ar: str, source_refs: Iterable[str]) -> NarrativeBlock:
    refs = sorted({_norm(r) for r in source_refs if _norm(r)})
    return {"text_ar": _norm(text_ar), "source_refs": refs}


def _evidence_block(lines: Iterable[str], source_refs: Iterable[str]) -> EvidenceBlock:
    clean_lines = [_norm(line) for line in lines if _norm(line)]
    refs = sorted({_norm(r) for r in source_refs if _norm(r)})
    return {"lines_ar": clean_lines, "source_refs": refs}


def _compose_carts_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    lines: list[str] = []
    refs: list[str] = []
    monitored = evidence.get("monitored_count")
    attention = evidence.get("attention_count")
    automatic = evidence.get("automatic_count")

    if monitored is not None:
        count = int(monitored)
        if count > 0:
            lines.append(EVIDENCE_CARTS_MONITORING.format(monitored_count=count))
            refs.append("monitored_count")

    if attention is not None:
        ac = int(attention)
        if ac == 1:
            lines.append(EVIDENCE_CARTS_ATTENTION_ONE)
            refs.append("attention_count")
        elif ac > 1:
            lines.append(EVIDENCE_CARTS_ATTENTION_MANY.format(attention_count=ac))
            refs.append("attention_count")

    if automatic is not None:
        auto = int(automatic)
        if auto > 0:
            lines.append(EVIDENCE_CARTS_AUTOMATIC.format(automatic_count=auto))
            refs.append("automatic_count")

    return _evidence_block(lines, refs)


def _compose_home_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    count = evidence.get("attention_count")
    if count is None:
        return _evidence_block([], [])
    ac = int(count)
    if ac <= 0:
        return _evidence_block([EVIDENCE_HOME_CALM], ["attention_count"])
    return _evidence_block(
        [EVIDENCE_HOME_ATTENTION.format(attention_count=ac)],
        ["attention_count"],
    )


def _compose_messages_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    count = evidence.get("needs_review_count")
    if count is None:
        return _evidence_block([], [])
    rc = int(count)
    if rc <= 0:
        return _evidence_block([EVIDENCE_MESSAGES_HEALTHY], ["needs_review_count"])
    return _evidence_block(
        [EVIDENCE_MESSAGES_NEEDS_REVIEW.format(needs_review_count=rc)],
        ["needs_review_count"],
    )


def _compose_whatsapp_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    ready = evidence.get("channel_ready")
    if ready is True:
        return _evidence_block([EVIDENCE_WHATSAPP_READY], ["channel_ready"])
    if ready is False:
        return _evidence_block([EVIDENCE_WHATSAPP_NOT_READY], ["channel_ready"])
    return _evidence_block([], [])


def _compose_widget_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    active = evidence.get("widget_active")
    if active is True:
        return _evidence_block([EVIDENCE_WIDGET_ACTIVE], ["widget_active"])
    if active is False:
        return _evidence_block([EVIDENCE_WIDGET_INACTIVE], ["widget_active"])
    return _evidence_block([], [])


def _compose_settings_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    complete = evidence.get("setup_complete")
    if complete is True:
        return _evidence_block([EVIDENCE_SETTINGS_COMPLETE], ["setup_complete"])
    if complete is False:
        incomplete = int(evidence.get("incomplete_count") or 0)
        if incomplete > 0:
            return _evidence_block(
                [EVIDENCE_SETTINGS_INCOMPLETE.format(incomplete_count=incomplete)],
                ["setup_complete", "incomplete_count"],
            )
        return _evidence_block([EVIDENCE_SETTINGS_INCOMPLETE.format(incomplete_count=1)], ["setup_complete"])
    return _evidence_block([], [])


def _compose_plans_evidence(evidence: Mapping[str, Any]) -> EvidenceBlock:
    lines: list[str] = []
    refs: list[str] = []
    plan_label = _norm(evidence.get("plan_label_ar"))
    if plan_label:
        lines.append(EVIDENCE_PLANS_ACTIVE.format(plan_label_ar=plan_label))
        refs.append("plan_label_ar")
    days = evidence.get("days_remaining")
    if days is not None and int(days) >= 0:
        lines.append(EVIDENCE_PLANS_TRIAL.format(days_remaining=int(days)))
        refs.append("days_remaining")
    return _evidence_block(lines, refs)


EVIDENCE_COMPOSER_BY_PAGE = {
    "home": _compose_home_evidence,
    "carts": _compose_carts_evidence,
    "messages": _compose_messages_evidence,
    "whatsapp": _compose_whatsapp_evidence,
    "widget": _compose_widget_evidence,
    "settings": _compose_settings_evidence,
    "plans": _compose_plans_evidence,
}


def _resolve_cartflow_action(
    page_key: str,
    evidence: Mapping[str, Any],
) -> NarrativeBlock:
    action_key = _norm(evidence.get("cartflow_action_key"))
    if not action_key:
        action_key = DEFAULT_CARTFLOW_ACTION_BY_PAGE.get(page_key, "holding_ready")
    text = CARTFLOW_ACTION_BY_KEY.get(action_key, CARTFLOW_ACTION_BY_KEY["holding_ready"])
    refs = ["cartflow_action_key"] if _norm(evidence.get("cartflow_action_key")) else ["default_action"]
    return _block(text, refs)


def _format_carts_evidence_summary(summary: Mapping[str, Any]) -> EvidenceBlock:
    """Format MIL evidence_summary counts into governed evidence lines."""
    monitored = summary.get("monitored_count")
    attention = summary.get("attention_count")
    automatic = summary.get("automatic_count")

    if monitored is not None and attention is not None:
        mc = int(monitored)
        ac = int(attention)
        if mc > 0 and ac >= mc:
            if mc == 1:
                return _evidence_block(
                    [EVIDENCE_CARTS_ALL_NEED_DECISION_ONE],
                    ["monitored_count", "attention_count"],
                )
            return _evidence_block(
                [EVIDENCE_CARTS_ALL_NEED_DECISION_MANY.format(monitored_count=mc)],
                ["monitored_count", "attention_count"],
            )

    lines: list[str] = []
    refs: list[str] = []

    if monitored is not None:
        count = int(monitored)
        if count > 0:
            lines.append(EVIDENCE_CARTS_MONITORING.format(monitored_count=count))
            refs.append("monitored_count")

    if attention is not None:
        ac = int(attention)
        if ac == 1:
            lines.append(EVIDENCE_CARTS_ATTENTION_ONE)
            refs.append("attention_count")
        elif ac > 1:
            lines.append(EVIDENCE_CARTS_ATTENTION_MANY.format(attention_count=ac))
            refs.append("attention_count")

    if automatic is not None:
        auto = int(automatic)
        if auto > 0:
            lines.append(EVIDENCE_CARTS_AUTOMATIC.format(automatic_count=auto))
            refs.append("automatic_count")

    return _evidence_block(lines, refs)


EVIDENCE_SUMMARY_FORMATTER_BY_PAGE = {
    "carts": _format_carts_evidence_summary,
}


def render_product_language_from_insight_v1(
    page_key: str,
    insight: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Render MPL narrative from Merchant Insight Layer output.

    Display order: headline (insight) → reason → CartFlow action → evidence.
    MPL does not derive meaning — it formats governed insight fields only.
    """
    key = _norm(page_key).lower()
    if key not in VALID_PAGE_KEYS:
        raise ValueError(f"unknown merchant page key: {page_key!r}")

    intent = get_page_intent_v1(key)
    refs = list(insight.get("source_refs") or [])
    summary = insight.get("evidence_summary") or {}
    formatter = EVIDENCE_SUMMARY_FORMATTER_BY_PAGE.get(key)
    evidence_block = formatter(summary) if formatter else _evidence_block([], [])

    sections: PageNarrativeSections = {
        "headline": _block(_norm(insight.get("primary_insight")), refs),
        "reason": _block(_norm(insight.get("reason")), refs),
        "cartflow_action": _block(_norm(insight.get("cartflow_action")), ["cartflow_action"]),
        "evidence": evidence_block,
    }

    return {
        "version": LANGUAGE_VERSION,
        "authority": AUTHORITY,
        "page_key": key,
        "primary_question_ar": intent["primary_question_ar"],
        "insight_type": _norm(insight.get("insight_type")),
        "confidence": _norm(insight.get("confidence")),
        "sections": sections,
        "composition_order": [
            SECTION_HEADLINE,
            SECTION_REASON,
            SECTION_CARTFLOW_ACTION,
            SECTION_EVIDENCE,
        ],
        "source_insight": {
            "version": _norm(insight.get("version")),
            "authority": _norm(insight.get("authority")),
        },
        "observability": {
            "renders_from_insight": True,
            "meaning_source": INSIGHT_AUTHORITY,
            "sections_rendered": [
                SECTION_HEADLINE,
                SECTION_REASON,
                SECTION_CARTFLOW_ACTION,
                SECTION_EVIDENCE,
            ],
            "details_deferred": True,
        },
    }


def compose_carts_narrative_from_payload_v1(
    payload: Mapping[str, Any],
    rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """Carts path: evidence → insight → product language (certification helper)."""
    from services.merchant_insight_layer_v1 import compose_page_insight_v1

    evidence = build_carts_page_evidence_v1(payload, rows)
    insight = compose_page_insight_v1("carts", evidence)
    return render_product_language_from_insight_v1("carts", insight)


def validate_product_language_from_insight_v1(narrative: Mapping[str, Any]) -> list[str]:
    """Certification for insight-sourced MPL narratives."""
    violations: list[str] = []

    if _norm(narrative.get("version")) != LANGUAGE_VERSION:
        violations.append("invalid version")
    if _norm(narrative.get("authority")) != AUTHORITY:
        violations.append("invalid authority")

    obs = narrative.get("observability") or {}
    if not obs.get("renders_from_insight"):
        violations.append("must render from insight")
    if _norm(obs.get("meaning_source")) != INSIGHT_AUTHORITY:
        violations.append("meaning_source must be merchant_insight_layer_v1")

    page_key = _norm(narrative.get("page_key")).lower()
    if page_key not in VALID_PAGE_KEYS:
        violations.append("unknown page_key")

    order = narrative.get("composition_order") or []
    expected = [SECTION_HEADLINE, SECTION_REASON, SECTION_CARTFLOW_ACTION, SECTION_EVIDENCE]
    if list(order) != expected:
        violations.append("composition_order must be insight-before-evidence")

    sections = narrative.get("sections")
    if not isinstance(sections, dict):
        violations.append("sections missing")
        return violations

    for required in expected:
        if required not in sections:
            violations.append(f"missing section: {required}")

    headline = sections.get(SECTION_HEADLINE) or {}
    if not _norm(headline.get("text_ar")):
        violations.append("headline.text_ar empty")
    elif re.match(r"^\d+\s", _norm(headline.get("text_ar"))):
        violations.append("headline must not lead with raw count")

    reason = sections.get(SECTION_REASON) or {}
    if not _norm(reason.get("text_ar")):
        violations.append("reason.text_ar empty")

    action = sections.get(SECTION_CARTFLOW_ACTION) or {}
    if not _norm(action.get("text_ar")):
        violations.append("cartflow_action.text_ar empty")

    forbidden = (
        "lifecycle_state",
        "group_key",
        "reason_tag",
        "snapshot",
        "bucket",
        "decision_key",
    )
    combined = _norm(narrative.get("primary_question_ar"))
    for sec in (headline, reason, action):
        combined += " " + _norm(sec.get("text_ar"))
    ev_sec = sections.get(SECTION_EVIDENCE) or {}
    for line in ev_sec.get("lines_ar") or []:
        combined += " " + _norm(line)
    lower = combined.lower()
    for token in forbidden:
        if token in lower:
            violations.append(f"forbidden token in narrative: {token}")

    return violations


def compose_page_narrative_v1(
    page_key: str,
    evidence: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    **Legacy** — compose Sections 1–3 directly from raw evidence.

    New page paths must use ``render_product_language_from_insight_v1()`` after
    ``compose_page_insight_v1()`` — meaning is owned by Merchant Insight Layer.

    Section 4 (details) is intentionally omitted — existing cards/lists remain
    unchanged and render below this narrative shell.
    """
    key = _norm(page_key).lower()
    if key not in VALID_PAGE_KEYS:
        raise ValueError(f"unknown merchant page key: {page_key!r}")

    ev: Mapping[str, Any] = evidence or {}
    intent = get_page_intent_v1(key)

    selector = HEADLINE_SELECTOR_BY_PAGE[key]
    headline_text, headline_refs = selector(ev)

    evidence_composer = EVIDENCE_COMPOSER_BY_PAGE[key]
    evidence_block = evidence_composer(ev)

    action_block = _resolve_cartflow_action(key, ev)

    sections: PageNarrativeSections = {
        "headline": _block(headline_text, headline_refs),
        "evidence": evidence_block,
        "cartflow_action": action_block,
    }

    return {
        "version": LANGUAGE_VERSION,
        "authority": AUTHORITY,
        "page_key": key,
        "primary_question_ar": intent["primary_question_ar"],
        "sections": sections,
        "observability": {
            "evidence_keys_supplied": sorted(_norm(k) for k in ev.keys() if _norm(k)),
            "sections_composed": [SECTION_HEADLINE, SECTION_EVIDENCE, SECTION_CARTFLOW_ACTION],
            "details_deferred": True,
        },
    }


def compose_merchant_product_language_v1(
    pages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Batch narrative composition for multiple pages.

    ``pages`` maps page_key → evidence dict from upstream read models.
    """
    narratives: dict[str, Any] = {}
    for page_key in ("home", "carts", "messages", "whatsapp", "widget", "settings", "plans"):
        if page_key not in pages:
            continue
        narratives[page_key] = compose_page_narrative_v1(page_key, pages[page_key])

    return {
        "version": LANGUAGE_VERSION,
        "authority": AUTHORITY,
        "page_intents": list_page_intents_v1(),
        "narratives": narratives,
        "observability": {
            "pages_composed": sorted(narratives.keys()),
            "pages_registered": sorted(VALID_PAGE_KEYS),
        },
    }


def validate_page_narrative_v1(narrative: Mapping[str, Any]) -> list[str]:
    """Return certification violations; empty list means valid."""
    violations: list[str] = []

    if _norm(narrative.get("version")) != LANGUAGE_VERSION:
        violations.append("invalid version")
    if _norm(narrative.get("authority")) != AUTHORITY:
        violations.append("invalid authority")

    page_key = _norm(narrative.get("page_key")).lower()
    if page_key not in VALID_PAGE_KEYS:
        violations.append("unknown page_key")

    intent = PAGE_INTENT_REGISTRY.get(page_key, {})
    if _norm(narrative.get("primary_question_ar")) != _norm(intent.get("primary_question_ar")):
        violations.append("primary_question_ar drift")

    sections = narrative.get("sections")
    if not isinstance(sections, dict):
        violations.append("sections missing")
        return violations

    for required in (SECTION_HEADLINE, SECTION_EVIDENCE, SECTION_CARTFLOW_ACTION):
        if required not in sections:
            violations.append(f"missing section: {required}")

    headline = sections.get(SECTION_HEADLINE) or {}
    if not _norm(headline.get("text_ar")):
        violations.append("headline.text_ar empty")

    action = sections.get(SECTION_CARTFLOW_ACTION) or {}
    if not _norm(action.get("text_ar")):
        violations.append("cartflow_action.text_ar empty")

    if SECTION_DETAILS in sections:
        violations.append("details must not be composed in v1 foundation")

    forbidden = (
        "lifecycle_state",
        "group_key",
        "reason_tag",
        "snapshot",
        "bucket",
        "decision_key",
    )
    combined = _norm(narrative.get("primary_question_ar"))
    for sec in (headline, action):
        combined += " " + _norm(sec.get("text_ar"))
    ev_sec = sections.get(SECTION_EVIDENCE) or {}
    for line in ev_sec.get("lines_ar") or []:
        combined += " " + _norm(line)
    lower = combined.lower()
    for token in forbidden:
        if token in lower:
            violations.append(f"forbidden token in narrative: {token}")

    return violations


def build_carts_page_evidence_v1(
    payload: Mapping[str, Any],
    rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Build explicit Carts page evidence from an existing normal-carts dashboard payload.

    Consumption-only: reads ``merchant_value_stories_v1``, ``merchant_intelligence_store_v1``,
    filter/store counters, and row lists — never mints facts.
    """
    rows_list = list(rows or [])
    evidence: dict[str, Any] = {}
    has_any = False

    filter_fc = payload.get("merchant_cart_filter_counts") or {}
    store_fc = payload.get("merchant_store_cart_counts") or {}

    monitored = len(rows_list)
    if monitored > 0:
        evidence["monitored_count"] = monitored
        has_any = True
    else:
        if filter_fc.get("all") is not None:
            val = int(filter_fc.get("all") or 0)
            if val > 0:
                evidence["monitored_count"] = val
                has_any = True
        elif store_fc.get("active_total") is not None:
            val = int(store_fc.get("active_total") or 0)
            if val > 0:
                evidence["monitored_count"] = val
                has_any = True

    attention = 0
    stories = ((payload.get("merchant_value_stories_v1") or {}).get("stories") or [])
    if stories:
        has_any = True
        for story in stories:
            if story.get("action_required"):
                attention += int(story.get("affected_carts") or 0)

    store = payload.get("merchant_intelligence_store_v1") or {}
    groups = store.get("groups") or []
    if groups:
        has_any = True
    if attention <= 0:
        for group in groups:
            if _norm(group.get("group_id")) == "needs_merchant":
                attention += int(group.get("affected_carts") or 0)

    if has_any and evidence.get("monitored_count") is not None:
        evidence["attention_count"] = attention
        evidence["automatic_count"] = max(0, int(evidence["monitored_count"]) - attention)

    sent = int(filter_fc.get("sent") or store_fc.get("sent_total") or 0)
    if attention > 0:
        evidence["cartflow_action_key"] = "waiting_merchant"
    elif sent > 0:
        evidence["cartflow_action_key"] = "monitoring_replies"
    elif has_any:
        evidence["cartflow_action_key"] = "observing_behavior"

    evidence["has_sufficient_evidence"] = bool(
        has_any
        and (
            stories
            or groups
            or rows_list
            or evidence.get("monitored_count")
        )
    )
    return evidence


def has_carts_sufficient_evidence_v1(
    payload: Mapping[str, Any],
    rows: Optional[Iterable[Mapping[str, Any]]] = None,
) -> bool:
    return bool(build_carts_page_evidence_v1(payload, rows).get("has_sufficient_evidence"))
