# -*- coding: utf-8 -*-
"""Capture Visual Rebuild V1 screenshots for Product Review (local fixture)."""
from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_cart_workspace_visual_rebuild_v1_out"
FIXTURE = "/scripts/_cart_workspace_visual_rebuild_v1_fixture.html"


def _serve() -> ThreadingHTTPServer:
    handler = type(
        "H",
        (SimpleHTTPRequestHandler,),
        {"directory": str(ROOT)},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    server = _serve()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{FIXTURE}"
    meta = {"url": url, "shots": []}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "01_desktop_console.png"), full_page=True)
        meta["shots"].append("01_desktop_console.png")

        # Expand one details to prove explanations are not default
        page.locator("details.cw-tile__details").first.click()
        page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "02_desktop_details_expanded.png"), full_page=True)
        meta["shots"].append("02_desktop_details_expanded.png")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle", timeout=60000)
        mobile.wait_for_timeout(400)
        mobile.screenshot(path=str(OUT / "03_mobile_console.png"), full_page=True)
        meta["shots"].append("03_mobile_console.png")
        browser.close()

    server.shutdown()
    (OUT / "capture_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, indent=2))
    print(f"OUT={OUT}")


if __name__ == "__main__":
    main()
