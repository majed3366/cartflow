# -*- coding: utf-8 -*-
"""
Deep trace for dashboard DB ready path — observability only (Step 4A).

Structured logs: [DB READY STAGE], [DB READY LOCK]
Per-stage query_count + total_sql_ms inside DB ready runs only.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional

log = logging.getLogger("cartflow")

_PREFIX_STAGE = "[DB READY STAGE]"
_PREFIX_LOCK = "[DB READY LOCK]"
_PREFIX_SUBSTAGE = "[DB READY SUBSTAGE]"
_PREFIX_TOP = "[DB READY TOP STAGES]"

_active: ContextVar[bool] = ContextVar("db_ready_diag_active", default=False)
_depth: ContextVar[int] = ContextVar("db_ready_diag_depth", default=0)
_trace_id: ContextVar[str] = ContextVar("db_ready_trace_id", default="")
_t0: ContextVar[float] = ContextVar("db_ready_t0", default=0.0)
_source: ContextVar[str] = ContextVar("db_ready_source", default="")
_slowest_stage: ContextVar[str] = ContextVar("db_ready_slowest_stage", default="")
_slowest_ms: ContextVar[float] = ContextVar("db_ready_slowest_ms", default=0.0)
_last_lock_wait_ms: ContextVar[float] = ContextVar("db_ready_last_lock_wait_ms", default=0.0)
_substage_rows: ContextVar[Optional[list[dict[str, Any]]]] = ContextVar(
    "db_ready_substage_rows", default=None
)

_sql_bucket: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "db_ready_sql_bucket", default=None
)
_sql_listener_registered = False


def db_ready_trace_active() -> bool:
    return bool(_active.get())


def _peek_sql_stats() -> tuple[int, float]:
    bucket = _sql_bucket.get()
    if not bucket:
        return 0, 0.0
    return int(bucket.get("queries") or 0), round(float(bucket.get("sql_ms") or 0.0), 1)


def _elapsed_ms(since_t0: Optional[float] = None) -> float:
    base = since_t0 if since_t0 is not None else float(_t0.get() or 0.0)
    if base <= 0:
        base = time.perf_counter()
    return round((time.perf_counter() - base) * 1000.0, 1)


def _stage_elapsed_ms(stage_t0: float) -> float:
    return round((time.perf_counter() - float(stage_t0)) * 1000.0, 1)


def _emit_stage(stage: str, *, stage_t0: Optional[float] = None, **extra: Any) -> None:
    st = (stage or "unknown").strip()[:64]
    parts = [
        _PREFIX_STAGE,
        f"stage={st}",
        f"elapsed_ms={_elapsed_ms()}",
    ]
    tid = str(_trace_id.get() or "").strip()
    if tid:
        parts.append(f"trace_id={tid}")
    src = str(_source.get() or "").strip()
    if src:
        parts.append(f"source={src[:32]}")
    if stage_t0 is not None:
        parts.append(f"stage_elapsed_ms={_stage_elapsed_ms(stage_t0)}")
    for k, v in extra.items():
        if v is None:
            continue
        parts.append(f"{k}={v}")
    line = " ".join(parts)
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(line, flush=True)
    except OSError:
        pass


def _emit_lock(lock: str, *, wait_ms: Optional[float] = None, hold_ms: Optional[float] = None) -> None:
    parts = [_PREFIX_LOCK, f"lock={(lock or 'unknown')[:32]}"]
    tid = str(_trace_id.get() or "").strip()
    if tid:
        parts.append(f"trace_id={tid}")
    if wait_ms is not None:
        parts.append(f"wait_ms={round(float(wait_ms), 1)}")
        _last_lock_wait_ms.set(round(float(wait_ms), 1))
    if hold_ms is not None:
        parts.append(f"hold_ms={round(float(hold_ms), 1)}")
    line = " ".join(parts)
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(line, flush=True)
    except OSError:
        pass


def _substage_list() -> list[dict[str, Any]]:
    rows = _substage_rows.get()
    return rows if rows is not None else []


def _record_substage(
    name: str,
    *,
    query_count: int,
    sql_ms: float,
    elapsed_ms: float,
    reason: str = "",
    rows_scanned: int = 0,
    rows_updated: int = 0,
    rows_inserted: int = 0,
) -> None:
    st = (name or "unknown").strip()[:64]
    row = {
        "stage": st,
        "query_count": max(0, int(query_count)),
        "sql_ms": round(max(0.0, float(sql_ms)), 1),
        "elapsed_ms": round(max(0.0, float(elapsed_ms)), 1),
        "reason": (reason or "unknown").strip()[:64],
        "rows_scanned": max(0, int(rows_scanned)),
        "rows_updated": max(0, int(rows_updated)),
        "rows_inserted": max(0, int(rows_inserted)),
    }
    rows = _substage_list()
    rows.append(row)
    _substage_rows.set(rows)


def _emit_substage(
    name: str,
    *,
    query_count: int,
    sql_ms: float,
    elapsed_ms: float,
    reason: str = "",
    rows_scanned: int = 0,
    rows_updated: int = 0,
    rows_inserted: int = 0,
) -> None:
    st = (name or "unknown").strip()[:64]
    parts = [
        _PREFIX_SUBSTAGE,
        f"stage={st}",
        f"reason={(reason or 'unknown').strip()[:64]}",
        f"query_count={max(0, int(query_count))}",
        f"sql_ms={round(max(0.0, float(sql_ms)), 1)}",
        f"elapsed_ms={round(max(0.0, float(elapsed_ms)), 1)}",
    ]
    rs = max(0, int(rows_scanned))
    ru = max(0, int(rows_updated))
    ri = max(0, int(rows_inserted))
    if rs or st.startswith("identity_backfill"):
        parts.append(f"rows_scanned={rs}")
    if ru:
        parts.append(f"rows_updated={ru}")
    if ri or st.startswith("identity_backfill"):
        parts.append(f"rows_inserted={ri}")
    tid = str(_trace_id.get() or "").strip()
    if tid:
        parts.append(f"trace_id={tid}")
    line = " ".join(parts)
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(line, flush=True)
    except OSError:
        pass


def _top_substages_sorted() -> list[dict[str, Any]]:
    rows = list(_substage_list())
    rows.sort(
        key=lambda r: (
            -int(r.get("query_count") or 0),
            -float(r.get("sql_ms") or 0.0),
            -float(r.get("elapsed_ms") or 0.0),
        )
    )
    return rows


def _emit_top_stages() -> list[dict[str, Any]]:
    ranked = _top_substages_sorted()
    if not ranked:
        return []
    tid = str(_trace_id.get() or "").strip()
    header = _PREFIX_TOP
    if tid:
        header = f"{header} trace_id={tid}"
    try:
        log.info("%s", header)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(header, flush=True)
    except OSError:
        pass
    for row in ranked[:15]:
        st = str(row.get("stage") or "unknown")
        q = int(row.get("query_count") or 0)
        sql_ms = round(float(row.get("sql_ms") or 0.0), 1)
        el = round(float(row.get("elapsed_ms") or 0.0), 1)
        block = f"{_PREFIX_TOP} stage={st} queries={q} sql_ms={sql_ms} elapsed_ms={el}"
        try:
            log.info("%s", block)
        except Exception:  # noqa: BLE001
            pass
        try:
            print(block, flush=True)
        except OSError:
            pass
    return ranked


def _maybe_install_sql_listener() -> None:
    global _sql_listener_registered
    if _sql_listener_registered:
        return
    try:
        from extensions import db
        from sqlalchemy import event

        eng = db.engine
    except Exception:  # noqa: BLE001
        return

    @event.listens_for(eng, "before_cursor_execute", retval=False)
    def _db_ready_count(  # noqa: N802
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: Any,
    ) -> None:
        bucket = _sql_bucket.get()
        if bucket is None:
            return
        bucket["queries"] = int(bucket.get("queries") or 0) + 1
        bucket["_cursor_t0"] = time.perf_counter()

    @event.listens_for(eng, "after_cursor_execute", retval=False)
    def _db_ready_time(  # noqa: N802
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: Any,
    ) -> None:
        bucket = _sql_bucket.get()
        if bucket is None:
            return
        t0 = bucket.pop("_cursor_t0", None)
        if t0 is not None:
            bucket["sql_ms"] = round(
                float(bucket.get("sql_ms") or 0.0)
                + (time.perf_counter() - float(t0)) * 1000.0,
                2,
            )

    _sql_listener_registered = True


def _begin_trace(*, source: str) -> str:
    seed = f"db_ready:{source}:{time.time_ns()}"
    tid = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    _trace_id.set(tid)
    _t0.set(time.perf_counter())
    _source.set((source or "unknown")[:32])
    _slowest_stage.set("")
    _slowest_ms.set(0.0)
    _last_lock_wait_ms.set(0.0)
    _substage_rows.set([])
    _active.set(True)
    return tid


def _finish_trace(*, success: bool, error: Optional[str] = None) -> None:
    duration_ms = _elapsed_ms()
    slow_st = str(_slowest_stage.get() or "").strip() or "unknown"
    q, sql_ms = _peek_sql_stats()
    top_ranked = _emit_top_stages()
    top = top_ranked[0] if top_ranked else {}
    try:
        from services.db_ready_stage_reason_v1 import (  # noqa: PLC0415
            build_tracked_classifications,
        )

        stage_classifications = build_tracked_classifications(_substage_list())
    except Exception:  # noqa: BLE001
        stage_classifications = []
    payload = {
        "trace_id": str(_trace_id.get() or ""),
        "source": str(_source.get() or ""),
        "duration_ms": duration_ms,
        "slowest_stage": slow_st,
        "slowest_stage_ms": round(float(_slowest_ms.get() or 0.0), 1),
        "lock_wait_ms": round(float(_last_lock_wait_ms.get() or 0.0), 1),
        "query_count": q,
        "total_sql_ms": sql_ms,
        "success": bool(success),
        "error": (error or "")[:255] or None,
        "top_substage": str(top.get("stage") or "")[:64] or None,
        "top_substage_queries": int(top.get("query_count") or 0),
        "top_substage_sql_ms": round(float(top.get("sql_ms") or 0.0), 1),
        "top_substage_elapsed_ms": round(float(top.get("elapsed_ms") or 0.0), 1),
        "top_substages": top_ranked[:15],
        "stage_classifications": stage_classifications,
    }
    _emit_stage("exit", success="1" if success else "0", **{
        k: v for k, v in payload.items() if k not in ("success", "error") and v is not None
    })
    try:
        from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
            record_db_ready_run,
        )

        record_db_ready_run(payload)
    except Exception:  # noqa: BLE001
        pass
    _active.set(False)
    _trace_id.set("")
    _t0.set(0.0)
    _source.set("")
    _substage_rows.set(None)
    _sql_bucket.set(None)


def _new_substage_meta(*, reason: Optional[str] = None) -> dict[str, Any]:
    return {
        "reason": (reason or "").strip()[:64],
        "rows_scanned": 0,
        "rows_updated": 0,
        "rows_inserted": 0,
    }


def _finalize_substage_record(
    name: str,
    meta: dict[str, Any],
    *,
    query_count: int,
    sql_ms: float,
    elapsed_ms: float,
) -> None:
    reason = str(meta.get("reason") or "unknown").strip()[:64]
    rows_scanned = int(meta.get("rows_scanned") or 0)
    rows_updated = int(meta.get("rows_updated") or 0)
    rows_inserted = int(meta.get("rows_inserted") or 0)
    _record_substage(
        name,
        query_count=query_count,
        sql_ms=sql_ms,
        elapsed_ms=elapsed_ms,
        reason=reason,
        rows_scanned=rows_scanned,
        rows_updated=rows_updated,
        rows_inserted=rows_inserted,
    )
    _emit_substage(
        name,
        query_count=query_count,
        sql_ms=sql_ms,
        elapsed_ms=elapsed_ms,
        reason=reason,
        rows_scanned=rows_scanned,
        rows_updated=rows_updated,
        rows_inserted=rows_inserted,
    )


@contextmanager
def db_ready_substage(name: str, *, reason: Optional[str] = None) -> Iterator[dict[str, Any]]:
    """Fine-grained substage — emits [DB READY SUBSTAGE] with query/sql/elapsed + reason."""
    st = (name or "unknown").strip()[:64]
    meta = _new_substage_meta(reason=reason)
    if not db_ready_trace_active():
        yield meta
        return
    st0 = time.perf_counter()
    q0, s0 = _peek_sql_stats()
    try:
        yield meta
    finally:
        q1, s1 = _peek_sql_stats()
        qd = max(0, q1 - q0)
        sd = round(max(0.0, s1 - s0), 1)
        ed = _stage_elapsed_ms(st0)
        if not (meta.get("reason") or "").strip():
            meta["reason"] = "unknown"
        _finalize_substage_record(st, meta, query_count=qd, sql_ms=sd, elapsed_ms=ed)


@contextmanager
def db_ready_run(*, source: str = "dashboard") -> Iterator[None]:
    """Wrap a DB ready entrypoint — nested calls are no-ops for begin/finish."""
    nested = db_ready_trace_active()
    prev_bucket: Optional[dict[str, Any]] = None
    if not nested:
        _depth.set(int(_depth.get()) + 1)
        _begin_trace(source=source)
        _maybe_install_sql_listener()
        bucket: dict[str, Any] = {"queries": 0, "sql_ms": 0.0}
        prev_bucket = _sql_bucket.get()
        _sql_bucket.set(bucket)
        db_ready_log_stage("enter")
    try:
        yield
    except Exception as exc:  # noqa: BLE001
        if not nested:
            _finish_trace(success=False, error=str(exc))
        raise
    else:
        if not nested:
            _finish_trace(success=True)
    finally:
        if not nested:
            _sql_bucket.set(prev_bucket)


@contextmanager
def db_ready_stage(stage: str, *, reason: Optional[str] = None) -> Iterator[dict[str, Any]]:
    """Log stage_start/done with per-stage query + sql deltas + root-cause reason."""
    st = (stage or "unknown").strip()[:64]
    meta = _new_substage_meta(reason=reason)
    if not db_ready_trace_active():
        yield meta
        return
    st0 = time.perf_counter()
    q0, s0 = _peek_sql_stats()
    _emit_stage(f"{st}_start", reason=(meta.get("reason") or None))
    try:
        yield meta
    finally:
        q1, s1 = _peek_sql_stats()
        stage_ms = _stage_elapsed_ms(st0)
        qd = max(0, q1 - q0)
        sd = round(max(0.0, s1 - s0), 1)
        if stage_ms > float(_slowest_ms.get() or 0.0):
            _slowest_ms.set(stage_ms)
            _slowest_stage.set(st)
        if not (meta.get("reason") or "").strip():
            meta["reason"] = "unknown"
        _finalize_substage_record(st, meta, query_count=qd, sql_ms=sd, elapsed_ms=stage_ms)
        _emit_stage(
            f"{st}_done",
            stage_t0=st0,
            query_count=qd,
            total_sql_ms=sd,
            reason=meta.get("reason"),
            rows_scanned=meta.get("rows_scanned"),
            rows_inserted=meta.get("rows_inserted"),
        )


def db_ready_log_stage(stage: str, *, stage_t0: Optional[float] = None, **extra: Any) -> None:
    if not db_ready_trace_active():
        return
    _emit_stage(stage, stage_t0=stage_t0, **extra)


@contextmanager
def db_ready_instrumented_lock(lock: threading.Lock, lock_name: str) -> Iterator[None]:
    """Measure lock wait (acquire) and hold (body) time."""
    if not db_ready_trace_active():
        with lock:
            yield
        return
    wait_t0 = time.perf_counter()
    db_ready_log_stage("warm_lock_wait_start", lock=lock_name)
    lock.acquire()
    wait_ms = _stage_elapsed_ms(wait_t0)
    _emit_lock(lock_name, wait_ms=wait_ms)
    db_ready_log_stage("warm_lock_wait_done", stage_t0=wait_t0, lock=lock_name)
    hold_t0 = time.perf_counter()
    try:
        yield
    finally:
        hold_ms = _stage_elapsed_ms(hold_t0)
        _emit_lock(lock_name, hold_ms=hold_ms)
        lock.release()


def clear_db_ready_diag_for_tests() -> None:
    _active.set(False)
    _depth.set(0)
    _trace_id.set("")
    _t0.set(0.0)
    _source.set("")
    _slowest_stage.set("")
    _slowest_ms.set(0.0)
    _last_lock_wait_ms.set(0.0)
    _substage_rows.set(None)
    _sql_bucket.set(None)


__all__ = [
    "clear_db_ready_diag_for_tests",
    "db_ready_instrumented_lock",
    "db_ready_log_stage",
    "db_ready_run",
    "db_ready_stage",
    "db_ready_substage",
    "db_ready_trace_active",
]
