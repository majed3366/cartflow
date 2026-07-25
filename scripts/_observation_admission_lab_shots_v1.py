# -*- coding: utf-8 -*-
"""Desktop/Mobile shots from composed HES after Observation Admission (living-store DB)."""
from __future__ import annotations

import html
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "observation_admission_bridge_v1"
SEED = 20260725
DB = Path(tempfile.gettempdir()) / f"cartflow_living_store_v1_{SEED}.db"
SIM_END = datetime(2026, 5, 31, 18, 0, 0, tzinfo=timezone.utc)


def main() -> int:
    if not DB.exists():
        print("missing living store db — run scripts/living_store_reality_v1.py first")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = "sqlite:///" + str(DB).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_OBSERVATION_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1", "1")
    os.environ.setdefault("CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1", "1")
    os.environ.setdefault("CARTFLOW_HOME_SLIM_TRANSPORT_V1", "1")

    import models  # noqa: F401
    from extensions import db, init_database

    init_database()
    db.create_all()

    from services.home_executive_summary_v1.compose_v1 import (
        build_home_executive_summary_v1,
    )
    from services.home_executive_summary_v1.slim_transport_v1 import (
        extract_home_teaser_inputs_v1,
    )
    from services.observation_foundation_v1.merchant_findings_v1 import (
        build_observation_reality_validation_v1,
    )
    from services.time_authority.authority import use_provider
    from services.time_authority.providers import FixedAsOfProvider

    with use_provider(FixedAsOfProvider(SIM_END)):
        orv = build_observation_reality_validation_v1("demo")
        teasers = extract_home_teaser_inputs_v1(
            {
                "store_slug": "demo",
                "observation_reality_validation_v1": orv,
                "merchant_nav_badge_abandoned": 135,
                "merchant_store_cart_counts": {
                    "waiting_total": 135,
                    "no_phone_total": 0,
                    "active_total": 135,
                },
            }
        )
        hes = build_home_executive_summary_v1(
            {
                "store_slug": "demo",
                "home_teaser_inputs_v1": teasers,
                "observation_reality_validation_v1": orv,
            }
        )

    cards = []
    for s in hes.get("sections") or []:
        cards.append(
            f"""
            <section class="card" data-id="{html.escape(str(s.get('id') or ''))}">
              <h2>{html.escape(str(s.get('title_ar') or ''))}</h2>
              <p class="summary">{html.escape(str(s.get('summary_ar') or ''))}</p>
              <div class="meta">
                <span class="status">{html.escape(str(s.get('status_ar') or ''))}</span>
                <a href="#workspace">عرض التفاصيل ←</a>
              </div>
            </section>
            """
        )
    ws_rows = []
    for d in orv.get("workspace_decisions") or []:
        ws_rows.append(
            f"""
            <article class="decision">
              <h3>{html.escape(str(d.get('merchant_decision') or d.get('title') or ''))}</h3>
              <p><strong>لماذا؟</strong> {html.escape(str(d.get('why') or ''))}</p>
              <p><strong>الأدلة</strong> {html.escape(str(d.get('evidence') or ''))}</p>
              <p><strong>الثقة</strong> {html.escape(str(d.get('confidence_ar') or ''))}</p>
              <p><strong>الإجراء</strong> {html.escape(str(d.get('recommended_action') or ''))}</p>
            </article>
            """
        )

    page_html = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<title>Observation Admission Bridge V1</title>
<style>
  body {{ font-family: "Segoe UI", Tahoma, sans-serif; background:#f4f7f5; color:#14231c; margin:0; }}
  header {{ background:#0f3d2e; color:#fff; padding:16px 24px; }}
  header .brand {{ font-weight:700; font-size:20px; }}
  main {{ max-width:920px; margin:0 auto; padding:24px; }}
  h1 {{ font-size:28px; margin:8px 0 4px; }}
  .lede {{ color:#5a6b62; margin-bottom:20px; }}
  .card {{ background:#fff; border:1px solid #d7e0db; border-radius:12px; padding:16px 18px; margin:12px 0; }}
  .card h2 {{ margin:0 0 8px; font-size:18px; }}
  .summary {{ margin:0 0 12px; line-height:1.6; }}
  .meta {{ display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:14px; }}
  .status {{ background:#e8f2ec; padding:4px 10px; border-radius:999px; }}
  a {{ color:#0f3d2e; }}
  .decision {{ background:#fff; border:1px solid #d7e0db; border-radius:12px; padding:16px; margin:12px 0; }}
  .decision h3 {{ margin-top:0; }}
</style>
</head>
<body>
<header><div class="brand">CartFlow · Observation Admission Bridge V1</div></header>
<main>
  <div class="lede">ملخص تنفيذي</div>
  <h1>ماذا يجب أن تعرف الآن؟</h1>
  <p class="lede">ملخص سريع فقط — التفاصيل في صفحاتها.</p>
  {''.join(cards)}
  <h1 style="margin-top:36px">مساحة القرار — قرارات الملاحظة</h1>
  <p class="lede">فقط الملاحظات المؤهلة لقرار (ليست كل الملاحظات).</p>
  {''.join(ws_rows) if ws_rows else '<p>لا قرارات ملاحظة حالياً.</p>'}
</main>
</body>
</html>
"""
    html_path = OUT / "_lab_render.html"
    html_path.write_text(page_html, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page.goto(html_path.as_uri(), timeout=60000)
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "after_desktop_home.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "after_mobile_home.png"), full_page=False)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "after_desktop_workspace.png"), full_page=False)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "after_mobile_workspace.png"), full_page=False)
        browser.close()

    obs = next((s for s in (hes.get("sections") or []) if s.get("id") == "observations"), {})
    recon = orv.get("admission_reconciliation") or {}
    ok = (
        int(orv.get("count") or 0) >= 1
        and not obs.get("empty")
        and int(recon.get("silent_drops") or 0) == 0
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db": str(DB),
        "orv_count": orv.get("count"),
        "present_capabilities": orv.get("present_capabilities"),
        "admission_reconciliation": recon,
        "suppressed_by_reason": orv.get("suppressed_by_reason"),
        "workspace_decision_count": len(orv.get("workspace_decisions") or []),
        "hes_observations": {
            "summary_ar": obs.get("summary_ar"),
            "count": obs.get("count"),
            "empty": obs.get("empty"),
        },
        "findings": [
            {
                "product": f.get("product_name_ar"),
                "capability": f.get("capability_id"),
                "statement": f.get("statement_ar"),
            }
            for f in (orv.get("findings") or [])
        ],
        "screenshots": {
            "desktop_home": "docs/product/observation_admission_bridge_v1/after_desktop_home.png",
            "mobile_home": "docs/product/observation_admission_bridge_v1/after_mobile_home.png",
            "desktop_workspace": "docs/product/observation_admission_bridge_v1/after_desktop_workspace.png",
            "mobile_workspace": "docs/product/observation_admission_bridge_v1/after_mobile_workspace.png",
        },
        "ok": ok,
        "status": "AWAITING_CEO_REVIEW" if ok else "NEEDS_FIX",
        "note": "Rendered from live admission→teaser→HES compose against Living Store DB (not invented copy).",
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    (OUT / "after_verification.json").write_text(text, encoding="utf-8")
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "backslashreplace").decode("ascii"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
