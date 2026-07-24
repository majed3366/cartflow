# -*- coding: utf-8 -*-
"""Capture production Gate 2B Desktop/Mobile Decision Workspace shots."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_2b_decision_composition_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g2b.{uid}@smartreplyai.net"
    password = f"G2bLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"G2B {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(7000)

        probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/cart-workspace/v1/projection?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const host = document.getElementById('cw-merchant-host') || {};
              const text = host.innerText || '';
              const p = j.projection || {};
              const cards = [].concat(p.zone_a || [], p.zone_b || []);
              const titles = cards.map(c => (c.decision_ar || c.title_ar || ''));
              return {
                http: r.status,
                ok: !!j.ok,
                gate_2b: !!(j.gate_2b_decision_composition_engine || p.gate_2b_decision_composition_engine),
                has_composition: !!(p.decision_composition_v1),
                has_mission: text.includes('أقرر'),
                has_why_now: text.includes('لماذا الآن') || cards.some(c => !!(c.why_now_ar)),
                has_ignore: text.includes('تجاهل') || cards.some(c => !!(c.ignore_consequence_ar)),
                has_first_step: text.includes('ابدأ بهذه الخطوة') || cards.some(c => !!(c.first_step_ar)),
                raw_counter_title: titles.some(t => t.includes('راجع سلال بلا رقم')),
                business_meaning: titles.some(t => t.includes('قابلين للاسترجاع')) || text.includes('قابلين للاسترجاع'),
                has_working_chrome: text.includes('CartFlow يعمل'),
                text_sample: text.slice(0, 1000),
                card_count: cards.length,
              };
            }"""
        )
        report["probe"] = probe
        desktop = OUT / "after_desktop_workspace.png"
        page.screenshot(path=str(desktop), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        mobile = OUT / "after_mobile_workspace.png"
        page.screenshot(path=str(mobile), full_page=False)
        browser.close()

    ok = (
        bool(probe.get("ok"))
        and bool(probe.get("gate_2b"))
        and bool(probe.get("has_mission"))
        and not probe.get("has_working_chrome")
        and not probe.get("raw_counter_title")
        and (
            bool(probe.get("has_why_now"))
            or bool(probe.get("has_first_step"))
            or int(probe.get("card_count") or 0) == 0
        )
    )
    payload = {
        **report,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_url": f"{BASE}/dashboard#workspace",
        "sprint": "gate_2b_decision_composition_engine",
        "screenshots": {
            "desktop": str(desktop.relative_to(ROOT)).replace("\\", "/"),
            "mobile": str(mobile.relative_to(ROOT)).replace("\\", "/"),
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
