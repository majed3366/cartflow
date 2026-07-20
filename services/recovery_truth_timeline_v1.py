# -*- coding: utf-8 -*-
"""
Durable recovery truth timeline — proven transitions for dashboard + debug.

Statuses (ordered):
  scheduled → delay_started → before_send → provider_queued → provider_sent
  → webhook_delivered → customer_reply → continuation_started
"""
from __future__ import annotations

import contextvars
import inspect
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoveryTruthTimelineEvent

log = logging.getLogger("cartflow")

TABLE_NAME = "recovery_truth_timeline_events"

_timeline_profile_request_path: contextvars.ContextVar[str] = contextvars.ContextVar(
    "timeline_ensure_profile_request_path",
    default="-",
)


def set_timeline_profile_request_path(path: str) -> None:
    """Set by HTTP middleware for [TIMELINE ENSURE PROFILE] request_path."""
    _timeline_profile_request_path.set((path or "-")[:512] or "-")


def reset_timeline_profile_request_path() -> None:
    _timeline_profile_request_path.set("-")


def _timeline_ensure_profile_request_path() -> str:
    p = (_timeline_profile_request_path.get() or "").strip()
    if p and p != "-":
        return p[:512]
    try:
        from services.db_request_audit import _audit_bucket  # noqa: PLC0415

        bucket = _audit_bucket.get()
        if bucket and bucket.get("path"):
            return str(bucket["path"])[:512]
    except Exception:  # noqa: BLE001
        pass
    try:
        from services.cart_event_request_scope import (  # noqa: PLC0415
            cart_event_profile_take_meta,
        )

        meta = cart_event_profile_take_meta()
        if meta.get("path"):
            return str(meta["path"])[:512]
    except Exception:  # noqa: BLE001
        pass
    return "-"


def _timeline_ensure_caller_label() -> tuple[str, str]:
    """Return (caller=file:line:func, endpoint=function name)."""
    for fr in inspect.stack()[2:14]:
        if "recovery_truth_timeline_v1.py" in (fr.filename or ""):
            continue
        name = Path(fr.filename or "").name
        caller = f"{name}:{fr.lineno}:{fr.function}"
        return caller, fr.function or "-"
    return "-", "-"

STATUS_SCHEDULED = "scheduled"
STATUS_DELAY_STARTED = "delay_started"
STATUS_BEFORE_SEND = "before_send"
STATUS_PROVIDER_QUEUED = "provider_queued"
STATUS_PROVIDER_SENT = "provider_sent"
STATUS_WEBHOOK_DELIVERED = "webhook_delivered"
STATUS_CUSTOMER_REPLY = "customer_reply"
STATUS_CONTINUATION_STARTED = "continuation_started"

CANONICAL_ORDER: tuple[str, ...] = (
    STATUS_SCHEDULED,
    STATUS_DELAY_STARTED,
    STATUS_BEFORE_SEND,
    STATUS_PROVIDER_QUEUED,
    STATUS_PROVIDER_SENT,
    STATUS_WEBHOOK_DELIVERED,
    STATUS_CUSTOMER_REPLY,
    STATUS_CONTINUATION_STARTED,
)

_ORDER_INDEX = {s: i for i, s in enumerate(CANONICAL_ORDER)}

_MONOTONIC_ONCE = frozenset(
    {
        STATUS_SCHEDULED,
        STATUS_DELAY_STARTED,
        STATUS_BEFORE_SEND,
        STATUS_PROVIDER_QUEUED,
        STATUS_PROVIDER_SENT,
        STATUS_WEBHOOK_DELIVERED,
        STATUS_CONTINUATION_STARTED,
    }
)

_PROVIDER_SEND_STATUSES = frozenset({STATUS_PROVIDER_QUEUED, STATUS_PROVIDER_SENT})
_PROVIDER_SENT_STATUSES = frozenset({STATUS_PROVIDER_SENT})
_LOG_SENT = frozenset({"sent_real", "mock_sent"})

