# -*- coding: utf-8 -*-
"""Living Store — App Bar Mobile Reality Correction V1 (visual bbox acceptance)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_app_bar_mobile_reality_correction_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "4e03720"


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


def visual_bar_probe(page, expected_section: str) -> dict:
    """Bounding-rect visual acceptance — DOM-only presence is insufficient."""
    return page.evaluate(
        """(expectedSection) => {
          const vw = window.innerWidth;
          const vh = window.innerHeight;
          const intersects = (r) =>
            !!r &&
            r.w >= 8 &&
            r.h >= 8 &&
            r.right > 2 &&
            r.left < vw - 2 &&
            r.top < Math.min(vh, 80) &&
            r.bottom > 0;

          const account = document.querySelector('#cf2-mobile-account');
          const brand = document.querySelector('.cf2-brand');
          const mark = document.querySelector('.cf2-brand__mark');
          const word = document.querySelector('.cf2-brand__word');
          const section = document.querySelector('#cf2-appbar-section');
          const menu = document.querySelector('.cf2-menu-btn');
          const bar = document.querySelector('.cf2-appbar');

          const wordStyle = word ? getComputedStyle(word) : null;
          const wordClipped =
            !!wordStyle &&
            (wordStyle.clip !== 'auto' && wordStyle.clip !== 'rect(auto, auto, auto, auto)' && wordStyle.clip.includes('0px')
              || wordStyle.position === 'absolute' && (parseFloat(wordStyle.width) <= 1 || parseFloat(wordStyle.height) <= 1)
              || wordStyle.visibility === 'hidden'
              || wordStyle.opacity === '0'
              || wordStyle.display === 'none');

          const rectOf = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return {
              x: Math.round(r.x),
              y: Math.round(r.y),
              w: Math.round(r.width),
              h: Math.round(r.height),
              left: Math.round(r.left),
              right: Math.round(r.right),
              top: Math.round(r.top),
              bottom: Math.round(r.bottom),
            };
          };

          const accountR = rectOf(account);
          const brandR = rectOf(brand);
          const markR = rectOf(mark);
          const wordR = rectOf(word);
          const sectionR = rectOf(section);
          const menuR = rectOf(menu);
          const barR = rectOf(bar);

          const sectionText = (section || {}).textContent?.trim() || '';
          const wordText = (word || {}).textContent?.trim() || '';

          const accountVisible = intersects(accountR);
          const markVisible = intersects(markR);
          const wordVisible = intersects(wordR) && !wordClipped && /CartFlow/i.test(wordText);
          const brandVisible = intersects(brandR) && markVisible && wordVisible;
          const sectionVisible =
            intersects(sectionR) &&
            sectionText === expectedSection &&
            (sectionR.w >= 36);
          const menuVisible = intersects(menuR);

          const orderOk =
            accountVisible &&
            brandVisible &&
            sectionVisible &&
            menuVisible &&
            accountR.left < brandR.left &&
            brandR.left < sectionR.left &&
            sectionR.left < menuR.left;

          const wrap =
            !!barR &&
            [accountR, brandR, sectionR, menuR].some(
              (r) => r && r.bottom > barR.bottom + 3
            );

          return {
            viewport: { w: vw, h: vh },
            appbarMarker: bar ? bar.getAttribute('data-cf2-appbar') : '',
            expectedSection,
            sectionText,
            wordText,
            wordClipped,
            rects: {
              bar: barR,
              account: accountR,
              brand: brandR,
              mark: markR,
              word: wordR,
              section: sectionR,
              menu: menuR,
            },
            visible: {
              account: accountVisible,
              brand: brandVisible,
              mark: markVisible,
              word: wordVisible,
              section: sectionVisible,
              menu: menuVisible,
            },
            orderOk,
            noWrap: !wrap,
            noOverflow: document.documentElement.scrollWidth <= vw + 1,
            cacheBump: [...document.querySelectorAll('link[rel=stylesheet]')]
              .some((l) => /uiv2v/.test(l.href || '')),
            homeMarker:
              document.querySelector('[data-cf2=\"home-stage-closure-v1\"]')?.getAttribute('data-cf2') || '',
            workspaceMarker:
              document.querySelector('[data-cf2=\"workspace-final-v1\"]')?.getAttribute('data-cf2') || '',
            allFourVisible:
              accountVisible && brandVisible && sectionVisible && menuVisible,
          };
        }""",
        expected_section,
    )


def goto_section(page, section: str) -> None:
    page.goto(f"{BASE}/dashboard#{section}", timeout=120000)
    page.wait_for_timeout(4500)
    if section == "home":
        page.wait_for_selector("[data-cf2='home-stage-closure-v1']", timeout=60000)
    else:
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    probe: dict = {"deploy": deploy, "iphone_viewport": {"width": 390, "height": 844}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 390, "height": 844}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        cookie = session_cookie(boot)
        boot.close()

        # iPhone-sized mobile context
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
            device_scale_factor=3,
        )
        mctx.add_cookies([cookie])
        page = mctx.new_page()

        # 01 home closed bar
        goto_section(page, "home")
        probe["01_home_closed"] = visual_bar_probe(page, "الرئيسية")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "01_mobile_home_bar_closed.png"))

        # 03 drawer open
        page.query_selector(".cf2-menu-btn").click()
        page.wait_for_timeout(450)
        probe["03_drawer_open"] = page.evaluate(
            """() => ({
              open: document.body.classList.contains('is-drawer-open'),
              overflow: getComputedStyle(document.body).overflow,
            })"""
        )
        page.screenshot(path=str(OUT / "03_mobile_home_drawer_open.png"), full_page=False)

        # 04 after drawer close — bar must still show all four
        page.query_selector(".cf2-drawer__close").click()
        page.wait_for_timeout(400)
        probe["04_after_drawer_close"] = visual_bar_probe(page, "الرئيسية")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "04_mobile_home_after_drawer_close.png"))
        probe["04_body_lock_released"] = page.evaluate(
            """() => ({
              open: document.body.classList.contains('is-drawer-open'),
              overflowY: getComputedStyle(document.body).overflowY,
              inline: document.body.style.overflow || '',
            })"""
        )

        # 02 workspace closed bar via hash navigation
        page.evaluate("() => { location.hash = '#workspace'; }")
        page.wait_for_timeout(5000)
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)
        probe["02_workspace_closed"] = visual_bar_probe(page, "مساحة القرار")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "02_mobile_workspace_bar_closed.png"))

        # 05 after hash navigation (same state, full frame proof)
        page.screenshot(path=str(OUT / "05_mobile_workspace_after_hash_navigation.png"), full_page=False)
        probe["05_after_hash"] = visual_bar_probe(page, "مساحة القرار")

        # scroll still works
        page.evaluate("() => window.scrollTo(0, 240)")
        page.wait_for_timeout(250)
        probe["scroll_after"] = page.evaluate("() => window.scrollY || 0")
        page.evaluate("() => window.scrollTo(0, 0)")
        mctx.close()

        # Desktop regression
        dctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        dctx.add_cookies([cookie])
        dpage = dctx.new_page()
        goto_section(dpage, "workspace")
        dpage.screenshot(path=str(OUT / "06_desktop_workspace_regression.png"), full_page=False)
        probe["desktop_regression"] = dpage.evaluate(
            """() => ({
              identity: !!(document.querySelector('#cf2-account-btn') &&
                getComputedStyle(document.querySelector('#cf2-account-btn')).display !== 'none'),
              identityName: (document.querySelector('.cf2-appbar__identity-name')||{}).textContent||'',
              homeFrozen: !!document.querySelector('[data-cf2=\"home-stage-closure-v1\"]'),
              workspace: document.querySelector('[data-cf2=\"workspace-final-v1\"]')?.getAttribute('data-cf2') || '',
              noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
            })"""
        )
        dctx.close()
        browser.close()

    def pass_closed(p: dict) -> bool:
        return bool(
            p.get("allFourVisible")
            and p.get("orderOk")
            and p.get("noWrap")
            and p.get("noOverflow")
            and not p.get("wordClipped")
            and (p.get("visible") or {}).get("word")
            and (p.get("visible") or {}).get("section")
            and (p.get("visible") or {}).get("menu")
            and (p.get("visible") or {}).get("account")
            and p.get("appbarMarker") == "mobile-reality-v1"
        )

    gates = {
        "visualFourElementsHome": pass_closed(probe.get("01_home_closed") or {}),
        "visualFourElementsWorkspace": pass_closed(probe.get("02_workspace_closed") or {}),
        "wordmarkNotClipped": not (probe.get("01_home_closed") or {}).get("wordClipped")
        and (probe.get("01_home_closed") or {}).get("wordText") == "CartFlow",
        "sectionHome": (probe.get("01_home_closed") or {}).get("sectionText") == "الرئيسية",
        "sectionWorkspace": (probe.get("02_workspace_closed") or {}).get("sectionText")
        == "مساحة القرار",
        "afterDrawerCloseStillComplete": pass_closed(probe.get("04_after_drawer_close") or {}),
        "afterHashNavigationStillComplete": pass_closed(probe.get("05_after_hash") or {}),
        "drawerBodyLockReleased": (probe.get("04_body_lock_released") or {}).get("overflowY")
        != "hidden"
        and not (probe.get("04_body_lock_released") or {}).get("open"),
        "pageVerticalScroll": (probe.get("scroll_after") or 0) > 40,
        "desktopIdentityIntact": bool((probe.get("desktop_regression") or {}).get("identity")),
        "workspaceCompositionUnchanged": (probe.get("desktop_regression") or {}).get("workspace")
        == "workspace-final-v1",
    }
    probe["gates"] = {k: ("PASS" if v else "FAIL") for k, v in gates.items()}
    probe["all_pass"] = all(gates.values()) and bool(deploy.get("ok"))

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"gates": probe["gates"], "all_pass": probe["all_pass"], "deploy": deploy}, ensure_ascii=False, indent=2))
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    return 0 if probe["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
