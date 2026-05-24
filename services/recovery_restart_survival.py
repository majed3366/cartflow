# -*- coding: utf-8 -*-
"""
Restart survival for delayed recoveries — durable schedule rows + resume scan.

Integration-ready: keyed by recovery_key / store_slug / session / cart (Zid/Salla/Shopify).
Does not replace in-process asyncio tasks; complements them with DB-backed due_at.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule

_log = logging.getLogger("cartflow")

STATUS_SCHEDULED = "scheduled"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_SKIPPED_RESUME = "skipped_resume_unsafe"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_FAILED_RESUME = "failed_resume"
STATUS_FAILED_RESUME_STALE = "failed_resume_stale"
STATUS_SKIPPED_DUPLICATE = "skipped_duplicate"
STATUS_SKIPPED_NO_PHONE = "skipped_no_phone"
STATUS_SKIPPED_NO_REASON = "skipped_no_reason"
STATUS_WHATSAPP_FAILED = "whatsapp_failed"

_TERMINAL = frozenset(
    {
        STATUS_COMPLETED,
        STATUS_CANCELLED,
        STATUS_SKIPPED_RESUME,
        STATUS_NEEDS_REVIEW,
        STATUS_FAILED_RESUME,
        STATUS_FAILED_RESUME_STALE,
        STATUS_SKIPPED_DUPLICATE,
        STATUS_SKIPPED_NO_PHONE,
        STATUS_SKIPPED_NO_REASON,
        STATUS_WHATSAPP_FAILED,
    }
)

# Completed must not be downgraded to failed/skipped without explicit override + log.
_PROTECTED_TERMINAL_NO_DOWNGRADE = frozenset({STATUS_COMPLETED})

_DEFAULT_RUNNING_STALE_SECONDS = 600


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _step_keys(
    *,
    multi_slot_index: Optional[int],
    sequential_attempt_index: Optional[int],
) -> tuple[int, int]:
    if sequential_attempt_index is not None:
        try:
            step = max(1, int(sequential_attempt_index))
        except (TypeError, ValueError):
            step = 1
    elif multi_slot_index is not None:
        try:
            step = max(1, int(multi_slot_index))
        except (TypeError, ValueError):
            step = 1
    else:
        step = 1
    msi = int(multi_slot_index) if multi_slot_index is not None else -1
    return step, msi


def _log_resume_scan(*, count: int, due_count: int, future_count: int = 0) -> None:
    try:
        print("[RECOVERY RESUME SCAN]", flush=True)
        print(f"pending_scheduled={count}", flush=True)
        print(f"due_now={due_count}", flush=True)
        print(f"future_rearm_candidates={future_count}", flush=True)
    except OSError:
        pass


def _log_future_rearm(tag: str, *, schedule_id: int, recovery_key: str = "", detail: str = "") -> None:
    try:
        print(f"[RECOVERY FUTURE REARM {tag}]", flush=True)
        print(f"schedule_id={int(schedule_id)}", flush=True)
        if recovery_key:
            print(f"recovery_key={recovery_key[:120]}", flush=True)
        if detail:
            print(f"detail={detail[:96]}", flush=True)
    except OSError:
        pass


# Per-process guard: avoid duplicate delay tasks for the same schedule row on startup.
_future_rearm_spawned: set[int] = set()


def _schedule_due_at_utc(row: RecoverySchedule) -> datetime:
    due = row.due_at
    if due is None:
        return _utc_now()
    if due.tzinfo is None:
        return due.replace(tzinfo=timezone.utc)
    return due.astimezone(timezone.utc)


def rearm_one_future_scheduled_recovery(
    row: RecoverySchedule,
    *,
    dispatch: bool = True,
) -> Dict[str, Any]:
    """
    Re-arm in-process delay dispatch for a future-due ``scheduled`` row (post-restart).

    Does not execute early; preserves ``due_at`` via ``dispatch_recovery_schedule``.
    """
    sid = int(row.id)
    rk = row.recovery_key
    _log_future_rearm("CHECK", schedule_id=sid, recovery_key=rk)

    if row.status != STATUS_SCHEDULED:
        _log_future_rearm(
            "SKIPPED",
            schedule_id=sid,
            recovery_key=rk,
            detail=f"not_scheduled:{row.status}",
        )
        return {
            "schedule_id": sid,
            "recovery_key": rk,
            "rearmed": False,
            "reason": f"not_scheduled:{row.status}",
        }

    due_at = _schedule_due_at_utc(row)
    now = _utc_now()
    if due_at <= now:
        _log_future_rearm(
            "SKIPPED",
            schedule_id=sid,
            recovery_key=rk,
            detail="already_due_use_resume_path",
        )
        return {
            "schedule_id": sid,
            "recovery_key": rk,
            "rearmed": False,
            "reason": "already_due",
        }

    if sid in _future_rearm_spawned:
        _log_future_rearm(
            "SKIPPED",
            schedule_id=sid,
            recovery_key=rk,
            detail="already_rearmed_this_process",
        )
        return {
            "schedule_id": sid,
            "recovery_key": rk,
            "rearmed": False,
            "reason": "already_rearmed_this_process",
        }

    ok, safety_reason = evaluate_resume_safety(row, trust_durable_schedule=True)
    if not ok:
        _log_future_rearm(
            "SKIPPED",
            schedule_id=sid,
            recovery_key=rk,
            detail=safety_reason,
        )
        return {
            "schedule_id": sid,
            "recovery_key": rk,
            "rearmed": False,
            "reason": safety_reason,
        }

    if not dispatch:
        return {
            "schedule_id": sid,
            "recovery_key": rk,
            "rearmed": False,
            "reason": "dry_run_allowed",
            "would_rearm": True,
            "due_at": _naive_utc(due_at).isoformat(),
        }

    from services.recovery_delay_dispatcher import spawn_recovery_schedule_dispatch

    _future_rearm_spawned.add(sid)
    spawn_recovery_schedule_dispatch(
        sid,
        due_at,
        "resume_scan_future_rearm",
    )
    _log_future_rearm(
        "REARMED",
        schedule_id=sid,
        recovery_key=rk,
        detail=f"due_at={_naive_utc(due_at).isoformat()}",
    )
    return {
        "schedule_id": sid,
        "recovery_key": rk,
        "rearmed": True,
        "reason": "rearmed",
        "due_at": _naive_utc(due_at).isoformat(),
    }


def _log_resume_candidate(row: RecoverySchedule) -> None:
    try:
        print("[RECOVERY RESUME CANDIDATE]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"store_slug={row.store_slug}", flush=True)
        print(f"due_at={_naive_utc(row.due_at).isoformat()}", flush=True)
        print(f"effective_delay_seconds={float(row.effective_delay_seconds)}", flush=True)
        print(f"source={row.delay_source}", flush=True)
        print(f"step={row.step}", flush=True)
    except OSError:
        pass


def _log_resume_skipped(recovery_key: str, reason: str) -> None:
    try:
        print("[RECOVERY RESUME SKIPPED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"reason={reason[:96]}", flush=True)
    except OSError:
        pass


def _log_resume_blocked(recovery_key: str, reason: str) -> None:
    try:
        print("[RECOVERY RESUME BLOCKED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"reason={reason[:96]}", flush=True)
    except OSError:
        pass


def _log_recovery_claim_attempt(
    *,
    recovery_key: str,
    path: str,
    row_id: Optional[int] = None,
    step: Optional[int] = None,
    current_status: Optional[str] = None,
) -> None:
    try:
        print("[RECOVERY CLAIM ATTEMPT]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"path={(path or '-')[:64]}", flush=True)
        if row_id is not None:
            print(f"schedule_id={row_id}", flush=True)
        if step is not None:
            print(f"step={step}", flush=True)
        if current_status:
            print(f"current_status={current_status[:64]}", flush=True)
    except OSError:
        pass


def _log_recovery_claimed(
    *,
    recovery_key: str,
    path: str,
    row_id: int,
    step: int,
) -> None:
    try:
        print("[RECOVERY CLAIMED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"path={(path or '-')[:64]}", flush=True)
        print(f"schedule_id={row_id}", flush=True)
        print(f"step={step}", flush=True)
    except OSError:
        pass


def _log_recovery_claim_skipped(
    *,
    recovery_key: str,
    path: str,
    reason: str,
    row_id: Optional[int] = None,
    current_status: Optional[str] = None,
) -> None:
    try:
        print("[RECOVERY CLAIM SKIPPED]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"path={(path or '-')[:64]}", flush=True)
        print(f"reason={(reason or '-')[:96]}", flush=True)
        if row_id is not None:
            print(f"schedule_id={row_id}", flush=True)
        if current_status:
            print(f"current_status={current_status[:64]}", flush=True)
    except OSError:
        pass


def _log_recovery_terminal_update(
    *,
    recovery_key: str,
    row_id: Optional[int],
    from_status: str,
    to_status: str,
    detail: str,
    overwrite: bool = False,
) -> None:
    try:
        print("[RECOVERY TERMINAL UPDATE]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        if row_id is not None:
            print(f"schedule_id={row_id}", flush=True)
        print(f"from_status={(from_status or '-')[:64]}", flush=True)
        print(f"to_status={(to_status or '-')[:64]}", flush=True)
        print(f"detail={(detail or '-')[:96]}", flush=True)
        if overwrite:
            print("overwrite=justified", flush=True)
    except OSError:
        pass


def _schedule_row_lookup(
    *,
    recovery_key: str,
    multi_slot_index: Optional[int],
    sequential_attempt_index: Optional[int],
    row_id: Optional[int] = None,
) -> Optional[RecoverySchedule]:
    try:
        if row_id is not None:
            return db.session.get(RecoverySchedule, int(row_id))
        step, msi = _step_keys(
            multi_slot_index=multi_slot_index,
            sequential_attempt_index=sequential_attempt_index,
        )
        rk = (recovery_key or "").strip()[:512]
        if not rk:
            return None
        return (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.step == step,
                RecoverySchedule.multi_slot_index == msi,
            )
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def claim_recovery_schedule_execution(
    *,
    recovery_key: str,
    multi_slot_index: Optional[int] = None,
    sequential_attempt_index: Optional[int] = None,
    row_id: Optional[int] = None,
    path: str = "unknown",
    accept_already_running: bool = False,
) -> tuple[bool, str, Optional[RecoverySchedule]]:
    """
    Atomic DB gate: only ``scheduled`` → ``running``. Shared by live delay task and resume.
    Returns (claimed, skip_reason, row).
    """
    rk = (recovery_key or "").strip()[:512]
    step, msi = _step_keys(
        multi_slot_index=multi_slot_index,
        sequential_attempt_index=sequential_attempt_index,
    )
    row = _schedule_row_lookup(
        recovery_key=rk,
        multi_slot_index=multi_slot_index,
        sequential_attempt_index=sequential_attempt_index,
        row_id=row_id,
    )
    cur_st = (row.status if row is not None else None) or "missing"
    _log_recovery_claim_attempt(
        recovery_key=rk,
        path=path,
        row_id=getattr(row, "id", None),
        step=step,
        current_status=cur_st,
    )
    if row is None:
        _log_recovery_claim_skipped(
            recovery_key=rk,
            path=path,
            reason="schedule_row_missing",
        )
        return False, "schedule_row_missing", None

    rid = int(row.id)
    if row.status in _TERMINAL:
        reason = f"already_terminal:{row.status}"
        _log_recovery_claim_skipped(
            recovery_key=rk,
            path=path,
            reason=reason,
            row_id=rid,
            current_status=row.status,
        )
        return False, reason, row

    if row.status == STATUS_RUNNING:
        if accept_already_running:
            _log_recovery_claimed(
                recovery_key=rk,
                path=f"{path}_reentry",
                row_id=rid,
                step=step,
            )
            return True, "already_running_holder", row
        _log_recovery_claim_skipped(
            recovery_key=rk,
            path=path,
            reason="already_running",
            row_id=rid,
            current_status=row.status,
        )
        return False, "already_running", row

    if row.status != STATUS_SCHEDULED:
        reason = f"not_claimable:{row.status}"
        _log_recovery_claim_skipped(
            recovery_key=rk,
            path=path,
            reason=reason,
            row_id=rid,
            current_status=row.status,
        )
        return False, reason, row

    try:
        updated = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.id == rid,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .update(
                {
                    RecoverySchedule.status: STATUS_RUNNING,
                    RecoverySchedule.updated_at: _utc_now(),
                },
                synchronize_session=False,
            )
        )
        db.session.commit()
        if int(updated or 0) != 1:
            db.session.expire(row)
            fresh = db.session.get(RecoverySchedule, rid)
            fst = (fresh.status if fresh else None) or "unknown"
            _log_recovery_claim_skipped(
                recovery_key=rk,
                path=path,
                reason="claim_race_lost",
                row_id=rid,
                current_status=fst,
            )
            return False, "claim_race_lost", fresh

        db.session.expire(row)
        claimed_row = db.session.get(RecoverySchedule, rid)
        _log_recovery_claimed(
            recovery_key=rk,
            path=path,
            row_id=rid,
            step=step,
        )
        return True, "claimed", claimed_row
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("claim_recovery_schedule_execution failed: %s", exc)
        _log_recovery_claim_skipped(
            recovery_key=rk,
            path=path,
            reason="claim_db_error",
        )
        return False, "claim_db_error", row


def map_cart_recovery_log_status_to_schedule_terminal(log_status: str) -> str:
    """Map ``CartRecoveryLog.status`` to durable ``recovery_schedules.status``."""
    s = (log_status or "").strip().lower()
    if s in ("mock_sent", "sent_real"):
        return STATUS_COMPLETED
    if s == "whatsapp_failed":
        return STATUS_WHATSAPP_FAILED
    if s in ("skipped_duplicate",):
        return STATUS_SKIPPED_DUPLICATE
    if s in ("skipped_no_verified_phone", "skipped_missing_phone"):
        return STATUS_SKIPPED_NO_PHONE
    if s in ("skipped_missing_reason_tag",):
        return STATUS_SKIPPED_NO_REASON
    if s.startswith("skipped") or s.startswith("stopped"):
        return STATUS_SKIPPED_RESUME
    return STATUS_FAILED_RESUME


def _log_resume_sent(recovery_key: str) -> None:
    try:
        print("[RECOVERY RESUME SENT]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print("action=dispatched_resume_task", flush=True)
    except OSError:
        pass


def _log_resume_task_enter(row: RecoverySchedule) -> None:
    try:
        print("[RESUME TASK ENTER]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"store_slug={row.store_slug}", flush=True)
        print(f"step={row.step}", flush=True)
    except OSError:
        pass


def _log_resume_task_after_delay(row: RecoverySchedule) -> None:
    try:
        print("[RESUME TASK AFTER DELAY]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
    except OSError:
        pass


def _log_resume_task_finalize(
    row: RecoverySchedule, status: str, detail: str
) -> None:
    try:
        print("[RESUME TASK FINALIZE]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"status={status}", flush=True)
        print(f"detail={(detail or '-')[:96]}", flush=True)
    except OSError:
        pass


def _log_resume_task_exception(row: RecoverySchedule, detail: str) -> None:
    try:
        print("[RESUME TASK EXCEPTION]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"error={(detail or '-')[:200]}", flush=True)
    except OSError:
        pass


def _running_stale_seconds() -> int:
    raw = os.getenv("CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS", "").strip()
    if raw.isdigit():
        return max(60, int(raw))
    return _DEFAULT_RUNNING_STALE_SECONDS


def _latest_cart_recovery_log_for_schedule(row: RecoverySchedule):
    from models import CartRecoveryLog

    sid = (row.session_id or "").strip()
    cid = (row.cart_id or "").strip() if row.cart_id else ""
    if not sid and not cid:
        return None
    try:
        from sqlalchemy import or_

        conds: list[Any] = []
        if sid:
            conds.append(CartRecoveryLog.session_id == sid)
        if cid:
            conds.append(CartRecoveryLog.cart_id == cid)
        return (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.step == int(row.step),
                or_(*conds),
            )
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def infer_resume_task_terminal_status(
    row: RecoverySchedule,
    *,
    exc_detail: str = "",
) -> tuple[str, str]:
    """Map post-task state to a terminal recovery_schedules.status (never leave running)."""
    if exc_detail == "cancelled":
        return STATUS_FAILED_RESUME, "task_cancelled"
    if exc_detail:
        return STATUS_FAILED_RESUME, exc_detail[:512]

    try:
        db.session.expire(row)
        fresh = db.session.get(RecoverySchedule, int(row.id))
    except SQLAlchemyError:
        db.session.rollback()
        fresh = row
    if fresh is None:
        return STATUS_FAILED_RESUME, "schedule_row_missing"

    if fresh.status in _TERMINAL:
        return str(fresh.status), (fresh.last_error or "already_terminal")[:512]

    if fresh.status != STATUS_RUNNING:
        return str(fresh.status), (fresh.last_error or "unexpected_non_running")[:512]

    from main import (  # noqa: PLC0415
        _NORMAL_RECOVERY_SENT_LOG_STATUSES,
        _cart_recovery_log_has_successful_send_for_step,
    )

    step = int(fresh.step)
    if _cart_recovery_log_has_successful_send_for_step(
        fresh.session_id, fresh.cart_id, step
    ):
        return STATUS_COMPLETED, "send_logged"

    log_row = _latest_cart_recovery_log_for_schedule(fresh)
    if log_row is not None:
        st = (log_row.status or "").strip()
        mapped = map_cart_recovery_log_status_to_schedule_terminal(st)
        return mapped, st

    return STATUS_FAILED_RESUME, "resume_task_exited_without_terminal_log"


def _finalize_running_schedule_row(
    row: RecoverySchedule,
    *,
    status: str,
    detail: str = "",
) -> None:
    try:
        db.session.expire(row)
        fresh = db.session.get(RecoverySchedule, int(row.id))
    except SQLAlchemyError:
        db.session.rollback()
        fresh = row
    if fresh is None or fresh.status != STATUS_RUNNING:
        return
    msi = fresh.multi_slot_index if fresh.multi_slot_index >= 0 else None
    finalize_recovery_schedule_durable(
        fresh.recovery_key,
        status=status,
        multi_slot_index=msi,
        sequential_attempt_index=fresh.sequential_attempt_index,
        detail=detail,
    )


def _running_row_updated_at_utc(row: RecoverySchedule) -> datetime:
    ua = row.updated_at
    if ua is None:
        return _utc_now() - timedelta(days=1)
    if ua.tzinfo is None:
        return ua.replace(tzinfo=timezone.utc)
    return ua.astimezone(timezone.utc)


def _is_running_schedule_stale(row: RecoverySchedule, cutoff: datetime) -> bool:
    return _running_row_updated_at_utc(row) < cutoff


def _log_recovery_stale_check(*, running_count: int, stale_threshold_seconds: int) -> None:
    try:
        print("[RECOVERY STALE CHECK]", flush=True)
        print(f"running_rows={running_count}", flush=True)
        print(f"stale_threshold_seconds={stale_threshold_seconds}", flush=True)
    except OSError:
        pass


def _log_recovery_stale_detected(row: RecoverySchedule, *, age_seconds: float) -> None:
    try:
        print("[RECOVERY STALE DETECTED]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"updated_at={_naive_utc(row.updated_at).isoformat()}", flush=True)
        print(f"age_seconds={round(age_seconds, 1)}", flush=True)
    except OSError:
        pass


def _log_recovery_stale_skipped(
    row: RecoverySchedule, *, reason: str
) -> None:
    try:
        print("[RECOVERY STALE SKIPPED]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"reason={(reason or '-')[:96]}", flush=True)
    except OSError:
        pass


def _log_recovery_stale_repaired(
    row: RecoverySchedule, *, terminal_status: str, detail: str
) -> None:
    try:
        print("[RECOVERY STALE REPAIRED]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"terminal_status={terminal_status[:64]}", flush=True)
        print(f"detail={(detail or '-')[:96]}", flush=True)
    except OSError:
        pass


def _log_recovery_stale_finalized(
    row: RecoverySchedule, *, terminal_status: str, detail: str
) -> None:
    try:
        print("[RECOVERY STALE FINALIZED]", flush=True)
        print(f"recovery_key={row.recovery_key[:120]}", flush=True)
        print(f"schedule_id={row.id}", flush=True)
        print(f"terminal_status={terminal_status[:64]}", flush=True)
        print(f"detail={(detail or '-')[:96]}", flush=True)
    except OSError:
        pass


def classify_stale_running_schedule_repair(
    row: RecoverySchedule,
    *,
    stale_threshold_seconds: int,
) -> tuple[str, str, str]:
    """
    Decide how to close a stale ``running`` row using DB evidence only.
    Returns (action, terminal_status, detail) where action is ``finalize`` or ``repair``.
    """
    from services.recovery_whatsapp_idempotency import (
        build_whatsapp_recovery_idempotency_key,
        find_existing_whatsapp_recovery_send,
    )

    key = build_whatsapp_recovery_idempotency_key(
        recovery_key=row.recovery_key,
        step=int(row.step),
        reason_tag=row.reason_tag,
        customer_phone=row.customer_phone,
        store_slug=row.store_slug,
        session_id=row.session_id,
        cart_id=row.cart_id,
    )
    wa_row = find_existing_whatsapp_recovery_send(key)
    if wa_row is not None:
        st = (wa_row.status or "").strip()
        if st == "skipped_duplicate":
            return (
                "finalize",
                STATUS_SKIPPED_DUPLICATE,
                f"stale_wa_idempotency:{st}",
            )
        if st in ("mock_sent", "sent_real", "queued"):
            return (
                "finalize",
                STATUS_COMPLETED,
                f"stale_send_evidence:{st}",
            )

    log_row = _latest_cart_recovery_log_for_schedule(row)
    if log_row is not None:
        st = (log_row.status or "").strip()
        if st == "skipped_duplicate":
            return (
                "finalize",
                STATUS_SKIPPED_DUPLICATE,
                f"stale_log:{st}",
            )
        mapped = map_cart_recovery_log_status_to_schedule_terminal(st)
        if mapped == STATUS_COMPLETED:
            return "finalize", STATUS_COMPLETED, f"stale_log:{st}"
        if mapped in _TERMINAL and mapped != STATUS_FAILED_RESUME:
            return "finalize", mapped, f"stale_log:{st}"

    return (
        "repair",
        STATUS_FAILED_RESUME_STALE,
        f"stale_no_send_evidence_{stale_threshold_seconds}s",
    )


def repair_stale_running_recovery_schedules(
    *,
    max_age_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Startup/due-scan only: repair ``running`` rows older than threshold using log evidence.
    Does not reschedule for immediate retry (``failed_resume_stale``); send evidence → terminal.
    """
    age = int(max_age_seconds or _running_stale_seconds())
    cutoff = _utc_now() - timedelta(seconds=age)
    stats: Dict[str, Any] = {
        "stale_threshold_seconds": age,
        "running_checked": 0,
        "stale_detected": 0,
        "finalized": 0,
        "repaired": 0,
        "skipped_not_stale": 0,
        "errors": 0,
    }
    try:
        db.create_all()
        running_rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.status == STATUS_RUNNING)
            .all()
        )
        stats["running_checked"] = len(running_rows)
        _log_recovery_stale_check(
            running_count=len(running_rows),
            stale_threshold_seconds=age,
        )
        now = _utc_now()
        for row in running_rows:
            if not _is_running_schedule_stale(row, cutoff):
                _log_recovery_stale_skipped(row, reason="not_stale_yet")
                stats["skipped_not_stale"] += 1
                continue

            age_sec = (now - _running_row_updated_at_utc(row)).total_seconds()
            stats["stale_detected"] += 1
            _log_recovery_stale_detected(row, age_seconds=age_sec)

            action, terminal_status, detail = classify_stale_running_schedule_repair(
                row, stale_threshold_seconds=age
            )
            if action == "finalize":
                _log_recovery_stale_finalized(
                    row, terminal_status=terminal_status, detail=detail
                )
                stats["finalized"] += 1
            else:
                _log_recovery_stale_repaired(
                    row, terminal_status=terminal_status, detail=detail
                )
                stats["repaired"] += 1
            _finalize_running_schedule_row(
                row, status=terminal_status, detail=detail
            )
        return stats
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("repair_stale_running_recovery_schedules failed: %s", exc)
        stats["errors"] = 1
        stats["error"] = str(exc)
        return stats


