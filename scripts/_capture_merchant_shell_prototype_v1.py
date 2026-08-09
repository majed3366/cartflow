# -*- coding: utf-8 -*-
"""Capture Merchant Shell Prototype V1 viewports (local file — no deploy)."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "docs" / "product" / "merchant_shell_prototype_v1" / "prototype" / "index.html"
SHOTS = ROOT / "docs" / "product" / "merchant_shell_prototype_v1" / "screenshots"
URL = PROTO.resolve().as_uri()


def shot(page, name: str) -> None:
    page.screenshot(path=str(SHOTS / name), full_page=False)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Desktop 1440 home
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = ctx.new_page()
        page.goto(URL + "#home", wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        shot(page, "01_desktop_1440_home.png")

        page.evaluate("() => window.MerchantShellPrototypeV1.go('workspace')")
        page.wait_for_timeout(300)
        shot(page, "02_desktop_1440_workspace.png")
        ctx.close()

        # Tablet 1024
        ctx = browser.new_context(viewport={"width": 1024, "height": 768}, locale="ar-SA")
        page = ctx.new_page()
        page.goto(URL + "#home", wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        shot(page, "03_tablet_1024.png")
        ctx.close()

        # Mobile 430 home closed
        ctx = browser.new_context(
            viewport={"width": 430, "height": 932},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        page = ctx.new_page()
        page.goto(URL + "#home", wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        shot(page, "04_mobile_430_home_closed.png")

        page.click("#ctx-handle")
        page.wait_for_timeout(350)
        shot(page, "05_mobile_430_home_sidebar_open.png")

        page.evaluate("() => window.MerchantShellPrototypeV1.closeCtx()")
        page.wait_for_timeout(200)
        page.evaluate("() => window.MerchantShellPrototypeV1.go('workspace')")
        page.wait_for_timeout(300)
        shot(page, "06_mobile_430_workspace.png")
        ctx.close()

        # Mobile 390 home closed + scrolled global upbar
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        page = ctx.new_page()
        page.goto(URL + "#home", wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        shot(page, "07_mobile_390_home_closed.png")

        page.evaluate(
            """() => {
              const list = document.querySelector('#global-list');
              if (list) list.scrollLeft = list.scrollWidth;
            }"""
        )
        page.wait_for_timeout(250)
        shot(page, "08_mobile_390_global_upbar_scrolled.png")
        ctx.close()

        browser.close()
    print("Wrote 8 screenshots to", SHOTS)


if __name__ == "__main__":
    main()
