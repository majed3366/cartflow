# -*- coding: utf-8 -*-
"""Task 2 audit: dashboard price template → runtime schedule → message (read-only)."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_recovery_template_truth_audit_out"
TRUTH_MSG = "PRICE_TEMPLATE_TRUTH_TEST_60_MIN"
TRUTH_DELAY = 60
TRUTH_UNIT = "minute"


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
    email = f"cf.tpl.truth.{uid}@smartreplyai.net"
    password = f"CfTplTruth!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"TplTruth {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def _api_json(page, path: str, *, method: str = "GET", body: dict | None = None) -> Any:
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
          try { j = JSON.parse(t); } catch (e) { j = { parse_error: true, raw: t.slice(0, 800), status: r.status }; }
          j._http_status = r.status;
          return j;
        }""",
        {"path": path, "method": method, "body": body},
    )


def _h(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def _save_price_template(page) -> dict[str, Any]:
    payload = {
        "reason_templates": {
            "price": {
                "enabled": True,
                "message": TRUTH_MSG,
                "message_count": 1,
                "messages": [
                    {"delay": TRUTH_DELAY, "unit": TRUTH_UNIT, "text": TRUTH_MSG},
                ],
            }
        },
        "selected_stage": 0,
    }
    post = _api_json(page, "/api/dashboard/trigger-templates", method="POST", body=payload)
    get_ = _api_json(page, "/api/dashboard/trigger-templates")
    return {"post": post, "get": get_}


def _create_normal_cart_price_api(page, store_slug: str) -> dict[str, Any]:
    uid = uuid.uuid4().hex[:12]
    session_id = f"s_tpl_truth_{uid}"
    cart_id = f"cf_cart_{uuid.uuid4()}"
    recovery_key = f"{store_slug}:{cart_id}"
    flow = page.evaluate(
        """async (args) => {
          const out = { steps: [] };
          const push = (name, r) => {
            out.steps.push({ name, status: r._http_status, body: r });
          };
          const cartEv = await fetch('/api/cart-event', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              event: 'cart_state_sync',
              reason: 'add',
              store: args.store_slug,
              session_id: args.session_id,
              cart_id: args.cart_id,
              cart_total: 149.0,
              items_count: 1,
            }),
          }).then(async (r) => {
            const t = await r.text();
            let j = null; try { j = JSON.parse(t); } catch (e) { j = { raw: t.slice(0, 400) }; }
            j._http_status = r.status; return j;
          });
          push('cart_state_sync', cartEv);
          const abandon = await fetch('/api/cart-event', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              event: 'cart_abandoned',
              store: args.store_slug,
              session_id: args.session_id,
              cart_id: args.cart_id,
              cart_total: 149.0,
              items_count: 1,
              cart: [{ name: 'TplTruth Item', price: 149.0, quantity: 1 }],
            }),
          }).then(async (r) => {
            const t = await r.text();
            let j = null; try { j = JSON.parse(t); } catch (e) { j = { raw: t.slice(0, 400) }; }
            j._http_status = r.status; return j;
          });
          push('cart_abandoned', abandon);
          const reason = await fetch('/api/cartflow/reason', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              store_slug: args.store_slug,
              session_id: args.session_id,
              reason: 'price',
              sub_category: 'price_discount_request',
              customer_phone: '0598877661',
              cart_id: args.cart_id,
            }),
          }).then(async (r) => {
            const t = await r.text();
            let j = null; try { j = JSON.parse(t); } catch (e) { j = { raw: t.slice(0, 400) }; }
            j._http_status = r.status; return j;
          });
          push('cartflow_reason', reason);
          return {
            session_id: args.session_id,
            cart_id: args.cart_id,
            recovery_key: args.recovery_key,
            steps: out.steps,
          };
        }""",
        {
            "store_slug": store_slug,
            "session_id": session_id,
            "cart_id": cart_id,
            "recovery_key": recovery_key,
        },
    )
    return flow or {}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "truth_marker": TRUTH_MSG,
        "expected_delay_seconds": TRUTH_DELAY * 60,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        _auth(page, report)

        page.goto(f"{BASE}/dashboard#messages", timeout=120000)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "01_before_template_save.png"), full_page=True)

        tpl_save = _save_price_template(page)
        report["dashboard_template_save"] = tpl_save

        store_slug = ""
        if isinstance(tpl_save.get("get"), dict):
            store_slug = str(tpl_save["get"].get("store_slug") or tpl_save["get"].get("zid_store_id") or "").strip()
        if not store_slug and isinstance(tpl_save.get("post"), dict):
            store_slug = str(tpl_save["post"].get("store_slug") or "").strip()
        report["store_slug"] = store_slug

        template_truth = _api_json(
            page,
            f"/dev/template-truth?store_slug={store_slug}&reason=price",
        )
        store_debug = _api_json(
            page,
            f"/dev/store-template-debug?store_slug={store_slug}&reason=price",
        )
        report["dev_template_truth"] = template_truth
        report["dev_store_template_debug"] = store_debug

        page.screenshot(path=str(OUT / "02_after_template_save.png"), full_page=True)

        cart_ids = _create_normal_cart_price_api(page, store_slug)
        report["cart_flow"] = cart_ids
        cart_id = str(cart_ids.get("cart_id") or "").strip()
        session_id = str(cart_ids.get("session_id") or "").strip()
        recovery_key = str(cart_ids.get("recovery_key") or "").strip()
        report["recovery_key"] = recovery_key

        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "03_after_cart_price_phone.png"), full_page=True)

        op_truth: dict[str, Any] = {}
        if recovery_key and session_id:
            for _poll in range(24):
                op_truth = _api_json(
                    page,
                    f"/dev/recovery-operational-truth?recovery_key={store_slug}:{session_id}",
                )
                if op_truth.get("reason_tag") and op_truth.get("schedule_rows"):
                    break
                page.wait_for_timeout(500)
            report["dev_recovery_operational_truth"] = op_truth
            report["dev_recovery_operational_truth_cart_key"] = _api_json(
                page,
                f"/dev/recovery-operational-truth?recovery_key={recovery_key}",
            )
            report["identity_trace"] = _api_json(
                page,
                f"/dev/test-widget-identity-trace?store_slug={store_slug}&session_id={session_id}&cart_id={cart_id}",
            )

        page.goto(f"{BASE}/dashboard#carts", timeout=120000)
        page.wait_for_timeout(8000)
        page.screenshot(path=str(OUT / "04_dashboard_carts_row.png"), full_page=True)

        normal_carts = _api_json(page, "/api/dashboard/normal-carts")
        report["api_normal_carts"] = {
            "ok": normal_carts.get("ok"),
            "row_count": len(normal_carts.get("merchant_carts_page_rows") or []),
        }
        dash_row = None
        for row in normal_carts.get("merchant_carts_page_rows") or []:
            rk = str(row.get("recovery_key") or "").strip()
            cid = str(row.get("cart_id") or "").strip()
            if rk == recovery_key or (cart_id and cid == cart_id):
                dash_row = row
                break
        report["dashboard_row"] = dash_row

        logs = _api_json(
            page,
            f"/api/dashboard/messages?limit=20" if False else "/api/dashboard/messages",
        )
        report["api_messages"] = logs

        # Build divergence summary
        price_entry = {}
        if isinstance(tpl_save.get("get"), dict):
            rows = tpl_save["get"].get("reason_rows") or []
            for row in rows:
                if row.get("key") == "price":
                    price_entry = row
                    break
        saved_msg = str(price_entry.get("message") or "").strip()
        msgs = price_entry.get("messages") or []
        saved_delay = None
        saved_unit = None
        if msgs and isinstance(msgs[0], dict):
            saved_delay = msgs[0].get("delay")
            saved_unit = msgs[0].get("unit")
            if not saved_msg:
                saved_msg = str(msgs[0].get("text") or "").strip()

        timing = (store_debug or {}).get("runtime_timing_resolution") or {}
        runtime_sec = timing.get("effective_delay_seconds")
        runtime_source = timing.get("source")

        schedule_sec = None
        schedule_due = None
        op = report.get("dev_recovery_operational_truth") or {}
        sched_rows = op.get("schedule_rows") or []
        if sched_rows:
            schedule_due = sched_rows[0].get("due_at")
        created_at = op.get("schedule_rows", [{}])[0].get("created_at") if sched_rows else None
        if schedule_due and created_at:
            try:
                due = datetime.fromisoformat(schedule_due.replace("Z", "+00:00"))
                cre = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                schedule_sec = (due - cre).total_seconds()
            except Exception:  # noqa: BLE001
                schedule_sec = None

        msg_logs = []
        for m in (logs.get("merchant_message_rows") or logs.get("rows") or []):
            if isinstance(m, dict):
                body = str(m.get("full_message_ar") or m.get("message") or "")
                if recovery_key and recovery_key.split(":")[-1] in str(m.get("recovery_key") or ""):
                    msg_logs.append(m)
                elif TRUTH_MSG in body:
                    msg_logs.append(m)

        report["truth_chain_summary"] = {
            "saved_template": {
                "table": "Store.reason_templates_json",
                "message": saved_msg,
                "delay": saved_delay,
                "unit": saved_unit,
                "message_hash": _h(saved_msg),
            },
            "runtime_timing_resolver": {
                "effective_delay_seconds": runtime_sec,
                "source": runtime_source,
                "template_delay_value": timing.get("template_delay_value"),
                "template_delay_unit": timing.get("template_delay_unit"),
            },
            "recovery_schedule": {
                "rows": sched_rows,
                "delay_seconds_from_due": schedule_sec,
                "next_attempt_due_at": op.get("next_attempt_due_at"),
            },
            "reason_tag": op.get("reason_tag"),
            "template_diagnosis": op.get("template_diagnosis"),
            "dashboard_row_delay_fields": {
                "merchant_followup_next_line_ar": (dash_row or {}).get("merchant_followup_next_line_ar"),
                "merchant_reason_chip_label_ar": (dash_row or {}).get("merchant_reason_chip_label_ar"),
                "reason_tag": (dash_row or {}).get("reason_tag"),
            },
            "message_logs_matching": msg_logs,
            "divergence": {
                "delay_saved_vs_runtime_sec": (
                    None
                    if runtime_sec is None
                    else float(runtime_sec) - float(TRUTH_DELAY * 60)
                ),
                "delay_saved_vs_schedule_sec": (
                    None
                    if schedule_sec is None
                    else float(schedule_sec) - float(TRUTH_DELAY * 60)
                ),
                "message_saved_hash": _h(saved_msg),
                "runtime_timing_source": runtime_source,
            },
        }

        browser.close()

    out_path = OUT / "recovery_template_truth_audit.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        print(json.dumps(report.get("truth_chain_summary"), ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print("truth_chain_summary written to json (console encoding skipped)")
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