def reconcile_stale_running_schedules(
    *,
    max_age_seconds: Optional[int] = None,
) -> int:
    """Backward-compatible count of stale running rows repaired/finalized on startup scan."""
    out = repair_stale_running_recovery_schedules(max_age_seconds=max_age_seconds)
    return int(out.get("finalized", 0)) + int(out.get("repaired", 0))


async def _execute_resume_recovery_task(row: RecoverySchedule) -> None:
    """Backward-compatible resume task — delegates to queue-ready execution boundary."""
    _log_resume_task_enter(row)
    from services.recovery_execution_boundary import execute_recovery_schedule

    try:
        await execute_recovery_schedule(schedule_id=int(row.id), source="resume_scan")
        _log_resume_task_after_delay(row)
    except Exception as exc:  # noqa: BLE001
        import asyncio

        if isinstance(exc, asyncio.CancelledError):
            _log_resume_task_exception(row, "cancelled")
            raise
        _log_resume_task_exception(row, str(exc)[:512])


def persist_recovery_schedule_durable(
    *,
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    reason_tag: Optional[str],
    abandon_event_phone: Optional[str],
    delay_seconds_scheduled: float,
    schedule_timing: Optional[Dict[str, Any]],
    recovery_context: Optional[Dict[str, Any]],
    multi_slot_index: Optional[int] = None,
    sequential_attempt_index: Optional[int] = None,
    multi_message_text: Optional[str] = None,
) -> Optional[RecoverySchedule]:
    """Upsert durable row before asyncio sleep — survives process restart."""
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return None
    step, msi = _step_keys(
        multi_slot_index=multi_slot_index,
        sequential_attempt_index=sequential_attempt_index,
    )
    timing = dict(schedule_timing or {})
    eff = float(
        timing.get("effective_delay_seconds")
        if timing.get("effective_delay_seconds") is not None
        else delay_seconds_scheduled
    )
    source = str(timing.get("source") or "scheduled_task_delay")[:128]
    now = _utc_now()
    due = now + timedelta(seconds=max(0.0, float(delay_seconds_scheduled)))
    ctx_blob = {
        "schedule_timing": timing,
        "recovery_context": dict(recovery_context or {}),
        "multi_message_text": (multi_message_text or "").strip()[:8000] or None,
        "abandon_event_phone": (abandon_event_phone or "").strip()[:100] or None,
    }
    try:
        db.create_all()
        row = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.step == step,
                RecoverySchedule.multi_slot_index == msi,
            )
            .first()
        )
        if row is None:
            try:
                from services.operational_control_v1 import (
                    operational_control_blocks_schedule_creation,
                )

                if operational_control_blocks_schedule_creation(
                    store_slug=store_slug,
                    reason_tag=reason_tag,
                    is_new_row=True,
                ):
                    return None
            except Exception:  # noqa: BLE001
                pass
        if row is None:
            row = RecoverySchedule(
                recovery_key=rk,
                store_slug=(store_slug or "").strip()[:255],
                session_id=(session_id or "").strip()[:512],
                cart_id=(str(cart_id).strip()[:255] if cart_id else None),
                reason_tag=(reason_tag or "").strip()[:128] or None,
                customer_phone=(abandon_event_phone or "").strip()[:100] or None,
                scheduled_at=now,
                due_at=due,
                effective_delay_seconds=eff,
                delay_source=source,
                status=STATUS_SCHEDULED,
                step=step,
                multi_slot_index=msi,
                sequential_attempt_index=(
                    int(sequential_attempt_index)
                    if sequential_attempt_index is not None
                    else None
                ),
                context_json=json.dumps(ctx_blob, ensure_ascii=False, default=str)[:65000],
            )
            db.session.add(row)
        else:
            if row.status in _TERMINAL:
                return row
            row.store_slug = (store_slug or "").strip()[:255]
            row.session_id = (session_id or "").strip()[:512]
            row.cart_id = (str(cart_id).strip()[:255] if cart_id else None)
            row.reason_tag = (reason_tag or "").strip()[:128] or None
            row.scheduled_at = now
            row.due_at = due
            row.effective_delay_seconds = eff
            row.delay_source = source
            row.status = STATUS_SCHEDULED
            row.context_json = json.dumps(ctx_blob, ensure_ascii=False, default=str)[
                :65000
            ]
            row.updated_at = now
        db.session.commit()
        return row
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("persist_recovery_schedule_durable failed: %s", exc)
        return None


