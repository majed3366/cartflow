# -*- coding: utf-8 -*-
"""
Single source of truth for merchant normal-carts tab buckets, labels, and counts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

# Completed provider send only — queued is scheduling, not «تم الإرسال».
SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})

FAILED_SEND_LOG_STATUSES = frozenset(
    {"whatsapp_failed", "failed_final", "failed_retry"}
)

NEEDS_FOLLOWUP_LOG_STATUSES = frozenset(
    {
        "whatsapp_failed",
        "failed_final",
        "failed_retry",
        "skipped_user_rejected_help",
        "vip_manual_handling",
    }
)

TERMINAL_PURCHASE_LOG_STATUSES = frozenset({"stopped_converted"})

PRIMARY_WAITING = "waiting"
PRIMARY_SENT = "sent"
PRIMARY_NEEDS_FOLLOWUP = "needs_followup"
PRIMARY_CUSTOMER_ENGAGED = "customer_engaged"
PRIMARY_CUSTOMER_REPLY = "customer_reply"
PRIMARY_RETURN_TO_SITE = "return_to_site"
PRIMARY_RECOVERED = "recovered"
PRIMARY_NO_PHONE = "no_phone"

SENT_STATUS_LABEL_AR = "تم الإرسال — بانتظار تفاعل العميل"
WAITING_STATUS_LABEL_AR = "بانتظار الإرسال"
NEEDS_FOLLOWUP_STATUS_LABEL_AR = "يحتاج متابعة"
CUSTOMER_ENGAGED_CONTINUATION_LABEL_AR = "تفاعل العميل — أرسل النظام متابعة"
CUSTOMER_REPLY_LABEL_AR = "رد العميل"
RETURN_TO_SITE_LABEL_AR = "عاد العميل للموقع — أوقفنا المتابعة مؤقتًا"
RECOVERED_STATUS_LABEL_AR = "تم الاسترجاع"
NO_PHONE_STATUS_LABEL_AR = "لا يوجد رقم للتواصل"

# UI filter bar keys (merchant_app.html data-filter / data-ma-filter).
UI_FILTER_ALL = "all"
UI_FILTER_SENT = "sent"
UI_FILTER_ATTENTION = "attention"
UI_FILTER_RECOVERED = "recovered"
UI_FILTER_NOPHONE = "nophone"
UI_FILTER_WAITING = "waiting"

_PRIMARY_TO_UI_BUCKET: dict[str, str] = {
    PRIMARY_WAITING: UI_FILTER_WAITING,
    PRIMARY_SENT: UI_FILTER_SENT,
    PRIMARY_NEEDS_FOLLOWUP: UI_FILTER_ATTENTION,
    PRIMARY_CUSTOMER_ENGAGED: UI_FILTER_ATTENTION,
    PRIMARY_CUSTOMER_REPLY: UI_FILTER_ATTENTION,
    PRIMARY_RETURN_TO_SITE: UI_FILTER_SENT,
    PRIMARY_RECOVERED: UI_FILTER_RECOVERED,
    PRIMARY_NO_PHONE: UI_FILTER_NOPHONE,
}

_BUCKET_STATUS_ROW_CLASS: dict[str, str] = {
    PRIMARY_WAITING: "s-waiting",
    PRIMARY_SENT: "s-sent",
    PRIMARY_NEEDS_FOLLOWUP: "s-attention",
    PRIMARY_CUSTOMER_ENGAGED: "s-attention",
    PRIMARY_CUSTOMER_REPLY: "s-attention",
    PRIMARY_RETURN_TO_SITE: "s-sent",
    PRIMARY_RECOVERED: "s-recovered",
    PRIMARY_NO_PHONE: "s-attention",
}


@dataclass(frozen=True)
class MerchantCartRowClassification:
    primary_bucket: str
    merchant_status_label_ar: str
    next_action_label_ar: str
    is_active: bool
    is_terminal: bool
    visible_tabs: tuple[str, ...] = field(default_factory=tuple)
    merchant_cart_bucket: str = ""
    merchant_status_row_class: str = "s-waiting"
    merchant_next_action_urgent: bool = False

    def to_payload_fields(self) -> dict[str, Any]:
        return {
            "merchant_cart_primary_bucket": self.primary_bucket,
            "merchant_cart_bucket": self.merchant_cart_bucket,
            "merchant_cart_visible_tabs": list(self.visible_tabs),
            "merchant_status_label_ar": self.merchant_status_label_ar,
            "merchant_status_row_class": self.merchant_status_row_class,
            "merchant_next_action_ar": self.next_action_label_ar,
            "merchant_next_action_urgent": self.merchant_next_action_urgent,
            "merchant_cart_is_active": self.is_active,
            "merchant_cart_is_terminal": self.is_terminal,
        }


def _norm_status(raw: Optional[str]) -> str:
    return (raw or "").strip().lower()


def _log_set(log_statuses: Optional[Any]) -> frozenset[str]:
    if not log_statuses:
        return frozenset()
    if isinstance(log_statuses, frozenset):
        return log_statuses
    out: set[str] = set()
    for raw in log_statuses:
        t = _norm_status(str(raw) if raw is not None else "")
        if t:
            out.add(t)
    return frozenset(out)


def _purchased_truth(
    *,
    purchased: bool,
    cart_status: str,
    coarse: str,
    phase_key: str,
    log_ss: frozenset[str],
) -> bool:
    if purchased:
        return True
    if cart_status == "recovered":
        return True
    if coarse == "converted":
        return True
    if phase_key in ("recovery_complete", "stopped_purchase"):
        return True
    if log_ss & TERMINAL_PURCHASE_LOG_STATUSES:
        return True
    return False


def _customer_engagement_truth(
    *,
    recovery_key: str,
    log_ss: frozenset[str],
    sent_count: int,
) -> tuple[bool, bool]:
    """
    (customer_replied, continuation_started) from canonical timeline only.
    """
    rk = (recovery_key or "").strip()
    if not rk:
        return False, False
    msg_sent = bool(sent_count >= 1 or log_ss & SENT_LOG_STATUSES)
    if not msg_sent:
        return False, False
    try:
        from services.recovery_truth_timeline_v1 import (
            STATUS_CONTINUATION_STARTED,
            customer_reply_proven,
            continuation_started_proven,
        )

        if not customer_reply_proven(rk):
            return False, False
        return True, continuation_started_proven(rk)
    except Exception:  # noqa: BLE001
        return False, False


def _return_to_site_truth(
    *,
    recovery_key: str,
    phase_key: str,
    coarse: str,
    log_ss: frozenset[str],
    behavioral: Mapping[str, Any],
) -> bool:
    try:
        from services.recovery_truth_timeline_v1 import customer_reply_proven

        if recovery_key and customer_reply_proven(recovery_key):
            return False
    except Exception:  # noqa: BLE001
        pass
    pk = (phase_key or "").strip()
    cnorm = _norm_status(coarse)
    if pk == "customer_returned" or cnorm == "returned":
        return True
    if "returned_to_site" in log_ss or "user_returned" in log_ss:
        return True
    if behavioral.get("customer_returned_to_site") is True:
        return True
    if behavioral.get("user_returned_to_site") is True:
        return True
    return False


def _needs_followup_truth(
    *,
    log_ss: frozenset[str],
    coarse: str,
    phase_key: str,
    sent_count: int,
    behavioral: Mapping[str, Any],
) -> bool:
    if log_ss & NEEDS_FOLLOWUP_LOG_STATUSES:
        return True
    if log_ss & FAILED_SEND_LOG_STATUSES:
        return True
    if coarse == "blocked" or phase_key == "blocked_missing_customer_phone":
        return True
    # Sent + passive customer reply only: stay on sent tab (not needs_followup).
    if sent_count >= 1 or log_ss & SENT_LOG_STATUSES:
        if behavioral.get("customer_replied") is True:
            return False
        if coarse in ("replied", "clicked", "returned"):
            return False
    if coarse == "stopped" or phase_key == "stopped_manual":
        return True
    return False


def _sent_truth(
    *,
    sent_count: int,
    log_ss: frozenset[str],
    coarse: str,
    latest_log_status: str,
    recovery_key: str = "",
) -> bool:
    from services.recovery_truth_timeline_v1 import provider_send_proven

    if provider_send_proven(
        recovery_key,
        log_statuses=log_ss,
        sent_count=sent_count,
    ):
        return True
    return False


def _no_phone_truth(
    *,
    has_phone: bool,
    sent_count: int,
    log_ss: frozenset[str],
    phase_key: str,
    coarse: str,
    phone_blocked_before_send: bool,
) -> bool:
    if sent_count >= 1:
        return False
    if log_ss & SENT_LOG_STATUSES:
        return False
    if phone_blocked_before_send:
        return True
    if phase_key == "blocked_missing_customer_phone":
        return True
    if "skipped_no_verified_phone" in log_ss:
        return True
    if not has_phone:
        return True
    if coarse == "blocked" and sent_count < 1:
        return True
    return False


def _visible_tabs_for_primary(primary: str, *, is_active: bool) -> tuple[str, ...]:
    ui = _PRIMARY_TO_UI_BUCKET.get(primary, UI_FILTER_WAITING)
    if primary == PRIMARY_RECOVERED:
        return (UI_FILTER_ALL, UI_FILTER_RECOVERED)
    if primary == PRIMARY_NO_PHONE:
        return (UI_FILTER_ALL, UI_FILTER_NOPHONE)
    if primary == PRIMARY_SENT:
        return (UI_FILTER_ALL, UI_FILTER_SENT)
    if primary == PRIMARY_NEEDS_FOLLOWUP:
        return (UI_FILTER_ALL, UI_FILTER_ATTENTION)
    if primary == PRIMARY_CUSTOMER_ENGAGED:
        return (UI_FILTER_ALL, UI_FILTER_ATTENTION)
    if primary == PRIMARY_CUSTOMER_REPLY:
        return (UI_FILTER_ALL, UI_FILTER_ATTENTION)
    if primary == PRIMARY_RETURN_TO_SITE:
        return (UI_FILTER_ALL, UI_FILTER_SENT)
    if primary == PRIMARY_WAITING:
        if is_active:
            return (UI_FILTER_ALL, UI_FILTER_WAITING)
        return (UI_FILTER_ALL,)
    return (UI_FILTER_ALL, ui)


def classify_merchant_cart_row(
    *,
    cart: Any = None,
    logs: Optional[Any] = None,
    schedule: Any = None,
    closure: Any = None,
    purchase_truth: bool = False,
    # Explicit fields (preferred when batch-building from ORM).
    cart_status: str = "",
    has_phone: bool = True,
    sent_count: int = 0,
    log_statuses: Optional[Any] = None,
    phase_key: str = "",
    coarse: str = "",
    phone_blocked_before_send: bool = False,
    behavioral: Optional[Mapping[str, Any]] = None,
    latest_log_status: str = "",
    recovery_key: str = "",
) -> MerchantCartRowClassification:
    """
    Deterministic primary bucket for one merchant cart row.

    Precedence: recovered → no_phone (pre-send) → customer_engaged (timeline reply)
    → needs_followup → sent → waiting.
    """
    del schedule, closure  # reserved for future schedule/closure wiring
    if cart is not None:
        cart_status = cart_status or str(getattr(cart, "status", None) or "")
        if not log_statuses and logs is not None:
            log_statuses = _statuses_from_log_objects(logs)
    log_ss = _log_set(log_statuses)
    bh: Mapping[str, Any] = behavioral if isinstance(behavioral, dict) else {}
    cnorm = _norm_status(coarse)
    pk = (phase_key or "").strip()
    cst = _norm_status(cart_status)
    latest = _norm_status(latest_log_status)
    if not latest and logs:
        latest = _latest_log_status(logs)

    purchased = _purchased_truth(
        purchased=bool(purchase_truth),
        cart_status=cst,
        coarse=cnorm,
        phase_key=pk,
        log_ss=log_ss,
    )
    if purchased:
        return MerchantCartRowClassification(
            primary_bucket=PRIMARY_RECOVERED,
            merchant_status_label_ar=RECOVERED_STATUS_LABEL_AR,
            next_action_label_ar="تمت عملية الشراء — انتهت مهمة الاسترجاع.",
            is_active=False,
            is_terminal=True,
            visible_tabs=_visible_tabs_for_primary(PRIMARY_RECOVERED, is_active=False),
            merchant_cart_bucket=UI_FILTER_RECOVERED,
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_RECOVERED],
            merchant_next_action_urgent=False,
        )

    if _no_phone_truth(
        has_phone=bool(has_phone),
        sent_count=int(sent_count or 0),
        log_ss=log_ss,
        phase_key=pk,
        coarse=cnorm,
        phone_blocked_before_send=bool(phone_blocked_before_send),
    ):
        return MerchantCartRowClassification(
            primary_bucket=PRIMARY_NO_PHONE,
            merchant_status_label_ar=NO_PHONE_STATUS_LABEL_AR,
            next_action_label_ar="أضف رقم العميل ليكمل مسار الاسترجاع.",
            is_active=True,
            is_terminal=False,
            visible_tabs=_visible_tabs_for_primary(PRIMARY_NO_PHONE, is_active=True),
            merchant_cart_bucket=UI_FILTER_NOPHONE,
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_NO_PHONE],
            merchant_next_action_urgent=True,
        )

    rk_eff = (recovery_key or "").strip()
    engaged_reply, engaged_cont = _customer_engagement_truth(
        recovery_key=rk_eff,
        log_ss=log_ss,
        sent_count=int(sent_count or 0),
    )
    if engaged_reply and _sent_truth(
        sent_count=int(sent_count or 0),
        log_ss=log_ss,
        coarse=cnorm,
        latest_log_status=latest,
        recovery_key=rk_eff,
    ):
        if engaged_cont:
            status_ar = CUSTOMER_ENGAGED_CONTINUATION_LABEL_AR
            next_ar = "النظام يتابع الاعتراض — لا حاجة لرسائل إرسال إضافية آلية."
            bucket = PRIMARY_CUSTOMER_ENGAGED
        else:
            status_ar = CUSTOMER_REPLY_LABEL_AR
            next_ar = "سجّلنا رد العميل — نراقب المتابعة التلقائية."
            bucket = PRIMARY_CUSTOMER_REPLY
        return MerchantCartRowClassification(
            primary_bucket=bucket,
            merchant_status_label_ar=status_ar,
            next_action_label_ar=next_ar,
            is_active=True,
            is_terminal=False,
            visible_tabs=_visible_tabs_for_primary(bucket, is_active=True),
            merchant_cart_bucket=_PRIMARY_TO_UI_BUCKET[bucket],
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[bucket],
            merchant_next_action_urgent=False,
        )

    if _return_to_site_truth(
        recovery_key=rk_eff,
        phase_key=pk,
        coarse=cnorm,
        log_ss=log_ss,
        behavioral=bh,
    ) and _sent_truth(
        sent_count=int(sent_count or 0),
        log_ss=log_ss,
        coarse=cnorm,
        latest_log_status=latest,
        recovery_key=rk_eff,
    ):
        return MerchantCartRowClassification(
            primary_bucket=PRIMARY_RETURN_TO_SITE,
            merchant_status_label_ar=RETURN_TO_SITE_LABEL_AR,
            next_action_label_ar="عاد للموقع — المتابعة معلّقة مؤقتًا حتى يكمل أو يغادر.",
            is_active=True,
            is_terminal=False,
            visible_tabs=_visible_tabs_for_primary(
                PRIMARY_RETURN_TO_SITE, is_active=True
            ),
            merchant_cart_bucket=UI_FILTER_SENT,
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_RETURN_TO_SITE],
            merchant_next_action_urgent=False,
        )

    if _needs_followup_truth(
        log_ss=log_ss,
        coarse=cnorm,
        phase_key=pk,
        sent_count=int(sent_count or 0),
        behavioral=bh,
    ):
        next_ar = "قد تحتاج تدخل التاجر — راجع بيانات العميل أو إعدادات الربط."
        if log_ss & FAILED_SEND_LOG_STATUSES:
            next_ar = "تعذّر إرسال واتساب — راجع الربط أو رقم المتجر."
        return MerchantCartRowClassification(
            primary_bucket=PRIMARY_NEEDS_FOLLOWUP,
            merchant_status_label_ar=NEEDS_FOLLOWUP_STATUS_LABEL_AR,
            next_action_label_ar=next_ar,
            is_active=True,
            is_terminal=False,
            visible_tabs=_visible_tabs_for_primary(PRIMARY_NEEDS_FOLLOWUP, is_active=True),
            merchant_cart_bucket=UI_FILTER_ATTENTION,
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_NEEDS_FOLLOWUP],
            merchant_next_action_urgent=True,
        )

    if _sent_truth(
        sent_count=int(sent_count or 0),
        log_ss=log_ss,
        coarse=cnorm,
        latest_log_status=latest,
        recovery_key=recovery_key,
    ):
        return MerchantCartRowClassification(
            primary_bucket=PRIMARY_SENT,
            merchant_status_label_ar=SENT_STATUS_LABEL_AR,
            next_action_label_ar="تم إرسال الرسالة — ننتظر تفاعل العميل.",
            is_active=True,
            is_terminal=False,
            visible_tabs=_visible_tabs_for_primary(PRIMARY_SENT, is_active=True),
            merchant_cart_bucket=UI_FILTER_SENT,
            merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_SENT],
            merchant_next_action_urgent=False,
        )

    return MerchantCartRowClassification(
        primary_bucket=PRIMARY_WAITING,
        merchant_status_label_ar=WAITING_STATUS_LABEL_AR,
        next_action_label_ar="ستُرسل رسالة المتابعة تلقائياً وفق التوقيت الذي ضبطته.",
        is_active=True,
        is_terminal=False,
        visible_tabs=_visible_tabs_for_primary(PRIMARY_WAITING, is_active=True),
        merchant_cart_bucket=UI_FILTER_WAITING,
        merchant_status_row_class=_BUCKET_STATUS_ROW_CLASS[PRIMARY_WAITING],
        merchant_next_action_urgent=False,
    )


def _statuses_from_log_objects(logs: Any) -> frozenset[str]:
    out: set[str] = set()
    for lg in logs or ():
        st = _norm_status(getattr(lg, "status", None))
        if st:
            out.add(st)
    return frozenset(out)


def _latest_log_status(logs: Any) -> str:
    best = ""
    best_id = -1
    for lg in logs or ():
        lid = int(getattr(lg, "id", 0) or 0)
        st = _norm_status(getattr(lg, "status", None))
        if lid >= best_id and st:
            best_id = lid
            best = st
    return best


def apply_merchant_cart_classification_to_payload(
    payload: dict[str, Any],
    classification: MerchantCartRowClassification,
) -> None:
    payload.update(classification.to_payload_fields())


def merchant_cart_filter_counts_from_rows(
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Tab counts derived from visible_tabs — must match client-side row filters."""
    counts = {
        UI_FILTER_ALL: len(rows),
        UI_FILTER_SENT: 0,
        UI_FILTER_ATTENTION: 0,
        UI_FILTER_RECOVERED: 0,
        UI_FILTER_NOPHONE: 0,
        UI_FILTER_WAITING: 0,
    }
    for row in rows:
        tabs = row.get("merchant_cart_visible_tabs") or []
        if not isinstance(tabs, list):
            tabs = []
        seen: set[str] = set()
        for tab in tabs:
            tk = str(tab or "").strip().lower()
            if not tk or tk == UI_FILTER_ALL or tk in seen:
                continue
            seen.add(tk)
            if tk in counts:
                counts[tk] = int(counts[tk]) + 1
    return counts


