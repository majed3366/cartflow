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

_TERMINAL = frozenset(
    {
        STATUS_COMPLETED,
        STATUS_CANCELLED,
        STATUS_SKIPPED_RESUME,
        STATUS_NEEDS_REVIEW,
    }
)


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


def _log_resume_scan(*, count: int, due_count: int) -> None:
    try:
        print("[RECOVERY RESUME SCAN]", flush=True)
        print(f"pending_scheduled={count}", flush=True)
        print(f"due_now={due_count}", flush=True)
    except OSError:
        pass


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


def _log_resume_sent(recovery_key: str) -> None:
    try:
        print("[RECOVERY RESUME SENT]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print("action=dispatched_resume_task", flush=True)
    except OSError:
        pass


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
) -> None:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return
    step, msi = _step_keys(
        multi_slot_index=multi_slot_index,
        sequential_attempt_index=sequential_attempt_index,
    )
    st = (status or "").strip()[:64] or STATUS_COMPLETED
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
            return
        row.status = st
        row.updated_at = _utc_now()
        if detail:
            row.last_error = str(detail)[:512]
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


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


def evaluate_resume_safety(row: RecoverySchedule) -> tuple[bool, str]:
    """Pre-send checks — mirrors runtime gates without bypassing them."""
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

    timing = ctx.get("schedule_timing") if isinstance(ctx.get("schedule_timing"), dict) else {}
    src = str(timing.get("source") or row.delay_source or "")
    if "legacy_recovery_delay" in src.casefold() and "test_patch" not in src:
        fb = timing.get("fallback_reason")
        if fb:
            return False, f"unsafe_legacy_fallback:{fb}"

    return True, "allowed"


def _claim_schedule_row(row_id: int) -> bool:
    try:
        updated = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.id == row_id,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .update(
                {RecoverySchedule.status: STATUS_RUNNING, RecoverySchedule.updated_at: _utc_now()},
                synchronize_session=False,
            )
        )
        db.session.commit()
        return int(updated or 0) == 1
    except SQLAlchemyError:
        db.session.rollback()
        return False


async def resume_one_schedule(
    row: RecoverySchedule,
    *,
    dispatch: bool = True,
) -> Dict[str, Any]:
    _log_resume_candidate(row)
    ok, reason = evaluate_resume_safety(row)
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

    if not _claim_schedule_row(int(row.id)):
        _log_resume_skipped(row.recovery_key, "duplicate_resume_claim")
        return {"recovery_key": row.recovery_key, "dispatched": False, "reason": "duplicate_resume_claim"}

    ctx = load_context(row)
    rc = dict(ctx.get("recovery_context") or {})
    rc["recovery_key"] = row.recovery_key
    rc["store_slug"] = row.store_slug
    rc["schedule_timing"] = ctx.get("schedule_timing")
    abandon_phone = ctx.get("abandon_event_phone") or row.customer_phone
    multi_text = ctx.get("multi_message_text")
    msi = row.multi_slot_index if row.multi_slot_index >= 0 else None
    seq_idx = row.sequential_attempt_index

    import asyncio
    from main import _run_recovery_sequence_after_cart_abandoned  # noqa: PLC0415

    asyncio.create_task(
        _run_recovery_sequence_after_cart_abandoned(
            row.recovery_key,
            0.0,
            row.store_slug,
            row.session_id,
            row.cart_id,
            abandon_phone,
            multi_slot_index=msi,
            multi_message_text=multi_text,
            sequential_attempt_index=seq_idx,
            recovery_context=rc,
        )
    )
    _log_resume_sent(row.recovery_key)
    return {"recovery_key": row.recovery_key, "dispatched": True, "reason": "allowed"}


async def run_recovery_resume_scan_async(
    *,
    max_dispatch: int = 25,
    dry_run: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    if not force and os.getenv("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", "1").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return {"enabled": False, "dispatched": 0}

    try:
        db.create_all()
        now = _utc_now()
        pending = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.status == STATUS_SCHEDULED)
            .count()
        )
        due_rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at <= now,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .limit(max(1, int(max_dispatch)))
            .all()
        )
        _log_resume_scan(count=pending, due_count=len(due_rows))
        outcomes: List[Dict[str, Any]] = []
        dispatched = 0
        for row in due_rows:
            out = await resume_one_schedule(row, dispatch=not dry_run)
            outcomes.append(out)
            if out.get("dispatched"):
                dispatched += 1
        return {
            "enabled": True,
            "dry_run": dry_run,
            "pending_scheduled": pending,
            "due_processed": len(due_rows),
            "dispatched": dispatched,
            "outcomes": outcomes,
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