def finalize_recovery_schedule_durable(
    recovery_key: str,
    *,
    status: str,
    multi_slot_index: Optional[int] = None,
    sequential_attempt_index: Optional[int] = None,
    detail: Optional[str] = None,
    allow_terminal_overwrite: bool = False,
) -> bool:
    """Set terminal status from ``running`` (or justified overwrite). Returns whether updated."""
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return False
    step, msi = _step_keys(
        multi_slot_index=multi_slot_index,
        sequential_attempt_index=sequential_attempt_index,
    )
    st = (status or "").strip()[:64] or STATUS_COMPLETED
    det = (detail or "").strip()[:512]
    try:
        row = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.step == step,
                RecoverySchedule.multi_slot_index == msi,
            )
            .first()
        )
        if row is None:
            return False
        prev = (row.status or "").strip()
        rid = int(row.id)

        if prev in _TERMINAL:
            if not allow_terminal_overwrite:
                _log_recovery_claim_skipped(
                    recovery_key=rk,
                    path="terminal_update",
                    reason="terminal_no_overwrite",
                    row_id=rid,
                    current_status=prev,
                )
                return False
            if (
                prev in _PROTECTED_TERMINAL_NO_DOWNGRADE
                and st != prev
                and st
                not in (
                    STATUS_COMPLETED,
                    STATUS_CANCELLED,
                    STATUS_NEEDS_REVIEW,
                )
            ):
                _log_recovery_claim_skipped(
                    recovery_key=rk,
                    path="terminal_update",
                    reason="completed_downgrade_blocked",
                    row_id=rid,
                    current_status=prev,
                )
                return False
            _log_recovery_terminal_update(
                recovery_key=rk,
                row_id=rid,
                from_status=prev,
                to_status=st,
                detail=det or "explicit_overwrite",
                overwrite=True,
            )
        elif prev == STATUS_RUNNING:
            _log_recovery_terminal_update(
                recovery_key=rk,
                row_id=rid,
                from_status=prev,
                to_status=st,
                detail=det or "-",
            )
        else:
            _log_recovery_claim_skipped(
                recovery_key=rk,
                path="terminal_update",
                reason=f"not_running:{prev}",
                row_id=rid,
                current_status=prev,
            )
            return False

        row.status = st
        row.updated_at = _utc_now()
        if det:
            row.last_error = det
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        return False


