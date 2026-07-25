# -*- coding: utf-8 -*-
"""Living Store production MX validation — Executive Editorial Brief V1."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "executive_editorial_brief_v1"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "deploy_sha_expected": "675304e",
        "store_slug": "demo",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return await r.json();
            }"""
        )
        evidence["review_session"] = {
            "ok": session.get("ok"),
            "store_slug": session.get("store_slug"),
            "email": session.get("email"),
        }
        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="ar-SA"
        )
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(7000)
        home = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const secs = hes.sections || [];
              const root = document.getElementById('ma-home-experience-root');
              const text = (root && root.innerText) || '';
              return {
                http: r.status,
                store_slug: j.store_slug
                  || ((j.merchant_home_experience_v1 || {}).store_slug)
                  || null,
                governance: hes.governance || {},
                editorial_brief: hes.editorial_brief || null,
                sections: secs.map(s => ({
                  id: s.id,
                  title_ar: s.title_ar,
                  summary_ar: s.summary_ar,
                  empty: s.empty,
                  commercial_situation: s.commercial_situation,
                  editorial_exclusivity: s.editorial_exclusivity,
                })),
                text_sample: text.slice(0, 1400),
              };
            }"""
        )
        evidence["home"] = home
        page.screenshot(path=str(OUT / "ceo_desktop_home.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "ceo_mobile_home.png"), full_page=False)
        browser.close()

    secs = list((home or {}).get("sections") or [])
    published = [
        s
        for s in secs
        if s.get("editorial_exclusivity") == "published"
        or (
            not s.get("empty")
            and s.get("editorial_exclusivity")
            not in {
                "suppressed_duplicate_situation",
                "suppressed_business_restatement",
            }
        )
    ]
    sits = [
        s.get("commercial_situation")
        for s in secs
        if s.get("editorial_exclusivity") == "published" and s.get("commercial_situation")
    ]
    summaries = [str(s.get("summary_ar") or "") for s in published]
    checks = {
        "store_demo": home.get("store_slug") == "demo",
        "editorial_flag": bool(
            ((home.get("governance") or {}).get("executive_editorial_exclusivity"))
        ),
        "editorial_brief_present": bool(home.get("editorial_brief")),
        "no_duplicate_situations": len(sits) == len(set(sits)),
        "not_both_checkout_and_raven_conversion": not (
            any("إتمام الشراء" in s for s in summaries)
            and any("تحويل" in s or "اهتمام" in s for s in summaries)
        ),
        "has_unique_health_or_obs": any(
            s.get("id") in {"health", "observations"} and not s.get("empty")
            for s in secs
        ),
    }
    evidence["checks"] = checks
    evidence["ok"] = all(checks.values())
    evidence["mx_verdict"] = (
        "Home publishes unique commercial situations under Principle 7"
        if evidence["ok"]
        else "NEEDS_REVIEW"
    )
    path = OUT / "living_store_validation.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(json.dumps({"ok": evidence["ok"], "checks": checks, "sits": sits}, ensure_ascii=False))
    return 0 if evidence["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
