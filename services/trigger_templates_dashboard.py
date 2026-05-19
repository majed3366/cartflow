# -*- coding: utf-8 -*-
"""
حِزمة JSON للوحة «قوالب حسب سبب التردد» — قراءة خفيفة من ‎Store.reason_templates_json‎ فقط.

لا يغيِّر مسار الإرسال؛ القراءة/العرض لواجهة التاجر فقط.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.recovery_template_defaults import guided_defaults_for_api
from services.store_reason_templates import (
    normalize_delay_unit,
    parse_reason_templates_column,
)
from services.trigger_template_ui_defaults import (
    _coerce_messages_list,
    _persist_delay_for_api,
    enrich_reason_entry_for_dashboard,
    stage_default_delay_ui,
    stage_default_text,
)

_log = logging.getLogger(__name__)

_GUIDED_DEFAULTS_SLICE: Optional[Dict[str, Dict[str, str]]] = None

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


def _guided_defaults_slice() -> Dict[str, Dict[str, str]]:
    global _GUIDED_DEFAULTS_SLICE
    if _GUIDED_DEFAULTS_SLICE is None:
        g_all = guided_defaults_for_api()
        _GUIDED_DEFAULTS_SLICE = {
            k: dict(g_all.get(k) or {})
            for k in TRIGGER_TEMPLATE_PAGE_KEYS
            if k in g_all
        }
    return _GUIDED_DEFAULTS_SLICE


def _default_row_for_reason(key: str, message_count: int = 3) -> Dict[str, Any]:
    """صف افتراضي كامل عند غياب المتجر أو فشل الإثراء — للعرض فقط."""
    mc = max(1, min(3, int(message_count or 3)))
    msgs: List[Dict[str, Any]] = []
    for i in range(mc):
        val, unit = stage_default_delay_ui(key, i)
        delay_v, unit_v = _persist_delay_for_api(val, unit)
        msgs.append(
            {
                "delay": float(delay_v),
                "unit": str(unit_v),
                "text": stage_default_text(key, i),
            }
        )
    first = msgs[0] if msgs else {"delay": 60.0, "unit": "minute", "text": ""}
    return {
        "key": key,
        "label_ar": _LABEL_AR.get(key, key),
        "enabled": True,
        "message": str(first.get("text") or ""),
        "delay_value": float(first.get("delay", 60.0)),
        "delay_unit": str(first.get("unit") or "minute"),
        "message_count": mc,
        "messages": msgs,
    }


def build_fallback_trigger_templates_payload() -> Dict[str, Any]:
    """حمولة آمنة عند غياب ‎Store‎ أو تعذّر القراءة — لا تُرجع 500 للواجهة."""
    return {
        "section_title_ar": "قوالب حسب سبب التردد",
        "section_subtitle_ar": "تحكم في رسالة الاسترجاع لكل سبب من أسباب التردد.",
        "reason_rows": [_default_row_for_reason(k) for k in TRIGGER_TEMPLATE_PAGE_KEYS],
        "guided_defaults": _guided_defaults_slice(),
        "display_fallback": True,
    }


def _reason_row_from_enriched(key: str, ent: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(ent.get("enabled", True))
    mc_raw = ent.get("message_count", 1)
    try:
        mc = int(mc_raw)
    except (TypeError, ValueError):
        mc = 1
    mc = max(1, min(3, mc))

    msgs_in = _coerce_messages_list(ent.get("messages"))
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
    message_one = text0 if text0 else fallback_msg

    return {
        "key": key,
        "label_ar": _LABEL_AR.get(key, key),
        "enabled": enabled,
        "message": message_one,
        "delay_value": delay_v,
        "delay_unit": unit_eff,
        "message_count": mc,
        "messages": msgs_in[:3] if msgs_in else [],
    }


def build_reason_row_for_key(store_row: Optional[Any], key: str) -> Dict[str, Any]:
    """صف واحد بعد الحفظ — إثراء مفتاح واحد فقط."""
    if key not in TRIGGER_TEMPLATE_PAGE_KEYS:
        return _default_row_for_reason("price")
    if store_row is None:
        return _default_row_for_reason(key)
    try:
        parsed = parse_reason_templates_column(
            getattr(store_row, "reason_templates_json", None)
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("trigger_templates parse failed for %s: %s", key, exc)
        return _default_row_for_reason(key)
    raw_ent = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
    try:
        ent = enrich_reason_entry_for_dashboard(key, dict(raw_ent))
        return _reason_row_from_enriched(key, ent)
    except Exception as exc:  # noqa: BLE001
        _log.warning("trigger_templates enrich failed for %s: %s", key, exc)
        return _default_row_for_reason(key)


def build_trigger_templates_save_ack(
    *,
    saved_reason_keys: List[str],
    store_row: Optional[Any] = None,
) -> Dict[str, Any]:
    """استجابة خفيفة لـ POST — دون إعادة بناء الصفوف الستة."""
    keys = [k for k in saved_reason_keys if k in TRIGGER_TEMPLATE_PAGE_KEYS]
    patch_rows: List[Dict[str, Any]] = []
    if store_row is not None:
        for k in keys:
            patch_rows.append(build_reason_row_for_key(store_row, k))
    return {
        "ok": True,
        "save_ack": True,
        "saved_reason_keys": keys,
        "reason_rows": patch_rows,
    }


def build_trigger_templates_get_payload(store_row: Optional[Any]) -> Dict[str, Any]:
    """حقل واحد من ‎Store‎ — استدعاء موحّد؛ لا يُسقِط التحميل عند بيانات تالفة."""
    if store_row is None:
        return build_fallback_trigger_templates_payload()

    try:
        parsed = parse_reason_templates_column(
            getattr(store_row, "reason_templates_json", None)
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("trigger_templates parse failed: %s", exc)
        return build_fallback_trigger_templates_payload()

    reason_rows: List[Dict[str, Any]] = []
    for key in TRIGGER_TEMPLATE_PAGE_KEYS:
        raw_ent = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
        try:
            ent = enrich_reason_entry_for_dashboard(key, dict(raw_ent))
            reason_rows.append(_reason_row_from_enriched(key, ent))
        except Exception as exc:  # noqa: BLE001
            _log.warning("trigger_templates enrich failed for %s: %s", key, exc)
            reason_rows.append(_default_row_for_reason(key))

    if not reason_rows:
        return build_fallback_trigger_templates_payload()

    return {
        "section_title_ar": "قوالب حسب سبب التردد",
        "section_subtitle_ar": "تحكم في رسالة الاسترجاع لكل سبب من أسباب التردد.",
        "reason_rows": reason_rows,
        "guided_defaults": _guided_defaults_slice(),
    }
