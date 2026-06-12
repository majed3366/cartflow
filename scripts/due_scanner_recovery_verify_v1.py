# -*- coding: utf-8 -*-
"""
Production Due Scanner Recovery v1 — deploy verification.

Read-only checks against live scheduler ownership + recovery health:
  - scanner policy allows start/poll/claim path (role=scheduler, may_due_scan)
  - overdue backlog observable and optionally decreasing after wait
  - restart survival protections still present

Usage:
  python scripts/due_scanner_recovery_verify_v1.py --base https://smartreplyai.net
  python scripts/due_scanner_recovery_verify_v1.py --base https://smartreplyai.net --wait 90 --json

Exit 0 = pass, 1 = fail.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.scheduler_ownership_verify_v1 import (  # noqa: E402
    evaluate_scheduler_health,
    fetch_scheduler_health,
)


def _fetch_json(url: str, *, timeout: float = 20.0) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError(f"{url} returned non-object JSON")
    return data


def _recovery_health(base: str) -> dict:
    return _fetch_json(base.rstrip("/") + "/dev/recovery-health")


def run_verification(
    base_url: str,
    *,
    wait_seconds: float = 0.0,
) -> dict:
    base = base_url.rstrip("/")
    report: dict = {
        "base_url": base,
        "passed": False,
        "checks": [],
        "wait_seconds": wait_seconds,
    }

    def add_check(name: str, passed: bool, detail: dict) -> None:
        report["checks"].append({"name": name, "passed": passed, **detail})

    scheduler_health = fetch_scheduler_health(base)
    report["scheduler_health"] = scheduler_health
    ownership = evaluate_scheduler_health(scheduler_health, expected_role="scheduler")
    report["ownership_eval"] = ownership

    may_due_scan = bool(
        scheduler_health.get("due_scanner_enabled")
        or (scheduler_health.get("scheduler_ownership") or {}).get("may_due_scan")
    )
    overdue = int(scheduler_health.get("overdue_scheduled_count") or 0)

    add_check(
        "scheduler_role_and_compliance",
        ownership.get("passed") and may_due_scan,
        {
            "role": scheduler_health.get("role"),
            "compliance": ownership.get("compliance"),
            "may_due_scan": may_due_scan,
            "errors": ownership.get("errors"),
            "warnings": ownership.get("warnings"),
        },
    )

    health_a = _recovery_health(base)
    report["recovery_health_initial"] = {
        "pending_due": health_a.get("pending_due"),
        "last_claim": health_a.get("last_claim"),
        "last_execution": health_a.get("last_execution"),
        "protections": health_a.get("protections"),
    }
    protections = health_a.get("protections") if isinstance(health_a.get("protections"), dict) else {}
    scanner_loop = protections.get("db_due_scanner_loop") if isinstance(
        protections.get("db_due_scanner_loop"), dict
    ) else {}
    restart = protections.get("restart_survival") if isinstance(
        protections.get("restart_survival"), dict
    ) else {}

    add_check(
        "db_due_scanner_loop_enabled",
        str(scanner_loop.get("status") or "").lower() == "enabled",
        {"scanner_loop": scanner_loop},
    )
    add_check(
        "restart_survival_present",
        bool(restart),
        {"restart_survival": restart},
    )

    health_b = health_a
    overdue_b = overdue
    if wait_seconds > 0:
        time.sleep(wait_seconds)
        scheduler_health_b = fetch_scheduler_health(base)
        overdue_b = int(scheduler_health_b.get("overdue_scheduled_count") or 0)
        health_b = _recovery_health(base)
        report["scheduler_health_after_wait"] = scheduler_health_b
        report["recovery_health_after_wait"] = {
            "pending_due": health_b.get("pending_due"),
            "last_claim": health_b.get("last_claim"),
            "last_execution": health_b.get("last_execution"),
        }

    has_activity = bool(health_b.get("last_claim") or health_b.get("last_execution"))
    backlog_improved = overdue_b < overdue or int(health_b.get("pending_due") or 0) < int(
        health_a.get("pending_due") or 0
    )
    add_check(
        "scanner_activity_or_backlog_progress",
        has_activity or backlog_improved or overdue == 0,
        {
            "overdue_initial": overdue,
            "overdue_after_wait": overdue_b,
            "pending_due_initial": health_a.get("pending_due"),
            "pending_due_after_wait": health_b.get("pending_due"),
            "last_claim": health_b.get("last_claim"),
            "last_execution": health_b.get("last_execution"),
            "note": (
                "PASS when claim/execution heartbeats exist, backlog decreased, or no overdue rows"
            ),
        },
    )

    report["passed"] = all(c.get("passed") for c in report["checks"])
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify production due scanner recovery.")
    parser.add_argument("--base", required=True, help="Service base URL")
    parser.add_argument(
        "--wait",
        type=float,
        default=0.0,
        help="Seconds to wait before re-checking backlog/activity (e.g. 90)",
    )
    parser.add_argument("--json", action="store_true", help="JSON report to stdout")
    args = parser.parse_args(argv)

    try:
        report = run_verification(args.base, wait_seconds=max(0.0, args.wait))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        if args.json:
            print(json.dumps({"passed": False, "error": str(exc)[:300]}, indent=2))
        else:
            print(f"FAIL: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Due Scanner Recovery Verify v1")
        print("=" * 40)
        for entry in report.get("checks") or []:
            status = "PASS" if entry.get("passed") else "FAIL"
            print(f"[{status}] {entry.get('name')}")
            for key in sorted(entry.keys()):
                if key in ("name", "passed"):
                    continue
                print(f"  {key}={entry.get(key)}")
        print("=" * 40)
        print(f"Overall: {'PASS' if report.get('passed') else 'FAIL'}")

    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
