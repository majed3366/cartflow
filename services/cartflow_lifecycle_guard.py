# -*- coding: utf-8 -*-
"""
Canonical lifecycle consistency helpers for CartFlow (read-mostly + merge pruning).

Does not change WhatsApp text, decision engine, VIP paths, recovery templates, or
duplicate prevention. Use for diagnostics, dashboard truth reconciliation, and
safe behavioral merges.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any, Optional

log = logging.getLogger("cartflow")

PREFIX_LIFECYCLE = "[CARTFLOW LIFECYCLE]"
PREFIX_STATE_CONFLICT = "[CARTFLOW STATE CONFLICT]"

# --- Canonical model (operational abstraction; not DB enums) ---
STATE_ABANDONED = "abandoned"
STATE_WAITING_DELAY = "waiting_delay"
STATE_QUEUED = "queued"
STATE_SEND_STARTED = "send_started"
STATE_SENT = "sent"
STATE_REPLIED = "replied"
STATE_RETURNED = "returned"
STATE_CONVERTED = "converted"
STATE_STOPPED = "stopped"
STATE_FAILED = "failed"
STATE_DUPLICATE_BLOCKED = "duplicate_blocked"
STATE_UNKNOWN = "unknown"

# Precedence rank: higher wins when two dashboard/merge signals contradict.
_PRECEDENCE: dict[str, int] = {
    STATE_CONVERTED: 100,
    STATE_STOPPED: 95,
    STATE_REPLIED: 88,
    STATE_RETURNED: 82,
    STATE_SENT: 75,
    STATE_FAILED: 70,
    STATE_DUPLICATE_BLOCKED: 62,
    STATE_SEND_STARTED: 55,
    STATE_QUEUED: 52,
    STATE_WAITING_DELAY: 48,
    STATE_ABANDONED: 40,
    STATE_UNKNOWN: 0,
}

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATE_ABANDONED: frozenset(
        {
            STATE_ABANDONED,
            STATE_WAITING_DELAY,
            STATE_QUEUED,
            STATE_SEND_STARTED,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
        }
    ),
    STATE_WAITING_DELAY: frozenset(
        {
            STATE_WAITING_DELAY,
            STATE_QUEUED,
            STATE_SEND_STARTED,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
            STATE_STOPPED,
        }
    ),
    STATE_QUEUED: frozenset(
        {
            STATE_QUEUED,
            STATE_SEND_STARTED,
            STATE_SENT,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
            STATE_STOPPED,
            STATE_CONVERTED,
            STATE_REPLIED,
            STATE_RETURNED,
        }
    ),
    STATE_SEND_STARTED: frozenset(
        {
            STATE_SEND_STARTED,
            STATE_SENT,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
            STATE_REPLIED,
            STATE_RETURNED,
            STATE_CONVERTED,
            STATE_STOPPED,
        }
    ),
    STATE_SENT: frozenset(
        {
            STATE_SENT,
            STATE_REPLIED,
            STATE_RETURNED,
            STATE_CONVERTED,
            STATE_STOPPED,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
            STATE_QUEUED,
        }
    ),
    STATE_FAILED: frozenset(
        {
            STATE_FAILED,
            STATE_QUEUED,
            STATE_WAITING_DELAY,
            STATE_DUPLICATE_BLOCKED,
            STATE_STOPPED,
            STATE_REPLIED,
            STATE_RETURNED,
            STATE_CONVERTED,
        }
    ),
    STATE_DUPLICATE_BLOCKED: frozenset(
        {
            STATE_DUPLICATE_BLOCKED,
            STATE_QUEUED,
            STATE_WAITING_DELAY,
            STATE_FAILED,
            STATE_STOPPED,
            STATE_REPLIED,
            STATE_RETURNED,
            STATE_CONVERTED,
        }
    ),
    STATE_REPLIED: frozenset(
        {
            STATE_REPLIED,
            STATE_RETURNED,
            STATE_CONVERTED,
            STATE_STOPPED,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
        }
    ),
    STATE_RETURNED: frozenset(
        {
            STATE_RETURNED,
            STATE_CONVERTED,
            STATE_STOPPED,
            STATE_REPLIED,
            STATE_FAILED,
            STATE_DUPLICATE_BLOCKED,
        }
    ),
    STATE_CONVERTED: frozenset({STATE_CONVERTED, STATE_STOPPED}),
    STATE_STOPPED: frozenset({STATE_STOPPED, STATE_CONVERTED}),
}

# Explicit invalid pairs (diagnostics)
_INVALID_JUMP_MESSAGES: dict[frozenset[str], str] = {
    frozenset({STATE_CONVERTED, STATE_SENT}): "sent_after_conversion",
    frozenset({STATE_CONVERTED, STATE_SEND_STARTED}): "send_after_conversion",
    frozenset({STATE_REPLIED, STATE_SENT}): "send_after_reply",
    frozenset({STATE_REPLIED, STATE_SEND_STARTED}): "send_after_reply",
    frozenset({STATE_RETURNED, STATE_SENT}): "send_after_return",
    frozenset({STATE_RETURNED, STATE_SEND_STARTED}): "send_after_return",
    frozenset({STATE_DUPLICATE_BLOCKED, STATE_SENT}): "duplicate_blocked_to_sent",
}

_LOCK = threading.Lock()
_recent_invalid_ts: deque[float] = deque(maxlen=120)
_conflict_events: deque[float] = deque(maxlen=120)
_counters: dict[str, int] = {
    "lifecycle_log": 0,
    "state_conflict_log": 0,
    "invalid_transition": 0,
    "dashboard_reconciliation": 0,
    "behavioral_prune": 0,
}

# Merchant-safe copy (dashboard hints only)
MERCHANT_SOFT_IGNORE_INCONSISTENT_AR = "تم تجاهل حالة غير متوافقة"
MERCHANT_SOFT_POST_INTERACTION_AR = "تم إيقاف الرسائل بعد تفاعل العميل"
MERCHANT_SOFT_INVALID_TRANSITION_AR = "تم منع انتقال غير صالح"


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def lifecycle_precedence_rank(state: Optional[str]) -> int:
    return int(_PRECEDENCE.get(_norm(state) or STATE_UNKNOWN, 0))


def map_recovery_log_status_to_state(status: Optional[str]) -> str:
    s = _norm(status)
    if s in ("mock_sent", "sent_real"):
        return STATE_SENT
    if s == "queued":
        return STATE_QUEUED
    if s in ("skipped_delay",):
        return STATE_WAITING_DELAY
    if s == "skipped_duplicate":
        return STATE_DUPLICATE_BLOCKED
    if s == "stopped_converted":
        return STATE_CONVERTED
    if s in ("skipped_followup_customer_replied", "skipped_user_rejected_help"):
        return STATE_REPLIED
    if s == "skipped_anti_spam":
        return STATE_RETURNED
    if s == "whatsapp_failed":
        return STATE_FAILED
    if s in ("skipped_attempt_limit", "skipped_delay_gate", "skipped_reason_template_disabled"):
        return STATE_STOPPED
    if not s:
        return STATE_UNKNOWN
    return STATE_ABANDONED


def map_lifecycle_hint_string(hint: Optional[str]) -> str:
    h = _norm(hint)
    if h in ("returned", "purchased", "converted", "purchase"):
        return STATE_RETURNED if h == "returned" else STATE_CONVERTED
    if h in ("clicked",):
        return STATE_SENT
    if h in ("interactive",):
        return STATE_REPLIED
    return STATE_UNKNOWN


def map_dashboard_phase_to_state(phase_key: Optional[str]) -> str:
    pk = (phase_key or "").strip()
    if pk in ("stopped_purchase", "recovery_complete"):
        return STATE_CONVERTED
    if pk == "behavioral_replied":
        return STATE_REPLIED
    if pk == "customer_returned":
        return STATE_RETURNED
    if pk in ("first_message_sent", "reminder_sent"):
        return STATE_SENT
    if pk == "pending_second_attempt":
        return STATE_WAITING_DELAY
    if pk in ("stopped_manual", "ignored"):
        return STATE_STOPPED
    if pk == "behavioral_link_clicked":
        return STATE_SENT
    if pk == "pending_send":
        return STATE_ABANDONED
    return STATE_UNKNOWN


def is_valid_transition(current_state: str, next_state: str) -> bool:
    cur = _norm(current_state) or STATE_UNKNOWN
    nxt = _norm(next_state) or STATE_UNKNOWN
    if cur == STATE_UNKNOWN or nxt == STATE_UNKNOWN:
        return True
    allowed = _ALLOWED_TRANSITIONS.get(cur)
    if allowed is None:
        return nxt == cur or nxt in _PRECEDENCE
    return nxt in allowed or nxt == cur


def explain_invalid_transition_pair(a: str, b: str) -> Optional[str]:
    sa, sb = _norm(a), _norm(b)
    if sa == sb:
        return None
    hi, lo = (sa, sb) if lifecycle_precedence_rank(sa) >= lifecycle_precedence_rank(sb) else (sb, sa)
    key = frozenset({hi, lo})
    return _INVALID_JUMP_MESSAGES.get(key)


def _emit(kind: str, prefix: str, **fields: Any) -> None:
    parts = [prefix, f"type={kind}"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        sval = "-" if val is None else str(val).strip().replace("\n", " ")[:220]
        parts.append(f"{key}={sval}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def emit_lifecycle_event(
    kind: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    current_state: str = "",
    attempted_state: str = "",
    detail: str = "",
) -> None:
    with _LOCK:
        _counters["lifecycle_log"] = int(_counters.get("lifecycle_log", 0)) + 1
    _emit(
        kind,
        PREFIX_LIFECYCLE,
        store_slug=(store_slug or "").strip()[:96] or "-",
        session_id=(session_id or "").strip()[:64] or "-",
        cart_id=(cart_id or "").strip()[:64] or "-",
        current_state=(current_state or "").strip()[:48] or "-",
        attempted_state=(attempted_state or "").strip()[:48] or "-",
        detail=(detail or "").strip()[:160] or "",
    )


def emit_state_conflict(
    kind: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    current_state: str = "",
    attempted_state: str = "",
    detail: str = "",
) -> None:
    with _LOCK:
        _counters["state_conflict_log"] = int(_counters.get("state_conflict_log", 0)) + 1
        _conflict_events.append(time.monotonic())
    _emit(
        kind,
        PREFIX_STATE_CONFLICT,
        store_slug=(store_slug or "").strip()[:96] or "-",
        session_id=(session_id or "").strip()[:64] or "-",
        cart_id=(cart_id or "").strip()[:64] or "-",
        current_state=(current_state or "").strip()[:48] or "-",
        attempted_state=(attempted_state or "").strip()[:48] or "-",
        detail=(detail or "").strip()[:160] or "",
    )
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
            source="lifecycle_guard",
            detail=(kind or "").strip()[:120] or "state_conflict",
        )
    except Exception:
        pass


def record_invalid_transition(
    current_state: str,
    next_state: str,
    *,
    detail: str = "",
) -> None:
    with _LOCK:
        _counters["invalid_transition"] = int(_counters.get("invalid_transition", 0)) + 1
        _recent_invalid_ts.append(time.monotonic())
        _conflict_events.append(time.monotonic())
    emit_lifecycle_event(
        "invalid_transition",
        current_state=current_state,
        attempted_state=next_state,
        detail=detail or "transition_matrix",
    )


def validate_and_log_transition(
    current_state: str,
    next_state: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """Return True if valid. Log diagnostics only when invalid (no auto-repair)."""
    if is_valid_transition(current_state, next_state):
        return True
    pair = explain_invalid_transition_pair(current_state, next_state)
    record_invalid_transition(current_state, next_state, detail=pair or "forbidden")
    emit_state_conflict(
        pair or "invalid_transition",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        current_state=current_state,
        attempted_state=next_state,
        detail="transition_validation",
    )
    return False


def _dashboard_winning_rank(
    *,
    phase_key: str,
    sent_ct: int,
    latest_log_status: Optional[str],
    behavioral: dict[str, Any],
) -> int:
    ranks: list[int] = []
    ranks.append(lifecycle_precedence_rank(map_dashboard_phase_to_state(phase_key)))
    if sent_ct >= 1:
        ranks.append(lifecycle_precedence_rank(STATE_SENT))
    ranks.append(lifecycle_precedence_rank(map_recovery_log_status_to_state(latest_log_status)))
    bh = behavioral if isinstance(behavioral, dict) else {}
    if bh.get("customer_replied") is True:
        ranks.append(lifecycle_precedence_rank(STATE_REPLIED))
    if bh.get("recovery_link_clicked") is True:
        ranks.append(lifecycle_precedence_rank(STATE_SENT))
    return max(ranks) if ranks else 0


def reconcile_normal_recovery_dashboard_hints(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    phase_key: str,
    sent_ct: int,
    latest_log_status: Optional[str],
    behavioral: dict[str, Any],
    blocker_key: Optional[str],
    blocker_bundle: Optional[dict[str, Any]],
    seq_label_ar: Optional[str],
    operational_hint_ar: Optional[str],
) -> dict[str, Any]:
    """
    Apply precedence so the dashboard does not show contradictory primary signals.
    Does not change underlying DB or recovery execution.
    """
    win = _dashboard_winning_rank(
        phase_key=phase_key,
        sent_ct=sent_ct,
        latest_log_status=latest_log_status,
        behavioral=behavioral,
    )
    out_blocker = blocker_bundle
    out_key = blocker_key
    out_seq = seq_label_ar
    out_hint = operational_hint_ar
    notes: list[str] = []

    # Stale duplicate banner after a successful send — duplicate must not imply “not sent”.
    if (
        out_key == "duplicate_attempt_blocked"
        and win >= lifecycle_precedence_rank(STATE_SENT)
        and sent_ct >= 1
    ):
        with _LOCK:
            _counters["dashboard_reconciliation"] = (
                int(_counters.get("dashboard_reconciliation", 0)) + 1
            )
        emit_state_conflict(
            "duplicate_terminal_state",
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            current_state="sent",
            attempted_state="duplicate_blocked",
            detail="dashboard Truth",
        )
        out_blocker = None
        out_key = None
        out_hint = MERCHANT_SOFT_IGNORE_INCONSISTENT_AR
        notes.append("suppressed_duplicate_after_send")

    # Conversion / purchase stop vs “sent” celebration — conversion wins.
    if (
        out_key == "purchase_completed"
        or phase_key in ("stopped_purchase", "recovery_complete")
    ) and out_seq and ("إرسال" in out_seq or "الرسالة" in out_seq):
        with _LOCK:
            _counters["dashboard_reconciliation"] = (
                int(_counters.get("dashboard_reconciliation", 0)) + 1
            )
        emit_lifecycle_event(
            "lifecycle_precedence_applied",
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            current_state="converted",
            attempted_state="sent_highlight",
            detail="dashboard_sequence",
        )
        out_seq = None
        out_hint = out_hint or MERCHANT_SOFT_POST_INTERACTION_AR
        notes.append("cleared_seq_label_after_conversion")

    # Replied / returned stronger than pending duplicate noise.
    if out_key == "duplicate_attempt_blocked" and win >= lifecycle_precedence_rank(STATE_RETURNED):
        with _LOCK:
            _counters["dashboard_reconciliation"] = (
                int(_counters.get("dashboard_reconciliation", 0)) + 1
            )
        emit_state_conflict(
            "duplicate_terminal_state",
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            current_state="returned_or_replied",
            attempted_state="duplicate_blocked",
            detail="dashboard Truth",
        )
        out_blocker = None
        out_key = None
        out_hint = MERCHANT_SOFT_IGNORE_INCONSISTENT_AR
        notes.append("suppressed_duplicate_after_return_reply")

    return {
        "blocker_bundle": out_blocker,
        "blocker_key": out_key,
        "sequence_label_ar": out_seq,
        "operational_hint_ar": out_hint,
        "lifecycle_notes": notes,
        "lifecycle_winning_rank": win,
    }


_TERMINAL_TRUTH_KEYS: frozenset[str] = frozenset(
    {
        "customer_replied",
        "user_returned_to_site",
        "customer_returned_to_site",
        "recovery_link_clicked",
    }
)


def prune_behavioral_merge_fields(
    prior: dict[str, Any],
    incoming: dict[str, Any],
    *,
    session_id: str = "",
    cart_id: str = "",
) -> dict[str, Any]:
    """
    Drop incoming patches that would weaken known terminal engagement flags.
    """
    if not isinstance(incoming, dict) or not incoming:
        return incoming if isinstance(incoming, dict) else {}
    if not isinstance(prior, dict):
        prior = {}
    pruned = dict(incoming)
    touched = False

    for tk in _TERMINAL_TRUTH_KEYS:
        if prior.get(tk) is True and pruned.get(tk) is False:
            pruned.pop(tk, None)
            touched = True
        if prior.get(tk) is True and tk in pruned and pruned.get(tk) is not True:
            if pruned.get(tk) not in (None, True):
                pruned.pop(tk, None)
                touched = True

    ph_prior = str(prior.get("lifecycle_hint") or "").strip().lower()
    ph_new = str(pruned.get("lifecycle_hint") or "").strip().lower()
    rank_prior = max(
        lifecycle_precedence_rank(map_lifecycle_hint_string(ph_prior)),
        lifecycle_precedence_rank(map_dashboard_phase_to_state(ph_prior)),
    )
    rank_new = max(
        lifecycle_precedence_rank(map_lifecycle_hint_string(ph_new)),
        lifecycle_precedence_rank(map_dashboard_phase_to_state(ph_new)),
    )
    if ph_prior and ph_new and rank_new < rank_prior:
        pruned.pop("lifecycle_hint", None)
        touched = True

    if touched:
        with _LOCK:
            _counters["behavioral_prune"] = int(_counters.get("behavioral_prune", 0)) + 1
        emit_lifecycle_event(
            "merge_precedence_applied",
            session_id=session_id,
            cart_id=cart_id,
            current_state=ph_prior or "-",
            attempted_state=ph_new or "-",
            detail="behavioral_prune",
        )

    return pruned


def invalid_transition_recently(*, within_seconds: float = 300.0) -> bool:
    now = time.monotonic()
    win = max(30.0, float(within_seconds))
    with _LOCK:
        for ts in reversed(_recent_invalid_ts):
            if now - ts <= win:
                return True
    return False


def get_lifecycle_diagnostics_readonly() -> dict[str, Any]:
    now = time.monotonic()
    win = 300.0
    with _LOCK:
        counters = dict(_counters)
        recent_conf = sum(1 for t in _conflict_events if now - t <= win)
        inv_recent = any(now - ts <= win for ts in _recent_invalid_ts)
    lifecycle_conflict_detected = recent_conf > 0 or inv_recent
    runtime_consistent = not inv_recent and counters.get("invalid_transition", 0) < 50000
    return {
        "counters": counters,
        "lifecycle_runtime_ok": bool(runtime_consistent),
        "lifecycle_conflict_detected": bool(lifecycle_conflict_detected),
        "invalid_transition_recently": bool(inv_recent),
        "runtime_state_consistent": bool(runtime_consistent),
        "lifecycle_conflict_events_recent": int(recent_conf),
    }


def reset_lifecycle_guard_for_tests() -> None:
    with _LOCK:
        _recent_invalid_ts.clear()
        _conflict_events.clear()
        for k in list(_counters.keys()):
            _counters[k] = 0
