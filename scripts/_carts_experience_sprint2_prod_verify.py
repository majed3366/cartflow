# -*- coding: utf-8 -*-
"""Carts Experience Sprint 2 — shared Hero production verify (Home + Carts)."""
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
OUT = Path(__file__).resolve().parent / "_carts_experience_sprint2_prod_out"
JS_MARKER = "fillSharedCartsHero"


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
        polish_url = f"{BASE}/static/merchant_product_polish_v1.css?_={int(time.time())}"
        _, polish = _get(polish_url)
        carts_hidden = 'body[data-ma-page="carts"] #ma-page-hero-global' in polish
        out["attempts"].append(
            {
                "n": i,
                "status": code,
                "marker_present": hit,
                "carts_hero_still_hidden_in_css": carts_hidden,
                "len": len(body),
            }
        )
        if hit and not carts_hidden:
            out["deployed"] = True
            out["attempt"] = i
            return out
        time.sleep(sleep_s)
    out["deployed"] = False
    return out


def _probe(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const hero = document.getElementById('ma-page-hero-global');
          const inline = document.getElementById('ma-carts-hero');
          const verdict = document.getElementById('ma-carts-attention-verdict-v1');
          const cs = hero ? getComputedStyle(hero) : null;
          return {
            page: document.body && document.body.getAttribute('data-ma-page'),
            hero_visible: !!(hero && cs && cs.display !== 'none' && cs.visibility !== 'hidden'),
            hero_classes: hero ? hero.className : '',
            shared_carts: hero ? hero.getAttribute('data-shared-hero-carts') : null,
            title: (document.getElementById('pageTitle') || {}).textContent || '',
            purpose: (document.getElementById('pagePurpose') || {}).textContent || '',
            sub: (document.getElementById('pageSub') || {}).textContent || '',
            inline_hidden: !inline || inline.hidden || getComputedStyle(inline).display === 'none',
            verdict_quiet: !verdict || verdict.hidden || !verdict.innerText.trim(),
          };
        }"""
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"utc": _utc(), "base": BASE}
    deploy = wait_for_deploy()
    report["deploy"] = deploy
    (OUT / "deploy_wait.json").write_text(
        json.dumps(deploy, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(deploy, indent=2))
    if not deploy.get("deployed"):
        (OUT / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 2

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900}, locale="ar-SA"
        )
        page = context.new_page()
        uid = uuid.uuid4().hex[:8]
        email = f"cf.carts.s2.{uid}@smartreplyai.net"
        password = f"CfCartsS2!{uid}"
        page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"Carts S2 {uid}", timeout=60000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["email"] = email

        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        # Ensure Home hero was not left on Carts framing.
        page.evaluate(
            """() => {
              if (typeof window.maRefillHomeSharedHero === 'function') {
                window.maRefillHomeSharedHero();
              }
            }"""
        )
        page.wait_for_timeout(500)
        report["home"] = _probe(page)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.screenshot(path=str(OUT / "01_home_desktop.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "01_home_mobile.png"), full_page=False)

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        try:
            page.wait_for_function(
                """() => {
                  const p = document.getElementById('pagePurpose');
                  const t = (p && p.textContent) || '';
                  return t && !t.includes('جارٍ تجهيز') && !t.includes('جاري تجهيز');
                }""",
                timeout=45000,
            )
        except Exception as exc:  # noqa: BLE001
            report["carts_story_wait_error"] = str(exc)
        page.wait_for_timeout(1500)
        report["carts"] = _probe(page)
        page.screenshot(path=str(OUT / "02_carts_desktop.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "02_carts_mobile.png"), full_page=False)

        browser.close()

    report["screenshots"] = sorted(p.name for p in OUT.glob("*.png"))
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "deployed": True,
                "home": report.get("home"),
                "carts": report.get("carts"),
                "screenshots": report["screenshots"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    ok = (
        report.get("carts", {}).get("hero_visible")
        and report.get("carts", {}).get("shared_carts") == "1"
        and "ما الذي يحتاج انتباهك الآن؟" in (report.get("carts", {}).get("sub") or "")
        and report.get("carts", {}).get("inline_hidden")
    )
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
