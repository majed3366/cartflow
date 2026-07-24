# -*- coding: utf-8 -*-
"""Gate 1 — measure /api/dashboard/summary payload + Home boot signals (prod)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "gate_1_home_slim_transport_v1"


def main() -> int:
    import sys

    label = (sys.argv[1] if len(sys.argv) > 1 else "probe").strip() or "probe"
    OUT.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:10]
    email = f"cf.g1.{uid}@smartreplyai.net"
    password = f"G1Live!{uid[:8]}"
    report: dict = {
        "label": label,
        "email": email,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_url": f"{BASE}/dashboard#home",
        "gate": "gate_1_home_slim_transport",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"G1 {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(7000)

        probe = page.evaluate(
            """async () => {
              const t0 = performance.now();
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const raw = await r.text();
              const t1 = performance.now();
              let j = {};
              try { j = JSON.parse(raw); } catch (e) { j = { parse_error: String(e) }; }
              const keys = Object.keys(j || {}).sort();
              const heavy = [
                'merchant_experience_integration_v1',
                'observation_reality_validation_v1',
                'merchant_daily_brief_v1',
                'merchant_pulse_v1',
                'commerce_signals_v1',
                'home_adaptive_cognition_v1',
                'adaptive_cognition_v1',
              ];
              const present_heavy = heavy.filter(k => j[k] != null);
              const hes = j.home_executive_summary_v1 || {};
              const teasers = j.home_teaser_inputs_v1 || {};
              const orv = j.observation_reality_validation_v1 || {};
              const meif = j.merchant_experience_integration_v1;
              let meif_bytes = 0;
              try { meif_bytes = meif ? JSON.stringify(meif).length : 0; } catch (e) {}
              let orv_bytes = 0;
              try { orv_bytes = orv && Object.keys(orv).length ? JSON.stringify(orv).length : 0; } catch (e) {}
              const text = (document.getElementById('ma-home-experience-root')||{}).innerText || '';
              const ids = (hes.sections || []).map(s => s.id);
              return {
                http: r.status,
                fetch_ms: Math.round(t1 - t0),
                body_bytes: raw.length,
                key_count: keys.length,
                keys_sample: keys.slice(0, 40),
                present_heavy,
                heavy_count: present_heavy.length,
                home_slim_transport_v1: !!j.home_slim_transport_v1,
                surface_mode: j.home_surface_mode || null,
                has_teasers: !!(teasers && teasers.schema === 'home_teaser_inputs_v1'),
                hes_ok: !!hes.ok,
                section_ids: ids,
                has_five_sections: ids.join(',') === 'health,decisions,observations,carts,communication',
                meif_bytes,
                orv_bytes,
                orv_findings: Array.isArray(orv.findings) ? orv.findings.length : null,
                orv_stripped: !!orv.stripped_for_home_slim_transport,
                has_recommended_action_on_home: JSON.stringify(hes).includes('recommended_action_ar'),
                has_hes_title: text.includes('ماذا يجب أن تعرف الآن؟'),
                has_view_details: text.includes('عرض التفاصيل'),
              };
            }"""
        )
        report["probe"] = probe
        # Also sample whether boot fired carts/messages (network) — best-effort via performance entries.
        net = page.evaluate(
            """() => {
              const entries = performance.getEntriesByType('resource') || [];
              const urls = entries.map(e => e.name || '');
              return {
                summary_calls: urls.filter(u => u.includes('/api/dashboard/summary')).length,
                normal_carts_calls: urls.filter(u => u.includes('/api/dashboard/normal-carts')).length,
                messages_calls: urls.filter(u => u.includes('/api/dashboard/messages')).length,
              };
            }"""
        )
        report["boot_network"] = net

        desktop = OUT / f"{label}_desktop_home.png"
        page.evaluate(
            """() => {
              const el = document.getElementById('ma-home-experience-root');
              if (el) el.scrollIntoView({block:'start'});
            }"""
        )
        page.wait_for_timeout(400)
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
            and probe.get("has_five_sections")
        )

    out_json = OUT / f"{label}_perf.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out_json), "ok": report["ok"], "probe": report["probe"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
