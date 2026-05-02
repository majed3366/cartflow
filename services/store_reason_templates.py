# -*- coding: utf-8 -*-
"""قوالب الاسترجاع حسب السبب (‎reason_templates‎) — تفعيل/تعطيل لكل سبب + نص على ‎Store.reason_templates_json‎."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

_REASON_TAGS = frozenset({"price", "shipping", "warranty", "thinking", "quality"})
_MAX_MESSAGE_CHARS = 65535


def normalize_delay_unit(raw: Any) -> Optional[str]:
    """‎minute‎ أو ‎hour‎؛ غير ذلك ‎None‎."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in ("minute", "minutes", "min", "دقيقة", "دقائق"):
        return "minute"
    if s in ("hour", "hours", "hr", "h", "ساعة", "ساعات"):
        return "hour"
    return None


def _coerce_message_count(raw: Any) -> int:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        v = 1
    return max(1, min(3, v))


def _parse_messages_column(raw: Any) -> List[Dict[str, Any]]:
    if raw is None or not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw[:3]:
        if not isinstance(item, dict):
            continue
        dr = item.get("delay")
        try:
            delay_v = float(dr)
        except (TypeError, ValueError):
            delay_v = 1.0
        if delay_v <= 0:
            delay_v = 1.0
        unit_raw = item.get("unit")
        unit_v = normalize_delay_unit(unit_raw)
        if unit_v is None:
            unit_v = "minute"
        txt_raw = item.get("text")
        txt_v = (
            str(txt_raw).strip()[:_MAX_MESSAGE_CHARS]
            if txt_raw is not None
            else ""
        )
        out.append({"delay": delay_v, "unit": unit_v, "text": txt_v})
    return out


def parse_reason_templates_column(raw: Any) -> Dict[str, Dict[str, Any]]:
    """‎{ slug: { enabled, message, message_count?, messages? } }‎."""
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
        mc = _coerce_message_count(entry.get("message_count"))
        messages_col = _parse_messages_column(entry.get("messages"))
        row_d: Dict[str, Any] = {"enabled": enabled, "message": msg, "message_count": mc}
        if messages_col:
            row_d["messages"] = messages_col
        out[tt] = row_d
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
        prev = dict(base.get(tt, {"enabled": True, "message": "", "message_count": 1}))
        if "enabled" in entry:
            prev["enabled"] = bool(entry.get("enabled"))
        if "message" in entry:
            m = entry.get("message")
            prev["message"] = (
                str(m).strip()[:_MAX_MESSAGE_CHARS] if m is not None else ""
            )
        if "message_count" in entry:
            prev["message_count"] = _coerce_message_count(entry.get("message_count"))
        if "messages" in entry:
            parsed_msgs = _parse_messages_column(entry.get("messages"))
            if parsed_msgs:
                prev["messages"] = parsed_msgs
            elif isinstance(entry.get("messages"), list) and len(entry["messages"]) == 0:
                prev.pop("messages", None)
        base[tt] = prev
    row.reason_templates_json = json.dumps(base, ensure_ascii=False) if base else None


def reason_templates_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "reason_templates_json", None) if row else None
    return {"reason_templates": parse_reason_templates_column(raw)}
