# -*- coding: utf-8 -*-
"""Capture all four merchant home sub-pages on production after final cleanup."""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_home_dashboard_final_cleanup_out"


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
    email = f"cf.home.final.{uid}@smartreplyai.net"
    password = f"CfHome!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"HomeFinal {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    return {"mode": "signup", "email": email}


def _ensure_readiness_panel(page) -> None:
    page.wait_for_function(
        """async () => {
          try {
            if (typeof window.maBootSetupReadinessHydration === 'function') {
              window.maBootSetupReadinessHydration();
            }
            const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
              credentials: 'same-origin', cache: 'no-store'
            });
            const d = await r.json();
            if (d && d.ok && typeof window.maApplyDashboardSummary === 'function') {
              window.maApplyDashboardSummary(d);
            }
            return !!document.querySelector('#ma-setup-readiness-root .ma-readiness-panel');
          } catch (e) { return false; }
        }""",
        timeout=120000,
    )
    page.wait_for_timeout(800)


def _shot(page, nav_target: str, filename: str) -> None:
    page.evaluate(
        """(target) => {
          if (window.maHomeNav) window.maHomeNav(target);
        }""",
        nav_target,
    )
    page.wait_for_timeout(2500)
    page.screenshot(path=str(OUT / filename), full_page=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "base": BASE,
        "git_head": _git_short(),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "screenshots": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        report["auth"] = _auth(page)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(3000)
        _ensure_readiness_panel(page)
        sections = [
            ("overview", "01_overview.png"),
            ("setup", "02_store_setup.png"),
            ("month", "03_monthly_summary.png"),
            ("test-tools", "04_test_tools.png"),
        ]
        for nav, fname in sections:
            _shot(page, nav, fname)
            report["screenshots"].append({"nav": nav, "file": fname})
        ctx.close()
        browser.close()
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
