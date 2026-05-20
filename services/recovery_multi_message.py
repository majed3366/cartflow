# -*- coding: utf-8 -*-
"""جدولة رسائل استرجاع متعددة لكل سبب (‎reason_templates.message_count‎ + ‎messages‎)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from services.reason_template_recovery import canonical_reason_template_key
from services.recovery_message_strategy import get_recovery_message
from services.recovery_store_lookup import log_recovery_template_lookup
from services.store_reason_templates import normalize_delay_unit, parse_reason_templates_column

_log = logging.getLogger("cartflow")

_DEFAULT_MULTI_DELAYS: Dict[str, List[Tuple[float, str]]] = {
    "price": [(2.0, "minute"), (2.0, "hour"), (24.0, "hour")],
    "shipping": [(5.0, "minute"), (1.0, "hour"), (12.0, "hour")],
    "warranty": [(5.0, "minute"), (2.0, "hour"), (24.0, "hour")],
    "thinking": [(3.0, "minute"), (1.0, "hour"), (24.0, "hour")],
    "quality": [(3.0, "minute"), (2.0, "hour"), (24.0, "hour")],
    "delivery": [(4.0, "minute"), (1.0, "hour"), (18.0, "hour")],
    "other": [(3.0, "minute"), (1.0, "hour"), (24.0, "hour")],
}


def delay_to_seconds(delay: float, unit: str) -> float:
    u = normalize_delay_unit(unit) or "minute"
    if u == "hour":
        return float(delay) * 3600.0
    return float(delay) * 60.0


def _default_slot_delay_tuple(canon: str, stage_index: int) -> Tuple[float, str]:
    defaults = _DEFAULT_MULTI_DELAYS.get(
        canon,
        [(3.0, "minute"), (1.0, "hour"), (24.0, "hour")],
    )
    row = defaults[stage_index] if stage_index < len(defaults) else defaults[-1]
    return (float(row[0]), str(row[1]))


def _legacy_recovery_delay_seconds(reason_tag: Optional[str]) -> float:
    from services.recovery_delay import get_recovery_delay

    return float(get_recovery_delay(reason_tag, store_config=None))


def emit_template_timing_used(
    *,
    reason_tag: Optional[str],
    stage: int,
    template_delay_value: Any,
    template_delay_unit: Any,
    effective_delay_seconds: float,
    source: str,
    recovery_key: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    line = (
        "[TEMPLATE TIMING USED] reason_tag=%s stage=%s template_delay_value=%s "
        "template_delay_unit=%s effective_delay_seconds=%s source=%s recovery_key=%s path=%s"
        % (
            reason_tag or "",
            stage,
            template_delay_value,
            template_delay_unit or "",
            effective_delay_seconds,
            source,
            recovery_key or "",
            path or "",
        )
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    _log.info(
        "[TEMPLATE TIMING USED] reason_tag=%s stage=%s template_delay_value=%s "
        "template_delay_unit=%s effective_delay_seconds=%s source=%s recovery_key=%s path=%s",
        reason_tag or "",
        stage,
        template_delay_value,
        template_delay_unit or "",
        effective_delay_seconds,
        source,
        recovery_key or "",
        path or "",
    )


def emit_template_timing_fallback(
    *,
    reason_tag: Optional[str],
    stage: int,
    fallback_reason: str,
    effective_delay_seconds: float,
    recovery_key: Optional[str] = None,
    path: Optional[str] = None,
) -> None:
    line = (
        "[TEMPLATE TIMING FALLBACK] reason_tag=%s stage=%s fallback_reason=%s "
        "effective_delay_seconds=%s recovery_key=%s path=%s"
        % (
            reason_tag or "",
            stage,
            fallback_reason,
            effective_delay_seconds,
            recovery_key or "",
            path or "",
        )
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    _log.info(
        "[TEMPLATE TIMING FALLBACK] reason_tag=%s stage=%s fallback_reason=%s "
        "effective_delay_seconds=%s recovery_key=%s path=%s",
        reason_tag or "",
        stage,
        fallback_reason,
        effective_delay_seconds,
        recovery_key or "",
        path or "",
    )


def _read_stage_delay_from_entry(
    entry: Dict[str, Any],
    canon: str,
    stage_index: int,
) -> Optional[Tuple[float, str, float]]:
    """قيمة التأخير من ‎messages[stage]‎ إن وُجدت."""
    messages_raw = entry.get("messages")
    if not isinstance(messages_raw, list) or stage_index >= len(messages_raw):
        return None
    raw_item = messages_raw[stage_index]
    if not isinstance(raw_item, dict):
        return None
    slot_defaults = _default_slot_delay_tuple(canon, stage_index)
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
    sec = delay_to_seconds(delay_num, unit_eff)
    return (delay_num, unit_eff, sec)


def resolve_recovery_schedule_timing(
    reason_tag: Optional[str],
    store: Any,
    *,
    stage_index: int = 0,
    recovery_key: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    تأخير الجدولة لمرحلة واحدة (٠ = الرسالة الأولى) — يقرأ ‎reason_templates.messages‎
    حتى عند ‎message_count == 1‎ (المسار أحادي الرسالة في ‎main‎).
    """
    stage_1based = int(stage_index) + 1
    canon = canonical_reason_template_key(reason_tag)
    rt_log = canon or (reason_tag or "")

    if canon is None:
        sec = _legacy_recovery_delay_seconds(reason_tag)
        log_recovery_template_lookup(
            reason=rt_log,
            template_found=False,
            message_count=None,
            delay=None,
            unit=None,
            source="legacy_recovery_delay",
            canon=None,
        )
        emit_template_timing_fallback(
            reason_tag=rt_log,
            stage=stage_1based,
            fallback_reason="unknown_reason_canon",
            effective_delay_seconds=sec,
            recovery_key=recovery_key,
            path=path,
        )
        return {
            "reason_tag": rt_log,
            "canon": None,
            "stage": stage_1based,
            "template_delay_value": None,
            "template_delay_unit": None,
            "effective_delay_seconds": sec,
            "source": "legacy_recovery_delay",
            "fallback_reason": "unknown_reason_canon",
        }

    templates = parse_reason_templates_column(
        getattr(store, "reason_templates_json", None) if store is not None else None
    )
    entry = templates.get(canon)
    if entry is None:
        sec = _legacy_recovery_delay_seconds(reason_tag)
        log_recovery_template_lookup(
            reason=rt_log,
            template_found=False,
            message_count=None,
            delay=None,
            unit=None,
            source="legacy_recovery_delay",
            canon=canon,
        )
        emit_template_timing_fallback(
            reason_tag=rt_log,
            stage=stage_1based,
            fallback_reason="no_template_entry",
            effective_delay_seconds=sec,
            recovery_key=recovery_key,
            path=path,
        )
        return {
            "reason_tag": rt_log,
            "canon": canon,
            "stage": stage_1based,
            "template_delay_value": None,
            "template_delay_unit": None,
            "effective_delay_seconds": sec,
            "source": "legacy_recovery_delay",
            "fallback_reason": "no_template_entry",
        }

    if not bool(entry.get("enabled", True)):
        sec = _legacy_recovery_delay_seconds(reason_tag)
        log_recovery_template_lookup(
            reason=rt_log,
            template_found=True,
            message_count=entry.get("message_count"),
            delay=None,
            unit=None,
            source="legacy_recovery_delay",
            canon=canon,
        )
        emit_template_timing_fallback(
            reason_tag=rt_log,
            stage=stage_1based,
            fallback_reason="template_disabled",
            effective_delay_seconds=sec,
            recovery_key=recovery_key,
        )
        return {
            "reason_tag": rt_log,
            "canon": canon,
            "stage": stage_1based,
            "template_delay_value": None,
            "template_delay_unit": None,
            "effective_delay_seconds": sec,
            "source": "legacy_recovery_delay",
            "fallback_reason": "template_disabled",
        }

    from_template = _read_stage_delay_from_entry(entry, canon, stage_index)
    if from_template is not None:
        delay_num, unit_eff, sec = from_template
        log_recovery_template_lookup(
            reason=rt_log,
            template_found=True,
            message_count=entry.get("message_count"),
            delay=delay_num,
            unit=unit_eff,
            source="reason_templates.messages",
            canon=canon,
        )
        out = {
            "reason_tag": rt_log,
            "canon": canon,
            "stage": stage_1based,
            "template_delay_value": delay_num,
            "template_delay_unit": unit_eff,
            "effective_delay_seconds": sec,
            "source": "reason_templates.messages",
            "fallback_reason": None,
        }
        emit_template_timing_used(
            reason_tag=rt_log,
            stage=stage_1based,
            template_delay_value=delay_num,
            template_delay_unit=unit_eff,
            effective_delay_seconds=sec,
            source=out["source"],
            recovery_key=recovery_key,
            path=path,
        )
        return out

    slot_defaults = _default_slot_delay_tuple(canon, stage_index)
    sec = delay_to_seconds(slot_defaults[0], slot_defaults[1])
    log_recovery_template_lookup(
        reason=rt_log,
        template_found=True,
        message_count=entry.get("message_count"),
        delay=slot_defaults[0],
        unit=slot_defaults[1],
        source="reason_templates.default_slot",
        canon=canon,
    )
    emit_template_timing_used(
        reason_tag=rt_log,
        stage=stage_1based,
        template_delay_value=slot_defaults[0],
        template_delay_unit=slot_defaults[1],
        effective_delay_seconds=sec,
        source="reason_templates.default_slot",
        recovery_key=recovery_key,
        path=path,
    )
    return {
        "reason_tag": rt_log,
        "canon": canon,
        "stage": stage_1based,
        "template_delay_value": slot_defaults[0],
        "template_delay_unit": slot_defaults[1],
        "effective_delay_seconds": sec,
        "source": "reason_templates.default_slot",
        "fallback_reason": "missing_messages_slot",
    }


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

    legacy_msg = str(entry.get("message") or "").strip()
    slots: List[Dict[str, Any]] = []

    for i in range(mc):
        raw_item: Dict[str, Any] = {}
        if i < len(messages_raw) and isinstance(messages_raw[i], dict):
            raw_item = messages_raw[i]

        parsed_delay = _read_stage_delay_from_entry(
            {"messages": messages_raw},
            canon,
            i,
        )
        if parsed_delay is not None:
            delay_num, unit_eff, sec = parsed_delay
        else:
            slot_defaults = _default_slot_delay_tuple(canon, i)
            delay_num, unit_eff = slot_defaults[0], slot_defaults[1]
            sec = delay_to_seconds(delay_num, unit_eff)

        text = str(raw_item.get("text") or "").strip()
        if not text and i == 0 and legacy_msg:
            text = legacy_msg
        if not text:
            text = get_recovery_message(reason_tag, i + 1, store)

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
