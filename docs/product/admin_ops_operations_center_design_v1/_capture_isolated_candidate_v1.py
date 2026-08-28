# -*- coding: utf-8 -*-
"""Local verification + screenshots for isolated Admin Operations candidate. No mutations."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8789"
PASSWORD = "ops-v11-verify-local"
OUT = Path(__file__).resolve().parent / "screenshots"
REPORT = Path(__file__).resolve().parent / "ISOLATED_VERIFY.json"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict = {"ok": False, "source": "isolated-candidate", "base": BASE, "checks": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})

        page.goto(f"{BASE}/admin/operations", wait_until="domcontentloaded")
        result["checks"]["unauth_redirect"] = "/admin/operations/login" in page.url

        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/admin/operations", timeout=30000)
        page.wait_for_selector("#ops-v11", timeout=30000)
        result["checks"]["auth_page"] = "/admin/operations" in page.url

        body = page.content()
        result["checks"]["has_ops_v11"] = 'id="ops-v11"' in body
        result["checks"]["no_scenario_label"] = "سيناريو" not in body
        result["checks"]["unknown_present"] = "UNKNOWN" in body
        result["checks"]["presentation_time_label"] = "وقت إنشاء العرض" in body
        result["checks"]["no_new_tajawal_font"] = "family=Tajawal" not in body
        result["checks"]["no_action_in_needs"] = "No immediate action required" not in (
            body.split('id="needs"', 1)[-1].split('id="platform"', 1)[0] if 'id="needs"' in body else body
        )
        result["checks"]["logout_only_post"] = 'action="/admin/operations/logout"' in body

        page.screenshot(path=str(OUT / "candidate_desktop_1440.png"), full_page=True)

        overflow = page.evaluate(
            """() => {
              const root = document.getElementById('ops-v11');
              if (!root) return {ok:false};
              const overflowed = [];
              root.querySelectorAll('*').forEach((el) => {
                if (el.scrollWidth > el.clientWidth + 2) {
                  overflowed.push({tag: el.tagName, cls: el.className, sw: el.scrollWidth, cw: el.clientWidth});
                }
              });
              return {ok: overflowed.length === 0, count: overflowed.length, sample: overflowed.slice(0, 5)};
            }"""
        )
        result["checks"]["desktop_overflow"] = overflow

        page.click('#ops-v11 [data-filter="platform"]')
        plat_count = page.locator('#needs .case[data-scope="platform"]').count()
        empty_hidden = page.locator("#empty-platform").is_hidden()
        result["checks"]["filter_platform"] = {
            "platform_cases": plat_count,
            "empty_hidden_when_cases": empty_hidden if plat_count else True,
        }
        page.screenshot(path=str(OUT / "candidate_desktop_filter_platform.png"), full_page=True)
        page.click('#ops-v11 [data-filter="all"]')

        first_case = page.locator("#needs details.case").first
        if first_case.count():
            first_case.locator("summary").focus()
            focused = page.evaluate(
                "() => document.activeElement && document.activeElement.closest('details') !== null"
            )
            result["checks"]["keyboard_focus_summary"] = bool(focused)
            was_open = first_case.get_attribute("open") is not None
            first_case.locator("summary").click()
            now_open = first_case.get_attribute("open") is not None
            result["checks"]["details_toggle"] = now_open != was_open or now_open
        else:
            result["checks"]["keyboard_focus_summary"] = "no_cases"
            result["checks"]["details_toggle"] = "no_cases"

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(200)
        result["checks"]["mobile_segments_visible"] = page.locator("#ops-v11 .segs").is_visible()
        page.screenshot(path=str(OUT / "candidate_mobile_390.png"), full_page=True)
        page.click('#ops-v11 [data-pane="platform"]')
        result["checks"]["mobile_platform_pane"] = page.locator(
            '#ops-v11 [data-pane="platform"].m-pane'
        ).is_visible()
        page.screenshot(path=str(OUT / "candidate_mobile_390_platform.png"), full_page=True)
        page.click('#ops-v11 [data-pane="merchants"]')
        result["checks"]["mobile_merchants_pane"] = page.locator(
            '#ops-v11 [data-pane="merchants"].m-pane'
        ).is_visible()
        page.screenshot(path=str(OUT / "candidate_mobile_390_merchants.png"), full_page=True)

        browser.close()
    result["ok"] = bool(result["checks"].get("unauth_redirect") and result["checks"].get("auth_page"))
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
