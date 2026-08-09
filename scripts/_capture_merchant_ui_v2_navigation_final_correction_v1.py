# -*- coding: utf-8 -*-
"""Living Store — Nav final correction evidence (no horizontal ctx strip)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_navigation_final_correction_v1"
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
  const strip = document.querySelector('#cf2-ctx-mobile, .cf2-ctx-mobile');
  const sheet = document.querySelector('#cf2-ctx-sheet');
  const trigger = document.querySelector('#cf2-ctx-trigger');
  const ctx = document.querySelector('#cf2-ctx');
  const shell = document.querySelector('.cf2-shell');
  const drawer = document.querySelector('#cf2-drawer');
  const drawerItems = [...document.querySelectorAll('#cf2-drawer [data-cf2-nav], #cf2-drawer [data-cf2-ctx-item]')].map(el => ({
    nav: el.getAttribute('data-cf2-nav'),
    ctx: el.getAttribute('data-cf2-ctx-item'),
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
  return {
    marker: document.querySelector('.cf2-appbar')?.getAttribute('data-cf2-appbar'),
    horizontalCtxStripExists: !!strip,
    ctxAttr: shell?.getAttribute('data-cf2-ctx'),
    sidebarVisible: !!(ctx && ctx.offsetParent !== null && ctx.getBoundingClientRect().width > 20),
    triggerVisible: !!(trigger && !trigger.hidden && trigger.getBoundingClientRect().width > 4),
    sheetOpen: !!(sheet && sheet.classList.contains('is-open')),
    drawerOpen: !!(drawer && drawer.classList.contains('is-open')),
    drawerItems,
    sheetItems,
    sidebarItems,
    drawerHasOverview: drawerItems.some(i => /نظرة عامة|الملخص/.test(i.text) || i.ctx),
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
        page.wait_for_selector('.cf2-appbar[data-cf2-appbar="nav-final-v1"]', timeout=60000)
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
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        m = mob.new_page()
        m.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        mob.add_cookies([session_cookie(m)])

        m.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        m.wait_for_timeout(2000)
        evidence["probes"]["mobile_home_closed"] = m.evaluate(PROBE)
        m.screenshot(path=str(OUT / "03_mobile_home_closed.png"), full_page=False)

        m.click("#cf2-ctx-trigger")
        m.wait_for_timeout(500)
        evidence["probes"]["mobile_home_context"] = m.evaluate(PROBE)
        m.screenshot(path=str(OUT / "04_mobile_home_context_open.png"), full_page=False)
        m.click("#cf2-ctx-sheet-close")
        m.wait_for_timeout(400)

        m.click(".cf2-menu-btn")
        m.wait_for_timeout(500)
        evidence["probes"]["mobile_home_global"] = m.evaluate(PROBE)
        m.screenshot(path=str(OUT / "05_mobile_global_drawer.png"), full_page=False)
        m.click(".cf2-drawer__close")
        m.wait_for_timeout(400)

        m.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        m.wait_for_timeout(2000)
        evidence["probes"]["mobile_workspace_closed"] = m.evaluate(PROBE)
        m.screenshot(path=str(OUT / "06_mobile_workspace_closed.png"), full_page=False)

        m.click("#cf2-ctx-trigger")
        m.wait_for_timeout(500)
        evidence["probes"]["mobile_workspace_context"] = m.evaluate(PROBE)
        m.screenshot(path=str(OUT / "07_mobile_workspace_context_open.png"), full_page=False)
        m.click("#cf2-ctx-sheet-close")
        m.wait_for_timeout(400)

        m.evaluate(
            """() => {
              const el = document.createElement('div');
              el.style.height = '1600px';
              el.setAttribute('data-scroll-probe', '1');
              document.querySelector('.cf2-stage__inner')?.appendChild(el);
              window.scrollTo(0, 700);
            }"""
        )
        m.wait_for_timeout(300)
        evidence["probes"]["mobile_scroll"] = m.evaluate(
            "() => ({ y: window.scrollY, bodyOverflow: getComputedStyle(document.body).overflowY })"
        )
        m.screenshot(path=str(OUT / "08_mobile_page_scroll.png"), full_page=False)

        mob.close()
        browser.close()

    fail = False
    for key, probe in evidence["probes"].items():
        if isinstance(probe, dict) and probe.get("horizontalCtxStripExists"):
            fail = True
        if isinstance(probe, dict) and probe.get("drawerHasOverview"):
            fail = True
    evidence["gate_no_horizontal_ctx"] = not fail

    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "fail_horizontal": fail, "deploy": deploy}, ensure_ascii=False))


if __name__ == "__main__":
    main()