def release_claimed_schedule_execution_terminal(
    recovery_context: Optional[Dict[str, Any]],
    *,
    exc_detail: str = "",
) -> None:
    """Finalize a claimed row still in ``running`` after execution (live or resume)."""
    if not isinstance(recovery_context, dict):
        return
    if not recovery_context.get("schedule_execution_claimed"):
        return
    row_id = recovery_context.get("durable_schedule_row_id")
    rk = (recovery_context.get("recovery_key") or "").strip()
    if row_id is None and not rk:
        return
    try:
        row = (
            db.session.get(RecoverySchedule, int(row_id))
            if row_id is not None
            else None
        )
    except (SQLAlchemyError, TypeError, ValueError):
        db.session.rollback()
        row = None
    if row is None and rk:
        row = _schedule_row_lookup(
            recovery_key=rk,
            multi_slot_index=recovery_context.get("multi_slot_index"),
            sequential_attempt_index=recovery_context.get("sequential_attempt_index"),
        )
    if row is None:
        return
    if row.status in _TERMINAL:
        return
    if row.status != STATUS_RUNNING:
        return
    status, detail = infer_resume_task_terminal_status(row, exc_detail=exc_detail)
    msi = row.multi_slot_index if row.multi_slot_index >= 0 else None
    finalize_recovery_schedule_durable(
        row.recovery_key,
        status=status,
        multi_slot_index=msi,
        sequential_attempt_index=row.sequential_attempt_index,
        detail=detail,
    )


