# -*- coding: utf-8 -*-
"""Capture Recovery+Packages V4 evidence (390 + 1280)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8798"
OUT = Path(
    r"C:\Users\Toshiba\AppData\Local\Temp\cf-psg-impl-v1\docs\product\merchant_recovery_packages_composition_v4\evidence"
)


def shot(page, name: str) -> None:
    try:
        page.evaluate("() => document.fonts && document.fonts.ready")
    except Exception:
        pass
    try:
        page.screenshot(path=str(OUT / name), full_page=False, timeout=90000, animations="disabled")
    except Exception as e:
        print("SHOT_FAIL", name, e)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    probes = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page()
        boot.goto(BASE + "/login", timeout=120000)
        sess = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin'
              });
              return await r.json();
            }"""
        )
        boot.close()
        cookie = {
            "name": sess["cookie_name"],
            "value": sess["cookie_value"],
            "url": BASE,
            "httpOnly": True,
            "sameSite": "Lax",
        }

        for vp, w, h in [("desktop", 1280, 900), ("mobile", 390, 844)]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(BASE + "/dashboard", timeout=180000, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)

            # Account drawer
            if vp == "desktop":
                page.click("#cf2-account-btn")
            else:
                page.click("#cf2-mobile-account")
            page.wait_for_timeout(1200)
            probes[f"{vp}_account"] = page.evaluate(
                """() => ({
                  store: (document.querySelector('#cf2-account-store-name')||{}).textContent||'',
                  plan: (document.querySelector('#cf2-account-plan')||{}).textContent||'',
                  packagesBtn: !!document.querySelector('[data-cf2-util=\"packages\"]'),
                  v1: !!document.querySelector('a[href*=\"cf_ui=v1\"]'),
                  ui: document.body.getAttribute('data-cf-ui')
                })"""
            )
            shot(page, f"{vp}_account_drawer.png")

            # Packages destination
            page.evaluate("() => { const b=document.querySelector('[data-cf2-util=\"packages\"]'); if(b) b.click(); }")
            page.wait_for_timeout(4000)
            probes[f"{vp}_packages"] = page.evaluate(
                """() => ({
                  page: !!document.querySelector('[data-cf2-page=\"packages\"]:not([hidden])'),
                  cards: document.querySelectorAll('[data-cf2-plan]').length,
                  current: !!document.querySelector('.cf2-plan-card.is-current'),
                  blocked: (document.body.innerText||'').includes('غير متاح'),
                  ui: document.body.getAttribute('data-cf-ui'),
                  v1: !!document.querySelector('a[href*=\"cf_ui=v1\"]')
                })"""
            )
            shot(page, f"{vp}_packages.png")

            # Recovery overview via Settings panel (reliable)
            page.evaluate(
                """() => {
                  if (window.CartFlowUiV2) window.CartFlowUiV2.go('settings');
                }"""
            )
            page.wait_for_timeout(2000)
            page.evaluate(
                """() => {
                  if (window.CartFlowUiV2Settings) window.CartFlowUiV2Settings.showPanel('recovery');
                  else location.hash = 'trigger-templates';
                }"""
            )
            page.wait_for_timeout(8000)
            page.wait_for_selector("[data-cf2-rec-pick]", timeout=30000)
            probes[f"{vp}_recovery"] = page.evaluate(
                """() => ({
                  ui: document.body.getAttribute('data-cf-ui'),
                  picker: document.querySelectorAll('[data-cf2-rec-pick]').length,
                  visibleCards: [...document.querySelectorAll('.ma-tpl-card')].filter(c=>!c.hidden).length,
                  theory: !!document.querySelector('.ma-tpl-ownership-banner:not([hidden])'),
                  flow: !!document.querySelector('.cf2-rec-flow'),
                  v1: !!document.querySelector('a[href*=\"cf_ui=v1\"]'),
                  ataba: (document.body.innerText||'').includes('العتبة')
                })"""
            )
            shot(page, f"{vp}_recovery_overview.png")

            # Price reason
            page.evaluate("() => { const b=document.querySelector('[data-cf2-rec-pick=\"price\"]'); if(b) b.click(); }")
            page.wait_for_timeout(800)
            probes[f"{vp}_price"] = page.evaluate(
                """() => ({
                  selected: (document.querySelector('#ma-tpl-root')||{}).getAttribute?.('data-cf2-rec-selected'),
                  visible: [...document.querySelectorAll('.ma-tpl-card')].filter(c=>!c.hidden).map(c=>c.getAttribute('data-ma-tpl-key'))
                })"""
            )
            shot(page, f"{vp}_reason_price.png")

            # Shipping
            page.evaluate("() => { const b=document.querySelector('[data-cf2-rec-pick=\"shipping\"]'); if(b) b.click(); }")
            page.wait_for_timeout(800)
            shot(page, f"{vp}_reason_shipping.png")

            # Stage counts 1/2/3 on price
            page.evaluate("() => { const b=document.querySelector('[data-cf2-rec-pick=\"price\"]'); if(b) b.click(); }")
            page.wait_for_timeout(400)
            for n in (1, 2, 3):
                page.evaluate(
                    f"""() => {{
                      const card=[...document.querySelectorAll('.ma-tpl-card')].find(c=>!c.hidden);
                      const sel=card && card.querySelector('[data-ma-tpl-msg-count]');
                      if (sel) {{ sel.value='{n}'; sel.dispatchEvent(new Event('change', {{bubbles:true}})); }}
                    }}"""
                )
                page.wait_for_timeout(600)
                probes[f"{vp}_stages_{n}"] = page.evaluate(
                    """() => {
                      const card=[...document.querySelectorAll('.ma-tpl-card')].find(c=>!c.hidden);
                      if (!card) return {enabled:0, disabled:0, missing:true};
                      const en=[...card.querySelectorAll('[data-ma-tpl-stage-route-enabled=\"1\"]')].length;
                      const dis=[...card.querySelectorAll('[data-ma-tpl-stage-route-enabled=\"0\"]')].length;
                      return {enabled:en, disabled:dis};
                    }"""
                )
                shot(page, f"{vp}_stages_{n}.png")

            # Inactive stage click attempt (stage 3 when count=1)
            page.evaluate(
                """() => {
                  const card=[...document.querySelectorAll('.ma-tpl-card')].find(c=>!c.hidden);
                  const sel=card && card.querySelector('[data-ma-tpl-msg-count]');
                  if (sel) { sel.value='1'; sel.dispatchEvent(new Event('change', {bubbles:true})); }
                }"""
            )
            page.wait_for_timeout(500)
            shot(page, f"{vp}_inactive_stages.png")

            ctx.close()
        browser.close()

    report = {
        "base": BASE,
        "probes": probes,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "identity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
