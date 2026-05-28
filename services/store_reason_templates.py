# -*- coding: utf-8 -*-
"""قوالب الاسترجاع حسب السبب (‎reason_templates‎) — تفعيل/تعطيل لكل سبب + نص على ‎Store.reason_templates_json‎.

رسالة الاسترجاع (‎message‎ / ‎messages‎) لمسار واتساب فقط.
‎widget_reason_label_ar‎ محفوظ للتوافق مع بيانات قديمة؛ واجهات الودجيت تتجاهله وتعرض كتالوج تسميات ثابت.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

_REASON_TAGS = frozenset(
    {"price", "shipping", "warranty", "thinking", "quality", "delivery", "other"}
)
_MAX_MESSAGE_CHARS = 65535
_MAX_WIDGET_REASON_LABEL_CHARS = 80


def _parse_guided_attempts_column(raw: Any) -> Dict[str, str]:
    if raw is None or not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        ks = str(k).strip()
        if ks not in ("1", "2", "3"):
            try:
                n = int(ks)
            except (TypeError, ValueError):
                continue
            if not (1 <= n <= 3):
                continue
            ks = str(n)
        if v is None:
            continue
        t = str(v).strip()[:_MAX_MESSAGE_CHARS]
        if t:
            out[ks] = t
    return out


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
        ga = _parse_guided_attempts_column(entry.get("guided_attempts"))
        if ga:
            row_d["guided_attempts"] = ga
        wl = entry.get("widget_reason_label_ar")
        if wl is not None:
            ws = str(wl).strip()[:_MAX_WIDGET_REASON_LABEL_CHARS]
            if ws:
                row_d["widget_reason_label_ar"] = ws
        out[tt] = row_d
    return out


def reason_template_key_is_persisted(
    parsed: Dict[str, Dict[str, Any]], key: str
) -> bool:
    """مفتاح موجود في ‎reason_templates_json‎ المحفوظ (ليس صفاً افتراضياً للعرض فقط)."""
    kk = str(key).strip().lower()
    return kk in parsed and isinstance(parsed.get(kk), dict)


def _finalize_reason_entry_for_storage(entry: Dict[str, Any]) -> Dict[str, Any]:
    """شكل موحّد لـ runtime و GET: ‎message_count‎ + ‎messages[]‎ + ‎message‎ للرسالة الأولى."""
    out = dict(entry)
    mc = _coerce_message_count(out.get("message_count"))
    msgs = _parse_messages_column(out.get("messages"))
    if msgs:
        out["messages"] = msgs
        mc = max(mc, len(msgs))
        first_text = str(msgs[0].get("text") or "").strip()
        if first_text:
            out["message"] = first_text
    else:
        out.pop("messages", None)
    legacy = str(out.get("message") or "").strip()
    if legacy and not msgs and mc >= 1:
        dv, unit = 1.0, "minute"
        msgs = [{"delay": dv, "unit": unit, "text": legacy[:_MAX_MESSAGE_CHARS]}]
        out["messages"] = msgs
    out["message_count"] = mc
    if not str(out.get("message") or "").strip() and msgs:
        out["message"] = str(msgs[0].get("text") or "").strip()[:_MAX_MESSAGE_CHARS]
    return out


def _mirror_reason_entry_to_trigger_templates(
    trigger_base: Dict[str, Dict[str, Any]], tag: str, reason_entry: Dict[str, Any]
) -> None:
    """مزامنة خفيفة لعمود ‎trigger_templates_json‎ (مسار نص قديم) من أول رسالة محفوظة."""
    msg = str(reason_entry.get("message") or "").strip()
    if not msg:
        msgs = reason_entry.get("messages")
        if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
            msg = str(msgs[0].get("text") or "").strip()
    trigger_base[tag] = {
        "enabled": bool(reason_entry.get("enabled", True)),
        "message": msg[:_MAX_MESSAGE_CHARS],
    }


def apply_reason_templates_from_body(row: Any, body: Dict[str, Any]) -> None:
    """دمج جزئي لحقول ‎reason_templates‎ في جسم الـ POST."""
    if "reason_templates" not in body:
        return
    incoming = body.get("reason_templates")
    base = parse_reason_templates_column(getattr(row, "reason_templates_json", None))
    if not isinstance(incoming, dict):
        return
    trigger_mirror: Optional[Dict[str, Dict[str, Any]]] = None
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
                prev_msgs = _parse_messages_column(prev.get("messages"))
                mc_target = _coerce_message_count(
                    entry.get("message_count")
                    if "message_count" in entry
                    else prev.get("message_count")
                )
                merged_msgs: List[Dict[str, Any]] = []
                for i in range(mc_target):
                    if i < len(parsed_msgs):
                        merged_msgs.append(parsed_msgs[i])
                    elif i < len(prev_msgs):
                        merged_msgs.append(prev_msgs[i])
                prev["messages"] = merged_msgs
        if "guided_attempts" in entry:
            inc_ga = entry.get("guided_attempts")
            if inc_ga is None:
                prev.pop("guided_attempts", None)
            elif isinstance(inc_ga, dict):
                cur = dict(prev.get("guided_attempts") or {})
                normalized: Dict[str, Any] = {}
                for rk, rv in inc_ga.items():
                    sk = str(rk).strip()
                    if sk not in ("1", "2", "3"):
                        try:
                            n = int(sk)
                        except (TypeError, ValueError):
                            continue
                        if 1 <= n <= 3:
                            sk = str(n)
                        else:
                            continue
                    normalized[sk] = rv
                for ak in ("1", "2", "3"):
                    if ak not in normalized:
                        continue
                    val = normalized.get(ak)
                    if val is None or not str(val).strip():
                        cur.pop(ak, None)
                    else:
                        cur[ak] = str(val).strip()[:_MAX_MESSAGE_CHARS]
                if cur:
                    prev["guided_attempts"] = cur
                else:
                    prev.pop("guided_attempts", None)
        if "widget_reason_label_ar" in entry:
            wlab = entry.get("widget_reason_label_ar")
            if wlab is None or not str(wlab).strip():
                prev.pop("widget_reason_label_ar", None)
            else:
                prev["widget_reason_label_ar"] = str(wlab).strip()[
                    :_MAX_WIDGET_REASON_LABEL_CHARS
                ]
        base[tt] = _finalize_reason_entry_for_storage(prev)
        if trigger_mirror is None:
            from services.store_trigger_templates import parse_trigger_templates_column

            trigger_mirror = parse_trigger_templates_column(
                getattr(row, "trigger_templates_json", None)
            )
        _mirror_reason_entry_to_trigger_templates(trigger_mirror, tt, base[tt])
    row.reason_templates_json = json.dumps(base, ensure_ascii=False) if base else None
    if trigger_mirror is not None:
        row.trigger_templates_json = (
            json.dumps(trigger_mirror, ensure_ascii=False) if trigger_mirror else None
        )


def reason_templates_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "reason_templates_json", None) if row else None
    return {"reason_templates": parse_reason_templates_column(raw)}
