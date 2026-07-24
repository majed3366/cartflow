# -*- coding: utf-8 -*-
"""Capture Gate 2C Desktop/Mobile Home + Workspace evidence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_2c_decision_portfolio_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g2c.{uid}@smartreplyai.net"
    password = f"G2cLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1000)
        page.locator('input[name="store_name"]').fill(f"G2C {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)

        # Home timing
        t0 = page.evaluate("() => performance.now()")
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
              const teaser = j.home_teaser_inputs_v1 || {};
              return {
                http: r.status,
                fetch_ms: Math.round(fetch_ms),
                body_bytes: JSON.stringify(j).length,
                surface_mode: j.home_surface_mode || null,
                hes_ok: !!hes.ok,
                meif: !!j.merchant_experience_integration_v1,
                decisions_count: ((teaser.decisions||{}).count),
                portfolio_flag: !!(teaser.decisions||{}).portfolio,
              };
            }"""
        )
        report["home_probe"] = home_probe
        page.screenshot(
            path=str(OUT / "after_desktop_home.png"), full_page=False
        )

        # Workspace: two projection calls to observe cache
        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(5000)
        ws_probe = page.evaluate(
            """async () => {
              async function one() {
                const t0 = performance.now();
                const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                  credentials: 'same-origin', cache: 'no-store'
                });
                const ms = performance.now() - t0;
                const j = await r.json().catch(() => ({}));
                const p = j.projection || {};
                const text = (document.getElementById('cw-merchant-host')||{}).innerText || '';
                return {
                  http: r.status,
                  fetch_ms: Math.round(ms),
                  gate_2c: !!(j.gate_2c_decision_portfolio || p.gate_2c_decision_portfolio),
                  cache: ((p.decision_composition_v1||{}).cache) || null,
                  timing_ms: ((p.decision_composition_v1||{}).timing_ms) || null,
                  landscape: (((p.decision_composition_v1||{}).category_landscape)||[]).length,
                  has_portfolio_ui: text.includes('محفظة') || text.includes('الأولوية'),
                  has_healthy: text.includes('لا إجراء مطلوب'),
                  has_working_chrome: text.includes('CartFlow يعمل'),
                  text_sample: text.slice(0, 900),
                };
              }
              const first = await one();
              const second = await one();
              return { first, second };
            }"""
        )
        report["workspace_probe"] = ws_probe
        page.screenshot(
            path=str(OUT / "after_desktop_workspace.png"), full_page=False
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(
            path=str(OUT / "after_mobile_workspace.png"), full_page=False
        )
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(2000)
        page.screenshot(
            path=str(OUT / "after_mobile_home.png"), full_page=False
        )
        browser.close()

    first = (ws_probe or {}).get("first") or {}
    second = (ws_probe or {}).get("second") or {}
    ok = (
        bool(home_probe.get("hes_ok"))
        and not home_probe.get("meif")
        and bool(first.get("gate_2c"))
        and not first.get("has_working_chrome")
        and (
            bool(second.get("cache", {}).get("hit"))
            or (second.get("fetch_ms") or 9999) <= (first.get("fetch_ms") or 0) + 50
        )
    )
    payload = {
        **report,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": "gate_2c_decision_portfolio_perf",
        "screenshots": {
            "desktop_home": "docs/product/gate_2c_decision_portfolio_v1/after_desktop_home.png",
            "desktop_workspace": "docs/product/gate_2c_decision_portfolio_v1/after_desktop_workspace.png",
            "mobile_home": "docs/product/gate_2c_decision_portfolio_v1/after_mobile_home.png",
            "mobile_workspace": "docs/product/gate_2c_decision_portfolio_v1/after_mobile_workspace.png",
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
