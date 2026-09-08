# -*- coding: utf-8 -*-
"""Capture 6 LIVE mobile screenshots from smartreplyai.net/dashboard."""
from __future__ import annotations

import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "live"
DESKTOP = Path(
    r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Founder_UX_Closure_V1_3"
)
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"
BASE = "https://smartreplyai.net"

SHOTS = [
    "01_home_evidence_ratio_mobile.png",
    "02_workspace_why_distinct_mobile.png",
    "03_workspace_accept_execute_sequence_mobile.png",
    "04_sidebar_ready_action_chosen_mobile.png",
    "05_sidebar_measuring_recheck_mobile.png",
    "06_home_workspace_final_consistency_mobile.png",
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="ar-SA",
        )
        page = context.new_page()
        page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
        page.fill('input[name="email"]', LAB_EMAIL)
        page.fill('input[name="password"]', LAB_PASSWORD)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_url("**/dashboard**", timeout=60000)
        page.wait_for_timeout(2500)

        def snap(name: str) -> None:
            dest = OUT / name
            page.screenshot(path=str(dest), full_page=False)
            shutil.copy2(dest, DESKTOP / name)
            print("wrote", dest)

        page.goto(BASE + "/dashboard#home", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("[data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        snap(SHOTS[0])

        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(1000)
        snap(SHOTS[1])
        page.locator("[data-cf2-ldh-journey='1']").first.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        snap(SHOTS[2])

        handle = page.locator("#cf2-ctx-handle")
        if handle.count():
            handle.first.click()
            page.wait_for_timeout(600)
        snap(SHOTS[3])
        if page.locator("#cf2-ctx-close").count():
            page.locator("#cf2-ctx-close").first.click()
            page.wait_for_timeout(300)

        page.goto(BASE + "/dashboard#home", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("[data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(600)
        snap(SHOTS[4])
        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        snap(SHOTS[5])
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
