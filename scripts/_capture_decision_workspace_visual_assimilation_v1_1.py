# -*- coding: utf-8 -*-
"""Capture Decision Workspace Visual Assimilation V1.1 proof."""
from __future__ import annotations

import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "decision_workspace_visual_assimilation_v1_1"
BASE = "http://127.0.0.1:8765"
BEFORE_SRC = (
    ROOT
    / "docs"
    / "product"
    / "decision_workspace_visual_assimilation_v1"
    / "after_desktop_viewport.png"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if BEFORE_SRC.exists():
        shutil.copyfile(BEFORE_SRC, OUT / "before_desktop_viewport.png")

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
        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(1800)
        probe = page.evaluate(
            """async () => {
              await fetch('/api/cart-workspace/v1/demo-seed', {
                method: 'POST', credentials: 'same-origin'
              });
              if (window.goTo) goTo('workspace');
              await new Promise((r) => setTimeout(r, 2200));
              const host = document.getElementById('cw-merchant-host');
              const text = (host && host.innerText) || '';
              return {
                text: text.slice(0, 900),
                hasStack: !!(host && host.querySelector('.cw-card__stack')),
                hasUnderstanding: !!(host && host.querySelector('.cw-beat--understanding')),
                hasActionBeat: !!(host && host.querySelector('.cw-beat--action')),
                hasBusinessException: /Business exception/i.test(text),
                hasLatinLeak: /\\b[A-Za-z]{4,}\\b/.test(text.replace(/CartFlow/g, '')),
              };
            }"""
        )
        print("probe", probe)
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(300)

        page.screenshot(path=str(OUT / "after_desktop_full.png"), full_page=True)
        page.screenshot(path=str(OUT / "after_desktop_viewport.png"), full_page=False)

        primary = page.locator(".cw-card--primary").first
        if primary.count():
            primary.screenshot(path=str(OUT / "after_decision_focal_closeup.png"))
        evid = page.locator(".cw-beat--evidence, .cw-beat--understanding").first
        if evid.count():
            # Capture evidence+understanding together via stack top
            stack_eu = page.locator(
                ".cw-card--primary .cw-beat--evidence, .cw-card--primary .cw-beat--understanding"
            )
            if stack_eu.count() >= 2:
                box1 = page.locator(".cw-card--primary .cw-beat--evidence").bounding_box()
                box2 = page.locator(
                    ".cw-card--primary .cw-beat--understanding"
                ).bounding_box()
                if box1 and box2:
                    x = min(box1["x"], box2["x"])
                    y = min(box1["y"], box2["y"])
                    x2 = max(box1["x"] + box1["width"], box2["x"] + box2["width"])
                    y2 = max(box1["y"] + box1["height"], box2["y"] + box2["height"])
                    page.screenshot(
                        path=str(OUT / "after_evidence_understanding_closeup.png"),
                        clip={
                            "x": max(0, x - 4),
                            "y": max(0, y - 4),
                            "width": x2 - x + 8,
                            "height": y2 - y + 8,
                        },
                    )
            else:
                evid.screenshot(path=str(OUT / "after_evidence_understanding_closeup.png"))

        action = page.locator(".cw-beat--action").first
        if action.count():
            action.screenshot(path=str(OUT / "after_action_hierarchy_closeup.png"))

        # Before/after comparison
        from PIL import Image, ImageDraw

        before = Image.open(OUT / "before_desktop_viewport.png").convert("RGB")
        after = Image.open(OUT / "after_desktop_viewport.png").convert("RGB")
        h = max(before.height, after.height)
        canvas = Image.new("RGB", (before.width + after.width + 48, h + 48), (244, 247, 250))
        canvas.paste(before, (16, 40))
        canvas.paste(after, (before.width + 32, 40))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), "BEFORE (V1)", fill=(8, 32, 72))
        draw.text((before.width + 32, 12), "AFTER (V1.1)", fill=(8, 32, 72))
        canvas.save(OUT / "before_after_comparison.png")

        if probe.get("hasBusinessException"):
            raise SystemExit("FAIL_ENGLISH_LEAK_Business_exception")
        if not probe.get("hasStack") or not probe.get("hasUnderstanding"):
            raise SystemExit("FAIL_HIERARCHY_STRUCTURE")
        print("OK", OUT)
        ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
