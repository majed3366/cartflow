# -*- coding: utf-8 -*-
"""
Provider Reliability — Durable Retry Ledger (V1).

Implements Provider Reliability Governance V1 §4 Retry Governance and PR-4/PR-7/PR-8:
  * PR-4  retries are durable (DB-backed; survive restart/deploy/crash)
  * PR-RT-1 explicit ownership   PR-RT-2 retry budget   PR-RT-3 exhaustion is terminal+observable
  * PR-RT-4 cancellation         PR-RT-5 never process-memory only
  * PR-RT-7 Retry-After compliance   PR-RT-8 idempotency   PR-RT-9 only retryable retries

Foundation stance: this module is the durable *system of record* for retry intent.
Live re-dispatch is gated by ``PROVIDER_RETRY_ACTIVE`` (default off) so recording a
retryable failure introduces **no merchant-visible behavior change** — no send is
added or altered. ``claim_due_retries`` is the restart-safe, process-memory-free
queue a future dispatcher will consume.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from services.provider_reliability_truth_v1 import (
    DISPOSITION_NON_PROVIDER,
    DISPOSITION_RETRY,
    DISPOSITION_SUPPRESSED,
    DISPOSITION_TERMINAL,
    DISPOSITION_UNKNOWN,
)

# Ledger statuses.
STATUS_PENDING = "pending"      # a retry is scheduled and due at next_attempt_at
STATUS_SUCCEEDED = "succeeded"  # send eventually succeeded
STATUS_EXHAUSTED = "exhausted"  # retry budget spent (terminal, observable)
STATUS_TERMINAL = "terminal"    # non-retryable failure recorded (no retry)
STATUS_SUPPRESSED = "suppressed"
STATUS_UNKNOWN = "unknown"      # observable unknown, awaiting reconciliation
STATUS_CANCELLED = "cancelled"  # cancelled (conversion / opt-out)

_OPEN_STATUSES = frozenset({STATUS_PENDING, STATUS_UNKNOWN})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def retry_active() -> bool:
    """Live re-dispatch gate (PR governance). Default OFF — record-only foundation."""
    v = (os.getenv("PROVIDER_RETRY_ACTIVE") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def default_retry_budget() -> int:
    """Max attempts (retry budget, PR-RT-2). Env ``PROVIDER_RETRY_MAX_ATTEMPTS`` (default 3)."""
    try:
        v = int((os.getenv("PROVIDER_RETRY_MAX_ATTEMPTS") or "3").strip())
    except (TypeError, ValueError):
        v = 3
    return max(1, v)


def _backoff_base_seconds() -> float:
    try:
        v = float((os.getenv("PROVIDER_RETRY_BACKOFF_SECONDS") or "60").strip())
    except (TypeError, ValueError):
        v = 60.0
    return max(0.0, v)


def _backoff_cap_seconds() -> float:
    try:
        v = float((os.getenv("PROVIDER_RETRY_BACKOFF_MAX_SECONDS") or "3600").strip())
    except (TypeError, ValueError):
        v = 3600.0
    return max(1.0, v)


def compute_backoff_seconds(attempt: int) -> float:
    """Exponential backoff for the *attempt*-th retry (1-based), capped."""
    a = max(1, int(attempt))
    base = _backoff_base_seconds()
    raw = base * (2 ** (a - 1))
    return float(min(raw, _backoff_cap_seconds()))


def parse_retry_after(value: Any, *, now: Optional[datetime] = None) -> Optional[float]:
    """
    Parse a provider ``Retry-After`` (PR-8): integer seconds or an HTTP-date.
    Returns seconds-from-now (>=0) or None when absent/unparseable.
    """
    if value is None:
        return None
    now = _aware(now) or _utcnow()
    s = str(value).strip()
    if not s:
        return None
    try:
        return max(0.0, float(s))
    except (TypeError, ValueError):
        pass
    try:
        dt = parsedate_to_datetime(s)
        if dt is None:
            return None
        dt = _aware(dt)
        return max(0.0, (dt - now).total_seconds())
    except (TypeError, ValueError, IndexError):
        return None


def _ensure_schema() -> None:
    try:
        from extensions import db
        from schema_widget import ensure_provider_retry_ledger_schema

        ensure_provider_retry_ledger_schema(db)
        db.create_all()
    except Exception:  # noqa: BLE001
        pass


def _find_row(correlation_key: str, provider: str, step: int) -> Optional[Any]:
    from extensions import db
    from models import ProviderRetryLedger

    return (
        db.session.query(ProviderRetryLedger)
        .filter(
            ProviderRetryLedger.correlation_key == correlation_key,
            ProviderRetryLedger.provider == provider,
            ProviderRetryLedger.step == int(step),
        )
        .first()
    )


def record_send_outcome(
    *,
    correlation_key: str,
    provider: str = "twilio",
    disposition: str,
    failure_class: Optional[str] = None,
    error: Optional[str] = None,
    retry_after: Any = None,
    store_slug: Optional[str] = None,
    session_id: Optional[str] = None,
    cart_id: Optional[str] = None,
    customer_phone: Optional[str] = None,
    step: int = 0,
    max_attempts: Optional[int] = None,
    succeeded: bool = False,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Durably record a send outcome and (for retryable failures) schedule the next attempt.

    Idempotent per (correlation_key, provider, step): re-recording the same outcome
    updates the single ledger row rather than fanning out (PR-RT-8). Never re-dispatches
    here (that is the future gated dispatcher); this only persists retry *intent*.
    """
    ck = (correlation_key or "").strip()[:512]
    prov = (provider or "twilio").strip()[:32]
    now = _aware(now) or _utcnow()
    budget = int(max_attempts) if max_attempts is not None else default_retry_budget()
    result: dict[str, Any] = {
        "ok": True,
        "correlation_key": ck,
        "provider": prov,
        "step": int(step),
        "disposition": disposition,
    }
    if not ck:
        return {"ok": False, "reason": "missing_correlation_key"}

    _ensure_schema()
    from extensions import db
    from models import ProviderRetryLedger

    try:
        row = _find_row(ck, prov, int(step))
        if row is None:
            row = ProviderRetryLedger(
                correlation_key=ck,
                provider=prov,
                store_slug=(store_slug or None),
                session_id=(session_id or None),
                cart_id=(cart_id or None),
                customer_phone=(customer_phone or None),
                step=int(step),
                attempt=0,
                max_attempts=budget,
                status=STATUS_PENDING,
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)

        row.max_attempts = budget
        row.last_disposition = (disposition or "")[:32]
        if failure_class:
            row.last_failure_class = failure_class[:64]
        if error:
            row.last_error = str(error)[:512]
        row.updated_at = now

        if succeeded:
            row.status = STATUS_SUCCEEDED
            row.next_attempt_at = None
            row.claimed_at = None
        elif disposition == DISPOSITION_RETRY:
            next_attempt_number = int(row.attempt) + 1
            if next_attempt_number >= budget:
                # Budget spent — exhaustion is a terminal, observable state (PR-RT-3).
                row.attempt = next_attempt_number
                row.status = STATUS_EXHAUSTED
                row.next_attempt_at = None
            else:
                ra_seconds = parse_retry_after(retry_after, now=now)
                backoff = compute_backoff_seconds(next_attempt_number)
                delay = max(backoff, ra_seconds or 0.0)
                row.attempt = next_attempt_number
                row.status = STATUS_PENDING
                row.claimed_at = None
                row.next_attempt_at = now + timedelta(seconds=delay)
                row.retry_after_until = (
                    now + timedelta(seconds=ra_seconds) if ra_seconds else None
                )
        elif disposition == DISPOSITION_TERMINAL:
            row.status = STATUS_TERMINAL
            row.next_attempt_at = None
        elif disposition == DISPOSITION_SUPPRESSED:
            row.status = STATUS_SUPPRESSED
            row.next_attempt_at = None
        elif disposition == DISPOSITION_NON_PROVIDER:
            row.status = STATUS_SUPPRESSED
            row.next_attempt_at = None
        else:  # DISPOSITION_UNKNOWN
            row.status = STATUS_UNKNOWN
            row.next_attempt_at = None

        db.session.commit()
        result.update(
            {
                "status": row.status,
                "attempt": int(row.attempt),
                "max_attempts": int(row.max_attempts),
                "next_attempt_at": row.next_attempt_at.isoformat()
                if row.next_attempt_at
                else None,
                "retry_active": retry_active(),
            }
        )
        return result
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "reason": f"db_error:{type(exc).__name__}", "detail": str(exc)[:200]}


