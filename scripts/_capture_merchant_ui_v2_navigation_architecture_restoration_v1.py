# -*- coding: utf-8 -*-
"""Living Store — Global Upbar + Contextual Sidebar architecture evidence."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_navigation_architecture_restoration_v1"
BASE = "https://smartreplyai.net"


def wait_for_deploy(sha_prefix: str, timeout_s: int = 720) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if not sha_prefix or sha.startswith(sha_prefix):
                    return {"ok": True, **last}
        except Exception as exc:  # noqa: BLE001
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def session_cookie(page) -> dict:
    session = page.evaluate(
        """async () => {
          const r = await fetch('/dev/living-store-home-review-session', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json().catch(() => ({}));
        }"""
    )
    return {
        "name": session["cookie_name"],
        "value": session["cookie_value"],
        "url": BASE,
        "httpOnly": True,
        "sameSite": "Lax",
    }


PROBE = """() => {
  const bar = document.querySelector('.cf2-appbar');
  const marker = bar && bar.getAttribute('data-cf2-appbar');
  const shell = document.querySelector('.cf2-shell');
  const ctx = document.querySelector('#cf2-ctx');
  const mobileCtx = document.querySelector('#cf2-ctx-mobile');
  const nav = [...document.querySelectorAll('.cf2-nav [data-cf2-nav]')].map(b => b.getAttribute('data-cf2-nav'));
  const ctxItems = [...document.querySelectorAll('#cf2-ctx [data-cf2-ctx-item]')].map(b => ({
    id: b.getAttribute('data-cf2-ctx-item'),
    label: (b.textContent || '').trim(),
    active: b.classList.contains('is-active'),
  }));
  const mobileItems = [...document.querySelectorAll('#cf2-ctx-mobile [data-cf2-ctx-item]')].map(b => ({
    id: b.getAttribute('data-cf2-ctx-item'),
    label: (b.textContent || '').trim(),
    active: b.classList.contains('is-active'),
  }));
  const drawerItems = [...document.querySelectorAll('.cf2-drawer [data-cf2-nav]')].map(b => b.getAttribute('data-cf2-nav'));
  const sectionInBar = !!document.querySelector('#cf2-appbar-section, .cf2-appbar__section, .cf2-appbar__core');
  const homeMarker = document.querySelector('[data-cf2=\"home-stage-closure-v1\"]');
  const wsMarker = document.querySelector('[data-cf2=\"workspace-final-v1\"]');
  return {
    marker,
    ctxAttr: shell && shell.getAttribute('data-cf2-ctx'),
    mobileCtxAttr: mobileCtx && mobileCtx.getAttribute('data-cf2-ctx-mobile'),
    mobileCtxHidden: mobileCtx ? !!mobileCtx.hidden : null,
    ctxVisible: !!(ctx && ctx.offsetParent !== null && ctx.getBoundingClientRect().width > 8),
    mobileCtxVisible: !!(mobileCtx && !mobileCtx.hidden && mobileCtx.getBoundingClientRect().height > 4),
    globalNavIds: nav,
    drawerNavIds: drawerItems,
    ctxItems,
    mobileItems,
    sectionMergedIntoUpbar: sectionInBar,
    homeCompositionMarker: !!homeMarker,
    workspaceCompositionMarker: !!wsMarker,
    bodyOverflow: getComputedStyle(document.body).overflowY,
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight,
  };
}"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sha_prefix = (
        (OUT / "expected_sha.txt").read_text(encoding="utf-8").strip()
        if (OUT / "expected_sha.txt").exists()
        else ""
    )
    deploy = wait_for_deploy(sha_prefix)
    evidence: dict = {"deploy": deploy, "probes": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Desktop
        desk = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            locale="ar-SA",
        )
        page = desk.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        desk.add_cookies([session_cookie(page)])

        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector('.cf2-appbar[data-cf2-appbar="global-upbar-v1"]', timeout=60000)
        evidence["probes"]["desktop_home"] = page.evaluate(PROBE)
        page.locator(".cf2-appbar, .cf2-shell").first.screenshot(
            path=str(OUT / "01_desktop_home_upbar_sidebar.png")
        )
        # Better: clip top+sidebar region
        page.screenshot(path=str(OUT / "01_desktop_home_upbar_sidebar.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 420})
        page.screenshot(path=str(OUT / "03_desktop_home_full.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["desktop_workspace"] = page.evaluate(PROBE)
        page.screenshot(path=str(OUT / "02_desktop_workspace_upbar_sidebar.png"), clip={"x": 0, "y": 0, "width": 1440, "height": 420})
        page.screenshot(path=str(OUT / "04_desktop_workspace_full.png"), full_page=False)
        desk.close()

        # Mobile
        mob = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="ar-SA",
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        mpage = mob.new_page()
        mpage.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        mob.add_cookies([session_cookie(mpage)])

        mpage.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2000)
        evidence["probes"]["mobile_home_closed"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "06_mobile_home_context_navigation.png"), full_page=False)

        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(500)
        evidence["probes"]["mobile_home_drawer"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "05_mobile_home_global_navigation.png"), full_page=False)
        mpage.click(".cf2-drawer__close")
        mpage.wait_for_timeout(400)

        # scroll evidence
        mpage.evaluate("window.scrollTo(0, Math.min(900, document.body.scrollHeight))")
        mpage.wait_for_timeout(300)
        mpage.screenshot(path=str(OUT / "09_mobile_home_page_scroll.png"), full_page=False)
        mpage.evaluate("window.scrollTo(0, 0)")

        mpage.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2000)
        evidence["probes"]["mobile_workspace_closed"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "08_mobile_workspace_context_navigation.png"), full_page=False)

        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(500)
        evidence["probes"]["mobile_workspace_drawer"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "07_mobile_workspace_global_navigation.png"), full_page=False)
        mpage.click(".cf2-drawer__close")
        mpage.wait_for_timeout(400)
        mpage.evaluate("window.scrollTo(0, Math.min(900, document.body.scrollHeight))")
        mpage.wait_for_timeout(300)
        mpage.screenshot(path=str(OUT / "10_mobile_workspace_page_scroll.png"), full_page=False)

        mob.close()
        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(OUT), "deploy": deploy}, ensure_ascii=False))


if __name__ == "__main__":
    main()
