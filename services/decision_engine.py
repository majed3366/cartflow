# -*- coding: utf-8 -*-
"""
محرّك قرار أساسي للاسترجاع — نسخة Layer D.2 (بدون إرسال واتساب بعد).
نص الرسالة يُختار من ‎recovery_message_templates‎؛ الإجراء ‎action‎ يبقى كما كان.
"""
from __future__ import annotations

from typing import Any, TypedDict

from services.recovery_message_templates import resolve_whatsapp_recovery_template_message


class RecoveryActionResult(TypedDict):
    action: str
    message: str


# وسوم بديلة من ودجت الطبقة ‎D‎ أو لوحة التجربة → نفس الإجراء الأساسي
_REASON_ACTION_SYNONYMS: dict[str, str] = {
    "shipping_cost": "shipping",
    "quality_uncertainty": "quality",
    "delivery_time": "delivery",
}


def decide_recovery_action(
    reason_tag: str | None,
    *,
    store: Any = None,
) -> RecoveryActionResult:
    """
    يحوّل وسم السبب المحفوظ إلى إجراء مقترح ونص متابعة (واتساب لاحقاً).
    """
    key = (reason_tag or "").strip().lower()
    action_lookup = _REASON_ACTION_SYNONYMS.get(key, key)

    action_map: dict[str, str] = {
        "price": "offer_alternative",
        "price_high": "offer_alternative",
        "quality": "show_social_proof",
        "shipping": "highlight_shipping",
        "delivery": "reassure_delivery",
        "warranty": "reassure_warranty",
        "other": "generic_followup",
    }

    action = action_map.get(action_lookup, action_map.get(key, "default"))

    message = resolve_whatsapp_recovery_template_message(reason_tag, store=store)

    return {"action": action, "message": message}


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    for _tag in (
        "price_high",
        "quality",
        "unknown_tag",
        "",
    ):
        _r: RecoveryActionResult = decide_recovery_action(_tag, store=None)
        print(_tag, "->", _r)