def merchant_nav_badge_active_cart_count(rows: list[dict[str, Any]]) -> int:
    """Sidebar abandoned badge = active non-terminal rows (same classifier)."""
    n = 0
    for row in rows:
        if row.get("merchant_cart_is_terminal"):
            continue
        if row.get("merchant_cart_is_active", True):
            n += 1
    return n


def merchant_nav_badge_waiting_count(rows: list[dict[str, Any]]) -> int:
    """Sidebar «بانتظار الإرسال» badge = same filter as tab=waiting (not all active carts)."""
    return len(merchant_cart_rows_matching_filter(rows, UI_FILTER_WAITING))


# Hash ?tab= values (sidebar / URL) → filter-bar / row attribute mode.
CART_TAB_URL_TO_FILTER_MODE: dict[str, str] = {
    "all": UI_FILTER_ALL,
    "waiting": UI_FILTER_WAITING,
    "sent": UI_FILTER_SENT,
    "intervention": UI_FILTER_ATTENTION,
    "attention": UI_FILTER_ATTENTION,
    "followup": UI_FILTER_ATTENTION,
    "completed": UI_FILTER_RECOVERED,
    "recovered": UI_FILTER_RECOVERED,
    "nophone": UI_FILTER_NOPHONE,
    "no_phone": UI_FILTER_NOPHONE,
}


