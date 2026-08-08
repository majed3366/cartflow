# -*- coding: utf-8 -*-
"""Living Store captures — Home Final Composition V1.1."""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_home_final_composition_v1_1"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_home_final_composition_v1"
    / "01_desktop_home.png"
)
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = ""


def wait_for_deploy(timeout_s: int = 600) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if not EXPECTED_SHA_PREFIX or sha.startswith(EXPECTED_SHA_PREFIX):
                    return {"ok": True, **last}
        except Exception as exc:  # noqa: BLE001
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "before").mkdir(exist_ok=True)
    if BEFORE.is_file():
        shutil.copy2(BEFORE, OUT / "before" / "01_desktop_home_v1.png")

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

        def home_probe(page):
            return page.evaluate(
                """() => {
                  const railBodies = [...document.querySelectorAll('.cf2-home__rail-body')]
                    .map(el => (el.textContent || '').trim());
                  const primaryWhy = (document.querySelector('.cf2-home__why') || {}).textContent || '';
                  const shippingDup = railBodies.some(b =>
                    primaryWhy && b && (
                      b === primaryWhy ||
                      (primaryWhy.length > 28 && b.includes(primaryWhy.slice(0, 40))) ||
                      (b.length > 28 && primaryWhy.includes(b.slice(0, 40)))
                    )
                  );
                  const btn = document.querySelector('.cf2-home__action a');
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    home: !!document.querySelector('.cf2-home'),
                    board: !!document.querySelector('.cf2-home__board'),
                    rail: !!document.querySelector('.cf2-home__rail'),
                    railLabel: (document.querySelector('.cf2-home__rail-label') || {}).textContent || '',
                    quietCta: !!(btn && btn.className.includes('quiet')),
                    shippingDup,
                    cache: [...document.querySelectorAll('link[rel=stylesheet]')].some(l => (l.href||'').includes('uiv2j')),
                    version: document.querySelector('.cf2-home')?.getAttribute('data-cf2') || '',
                  };
                }"""
            )

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop"] = home_probe(page)
        page.screenshot(path=str(OUT / "01_desktop_home.png"), full_page=False)
        board = page.query_selector(".cf2-home__board")
        if board:
            board.screenshot(path=str(OUT / "02_desktop_board_closeup.png"))
        page.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "04_desktop_grayscale.png"), full_page=False)
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
        probe["mobile"] = home_probe(mpage)
        mpage.screenshot(path=str(OUT / "03_mobile_home.png"), full_page=False)
        mctx.close()
        browser.close()

    (OUT / "gate_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    d = probe.get("desktop") or {}
    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            d.get("home"),
            d.get("board"),
            d.get("cache"),
            d.get("version") == "home-final-v11",
            not d.get("shippingDup"),
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
