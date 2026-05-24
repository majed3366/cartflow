# -*- coding: utf-8 -*-
"""
Canonical lifecycle truth evaluator v1 (shadow / observation only).

Single answer to: "What is the final truth NOW?" for a recovery session.

Precedence (explicit, audited — do not reorder without updating tests):
  purchase > reply > return > waiting > send

Special terminal states (evaluated inside tiers where noted):
  cancelled, vip_manual, failed

Does not change recovery execution, WhatsApp, delays, purchase truth writes,
or dashboard rendering. Shadow mode logs ``[LIFECYCLE TRUTH MISMATCH]`` only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from services.cartflow_merchant_lifecycle_precedence import (
    lifecycle_delay_scheduling_only,
    lifecycle_purchased_evidence,
    lifecycle_replied_evidence,
    lifecycle_returned_evidence,
    recovery_log_statuses_lower,
)
from services.lifecycle_intelligence import (
    BEHAVIOR_CUSTOMER_REPLIED,
    BEHAVIOR_DELAY_WAITING,
    BEHAVIOR_IGNORED,
    BEHAVIOR_PURCHASE_COMPLETED,
    BEHAVIOR_RETURNED_TO_SITE,
    BEHAVIOR_UNKNOWN,
    LifecycleDecisionResult,
)

log = logging.getLogger("cartflow")

# --- Canonical states (product vocabulary) ---
CANONICAL_PURCHASED = "purchased"
CANONICAL_REPLIED = "replied"
CANONICAL_RETURNED = "returned"
CANONICAL_WAITING = "waiting"
CANONICAL_SENT = "sent"
CANONICAL_FAILED = "failed"
CANONICAL_VIP_MANUAL = "vip_manual"
CANONICAL_CANCELLED = "cancelled"

CANONICAL_STATES = frozenset(
    {
        CANONICAL_PURCHASED,
        CANONICAL_REPLIED,
        CANONICAL_RETURNED,
        CANONICAL_WAITING,
        CANONICAL_SENT,
        CANONICAL_FAILED,
        CANONICAL_VIP_MANUAL,
        CANONICAL_CANCELLED,
    }
)

_HARD_TERMINAL = frozenset(
    {CANONICAL_PURCHASED, CANONICAL_CANCELLED, CANONICAL_VIP_MANUAL}
)
_SOFT_TERMINAL = frozenset({CANONICAL_RETURNED, CANONICAL_REPLIED})

_SENT_LOG_STATUSES = frozenset({"mock_sent", "sent_real"})
_FAILED_LOG_STATUSES = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})
_CANCELLED_SCHEDULE_MARKERS = frozenset({"cancelled", "purchase_truth_stop"})

MERCHANT_MESSAGE_AR: dict[str, str] = {
    CANONICAL_PURCHASED: "تم الشراء — أوقفنا المتابعة",
    CANONICAL_RETURNED: "عاد العميل — لن نزعجه حالياً",
    CANONICAL_WAITING: "بانتظار الوقت المناسب",
    CANONICAL_REPLIED: "تفاعل العميل مع الرسالة — لن نرسل متابعة تلقائية الآن",
    CANONICAL_SENT: "تم إرسال رسالة استرجاع",
    CANONICAL_FAILED: "تعذّر إرسال واتساب — راجع الإعدادات أو حاول لاحقاً",
    CANONICAL_VIP_MANUAL: "يتم التعامل مع هذه السلة يدوياً",
    CANONICAL_CANCELLED: "أُلغيت المتابعة التلقائية",
}


@dataclass(frozen=True)
class LifecycleTruthResult:
    canonical_state: str
    terminal: bool
    reason: str
    source: str
    merchant_message: str


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _merchant_message(state: str) -> str:
    return MERCHANT_MESSAGE_AR.get(state, MERCHANT_MESSAGE_AR[CANONICAL_WAITING])


def _result(
    *,
    canonical_state: str,
    reason: str,
    source: str,
    terminal: Optional[bool] = None,
) -> LifecycleTruthResult:
    st = canonical_state if canonical_state in CANONICAL_STATES else CANONICAL_WAITING
    term = (
        terminal
        if terminal is not None
        else (st in _HARD_TERMINAL or st in _SOFT_TERMINAL)
    )
    return LifecycleTruthResult(
        canonical_state=st,
        terminal=bool(term),
        reason=reason,
        source=source,
        merchant_message=_merchant_message(st),
    )


def _purchase_evidence(
    *,
    purchased: bool,
    recovery_key: str,
    ls: str,
    bk: str,
    pk: str,
    cr: str,
    log_ss: frozenset[str],
) -> bool:
    if purchased:
        return True
    if lifecycle_purchased_evidence(
        ls=ls, bk=bk, pk=pk, cr=cr, log_ss=log_ss
    ):
        return True
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    try:
        from services.cartflow_purchase_truth import has_purchase

        return bool(has_purchase(rk))
    except Exception:  # noqa: BLE001
        return False


def _cancelled_evidence(
    *,
    schedule_status: str,
    schedule_last_error: str,
    log_ss: frozenset[str],
) -> bool:
    ss = _norm(schedule_status)
    err = _norm(schedule_last_error)
    if ss == "cancelled":
        return True
    if "purchase_truth_stop" in err:
        return True
    return bool(log_ss & _CANCELLED_SCHEDULE_MARKERS)


def _vip_manual_evidence(*, ls: str, log_ss: frozenset[str]) -> bool:
    return ls == "vip_manual_handling" or "vip_manual_handling" in log_ss


def _failed_evidence(*, ls: str, log_ss: frozenset[str]) -> bool:
    return ls in _FAILED_LOG_STATUSES or bool(log_ss & _FAILED_LOG_STATUSES)


def _sent_evidence(*, ls: str, log_ss: frozenset[str], sent_ct: int) -> bool:
    if sent_ct > 0:
        return True
    if ls in _SENT_LOG_STATUSES:
        return True
    return bool(log_ss & _SENT_LOG_STATUSES)


def evaluate_lifecycle_truth(
    *,
    recovery_key: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    purchased: bool = False,
    replied: bool = False,
    returned: bool = False,
    delay_pending: bool = False,
    ignored: bool = False,
    reason_tag: Optional[str] = None,
    attempt_count: int = 0,
    phase_key: str = "",
    coarse: str = "",
    blocker_key: str = "",
    latest_log_status: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    behavioral: Optional[dict[str, Any]] = None,
    sent_ct: int = 0,
    schedule_status: str = "",
    schedule_last_error: str = "",
    dashboard_return_track: bool = False,
    dashboard_return_intel_panel: bool = False,
) -> LifecycleTruthResult:
    """
    Canonical lifecycle owner — one state per evaluation.

    Precedence: purchase > reply > return > waiting > send
    (cancelled / vip_manual / failed evaluated at documented tiers).
    """
    bh = behavioral if isinstance(behavioral, dict) else {}
    log_ss = recovery_log_statuses_lower(log_statuses)
    ls = _norm(latest_log_status)
    pk = _norm(phase_key)
    bk = _norm(blocker_key)
    cr = _norm(coarse)
    _ = reason_tag, attempt_count, store_slug, session_id, cart_id  # reserved for v2

    # --- Tier 1: purchase (highest) ---
    if _purchase_evidence(
        purchased=purchased,
        recovery_key=recovery_key,
        ls=ls,
        bk=bk,
        pk=pk,
        cr=cr,
        log_ss=log_ss,
    ):
        return _result(
            canonical_state=CANONICAL_PURCHASED,
            reason="purchase_evidence",
            source="precedence:purchase",
            terminal=True,
        )

    # Cancelled durable schedule (terminal, still below purchase)
    if _cancelled_evidence(
        schedule_status=schedule_status,
        schedule_last_error=schedule_last_error,
        log_ss=log_ss,
    ):
        return _result(
            canonical_state=CANONICAL_CANCELLED,
            reason="schedule_or_log_cancelled",
            source="precedence:cancelled",
            terminal=True,
        )

    # VIP manual handling (blocks automation; below purchase)
    if _vip_manual_evidence(ls=ls, log_ss=log_ss):
        return _result(
            canonical_state=CANONICAL_VIP_MANUAL,
            reason="vip_manual_handling",
            source="precedence:vip_manual",
            terminal=True,
        )

    # --- Tier 2: reply (before return — audited product precedence) ---
    if replied or lifecycle_replied_evidence(
        bh=bh, ls=ls, bk=bk, pk=pk, log_ss=log_ss
    ):
        return _result(
            canonical_state=CANONICAL_REPLIED,
            reason="customer_replied",
            source="precedence:reply",
            terminal=True,
        )

    # --- Tier 3: return ---
    if returned or lifecycle_returned_evidence(
        bh=bh,
        ls=ls,
        bk=bk,
        pk=pk,
        cr=cr,
        log_ss=log_ss,
        dashboard_return_track=dashboard_return_track,
        dashboard_return_intel_panel=dashboard_return_intel_panel,
    ):
        return _result(
            canonical_state=CANONICAL_RETURNED,
            reason="user_returned",
            source="precedence:return",
            terminal=True,
        )

    # Failed send (after behavioral tiers; before delay/send story)
    if _failed_evidence(ls=ls, log_ss=log_ss):
        return _result(
            canonical_state=CANONICAL_FAILED,
            reason="whatsapp_send_failed",
            source="precedence:failed",
            terminal=False,
        )

    # --- Tier 4: waiting / delay ---
    if delay_pending or ignored or lifecycle_delay_scheduling_only(
        ls=ls,
        pk=pk,
        purchased=False,
        replied=False,
        returned=False,
    ):
        reason = "delay_not_elapsed" if delay_pending else "scheduling_or_pending"
        if ignored:
            reason = "awaiting_followup_attempt"
        return _result(
            canonical_state=CANONICAL_WAITING,
            reason=reason,
            source="precedence:waiting",
            terminal=False,
        )

    # --- Tier 5: send ---
    if _sent_evidence(ls=ls, log_ss=log_ss, sent_ct=int(sent_ct or 0)):
        return _result(
            canonical_state=CANONICAL_SENT,
            reason="recovery_message_sent",
            source="precedence:send",
            terminal=False,
        )

    return _result(
        canonical_state=CANONICAL_WAITING,
        reason="no_stronger_signal",
        source="precedence:default",
        terminal=False,
    )


# --- Shadow mode: legacy vs canonical ---

_INTELLIGENCE_BEHAVIOR_TO_CANONICAL: dict[str, str] = {
    BEHAVIOR_PURCHASE_COMPLETED: CANONICAL_PURCHASED,
    BEHAVIOR_RETURNED_TO_SITE: CANONICAL_RETURNED,
    BEHAVIOR_CUSTOMER_REPLIED: CANONICAL_REPLIED,
    BEHAVIOR_DELAY_WAITING: CANONICAL_WAITING,
    BEHAVIOR_IGNORED: CANONICAL_WAITING,
    BEHAVIOR_UNKNOWN: CANONICAL_WAITING,
}


def legacy_canonical_from_intelligence(
    intelligence_result: LifecycleDecisionResult | dict[str, Any],
) -> str:
    """Legacy truth at observe sites: lifecycle_intelligence behavior label only.

    Intelligence uses return-before-reply; canonical uses reply-before-return.
    """
    behavior = (intelligence_result or {}).get("behavior", "")
    return _INTELLIGENCE_BEHAVIOR_TO_CANONICAL.get(
        str(behavior or "").strip(),
        CANONICAL_WAITING,
    )


def _emit_lifecycle_truth_mismatch(**fields: Any) -> None:
    parts = ["[LIFECYCLE TRUTH MISMATCH]"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        parts.append(f"{key}={str(val)[:220] if val is not None else '-'}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.warning("%s", line)


def shadow_compare_at_intelligence_observe(
    *,
    intelligence_result: LifecycleDecisionResult | dict[str, Any],
    recovery_key: str = "",
    session_id: str = "",
    purchased: bool = False,
    replied: bool = False,
    returned: bool = False,
    delay_pending: bool = False,
    ignored: bool = False,
    reason_tag: Optional[str] = None,
    attempt_count: int = 0,
    latest_log_status: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    phase_key: str = "",
    coarse: str = "",
    blocker_key: str = "",
    behavioral: Optional[dict[str, Any]] = None,
    sent_ct: int = 0,
) -> LifecycleTruthResult:
    """
    Compare legacy (lifecycle_intelligence) vs canonical evaluator; log on diff.

    Observation only — no side effects on recovery paths.
    """
    canonical = evaluate_lifecycle_truth(
        recovery_key=recovery_key,
        session_id=session_id,
        purchased=purchased,
        replied=replied,
        returned=returned,
        delay_pending=delay_pending,
        ignored=ignored,
        reason_tag=reason_tag,
        attempt_count=attempt_count,
        latest_log_status=latest_log_status,
        log_statuses=log_statuses,
        phase_key=phase_key,
        coarse=coarse,
        blocker_key=blocker_key,
        behavioral=behavioral,
        sent_ct=sent_ct,
    )
    legacy = legacy_canonical_from_intelligence(intelligence_result)
    if legacy != canonical.canonical_state:
        intel = intelligence_result or {}
        _emit_lifecycle_truth_mismatch(
            recovery_key=(recovery_key or "-")[:120],
            session_id=(session_id or "-")[:80],
            legacy_canonical=legacy,
            canonical_canonical=canonical.canonical_state,
            legacy_behavior=intel.get("behavior", "-"),
            legacy_decision=intel.get("decision", "-"),
            canonical_reason=canonical.reason,
            canonical_source=canonical.source,
            purchased=bool(purchased),
            replied=bool(replied),
            returned=bool(returned),
            delay_pending=bool(delay_pending),
        )
    return canonical


__all__ = [
    "CANONICAL_CANCELLED",
    "CANONICAL_FAILED",
    "CANONICAL_PURCHASED",
    "CANONICAL_REPLIED",
    "CANONICAL_RETURNED",
    "CANONICAL_SENT",
    "CANONICAL_STATES",
    "CANONICAL_VIP_MANUAL",
    "CANONICAL_WAITING",
    "LifecycleTruthResult",
    "MERCHANT_MESSAGE_AR",
    "evaluate_lifecycle_truth",
    "legacy_canonical_from_intelligence",
    "shadow_compare_at_intelligence_observe",
]
