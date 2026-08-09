# -*- coding: utf-8 -*-
"""Living Store evidence — Decision Workspace Mobile Hierarchy Refinement V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "decision_workspace_mobile_hierarchy_refinement_v1"
SHOTS = OUT / "screenshots"
BASE = "https://smartreplyai.net"
MARKER = "v1"
SHELL_MARKER = "shell-integration-v1"
EXPECTED_SHA_PREFIX = ""  # set after deploy


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
  const ws = document.querySelector('#cf2-workspace-root .cf2-ws');
  const title = document.querySelector('#cf2-workspace-root .cf2-ws__title');
  const mass = document.querySelector('#cf2-workspace-root .cf2-dmass__text');
  const q = document.querySelector('.cf2-page[data-cf2-page="workspace"] .cf2-page__question');
  const eyebrow = document.querySelector('#cf2-workspace-root .cf2-ws__eyebrow');
  const conf = document.querySelector('#cf2-workspace-root .cf2-ws__confidence');
  const meaning = document.querySelector('#cf2-workspace-root [data-cf2-node="understanding"] .cf2-beat__body');
  const action = document.querySelector('#cf2-workspace-root [data-cf2-node="action"]');
  const next = document.querySelector('#cf2-workspace-root .cf2-ws__next');
  const chrome = document.querySelector('.cf2-chrome');
  const doc = document.documentElement;
  const body = document.body;
  const vh = window.innerHeight;
  const inFirst = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.top < vh - 8 && r.bottom > 0;
  };
  const fs = (el) => (el ? parseFloat(getComputedStyle(el).fontSize) : 0);
  const fw = (el) => (el ? parseInt(getComputedStyle(el).fontWeight, 10) || 0 : 0);
  const titleR = title?.getBoundingClientRect();
  const eyeR = eyebrow?.getBoundingClientRect();
  const titleAboveStatus = !!(titleR && eyeR && titleR.top <= eyeR.top + 1);
  return {
    mobileHierarchy: ws?.getAttribute('data-cf2-mobile-hierarchy') || '',
    wsMarker: ws?.getAttribute('data-cf2') || '',
    shellMarker: chrome?.getAttribute('data-cf2-appbar') || '',
    titleText: (title?.textContent || '').trim().slice(0, 80),
    qFs: fs(q),
    titleFs: fs(title),
    massFs: fs(mass),
    eyebrowFs: fs(eyebrow),
    confFs: fs(conf),
    meaningFs: fs(meaning),
    titleFw: fw(title),
    massFw: fw(mass),
    decisionOwns: fs(title) > fs(q) + 2 && fs(title) >= fs(mass),
    titleAboveStatus,
    firstViewport: {
      question: inFirst(q),
      decision: inFirst(title),
      status: inFirst(eyebrow),
      confidence: inFirst(conf),
      meaning: inFirst(meaning),
      confirmation: inFirst(mass),
      action: inFirst(action),
      next: inFirst(next),
    },
    hasCO: !!document.querySelector('#cf2-workspace-root .cf2-ws__mark .cf2-co'),
    hasEvField: !!document.querySelector('#cf2-workspace-root .cf2-evfield'),
    hasRoute: !!document.querySelector('#cf2-workspace-root .cf2-route'),
    hasTerminus: !!document.querySelector('#cf2-workspace-root .cf2-terminus'),
    overflowX: doc.scrollWidth > doc.clientWidth + 1,
    scrollable: Math.max(doc.scrollHeight, body.scrollHeight) > vh + 8,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    scrollY: window.scrollY || doc.scrollTop || 0,
  };
}"""


OVERFLOW = """() => {
  const doc = document.documentElement;
  const body = document.body;
  const offenders = [];
  const vw = window.innerWidth;
  document.querySelectorAll('#cf2-workspace-root *').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    if (r.right > vw + 1 || r.left < -1) {
      const tag = el.tagName.toLowerCase();
      const cls = (el.className && String(el.className).slice(0, 60)) || '';
      offenders.push({ tag, cls, left: Math.round(r.left), right: Math.round(r.right) });
    }
  });
  return {
    overflowX: doc.scrollWidth > doc.clientWidth + 1,
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    offenderCount: offenders.length,
    offenders: offenders.slice(0, 12),
    bodyOverflowX: getComputedStyle(body).overflowX,
  };
}"""


def goto_workspace(page) -> None:
    page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(400)
    page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(500)
    page.evaluate(
        "() => { if (window.CartFlowUiV2 && window.CartFlowUiV2.go) window.CartFlowUiV2.go('workspace'); }"
    )
    page.wait_for_function(
        """() => {
          const root = document.querySelector('#cf2-workspace-root');
          return !!(root && (root.querySelector('.cf2-ws') || root.querySelector('.cf2-error')));
        }""",
        timeout=90000,
    )
    page.wait_for_timeout(700)


