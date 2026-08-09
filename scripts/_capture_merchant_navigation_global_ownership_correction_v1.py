# -*- coding: utf-8 -*-
"""Living Store — Global Ownership Correction V1 evidence + acceptance probes."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_navigation_global_ownership_correction_v1"
SHOTS = OUT / "screenshots"
BASE = "https://smartreplyai.net"
MARKER = "global-ownership-v1"
CANONICAL_IDS = ["home", "workspace", "products", "carts", "comms", "settings"]
CANONICAL_LABELS = [
    "الرئيسية",
    "مساحة القرار",
    "المنتجات",
    "السلال",
    "التواصل",
    "الإعدادات",
]


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


OWNERSHIP_PROBE = """() => {
  const appbar = document.querySelector('.cf2-appbar');
  const navModel = window.CartFlowUiV2 && window.CartFlowUiV2.nav;
  const globalModel = (navModel && navModel.global) || [];
  const upbar = document.querySelector('#cf2-nav');
  const upbarIds = [...(upbar?.querySelectorAll('[data-cf2-nav]') || [])].map(el => el.getAttribute('data-cf2-nav'));
  const mobileList = document.querySelector('#cf2-global-panel-list');
  const mobileIds = [...(mobileList?.querySelectorAll('[data-cf2-nav]') || [])].map(el => el.getAttribute('data-cf2-nav'));
  const drawerMount = document.querySelector('#cf2-drawer-global');
  const drawerIds = [...(drawerMount?.querySelectorAll('[data-cf2-nav]') || [])].map(el => el.getAttribute('data-cf2-nav'));
  const globalBtn = document.querySelector('#cf2-global-btn');
  const ctxBtn = document.querySelector('#cf2-ctx-btn');
  const accountBtn = document.querySelector('#cf2-mobile-account');
  const menuBtn = document.querySelector('.cf2-menu-btn');
  const panel = document.querySelector('#cf2-global-panel');
  const drawer = document.querySelector('#cf2-drawer');
  const ctx = document.querySelector('#cf2-ctx');
  const stage = document.querySelector('.cf2-stage__inner');
  const appbarRect = appbar?.getBoundingClientRect();
  const overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
  const bodyOverflow = getComputedStyle(document.body).overflowY;
  return {
    marker: appbar?.getAttribute('data-cf2-appbar'),
    globalModelIds: globalModel.map(i => i.id),
    globalModelLabels: globalModel.map(i => i.label),
    upbarIds,
    mobileIds,
    drawerIds,
    globalBtnVisible: !!(globalBtn && getComputedStyle(globalBtn).display !== 'none' && globalBtn.getBoundingClientRect().width > 2),
    ctxBtnVisible: !!(ctxBtn && !ctxBtn.hidden && getComputedStyle(ctxBtn).display !== 'none' && ctxBtn.getBoundingClientRect().width > 2),
    accountBtnVisible: !!(accountBtn && getComputedStyle(accountBtn).display !== 'none' && accountBtn.getBoundingClientRect().width > 2),
    menuBtnVisible: !!(menuBtn && getComputedStyle(menuBtn).display !== 'none' && menuBtn.getBoundingClientRect().width > 2),
    globalPanelOpen: document.body.classList.contains('is-global-nav-open'),
    drawerOpen: document.body.classList.contains('is-drawer-open'),
    ctxOpen: document.body.classList.contains('is-ctx-open'),
    panelDistinctFromDrawer: panel !== drawer,
    ctxDistinctFromPanel: ctx !== panel,
    ctxDistinctFromDrawer: ctx !== drawer,
    hash: location.hash,
    stageLead: (stage?.querySelector('.cf2-page.is-active .cf2-page__question')?.textContent || '').trim(),
    sidebarArea: (ctx?.querySelector('.cf2-ctx__area')?.textContent || '').trim(),
    sidebarItems: [...(ctx?.querySelectorAll('[data-cf2-ctx-item]') || [])].map(el => (el.textContent || '').trim()),
    appbarWidth: appbarRect?.width || 0,
    overflowX,
    bodyAllowsScroll: bodyOverflow !== 'hidden' || document.body.classList.contains('is-global-nav-open') || document.body.classList.contains('is-drawer-open') || document.body.classList.contains('is-ctx-open'),
    hasPageChrome: !!document.querySelector('#cf2-page-chrome, .cf2-page-chrome'),
    hasSectionChrome: !!document.querySelector('#cf2-section-chrome'),
    hasTanqul: /تنقل القسم/.test(document.body.innerText || ''),
  };
}"""


def same_ids(a, b) -> bool:
    return list(a or []) == list(b or [])


def evaluate_gates(probes: dict) -> dict:
    mobile_closed = probes.get("mobile_home_closed") or {}
    mobile_global = probes.get("mobile_home_global_open") or {}
    mobile_ws = probes.get("mobile_workspace_after_switch") or {}
    mobile_ctx = probes.get("mobile_workspace_ctx_open") or {}
    mobile_acct = probes.get("mobile_account_drawer") or {}
    desk_home = probes.get("desktop_home") or {}
    desk_ws = probes.get("desktop_workspace") or {}

    model_ok = same_ids(mobile_closed.get("globalModelIds"), CANONICAL_IDS) and same_ids(
        mobile_closed.get("globalModelLabels"), CANONICAL_LABELS
    )
    return {
        "globalNavCanonicalModel": model_ok,
        "desktopGlobalNavConsumesCanonicalModel": same_ids(
            desk_home.get("upbarIds"), CANONICAL_IDS
        )
        and same_ids(desk_home.get("globalModelIds"), CANONICAL_IDS),
        "mobileGlobalNavConsumesCanonicalModel": same_ids(
            mobile_global.get("mobileIds"), CANONICAL_IDS
        )
        and same_ids(mobile_global.get("globalModelIds"), CANONICAL_IDS),
        "drawerIfUsedConsumesCanonicalModel": same_ids(
            mobile_acct.get("drawerIds"), CANONICAL_IDS
        ),
        "mobileGlobalNavNotDrawerOnly": bool(mobile_closed.get("globalBtnVisible"))
        and bool(mobile_global.get("globalPanelOpen"))
        and not bool(mobile_global.get("drawerOpen"))
        and bool(mobile_global.get("panelDistinctFromDrawer")),
        "globalAndContextualSeparate": bool(mobile_ctx.get("ctxDistinctFromPanel"))
        and bool(mobile_ctx.get("ctxOpen"))
        and not bool(mobile_ctx.get("globalPanelOpen"))
        and not bool(mobile_ctx.get("drawerOpen")),
        "globalAndAccountSeparate": bool(mobile_acct.get("drawerOpen"))
        and not bool(mobile_acct.get("globalPanelOpen"))
        and bool(mobile_acct.get("panelDistinctFromDrawer")),
        "desktopUpbarUnchanged": bool(desk_home.get("upbarIds"))
        and desk_home.get("marker") == MARKER
        and not desk_home.get("globalBtnVisible"),
        "contextualArchitectureUnchanged": desk_home.get("sidebarArea") == "الرئيسية"
        and "نظرة عامة" in (desk_home.get("sidebarItems") or [])
        and mobile_ws.get("sidebarArea") == "مساحة القرار",
        "homeCompositionUnchanged": "ماذا يجب أن أعرف الآن عن متجري؟"
        in (mobile_closed.get("stageLead") or ""),
        "workspaceCompositionUnchanged": "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟"
        in (mobile_ws.get("stageLead") or ""),
        "mobileNoHorizontalOverflow": not bool(mobile_closed.get("overflowX"))
        and not bool(mobile_ws.get("overflowX")),
        "mobileVerticalScroll": bool(mobile_closed.get("bodyAllowsScroll"))
        and bool(mobile_ws.get("bodyAllowsScroll")),
        "rejectedChromeAbsent": not mobile_closed.get("hasPageChrome")
        and not mobile_closed.get("hasSectionChrome")
        and not mobile_closed.get("hasTanqul"),
        "workspaceHashAfterGlobalSwitch": mobile_ws.get("hash") == "#workspace",
        "homeHashRestore": probes.get("mobile_home_restore", {}).get("hash") == "#home",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    sha_prefix = (
        (OUT / "expected_sha.txt").read_text(encoding="utf-8").strip()
        if (OUT / "expected_sha.txt").exists()
        else ""
    )
    deploy = wait_for_deploy(sha_prefix)
    evidence: dict = {"deploy": deploy, "probes": {}, "gates": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Desktop regression
        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = desk.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        desk.add_cookies([session_cookie(page)])
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-appbar[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["desktop_home"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(path=str(SHOTS / "06_desktop_home_regression.png"), full_page=True)
        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["desktop_workspace"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(
            path=str(SHOTS / "07_desktop_workspace_regression.png"), full_page=True
        )
        desk.close()

        # Mobile evidence
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        page = mobile.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        mobile.add_cookies([session_cookie(page)])
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-appbar[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["mobile_home_closed"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(path=str(SHOTS / "01_mobile_home_closed.png"), full_page=False)

        page.click("#cf2-global-btn")
        page.wait_for_timeout(500)
        evidence["probes"]["mobile_home_global_open"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(
            path=str(SHOTS / "02_mobile_home_global_nav_open.png"), full_page=False
        )

        page.click('#cf2-global-panel-list [data-cf2-nav="workspace"]')
        page.wait_for_timeout(2500)
        evidence["probes"]["mobile_workspace_after_switch"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(
            path=str(SHOTS / "03_mobile_workspace_after_global_switch.png"),
            full_page=False,
        )

        if page.locator("#cf2-ctx-btn:not([hidden])").count():
            page.click("#cf2-ctx-btn")
            page.wait_for_timeout(500)
        evidence["probes"]["mobile_workspace_ctx_open"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(
            path=str(SHOTS / "04_mobile_workspace_contextual_nav_open.png"),
            full_page=False,
        )

        if page.locator("body.is-ctx-open").count():
            page.evaluate(
                "() => window.CartFlowUiV2 && window.CartFlowUiV2.closeCtxDrawer()"
            )
            page.wait_for_timeout(300)
        page.click("#cf2-mobile-account")
        page.wait_for_timeout(500)
        evidence["probes"]["mobile_account_drawer"] = page.evaluate(OWNERSHIP_PROBE)
        page.screenshot(
            path=str(SHOTS / "05_mobile_global_account_drawer.png"), full_page=False
        )

        if page.locator("body.is-drawer-open").count():
            page.evaluate(
                "() => { const b = document.querySelector('.cf2-drawer-backdrop'); if (b) b.click(); }"
            )
            page.wait_for_timeout(300)
        page.click("#cf2-global-btn")
        page.wait_for_timeout(400)
        page.click('#cf2-global-panel-list [data-cf2-nav="home"]')
        page.wait_for_timeout(2000)
        evidence["probes"]["mobile_home_restore"] = page.evaluate(OWNERSHIP_PROBE)

        mobile.close()
        browser.close()

    evidence["gates"] = evaluate_gates(evidence["probes"])
    evidence["all_gates_pass"] = all(bool(v) for v in evidence["gates"].values())
    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"all_gates_pass": evidence["all_gates_pass"], "gates": evidence["gates"], "deploy": deploy}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
