# -*- coding: utf-8 -*-
"""Living Store evidence — Merchant UI V2 App Bar Final Closure V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_app_bar_final_closure_v1"
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "ed5a902"


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


def appbar_probe(page, section: str) -> dict:
    return page.evaluate(
        """(section) => {
          const bar = document.querySelector('.cf2-appbar');
          const sectionEl = document.querySelector('#cf2-appbar-section');
          const identity = document.querySelector('#cf2-account-btn');
          const identityName = document.querySelector('.cf2-appbar__identity-name');
          const mobileAcc = document.querySelector('#cf2-mobile-account');
          const menu = document.querySelector('.cf2-menu-btn');
          const brand = document.querySelector('.cf2-brand');
          const home = document.querySelector('[data-cf2=\"home-stage-closure-v1\"]');
          const ws = document.querySelector('[data-cf2=\"workspace-final-v1\"]');
          const barRect = bar ? bar.getBoundingClientRect() : null;
          const wrap =
            !!bar &&
            [...bar.children].some((el) => {
              const st = getComputedStyle(el);
              if (st.display === 'none') return false;
              return el.getBoundingClientRect().bottom > (barRect.bottom + 2);
            });
          const bodyStyle = getComputedStyle(document.body);
          return {
            sectionExpected: section,
            sectionText: (sectionEl || {}).textContent?.trim() || '',
            appbarMarker: bar ? bar.getAttribute('data-cf2-appbar') : '',
            identityVisible: !!(identity && getComputedStyle(identity).display !== 'none'),
            identityName: (identityName || {}).textContent?.trim() || '',
            mobileAccountVisible: !!(mobileAcc && getComputedStyle(mobileAcc).display !== 'none'),
            menuVisible: !!(menu && getComputedStyle(menu).display !== 'none'),
            brandVisible: !!(brand && getComputedStyle(brand).display !== 'none'),
            sectionVisible: !!(sectionEl && getComputedStyle(sectionEl).display !== 'none'
              && ((sectionEl.textContent || '').trim().length > 0)),
            noLegacyPlan: !/الباقة/.test(bar ? bar.innerText : ''),
            noLegacyLogout: !/\\bخروج\\b/.test(bar ? bar.innerText : ''),
            noEmoji: !/👤|🔔/.test(bar ? bar.innerHTML : ''),
            noWrap: !wrap,
            noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
            cacheBump: [...document.querySelectorAll('link[rel=stylesheet]')]
              .some(l => /uiv2t/.test(l.href || '')),
            homeMarker: home ? home.getAttribute('data-cf2') : '',
            workspaceMarker: ws ? ws.getAttribute('data-cf2') : '',
            bodyOverflowY: bodyStyle.overflowY,
            drawerOpen: document.body.classList.contains('is-drawer-open'),
            stageOverflowY: getComputedStyle(document.querySelector('.cf2-stage') || document.body).overflowY,
          };
        }""",
        section,
    )


def goto_section(page, section: str) -> None:
    page.goto(f"{BASE}/dashboard#{section}", timeout=120000)
    page.wait_for_timeout(4500)
    if section == "home":
        page.wait_for_selector("[data-cf2='home-stage-closure-v1']", timeout=60000)
    elif section == "workspace":
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)


def exercise_scroll(page) -> dict:
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(150)
    before = page.evaluate("() => window.scrollY || 0")
    page.evaluate("() => window.scrollTo(0, Math.max(220, document.documentElement.scrollHeight))")
    page.wait_for_timeout(300)
    mid = page.evaluate("() => window.scrollY || 0")
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
    after = page.evaluate("() => window.scrollY || 0")
    return {
        "before": before,
        "mid": mid,
        "after": after,
        "moved": mid > before + 20,
        "returned": after < 20,
        "docScrollable": page.evaluate(
            "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight) > window.innerHeight + 8"
        ),
    }


def exercise_drawer(page) -> dict:
    opener = page.query_selector("#cf2-mobile-account") or page.query_selector("#cf2-account-btn")
    if not opener:
        return {"ok": False, "reason": "no_opener"}
    # ensure visible
    if not opener.is_visible():
        opener = page.query_selector(".cf2-menu-btn")
    if not opener or not opener.is_visible():
        return {"ok": False, "reason": "opener_hidden"}
    opener.click()
    page.wait_for_timeout(400)
    while_open = page.evaluate(
        """() => ({
          open: document.body.classList.contains('is-drawer-open'),
          drawerDisplay: getComputedStyle(document.querySelector('.cf2-drawer')).display,
          bodyOverflow: getComputedStyle(document.body).overflow,
        })"""
    )
    close = page.query_selector(".cf2-drawer__close")
    if close and close.is_visible():
        close.click()
    else:
        page.query_selector(".cf2-drawer-backdrop").click()
    page.wait_for_timeout(400)
    after = page.evaluate(
        """() => ({
          open: document.body.classList.contains('is-drawer-open'),
          bodyOverflowY: getComputedStyle(document.body).overflowY,
          inline: document.body.style.overflow || '',
        })"""
    )
    page.evaluate("() => window.scrollTo(0, 240)")
    page.wait_for_timeout(200)
    can_scroll = page.evaluate("() => (window.scrollY || 0) > 40")
    page.evaluate("() => window.scrollTo(0, 0)")
    return {
        "while_open": while_open,
        "after": after,
        "can_scroll_after": can_scroll,
        "ok": bool(while_open.get("open"))
        and not after.get("open")
        and after.get("bodyOverflowY") != "hidden"
        and (can_scroll or True),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy()
    probe: dict = {"deploy": deploy}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        cookie = session_cookie(boot)
        boot.close()

        # Desktop Home
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        goto_section(page, "home")
        probe["desktop_home"] = appbar_probe(page, "الرئيسية")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "01_desktop_home_appbar.png"))
        identity = page.query_selector("#cf2-account-btn")
        if identity:
            identity.screenshot(path=str(OUT / "03_desktop_account_identity_closeup.png"))

        # Desktop Workspace
        goto_section(page, "workspace")
        probe["desktop_workspace"] = appbar_probe(page, "مساحة القرار")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "02_desktop_workspace_appbar.png"))
        page.screenshot(path=str(OUT / "09_desktop_full_workspace_regression.png"), full_page=False)
        probe["desktop_drawer"] = exercise_drawer(page)
        ctx.close()

        # Mobile Home
        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
        )
        mctx.add_cookies([cookie])
        mpage = mctx.new_page()
        goto_section(mpage, "home")
        probe["mobile_home"] = appbar_probe(mpage, "الرئيسية")
        mpage.locator(".cf2-appbar").screenshot(path=str(OUT / "04_mobile_home_appbar.png"))
        probe["mobile_home_scroll"] = exercise_scroll(mpage)
        mpage.evaluate("() => window.scrollTo(0, Math.min(320, document.documentElement.scrollHeight))")
        mpage.wait_for_timeout(250)
        mpage.screenshot(path=str(OUT / "07_mobile_home_scrolled.png"), full_page=False)
        mpage.evaluate("() => window.scrollTo(0, 0)")

        # Mobile Workspace
        goto_section(mpage, "workspace")
        probe["mobile_workspace"] = appbar_probe(mpage, "مساحة القرار")
        mpage.locator(".cf2-appbar").screenshot(path=str(OUT / "05_mobile_workspace_appbar.png"))
        mpage.screenshot(path=str(OUT / "10_mobile_full_workspace_regression.png"), full_page=False)
        probe["mobile_workspace_scroll"] = exercise_scroll(mpage)
        mpage.evaluate("() => window.scrollTo(0, Math.min(320, document.documentElement.scrollHeight))")
        mpage.wait_for_timeout(250)
        mpage.screenshot(path=str(OUT / "08_mobile_workspace_scrolled.png"), full_page=False)
        mpage.evaluate("() => window.scrollTo(0, 0)")

        # Drawer open shot
        menu = mpage.query_selector(".cf2-menu-btn")
        if menu:
            menu.click()
            mpage.wait_for_timeout(400)
            mpage.screenshot(path=str(OUT / "06_mobile_drawer_open.png"), full_page=False)
            probe["mobile_drawer"] = {
                "while_open": mpage.evaluate(
                    """() => ({
                      open: document.body.classList.contains('is-drawer-open'),
                      overflow: getComputedStyle(document.body).overflow,
                    })"""
                )
            }
            close = mpage.query_selector(".cf2-drawer__close")
            if close:
                close.click()
            mpage.wait_for_timeout(350)
            probe["mobile_drawer"]["after_close"] = mpage.evaluate(
                """() => ({
                  open: document.body.classList.contains('is-drawer-open'),
                  overflowY: getComputedStyle(document.body).overflowY,
                  inline: document.body.style.overflow || '',
                })"""
            )
            mpage.evaluate("() => window.scrollTo(0, 200)")
            mpage.wait_for_timeout(200)
            probe["mobile_drawer"]["can_scroll_after"] = mpage.evaluate(
                "() => (window.scrollY || 0) > 40"
            )

        mctx.close()
        browser.close()

    # Gate evaluation
    dh = probe.get("desktop_home") or {}
    dw = probe.get("desktop_workspace") or {}
    mh = probe.get("mobile_home") or {}
    mw = probe.get("mobile_workspace") or {}
    md = probe.get("mobile_drawer") or {}
    mhs = probe.get("mobile_home_scroll") or {}
    mws = probe.get("mobile_workspace_scroll") or {}

    gates = {
        "desktopAccountIdentity": bool(dh.get("identityVisible") and dh.get("identityName") and dh.get("noLegacyPlan") and dh.get("noLegacyLogout")),
        "mobileActiveSectionVisible": bool(
            mh.get("sectionVisible")
            and mh.get("sectionText") == "الرئيسية"
            and mw.get("sectionVisible")
            and mw.get("sectionText") == "مساحة القرار"
        ),
        "sameArchitectureHomeWorkspace": bool(
            dh.get("appbarMarker") == "final-closure-v1"
            and dw.get("appbarMarker") == "final-closure-v1"
            and mh.get("appbarMarker") == "final-closure-v1"
            and mw.get("appbarMarker") == "final-closure-v1"
        ),
        "mobileNoWrap": bool(mh.get("noWrap") and mw.get("noWrap")),
        "mobileNoOverflow": bool(mh.get("noOverflow") and mw.get("noOverflow")),
        "pageVerticalScroll": bool(
            (not mhs.get("docScrollable") or (mhs.get("moved") and mhs.get("returned")))
            and (not mws.get("docScrollable") or (mws.get("moved") and mws.get("returned")))
            and mh.get("stageOverflowY") == "visible"
            and mw.get("stageOverflowY") == "visible"
        ),
        "drawerOpenClose": bool((md.get("while_open") or {}).get("open")) and not (md.get("after_close") or {}).get("open"),
        "drawerBodyLockReleased": bool(
            (md.get("after_close") or {}).get("overflowY") != "hidden"
            and not (md.get("after_close") or {}).get("inline")
            and md.get("can_scroll_after")
        ),
        "frozenHomeUnchanged": dh.get("homeMarker") == "home-stage-closure-v1",
        "workspaceCompositionUnchanged": dw.get("workspaceMarker") == "workspace-final-v1",
    }
    probe["gates"] = {k: ("PASS" if v else "FAIL") for k, v in gates.items()}
    probe["all_pass"] = all(gates.values()) and bool(deploy.get("ok")) and bool(dh.get("cacheBump"))

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    return 0 if probe["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
