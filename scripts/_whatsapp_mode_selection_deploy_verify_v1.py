# -*- coding: utf-8 -*-
"""Production verify: WhatsApp Mode Selection V1 on #whatsapp."""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_whatsapp_mode_selection_deploy_verify_v1_out" / "verify_report.json"


def main() -> int:
    uid = uuid.uuid4().hex[:8]
    email = f"cf.wa.mode.{uid}@smartreplyai.net"
    password = f"CfWa!{uid[:8]}"
    report: dict = {
        "audit": "whatsapp_mode_selection_deploy_verify_v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
    }

    with sync_playwright() as p:
        page = p.chromium.launch().new_page(viewport={"width": 1366, "height": 900})
        page.goto(f"{BASE}/signup", timeout=180000, wait_until="domcontentloaded")
        page.locator('input[name="store_name"]').fill(f"WA Mode {uid}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_url("**/dashboard**", timeout=120000)

        api = page.evaluate(
            """async () => {
              const r = await fetch('/api/recovery-settings?_=' + Date.now(), {credentials:'same-origin'});
              return await r.json();
            }"""
        )
        report["api_default"] = {
            "whatsapp_mode": api.get("whatsapp_mode"),
            "selection_title": (api.get("whatsapp_mode_selection") or {}).get("title_ar"),
            "options_count": ((api.get("whatsapp_mode_selection") or {}).get("options") || []).length,
        }

        page.goto(f"{BASE}/dashboard#whatsapp", timeout=180000, wait_until="domcontentloaded")
        page.wait_for_timeout(12000)

        dom = page.evaluate(
            """() => {
              const root = document.getElementById('ma-wa-mode-selection-root');
              return {
                text: root ? root.innerText : '',
                has_cartflow: (root ? root.innerText : '').includes('واتساب CartFlow'),
                has_merchant: (root ? root.innerText : '').includes('واتساب أعمال الخاص بي'),
                has_recommended: (root ? root.innerText : '').includes('موصى به'),
              };
            }"""
        )
        report["dashboard_default"] = dom

        switch = page.evaluate(
            """async () => {
              const r = await fetch('/api/recovery-settings', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                  whatsapp_mode: 'merchant_whatsapp',
                  store_whatsapp_number: '+966500000555',
                  whatsapp_recovery_enabled: true,
                  whatsapp_onboarding_journey: 'existing_whatsapp_business',
                }),
              });
              const body = await r.json();
              const panel = body.whatsapp_mode_merchant_panel || {};
              return {
                ok: body.ok,
                mode: body.whatsapp_mode,
                panel_visible: panel.visible,
                meta_pairing: panel.meta_pairing_status_ar,
                embedded: panel.embedded_signup_status_ar,
              };
            }"""
        )
        report["merchant_switch"] = switch

        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        panel_dom = page.evaluate(
            """() => {
              const p = document.getElementById('ma-wa-merchant-owned-panel');
              return {
                visible: p && !p.hidden,
                text: p ? p.innerText : '',
              };
            }"""
        )
        report["dashboard_merchant_panel"] = panel_dom

    report["checks"] = {
        "default_cartflow_managed": report["api_default"].get("whatsapp_mode") == "cartflow_managed",
        "selection_cards_rendered": report["dashboard_default"].get("has_cartflow")
        and report["dashboard_default"].get("has_merchant"),
        "merchant_mode_persisted": report["merchant_switch"].get("mode") == "merchant_whatsapp",
        "merchant_panel_api": report["merchant_switch"].get("panel_visible") is True,
        "merchant_panel_dom": report["dashboard_merchant_panel"].get("visible") is True,
    }
    report["pass"] = all(report["checks"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.stdout.buffer.write(
        json.dumps({"pass": report["pass"], "checks": report["checks"]}, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )
    )
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
