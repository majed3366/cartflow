# -*- coding: utf-8 -*-
"""Capture Daily Brief IA Redesign V1 fixture screenshots."""
from __future__ import annotations

import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "_daily_brief_ia_redesign_v1_out"


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, cwd=ROOT
        ).strip()
    except Exception:
        return "unknown"


def _serve(root: Path) -> ThreadingHTTPServer:
    handler = type("Handler", (SimpleHTTPRequestHandler,), {"directory": str(root)})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    server = _serve(ROOT)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/scripts/_daily_brief_ia_redesign_v1_fixture.html"

    with sync_playwright() as p:
        browser = p.chromium.launch()

        desktop = browser.new_page(viewport={"width": 900, "height": 720})
        desktop.goto(url, wait_until="networkidle", timeout=60000)
        desktop.locator("#ma-daily-brief-body-a").screenshot(
            path=str(OUT / "01_ia_desktop_hero_grid.png")
        )

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle", timeout=60000)
        mobile.locator("#ma-daily-brief-body-b").screenshot(
            path=str(OUT / "02_ia_mobile_stack.png")
        )
        mobile.locator("#ma-daily-brief-body-c").screenshot(
            path=str(OUT / "03_ia_empty_calm_mobile.png")
        )

        browser.close()

    server.shutdown()
    (OUT / "capture_meta.json").write_text(
        __import__("json").dumps({"git": _git_short()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved screenshots to {OUT}")


if __name__ == "__main__":
    main()
