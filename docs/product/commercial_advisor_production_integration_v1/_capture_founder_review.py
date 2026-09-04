# -*- coding: utf-8 -*-
"""Capture founder_review_v1 — Commercial Advisor Production Integration V1."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from services.commercial_opportunity_layer_v1.compose_v1 import (  # noqa: E402
    compose_commercial_opportunity_layer_v1,
)

OUT = Path(__file__).resolve().parent / "founder_review_v1"
DESKTOP = Path(
    r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Commercial_Advisor_Production_Integration_V1"
)
STATIC = ROOT / "static"


def _hes() -> dict:
    return {
        "ok": True,
        "enabled": True,
        "lede_ar": "معرفة المتجر جاهزة.",
        "sections": [
            {
                "id": "ops_primary",
                "zone": "primary",
                "title_ar": "سلال بانتظار متابعة",
                "truth_ar": "هناك سلال تحتاج انتباهًا تشغيليًا الآن.",
                "recommendation_ar": "راجع السلال ذات الأولوية — منفصلة عن الفرصة التجارية.",
                "view_details_href": "#workspace",
            },
            {
                "id": "know_1",
                "zone": "know",
                "title_ar": "التواصل",
                "truth_ar": "قناة واتساب جاهزة.",
            },
        ],
    }


def _col_ready() -> dict:
    return compose_commercial_opportunity_layer_v1(
        {
            "store_slug": "prod_cda_founder",
            "merchant_reason_counts_week": {
                "shipping": 14,
                "price": 7,
                "thinking": 4,
            },
        }
    )


def _col_empty() -> dict:
    return compose_commercial_opportunity_layer_v1(
        {"store_slug": "prod_cda_founder", "merchant_reason_counts_week": {}}
    )


def _shell(body: str) -> str:
    home_css = (STATIC / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
    ws_css = (STATIC / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
    cda_css = (STATIC / "commercial_decision_arc_production_v1.css").read_text(
        encoding="utf-8"
    )
    base = """
