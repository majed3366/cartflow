# -*- coding: utf-8 -*-
"""
Recovery timing presentation — one authoritative model: configured stages.

Global summary is a derived min–max of enabled reasons' first-message delays.
Selected stage remains an independent, scoped label.
No independent hardcoded 30m–3h clock.
"""
from __future__ import annotations

from typing import Iterable


def delay_seconds(value: float, unit: str) -> float | None:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if val < 0:
        return None
    u = str(unit or "minute").strip().lower()
    if u in ("day", "days"):
        return val * 86400
    if u in ("hour", "hours"):
        return val * 3600
    return val * 60


def format_delay_ar(seconds: float) -> str:
    s = int(round(float(seconds)))
    if s % 86400 == 0:
        n = s // 86400
        return f"{n} يوم" if n != 1 else "يوم"
    if s % 3600 == 0:
        n = s // 3600
        return "ساعة" if n == 1 else f"{n} ساعات"
    n = s // 60 if s % 60 == 0 else int(round(s / 60))
    return f"{n} دقيقة"


def first_message_delays_seconds(reason_rows: Iterable[dict]) -> list[float]:
    """Enabled reasons only — first scheduled send per reason."""
    out: list[float] = []
    for row in reason_rows:
        if not isinstance(row, dict) or row.get("enabled") is False:
            continue
        msgs = row.get("messages") if isinstance(row.get("messages"), list) else []
        m0 = msgs[0] if msgs and isinstance(msgs[0], dict) else None
        if m0 and m0.get("delay") is not None:
            sec = delay_seconds(m0.get("delay"), m0.get("unit") or row.get("delay_unit") or "minute")
        elif row.get("delay_value") is not None:
            sec = delay_seconds(row.get("delay_value"), row.get("delay_unit") or "minute")
        else:
            continue
        if sec is not None:
            out.append(sec)
    return out


def global_send_range_ar(seconds: Iterable[float]) -> str:
    vals = sorted(float(s) for s in seconds)
    if not vals:
        return "حسب كل سبب"
    lo, hi = vals[0], vals[-1]
    if lo == hi:
        return f"من {format_delay_ar(lo)} بحسب السبب والمرحلة"
    return f"من {format_delay_ar(lo)} إلى {format_delay_ar(hi)} بحسب السبب والمرحلة"


def selected_stage_timing_ar(stage_index: int, value: float, unit: str) -> str:
    n = max(1, int(stage_index) + 1)
    try:
        val = float(value)
    except (TypeError, ValueError):
        val = 0.0
    val_s = str(int(val)) if val == int(val) else str(val)
    u = str(unit or "minute").strip().lower()
    if u in ("day", "days"):
        unit_ar = "يوم"
    elif u in ("hour", "hours"):
        unit_ar = "ساعة" if val == 1 else "ساعات"
    else:
        unit_ar = "دقيقة"
    return f"الرسالة {n} لهذا السبب: بعد {val_s} {unit_ar} من ترك السلة"


__all__ = [
    "delay_seconds",
    "first_message_delays_seconds",
    "format_delay_ar",
    "global_send_range_ar",
    "selected_stage_timing_ar",
]
