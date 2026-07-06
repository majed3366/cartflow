# -*- coding: utf-8 -*-
"""Capture Product Excellence Implementation V1 on local/production /dashboard."""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_product_excellence_implementation_v1_out"
BASE = os.environ.get("CARTFLOW_DASHBOARD_BASE", "http://127.0.0.1:8000")


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, cwd=ROOT
        ).strip()
    except Exception:
        return "unknown"


def _auth(page: Page) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator('input[name="email"]').fill(email, timeout=60000)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(3500)
        return
    uid = uuid.uuid4().hex[:8]
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"PE V2 {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"pe.v2.{uid}@example.com")
    page.locator('input[name="password"]').first.fill(f"PeV2Impl!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"PeV2Impl!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(4000)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shots = [
        ("01_home_mobile.png", f"{BASE}/dashboard#home", {"width": 390, "height": 844}, ".v2-hero"),
        ("02_home_desktop.png", f"{BASE}/dashboard#home", {"width": 1200, "height": 800}, ".v2-hero"),
        ("03_carts_mobile.png", f"{BASE}/dashboard#carts", {"width": 390, "height": 844}, "#ma-carts-queue-v2"),
        ("04_carts_desktop.png", f"{BASE}/dashboard#carts", {"width": 1200, "height": 800}, "#ma-carts-panel-v2"),
        ("05_cart_detail_mobile.png", f"{BASE}/dashboard#carts", {"width": 390, "height": 844}, ".v2-flow-step"),
        ("06_cart_detail_desktop.png", f"{BASE}/dashboard#carts", {"width": 1200, "height": 800}, ".v2-flow-step"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(locale="ar-SA")
        page = ctx.new_page()
        _auth(page)
        for name, url, vp, sel in shots:
            page.set_viewport_size(vp)
            page.goto(url, wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(3000)
            try:
                page.wait_for_selector(sel, timeout=20000)
            except Exception:
                pass
            page.screenshot(path=str(OUT / name), full_page=True)
        browser.close()

    (OUT / "capture_meta.json").write_text(
        json.dumps({"git": _git_short(), "base": BASE, "version": "implementation-v1"}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved to {OUT}")


if __name__ == "__main__":
    main()
