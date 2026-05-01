# -*- coding: utf-8 -*-
"""حقول ضبط نمط رسائل الواجهة (preset/custom + tone) على ‎Store‎ — بدون مسارات واتساب."""
from __future__ import annotations

from typing import Any, Dict, Optional

_MAX_TEMPLATE_CHARS = 65535
_VALID_TEMPLATE_MODES = frozenset({"preset", "custom"})
_VALID_TEMPLATE_TONES = frozenset({"friendly", "formal", "sales"})


def coerce_template_custom_text(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s[:_MAX_TEMPLATE_CHARS]


def apply_template_control_from_body(row: Any, body: Dict[str, Any]) -> None:
    """تحديث جزئي: المفاتيح الغائبة لا تُغيّر القيم الحالية."""
    if "template_mode" in body:
        m = str(body.get("template_mode") or "").strip().lower()
        if m in _VALID_TEMPLATE_MODES:
            row.template_mode = m
    if "template_tone" in body:
        t = str(body.get("template_tone") or "").strip().lower()
        if t in _VALID_TEMPLATE_TONES:
            row.template_tone = t
    if "template_custom_text" in body:
        row.template_custom_text = coerce_template_custom_text(
            body.get("template_custom_text")
        )


def template_control_fields_for_api(row: Optional[Any]) -> Dict[str, str]:
    """قيم للوحة و‎JSON‎ الواجهة — سلسلة فارغة للنص المخصص عند عدم التعيين."""
    if row is None:
        return {
            "template_mode": "preset",
            "template_tone": "friendly",
            "template_custom_text": "",
        }
    mode = getattr(row, "template_mode", None)
    if not isinstance(mode, str) or mode.strip().lower() not in _VALID_TEMPLATE_MODES:
        mode_s = "preset"
    else:
        mode_s = mode.strip().lower()
    tone = getattr(row, "template_tone", None)
    if not isinstance(tone, str) or tone.strip().lower() not in _VALID_TEMPLATE_TONES:
        tone_s = "friendly"
    else:
        tone_s = tone.strip().lower()
    ct_raw = getattr(row, "template_custom_text", None)
    ct = ""
    if isinstance(ct_raw, str) and ct_raw.strip():
        ct = ct_raw.strip()[:_MAX_TEMPLATE_CHARS]
    return {
        "template_mode": mode_s,
        "template_tone": tone_s,
        "template_custom_text": ct,
    }
