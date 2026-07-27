# -*- coding: utf-8 -*-
"""Home Constitution V2 — production Home-only CEO review probe (Living Store demo)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "home_constitution_v2"
HOME_Q = "ماذا يجب أن أعرف الآن عن متجري؟"
FORBIDDEN_CHROME = (
    "ملخص تنفيذي",
    "ملخص سريع فقط",
    "الرئيسية تقدّم ما يهم أولاً",
    "مرحباً",
)
FORBIDDEN_STATUS = ("القرار الأهم", "منتج", "مكتمل اليوم")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "constitution": "home_constitution_v2",
        "scope": "home_only",
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
            "email": body.get("email"),
            "password_issued": bool(body.get("password_once")),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            (OUT / "prod_home_ceo_review.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print("FAIL: no review session cookie")
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

        def capture(label: str, width: int, height: int) -> dict:
            ctx = browser.new_context(
                viewport={"width": width, "height": height}, locale="ar-SA"
            )
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            try:
                page.wait_for_selector('[data-hes="1"]', timeout=90000)
            except Exception:
                page.wait_for_timeout(12000)
            page.wait_for_timeout(800)
            data = page.evaluate(
                """async () => {
                  const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                    credentials: 'same-origin', cache: 'no-store'
                  });
                  const j = await r.json().catch(() => ({}));
                  const hes = j.home_executive_summary_v1 || {};
                  const secs = Array.isArray(hes.sections) ? hes.sections : [];
                  const root = document.getElementById('ma-home-experience-root');
                  const purpose = document.getElementById('pagePurpose');
                  const greeting = document.getElementById('ma-home-greeting-shell');
                  const counts = root
                    ? root.querySelectorAll('[data-hes-count]').length
                    : -1;
                  const eyebrow = root
                    ? root.querySelectorAll('.hes-eyebrow').length
                    : -1;
                  const lede = root ? root.querySelectorAll('.hes-lede').length : -1;
                  const footer = root
                    ? root.querySelectorAll('.hes-ownership').length
                    : -1;
                  const sitItemCta = root
                    ? root.querySelectorAll('.hes-situation-card__meta a').length
                    : -1;
                  const sectionCtas = root
                    ? root.querySelectorAll('[data-hes-view-details]').length
                    : -1;
                  return {
                    http: r.status,
                    store_slug: j.store_slug || null,
                    home_surface_mode: j.home_surface_mode || null,
                    constitution: hes.constitution || null,
                    title_ar: hes.title_ar || null,
                    eyebrow_ar: hes.eyebrow_ar || null,
                    lede_ar: hes.lede_ar || null,
                    section_ids: secs.map(s => s.id),
                    sections: secs.map(s => ({
                      id: s.id,
                      title_ar: s.title_ar,
                      summary_ar: s.summary_ar,
                      status_ar: s.status_ar || null,
                      has_count: Object.prototype.hasOwnProperty.call(s, 'count'),
                      view_details_href: s.view_details_href,
                      empty: !!s.empty,
                    })),
                    page_purpose: purpose ? (purpose.textContent || '').trim() : null,
                    greeting_present: !!(greeting && !greeting.closest('[hidden]')),
                    ui: {
                      count_badges: counts,
                      eyebrow_nodes: eyebrow,
                      lede_nodes: lede,
                      ownership_footer: footer,
                      situation_item_ctas: sitItemCta,
                      section_view_details: sectionCtas,
                      root_text: ((root && root.innerText) || '').slice(0, 1200),
                    },
                  };
                }"""
            )
            shot = OUT / f"prod_{label}_home.png"
            page.screenshot(path=str(shot), full_page=False)
            data["screenshot"] = str(shot.relative_to(OUT.parent.parent.parent))
            ctx.close()
            return data

        desk = capture("desktop", 1440, 900)
        mob = capture("mobile", 390, 844)
        browser.close()

    report["desktop"] = desk
    report["mobile"] = mob

    flags: list[str] = []
    for label, snap in (("desktop", desk), ("mobile", mob)):
        if snap.get("store_slug") != "demo":
            flags.append(f"{label}:store_slug!={snap.get('store_slug')}")
        if snap.get("home_surface_mode") != "executive_summary_v1":
            flags.append(f"{label}:surface_mode")
        if snap.get("page_purpose") != HOME_Q:
            flags.append(f"{label}:page_purpose")
        # Question must not be duplicated as HES h2 chrome.
        root_text = ((snap.get("ui") or {}).get("root_text") or "")
        if HOME_Q in root_text:
            flags.append(f"{label}:question_duplicated_in_hes")
        for chrome in FORBIDDEN_CHROME:
            if chrome in root_text:
                flags.append(f"{label}:chrome:{chrome[:20]}")
        ui = snap.get("ui") or {}
        if int(ui.get("count_badges") or 0) > 0:
            flags.append(f"{label}:count_badges")
        if int(ui.get("eyebrow_nodes") or 0) > 0:
            flags.append(f"{label}:eyebrow")
        if int(ui.get("lede_nodes") or 0) > 0:
            flags.append(f"{label}:lede")
        if int(ui.get("ownership_footer") or 0) > 0:
            flags.append(f"{label}:footer")
        if int(ui.get("situation_item_ctas") or 0) > 0:
            flags.append(f"{label}:dup_situation_cta")
        ids = snap.get("section_ids") or []
        if not ids or ids[0] != "health":
            flags.append(f"{label}:health_first")
        if "decisions" not in ids:
            flags.append(f"{label}:missing_decisions")
        if len(ids) > 5:
            flags.append(f"{label}:over_budget")
        for sec in snap.get("sections") or []:
            if sec.get("has_count"):
                flags.append(f"{label}:payload_count:{sec.get('id')}")
            st = sec.get("status_ar") or ""
            if st in FORBIDDEN_STATUS:
                flags.append(f"{label}:status:{st}")
            summary = sec.get("summary_ar") or ""
            if re.match(r"^\d", summary):
                flags.append(f"{label}:count_first:{sec.get('id')}")
            href = sec.get("view_details_href") or ""
            sid = sec.get("id")
            if sid == "health" and href not in {
                "#workspace",
                "#communication",
                "#settings",
            }:
                flags.append(f"{label}:health_href:{href}")
            if sid == "decisions" and href != "#workspace":
                flags.append(f"{label}:decisions_href")
            if sid == "carts" and href != "#carts":
                flags.append(f"{label}:carts_href")
            if sid == "communication" and href != "#communication":
                flags.append(f"{label}:comm_href")
        vd = int(ui.get("section_view_details") or 0)
        if vd > 5:
            flags.append(f"{label}:too_many_view_details")

    # Desktop/Mobile meaning parity: same section ids + summaries.
    d_secs = {
        s["id"]: (s.get("summary_ar"), s.get("status_ar"))
        for s in (desk.get("sections") or [])
    }
    m_secs = {
        s["id"]: (s.get("summary_ar"), s.get("status_ar"))
        for s in (mob.get("sections") or [])
    }
    if d_secs != m_secs:
        flags.append("parity:desktop_mobile_mismatch")

    report["flags"] = flags
    report["verdict"] = "PASS_HOME_CONSTITUTION_V2" if not flags else "FAIL_HOME_CONSTITUTION_V2"
    path = OUT / "prod_home_ceo_review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(report["verdict"])
    print(json.dumps({"flags": flags, "section_ids": desk.get("section_ids")}, ensure_ascii=False))
    return 0 if not flags else 2


if __name__ == "__main__":
    raise SystemExit(main())
