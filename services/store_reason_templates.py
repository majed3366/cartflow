# -*- coding: utf-8 -*-
"""قوالب الاسترجاع حسب السبب (‎reason_templates‎) — تفعيل/تعطيل لكل سبب + نص على ‎Store.reason_templates_json‎."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

_REASON_TAGS = frozenset({"price", "shipping", "warranty", "thinking", "quality"})
_MAX_MESSAGE_CHARS = 65535


def parse_reason_templates_column(raw: Any) -> Dict[str, Dict[str, Any]]:
    """‎{ slug: { enabled: bool (افتراضي ‎True‎), message: str } }‎."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        data = raw
    else:
        s = str(raw).strip()
        if not s:
            return {}
        try:
            data = json.loads(s)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for tag, entry in data.items():
        tt = str(tag).strip().lower()
        if tt not in _REASON_TAGS:
            continue
        if not isinstance(entry, dict):
            continue
        enabled = bool(entry.get("enabled", True))
        msg_raw = entry.get("message")
        msg = (
            str(msg_raw).strip()[:_MAX_MESSAGE_CHARS]
            if msg_raw is not None
            else ""
        )
        out[tt] = {"enabled": enabled, "message": msg}
    return out


def apply_reason_templates_from_body(row: Any, body: Dict[str, Any]) -> None:
    """دمج جزئي لحقول ‎reason_templates‎ في جسم الـ POST."""
    if "reason_templates" not in body:
        return
    incoming = body.get("reason_templates")
    base = parse_reason_templates_column(getattr(row, "reason_templates_json", None))
    if not isinstance(incoming, dict):
        return
    for tag, entry in incoming.items():
        tt = str(tag).strip().lower()
        if tt not in _REASON_TAGS:
            continue
        if not isinstance(entry, dict):
            continue
        prev = dict(base.get(tt, {"enabled": True, "message": ""}))
        if "enabled" in entry:
            prev["enabled"] = bool(entry.get("enabled"))
        if "message" in entry:
            m = entry.get("message")
            prev["message"] = (
                str(m).strip()[:_MAX_MESSAGE_CHARS] if m is not None else ""
            )
        base[tt] = prev
    row.reason_templates_json = json.dumps(base, ensure_ascii=False) if base else None


def reason_templates_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "reason_templates_json", None) if row else None
    return {"reason_templates": parse_reason_templates_column(raw)}
