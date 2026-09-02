# -*- coding: utf-8 -*-
"""Capture Merchant IA Ownership Reconciliation V3 evidence."""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
OUT = Path(
    r"C:\Users\Toshiba\AppData\Local\Temp\cf-psg-impl-v1\docs\product\merchant_ia_ownership_reconciliation_v3\evidence"
)


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
            page.wait_for_timeout(1500)
            probes[f"{vp}_account"] = page.evaluate(
                """() => ({
                  store: (document.querySelector('#cf2-account-store-name')||{}).textContent||'',
                  meta: (document.querySelector('#cf2-account-store-meta')||{}).textContent||'',
                  plan: (document.querySelector('#cf2-account-plan')||{}).textContent||'',
                  hasV1Link: !!document.querySelector('a[href*=\"cf_ui=v1\"]'),
                  labels: [...document.querySelectorAll('.cf2-drawer__item')].map(x=>x.textContent.trim())
                })"""
            )
            page.screenshot(path=str(OUT / f"{vp}_account_drawer.png"), full_page=False)

            # Settings recovery
            page.evaluate("location.hash='trigger-templates'")
            page.wait_for_timeout(4500)
            probes[f"{vp}_recovery"] = page.evaluate(
                """() => ({
                  hash: location.hash,
                  tpl: document.querySelectorAll('#ma-tpl-root .ma-tpl-card, #ma-tpl-root [data-reason], #ma-tpl-root article').length,
                  v1: !!document.querySelector('a[href*=\"cf_ui=v1\"]'),
                  ui: document.body.getAttribute('data-cf-ui'),
                  ataba: (document.body.innerText||'').includes('العتبة')
                })"""
            )
            page.screenshot(path=str(OUT / f"{vp}_settings_recovery.png"), full_page=True)

            # WhatsApp → open recovery handoff
            page.evaluate("location.hash='whatsapp'")
            page.wait_for_timeout(3500)
            page.evaluate(
                """() => {
                  const b = document.querySelector('[data-cf2-open-settings=\"recovery\"]');
                  if (b) b.click();
                }"""
            )
            page.wait_for_timeout(4000)
            probes[f"{vp}_template_nav"] = page.evaluate(
                """() => ({
                  panel: !!document.querySelector('[data-cf2-settings-panel=\"recovery\"]:not([hidden])'),
                  tpl: document.querySelectorAll('#ma-tpl-root .ma-tpl-card, #ma-tpl-root article').length,
                  v1: !!document.querySelector('a[href*=\"cf_ui=v1\"]'),
                  ui: document.body.getAttribute('data-cf-ui')
                })"""
            )
            page.screenshot(path=str(OUT / f"{vp}_template_nav_result.png"), full_page=True)

            # VIP threshold labels
            page.evaluate(
                """() => {
                  const a = [...document.querySelectorAll('.cf2-ctx__item,.cf2-settings__row')]
                    .find(x => (x.textContent||'').includes('سياسة السلال'));
                  if (a) a.click();
                }"""
            )
            page.wait_for_timeout(3500)
            probes[f"{vp}_vip"] = page.evaluate(
                """() => ({
                  ataba: (document.body.innerText||'').includes('العتبة'),
                  minLabel: (document.body.innerText||'').includes('الحد الأدنى لقيمة السلة'),
                  ui: document.body.getAttribute('data-cf-ui')
                })"""
            )
            page.screenshot(path=str(OUT / f"{vp}_vip_threshold.png"), full_page=True)

            # Package / store settings
            page.evaluate(
                """() => {
                  const a = [...document.querySelectorAll('.cf2-ctx__item,.cf2-settings__row')]
                    .find(x => (x.textContent||'').includes('المتجر'));
                  if (a) a.click();
                }"""
            )
            page.wait_for_timeout(3500)
            probes[f"{vp}_package"] = page.evaluate(
                """() => ({
                  hasPlan: (document.body.innerText||'').includes('الباقة الحالية'),
                  ui: document.body.getAttribute('data-cf-ui')
                })"""
            )
            page.screenshot(path=str(OUT / f"{vp}_package.png"), full_page=True)
            ctx.close()
        browser.close()

    report = {"base": BASE, "probes": probes, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (OUT / "identity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
