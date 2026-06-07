# -*- coding: utf-8 -*-
"""Safe timing guardrails for recovery template stages (dashboard policy layer)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from services.merchant_whatsapp_meta_policy_awareness_v1 import (
    TIMING_AUTO_ADJUST_MESSAGE_AR,
)
from services.store_reason_templates import normalize_delay_unit

EXECUTION_STAGE_1 = 1
EXECUTION_STAGE_2 = 2
EXECUTION_STAGE_3 = 3

GUARDRAIL_EVENT_TIMING_CLAMP = "timing_guardrail_clamp"

STAGE_GUARDRAIL_SPEC: Mapping[int, dict[str, Any]] = {
    EXECUTION_STAGE_1: {
        "merchant_configurable": True,
        "recommended_hours": None,
        "min_hours": None,
        "label_ar": "المرحلة الأولى — رسالة السبب",
    },
    EXECUTION_STAGE_2: {
        "merchant_configurable": True,
        "recommended_hours": 24.0,
        "min_hours": 6.0,
        "label_ar": "المرحلة الثانية — متابعة عامة",
    },
    EXECUTION_STAGE_3: {
        "merchant_configurable": True,
        "recommended_hours": 72.0,
        "min_hours": 24.0,
        "label_ar": "المرحلة الثالثة — متابعة أخيرة",
    },
}


@dataclass(frozen=True)
class TimingGuardrailResult:
    stage: int
    original_delay: float
    original_unit: str
    clamped_delay: float
    clamped_unit: str
    was_adjusted: bool
    recommended_hours: Optional[float]
    min_hours: Optional[float]
    policy_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "original_delay": self.original_delay,
            "original_unit": self.original_unit,
            "clamped_delay": self.clamped_delay,
            "clamped_unit": self.clamped_unit,
            "was_adjusted": self.was_adjusted,
            "recommended_hours": self.recommended_hours,
            "min_hours": self.min_hours,
            "policy_reason": self.policy_reason,
        }


def _normalize_guardrail_unit(raw: Any) -> str:
    u = normalize_delay_unit(raw)
    if u:
        return u
    s = str(raw or "").strip().lower()
    if s in ("day", "days", "d"):
        return "day"
    return "minute"


def delay_to_hours(delay: Any, unit: Any) -> float:
    try:
        val = float(delay)
    except (TypeError, ValueError):
        val = 1.0
    if val <= 0:
        val = 1.0
    u = _normalize_guardrail_unit(unit)
    if u == "hour":
        return val
    if u == "day":
        return val * 24.0
    return val / 60.0


def hours_to_persist_display(hours: float) -> tuple[float, str]:
    """Pick merchant-friendly unit after clamp."""
    h = max(0.0, float(hours))
    if h >= 24.0 and abs(h % 24.0) < 0.01:
        return h / 24.0, "day"
    if h >= 1.0 and abs(h - round(h)) < 0.01:
        return round(h), "hour"
    minutes = max(1, int(round(h * 60)))
    return float(minutes), "minute"


def recommended_timing_for_stage(stage: int) -> Optional[dict[str, Any]]:
    spec = STAGE_GUARDRAIL_SPEC.get(int(stage))
    if not spec:
        return None
    rec_h = spec.get("recommended_hours")
    if rec_h is None:
        return {
            "stage": stage,
            "merchant_configurable": True,
            "recommended_display": None,
            "min_hours": None,
            "label_ar": spec.get("label_ar"),
        }
    disp_val, disp_unit = hours_to_persist_display(float(rec_h))
    min_h = spec.get("min_hours")
    min_disp = None
    if min_h is not None:
        min_disp_val, min_disp_unit = hours_to_persist_display(float(min_h))
        min_disp = {"delay": min_disp_val, "unit": min_disp_unit}
    return {
        "stage": stage,
        "merchant_configurable": bool(spec.get("merchant_configurable")),
        "recommended_display": {"delay": disp_val, "unit": disp_unit},
        "recommended_hours": rec_h,
        "min_hours": min_h,
        "min_display": min_disp,
        "label_ar": spec.get("label_ar"),
    }


def clamp_stage_delay(stage: int, delay: Any, unit: Any) -> TimingGuardrailResult:
    """Enforce hard minimum for stages 2 and 3; stage 1 is pass-through."""
    try:
        st = int(stage)
    except (TypeError, ValueError):
        st = EXECUTION_STAGE_1
    spec = STAGE_GUARDRAIL_SPEC.get(st, STAGE_GUARDRAIL_SPEC[EXECUTION_STAGE_1])
    try:
        raw_delay = float(delay)
    except (TypeError, ValueError):
        raw_delay = 1.0
    raw_unit = _normalize_guardrail_unit(unit)
    rec_h = spec.get("recommended_hours")
    min_h = spec.get("min_hours")

    if min_h is None:
        return TimingGuardrailResult(
            stage=st,
            original_delay=raw_delay,
            original_unit=raw_unit,
            clamped_delay=raw_delay,
            clamped_unit=raw_unit,
            was_adjusted=False,
            recommended_hours=rec_h,
            min_hours=min_h,
        )

    hours = delay_to_hours(raw_delay, raw_unit)
    if hours >= float(min_h):
        return TimingGuardrailResult(
            stage=st,
            original_delay=raw_delay,
            original_unit=raw_unit,
            clamped_delay=raw_delay,
            clamped_unit=raw_unit,
            was_adjusted=False,
            recommended_hours=rec_h,
            min_hours=min_h,
        )

    clamped_delay, clamped_unit = hours_to_persist_display(float(min_h))
    return TimingGuardrailResult(
        stage=st,
        original_delay=raw_delay,
        original_unit=raw_unit,
        clamped_delay=clamped_delay,
        clamped_unit=clamped_unit,
        was_adjusted=True,
        recommended_hours=rec_h,
        min_hours=min_h,
        policy_reason=f"below_min_{min_h}h",
    )


def apply_timing_guardrails_to_reason_templates_incoming(
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Clamp stage 2/3 delays in incoming reason_templates body (dashboard save only).
    Does not alter runtime send path directly.
    """
    if not isinstance(incoming, dict):
        return incoming, {"adjustments": [], "adjusted": False}

    out = dict(incoming)
    adjustments: list[dict[str, Any]] = []

    for tag, entry in incoming.items():
        if not isinstance(entry, dict):
            continue
        ent = dict(entry)
        msgs = ent.get("messages")
        if not isinstance(msgs, list):
            continue
        new_msgs: list[Any] = []
        for i, slot in enumerate(msgs[:3]):
            if not isinstance(slot, dict):
                new_msgs.append(slot)
                continue
            stage = i + 1
            result = clamp_stage_delay(
                stage, slot.get("delay"), slot.get("unit")
            )
            slot_out = dict(slot)
            if result.was_adjusted:
                slot_out["delay"] = result.clamped_delay
                slot_out["unit"] = result.clamped_unit
                adjustments.append(
                    {
                        **result.to_dict(),
                        "reason_tag": str(tag),
                        "event": GUARDRAIL_EVENT_TIMING_CLAMP,
                    }
                )
            new_msgs.append(slot_out)
        ent["messages"] = new_msgs
        out[str(tag)] = ent

    adjusted = bool(adjustments)
    return out, {
        "adjusted": adjusted,
        "adjustments": adjustments,
        "timing_guardrail_message_ar": (
            TIMING_AUTO_ADJUST_MESSAGE_AR if adjusted else ""
        ),
        "recommended_timing_by_stage": [
            recommended_timing_for_stage(s)
            for s in (EXECUTION_STAGE_1, EXECUTION_STAGE_2, EXECUTION_STAGE_3)
        ],
    }


def timing_guardrails_for_api() -> dict[str, Any]:
    return {
        "architecture_only": True,
        "runtime_send_unchanged": True,
        "stages": [
            recommended_timing_for_stage(s)
            for s in (EXECUTION_STAGE_1, EXECUTION_STAGE_2, EXECUTION_STAGE_3)
        ],
        "auto_adjust_message_ar": TIMING_AUTO_ADJUST_MESSAGE_AR,
    }