def load_context(row: RecoverySchedule) -> Dict[str, Any]:
    raw = row.context_json
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def inspect_persistence_state() -> Dict[str, Any]:
    """Read-only snapshot for dev verification."""
    try:
        db.create_all()
        total = db.session.query(RecoverySchedule).count()
        by_status: Dict[str, int] = {}
        for st, cnt in (
            db.session.query(RecoverySchedule.status, func.count(RecoverySchedule.id))
            .group_by(RecoverySchedule.status)
            .all()
        ):
            by_status[str(st)] = int(cnt)
        now = _utc_now()
        due_n = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at <= now,
            )
            .count()
        )
        sample = (
            db.session.query(RecoverySchedule)
            .order_by(RecoverySchedule.due_at.asc())
            .limit(5)
            .all()
        )
        samples = [
            {
                "recovery_key": r.recovery_key,
                "store_slug": r.store_slug,
                "due_at": _naive_utc(r.due_at).isoformat(),
                "effective_delay_seconds": float(r.effective_delay_seconds),
                "delay_source": r.delay_source,
                "status": r.status,
                "step": r.step,
            }
            for r in sample
        ]
        return {
            "table": "recovery_schedules",
            "total_rows": total,
            "by_status": by_status,
            "due_scheduled_now": due_n,
            "sample_rows": samples,
            "fields": [
                "recovery_key",
                "store_slug",
                "session_id",
                "cart_id",
                "reason_tag",
                "customer_phone",
                "scheduled_at",
                "due_at",
                "effective_delay_seconds",
                "delay_source",
                "status",
                "step",
                "multi_slot_index",
                "context_json",
            ],
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"error": str(exc)}