def capture_band(page, name: str, scroll_js: str, probe: dict, shots: Path) -> None:
    page.evaluate(scroll_js)
    page.wait_for_timeout(400)
    probe[name] = page.evaluate(PROBE)
    page.screenshot(path=str(shots / f"{name}.png"), full_page=False)


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy(EXPECTED_SHA_PREFIX)
    probe: dict = {"deploy": deploy}
    overflow: dict = {"deploy": deploy}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        cookie = None

        # Desktop regression
        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        dpage = desk.new_page()
        dpage.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
        cookie = session_cookie(dpage)
        desk.add_cookies([cookie])
        goto_workspace(dpage)
        dpage.evaluate("() => window.scrollTo(0, 0)")
        dpage.wait_for_timeout(350)
        probe["desktop"] = dpage.evaluate(PROBE)
        dpage.screenshot(path=str(SHOTS / "07_desktop_workspace_regression.png"), full_page=True)

        for width, prefix in ((430, "01_mobile_430"), (390, "04_mobile_390")):
            # Remap: 430 -> 01/02/03, 390 -> 04/05/06
            top = f"{prefix}_top" if width == 430 else "04_mobile_390_top"
            mid = "02_mobile_430_mid" if width == 430 else "05_mobile_390_mid"
            action = "03_mobile_430_action" if width == 430 else "06_mobile_390_action"
            if width == 430:
                top, mid, action = (
                    "01_mobile_430_top",
                    "02_mobile_430_mid",
                    "03_mobile_430_action",
                )
            else:
                top, mid, action = (
                    "04_mobile_390_top",
                    "05_mobile_390_mid",
                    "06_mobile_390_action",
                )

            ctx = browser.new_context(
                viewport={"width": width, "height": 844 if width == 390 else 932},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
                locale="ar-SA",
            )
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            goto_workspace(page)
            page.evaluate(
                """() => {
                  document.body.classList.remove('is-ctx-open');
                  const c = document.querySelector('#cf2-ctx');
                  if (c) c.classList.remove('is-open');
                  window.scrollTo(0, 0);
                }"""
            )
            page.wait_for_timeout(350)
            probe[top] = page.evaluate(PROBE)
            overflow[f"{width}_top"] = page.evaluate(OVERFLOW)
            page.screenshot(path=str(SHOTS / f"{top}.png"), full_page=False)

            page.evaluate(
                """() => {
                  const n = document.querySelector('#cf2-workspace-root [data-cf2-node="understanding"]');
                  if (n) n.scrollIntoView({ block: 'start' });
                }"""
            )
            page.wait_for_timeout(400)
            probe[mid] = page.evaluate(PROBE)
            page.screenshot(path=str(SHOTS / f"{mid}.png"), full_page=False)

            page.evaluate(
                """() => {
                  const n = document.querySelector('#cf2-workspace-root [data-cf2-node="action"]');
                  if (n) n.scrollIntoView({ block: 'start' });
                }"""
            )
            page.wait_for_timeout(400)
            probe[action] = page.evaluate(PROBE)
            overflow[f"{width}_action"] = page.evaluate(OVERFLOW)
            page.screenshot(path=str(SHOTS / f"{action}.png"), full_page=False)
            ctx.close()

        browser.close()

    top430 = probe.get("01_mobile_430_top") or {}
    top390 = probe.get("04_mobile_390_top") or {}
    desk = probe.get("desktop") or {}

    gates = {
        "deployOk": bool(deploy.get("ok")),
        "markerPresent": top430.get("mobileHierarchy") == MARKER
        and top390.get("mobileHierarchy") == MARKER,
        "shellUntouched": top430.get("shellMarker") == SHELL_MARKER,
        "decisionOwns430": bool(top430.get("decisionOwns")),
        "decisionOwns390": bool(top390.get("decisionOwns")),
        "titleAboveStatus430": bool(top430.get("titleAboveStatus")),
        "titleAboveStatus390": bool(top390.get("titleAboveStatus")),
        "decisionInFirstViewport430": bool(
            (top430.get("firstViewport") or {}).get("decision")
        ),
        "decisionInFirstViewport390": bool(
            (top390.get("firstViewport") or {}).get("decision")
        ),
        "noOverflowX430": not top430.get("overflowX", True),
        "noOverflowX390": not top390.get("overflowX", True),
        "desktopShellOk": desk.get("shellMarker") == SHELL_MARKER,
        "desktopDecisionPresent": bool(desk.get("titleText")),
        "commerceInMotion": all(
            [
                top430.get("hasCO"),
                top430.get("hasEvField"),
                top430.get("hasRoute"),
                top430.get("hasTerminus"),
            ]
        ),
        "desktopMassStillDominant": (desk.get("massFs") or 0)
        >= (desk.get("titleFs") or 0) - 0.5,
    }
    probe["gates"] = gates
    overflow["summary"] = {
        "noOverflow430": not (overflow.get("430_top") or {}).get("overflowX", True),
        "noOverflow390": not (overflow.get("390_top") or {}).get("overflowX", True),
        "offenderCount430": (overflow.get("430_top") or {}).get("offenderCount", -1),
        "offenderCount390": (overflow.get("390_top") or {}).get("offenderCount", -1),
    }

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "mobile_overflow_probe.json").write_text(
        json.dumps(overflow, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"deploy": deploy, "gates": gates, "overflow": overflow["summary"]}, ensure_ascii=False, indent=2))
    if not all(gates.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
