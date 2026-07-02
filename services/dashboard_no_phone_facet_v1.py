# -*- coding: utf-8 -*-
"""
No-phone dashboard facet — display/filter only (not a lifecycle state).

Shared rule for store counter ``no_phone_total`` and row ``merchant_cart_visible_tabs``.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.customer_lifecycle_states_v1 import (
    STATE_ARCHIVED,
    STATE_COMPLETED,
    UI_FILTER_NOPHONE,
)
from services.dashboard_completed_row_semantics_v1 import is_completed_dashboard_row
from services.merchant_dashboard_recovery_resolve_v1 import SENT_LOG_STATUSES


def log_has_sent_recovery(*, log_has_sent: Optional[bool] = None, log_statuses: Any = None) -> bool:
    if log_has_sent is not None:
        return bool(log_has_sent)
    if not log_statuses:
        return False
    if isinstance(log_statuses, (set, frozenset)):
        ss = log_statuses
    elif isinstance(log_statuses, (list, tuple)):
        ss = frozenset(str(x or "").strip().lower() for x in log_statuses if x)
    else:
        ss = frozenset({str(log_statuses).strip().lower()}) if log_statuses else frozenset()
    return bool(ss & SENT_LOG_STATUSES)


def is_no_phone_pre_send_dashboard_row(
    row: Mapping[str, Any],
    *,
    log_has_sent: Optional[bool] = None,
    log_statuses: Any = None,
) -> bool:
    """
    Active dashboard row, pre-send, no verified phone — same rule as no_phone_total.
    Does not change lifecycle state or bucket.
    """
    if log_has_sent_recovery(log_has_sent=log_has_sent, log_statuses=log_statuses):
        return False
    if row.get("merchant_has_customer_phone") is True:
        return False
    if row.get("merchant_has_customer_phone") is not False:
        return False
    if row.get("customer_lifecycle_is_archived_visual") is True:
        return False
    if row.get("merchant_is_history_slice") is True:
        return False
    if row.get("merchant_cart_is_active") is False:
        return False
    sk = str(row.get("customer_lifecycle_state") or "").strip().lower()
    if sk in (STATE_ARCHIVED, STATE_COMPLETED):
        return False
    if is_completed_dashboard_row(row):
        return False
    return True


def apply_no_phone_visible_tab_facet(
    row: dict[str, Any],
    *,
    log_has_sent: Optional[bool] = None,
    log_statuses: Any = None,
) -> bool:
    """Append ``nophone`` to visible tabs when facet applies; keep lifecycle bucket."""
    if not is_no_phone_pre_send_dashboard_row(
        row,
        log_has_sent=log_has_sent,
        log_statuses=log_statuses,
    ):
        return False
    tabs = list(row.get("merchant_cart_visible_tabs") or [])
    if UI_FILTER_NOPHONE not in tabs:
        tabs.append(UI_FILTER_NOPHONE)
    row["merchant_cart_visible_tabs"] = tabs
    return True


__all__ = [
    "apply_no_phone_visible_tab_facet",
    "is_no_phone_pre_send_dashboard_row",
    "log_has_sent_recovery",
]