def evaluate_resume_safety(
    row: RecoverySchedule,
    *,
    trust_durable_schedule: bool = False,
) -> tuple[bool, str]:
    """Pre-send checks — mirrors runtime gates without bypassing them.

    When ``trust_durable_schedule`` is True (resume/rearm of an existing DB row),
    skip the legacy-timing fallback guard — ``due_at`` is already authoritative.
    """
    from services.recovery_store_context import canonical_store_slug_from_recovery_key
    from services.reason_template_recovery import reason_template_blocks_recovery_whatsapp

    rk = row.recovery_key
    canon = canonical_store_slug_from_recovery_key(rk) or (row.store_slug or "").strip()
    row_slug = (row.store_slug or "").strip()
    if canon and row_slug and canon.casefold() != row_slug.casefold():
        return False, "store_context_mismatch"

    from main import (  # noqa: PLC0415
        _cart_recovery_log_has_successful_send_for_step,
        _is_user_converted,
        _recovery_resolve_user_returned_for_send,
        _recovery_store_from_context,
    )

    if _is_user_converted(rk):
        try:
            from services.purchase_lifecycle_closure import (
                block_recovery_if_purchase_lifecycle_closed,
            )

            block_recovery_if_purchase_lifecycle_closed(
                rk,
                session_id=(row.session_id or "").strip(),
                cart_id=(row.cart_id or "").strip() if row.cart_id else "",
            )
        except Exception:  # noqa: BLE001
            pass
        return False, "purchase_completed"
    if _recovery_resolve_user_returned_for_send(
        rk,
        store_slug=row_slug,
        session_id=row.session_id,
        cart_id=row.cart_id,
    ):
        return False, "user_returned"
    if _cart_recovery_log_has_successful_send_for_step(
        row.session_id, row.cart_id, int(row.step)
    ):
        return False, "already_sent"

    ctx = load_context(row)
    rc = ctx.get("recovery_context") if isinstance(ctx.get("recovery_context"), dict) else {}
    store_obj = _recovery_store_from_context(
        {**rc, "recovery_key": rk},
        store_slug=canon or row_slug,
        allow_schema_warm=True,
    )
    if store_obj is None:
        return False, "store_row_missing"

    zid = (getattr(store_obj, "zid_store_id", None) or "").strip()
    if canon and zid and zid.casefold() != canon.casefold():
        return False, "store_template_mismatch"

    rt = (row.reason_tag or rc.get("reason_tag") or "").strip() or None
    if rt and reason_template_blocks_recovery_whatsapp(rt, store_obj):
        return False, "template_disabled"

    if not trust_durable_schedule:
        timing = ctx.get("schedule_timing") if isinstance(ctx.get("schedule_timing"), dict) else {}
        src = str(timing.get("source") or row.delay_source or "")
        if "legacy_recovery_delay" in src.casefold() and "test_patch" not in src:
            fb = timing.get("fallback_reason")
            if fb:
                return False, f"unsafe_legacy_fallback:{fb}"

    return True, "allowed"


