# -*- coding: utf-8 -*-
"""Production audit: VIP merchant alert delivery + lifecycle UI contradiction."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_merchant_alert_lifecycle_audit_out"
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
    email = f"cf.vip.lc.{uid}@smartreplyai.net"
    password = f"CfVipLc!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipLc {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def _find_cart_row(rows: list, cart_id: str) -> dict | None:
    cid = (cart_id or "").strip()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("cart_id") or "").strip() == cid:
            return row
        if str(row.get("merchant_case_row_id") or "") and cid in str(row.get("recovery_key") or ""):
            return row
    return None


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

        vip_save = _api(
            page,
            "/api/recovery-settings",
            method="POST",
            body={
                "merchant_settings_scope": "vip",
                "vip_enabled": True,
                "vip_cart_threshold": 500,
                "vip_notify_enabled": True,
            },
        )
        wa_save = _api(
            page,
            "/api/recovery-settings",
            method="POST",
            body={
                "store_whatsapp_number": MERCHANT_WA,
                "whatsapp_recovery_enabled": True,
                "whatsapp_provider_mode": "production",
            },
        )
        settings = {
            "vip_save": vip_save,
            "wa_save": wa_save,
            "vip": _api(page, "/api/recovery-settings?scope=vip"),
            "wa": _api(page, "/api/recovery-settings"),
        }
        report["settings"] = settings
        store_slug = str(
            (settings.get("wa") or {}).get("zid_store_id")
            or (settings.get("wa") or {}).get("store_slug")
            or ""
        ).strip()

        uid = uuid.uuid4().hex[:12]
        session_id = f"s_vip_lc_{uid}"
        cart_id = f"cf_cart_{uid}"
        recovery_key = f"{store_slug}:{cart_id}"

        cart_sync = _api(
            page,
            "/api/cart-event",
            method="POST",
            body={
                "event": "cart_state_sync",
                "reason": "add",
                "store": store_slug,
                "session_id": session_id,
                "cart_id": cart_id,
                "cart_total": 1299.0,
                "items_count": 1,
                "cart": [{"price": 1299.0, "quantity": 1}],
            },
        )
        reason_post = _api(
            page,
            "/api/cartflow/reason",
            method="POST",
            body={
                "store": store_slug,
                "session_id": session_id,
                "cart_id": cart_id,
                "reason": "price",
                "customer_phone": "966501234567",
            },
        )
        report["cart_flow"] = {
            "cart_state_sync": cart_sync,
            "cartflow_reason": reason_post,
            "cart_id": cart_id,
            "session_id": session_id,
            "recovery_key": recovery_key,
            "store_slug": store_slug,
        }

        page.wait_for_timeout(4000)

        alert_truth = _api(
            page,
            f"/dev/vip-merchant-alert-operational-truth?cart_id={cart_id}&store_slug={store_slug}",
        )
        recovery_truth = _api(
            page,
            f"/dev/recovery-operational-truth?recovery_key={recovery_key}",
        )
        lifecycle_truth = _api(
            page,
            f"/dev/lifecycle-truth-check?recovery_key={recovery_key}",
        )
        normal_carts = _api(page, f"/api/dashboard/normal-carts?_ts={int(datetime.now().timestamp())}")
        vip_carts = _api(page, f"/api/dashboard/vip-carts?_ts={int(datetime.now().timestamp())}")

        report["dev_vip_merchant_alert_operational_truth"] = alert_truth
        report["dev_recovery_operational_truth"] = recovery_truth
        report["dev_lifecycle_truth_check"] = lifecycle_truth
        report["normal_carts_row"] = _find_cart_row(
            (normal_carts.get("merchant_table_rows") or normal_carts.get("merchant_carts_page_rows") or []),
            cart_id,
        )
        report["normal_carts_api_meta"] = {
            "ok": normal_carts.get("ok"),
            "row_count": len(normal_carts.get("merchant_table_rows") or []),
            "page_row_count": len(normal_carts.get("merchant_carts_page_rows") or []),
        }
        report["vip_carts_api"] = {
            "ok": vip_carts.get("ok"),
            "page_rows": vip_carts.get("merchant_vip_page_rows") or [],
            "row_count": len(vip_carts.get("merchant_vip_page_rows") or []),
        }

        if report["normal_carts_row"]:
            nc = report["normal_carts_row"]
            report["lifecycle_contradiction_evidence"] = {
                "customer_lifecycle_state": nc.get("customer_lifecycle_state"),
                "customer_lifecycle_label_ar": nc.get("customer_lifecycle_label_ar"),
                "merchant_followup_progress_ar": nc.get("merchant_followup_progress_ar"),
                "merchant_followup_sequence_line_ar": nc.get("merchant_followup_sequence_line_ar"),
                "merchant_followup_next_line_ar": nc.get("merchant_followup_next_line_ar"),
                "merchant_followup_sent_count": nc.get("merchant_followup_sent_count"),
                "merchant_followup_configured_count": nc.get("merchant_followup_configured_count"),
                "merchant_status_label_ar": nc.get("merchant_status_label_ar"),
                "is_vip_cart": nc.get("is_vip_cart"),
                "operational_lane": nc.get("operational_lane"),
                "vip_cart_threshold": nc.get("vip_cart_threshold"),
            }

        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "01_vip_dashboard.png"), full_page=True)
        page.goto(f"{BASE}/dashboard#carts", timeout=120000)
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "02_normal_carts_intervention.png"), full_page=True)

        browser.close()

    out_path = OUT / "vip_merchant_alert_lifecycle_audit.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("wrote", out_path)
    try:
        print(json.dumps(report.get("lifecycle_contradiction_evidence") or report.get("dev_vip_merchant_alert_operational_truth"), ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
