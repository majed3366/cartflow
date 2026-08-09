# -*- coding: utf-8 -*-
"""Living Store — Decision Workspace Mobile CIM Footprint Closure V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "decision_workspace_mobile_cim_footprint_closure_v1"
SHOTS = OUT / "screenshots"
BASE = "https://smartreplyai.net"
SHELL_MARKER = "shell-integration-v1"
EXPECTED_SHA_PREFIX = "d52da0b"


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


FOOTPRINT = """() => {
  const conf = document.querySelector('#cf2-workspace-root .cf2-ws__confidence');
  const field = document.querySelector('#cf2-workspace-root .cf2-evfield');
  const firstLi = document.querySelector('#cf2-workspace-root .cf2-beat--evidence .cf2-beat__list li');
  const title = document.querySelector('#cf2-workspace-root .cf2-ws__title');
  const chrome = document.querySelector('.cf2-chrome');
  const doc = document.documentElement;
  const confR = conf?.getBoundingClientRect();
  const fieldR = field?.getBoundingClientRect();
  const liR = firstLi?.getBoundingClientRect();
  const titleFs = title ? parseFloat(getComputedStyle(title).fontSize) : 0;
  const q = document.querySelector('.cf2-page[data-cf2-page="workspace"] .cf2-page__question');
  const qFs = q ? parseFloat(getComputedStyle(q).fontSize) : 0;
  const gapConfToLi = (confR && liR) ? Math.round(liR.top - confR.bottom) : null;
  const fieldH = fieldR ? Math.round(fieldR.height) : null;
  const minH = field ? getComputedStyle(field).minHeight : '';
  const gap = field ? getComputedStyle(field).gap : '';
  const pad = field ? getComputedStyle(field).padding : '';
  return {
    shellMarker: chrome?.getAttribute('data-cf2-appbar') || '',
    mobileHierarchy: document.querySelector('#cf2-workspace-root .cf2-ws')?.getAttribute('data-cf2-mobile-hierarchy') || '',
    density: field?.getAttribute('data-cf2-density') || '',
    fieldHeight: fieldH,
    fieldMinHeight: minH,
    fieldGap: gap,
    fieldPadding: pad,
    gapConfidenceToFirstEvidence: gapConfToLi,
    hasEvField: !!field,
    hasRoute: !!document.querySelector('#cf2-workspace-root .cf2-route'),
    hasCO: !!document.querySelector('#cf2-workspace-root .cf2-ws__mark .cf2-co'),
    decisionOwns: titleFs > qFs + 2,
    overflowX: doc.scrollWidth > doc.clientWidth + 1,
    viewport: { w: window.innerWidth, h: window.innerHeight },
  };
}"""


OVERFLOW = """() => {
  const doc = document.documentElement;
  const offenders = [];
  const vw = window.innerWidth;
  document.querySelectorAll('#cf2-workspace-root *').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    if (r.right > vw + 1 || r.left < -1) {
      offenders.push({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || '').slice(0, 60),
        left: Math.round(r.left),
        right: Math.round(r.right),
      });
    }
  });
  return {
    overflowX: doc.scrollWidth > doc.clientWidth + 1,
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    offenderCount: offenders.length,
    offenders: offenders.slice(0, 8),
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


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy(EXPECTED_SHA_PREFIX)
    probe: dict = {"deploy": deploy}
    overflow: dict = {"deploy": deploy}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page0 = browser.new_page()
        page0.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
        cookie = session_cookie(page0)
        page0.close()

        # Desktop regression
        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        desk.add_cookies([cookie])
        dpage = desk.new_page()
        goto_workspace(dpage)
        dpage.evaluate("() => window.scrollTo(0, 0)")
        dpage.wait_for_timeout(300)
        probe["desktop"] = dpage.evaluate(FOOTPRINT)
        dpage.screenshot(
            path=str(SHOTS / "06_desktop_workspace_regression.png"), full_page=True
        )
        desk.close()

        for width, after_name, full_name in (
            (430, "02_mobile_430_after.png", "05_mobile_430_full_flow.png"),
            (390, "04_mobile_390_after.png", None),
        ):
            ctx = browser.new_context(
                viewport={"width": width, "height": 932 if width == 430 else 844},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
                locale="ar-SA",
            )
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            goto_workspace(page)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(350)
            key = f"mobile_{width}"
            probe[key] = page.evaluate(FOOTPRINT)
            overflow[key] = page.evaluate(OVERFLOW)
            page.screenshot(path=str(SHOTS / after_name), full_page=False)
            if full_name:
                page.screenshot(path=str(SHOTS / full_name), full_page=True)
            ctx.close()

        browser.close()

    m430 = probe.get("mobile_430") or {}
    m390 = probe.get("mobile_390") or {}
    deskp = probe.get("desktop") or {}

    # Sparse field used to be min-height 100px; after should be materially shorter.
    gates = {
        "deployOk": bool(deploy.get("ok")),
        "shellUntouched": m430.get("shellMarker") == SHELL_MARKER,
        "hierarchyMarkerPresent": m430.get("mobileHierarchy") == "v1",
        "cimPresent430": bool(m430.get("hasEvField") and m430.get("hasRoute")),
        "cimPresent390": bool(m390.get("hasEvField") and m390.get("hasRoute")),
        "fieldCompressed430": (m430.get("fieldHeight") or 999) <= 48,
        "fieldCompressed390": (m390.get("fieldHeight") or 999) <= 48,
        "gapReduced430": (m430.get("gapConfidenceToFirstEvidence") or 999) <= 56,
        "gapReduced390": (m390.get("gapConfidenceToFirstEvidence") or 999) <= 56,
        "minHeightCleared430": str(m430.get("fieldMinHeight") or "").startswith("0"),
        "minHeightCleared390": str(m390.get("fieldMinHeight") or "").startswith("0"),
        "decisionOwns430": bool(m430.get("decisionOwns")),
        "decisionOwns390": bool(m390.get("decisionOwns")),
        "noOverflow430": not m430.get("overflowX", True),
        "noOverflow390": not m390.get("overflowX", True),
        "desktopShellOk": deskp.get("shellMarker") == SHELL_MARKER,
        # Desktop sparse may still use language.css min-height — expected unchanged.
        "desktopFieldUnchangedContract": (deskp.get("fieldHeight") or 0) >= 70
        or (deskp.get("density") not in ("sparse",)),
    }
    probe["gates"] = gates
    overflow["summary"] = {
        "noOverflow430": not (overflow.get("mobile_430") or {}).get("overflowX", True),
        "noOverflow390": not (overflow.get("mobile_390") or {}).get("overflowX", True),
        "offenderCount430": (overflow.get("mobile_430") or {}).get("offenderCount", -1),
        "offenderCount390": (overflow.get("mobile_390") or {}).get("offenderCount", -1),
    }

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "mobile_overflow_probe.json").write_text(
        json.dumps(overflow, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "deploy": deploy,
                "gates": gates,
                "footprint": {
                    "430": {
                        "fieldH": m430.get("fieldHeight"),
                        "gap": m430.get("gapConfidenceToFirstEvidence"),
                        "minH": m430.get("fieldMinHeight"),
                    },
                    "390": {
                        "fieldH": m390.get("fieldHeight"),
                        "gap": m390.get("gapConfidenceToFirstEvidence"),
                        "minH": m390.get("fieldMinHeight"),
                    },
                    "desktop_fieldH": deskp.get("fieldHeight"),
                },
                "overflow": overflow["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not all(gates.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