async def resume_one_schedule(
    row: RecoverySchedule,
    *,
    dispatch: bool = True,
) -> Dict[str, Any]:
    _log_resume_candidate(row)
    ok, reason = evaluate_resume_safety(row, trust_durable_schedule=True)
    if not ok:
        if reason in ("store_context_mismatch", "store_template_mismatch", "unsafe_legacy_fallback"):
            _log_resume_blocked(row.recovery_key, reason)
        else:
            _log_resume_skipped(row.recovery_key, reason)
        finalize_recovery_schedule_durable(
            row.recovery_key,
            status=STATUS_SKIPPED_RESUME,
            multi_slot_index=row.multi_slot_index if row.multi_slot_index >= 0 else None,
            sequential_attempt_index=row.sequential_attempt_index,
            detail=reason,
        )
        return {"recovery_key": row.recovery_key, "dispatched": False, "reason": reason}

    if not dispatch:
        return {"recovery_key": row.recovery_key, "dispatched": False, "reason": "dry_run_allowed"}

    claimed, claim_reason, _claimed_row = claim_recovery_schedule_execution(
        recovery_key=row.recovery_key,
        multi_slot_index=row.multi_slot_index if row.multi_slot_index >= 0 else None,
        sequential_attempt_index=row.sequential_attempt_index,
        row_id=int(row.id),
        path="resume_dispatch",
    )
    if not claimed:
        skip = (
            "duplicate_resume_claim"
            if claim_reason in ("already_running", "claim_race_lost")
            else claim_reason
        )
        _log_resume_skipped(row.recovery_key, skip)
        return {"recovery_key": row.recovery_key, "dispatched": False, "reason": skip}

    import asyncio

    from services.recovery_execution_boundary import execute_recovery_schedule

    asyncio.create_task(
        execute_recovery_schedule(schedule_id=int(row.id), source="resume_scan")
    )
    _log_resume_sent(row.recovery_key)
    return {"recovery_key": row.recovery_key, "dispatched": True, "reason": "allowed"}


