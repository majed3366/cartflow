# -*- coding: utf-8 -*-
"""
Step-level query + duration deltas for build_merchant_whatsapp_readiness_card only.

Uses db_request_audit cursor counter when a request audit bucket exists; otherwise
queries= n/a in [WA READINESS STEP] lines. Logging only; no behavioral changes.
"""
from __future__ import annotations

import contextvars
import logging
import os
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import DefaultDict, Iterator, Optional

log = logging.getLogger("cartflow")

_session_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "wa_readiness_step_profile_session", default=False
)


@dataclass
class _Agg:
    calls: int = 0
    total_queries: int = 0
    query_unknown_calls: int = 0
    total_ms: float = 0.0


_agg: DefaultDict[str, _Agg] = defaultdict(_Agg)


def wa_readiness_step_profiling_enabled() -> bool:
    v = (os.getenv("CARTFLOW_WA_READINESS_STEP_PROFILE") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    try:
        from services.db_request_audit import audit_enabled

        return audit_enabled()
    except Exception:  # noqa: BLE001
        return False


def wa_readiness_profile_begin() -> None:
    """Start a profiling session for one card build."""
    _agg.clear()
    _session_active.set(True)


def wa_readiness_profile_end() -> None:
    """Emit TOP and clear session."""
    try:
        _emit_top_ranked()
    finally:
        _session_active.set(False)


def wa_readiness_step_session_active() -> bool:
    return bool(_session_active.get())


def _peek_queries() -> Optional[int]:
    try:
        from services.db_request_audit import peek_request_audit_bucket_for_profile

        b = peek_request_audit_bucket_for_profile()
        if b is None:
            return None
        return int(b.get("queries") or 0)
    except Exception:  # noqa: BLE001
        return None


@contextmanager
def wa_readiness_step(step: str) -> Iterator[None]:
    if not wa_readiness_step_session_active():
        yield
        return

    safe_step = str(step).replace("\n", " ").strip()[:200] or "?"
    q0 = _peek_queries()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        q1 = _peek_queries()
        elapsed_ms = (time.perf_counter() - float(t0)) * 1000.0

        dq_l: Optional[int]
        if q0 is None or q1 is None:
            dq_s = "n/a"
            dq_l = None
        else:
            dq_l = max(0, int(q1) - int(q0))
            dq_s = str(int(dq_l))

        line = (
            f"[WA READINESS STEP] step={safe_step} "
            f"queries={dq_s} duration_ms={round(elapsed_ms, 2)}"
        )
        try:
            print(line, flush=True)
        except OSError:
            pass
        try:
            log.info("%s", line)
        except Exception:  # noqa: BLE001
            pass

        a = _agg[safe_step]
        a.calls += 1
        a.total_ms += elapsed_ms
        if dq_l is None:
            a.query_unknown_calls += 1
        else:
            a.total_queries += int(dq_l)


def _emit_top_ranked() -> None:
    if not _agg:
        return
    rows = sorted(
        _agg.items(),
        key=lambda kv: (-kv[1].total_queries, -kv[1].total_ms, kv[0]),
    )
    for rank, (step, ag) in enumerate(rows[:40], start=1):
        if ag.calls < 1:
            continue
        if ag.query_unknown_calls > 0:
            q_part = "n/a"
        else:
            q_part = str(int(ag.total_queries))
        line = (
            f"[WA READINESS TOP] rank={rank} step={step} "
            f"queries={q_part} duration_ms={round(ag.total_ms, 2)}"
        )
        try:
            print(line, flush=True)
        except OSError:
            pass
        try:
            log.info("%s", line)
        except Exception:  # noqa: BLE001
            pass
