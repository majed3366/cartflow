# -*- coding: utf-8 -*-
"""Retry Workspace shots in same Living Store review session (evidence only)."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "business_themes_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return await r.json();
            }"""
        )
        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="ar-SA"
        )
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(9000)
        probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const text = document.body.innerText || '';
              let body = {};
              try { body = await r.json(); } catch (e) { body = {}; }
              const p = body.projection || {};
              const cards = [].concat(p.zone_b || []).concat(p.zone_a || []);
              return {
                http: r.status,
                fail_ui: text.includes('تعذر'),
                text_sample: text.slice(0, 1600),
                gate_business_themes_v1: !!p.gate_business_themes_v1,
                zone_a: (p.zone_a || []).length,
                zone_b: (p.zone_b || []).length,
                theme_cards: cards.filter(c => c && c.gate_business_themes).length,
                fact_cards: cards.filter(c => c && c.gate_business_facts).length,
                top_titles: cards.slice(0, 8).map(c =>
                  (c && (c.merchant_decision || c.title || c.why || '')).toString().slice(0, 120)
                ),
              };
            }"""
        )
        page.screenshot(path=str(OUT / "ceo_desktop_workspace.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "ceo_mobile_workspace.png"), full_page=False)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUT / "ceo_mobile_home.png"), full_page=False)
        browser.close()

    path = OUT / "workspace_retry_probe.json"
    path.write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
