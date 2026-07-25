# -*- coding: utf-8 -*-
"""Capture Gate 2D Desktop/Mobile Home + Workspace evidence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_2d_business_domain_dedupe_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g2d.{uid}@smartreplyai.net"
    password = f"G2dLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1000)
        page.locator('input[name="store_name"]').fill(f"G2D {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)

        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(5000)
        home_probe = page.evaluate(
            """async () => {
              const t0 = performance.now();
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const fetch_ms = performance.now() - t0;
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const sections = hes.sections || [];
              const byId = Object.fromEntries(sections.map(s => [s.id, s]));
              const teaser = j.home_teaser_inputs_v1 || {};
              const text = (document.getElementById('ma-home-executive-summary')
                || document.querySelector('[data-hes]')
                || document.body).innerText || '';
              return {
                http: r.status,
                fetch_ms: Math.round(fetch_ms),
                body_bytes: JSON.stringify(j).length,
                surface_mode: j.home_surface_mode || null,
                hes_ok: !!hes.ok,
                meif: !!j.merchant_experience_integration_v1,
                section_ids: sections.map(s => s.id),
                decisions_summary: (byId.decisions||{}).summary_ar || '',
                health_summary: (byId.health||{}).summary_ar || '',
                health_equals_decision: ((byId.health||{}).summary_ar||'') ===
                  ((byId.decisions||{}).summary_ar||''),
                has_why_on_home: text.includes('لماذا؟') || text.includes('لماذا الآن'),
                gate_2d_teaser: !!(teaser.decisions||{}).gate_2d,
                portfolio: !!(teaser.decisions||{}).portfolio,
              };
            }"""
        )
        report["home_probe"] = home_probe
        page.screenshot(path=str(OUT / "after_desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(5000)
        ws_probe = page.evaluate(
            """async () => {
              const t0 = performance.now();
              const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const ms = performance.now() - t0;
              const j = await r.json().catch(() => ({}));
              const p = j.projection || {};
              const text = (document.getElementById('cw-merchant-host')||{}).innerText || '';
              const regs = ((p.decision_composition_v1||{}).suppression_registry)||[];
              return {
                http: r.status,
                fetch_ms: Math.round(ms),
                gate_2d: !!(j.gate_2d_business_domains || p.gate_2d_business_domains),
                gate_2d_dedupe: !!(p.gate_2d_decision_dedupe),
                landscape: (((p.decision_composition_v1||{}).category_landscape)||[]).length,
                has_portfolio_ui: text.includes('محفظة') || text.includes('الأولوية'),
                has_healthy: text.includes('لا إجراء مطلوب'),
                has_why_on_workspace: text.includes('لماذا'),
                has_working_chrome: text.includes('CartFlow يعمل'),
                suppressed: regs.length,
                cache_hit: !!(((p.decision_composition_v1||{}).cache)||{}).hit,
              };
            }"""
        )
        report["workspace_probe"] = ws_probe
        page.screenshot(path=str(OUT / "after_desktop_workspace.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#carts", timeout=120000)
        page.wait_for_timeout(3000)
        carts_probe = page.evaluate(
            """() => {
              const text = document.body.innerText || '';
              return {
                has_why_matters: text.includes('لماذا يهم'),
                has_recommendation: text.includes('التوصية') || text.includes('يلزم إجراء'),
              };
            }"""
        )
        report["carts_probe"] = carts_probe
        page.screenshot(path=str(OUT / "after_desktop_carts.png"), full_page=False)

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "after_mobile_workspace.png"), full_page=False)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "after_mobile_home.png"), full_page=False)
        browser.close()

    ok = (
        bool(home_probe.get("hes_ok"))
        and not home_probe.get("meif")
        and home_probe.get("section_ids") == [
            "health",
            "decisions",
            "observations",
            "carts",
            "communication",
        ]
        and not home_probe.get("health_equals_decision")
        and not home_probe.get("has_why_on_home")
        and bool(ws_probe.get("gate_2d"))
        and bool(ws_probe.get("has_portfolio_ui"))
        and not ws_probe.get("has_working_chrome")
        and not carts_probe.get("has_why_matters")
    )
    payload = {
        **report,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": "gate_2d_business_domain_dedupe",
        "screenshots": {
            "desktop_home": "docs/product/gate_2d_business_domain_dedupe_v1/after_desktop_home.png",
            "desktop_workspace": "docs/product/gate_2d_business_domain_dedupe_v1/after_desktop_workspace.png",
            "desktop_carts": "docs/product/gate_2d_business_domain_dedupe_v1/after_desktop_carts.png",
            "mobile_home": "docs/product/gate_2d_business_domain_dedupe_v1/after_mobile_home.png",
            "mobile_workspace": "docs/product/gate_2d_business_domain_dedupe_v1/after_mobile_workspace.png",
        },
        "ok": ok,
        "status": (
            "AWAITING_CEO_REVIEW_BEFORE_GATE_2_CLOSE"
            if ok
            else "NEEDS_DEPLOY_OR_FIX"
        ),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (OUT / "after_verification.json").write_text(text, encoding="utf-8")
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
