# -*- coding: utf-8 -*-
"""Currency Standard Revision V1 — SR compact format visual audit."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_currency_sr_visual_review_v1_out"

PAGES = [
    ("carts", "/dashboard#carts"),
    ("vip", "/dashboard#vip"),
    ("plans", "/dashboard#plans"),
    ("home_month", "/dashboard#home-month"),
    ("messages", "/dashboard#messages"),
]

REJECT = ("ر.س", "ريال سعودي")


def _auth(page) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or os.environ.get("CARTFLOW_REVIEW_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or os.environ.get("CARTFLOW_REVIEW_PASSWORD") or "").strip()
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
    page.locator('input[name="store_name"]').fill(f"SR Audit {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"sr.audit.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"SrAudit!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"SrAudit!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "passed": True}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ar-SA", viewport={"width": 1280, "height": 900})
        _auth(page)

        for key, path in PAGES:
            page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
            page.wait_for_timeout(3500)
            body = page.locator("body").inner_text()
            issues = [f"contains {bad}" for bad in REJECT if bad in body]
            has_sr = " SR" in body or body.endswith("SR") or "SR /" in body
            if not has_sr and key in ("plans", "home_month"):
                issues.append("no SR token visible")
            shot = OUT / f"desktop_{key}.png"
            page.screenshot(path=str(shot), full_page=True)
            ok = len(issues) == 0
            report["pages"][key] = {
                "passed": ok,
                "issues": issues,
                "has_sr": has_sr,
                "screenshot": shot.name,
            }
            if not ok:
                report["passed"] = False

        browser.close()

    out_path = OUT / "currency_sr_review.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(out_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
