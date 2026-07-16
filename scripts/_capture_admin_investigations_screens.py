# -*- coding: utf-8 -*-
"""Capture Admin Investigations dashboard screenshots (desktop + mobile)."""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture" / "reality_validation_checkpoint_v2" / "admin_investigations"
sys.path.insert(0, str(ROOT))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CARTFLOW_ADMIN_PASSWORD", "checkpoint-admin-capture-pass")
    os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-for-admin-cookie-hmac-capture")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")

    from fastapi.testclient import TestClient
    from playwright.sync_api import sync_playwright

    import uvicorn

    from main import app
    from services.cartflow_admin_http_auth import (
        admin_cookie_name,
        issue_admin_session_cookie_value,
    )

    client = TestClient(app)
    r = client.post(
        "/admin/operations/login",
        data={
            "password": os.environ["CARTFLOW_ADMIN_PASSWORD"],
            "next": "/admin/investigations",
        },
        follow_redirects=False,
    )
    assert r.status_code in (303, 302), r.text[:300]
    cookie_val = r.cookies.get(admin_cookie_name()) or issue_admin_session_cookie_value()

    config = uvicorn.Config(app, host="127.0.0.1", port=8778, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(80):
        time.sleep(0.25)
        if getattr(server, "started", False):
            break

    base = "http://127.0.0.1:8778"
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, vp, name in (
            ("desktop", {"width": 1440, "height": 900}, "admin_investigations_desktop.png"),
            ("mobile", {"width": 390, "height": 844}, "admin_investigations_mobile.png"),
            ("desktop_detail", {"width": 1440, "height": 900}, "admin_inv009_detail_desktop.png"),
        ):
            ctx = browser.new_context(viewport=vp)
            ctx.add_cookies(
                [
                    {
                        "name": admin_cookie_name(),
                        "value": cookie_val,
                        "url": base,
                    }
                ]
            )
            page = ctx.new_page()
            url = (
                f"{base}/admin/investigations/INV-009"
                if "detail" in label
                else f"{base}/admin/investigations"
            )
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(800)
            path = OUT / name
            page.screenshot(path=str(path), full_page=True)
            shots.append(name)
            ctx.close()
        browser.close()
    server.should_exit = True
    print({"ok": True, "shots": shots, "out": str(OUT)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
