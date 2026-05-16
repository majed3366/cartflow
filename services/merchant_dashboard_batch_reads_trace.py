# -*- coding: utf-8 -*-
"""
Sub-step timing for ‎main._merchant_normal_dashboard_batch_reads‎ — سجلات فقط.

تفعيل: ‎CARTFLOW_OBSERVABILITY_MODE=debug‎؛ ‎CARTFLOW_MERCHANT_BATCH_READS_TRACE=0‎ يعطّل.
لا استعلامات إضافية؛ يعتمد عدّاد ‎db_request_audit‎ إن وُجد.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("cartflow")

Seg = Tuple[str, float, str, str, Optional[int]]
# step, duration_ms, queries_step, queries_fn_cumulative, rows_loaded


def merchant_dashboard_batch_reads_trace_enabled() -> bool:
    try:
        from services.cartflow_observability_mode import (
            observability_merchant_dashboard_batch_reads_trace_enabled,
        )

        return observability_merchant_dashboard_batch_reads_trace_enabled()
    except Exception:  # noqa: BLE001
        return False


def merchant_dashboard_batch_reads_trace_peek_for_seg(
    tr: Optional[Dict[str, Any]],
) -> Optional[int]:
    """لالتقاط نقطة عدّ قبل/أثناء مقطع — بدون تشغيل عند تعطيل التتبّع خارجياً يُفسَّر بدون استدعاء."""
    if tr is None:
        return None
    return _peek_q()


def _peek_q() -> Optional[int]:
    try:
        from services.db_request_audit import peek_request_audit_bucket_for_profile

        b = peek_request_audit_bucket_for_profile()
        if b is None:
            return None
        return int(b.get("queries") or 0)
    except Exception:  # noqa: BLE001
        return None


def merchant_dashboard_batch_reads_trace_begin(
    *,
    slug_len: int,
    full_rows_len: int,
) -> Optional[Dict[str, Any]]:
    if not merchant_dashboard_batch_reads_trace_enabled():
        return None
    fn_t0 = time.perf_counter()
    fn_q0 = _peek_q()
    ctx: Dict[str, Any] = {
        "fn_t0": fn_t0,
        "fn_q0": fn_q0,
        "segments": [],
    }
    line = (
        f"[MERCHANT_BATCH_READS_SUBSTEP] step=batch_reads_enter caller=_merchant_normal_dashboard_batch_reads "
        f"fn_elapsed_ms=0 slug_len_chars={slug_len} full_rows_candidates={full_rows_len} "
        f"queries_cumulative=0 queries_step=n/a rows_loaded=n/a"
    )
    _emit(line)
    return ctx


def _emit(line: str) -> None:
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def merchant_dashboard_batch_reads_trace_seg_end(
    tr: Optional[Dict[str, Any]],
    seg_t0: float,
    seg_q0: Optional[int],
    step: str,
    *,
    rows_loaded: Optional[int] = None,
) -> None:
    if tr is None:
        return
    fn_q0_any = tr.get("fn_q0")
    duration_ms = (time.perf_counter() - float(seg_t0)) * 1000.0
    q_now = _peek_q()
    q_step = "n/a"
    if seg_q0 is not None and q_now is not None:
        q_step = str(max(0, int(q_now) - int(seg_q0)))
    cum = "n/a"
    if fn_q0_any is not None and q_now is not None:
        cum = str(max(0, int(q_now) - int(fn_q0_any)))
    step_s = str(step).replace("\n", " ")[:120]
    rows_s = str(int(rows_loaded)) if rows_loaded is not None else "n/a"
    line = (
        f"[MERCHANT_BATCH_READS_SUBSTEP] step={step_s} caller=_merchant_normal_dashboard_batch_reads "
        f"duration_ms={round(duration_ms, 3)} queries_step={q_step} "
        f"queries_cumulative_fn={cum} rows_loaded={rows_s}"
    )
    _emit(line)
    lst: List[Seg] = tr["segments"]
    lst.append((step_s, duration_ms, q_step, cum, rows_loaded))


def merchant_dashboard_batch_reads_trace_finish(tr: Optional[Dict[str, Any]]) -> None:
    if tr is None:
        return
    segments: List[Seg] = list(tr.get("segments") or [])
    if not segments:
        return
    sorted_segs = sorted(segments, key=lambda s: (-s[1], s[0]))
    for rank, (step_s, dur_ms, dq, cq, nrow) in enumerate(sorted_segs, start=1):
        rs = str(int(nrow)) if nrow is not None else "n/a"
        rl = (
            f"[MERCHANT_BATCH_READS_RANK] rank={rank} step={step_s} "
            f"duration_ms={round(float(dur_ms), 3)} queries_step={dq} "
            f"queries_cumulative_fn={cq} rows_loaded={rs}"
        )
        _emit(rl)
    total_ms = (time.perf_counter() - float(tr["fn_t0"])) * 1000.0
    q_end = _peek_q()
    fq = tr.get("fn_q0")
    qtot = "n/a"
    if fq is not None and q_end is not None:
        qtot = str(max(0, int(q_end) - int(fq)))
    tl = (
        f"[MERCHANT_BATCH_READS_SUBSTEP] step=batch_reads_total_summary "
        f"duration_ms={round(total_ms, 3)} queries_cumulative_fn={qtot}"
    )
    _emit(tl)

