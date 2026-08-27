# -*- coding: utf-8 -*-
"""Evidence — Carts Empty / Calm State Visual Closure V1."""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "carts_empty_calm_state_v1"
SHOTS = OUT / "screenshots"
BASE = os.environ.get("CARTFLOW_CAPTURE_BASE", "https://smartreplyai.net").rstrip("/")
FORCE_EMPTY = os.environ.get("CARTFLOW_FORCE_EMPTY", "").strip() in ("1", "true", "yes")


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
  const q = document.querySelector('[data-cf2-page="carts"] .cf2-page__question');
  const root = document.querySelector('#cf2-carts-root');
  const carts = root && (root.classList.contains('cf2-carts') ? root : root.querySelector('.cf2-carts'));
  const orient = document.querySelector('.cf2-carts__orient-h');
  const filters = [...document.querySelectorAll('.cf2-carts__filter')];
  const emptyPanel = document.querySelector('.cf2-carts__empty');
  const detailEmpty = document.querySelector('.cf2-carts__detail-empty');
  const rows = [...document.querySelectorAll('.cf2-carts__row')];
  const text = (root && root.innerText) || '';
  const repeats = (text.match(/لا توجد سلال/g) || []).length;
  return {
    marker: carts ? carts.getAttribute('data-cf2') : '',
    storeEmpty: carts ? carts.getAttribute('data-carts-empty') : '',
    isEmptyClass: !!(carts && carts.classList.contains('is-empty')),
    question: !!(q && q.textContent && q.textContent.trim()),
    calm: orient ? orient.textContent.trim() : '',
    filterCount: filters.length,
    emptyPanel: !!emptyPanel,
    selectGhost: !!(detailEmpty && /اختر سلة/.test(detailEmpty.innerText || '')),
    rowCount: rows.length,
    repeatLaTujad: repeats,
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  };
}"""


def shot(page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=False)


def open_carts(page) -> None:
    page.goto(f"{BASE}/dashboard?cf_ui=v2#carts", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(1400)


def force_store_empty(page) -> None:
    page.route(
        "**/api/dashboard/normal-carts*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "ok": True,
                    "merchant_carts_page_rows": [],
                    "merchant_archived_carts_page_rows": [],
                    "merchant_cart_filter_counts": {
                        "all": 0,
                        "attention": 0,
                        "nophone": 0,
                        "sent": 0,
                        "recovered": 0,
                    },
                }
            ),
        ),
    )


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    probes = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def make_page(width, height, mobile=False):
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=mobile,
                has_touch=mobile,
                locale="ar-SA",
            )
            page = ctx.new_page()
            cookie = session_cookie(page)
            if cookie:
                ctx.add_cookies([cookie])
            return ctx, page

        for name, w, h, mobile in (
            ("01_mobile_430_zero_cart.png", 430, 932, True),
            ("02_mobile_390_zero_cart.png", 390, 844, True),
            ("03_desktop_zero_cart.png", 1440, 900, False),
        ):
            ctx, page = make_page(w, h, mobile)
            if FORCE_EMPTY:
                force_store_empty(page)
            open_carts(page)
            page.wait_for_selector("#cf2-carts-root.cf2-carts.is-empty, #cf2-carts-root[data-carts-empty=store]", timeout=20000)
            probes[name] = page.evaluate(PROBE)
            shot(page, name)
            ctx.close()

        ctx, page = make_page(1440, 900, False)
        open_carts(page)
        page.wait_for_selector("#cf2-carts-root.cf2-carts", timeout=20000)
        live = page.evaluate(PROBE)
        probes["04_live"] = live
        if live.get("rowCount", 0) > 0:
            shot(page, "04_desktop_nonempty_regression.png")
        ctx.close()

        browser.close()
    (OUT / "probe.json").write_text(json.dumps(probes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(probes, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
