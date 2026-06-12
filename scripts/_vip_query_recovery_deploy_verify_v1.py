# -*- coding: utf-8 -*-
"""Post-deploy verification: VIP Query Architecture Recovery v1 on production."""
from __future__ import annotations

import json
import os
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request
from playwright.sync_api import BrowserContext, Page, sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_query_recovery_deploy_verify_v1_out"

ROW_PROBE = r"""() => {
  var tb = document.getElementById('ma-tbody-vip-page');
  if (!tb) return { data_rows: 0, loading: false, has_amount: false };
  var text = tb.innerText || '';
  return {
    data_rows: tb.querySelectorAll('tr:not(.ma-dash-skel-row):not([data-ma-vip-loading])').length,
    loading: text.indexOf('جاري تحميل سلال VIP') >= 0,
    has_amount: /\d+\s*ريال/.test(text),
  };
}"""

BASELINE = {
    "laptop_first_row_ms": 8127,
    "mobile_first_row_ms": 9388,
    "isolated_fetch_ms_low": 3176,
    "isolated_fetch_ms_high": 3819,
    "business_sql_5_rows": 239,
}


def _auth(page: Page, report: dict[str, Any]) -> None:
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
    email = f"cf.vip.recovery.{uid}@smartreplyai.net"
    password = f"CfRecov!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipRecov {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def _fresh_context(browser, *, mobile: bool) -> BrowserContext:
    if mobile:
        return browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent="CartFlowVipRecoveryVerify/Mobile",
        )
    return browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="CartFlowVipRecoveryVerify/Laptop",
    )


