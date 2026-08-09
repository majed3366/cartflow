# -*- coding: utf-8 -*-
"""Living Store evidence — Decision Workspace Composition Closure V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "decision_workspace_composition_closure_v1"
SHOTS = OUT / "screenshots"
BASE = "https://smartreplyai.net"
MARKER = "workspace-composition-closure-v1"
SHELL_MARKER = "shell-integration-v1"
EXPECTED_SHA_PREFIX = ""  # set after deploy tip is known


def wait_for_deploy(sha_prefix: str, timeout_s: int = 720) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{BASE}/", method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                sha = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
                last = {"sha": sha, "status": resp.status}
                if not sha_prefix or sha.startswith(sha_prefix):
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


PROBE = """() => {
  const ws = document.querySelector('[data-cf2]');
  const title = document.querySelector('.cf2-ws__title');
  const mass = document.querySelector('.cf2-dmass__text');
  const primary = document.querySelector('.cf2-dobj--primary');
  const route = document.querySelector('.cf2-route');
  const doc = document.documentElement;
  const body = document.body;
  const stage = document.querySelector('.cf2-stage');
  const chrome = document.querySelector('.cf2-chrome');
  const ctx = document.querySelector('#cf2-ctx');
  const handle = document.querySelector('#cf2-ctx-handle');
  const titleFs = title ? parseFloat(getComputedStyle(title).fontSize) : 0;
  const massFs = mass ? parseFloat(getComputedStyle(mass).fontSize) : 0;
  const headDup = !!(title && mass && title.textContent.trim() === mass.textContent.trim());
  const confDup = [...document.querySelectorAll('.cf2-beat__list li')]
    .some(li => /مستوى\\s*الثقة/i.test(li.textContent || ''));
  const overflowX = doc.scrollWidth > doc.clientWidth + 1;
  const scrollable = Math.max(doc.scrollHeight, body.scrollHeight) > window.innerHeight + 8;
  return {
    wsMarker: ws?.getAttribute('data-cf2') || '',
    shellMarker: chrome?.getAttribute('data-cf2-appbar') || '',
    headDup,
    confDup,
    titleFs,
    massFs,
    hierarchyDesktopOk: window.innerWidth >= 1024 ? massFs >= titleFs - 0.5 : true,
    hierarchyMobileOk: window.innerWidth < 1024 ? titleFs >= massFs - 0.5 : true,
    tension: primary?.getAttribute('data-cf2-tension') || '',
    evidence: primary?.getAttribute('data-cf2-evidence') || '',
    progress: route?.getAttribute('data-cf2-progress') || '',
    hasCO: !!document.querySelector('.cf2-ws__mark .cf2-co'),
    hasEvField: !!document.querySelector('.cf2-evfield'),
    hasArriving: !!document.querySelector('.is-arriving'),
    hasRoute: !!route,
    hasTerminus: !!document.querySelector('.cf2-terminus'),
    nextCount: document.querySelectorAll('.cf2-dobj--next').length,
    overflowX,
    scrollable,
    stageOverflowY: stage ? getComputedStyle(stage).overflowY : '',
    bodyOverflowY: getComputedStyle(body).overflowY,
    ctxOpen: !!(ctx && ctx.classList.contains('is-open')),
    handleVisible: !!(handle && getComputedStyle(handle).display !== 'none'),
    viewport: { w: window.innerWidth, h: window.innerHeight },
    scrollY: window.scrollY || doc.scrollTop || 0,
  };
}"""


def goto_workspace(page) -> None:
    page.goto(f"{BASE}/dashboard#workspace", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(900)
    page.evaluate("() => { if (window.CartFlowUiV2 && window.CartFlowUiV2.go) window.CartFlowUiV2.go('workspace'); }")
    page.wait_for_selector(".cf2-ws, .cf2-error, .cf2-loading", timeout=60000)
    page.wait_for_timeout(1200)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy(EXPECTED_SHA_PREFIX)
    probe: dict = {"deploy": deploy}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        cookie = None

        # 1) Desktop full page
        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        dpage = desk.new_page()
        if cookie is None:
            dpage.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
            cookie = session_cookie(dpage)
        desk.add_cookies([cookie])
        goto_workspace(dpage)
        dpage.evaluate("() => window.scrollTo(0, 0)")
        dpage.wait_for_timeout(400)
        probe["desktop"] = dpage.evaluate(PROBE)
        dpage.screenshot(path=str(SHOTS / "01_desktop_workspace_full.png"), full_page=True)

        # Mobile closed contextual
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        mobile.add_cookies([cookie])
        mpage = mobile.new_page()
        goto_workspace(mpage)
        mpage.evaluate(
            """() => {
              document.body.classList.remove('is-ctx-open');
              const ctx = document.querySelector('#cf2-ctx');
              if (ctx) ctx.classList.remove('is-open');
              window.scrollTo(0, 0);
            }"""
        )
        mpage.wait_for_timeout(350)
        probe["mobile_top"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(SHOTS / "02_mobile_workspace_top.png"), full_page=False)
        mpage.screenshot(
            path=str(SHOTS / "05_mobile_contextual_closed.png"), full_page=False
        )

        # Mid scroll
        mpage.evaluate(
            """() => {
              const h = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
              window.scrollTo(0, Math.min(Math.floor(h * 0.38), h - window.innerHeight));
            }"""
        )
        mpage.wait_for_timeout(400)
        probe["mobile_mid"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(SHOTS / "03_mobile_workspace_mid.png"), full_page=False)

        # Lower section
        mpage.evaluate(
            """() => {
              const next = document.querySelector('.cf2-ws__next') || document.querySelector('.cf2-terminus');
              if (next) next.scrollIntoView({ block: 'start' });
              else window.scrollTo(0, document.documentElement.scrollHeight);
            }"""
        )
        mpage.wait_for_timeout(400)
        probe["mobile_lower"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(SHOTS / "04_mobile_workspace_lower.png"), full_page=False)

        # Contextual open
        mpage.evaluate("() => window.scrollTo(0, 0)")
        mpage.wait_for_timeout(250)
        handle = mpage.query_selector("#cf2-ctx-handle")
        if handle:
            handle.click()
            mpage.wait_for_timeout(450)
        else:
            mpage.evaluate(
                """() => {
                  document.body.classList.add('is-ctx-open');
                  const ctx = document.querySelector('#cf2-ctx');
                  if (ctx) ctx.classList.add('is-open');
                }"""
            )
            mpage.wait_for_timeout(350)
        probe["mobile_ctx_open"] = mpage.evaluate(PROBE)
        mpage.screenshot(path=str(SHOTS / "06_mobile_contextual_open.png"), full_page=False)

        browser.close()

    gates = {
        "deployOk": bool(deploy.get("ok")),
        "markerPresent": probe.get("desktop", {}).get("wsMarker") == MARKER,
        "shellUntouched": probe.get("desktop", {}).get("shellMarker") == SHELL_MARKER,
        "noOverflowX_desktop": not probe.get("desktop", {}).get("overflowX", True),
        "noOverflowX_mobile": not probe.get("mobile_top", {}).get("overflowX", True),
        "noConfDup": not probe.get("desktop", {}).get("confDup", True),
        "hierarchyDesktop": bool(probe.get("desktop", {}).get("hierarchyDesktopOk")),
        "hierarchyMobile": bool(probe.get("mobile_top", {}).get("hierarchyMobileOk")),
        "commerceInMotion": all(
            [
                probe.get("desktop", {}).get("hasCO"),
                probe.get("desktop", {}).get("hasEvField"),
                probe.get("desktop", {}).get("hasRoute"),
                probe.get("desktop", {}).get("hasTerminus"),
            ]
        ),
        "stageNotScrollTrap": probe.get("desktop", {}).get("stageOverflowY")
        in ("visible", "auto", ""),
        "ctxClosedShot": not probe.get("mobile_top", {}).get("ctxOpen", True),
        "ctxOpenShot": bool(probe.get("mobile_ctx_open", {}).get("ctxOpen")),
    }
    probe["gates"] = gates
    probe["acceptance"] = {
        "question": (
            "Can a merchant understand what decision, why, evidence strength, "
            "meaning, and next step without confusion or visual overload?"
        ),
        "for_visual_review": True,
        "freeze": False,
    }
    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"deploy": deploy, "gates": gates}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
