# -*- coding: utf-8 -*-
"""
Read-only scheduler ownership deploy verification.

Usage:
  python scripts/scheduler_ownership_verify.py --scheduler http://127.0.0.1:8011 --api http://127.0.0.1:8012
  python scripts/scheduler_ownership_verify.py --check scheduler:http://host1 --check api:http://host2
  python scripts/scheduler_ownership_verify.py --scheduler http://127.0.0.1:8011 --json

Exit code 0 = pass, 1 = fail.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.scheduler_ownership_verify_v1 import run_deploy_verification  # noqa: E402


def _parse_checks(args: argparse.Namespace) -> list[tuple[str, str]]:
    checks: list[tuple[str, str]] = []
    if args.scheduler:
        checks.append(("scheduler", args.scheduler))
    for url in args.api or []:
        checks.append(("api", url))
    for raw in args.check or []:
        if ":" not in raw:
            raise SystemExit(f"invalid --check value {raw!r}; use role:url")
        role, url = raw.split(":", 1)
        checks.append((role.strip().lower(), url.strip()))
    if not checks:
        raise SystemExit("provide --scheduler/--api or --check role:url")
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify scheduler ownership deployment.")
    parser.add_argument("--scheduler", help="Scheduler service base URL")
    parser.add_argument("--api", action="append", help="API replica base URL (repeatable)")
    parser.add_argument(
        "--check",
        action="append",
        help="Explicit role:url pair (repeatable), e.g. scheduler:https://host",
    )
    parser.add_argument("--json", action="store_true", help="JSON report to stdout")
    args = parser.parse_args(argv)
    checks = _parse_checks(args)
    report = run_deploy_verification(checks)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Scheduler Ownership Deploy Verification")
        print("=" * 40)
        for entry in report.get("checks") or []:
            status = "PASS" if entry.get("passed") else "FAIL"
            print(f"[{status}] {entry.get('expected_role')} {entry.get('url')}")
            print(
                f"  role={entry.get('role')} compliance={entry.get('compliance')} "
                f"ok={entry.get('health_ok')}"
            )
            if entry.get("diagnosis_codes"):
                print(
                    f"  diagnosis={entry.get('diagnosis_codes')} "
                    f"severity={entry.get('diagnosis_severity')}"
                )
            for err in entry.get("errors") or []:
                print(f"  ERROR: {err}")
            for warn in entry.get("warnings") or []:
                print(f"  WARN: {warn}")
        print("=" * 40)
        print(f"Overall: {'PASS' if report.get('passed') else 'FAIL'}")

    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
