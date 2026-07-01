# -*- coding: utf-8 -*-
"""Merchant decision layer v1-A — canonical recommended action keys (read-only)."""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

DECISION_OBTAIN_CONTACT = "obtain_contact"
DECISION_FIX_CHANNEL = "fix_channel"
DECISION_CONTACT_CUSTOMER = "contact_customer"
DECISION_MONITOR = "monitor"

INTERVENTION_DECISION_KEYS = frozenset(
    {
        DECISION_OBTAIN_CONTACT,
        DECISION_FIX_CHANNEL,
        DECISION_CONTACT_CUSTOMER,
    }
)

_V1A_DECISION_KEYS = INTERVENTION_DECISION_KEYS | {DECISION_MONITOR}

_STATE_COMPLETED = "completed"
_STATE_ARCHIVED = "archived"
_STATE_NEEDS_INTERVENTION = "needs_intervention"
_STATE_RECOVERY_FOLLOWUP_COMPLETE = "recovery_followup_complete"

_RETURN_STATES = frozenset({"return_to_site", "waiting_purchase_window"})

_PHONE_BLOCK_LOGS = frozenset(
    {"schedule_blocked_missing_phone", "skipped_missing_phone"}
)
_FAIL_LOGS = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})

_LABEL_WAITING_CONTACT_AR = "بانتظار اكتمال بيانات التواصل"
_MERCHANT_NEEDED_YES = "نعم"


def _log_set(log_statuses: Optional[Iterable[str]]) -> frozenset[str]:
    out: set[str] = set()
    for raw in log_statuses or ():
        s = (str(raw) or "").strip().lower()
        if s:
            out.add(s)
    return frozenset(out)


def resolve_merchant_decision_key_v1(
    *,
    customer_lifecycle_state: str = "",
    customer_lifecycle_merchant_needed_ar: str = "",
    customer_lifecycle_label_ar: str = "",
    has_phone: bool = True,
    phase_key: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    purchase_truth: bool = False,
) -> Optional[str]:
    """Return canonical decision key for V1-A in-scope cases only."""
    state = (customer_lifecycle_state or "").strip().lower()
    if purchase_truth or state == _STATE_COMPLETED:
        return None
    if state in (_STATE_ARCHIVED, _STATE_RECOVERY_FOLLOWUP_COMPLETE):
        return None

    if state in _RETURN_STATES:
        return DECISION_MONITOR

    needed = (customer_lifecycle_merchant_needed_ar or "").strip()
    if needed != _MERCHANT_NEEDED_YES:
        return None

    if state != _STATE_NEEDS_INTERVENTION:
        return None

    label = (customer_lifecycle_label_ar or "").strip()
    logs = _log_set(log_statuses)

    if (
        not has_phone
        or logs & _PHONE_BLOCK_LOGS
        or label == _LABEL_WAITING_CONTACT_AR
    ):
        return DECISION_OBTAIN_CONTACT

    if logs & _FAIL_LOGS:
        return DECISION_FIX_CHANNEL

    return DECISION_CONTACT_CUSTOMER


def attach_merchant_decision_layer_v1(
    target: dict[str, Any],
    *,
    customer_lifecycle_state: str = "",
    customer_lifecycle_merchant_needed_ar: str = "",
    customer_lifecycle_label_ar: str = "",
    has_phone: bool = True,
    phase_key: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    purchase_truth: bool = False,
) -> None:
    """Attach ``merchant_decision_key`` when V1-A resolves a recommended action."""
    key = resolve_merchant_decision_key_v1(
        customer_lifecycle_state=customer_lifecycle_state,
        customer_lifecycle_merchant_needed_ar=customer_lifecycle_merchant_needed_ar,
        customer_lifecycle_label_ar=customer_lifecycle_label_ar,
        has_phone=has_phone,
        phase_key=phase_key,
        log_statuses=log_statuses,
        purchase_truth=purchase_truth,
    )
    if key and key in _V1A_DECISION_KEYS:
        target["merchant_decision_key"] = key


__all__ = [
    "DECISION_CONTACT_CUSTOMER",
    "DECISION_FIX_CHANNEL",
    "DECISION_MONITOR",
    "DECISION_OBTAIN_CONTACT",
    "INTERVENTION_DECISION_KEYS",
    "attach_merchant_decision_layer_v1",
    "resolve_merchant_decision_key_v1",
]
