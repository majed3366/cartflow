# -*- coding: utf-8 -*-
"""
Durable lifecycle closure v2 — one canonical terminal status per recovery_key.

Statuses: purchase_completed | returned_to_site | replied | failed | cancelled

Precedence when updating existing row:
  purchase_completed > returned_to_site > replied > failed > cancelled
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import LifecycleClosureRecord
from schema_lifecycle_closure import ensure_lifecycle_closure_schema

log = logging.getLogger("cartflow")

CLOSURE_PURCHASE_COMPLETED = "purchase_completed"
CLOSURE_RETURNED_TO_SITE = "returned_to_site"
CLOSURE_REPLIED = "replied"
CLOSURE_FAILED = "failed"
CLOSURE_CANCELLED = "cancelled"

CANONICAL_CLOSURE_STATUSES = frozenset(
    {
        CLOSURE_PURCHASE_COMPLETED,
        CLOSURE_RETURNED_TO_SITE,
        CLOSURE_REPLIED,
        CLOSURE_FAILED,
        CLOSURE_CANCELLED,
    }
)

_CLOSURE_RANK: dict[str, int] = {
    CLOSURE_CANCELLED: 1,
    CLOSURE_FAILED: 2,
    CLOSURE_REPLIED: 3,
    CLOSURE_RETURNED_TO_SITE: 4,
    CLOSURE_PURCHASE_COMPLETED: 5,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _emit(tag: str, **fields: Any) -> None:
    parts = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        parts.append(f"{k}={str(v)[:220]}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def reset_lifecycle_closure_truth_for_tests() -> None:
    try:
        ensure_lifecycle_closure_schema(db)
        db.session.query(LifecycleClosureRecord).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


def get_durable_closure(recovery_key: str) -> Optional[dict[str, Any]]:
    rk = (recovery_key or "").strip()
    if not rk:
        return None
    try:
        ensure_lifecycle_closure_schema(db)
        row = (
            db.session.query(LifecycleClosureRecord)
            .filter(LifecycleClosureRecord.recovery_key == rk)
            .first()
        )
        if row is None:
            return None
        ct = row.closure_time
        if ct is not None and getattr(ct, "tzinfo", None) is None:
            ct = ct.replace(tzinfo=timezone.utc)
        return {
            "recovery_key": rk,
            "closure_status": (row.closure_status or "").strip(),
            "closure_reason": (row.closure_reason or "").strip(),
            "closure_source": (row.closure_source or "").strip(),
            "closure_time": ct.astimezone(timezone.utc).isoformat() if ct else None,
        }
    except Exception:  # noqa: BLE001
        return None


def record_durable_lifecycle_closure(
    recovery_key: str,
    *,
    closure_status: str,
    closure_reason: str,
    closure_source: str,
    closure_time: Optional[datetime] = None,
) -> bool:
    """
    Persist durable closure. Returns True when row written or upgraded.
    """
    rk = (recovery_key or "").strip()
    st = (closure_status or "").strip()
    if not rk or st not in CANONICAL_CLOSURE_STATUSES:
        return False

    reason = (closure_reason or st)[:128]
    source = (closure_source or "unknown")[:128]
    when = closure_time or _utc_now()
    new_rank = _CLOSURE_RANK.get(st, 0)

    ensure_lifecycle_closure_schema(db)
    try:
        row = (
            db.session.query(LifecycleClosureRecord)
            .filter(LifecycleClosureRecord.recovery_key == rk)
            .first()
        )
        if row is None:
            row = LifecycleClosureRecord(
                recovery_key=rk,
                closure_status=st[:64],
                closure_reason=reason,
                closure_source=source,
                closure_time=when,
            )
            db.session.add(row)
            db.session.commit()
            _emit(
                "LIFECYCLE CLOSURE RECORDED",
                recovery_key=rk,
                closure_status=st,
                closure_reason=reason,
                closure_source=source,
            )
            return True

        cur = (row.closure_status or "").strip()
        cur_rank = _CLOSURE_RANK.get(cur, 0)
        if new_rank < cur_rank:
            return False
        row.closure_status = st[:64]
        row.closure_reason = reason
        row.closure_source = source
        row.closure_time = when
        db.session.commit()
        _emit(
            "LIFECYCLE CLOSURE UPDATED",
            recovery_key=rk,
            closure_status=st,
            closure_reason=reason,
            closure_source=source,
            previous=cur or "-",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.warning("durable lifecycle closure failed: %s", exc)
        return False


__all__ = [
    "CANONICAL_CLOSURE_STATUSES",
    "CLOSURE_CANCELLED",
    "CLOSURE_FAILED",
    "CLOSURE_PURCHASE_COMPLETED",
    "CLOSURE_REPLIED",
    "CLOSURE_RETURNED_TO_SITE",
    "get_durable_closure",
    "record_durable_lifecycle_closure",
    "reset_lifecycle_closure_truth_for_tests",
]
