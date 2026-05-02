# -*- coding: utf-8 -*-
"""جدولة رسائل استرجاع متعددة لكل سبب (‎reason_templates.message_count‎ + ‎messages‎)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.reason_template_recovery import canonical_reason_template_key
from services.recovery_message_templates import resolve_whatsapp_recovery_template_message
from services.store_reason_templates import normalize_delay_unit, parse_reason_templates_column

_DEFAULT_MULTI_DELAYS: Dict[str, List[Tuple[float, str]]] = {
    "price": [(2.0, "minute"), (2.0, "hour"), (24.0, "hour")],
    "shipping": [(5.0, "minute"), (1.0, "hour"), (12.0, "hour")],
    "warranty": [(5.0, "minute"), (2.0, "hour"), (24.0, "hour")],
    "thinking": [(3.0, "minute"), (1.0, "hour"), (24.0, "hour")],
    "quality": [(3.0, "minute"), (2.0, "hour"), (24.0, "hour")],
}


def delay_to_seconds(delay: float, unit: str) -> float:
    u = normalize_delay_unit(unit) or "minute"
    if u == "hour":
        return float(delay) * 3600.0
    return float(delay) * 60.0


def multi_message_slots_for_abandon(
    reason_tag: Optional[str],
    store: Any,
) -> Optional[List[Dict[str, Any]]]:
    """
    يُرجع قائمة خانات الجدولة إذا كان ‎messages‎ غير فارغة و‎max(message_count, len(messages)) > 1‎.
    وإلا ‎None‎ (المسار القديم برسالة واحدة).
    """
    canon = canonical_reason_template_key(reason_tag)
    if canon is None:
        return None
    templates = parse_reason_templates_column(
        getattr(store, "reason_templates_json", None) if store is not None else None
    )
    entry = templates.get(canon)
    if entry is None:
        return None
    if not bool(entry.get("enabled", True)):
        return None
    messages_raw = entry.get("messages")
    if messages_raw is None:
        return None
    if not isinstance(messages_raw, list) or len(messages_raw) == 0:
        return None
    try:
        mc_stored = int(entry.get("message_count") or 1)
    except (TypeError, ValueError):
        mc_stored = 1
    mc_stored = max(1, min(3, mc_stored))
    msg_len = min(3, len(messages_raw))
    mc = max(mc_stored, msg_len)
    if mc <= 1:
        return None

    defaults = _DEFAULT_MULTI_DELAYS.get(
        canon,
        [(3.0, "minute"), (1.0, "hour"), (24.0, "hour")],
    )

    legacy_msg = str(entry.get("message") or "").strip()
    slots: List[Dict[str, Any]] = []

    for i in range(mc):
        slot_defaults = defaults[i] if i < len(defaults) else defaults[-1]
        raw_item: Dict[str, Any] = {}
        if i < len(messages_raw) and isinstance(messages_raw[i], dict):
            raw_item = messages_raw[i]

        delay_raw = raw_item.get("delay", slot_defaults[0])
        try:
            delay_num = float(delay_raw)
        except (TypeError, ValueError):
            delay_num = float(slot_defaults[0])
        if delay_num <= 0:
            delay_num = float(slot_defaults[0])

        unit_eff = normalize_delay_unit(raw_item.get("unit"))
        if unit_eff is None:
            unit_eff = normalize_delay_unit(slot_defaults[1]) or str(slot_defaults[1])

        text = str(raw_item.get("text") or "").strip()
        if not text and i == 0 and legacy_msg:
            text = legacy_msg
        if not text:
            text = resolve_whatsapp_recovery_template_message(reason_tag, store=store)

        sec = delay_to_seconds(delay_num, unit_eff)

        slots.append(
            {
                "index": i + 1,
                "delay_seconds": sec,
                "delay_display": delay_num,
                "unit_display": unit_eff,
                "text": text,
                "canon": canon,
            }
        )

    return slots
