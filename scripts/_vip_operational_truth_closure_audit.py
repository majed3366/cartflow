# -*- coding: utf-8 -*-
"""Production closure audit: VIP alert delivery + lane isolation + lifecycle truth."""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_operational_truth_closure_out"
MERCHANT_WA = (os.environ.get("CARTFLOW_VIP_ALERT_MERCHANT_PHONE") or "966579706669").strip()


def _api(page, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    return page.evaluate(
        """async (args) => {
          const opts = { method: args.method, credentials: 'same-origin', cache: 'no-store' };
          if (args.body) {
            opts.headers = { 'Content-Type': 'application/json' };
            opts.body = JSON.stringify(args.body);
          }
          const r = await fetch(args.path, opts);
          const t = await r.text();
          let j = null;
          try { j = JSON.parse(t); } catch (e) { j = { raw: t.slice(0, 1200) }; }
          j._http_status = r.status;
          return j;
        }""",
        {"path": path, "method": method, "body": body},
    )


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
    email = f"cf.vip.closure.{uid}@smartreplyai.net"
    password = f"CfVipCl!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipClosure {uid[:6]}")
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
        "merchant_phone_expected": MERCHANT_WA,
        "closure_checks": {},
    }
    uid = uuid.uuid4().hex[:12]
    cart_id = f"cf_cart_vip_closure_{uid}"
    session_id = f"s_vip_closure_{uid}"
    cart_total = 1299.0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        _auth(page, report)
        me = _api(page, "/api/me")
        report["me"] = me
        store_slug = str(me.get("store_slug") or me.get("zid_store_id") or "").strip()
        if not store_slug:
            report["error"] = "no_store_slug"
            OUT.joinpath("report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            browser.close()
            return 1

        _api(
            page,
            "/api/merchant/vip-settings",
            method="POST",
            body={
                "vip_cart_threshold": 500,
                "vip_notify_enabled": True,
                "store_whatsapp_number": f"+{MERCHANT_WA}",
            },
        )

        ev = _api(
            page,
            "/api/cart-event",
            method="POST",
            body={
                "event": "cart_state_sync",
                "reason": "add",
                "store": store_slug,
                "session_id": session_id,
                "cart_id": cart_id,
                "cart_total": cart_total,
                "items_count": 1,
                "cart": [{"price": cart_total, "quantity": 1}],
            },
        )
        report["cart_event"] = ev
        time.sleep(35)

        truth = _api(
            page,
            f"/dev/vip-merchant-alert-operational-truth?cart_id={cart_id}&store_slug={store_slug}",
        )
        report["operational_truth"] = truth

        vip_rows = _api(page, f"/api/dashboard/vip-carts?store={store_slug}")
        report["vip_carts"] = {
            "count": len(vip_rows.get("carts") or vip_rows.get("rows") or []),
            "found": any(
                str(r.get("cart_id") or "") == cart_id
                for r in (vip_rows.get("carts") or vip_rows.get("rows") or [])
                if isinstance(r, dict)
            ),
        }

        normal = _api(page, f"/api/dashboard/normal-carts?store={store_slug}")
        normal_rows = normal.get("carts") or normal.get("rows") or []
        leaked = next(
            (r for r in normal_rows if isinstance(r, dict) and str(r.get("cart_id") or "") == cart_id),
            None,
        )
        report["normal_carts_leak"] = leaked is not None
        if leaked:
            report["leaked_row_lifecycle"] = {
                "customer_lifecycle_state": leaked.get("customer_lifecycle_state"),
                "merchant_followup_clarity_ar": leaked.get("merchant_followup_clarity_ar"),
                "sent_count": leaked.get("sent_count"),
            }

        report["closure_checks"] = {
            "vip_row_visible": report["vip_carts"].get("found"),
            "alert_log_exists": bool((truth.get("merchant_alert_log_rows") or [])),
            "destination_matches": str(truth.get("normalized_destination_phone") or "").endswith(
                MERCHANT_WA[-9:]
            ),
            "delivered_to_device": truth.get("delivered_to_device"),
            "latest_status_not_sent_real": (truth.get("latest_alert_status") or "") != "sent_real",
            "no_normal_carts_leak": not report["normal_carts_leak"],
            "no_followup_clarity_on_leak": not bool(
                (leaked or {}).get("merchant_followup_clarity_ar")
            ),
        }
        report["cart_id"] = cart_id
        report["store_slug"] = store_slug
        report["provider_sid"] = truth.get("latest_provider_message_sid")

        page.screenshot(path=str(OUT / "vip_dashboard_after_fresh_cart.png"), full_page=True)
        browser.close()

    OUT.joinpath("report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    checks = report.get("closure_checks") or {}
    ok = all(
        checks.get(k)
        for k in (
            "vip_row_visible",
            "alert_log_exists",
            "latest_status_not_sent_real",
            "no_normal_carts_leak",
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not checks.get("delivered_to_device"):
        print(
            "\nMANUAL STEP REQUIRED: Capture WhatsApp screenshot on merchant device "
            f"({MERCHANT_WA}) and save to",
            OUT / "merchant_whatsapp_alert_screenshot.png",
        )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
