# -*- coding: utf-8 -*-
"""Capture restored Home / Workspace desktop + mobile evidence."""
from __future__ import annotations

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
OUT.mkdir(parents=True, exist_ok=True)


def mint() -> str:
    req = urllib.request.Request(
        BASE + "/dev/living-store-home-review-session", method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    return f"{body['cookie_name']}={body['cookie_value']}"


def cookie_dict(pair: str) -> dict:
    name, value = pair.split("=", 1)
    return {"name": name, "value": value, "url": BASE}


PROBE_JS = """
() => {
  const home = document.querySelector('#cf2-home-root, .cf2-home');
  const ws = document.querySelector('#cf2-workspace-root, .cf2-ws');
  const root = home || ws || document.body;
  return {
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
    kicker: !!document.querySelector('.cf2-home__kicker'),
    gravity: !!document.querySelector('.cf2-home__lane'),
    rail: document.querySelectorAll('.cf2-co-row').length,
    mtrace: document.querySelectorAll('.cf2-mtrace').length,
    evfield: document.querySelectorAll('.cf2-evfield').length,
    route: document.querySelectorAll('.cf2-route').length,
    dmass: document.querySelectorAll('.cf2-dmass').length,
    utility: !!document.querySelector('.cf2-utility'),
    upbar: !!document.querySelector('.cf2-global'),
    ctx: !!document.querySelector('.cf2-ctx'),
    text: (root.innerText || '').slice(0, 240),
  };
}
"""


def main() -> None:
    ident = urllib.request.urlopen(BASE + "/", timeout=15)
    sha = ident.headers.get("X-CartFlow-Git-Sha") or ""
    pair = mint()
    evidence = {"review_sha_header": sha, "base": BASE, "probes": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, section, w, h in (
            ("desktop_home", "home", 1440, 900),
            ("desktop_workspace", "workspace", 1440, 900),
            ("mobile_home", "home", 390, 844),
            ("mobile_workspace", "workspace", 390, 844),
        ):
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                locale="ar",
            )
            ctx.add_cookies([cookie_dict(pair)])
            page = ctx.new_page()
            page.goto(BASE + "/dashboard?cf_ui=v2#" + section, wait_until="domcontentloaded")
            page.wait_for_timeout(400)
            page.evaluate(
                "sec => { if (window.CartFlowUiV2 && window.CartFlowUiV2.go) window.CartFlowUiV2.go(sec); }",
                section,
            )
            page.wait_for_function(
                """() => {
                  const t = document.body.innerText || '';
                  if (t.includes('جاري تحميل معرفة') || t.includes('جاري تحميل بيئة') || t.includes('جاري تحميل الملخص')) {
                    return false;
                  }
                  return !!(document.querySelector('.cf2-home, .cf2-ws, .cf2-error, .cf2-empty'));
                }""",
                timeout=12000,
            )
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / (name + ".png")), full_page=False)
            evidence["probes"][name] = page.evaluate(PROBE_JS)
            ctx.close()
        browser.close()
    (OUT / "probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
