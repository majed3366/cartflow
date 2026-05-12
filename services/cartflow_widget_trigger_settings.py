# -*- coding: utf-8 -*-
"""إعدادات تحكم مشغّل ظهور الودجيت (طبقة إعدادات فقط — لا تغيّر منطق الخروج/التردد الحالي في الويدجت)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

DEFAULT_WIDGET_TRIGGER_CONFIG: Dict[str, Any] = {
    "exit_intent_enabled": True,
    "exit_intent_sensitivity": "medium",
    "exit_intent_delay_seconds": 0,
    "exit_intent_frequency": "per_session",
    "hesitation_trigger_enabled": True,
    "hesitation_after_seconds": 20,
    "hesitation_condition": "after_cart_add",
    "visibility_widget_globally_enabled": True,
    "visibility_temporarily_disabled": False,
    "visibility_page_scope": "all",
    # حقول إضافية للوحة التاجر — يستهلكها الويدجت لاحقاً عند التفعيل؛ آمنة كقيم افتراضية.
    "widget_brand_line_ar": "",
    "widget_phone_capture_mode": "after_reason",
    "suppress_after_widget_dismiss": True,
    "suppress_after_purchase": True,
    "suppress_when_checkout_started": True,
    "reason_display_order": [
        "price",
        "shipping",
        "delivery",
        "quality",
        "warranty",
        "thinking",
        "other",
    ],
}

_SENS = frozenset({"low", "medium", "high"})
_DELAY = frozenset({0, 3, 5})
_FREQ = frozenset({"per_session", "per_24h", "no_rapid_repeat"})
_HES_SEC = frozenset({5, 10, 15, 20, 30, 45, 60, 90, 120})
_HES_COND = frozenset(
    {"after_cart_add", "repeated_view", "inactivity", "cart_interaction"}
)
_SCOPE = frozenset({"product", "cart", "all"})
_PHONE_CAPTURE = frozenset({"after_reason", "immediate", "none"})
_REASON_ORDER_KEYS = frozenset(
    {"price", "shipping", "delivery", "quality", "warranty", "thinking", "other"}
)
_DEFAULT_REASON_ORDER: List[str] = list(
    DEFAULT_WIDGET_TRIGGER_CONFIG["reason_display_order"]
)


def _boolish(v: Any, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off", ""):
            return False
    return default


def _int_choice(v: Any, allowed: set[int], default: int) -> int:
    try:
        i = int(v)
    except (TypeError, ValueError):
        return default
    return i if i in allowed else default


def _str_choice(v: Any, allowed: frozenset[str], default: str) -> str:
    if not isinstance(v, str):
        return default
    s = v.strip().lower()
    return s if s in allowed else default


def _normalize_brand_line(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s[:120] if s else ""


def _normalize_reason_display_order(raw: Any) -> List[str]:
    out: List[str] = []
    if isinstance(raw, list):
        for x in raw:
            k = str(x).strip().lower()
            if k in _REASON_ORDER_KEYS and k not in out:
                out.append(k)
    for k in _DEFAULT_REASON_ORDER:
        if k not in out:
            out.append(k)
    return out[: len(_DEFAULT_REASON_ORDER)]


def normalize_widget_trigger_config(raw: Any) -> Dict[str, Any]:
    out = dict(DEFAULT_WIDGET_TRIGGER_CONFIG)
    if not isinstance(raw, dict):
        return out
    out["exit_intent_enabled"] = _boolish(
        raw.get("exit_intent_enabled"), bool(out["exit_intent_enabled"])
    )
    out["exit_intent_sensitivity"] = _str_choice(
        raw.get("exit_intent_sensitivity"),
        _SENS,
        str(out["exit_intent_sensitivity"]),
    )
    out["exit_intent_delay_seconds"] = _int_choice(
        raw.get("exit_intent_delay_seconds"), _DELAY, int(out["exit_intent_delay_seconds"])
    )
    out["exit_intent_frequency"] = _str_choice(
        raw.get("exit_intent_frequency"),
        _FREQ,
        str(out["exit_intent_frequency"]),
    )
    out["hesitation_trigger_enabled"] = _boolish(
        raw.get("hesitation_trigger_enabled"),
        bool(out["hesitation_trigger_enabled"]),
    )
    out["hesitation_after_seconds"] = _int_choice(
        raw.get("hesitation_after_seconds"),
        _HES_SEC,
        int(out["hesitation_after_seconds"]),
    )
    out["hesitation_condition"] = _str_choice(
        raw.get("hesitation_condition"),
        _HES_COND,
        str(out["hesitation_condition"]),
    )
    out["visibility_widget_globally_enabled"] = _boolish(
        raw.get("visibility_widget_globally_enabled"),
        bool(out["visibility_widget_globally_enabled"]),
    )
    out["visibility_temporarily_disabled"] = _boolish(
        raw.get("visibility_temporarily_disabled"),
        bool(out["visibility_temporarily_disabled"]),
    )
    out["visibility_page_scope"] = _str_choice(
        raw.get("visibility_page_scope"),
        _SCOPE,
        str(out["visibility_page_scope"]),
    )
    out["widget_brand_line_ar"] = _normalize_brand_line(
        raw.get("widget_brand_line_ar", out.get("widget_brand_line_ar"))
    )
    out["widget_phone_capture_mode"] = _str_choice(
        raw.get("widget_phone_capture_mode"),
        _PHONE_CAPTURE,
        str(out["widget_phone_capture_mode"]),
    )
    out["suppress_after_widget_dismiss"] = _boolish(
        raw.get("suppress_after_widget_dismiss"),
        bool(out["suppress_after_widget_dismiss"]),
    )
    out["suppress_after_purchase"] = _boolish(
        raw.get("suppress_after_purchase"),
        bool(out["suppress_after_purchase"]),
    )
    out["suppress_when_checkout_started"] = _boolish(
        raw.get("suppress_when_checkout_started"),
        bool(out["suppress_when_checkout_started"]),
    )
    out["reason_display_order"] = _normalize_reason_display_order(
        raw.get("reason_display_order", out.get("reason_display_order"))
    )
    return out


def widget_trigger_config_from_store_row(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "cf_widget_trigger_settings_json", None) if row is not None else None
    if not isinstance(raw, str) or not raw.strip():
        return dict(DEFAULT_WIDGET_TRIGGER_CONFIG)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(DEFAULT_WIDGET_TRIGGER_CONFIG)
    return normalize_widget_trigger_config(data)


def merge_widget_trigger_config_from_body(
    row: Optional[Any], body: Dict[str, Any]
) -> Dict[str, Any]:
    base = widget_trigger_config_from_store_row(row)
    patch = body.get("widget_trigger_config")
    if not isinstance(patch, dict):
        return base
    merged = dict(base)
    merged.update(patch)
    return normalize_widget_trigger_config(merged)


def apply_widget_trigger_settings_from_body(row: Any, body: Dict[str, Any]) -> None:
    cfg = body.get("widget_trigger_config")
    if not isinstance(cfg, dict):
        return
    normalized = normalize_widget_trigger_config(cfg)
    row.cf_widget_trigger_settings_json = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":")
    )


def widget_trigger_config_for_api(row: Optional[Any]) -> Dict[str, Any]:
    return {"widget_trigger_config": widget_trigger_config_from_store_row(row)}
