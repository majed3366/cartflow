# -*- coding: utf-8 -*-
"""
Merchant-facing attention / intervention display semantics (presentation only).

Maps lifecycle truth to dashboard labels and optional contact controls without
changing lifecycle classification, recovery execution, or scheduling.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional
from urllib.parse import quote

from services.customer_lifecycle_states_v1 import (
    LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    STATE_ARCHIVED,
    STATE_COMPLETED,
    STATE_CUSTOMER_ENGAGED,
    STATE_CUSTOMER_REPLY,
    STATE_NEEDS_INTERVENTION,
    STATE_RETURN_TO_SITE,
    STATE_WAITING_PURCHASE_WINDOW,
)
from services.merchant_decision_layer_v1 import (
    DECISION_CONTACT_CUSTOMER,
    DECISION_FIX_CHANNEL,
    DECISION_OBTAIN_CONTACT,
)

LABEL_INTERVENTION_AR = "تحتاج تدخل"
LABEL_WAITING_READY_AR = "بانتظار الجاهزية"
LABEL_CANNOT_FOLLOW_AR = "لا يمكن المتابعة حالياً"
LABEL_NEEDS_SETUP_AR = "يحتاج إعداد"
LABEL_SYSTEM_FOLLOWS_AR = "النظام يتابع تلقائياً"
LABEL_WAITING_PHONE_AR = "بانتظار رقم العميل"
LABEL_CANNOT_FOLLOW_NO_PHONE_AR = "لا يمكن المتابعة — لا يوجد رقم عميل"

_MERCHANT_NEEDED_YES = "نعم"
_FAIL_LOGS = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def normalize_customer_phone_for_wa_me(raw: Optional[str]) -> str:
    """Digits-only phone for wa.me links (e.g. 9665xxxxxxxx)."""
    if raw is None or not str(raw).strip():
        return ""
    digits = "".join(c for c in str(raw) if c.isdigit())
    if not digits:
        return ""
    if len(digits) == 9 and digits.startswith("5"):
        return "966" + digits
    if len(digits) == 10 and digits.startswith("05"):
        return "966" + digits[1:]
    if digits.startswith("966") and len(digits) >= 11:
        return digits
    return digits


def _merchant_intervention_prefill_whatsapp_body(*, cart_link: str = "") -> str:
    base = "هلا 👋\nنتواصل معك بخصوص سلتك المتروكة."
    link = _norm(cart_link)
    if link:
        return base + "\nرابط السلة:\n" + link
    return base


def _log_set(log_statuses: Any) -> frozenset[str]:
    out: set[str] = set()
    for raw in log_statuses or ():
        s = _norm_lower(raw)
        if s:
            out.add(s)
    return frozenset(out)


def _sync_display_labels(row: dict[str, Any]) -> None:
    label = _norm(row.get("customer_lifecycle_label_ar"))
    if label:
        row["merchant_status_label_ar"] = label
        row["lifecycle_label_ar"] = label


def _is_terminal_purchase_safe_state(state: str, row: Mapping[str, Any]) -> bool:
    if state in (STATE_COMPLETED, STATE_ARCHIVED):
        return True
    if state in (STATE_RETURN_TO_SITE, STATE_WAITING_PURCHASE_WINDOW):
        return True
    if _norm_lower(row.get("merchant_coarse_status")) == "converted":
        return True
    if _norm(row.get("customer_lifecycle_completed_variant")) == "purchased":
        return True
    lbl = _norm(row.get("customer_lifecycle_label_ar"))
    if "تم الشراء" in lbl or "تمت الاستعادة" in lbl or "تم الاسترجاع" in lbl:
        return True
    return False


def resolve_needs_intervention_display_label(
    *,
    canonical_label_ar: str = "",
    merchant_needed_ar: str = "",
    decision_key: str = "",
    has_phone: bool = False,
    log_statuses: Any = None,
) -> str:
    """Presentation label for needs_intervention when intervention is not executable."""
    label = _norm(canonical_label_ar)
    needed = _norm(merchant_needed_ar)
    key = _norm_lower(decision_key)
    logs = _log_set(log_statuses)

    if not has_phone or key == DECISION_OBTAIN_CONTACT:
        if label == LABEL_WAITING_CONTACT_COMPLETION_AR:
            return LABEL_WAITING_PHONE_AR
        return LABEL_CANNOT_FOLLOW_NO_PHONE_AR

    if label == LABEL_SCHEDULE_NOT_MATERIALIZED_AR or needed != _MERCHANT_NEEDED_YES:
        return LABEL_WAITING_READY_AR

    if key == DECISION_FIX_CHANNEL or bool(logs & _FAIL_LOGS):
        return LABEL_NEEDS_SETUP_AR

    if needed != _MERCHANT_NEEDED_YES:
        return LABEL_SYSTEM_FOLLOWS_AR

    return LABEL_CANNOT_FOLLOW_AR


def apply_attention_merchant_semantics_v1(
    row: dict[str, Any],
    *,
    customer_phone_raw: str = "",
    is_vip_lane: bool = False,
    log_statuses: Any = None,
    cart_link: str = "",
) -> None:
    """
    Attach merchant-visible intervention semantics to a normal-carts row.

    Does not mutate ``customer_lifecycle_state`` or filter buckets.
    """
    state = _norm_lower(row.get("customer_lifecycle_state"))
    if not state:
        return
    if _is_terminal_purchase_safe_state(state, row):
        row["merchant_intervention_executable"] = False
        return
    if is_vip_lane:
        row["merchant_intervention_executable"] = False
        return

    row.setdefault("merchant_intervention_executable", False)
    row.pop("merchant_intervention_contact_href", None)
    row.pop("merchant_intervention_action_ar", None)

    if state in (STATE_CUSTOMER_REPLY, STATE_CUSTOMER_ENGAGED):
        row["merchant_attention_display_group"] = "engagement"
        row["merchant_intervention_executable"] = False
        return

    if state != STATE_NEEDS_INTERVENTION:
        row["merchant_intervention_executable"] = False
        return

    canonical_label = _norm(row.get("customer_lifecycle_label_ar"))
    needed = _norm(row.get("customer_lifecycle_merchant_needed_ar"))
    decision_key = _norm_lower(row.get("merchant_decision_key"))
    has_phone = bool(row.get("merchant_has_customer_phone"))
    wa_digits = normalize_customer_phone_for_wa_me(customer_phone_raw) if has_phone else ""

    executable = (
        needed == _MERCHANT_NEEDED_YES
        and decision_key == DECISION_CONTACT_CUSTOMER
        and bool(wa_digits)
    )

    if executable:
        body = _merchant_intervention_prefill_whatsapp_body(cart_link=cart_link)
        row["merchant_intervention_executable"] = True
        row["merchant_intervention_action_ar"] = "فتح واتساب"
        row["merchant_intervention_contact_href"] = (
            f"https://wa.me/{wa_digits}?text={quote(body, safe='')}"
        )
        row["customer_lifecycle_label_ar"] = LABEL_INTERVENTION_AR
        _sync_display_labels(row)
        return

    row["merchant_intervention_executable"] = False
    row["customer_lifecycle_label_ar"] = resolve_needs_intervention_display_label(
        canonical_label_ar=canonical_label,
        merchant_needed_ar=needed,
        decision_key=decision_key,
        has_phone=has_phone,
        log_statuses=log_statuses,
    )
    _sync_display_labels(row)


__all__ = [
    "LABEL_CANNOT_FOLLOW_AR",
    "LABEL_CANNOT_FOLLOW_NO_PHONE_AR",
    "LABEL_INTERVENTION_AR",
    "LABEL_NEEDS_SETUP_AR",
    "LABEL_SYSTEM_FOLLOWS_AR",
    "LABEL_WAITING_PHONE_AR",
    "LABEL_WAITING_READY_AR",
    "apply_attention_merchant_semantics_v1",
    "normalize_customer_phone_for_wa_me",
    "resolve_needs_intervention_display_label",
]
