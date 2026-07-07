# -*- coding: utf-8 -*-
"""PDS Final Closure V1 — complete merchant visual identity review gate."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_visual_identity_final_review_out"

PAGES = [
    ("home", "/dashboard#home"),
    ("home_setup", "/dashboard#home-setup"),
    ("home_month", "/dashboard#home-month"),
    ("carts", "/dashboard#carts"),
    ("whatsapp", "/dashboard#whatsapp"),
    ("widget", "/dashboard#widget"),
    ("plans", "/dashboard#plans"),
    ("settings", "/dashboard#settings"),
    ("messages", "/dashboard#messages"),
    ("trigger_templates", "/dashboard#trigger-templates"),
    ("reasons", "/dashboard#reasons"),
]

CLOSURE_CSS = [
    "merchant_shell_identity_v1.css",
    "merchant_card_system_v1.css",
    "merchant_icon_language_v1.css",
    "merchant_spacing_certification_v1.css",
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
    page.locator('input[name="store_name"]').fill(f"PDS Close {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"pds.close.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"PdsClose!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"PdsClose!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _style_probe(page, selector: str) -> dict | None:
    return page.evaluate(
        """(sel) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const cs = getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        boxShadow: cs.boxShadow,
        backgroundImage: cs.backgroundImage,
        paddingTop: cs.paddingTop,
        fontFamily: cs.fontFamily,
      };
    }""",
        selector,
    )


def _page_checks(page) -> dict:
    checks: dict = {
        "pds_closure_class": page.evaluate(
            '() => document.body.classList.contains("cf-pds-closure")'
        ),
        "closure_css": {},
        "shell": _style_probe(page, ".ma-global-topbar"),
        "sidebar": _style_probe(page, "#ma-context-sidebar"),
        "card": _style_probe(page, ".setting-card, .ma-fw-card, .card, .kpi"),
    }
    for name in CLOSURE_CSS:
        checks["closure_css"][name] = page.locator(f'link[href*="{name}"]').count() > 0
    return checks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "screenshots": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch()
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

                shell_path = OUT / f"{prefix}_shell.png"
                loc = page.locator(".ma-global-topbar")
                if loc.count():
                    loc.first.screenshot(path=str(shell_path))
                    report["screenshots"][f"{prefix}_shell"] = shell_path.name

                if viewport_name == "desktop":
                    report["pages"][page_key] = _page_checks(page)

            page.close()
        browser.close()

    all_css = all(
        all(v for v in p.get("closure_css", {}).values())
        for p in report["pages"].values()
    )
    report["certification"] = {
        "all_closure_css_loaded": all_css,
        "pds_closure_body_class": all(
            p.get("pds_closure_class") for p in report["pages"].values()
        ),
        "pages_reviewed": len(report["pages"]),
    }

    (OUT / "final_review_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
