# -*- coding: utf-8 -*-
"""Capture organic production Home Executive Summary Desktop/Mobile shots."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "home_executive_summary_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.hes.{uid}@smartreplyai.net"
    password = f"HesLive!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"HES {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(6000)

        probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json();
              const hes = j.home_executive_summary_v1 || {};
              const orv = j.observation_reality_validation_v1 || {};
              const text = (document.getElementById('ma-home-experience-root')||{}).innerText || '';
              const ids = (hes.sections || []).map(s => s.id);
              return {
                http: r.status,
                surface_mode: j.home_surface_mode || null,
                hes_ok: !!hes.ok,
                section_ids: ids,
                has_five_sections: ids.join(',') === 'health,decisions,observations,carts,communication',
                has_status: (hes.sections || []).every(s => !!(s && s.status_ar)),
                obs_empty: ((hes.sections||[]).find(s => s.id==='observations')||{}).empty,
                obs_summary: ((hes.sections||[]).find(s => s.id==='observations')||{}).summary_ar,
                orv_findings: (orv.findings || []).length,
                has_demo_perfume: text.includes('DEMO-PERFUME') || text.includes('هذا المنتج'),
                has_hes_title: text.includes('ماذا يجب أن تعرف الآن؟'),
                has_view_details: text.includes('عرض التفاصيل'),
                has_carts_section: text.includes('السلال'),
                has_communication_section: text.includes('التواصل'),
                text_sample: text.slice(0, 900),
              };
            }"""
        )
        report["probe"] = probe
        page.evaluate(
            """() => {
              const el = document.getElementById('ma-home-experience-root');
              if (el) el.scrollIntoView({block:'start'});
            }"""
        )
        page.wait_for_timeout(400)
        desktop = OUT / "01_desktop_home_executive_summary.png"
        page.screenshot(path=str(desktop), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        mobile = OUT / "02_mobile_home_executive_summary.png"
        page.screenshot(path=str(mobile), full_page=False)
        browser.close()

    obs_empty = probe.get("obs_empty")
    ok = (
        bool(probe.get("hes_ok"))
        and probe.get("surface_mode") == "executive_summary_v1"
        and bool(probe.get("has_five_sections"))
        and bool(probe.get("has_status"))
        and bool(probe.get("has_hes_title"))
        and bool(probe.get("has_view_details"))
        and bool(probe.get("has_carts_section"))
        and bool(probe.get("has_communication_section"))
        and not probe.get("has_demo_perfume")
        and obs_empty in (True, "True", "true", 1)
    )
    report.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "production_url": f"{BASE}/dashboard#home",
            "sprint": "home_stabilization_v1",
            "screenshots": {
                "desktop": str(desktop.relative_to(ROOT)).replace("\\", "/"),
                "mobile": str(mobile.relative_to(ROOT)).replace("\\", "/"),
            },
            "ok": ok,
            "status": (
                "AWAITING_CEO_REVIEW_BEFORE_PRODUCT_INTELLIGENCE_V1"
                if ok
                else "NEEDS_DEPLOY_OR_FIX"
            ),
        }
    )
    (OUT / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
