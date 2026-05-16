# -*- coding: utf-8 -*-
"""تقييم ‎reason_templates‎ قبل إرسال واتساب الاسترجاع — تعطيل لكل سبب + أولوية النص."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from services.recovery_message_templates import resolve_whatsapp_recovery_template_message
from services.store_reason_templates import parse_reason_templates_column


def canonical_reason_template_key(reason_tag: Optional[str]) -> Optional[str]:
    """
    وسوم الواجهة / الطبقات → مفتاح ‎reason_templates‎.
    ‎price_high → price‎، ‎shipping_delay → shipping‎، ‎warranty_issue → warranty‎، ‎thinking → thinking‎، ‎other‎، ‎delivery‎.
    """
    k = (reason_tag or "").strip().lower()
    if not k:
        return None
    if k == "thinking":
        return "thinking"
    if k == "other" or k.startswith("other_"):
        return "other"
    if k == "quality" or "quality" in k:
        return "quality"
    if k.startswith("price") or "price" in k:
        return "price"
    if "delivery" in k:
        return "delivery"
    if "shipping" in k:
        return "shipping"
    if "warranty" in k:
        return "warranty"
    return None


def _raw_enabled_value_from_store_json(store: Any, canon: str) -> str:
    """Unparsed ‎enabled‎ for ‎canon‎ on ‎reason_templates_json‎ (diagnostics only)."""
    if store is None:
        return "-"
    raw_col = getattr(store, "reason_templates_json", None)
    if raw_col is None:
        return "(null)"
    try:
        blob: Any
        if isinstance(raw_col, dict):
            blob = raw_col
        else:
            s = str(raw_col).strip()
            if not s:
                return "(empty)"
            blob = json.loads(s)
        if not isinstance(blob, dict):
            return "(not_object)"
        ent = blob.get(canon)
        if ent is None:
            return f"(no_key:{canon})"
        if not isinstance(ent, dict):
            return repr(ent)[:160]
        if "enabled" not in ent:
            return "(no_enabled_field)"
        return repr(ent.get("enabled"))
    except Exception as exc:  # noqa: BLE001
        return f"(raw_parse_error:{type(exc).__name__})"


def _log_template_enabled_source(
    *,
    canon: str,
    store: Any,
    templates: Dict[str, Dict[str, Any]],
    entry: Optional[Dict[str, Any]],
    enabled_eff: bool,
) -> None:
    try:
        sid = getattr(store, "id", None) if store is not None else None
        sslug = (
            getattr(store, "zid_store_id", None) or getattr(store, "store_slug", None)
            if store is not None
            else None
        )
        raw_col = getattr(store, "reason_templates_json", None) if store is not None else None
        present = bool(
            raw_col is not None
            and (
                (isinstance(raw_col, str) and str(raw_col).strip())
                or isinstance(raw_col, dict)
            )
        )
        keys = ",".join(sorted(templates.keys()))
        if entry is None:
            src = "fallback" if store is None else "default"
        else:
            src = "reason_templates_json"
        raw_ev = _raw_enabled_value_from_store_json(store, canon) if store is not None else "-"
        print("[TEMPLATE ENABLED SOURCE]", flush=True)
        print(f"reason={canon}", flush=True)
        print("enabled=" + ("true" if enabled_eff else "false"), flush=True)
        print(f"source={src}", flush=True)
        print(f"store_id={sid if sid is not None else '-'}", flush=True)
        print(f"store_slug={sslug if sslug else '-'}", flush=True)
        print(f"reason_templates_present={'true' if present else 'false'}", flush=True)
        print(f"template_keys={keys or '-'}", flush=True)
        print(f"raw_enabled_value={raw_ev}", flush=True)
    except Exception:
        pass


def _log_template_skipped(canon: str) -> None:
    try:
        print("[TEMPLATE SKIPPED]")
        print("reason=", canon)
        print("enabled=false")
    except Exception:
        pass


def reason_template_blocks_recovery_whatsapp(reason_tag: Optional[str], store: Any) -> bool:
    """
    ‎True‎ إذا كان السبب معطّلاً صراحةً في ‎reason_templates‎ (لا إرسال واتساب لهذه الجلسة لهذا السبب).
    """
    canon = canonical_reason_template_key(reason_tag)
    if canon is None:
        return False
    templates = parse_reason_templates_column(
        getattr(store, "reason_templates_json", None) if store is not None else None
    )
    entry = templates.get(canon)
    if entry is None:
        _log_template_enabled_source(
            canon=canon,
            store=store,
            templates=templates,
            entry=None,
            enabled_eff=True,
        )
        return False
    enabled_eff = bool(entry.get("enabled", True))
    _log_template_enabled_source(
        canon=canon,
        store=store,
        templates=templates,
        entry=entry,
        enabled_eff=enabled_eff,
    )
    if entry.get("enabled") is False:
        _log_template_skipped(canon)
        return True
    return False


def resolve_recovery_whatsapp_message_with_reason_templates(
    reason_tag: Optional[str],
    *,
    store: Any = None,
) -> str:
    """نص ‎reason_templates.message‎ إن وُجد ومفعّل؛ وإلا نفس سلسلة القوالب الحالية."""
    canon = canonical_reason_template_key(reason_tag)
    if canon is not None and store is not None:
        templates = parse_reason_templates_column(
            getattr(store, "reason_templates_json", None)
        )
        entry = templates.get(canon)
        if entry is not None and bool(entry.get("enabled", True)):
            msg = str(entry.get("message") or "").strip()
            if msg:
                return msg
    return resolve_whatsapp_recovery_template_message(reason_tag, store=store)
