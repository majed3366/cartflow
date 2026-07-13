# -*- coding: utf-8 -*-
"""Capture Wireframe Contract V1 screenshots (desktop + mobile + empty)."""
from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_cart_workspace_wireframe_contract_v1_out"
FIXTURE = "/scripts/_cart_workspace_wireframe_contract_v1_fixture.html"
REVIEW = (
    ROOT
    / "docs"
    / "architecture"
    / "cart_workspace_wireframe_contract_v1_review"
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
        desk = OUT / "01_desktop.png"
        page.screenshot(path=str(desk), full_page=True)
        (REVIEW / "01_desktop.png").write_bytes(desk.read_bytes())

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle", timeout=60000)
        mobile.wait_for_timeout(350)
        mpath = OUT / "02_mobile.png"
        mobile.screenshot(path=str(mpath), full_page=True)
        (REVIEW / "02_mobile.png").write_bytes(mpath.read_bytes())

        empty = browser.new_page(viewport={"width": 1280, "height": 900})
        empty.goto(url, wait_until="networkidle", timeout=60000)
        empty.evaluate(
            """() => {
              try {
                sessionStorage.removeItem('cw_following_vip_v1:fixture-wireframe-v1');
              } catch (e) {}
              const quiet = {
                projection_version: 3,
                projection_fingerprint: 'fixture-quiet',
                quiet: true,
                zone_a: [],
                zone_b: [],
                zone_c: { visible: true, active_recovery_indicator: true, summary: 'quiet' },
                zone_d: { completed_count: 6, achievement_amount_ar: '852 ريال' },
                zone_e: null
              };
              window.CartWorkspaceRenderControllerV1.resetForTests();
              window.CartWorkspaceRenderControllerV1.applyProjection(
                document.getElementById('cw-merchant-host'),
                quiet
              );
            }"""
        )
        empty.wait_for_timeout(250)
        epath = OUT / "03_empty.png"
        empty.screenshot(path=str(epath), full_page=True)
        (REVIEW / "03_empty.png").write_bytes(epath.read_bytes())
        browser.close()

    server.shutdown()
    meta = {
        "url": url,
        "shots": ["01_desktop.png", "02_mobile.png", "03_empty.png"],
    }
    (OUT / "capture_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (REVIEW / "capture_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
