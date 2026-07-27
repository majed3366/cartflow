# -*- coding: utf-8 -*-
"""
Home Performance Hardening V1 — complete request timeline.

Opt-in via ``?home_perf=1`` (or header ``X-CartFlow-Home-Perf: 1``).
Records every stage: start, end, duration_ms, pct of total.
Does not change merchant-visible Home content when attached.
"""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional

log = logging.getLogger("cartflow")

_enabled: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "home_perf_enabled_v1", default=False
)
_t0: contextvars.ContextVar[float] = contextvars.ContextVar(
    "home_perf_t0_v1", default=0.0
)
_stages: contextvars.ContextVar[Optional[list[dict[str, Any]]]] = contextvars.ContextVar(
    "home_perf_stages_v1", default=None
)
_notes: contextvars.ContextVar[Optional[list[str]]] = contextvars.ContextVar(
    "home_perf_notes_v1", default=None
)


def home_perf_wants_from_request(request: Any) -> bool:
    try:
        qp = getattr(request, "query_params", None)
        if qp is not None and str(qp.get("home_perf") or "").strip() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True
        headers = getattr(request, "headers", None)
        if headers is not None:
            return str(headers.get("x-cartflow-home-perf") or "").strip() in {
                "1",
                "true",
                "yes",
                "on",
            }
    except Exception:  # noqa: BLE001
        return False
    return False


def home_perf_enabled() -> bool:
    return bool(_enabled.get())


def home_perf_begin(*, label: str = "home_summary") -> None:
    _enabled.set(True)
    _t0.set(time.perf_counter())
    _stages.set([])
    _notes.set([str(label or "home_summary")])


def home_perf_note(msg: str) -> None:
    if not home_perf_enabled():
        return
    notes = _notes.get()
    if notes is None:
        notes = []
        _notes.set(notes)
    notes.append(str(msg or "")[:240])


@contextmanager
def home_perf_stage(name: str) -> Iterator[None]:
    if not home_perf_enabled():
        yield
        return
    t_origin = float(_t0.get() or time.perf_counter())
    start = time.perf_counter()
    start_ms = round((start - t_origin) * 1000.0, 3)
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
        stages = _stages.get()
        if stages is None:
            stages = []
            _stages.set(stages)
        stages.append(
            {
                "stage": str(name or "unnamed")[:96],
                "start_ms": start_ms,
                "end_ms": end_ms,
                "duration_ms": duration_ms,
                "error": err,
            }
        )


def home_perf_end() -> dict[str, Any]:
    if not home_perf_enabled():
        return {"ok": False, "enabled": False, "stages": []}
    t_origin = float(_t0.get() or time.perf_counter())
    total_ms = round((time.perf_counter() - t_origin) * 1000.0, 3)
    stages = list(_stages.get() or [])
    for row in stages:
        dur = float(row.get("duration_ms") or 0.0)
        row["pct_of_total"] = (
            round((dur / total_ms) * 100.0, 2) if total_ms > 0 else 0.0
        )
    ranked = sorted(stages, key=lambda r: float(r.get("duration_ms") or 0.0), reverse=True)
    out = {
        "ok": True,
        "enabled": True,
        "schema": "home_perf_timeline_v1",
        "total_ms": total_ms,
        "stage_count": len(stages),
        "stages": stages,
        "top_stages": ranked[:10],
        "notes": list(_notes.get() or []),
    }
    try:
        log.info(
            "[HOME PERF TIMELINE] total_ms=%.1f top=%s",
            total_ms,
            [
                f"{r.get('stage')}={r.get('duration_ms')}ms({r.get('pct_of_total')}%)"
                for r in ranked[:5]
            ],
        )
    except Exception:  # noqa: BLE001
        pass
    _enabled.set(False)
    _stages.set(None)
    _notes.set(None)
    return out


def home_perf_attach_to_payload(payload: dict[str, Any], report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    if not isinstance(report, Mapping) or not report.get("ok"):
        return payload
    # Internal measurement only — never merchant UI contract.
    payload["_home_perf_timeline_v1"] = dict(report)
    payload["_home_perf_timeline_v1"]["merchant_safe"] = False
    return payload


__all__ = [
    "home_perf_attach_to_payload",
    "home_perf_begin",
    "home_perf_enabled",
    "home_perf_end",
    "home_perf_note",
    "home_perf_stage",
    "home_perf_wants_from_request",
]
