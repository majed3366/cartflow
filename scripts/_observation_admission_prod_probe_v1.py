# -*- coding: utf-8 -*-
"""Probe production Home for Observation Admission visibility."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "observation_admission_bridge_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.oab.probe.{uid}@smartreplyai.net"
    password = f"OabProbe!{uid[:8]}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1000)
        page.locator('input[name="store_name"]').fill(f"OAB {uid[:6]}")
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
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const orv = j.observation_reality_validation_v1 || {};
              const secs = hes.sections || [];
              const by = Object.fromEntries(secs.map(s => [s.id, s]));
              const root = document.getElementById('ma-home-experience-root');
              const text = (root && root.innerText) || '';
              return {
                http: r.status,
                store_slug: j.store_slug
                  || ((j.merchant_home_experience_v1 || {}).store_slug)
                  || null,
                home_surface_mode: j.home_surface_mode || null,
                orv_key_present: Object.prototype.hasOwnProperty.call(
                  j, 'observation_reality_validation_v1'
                ),
                orv_count: (orv.findings || []).length,
                orv_present_capabilities: orv.present_capabilities || [],
                orv_recon: orv.admission_reconciliation || null,
                orv_empty_state: orv.empty_state_ar || null,
                obs_summary: ((by.observations || {}).summary_ar) || null,
                obs_empty: (by.observations || {}).empty,
                obs_count: (by.observations || {}).count,
                section_ids: secs.map(s => s.id),
                text_has_raven: text.includes('Raven'),
                text_sample: text.slice(0, 700),
              };
            }"""
        )
        page.screenshot(
            path=str(OUT / "prod_before_empty_desktop_home.png"), full_page=False
        )
        browser.close()

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "url": f"{BASE}/dashboard#home",
        "email": email,
        "probe": probe,
        "interpretation": (
            "Fresh merchant signup store — not living-store demo mass. "
            "Empty observations are expected unless session is bound to "
            "production store_slug=demo with Living Store history."
        ),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    (OUT / "prod_home_probe_before.json").write_text(text, encoding="utf-8")
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
