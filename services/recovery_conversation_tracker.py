# -*- coding: utf-8 -*-
"""تتبع آخر رد عميل في مسار الاسترجاع — معاينة، وقت، شارة للوحة."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from models import AbandonedCart

from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart
from services.recovery_interaction_state import (
    STATE_ENGAGED,
    STATE_RECOVERED,
    normalize_interaction_state,
    truncate_preview_text,
)
from services.recovery_reply_actions import recovery_merchant_action_for_intent
from services.recovery_reply_intent_labels import recovery_reply_intent_badge_ar
from services.recovery_reply_suggestions import (
    effective_suggestion_intent,
    get_recovery_reply_suggestion,
)
from services.whatsapp_positive_reply import normalize_wa_customer_digits


def _parse_iso_utc(iso_s: Optional[str]) -> Optional[datetime]:
    if not iso_s or not str(iso_s).strip():
        return None
    s = str(iso_s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def format_last_interaction_ar(iso_s: Optional[str]) -> str:
    dt = _parse_iso_utc(iso_s)
    if dt is None:
        return ""
    try:
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (OSError, ValueError):
        return (iso_s or "").strip()[:32]


def conversation_dashboard_extras(ac: AbandonedCart) -> dict[str, Any]:
    """
    حقول إضافية لبطاقة «السلال العادية» — بدون تغيير مسار الإرسال.
    """
    st = (getattr(ac, "status", None) or "").strip().lower()
    bh = behavioral_dict_for_abandoned_cart(ac)
    replied = bool(bh.get("customer_replied") is True or bh.get("interactive_mode") is True)
    raw_state = bh.get("recovery_conversation_state")
    if st == "recovered":
        conv_key = STATE_RECOVERED
    elif replied:
        conv_key = normalize_interaction_state(
            str(raw_state) if raw_state is not None else STATE_ENGAGED
        )
    else:
        conv_key = ""

    preview = str(bh.get("last_customer_reply_preview") or "").strip()
    if not preview:
        preview = truncate_preview_text(str(bh.get("latest_customer_message") or ""))
    last_iso = str(
        bh.get("last_customer_reply_at") or bh.get("latest_customer_reply_at") or ""
    ).strip()
    intent_raw = str(bh.get("recovery_reply_intent") or "").strip().lower()
    intent_label_ar = recovery_reply_intent_badge_ar(intent_raw) if intent_raw else ""

    suggested_reply_ar = ""
    suggested_action_hint_ar = ""
    suggested_action_key = ""
    if replied and st != "recovered":
        cust_for_sugg = str(bh.get("latest_customer_message") or preview or "").strip()
        eff_intent = intent_raw if intent_raw else "other"
        sug = get_recovery_reply_suggestion(eff_intent, cust_for_sugg)
        suggested_reply_ar = str(sug.get("suggested_reply") or "").strip()
        suggested_action_hint_ar = str(sug.get("suggested_action") or "").strip()
        suggested_action_key = recovery_merchant_action_for_intent(
            effective_suggestion_intent(eff_intent)
        ).key
    subtitle = ""
    badge = False
    open_hint = ""
    if st == "recovered":
        subtitle = ""
        badge = False
    elif replied and conv_key and conv_key != STATE_RECOVERED:
        subtitle = "المحادثة نشطة"
        badge = True
        open_hint = "نسخ رابط المحادثة للصقه في واتساب (لا يُفتح تلقائياً)."

    digits = normalize_wa_customer_digits(str(getattr(ac, "customer_phone", None) or ""))
    copy_wa_url = f"https://wa.me/{digits}" if digits and len(digits) >= 11 else ""

    return {
        "normal_recovery_interactive_mode": replied and st != "recovered",
        "normal_recovery_interactive_subtitle_ar": subtitle,
        "normal_recovery_active_conversation_badge": badge,
        "normal_recovery_customer_reply_preview": preview,
        "normal_recovery_last_customer_reply_at": last_iso,
        "normal_recovery_last_interaction_display_ar": format_last_interaction_ar(last_iso)
        if last_iso
        else "",
        "normal_recovery_conversation_state_key": conv_key,
        "normal_recovery_open_conversation_hint_ar": open_hint,
        "normal_recovery_copy_wa_url": copy_wa_url,
        "normal_recovery_reply_intent_key": intent_raw,
        "normal_recovery_reply_intent_label_ar": intent_label_ar,
        "normal_recovery_suggested_reply_ar": suggested_reply_ar,
        "normal_recovery_suggested_action_hint_ar": suggested_action_hint_ar,
        "normal_recovery_suggested_action_key": suggested_action_key,
    }
