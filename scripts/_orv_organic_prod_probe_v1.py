# -*- coding: utf-8 -*-
"""Probe organic production Home ORV payload (no client inject)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "observation_reality_validation_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.orv.organic.{uid}@smartreplyai.net"
    password = f"OrvOrg!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"ORV Org {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(5500)

        summary = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json();
              const orv = j.observation_reality_validation_v1 || {};
              const findings = Array.isArray(orv.findings) ? orv.findings : [];
              return {
                http: r.status,
                store_slug: (j.merchant_home_experience_v1 || {}).store_slug || j.store_slug,
                orv_ok: orv.ok,
                orv_enabled: orv.enabled,
                findings_n: findings.length,
                titles: findings.map(f => f.title_ar),
                has_action: findings.every(f => !!(f.recommended_action_ar)),
                has_conf: findings.every(f => !!(f.confidence_ar)),
                resolved: orv.store_slug_resolved || null,
                missing: orv.missing_capabilities || [],
                meif_home: !!(j.merchant_experience_integration_v1 &&
                  j.merchant_experience_integration_v1.pages &&
                  j.merchant_experience_integration_v1.pages.home),
              };
            }"""
        )
        report["summary"] = summary

        root = page.evaluate(
            """() => {
              const el = document.getElementById('observation-reality-validation-root');
              const text = (el && el.innerText) || '';
              return {
                exists: !!el,
                hidden: !!(el && el.hidden),
                cards: document.querySelectorAll('[data-orv-finding]').length,
                text_sample: text.slice(0, 500),
                has_title: text.includes('ماذا نلاحظ في منتجاتك الآن؟'),
              };
            }"""
        )
        report["dom"] = root
        page.screenshot(
            path=str(OUT / "07_organic_prod_home_before_fix.png"), full_page=False
        )
        browser.close()

    (OUT / "organic_prod_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
