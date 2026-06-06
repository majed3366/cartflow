# -*- coding: utf-8 -*-
"""Production gate: 3× VIP refresh — cached rows visible <1s, no disappear window."""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_refresh_stability_gate_out"


def _auth(page, report: dict) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        report["auth"] = {"mode": "login", "email": email}
        return

    uid = uuid.uuid4().hex[:10]
    email = f"cf.vip.stab.{uid}@smartreplyai.net"
    password = f"CfVipStab!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipStab {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def _save_vip_threshold(page) -> None:
    page.goto(f"{BASE}/dashboard#vip", timeout=120000)
    page.wait_for_timeout(2500)
    page.evaluate(
        """() => {
          if (typeof window.maInitVipSettingsPage === 'function') window.maInitVipSettingsPage();
          var th = document.getElementById('ma-vip-threshold');
          if (th) th.value = '500';
          var en = document.getElementById('ma-vip-enabled');
          if (en) en.checked = true;
        }"""
    )
    page.locator("#ma-vip-settings-save").click(timeout=20000)
    page.wait_for_timeout(2000)


def _create_vip_cart(page) -> None:
    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(4000)
    page.locator("#p-watch_pro .add-btn").click()
    page.wait_for_timeout(2000)
    page.evaluate("window.__cfV2ShowNow && window.__cfV2ShowNow()")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="نعم").click(timeout=20000)
    page.get_by_role("button", name="السعر").click(timeout=20000)
    page.get_by_role("button", name="شكراً").click(timeout=20000)
    page.locator('input[type="tel"]').last.fill("0598877660")
    page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
    page.wait_for_timeout(2500)


def _vip_row_snap(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          var tb = document.getElementById('ma-tbody-vip-page');
          var text = tb ? (tb.innerText || '') : '';
          return {
            rows: tb ? tb.querySelectorAll('tr:not(.ma-dash-skel-row):not([data-ma-vip-loading])').length : 0,
            skel: tb ? !!tb.querySelector('.ma-dash-skel-row') : false,
            loading: tb ? !!tb.querySelector('[data-ma-vip-loading]') : false,
            empty_vip: text.indexOf('لا توجد سلال VIP') >= 0,
            has_amount: /\\d+\\s*ريال/.test(text),
            cache_key: !!sessionStorage.getItem('ma_vip_carts_cache_v1'),
          };
        }"""
    )


def _wait_vip_rows(page, timeout_s: float = 120) -> dict[str, Any]:
    t0 = time.time()
    last: dict[str, Any] = {}
    while (time.time() - t0) < timeout_s:
        snap = _vip_row_snap(page)
        last = snap
        if int(snap.get("rows") or 0) >= 1 and snap.get("has_amount"):
            last["visible_ms"] = round((time.time() - t0) * 1000, 1)
            return last
        page.wait_for_timeout(200)
    last["timeout"] = True
    return last


def _reload_vip_proof(page, reload_i: int) -> dict[str, Any]:
    t0 = time.time()
    page.reload(timeout=120000)
    first_rows_ms: float | None = None
    had_skel_gap = False
    timeline: list[dict[str, Any]] = []
    for i in range(30):
        snap = _vip_row_snap(page)
        elapsed = round((time.time() - t0) * 1000, 1)
        snap["poll_i"] = i
        snap["elapsed_ms"] = elapsed
        timeline.append(snap)
        if first_rows_ms is None and int(snap.get("rows") or 0) >= 1 and snap.get("has_amount"):
            first_rows_ms = elapsed
        if (
            first_rows_ms is None
            and int(snap.get("rows") or 0) == 0
            and (snap.get("skel") or snap.get("empty_vip"))
            and not snap.get("has_amount")
        ):
            had_skel_gap = True
        if first_rows_ms is not None and i >= 5:
            break
        page.wait_for_timeout(100)
    return {
        "reload_i": reload_i,
        "first_rows_ms": first_rows_ms,
        "had_disappear_window": had_skel_gap and (first_rows_ms is None or first_rows_ms > 1000),
        "cache_under_1s": first_rows_ms is not None and first_rows_ms <= 1000,
        "final": timeline[-1] if timeline else {},
        "timeline_head": timeline[:8],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "refreshes": [],
        "normal_carts": {},
        "pass": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        _auth(page, report)
        _save_vip_threshold(page)
        _create_vip_cart(page)
        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
        primed = _wait_vip_rows(page, timeout_s=120)
        page.screenshot(path=str(OUT / "before_refresh_baseline.png"), full_page=True)
        report["primed"] = primed

        # Prime sessionStorage cache via one successful render
        page.wait_for_timeout(2000)
        cache = page.evaluate(
            "() => { try { return JSON.parse(sessionStorage.getItem('ma_vip_carts_cache_v1')||'null'); } catch(e) { return null; } }"
        )
        report["cache_primed"] = {
            "has_cache": bool(cache),
            "row_count": len((cache or {}).get("page_rows") or []),
        }

        for i in range(3):
            proof = _reload_vip_proof(page, i)
            report["refreshes"].append(proof)
            page.screenshot(path=str(OUT / f"refresh_{i + 1}_final.png"), full_page=True)

        page.goto(f"{BASE}/dashboard#carts", timeout=120000)
        page.wait_for_timeout(8000)
        normal = page.evaluate(
            """() => {
              var tb = document.getElementById('ma-tbody-all-carts');
              var rows = tb ? tb.querySelectorAll('tr[data-ma-filter]').length : 0;
              var badge = document.getElementById('ma-nav-badge-abandoned');
              var badgeN = badge ? parseInt(badge.textContent || '0', 10) : null;
              return { visible_rows: rows, nav_badge: badgeN, parity: rows === badgeN };
            }"""
        )
        report["normal_carts"] = normal
        page.screenshot(path=str(OUT / "normal_carts_after_vip_gate.png"), full_page=True)
        browser.close()

    all_cache_fast = all(r.get("cache_under_1s") for r in report["refreshes"])
    no_disappear = all(not r.get("had_disappear_window") for r in report["refreshes"])
    has_rows = all(int((r.get("final") or {}).get("rows") or 0) >= 1 for r in report["refreshes"])
    normal_ok = int(normal.get("visible_rows") or 0) > 0
    report["pass"] = bool(all_cache_fast and no_disappear and has_rows and normal_ok)

    out_json = OUT / "vip_refresh_stability_gate.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
