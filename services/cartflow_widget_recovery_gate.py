# -*- coding: utf-8 -*-
"""إظهار واجهة استعادة الودجيت للعملاء فقط (‎cartflow_widget_*‎) — بدون تأثير على تتبع السلة أو VIP."""
from __future__ import annotations

from typing import Any, Dict, Optional

_VALID_UNITS = frozenset({"minutes", "hours", "days"})


def apply_cartflow_widget_recovery_gate_from_body(row: Any, body: Dict[str, Any]) -> None:
    if "cartflow_widget_enabled" in body:
        row.cartflow_widget_enabled = bool(body.get("cartflow_widget_enabled"))
    if "cartflow_widget_delay_value" in body:
        raw = body.get("cartflow_widget_delay_value")
        try:
            v = int(raw)
        except (TypeError, ValueError):
            v = 0
        row.cartflow_widget_delay_value = max(0, v)
    if "cartflow_widget_delay_unit" in body:
        u = (
            str(body.get("cartflow_widget_delay_unit") or "")
            .strip()
            .lower()
        )
        if u in _VALID_UNITS:
            row.cartflow_widget_delay_unit = u


def cartflow_widget_recovery_gate_fields_for_api(
    row: Optional[Any],
) -> Dict[str, Any]:
    if row is None:
        return {
            "cartflow_widget_enabled": True,
            "cartflow_widget_delay_value": 0,
            "cartflow_widget_delay_unit": "minutes",
        }
    en = getattr(row, "cartflow_widget_enabled", True)
    try:
        enabled = bool(en)
    except (TypeError, ValueError):
        enabled = True
    raw_d = getattr(row, "cartflow_widget_delay_value", None)
    try:
        delay_v = max(0, int(raw_d)) if raw_d is not None else 0
    except (TypeError, ValueError):
        delay_v = 0
    du_raw = getattr(row, "cartflow_widget_delay_unit", None)
    du_s = (
        str(du_raw).strip().lower()
        if isinstance(du_raw, str) and du_raw.strip()
        else ""
    )
    du_out = du_s if du_s in _VALID_UNITS else "minutes"
    return {
        "cartflow_widget_enabled": enabled,
        "cartflow_widget_delay_value": delay_v,
        "cartflow_widget_delay_unit": du_out,
    }
