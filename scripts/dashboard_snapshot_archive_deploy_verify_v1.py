# -*- coding: utf-8 -*-
"""
Production deploy verification — Dashboard Snapshot Archive v1.

Read-only by default. Pass --run-tick to execute one bounded archive tick
(only succeeds when archive env is enabled on the probed service).

Usage:
  python scripts/dashboard_snapshot_archive_deploy_verify_v1.py
  python scripts/dashboard_snapshot_archive_deploy_verify_v1.py --run-tick
  python scripts/dashboard_snapshot_archive_deploy_verify_v1.py --base https://smartreplyai.net
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "_dashboard_snapshot_archive_deploy_verify_v1_out"
OUT_FILE = OUT_DIR / "verify_report.json"
DEFAULT_BASE = "https://smartreplyai.net"


def _get_json(url: str, *, timeout: float = 120.0) -> tuple[int | None, dict | str]:
    req = urllib.request.Request(url, headers={"User-Agent": "cartflow-archive-verify/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            body = exc.read(500).decode("utf-8", "replace")
        return exc.code, body
    except OSError as exc:
        return None, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument(
        "--run-tick",
        action="store_true",
        help="Request run_tick=1 (scheduler only; archive env must be enabled there)",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")
    now = datetime.now(timezone.utc).isoformat()

    report: dict = {
        "verified_at": now,
        "probe_base": base,
        "run_tick_requested": bool(args.run_tick),
        "checks": {},
        "errors": [],
    }

    # Baseline growth measurement
    status_growth, growth = _get_json(f"{base}/dev/data-growth-measurement")
    report["data_growth_http"] = status_growth
    if isinstance(growth, dict) and growth.get("ok"):
        acc = growth.get("dashboard_snapshot_accumulation") or {}
        report["baseline_hot_rows"] = acc.get("total_rows")
        report["baseline_historical_only"] = acc.get("historical_only_rows")
        report["baseline_latest_pairs"] = acc.get("latest_row_per_store_type_count")
        report["checks"]["growth_endpoint_ok"] = True
    else:
        report["checks"]["growth_endpoint_ok"] = False
        report["errors"].append(f"data-growth-measurement failed: {growth!r}")

    # Archive diagnostics (dry unless --run-tick)
    q = urllib.parse.urlencode({"run_tick": "1" if args.run_tick else "0"})
    status_arch, archive = _get_json(f"{base}/dev/dashboard-snapshot-archive?{q}")
    report["archive_http"] = status_arch
    report["archive_body"] = archive if isinstance(archive, dict) else {"raw": str(archive)[:500]}

    if status_arch == 404:
        report["checks"]["archive_endpoint_deployed"] = False
        report["errors"].append("archive endpoint 404 — deploy code + migration first")
    elif isinstance(archive, dict) and archive.get("ok"):
        report["checks"]["archive_endpoint_deployed"] = True
        report["checks"]["archive_table_readable"] = True
        report["total_snapshot_rows_hot"] = archive.get("total_snapshot_rows_hot")
        report["total_snapshot_rows_archive"] = archive.get("total_snapshot_rows_archive")
        report["latest_rows_kept"] = archive.get("latest_rows_kept")
        report["rows_eligible_for_archive"] = archive.get("rows_eligible_for_archive")
        report["archive_enabled_on_probe"] = archive.get("archive_enabled")
        report["remaining_risk"] = archive.get("remaining_risk")
        if args.run_tick:
            tick = archive.get("tick_result") or {}
            report["tick_result"] = tick
            report["rows_archived_this_tick"] = tick.get("rows_archived_this_tick")
            report["tick_elapsed_ms"] = tick.get("tick_elapsed_ms")
            report["checks"]["tick_ok"] = tick.get("ok") is True or tick.get("skipped")
    else:
        report["checks"]["archive_endpoint_deployed"] = status_arch == 200
        report["errors"].append(f"archive endpoint error: {archive!r}")

    # API role must not run archive loop
    status_health, health = _get_json(f"{base}/health/scheduler")
    report["health_http"] = status_health
    if isinstance(health, dict):
        report["api_role"] = health.get("role")
        report["checks"]["api_role_is_api"] = health.get("role") == "api"
        if health.get("role") != "api":
            report["errors"].append(f"expected api role on public URL, got {health.get('role')}")

    # Dashboard smoke — summary endpoint should respond (may need auth; 401/403 ok)
    status_summary, summary = _get_json(f"{base}/api/dashboard/summary")
    report["summary_http"] = status_summary
    report["checks"]["dashboard_summary_reachable"] = status_summary in (200, 401, 403, 302)

    report["checks"]["all_pass"] = all(
        v
        for k, v in report["checks"].items()
        if k != "all_pass" and k != "tick_ok"
    ) and not report["errors"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT_FILE}")
    return 0 if report["checks"].get("all_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
