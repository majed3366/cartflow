# -*- coding: utf-8 -*-
"""Living Store + language board captures — Visual Language Maturity V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_visual_language_maturity_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "41777ae"


def wait_for_deploy(timeout_s: int = 480) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        req = urllib.request.Request(f"{BASE}/", method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
            last = {"sha": sha, "status": resp.status}
            if not EXPECTED_SHA_PREFIX or sha.startswith(EXPECTED_SHA_PREFIX):
                return {"ok": True, **last}
        time.sleep(12)
    return {"ok": False, **last}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    probe: dict = {"deploy": deploy}

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
        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "url": BASE,
            "httpOnly": True,
            "sameSite": "Lax",
        }

        # Board (static)
        board = browser.new_page(viewport={"width": 1440, "height": 1100}, locale="ar-SA")
        board.goto(f"{BASE}/static/merchant_ui_v2_language_board.html", timeout=120000)
        board.wait_for_timeout(1500)
        probe["board"] = board.evaluate(
            """() => ({
              ui: document.body.getAttribute('data-cf-ui'),
              cos: document.querySelectorAll('[data-cf2-co]').length,
              fields: document.querySelectorAll('.cf2-evfield').length,
              openFrame: !!document.querySelector('.cf2-co--attention .cf2-co__glyph'),
            })"""
        )
        board.locator("#family").screenshot(path=str(OUT / "01_object_family.png"))
        board.locator("#transitions").screenshot(path=str(OUT / "02_state_transitions.png"))
        board.locator("#fields").screenshot(path=str(OUT / "03_evidence_grammar.png"))
        board.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        board.wait_for_timeout(300)
        board.locator("#family").screenshot(path=str(OUT / "13c_family_grayscale.png"))
        board.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop_home"] = page.evaluate(
            """() => ({
              ui: document.body.getAttribute('data-cf-ui'),
              maturity: ([...document.querySelectorAll('link[rel=stylesheet]')].some(l => (l.href||'').includes('uiv2g'))),
              openCo: !!document.querySelector('.cf2-co--attention, .cf2-co--ev-sparse, .cf2-co--insufficient'),
              gravity: !!document.querySelector('.cf2-scene__gravity'),
            })"""
        )
        page.screenshot(path=str(OUT / "09_desktop_home.png"), full_page=False)
        page.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop_workspace"] = page.evaluate(
            """() => ({
              route: !!document.querySelector('.cf2-route'),
              dmass: !!document.querySelector('.cf2-dmass'),
              scoop: !!document.querySelector('.cf2-co--recovery-continue, .cf2-co--waiting, .cf2-co--uncertainty'),
            })"""
        )
        page.screenshot(path=str(OUT / "10_desktop_workspace.png"), full_page=False)
        page.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "13b_workspace_grayscale.png"), full_page=False)
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(4000)
        page.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "13a_home_grayscale.png"), full_page=False)
        ctx.close()

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
        mpage.screenshot(path=str(OUT / "11_mobile_home.png"), full_page=False)
        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        mpage.wait_for_timeout(4500)
        mpage.screenshot(path=str(OUT / "12_mobile_workspace.png"), full_page=False)
        mctx.close()
        browser.close()

    (OUT / "gate_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            (probe.get("board") or {}).get("cos", 0) >= 10,
            (probe.get("desktop_home") or {}).get("maturity"),
            (probe.get("desktop_home") or {}).get("gravity"),
            (probe.get("desktop_workspace") or {}).get("dmass"),
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
