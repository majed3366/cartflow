# -*- coding: utf-8 -*-
"""
Phase timing for ‎_normal_recovery_merchant_lightweight_alert_list_for_api‎ only.

Uses ‎db_request_audit‎ query counter when present — no extra SQL.
‎OBSERVABILITY_MODE=debug‎؛ ‎CARTFLOW_LIGHTWEIGHT_ALERT_LIST_TRACE=0‎ يعطّل.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

log = logging.getLogger("cartflow")


def lightweight_alert_list_trace_enabled() -> bool:
    try:
        from services.cartflow_observability_mode import (
            observability_lightweight_alert_list_trace_enabled,
        )

        return observability_lightweight_alert_list_trace_enabled()
    except Exception:  # noqa: BLE001
        return False


def _peek_queries() -> Optional[int]:
    try:
        from services.db_request_audit import peek_request_audit_bucket_for_profile

        b = peek_request_audit_bucket_for_profile()
        if b is None:
            return None
        return int(b.get("queries") or 0)
    except Exception:  # noqa: BLE001
        return None


def lightweight_alert_list_trace_ctx_begin() -> Dict[str, Any]:
    """Call once at API list function entry."""
    q0 = _peek_queries()
    t0 = time.perf_counter()
    return {
        "fn_t0": t0,
        "fn_q0": q0,
        "phase_last_t": t0,
        "phase_last_q": q0,
    }


def lightweight_alert_list_trace_phase(
    phase: str,
    ctx: Dict[str, Any],
    **extra: Any,
) -> None:
    if ctx is None:
        return
    phase_s = str(phase).replace("\n", " ")[:160]
    now = time.perf_counter()
    qn = _peek_queries()

    fn_elapsed_ms = (now - float(ctx["fn_t0"])) * 1000.0
    step_elapsed_ms = (now - float(ctx["phase_last_t"])) * 1000.0

    cq = "n/a"
    sq = "n/a"
    if ctx["fn_q0"] is not None and qn is not None:
        cq = str(max(0, int(qn) - int(ctx["fn_q0"])))
    pq = ctx.get("phase_last_q")
    if pq is not None and qn is not None:
        sq = str(max(0, int(qn) - int(pq)))

    ctx["phase_last_t"] = now
    ctx["phase_last_q"] = qn

    extra_parts = []
    for k, v in sorted(extra.items(), key=lambda kv: kv[0]):
        if v is None:
            continue
        extra_parts.append(f"{k}={v}")
    extras = (" " + " ".join(extra_parts)) if extra_parts else ""

    line = (
        f"[LIGHTWEIGHT_ALERT_LIST_TRACE] phase={phase_s}"
        f" fn_elapsed_ms={round(fn_elapsed_ms, 3)} step_ms={round(step_elapsed_ms, 3)}"
        f" queries_cumulative={cq} queries_step={sq}{extras}"
    )
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass

