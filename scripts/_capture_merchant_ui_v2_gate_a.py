# -*- coding: utf-8 -*-
"""Gate A captures — Merchant UI V2 vertical slice (Living Store)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = ""  # filled after deploy
ASSETS = (
    "/static/merchant_ui_v2_ds.css",
    "/static/merchant_ui_v2_frame.css",
    "/static/merchant_ui_v2_home.css",
    "/static/merchant_ui_v2_workspace.css",
    "/static/merchant_ui_v2_app.js",
    "/static/merchant_ui_v2_home.js",
    "/static/merchant_ui_v2_workspace.js",
)


def http_status(url: str) -> int:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return int(resp.status)
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        return int(code) if code else -1


def wait_for_deploy(timeout_s: int = 480) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        req = urllib.request.Request(f"{BASE}/", method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
            last = {"sha": sha, "status": resp.status}
            if not EXPECTED_SHA_PREFIX or sha.startswith(EXPECTED_SHA_PREFIX):
                # Also require V2 asset present
                if http_status(BASE + ASSETS[0]) == 200:
                    return {"ok": True, **last}
        time.sleep(12)
    return {"ok": False, **last}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    probe: dict = {
        "deploy": deploy,
        "assets": {a: http_status(BASE + a) for a in ASSETS},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return await r.json().catch(() => ({}));
            }"""
        )
        boot.close()
        if not (session.get("cookie_name") and session.get("cookie_value")):
            raise SystemExit(f"FAIL_NO_SESSION: {session}")

        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "url": BASE,
            "httpOnly": True,
            "sameSite": "Lax",
        }

        def probe_page(page):
            return page.evaluate(
                """() => {
                  const links = [...document.querySelectorAll('link[rel="stylesheet"]')]
                    .map(l => l.getAttribute('href') || '');
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    appbar: !!document.querySelector('.cf2-appbar'),
                    ctx: !!document.querySelector('.cf2-ctx'),
                    stage: !!document.querySelector('.cf2-stage'),
                    home: !!document.querySelector('.cf2-home, #cf2-home-root .cf2-home__dominant'),
                    workspace: !!document.querySelector('.cf2-ws, .cf2-reason'),
                    drawerOpen: !!document.querySelector('.cf2-drawer.is-open'),
                    legacyFrameLinked: links.some(h => h.includes('merchant_frame_v1.css')),
                    legacyPeLinked: links.some(h => h.includes('merchant_pe_v2.css')),
                    v2CssLinked: links.some(h => h.includes('merchant_ui_v2_frame.css')),
                  };
                }"""
            )

        # Desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(4500)
        probe["desktop_home"] = probe_page(page)
        page.screenshot(path=str(OUT / "desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        page.wait_for_timeout(4500)
        probe["desktop_workspace"] = probe_page(page)
        page.screenshot(path=str(OUT / "desktop_workspace.png"), full_page=False)
        ctx.close()

        # Mobile
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
        )
        mctx.add_cookies([cookie])
        mpage = mctx.new_page()
        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile_home"] = probe_page(mpage)
        mpage.screenshot(path=str(OUT / "mobile_home.png"), full_page=False)

        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile_workspace"] = probe_page(mpage)
        mpage.screenshot(path=str(OUT / "mobile_workspace.png"), full_page=False)

        # Mobile drawer open
        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(600)
        probe["mobile_drawer"] = probe_page(mpage)
        mpage.screenshot(path=str(OUT / "mobile_drawer_open.png"), full_page=False)
        mctx.close()
        browser.close()

    (OUT / "gate_a_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))

    dh = probe.get("desktop_home") or {}
    dw = probe.get("desktop_workspace") or {}
    md = probe.get("mobile_drawer") or {}
    checks = [
        bool(probe.get("deploy", {}).get("ok")),
        dh.get("ui") == "v2",
        dh.get("appbar") and dh.get("stage"),
        dh.get("v2CssLinked"),
        not dh.get("legacyFrameLinked"),
        not dh.get("legacyPeLinked"),
        dh.get("home"),
        dw.get("workspace"),
        md.get("drawerOpen"),
    ]
    return 0 if all(checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
