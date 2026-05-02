# -*- coding: utf-8 -*-
"""تقييم ‎reason_templates‎ قبل إرسال واتساب الاسترجاع — تعطيل لكل سبب + أولوية النص."""
from __future__ import annotations

from typing import Any, Optional

from services.recovery_message_templates import resolve_whatsapp_recovery_template_message
from services.store_reason_templates import parse_reason_templates_column


def canonical_reason_template_key(reason_tag: Optional[str]) -> Optional[str]:
    """
    وسوم الواجهة / الطبقات → مفتاح ‎reason_templates‎.
    ‎price_high → price‎، ‎shipping_delay → shipping‎، ‎warranty_issue → warranty‎، ‎thinking → thinking‎.
    """
    k = (reason_tag or "").strip().lower()
    if not k:
        return None
    if k == "thinking":
        return "thinking"
    if k == "quality" or "quality" in k:
        return "quality"
    if k.startswith("price") or "price" in k:
        return "price"
    if "shipping" in k:
        return "shipping"
    if "warranty" in k:
        return "warranty"
    return None


def _log_template_toggle(canon: str, enabled_eff: bool) -> None:
    try:
        print("[TEMPLATE TOGGLE]")
        print("reason=", canon)
        print("enabled=" + ("true" if enabled_eff else "false"))
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
        _log_template_toggle(canon, True)
        return False
    enabled_eff = bool(entry.get("enabled", True))
    _log_template_toggle(canon, enabled_eff)
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
