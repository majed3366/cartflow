# -*- coding: utf-8 -*-
"""Evidence — Carts Product Composition V1 (local or Living Store)."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "carts_product_composition_v1"
SHOTS = OUT / "screenshots"
BASE = os.environ.get("CARTFLOW_CAPTURE_BASE", "https://smartreplyai.net").rstrip("/")
MARKER = "carts-product-composition-v1"
SHELL_MARKER = "shell-integration-v1"


def wait_for_deploy(sha_prefix: str, timeout_s: int = 720) -> dict:
    if not sha_prefix or "127.0.0.1" in BASE or "localhost" in BASE:
        return {"ok": True, "sha": "local", "skipped": True}
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if sha.startswith(sha_prefix):
                    return {"ok": True, **last}
        except Exception as exc:  # noqa: BLE001
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def session_cookie(page):
    page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
    session = page.evaluate(
        """async () => {
          const r = await fetch('/dev/living-store-home-review-session', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json().catch(() => ({}));
        }"""
    )
    if not session or not session.get("cookie_name"):
        return None
    return {
        "name": session["cookie_name"],
        "value": session["cookie_value"],
        "url": BASE,
        "httpOnly": True,
        "sameSite": "Lax",
    }


PROBE = """() => {
  const root = document.querySelector('#cf2-carts-root');
  const carts = root && (root.classList.contains('cf2-carts') ? root : root.querySelector('.cf2-carts'));
  const chrome = document.querySelector('.cf2-chrome');
  const doc = document.documentElement;
  const body = document.body;
  const rows = [...document.querySelectorAll('.cf2-carts__row')];
  const primary = document.querySelector('[data-cf-primary-action]');
  const vipForm = !!document.querySelector('#ma-vip-settings-form, [name="vip_cart_threshold"]');
  const stories = /قصة|التوصية|ماذا يجب أن أعرف|ما القرار الذي يجب/.test(root ? root.innerText : '');
  return {
    marker: carts ? carts.getAttribute('data-cf2') : '',
    shellMarker: chrome ? chrome.getAttribute('data-cf2-appbar') : '',
    question: !!(document.querySelector('[data-cf2-page="carts"] .cf2-page__question')),
    rowCount: rows.length,
    actionable: rows.filter(r => r.classList.contains('is-actionable')).length,
    waiting: rows.filter(r => r.classList.contains('is-waiting')).length,
    terminal: rows.filter(r => r.classList.contains('is-terminal') || r.classList.contains('is-archived')).length,
    primaryKey: primary ? primary.getAttribute('data-cf-primary-action') : '',
    detailOpen: !!(carts && carts.classList.contains('is-detail-open')),
    empty: !!document.querySelector('[data-carts-empty]'),
    emptyMode: (document.querySelector('[data-carts-empty]') || {}).getAttribute?.('data-carts-empty') || '',
    vipConfig: vipForm,
    workspaceOverlap: stories,
    overflowX: doc.scrollWidth > doc.clientWidth + 1,
    bodyOverflowX: getComputedStyle(body).overflowX,
  };
}"""


def shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=True)


def open_carts(page) -> None:
    page.goto(f"{BASE}/dashboard?cf_ui=v2#carts", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(1200)


def main() -> None:
    sha_prefix = os.environ.get("CARTFLOW_EXPECT_SHA", "")
    deploy = wait_for_deploy(sha_prefix)
    SHOTS.mkdir(parents=True, exist_ok=True)
    desktop_probe: dict = {}
    mobile_probe: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ar-SA",
        )
        page = context.new_page()
        cookie = session_cookie(page)
        if cookie:
            context.add_cookies([cookie])
        open_carts(page)
        page.wait_for_selector("#cf2-carts-root.cf2-carts, #cf2-carts-root .cf2-carts__row, #cf2-carts-root .cf2-carts__empty, #cf2-carts-root .cf2-loading", timeout=30000)
        page.wait_for_timeout(800)
        page.wait_for_function(
            "() => document.querySelector('#cf2-carts-root') && document.querySelector('#cf2-carts-root').getAttribute('data-cf2') === 'carts-product-composition-v1'",
            timeout=15000,
        )
        desktop_probe = page.evaluate(PROBE)
        shot(page, "01_desktop_queue_actionable.png")
        row = page.query_selector(".cf2-carts__row")
        if row:
            row.click()
            page.wait_for_timeout(400)
            shot(page, "02_desktop_selected_detail.png")
        waiting = page.query_selector('[data-carts-filter="sent"]')
        if waiting:
            waiting.click()
            page.wait_for_timeout(300)
            shot(page, "03_desktop_waiting_quiet.png")
        recovered = page.query_selector('[data-carts-filter="recovered"]')
        if recovered:
            recovered.click()
            page.wait_for_timeout(300)
            term = page.query_selector(".cf2-carts__row.is-terminal, .cf2-carts__detail-state.is-purchased")
            if term:
                if page.query_selector(".cf2-carts__row.is-terminal"):
                    page.query_selector(".cf2-carts__row.is-terminal").click()
                    page.wait_for_timeout(300)
                shot(page, "04_desktop_purchased_terminal.png")
        desktop_probe = page.evaluate(PROBE)
        desktop_probe["deploy"] = deploy

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        mpage = mobile.new_page()
        if cookie:
            mobile.add_cookies([cookie])
        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#carts", wait_until="networkidle", timeout=90000)
        mpage.wait_for_timeout(1200)
        shot(mpage, "05_mobile_queue_top.png")
        arow = mpage.query_selector(".cf2-carts__row.is-actionable") or mpage.query_selector(".cf2-carts__row")
        if arow:
            shot(mpage, "06_mobile_actionable_cart.png")
            arow.click()
            mpage.wait_for_timeout(400)
            shot(mpage, "07_mobile_cart_detail.png")
            shot(mpage, "08_mobile_primary_action.png")
            tl = mpage.query_selector(".cf2-carts__timeline summary")
            if tl:
                tl.click()
                mpage.wait_for_timeout(250)
                shot(mpage, "09_mobile_timeline.png")
            back = mpage.query_selector("[data-carts-back]")
            if back:
                back.click()
                mpage.wait_for_timeout(300)
                shot(mpage, "10_mobile_return_queue.png")
        att = mpage.query_selector('[data-carts-filter="attention"]')
        if att:
            att.click()
            mpage.wait_for_timeout(300)
            shot(mpage, "11_mobile_calm_state.png")
        mobile_probe = mpage.evaluate(PROBE)
        mobile_probe["deploy"] = deploy
        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(desktop_probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "mobile_overflow_probe.json").write_text(
        json.dumps(mobile_probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"desktop": desktop_probe, "mobile": mobile_probe}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
