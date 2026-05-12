# -*- coding: utf-8 -*-
"""
عرض ودمج إعدادات قسم الودجيت في لوحة التاجر — قراءة فقط + تجهيز حفظ آمن.
لا يغيّر منطق الاسترجاع أو الويدجت في المتجر؛ يمرّر الحقول نفسها لطبقات ‎Store‎ الموجودة.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from services.cartflow_widget_recovery_gate import cartflow_widget_recovery_gate_fields_for_api
from services.cartflow_widget_trigger_settings import widget_trigger_config_from_store_row
from services.store_reason_templates import parse_reason_templates_column
from services.store_template_control import exit_intent_template_fields_for_api
from services.store_widget_customization import widget_customization_fields_for_api

# ترتيب العرض الافتراضي — المفتاح الداخلي لا يُعرض للتاجر في الواجهة النصية.
_REASON_PANEL_DEF: Tuple[Tuple[str, str], ...] = (
    ("price", "السعر"),
    ("shipping", "الشحن"),
    ("delivery", "التوصيل"),
    ("quality", "الجودة"),
    ("warranty", "الضمان"),
    ("thinking", "يفكر في القرار"),
    ("other", "أخرى"),
)

_REASON_INTERNAL_KEYS = frozenset(k for k, _ in _REASON_PANEL_DEF)


def _default_label_for_reason_key(key: str) -> str:
    for k, lab in _REASON_PANEL_DEF:
        if k == key:
            return lab
    return "أخرى"


def _coerce_customer_label(raw_msg: str, key: str) -> str:
    s = (raw_msg or "").strip()
    if not s:
        return _default_label_for_reason_key(key)
    if len(s) > 80:
        return s[:77] + "…"
    return s


def merchant_reason_panel_rows_for_widget_settings(
    row: Optional[Any],
    *,
    trigger_cfg: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """صفوف أسباب للواجهة التجارية — ترتيب من الإعدادات مع تسمية من القالب أو الافتراضي."""
    rt = parse_reason_templates_column(getattr(row, "reason_templates_json", None) if row else None)
    cfg = trigger_cfg if isinstance(trigger_cfg, dict) else widget_trigger_config_from_store_row(row)
    order_raw = cfg.get("reason_display_order")
    order: List[str] = []
    if isinstance(order_raw, list):
        for x in order_raw:
            k = str(x).strip().lower()
            if k in _REASON_INTERNAL_KEYS and k not in order:
                order.append(k)
    for k, _ in _REASON_PANEL_DEF:
        if k not in order:
            order.append(k)
    out: List[Dict[str, Any]] = []
    for idx, key in enumerate(order):
        if key not in _REASON_INTERNAL_KEYS:
            continue
        ent = rt.get(key) if isinstance(rt.get(key), dict) else {}
        enabled = bool(ent.get("enabled", True)) if isinstance(ent, dict) else True
        msg = ""
        if isinstance(ent, dict):
            msg = str(ent.get("message") or "").strip()
        out.append(
            {
                "key": key,
                "sort_index": idx,
                "label_ar": _coerce_customer_label(msg, key),
                "enabled": enabled,
            }
        )
    return out


def merchant_widget_panel_bundle(row: Optional[Any]) -> Dict[str, Any]:
    """حزمة جاهزة للقالب ولـ ‎JSON‎ التهيئة في المتصفح."""
    wtc = widget_trigger_config_from_store_row(row)
    wc = widget_customization_fields_for_api(row)
    gate = cartflow_widget_recovery_gate_fields_for_api(row)
    exit_tpl = exit_intent_template_fields_for_api(row)
    reason_rows = merchant_reason_panel_rows_for_widget_settings(row, trigger_cfg=wtc)
    return {
        "trigger": dict(wtc),
        "widget_name": wc.get("widget_name") or "مساعد المتجر",
        "widget_primary_color": wc.get("widget_primary_color") or "#6C5CE7",
        "widget_style": wc.get("widget_style") or "modern",
        "cartflow_widget_enabled": bool(gate.get("cartflow_widget_enabled", True)),
        "cartflow_widget_delay_value": int(gate.get("cartflow_widget_delay_value") or 0),
        "cartflow_widget_delay_unit": str(gate.get("cartflow_widget_delay_unit") or "minutes"),
        "exit_intent_template_mode": exit_tpl.get("exit_intent_template_mode") or "preset",
        "exit_intent_template_tone": exit_tpl.get("exit_intent_template_tone") or "friendly",
        "exit_intent_custom_text": exit_tpl.get("exit_intent_custom_text") or "",
        "reason_rows": reason_rows,
    }


def merchant_widget_bootstrap_json(row: Optional[Any]) -> str:
    bundle = merchant_widget_panel_bundle(row)
    return json.dumps(bundle, ensure_ascii=False)
