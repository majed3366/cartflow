# -*- coding: utf-8 -*-
"""Debug trace for durable attempt-2 scheduling / dispatch (production gap analysis)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule
from services.recovery_multi_message import resolve_configured_message_count
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    _utc_now,
    evaluate_resume_safety,
    load_context,
)

_log = logging.getLogger("cartflow")


def _env_truthy(name: str, *, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _attempt_index_from_row(row: RecoverySchedule) -> int:
    if row.sequential_attempt_index is not None:
        try:
            return max(1, int(row.sequential_attempt_index))
        except (TypeError, ValueError):
            pass
    if row.multi_slot_index is not None and int(row.multi_slot_index) >= 0:
        return max(1, int(row.multi_slot_index))
    return max(1, int(row.step or 1))


def _row_is_attempt2(row: RecoverySchedule) -> bool:
    return _attempt_index_from_row(row) >= 2


def _find_attempt2_schedule_row(
    recovery_key: str,
) -> Optional[RecoverySchedule]:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return None
    try:
        db.create_all()
        rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == rk)
            .order_by(RecoverySchedule.step.asc(), RecoverySchedule.id.asc())
            .all()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("attempt2 trace schedule query failed: %s", exc)
        return None
    for row in rows:
        if _row_is_attempt2(row):
            return row
    return None


def _all_schedule_rows(recovery_key: str) -> List[Dict[str, Any]]:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return []
    try:
        db.create_all()
        rows = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == rk)
            .order_by(RecoverySchedule.step.asc(), RecoverySchedule.id.asc())
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []
    out: List[Dict[str, Any]] = []
    now = _utc_now()
    for row in rows:
        due = row.due_at
        if due is not None and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        out.append(
            {
                "schedule_id": int(row.id),
                "step": int(row.step or 1),
                "multi_slot_index": int(row.multi_slot_index),
                "sequential_attempt_index": row.sequential_attempt_index,
                "attempt_index": _attempt_index_from_row(row),
                "status": (row.status or "").strip(),
                "due_at": due.isoformat() if due is not None else None,
                "created_at": (
                    row.created_at.isoformat()
                    if getattr(row, "created_at", None) is not None
                    else None
                ),
                "scheduled_at": (
                    row.scheduled_at.isoformat()
                    if getattr(row, "scheduled_at", None) is not None
                    else None
                ),
                "due_now": bool(due is not None and due <= now),
                "delay_source": (row.delay_source or "").strip()[:128],
                "effective_delay_seconds": float(row.effective_delay_seconds or 0),
            }
        )
    return out


def _step2_sent_in_logs(session_id: str, cart_id: Optional[str]) -> bool:
    from main import _cart_recovery_log_has_successful_send_for_step  # noqa: PLC0415

    return _cart_recovery_log_has_successful_send_for_step(
        session_id, cart_id, 2
    )


def _infer_dispatch_called(row: Optional[RecoverySchedule]) -> str:
    if row is None:
        return "false"
    st = (row.status or "").strip().lower()
    if st == STATUS_SCHEDULED:
        return "false"
    if st == "running":
        return "true_running"
    if st in ("completed", "skipped_resume", "skipped_duplicate", "whatsapp_failed"):
        return f"true_terminal:{st}"
    return f"true_status:{st}"


def build_attempt2_trace(recovery_key: str) -> Dict[str, Any]:
    """Full attempt-2 durable scheduling snapshot for one recovery_key."""
    rk = (recovery_key or "").strip()[:512]
    from services.cartflow_session_truth import parse_recovery_key

    store_slug, session_id = parse_recovery_key(rk)
    cart_id: Optional[str] = None

    store_obj = None
    store_obj_fresh = None
    reason_tag: Optional[str] = None
    try:
        from main import (  # noqa: PLC0415
            _cart_recovery_reason_latest_row,
            _cart_recovery_reason_latest_row_any_store,
            _fresh_store_row_for_recovery_templates,
            _load_store_row_for_recovery,
            _normal_recovery_gate_sent_count,
            _reason_tag_for_session,
            _session_recovery_followup_next_due_at,
        )
        from services.recovery_multi_message import diagnose_multi_message_config

        store_obj = _load_store_row_for_recovery(store_slug or "")
        store_obj_fresh = _fresh_store_row_for_recovery_templates(store_slug or "")
        reason_tag = _reason_tag_for_session(store_slug or "", session_id or "") or None
        if not reason_tag and session_id:
            row_any = _cart_recovery_reason_latest_row_any_store(session_id)
            if row_any is not None:
                reason_tag = (row_any.reason or "").strip() or None
        if not reason_tag and store_slug and session_id:
            row_ss = _cart_recovery_reason_latest_row(store_slug, session_id)
            if row_ss is not None:
                reason_tag = (row_ss.reason or "").strip() or None
        sent_count = _normal_recovery_gate_sent_count(rk, session_id or "", cart_id)
        mem_due = (_session_recovery_followup_next_due_at.get(rk) or "").strip()
    except Exception as exc:  # noqa: BLE001
        _log.warning("attempt2 trace runtime helpers failed: %s", exc)
        sent_count = 0
        mem_due = ""
        diagnose_multi_message_config = None  # type: ignore[misc, assignment]

    attempt2_row = _find_attempt2_schedule_row(rk)
    schedule_rows = _all_schedule_rows(rk)

    recovery_ctx: Dict[str, Any] = {}
    ctx_configured_count: Optional[int] = None
    ctx_configured_source: Optional[str] = None
    if attempt2_row is not None:
        ctx = load_context(attempt2_row)
        rc = ctx.get("recovery_context")
        if isinstance(rc, dict):
            recovery_ctx = rc
            raw_cc = rc.get("configured_message_count")
            if raw_cc is not None:
                try:
                    ctx_configured_count = int(raw_cc)
                except (TypeError, ValueError):
                    ctx_configured_count = None
            ctx_configured_source = (
                str(rc.get("configured_message_count_source") or "").strip() or None
            )
            if not reason_tag and rc.get("reason_tag"):
                reason_tag = str(rc.get("reason_tag")).strip() or None
        cart_id = (attempt2_row.cart_id or "").strip() or cart_id

    store_for_templates = store_obj_fresh or store_obj
    template_diag: Dict[str, Any] = {}
    if diagnose_multi_message_config is not None:
        template_diag = diagnose_multi_message_config(reason_tag, store_for_templates)

    cfg_count, cfg_source = resolve_configured_message_count(
        reason_tag,
        store_for_templates,
        recovery_context=recovery_ctx or None,
    )

    now = _utc_now()
    due_at_iso: Optional[str] = None
    due_now = False
    schedule_status = "-"
    schedule_row_exists = attempt2_row is not None
    created_at_iso: Optional[str] = None
    attempt_index = 2

    if attempt2_row is not None:
        attempt_index = _attempt_index_from_row(attempt2_row)
        schedule_status = (attempt2_row.status or "").strip() or "-"
        created_at_iso = (
            attempt2_row.created_at.isoformat()
            if getattr(attempt2_row, "created_at", None) is not None
            else None
        )
        due = attempt2_row.due_at
        if due is not None:
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            else:
                due = due.astimezone(timezone.utc)
            due_at_iso = due.isoformat()
            due_now = due <= now
        cart_id = (attempt2_row.cart_id or "").strip() or cart_id

    next_attempt_due_at = due_at_iso or mem_due or "-"

    resume_ok = False
    resume_reason = "no_row"
    if attempt2_row is not None and (attempt2_row.status or "").strip() == STATUS_SCHEDULED:
        resume_ok, resume_reason = evaluate_resume_safety(
            attempt2_row, trust_durable_schedule=True
        )

    scanner_enabled = _env_truthy("CARTFLOW_DB_DUE_SCANNER_ENABLED", default=False)
    picked_by_scanner = bool(
        scanner_enabled
        and schedule_row_exists
        and due_now
        and (attempt2_row.status or "").strip() == STATUS_SCHEDULED
        and resume_ok
    )

    step2_sent = _step2_sent_in_logs(session_id or "", cart_id)
    dispatch_called = _infer_dispatch_called(attempt2_row)

    blocked_by = "-"
    if step2_sent:
        blocked_by = "-"
    elif not schedule_row_exists:
        blocked_by = "schedule_row_missing"
    elif schedule_status != STATUS_SCHEDULED:
        if schedule_status == "running":
            blocked_by = "in_flight_running"
        else:
            blocked_by = f"terminal_status:{schedule_status}"
    elif not due_now:
        blocked_by = "delay_not_elapsed"
    elif not resume_ok:
        blocked_by = resume_reason
    else:
        blocked_by = "-"

    if step2_sent:
        decision = "sent_attempt_2"
    elif not schedule_row_exists:
        decision = "schedule_missing"
    elif not due_now:
        decision = "waiting_due"
    elif schedule_status == STATUS_SCHEDULED and resume_ok:
        decision = "due_ready_to_dispatch"
    elif schedule_status == STATUS_SCHEDULED:
        decision = f"due_blocked:{resume_reason}"
    elif schedule_status == "running":
        decision = "dispatch_in_progress"
    else:
        decision = f"terminal:{schedule_status}"

    trace = {
        "recovery_key": rk,
        "store_slug": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "reason_tag": reason_tag,
        "store_zid_runtime": (
            (getattr(store_obj, "zid_store_id", None) or "").strip()
            if store_obj is not None
            else None
        ),
        "store_zid_fresh": (
            (getattr(store_obj_fresh, "zid_store_id", None) or "").strip()
            if store_obj_fresh is not None
            else None
        ),
        "recovery_context_configured_count": ctx_configured_count,
        "recovery_context_configured_source": ctx_configured_source,
        "template_diagnosis": template_diag,
        "configured_count": int(cfg_count),
        "configured_count_source": cfg_source,
        "sent_count": int(sent_count),
        "current_attempt": int(sent_count) if sent_count > 0 else 1,
        "attempt_index": int(attempt_index),
        "next_attempt_due_at": next_attempt_due_at,
        "schedule_row_exists": schedule_row_exists,
        "schedule_id": int(attempt2_row.id) if attempt2_row is not None else None,
        "schedule_status": schedule_status,
        "schedule_created_at": created_at_iso,
        "due_at": due_at_iso,
        "due_now": due_now,
        "picked_by_scanner": picked_by_scanner,
        "db_due_scanner_enabled": scanner_enabled,
        "resume_safety_ok": resume_ok,
        "resume_safety_reason": resume_reason,
        "dispatch_called": dispatch_called,
        "blocked_by": blocked_by,
        "decision": decision,
        "step2_sent_in_logs": step2_sent,
        "schedule_rows": schedule_rows,
    }
    return trace


def emit_attempt2_trace_log(
    trace: Dict[str, Any],
    *,
    path: str = "",
) -> None:
    """Emit single-line production grep target."""
    line = (
        "[ATTEMPT 2 TRACE] "
        f"recovery_key={trace.get('recovery_key') or '-'} "
        f"configured_count={trace.get('configured_count')} "
        f"sent_count={trace.get('sent_count')} "
        f"current_attempt={trace.get('current_attempt')} "
        f"next_attempt_due_at={trace.get('next_attempt_due_at') or '-'} "
        f"schedule_row_exists={str(trace.get('schedule_row_exists')).lower()} "
        f"schedule_status={trace.get('schedule_status') or '-'} "
        f"due_now={str(trace.get('due_now')).lower()} "
        f"picked_by_scanner={str(trace.get('picked_by_scanner')).lower()} "
        f"dispatch_called={trace.get('dispatch_called') or 'false'} "
        f"blocked_by={trace.get('blocked_by') or '-'} "
        f"decision={trace.get('decision') or '-'} "
        f"path={(path or '-')[:64]}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    _log.info("%s", line)


def trace_attempt2_for_recovery_key(
    recovery_key: str,
    *,
    path: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    trace = build_attempt2_trace(recovery_key)
    if extra:
        trace.update(extra)
    emit_attempt2_trace_log(trace, path=path)
    return trace


def trace_attempt2_after_followup_scheduled(
    recovery_key: str,
    *,
    seq_row: Any,
    next_idx: int,
    due_dt_iso: str,
    path: str = "post_send_schedule_next",
) -> None:
    trace = build_attempt2_trace(recovery_key)
    trace["path"] = path
    trace["scheduled_next_index"] = int(next_idx)
    trace["persist_row_id"] = int(seq_row.id) if seq_row is not None else None
    trace["persist_ok"] = seq_row is not None
    if seq_row is None:
        trace["blocked_by"] = "persist_returned_none"
        trace["decision"] = "schedule_persist_failed"
        trace["schedule_row_exists"] = False
    emit_attempt2_trace_log(trace, path=path)


def trace_attempt2_at_send_gate(
    recovery_key: str,
    *,
    step_num: int,
    allowed: bool,
    block_reason: str,
    path: str = "send_gate",
) -> None:
    if int(step_num) < 2:
        return
    trace = build_attempt2_trace(recovery_key)
    trace["path"] = path
    trace["send_gate_allowed"] = bool(allowed)
    if not allowed:
        trace["blocked_by"] = (block_reason or "send_gate")[:120]
        trace["decision"] = f"blocked_at_send:{block_reason}"
    elif trace.get("step2_sent_in_logs"):
        trace["decision"] = "sent_attempt_2"
    emit_attempt2_trace_log(trace, path=path)
