# -*- coding: utf-8 -*-
"""
Workspace Performance Recovery Gate 0 — request timeline.

Opt-in via ``?workspace_perf=1`` (or header ``X-CartFlow-Workspace-Perf: 1``).
Records every stage: elapsed ms, pct of total, cache hit/miss, query deltas.
Does not change merchant-visible Workspace content when attached.
"""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional

log = logging.getLogger("cartflow")

_enabled: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "workspace_perf_enabled_v1", default=False
)
_t0: contextvars.ContextVar[float] = contextvars.ContextVar(
    "workspace_perf_t0_v1", default=0.0
)
_stages: contextvars.ContextVar[Optional[list[dict[str, Any]]]] = contextvars.ContextVar(
    "workspace_perf_stages_v1", default=None
)
_notes: contextvars.ContextVar[Optional[list[str]]] = contextvars.ContextVar(
    "workspace_perf_notes_v1", default=None
)
_meta: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "workspace_perf_meta_v1", default=None
)


def workspace_perf_wants_from_request(request: Any) -> bool:
    try:
        qp = getattr(request, "query_params", None)
        if qp is not None and str(qp.get("workspace_perf") or "").strip() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True
        headers = getattr(request, "headers", None)
        if headers is not None:
            return str(headers.get("x-cartflow-workspace-perf") or "").strip() in {
                "1",
                "true",
                "yes",
                "on",
            }
    except Exception:  # noqa: BLE001
        return False
    return False


def workspace_perf_enabled() -> bool:
    return bool(_enabled.get())


def _peek_queries() -> Optional[int]:
    try:
        from services.db_request_audit import (  # noqa: PLC0415
            peek_request_audit_bucket_for_profile,
        )

        b = peek_request_audit_bucket_for_profile()
        if not isinstance(b, dict):
            return None
        q = b.get("query_count")
        if q is None:
            q = b.get("queries")
        return int(q) if q is not None else None
    except Exception:  # noqa: BLE001
        return None


def workspace_perf_begin(*, label: str = "workspace_projection") -> None:
    _enabled.set(True)
    _t0.set(time.perf_counter())
    _stages.set([])
    _notes.set([str(label or "workspace_projection")])
    _meta.set(
        {
            "paint_cache": "unknown",
            "durable_snapshot": "unknown",
            "dce_cache": "unknown",
            "orv_rebuilt": False,
            "facts_rebuilt": False,
            "situations_rebuilt": False,
            "package_reuse": False,
        }
    )


def workspace_perf_note(msg: str) -> None:
    if not workspace_perf_enabled():
        return
    notes = _notes.get()
    if notes is None:
        notes = []
        _notes.set(notes)
    notes.append(str(msg or "")[:240])


def workspace_perf_meta(**kwargs: Any) -> None:
    if not workspace_perf_enabled():
        return
    meta = _meta.get()
    if meta is None:
        meta = {}
        _meta.set(meta)
    for k, v in kwargs.items():
        meta[str(k)] = v


@contextmanager
def workspace_perf_stage(
    name: str,
    *,
    cache: Optional[str] = None,
) -> Iterator[None]:
    if not workspace_perf_enabled():
        yield
        return
    t_origin = float(_t0.get() or time.perf_counter())
    start = time.perf_counter()
    start_ms = round((start - t_origin) * 1000.0, 3)
    q0 = _peek_queries()
    err: Optional[str] = None
    try:
        yield
    except Exception as exc:  # noqa: BLE001
        err = type(exc).__name__
        raise
    finally:
        end = time.perf_counter()
        end_ms = round((end - t_origin) * 1000.0, 3)
        duration_ms = round((end - start) * 1000.0, 3)
        q1 = _peek_queries()
        queries: Optional[int] = None
        if q0 is not None and q1 is not None:
            queries = max(0, int(q1) - int(q0))
        stages = _stages.get()
        if stages is None:
            stages = []
            _stages.set(stages)
        row: dict[str, Any] = {
            "stage": str(name or "unnamed")[:96],
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "queries": queries,
            "error": err,
        }
        if cache is not None:
            row["cache"] = str(cache)[:32]
        stages.append(row)


def workspace_perf_end() -> dict[str, Any]:
    if not workspace_perf_enabled():
        return {"ok": False, "enabled": False, "stages": []}
    t_origin = float(_t0.get() or time.perf_counter())
    total_ms = round((time.perf_counter() - t_origin) * 1000.0, 3)
    stages = list(_stages.get() or [])
    total_queries = 0
    have_q = False
    for row in stages:
        dur = float(row.get("duration_ms") or 0.0)
        row["pct_of_total"] = (
            round((dur / total_ms) * 100.0, 2) if total_ms > 0 else 0.0
        )
        if row.get("queries") is not None:
            have_q = True
            total_queries += int(row.get("queries") or 0)
    ranked = sorted(
        stages, key=lambda r: float(r.get("duration_ms") or 0.0), reverse=True
    )
    out = {
        "ok": True,
        "enabled": True,
        "schema": "workspace_perf_timeline_v1",
        "total_ms": total_ms,
        "stage_count": len(stages),
        "stages": stages,
        "top_stages": ranked[:10],
        "notes": list(_notes.get() or []),
        "meta": dict(_meta.get() or {}),
        "total_queries": total_queries if have_q else None,
        "slowest_stage": (ranked[0].get("stage") if ranked else None),
        "merchant_safe": False,
    }
    try:
        log.info(
            "[WORKSPACE PERF TIMELINE] total_ms=%.1f top=%s meta=%s",
            total_ms,
            [
                f"{r.get('stage')}={r.get('duration_ms')}ms({r.get('pct_of_total')}%)"
                for r in ranked[:5]
            ],
            out.get("meta"),
        )
    except Exception:  # noqa: BLE001
        pass
    _enabled.set(False)
    _stages.set(None)
    _notes.set(None)
    _meta.set(None)
    return out


def workspace_perf_attach_to_payload(
    payload: dict[str, Any], report: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    if not isinstance(report, Mapping) or not report.get("ok"):
        return payload
    payload["_workspace_perf_timeline_v1"] = dict(report)
    return payload


__all__ = [
    "workspace_perf_attach_to_payload",
    "workspace_perf_begin",
    "workspace_perf_enabled",
    "workspace_perf_end",
    "workspace_perf_meta",
    "workspace_perf_note",
    "workspace_perf_stage",
    "workspace_perf_wants_from_request",
]
