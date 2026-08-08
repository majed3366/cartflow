# -*- coding: utf-8 -*-
"""Gate 1 production captures — Merchant Experience Rebuild V1 (Home + Workspace)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_experience_rebuild_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "61c415f"
ASSETS = (
    "/static/merchant_frame_v1.css",
    "/static/merchant_ds_v1.css",
    "/static/merchant_grammar_v1.css",
    "/static/merchant_experience_home_v1.css",
    "/static/merchant_experience_workspace_v1.css",
    "/static/home_executive_summary_v1.js",
    "/static/cart_workspace_decision_card_v1.js",
    "/static/cart_workspace_grid_v1.js",
)
LEGACY_LINKED = (
    "decision_workspace_visual_assimilation_v1.css",
    "platform_shell_visual_assimilation_v1.css",
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

        def page_probe(page):
            return page.evaluate(
                """() => {
                  const links = [...document.querySelectorAll('link[rel="stylesheet"]')]
                    .map(l => l.getAttribute('href') || '');
                  return {
                    frame: document.body.getAttribute('data-cf-frame'),
                    merchant: document.body.getAttribute('data-cf-merchant-app'),
                    page: document.body.getAttribute('data-ma-page'),
                    cxHome: !!document.querySelector('.cx-home, [data-cx="home"]'),
                    cxInsightPrimary: !!document.querySelector('.cx-insight--primary'),
                    cxWs: !!document.querySelector('.cx-ws, [data-cx="workspace"]'),
                    cxDecision: !!document.querySelector('.cx-decision'),
                    railPrimaryVisible: (() => {
                      const el = document.querySelector('.cf-rail__primary .ma-gtb-section');
                      if (!el) return false;
                      const s = getComputedStyle(el);
                      return s.display !== 'none' && s.visibility !== 'hidden';
                    })(),
                    linksExperienceHome: links.some(h => h.includes('merchant_experience_home_v1.css')),
                    linksExperienceWs: links.some(h => h.includes('merchant_experience_workspace_v1.css')),
                    legacyLinked: links.filter(h =>
                      ['decision_workspace_visual_assimilation_v1.css',
                       'platform_shell_visual_assimilation_v1.css'].some(x => h.includes(x))
                    ),
                  };
                }"""
            )

        # Desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(4500)
        probe["desktop_home"] = page_probe(page)
        page.screenshot(path=str(OUT / "desktop_home.png"), full_page=False)
        page.screenshot(path=str(OUT / "desktop_home_full.png"), full_page=True)

        page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        page.wait_for_timeout(4500)
        probe["desktop_workspace"] = page_probe(page)
        page.screenshot(path=str(OUT / "desktop_workspace.png"), full_page=False)
        page.screenshot(path=str(OUT / "desktop_workspace_full.png"), full_page=True)
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
        mpage.goto(f"{BASE}/dashboard#home", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile_home"] = page_probe(mpage)
        mpage.screenshot(path=str(OUT / "mobile_home.png"), full_page=False)

        mpage.goto(f"{BASE}/dashboard#workspace", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile_workspace"] = page_probe(mpage)
        mpage.screenshot(path=str(OUT / "mobile_workspace.png"), full_page=False)
        mctx.close()
        browser.close()

    (OUT / "gate1_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))

    ok = bool(probe.get("deploy", {}).get("ok"))
    dh = probe.get("desktop_home") or {}
    dw = probe.get("desktop_workspace") or {}
    checks = [
        ok,
        dh.get("frame") == "v1",
        dh.get("linksExperienceHome"),
        dw.get("linksExperienceWs"),
        not dh.get("legacyLinked"),
        not dw.get("legacyLinked"),
        dh.get("cxHome") or dh.get("cxInsightPrimary"),
        dw.get("cxWs") or dw.get("cxDecision"),
        dh.get("railPrimaryVisible"),
    ]
    return 0 if all(checks) else 2


if __name__ == "__main__":
    raise SystemExit(main())
