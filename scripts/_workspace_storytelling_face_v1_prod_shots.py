# -*- coding: utf-8 -*-
"""Living Store shots for Workspace Storytelling Face V1."""
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
    / "decision_workspace_storytelling_face_v1"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "foundation": "decision_workspace_storytelling_face_v1",
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
            page.wait_for_timeout(3500)
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
                  const text = (host && host.innerText) || '';
                  return {
                    http: r.status,
                    ok: !!j.ok,
                    storytelling: !!p.decision_workspace_storytelling_face_v1,
                    readiness: primary.execution_readiness || null,
                    action_ready: !!primary.execution_available,
                    href: primary.view_details_href || null,
                    priority: primary.priority_reason_ar || null,
                    observation: primary.observation_ar || null,
                    decision: primary.decision_sentence_ar || null,
                    has_mulahaza: text.includes('الملاحظة') || text.includes('ملاحظة'),
                    has_meaning: text.includes('المعنى التشغيلي'),
                    has_continues: text.includes('ما يواصل CartFlow'),
                    has_cs: text.includes('cs:'),
                    has_diagnostic: text.includes('diagnostic:'),
                    has_priority_rank: text.includes('الأولوية الأولى'),
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
        "storytelling": all(s.get("storytelling") for s in samples),
        "no_report_labels": all(
            (not s.get("has_mulahaza"))
            and (not s.get("has_meaning"))
            and (not s.get("has_continues"))
            for s in samples
        ),
        "no_engine_ids": all(
            (not s.get("has_cs")) and (not s.get("has_diagnostic")) for s in samples
        ),
        "priority_rank": all(s.get("has_priority_rank") for s in samples),
        "no_fake_action_when_waiting": all(
            s.get("readiness") != "NEEDS_MORE_EVIDENCE" or not (s.get("href") or "").strip()
            for s in samples
        ),
    }
    report["checks"]["all_pass"] = all(report["checks"].values())
    report["verdict"] = (
        "PASS_WORKSPACE_STORYTELLING_FACE_V1_SHOTS"
        if report["checks"]["all_pass"]
        else "FAIL_WORKSPACE_STORYTELLING_FACE_V1_SHOTS"
    )
    (OUT / "prod_shots_meta.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"]}, ensure_ascii=False, indent=2))
    for s in samples:
        print(
            f"{s['mode']}: readiness={s.get('readiness')} action={s.get('action_ready')} "
            f"href={s.get('href')!r}"
        )
    return 0 if report["checks"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
