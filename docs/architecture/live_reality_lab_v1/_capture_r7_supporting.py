# -*- coding: utf-8 -*-
"""Supporting screenshots for Live Reality Lab R7 (not Founder Product PASS)."""
from __future__ import annotations

import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
EMAIL = "reality.lab@cartflow.local"
PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "architecture" / "live_reality_lab_v1" / "founder_review_r7_v1"
DESKTOP = Path(r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Live_Reality_Lab_R7")

SHOTS = [
    ("01_r7_home_mobile.png", 390, "home"),
    ("02_r7_workspace_mobile.png", 390, "workspace"),
    ("03_r7_home_desktop.png", 1280, "home"),
    ("04_r7_workspace_desktop.png", 1280, "workspace"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ar-SA",
        )
        page = context.new_page()
        page.goto(BASE + "/login", wait_until="domcontentloaded", timeout=60000)
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard**", timeout=60000)
        page.wait_for_timeout(2500)

        for name, width, surface in SHOTS:
            page.set_viewport_size({"width": width, "height": 900 if width >= 1000 else 844})
            hash_path = "#home" if surface == "home" else "#workspace"
            page.goto(BASE + "/dashboard" + hash_path, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(3500)
            # Prefer waiting for priority contract markers when present
            try:
                page.wait_for_selector("[data-cf2-priority-contract]", timeout=8000)
            except Exception:
                pass
            dest = OUT / name
            page.screenshot(path=str(dest), full_page=False)
            shutil.copy2(dest, DESKTOP / name)
            print(f"wrote {dest}")

        browser.close()

    print(f"DESKTOP={DESKTOP}")
    print(f"COUNT={len(list(OUT.glob('*.png')))}")


if __name__ == "__main__":
    main()
