# -*- coding: utf-8 -*-
"""Typography Lock V1 — production typography certification gate."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_typography_certification_v1_out"

PAGES = [
    ("home", "/dashboard#home"),
    ("carts", "/dashboard#carts"),
    ("whatsapp", "/dashboard#whatsapp"),
    ("plans", "/dashboard#plans"),
    ("settings", "/dashboard#settings"),
]

PROBES = [
    ("body", "body"),
    ("hero_title", ".v2-hero-title, .ma-vi-hero .ma-page-hero__title, #ma-page-hero-global .ma-page-hero__title"),
    ("hero_subtitle", ".ma-vi-hero .ma-page-hero__purpose, .ma-vi-hero #pageSub, .v2-hero-purpose"),
    ("card_title", ".setting-title, .ma-vi-card__title"),
    ("button", "button.btn, .v2-btn, .filter-btn"),
    ("badge", ".nb, .wa-pill, .ma-plan-badge"),
    ("numeric", ".kpi-value, .mc-v, .v2-queue-amount, .ma-plan-price-main"),
    ("sidebar", "#ma-context-sidebar .nav-item"),
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
    page.locator('input[name="store_name"]').fill(f"Typo Gate {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"typo.gate.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"TypoGate!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"TypoGate!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _font_probe(page, selector: str) -> dict | None:
    return page.evaluate(
        """(sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const cs = getComputedStyle(el);
      return {
        family: cs.fontFamily,
        size: cs.fontSize,
        weight: cs.fontWeight,
        lineHeight: cs.lineHeight,
      };
    }""",
        selector,
    )


def _is_arial(family: str) -> bool:
    f = (family or "").lower()
    return "arial" in f and "ibm plex" not in f and "plex" not in f


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "hero_subtitle_consistency": {}, "screenshots": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        hero_subs: dict[str, dict] = {}

        for viewport_name, size in (("desktop", {"width": 1280, "height": 900}), ("mobile", {"width": 390, "height": 844})):
            page = browser.new_page(locale="ar-SA")
            page.set_viewport_size(size)
            _auth(page)

            for page_key, path in PAGES:
                page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
                page.wait_for_timeout(3500)
                prefix = f"{viewport_name}_{page_key}"

                full_path = OUT / f"{prefix}_full.png"
                page.screenshot(path=str(full_path), full_page=True)
                report["screenshots"][f"{prefix}_full"] = full_path.name

                probes: dict = {}
                for probe_key, selector in PROBES:
                    probes[probe_key] = _font_probe(page, selector)

                if viewport_name == "desktop":
                    report["pages"][page_key] = {
                        "typo_css": page.locator('link[href*="merchant_typography_certification_v1.css"]').count() > 0,
                        "google_fonts": page.locator('link[href*="fonts.googleapis.com"]').count() == 0,
                        "probes": probes,
                        "arial_body": _is_arial((probes.get("body") or {}).get("family", "")),
                        "currency_rs": "ر.س" in page.locator("body").inner_text(),
                    }
                    sub = probes.get("hero_subtitle")
                    if sub:
                        hero_subs[page_key] = {
                            "size": sub.get("size"),
                            "weight": sub.get("weight"),
                            "lineHeight": sub.get("lineHeight"),
                        }

            page.close()

        browser.close()

    if hero_subs:
        sizes = {v["size"] for v in hero_subs.values()}
        weights = {v["weight"] for v in hero_subs.values()}
        report["hero_subtitle_consistency"] = {
            "by_page": hero_subs,
            "uniform_size": len(sizes) == 1,
            "uniform_weight": len(weights) == 1,
        }

    (OUT / "typography_cert_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
