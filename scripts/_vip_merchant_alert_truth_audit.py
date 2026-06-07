# -*- coding: utf-8 -*-
"""Production VIP merchant alert operational truth audit."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_merchant_alert_truth_audit_out"
MERCHANT_WA = (os.environ.get("CARTFLOW_VIP_ALERT_MERCHANT_PHONE") or "966579706669").strip()


def _auth(page, report: dict) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        report["auth"] = {"mode": "login", "email": email}
        return
    uid = uuid.uuid4().hex[:10]
    email = f"cf.vip.alert.{uid}@smartreplyai.net"
    password = f"CfVipAlert!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipAlert {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "merchant_phone_configured": MERCHANT_WA,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        _auth(page, report)

        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
        page.wait_for_timeout(2500)
        page.evaluate(
            """() => {
              if (typeof window.maInitVipSettingsPage === 'function') window.maInitVipSettingsPage();
              var th = document.getElementById('ma-vip-threshold');
              if (th) th.value = '500';
              var en = document.getElementById('ma-vip-enabled');
              if (en) en.checked = true;
              var nt = document.getElementById('ma-vip-notify-enabled');
              if (nt) nt.checked = true;
            }"""
        )
        page.locator("#ma-vip-settings-save").click(timeout=20000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "01_vip_settings.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#whatsapp", timeout=120000)
        page.wait_for_timeout(2000)
        page.evaluate(
            f"""() => {{
              var n = document.getElementById('ma-wa-store-number');
              if (n) n.value = '{MERCHANT_WA}';
            }}"""
        )
        page.locator("#ma-wa-settings-save").click(timeout=20000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "02_whatsapp_settings.png"), full_page=False)

        settings = page.evaluate(
            """async () => {
              const vip = await fetch('/api/recovery-settings?scope=vip', {credentials:'same-origin'});
              const wa = await fetch('/api/recovery-settings', {credentials:'same-origin'});
              return { vip: await vip.json(), wa: await wa.json() };
            }"""
        )
        report["settings"] = settings
        store_slug = str((settings.get("wa") or {}).get("store_slug") or (settings.get("vip") or {}).get("store_slug") or "").strip()
        if not store_slug:
            store_slug = str((settings.get("wa") or {}).get("zid_store_id") or "").strip()
        report["store_slug"] = store_slug

        uid = uuid.uuid4().hex[:12]
        session_id = f"s_vip_alert_{uid}"
        cart_id = f"cf_cart_{uid}"
        cart_flow = page.evaluate(
            """async (args) => {
              const ev = await fetch('/api/cart-event', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  event: 'cart_state_sync',
                  reason: 'add',
                  store: args.store_slug,
                  session_id: args.session_id,
                  cart_id: args.cart_id,
                  cart_total: 1299.0,
                  items_count: 1,
                  cart: [{ price: 1299.0, quantity: 1 }],
                }),
              }).then(async (r) => { const t = await r.text(); let j=null; try{j=JSON.parse(t);}catch(e){j={raw:t};} j._http_status=r.status; return j; });
              return { cart_event: ev };
            }""",
            {"store_slug": store_slug, "session_id": session_id, "cart_id": cart_id},
        )
        report["cart_flow"] = cart_flow
        report["cart_id"] = cart_id
        report["session_id"] = session_id

        page.wait_for_timeout(3000)
        op = page.evaluate(
            """async (args) => {
              const u = '/dev/vip-merchant-alert-operational-truth?cart_id=' + encodeURIComponent(args.cart_id)
                + '&store_slug=' + encodeURIComponent(args.store_slug);
              const r = await fetch(u, { credentials: 'same-origin', cache: 'no-store' });
              return await r.json();
            }""",
            {"cart_id": cart_id, "store_slug": store_slug},
        )
        report["dev_vip_merchant_alert_operational_truth"] = op

        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "03_vip_dashboard_row.png"), full_page=True)

        vip_api = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/vip-carts', { credentials: 'same-origin', cache: 'no-store' });
              return await r.json();
            }"""
        )
        report["vip_carts_api"] = {
            "row_count": len(vip_api.get("merchant_vip_page_rows") or []),
            "alert_state_ar": vip_api.get("merchant_vip_alert_state_ar"),
        }
        browser.close()

    out_path = OUT / "vip_merchant_alert_truth_audit.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print("wrote", out_path)
    else:
        print("wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
