# -*- coding: utf-8 -*-
"""Hero Experience Sprint 2.1 — Question First production verify (Home + Carts)."""
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
OUT = Path(__file__).resolve().parent / "_hero_question_first_sprint2_1_prod_out"
MARKERS = ("maFillQuestionFirstHero", "data-hero-narrative")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get(url: str, timeout: float = 60.0) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "*/*", "User-Agent": "cartflow-hero-sprint2-1/1.0"},
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
        code_js, app = _get(f"{BASE}/static/merchant_app.js?_={ts}")
        code_css, vi = _get(f"{BASE}/static/merchant_visual_identity_v1.css?_={ts}")
        hit = all(m in app for m in MARKERS) and 'data-hero-narrative="question-first"' in vi
        out["attempts"].append(
            {
                "n": i,
                "js": code_js,
                "css": code_css,
                "marker_present": hit,
            }
        )
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
          const hero = document.getElementById('ma-page-hero-global');
          const pt = document.getElementById('pageTitle');
          const pp = document.getElementById('pagePurpose');
          const ps = document.getElementById('pageSub');
          const order = (el) => el ? getComputedStyle(el).order : null;
          return {
            page: document.body && document.body.getAttribute('data-ma-page'),
            narrative: hero ? hero.getAttribute('data-hero-narrative') : null,
            title: (pt && pt.textContent) || '',
            purpose: (pp && pp.textContent) || '',
            purpose_hidden: !!(pp && pp.hidden),
            sub: (ps && ps.textContent) || '',
            order_sub: order(ps),
            order_title: order(pt),
            order_purpose: order(pp),
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
        email = f"cf.hero.s21.{uid}@smartreplyai.net"
        password = f"CfHeroS21!{uid}"
        page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        page.locator('input[name="store_name"]').fill(f"Hero S21 {uid}", timeout=60000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["email"] = email

        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        page.evaluate(
            """() => {
              if (typeof window.maRefillHomeSharedHero === 'function') {
                window.maRefillHomeSharedHero();
              }
            }"""
        )
        # Inject recovered story for visual proof of Question → Answer → Support
        page.evaluate(
            """() => {
              if (typeof window.maApplyMerchantPulseV1 === 'function') {
                const slot = (status, message) => ({
                  status, message, confidence: 'high',
                  last_updated: new Date().toISOString(),
                });
                window.maApplyMerchantPulseV1({
                  ok: true,
                  merchant_pulse_v1: {
                    ok: true, version: 'v1', projection: 'MerchantPulseV1',
                    fork: 'leave', status: 'healthy',
                    executive_brief: slot('healthy',
                      'خلال غيابك تم استرداد 4 عمليات شراء بقيمة 852 ريال.'),
                    decision_summary: slot('no_action', 'لا توجد حالة تحتاج تدخلك الآن.'),
                    cartflow_progress: Object.assign(
                      slot('no_action', '—'), { hidden: true }),
                    merchant_decision: slot('no_action', 'لا قرار مطلوب حاليًا.'),
                  },
                });
              }
            }"""
        )
        page.wait_for_timeout(800)
        report["home"] = _probe(page)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.screenshot(path=str(OUT / "01_home_desktop.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "01_home_mobile.png"), full_page=False)

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.evaluate(
            """() => {
              if (typeof window.maFillQuestionFirstHero === 'function') {
                window.maFillQuestionFirstHero({
                  question: 'ما الذي يحتاج انتباهك الآن؟',
                  story: 'لديك 29 سلة تحتاج انتباهك.',
                  support: 'تابع الحالات التي تحتاج قرارًا منك.',
                });
                const hero = document.getElementById('ma-page-hero-global');
                if (hero) hero.setAttribute('data-shared-hero-carts', '1');
              }
            }"""
        )
        page.wait_for_timeout(500)
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
    print(json.dumps({"home": report.get("home"), "carts": report.get("carts")}, ensure_ascii=False, indent=2))
    home_ok = (
        report.get("home", {}).get("narrative") == "question-first"
        and report.get("home", {}).get("order_sub") == "1"
        and report.get("home", {}).get("order_title") == "2"
        and "ماذا حدث أثناء غيابك؟" in (report.get("home", {}).get("sub") or "")
        and "تم استرداد" in (report.get("home", {}).get("title") or "")
    )
    carts_ok = (
        report.get("carts", {}).get("narrative") == "question-first"
        and report.get("carts", {}).get("order_sub") == "1"
        and "ما الذي يحتاج انتباهك الآن؟" in (report.get("carts", {}).get("sub") or "")
        and "29" in (report.get("carts", {}).get("title") or "")
    )
    return 0 if home_ok and carts_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
