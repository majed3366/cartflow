# -*- coding: utf-8 -*-
"""Living Store captures — Merchant UI V2 Visual Language Deepening V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_deepening_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "32b25e8"


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
                if http_status(BASE + "/static/merchant_ui_v2_language.css") == 200:
                    # Prefer build with deepening markers once SHA matches
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
        if not (session.get("cookie_name") and session.get("cookie_value")):
            raise SystemExit(f"FAIL_NO_SESSION: {session}")

        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "url": BASE,
            "httpOnly": True,
            "sameSite": "Lax",
        }

        def lang_probe(page):
            return page.evaluate(
                """() => {
                  const css = [...document.styleSheets];
                  let railRule = false;
                  try {
                    for (const s of css) {
                      const rules = s.cssRules || [];
                      for (const r of rules) {
                        if (r.selectorText && r.selectorText.includes('cf2-co-row--rail')) railRule = true;
                      }
                    }
                  } catch (e) {}
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    rail: !!document.querySelector('.cf2-co-row--rail'),
                    gravity: !!document.querySelector('.cf2-scene__gravity'),
                    terminus: !!document.querySelector('.cf2-terminus'),
                    route: !!document.querySelector('.cf2-route'),
                    dmass: !!document.querySelector('.cf2-dmass'),
                    evfield: !!document.querySelector('.cf2-evfield'),
                    density: (document.querySelector('[data-cf2-density]') || {}).getAttribute?.('data-cf2-density') || null,
                    co: document.querySelectorAll('[data-cf2-co]').length,
                    cache: ([...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href).find(h => h.includes('language')) || '').includes('uiv2e'),
                  };
                }"""
            )

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop_home"] = lang_probe(page)
        page.screenshot(path=str(OUT / "01_desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop_workspace"] = lang_probe(page)
        page.screenshot(path=str(OUT / "02_desktop_workspace.png"), full_page=False)

        page.evaluate("() => document.body.setAttribute('data-cf2-proof', 'grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "06_workspace_grayscale.png"), full_page=False)
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(4000)
        page.evaluate("() => document.body.setAttribute('data-cf2-proof', 'grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "05_home_grayscale.png"), full_page=False)
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
        probe["mobile_home"] = lang_probe(mpage)
        mpage.screenshot(path=str(OUT / "03_mobile_home.png"), full_page=False)

        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#workspace", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile_workspace"] = lang_probe(mpage)
        mpage.screenshot(path=str(OUT / "04_mobile_workspace.png"), full_page=False)
        mctx.close()
        browser.close()

    (OUT / "gate_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))

    dh = probe.get("desktop_home") or {}
    dw = probe.get("desktop_workspace") or {}
    checks = [
        bool(probe.get("deploy", {}).get("ok")),
        dh.get("ui") == "v2",
        dh.get("gravity"),
        dh.get("rail"),
        dh.get("evfield"),
        dw.get("route"),
        dw.get("dmass"),
        dw.get("terminus"),
    ]
    return 0 if all(checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