def _fetch_vip_debug(cookies: list[dict[str, Any]]) -> dict[str, Any]:
    """Isolated GET /api/dashboard/vip-carts?debug_perf=1 using cookie jar."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    for c in cookies:
        cj.set_cookie(
            http.cookiejar.Cookie(
                version=0,
                name=c["name"],
                value=c["value"],
                port=None,
                port_specified=False,
                domain=c.get("domain", "smartreplyai.net").lstrip("."),
                domain_specified=True,
                domain_initial_dot=False,
                path=c.get("path", "/"),
                path_specified=True,
                secure=bool(c.get("secure")),
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False,
            )
        )
    url = f"{BASE}/api/dashboard/vip-carts?debug_perf=1"
    t0 = time.perf_counter()
    try:
        with opener.open(
            urllib.request.Request(url, headers={"Cache-Control": "no-cache"}),
            timeout=60,
        ) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
            ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "status": resp.status,
                "ms": ms,
                "ok": body.get("ok"),
                "rows": len(body.get("merchant_vip_page_rows") or []),
                "debug_perf": body.get("debug_perf"),
                "deployed_batch": isinstance(body.get("debug_perf"), dict),
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "ms": round((time.perf_counter() - t0) * 1000, 2),
            "error": str(exc),
            "deployed_batch": False,
        }


def _poll_deploy(cookies: list[dict[str, Any]], report: dict[str, Any]) -> bool:
    polls: list[dict[str, Any]] = []
    for i in range(40):
        snap = _fetch_vip_debug(cookies)
        polls.append({"i": i, **snap})
        deployed = snap.get("deployed_batch") and (
            (snap.get("debug_perf") or {}).get("query_count", 999) <= 20
        )
        print(f"deploy poll {i}: deployed={deployed} ms={snap.get('ms')} debug={snap.get('debug_perf')}")
        if deployed:
            report["deploy_polls"] = polls
            report["deploy_detected_at_poll"] = i
            return True
        time.sleep(15)
    report["deploy_polls"] = polls
    return False


def _fresh_vip_load(ctx: BrowserContext, label: str) -> dict[str, Any]:
    page = ctx.new_page()
    vip_network: list[dict[str, Any]] = []
    nav_start = time.perf_counter()

    def on_response(resp) -> None:
        if "/api/dashboard/vip-carts" in resp.url:
            try:
                body = resp.json()
            except Exception:
                body = {}
            vip_network.append(
                {
                    "url": resp.url,
                    "status": resp.status,
                    "response_ms_from_nav": round((time.perf_counter() - nav_start) * 1000, 1),
                    "cart_count": len((body or {}).get("merchant_vip_page_rows") or []),
                    "debug_perf": (body or {}).get("debug_perf"),
                }
            )

    page.on("response", on_response)
    page.add_init_script("() => { try { sessionStorage.clear(); } catch(e) {} }")
    hash_start = time.perf_counter()
    page.goto(f"{BASE}/dashboard#vip", timeout=180000, wait_until="domcontentloaded")

    first_row_ms: float | None = None
    for i in range(100):
        elapsed = round((time.perf_counter() - hash_start) * 1000, 1)
        snap = page.evaluate(ROW_PROBE)
        if int(snap.get("data_rows") or 0) >= 1 and snap.get("has_amount"):
            first_row_ms = elapsed
            break
        page.wait_for_timeout(100)

    page.screenshot(path=str(OUT / f"{label}_final.png"), full_page=True)
    page.close()
    return {
        "label": label,
        "first_visible_row_ms_from_hash": first_row_ms,
        "vip_network": vip_network,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit": "vip_query_architecture_recovery_deploy_verify_v1",
        "base": BASE,
        "baseline": BASELINE,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        auth_ctx = _fresh_context(browser, mobile=False)
        auth_page = auth_ctx.new_page()
        _auth(auth_page, report)
        cookies = auth_ctx.cookies()
        auth_ctx.close()

        report["deploy_ready"] = _poll_deploy(cookies, report)

        isolated_samples: list[dict[str, Any]] = []
        for _ in range(3):
            isolated_samples.append(_fetch_vip_debug(cookies))
            time.sleep(0.5)
        report["isolated_vip_fetch"] = isolated_samples

        fresh_runs: list[dict[str, Any]] = []
        for mobile in (False, True):
            for run_i in range(2):
                ctx = _fresh_context(browser, mobile=mobile)
                ctx.add_cookies(cookies)
                label = f"{'mobile' if mobile else 'laptop'}_fresh_run{run_i + 1}"
                fresh_runs.append(_fresh_vip_load(ctx, label))
                ctx.close()
        report["fresh_load_runs"] = fresh_runs
        browser.close()

    laptop_rows = [
        r["first_visible_row_ms_from_hash"]
        for r in fresh_runs
        if r["label"].startswith("laptop") and r["first_visible_row_ms_from_hash"]
    ]
    mobile_rows = [
        r["first_visible_row_ms_from_hash"]
        for r in fresh_runs
        if r["label"].startswith("mobile") and r["first_visible_row_ms_from_hash"]
    ]
    fetch_ms = [s.get("ms") for s in isolated_samples if s.get("ms")]
    query_counts = [
        (s.get("debug_perf") or {}).get("query_count")
        for s in isolated_samples
        if isinstance(s.get("debug_perf"), dict)
    ]

    report["summary"] = {
        "deploy_ready": report.get("deploy_ready"),
        "laptop_first_row_ms_median": statistics.median(laptop_rows) if laptop_rows else None,
        "mobile_first_row_ms_median": statistics.median(mobile_rows) if mobile_rows else None,
        "isolated_fetch_ms_median": statistics.median(fetch_ms) if fetch_ms else None,
        "query_count_median": statistics.median(query_counts) if query_counts else None,
        "vs_baseline": {
            "laptop_delta_ms": (
                (statistics.median(laptop_rows) - BASELINE["laptop_first_row_ms"])
                if laptop_rows
                else None
            ),
            "mobile_delta_ms": (
                (statistics.median(mobile_rows) - BASELINE["mobile_first_row_ms"])
                if mobile_rows
                else None
            ),
            "isolated_fetch_delta_ms": (
                (statistics.median(fetch_ms) - BASELINE["isolated_fetch_ms_high"])
                if fetch_ms
                else None
            ),
        },
    }

    out_json = OUT / "deploy_verify_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print("written", out_json)
    return 0 if report.get("deploy_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
