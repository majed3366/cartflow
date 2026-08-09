# -*- coding: utf-8 -*-
"""Living Store — Navigation Architecture Reset V1 evidence (two levels only)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_navigation_architecture_reset_v1"
BASE = "https://smartreplyai.net"
MARKER = "nav-reset-v1"


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
  const appbar = document.querySelector('.cf2-appbar');
  const appbarText = (appbar?.innerText || '').replace(/\\s+/g, ' ').trim();
  const pageChrome = document.querySelector('#cf2-page-chrome, .cf2-page-chrome');
  const ctxSheet = document.querySelector('#cf2-ctx-sheet, .cf2-ctx-sheet');
  const sectionChrome = document.querySelector('#cf2-section-chrome');
  const ctx = document.querySelector('#cf2-ctx');
  const ctxBtn = document.querySelector('#cf2-ctx-btn');
  const drawer = document.querySelector('#cf2-drawer');
  const shell = document.querySelector('.cf2-shell');
  const stage = document.querySelector('.cf2-stage__inner');
  const drawerItems = [...document.querySelectorAll('#cf2-drawer [data-cf2-nav], #cf2-drawer a.cf2-drawer__item')].map(el => ({
    nav: el.getAttribute('data-cf2-nav'),
    text: (el.textContent || '').trim(),
  }));
  const sidebarItems = [...document.querySelectorAll('#cf2-ctx [data-cf2-ctx-item]')].map(el => ({
    id: el.getAttribute('data-cf2-ctx-item'),
    text: (el.textContent || '').trim(),
  }));
  const stageLead = (stage?.querySelector('.cf2-page.is-active .cf2-page__question')?.textContent || '').trim();
  return {
    marker: appbar?.getAttribute('data-cf2-appbar'),
    appbarText,
    appbarHasHomePill: /الرئيسية/.test(appbarText),
    appbarHasWorkspacePill: /مساحة القرار/.test(appbarText),
    pageChromePresent: !!pageChrome,
    ctxSheetPresent: !!ctxSheet,
    sectionChromePresent: !!sectionChrome,
    hasTanqulQism: /تنقل القسم/.test(document.body.innerText || ''),
    hasFiHathaInAppbar: /في هذا القسم/.test(appbarText),
    ctxBtnVisible: !!(ctxBtn && !ctxBtn.hidden && ctxBtn.getBoundingClientRect().width > 2),
    ctxOpen: document.body.classList.contains('is-ctx-open'),
    drawerOpen: document.body.classList.contains('is-drawer-open'),
    ctxAttr: shell?.getAttribute('data-cf2-ctx'),
    sidebarVisible: !!(ctx && !ctx.hidden && ctx.offsetParent !== null && ctx.getBoundingClientRect().width > 20),
    sidebarArea: (ctx?.querySelector('.cf2-ctx__area')?.textContent || '').trim(),
    sidebarItems,
    drawerItems,
    drawerHasCtxItems: drawerItems.some(i => /نظرة عامة|ما يحتاج قرارك/.test(i.text)),
    stageLead,
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
    evidence: dict = {"deploy": deploy, "probes": {}, "layers": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = desk.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        desk.add_cookies([session_cookie(page)])

        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-appbar[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["desktop_home"] = page.evaluate(PROBE)
        evidence["layers"]["01_desktop_home"] = {
            "GLOBAL": "Upbar platform sections",
            "CONTEXTUAL": "Sidebar #cf2-ctx",
            "CONTENT": "Home stage",
        }
        page.screenshot(path=str(OUT / "01_desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["desktop_workspace"] = page.evaluate(PROBE)
        evidence["layers"]["02_desktop_workspace"] = {
            "GLOBAL": "Upbar platform sections",
            "CONTEXTUAL": "Sidebar #cf2-ctx",
            "CONTENT": "Workspace stage",
        }
        page.screenshot(path=str(OUT / "02_desktop_workspace.png"), full_page=False)
        desk.close()

        mob = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
        )
        mpage = mob.new_page()
        mpage.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        mob.add_cookies([session_cookie(mpage)])

        mpage.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2200)
        mpage.wait_for_selector(f'.cf2-appbar[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["mobile_home_closed"] = mpage.evaluate(PROBE)
        evidence["layers"]["03_mobile_home_closed"] = {
            "GLOBAL": "App Bar only (closed)",
            "CONTEXTUAL": "closed / not visible",
            "CONTENT": "Home stage starts under App Bar",
        }
        mpage.screenshot(path=str(OUT / "03_mobile_home_closed.png"), full_page=False)

        if mpage.locator("#cf2-ctx-btn").is_visible():
            mpage.click("#cf2-ctx-btn")
            mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_home_ctx"] = mpage.evaluate(PROBE)
        evidence["layers"]["04_mobile_home_ctx"] = {
            "GLOBAL": "App Bar",
            "CONTEXTUAL": "same #cf2-ctx as mobile sidebar drawer",
            "CONTENT": "Home (dimmed)",
        }
        mpage.screenshot(path=str(OUT / "04_mobile_home_contextual_sidebar.png"), full_page=False)
        mpage.click("#cf2-ctx-close")
        mpage.wait_for_timeout(400)

        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_home_global"] = mpage.evaluate(PROBE)
        evidence["layers"]["07_mobile_home_global"] = {
            "GLOBAL": "Global Drawer",
            "CONTEXTUAL": "not open",
            "CONTENT": "Home (dimmed)",
        }
        mpage.screenshot(path=str(OUT / "07_mobile_home_global_drawer.png"), full_page=False)
        mpage.click(".cf2-drawer__close")
        mpage.wait_for_timeout(400)

        mpage.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2200)
        evidence["probes"]["mobile_workspace_closed"] = mpage.evaluate(PROBE)
        evidence["layers"]["05_mobile_workspace_closed"] = {
            "GLOBAL": "App Bar only (closed)",
            "CONTEXTUAL": "closed / not visible",
            "CONTENT": "Workspace stage starts under App Bar",
        }
        mpage.screenshot(path=str(OUT / "05_mobile_workspace_closed.png"), full_page=False)

        if mpage.locator("#cf2-ctx-btn").is_visible():
            mpage.click("#cf2-ctx-btn")
            mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_workspace_ctx"] = mpage.evaluate(PROBE)
        evidence["layers"]["06_mobile_workspace_ctx"] = {
            "GLOBAL": "App Bar",
            "CONTEXTUAL": "same #cf2-ctx as mobile sidebar drawer",
            "CONTENT": "Workspace (dimmed)",
        }
        mpage.screenshot(path=str(OUT / "06_mobile_workspace_contextual_sidebar.png"), full_page=False)
        mpage.click("#cf2-ctx-close")
        mpage.wait_for_timeout(400)

        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_workspace_global"] = mpage.evaluate(PROBE)
        evidence["layers"]["08_mobile_workspace_global"] = {
            "GLOBAL": "Global Drawer",
            "CONTEXTUAL": "not open",
            "CONTENT": "Workspace (dimmed)",
        }
        mpage.screenshot(path=str(OUT / "08_mobile_workspace_global_drawer.png"), full_page=False)

        mob.close()
        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(OUT), "sha": deploy.get("sha")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
