# -*- coding: utf-8 -*-
"""Home Dashboard Closure v2 — production screenshot + summary gate."""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_home_dashboard_closure_v2_out"
TARGET_BUILD = "ui-setup-v8c-home-closure-v2"


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _auth(page) -> dict:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000)
        page.wait_for_timeout(1500)
        page.locator('input[name="email"], input[type="email"]').first.fill(email)
        page.locator('input[name="password"], input[type="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        return {"mode": "env_login", "email": email}
    uid = uuid.uuid4().hex[:10]
    email = f"cf.home.closure.{uid}@smartreplyai.net"
    password = f"CfClose!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"HomeClose {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    return {"mode": "signup", "email": email}


def _wait_summary_ok(page) -> dict:
    return page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          let body = null;
          try { body = await r.json(); } catch (e) { body = {parse_error: String(e)}; }
          if (body && body.ok && typeof window.maApplyDashboardSummary === 'function') {
            window.maApplyDashboardSummary(body);
          }
          return {status: r.status, ok: !!(body && body.ok), body};
        }"""
    )


def _shot(page, nav_target: str, filename: str) -> None:
    page.evaluate(
        """(target) => {
          if (window.maHomeNav) window.maHomeNav(target);
        }""",
        nav_target,
    )
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / filename), full_page=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "base": BASE,
        "git_head": _git_short(),
        "target_build": TARGET_BUILD,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {},
        "screenshots": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1366, "height": 900})
        mobile = browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        report["auth"] = _auth(desktop)
        _auth(mobile)
        for page in (desktop, mobile):
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            page.wait_for_timeout(2500)
        summary = _wait_summary_ok(desktop)
        report["summary"] = {
            "status": summary.get("status"),
            "ok": summary.get("ok"),
            "kpi_abandoned": (summary.get("body") or {}).get("merchant_kpi_abandoned_fmt"),
            "month_abandoned": (summary.get("body") or {}).get("merchant_month_abandoned_fmt"),
        }
        _shot(desktop, "overview", "01_overview_desktop.png")
        _shot(desktop, "setup", "02_store_setup_desktop.png")
        _shot(desktop, "month", "03_monthly_summary_desktop.png")
        _shot(mobile, "overview", "04_overview_mobile.png")
        _shot(mobile, "month", "05_monthly_summary_mobile.png")
        report["screenshots"] = [
            {"nav": "overview", "viewport": "desktop", "file": "01_overview_desktop.png"},
            {"nav": "setup", "viewport": "desktop", "file": "02_store_setup_desktop.png"},
            {"nav": "month", "viewport": "desktop", "file": "03_monthly_summary_desktop.png"},
            {"nav": "overview", "viewport": "mobile", "file": "04_overview_mobile.png"},
            {"nav": "month", "viewport": "mobile", "file": "05_monthly_summary_mobile.png"},
        ]
        browser.close()
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["summary"].get("status") != 200 or not report["summary"].get("ok"):
        raise SystemExit("summary gate failed")


if __name__ == "__main__":
    main()
