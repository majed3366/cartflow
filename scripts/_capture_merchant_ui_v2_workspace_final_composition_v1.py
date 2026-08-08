# -*- coding: utf-8 -*-
"""Living Store evidence — Decision Workspace Final Product Composition V1."""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_workspace_final_composition_v1"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_visual_language_maturity_v1"
    / "10_desktop_workspace.png"
)
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "1a4df46"


def wait_for_deploy(timeout_s: int = 720) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if not EXPECTED_SHA_PREFIX or sha.startswith(EXPECTED_SHA_PREFIX):
                    return {"ok": True, **last}
        except Exception as exc:  # noqa: BLE001
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def session_cookie(page) -> dict:
    session = page.evaluate(
        """async () => {
          const r = await fetch('/dev/living-store-home-review-session', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json().catch(() => ({}));
        }"""
    )
    return {
        "name": session["cookie_name"],
        "value": session["cookie_value"],
        "url": BASE,
        "httpOnly": True,
        "sameSite": "Lax",
    }


def ws_probe(page) -> dict:
    return page.evaluate(
        """() => {
          const root = document.querySelector('#cf2-workspace-root');
          const ws = document.querySelector('[data-cf2=\"workspace-final-v1\"]');
          const coCount = document.querySelectorAll(
            '#cf2-workspace-root .cf2-co__glyph'
          ).length;
          const section = (document.querySelector('#cf2-appbar-section') || {}).textContent || '';
          const route = document.querySelector('.cf2-route');
          const progress = route ? route.getAttribute('data-cf2-progress') : '';
          const title = (document.querySelector('.cf2-ws__title') || {}).textContent || '';
          const conf = (document.querySelector('.cf2-ws__confidence') || {}).textContent || '';
          const mass = document.querySelector('.cf2-dmass');
          const terminus = document.querySelector('.cf2-terminus');
          const ctxOff = document.querySelector('.cf2-shell')?.getAttribute('data-cf2-ctx') === 'off';
          const emojiAccount = !!document.querySelector('#cf2-mobile-account') &&
            /👤/.test((document.querySelector('#cf2-mobile-account') || {}).textContent || '');
          return {
            url: location.href,
            ui: document.body.getAttribute('data-cf-ui'),
            marker: ws ? ws.getAttribute('data-cf2') : '',
            coCount,
            section: section.trim(),
            progress,
            title: title.trim(),
            confidence: conf.trim(),
            hasMass: !!mass,
            massReady: !!(mass && mass.classList.contains('is-ready')),
            massForming: !!(mass && mass.classList.contains('is-forming')),
            terminusArmed: !!(terminus && terminus.classList.contains('is-armed')),
            evArriving: !!document.querySelector('.cf2-evfield.is-arriving'),
            activeNode: !!document.querySelector('.cf2-route__node.is-active'),
            ctxOff,
            emojiAccount,
            appbarAccountSvg: !!document.querySelector('.cf2-appbar__account-icon'),
            noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
              cacheBump: [...document.querySelectorAll('link[rel=stylesheet]')]
              .some(l => /uiv2r/.test(l.href || '')),
          };
        }"""
    )


def goto_workspace(page) -> None:
    page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
    page.wait_for_timeout(5500)
    page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    probe: dict = {"deploy": deploy, "url": f"{BASE}/dashboard#workspace"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        cookie = session_cookie(boot)
        boot.close()

        # Desktop full + primary + route
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        goto_workspace(page)
        probe["desktop"] = ws_probe(page)
        page.screenshot(path=str(OUT / "01_desktop_workspace_full.png"), full_page=True)
        page.screenshot(path=str(OUT / "02_desktop_primary_decision.png"), full_page=False)
        primary = page.query_selector(".cf2-dobj--primary") or page.query_selector(".cf2-ws")
        if primary:
            primary.screenshot(path=str(OUT / "03_desktop_route_progression.png"))
        # Motion A/B: same Living Store truth — arrival vs settled (no invented readiness)
        page.reload(wait_until="domcontentloaded", timeout=120000)
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)
        page.wait_for_timeout(120)
        page.screenshot(path=str(OUT / "07_motion_state_a.png"), full_page=False)
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "08_motion_state_b.png"), full_page=False)
        # Grayscale logo-hidden
        page.evaluate(
            """() => {
              document.documentElement.style.filter = 'grayscale(1)';
              document.querySelectorAll('.cf2-brand__mark, .cf2-brand__word')
                .forEach(el => { el.style.visibility = 'hidden'; });
            }"""
        )
        page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "09_grayscale_logo_hidden.png"), full_page=False)
        ctx.close()

        # Mobile first viewport + progression + appbar
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
        )
        mctx.add_cookies([cookie])
        mpage = mctx.new_page()
        goto_workspace(mpage)
        probe["mobile"] = ws_probe(mpage)
        mpage.screenshot(path=str(OUT / "04_mobile_first_viewport.png"), full_page=False)
        mpage.screenshot(path=str(OUT / "05_mobile_decision_progression.png"), full_page=True)
        appbar = mpage.query_selector(".cf2-appbar")
        if appbar:
            appbar.screenshot(path=str(OUT / "06_mobile_appbar.png"))
        mctx.close()
        browser.close()

    # Before/after collage: maturity desktop (before) + new desktop (after)
    try:
        from PIL import Image, ImageDraw, ImageFont

        after = Image.open(OUT / "02_desktop_primary_decision.png").convert("RGB")
        before = Image.open(BEFORE).convert("RGB") if BEFORE.is_file() else after
        h = 720
        bw = int(before.width * h / before.height)
        aw = int(after.width * h / after.height)
        before = before.resize((bw, h))
        after = after.resize((aw, h))
        gap = 24
        canvas = Image.new("RGB", (bw + aw + gap + 40, h + 56), (245, 247, 250))
        canvas.paste(before, (20, 40))
        canvas.paste(after, (20 + bw + gap, 40))
        draw = ImageDraw.Draw(canvas)
        draw.text((20, 12), "BEFORE (maturity)", fill=(80, 90, 110))
        draw.text((20 + bw + gap, 12), "AFTER (final composition)", fill=(8, 32, 72))
        canvas.save(OUT / "10_before_after.png")
    except Exception as exc:  # noqa: BLE001
        probe["before_after_error"] = str(exc)
        if BEFORE.is_file():
            shutil.copyfile(BEFORE, OUT / "10_before_after.png")

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))

    d = probe.get("desktop") or {}
    m = probe.get("mobile") or {}
    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            d.get("ui") == "v2",
            d.get("marker") == "workspace-final-v1",
            d.get("coCount", 99) <= 2,
            d.get("ctxOff"),
            d.get("cacheBump"),
            d.get("noOverflow"),
            m.get("marker") == "workspace-final-v1",
            m.get("section") == "مساحة القرار",
            m.get("appbarAccountSvg"),
            not m.get("emojiAccount"),
            m.get("noOverflow"),
            m.get("coCount", 99) <= 2,
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
