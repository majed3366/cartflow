# -*- coding: utf-8 -*-
"""Living Store Desktop/Mobile shots for Decision Workspace Refinement V2."""
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
    / "decision_workspace_refinement_v2"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "foundation": "decision_workspace_refinement_v2",
        "base": BASE,
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
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        body = session.get("body") or {}
        report["review_session"] = {
            "http": session.get("http"),
            "ok": body.get("ok"),
            "store_slug": body.get("store_slug"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_SESSION"
            (OUT / "prod_shots_meta.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
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
        samples = []
        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(
                viewport={"width": w, "height": h}, locale="ar-SA"
            )
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / f"prod_{mode}_home.png"), full_page=False)
            page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
            page.wait_for_timeout(5000)
            probe = page.evaluate(
                """async () => {
                  const r = await fetch(
                    '/api/cart-workspace/v1/projection?_=' + Date.now(),
                    { credentials: 'same-origin', cache: 'no-store' }
                  );
                  const j = await r.json().catch(() => ({}));
                  const p = j.projection || {};
                  const cards = p.zone_b || [];
                  const primary = cards.find(c => c && c.is_primary_decision) || cards[0] || {};
                  const host = document.getElementById('cw-merchant-host');
                  const q = document.getElementById('cw-constitution-question');
                  const text = (host && host.innerText) || '';
                  return {
                    http: r.status,
                    ok: !!j.ok,
                    refinement_v2: !!p.decision_workspace_refinement_v2,
                    mission: p.mission_question || null,
                    question_ui: (q && q.textContent) || null,
                    primary_readiness: primary.execution_readiness || null,
                    primary_domain: primary.execution_domain || null,
                    primary_href: primary.view_details_href || null,
                    primary_cta: primary.view_details_ar || null,
                    has_readiness_ui: text.includes('جاهزية التنفيذ'),
                    has_verify_ui: text.includes('كيف يتحقق'),
                    has_where_ui: text.includes('أين تنفّذ') || text.includes('أين تنفذ'),
                    loops_workspace: !!(primary.view_details_href || '').startsWith('#workspace'),
                    text_sample: text.slice(0, 1200),
                  };
                }"""
            )
            samples.append({"mode": mode, **probe})
            page.screenshot(
                path=str(OUT / f"prod_{mode}_workspace.png"), full_page=False
            )
            ctx.close()
        browser.close()

    report["samples"] = samples
    report["checks"] = {
        "all_ok": all(s.get("ok") for s in samples),
        "refinement_v2": all(s.get("refinement_v2") for s in samples),
        "methodology_ui": all(
            s.get("has_readiness_ui") and s.get("has_verify_ui") for s in samples
        ),
        "no_workspace_loop": all(not s.get("loops_workspace") for s in samples),
    }
    report["verdict"] = (
        "PASS_WORKSPACE_REFINEMENT_V2_SHOTS"
        if all(report["checks"].values())
        else "FAIL_WORKSPACE_REFINEMENT_V2_SHOTS"
    )
    (OUT / "prod_shots_meta.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"]}, indent=2))
    for s in samples:
        print(
            f"{s['mode']}: readiness={s.get('primary_readiness')} domain={s.get('primary_domain')} "
            f"href={s.get('primary_href')} cta={s.get('primary_cta')}"
        )
    return 0 if str(report["verdict"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
