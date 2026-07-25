# -*- coding: utf-8 -*-
"""Capture Gate 2F Desktop/Mobile Home + Workspace evidence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_2f_store_executive_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g2f.{uid}@smartreplyai.net"
    password = f"G2fLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1000)
        page.locator('input[name="store_name"]').fill(f"G2F {uid[:6]}")
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
              const dec = (byId.decisions||{}).summary_ar || '';
              const health = (byId.health||{}).summary_ar || '';
              const forbidden = ['scheduler', 'CartFlow', 'عدّاد', 'محرك الاسترجاع', 'بلا رقم'];
              const allText = [health, dec,
                (byId.carts||{}).summary_ar || '',
                (byId.communication||{}).summary_ar || '',
                (byId.observations||{}).summary_ar || ''].join(' ');
              return {
                http: r.status,
                fetch_ms: Math.round(fetch_ms),
                body_bytes: JSON.stringify(j).length,
                hes_ok: !!hes.ok,
                meif: !!j.merchant_experience_integration_v1,
                section_ids: sections.map(s => s.id),
                health_summary: health,
                decisions_summary: dec,
                health_equals_decision: health === dec,
                decision_has_counter_phrase: /\\d+\\s*سلة/.test(dec) && dec.includes('بلا رقم'),
                store_executive: !!(hes.governance||{}).store_executive_thinking,
                system_centric: forbidden.some(t => allText.includes(t)),
                obs: (byId.observations||{}).summary_ar || '',
                carts: (byId.carts||{}).summary_ar || '',
                comm: (byId.communication||{}).summary_ar || '',
              };
            }"""
        )
        report["home_probe"] = home_probe
        page.screenshot(path=str(OUT / "after_desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(5000)
        ws_probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const p = j.projection || {};
              const text = (document.getElementById('cw-merchant-host')||{}).innerText || '';
              const cards = (p.zone_b||[]).concat(p.zone_a||[]);
              const top = cards[0] || {};
              const title = top.decision_ar || top.title_ar || '';
              return {
                http: r.status,
                gate_2f: !!(p.gate_2f_store_executive),
                gate_2e: !!(p.gate_2e_executive_business),
                landscape: (((p.decision_composition_v1||{}).category_landscape)||[]).length,
                has_exec_subtitle: text.includes('مساعد تنفيذي') || text.includes('أثر العمل'),
                top_decision: title,
                top_has_meaning: !!(top.business_meaning_ar),
                counter_as_title: /\\d+\\s*سلة/.test(title) && title.includes('بلا رقم'),
                cache_hit: !!(((p.decision_composition_v1||{}).cache)||{}).hit,
              };
            }"""
        )
        report["workspace_probe"] = ws_probe
        page.screenshot(path=str(OUT / "after_desktop_workspace.png"), full_page=False)

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "after_mobile_workspace.png"), full_page=False)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "after_mobile_home.png"), full_page=False)
        browser.close()

    ok = (
        bool(home_probe.get("hes_ok"))
        and not home_probe.get("meif")
        and home_probe.get("section_ids")
        == [
            "health",
            "decisions",
            "observations",
            "carts",
            "communication",
        ]
        and not home_probe.get("health_equals_decision")
        and not home_probe.get("decision_has_counter_phrase")
        and bool(home_probe.get("store_executive"))
        and not home_probe.get("system_centric")
        and bool(ws_probe.get("gate_2f"))
        and not ws_probe.get("counter_as_title")
    )
    payload = {
        **report,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sprint": "gate_2f_store_executive",
        "screenshots": {
            "desktop_home": "docs/product/gate_2f_store_executive_v1/after_desktop_home.png",
            "desktop_workspace": "docs/product/gate_2f_store_executive_v1/after_desktop_workspace.png",
            "mobile_home": "docs/product/gate_2f_store_executive_v1/after_mobile_home.png",
            "mobile_workspace": "docs/product/gate_2f_store_executive_v1/after_mobile_workspace.png",
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
