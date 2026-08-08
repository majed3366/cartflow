# -*- coding: utf-8 -*-
"""Capture Platform Shell Visual Assimilation V1 proof across six merchant surfaces."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "platform_shell_visual_assimilation_v1"
BASE = "http://127.0.0.1:8765"
BEFORE_REF = (
    ROOT
    / "docs"
    / "product"
    / "decision_workspace_v2"
    / "prod_desktop_workspace.png"
)

PAGES = (
    ("home", "home"),
    ("workspace", "workspace"),
    ("products", "products"),
    ("carts", "carts"),
    ("comms", "comms"),
    ("settings", "settings"),
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if BEFORE_REF.exists():
        shutil.copyfile(BEFORE_REF, OUT / "before_shell_reference_green_chrome.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return await r.json().catch(() => ({}));
            }"""
        )
        boot.close()
        if not (session.get("cookie_name") and session.get("cookie_value")):
            raise SystemExit(f"FAIL_NO_SESSION: {session}")

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies(
            [
                {
                    "name": session["cookie_name"],
                    "value": session["cookie_value"],
                    "url": BASE,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(2000)

        # Seed workspace so that surface isn't empty when we visit it
        page.evaluate(
            """async () => {
              try {
                await fetch('/api/cart-workspace/v1/demo-seed', {
                  method: 'POST', credentials: 'same-origin'
                });
              } catch (e) {}
            }"""
        )

        shell_probe = page.evaluate(
            """() => {
              const mark = document.querySelector('.ma-gtb-logo__mark');
              const css = [...document.styleSheets]
                .map(s => s.href || '')
                .some(h => h.includes('platform_shell_visual_assimilation'));
              const top = getComputedStyle(document.querySelector('.ma-global-topbar'));
              const side = getComputedStyle(document.querySelector('.ma-context-sidebar'));
              return {
                css,
                markDisplay: mark && getComputedStyle(mark).display,
                markSrc: mark && mark.getAttribute('src'),
                topBg: top && top.backgroundImage,
                sideBg: side && side.backgroundImage,
                greenVar: getComputedStyle(document.body).getPropertyValue('--green').trim(),
              };
            }"""
        )
        print("shell_probe", shell_probe)
        if not shell_probe.get("css"):
            raise SystemExit("FAIL_SHELL_CSS_MISSING")
        if shell_probe.get("markDisplay") == "none":
            raise SystemExit("FAIL_MARK_HIDDEN")

        # Shared chrome close-ups from home
        page.screenshot(
            path=str(OUT / "shared_topbar_closeup.png"),
            clip={"x": 0, "y": 0, "width": 1440, "height": 72},
        )
        page.screenshot(
            path=str(OUT / "shared_sidebar_closeup.png"),
            clip={"x": 1440 - 260, "y": 56, "width": 260, "height": 420},
        )

        # Buttons sample: clip utilities + any primary on home if present
        page.screenshot(
            path=str(OUT / "shared_buttons_states_sample.png"),
            clip={"x": 900, "y": 0, "width": 540, "height": 72},
        )

        for section, name in PAGES:
            page.locator(f'button.ma-gtb-section[data-ma-section="{section}"]').click()
            page.wait_for_timeout(2400)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(250)
            page.screenshot(
                path=str(OUT / f"after_{name}_desktop.png"), full_page=False
            )
            print(
                "captured",
                name,
                page.evaluate("() => document.body.getAttribute('data-ma-page')"),
                page.evaluate("() => location.hash"),
            )

        # Before/After shell: historical green vs current home
        before = Image.open(OUT / "before_shell_reference_green_chrome.png").convert("RGB")
        after = Image.open(OUT / "after_home_desktop.png").convert("RGB")
        # normalize heights for comparison strip of topbars
        bh = min(220, before.height, after.height)
        before_c = before.crop((0, 0, before.width, bh)).resize((720, bh))
        after_c = after.crop((0, 0, after.width, bh)).resize((720, bh))
        canvas = Image.new("RGB", (720 * 2 + 48, bh + 48), (244, 247, 250))
        canvas.paste(before_c, (16, 40))
        canvas.paste(after_c, (736, 40))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "BEFORE (legacy green chrome)", fill=(8, 32, 72))
        draw.text((736, 12), "AFTER (platform shell V1)", fill=(8, 32, 72))
        canvas.save(OUT / "before_after_shell_comparison.png")

        print("OK", OUT)
        ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
