# -*- coding: utf-8 -*-
"""
Cart Page V2 Phase 0 — primary action projection (presentation-safe, additive).

Maps each normal-carts row to exactly one primary merchant action key.
Does not write DB, change lifecycle/recovery/WhatsApp/archive APIs, or alter UI.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

ENV_PRIMARY_ACTION = "CARTFLOW_CARTS_V2_PRIMARY_ACTION"
PROJECTION_VERSION = "v1"
ROW_KEY = "cart_page_primary_action_v1"

KEY_NO_ACTION = "no_action_required"
KEY_WAIT = "wait"
KEY_CONTACT = "contact_customer"
KEY_REVIEW = "review_cart"
KEY_FOLLOW_UP = "follow_up_manually"
KEY_ARCHIVE = "archive"
KEY_REOPEN = "reopen"

ALLOWED_KEYS = frozenset(
    {
        KEY_NO_ACTION,
        KEY_WAIT,
        KEY_CONTACT,
        KEY_REVIEW,
        KEY_FOLLOW_UP,
        KEY_ARCHIVE,
        KEY_REOPEN,
    }
)

LABEL_AR = {
    KEY_NO_ACTION: "لا يلزم إجراء",
    KEY_WAIT: "انتظر — CartFlow يتابع",
    KEY_CONTACT: "تواصل مع العميل",
    KEY_REVIEW: "راجع السلة",
    KEY_FOLLOW_UP: "متابعة يدوية",
    KEY_ARCHIVE: "نقل للأرشيف",
    KEY_REOPEN: "إعادة فتح",
}

# Higher = more urgent for future decide-queue ordering (presentation only).
PRIORITY = {
    KEY_CONTACT: 100,
    KEY_FOLLOW_UP: 90,
    KEY_REVIEW: 80,
    KEY_WAIT: 40,
    KEY_REOPEN: 30,
    KEY_NO_ACTION: 10,
    KEY_ARCHIVE: 5,
}

_AUTOMATIC_WAIT_STATES = frozenset(
    {
        "active",
        "waiting_first_send",
        "waiting_customer_reply",
        "customer_reply",
        "customer_engaged",
        "return_to_site",
        "waiting_purchase_window",
        "waiting_next_scheduled",
    }
)


def cart_page_primary_action_enabled() -> bool:
    """Default on — additive and UI-inert until Phase 1+ consumes it."""
    raw = (os.environ.get(ENV_PRIMARY_ACTION) or "1").strip().lower()
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return _norm(value) in ("1", "true", "yes", "on")


def _pack(
    *,
    key: str,
    reason: str,
    source_state: str,
    secondary_key: Optional[str] = None,
) -> dict[str, Any]:
    k = key if key in ALLOWED_KEYS else KEY_REVIEW
    out: dict[str, Any] = {
        "version": PROJECTION_VERSION,
        "key": k,
        "label": LABEL_AR.get(k, k),
        "reason": (reason or "")[:240],
        "priority": int(PRIORITY.get(k, 0)),
        "source_state": (source_state or "")[:64],
    }
    if secondary_key and secondary_key in ALLOWED_KEYS and secondary_key != k:
        # Demoted only — never a co-primary. UI must not treat as equal CTA (Phase 1+).
        out["secondary_key"] = secondary_key
        out["secondary_label"] = LABEL_AR.get(secondary_key, secondary_key)
        out["secondary_demoted"] = True
    return out


def project_cart_page_primary_action_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    Derive one primary action from existing row fields.

    Archive is never the primary for active/automatic/intervention carts.
    Reopen is primary only for archived/historical restore.
    """
    state = _norm(row.get("customer_lifecycle_state"))
    dash = _norm(row.get("customer_lifecycle_dashboard_action"))
    archived_visual = _truthy(row.get("customer_lifecycle_is_archived_visual"))
    completed_variant = _norm(row.get("customer_lifecycle_completed_variant"))
    decision_key = _norm(row.get("merchant_decision_key"))
    executable = _truthy(row.get("merchant_intervention_executable"))
    has_phone = _truthy(row.get("merchant_has_customer_phone"))
    is_vip = _truthy(row.get("is_vip_lane")) or _truthy(row.get("vip_lane"))
    label = _norm(row.get("customer_lifecycle_label_ar"))
    needed = _norm(row.get("customer_lifecycle_merchant_needed_ar"))

    # --- Historical / archived ---
    if state == "archived" or archived_visual or dash == "reopen":
        if completed_variant == "purchased" or state == "completed":
            return _pack(
                key=KEY_NO_ACTION,
                reason="purchased_or_completed_terminal",
                source_state=state or "completed",
            )
        return _pack(
            key=KEY_REOPEN,
            reason="archived_restore_visibility",
            source_state=state or "archived",
        )

    # --- Completed / success ---
    if state == "completed" or completed_variant in ("purchased", "recovered"):
        return _pack(
            key=KEY_NO_ACTION,
            reason="completed_outcome",
            source_state=state or "completed",
        )

    if state == "recovery_followup_complete":
        return _pack(
            key=KEY_NO_ACTION,
            reason="recovery_sequence_finished",
            source_state=state,
            secondary_key=KEY_ARCHIVE if dash == "archive" else None,
        )

    # --- Unclassified ---
    if not state or state in ("lifecycle_unavailable", "unavailable", "-"):
        return _pack(
            key=KEY_REVIEW,
            reason="lifecycle_unavailable",
            source_state=state or "lifecycle_unavailable",
        )

    # --- VIP manual path (before generic intervention) ---
    if is_vip and state == "needs_intervention":
        if "تم التواصل" in (row.get("customer_lifecycle_label_ar") or ""):
            return _pack(
                key=KEY_WAIT,
                reason="vip_already_contacted",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        return _pack(
            key=KEY_FOLLOW_UP,
            reason="vip_manual_path",
            source_state=state,
            secondary_key=KEY_ARCHIVE if dash == "archive" else None,
        )

    # --- Needs intervention variants ---
    if state == "needs_intervention":
        if decision_key == "contact_customer" and executable and has_phone:
            return _pack(
                key=KEY_CONTACT,
                reason="intervention_contact_executable",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        if decision_key in ("obtain_contact",) or (
            not has_phone and needed in ("نعم", "yes", "1", "true")
        ):
            return _pack(
                key=KEY_FOLLOW_UP,
                reason="intervention_no_phone",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        if decision_key == "fix_channel" or "إعداد" in label or "اعداد" in label:
            return _pack(
                key=KEY_FOLLOW_UP,
                reason="intervention_channel_fail",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        if "جاهزية" in (row.get("customer_lifecycle_label_ar") or "") or decision_key == "monitor":
            return _pack(
                key=KEY_WAIT,
                reason="intervention_schedule_not_ready",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        if needed in ("نعم", "yes", "1", "true") and not executable:
            return _pack(
                key=KEY_REVIEW,
                reason="intervention_needed_not_executable",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        if executable and has_phone:
            return _pack(
                key=KEY_CONTACT,
                reason="intervention_executable_fallback",
                source_state=state,
                secondary_key=KEY_ARCHIVE if dash == "archive" else None,
            )
        return _pack(
            key=KEY_REVIEW,
            reason="intervention_default_review",
            source_state=state,
            secondary_key=KEY_ARCHIVE if dash == "archive" else None,
        )

    # --- Automatic CartFlow ---
    if state in _AUTOMATIC_WAIT_STATES:
        secondary = KEY_ARCHIVE if dash == "archive" else None
        # return_to_site / purchase window: governance says no Archive secondary
        if state in ("return_to_site", "waiting_purchase_window"):
            secondary = None
        return _pack(
            key=KEY_WAIT,
            reason="automatic_cartflow",
            source_state=state,
            secondary_key=secondary,
        )

    # --- Safe default: never archive as primary for unknown active ---
    return _pack(
        key=KEY_REVIEW,
        reason="unmapped_state_review",
        source_state=state or "unknown",
        secondary_key=KEY_ARCHIVE if dash == "archive" else None,
    )


def attach_cart_page_primary_action_v1(target: Mapping[str, Any] | dict[str, Any]) -> None:
    """Attach projection to one row when flag enabled. No-op if disabled or non-dict."""
    if not cart_page_primary_action_enabled():
        return
    if not isinstance(target, dict):
        return
    try:
        target[ROW_KEY] = project_cart_page_primary_action_v1(target)
    except Exception:  # noqa: BLE001
        # Never break normal-carts assembly
        return


def ensure_normal_carts_primary_action_v1(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure active + archived rows carry primary-action projection (read-time safe).
    Idempotent; skips when flag off.
    """
    if not isinstance(payload, dict):
        return payload
    if not cart_page_primary_action_enabled():
        return payload
    for key in ("merchant_carts_page_rows", "merchant_archived_carts_page_rows"):
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                attach_cart_page_primary_action_v1(row)
    return payload


__all__ = [
    "ALLOWED_KEYS",
    "ENV_PRIMARY_ACTION",
    "KEY_ARCHIVE",
    "KEY_CONTACT",
    "KEY_FOLLOW_UP",
    "KEY_NO_ACTION",
    "KEY_REOPEN",
    "KEY_REVIEW",
    "KEY_WAIT",
    "PROJECTION_VERSION",
    "ROW_KEY",
    "attach_cart_page_primary_action_v1",
    "cart_page_primary_action_enabled",
    "ensure_normal_carts_primary_action_v1",
    "project_cart_page_primary_action_v1",
]
