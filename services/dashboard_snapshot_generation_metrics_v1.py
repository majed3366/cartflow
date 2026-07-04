# -*- coding: utf-8 -*-
"""
Snapshot generation metrics v1 — Snapshot Generation Governance SG-4.

In-process, thread-safe counters that make snapshot generation cost observable:
how many snapshot rows were written, how many identical rewrites were avoided
(skip / in-place freshness touch), the change-detection hit rate, and the
resulting write reduction.

No PII. No hot-path instrumentation. Recording happens only on the background
builder generation path (never on the merchant read path).
"""
from __future__ import annotations

from threading import Lock
from typing import Any

# Generation decision modes (mirrors services.dashboard_snapshot_change_v1).
MODE_WRITE = "write"   # a new snapshot row was appended (real generation)
MODE_TOUCH = "touch"   # existing row freshness refreshed in place (no new row)
MODE_SKIP = "skip"     # nothing written — identical content, still fresh

_lock = Lock()

# Aggregate counters.
_decisions_total = 0
_rows_written = 0          # WRITE outcomes -> new rows appended
_touches = 0              # TOUCH outcomes -> in-place freshness refresh
_skips = 0                # SKIP outcomes -> nothing written
_change_detection_checks = 0   # gate active + a previous row existed
_change_detected = 0           # gate found content differed (-> write)
_identical_detected = 0        # gate found identical content (-> skip/touch)
_first_builds = 0              # no previous row (mandatory write)
_gate_disabled_writes = 0     # gate off for the type (write without comparison)

_by_type: dict[str, dict[str, int]] = {}
_by_reason: dict[str, int] = {}


def _type_bucket(snapshot_type: str) -> dict[str, int]:
    b = _by_type.get(snapshot_type)
    if b is None:
        b = {"write": 0, "touch": 0, "skip": 0}
        _by_type[snapshot_type] = b
    return b


def record_generation_decision(
    *,
    snapshot_type: str,
    mode: str,
    reason: str,
    change_checked: bool,
    content_changed: bool,
) -> None:
    """Record one generation decision from the guarded snapshot writer."""
    stype = (snapshot_type or "unknown").strip() or "unknown"
    m = (mode or "").strip().lower()
    rsn = (reason or "").strip() or "unspecified"
    global _decisions_total, _rows_written, _touches, _skips
    global _change_detection_checks, _change_detected, _identical_detected
    global _first_builds, _gate_disabled_writes
    with _lock:
        _decisions_total += 1
        bucket = _type_bucket(stype)
        _by_reason[rsn] = _by_reason.get(rsn, 0) + 1
        if m == MODE_WRITE:
            _rows_written += 1
            bucket["write"] += 1
        elif m == MODE_TOUCH:
            _touches += 1
            bucket["touch"] += 1
        elif m == MODE_SKIP:
            _skips += 1
            bucket["skip"] += 1
        if change_checked:
            _change_detection_checks += 1
            if content_changed:
                _change_detected += 1
            else:
                _identical_detected += 1
        else:
            if rsn == "first_build":
                _first_builds += 1
            elif rsn == "gate_disabled":
                _gate_disabled_writes += 1


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * float(part) / float(whole), 2)


def snapshot_generation_metrics_report() -> dict[str, Any]:
    """Read-only snapshot generation metrics (SG-4 observability)."""
    with _lock:
        decisions = _decisions_total
        rows_written = _rows_written
        touches = _touches
        skips = _skips
        checks = _change_detection_checks
        changed = _change_detected
        identical = _identical_detected
        rows_avoided = touches + skips
        by_type = {k: dict(v) for k, v in _by_type.items()}
        by_reason = dict(_by_reason)
        first_builds = _first_builds
        gate_disabled = _gate_disabled_writes

    # In the pre-optimization model every decision produced a new row, so the
    # theoretical baseline row count == number of decisions.
    return {
        "decisions_total": decisions,
        "rows_written": rows_written,
        "rows_avoided": rows_avoided,
        "writes_executed": rows_written,
        "writes_avoided": rows_avoided,
        "touches": touches,
        "skips": skips,
        "first_builds": first_builds,
        "gate_disabled_writes": gate_disabled,
        "change_detection_checks": checks,
        "change_detected": changed,
        "identical_detected": identical,
        # Fraction of change-detection checks where content was identical
        # (i.e. a write we were able to avoid).
        "change_detection_hit_rate_pct": _pct(identical, checks),
        # Fraction of all decisions that skipped entirely (no DB write at all).
        "snapshot_skip_rate_pct": _pct(skips, decisions),
        # Rows eliminated vs the append-every-tick baseline.
        "write_reduction_pct": _pct(rows_avoided, decisions),
        "average_write_reduction": (
            round(float(rows_avoided) / float(decisions), 4) if decisions else 0.0
        ),
        "by_type": by_type,
        "by_reason": by_reason,
    }


def reset_snapshot_generation_metrics() -> None:
    """Reset all counters (tests / process restart diagnostics)."""
    global _decisions_total, _rows_written, _touches, _skips
    global _change_detection_checks, _change_detected, _identical_detected
    global _first_builds, _gate_disabled_writes
    with _lock:
        _decisions_total = 0
        _rows_written = 0
        _touches = 0
        _skips = 0
        _change_detection_checks = 0
        _change_detected = 0
        _identical_detected = 0
        _first_builds = 0
        _gate_disabled_writes = 0
        _by_type.clear()
        _by_reason.clear()


__all__ = [
    "MODE_SKIP",
    "MODE_TOUCH",
    "MODE_WRITE",
    "record_generation_decision",
    "reset_snapshot_generation_metrics",
    "snapshot_generation_metrics_report",
]