async def run_recovery_resume_scan_async(
    *,
    max_dispatch: int = 25,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    from services.recovery_scheduler_guardrails import (
        is_recovery_resume_on_startup_enabled,
    )

    if not is_recovery_resume_on_startup_enabled(force=force):
        return {
            "enabled": False,
            "dispatched": 0,
            "reason": "resume_on_startup_disabled",
        }

    try:
        db.create_all()
        stale_repair = repair_stale_running_recovery_schedules()
        now = _utc_now()
        pending = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.status == STATUS_SCHEDULED)
            .count()
        )
        lim = max(1, int(max_dispatch))
        due_rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at <= now,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .limit(lim)
            .all()
        )
        future_rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at > now,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .limit(lim)
            .all()
        )
        _log_resume_scan(
            count=pending,
            due_count=len(due_rows),
            future_count=len(future_rows),
        )
        outcomes: List[Dict[str, Any]] = []
        dispatched = 0
        for row in due_rows:
            out = await resume_one_schedule(row, dispatch=not dry_run)
            outcomes.append(out)
            if out.get("dispatched"):
                dispatched += 1
        future_outcomes: List[Dict[str, Any]] = []
        future_rearmed = 0
        for row in future_rows:
            out = rearm_one_future_scheduled_recovery(row, dispatch=not dry_run)
            future_outcomes.append(out)
            if out.get("rearmed"):
                future_rearmed += 1
        return {
            "enabled": True,
            "dry_run": dry_run,
            "stale_running_repair": stale_repair,
            "stale_running_reconciled": int(stale_repair.get("finalized", 0))
            + int(stale_repair.get("repaired", 0)),
            "pending_scheduled": pending,
            "due_processed": len(due_rows),
            "dispatched": dispatched,
            "outcomes": outcomes,
            "future_processed": len(future_rows),
            "future_rearmed": future_rearmed,
            "future_outcomes": future_outcomes,
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("recovery resume scan failed: %s", exc)
        return {"enabled": True, "error": str(exc), "dispatched": 0}


def run_recovery_resume_scan_sync(
    *,
    max_dispatch: int = 25,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return {"enabled": True, "error": "event_loop_running", "dispatched": 0}
        return loop.run_until_complete(
            run_recovery_resume_scan_async(
                max_dispatch=max_dispatch, dry_run=dry_run, force=force
            )
        )
    except RuntimeError:
        return asyncio.run(
            run_recovery_resume_scan_async(
                max_dispatch=max_dispatch, dry_run=dry_run, force=force
            )
        )


def dev_verify_recovery_restart_survival(
    *,
    action: str = "inspect",
    recovery_key: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    act = (action or "inspect").strip().lower()
    out: Dict[str, Any] = {"action": act, "persistence": inspect_persistence_state()}
    if act == "inspect":
        return out
    if act == "simulate_restart_scan":
        out["scan"] = run_recovery_resume_scan_sync(
            max_dispatch=50, dry_run=dry_run, force=True
        )
        return out
    if act == "find" and recovery_key:
        rk = recovery_key.strip()
        row = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == rk)
            .order_by(RecoverySchedule.due_at.asc())
            .all()
        )
        out["rows"] = [
            {
                "id": r.id,
                "status": r.status,
                "due_at": _naive_utc(r.due_at).isoformat(),
                "effective_delay_seconds": float(r.effective_delay_seconds),
                "delay_source": r.delay_source,
                "step": r.step,
            }
            for r in row
        ]
        return out
    out["error"] = "unknown_action"
    return out


def cancel_durable_schedules_for_purchase(
    recovery_key: str,
    *,
    detail: str = "purchase_detected",
) -> int:
    """
  Cancel pending durable recovery schedules when purchase truth is recorded.
  Additive — does not alter send/decision logic.
  """
    rk = (recovery_key or "").strip()
    if not rk:
        return 0
    det = (detail or "purchase_detected")[:512]
    try:
        rows = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .all()
        )
        if not rows:
            return 0
        n = 0
        for row in rows:
            row.status = STATUS_CANCELLED
            row.last_error = det
            row.updated_at = _utc_now()
            n += 1
        db.session.commit()
        return n
    except SQLAlchemyError:
        db.session.rollback()
        return 0
