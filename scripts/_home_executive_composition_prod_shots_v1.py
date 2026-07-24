# -*- coding: utf-8 -*-
"""Gate 1-B — production Home Executive Composition Desktop/Mobile evidence."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_1b_executive_composition_v1"


def main() -> int:
    import sys

    label = (sys.argv[1] if len(sys.argv) > 1 else "after").strip() or "after"
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g1b.{uid}@smartreplyai.net"
    password = f"G1bLive!{uid[:8]}"
    report: dict = {
        "label": label,
        "email": email,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_url": f"{BASE}/dashboard#home",
        "gate": "gate_1b_executive_composition",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"G1B {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(7000)

        probe = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json();
              const hes = j.home_executive_summary_v1 || {};
              const sections = (hes.sections || []).map(s => ({
                id: s.id,
                title_ar: s.title_ar,
                summary_ar: s.summary_ar,
                status_ar: s.status_ar,
                href: s.view_details_href,
                empty: !!s.empty,
                owner_page: s.owner_page || null,
              }));
              const text = (document.getElementById('ma-home-experience-root')||{}).innerText || '';
              return {
                http: r.status,
                surface_mode: j.home_surface_mode || null,
                slim: !!j.home_slim_transport_v1,
                gate: (hes.governance || {}).gate || null,
                hes_ok: !!hes.ok,
                sections,
                has_store_status_title: text.includes('حالة المتجر'),
                has_old_health_title: text.includes('صحة العمل'),
                has_view_details: text.includes('عرض التفاصيل'),
                has_hes_title: text.includes('ماذا يجب أن تعرف الآن؟'),
                ownership_href: hes.section_ownership_href || null,
                text_sample: text.slice(0, 1200),
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
        desktop = OUT / f"{label}_desktop_home.png"
        page.screenshot(path=str(desktop), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        mobile = OUT / f"{label}_mobile_home.png"
        page.screenshot(path=str(mobile), full_page=False)
        browser.close()

        report["screenshots"] = {
            "desktop": str(desktop.relative_to(ROOT)).replace("\\", "/"),
            "mobile": str(mobile.relative_to(ROOT)).replace("\\", "/"),
        }
        report["ok"] = bool(
            probe.get("http") == 200
            and probe.get("hes_ok")
            and probe.get("has_hes_title")
            and probe.get("has_view_details")
        )
        if label.startswith("after"):
            report["ok"] = bool(
                report["ok"]
                and probe.get("has_store_status_title")
                and not probe.get("has_old_health_title")
            )

    out_json = OUT / f"{label}_verification.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "wrote": str(out_json),
        "ok": report["ok"],
        "http": (report.get("probe") or {}).get("http"),
        "has_store_status_title": (report.get("probe") or {}).get("has_store_status_title"),
        "has_old_health_title": (report.get("probe") or {}).get("has_old_health_title"),
        "section_titles": [
            s.get("title_ar") for s in ((report.get("probe") or {}).get("sections") or [])
        ],
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
