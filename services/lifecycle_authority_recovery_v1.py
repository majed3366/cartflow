# -*- coding: utf-8 -*-
"""
Lifecycle Authority Recovery v1 — single merchant-facing lifecycle SoT.

``customer_lifecycle_state`` from ``classify_customer_lifecycle_state_v1`` is the
only lifecycle authority. Evidence sources (logs, schedules, behavioral, VIP column,
archive) feed classification; they do not own merchant lifecycle labels.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.customer_lifecycle_states_v1 import (
    LIFECYCLE_TRUTH_UNAVAILABLE_STATE,
    STATE_ARCHIVED,
    STATE_COMPLETED,
    STATE_NEEDS_INTERVENTION,
    STATE_RECOVERY_FOLLOWUP_COMPLETE,
    STATE_WAITING_CUSTOMER_REPLY,
    STATE_WAITING_FIRST_SEND,
    STATE_WAITING_NEXT_SCHEDULED,
    STATE_WAITING_PURCHASE_WINDOW,
    attach_customer_lifecycle_state_v1,
    classify_customer_lifecycle_state_v1,
    finalize_merchant_lifecycle_row_truth,
    lifecycle_filter_counts_from_rows,
)

_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"

VIP_EVIDENCE_VALUES = frozenset({"abandoned", "contacted", "closed", "converted"})

VIP_LEGACY_CARD_CLASS: dict[str, str] = {
    "contacted": "border border-blue-200/90 bg-blue-50/60",
    "converted": "border border-emerald-200/90 bg-emerald-50/50",
    "closed": "border border-slate-200/70 bg-slate-50/40 opacity-90",
    "abandoned": "border border-slate-200 bg-slate-50/80",
}

VIP_LEGACY_BADGE_CLASS: dict[str, str] = {
    "contacted": (
        "inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 "
        "text-xs font-semibold leading-tight border-blue-200 bg-blue-50 text-blue-900"
    ),
    "converted": (
        "inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 "
        "text-xs font-semibold leading-tight border-emerald-200 bg-emerald-100/90 text-emerald-900"
    ),
    "closed": (
        "inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 "
        "text-xs font-semibold leading-tight border-slate-200 bg-slate-100/80 text-slate-600"
    ),
    "abandoned": (
        "inline-flex max-w-full items-center rounded-full border px-2.5 py-0.5 "
        "text-xs font-semibold leading-tight border-slate-300 bg-slate-100 text-slate-700"
    ),
}


def _ar_num(value: int) -> str:
    n = max(0, int(value or 0))
    return "".join(_AR_DIGITS[int(ch)] for ch in str(n))


def normalize_vip_lifecycle_evidence(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in VIP_EVIDENCE_VALUES:
        return s
    return "abandoned"


def log_statuses_from_logs(
    logs: Optional[Sequence[Any]],
    *,
    session_id: str = "",
    recovery_keys: Optional[Sequence[str]] = None,
) -> tuple[frozenset[str], int, list[Any]]:
    """Evidence-only: log statuses and sent count for lifecycle classification."""
    ss: set[str] = set()
    sent_n = 0
    matched: list[Any] = []
    sid = (session_id or "").strip()
    rk_set = {str(k or "").strip() for k in (recovery_keys or ()) if str(k or "").strip()}
    sent_log = frozenset({"sent_real", "mock_sent"})
    for lg in logs or ():
        lg_sid = str(getattr(lg, "session_id", None) or "").strip()
        lg_rk = str(getattr(lg, "recovery_key", None) or "").strip()
        if sid and lg_sid == sid:
            pass
        elif lg_rk and lg_rk in rk_set:
            pass
        else:
            continue
        matched.append(lg)
        st = str(getattr(lg, "status", None) or "").strip().lower()
        if st:
            ss.add(st)
        if st in sent_log:
            sent_n += 1
    return frozenset(ss), sent_n, matched


def sync_merchant_followup_clarity_from_lifecycle(
    target: Mapping[str, Any],
    *,
    sent_count: int = 0,
    configured_count: int = 0,
) -> dict[str, Any]:
    """
    Derive follow-up display lines from lifecycle SoT — not RecoverySchedule authority.
    """
    if not isinstance(target, dict):
        return {}
    state = str(target.get("customer_lifecycle_state") or "").strip()
    sent_n = max(0, int(sent_count or 0))
    cap = max(0, int(configured_count or 0))
    out: dict[str, Any] = {
        "merchant_followup_sent_count": sent_n,
        "merchant_followup_configured_count": cap,
        "merchant_followup_progress_ar": None,
        "merchant_followup_sequence_line_ar": None,
        "merchant_followup_next_line_ar": None,
    }
    if (
        not state
        or state == LIFECYCLE_TRUTH_UNAVAILABLE_STATE
        or state in (STATE_COMPLETED, STATE_ARCHIVED)
        or cap < 1
        or sent_n < 1
    ):
        target.update(out)
        return out

    sent_show = min(sent_n, cap) if cap else sent_n
    out["merchant_followup_progress_ar"] = (
        f"تم إرسال {_ar_num(sent_show)} من {_ar_num(cap)}"
    )

    what_next = str(target.get("customer_lifecycle_what_next_ar") or "").strip()
    next_line = str(target.get("customer_lifecycle_next_followup_line_ar") or "").strip()

    if state in (
        STATE_RECOVERY_FOLLOWUP_COMPLETE,
        STATE_WAITING_CUSTOMER_REPLY,
        STATE_WAITING_PURCHASE_WINDOW,
    ):
        out["merchant_followup_sequence_line_ar"] = what_next or (
            "اكتملت سلسلة المتابعة — بانتظار تفاعل العميل"
        )
    elif state == STATE_WAITING_NEXT_SCHEDULED and next_line:
        out["merchant_followup_next_line_ar"] = next_line
    elif next_line:
        out["merchant_followup_next_line_ar"] = next_line
    elif what_next and "لا مزيد" in what_next:
        out["merchant_followup_sequence_line_ar"] = what_next

    target.update(out)
    return out


def sync_vip_legacy_display_from_lifecycle(target: dict[str, Any]) -> None:
    """Map lifecycle SoT onto legacy VIP template fields (display derivatives only)."""
    state = str(target.get("customer_lifecycle_state") or "").strip()
    label = str(
        target.get("customer_lifecycle_label_ar")
        or target.get("merchant_status_label_ar")
        or ""
    ).strip()
    vip_ev = normalize_vip_lifecycle_evidence(target.get("vip_lifecycle_status_evidence"))

    if state == STATE_COMPLETED:
        vip_ev = "converted"
    elif state == STATE_ARCHIVED:
        vip_ev = "closed"
    elif state == STATE_NEEDS_INTERVENTION and vip_ev == "abandoned":
        vip_ev = "abandoned"
    elif state == STATE_NEEDS_INTERVENTION and vip_ev == "contacted":
        vip_ev = "contacted"

    target["vip_lifecycle_status_evidence"] = vip_ev
    target["vip_lifecycle_status"] = state or vip_ev
    target["vip_lifecycle_label_ar"] = label or target.get("vip_lifecycle_label_ar")
    target["display_status_ar"] = label
    target["alert_status"] = state or vip_ev
    target["vip_lifecycle_card_class"] = VIP_LEGACY_CARD_CLASS.get(
        vip_ev, VIP_LEGACY_CARD_CLASS["abandoned"]
    )
    target["vip_lifecycle_badge_class"] = VIP_LEGACY_BADGE_CLASS.get(
        vip_ev, VIP_LEGACY_BADGE_CLASS["abandoned"]
    )
    target["vip_lifecycle_hide_actions"] = state in (STATE_ARCHIVED, STATE_COMPLETED)
    target["vip_show_wa_opened_hint"] = vip_ev == "contacted"
    target["vip_lifecycle_effective"] = state or vip_ev


def attach_merchant_row_lifecycle_authority(
    target: dict[str, Any],
    *,
    recovery_key: str = "",
    phase_key: str = "",
    coarse: str = "",
    sent_count: int = 0,
    attempt_cap: int = 1,
    log_statuses: Any = None,
    behavioral: Optional[Mapping[str, Any]] = None,
    purchase_truth: bool = False,
    cart_status: str = "",
    merchant_archived: bool = False,
    terminal_history_archived: bool = False,
    is_vip_lane: bool = False,
    has_phone: bool = True,
    abandoned_cart_id: Optional[int] = None,
    next_attempt_due_at: Optional[str] = None,
    timeline_statuses: Optional[frozenset[str]] = None,
    last_provider_sent_at: Optional[str] = None,
    matched_logs: Optional[Sequence[Any]] = None,
    schedule_prefetched: bool = False,
    effective_delay_seconds_prefetched: Optional[float] = None,
    vip_lifecycle_status_evidence: str = "",
    phase_key_evidence: str = "",
    coarse_evidence: str = "",
) -> None:
    """Attach lifecycle SoT, sync follow-up clarity, finalize consistency."""
    attach_customer_lifecycle_state_v1(
        target,
        recovery_key=recovery_key,
        phase_key=phase_key,
        coarse=coarse,
        sent_count=sent_count,
        attempt_cap=attempt_cap,
        log_statuses=log_statuses,
        behavioral=behavioral,
        purchase_truth=purchase_truth,
        cart_status=cart_status,
        merchant_archived=merchant_archived,
        terminal_history_archived=terminal_history_archived,
        is_vip_lane=is_vip_lane,
        has_phone=has_phone,
        abandoned_cart_id=abandoned_cart_id,
        next_attempt_due_at=next_attempt_due_at,
        timeline_statuses=timeline_statuses,
        last_provider_sent_at=last_provider_sent_at,
        matched_logs=matched_logs,
        schedule_prefetched=schedule_prefetched,
        effective_delay_seconds_prefetched=effective_delay_seconds_prefetched,
        vip_lifecycle_status_evidence=vip_lifecycle_status_evidence,
    )
    sync_merchant_followup_clarity_from_lifecycle(
        target,
        sent_count=sent_count,
        configured_count=attempt_cap,
    )
    if is_vip_lane:
        sync_vip_legacy_display_from_lifecycle(target)
    finalize_merchant_lifecycle_row_truth(
        target,
        recovery_key=recovery_key or str(target.get("recovery_key") or ""),
        phase_key_evidence=phase_key_evidence or phase_key,
        coarse_evidence=coarse_evidence or coarse,
    )


def lifecycle_authority_active_count(rows: Sequence[Mapping[str, Any]]) -> int:
    """Summary/nav badge: active carts from lifecycle SoT only."""
    n = 0
    for row in rows:
        sk = str(row.get("customer_lifecycle_state") or "").strip()
        if not sk or sk == LIFECYCLE_TRUTH_UNAVAILABLE_STATE:
            continue
        if sk in (STATE_ARCHIVED, STATE_COMPLETED):
            continue
        n += 1
    return n


def lifecycle_authority_waiting_count(rows: Sequence[Mapping[str, Any]]) -> int:
    counts = lifecycle_filter_counts_from_rows(list(rows))
    return int(counts.get("waiting", 0) or 0)


def enrich_message_history_rows_with_lifecycle(
    rows: list[dict[str, Any]],
    *,
    dash_store: Any,
) -> None:
    """Attach lifecycle SoT per message row from recovery_key evidence."""
    if not rows or dash_store is None:
        return
    from services.merchant_dashboard_recovery_resolve_v1 import store_slug_from_dash  # noqa: PLC0415

    slug = store_slug_from_dash(dash_store)
    if not slug:
        return

    keys: list[str] = []
    for row in rows:
        rk = str(row.get("recovery_key") or "").strip()
        if rk:
            keys.append(rk)
    if not keys:
        return

    try:
        from models import CartRecoveryLog  # noqa: PLC0415
        from extensions import db  # noqa: PLC0415

        logs = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.recovery_key.in_(list(dict.fromkeys(keys))[:80]))
            .limit(400)
            .all()
        )
    except Exception:  # noqa: BLE001
        try:
            db.session.rollback()  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001
            pass
        return

    by_rk: dict[str, list[Any]] = {}
    for lg in logs:
        rk = str(getattr(lg, "recovery_key", None) or "").strip()
        if rk:
            by_rk.setdefault(rk, []).append(lg)

    for row in rows:
        rk = str(row.get("recovery_key") or "").strip()
        if not rk:
            continue
        matched = by_rk.get(rk, [])
        log_ss, sent_n, _ = log_statuses_from_logs(matched, recovery_keys=[rk])
        payload: dict[str, Any] = {}
        attach_customer_lifecycle_state_v1(
            payload,
            recovery_key=rk,
            sent_count=sent_n,
            attempt_cap=max(2, sent_n or 1),
            log_statuses=log_ss,
            coarse="sent" if sent_n else "pending",
            matched_logs=matched,
        )
        row["customer_lifecycle_state"] = payload.get("customer_lifecycle_state")
        row["customer_lifecycle_label_ar"] = payload.get("customer_lifecycle_label_ar")
        row["lifecycle_status_ar"] = payload.get("customer_lifecycle_label_ar")


__all__ = [
    "attach_merchant_row_lifecycle_authority",
    "enrich_message_history_rows_with_lifecycle",
    "lifecycle_authority_active_count",
    "lifecycle_authority_waiting_count",
    "log_statuses_from_logs",
    "normalize_vip_lifecycle_evidence",
    "sync_merchant_followup_clarity_from_lifecycle",
    "sync_vip_legacy_display_from_lifecycle",
]
