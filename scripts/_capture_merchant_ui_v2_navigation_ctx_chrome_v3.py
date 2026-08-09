# -*- coding: utf-8 -*-
"""Living Store — Mobile Context Navigation Architecture Correction V3 evidence."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_navigation_ctx_chrome_v3"
BASE = "https://smartreplyai.net"
MARKER = "nav-ctx-chrome-v3"


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
  const pageChrome = document.querySelector('#cf2-page-chrome');
  const trigger = document.querySelector('#cf2-ctx-trigger');
  const triggerTextEl = document.querySelector('#cf2-ctx-trigger-text');
  const sectionChrome = document.querySelector('#cf2-section-chrome');
  const stage = document.querySelector('.cf2-stage__inner');
  const sheet = document.querySelector('#cf2-ctx-sheet');
  const drawer = document.querySelector('#cf2-drawer');
  const ctx = document.querySelector('#cf2-ctx');
  const shell = document.querySelector('.cf2-shell');
  const root = document.querySelector('.cf2-root');
  const inAppbar = !!(trigger && appbar && appbar.contains(trigger));
  const inStage = !!(trigger && stage && stage.contains(trigger));
  const inPageChrome = !!(trigger && pageChrome && pageChrome.contains(trigger));
  const inRootFrame = !!(pageChrome && root && root.contains(pageChrome) && !stage?.contains(pageChrome));
  const drawerItems = [...document.querySelectorAll('#cf2-drawer [data-cf2-nav], #cf2-drawer a.cf2-drawer__item')].map(el => ({
    nav: el.getAttribute('data-cf2-nav'),
    text: (el.textContent || '').trim(),
  }));
  const sheetItems = [...document.querySelectorAll('#cf2-ctx-sheet [data-cf2-ctx-item]')].map(el => ({
    id: el.getAttribute('data-cf2-ctx-item'),
    text: (el.textContent || '').trim(),
  }));
  const sidebarItems = [...document.querySelectorAll('#cf2-ctx [data-cf2-ctx-item]')].map(el => ({
    id: el.getAttribute('data-cf2-ctx-item'),
    text: (el.textContent || '').trim(),
  }));
  const stageText = (stage?.innerText || '').slice(0, 280);
  const hasFloatingFiHatha = /في هذا القسم/.test(stageText);
  return {
    marker: appbar?.getAttribute('data-cf2-appbar'),
    appbarText,
    appbarHasHomePill: /الرئيسية/.test(appbarText),
    appbarHasWorkspacePill: /مساحة القرار/.test(appbarText),
    appbarHasOverview: /نظرة عامة|ما يحتاج قرارك/.test(appbarText),
    triggerInAppbar: inAppbar,
    triggerInStageContent: inStage,
    triggerInPageChrome: inPageChrome,
    pageChromeInFrame: inRootFrame,
    sectionChromePresent: !!sectionChrome,
    pageChromeVisible: !!(pageChrome && !pageChrome.hidden && pageChrome.getBoundingClientRect().height > 2),
    pageChromeKicker: (pageChrome?.querySelector('.cf2-page-chrome__kicker')?.textContent || '').trim(),
    triggerActiveText: (triggerTextEl?.textContent || '').trim(),
    triggerVisible: !!(trigger && !trigger.hidden && trigger.getBoundingClientRect().width > 4),
    stageHasFloatingFiHathaButton: hasFloatingFiHatha,
    sheetOpen: !!(sheet && sheet.classList.contains('is-open')),
    drawerOpen: !!(drawer && drawer.classList.contains('is-open')),
    ctxAttr: shell?.getAttribute('data-cf2-ctx'),
    sidebarVisible: !!(ctx && ctx.offsetParent !== null && ctx.getBoundingClientRect().width > 20),
    drawerItems,
    sheetItems,
    sidebarItems,
    drawerHasCtxItems: drawerItems.some(i => /نظرة عامة|ما يحتاج قرارك/.test(i.text)),
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

        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = desk.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        desk.add_cookies([session_cookie(page)])

        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-appbar[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["desktop_home"] = page.evaluate(PROBE)
        page.screenshot(path=str(OUT / "01_desktop_home.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["desktop_workspace"] = page.evaluate(PROBE)
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
        mpage.screenshot(path=str(OUT / "03_mobile_home_closed.png"), full_page=False)

        if mpage.locator("#cf2-ctx-trigger").is_visible():
            mpage.click("#cf2-ctx-trigger")
            mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_home_context"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "04_mobile_home_context_open.png"), full_page=False)
        mpage.click("#cf2-ctx-sheet-close")
        mpage.wait_for_timeout(400)

        mpage.click(".cf2-menu-btn")
        mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_global_drawer"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "07_mobile_global_drawer.png"), full_page=False)
        mpage.click(".cf2-drawer__close")
        mpage.wait_for_timeout(400)

        mpage.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        mpage.wait_for_timeout(2200)
        evidence["probes"]["mobile_workspace_closed"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "05_mobile_workspace_closed.png"), full_page=False)

        if mpage.locator("#cf2-ctx-trigger").is_visible():
            mpage.click("#cf2-ctx-trigger")
            mpage.wait_for_timeout(600)
        evidence["probes"]["mobile_workspace_context"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(OUT / "06_mobile_workspace_context_open.png"), full_page=False)

        mob.close()
        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(OUT), "sha": deploy.get("sha")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
