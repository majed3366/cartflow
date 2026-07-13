# -*- coding: utf-8 -*-
"""Capture Visual Rebuild V3 production-candidate screenshots."""
from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_cart_workspace_visual_rebuild_v3_out"
FIXTURE = "/scripts/_cart_workspace_visual_rebuild_v3_fixture.html"
REVIEW = (
    ROOT
    / "docs"
    / "architecture"
    / "cart_workspace_visual_rebuild_v3_review"
)


def _serve() -> ThreadingHTTPServer:
    handler = type("H", (SimpleHTTPRequestHandler,), {"directory": str(ROOT)})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    server = _serve()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{FIXTURE}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(350)
        for name in ("01_desktop.png",):
            path = OUT / name
            page.screenshot(path=str(path), full_page=True)
            (REVIEW / name).write_bytes(path.read_bytes())

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle", timeout=60000)
        mobile.wait_for_timeout(350)
        mpath = OUT / "02_mobile.png"
        mobile.screenshot(path=str(mpath), full_page=True)
        (REVIEW / "02_mobile.png").write_bytes(mpath.read_bytes())
        browser.close()

    server.shutdown()
    meta = {"url": url, "shots": ["01_desktop.png", "02_mobile.png"]}
    (OUT / "capture_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (REVIEW / "capture_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
