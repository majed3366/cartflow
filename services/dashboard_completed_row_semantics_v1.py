# -*- coding: utf-8 -*-
"""
Completed-page row semantics — shared rule for completed counter and completed tab.

Mirrors ``isCompletedDashboardRow`` in ``static/merchant_dashboard_lazy.js``.
Read-only classification helper; does not change lifecycle or recovery behavior.
"""
from __future__ import annotations

from typing import Any, Mapping


def is_archived_destination_dashboard_row(row: Mapping[str, Any]) -> bool:
    if row.get("customer_lifecycle_is_archived_visual") is True:
        return True
    return str(row.get("customer_lifecycle_state") or "").strip().lower() == "archived"


def is_completed_dashboard_row(row: Mapping[str, Any]) -> bool:
    """Whether a cart belongs on the merchant «مكتملة» completed page."""
    if not row:
        return False
    if is_archived_destination_dashboard_row(row):
        return True
    lc = str(row.get("customer_lifecycle_state") or "").strip().lower()
    if lc == "completed":
        return True
    if str(row.get("merchant_coarse_status") or "").strip().lower() == "converted":
        return True
    if str(row.get("customer_lifecycle_completed_variant") or "").strip() == "purchased":
        return True
    primary = str(row.get("merchant_cart_primary_bucket") or "").strip().lower()
    if primary in ("recovered", "completed"):
        return True
    bucket = str(row.get("merchant_cart_bucket") or "").strip().lower()
    if bucket in ("recovered", "completed"):
        return True
    tabs = row.get("merchant_cart_visible_tabs") or []
    if isinstance(tabs, (list, tuple)):
        for tab in tabs:
            tk = str(tab or "").strip().lower()
            if tk in ("recovered", "completed"):
                return True
    lbl = str(row.get("customer_lifecycle_label_ar") or "")
    if "تم الشراء" in lbl:
        return True
    if "تمت الاستعادة" in lbl:
        return True
    if "تم الاسترجاع" in lbl:
        return True
    if row.get("merchant_cart_is_terminal") is True and "تم" in lbl:
        return True
    return False


__all__ = [
    "is_archived_destination_dashboard_row",
    "is_completed_dashboard_row",
]
