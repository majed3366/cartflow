# -*- coding: utf-8 -*-
"""Capture rendered evidence for Visual Identity Residual Closure V1."""
from __future__ import annotations

import json
import pathlib
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8772"
OUT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "merchant_platform_visual_identity_residual_closure_v1"
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


STYLE_JS = """
([sel]) => {
  const el = document.querySelector(sel);
  if (!el) return {missing: true, sel};
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  return {
    sel,
    backgroundColor: cs.backgroundColor,
    borderTopStyle: cs.borderTopStyle,
    borderInlineStartStyle: cs.borderInlineStartStyle,
    borderInlineStartWidth: cs.borderInlineStartWidth,
    borderInlineStartColor: cs.borderInlineStartColor,
    borderTopColor: cs.borderTopColor,
    boxShadow: cs.boxShadow,
    borderRadius: cs.borderRadius,
    overflowX: document.documentElement.scrollWidth > window.innerWidth + 2,
    w: Math.round(r.width),
    h: Math.round(r.height),
    text: (el.innerText || '').slice(0, 160),
  };
}
"""


def capture(page, name: str) -> None:
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)


def wait_surface(page, sel: str) -> None:
    page.wait_for_selector(sel, timeout=14000)
    page.wait_for_timeout(800)


def main() -> None:
    ident = urllib.request.urlopen(BASE + "/", timeout=15)
    sha = ident.headers.get("X-CartFlow-Git-Sha") or ""
    pair = mint()
    evidence = {
        "review_sha_header": sha,
        "base": BASE,
        "styles": {},
        "smoke": {},
        "html": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp_name, vp in (
            ("desktop", {"width": 1440, "height": 900}),
            ("mobile", {"width": 390, "height": 844, "is_mobile": True, "has_touch": True}),
        ):
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=bool(vp.get("is_mobile")),
                has_touch=bool(vp.get("has_touch")),
                locale="ar-SA",
            )
            context.add_cookies([cookie_dict(pair)])
            page = context.new_page()
            reqs: list[str] = []
            page.on(
                "request",
                lambda r: reqs.append(r.url)
                if "/api/" in r.url or "/dashboard" in r.url
                else None,
            )
            page.goto(
                BASE + "/dashboard?cf_ui=v2#home",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            page.wait_for_timeout(1100)
            html = page.content()
            evidence["html"][vp_name] = {
                "resid1": "resid1" in html,
                "assim1": "assim1" in html,
                "qpool1": "qpool1" in html,
            }
            capture(page, f"{vp_name}_home_ref")

            page.evaluate("location.hash = '#workspace'")
            page.wait_for_timeout(1000)
            capture(page, f"{vp_name}_workspace_ref")

            page.evaluate("location.hash = '#carts'")
            wait_surface(page, ".cf2-carts")
            page.wait_for_timeout(1400)
            capture(page, f"{vp_name}_carts")
            row = page.query_selector(".cf2-carts__row")
            if row and row.is_visible():
                row.click(timeout=4000)
                page.wait_for_timeout(700)
                capture(page, f"{vp_name}_carts_selected")
                evidence["styles"][f"{vp_name}_carts_selected"] = page.evaluate(
                    STYLE_JS, [".cf2-carts__row.is-selected"]
                )
                if vp_name == "mobile":
                    back = page.query_selector(".cf2-carts__back")
                    if back and back.is_visible():
                        back.click(timeout=4000)
                        page.wait_for_timeout(400)

            page.evaluate("location.hash = '#comms'")
            wait_surface(page, ".cf2-comms")
            page.wait_for_timeout(1400)
            capture(page, f"{vp_name}_comms")
            evidence["styles"][f"{vp_name}_comms_empty"] = page.evaluate(
                STYLE_JS, [".cf2-comms__empty"]
            )
            evidence["styles"][f"{vp_name}_comms_detail"] = page.evaluate(
                STYLE_JS, [".cf2-comms__detail"]
            )
            evidence["styles"][f"{vp_name}_comms_row"] = page.evaluate(
                STYLE_JS, [".cf2-comms__row"]
            )
            crow = page.query_selector(".cf2-comms__row")
            if crow and crow.is_visible():
                crow.click(timeout=4000)
                page.wait_for_timeout(700)
                capture(page, f"{vp_name}_comms_selected")
                evidence["styles"][f"{vp_name}_comms_selected"] = page.evaluate(
                    STYLE_JS, [".cf2-comms__row.is-selected"]
                )

            page.evaluate("location.hash = '#settings'")
            wait_surface(page, ".cf2-settings")
            page.wait_for_timeout(1200)
            capture(page, f"{vp_name}_settings")
            evidence["styles"][f"{vp_name}_settings_row"] = page.evaluate(
                STYLE_JS, [".cf2-settings__row"]
            )
            evidence["styles"][f"{vp_name}_settings_needs"] = page.evaluate(
                STYLE_JS, [".cf2-settings__row.is-needs"]
            )
            evidence["styles"][f"{vp_name}_settings_detail"] = page.evaluate(
                STYLE_JS, [".cf2-settings__detail"]
            )
            srow = page.query_selector(".cf2-settings__row")
            if srow and srow.is_visible():
                srow.click(timeout=4000)
                page.wait_for_timeout(600)
                capture(page, f"{vp_name}_settings_selected")
                evidence["styles"][f"{vp_name}_settings_selected"] = page.evaluate(
                    STYLE_JS, [".cf2-settings__row.is-selected"]
                )
                if vp_name == "mobile":
                    back = page.query_selector(".cf2-settings__back")
                    if back and back.is_visible():
                        back.click(timeout=4000)
                        page.wait_for_timeout(350)

            api = [u for u in reqs if "/api/" in u]
            evidence["smoke"][vp_name] = {
                "api_count": len(api),
                "api_paths": sorted(
                    {u.split(BASE, 1)[-1].split("?", 1)[0] for u in api}
                )[:24],
                "overflow": page.evaluate(
                    "() => document.documentElement.scrollWidth > window.innerWidth + 2"
                ),
            }
            context.close()
        browser.close()
    (OUT / "review_metrics.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "sha": sha, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
