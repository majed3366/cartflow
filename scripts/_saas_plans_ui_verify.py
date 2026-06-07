# -*- coding: utf-8 -*-
"""Visual verification — merchant plans UI (read-only)."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_VERIFY_BASE", "http://127.0.0.1:8011")
OUT = Path(__file__).resolve().parent / "_saas_plans_ui_out"
OUT.mkdir(parents=True, exist_ok=True)


def _signup(page) -> None:
    email = f"plans-ui-{uuid.uuid4().hex[:10]}@example.com"
    password = "password123"
    page.goto(f"{BASE}/signup", wait_until="domcontentloaded", timeout=120000)
    page.fill('input[name="store_name"]', "متجر اختبار الباقات")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.fill('input[name="confirm_password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard**", timeout=120000)


def main() -> None:
    report = {"base": BASE, "screenshots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        _signup(page)

        page.goto(f"{BASE}/dashboard#settings", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(1500)
        shot_settings = OUT / "01_current_plan_settings_desktop.png"
        page.screenshot(path=str(shot_settings), full_page=True)
        report["screenshots"].append(str(shot_settings.name))

        page.goto(f"{BASE}/dashboard#plans", wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(1500)
        shot_plans = OUT / "02_plans_comparison_desktop.png"
        page.screenshot(path=str(shot_plans), full_page=True)
        report["screenshots"].append(str(shot_plans.name))

        ctx_m = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True
        )
        page_m = ctx_m.new_page()
        page_m.context.add_cookies(page.context.cookies())
        page_m.goto(f"{BASE}/dashboard#plans", wait_until="domcontentloaded", timeout=120000)
        page_m.wait_for_timeout(1500)
        shot_mobile = OUT / "03_plans_comparison_mobile.png"
        page_m.screenshot(path=str(shot_mobile), full_page=True)
        report["screenshots"].append(str(shot_mobile.name))

        ctx.close()
        ctx_m.close()
        browser.close()

    import json

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
