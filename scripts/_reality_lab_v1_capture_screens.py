# -*- coding: utf-8 -*-
"""Capture desktop/mobile dashboard screenshots for Reality Lab V1 using existing lab DB."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "architecture" / "reality_validation_lab_v1_small"
EVIDENCE = OUT / "lab_evidence.json"
PORT = 8777


def main() -> int:
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    db_path = data.get("db_path")
    if not db_path or not Path(db_path).exists():
        print("lab db missing", db_path)
        return 1
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")

    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from fastapi.testclient import TestClient
    from main import app
    from services.merchant_auth_http import merchant_cookie_name

    client = TestClient(app)
    email = f"lab-shot-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/signup",
        data={
            "store_name": "متجر واقع صغير",
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=False,
    )
    cookies = dict(r.cookies)
    cname = merchant_cookie_name()

    import uvicorn
    from playwright.sync_api import sync_playwright

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(2.5)
    base = f"http://127.0.0.1:{PORT}"
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for filename, viewport, hash_path in (
            ("01_desktop_home.png", {"width": 1440, "height": 900}, "#home"),
            ("02_mobile_home.png", {"width": 390, "height": 844}, "#home"),
            ("03_desktop_carts.png", {"width": 1440, "height": 900}, "#carts"),
            ("04_mobile_carts.png", {"width": 390, "height": 844}, "#carts"),
        ):
            ctx = browser.new_context(viewport=viewport)
            if cookies.get(cname):
                ctx.add_cookies(
                    [{"name": cname, "value": cookies[cname], "url": base}]
                )
            page = ctx.new_page()
            page.goto(f"{base}/dashboard{hash_path}", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)
            path = OUT / filename
            page.screenshot(path=str(path), full_page=True)
            shots.append(filename)
            ctx.close()
        browser.close()
    server.should_exit = True
    meta = {"shots": shots, "base": base, "email": email}
    (OUT / "screenshot_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    data["screenshots"] = shots
    EVIDENCE.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