def cart_tab_to_filter_mode(cart_tab: Optional[str]) -> str:
    """Map dashboard cart tab (URL or sidebar) to classifier filter mode."""
    key = (cart_tab or UI_FILTER_ALL).strip().lower()
    return CART_TAB_URL_TO_FILTER_MODE.get(key, key)


def merchant_cart_row_matches_filter(
    row: Mapping[str, Any],
    filter_mode: str,
) -> bool:
    """
    Whether a row is visible for a cart tab / filter-bar mode.
    Uses primary_bucket first, then visible_tabs (same rules as JS filter).
    """
    mode = (filter_mode or UI_FILTER_ALL).strip().lower()
    if mode == UI_FILTER_ALL:
        return True
    primary = str(row.get("merchant_cart_primary_bucket") or "").strip().lower()
    if primary and primary == mode:
        return True
    ui_bucket = str(row.get("merchant_cart_bucket") or "").strip().lower()
    if ui_bucket and ui_bucket == mode:
        return True
    tabs = row.get("merchant_cart_visible_tabs") or []
    if isinstance(tabs, (list, tuple)):
        for tab in tabs:
            if str(tab or "").strip().lower() == mode:
                return True
    return False


def merchant_cart_rows_matching_filter(
    rows: list[dict[str, Any]],
    filter_mode: str,
) -> list[dict[str, Any]]:
    return [r for r in rows if merchant_cart_row_matches_filter(r, filter_mode)]
