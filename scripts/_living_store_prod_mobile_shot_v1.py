# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "observation_admission_bridge_v1"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE}/login", timeout=120000)
        session = page.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin'
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
        mob = browser.new_context(
            viewport={"width": 390, "height": 844}, locale="ar-SA"
        )
        mob.add_cookies([cookie])
        m = mob.new_page()
        m.goto(f"{BASE}/dashboard#home", timeout=120000)
        sample = ""
        for _ in range(30):
            m.wait_for_timeout(2000)
            sample = m.evaluate(
                """() => {
                  const el = document.getElementById('ma-home-experience-root');
                  return (el && el.innerText) || '';
                }"""
            )
            if "Raven" in sample or "ملاحظات المنتجات" in sample:
                break
        m.screenshot(path=str(OUT / "prod_after_mobile_home.png"), full_page=False)
        (OUT / "prod_mobile_text_sample.json").write_text(
            json.dumps(
                {"has_raven": "Raven" in sample, "text_sample": sample[:700]},
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        mob.close()
        browser.close()
    print("mobile_ok", "Raven" in sample)
    return 0 if "Raven" in sample else 2


if __name__ == "__main__":
    raise SystemExit(main())
