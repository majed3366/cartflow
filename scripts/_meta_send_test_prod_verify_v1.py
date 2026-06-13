# -*- coding: utf-8 -*-
"""Production verify: Meta hello_world admin test send + screenshot."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
OUT_DIR = Path(__file__).resolve().parent / "_meta_send_test_prod_v1_out"


def main() -> int:
    password = (os.environ.get("CARTFLOW_ADMIN_PASSWORD") or "").strip()
    to = (os.environ.get("META_TEST_RECIPIENT_TO") or "").strip()
    if not password:
        print("CARTFLOW_ADMIN_PASSWORD required", file=sys.stderr)
        return 1
    if not to:
        print("META_TEST_RECIPIENT_TO required (Meta test recipient E.164)", file=sys.stderr)
        return 1

    from playwright.sync_api import sync_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "audit": "meta_send_test_prod_v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "to": to,
        "meta_status_before": None,
        "send_api": None,
        "ui": {},
        "pass": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"{BASE}/admin/operations/login", timeout=120_000)
        page.locator('input[name="password"]').fill(password)
        page.locator("form").first.evaluate("f => f.submit()")
        page.wait_for_timeout(2500)

        meta_status = page.evaluate(
            """async () => {
              const r = await fetch('/admin/api/whatsapp/meta-status', {credentials: 'same-origin'});
              return {status: r.status, body: await r.json()};
            }"""
        )
        report["meta_status_before"] = meta_status

        page.goto(f"{BASE}/admin/whatsapp", timeout=120_000)
        page.wait_for_timeout(3000)
        page.locator("#awm-meta-send-to").fill(to)
        page.locator("#awm-meta-send-btn").click()
        page.wait_for_timeout(12000)

        send_api = page.evaluate(
            """async (to) => {
              const r = await fetch('/admin/api/whatsapp/meta-send-test', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({to: to}),
              });
              const body = await r.json();
              return {status: r.status, body: body};
            }""",
            to,
        )
        report["send_api"] = send_api
        body = (send_api or {}).get("body") or {}

        report["ui"] = {
            "result_text": page.locator("#awm-meta-send-result").inner_text(),
            "message_id_text": page.locator("#awm-meta-send-message-id").inner_text(),
            "status_text": page.locator("#awm-meta-send-status").inner_text(),
            "connected_text": page.locator("#awm-meta-connected").inner_text(),
        }

        screenshot_path = OUT_DIR / "admin_whatsapp_meta_test_send_success.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        report["screenshot"] = str(screenshot_path)

        text_blob = json.dumps(report)
        report["checks"] = {
            "meta_connected": (meta_status or {}).get("body", {}).get("connected") is True,
            "send_ok": body.get("ok") is True,
            "message_id_present": bool(body.get("message_id")),
            "no_token_leak": password not in text_blob and "access_token" not in body,
            "ui_shows_success": "نجح" in report["ui"].get("result_text", ""),
        }
        report["pass"] = all(report["checks"].values())
        report["delivery_note"] = (
            "Meta accepted outbound send (message_id returned). "
            "Final device delivery is confirmed on the test recipient handset "
            "or via future webhook status events (not verified in this script)."
        )
        browser.close()

    out_json = OUT_DIR / "verify_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "message_id": (body or {}).get("message_id"), "out": str(out_json)}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
