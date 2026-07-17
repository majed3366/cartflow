# -*- coding: utf-8 -*-
"""
Recovery Journey Home v1 — presentation mapping for Home Attention (PIB-3).

Consumes existing canonical lifecycle labels + explanation catalog copy.
Does not mint lifecycle states, schedule sends, or invent recovery logic.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.customer_lifecycle_states_v1 import (
    LABEL_AR,
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    STATE_NEEDS_INTERVENTION,
    STATE_RETURN_TO_SITE,
    STATE_WAITING_FIRST_SEND,
    STATE_WAITING_PURCHASE_WINDOW,
)

JOURNEY_VERSION = "v1"

CHANNEL_WIDGET_CONTACT_AR = "الودجت / بيانات التواصل"
CHANNEL_WHATSAPP_AR = "واتساب"
CHANNEL_MERCHANT_AR = "تدخل التاجر"
CHANNEL_SITE_RETURN_AR = "الموقع بعد رسالة الاسترجاع"

_NO_MERCHANT_ACTION_AR = "لا يلزم إجراء منك الآن — CartFlow يتابع تلقائياً"
_NO_BLOCKER_AR = "لا يوجد حاجز حالياً"

_JOURNEY_REQUIRED_FIELDS = (
    "recovery_stage_key",
    "recovery_stage_ar",
    "recovery_channel_ar",
    "recovery_stage_why_ar",
    "recovery_blocker_ar",
    "recovery_next_platform_ar",
    "recovery_next_merchant_ar",
    "recovery_completion_condition_ar",
)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def is_recovery_journey_complete_v1(journey: Mapping[str, Any] | None) -> bool:
    if not isinstance(journey, Mapping):
        return False
    return all(_norm(journey.get(k)) for k in _JOURNEY_REQUIRED_FIELDS)


def build_recovery_journey_for_attention_v1(
    *,
    operational_decision_key: str,
    case_count: int = 0,
    action_ar: str = "",
) -> Optional[dict[str, Any]]:
    """
    Map one Attention operational decision to a Recovery Journey chapter.

    Uses LT-C1 state keys + existing Arabic labels only.
    """
    op = _norm(operational_decision_key)
    cases = int(case_count or 0)
    case_suffix = f" ({cases} حالات)" if cases > 0 else ""

    if op == "decision:obtain_contact":
        stage_key = STATE_NEEDS_INTERVENTION
        journey = {
            "version": JOURNEY_VERSION,
            "recovery_stage_key": stage_key,
            "recovery_stage_ar": f"{LABEL_WAITING_CONTACT_COMPLETION_AR}{case_suffix}",
            "recovery_channel_ar": CHANNEL_WIDGET_CONTACT_AR,
            "recovery_stage_why_ar": (
                "مسار الاسترجاع وصل لمرحلة تحتاج رقم تواصل قبل أي إرسال واتساب."
            ),
            "recovery_blocker_ar": (
                f"لا يوجد رقم عميل — واتساب لا يُرسل{case_suffix}"
                if cases > 0
                else "لا يوجد رقم عميل — واتساب لا يُرسل"
            ),
            "recovery_next_platform_ar": (
                "بعد توفر الرقم: يجهّز CartFlow جدولة/إرسال رسالة واتساب تلقائياً."
            ),
            "recovery_next_merchant_ar": _norm(action_ar)
            or "الحصول على رقم العميل من السلال بانتظار التواصل",
            "recovery_completion_condition_ar": (
                "يتوفر رقم تواصل صالح وتُستأنف متابعة الاسترجاع الآلية."
            ),
            "recovery_merchant_required": True,
            "recovery_platform_waiting": True,
            "canonical_label_ar": LABEL_AR.get(stage_key, ""),
        }
        return journey

    if op == "decision:fix_channel":
        stage_key = STATE_NEEDS_INTERVENTION
        journey = {
            "version": JOURNEY_VERSION,
            "recovery_stage_key": stage_key,
            "recovery_stage_ar": f"{LABEL_AR[stage_key]}{case_suffix}",
            "recovery_channel_ar": CHANNEL_WHATSAPP_AR,
            "recovery_stage_why_ar": (
                "تعذّر على CartFlow إكمال إرسال الاسترجاع عبر واتساب."
            ),
            "recovery_blocker_ar": (
                f"قناة واتساب متعطلة أو فشل الإرسال{case_suffix}"
                if cases > 0
                else "قناة واتساب متعطلة أو فشل الإرسال"
            ),
            "recovery_next_platform_ar": (
                "بعد إصلاح القناة: يُستأنف إرسال رسائل الاسترجاع تلقائياً."
            ),
            "recovery_next_merchant_ar": _norm(action_ar)
            or "إصلاح قناة واتساب من الإعدادات",
            "recovery_completion_condition_ar": (
                "تعود قناة واتساب صالحة ويُقبل الإرسال من المزود."
            ),
            "recovery_merchant_required": True,
            "recovery_platform_waiting": True,
            "canonical_label_ar": LABEL_AR.get(stage_key, ""),
        }
        return journey

    if op == "decision:contact_customer":
        stage_key = STATE_NEEDS_INTERVENTION
        journey = {
            "version": JOURNEY_VERSION,
            "recovery_stage_key": stage_key,
            "recovery_stage_ar": f"{LABEL_AR[stage_key]}{case_suffix}",
            "recovery_channel_ar": CHANNEL_MERCHANT_AR,
            "recovery_stage_why_ar": (
                "المسار الآلي توقف عند نقطة تحتاج تدخلاً يدوياً بعد توفر بيانات التواصل."
            ),
            "recovery_blocker_ar": (
                f"يلزم تدخل التاجر لإكمال الاسترجاع{case_suffix}"
                if cases > 0
                else "يلزم تدخل التاجر لإكمال الاسترجاع"
            ),
            "recovery_next_platform_ar": (
                "CartFlow يحافظ على سياق السلة والدليل — لا يرسل بديلاً عن تدخلك هنا."
            ),
            "recovery_next_merchant_ar": _norm(action_ar)
            or "التواصل مع العميل من لوحة السلال",
            "recovery_completion_condition_ar": (
                "يتواصل التاجر مع العميل أو تُغلق الحالة وفق قرار التاجر."
            ),
            "recovery_merchant_required": True,
            "recovery_platform_waiting": False,
            "canonical_label_ar": LABEL_AR.get(stage_key, ""),
        }
        return journey

    if op in ("decision:monitor", "decision:decision_monitor_return") or op.endswith(
        ":monitor"
    ):
        # Prefer purchase-window wording when returning after recovery message.
        stage_key = STATE_WAITING_PURCHASE_WINDOW
        journey = {
            "version": JOURNEY_VERSION,
            "recovery_stage_key": stage_key,
            "recovery_stage_ar": LABEL_AR[stage_key],
            "recovery_channel_ar": CHANNEL_SITE_RETURN_AR,
            "recovery_stage_why_ar": (
                "عاد العميل إلى المتجر بعد رسالة الاسترجاع — أوقفنا المتابعة مؤقتاً."
            ),
            "recovery_blocker_ar": _NO_BLOCKER_AR,
            "recovery_next_platform_ar": (
                "CartFlow يراقب ما إذا أكمل العميل الشراء دون إزعاج إضافي."
            ),
            "recovery_next_merchant_ar": _NO_MERCHANT_ACTION_AR,
            "recovery_completion_condition_ar": (
                "يكمل العميل الشراء، أو تنتهي نافذة المراقبة وتعود المتابعة وفق الإعدادات."
            ),
            "recovery_merchant_required": False,
            "recovery_platform_waiting": True,
            "canonical_label_ar": LABEL_AR.get(STATE_RETURN_TO_SITE, ""),
            "related_stage_keys": [STATE_RETURN_TO_SITE, STATE_WAITING_PURCHASE_WINDOW],
        }
        return journey

    # Non-recovery Attention topics do not claim a recovery journey chapter.
    return None


def attach_recovery_journey_to_attention_item_v1(
    item: dict[str, Any],
    *,
    operational_decision_key: str = "",
    case_count: int = 0,
) -> dict[str, Any]:
    """Attach journey fields onto an Attention item (mutates and returns item)."""
    op = _norm(operational_decision_key) or _norm(item.get("operational_decision_key"))
    cases = int(case_count or item.get("decision_count") or 0)
    journey = build_recovery_journey_for_attention_v1(
        operational_decision_key=op,
        case_count=cases,
        action_ar=_norm(item.get("action_ar")),
    )
    if journey is None:
        item["recovery_journey_v1"] = None
        item["recovery_journey_complete"] = False
        return item

    item["recovery_journey_v1"] = journey
    item["recovery_journey_complete"] = is_recovery_journey_complete_v1(journey)
    # Flatten for UI / merchant acceptance (Home summarizes Attention).
    for key in _JOURNEY_REQUIRED_FIELDS:
        item[key] = journey.get(key)
    item["recovery_merchant_required"] = bool(journey.get("recovery_merchant_required"))
    item["recovery_platform_waiting"] = bool(journey.get("recovery_platform_waiting"))
    return item


def recovery_decision_requires_journey_v1(operational_decision_key: str) -> bool:
    op = _norm(operational_decision_key)
    return op in (
        "decision:obtain_contact",
        "decision:fix_channel",
        "decision:contact_customer",
        "decision:monitor",
    ) or op.endswith(":monitor")


__all__ = [
    "CHANNEL_MERCHANT_AR",
    "CHANNEL_SITE_RETURN_AR",
    "CHANNEL_WHATSAPP_AR",
    "CHANNEL_WIDGET_CONTACT_AR",
    "JOURNEY_VERSION",
    "STATE_WAITING_FIRST_SEND",
    "attach_recovery_journey_to_attention_item_v1",
    "build_recovery_journey_for_attention_v1",
    "is_recovery_journey_complete_v1",
    "recovery_decision_requires_journey_v1",
]
