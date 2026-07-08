# -*- coding: utf-8 -*-
"""
Merchant Product Language V1 — governed Arabic templates.

Static phrasing only. Templates are selected by explicit evidence keys;
they never infer conclusions or mint facts.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

# ---------------------------------------------------------------------------
# Headline — Section 1: short operational answer
# ---------------------------------------------------------------------------

HEADLINE_NO_ACTION = "لا يلزم إجراء الآن."
HEADLINE_STORE_READY = "متجرك جاهز."
HEADLINE_OPERATING_NORMALLY = "CartFlow يعمل بشكل طبيعي."
HEADLINE_WHATSAPP_NORMAL = "واتساب يعمل بشكل طبيعي."
HEADLINE_COMMUNICATION_HEALTHY = "التواصل مع العملاء مستقر."
HEADLINE_WIDGET_OBSERVING = "CartFlow يراقب تردد العملاء."
HEADLINE_SETTINGS_OK = "إعدادات متجرك مضبوطة."
HEADLINE_PLANS_ACTIVE = "اشتراكك نشط."

HEADLINE_ATTENTION_CARTS_ONE = "سلة واحدة تستحق انتباهك."
HEADLINE_ATTENTION_CARTS_TWO = "سلتان تستحقان انتباهك."
HEADLINE_ATTENTION_CARTS_MANY = "{count} سلال تستحق انتباهك."

HEADLINE_HOME_ATTENTION_ONE = "أمر واحد يحتاج انتباهك اليوم."
HEADLINE_HOME_ATTENTION_MANY = "{count} أمور تحتاج انتباهك اليوم."

HEADLINE_MESSAGES_NEEDS_REVIEW_ONE = "رسالة واحدة تحتاج متابعة."
HEADLINE_MESSAGES_NEEDS_REVIEW_MANY = "{count} رسائل تحتاج متابعة."

HEADLINE_WHATSAPP_NOT_READY = "قناة التواصل تحتاج إعداداً."
HEADLINE_WIDGET_NOT_READY = "CartFlow لا يزال يجمع إشارات التردد."
HEADLINE_SETTINGS_INCOMPLETE = "بعض الإعدادات تحتاج اكمالاً."
HEADLINE_PLANS_ATTENTION = "اشتراكك يحتاج متابعة."

# ---------------------------------------------------------------------------
# Evidence — Section 2: explain WHY (never numbers alone)
# ---------------------------------------------------------------------------

EVIDENCE_CARTS_MONITORING = (
    "CartFlow يراقب {monitored_count} سلة في متجرك."
)
EVIDENCE_CARTS_ATTENTION_ONE = "واحدة منها تحتاج انتباهك."
EVIDENCE_CARTS_ATTENTION_MANY = "{attention_count} منها تحتاج انتباهك."
EVIDENCE_CARTS_AUTOMATIC = "{automatic_count} تتقدم تلقائياً."

EVIDENCE_CARTS_ALL_NEED_DECISION_ONE = (
    "الأدلة: سلة واحدة تحت المتابعة، وهي ضمن حالة تحتاج قرارك."
)
EVIDENCE_CARTS_ALL_NEED_DECISION_MANY = (
    "الأدلة: {monitored_count} سلال تحت المتابعة، وكلها ضمن حالات تحتاج قرارك."
)

EVIDENCE_HOME_CALM = "لا توجد أمور عاجلة في ملخص اليوم."
EVIDENCE_HOME_ATTENTION = "CartFlow رصد {attention_count} موضوعاً يستحق نظرة."

EVIDENCE_MESSAGES_HEALTHY = "مسار الرسائل مع العملاء مستقر."
EVIDENCE_MESSAGES_NEEDS_REVIEW = "{needs_review_count} محادثة تحتاج متابعة منك."

EVIDENCE_WHATSAPP_READY = "قناة واتساب متصلة وجاهزة للاستخدام."
EVIDENCE_WHATSAPP_NOT_READY = "إعداد واتساب غير مكتمل بعد."

EVIDENCE_WIDGET_ACTIVE = "الودجت يلتقط أسباب التردد من العملاء."
EVIDENCE_WIDGET_INACTIVE = "الودجت لم يبدأ جمع إشارات كافية بعد."

EVIDENCE_SETTINGS_COMPLETE = "الإعدادات الأساسية للمتجر مكتملة."
EVIDENCE_SETTINGS_INCOMPLETE = "{incomplete_count} خطوة إعداد لم تكتمل بعد."

EVIDENCE_PLANS_ACTIVE = "خطتك الحالية: {plan_label_ar}."
EVIDENCE_PLANS_TRIAL = "أنت على فترة تجريبية — {days_remaining} يوم متبقٍ."

# ---------------------------------------------------------------------------
# CartFlow action — Section 3: what CartFlow is doing now
# ---------------------------------------------------------------------------

ACTION_MONITORING_REPLIES = "CartFlow يراقب ردود العملاء."
ACTION_SENDING_RECOVERY = "CartFlow يرسل رسائل الاسترداد المجدولة."
ACTION_WAITING_MERCHANT = "CartFlow ينتظر تدخلك في حالات محددة."
ACTION_OBSERVING_BEHAVIOR = "CartFlow يراقب سلوك العملاء في المتجر."
ACTION_ROUTING_MESSAGES = "CartFlow ينظم مسار رسائل العملاء."
ACTION_MAINTAINING_CHANNEL = "CartFlow يحافظ على جاهزية قناة التواصل."
ACTION_COLLECTING_HESITATION = "CartFlow يجمع أسباب تردد العملاء."
ACTION_HOLDING_READY = "CartFlow جاهز للمتابعة — لا يلزم إجراء الآن."
ACTION_APPLYING_SETTINGS = "CartFlow يطبق إعدادات متجرك على المتابعة اليومية."
ACTION_MANAGING_SUBSCRIPTION = "CartFlow يطبق حدود خطتك الحالية."

CARTFLOW_ACTION_BY_KEY: dict[str, str] = {
    "monitoring_replies": ACTION_MONITORING_REPLIES,
    "sending_recovery": ACTION_SENDING_RECOVERY,
    "waiting_merchant": ACTION_WAITING_MERCHANT,
    "observing_behavior": ACTION_OBSERVING_BEHAVIOR,
    "routing_messages": ACTION_ROUTING_MESSAGES,
    "maintaining_channel": ACTION_MAINTAINING_CHANNEL,
    "collecting_hesitation": ACTION_COLLECTING_HESITATION,
    "holding_ready": ACTION_HOLDING_READY,
    "applying_settings": ACTION_APPLYING_SETTINGS,
    "managing_subscription": ACTION_MANAGING_SUBSCRIPTION,
}

# ---------------------------------------------------------------------------
# Page-default CartFlow actions (when evidence omits action_key)
# ---------------------------------------------------------------------------

DEFAULT_CARTFLOW_ACTION_BY_PAGE: dict[str, str] = {
    "home": "holding_ready",
    "carts": "observing_behavior",
    "messages": "routing_messages",
    "whatsapp": "maintaining_channel",
    "widget": "collecting_hesitation",
    "settings": "applying_settings",
    "plans": "managing_subscription",
}

# ---------------------------------------------------------------------------
# Headline selectors — evidence-driven, never speculative
# ---------------------------------------------------------------------------

HeadlineSelector = Callable[[Mapping[str, Any]], tuple[str, list[str]]]


def _headline_from_attention(
    count: int,
    *,
    one: str,
    two: str,
    many_template: str,
    ref_key: str,
) -> tuple[str, list[str]]:
    if count <= 0:
        return HEADLINE_NO_ACTION, []
    if count == 1:
        return one, [ref_key]
    if count == 2:
        return two, [ref_key]
    return many_template.format(count=count), [ref_key]


def select_home_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    count = int(evidence.get("attention_count") or 0)
    if count <= 0:
        return HEADLINE_NO_ACTION, ["attention_count"]
    if count == 1:
        return HEADLINE_HOME_ATTENTION_ONE, ["attention_count"]
    return HEADLINE_HOME_ATTENTION_MANY.format(count=count), ["attention_count"]


def select_carts_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    return _headline_from_attention(
        int(evidence.get("attention_count") or 0),
        one=HEADLINE_ATTENTION_CARTS_ONE,
        two=HEADLINE_ATTENTION_CARTS_TWO,
        many_template=HEADLINE_ATTENTION_CARTS_MANY,
        ref_key="attention_count",
    )


def select_messages_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    count = int(evidence.get("needs_review_count") or 0)
    if count <= 0:
        return HEADLINE_COMMUNICATION_HEALTHY, ["needs_review_count"]
    if count == 1:
        return HEADLINE_MESSAGES_NEEDS_REVIEW_ONE, ["needs_review_count"]
    return HEADLINE_MESSAGES_NEEDS_REVIEW_MANY.format(count=count), ["needs_review_count"]


def select_whatsapp_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    ready = evidence.get("channel_ready")
    if ready is True:
        return HEADLINE_WHATSAPP_NORMAL, ["channel_ready"]
    if ready is False:
        return HEADLINE_WHATSAPP_NOT_READY, ["channel_ready"]
    return HEADLINE_OPERATING_NORMALLY, []


def select_widget_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    active = evidence.get("widget_active")
    if active is True:
        return HEADLINE_WIDGET_OBSERVING, ["widget_active"]
    if active is False:
        return HEADLINE_WIDGET_NOT_READY, ["widget_active"]
    return HEADLINE_OPERATING_NORMALLY, []


def select_settings_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    complete = evidence.get("setup_complete")
    if complete is True:
        return HEADLINE_SETTINGS_OK, ["setup_complete"]
    if complete is False:
        return HEADLINE_SETTINGS_INCOMPLETE, ["setup_complete"]
    return HEADLINE_STORE_READY, []


def select_plans_headline(evidence: Mapping[str, Any]) -> tuple[str, list[str]]:
    needs_attention = evidence.get("subscription_needs_attention")
    if needs_attention is True:
        return HEADLINE_PLANS_ATTENTION, ["subscription_needs_attention"]
    return HEADLINE_PLANS_ACTIVE, ["subscription_status"]


HEADLINE_SELECTOR_BY_PAGE: dict[str, HeadlineSelector] = {
    "home": select_home_headline,
    "carts": select_carts_headline,
    "messages": select_messages_headline,
    "whatsapp": select_whatsapp_headline,
    "widget": select_widget_headline,
    "settings": select_settings_headline,
    "plans": select_plans_headline,
}
