# -*- coding: utf-8 -*-
"""
Merchant Proof Surface v1 — read-only presentation composition.

Surfaces existing engineering truth on merchant dashboard rows without minting
new evidence (Proof of Value Governance PG-3, PV-1, PV-11).

Does not modify Purchase Truth, Lifecycle Truth, or Provider Reliability modules.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

PROOF_SURFACE_VERSION = "v1"

# Proof domains (foundation §2)
DOMAIN_RECOVERY = "recovery"
DOMAIN_UNDERSTANDING = "understanding"
DOMAIN_DECISION = "decision"
DOMAIN_OPERATIONAL = "operational"

# Confidence (governance §7)
CONF_CONFIRMED = "confirmed"
CONF_HIGH = "high"
CONF_MEDIUM = "medium"
CONF_LOW = "low"
CONF_UNKNOWN = "unknown"

CONFIDENCE_AR = {
    CONF_CONFIRMED: "مؤكد",
    CONF_HIGH: "مرتفع",
    CONF_MEDIUM: "متوسط",
    CONF_LOW: "منخفض",
    CONF_UNKNOWN: "غير معروف",
}

# Evidence types (merchant-facing labels in evidence_source_ar)
EVIDENCE_LIFECYCLE = "lifecycle_truth"
EVIDENCE_RECOVERY = "recovery_truth"
EVIDENCE_PURCHASE = "purchase_truth"
EVIDENCE_PROVIDER = "provider_truth"
EVIDENCE_REASON = "reason_capture"

EVIDENCE_SOURCE_AR = {
    EVIDENCE_LIFECYCLE: "حالة دورة العميل (Lifecycle Truth)",
    EVIDENCE_RECOVERY: "سجل الاسترجاع (Recovery Truth)",
    EVIDENCE_PURCHASE: "تأكيد الشراء (Purchase Truth)",
    EVIDENCE_PROVIDER: "حالة التسليم (Provider Truth)",
    EVIDENCE_REASON: "سبب التردد المُسجَّل",
}

_ACCEPTANCE_LOGS = frozenset({"sent_real", "mock_sent"})
_STOP_LOGS = frozenset(
    {
        "stopped_converted",
        "skipped_duplicate",
        "stopped_user_rejected",
        "skipped_user_rejected_help",
    }
)
_FAIL_LOGS = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})

_STEP_SCHEDULED = "scheduled"
_STEP_MESSAGE_ACCEPTED = "message_accepted"
_STEP_PROVIDER_DELIVERED = "provider_delivered"
_STEP_CUSTOMER_PURCHASED = "customer_purchased"
_STEP_RECOVERY_STOPPED = "recovery_stopped"

STEP_LABEL_AR = {
    _STEP_SCHEDULED: "جدولة الإرسال",
    _STEP_MESSAGE_ACCEPTED: "قبول المزود للرسالة",
    _STEP_PROVIDER_DELIVERED: "تسليم الرسالة للعميل",
    _STEP_CUSTOMER_PURCHASED: "إتمام الشراء",
    _STEP_RECOVERY_STOPPED: "إيقاف مسار الاسترجاع",
}

_STATE_DONE = "done"
_STATE_ACTIVE = "active"
_STATE_PENDING = "pending"
_STATE_SKIPPED = "skipped"
_STATE_UNKNOWN = "unknown"
_STATE_FAILED = "failed"


def _log_set(log_statuses: Optional[Iterable[str]]) -> frozenset[str]:
    out: set[str] = set()
    for raw in log_statuses or ():
        s = (str(raw) or "").strip().lower()
        if s:
            out.add(s)
    return frozenset(out)


def _confidence_ar(level: str) -> str:
    return CONFIDENCE_AR.get((level or "").strip().lower(), CONFIDENCE_AR[CONF_UNKNOWN])


def _step(
    *,
    key: str,
    state: str,
    confidence: str,
    evidence_type: str,
    note_ar: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label_ar": STEP_LABEL_AR.get(key, key),
        "state": state,
        "confidence": confidence,
        "confidence_ar": _confidence_ar(confidence),
        "evidence_type": evidence_type,
        "note_ar": (note_ar or "").strip() or None,
    }


def _delivery_step_from_truth(
    *,
    acceptance_reached: bool,
    delivery_truth: Any,
) -> dict[str, Any]:
    if not acceptance_reached:
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_SKIPPED,
            confidence=CONF_UNKNOWN,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="لم تُقبل رسالة بعد",
        )
    if delivery_truth is None:
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_UNKNOWN,
            confidence=CONF_UNKNOWN,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="بانتظار تأكيد التسليم — لم يصل دليل تسليم بعد",
        )
    level = str(getattr(delivery_truth, "truth_level", "") or "").strip()
    if level == "failed_delivery":
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_FAILED,
            confidence=CONF_CONFIRMED,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="تعذّر تسليم الرسالة للعميل",
        )
    if level in ("read_by_customer", "delivered_to_customer"):
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_DONE,
            confidence=CONF_CONFIRMED,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="وصلت الرسالة للعميل",
        )
    if level == "sent_to_network":
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_ACTIVE,
            confidence=CONF_MEDIUM,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="وصلت لشبكة المزود — لم يُؤكَّد وصولها للعميل بعد",
        )
    if level == "accepted_by_provider":
        return _step(
            key=_STEP_PROVIDER_DELIVERED,
            state=_STATE_UNKNOWN,
            confidence=CONF_UNKNOWN,
            evidence_type=EVIDENCE_PROVIDER,
            note_ar="قُبلت من المزود — بانتظار تأكيد التسليم",
        )
    return _step(
        key=_STEP_PROVIDER_DELIVERED,
        state=_STATE_UNKNOWN,
        confidence=CONF_UNKNOWN,
        evidence_type=EVIDENCE_PROVIDER,
        note_ar="بانتظار تأكيد التسليم",
    )


def _lookup_delivery_truth(latest_log: Any) -> Any:
    sid = ""
    if latest_log is not None:
        sid = (getattr(latest_log, "provider_message_sid", None) or "").strip()
    if not sid:
        return None
    try:
        from services.whatsapp_delivery_truth_v1 import get_delivery_truth  # noqa: PLC0415

        return get_delivery_truth(sid[:128])
    except Exception:  # noqa: BLE001
        return None


def build_recovery_proof_steps(
    *,
    purchase_truth: bool = False,
    log_statuses: Optional[Iterable[str]] = None,
    next_attempt_due_at: Optional[str] = None,
    sent_count: int = 0,
    customer_lifecycle_state: str = "",
    latest_log: Any = None,
) -> list[dict[str, Any]]:
    """Map existing recovery signals to governed proof steps (presentation only)."""
    logs = _log_set(log_statuses)
    lc = (customer_lifecycle_state or "").strip().lower()
    sent_n = max(0, int(sent_count or 0))
    acceptance = bool(logs & _ACCEPTANCE_LOGS) or sent_n > 0
    scheduled_hint = bool((next_attempt_due_at or "").strip()) or "scheduled" in logs

    if acceptance:
        sched_state = _STATE_DONE
        sched_conf = CONF_CONFIRMED
        sched_note = "تمت جدولة الإرسال وبدء المسار"
    elif scheduled_hint:
        sched_state = _STATE_ACTIVE
        sched_conf = CONF_MEDIUM
        sched_note = "الإرسال مجدول — لم تُرسل رسالة بعد"
    else:
        sched_state = _STATE_PENDING
        sched_conf = CONF_UNKNOWN
        sched_note = "لم يبدأ مسار الإرسال بعد"

    steps: list[dict[str, Any]] = [
        _step(
            key=_STEP_SCHEDULED,
            state=sched_state,
            confidence=sched_conf,
            evidence_type=EVIDENCE_RECOVERY,
            note_ar=sched_note,
        )
    ]

    if acceptance:
        msg_state = _STATE_DONE
        msg_conf = CONF_CONFIRMED
        msg_note = "قبل المزود الرسالة — هذا لا يعني بالضرورة وصولها للعميل"
    elif scheduled_hint:
        msg_state = _STATE_PENDING
        msg_conf = CONF_MEDIUM
        msg_note = "بانتظار الإرسال"
    else:
        msg_state = _STATE_SKIPPED
        msg_conf = CONF_UNKNOWN
        msg_note = "لا توجد رسالة مقبولة"

    steps.append(
        _step(
            key=_STEP_MESSAGE_ACCEPTED,
            state=msg_state,
            confidence=msg_conf,
            evidence_type=EVIDENCE_RECOVERY,
            note_ar=msg_note,
        )
    )

    delivery_truth = _lookup_delivery_truth(latest_log) if acceptance else None
    steps.append(
        _delivery_step_from_truth(
            acceptance_reached=acceptance,
            delivery_truth=delivery_truth,
        )
    )

    if purchase_truth or lc == "completed":
        purch_state = _STATE_DONE
        purch_conf = CONF_CONFIRMED
        purch_note = "تم تأكيد الشراء"
    else:
        purch_state = _STATE_PENDING
        purch_conf = CONF_UNKNOWN
        purch_note = "لم يُؤكَّد شراء بعد"

    steps.append(
        _step(
            key=_STEP_CUSTOMER_PURCHASED,
            state=purch_state,
            confidence=purch_conf,
            evidence_type=EVIDENCE_PURCHASE,
            note_ar=purch_note,
        )
    )

    stopped = (
        purchase_truth
        or lc in ("completed", "archived", "recovery_followup_complete")
        or bool(logs & _STOP_LOGS)
        or bool(logs & _FAIL_LOGS and not acceptance)
    )
    if stopped:
        stop_state = _STATE_DONE
        stop_conf = CONF_CONFIRMED if purchase_truth else CONF_MEDIUM
        if purchase_truth:
            stop_note = "توقّف المسار بعد الشراء"
        elif logs & _STOP_LOGS:
            stop_note = "توقّف المسار تلقائياً"
        elif logs & _FAIL_LOGS:
            stop_note = "توقّف أو تعذّر الإرسال"
        else:
            stop_note = "المسار منتهٍ أو متوقف"
    elif acceptance:
        stop_state = _STATE_ACTIVE
        stop_conf = CONF_MEDIUM
        stop_note = "المسار نشط — ننتظر تفاعل العميل"
    else:
        stop_state = _STATE_PENDING
        stop_conf = CONF_UNKNOWN
        stop_note = "لم يُوقَف المسار بعد"

    steps.append(
        _step(
            key=_STEP_RECOVERY_STOPPED,
            state=stop_state,
            confidence=stop_conf,
            evidence_type=EVIDENCE_RECOVERY,
            note_ar=stop_note,
        )
    )
    return steps


def resolve_row_proof_confidence(
    *,
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    reason_tag: str = "",
    recovery_steps: Optional[list[dict[str, Any]]] = None,
) -> str:
    """Weakest-link confidence for the row proof bundle (MT-C-1)."""
    if purchase_truth:
        return CONF_CONFIRMED
    lc = (customer_lifecycle_state or "").strip().lower()
    if lc and lc not in ("", "unknown"):
        base = CONF_CONFIRMED
    else:
        base = CONF_UNKNOWN
    steps = recovery_steps or []
    rank = {
        CONF_CONFIRMED: 4,
        CONF_HIGH: 3,
        CONF_MEDIUM: 2,
        CONF_LOW: 1,
        CONF_UNKNOWN: 0,
    }
    weakest = base
    for st in steps:
        c = str(st.get("confidence") or CONF_UNKNOWN)
        if rank.get(c, 0) < rank.get(weakest, 0):
            weakest = c
    if not (reason_tag or "").strip() and rank.get(weakest, 0) > rank[CONF_UNKNOWN]:
        if weakest == CONF_CONFIRMED:
            weakest = CONF_MEDIUM
    return weakest


def resolve_primary_proof_domain(
    *,
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    merchant_decision_key: str = "",
) -> str:
    if purchase_truth:
        return DOMAIN_RECOVERY
    if (merchant_decision_key or "").strip():
        return DOMAIN_DECISION
    lc = (customer_lifecycle_state or "").strip().lower()
    if lc in ("needs_intervention", "waiting_customer_reply", "customer_reply"):
        return DOMAIN_DECISION
    return DOMAIN_UNDERSTANDING


def build_merchant_proof_surface_v1(
    *,
    recovery_key: str = "",
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    customer_lifecycle_what_happened_ar: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    next_attempt_due_at: Optional[str] = None,
    sent_count: int = 0,
    reason_tag: str = "",
    merchant_decision_key: str = "",
    latest_log: Any = None,
) -> dict[str, Any]:
    """Compose merchant-visible proof metadata from existing row inputs."""
    steps = build_recovery_proof_steps(
        purchase_truth=purchase_truth,
        log_statuses=log_statuses,
        next_attempt_due_at=next_attempt_due_at,
        sent_count=sent_count,
        customer_lifecycle_state=customer_lifecycle_state,
        latest_log=latest_log,
    )
    confidence = resolve_row_proof_confidence(
        purchase_truth=purchase_truth,
        customer_lifecycle_state=customer_lifecycle_state,
        reason_tag=reason_tag,
        recovery_steps=steps,
    )
    domain = resolve_primary_proof_domain(
        purchase_truth=purchase_truth,
        customer_lifecycle_state=customer_lifecycle_state,
        merchant_decision_key=merchant_decision_key,
    )
    rk = (recovery_key or "").strip()
    what_happened = (customer_lifecycle_what_happened_ar or "").strip()
    if not what_happened and purchase_truth:
        what_happened = "تم تأكيد شراء العميل"
    why_parts: list[str] = []
    if lc_label := (customer_lifecycle_state or "").strip():
        why_parts.append(f"حالة المسار: {lc_label}")
    if (reason_tag or "").strip():
        why_parts.append("سبب التردد مسجّل")
    if purchase_truth:
        why_parts.append("Purchase Truth")
    if any(s.get("state") == _STATE_DONE for s in steps if s.get("key") == _STEP_MESSAGE_ACCEPTED):
        why_parts.append("سجل إرسال مقبول")
    why_we_know = " — ".join(why_parts) if why_parts else "بيانات محدودة — الثقة منخفضة"

    evidence_type = EVIDENCE_PURCHASE if purchase_truth else EVIDENCE_LIFECYCLE
    if domain == DOMAIN_RECOVERY:
        evidence_type = EVIDENCE_RECOVERY if not purchase_truth else EVIDENCE_PURCHASE

    return {
        "version": PROOF_SURFACE_VERSION,
        "primary_domain": domain,
        "confidence": confidence,
        "confidence_ar": _confidence_ar(confidence),
        "evidence_type": evidence_type,
        "evidence_source_ar": EVIDENCE_SOURCE_AR.get(
            evidence_type, EVIDENCE_SOURCE_AR[EVIDENCE_LIFECYCLE]
        ),
        "proof_source": rk[:512] if rk else None,
        "what_happened_ar": what_happened or None,
        "why_we_know_ar": why_we_know,
        "recovery_steps": steps,
    }


def attach_merchant_proof_surface_v1(
    target: Mapping[str, Any] | dict[str, Any],
    *,
    recovery_key: str = "",
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    customer_lifecycle_what_happened_ar: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    next_attempt_due_at: Optional[str] = None,
    sent_count: int = 0,
    reason_tag: str = "",
    merchant_decision_key: str = "",
    latest_log: Any = None,
) -> None:
    """Attach ``merchant_proof_surface_v1`` dict to a normal-carts row (additive)."""
    if not isinstance(target, dict):
        return
    rk = (recovery_key or target.get("recovery_key") or "").strip()
    bundle = build_merchant_proof_surface_v1(
        recovery_key=rk,
        purchase_truth=bool(
            purchase_truth or target.get("customer_lifecycle_completed_variant") == "purchased"
        ),
        customer_lifecycle_state=str(
            customer_lifecycle_state or target.get("customer_lifecycle_state") or ""
        ),
        customer_lifecycle_what_happened_ar=str(
            customer_lifecycle_what_happened_ar
            or target.get("customer_lifecycle_what_happened_ar")
            or ""
        ),
        log_statuses=log_statuses,
        next_attempt_due_at=next_attempt_due_at or target.get("next_attempt_due_at"),
        sent_count=sent_count,
        reason_tag=str(reason_tag or target.get("reason_tag") or ""),
        merchant_decision_key=str(
            merchant_decision_key or target.get("merchant_decision_key") or ""
        ),
        latest_log=latest_log,
    )
    target["merchant_proof_surface_v1"] = bundle


__all__ = [
    "PROOF_SURFACE_VERSION",
    "attach_merchant_proof_surface_v1",
    "build_merchant_proof_surface_v1",
    "build_recovery_proof_steps",
    "resolve_primary_proof_domain",
    "resolve_row_proof_confidence",
]
