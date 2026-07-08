# -*- coding: utf-8
"""Currency Rendering Standardization V2 — SR prefix visual audit."""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_currency_sr_v2_visual_review_out"

DESKTOP_PAGES = [
    ("carts", "/dashboard#carts"),
    ("completed", "/dashboard#completed"),
    ("vip", "/dashboard#vip"),
    ("home_month", "/dashboard#home-month"),
    ("plans", "/dashboard#plans"),
]

MOBILE_PAGES = [
    ("carts", "/dashboard#carts"),
    ("plans", "/dashboard#plans"),
]

REJECT = ("ر.س", "ريال سعودي")
SR_PATTERN = re.compile(r"SR\s[\d,]+")


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
    page.locator('input[name="store_name"]').fill(f"SR V2 {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"sr.v2.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"SrV2!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"SrV2!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _audit_body(body: str, require_sr: bool) -> list[str]:
    issues: list[str] = []
    for bad in REJECT:
        if bad in body:
            issues.append(f"contains {bad}")
    if re.search(r"(?<!\S)ر(?!\S)", body):
        issues.append("contains standalone ر")
    if re.search(r"(?<!\S)س(?!\S)", body) and "رس" in body.replace(" ", ""):
        issues.append("contains split Arabic currency letters")
    if require_sr and not SR_PATTERN.search(body):
        issues.append("no SR prefix amount visible")
    return issues


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "passed": True}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport_name, size, pages in (
            ("desktop", {"width": 1440, "height": 900}, DESKTOP_PAGES),
            ("mobile", {"width": 390, "height": 844}, MOBILE_PAGES),
        ):
            page = browser.new_page(locale="ar-SA", viewport=size)
            _auth(page)
            for key, path in pages:
                page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
                page.wait_for_timeout(3500)
                if viewport_name == "mobile" and key == "carts":
                    for summary in page.locator("summary.ma-mi-group-card").all()[:2]:
                        try:
                            summary.click(timeout=3000)
                            page.wait_for_timeout(800)
                        except Exception:
                            pass
                body = page.locator("body").inner_text()
                prefix = f"{viewport_name}_{key}"
                require_sr = key in ("plans", "home_month") or (
                    viewport_name == "mobile" and key == "carts" and "SR" in body
                )
                issues = _audit_body(body, require_sr)
                shot = OUT / f"{prefix}.png"
                page.screenshot(path=str(shot), full_page=True)
                ok = len(issues) == 0
                report["pages"][prefix] = {
                    "passed": ok,
                    "issues": issues,
                    "has_sr_prefix": bool(SR_PATTERN.search(body)),
                    "screenshot": shot.name,
                }
                if not ok:
                    report["passed"] = False
            page.close()
        browser.close()

    out_path = OUT / "currency_sr_v2_review.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(out_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