def claim_due_retries(*, limit: int = 50, now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """
    Restart-safe, process-memory-free claim of due retries (PR-4/PR-RT-5).

    Selects PENDING rows whose next_attempt_at<=now and whose Retry-After floor has
    passed, then atomically stamps claimed_at so a second claim (any process, after any
    restart) does not double-dispatch. Returns claimed row snapshots. Does not send.
    """
    now = _aware(now) or _utcnow()
    _ensure_schema()
    from extensions import db
    from models import ProviderRetryLedger

    claimed: list[dict[str, Any]] = []
    try:
        rows = (
            db.session.query(ProviderRetryLedger)
            .filter(
                ProviderRetryLedger.status == STATUS_PENDING,
                ProviderRetryLedger.claimed_at.is_(None),
                ProviderRetryLedger.next_attempt_at.isnot(None),
                ProviderRetryLedger.next_attempt_at <= now,
            )
            .order_by(ProviderRetryLedger.next_attempt_at.asc())
            .limit(max(1, int(limit)))
            .all()
        )
        for row in rows:
            ra = _aware(row.retry_after_until)
            if ra is not None and ra > now:
                continue
            # Atomic claim: only succeeds if still unclaimed pending.
            updated = (
                db.session.query(ProviderRetryLedger)
                .filter(
                    ProviderRetryLedger.id == row.id,
                    ProviderRetryLedger.status == STATUS_PENDING,
                    ProviderRetryLedger.claimed_at.is_(None),
                )
                .update({"claimed_at": now, "updated_at": now}, synchronize_session=False)
            )
            if updated == 1:
                claimed.append(
                    {
                        "id": int(row.id),
                        "correlation_key": row.correlation_key,
                        "provider": row.provider,
                        "step": int(row.step),
                        "attempt": int(row.attempt),
                        "max_attempts": int(row.max_attempts),
                        "store_slug": row.store_slug,
                        "session_id": row.session_id,
                        "cart_id": row.cart_id,
                        "customer_phone": row.customer_phone,
                    }
                )
        db.session.commit()
        return claimed
    except SQLAlchemyError:
        db.session.rollback()
        return claimed


def cancel_retry(
    *, correlation_key: str, provider: str = "twilio", step: Optional[int] = None, reason: str = ""
) -> int:
    """Cancel open retries for a correlation_key (PR-RT-4: conversion / opt-out)."""
    ck = (correlation_key or "").strip()[:512]
    if not ck:
        return 0
    _ensure_schema()
    from extensions import db
    from models import ProviderRetryLedger

    try:
        q = db.session.query(ProviderRetryLedger).filter(
            ProviderRetryLedger.correlation_key == ck,
            ProviderRetryLedger.provider == (provider or "twilio")[:32],
            ProviderRetryLedger.status.in_(sorted(_OPEN_STATUSES)),
        )
        if step is not None:
            q = q.filter(ProviderRetryLedger.step == int(step))
        n = q.update(
            {
                "status": STATUS_CANCELLED,
                "next_attempt_at": None,
                "last_error": (reason or "cancelled")[:512],
                "updated_at": _utcnow(),
            },
            synchronize_session=False,
        )
        db.session.commit()
        return int(n)
    except SQLAlchemyError:
        db.session.rollback()
        return 0


def ledger_status_counts() -> dict[str, int]:
    """Aggregate ledger counts by status (for metrics/visibility)."""
    _ensure_schema()
    from extensions import db
    from models import ProviderRetryLedger
    from sqlalchemy import func

    counts: dict[str, int] = {}
    try:
        rows = (
            db.session.query(ProviderRetryLedger.status, func.count(ProviderRetryLedger.id))
            .group_by(ProviderRetryLedger.status)
            .all()
        )
        for status, n in rows:
            counts[str(status)] = int(n)
    except SQLAlchemyError:
        db.session.rollback()
    return counts


def due_retry_backlog(*, now: Optional[datetime] = None) -> int:
    """Count of pending retries currently due (retry queue depth)."""
    now = _aware(now) or _utcnow()
    _ensure_schema()
    from extensions import db
    from models import ProviderRetryLedger

    try:
        return int(
            db.session.query(ProviderRetryLedger)
            .filter(
                ProviderRetryLedger.status == STATUS_PENDING,
                ProviderRetryLedger.claimed_at.is_(None),
                ProviderRetryLedger.next_attempt_at.isnot(None),
                ProviderRetryLedger.next_attempt_at <= now,
            )
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


__all__ = [
    "STATUS_CANCELLED",
    "STATUS_EXHAUSTED",
    "STATUS_PENDING",
    "STATUS_SUCCEEDED",
    "STATUS_SUPPRESSED",
    "STATUS_TERMINAL",
    "STATUS_UNKNOWN",
    "cancel_retry",
    "claim_due_retries",
    "compute_backoff_seconds",
    "default_retry_budget",
    "due_retry_backlog",
    "ledger_status_counts",
    "parse_retry_after",
    "record_send_outcome",
    "retry_active",
]
