# -*- coding: utf-8 -*-
"""Capture Signature Primitives V1 proof — color + grayscale (logo hidden)."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "signature_primitives_v1"
BASE = "http://127.0.0.1:8765"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return await r.json().catch(() => ({}));
            }"""
        )
        boot.close()
        if not (session.get("cookie_name") and session.get("cookie_value")):
            raise SystemExit(f"FAIL_NO_SESSION: {session}")

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies(
            [
                {
                    "name": session["cookie_name"],
                    "value": session["cookie_value"],
                    "url": BASE,
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        page.wait_for_timeout(2000)
        page.evaluate(
            """async () => {
              await fetch('/api/cart-workspace/v1/demo-seed', {
                method: 'POST', credentials: 'same-origin'
              });
            }"""
        )

        # Home color
        page.locator('button.ma-gtb-section[data-ma-section="home"]').click()
        page.wait_for_timeout(2200)
        page.evaluate("window.scrollTo(0,0)")
        home_probe = page.evaluate(
            """() => {
              const secs = [...document.querySelectorAll('[data-cf-sig=\"home-section\"]')];
              return {
                css: [...document.styleSheets].some(s => (s.href||'').includes('cf_signature_primitives')),
                js: !!(window.CFSignature && window.CFSignature.attrsForCard),
                sections: secs.map(el => ({
                  gravity: el.getAttribute('data-cf-gravity'),
                  rank: el.getAttribute('data-cf-rank'),
                  momentum: el.getAttribute('data-cf-momentum'),
                })),
              };
            }"""
        )
        print("home_probe", home_probe)
        page.screenshot(path=str(OUT / "home_grammar_color.png"), full_page=False)
        page.evaluate('document.body.setAttribute("data-cf-sig-proof","grayscale")')
        page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "home_grammar_grayscale_no_logo.png"), full_page=False)
        page.evaluate('document.body.removeAttribute("data-cf-sig-proof")')

        # Workspace color + grammar closeups
        page.locator('button.ma-gtb-section[data-ma-section="workspace"]').click()
        page.wait_for_timeout(2800)
        page.evaluate("window.scrollTo(0,0)")
        ws_probe = page.evaluate(
            """() => {
              const ops = document.querySelector('[data-cf-sig=\"workspace\"]');
              const card = document.querySelector('[data-cf-sig=\"decision-card\"][data-cf-role=\"primary\"], .cw-card--primary');
              return {
                workspace: ops && {
                  quiet: ops.getAttribute('data-cf-quiet'),
                  routes: ops.getAttribute('data-cf-route-count'),
                  breathing: ops.getAttribute('data-cf-breathing'),
                },
                primary: card && {
                  role: card.getAttribute('data-cf-role'),
                  density: card.getAttribute('data-cf-density'),
                  evidence: card.getAttribute('data-cf-evidence-n'),
                  tension: card.getAttribute('data-cf-tension'),
                  momentum: card.getAttribute('data-cf-momentum'),
                  gravity: card.getAttribute('data-cf-gravity'),
                  hasBeats: !!card.querySelector('.cw-beat--evidence') &&
                    !!card.querySelector('.cw-beat--understanding') &&
                    !!card.querySelector('.cw-beat--decision') &&
                    !!card.querySelector('.cw-beat--action'),
                },
              };
            }"""
        )
        print("workspace_probe", ws_probe)
        if not (ws_probe.get("primary") and ws_probe["primary"].get("density")):
            raise SystemExit("FAIL_NO_PRIMARY_GRAMMAR")
        if not ws_probe["primary"].get("hasBeats"):
            raise SystemExit("FAIL_NO_BEAT_STACK")

        page.screenshot(path=str(OUT / "workspace_grammar_color.png"), full_page=False)
        primary = page.locator(".cw-card--primary, [data-cf-role='primary']").first
        if primary.count():
            primary.screenshot(path=str(OUT / "decision_mass_closeup.png"))
        evid = page.locator(".cw-beat--evidence").first
        if evid.count():
            page.locator(".cw-card--primary .cw-card__stack").first.screenshot(
                path=str(OUT / "evidence_to_action_stack_closeup.png")
            )

        page.evaluate('document.body.setAttribute("data-cf-sig-proof","grayscale")')
        page.wait_for_timeout(200)
        page.screenshot(
            path=str(OUT / "workspace_grammar_grayscale_no_logo.png"), full_page=False
        )
        if primary.count():
            primary.screenshot(path=str(OUT / "decision_mass_grayscale_closeup.png"))
        page.evaluate('document.body.removeAttribute("data-cf-sig-proof")')

        if not home_probe.get("css") or not home_probe.get("js"):
            raise SystemExit("FAIL_SIGNATURE_ASSETS")
        print("OK", OUT)
        ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
