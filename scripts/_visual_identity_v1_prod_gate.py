# -*- coding: utf-8 -*-
"""Visual Identity Unification V1 — production gate (all surfaces, granular screenshots)."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_visual_identity_v1_prod_gate_out"

PAGES = [
    ("home", "/dashboard#home"),
    ("carts", "/dashboard#carts"),
    ("whatsapp", "/dashboard#whatsapp"),
    ("plans", "/dashboard#plans"),
    ("settings", "/dashboard#settings"),
]

HERO_SELECTORS = {
    "home": ".v2-hero, .ma-page-hero",
    "carts": "#ma-carts-hero, .ma-vi-hero",
    "whatsapp": "#ma-page-hero-global.ma-vi-hero",
    "plans": "#ma-page-hero-global.ma-vi-hero",
    "settings": "#ma-page-hero-global.ma-vi-hero",
}

CARD_SELECTORS = {
    "home": ".v2-hero, .ma-knowledge-insight, .kpi, .ma-home-section",
    "carts": ".ma-mi-group-card, .ma-mi-group, .v2-queue-item",
    "whatsapp": ".setting-card, .ma-wa-v2-card",
    "plans": ".ma-plans-current-card, .ma-plan-card, .setting-card",
    "settings": ".setting-card, .ma-store-connection-card",
}


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
    page.locator('input[name="store_name"]').fill(f"VI Gate {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"vi.gate.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"ViGate!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"ViGate!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _shot_element(page, selector: str, path: Path) -> bool:
    loc = page.locator(selector).first
    if loc.count() == 0:
        return False
    try:
        loc.screenshot(path=str(path), timeout=15000)
        return True
    except Exception:
        return False


def _font_info(page) -> dict:
    return page.evaluate(
        """() => {
      const pick = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const cs = getComputedStyle(el);
        return { family: cs.fontFamily, size: cs.fontSize, weight: cs.fontWeight };
      };
      return {
        body: pick('body'),
        hero: pick('.v2-hero-title, .ma-vi-hero .ma-page-hero__title, #ma-page-hero-global.ma-vi-hero .ma-page-hero__title'),
        story: pick('.ma-mi-group-card__title'),
        metric: pick('.kpi-value, .camt, .v2-queue-amount'),
        card: pick('.setting-title, .setting-card'),
      };
    }"""
    )


def _page_checks(page, page_key: str, body_text: str) -> dict:
    fonts = _font_info(page)
    body_ff = (fonts.get("body") or {}).get("family") or ""
    return {
        "vi_css": page.locator('link[href*="merchant_visual_identity_v1.css"]').count() > 0,
        "pds_css": page.locator('link[href*="merchant_pds_compliance_v1.css"]').count() > 0,
        "arial_body": "Arial" in body_ff or "arial" in body_ff.lower(),
        "hero_present": page.locator(HERO_SELECTORS.get(page_key, ".ma-vi-hero, .v2-hero")).count() > 0,
        "hero_ma_vi": page.locator(".ma-vi-hero, .v2-hero").count() > 0,
        "card_present": page.locator(CARD_SELECTORS.get(page_key, ".setting-card")).count() > 0,
        "currency_rs": "ر.س" in body_text,
        "currency_ryal_only": " ريال" in body_text or body_text.count("ريال") > body_text.count("ر.س"),
        "sidebar_visible_desktop": page.locator("#ma-context-sidebar").count() > 0,
        "fonts": fonts,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "screenshots": {}, "po_review": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport_name, size in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
            page = browser.new_page(locale="ar-SA")
            page.set_viewport_size(size)
            if viewport_name == "desktop":
                _auth(page)
            elif viewport_name == "mobile":
                _auth(page)

            for page_key, path in PAGES:
                page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
                page.wait_for_timeout(4000)
                prefix = f"{viewport_name}_{page_key}"
                body_text = page.locator("body").inner_text()

                full_path = OUT / f"{prefix}_full.png"
                page.screenshot(path=str(full_path), full_page=True)
                report["screenshots"][f"{prefix}_full"] = full_path.name

                hero_sel = HERO_SELECTORS.get(page_key, ".ma-vi-hero")
                hero_path = OUT / f"{prefix}_hero.png"
                hero_ok = _shot_element(page, hero_sel, hero_path)
                if not hero_ok:
                    page.screenshot(path=str(hero_path), full_page=False)
                report["screenshots"][f"{prefix}_hero"] = hero_path.name

                card_sel = CARD_SELECTORS.get(page_key, ".setting-card")
                card_path = OUT / f"{prefix}_cards.png"
                card_ok = _shot_element(page, card_sel, card_path)
                if not card_ok:
                    pass  # no cards on empty store
                else:
                    report["screenshots"][f"{prefix}_cards"] = card_path.name

                if viewport_name == "desktop":
                    sb_path = OUT / f"{prefix}_sidebar.png"
                    _shot_element(page, "#ma-context-sidebar", sb_path)
                    report["screenshots"][f"{prefix}_sidebar"] = sb_path.name

                    checks = _page_checks(page, page_key, body_text)
                    report["pages"][page_key] = checks

            page.close()

        browser.close()

    (OUT / "prod_gate_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
