# -*- coding: utf-8 -*-
"""Measure normal-carts live vs slim snapshot payload sizes (read-only)."""
from __future__ import annotations

import json
import statistics
from typing import Any

from services.dashboard_snapshot_normal_carts_slim_v1 import (
    slim_normal_carts_payload_for_snapshot,
    slim_normal_carts_row_for_snapshot,
)
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    encode_snapshot_payload_json,
    snapshot_payload_json_cap,
)


def _json_bytes(obj: object) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))


def _row_json_bytes(row: dict[str, Any]) -> int:
    return _json_bytes(row)


def _largest_row(rows: list[dict[str, Any]]) -> tuple[int, dict[str, Any] | None]:
    best = 0
    best_row: dict[str, Any] | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        n = _row_json_bytes(row)
        if n > best:
            best = n
            best_row = row
    return best, best_row


def _estimate_total(avg_row_bytes: float, row_count: int, overhead_bytes: int) -> int:
    return int(overhead_bytes + avg_row_bytes * row_count)


def measure_normal_carts_payload_sizes(
    payload: dict[str, Any],
    *,
    store_slug: str = "",
) -> dict[str, Any]:
    """Return byte sizes for live vs slim normal-carts payloads."""
    body = dict(payload or {})
    slim = slim_normal_carts_payload_for_snapshot(body)

    active = [r for r in (body.get("merchant_carts_page_rows") or []) if isinstance(r, dict)]
    archived = [
        r for r in (body.get("merchant_archived_carts_page_rows") or []) if isinstance(r, dict)
    ]
    slim_active = [r for r in (slim.get("merchant_carts_page_rows") or []) if isinstance(r, dict)]
    slim_archived = [
        r for r in (slim.get("merchant_archived_carts_page_rows") or []) if isinstance(r, dict)
    ]
    all_live_rows = active + archived
    all_slim_rows = slim_active + slim_archived

    live_full_bytes = _json_bytes(body)
    slim_full_bytes = _json_bytes(slim)
    live_no_perf = dict(body)
    live_no_perf.pop("_perf", None)
    live_no_perf.pop("debug_perf", None)
    live_stripped_perf_bytes = _json_bytes(live_no_perf)

    live_largest, live_largest_row = _largest_row(all_live_rows)
    slim_largest, slim_largest_row = _largest_row(all_slim_rows)

    slim_row_sizes = [_row_json_bytes(slim_normal_carts_row_for_snapshot(r)) for r in all_live_rows]
    avg_slim_row = statistics.mean(slim_row_sizes) if slim_row_sizes else 0.0
    median_slim_row = statistics.median(slim_row_sizes) if slim_row_sizes else 0.0

    top_level_overhead = slim_full_bytes - sum(
        _row_json_bytes(r) for r in slim_active + slim_archived
    )

    cap = snapshot_payload_json_cap(SNAPSHOT_TYPE_NORMAL_CARTS)
    slim_encoded = encode_snapshot_payload_json(slim, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS)
    slim_encoded_bytes = len(slim_encoded.encode("utf-8"))

    report: dict[str, Any] = {
        "store_slug": store_slug or None,
        "row_counts": {
            "active": len(active),
            "archived": len(archived),
            "total": len(all_live_rows),
        },
        "payload_bytes": {
            "live_full_including_perf": live_full_bytes,
            "live_without_perf_debug": live_stripped_perf_bytes,
            "slim_snapshot": slim_full_bytes,
            "slim_snapshot_encoded": slim_encoded_bytes,
            "reduction_pct": round(
                100.0 * (1 - slim_full_bytes / live_stripped_perf_bytes), 2
            )
            if live_stripped_perf_bytes
            else 0.0,
            "old_cap_bytes": 65_000,
            "current_cap_bytes": cap,
            "live_exceeds_old_cap": live_stripped_perf_bytes > 65_000,
            "slim_exceeds_old_cap": slim_full_bytes > 65_000,
            "slim_exceeds_current_cap": slim_full_bytes > cap,
            "slim_encoded_exceeds_current_cap": slim_encoded_bytes > cap,
        },
        "largest_row_bytes": {
            "live": live_largest,
            "slim": slim_largest,
            "live_recovery_key": (live_largest_row or {}).get("recovery_key"),
            "slim_recovery_key": (slim_largest_row or {}).get("recovery_key"),
        },
        "slim_row_stats": {
            "avg_bytes": round(avg_slim_row, 1),
            "median_bytes": round(median_slim_row, 1),
            "min_bytes": min(slim_row_sizes) if slim_row_sizes else 0,
            "max_bytes": max(slim_row_sizes) if slim_row_sizes else 0,
            "top_level_overhead_bytes": top_level_overhead,
        },
        "estimates_slim_bytes": {
            "rows_100": _estimate_total(avg_slim_row, 100, top_level_overhead),
            "rows_250": _estimate_total(avg_slim_row, 250, top_level_overhead),
            "rows_500": _estimate_total(avg_slim_row, 500, top_level_overhead),
        },
        "largest_live_row_heavy_keys": [],
    }

    if live_largest_row:
        heavy = []
        for key, val in live_largest_row.items():
            try:
                kb = _json_bytes({key: val})
            except Exception:  # noqa: BLE001
                continue
            if kb >= 200:
                heavy.append({"key": key, "bytes": kb})
        heavy.sort(key=lambda x: int(x["bytes"]), reverse=True)
        report["largest_live_row_heavy_keys"] = heavy[:12]

    return report


__all__ = ["measure_normal_carts_payload_sizes"]
