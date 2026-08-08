# -*- coding: utf-8 -*-
"""Living Store production validation — Home V2 default baseline promotion."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_home_production_baseline_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = ""
# Frozen visual baseline SHA (composition); promotion deploy may differ.
HOME_VISUAL_BASELINE = "71cf4e3"


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
    deploy = wait_for_deploy()
    probe: dict = {
        "deploy": deploy,
        "home_visual_baseline": HOME_VISUAL_BASELINE,
        "default_url": f"{BASE}/dashboard#home",
        "rollback": {
            "query": f"{BASE}/dashboard?cf_ui=v1#home",
            "dev_route": f"{BASE}/dev/merchant-ui-v1",
            "env": "CARTFLOW_MERCHANT_UI_V2=0",
            "cookie": "cf_ui_v2=0",
        },
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
        # Fresh auth cookie only — do NOT carry a cf_ui_v2 override.
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
                  const body = document.body;
                  const links = [...document.querySelectorAll('link[rel=stylesheet]')]
                    .map(l => l.href || '');
                  const scripts = [...document.querySelectorAll('script[src]')]
                    .map(s => s.src || '');
                  const legacyCss = links.some(h =>
                    /merchant_frame_v1|merchant_pe_v2|merchant_experience_home_v1|decision_workspace_visual_assimilation/i.test(h)
                  );
                  const v2Css = links.some(h => /merchant_ui_v2_home\\.css/.test(h));
                  const v2Frame = links.some(h => /merchant_ui_v2_frame\\.css/.test(h));
                  const hasCfUiQuery = /[?&]cf_ui=/.test(location.search);
                  return {
                    url: location.href,
                    hash: location.hash,
                    hasCfUiQuery,
                    ui: body.getAttribute('data-cf-ui'),
                    version: document.querySelector('.cf2-home')?.getAttribute('data-cf2') || '',
                    home: !!document.querySelector('.cf2-home'),
                    scene: !!document.querySelector('.cf2-home__scene'),
                    monitor: !!document.querySelector('.cf2-home__monitor'),
                    stance: !!document.querySelector('.cf2-home__stance'),
                    confidence: (document.querySelector('.cf2-home__confidence') || {}).textContent || '',
                    title: (document.querySelector('.cf2-home__title') || {}).textContent || '',
                    navHome: !!document.querySelector('[data-cf2-nav=\"home\"].is-active, .cf2-nav [aria-current=\"page\"]'),
                    legacyCss,
                    v2Css,
                    v2Frame,
                    noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
                    mixedStyles: legacyCss && v2Css,
                  };
                }"""
            )

        # Desktop — default /dashboard#home (no cf_ui query)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop"] = home_probe(page)
        page.screenshot(path=str(OUT / "desktop_production_home.png"), full_page=False)
        board = page.query_selector(".cf2-home__board") or page.query_selector(".cf2-home")
        if board:
            board.screenshot(path=str(OUT / "production_home_closeup.png"))
        ctx.close()

        # Laptop
        lctx = browser.new_context(viewport={"width": 1280, "height": 800}, locale="ar-SA")
        lctx.add_cookies([cookie])
        lpage = lctx.new_page()
        lpage.goto(f"{BASE}/dashboard#home", timeout=120000)
        lpage.wait_for_timeout(4500)
        probe["laptop"] = home_probe(lpage)
        lpage.screenshot(path=str(OUT / "laptop_production_home.png"), full_page=False)
        lctx.close()

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
        probe["mobile"] = home_probe(mpage)
        mpage.screenshot(path=str(OUT / "mobile_production_home.png"), full_page=False)
        mctx.close()

        # Rollback smoke (V1 still reachable)
        rctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        rctx.add_cookies([cookie])
        rpage = rctx.new_page()
        rpage.goto(f"{BASE}/dashboard?cf_ui=v1#home", timeout=120000)
        rpage.wait_for_timeout(3500)
        probe["rollback_v1"] = rpage.evaluate(
            """() => ({
              ui: document.body.getAttribute('data-cf-ui'),
              hasV1Frame: [...document.querySelectorAll('link[rel=stylesheet]')]
                .some(l => /merchant_frame_v1/.test(l.href || '')),
              hasV2Home: [...document.querySelectorAll('link[rel=stylesheet]')]
                .some(l => /merchant_ui_v2_home/.test(l.href || '')),
            })"""
        )
        rctx.close()
        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))

    def ok_surface(d: dict) -> bool:
        return all(
            [
                d.get("ui") == "v2",
                d.get("version") == "home-stage-closure-v1",
                d.get("home"),
                d.get("scene"),
                d.get("monitor"),
                d.get("stance"),
                d.get("v2Css"),
                d.get("v2Frame"),
                not d.get("legacyCss"),
                not d.get("mixedStyles"),
                d.get("noOverflow"),
                not d.get("hasCfUiQuery"),
            ]
        )

    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            ok_surface(probe.get("desktop") or {}),
            ok_surface(probe.get("laptop") or {}),
            ok_surface(probe.get("mobile") or {}),
            (probe.get("rollback_v1") or {}).get("hasV1Frame"),
            not (probe.get("rollback_v1") or {}).get("hasV2Home"),
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
