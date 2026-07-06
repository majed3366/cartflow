# -*- coding: utf-8 -*-
"""Capture Carts Workspace Experience V1 before/after fixture screenshots."""
from __future__ import annotations

import json
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_carts_workspace_v1_out"
FIXTURE = Path(__file__).resolve().parent / "_carts_workspace_v1_fixture.html"


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
    url = f"http://127.0.0.1:{port}/scripts/_carts_workspace_v1_fixture.html"
    meta = {"git": _git_short(), "fixture": FIXTURE.name}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(400)

        page.locator("#fixture-before").screenshot(
            path=str(OUT / "01_carts_workspace_before.png")
        )
        page.locator("#fixture-after").screenshot(
            path=str(OUT / "02_carts_workspace_after.png")
        )
        page.screenshot(path=str(OUT / "03_carts_workspace_comparison.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(300)
        page.locator("#fixture-after").screenshot(
            path=str(OUT / "04_carts_workspace_after_mobile.png")
        )
        browser.close()

    server.shutdown()
    (OUT / "capture_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved screenshots to {OUT}")


if __name__ == "__main__":
    main()
