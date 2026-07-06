# -*- coding: utf-8 -*-
"""Capture Product Excellence Visual Rebuild V1 before/after screenshots."""
from __future__ import annotations

import json
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PROTO = Path(__file__).resolve().parent / "_product_excellence_visual_rebuild_v1"
OUT = Path(__file__).resolve().parent / "_product_excellence_visual_rebuild_v1_out"


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, cwd=ROOT
        ).strip()
    except Exception:
        return "unknown"


def _serve(root: Path) -> ThreadingHTTPServer:
    handler = type(
        "Handler",
        (SimpleHTTPRequestHandler,),
        {"directory": str(root)},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    server = _serve(ROOT)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}/scripts/_product_excellence_visual_rebuild_v1"

    shots = [
        ("01_home_before.png", f"{base}/before_home.html", {"width": 420, "height": 900}),
        ("02_home_after.png", f"{base}/home_prototype.html", {"width": 420, "height": 900}),
        ("03_carts_before.png", f"{base}/before_carts.html", {"width": 900, "height": 700}),
        ("04_carts_after.png", f"{base}/carts_prototype.html", {"width": 1100, "height": 800}),
        ("05_cart_detail_after.png", f"{base}/cart_detail_prototype.html", {"width": 420, "height": 900}),
        ("06_comparison_index.png", f"{base}/index.html", {"width": 1200, "height": 1400}),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, url, vp in shots:
            page = browser.new_page(viewport=vp)
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / name), full_page=True)
            page.close()
        browser.close()

    server.shutdown()
    meta = {"git": _git_short(), "prototype_dir": PROTO.name}
    (OUT / "capture_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved screenshots to {OUT}")


if __name__ == "__main__":
    main()
