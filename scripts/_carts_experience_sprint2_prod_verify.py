# -*- coding: utf-8 -*-
"""Carts Experience Sprint 2 — shared Hero production verify (Home + Carts)."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_PROD_BASE", "https://smartreplyai.net").rstrip("/")
OUT = Path(__file__).resolve().parent / "_carts_experience_sprint2_prod_out"
JS_MARKER = "fillSharedCartsHero"
EMAIL = os.environ.get("CARTFLOW_PROD_EMAIL", "")
PASSWORD = os.environ.get("CARTFLOW_PROD_PASSWORD", "")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get(url: str, timeout: float = 60.0) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "*/*", "User-Agent": "cartflow-carts-sprint2/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def wait_for_deploy(*, attempts: int = 40, sleep_s: float = 15.0) -> dict[str, Any]:
    url = f"{BASE}/static/merchant_dashboard_lazy.js?_={int(time.time())}"
    out: dict[str, Any] = {"url": url, "attempts": []}
    for i in range(1, attempts + 1):
        code, body = _get(url)
        hit = JS_MARKER in body and "cartsHeroStoryFromVerdict" in body
        out["attempts"].append(
            {"n": i, "status": code, "marker_present": hit, "len": len(body)}
        )
        if hit:
            out["deployed"] = True
            out["attempt"] = i
            return out
        time.sleep(sleep_s)
    out["deployed"] = False
    return out


def _shot(page, name: str, *, width: int, height: int) -> str:
    page.set_viewport_size({"width": width, "height": height})
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path.name


def capture() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"utc": _utc(), "base": BASE, "shots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ar-SA")
        page = context.new_page()
        page.goto(f"{BASE}/dashboard", wait_until="domcontentloaded", timeout=90000)
        if EMAIL and PASSWORD:
            if page.locator('input[type="email"], input[name="email"]').count():
                page.fill('input[type="email"], input[name="email"]', EMAIL)
                page.fill('input[type="password"], input[name="password"]', PASSWORD)
                page.click('button[type="submit"], button:has-text("دخول")')
                page.wait_for_url("**/dashboard**", timeout=60000)
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2500)
        hero = page.locator("#ma-page-hero-global")
        report["home_hero_visible"] = hero.is_visible()
        report["home_hero_classes"] = hero.get_attribute("class") or ""
        report["shots"].append(_shot(page, "01_home_desktop", width=1280, height=900))
        report["shots"].append(_shot(page, "01_home_mobile", width=390, height=844))

        page.goto(f"{BASE}/dashboard#carts", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)
        report["carts_hero_visible"] = hero.is_visible()
        report["carts_shared_attr"] = hero.get_attribute("data-shared-hero-carts")
        report["carts_title"] = page.locator("#pageTitle").inner_text()
        report["carts_purpose"] = page.locator("#pagePurpose").inner_text()
        report["carts_sub"] = page.locator("#pageSub").inner_text()
        report["inline_carts_hero_hidden"] = page.locator("#ma-carts-hero").is_hidden()
        report["shots"].append(_shot(page, "02_carts_desktop", width=1280, height=900))
        report["shots"].append(_shot(page, "02_carts_mobile", width=390, height=844))
        browser.close()
    return report


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    (OUT / "deploy_wait.json").write_text(
        json.dumps(deploy, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not deploy.get("deployed"):
        print("DEPLOY_NOT_READY")
        raise SystemExit(2)
    report = capture()
    report["deploy"] = deploy
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