_TRACE_STATUSES = frozenset(
    {
        STATUS_SCHEDULED,
        STATUS_DELAY_STARTED,
        STATUS_BEFORE_SEND,
        STATUS_PROVIDER_QUEUED,
        STATUS_PROVIDER_SENT,
    }
)


def _norm(s: Any) -> str:
    return str(s or "").strip()


def parse_recovery_key(recovery_key: str) -> tuple[str, str]:
    rk = _norm(recovery_key)
    if not rk or ":" not in rk:
        return rk, ""
    store_slug, session_id = rk.split(":", 1)
    return _norm(store_slug), _norm(session_id)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: Any) -> str:
    if dt is None:
        return ""
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError, AttributeError):
        return ""


def _db_label() -> str:
    try:
        eng = db.engine
        url = str(getattr(eng, "url", "") or "")
        if not url:
            return "unknown"
        masked = re.sub(r":([^:@/]+)@", r":***@", url)
        dialect = getattr(getattr(eng, "dialect", None), "name", None) or "unknown"
        return f"{dialect}|{masked[:200]}"
    except Exception:  # noqa: BLE001
        return "unknown"


def _table_exists() -> bool:
    try:
        from sqlalchemy import inspect

        return bool(inspect(db.engine).has_table(TABLE_NAME))
    except Exception:  # noqa: BLE001
        return False


