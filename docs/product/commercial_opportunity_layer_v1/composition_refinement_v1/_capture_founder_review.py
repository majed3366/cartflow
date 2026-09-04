# -*- coding: utf-8 -*-
"""Capture Composition Refinement V1 founder_review screenshots (10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from services.commercial_opportunity_layer_v1.compose_v1 import (  # noqa: E402
    compose_commercial_opportunity_layer_v1,
)

OUT = Path(__file__).resolve().parent / "founder_review"
STATIC = ROOT / "static"


def _hes_pkg() -> dict:
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
                "recommendation_ar": "راجع السلال ذات الأولوية.",
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


def _shell_html(body_inner: str) -> str:
    home_css = (STATIC / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
    ws_css = (STATIC / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
    base = """
:root { --cf2-ink:#1a2332; --cf2-muted:#5a6577; --cf2-bg:#f7f5f1; --cf2-paper:#fff; }
html,body { margin:0; padding:0; background:var(--cf2-bg); color:var(--cf2-ink);
  font-family: "Segoe UI", Tahoma, Arial, sans-serif; direction:rtl; }
.cf2-btn { display:inline-block; padding:10px 16px; background:var(--cf2-ink); color:#fff;
  text-decoration:none; border-radius:4px; font-weight:600; font-size:0.9rem; }
.cf2-page { max-width:920px; margin:0 auto; padding:24px 20px 48px; }
.cf2-page__question { font-size:1.15rem; font-weight:700; margin:0 0 18px; }
"""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>COL Composition Refinement V1</title>
<style>{base}\n{home_css}\n{ws_css}</style>
</head>
<body data-cf-ui="v2">
<main class="cf2-page">
<p class="cf2-page__question">ماذا يجب أن أعرف الآن عن متجري؟</p>
{body_inner}
</main>
</body></html>"""


def render_home_via_js(page, summary: dict) -> None:
    home_js = (STATIC / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
    page.add_script_tag(
        content="""
window.CartFlowUiV2Lang = {
  esc: function(s){ return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); },
  evidenceFieldFromSufficiency: function(){ return ''; }
};
window.CartFlowSemanticVisualV1 = {
  projectHomeSurface: function(){
    return { core_silence:'ACTIVE', density:'DENSE', attention_intensity:'PRIMARY',
      evidence_sufficiency:'SUFFICIENT', wait_kind:'NONE' };
  }
};
"""
    )
    page.add_script_tag(content=home_js)
    page.evaluate(
        """(summary) => {
      const root = document.getElementById('home-root');
      window.CartFlowUiV2Home.paint(root, summary);
    }""",
        summary,
    )


def capture_pair(browser, name: str, html: str, *, inject_summary=None, expand=False):
    OUT.mkdir(parents=True, exist_ok=True)
    slot = OUT / name
    slot.mkdir(parents=True, exist_ok=True)
    for width, fname in ((390, "mobile_390.png"), (1280, "desktop_1280.png")):
        context = browser.new_context(
            viewport={"width": width, "height": 900 if width > 500 else 844},
            device_scale_factor=1,
        )
        page = context.new_page()
        if inject_summary is not None:
            page.set_content(
                html.replace("BODY_SLOT", '<div id="home-root"></div>'),
                wait_until="domcontentloaded",
            )
            render_home_via_js(page, inject_summary)
        else:
            page.set_content(html, wait_until="domcontentloaded")
        if expand:
            page.locator(
                "details.cf2-col__evidence, details.cf2-col-ws__evidence"
            ).first.click()
        page.wait_for_timeout(250)
        page.screenshot(path=str(slot / fname), full_page=True)
        context.close()


def main() -> None:
    from playwright.sync_api import sync_playwright

    hes = _hes_pkg()
    col_on = compose_commercial_opportunity_layer_v1(
        {
            "store_slug": "founder_refine",
            "merchant_reason_counts_week": {
                "shipping": 14,
                "price": 7,
                "thinking": 4,
            },
        }
    )
    col_empty = compose_commercial_opportunity_layer_v1(
        {"store_slug": "founder_refine", "merchant_reason_counts_week": {}}
    )
    summary_on = {
        "home_executive_summary_v1": hes,
        "commercial_opportunity_layer_v1": col_on,
        "operational_guidance_v1": {
            "ok": True,
            "home_surface": {
                "what_we_see_ar": "أسباب شحن متكررة هذا الأسبوع.",
                "what_it_means_ar": "احتكاك تشغيلي عند خطوة الشحن.",
                "what_to_do_now_ar": "راجع نصوص الشحن دون تغيير السعر.",
                "when_to_recheck_ar": "بعد عيّنة تردد جديدة.",
            },
        },
    }
    summary_empty = {
        "home_executive_summary_v1": hes,
        "commercial_opportunity_layer_v1": col_empty,
    }
    shell = _shell_html("BODY_SLOT")
    opp = col_on["primary"]
    dc = opp["decision_contract_ar"]
    ev_lis = "".join(f"<li>{x}</li>" for x in opp["evidence"]["lines_ar"])
    ws_body = f"""
<section class="cf2-col-ws" data-cf2="commercial-opportunity-workspace-v1" data-cf2-col-refine="v1">
<p class="cf2-col-ws__lane">قرار تجاري</p>
<div class="cf2-col-ws__unit cf2-col-ws__unit--mass" data-cf2-col-ws-unit="decision">
<p class="cf2-col-ws__k">القرار</p><p class="cf2-col-ws__v">{dc['decision_ar']}</p></div>
<div class="cf2-col-ws__unit" data-cf2-col-ws-unit="why">
<p class="cf2-col-ws__k">لماذا الآن؟</p><p class="cf2-col-ws__v">{dc['why_now_ar']}</p></div>
<div class="cf2-col-ws__unit cf2-col-ws__unit--mass" data-cf2-col-ws-unit="do">
<p class="cf2-col-ws__k">نفّذ هذا</p><p class="cf2-col-ws__v">{dc['do_this_ar']}</p></div>
<div class="cf2-col-ws__unit" data-cf2-col-ws-unit="dont">
<p class="cf2-col-ws__k">لا تفعل هذا</p><p class="cf2-col-ws__v">{dc['dont_ar']}</p></div>
<div class="cf2-col-ws__unit" data-cf2-col-ws-unit="measure">
<p class="cf2-col-ws__k">سنقيس</p><p class="cf2-col-ws__v">{dc['measure_ar']}</p></div>
<div class="cf2-col-ws__unit" data-cf2-col-ws-unit="recheck">
<p class="cf2-col-ws__k">سنغير رأينا إذا...</p><p class="cf2-col-ws__v">{dc['recheck_ar']}</p></div>
<details class="cf2-col-ws__evidence"><summary>عرض الدليل</summary><ul>{ev_lis}</ul></details>
</section>
"""
    ws_html = _shell_html(ws_body).replace(
        "ماذا يجب أن أعرف الآن عن متجري؟", "مساحة القرار"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        capture_pair(browser, "01_home_primary", shell, inject_summary=summary_on)
        capture_pair(
            browser, "02_home_secondary_hierarchy", shell, inject_summary=summary_on
        )
        capture_pair(browser, "03_workspace_default", ws_html)
        capture_pair(
            browser, "04_workspace_evidence_expanded", ws_html, expand=True
        )
        capture_pair(
            browser, "05_no_opportunity", shell, inject_summary=summary_empty
        )
        browser.close()

    pngs = list(OUT.rglob("*.png"))
    (OUT / "MANIFEST.md").write_text(
        "# Composition Refinement V1 — Founder Review\n\n"
        + json.dumps(
            {
                "screenshots": len(pngs),
                "required": 10,
                "primary_family": opp["family"],
                "refine": "composition_refinement_v1",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("wrote", OUT, "pngs", len(pngs))


if __name__ == "__main__":
    main()
