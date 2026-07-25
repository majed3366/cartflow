# -*- coding: utf-8 -*-
"""
Execute Living Store on production demo, bind Home review session, capture proof.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "observation_admission_bridge_v1"


def _get_json(page, path: str) -> dict:
    return page.evaluate(
        """async (path) => {
          const r = await fetch(path, { credentials: 'same-origin', cache: 'no-store' });
          const j = await r.json().catch(() => ({}));
          return { http: r.status, body: j };
        }""",
        path,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(f"{BASE}/login", timeout=120000)
        page.wait_for_timeout(800)

        before = _get_json(page, "/dev/observation-reality-validation?store=demo")
        evidence["orv_before"] = before

        start = page.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-reality-run', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        evidence["run_start"] = start

        deadline = time.time() + 900
        job = {}
        while time.time() < deadline:
            st = _get_json(page, "/dev/living-store-reality-status")
            job = (st.get("body") or {}).get("job") or {}
            status = str(job.get("status") or "")
            print("job_status", status, flush=True)
            if status in ("completed", "failed", "idle") and status != "idle":
                break
            if status == "idle" and evidence.get("run_start", {}).get("body", {}).get(
                "ok"
            ):
                # race: status not yet flipped
                time.sleep(2)
                continue
            if status == "failed":
                break
            if status == "completed":
                break
            time.sleep(5)
        evidence["job_final"] = job

        after = _get_json(page, "/dev/observation-reality-validation?store=demo")
        evidence["orv_after"] = after

        session = page.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        evidence["review_session"] = {
            "http": session.get("http"),
            "store_slug": ((session.get("body") or {}).get("store_slug")),
            "email": ((session.get("body") or {}).get("email")),
            "cookie_name": ((session.get("body") or {}).get("cookie_name")),
            "ok": ((session.get("body") or {}).get("ok")),
            "note": ((session.get("body") or {}).get("note")),
        }
        body = session.get("body") or {}
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if cookie_name and cookie_value:
            browser_ctx = browser.new_context(
                viewport={"width": 1440, "height": 900}, locale="ar-SA"
            )
            browser_ctx.add_cookies(
                [
                    {
                        "name": cookie_name,
                        "value": cookie_value,
                        "domain": "smartreplyai.net",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax",
                    }
                ]
            )
            home = browser_ctx.new_page()
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
            home.screenshot(
                path=str(OUT / "prod_after_desktop_home.png"), full_page=False
            )
            mobile_ctx = browser.new_context(
                viewport={"width": 390, "height": 844}, locale="ar-SA"
            )
            if cookie_name and cookie_value:
                mobile_ctx.add_cookies(
                    [
                        {
                            "name": cookie_name,
                            "value": cookie_value,
                            "domain": "smartreplyai.net",
                            "path": "/",
                            "httpOnly": True,
                            "secure": True,
                            "sameSite": "Lax",
                        }
                    ]
                )
            mobile = mobile_ctx.new_page()
            mobile.goto(f"{BASE}/dashboard#home", timeout=120000)
            mobile.wait_for_timeout(6000)
            mobile.screenshot(
                path=str(OUT / "prod_after_mobile_home.png"), full_page=False
            )
            mobile_ctx.close()
            browser_ctx.close()

        browser.close()

    path = OUT / "prod_home_verify_after.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    try:
        print(json.dumps(evidence, ensure_ascii=False, indent=2)[:4000])
    except UnicodeEncodeError:
        print(json.dumps(evidence, ensure_ascii=True, indent=2)[:4000])
    job_ok = (evidence.get("job_final") or {}).get("status") == "completed"
    home = evidence.get("home_api_probe") or {}
    visual_ok = (
        home.get("store_slug") == "demo"
        and home.get("obs_empty") is False
        and int(home.get("obs_count") or 0) > 0
    )
    return 0 if job_ok and visual_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