def _emit_timeline_write(
    *,
    recovery_key: str,
    status: str,
    insert_success: str,
    source: str = "",
    table: str = TABLE_NAME,
    row_id: Optional[int] = None,
    error: str = "",
    verify_count: Optional[int] = None,
) -> None:
    ts = _dt_iso(_utc_now())
    parts = [
        "[TIMELINE WRITE]",
        f"recovery_key={recovery_key[:512] or '-'}",
        f"status={status or '-'}",
        f"insert_success={insert_success}",
        f"table={table}",
        f"db={_db_label()}",
        f"timestamp={ts}",
    ]
    if source:
        parts.append(f"source={source[:128]}")
    if row_id is not None:
        parts.append(f"row_id={int(row_id)}")
    if verify_count is not None:
        parts.append(f"verify_count={int(verify_count)}")
    if error:
        parts.append(f"error={error[:240]}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def ensure_timeline_table_ready(*, recovery_key: str = "") -> bool:
    """Create table if missing; return whether table exists."""
    t0 = time.perf_counter()
    caller, endpoint = _timeline_ensure_caller_label()
    request_path = _timeline_ensure_profile_request_path()
    rk_log = (_norm(recovery_key) or "-")[:512]
    executed_schema_check = False
    try:
        import schema_recovery_truth_timeline as sch  # noqa: PLC0415

        schema_once_before = bool(sch._schema_once)
        from schema_recovery_truth_timeline import (  # noqa: PLC0415
            ensure_recovery_truth_timeline_schema,
        )

        ensure_recovery_truth_timeline_schema(db)
        executed_schema_check = not schema_once_before
    except Exception as exc:  # noqa: BLE001
        duration_ms = (time.perf_counter() - t0) * 1000.0
        log.info(
            "[TIMELINE ENSURE PROFILE] caller=%s duration_ms=%.2f endpoint=%s "
            "recovery_key=%s request_path=%s executed_schema_check=%s",
            caller,
            duration_ms,
            endpoint,
            rk_log,
            request_path,
            "false",
        )
        _emit_timeline_write(
            recovery_key="-",
            status="-",
            insert_success="schema_failed",
            source="ensure_timeline_table_ready",
            error=str(exc)[:240],
        )
        return False
    exists = _table_exists()
    duration_ms = (time.perf_counter() - t0) * 1000.0
    log.info(
        "[TIMELINE ENSURE PROFILE] caller=%s duration_ms=%.2f endpoint=%s "
        "recovery_key=%s request_path=%s executed_schema_check=%s",
        caller,
        duration_ms,
        endpoint,
        rk_log,
        request_path,
        "true" if executed_schema_check else "false",
    )
    if not exists:
        _emit_timeline_write(
            recovery_key="-",
            status="-",
            insert_success="table_missing",
            source="ensure_timeline_table_ready",
        )
    return exists


def record_recovery_truth_event(
    *,
    recovery_key: str,
    status: str,
    source: str,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """
    Persist one timeline transition. Returns True when a new row was written.
    Always emits [TIMELINE WRITE] for trace statuses (and on failures).
    """
    rk = _norm(recovery_key)[:512]
    st = _norm(status)[:64]
    src = _norm(source)[:128] or "unknown"
    trace = st in _TRACE_STATUSES or st in _MONOTONIC_ONCE

    if trace:
        _emit_timeline_write(
            recovery_key=rk,
            status=st,
            insert_success="attempt",
            source=src,
        )

    if not rk or not st:
        if trace:
            _emit_timeline_write(
                recovery_key=rk or "-",
                status=st or "-",
                insert_success="skipped_empty",
                source=src,
            )
        return False

    slug = _norm(store_slug)[:255]
    sid = _norm(session_id)[:512]
    cid = _norm(cart_id)[:255]
    if not slug:
        slug, sid_from_rk = parse_recovery_key(rk)
        if not sid and sid_from_rk:
            sid = sid_from_rk

    if not ensure_timeline_table_ready(recovery_key=rk):
        if trace:
            _emit_timeline_write(
                recovery_key=rk,
                status=st,
                insert_success="false",
                source=src,
                error="table_not_ready",
            )
        return False

    try:
        if st in _MONOTONIC_ONCE:
            exists = (
                db.session.query(RecoveryTruthTimelineEvent.id)
                .filter(
                    RecoveryTruthTimelineEvent.recovery_key == rk,
                    RecoveryTruthTimelineEvent.status == st,
                )
                .first()
            )
            if exists is not None:
                if trace:
                    _emit_timeline_write(
                        recovery_key=rk,
                        status=st,
                        insert_success="skipped_duplicate",
                        source=src,
                        row_id=int(getattr(exists, "id", 0) or 0) or None,
                    )
                return False

        row = RecoveryTruthTimelineEvent(
            recovery_key=rk,
            store_slug=slug or "unknown",
            session_id=sid or None,
            cart_id=cid or None,
            status=st,
            source=src,
            created_at=_utc_now(),
        )
        db.session.add(row)
        db.session.commit()
        row_id = int(getattr(row, "id", 0) or 0)
        verify_count = (
            db.session.query(func.count(RecoveryTruthTimelineEvent.id))
            .filter(
                RecoveryTruthTimelineEvent.recovery_key == rk,
                RecoveryTruthTimelineEvent.status == st,
            )
            .scalar()
        )
        try:
            verify_count = int(verify_count or 0)
        except (TypeError, ValueError):
            verify_count = 0

        if trace:
            _emit_timeline_write(
                recovery_key=rk,
                status=st,
                insert_success="true" if verify_count > 0 else "verify_miss",
                source=src,
                row_id=row_id or None,
                verify_count=verify_count,
            )
        try:
            from services.product_data.product_signal_hook_v1 import (  # noqa: PLC0415
                product_signal_try_from_recovery_timeline,
            )

            product_signal_try_from_recovery_timeline(
                store_slug=slug or "",
                session_id=sid or "",
                status=st,
                cart_id=cid or "",
                recovery_key=rk,
                timeline_event_id=row_id or None,
            )
        except Exception:  # noqa: BLE001
            pass
        return verify_count > 0
    except SQLAlchemyError as exc:
        db.session.rollback()
        if trace:
            _emit_timeline_write(
                recovery_key=rk,
                status=st,
                insert_success="false",
                source=src,
                error=str(exc)[:240],
            )
        else:
            log.warning("record_recovery_truth_event failed: %s", exc)
        return False
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        if trace:
            _emit_timeline_write(
                recovery_key=rk,
                status=st,
                insert_success="false",
                source=src,
                error=str(exc)[:240],
            )
        return False


def diagnose_timeline_persistence(recovery_key: str) -> dict[str, Any]:
    """Read-only: table presence, row counts, nearby keys (debug)."""
    rk = _norm(recovery_key)[:512]
    slug, sid = parse_recovery_key(rk)
    out: dict[str, Any] = {
        "recovery_key": rk or None,
        "table": TABLE_NAME,
        "db": _db_label(),
        "table_exists": False,
        "rows_exact_key": 0,
        "rows_session_suffix": 0,
        "rows_store_slug": 0,
        "statuses_exact_key": [],
        "sample_recovery_keys_same_session": [],
        "sample_recovery_keys_same_store": [],
    }
    if not rk:
        return out
    try:
        ensure_timeline_table_ready(recovery_key=rk)
        out["table_exists"] = _table_exists()
        if not out["table_exists"]:
            return out
        out["rows_exact_key"] = int(
            db.session.query(func.count(RecoveryTruthTimelineEvent.id))
            .filter(RecoveryTruthTimelineEvent.recovery_key == rk)
            .scalar()
            or 0
        )
        if sid:
            out["rows_session_suffix"] = int(
                db.session.query(func.count(RecoveryTruthTimelineEvent.id))
                .filter(RecoveryTruthTimelineEvent.recovery_key.like(f"%:{sid}"))
                .scalar()
                or 0
            )
            keys_sess = (
                db.session.query(RecoveryTruthTimelineEvent.recovery_key)
                .filter(RecoveryTruthTimelineEvent.recovery_key.like(f"%:{sid}"))
                .distinct()
                .limit(12)
                .all()
            )
            out["sample_recovery_keys_same_session"] = [
                _norm(k[0]) for k in keys_sess if k and _norm(k[0])
            ]
        if slug:
            out["rows_store_slug"] = int(
                db.session.query(func.count(RecoveryTruthTimelineEvent.id))
                .filter(RecoveryTruthTimelineEvent.store_slug == slug)
                .scalar()
                or 0
            )
            keys_store = (
                db.session.query(RecoveryTruthTimelineEvent.recovery_key)
                .filter(RecoveryTruthTimelineEvent.store_slug == slug)
                .order_by(RecoveryTruthTimelineEvent.id.desc())
                .distinct()
                .limit(12)
                .all()
            )
            out["sample_recovery_keys_same_store"] = [
                _norm(k[0]) for k in keys_store if k and _norm(k[0])
            ]
        status_rows = (
            db.session.query(RecoveryTruthTimelineEvent.status)
            .filter(RecoveryTruthTimelineEvent.recovery_key == rk)
            .all()
        )
        out["statuses_exact_key"] = sorted(
            {_norm(r[0]) for r in status_rows if r and _norm(r[0])}
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:240]
    return out


def get_recovery_truth_timeline(recovery_key: str) -> list[dict[str, Any]]:
    """Ordered timeline for one recovery_key."""
    rk = _norm(recovery_key)[:512]
    if not rk:
        return []
    if not ensure_timeline_table_ready(recovery_key=rk):
        return []
    try:
        rows = (
            db.session.query(RecoveryTruthTimelineEvent)
            .filter(RecoveryTruthTimelineEvent.recovery_key == rk)
            .order_by(
                RecoveryTruthTimelineEvent.created_at.asc(),
                RecoveryTruthTimelineEvent.id.asc(),
            )
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        st = _norm(getattr(row, "status", None))
        out.append(
            {
                "status": st,
                "timestamp": _dt_iso(getattr(row, "created_at", None)),
                "source": _norm(getattr(row, "source", None)) or None,
                "store_slug": _norm(getattr(row, "store_slug", None)) or None,
                "session_id": _norm(getattr(row, "session_id", None)) or None,
                "cart_id": _norm(getattr(row, "cart_id", None)) or None,
                "recovery_key": rk,
                "row_id": int(getattr(row, "id", 0) or 0) or None,
            }
        )
    out.sort(
        key=lambda e: (
            _ORDER_INDEX.get(str(e.get("status") or ""), 999),
            str(e.get("timestamp") or ""),
        )
    )
    return out


def timeline_status_set(recovery_key: str) -> frozenset[str]:
    return frozenset(
        _norm(e.get("status"))
        for e in get_recovery_truth_timeline(recovery_key)
        if _norm(e.get("status"))
    )


def bulk_timeline_status_sets(
    recovery_keys: Any,
) -> dict[str, frozenset[str]]:
    """One query for many keys — dashboard normal-carts batch path."""
    keys: list[str] = []
    seen: set[str] = set()
    for raw in recovery_keys or ():
        rk = _norm(str(raw))[:512]
        if rk and rk not in seen:
            seen.add(rk)
            keys.append(rk)
    if not keys:
        return {}
    if not ensure_timeline_table_ready(recovery_key=keys[0]):
        return {}
    try:
        rows = (
            db.session.query(
                RecoveryTruthTimelineEvent.recovery_key,
                RecoveryTruthTimelineEvent.status,
            )
            .filter(RecoveryTruthTimelineEvent.recovery_key.in_(keys))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return {}
    acc: dict[str, set[str]] = {k: set() for k in keys}
    for rk_raw, st_raw in rows:
        rk = _norm(rk_raw)[:512]
        st = _norm(st_raw)
        if not rk or not st:
            continue
        if rk not in acc:
            acc[rk] = set()
        acc[rk].add(st)
    return {k: frozenset(v) for k, v in acc.items()}


def provider_send_proven(
    recovery_key: str,
    *,
    log_statuses: Optional[Any] = None,
    sent_count: int = 0,
    timeline_statuses: Optional[frozenset[str]] = None,
) -> bool:
    log_ss: set[str] = set()
    if log_statuses:
        for raw in log_statuses:
            t = _norm(raw).lower()
            if t:
                log_ss.add(t)
    if log_ss & _LOG_SENT:
        return True
    if int(sent_count or 0) >= 1:
        return True
    rk = _norm(recovery_key)[:512]
    if not rk:
        return False
    if timeline_statuses is not None:
        return bool(timeline_statuses & _PROVIDER_SENT_STATUSES)
    ts = timeline_status_set(rk)
    return bool(ts & _PROVIDER_SENT_STATUSES)


def customer_reply_proven(
    recovery_key: str,
    *,
    behavioral: Optional[dict[str, Any]] = None,
) -> bool:
    bh = behavioral if isinstance(behavioral, dict) else {}
    if bh.get("customer_replied") is True:
        return True
    rk = _norm(recovery_key)[:512]
    if not rk:
        return False
    return STATUS_CUSTOMER_REPLY in timeline_status_set(rk)


def continuation_started_proven(recovery_key: str) -> bool:
    return STATUS_CONTINUATION_STARTED in timeline_status_set(recovery_key)


def customer_reply_proven_for_dashboard(
    recovery_key: str,
    *,
    behavioral: Optional[dict[str, Any]] = None,
) -> bool:
    del behavioral
    return STATUS_CUSTOMER_REPLY in timeline_status_set(recovery_key)


def map_cart_recovery_log_status_to_timeline(status: str) -> Optional[str]:
    st = _norm(status).lower()
    if st == "queued":
        return STATUS_PROVIDER_QUEUED
    if st in _LOG_SENT:
        return STATUS_PROVIDER_SENT
    return None


__all__ = [
    "_emit_timeline_write",
    "CANONICAL_ORDER",
    "STATUS_BEFORE_SEND",
    "STATUS_CONTINUATION_STARTED",
    "STATUS_CUSTOMER_REPLY",
    "STATUS_DELAY_STARTED",
    "STATUS_PROVIDER_QUEUED",
    "STATUS_PROVIDER_SENT",
    "STATUS_SCHEDULED",
    "STATUS_WEBHOOK_DELIVERED",
    "TABLE_NAME",
    "continuation_started_proven",
    "customer_reply_proven_for_dashboard",
    "diagnose_timeline_persistence",
    "ensure_timeline_table_ready",
    "get_recovery_truth_timeline",
    "reset_timeline_profile_request_path",
    "set_timeline_profile_request_path",
    "map_cart_recovery_log_status_to_timeline",
    "provider_send_proven",
    "record_recovery_truth_event",
    "timeline_status_set",
]
