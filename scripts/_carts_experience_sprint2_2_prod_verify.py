# -*- coding: utf-8 -*-
"""Carts Experience Sprint 2.2 — production verify (stable reveal)."""
from __future__ import annotations

import json
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_carts_experience_sprint2_2_prod_out"
MARKERS = ("cartsPlanIsCanonicalReveal", "rsc_commit_hold_reveal", "data-carts-ready")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get(url: str, timeout: float = 60.0) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "*/*", "User-Agent": "cartflow-carts-sprint2-2/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def wait_for_deploy(*, attempts: int = 40, sleep_s: float = 15.0) -> dict[str, Any]:
    out: dict[str, Any] = {"attempts": []}
    for i in range(1, attempts + 1):
        ts = int(time.time())
        code, lazy = _get(f"{BASE}/static/merchant_dashboard_lazy.js?_={ts}")
        _, polish = _get(f"{BASE}/static/merchant_product_polish_v1.css?_={ts}")
        hit = all(m in lazy for m in MARKERS) and "جارٍ تجهيز صورة السلال" not in lazy
        hit = hit and 'data-carts-ready="0"' in polish
        out["attempts"].append({"n": i, "status": code, "marker_present": hit})
        if hit:
            out["deployed"] = True
            out["attempt"] = i
            return out
        time.sleep(sleep_s)
    out["deployed"] = False
    return out


def _probe(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const title = (document.getElementById('pageTitle') || {}).textContent || '';
          const sub = (document.getElementById('pageSub') || {}).textContent || '';
          const loading = document.getElementById('ma-carts-unified-loading');
          const filters = document.getElementById('ma-cart-filters');
          const hint = document.getElementById('ma-cart-filters-hint');
          const shell = document.querySelector('#page-carts .ma-pe-v2-carts-shell');
          return {
            page: document.body && document.body.getAttribute('data-ma-page'),
            ready: document.body && document.body.getAttribute('data-carts-ready'),
            title,
            sub,
            has_technical: /تجهيز صورة|جارٍ تجهيز/.test(title),
            loading_visible: !!(loading && !loading.hidden && getComputedStyle(loading).display !== 'none'),
            shell_visible: !!(shell && getComputedStyle(shell).display !== 'none'),
            filters_visible: !!(filters && !filters.hidden),
            hint_text: (hint && !hint.hidden) ? (hint.textContent || '').trim() : '',
          };
        }"""
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"utc": _utc(), "base": BASE}
    deploy = wait_for_deploy()
    report["deploy"] = deploy
    print(json.dumps(deploy, indent=2))
    if not deploy.get("deployed"):
        (OUT / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(
            viewport={"width": 1280, "height": 900}, locale="ar-SA"
        ).new_page()
        uid = uuid.uuid4().hex[:8]
        page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        page.locator('input[name="store_name"]').fill(f"Carts S22 {uid}", timeout=60000)
        page.locator('input[name="email"]').fill(f"cf.carts.s22.{uid}@smartreplyai.net")
        page.locator('input[name="password"]').first.fill(f"CfCartsS22!{uid}")
        page.locator('input[name="confirm_password"]').fill(f"CfCartsS22!{uid}")
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["email"] = f"cf.carts.s22.{uid}@smartreplyai.net"

        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        report["carts_early"] = _probe(page)
        page.screenshot(path=str(OUT / "01_carts_loading_or_early.png"), full_page=False)

        try:
            page.wait_for_function(
                """() => document.body.getAttribute('data-carts-ready') === '1'""",
                timeout=90000,
            )
        except Exception as exc:  # noqa: BLE001
            report["ready_wait_error"] = str(exc)

        page.wait_for_timeout(1000)
        report["carts_ready"] = _probe(page)
        page.screenshot(path=str(OUT / "02_carts_desktop_ready.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "02_carts_mobile_ready.png"), full_page=False)

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        page.screenshot(path=str(OUT / "03_home_desktop.png"), full_page=False)
        browser.close()

    report["screenshots"] = sorted(p.name for p in OUT.glob("*.png"))
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "early": report.get("carts_early"),
        "ready": report.get("carts_ready"),
        "screenshots": report["screenshots"],
    }, ensure_ascii=False, indent=2))

    early = report.get("carts_early") or {}
    ready = report.get("carts_ready") or {}
    ok = (
        not early.get("has_technical")
        and not ready.get("has_technical")
        and ready.get("ready") == "1"
        and "ما الذي يحتاج انتباهك الآن؟" in (ready.get("sub") or "")
    )
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
