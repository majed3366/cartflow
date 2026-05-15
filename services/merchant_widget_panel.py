# -*- coding: utf-8 -*-
"""
عرض ودمج إعدادات قسم الودجيت في لوحة التاجر — قراءة فقط + تجهيز حفظ آمن.
لا يغيّر منطق الاسترجاع أو الويدجت في المتجر؛ يمرّر الحقول نفسها لطبقات ‎Store‎ الموجودة.

---
# CartFlow Widget hesitation copy
# نص أسباب التردد المعروضة للعميل داخل الودجيت: كتالوج ثابت (لا تحرير من التاجر).
# Independent customer-facing widget text — do NOT derive from recovery ‎message‎.
# لا تُستخرج التسميات من قوالب الاسترجاع أو ‎widget_reason_label_ar‎ (البقاء في ‎reason_templates‎ اختياري فقط لتجاهله في الواجهة).
---
# Recovery Trigger Templates
# ‎reason_templates.message‎ / ‎messages‎ — قوالب استرجاع بعد ترك السلة؛ مستقلة عن تسميات الودجيت.
# Future hook: Product Intelligence / Offer Control (لا تغيير هنا الآن).
# Do NOT surface recovery WhatsApp bodies as hesitation chip headings.
---
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from services.cartflow_widget_recovery_gate import cartflow_widget_recovery_gate_fields_for_api
from services.cartflow_widget_trigger_settings import widget_trigger_config_from_store_row
from services.store_reason_templates import parse_reason_templates_column
from services.store_template_control import exit_intent_template_fields_for_api
from services.store_widget_customization import widget_customization_fields_for_api

# ترتيب وسمات أسباب التردد المعروضة في الودجيت — لا تظهر حقول تنصيط للأسماء؛ التفعيل والترتيب فقط.
_WIDGET_FIXED_HESITATION_LABEL_AR: Dict[str, str] = {
    "price": "السعر",
    "quality": "الجودة",
    "shipping": "الشحن",
    "delivery": "مدة التوصيل",
    "warranty": "الضمان",
    "other": "سبب آخر",
}
_REASON_PANEL_KEYS_ORDER: Tuple[str, ...] = tuple(_WIDGET_FIXED_HESITATION_LABEL_AR.keys())
_MERCHANT_PANEL_REASON_KEYS = frozenset(_REASON_PANEL_KEYS_ORDER)


def _fixed_widget_hesitation_label_ar(key: str) -> str:
    k = str(key or "").strip().lower()
    return _WIDGET_FIXED_HESITATION_LABEL_AR.get(k, "سبب آخر")


def merchant_reason_panel_rows_for_widget_settings(
    row: Optional[Any],
    *,
    trigger_cfg: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """صفوف أسباب للواجهة التجارية — ترتيب من الإعدادات مع تسميات كتالوج ثابتة."""
    rt = parse_reason_templates_column(getattr(row, "reason_templates_json", None) if row else None)
    cfg = trigger_cfg if isinstance(trigger_cfg, dict) else widget_trigger_config_from_store_row(row)
    order_raw = cfg.get("reason_display_order")
    order: List[str] = []
    if isinstance(order_raw, list):
        for x in order_raw:
            k = str(x).strip().lower()
            if k in _MERCHANT_PANEL_REASON_KEYS and k not in order:
                order.append(k)
    for k in _REASON_PANEL_KEYS_ORDER:
        if k not in order:
            order.append(k)
    out: List[Dict[str, Any]] = []
    for idx, key in enumerate(order):
        if key not in _MERCHANT_PANEL_REASON_KEYS:
            continue
        ent = rt.get(key) if isinstance(rt.get(key), dict) else {}
        enabled = bool(ent.get("enabled", True)) if isinstance(ent, dict) else True
        out.append(
            {
                "key": key,
                "sort_index": idx,
                "label_ar": _fixed_widget_hesitation_label_ar(key),
                "enabled": enabled,
            }
        )
    return out


def merchant_visible_reason_keys_for_runtime(row: Optional[Any]) -> List[str]:
    """مفاتيح الأسباب المفعّلة فقط — نفس منطق صفوف اللوحة (للتحقق من ‎public-config‎ / الودجت)."""
    rows = merchant_reason_panel_rows_for_widget_settings(row)
    return [str(r["key"]) for r in rows if r.get("enabled") is True]


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
