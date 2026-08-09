# -*- coding: utf-8 -*-
"""Living Store — Merchant Shell Production Integration V1 evidence."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_shell_production_integration_v1"
SHOTS = OUT / "screenshots"
BASE = "https://smartreplyai.net"
MARKER = "shell-integration-v1"
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


PROBE = """() => {
  const chrome = document.querySelector('.cf2-chrome');
  const nav = document.querySelector('#cf2-nav');
  const navItems = [...(nav?.querySelectorAll('[data-cf2-nav]') || [])];
  const model = (window.CartFlowUiV2 && window.CartFlowUiV2.nav && window.CartFlowUiV2.nav.global) || [];
  const ctx = document.querySelector('#cf2-ctx');
  const handle = document.querySelector('#cf2-ctx-handle');
  const drawer = document.querySelector('#cf2-drawer');
  const stage = document.querySelector('.cf2-stage');
  const stageInner = document.querySelector('.cf2-stage__inner');
  const utility = document.querySelector('.cf2-utility');
  const globalRow = document.querySelector('.cf2-global');
  const docEl = document.documentElement;
  const body = document.body;
  const navRect = nav?.getBoundingClientRect();
  const stageRect = stage?.getBoundingClientRect();
  const overflowX = docEl.scrollWidth > docEl.clientWidth + 1;
  const navScrollable = !!(nav && nav.scrollWidth > nav.clientWidth + 2);
  const drawerText = (drawer?.innerText || '').replace(/\\s+/g, ' ').trim();
  const drawerHasPlatformPrimary = /أقسام المنصة/.test(drawerText);
  return {
    marker: chrome?.getAttribute('data-cf2-appbar'),
    modelIds: model.map(i => i.id),
    modelLabels: model.map(i => i.label),
    upbarIds: navItems.map(el => el.getAttribute('data-cf2-nav')),
    upbarLabels: navItems.map(el => (el.textContent || '').trim()),
    upbarVisible: !!(nav && getComputedStyle(nav).display !== 'none' && (navRect?.height || 0) > 2),
    utilityVisible: !!(utility && getComputedStyle(utility).display !== 'none'),
    globalRowVisible: !!(globalRow && getComputedStyle(globalRow).display !== 'none'),
    activeLabel: (nav?.querySelector('.cf2-nav__item.is-active')?.textContent || '').trim(),
    hash: location.hash,
    stageLead: (stageInner?.querySelector('.cf2-page.is-active .cf2-page__question')?.textContent || '').trim(),
    ctxArea: (ctx?.querySelector('.cf2-ctx__area')?.textContent || '').trim(),
    ctxItems: [...(ctx?.querySelectorAll('[data-cf2-ctx-item]') || [])].map(el => (el.textContent || '').trim()),
    handleVisible: !!(handle && !handle.hidden && getComputedStyle(handle).display !== 'none' && handle.getBoundingClientRect().width > 2),
    ctxOpen: body.classList.contains('is-ctx-open'),
    drawerOpen: body.classList.contains('is-drawer-open'),
    drawerHasPlatformPrimary,
    drawerHasAccount: /الملف والباقة|تسجيل الخروج/.test(drawerText),
    hasGlobalBtn: !!document.querySelector('#cf2-global-btn, .cf2-global-btn'),
    hasGlobalPanel: !!document.querySelector('#cf2-global-panel, .cf2-global-panel'),
    hasCtxBtnInChrome: !!document.querySelector('.cf2-chrome #cf2-ctx-btn, .cf2-chrome .cf2-ctx-btn'),
    hasPageChrome: !!document.querySelector('#cf2-page-chrome, .cf2-page-chrome'),
    overflowX,
    navScrollable,
    stageWidth: stageRect?.width || 0,
    viewportWidth: window.innerWidth,
    stageFitsViewport: !stageRect || stageRect.width <= window.innerWidth + 1,
    bodyOverflowY: getComputedStyle(body).overflowY,
  };
}"""


def evaluate_gates(probes: dict, overflow: dict) -> dict:
    mobile = probes.get("mobile_430_home_closed") or {}
    mobile_ws = probes.get("mobile_430_workspace_closed") or {}
    mobile_ctx = probes.get("mobile_430_home_context_open") or {}
    mobile_ws_ctx = probes.get("mobile_430_workspace_context_open") or {}
    mobile_acct = probes.get("mobile_account_utility_open") or {}
    desk_home = probes.get("desktop_home") or {}
    desk_ws = probes.get("desktop_workspace") or {}
    restore = probes.get("mobile_home_restore") or {}

    return {
        "globalVisibleMobileClosed": bool(mobile.get("upbarVisible"))
        and list(mobile.get("upbarIds") or []) == CANONICAL_IDS,
        "sameGlobalModelDesktopMobile": list(desk_home.get("modelIds") or [])
        == CANONICAL_IDS
        and list(mobile.get("modelIds") or []) == CANONICAL_IDS
        and list(desk_home.get("upbarIds") or []) == list(mobile.get("upbarIds") or []),
        "contextualSameOwner": desk_home.get("ctxArea") == "الرئيسية"
        and "نظرة عامة" in (desk_home.get("ctxItems") or [])
        and "الملخص" in (desk_home.get("ctxItems") or [])
        and mobile_ws.get("ctxArea") == "مساحة القرار"
        and "ما يحتاج قرارك" in (mobile_ws.get("ctxItems") or []),
        "accountUtilitySeparate": bool(mobile_acct.get("drawerOpen"))
        and bool(mobile_acct.get("drawerHasAccount"))
        and not bool(mobile_acct.get("drawerHasPlatformPrimary"))
        and not bool(mobile_acct.get("ctxOpen")),
        "rejectedExperimentsGone": not mobile.get("hasGlobalBtn")
        and not mobile.get("hasGlobalPanel")
        and not mobile.get("hasCtxBtnInChrome")
        and not mobile.get("hasPageChrome"),
        "homeCompositionUnchanged": "ماذا يجب أن أعرف الآن عن متجري؟"
        in (mobile.get("stageLead") or ""),
        "workspaceCompositionUnchanged": "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟"
        in (mobile_ws.get("stageLead") or ""),
        "workspaceSwitchWorks": mobile_ws.get("hash") == "#workspace"
        and mobile_ws.get("activeLabel") == "مساحة القرار",
        "homeRestoreWorks": restore.get("hash") == "#home"
        and restore.get("activeLabel") == "الرئيسية",
        "contextOpenHomeOnly": bool(mobile_ctx.get("ctxOpen"))
        and mobile_ctx.get("ctxArea") == "الرئيسية"
        and not bool(mobile_ctx.get("drawerOpen")),
        "contextOpenWorkspaceOnly": bool(mobile_ws_ctx.get("ctxOpen"))
        and mobile_ws_ctx.get("ctxArea") == "مساحة القرار",
        "mobileHandlePresentWhenCtx": bool(mobile.get("handleVisible")),
        "noExtraNavLayer": not mobile.get("hasGlobalBtn")
        and not mobile.get("hasGlobalPanel")
        and not mobile.get("hasPageChrome")
        and not mobile.get("hasCtxBtnInChrome"),
        "overflowOk": all(bool(v.get("ok")) for v in overflow.values()),
    }


def overflow_probe(page) -> dict:
    return page.evaluate(
        """() => {
          const docEl = document.documentElement;
          const nav = document.querySelector('#cf2-nav');
          const stage = document.querySelector('.cf2-stage');
          const root = document.querySelector('.cf2-root');
          const pageOverflow = docEl.scrollWidth > docEl.clientWidth + 1;
          const stageOverflow = stage && stage.scrollWidth > stage.clientWidth + 1;
          const rootOverflow = root && root.scrollWidth > root.clientWidth + 1;
          const navOnlyScroll = !!(nav && nav.scrollWidth > nav.clientWidth + 2);
          return {
            pageOverflow,
            stageOverflow,
            rootOverflow,
            navOnlyScroll,
            viewportWidth: window.innerWidth,
            scrollWidth: docEl.scrollWidth,
            ok: !pageOverflow && !stageOverflow && !rootOverflow,
          };
        }"""
    )


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
    overflow: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        desk = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = desk.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        desk.add_cookies([session_cookie(page)])
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-chrome[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["desktop_home"] = page.evaluate(PROBE)
        overflow["desktop_1440_home"] = overflow_probe(page)
        page.screenshot(path=str(SHOTS / "01_desktop_home.png"), full_page=True)

        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["desktop_workspace"] = page.evaluate(PROBE)
        overflow["desktop_1440_workspace"] = overflow_probe(page)
        page.screenshot(path=str(SHOTS / "02_desktop_workspace.png"), full_page=True)
        desk.close()

        # 1024 overflow check
        tab = browser.new_context(viewport={"width": 1024, "height": 768}, locale="ar-SA")
        page = tab.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        tab.add_cookies([session_cookie(page)])
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1500)
        page.wait_for_selector(f'.cf2-chrome[data-cf2-appbar="{MARKER}"]', timeout=60000)
        overflow["tablet_1024"] = overflow_probe(page)
        tab.close()

        mobile = browser.new_context(
            viewport={"width": 430, "height": 932},
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
        page.wait_for_selector(f'.cf2-chrome[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["mobile_430_home_closed"] = page.evaluate(PROBE)
        overflow["mobile_430_home"] = overflow_probe(page)
        page.screenshot(path=str(SHOTS / "03_mobile_430_home_closed.png"), full_page=False)

        page.evaluate(
            """() => {
              const nav = document.querySelector('#cf2-nav');
              if (nav) nav.scrollLeft = nav.scrollWidth;
            }"""
        )
        page.wait_for_timeout(250)
        evidence["probes"]["mobile_430_home_scrolled"] = page.evaluate(PROBE)
        page.screenshot(
            path=str(SHOTS / "04_mobile_430_home_global_scrolled.png"), full_page=False
        )

        page.click("#cf2-ctx-handle")
        page.wait_for_timeout(400)
        evidence["probes"]["mobile_430_home_context_open"] = page.evaluate(PROBE)
        page.screenshot(
            path=str(SHOTS / "05_mobile_430_home_context_open.png"), full_page=False
        )

        page.evaluate("() => window.CartFlowUiV2.closeCtxDrawer()")
        page.wait_for_timeout(200)
        page.click('#cf2-nav [data-cf2-nav="workspace"]')
        page.wait_for_timeout(2500)
        evidence["probes"]["mobile_430_workspace_closed"] = page.evaluate(PROBE)
        overflow["mobile_430_workspace"] = overflow_probe(page)
        page.screenshot(
            path=str(SHOTS / "06_mobile_430_workspace_closed.png"), full_page=False
        )

        page.click("#cf2-ctx-handle")
        page.wait_for_timeout(400)
        evidence["probes"]["mobile_430_workspace_context_open"] = page.evaluate(PROBE)
        page.screenshot(
            path=str(SHOTS / "07_mobile_430_workspace_context_open.png"), full_page=False
        )

        page.evaluate("() => window.CartFlowUiV2.closeCtxDrawer()")
        page.wait_for_timeout(200)
        page.click("#cf2-mobile-account")
        page.wait_for_timeout(400)
        evidence["probes"]["mobile_account_utility_open"] = page.evaluate(PROBE)
        page.screenshot(
            path=str(SHOTS / "10_mobile_account_utility_open.png"), full_page=False
        )

        page.evaluate(
            "() => { const b = document.querySelector('.cf2-drawer-backdrop'); if (b) b.click(); }"
        )
        page.wait_for_timeout(200)
        page.click('#cf2-nav [data-cf2-nav="home"]')
        page.wait_for_timeout(2000)
        evidence["probes"]["mobile_home_restore"] = page.evaluate(PROBE)
        mobile.close()

        m390 = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ar-SA",
        )
        page = m390.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        m390.add_cookies([session_cookie(page)])
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        page.wait_for_selector(f'.cf2-chrome[data-cf2-appbar="{MARKER}"]', timeout=60000)
        evidence["probes"]["mobile_390_home_closed"] = page.evaluate(PROBE)
        overflow["mobile_390_home"] = overflow_probe(page)
        page.screenshot(path=str(SHOTS / "08_mobile_390_home_closed.png"), full_page=False)

        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2000)
        evidence["probes"]["mobile_390_workspace_closed"] = page.evaluate(PROBE)
        overflow["mobile_390_workspace"] = overflow_probe(page)
        page.screenshot(
            path=str(SHOTS / "09_mobile_390_workspace_closed.png"), full_page=False
        )
        m390.close()
        browser.close()

    evidence["gates"] = evaluate_gates(evidence["probes"], overflow)
    evidence["all_gates_pass"] = all(bool(v) for v in evidence["gates"].values())
    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "responsive_overflow_probe.json").write_text(
        json.dumps({"deploy": deploy, "viewports": overflow}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "all_gates_pass": evidence["all_gates_pass"],
                "gates": evidence["gates"],
                "deploy": deploy,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
