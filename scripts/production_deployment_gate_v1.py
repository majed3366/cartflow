# -*- coding: utf-8 -*-
"""
Production deployment gate v1 — block deploy when scheduler or dashboard regress.

Usage:
  python scripts/production_deployment_gate_v1.py
  python scripts/production_deployment_gate_v1.py --base https://smartreplyai.net
  python scripts/production_deployment_gate_v1.py --json

Exit code 0 = pass, 1 = fail.

Requires merchant session cookies for dashboard API checks unless
CARTFLOW_PROD_EMAIL and CARTFLOW_PROD_PASSWORD are set (signup fallback).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.production_deployment_gate_v1 import run_production_deployment_gate  # noqa: E402


def _auth_cookies(base: str, *, timeout: float) -> list[dict]:
    from playwright.sync_api import sync_playwright

    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        if email and password:
            page.goto(f"{base}/login", timeout=int(timeout * 1000), wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            page.locator('input[name="email"]').fill(email, timeout=60000)
            page.locator('input[name="password"]').first.fill(password)
            page.get_by_role("button", name="دخول").click()
            page.wait_for_timeout(4000)
        else:
            uid = uuid.uuid4().hex[:10]
            email = f"cf.deploy.gate.{uid}@smartreplyai.net"
            password = f"CfDeploy!{uid[:8]}"
            page.goto(f"{base}/signup", timeout=int(timeout * 1000), wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            page.locator('input[name="store_name"]').fill(f"DeployGate {uid[:6]}")
            page.locator('input[name="email"]').fill(email)
            page.locator('input[name="password"]').first.fill(password)
            page.locator('input[name="confirm_password"]').fill(password)
            page.locator('button[type="submit"]').click()
            page.wait_for_timeout(5000)
        cookies = page.context.cookies()
        browser.close()
    return cookies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production deployment gate v1")
    parser.add_argument("--base", default="https://smartreplyai.net", help="Production base URL")
    parser.add_argument("--json", action="store_true", help="JSON report to stdout")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Scheduler-only gate (no merchant auth)",
    )
    args = parser.parse_args(argv)

    cookies = None
    if not args.skip_dashboard:
        cookies = _auth_cookies(args.base, timeout=args.timeout)

    report = run_production_deployment_gate(
        args.base,
        cookies=cookies,
        timeout=args.timeout,
    )

    out_dir = Path(__file__).resolve().parent / "_production_deployment_gate_v1_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gate_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Production Deployment Gate v1")
        print("=" * 40)
        for check in report.get("checks") or []:
            status = "PASS" if check.get("passed") else "FAIL"
            print(f"[{status}] {check.get('name')}")
            for err in check.get("errors") or []:
                print(f"  ERROR: {err}")
        print("=" * 40)
        print(f"Overall: {'PASS' if report.get('passed') else 'FAIL'}")
        print(f"Report: {out_path}")

    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
