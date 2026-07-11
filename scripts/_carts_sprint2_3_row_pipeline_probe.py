# -*- coding: utf-8 -*-
"""
Sprint 2.3 — Desktop row pipeline probe (investigation only, no product fix).

Same session: capture __maCartsRowProbe at desktop (>=900) and mobile (<900)
after a normal-carts refresh. Finds the first stage where queue items vanish.

Requires CARTFLOW_PROD_EMAIL / CARTFLOW_PROD_PASSWORD (or existing cookies).
Expects build ui-setup-v8i-cart-row-trace-v1 after deploy.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
BUILD = "ui-setup-v8i-cart-row-trace-v1"
OUT = Path(__file__).resolve().parent / "_carts_sprint2_3_row_pipeline_probe_out"


def _auth(page) -> dict:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    page.goto(f"{BASE}/dashboard#carts", timeout=120000)
    page.wait_for_timeout(2000)
    if "/login" not in (page.url or ""):
        return {"ok": True, "mode": "session"}
    if not email or not password:
        return {"ok": False, "mode": "missing_creds"}
    page.goto(f"{BASE}/login", timeout=120000)
    page.locator('input[name="email"], input[type="email"]').first.fill(email)
    page.locator('input[name="password"], input[type="password"]').first.fill(
        password
    )
    page.locator('button[type="submit"], input[type="submit"]').first.click()
    page.wait_for_timeout(4000)
    page.goto(f"{BASE}/dashboard#carts", timeout=120000)
    page.wait_for_timeout(5000)
    return {"ok": "/login" not in (page.url or ""), "mode": "password"}


PROBE_JS = """() => {
  const p = typeof window.__maCartsRowProbe === 'function'
    ? window.__maCartsRowProbe()
    : null;
  const filtAll = document.getElementById('ma-filt-all');
  const filtSent = document.getElementById('ma-filt-sent');
  return {
    url: location.href,
    build: window.MERCHANT_SETUP_RENDER_BUILD || null,
    build_ok: (window.MERCHANT_SETUP_RENDER_BUILD || '') === %s,
    filt_all: filtAll ? filtAll.textContent : null,
    filt_sent: filtSent ? filtSent.textContent : null,
    probe: p,
    trace: (window.__maCartsRowTrace || []).slice(-40),
  };
}""" % (
    json.dumps(BUILD)
)


def _capture(page, label: str, width: int, height: int, *, refetch: bool) -> dict:
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(800)
    if refetch:
        page.evaluate(
            """async () => {
              if (typeof window.maFetchNormalCartsNow === 'function') {
                await window.maFetchNormalCartsNow('sprint23_row_probe');
                return;
              }
              const r = await fetch('/api/dashboard/normal-carts?_ts=' + Date.now()
                + '&_label=sprint23_row_probe',
                { credentials: 'same-origin', cache: 'no-store' });
              const d = await r.json();
              if (window.__maNormalCartsTestHooks
                  && typeof window.__maNormalCartsTestHooks.applyNormalCarts === 'function') {
                window.__maNormalCartsTestHooks.applyNormalCarts(d);
              }
            }"""
        )
        page.wait_for_timeout(4500)
    else:
        page.wait_for_timeout(500)
    shot = OUT / f"{label}.png"
    page.screenshot(path=str(shot), full_page=False)
    data = page.evaluate(PROBE_JS)
    data["label"] = label
    data["viewport"] = {"width": width, "height": height}
    data["refetch"] = refetch
    data["screenshot"] = str(shot)
    return data


def _first_drop(desktop: dict, mobile: dict) -> dict:
    """Compare probes; identify earliest divergence from DOM/RSC snapshots."""
    dp = (desktop or {}).get("probe") or {}
    mp = (mobile or {}).get("probe") or {}
    d_dom = dp.get("dom") or {}
    m_dom = mp.get("dom") or {}
    return {
        "desktop_visible_queue": d_dom.get("visible_queue_item_count"),
        "mobile_visible_queue": m_dom.get("visible_queue_item_count"),
        "desktop_memory_rows": dp.get("memory_rows"),
        "mobile_memory_rows": mp.get("memory_rows"),
        "desktop_story_cards": d_dom.get("story_card_count"),
        "mobile_story_cards": m_dom.get("story_card_count"),
        "desktop_rsc": dp.get("rsc"),
        "mobile_rsc": mp.get("rsc"),
        "desktop_calm": d_dom.get("calm_or_pending"),
        "mobile_calm": m_dom.get("calm_or_pending"),
        "desktop_calm_text": d_dom.get("calm_text"),
        "mobile_calm_text": m_dom.get("calm_text"),
        "same_memory": dp.get("memory_rows") == mp.get("memory_rows"),
        "same_visible": d_dom.get("visible_queue_item_count")
        == m_dom.get("visible_queue_item_count"),
        "parity_ok": (
            d_dom.get("visible_queue_item_count")
            == m_dom.get("visible_queue_item_count")
            and (d_dom.get("visible_queue_item_count") or 0) > 0
        ),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "build_expected": BUILD,
        "base": BASE,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        auth = _auth(page)
        report["auth"] = auth
        if not auth.get("ok"):
            (OUT / "report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(json.dumps(report, indent=2))
            return 2
        desktop = _capture(page, "01_desktop", 1280, 900, refetch=True)
        # Same DOM / same payload — resize only (CSS vs session divergence).
        mobile_resize = _capture(page, "02_mobile_resize_same_dom", 390, 844, refetch=False)
        mobile_refetch = _capture(page, "03_mobile_refetch", 390, 844, refetch=True)
        report["desktop"] = desktop
        report["mobile_resize_same_dom"] = mobile_resize
        report["mobile_refetch"] = mobile_refetch
        report["comparison_resize"] = _first_drop(desktop, mobile_resize)
        report["comparison_refetch"] = _first_drop(desktop, mobile_refetch)
        browser.close()
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("resize_parity", json.dumps(report["comparison_resize"], indent=2, ensure_ascii=False))
    print("refetch_parity", json.dumps(report["comparison_refetch"], indent=2, ensure_ascii=False))
    print("wrote", OUT / "report.json")
    ok = report["comparison_resize"].get("parity_ok") and report[
        "comparison_refetch"
    ].get("parity_ok")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
