# -*- coding: utf-8 -*-
"""Reason tag → template_key mapping — single source of truth (no runtime send)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_whatsapp_template_registry_v1 import (
    TEMPLATE_REGISTRY,
    TemplateRegistryEntry,
    get_registry_entry,
)

# Canonical reason → template_key (fixed; merchants cannot alter).
REASON_TO_TEMPLATE_KEY: Mapping[str, str] = {
    "price": "PRICE_TEMPLATE",
    "shipping": "SHIPPING_TEMPLATE",
    "quality": "QUALITY_TEMPLATE",
    "delivery": "DELIVERY_TEMPLATE",
    "warranty": "WARRANTY_TEMPLATE",
    "other": "OTHER_TEMPLATE",
    "unknown": "UNKNOWN_REASON_TEMPLATE",
}

# Widget / legacy aliases normalize before lookup.
_REASON_ALIASES: Mapping[str, str] = {
    "thinking": "other",
    "price_high": "price",
    "price_low": "price",
    "shipping_cost": "shipping",
    "shipping_delay": "shipping",
    "quality_issue": "quality",
    "delivery_delay": "delivery",
    "warranty_issue": "warranty",
}

FOLLOWUP_SLOT_TO_TEMPLATE_KEY: Mapping[int, str] = {
    1: "FOLLOWUP_1_TEMPLATE",
    2: "FOLLOWUP_2_TEMPLATE",
    3: "FOLLOWUP_3_TEMPLATE",
}


def normalize_reason_tag(reason_tag: Optional[str]) -> Optional[str]:
    """Normalize widget/API reason tags to canonical reason keys."""
    k = (reason_tag or "").strip().lower()
    if not k:
        return None
    if k in REASON_TO_TEMPLATE_KEY:
        return k
    if k in _REASON_ALIASES:
        return _REASON_ALIASES[k]
    if k == "other" or k.startswith("other"):
        return "other"
    if k.startswith("price") or "price" in k:
        return "price"
    if "shipping" in k:
        return "shipping"
    if "quality" in k:
        return "quality"
    if "delivery" in k:
        return "delivery"
    if "warranty" in k:
        return "warranty"
    if k == "unknown":
        return "unknown"
    return None


def resolve_template_key_for_reason(reason_tag: Optional[str]) -> str:
    """Return registry template_key for a reason tag; unknown → UNKNOWN_REASON_TEMPLATE."""
    canon = normalize_reason_tag(reason_tag)
    if canon is None:
        return "UNKNOWN_REASON_TEMPLATE"
    return REASON_TO_TEMPLATE_KEY.get(canon, "UNKNOWN_REASON_TEMPLATE")


def resolve_registry_entry_for_reason(
    reason_tag: Optional[str],
) -> Optional[TemplateRegistryEntry]:
    key = resolve_template_key_for_reason(reason_tag)
    return get_registry_entry(key)


def resolve_template_key_for_followup_slot(slot: Any) -> Optional[str]:
    try:
        n = int(slot)
    except (TypeError, ValueError):
        return None
    if not (1 <= n <= 3):
        return None
    return FOLLOWUP_SLOT_TO_TEMPLATE_KEY.get(n)


def reason_mapping_rows_for_api() -> list[dict[str, Any]]:
    """Admin/merchant architecture view of fixed mappings."""
    rows: list[dict[str, Any]] = []
    for reason, template_key in REASON_TO_TEMPLATE_KEY.items():
        entry = TEMPLATE_REGISTRY.get(template_key)
        rows.append(
            {
                "reason_tag": reason,
                "template_key": template_key,
                "display_name_ar": entry.display_name_ar if entry else reason,
                "mapping_locked": True,
            }
        )
    return rows
