# -*- coding: utf-8 -*-
"""قوالب المشغّل حسب ‎reason_tag‎ على ‎Store‎ — JSON على العمود ‎trigger_templates_json‎."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

# مفاتيح مسموحة في التخزين (التردد في الواجهة يُحفظ تحت ‎other‎)
_TRIGGER_REASON_TAGS = frozenset({"price", "shipping", "warranty", "other", "quality"})
_MAX_MESSAGE_CHARS = 65535


def parse_trigger_templates_column(raw: Any) -> Dict[str, Dict[str, Any]]:
    """يعيد ‎{ reason_tag: { enabled: bool, message: str } }‎ معقّاة."""
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
        if tt not in _TRIGGER_REASON_TAGS:
            continue
        if not isinstance(entry, dict):
            continue
        enabled = bool(entry.get("enabled", False))
        msg_raw = entry.get("message")
        msg = (
            str(msg_raw).strip()[:_MAX_MESSAGE_CHARS]
            if msg_raw is not None
            else ""
        )
        out[tt] = {"enabled": enabled, "message": msg}
    return out


def apply_trigger_templates_from_body(row: Any, body: Dict[str, Any]) -> None:
    """دمج جزئي: كل مفتاح في ‎trigger_templates‎ يحدّث ذلك السبب فقط."""
    if "trigger_templates" not in body:
        return
    incoming = body.get("trigger_templates")
    base = parse_trigger_templates_column(getattr(row, "trigger_templates_json", None))
    if not isinstance(incoming, dict):
        return
    for tag, entry in incoming.items():
        tt = str(tag).strip().lower()
        if tt not in _TRIGGER_REASON_TAGS:
            continue
        if not isinstance(entry, dict):
            continue
        prev = dict(base.get(tt, {"enabled": False, "message": ""}))
        if "enabled" in entry:
            prev["enabled"] = bool(entry.get("enabled"))
        if "message" in entry:
            m = entry.get("message")
            prev["message"] = (
                str(m).strip()[:_MAX_MESSAGE_CHARS] if m is not None else ""
            )
        base[tt] = prev
    row.trigger_templates_json = json.dumps(base, ensure_ascii=False) if base else None


def trigger_templates_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "trigger_templates_json", None) if row else None
    return {"trigger_templates": parse_trigger_templates_column(raw)}
