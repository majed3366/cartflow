# -*- coding: utf-8 -*-
"""Capture Decision Workspace Visual Assimilation V1 before/after proof."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "decision_workspace_visual_assimilation_v1"
BASE = "http://127.0.0.1:8765"
REF_BEFORE = (
    ROOT / "docs" / "product" / "decision_workspace_v2" / "prod_desktop_workspace.png"
)


def _bind_and_open(browser, prefix: str) -> None:
    boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
    boot.goto(f"{BASE}/login", timeout=120000)
    session = boot.evaluate(
        """async () => {
          const r = await fetch('/dev/living-store-home-review-session', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store'
          });
          return { http: r.status, body: await r.json().catch(() => ({})) };
        }"""
    )
    body = session.get("body") or {}
    boot.close()
    if not (body.get("cookie_name") and body.get("cookie_value")):
        raise SystemExit(f"FAIL_NO_SESSION: {session}")

    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
    ctx.add_cookies(
        [
            {
                "name": body["cookie_name"],
                "value": body["cookie_value"],
                "url": BASE,
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )
    page = ctx.new_page()
    page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
    page.wait_for_timeout(2000)
    page.evaluate(
        """async () => {
          await fetch('/api/cart-workspace/v1/demo-seed', {
            method: 'POST', credentials: 'same-origin'
          });
          if (window.goTo) goTo('workspace');
          await new Promise((r) => setTimeout(r, 2000));
        }"""
    )
    page.wait_for_timeout(1200)
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(300)

    page.screenshot(path=str(OUT / f"{prefix}_desktop_full.png"), full_page=True)
    page.screenshot(path=str(OUT / f"{prefix}_desktop_viewport.png"), full_page=False)

    primary = page.locator(".cw-card--primary").first
    if primary.count():
        primary.screenshot(path=str(OUT / f"{prefix}_decision_closeup.png"))
    evidence = page.locator(".cw-card__evidence").first
    if evidence.count():
        evidence.screenshot(path=str(OUT / f"{prefix}_evidence_closeup.png"))
    else:
        # Knowledge/evidence densification area fallback: primary card body
        if primary.count():
            primary.screenshot(path=str(OUT / f"{prefix}_evidence_knowledge_closeup.png"))

    # Header + sidebar strip
    page.screenshot(
        path=str(OUT / f"{prefix}_header_sidebar_closeup.png"),
        clip={"x": 0, "y": 0, "width": 1440, "height": 220},
    )

    host_text = page.evaluate(
        "() => ((document.getElementById('cw-merchant-host') || {}).innerText || '').slice(0, 200)"
    )
    print(prefix, "host_sample=", host_text)
    ctx.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after", "both"), default="both")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    if REF_BEFORE.exists() and args.phase in ("before", "both"):
        shutil.copyfile(REF_BEFORE, OUT / "before_reference_prod_green_chrome.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        if args.phase in ("before", "both"):
            _bind_and_open(browser, "before")
        if args.phase in ("after", "both"):
            _bind_and_open(browser, "after")
        browser.close()
    print("OK", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
