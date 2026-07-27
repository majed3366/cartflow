# -*- coding: utf-8 -*-
"""Diagnostic Reasoning V1 — production Home-only CEO probe."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "diagnostic_reasoning_v1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "foundation": "diagnostic_reasoning_v1",
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
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            print("FAIL: no review session")
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
            t0 = time.perf_counter()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            try:
                page.wait_for_selector('[data-hes="1"]', timeout=90000)
            except Exception:
                page.wait_for_timeout(12000)
            page.wait_for_timeout(600)
            nav_ms = round((time.perf_counter() - t0) * 1000, 1)
            data = page.evaluate(
                """async () => {
                  const t0 = performance.now();
                  const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                    credentials: 'same-origin', cache: 'no-store'
                  });
                  const j = await r.json().catch(() => ({}));
                  const api_ms = Math.round(performance.now() - t0);
                  const hes = j.home_executive_summary_v1 || {};
                  const dx = j.diagnostic_publication_v1 || null;
                  const secs = Array.isArray(hes.sections) ? hes.sections : [];
                  const root = document.getElementById('ma-home-experience-root');
                  return {
                    http: r.status,
                    api_ms,
                    store_slug: j.store_slug || null,
                    diagnostic_snapshot_read_ms: j.diagnostic_snapshot_read_ms,
                    diagnostic_publication: dx ? {
                      diagnosis_ar: dx.diagnosis_ar,
                      recommendation_ar: dx.recommendation_ar,
                      diagnosis_status: dx.diagnosis_status,
                      family: dx.diagnostic_family,
                      freshness: dx.freshness,
                    } : null,
                    hes_diagnostic_reasoning: hes.diagnostic_reasoning || null,
                    diagnosis_language: hes.diagnosis_language || null,
                    sections: secs.map(s => ({
                      id: s.id,
                      diagnosis_ar: s.diagnosis_ar || null,
                      recommendation_ar: s.recommendation_ar || null,
                    })),
                    root_text: ((root && root.innerText) || '').slice(0, 1400),
                  };
                }"""
            )
            data["nav_ms"] = nav_ms
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
            flags.append(f"{label}:store")
        text = ((snap.get("root_text") or "") + " " + json.dumps(snap.get("sections") or [], ensure_ascii=False))
        if "يعتقد CartFlow" in text or "CartFlow believes" in text:
            flags.append(f"{label}:cartflow_believes")
        if "راجع مسار التحويل" in text:
            flags.append(f"{label}:conversion_path")
        # Prefer evidence language or honest insufficiency
        diags = [s.get("diagnosis_ar") or "" for s in (snap.get("sections") or [])]
        if not any(diags):
            flags.append(f"{label}:no_diagnosis")
        for d in diags:
            if d.startswith("راجع"):
                flags.append(f"{label}:rec_first")
        # Stage observation must not claim shipping_cost without publication support.
        pub = snap.get("diagnostic_publication") or {}
        if (
            "تكلفة الشحن هي السبب" in text
            and str(pub.get("diagnosis_status") or "") != "supported"
            and str(pub.get("family") or "") != ""
        ):
            flags.append(f"{label}:unsupported_shipping_cost_claim")

    d_map = {
        s["id"]: (s.get("diagnosis_ar"), s.get("recommendation_ar"))
        for s in (desk.get("sections") or [])
    }
    m_map = {
        s["id"]: (s.get("diagnosis_ar"), s.get("recommendation_ar"))
        for s in (mob.get("sections") or [])
    }
    if d_map != m_map:
        flags.append("parity_mismatch")

    report["flags"] = flags
    report["latency"] = {
        "desktop_api_ms": desk.get("api_ms"),
        "mobile_api_ms": mob.get("api_ms"),
        "desktop_diagnostic_read_ms": desk.get("diagnostic_snapshot_read_ms"),
        "mobile_diagnostic_read_ms": mob.get("diagnostic_snapshot_read_ms"),
    }
    report["verdict"] = (
        "PASS_DIAGNOSTIC_REASONING_V1" if not flags else "FAIL_DIAGNOSTIC_REASONING_V1"
    )
    path = OUT / "prod_home_ceo_review.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(report["verdict"])
    print(json.dumps({"flags": flags, "latency": report["latency"]}, ensure_ascii=False))
    return 0 if not flags else 2


if __name__ == "__main__":
    raise SystemExit(main())
