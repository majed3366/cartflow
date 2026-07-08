# -*- coding: utf-8 -*-
"""Cart example currency regression — visual audit (أمثلة من السلال / باقi السلال)."""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "https://smartreplyai.net")
OUT = Path(__file__).resolve().parent / "_currency_cart_examples_visual_review_out"

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
    page.locator('input[name="store_name"]').fill(f"CartEx {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"cart.ex.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"CartEx!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"CartEx!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _expand_carts_story(page) -> None:
    page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="networkidle")
    page.wait_for_timeout(3500)
    for summary in page.locator("summary.ma-mi-group-card").all()[:3]:
        try:
            summary.click(timeout=3000)
            page.wait_for_timeout(900)
        except Exception:
            pass
    for more in page.locator("summary.ma-mi-group-more__summary").all()[:2]:
        try:
            more.click(timeout=3000)
            page.wait_for_timeout(700)
        except Exception:
            pass


def _audit_queue(page) -> list[str]:
    issues: list[str] = []
    queue = page.locator("#page-carts .ma-mi-group-section__queue, #page-carts .ma-mi-group-more")
    body = queue.inner_text() if queue.count() else page.locator("#page-carts").inner_text()
    for bad in REJECT:
        if bad in body:
            issues.append(f"contains {bad}")
    if re.search(r"(?<!\S)ر(?!\S)", body):
        issues.append("contains standalone ر")
    if not SR_PATTERN.search(body) and queue.count():
        issues.append("no SR prefix amount in cart examples")
    amounts = page.locator("#page-carts .v2-queue-amount.cf-currency-atom")
    nested = page.locator("#page-carts .v2-queue-amount .cf-currency-atom")
    if nested.count():
        issues.append(f"nested currency atoms: {nested.count()}")
    for i in range(min(amounts.count(), 8)):
        el = amounts.nth(i)
        text = el.inner_text()
        if not SR_PATTERN.search(text):
            issues.append(f"amount {i} not SR format: {text!r}")
        box = el.bounding_box()
        parent = el.locator("xpath=ancestor::button[contains(@class,'v2-queue-item')][1]")
        if box and parent.count():
            pbox = parent.bounding_box()
            if pbox and (box["x"] + box["width"] > pbox["x"] + pbox["width"] + 2):
                issues.append(f"amount {i} overflows card")
    return issues


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "viewports": {}, "passed": True}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport_name, size in (("desktop", {"width": 1440, "height": 900}), ("mobile", {"width": 390, "height": 844})):
            page = browser.new_page(locale="ar-SA", viewport=size)
            _auth(page)
            _expand_carts_story(page)
            issues = _audit_queue(page)
            shot = OUT / f"{viewport_name}_carts_examples.png"
            page.screenshot(path=str(shot), full_page=True)
            ok = len(issues) == 0
            report["viewports"][viewport_name] = {
                "passed": ok,
                "issues": issues,
                "screenshot": shot.name,
                "has_examples_label": "أمثلة من السلال" in page.locator("body").inner_text(),
            }
            if not ok:
                report["passed"] = False
            page.close()
        browser.close()

    out_path = OUT / "cart_examples_currency_review.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(out_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
