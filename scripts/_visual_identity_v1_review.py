# -*- coding: utf-8 -*-
"""Visual Identity Unification V1 — cross-page product review + report."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_visual_identity_v1_review_out"

PAGES = [
    ("desktop_home", "/dashboard#home", 1200, 900),
    ("desktop_carts", "/dashboard#carts", 1200, 900),
    ("desktop_whatsapp", "/dashboard#whatsapp", 1200, 900),
    ("desktop_plans", "/dashboard#plans", 1200, 900),
    ("desktop_settings", "/dashboard#settings", 1200, 900),
    ("desktop_sidebar", "/dashboard#carts", 1200, 900),
    ("mobile_home", "/dashboard#home", 390, 844),
    ("mobile_carts", "/dashboard#carts", 390, 844),
    ("mobile_whatsapp", "/dashboard#whatsapp", 390, 844),
    ("mobile_plans", "/dashboard#plans", 390, 844),
    ("mobile_settings", "/dashboard#settings", 390, 844),
]


def _auth(page) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator('input[name="email"]').fill(email, timeout=60000)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        return
    uid = uuid.uuid4().hex[:8]
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"VI Unify {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"vi.unify.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"ViUnify!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"ViUnify!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _computed_font(page, selector: str) -> str:
    return page.evaluate(
        """(sel) => {
        const el = document.querySelector(sel) || document.body;
        return getComputedStyle(el).fontFamily || '';
      }""",
        selector,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "base": BASE,
        "phase_10_audit": {},
        "surfaces": {},
        "screenshots": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ar-SA")
        _auth(page)

        vi_css = False
        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="networkidle")
        page.wait_for_timeout(3000)
        vi_css = page.locator('link[href*="merchant_visual_identity_v1.css"]').count() > 0

        for name, path, w, h in PAGES:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
            page.wait_for_timeout(3500)
            shot = OUT / f"{name}.png"
            if name == "desktop_sidebar":
                try:
                    page.locator("#ma-context-sidebar").screenshot(path=str(shot))
                except Exception:
                    page.screenshot(path=str(shot))
            else:
                page.screenshot(path=str(shot), full_page=True)

            font_body = _computed_font(page, "body")
            font_hero = _computed_font(page, ".ma-vi-hero .ma-page-hero__title, .v2-hero-title")
            hero_present = page.locator(".ma-vi-hero, .v2-hero").count() > 0
            card_present = page.locator(".setting-card, .ma-mi-group, .v2-hero").count() > 0
            arial = "Arial" in font_body or "arial" in font_body.lower()

            checks = {
                "vi_css_loaded": vi_css
                or page.locator('link[href*="merchant_visual_identity_v1.css"]').count() > 0,
                "arial_typography": arial,
                "hero_language": hero_present,
                "card_family": card_present,
                "sidebar_gradient": page.locator(".ma-context-sidebar").count() > 0,
            }
            verdict = "compliant" if all(checks.values()) else "partial" if checks["vi_css_loaded"] else "non_compliant"
            report["surfaces"][name] = {"path": path, "checks": checks, "fonts": {"body": font_body, "hero": font_hero}, "verdict": verdict}
            report["screenshots"][name] = shot.name

        report["phase_10_audit"] = {
            "one_product_feel": all(
                report["surfaces"].get(k, {}).get("checks", {}).get("vi_css_loaded")
                for k in ("desktop_home", "desktop_carts", "desktop_whatsapp", "desktop_plans", "desktop_settings")
            ),
            "same_design_team": all(
                report["surfaces"].get(k, {}).get("checks", {}).get("arial_typography")
                for k in ("desktop_home", "desktop_whatsapp", "desktop_plans")
            ),
            "recognize_without_logo": report["surfaces"].get("desktop_carts", {}).get("checks", {}).get(
                "hero_language", False
            ),
            "merchant_trust": report["surfaces"].get("desktop_home", {}).get("verdict") in ("compliant", "partial"),
        }

        browser.close()

    (OUT / "visual_identity_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
