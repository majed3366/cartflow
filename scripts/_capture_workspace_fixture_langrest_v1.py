# -*- coding: utf-8 -*-
import json
import pathlib
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8773"
OUT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "home_workspace_visual_language_restoration_v1"
    / "review"
)

req = urllib.request.Request(
    BASE + "/dev/living-store-home-review-session", method="POST"
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = json.loads(resp.read().decode())
pair = f"{body['cookie_name']}={body['cookie_value']}"
name, value = pair.split("=", 1)

FIXTURE = """() => {
  const root = document.getElementById('cf2-workspace-root');
  if (!root || !window.CartFlowUiV2Workspace) return {ok:false};
  root.innerHTML = window.CartFlowUiV2Workspace.render({
    projection: { zone_b: [{
      is_primary_decision: true,
      decision_id: 'review-fixture',
      decision_sentence_ar: 'لا تغيّر سياسة الشحن حتى تتضح الأدلة.',
      evidence_lines_ar: ['يغادر العملاء بعد خطوة الشحن في مسار Nano 20W.'],
      ignore_consequence_ar: 'ترك الإشارة معلّقة يبقي عنق الزجاجة دون معالجة.',
      execution_readiness: 'NEEDS_MORE_EVIDENCE',
      execution_available: false,
      action_wait_lines_ar: ['لا يوجد إجراء حالياً.', 'سيخبرك CartFlow عندما يصبح القرار جاهزاً.']
    }]}
  });
  return {
    ok: true,
    rail: document.querySelectorAll('.cf2-co-row').length,
    route: document.querySelectorAll('.cf2-route').length,
    dmass: document.querySelectorAll('.cf2-dmass').length,
    evfield: document.querySelectorAll('.cf2-evfield').length
  };
}"""

probes = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for fname, w, h in (
        ("desktop_workspace_fixture", 1440, 900),
        ("mobile_workspace_fixture", 390, 844),
    ):
        ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar")
        ctx.add_cookies([{"name": name, "value": value, "url": BASE}])
        page = ctx.new_page()
        page.goto(BASE + "/dashboard?cf_ui=v2#workspace", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        page.evaluate(
            "sec => { if (window.CartFlowUiV2 && window.CartFlowUiV2.go) window.CartFlowUiV2.go(sec); }",
            "workspace",
        )
        page.wait_for_timeout(600)
        probes[fname] = page.evaluate(FIXTURE)
        page.screenshot(path=str(OUT / (fname + ".png")), full_page=False)
        ctx.close()
    browser.close()
print(json.dumps(probes, ensure_ascii=False, indent=2))