:root { --cf2-ink:#1a2332; --cf2-muted:#5a6577; --cf2-bg:#f7f5f1; }
html,body{margin:0;padding:0;background:var(--cf2-bg);color:var(--cf2-ink);
font-family:"Segoe UI",Tahoma,Arial,sans-serif;direction:rtl;}
.cf2-btn{display:inline-block;padding:10px 16px;background:var(--cf2-ink);color:#fff;
text-decoration:none;border-radius:4px;font-weight:600;font-size:0.9rem;}
.cf2-page{max-width:920px;margin:0 auto;padding:20px 16px 48px;}
.cf2-page__question{font-size:1.12rem;font-weight:700;margin:0 0 16px;}
.cf2-shell-bar{font-size:0.72rem;font-weight:700;color:var(--cf2-muted);margin:0 0 8px;
letter-spacing:0.04em;text-transform:uppercase;}
"""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>{base}\n{home_css}\n{ws_css}\n{cda_css}</style></head>
<body data-cf-ui="v2">
<main class="cf2-page">
<p class="cf2-shell-bar">CartFlow Merchant UI V2 · Production Integration</p>
<p class="cf2-page__question">ماذا يجب أن أعرف الآن عن متجري؟</p>
{body}
</main></body></html>"""


STUBS = """
window.CartFlowUiV2Lang = {
  esc: function(s){ return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); },
  evidenceFieldFromSufficiency: function(){ return ''; }
};
window.CartFlowSemanticVisualV1 = {
  projectHomeSurface: function(){
    return { core_silence:'ACTIVE', density:'DENSE', attention_intensity:'PRIMARY',
      evidence_sufficiency:'SUFFICIENT', wait_kind:'NONE' };
  },
  projectWorkspaceSurface: function(){
    return { core_silence:'ACTIVE', density:'DENSE', attention_intensity:'PRIMARY',
      evidence_sufficiency:'SUFFICIENT', wait_kind:'NONE' };
  }
};
"""


def paint_home(page, summary: dict, paint_opts: dict | None = None) -> None:
    cda = (STATIC / "commercial_decision_arc_production_v1.js").read_text(encoding="utf-8")
    home = (STATIC / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
    page.add_script_tag(content=STUBS)
    page.add_script_tag(content=cda)
    page.add_script_tag(content=home)
    page.evaluate(
        """([summary, opts]) => {
          window.CartFlowUiV2Home.paint(
            document.getElementById('home-root'), summary, opts || {});
        }""",
        [summary, paint_opts or {}],
    )


def paint_workspace(page, opp: dict, paint_opts: dict | None = None) -> None:
    cda = (STATIC / "commercial_decision_arc_production_v1.js").read_text(encoding="utf-8")
    ws = (STATIC / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
    page.add_script_tag(content=STUBS)
    page.add_script_tag(content=cda)
    page.add_script_tag(content=ws)
    page.evaluate(
        """([opp, opts]) => {
          try { sessionStorage.setItem('cf2_col_focus_v1', JSON.stringify(opp)); } catch(e){}
          document.getElementById('ws-root').innerHTML =
            window.CartFlowUiV2Workspace.render({ projection: { zone_b: [] } }, opts || {});
        }""",
        [opp, paint_opts or {}],
    )


def capture(browser, name: str, html: str, *, kind: str, summary=None, opp=None, opts=None, expand=False):
    OUT.mkdir(parents=True, exist_ok=True)
    slot = OUT / name
    slot.mkdir(parents=True, exist_ok=True)
    for width, fname in ((390, "mobile_390.png"), (1280, "desktop_1280.png")):
        ctx = browser.new_context(
            viewport={"width": width, "height": 900 if width > 500 else 844},
            device_scale_factor=1,
        )
        page = ctx.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        if kind == "home":
            paint_home(page, summary, opts)
        elif kind == "workspace":
            paint_workspace(page, opp, opts)
        if expand:
            loc = page.locator("details.cf-cda__evidence").first
            if loc.count():
                loc.click()
        page.wait_for_timeout(220)
        page.screenshot(path=str(slot / fname), full_page=True)
        ctx.close()


def main() -> None:
    from playwright.sync_api import sync_playwright

    col = _col_ready()
    empty = _col_empty()
    hes = _hes()
    summary_full = {
        "home_executive_summary_v1": hes,
        "commercial_opportunity_layer_v1": col,
        "operational_guidance_v1": {
            "ok": True,
            "home_surface": {
                "what_we_see_ar": "أسباب شحن متكررة هذا الأسبوع.",
                "what_it_means_ar": "احتكاك عند خطوة الشحن — منفصل عن القرار التجاري.",
                "what_to_do_now_ar": "راجع السلال ذات الأولوية.",
                "when_to_recheck_ar": "بعد عيّنة تردد جديدة.",
            },
        },
    }
    summary_empty = {
        "home_executive_summary_v1": hes,
        "commercial_opportunity_layer_v1": empty,
    }
    home_html = _shell('<div id="home-root"></div>')
    ws_html = _shell(
        '<p class="cf2-page__question" style="font-size:1rem">مساحة القرار</p><div id="ws-root"></div>'
    )
    opp = col["primary"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        capture(
            browser,
            "01_home_primary",
            home_html,
            kind="home",
            summary=summary_full,
            opts={"homeArc": "action_chosen"},
        )
        capture(
            browser,
            "02_home_measurement",
            home_html,
            kind="home",
            summary=summary_full,
            opts={"homeArc": "under_measurement"},
        )
        capture(
            browser,
            "03_workspace_decision",
            ws_html,
            kind="workspace",
            opp=opp,
            opts={"workspaceArc": "action_chosen"},
        )
        capture(
            browser,
            "04_workspace_recheck",
            ws_html,
            kind="workspace",
            opp=opp,
            opts={"workspaceArc": "recheck_due"},
        )
        capture(
            browser,
            "05_insufficient_evidence",
            home_html,
            kind="home",
            summary=summary_empty,
        )
        capture(
            browser,
            "06_full_product_context",
            home_html,
            kind="home",
            summary=summary_full,
            opts={"homeArc": "action_chosen"},
            expand=True,
        )
        browser.close()

    pngs = list(OUT.rglob("*.png"))
    (OUT / "MANIFEST.md").write_text(
        "# Founder Review — Commercial Advisor Production Integration V1\n\n"
        + json.dumps(
            {
                "screenshots": len(pngs),
                "required": 12,
                "primitive": "cf-cda",
                "logic_baseline": "b1867d2c",
                "flag": "CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1",
                "deploy": False,
            },
            indent=2,
        )
        + "\n\n## Founder questions\n\n"
        "1. هل CartFlow الحقيقي بدأ يبدو كمنظومة قرار تجاري؟\n"
        "2. هل cf-cda يعيش داخل المنتج؟\n"
        "3. هل Operational ≠ Commercial واضحان؟\n"
        "4. هل القرار أهم من الدليل؟\n"
        "5. هل القياس وإعادة النظر مفهومان؟\n"
        "6. هل Workspace أقرب إلى Decision System؟\n"
        "7. هل secondaries أخف؟\n"
        "8. هل الموبايل يحتفظ بالشخصية؟\n"
        "9. هل insufficient evidence ذكاء؟\n"
        "10. هل الهوية تحسّن المنتج لا تحوّله لمعرض؟\n",
        encoding="utf-8",
    )

    DESKTOP.mkdir(parents=True, exist_ok=True)
    for child in list(DESKTOP.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for item in OUT.iterdir():
        dest = DESKTOP / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    print("wrote", OUT, "pngs", len(pngs))
    print("desktop", DESKTOP)


if __name__ == "__main__":
    main()
