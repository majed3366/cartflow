# -*- coding: utf-8 -*-
"""
Stage diagnostics for GET /demo/store* — observability only, no behavior change.
"""
from __future__ import annotations

from typing import Any, Optional

from services.request_hang_diag_v1 import (
    begin_hang_trace,
    emit_hang_stage_line,
    hang_elapsed_ms,
    hang_stage_elapsed_ms,
)

_PREFIX = "[DEMO STORE STAGE]"


def begin_demo_store_trace(request: Any) -> str:
    return begin_hang_trace(request)


def demo_store_query_flags(request: Any) -> dict[str, Any]:
    """Read-only query flags for log correlation."""
    out: dict[str, Any] = {
        "store_slug": "-",
        "merchant_activation": "0",
        "reset_demo": "0",
    }
    try:
        qp = getattr(request, "query_params", None)
        if qp is None:
            return out
        ma = str(qp.get("merchant_activation") or "").strip().lower()
        out["merchant_activation"] = "1" if ma in ("1", "true", "yes") else "0"
        rd = str(qp.get("reset_demo") or "").strip().lower()
        out["reset_demo"] = "1" if rd in ("1", "true", "yes") else "0"
        ss = (qp.get("store_slug") or qp.get("store") or "").strip()[:64]
        if ss:
            out["store_slug"] = ss
    except Exception:  # noqa: BLE001
        pass
    return out


def demo_store_log_stage(
    stage: str,
    *,
    request: Any = None,
    store_slug: Optional[str] = None,
    **extra: Any,
) -> None:
    fields = dict(extra)
    if request is not None:
        fields.update(demo_store_query_flags(request))
    if store_slug:
        fields["store_slug"] = str(store_slug)[:64]
    emit_hang_stage_line(_PREFIX, stage, **fields)


def demo_store_context_log_stage(
    stage: str,
    *,
    stage_t0: Optional[float] = None,
    **extra: Any,
) -> None:
    fields = dict(extra)
    if stage_t0 is not None:
        fields["stage_elapsed_ms"] = hang_stage_elapsed_ms(stage_t0)
    emit_hang_stage_line(_PREFIX, stage, **fields)


__all__ = [
    "begin_demo_store_trace",
    "demo_store_context_log_stage",
    "demo_store_log_stage",
    "demo_store_query_flags",
]
