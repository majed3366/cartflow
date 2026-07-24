# -*- coding: utf-8 -*-
"""Capture production Gate 2 Desktop/Mobile evidence (Workspace + Home)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_2_decision_ownership_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g2.{uid}@smartreplyai.net"
    password = f"G2Live!{uid[:8]}"
    report: dict = {"email": email}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"G2 {uid[:6]}")
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
              const host = document.getElementById('cw-merchant-host')
                || document.querySelector('[data-cw-host]')
                || document.getElementById('page-workspace');
              const meif = document.getElementById('meif-decision-root');
              const text = (host && host.innerText) || '';
              const dual = !!(window.CARTFLOW_DECISION_DUAL_STACK_V1);
              return {
                http: r.status,
                ok: !!j.ok,
                gate_2: !!j.gate_2_single_decision_owner,
                business_finding_count: j.projection && j.projection.business_finding_count,
                mission: (j.projection && j.projection.mission_question) || '',
                dual_stack: dual,
                meif_hidden: !meif || !!meif.hidden || meif.getAttribute('hidden') !== null,
                meif_empty: !meif || !(meif.innerText || '').trim(),
                has_mission_copy: text.includes('أقرر') || (j.projection && (j.projection.mission_question || '').includes('أقرر')),
                workspace_text_sample: text.slice(0, 800),
              };
            }"""
        )
        report["workspace_probe"] = probe

        desktop_ws = OUT / "after_desktop_workspace.png"
        page.screenshot(path=str(desktop_ws), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        mobile_ws = OUT / "after_mobile_workspace.png"
        page.screenshot(path=str(mobile_ws), full_page=False)

        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(6000)
        home_probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const dec = (hes.sections || []).find(s => s && s.id === 'decisions') || {};
              const text = (document.getElementById('ma-home-experience-root')||{}).innerText || '';
              return {
                http: r.status,
                surface_mode: j.home_surface_mode || null,
                hes_ok: !!hes.ok,
                decisions_href: dec.view_details_href || null,
                decisions_cta: dec.view_details_ar || null,
                has_workspace_cta: (dec.view_details_ar || '').includes('مساحة القرار')
                  || text.includes('مساحة القرار'),
                meif_present: !!j.merchant_experience_integration_v1,
              };
            }"""
        )
        report["home_probe"] = home_probe
        desktop_home = OUT / "after_desktop_home.png"
        page.screenshot(path=str(desktop_home), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        mobile_home = OUT / "after_mobile_home.png"
        page.screenshot(path=str(mobile_home), full_page=False)
        browser.close()

    ok = (
        bool(probe.get("ok"))
        and bool(probe.get("gate_2"))
        and bool(probe.get("meif_hidden"))
        and not bool(probe.get("dual_stack"))
        and home_probe.get("decisions_href") == "#workspace"
        and bool(home_probe.get("has_workspace_cta"))
        and not home_probe.get("meif_present")
    )
    report.update(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "production_url_workspace": f"{BASE}/dashboard#workspace",
            "production_url_home": f"{BASE}/dashboard#home",
            "sprint": "gate_2_single_decision_owner",
            "screenshots": {
                "desktop_workspace": str(desktop_ws.relative_to(ROOT)).replace("\\", "/"),
                "mobile_workspace": str(mobile_ws.relative_to(ROOT)).replace("\\", "/"),
                "desktop_home": str(desktop_home.relative_to(ROOT)).replace("\\", "/"),
                "mobile_home": str(mobile_home.relative_to(ROOT)).replace("\\", "/"),
            },
            "ok": ok,
            "status": (
                "AWAITING_CEO_REVIEW_BEFORE_GATE_2_CLOSE"
                if ok
                else "NEEDS_DEPLOY_OR_FIX"
            ),
        }
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    (OUT / "after_verification.json").write_text(payload, encoding="utf-8")
    try:
        print(payload)
    except UnicodeEncodeError:
        print(payload.encode("ascii", "backslashreplace").decode("ascii"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
