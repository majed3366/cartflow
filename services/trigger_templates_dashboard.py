# -*- coding: utf-8 -*-
"""
حِزمة JSON للوحة «قوالب حسب سبب التردد» — قراءة خفيفة من ‎Store.reason_templates_json‎ فقط.

لا يغيِّر مسار الإرسال؛ القراءة/العرض لواجهة التاجر فقط.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.recovery_template_defaults import guided_defaults_for_api
from services.store_reason_templates import (
    normalize_delay_unit,
    parse_reason_templates_column,
)

TRIGGER_TEMPLATE_PAGE_KEYS: tuple[str, ...] = (
    "price",
    "quality",
    "shipping",
    "delivery",
    "warranty",
    "other",
)

_LABEL_AR: Dict[str, str] = {
    "price": "السعر",
    "quality": "الجودة",
    "shipping": "الشحن",
    "delivery": "مدة التوصيل",
    "warranty": "الضمان",
    "other": "سبب آخر",
}


def build_trigger_templates_get_payload(store_row: Optional[Any]) -> Dict[str, Any]:
    """حقل واحد من ‎Store‎ — استدعاء موحّد دون استعلامات إضافية."""
    parsed = parse_reason_templates_column(
        getattr(store_row, "reason_templates_json", None)
        if store_row is not None
        else None
    )
    reason_rows: List[Dict[str, Any]] = []
    for key in TRIGGER_TEMPLATE_PAGE_KEYS:
        raw_ent = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
        ent = dict(raw_ent)
        enabled = bool(ent.get("enabled", True))
        mc_raw = ent.get("message_count", 1)
        try:
            mc = int(mc_raw)
        except (TypeError, ValueError):
            mc = 1
        mc = max(1, min(3, mc))

        msgs_in = list(ent.get("messages") or [])
        first: Dict[str, Any] = {}
        if msgs_in and isinstance(msgs_in[0], dict):
            first = dict(msgs_in[0])
        delay_v_raw = first.get("delay", 1.0)
        try:
            delay_v = float(delay_v_raw)
        except (TypeError, ValueError):
            delay_v = 1.0
        if delay_v <= 0:
            delay_v = 1.0

        nu = normalize_delay_unit(first.get("unit"))
        unit_eff = nu if nu is not None else "minute"

        text0 = str(first.get("text") or "").strip()
        fallback_msg = str(ent.get("message") or "").strip()
        message_one = fallback_msg if fallback_msg else text0

        reason_rows.append(
            {
                "key": key,
                "label_ar": _LABEL_AR.get(key, key),
                "enabled": enabled,
                "message": message_one,
                "delay_value": delay_v,
                "delay_unit": unit_eff,
                "message_count": mc,
                "messages": msgs_in[:3] if msgs_in else [],
            }
        )

    g_all = guided_defaults_for_api()
    guided_slice = {
        k: dict(g_all.get(k) or {}) for k in TRIGGER_TEMPLATE_PAGE_KEYS if k in g_all
    }
    return {
        "section_title_ar": "قوالب حسب سبب التردد",
        "section_subtitle_ar": "تحكم في رسالة الاسترجاع لكل سبب من أسباب التردد.",
        "reason_rows": reason_rows,
        "guided_defaults": guided_slice,
    }
