# -*- coding: utf-8 -*-
"""Bind demo-primary review session and capture production Home proof (no re-seed)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "observation_admission_bridge_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "seed_skipped": True,
        "note": "Living Store already completed on production demo; shots-only pass.",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/login", timeout=120000)
        orv = page.evaluate(
            """async () => {
              const r = await fetch('/dev/observation-reality-validation?store=demo', {
                credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        evidence["orv_demo"] = orv
        status = page.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-reality-status', {
                credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        evidence["job_status"] = status
        session = page.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        body = session.get("body") or {}
        evidence["review_session"] = {
            "http": session.get("http"),
            "ok": body.get("ok"),
            "store_slug": body.get("store_slug"),
            "email": body.get("email"),
            "cookie_name": body.get("cookie_name"),
            "note": body.get("note"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            (OUT / "prod_home_verify_after.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return 2

        cookie = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
        desk = browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="ar-SA"
        )
        desk.add_cookies([cookie])
        home = desk.new_page()
        home.goto(f"{BASE}/dashboard#home", timeout=120000)
        home.wait_for_timeout(7000)
        probe = home.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              const hes = j.home_executive_summary_v1 || {};
              const secs = hes.sections || [];
              const by = Object.fromEntries(secs.map(s => [s.id, s]));
              const root = document.getElementById('ma-home-experience-root');
              const text = (root && root.innerText) || '';
              return {
                http: r.status,
                store_slug: j.store_slug
                  || ((j.merchant_home_experience_v1 || {}).store_slug)
                  || null,
                obs_summary: ((by.observations || {}).summary_ar) || null,
                obs_empty: (by.observations || {}).empty,
                obs_count: (by.observations || {}).count,
                text_has_raven: text.includes('Raven'),
                text_sample: text.slice(0, 900),
              };
            }"""
        )
        evidence["home_api_probe"] = probe
        home.screenshot(path=str(OUT / "prod_after_desktop_home.png"), full_page=False)
        desk.close()

        mob = browser.new_context(
            viewport={"width": 390, "height": 844}, locale="ar-SA"
        )
        mob.add_cookies([cookie])
        mpage = mob.new_page()
        mpage.goto(f"{BASE}/dashboard#home", timeout=120000)
        mpage.wait_for_timeout(6000)
        mpage.screenshot(path=str(OUT / "prod_after_mobile_home.png"), full_page=False)
        mob.close()
        browser.close()

    path = OUT / "prod_home_verify_after.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    home = evidence.get("home_api_probe") or {}
    print(
        json.dumps(home, ensure_ascii=True, indent=2),
        flush=True,
    )
    empty = home.get("obs_empty")
    empty_false = empty is False or str(empty).lower() == "false"
    ok = (
        home.get("store_slug") == "demo"
        and empty_false
        and int(home.get("obs_count") or 0) > 0
        and bool(home.get("text_has_raven"))
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
