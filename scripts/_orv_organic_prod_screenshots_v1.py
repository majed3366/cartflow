# -*- coding: utf-8 -*-
"""Organic production Home screenshots for approved ORV (no client inject)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "observation_reality_validation_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.orv.live.{uid}@smartreplyai.net"
    password = f"OrvLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"ORV Live {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(6000)

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
                findings_n: findings.length,
                titles: findings.map(f => f.title_ar),
                actions: findings.map(f => f.recommended_action_ar),
                conf: findings.map(f => f.confidence_ar),
                mass_source: orv.mass_source || null,
                resolved: orv.store_slug_resolved || null,
              };
            }"""
        )
        report["summary"] = summary

        page.evaluate(
            """() => {
              const el = document.getElementById('observation-reality-validation-root');
              if (el) el.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(500)

        probe = page.evaluate(
            """() => {
              const root = document.getElementById('observation-reality-validation-root');
              const text = (root && root.innerText) || '';
              const banned = [
                'cart_add', 'purchase=', 'return=', 'shipping=',
                'price=', 'evidence_refs', 'DEMO-PERFUME'
              ];
              return {
                cards: document.querySelectorAll('[data-orv-finding]').length,
                actions: document.querySelectorAll('[data-orv-action]').length,
                conf: document.querySelectorAll('[data-orv-confidence]').length,
                statements: document.querySelectorAll('[data-orv-statement]').length,
                has_title: text.includes('ماذا نلاحظ في منتجاتك الآن؟'),
                banned_visible: banned.filter((b) => text.includes(b)),
                text_sample: text.slice(0, 600),
              };
            }"""
        )
        report["probe"] = probe

        desktop = OUT / "08_production_desktop_orv_restored.png"
        page.screenshot(path=str(desktop), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        page.evaluate(
            """() => {
              const el = document.getElementById('observation-reality-validation-root');
              if (el) el.scrollIntoView({block: 'start'});
            }"""
        )
        page.wait_for_timeout(400)
        mobile = OUT / "09_production_mobile_orv_restored.png"
        page.screenshot(path=str(mobile), full_page=False)
        browser.close()

    ok = (
        probe.get("cards") == 4
        and probe.get("actions") == 4
        and probe.get("conf") == 4
        and probe.get("statements") == 4
        and probe.get("has_title")
        and not probe.get("banned_visible")
        and summary.get("findings_n") == 4
    )
    report.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "production_url": f"{BASE}/dashboard#home",
            "screenshots": {
                "desktop": str(desktop.relative_to(OUT.parent.parent.parent)).replace(
                    "\\", "/"
                ),
                "mobile": str(mobile.relative_to(OUT.parent.parent.parent)).replace(
                    "\\", "/"
                ),
            },
            "ok": ok,
        }
    )
    (OUT / "orv_restored_organic_verify.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
