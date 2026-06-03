# -*- coding: utf-8 -*-
"""تخصيص مظهر الودجيت (اسم / لون / شكل) على ‎Store‎ — تحديث جزئي عبر لوحة الاسترجاع."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

_DEFAULT_WIDGET_NAME = "مساعد المتجر"
_DEFAULT_PRIMARY = "#6C5CE7"
_DEFAULT_STYLE = "modern"
_VALID_STYLES = frozenset({"modern", "minimal", "bold"})
_MAX_WIDGET_NAME_LEN = 120
_RE_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")
_RE_HEX3 = re.compile(r"^#[0-9A-Fa-f]{3}$")


def normalize_widget_primary_hex(raw: Any) -> str:
    if raw is None:
        return _DEFAULT_PRIMARY
    s = str(raw).strip()
    if _RE_HEX6.match(s):
        return "#" + s[1:].upper()
    if _RE_HEX3.match(s):
        h = s[1:]
        return "#" + "".join((c * 2) for c in h).upper()
    s2 = s.lstrip("#")
    if len(s2) == 6 and re.fullmatch(r"[0-9A-Fa-f]{6}", s2):
        return "#" + s2.upper()
    return _DEFAULT_PRIMARY


def is_default_widget_name(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    return value.strip() == _DEFAULT_WIDGET_NAME


def reconcile_widget_name_columns(row: Any) -> None:
    """
    Align legacy split: ‎widget_display_name=CARTFLOW‎ with ‎widget_name=مساعد المتجر‎ (default).
    """
    if row is None:
        return
    name_raw = getattr(row, "widget_name", None)
    disp_raw = getattr(row, "widget_display_name", None)
    name_s = name_raw.strip() if isinstance(name_raw, str) else ""
    disp_s = disp_raw.strip() if isinstance(disp_raw, str) else ""
    if (not name_s or is_default_widget_name(name_s)) and disp_s:
        row.widget_name = disp_s[:_MAX_WIDGET_NAME_LEN]
        return
    if name_s and not is_default_widget_name(name_s) and not disp_s:
        row.widget_display_name = name_s[:255]


def canonical_widget_name_on_row(row: Optional[Any]) -> str:
    """Storefront canonical name — non-default ‎widget_name‎, else ‎widget_display_name‎."""
    if row is None:
        return _DEFAULT_WIDGET_NAME
    name_raw = getattr(row, "widget_name", None)
    disp_raw = getattr(row, "widget_display_name", None)
    name_s = name_raw.strip() if isinstance(name_raw, str) else ""
    disp_s = disp_raw.strip() if isinstance(disp_raw, str) else ""
    if name_s and not is_default_widget_name(name_s):
        return name_s[:_MAX_WIDGET_NAME_LEN]
    if disp_s:
        return disp_s[:_MAX_WIDGET_NAME_LEN]
    if name_s:
        return name_s[:_MAX_WIDGET_NAME_LEN]
    return _DEFAULT_WIDGET_NAME


def apply_widget_customization_from_body(row: Any, body: Dict[str, Any]) -> None:
    if "widget_name" in body:
        n = str(body.get("widget_name") or "").strip()
        row.widget_name = (n[:_MAX_WIDGET_NAME_LEN] if n else _DEFAULT_WIDGET_NAME)
        if n:
            row.widget_display_name = n[:255]
    if "widget_primary_color" in body:
        row.widget_primary_color = normalize_widget_primary_hex(
            body.get("widget_primary_color")
        )
    if "widget_style" in body:
        st = str(body.get("widget_style") or "").strip().lower()
        if st in _VALID_STYLES:
            row.widget_style = st


def widget_customization_fields_for_api(row: Optional[Any]) -> Dict[str, str]:
    if row is None:
        return {
            "widget_name": _DEFAULT_WIDGET_NAME,
            "widget_primary_color": _DEFAULT_PRIMARY,
            "widget_style": _DEFAULT_STYLE,
        }
    name_s = canonical_widget_name_on_row(row)
    col_raw = getattr(row, "widget_primary_color", None)
    color_s = (
        normalize_widget_primary_hex(col_raw)
        if col_raw is not None
        else _DEFAULT_PRIMARY
    )
    style_raw = getattr(row, "widget_style", None)
    if isinstance(style_raw, str) and style_raw.strip().lower() in _VALID_STYLES:
        style_s = style_raw.strip().lower()
    else:
        style_s = _DEFAULT_STYLE
    disp_out = ""
    disp_raw = getattr(row, "widget_display_name", None) if row is not None else None
    if isinstance(disp_raw, str) and disp_raw.strip():
        disp_out = disp_raw.strip()[:255]
    return {
        "widget_name": name_s,
        "widget_display_name": disp_out or name_s,
        "widget_primary_color": color_s,
        "widget_style": style_s,
    }
