# -*- coding: utf-8 -*-
"""Timing guardrail merchant-facing copy — display only (no rule changes)."""
from __future__ import annotations

from typing import Any, Optional

from services.merchant_whatsapp_meta_policy_awareness_v1 import (
    TIMING_POLICY_EXPLANATION_AR,
)
from services.merchant_whatsapp_timing_guardrails_v1 import (
    EXECUTION_STAGE_1,
    EXECUTION_STAGE_2,
    EXECUTION_STAGE_3,
    TimingGuardrailResult,
    recommended_timing_for_stage,
)

_STAGE_DENIAL_AR: dict[int, str] = {
    EXECUTION_STAGE_2: "لا يمكن ضبط المرحلة الثانية بأقل من {min}.",
    EXECUTION_STAGE_3: "لا يمكن ضبط المرحلة الثالثة بأقل من {min}.",
}


def _unit_label_ar(unit: str, value: float) -> str:
    u = (unit or "minute").strip().lower()
    v = float(value)
    if u == "day":
        return "يوم" if abs(v - 1.0) < 0.01 else "أيام"
    if u == "hour":
        if abs(v - 1.0) < 0.01:
            return "ساعة"
        if abs(v - 2.0) < 0.01:
            return "ساعتين"
        if 3 <= v <= 10:
            return "ساعات"
        return "ساعة"
    if abs(v - 1.0) < 0.01:
        return "دقيقة"
    if abs(v - 2.0) < 0.01:
        return "دقيقتين"
    if 3 <= v <= 10:
        return "دقائق"
    return "دقيقة"


def format_delay_display_ar(delay: Any, unit: Any) -> str:
    try:
        val = float(delay)
    except (TypeError, ValueError):
        val = 1.0
    if val <= 0:
        val = 1.0
    u = (unit or "minute").strip().lower()
    if u in ("days", "d"):
        u = "day"
    if u in ("hours", "h", "hr"):
        u = "hour"
    if u in ("minutes", "min"):
        u = "minute"
    if u not in ("minute", "hour", "day"):
        u = "minute"
    n = int(val) if abs(val - round(val)) < 0.01 else val
    if isinstance(n, float) and n != int(n):
        n = round(n, 1)
    return f"{n} {_unit_label_ar(u, float(val))}"


def format_policy_hours_display_ar(hours: Optional[float]) -> str:
    """Merchant-facing guardrail copy — always in hours (not days)."""
    if hours is None:
        return "—"
    h = float(hours)
    if abs(h - 6.0) < 0.01:
        return "6 ساعات"
    if abs(h - 24.0) < 0.01:
        return "24 ساعة"
    if abs(h - 72.0) < 0.01:
        return "72 ساعة"
    n = int(h) if abs(h - round(h)) < 0.01 else h
    if abs(h - 1.0) < 0.01:
        return "1 ساعة"
    if abs(h - 2.0) < 0.01:
        return "2 ساعتين"
    if 3 <= h <= 10:
        return f"{n} ساعات"
    return f"{n} ساعة"


def _display_from_hours(hours: Optional[float]) -> str:
    if hours is None:
        return "—"
    return format_policy_hours_display_ar(float(hours))


def stage_timing_panel_fields(
    stage: int,
    *,
    current_delay: Any = None,
    current_unit: Any = None,
) -> dict[str, Any]:
    """Recommended / minimum / current saved — merchant-visible timing truth."""
    spec = recommended_timing_for_stage(stage) or {}
    rec_h = spec.get("recommended_hours")
    min_h = spec.get("min_hours")
    rec_disp = spec.get("recommended_display")
    min_disp = spec.get("min_display")

    if rec_h is not None:
        recommended_ar = format_policy_hours_display_ar(float(rec_h))
    elif rec_disp and isinstance(rec_disp, dict):
        recommended_ar = format_delay_display_ar(
            rec_disp.get("delay"), rec_disp.get("unit")
        )
    else:
        recommended_ar = "—"

    if min_h is not None:
        minimum_ar = format_policy_hours_display_ar(float(min_h))
    elif min_disp and isinstance(min_disp, dict):
        minimum_ar = format_delay_display_ar(
            min_disp.get("delay"), min_disp.get("unit")
        )
    else:
        minimum_ar = "بدون حد أدنى"

    if current_delay is not None and str(current_delay).strip() != "":
        current_ar = format_delay_display_ar(current_delay, current_unit)
    else:
        current_ar = "—"

    return {
        "stage": stage,
        "recommended_timing_ar": recommended_ar,
        "minimum_allowed_timing_ar": minimum_ar,
        "current_saved_timing_ar": current_ar,
        "label_ar": spec.get("label_ar") or f"المرحلة {stage}",
    }


def enrich_timing_adjustment_for_merchant(result: TimingGuardrailResult) -> dict[str, Any]:
    """Explicit entered → policy limit → saved value copy."""
    base = result.to_dict()
    entered_ar = format_delay_display_ar(
        result.original_delay, result.original_unit
    )
    min_ar = format_policy_hours_display_ar(result.min_hours)
    rec_ar = format_policy_hours_display_ar(result.recommended_hours)
    if result.was_adjusted and result.min_hours is not None:
        saved_ar = format_policy_hours_display_ar(result.min_hours)
    else:
        saved_ar = format_delay_display_ar(
            result.clamped_delay, result.clamped_unit
        )

    denial_ar = ""
    saved_message_ar = ""
    if result.was_adjusted:
        tmpl = _STAGE_DENIAL_AR.get(result.stage, "لا يمكن ضبط هذه المرحلة بأقل من {min}.")
        denial_ar = tmpl.format(min=min_ar)
        saved_message_ar = f"تم حفظ التوقيت على {saved_ar}."

    return {
        **base,
        "entered_timing_ar": entered_ar,
        "saved_timing_ar": saved_ar,
        "minimum_allowed_timing_ar": min_ar,
        "recommended_timing_ar": rec_ar,
        "denial_message_ar": denial_ar,
        "saved_message_ar": saved_message_ar,
        "feedback_lines_ar": [x for x in (denial_ar, saved_message_ar) if x],
    }


def build_timing_guardrail_save_feedback(
    adjustments: list[dict[str, Any]],
) -> dict[str, Any]:
    if not adjustments:
        return {
            "adjusted": False,
            "feedback_lines_ar": [],
            "timing_guardrail_message_ar": "",
        }
    lines: list[str] = []
    for adj in adjustments:
        for line in adj.get("feedback_lines_ar") or []:
            if line and line not in lines:
                lines.append(line)
    return {
        "adjusted": True,
        "adjustments": adjustments,
        "feedback_lines_ar": lines,
        "timing_guardrail_message_ar": "\n".join(lines),
    }


def timing_guardrails_ux_for_api() -> dict[str, Any]:
    return {
        "policy_explanation_ar": TIMING_POLICY_EXPLANATION_AR,
        "stage_panels": {
            str(s): stage_timing_panel_fields(s)
            for s in (EXECUTION_STAGE_1, EXECUTION_STAGE_2, EXECUTION_STAGE_3)
        },
    }
