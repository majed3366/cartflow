# -*- coding: utf-8 -*-
"""Home Diagnosis Language V1 — production Home-only CEO review probe."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "home_diagnosis_language_v1"
HOME_Q = "ماذا يجب أن أعرف الآن عن متجري؟"
FORBIDDEN_OPENERS = ("راجع ", "راجع", "اذهب ", "افتح ", "اضبط ")
DIAG_OPENERS = (
    "يعتقد CartFlow",
    "أقوى الأدلة",
    "تشير الأدلة",
    "لا يستطيع CartFlow",
    "يظهر العملاء",
    "يغادر العملاء",
    "يعود العملاء",
    "الأدلة ما زالت",
    "لا يمكن التواصل",
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "diagnosis_language": "home_diagnosis_language_v1",
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
                  return {
                    http: r.status,
                    store_slug: j.store_slug || null,
                    home_surface_mode: j.home_surface_mode || null,
                    constitution: hes.constitution || null,
                    diagnosis_language: hes.diagnosis_language || null,
                    section_ids: secs.map(s => s.id),
                    sections: secs.map(s => ({
                      id: s.id,
                      title_ar: s.title_ar,
                      diagnosis_ar: s.diagnosis_ar || null,
                      recommendation_ar: s.recommendation_ar || null,
                      summary_ar: s.summary_ar,
                      status_ar: s.status_ar || null,
                      view_details_href: s.view_details_href,
                    })),
                    page_purpose: purpose ? (purpose.textContent || '').trim() : null,
                    ui: {
                      diagnosis_nodes: root
                        ? root.querySelectorAll('[data-hes-diagnosis]').length
                        : -1,
                      recommendation_nodes: root
                        ? root.querySelectorAll('[data-hes-recommendation]').length
                        : -1,
                      marker: root
                        ? !!(root.querySelector('[data-diagnosis-language=\"home_diagnosis_language_v1\"]'))
                        : false,
                      root_text: ((root && root.innerText) || '').slice(0, 1600),
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
            flags.append(f"{label}:store_slug")
        if snap.get("diagnosis_language") != "home_diagnosis_language_v1":
            flags.append(f"{label}:diagnosis_marker")
        if not (snap.get("ui") or {}).get("marker"):
            flags.append(f"{label}:ui_marker")
        if snap.get("page_purpose") != HOME_Q:
            flags.append(f"{label}:page_purpose")
        ui = snap.get("ui") or {}
        if int(ui.get("diagnosis_nodes") or 0) < 1:
            flags.append(f"{label}:no_diagnosis_nodes")
        if int(ui.get("recommendation_nodes") or 0) < 1:
            flags.append(f"{label}:no_recommendation_nodes")
        for sec in snap.get("sections") or []:
            diag = (sec.get("diagnosis_ar") or "").strip()
            rec = (sec.get("recommendation_ar") or "").strip()
            if not diag:
                flags.append(f"{label}:missing_diagnosis:{sec.get('id')}")
                continue
            if any(diag.startswith(p) for p in FORBIDDEN_OPENERS):
                flags.append(f"{label}:forbidden_opener:{sec.get('id')}")
            if not any(diag.startswith(p) for p in DIAG_OPENERS):
                flags.append(f"{label}:weak_diagnosis_opener:{sec.get('id')}")
            if not rec:
                flags.append(f"{label}:missing_recommendation:{sec.get('id')}")
            # Observation-only interest line must not be the diagnosis.
            if re.search(r"اهتمام مرتفع دون شراء", diag):
                flags.append(f"{label}:event_summary:{sec.get('id')}")

    d_secs = {
        s["id"]: (s.get("diagnosis_ar"), s.get("recommendation_ar"))
        for s in (desk.get("sections") or [])
    }
    m_secs = {
        s["id"]: (s.get("diagnosis_ar"), s.get("recommendation_ar"))
        for s in (mob.get("sections") or [])
    }
    if d_secs != m_secs:
        flags.append("parity:desktop_mobile_mismatch")

    report["flags"] = flags
    report["verdict"] = (
        "PASS_HOME_DIAGNOSIS_LANGUAGE_V1" if not flags else "FAIL_HOME_DIAGNOSIS_LANGUAGE_V1"
    )
    path = OUT / "prod_home_ceo_review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(report["verdict"])
    print(
        json.dumps(
            {
                "flags": flags,
                "section_ids": desk.get("section_ids"),
                "sample": [
                    {
                        "id": s.get("id"),
                        "diagnosis_ar": s.get("diagnosis_ar"),
                        "recommendation_ar": s.get("recommendation_ar"),
                    }
                    for s in (desk.get("sections") or [])
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if not flags else 2


if __name__ == "__main__":
    raise SystemExit(main())
