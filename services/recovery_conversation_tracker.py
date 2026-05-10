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
from services.recovery_product_suggestions import (
    get_product_aware_recovery_suggestion_for_abandoned_cart,
)
from services.recovery_conversation_state_machine import (
    compute_conversational_cooldown,
    stage_label_ar,
)
from services.recovery_reply_suggestions import effective_suggestion_intent
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


def conversation_dashboard_extras(
    ac: AbandonedCart,
    *,
    behavioral_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    حقول إضافية لبطاقة «السلال العادية» — بدون تغيير مسار الإرسال.

    behavioral_payload: اختياري — نفس دمج ‎cf_behavioral‎ المستخدم في ‎_normal_recovery_phase_steps_payload‎
    عند تجميع صفوف ‎AbandonedCart‎ المكرّرة لنفس الجلسة.
    """
    st = (getattr(ac, "status", None) or "").strip().lower()
    if behavioral_payload is not None:
        bh = behavioral_payload
    else:
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
    suggested_strategy_ar = ""
    suggestion_reason_ar = ""
    suggestion_ux_badge_ar = ""
    optional_offer_type = ""
    checkout_cta_mode = ""
    offer_decision_type_ar = ""
    offer_confidence_ar = ""
    offer_rationale_ar = ""
    offer_persuasion_ar = ""
    offer_flag_discount = False
    offer_flag_shipping = False
    offer_flag_alternative = False
    offer_strategy_key = ""
    offer_persuasion_key = ""
    adaptive_stage_key = ""
    adaptive_stage_label_ar = ""
    adaptive_path_ar = ""
    adaptive_transition_ar = ""
    adaptive_turns = 0
    checkout_push_mode = False
    cooldown_snapshot: dict[str, Any] = {}
    cooldown_state_key = ""
    cooldown_state_ar = ""
    silence_duration_display_ar = ""
    silence_duration_minutes_val: Optional[float] = None
    activity_level_ar = ""
    followup_recommendation_ar = ""
    followup_recommended = False
    followup_type_key = ""
    followup_type_ar = ""
    cooldown_context_ar = ""
    pressure_note_ar = ""
    cooldown_panel = False
    return_intel_panel = False
    customer_returned_to_site_track = False
    recovery_return_timestamp_ar = ""
    recovery_returned_product_page_flag = False
    recovery_returned_checkout_page_flag = False
    recovery_site_return_count_val = 0
    return_intel_pressure_note_ar = ""
    return_intel_completion_opportunity = False
    normal_recovery_return_context_key = ""
    normal_recovery_continuation_summary_ar = str(
        bh.get("continuation_summary_ar") or ""
    ).strip()
    normal_recovery_continuation_state_key = str(
        bh.get("continuation_state") or ""
    ).strip()
    if st != "recovered":
        normal_recovery_return_context_key = str(
            bh.get("recovery_return_context") or ""
        ).strip().lower()[:64]
        customer_returned_to_site_track = bool(
            bh.get("customer_returned_to_site") is True
            or bh.get("user_returned_to_site") is True
        )
        try:
            recovery_site_return_count_val = int(
                bh.get("recovery_site_return_count") or 0
            )
        except (TypeError, ValueError):
            recovery_site_return_count_val = 0
        rs_ts = str(bh.get("recovery_return_timestamp") or "").strip()
        if rs_ts:
            recovery_return_timestamp_ar = format_last_interaction_ar(rs_ts)
        recovery_returned_product_page_flag = (
            bh.get("recovery_returned_product_page") is True
        )
        recovery_returned_checkout_page_flag = (
            bh.get("recovery_returned_checkout_page") is True
        )
        return_intel_panel = (
            customer_returned_to_site_track
            or recovery_site_return_count_val > 0
            or bool(rs_ts)
        )
        ash_bh = str(bh.get("recovery_adaptive_stage") or "").strip()
        return_intel_completion_opportunity = ash_bh == "returned_checkout"
        if recovery_returned_checkout_page_flag:
            return_intel_pressure_note_ar = (
                "وصل صفحة الدفع — فرصة إكمال مرتفعة؛ ركّز على المساندة لا العروض المفاجئة."
            )
        elif recovery_returned_product_page_flag:
            return_intel_pressure_note_ar = (
                "عاد لصفحة المنتج — يُنصح بتخفيف الضغط البيعي وتجنّب إغراءات خصم متكررة."
            )
        elif return_intel_panel:
            return_intel_pressure_note_ar = (
                "العميل عاد للموقع — حافظ على حوار هادئ دون مضايقة أو بيع مذعور."
            )
    if replied and st != "recovered":
        adaptive_stage_key = str(bh.get("recovery_adaptive_stage") or "").strip()
        try:
            adaptive_turns_pre = int(bh.get("recovery_adaptive_turn_count") or 0)
        except (TypeError, ValueError):
            adaptive_turns_pre = 0
        cooldown_snapshot = compute_conversational_cooldown(
            last_customer_reply_iso=last_iso,
            adaptive_stage_key=adaptive_stage_key,
            adaptive_turn_count=adaptive_turns_pre,
        )
        cooldown_state_key = str(cooldown_snapshot.get("cooldown_state") or "")
        cooldown_state_ar = str(cooldown_snapshot.get("cooldown_state_ar") or "")
        silence_duration_display_ar = str(
            cooldown_snapshot.get("silence_duration_display_ar") or ""
        )
        try:
            silence_duration_minutes_val = float(
                cooldown_snapshot.get("silence_duration_minutes") or 0.0
            )
        except (TypeError, ValueError):
            silence_duration_minutes_val = 0.0
        activity_level_ar = str(cooldown_snapshot.get("activity_level_ar") or "")
        followup_recommendation_ar = str(
            cooldown_snapshot.get("followup_recommendation_ar") or ""
        )
        followup_recommended = bool(cooldown_snapshot.get("recommend_followup"))
        followup_type_key = str(cooldown_snapshot.get("recommended_followup_key") or "")
        followup_type_ar = str(
            cooldown_snapshot.get("recommended_followup_type_ar") or ""
        )
        cooldown_context_ar = str(cooldown_snapshot.get("cooldown_context_ar") or "")
        pressure_note_ar = str(cooldown_snapshot.get("pressure_note_ar") or "")
        cooldown_panel = True
        cust_for_sugg = str(bh.get("latest_customer_message") or preview or "").strip()
        eff_intent = intent_raw if intent_raw else "other"
        pa = get_product_aware_recovery_suggestion_for_abandoned_cart(
            ac,
            eff_intent,
            cust_for_sugg,
            cooldown_snapshot=cooldown_snapshot,
        )
        suggested_reply_ar = str(pa.get("suggested_reply") or "").strip()
        suggested_strategy_ar = str(pa.get("suggested_strategy") or "").strip()
        suggestion_reason_ar = str(pa.get("suggestion_reason_ar") or "").strip()
        ub = pa.get("ux_badge_ar")
        suggestion_ux_badge_ar = str(ub).strip() if ub else ""
        ot = pa.get("optional_offer_type")
        optional_offer_type = str(ot).strip() if ot else ""
        cm = pa.get("checkout_cta_mode")
        checkout_cta_mode = str(cm).strip() if cm else ""
        suggested_action_key = recovery_merchant_action_for_intent(
            effective_suggestion_intent(eff_intent)
        ).key
        suggested_action_hint_ar = suggested_strategy_ar
        od = pa.get("offer_decision")
        if isinstance(od, dict):
            offer_decision_type_ar = str(od.get("strategy_type_ar") or "").strip()
            offer_confidence_ar = str(od.get("confidence_level_ar") or "").strip()
            offer_rationale_ar = str(od.get("decision_rationale_ar") or "").strip()
            offer_persuasion_ar = str(od.get("persuasion_mode_ar") or "").strip()
            offer_flag_discount = bool(od.get("should_offer_discount"))
            offer_flag_shipping = bool(od.get("should_offer_free_shipping"))
            offer_flag_alternative = bool(od.get("should_offer_alternative"))
            offer_strategy_key = str(od.get("strategy_type") or "").strip()
            offer_persuasion_key = str(od.get("persuasion_mode") or "").strip()
        else:
            offer_decision_type_ar = ""
            offer_confidence_ar = ""
            offer_rationale_ar = ""
            offer_persuasion_ar = ""
            offer_flag_discount = False
            offer_flag_shipping = False
            offer_flag_alternative = False
            offer_strategy_key = ""
            offer_persuasion_key = ""
        adaptive_stage_label_ar = (
            stage_label_ar(adaptive_stage_key) if adaptive_stage_key else ""
        )
        adaptive_path_ar = str(bh.get("recovery_adaptive_path_label_ar") or "").strip()
        adaptive_transition_ar = str(
            bh.get("recovery_last_transition_reason_ar") or ""
        ).strip()
        try:
            adaptive_turns = int(bh.get("recovery_adaptive_turn_count") or 0)
        except (TypeError, ValueError):
            adaptive_turns = 0
        checkout_push_mode = (
            adaptive_stage_key == "checkout_ready"
            or adaptive_stage_key == "returned_checkout"
            or offer_strategy_key in ("checkout_push", "completion_assistance")
        )
        return_intel_completion_opportunity = (
            adaptive_stage_key == "returned_checkout"
            or offer_strategy_key == "completion_assistance"
        )
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
        "normal_recovery_suggested_strategy_ar": suggested_strategy_ar,
        "normal_recovery_suggestion_reason_ar": suggestion_reason_ar,
        "normal_recovery_suggestion_ux_badge_ar": suggestion_ux_badge_ar,
        "normal_recovery_optional_offer_type": optional_offer_type,
        "normal_recovery_checkout_cta_mode": checkout_cta_mode,
        "normal_recovery_offer_decision_type_ar": offer_decision_type_ar,
        "normal_recovery_offer_confidence_ar": offer_confidence_ar,
        "normal_recovery_offer_decision_rationale_ar": offer_rationale_ar,
        "normal_recovery_offer_persuasion_ar": offer_persuasion_ar,
        "normal_recovery_offer_flag_discount": offer_flag_discount,
        "normal_recovery_offer_flag_free_shipping": offer_flag_shipping,
        "normal_recovery_offer_flag_alternative": offer_flag_alternative,
        "normal_recovery_offer_strategy_key": offer_strategy_key,
        "normal_recovery_offer_persuasion_key": offer_persuasion_key,
        "normal_recovery_adaptive_stage_key": adaptive_stage_key,
        "normal_recovery_adaptive_stage_ar": adaptive_stage_label_ar,
        "normal_recovery_adaptive_path_ar": adaptive_path_ar,
        "normal_recovery_adaptive_transition_ar": adaptive_transition_ar,
        "normal_recovery_adaptive_turn_count": adaptive_turns,
        "normal_recovery_checkout_push_mode": checkout_push_mode,
        "normal_recovery_cooldown_panel": cooldown_panel,
        "normal_recovery_cooldown_state_key": cooldown_state_key,
        "normal_recovery_cooldown_state_ar": cooldown_state_ar,
        "normal_recovery_silence_duration_display_ar": silence_duration_display_ar,
        "normal_recovery_silence_duration_minutes": silence_duration_minutes_val,
        "normal_recovery_activity_level_ar": activity_level_ar,
        "normal_recovery_followup_recommended": followup_recommended,
        "normal_recovery_followup_recommendation_ar": followup_recommendation_ar,
        "normal_recovery_followup_type_key": followup_type_key,
        "normal_recovery_followup_type_ar": followup_type_ar,
        "normal_recovery_cooldown_context_ar": cooldown_context_ar,
        "normal_recovery_cooldown_pressure_note_ar": pressure_note_ar,
        "normal_recovery_return_intel_panel": return_intel_panel,
        "normal_recovery_customer_returned_to_site_track": customer_returned_to_site_track,
        "normal_recovery_return_timestamp_display_ar": recovery_return_timestamp_ar,
        "normal_recovery_returned_product_page": recovery_returned_product_page_flag,
        "normal_recovery_returned_checkout_page": recovery_returned_checkout_page_flag,
        "normal_recovery_return_context_key": normal_recovery_return_context_key,
        "normal_recovery_site_return_count": recovery_site_return_count_val,
        "normal_recovery_return_intel_pressure_note_ar": return_intel_pressure_note_ar,
        "normal_recovery_return_completion_opportunity": return_intel_completion_opportunity,
        "normal_recovery_continuation_summary_ar": normal_recovery_continuation_summary_ar,
        "normal_recovery_continuation_state_key": normal_recovery_continuation_state_key,
    }
