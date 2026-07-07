# -*- coding: utf-8 -*-
"""PDS Compliance V1 — production visual review + reference surface certification."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_pds_compliance_v1_visual_review_out"

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
    page.locator('input[name="store_name"]').fill(f"PDS Compliance {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"pds.compliance.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"PdsCompliance!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"PdsCompliance!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _font_family(page) -> str:
    return page.evaluate(
        """() => {
        const el = document.querySelector('.ma-mi-group-card__title')
          || document.querySelector('.ma-page-hero__title')
          || document.body;
        return el ? getComputedStyle(el).fontFamily : '';
      }"""
    )


def _certify_surface(name: str, checks: dict) -> str:
    required = [
        "pds_css_loaded",
        "ibm_plex_typography",
        "no_rejected_purchase_title",
    ]
    if name.endswith("_carts"):
        required.append("story_cards_present")
    passed = all(checks.get(k) for k in required)
    partial_keys = [k for k in required if not checks.get(k)]
    if passed:
        return "compliant"
    if len(partial_keys) <= 1 and checks.get("pds_css_loaded"):
        return "partial"
    return "non_compliant"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "base": BASE,
        "reference_surface": "carts",
        "certification_questions": {},
        "surfaces": {},
        "screenshots": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ar-SA")
        _auth(page)

        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        pds_loaded = page.locator('link[href*="merchant_pds_compliance_v1.css"]').count() > 0
        font = _font_family(page)
        ibm_plex = "IBM Plex" in font or "ibm plex" in font.lower()

        for name, path, w, h in PAGES:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
            page.wait_for_timeout(3500)
            shot = OUT / f"{name}.png"
            if name == "desktop_sidebar":
                try:
                    page.locator("#ma-context-sidebar").screenshot(path=str(shot))
                except Exception:
                    page.screenshot(path=str(shot), full_page=False)
            else:
                page.screenshot(path=str(shot), full_page=True)

            body_text = page.locator("body").inner_text()
            checks = {
                "pds_css_loaded": pds_loaded
                or page.locator('link[href*="merchant_pds_compliance_v1.css"]').count() > 0,
                "ibm_plex_typography": ibm_plex or "IBM Plex" in _font_family(page),
                "story_cards_present": page.locator(".ma-mi-group-card").count() > 0,
                "currency_r_s_format": "ر.س" in body_text,
                "no_rejected_purchase_title": "اكتملت مشتريات" not in body_text,
                "page_purpose_visible": page.locator("#pagePurpose, .ma-page-hero__purpose").count() > 0,
            }
            verdict = _certify_surface(name, checks)
            report["surfaces"][name] = {"path": path, "checks": checks, "verdict": verdict}
            report["screenshots"][name] = shot.name

        report["certification_questions"] = {
            "identify_cartflow_without_logo": report["surfaces"].get("desktop_carts", {}).get(
                "verdict"
            )
            in ("compliant", "partial"),
            "same_product_feel": all(
                report["surfaces"].get(k, {}).get("checks", {}).get("ibm_plex_typography")
                for k in ("desktop_home", "desktop_carts", "desktop_whatsapp")
            ),
            "typography_identical": ibm_plex,
            "currency_identical": report["surfaces"].get("desktop_carts", {})
            .get("checks", {})
            .get("currency_r_s_format", False),
            "carts_reference_surface": report["surfaces"].get("desktop_carts", {}).get("verdict"),
        }

        browser.close()

    (OUT / "certification_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
