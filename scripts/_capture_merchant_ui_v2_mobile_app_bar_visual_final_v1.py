# -*- coding: utf-8 -*-
"""Living Store — Mobile App Bar Visual Composition Final V1."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_mobile_app_bar_visual_final_v1"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_app_bar_mobile_reality_correction_v1"
    / "01_mobile_home_bar_closed.png"
)
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = ""  # filled by caller / env after push


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


COMPOSITION_PROBE = """(expectedSection) => {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const intersects = (r) =>
    !!r && r.w >= 8 && r.h >= 8 && r.right > 2 && r.left < vw - 2 &&
    r.top < Math.min(vh, 80) && r.bottom > 0;

  const account = document.querySelector('#cf2-mobile-account');
  const core = document.querySelector('.cf2-appbar__core');
  const brand = document.querySelector('.cf2-brand');
  const mark = document.querySelector('.cf2-brand__mark');
  const word = document.querySelector('.cf2-brand__word');
  const rule = document.querySelector('.cf2-appbar__core-rule');
  const section = document.querySelector('#cf2-appbar-section');
  const menu = document.querySelector('.cf2-menu-btn');
  const bar = document.querySelector('.cf2-appbar');

  const wordStyle = word ? getComputedStyle(word) : null;
  const wordClipped =
    !!wordStyle &&
    ((wordStyle.clip !== 'auto' && wordStyle.clip !== 'rect(auto, auto, auto, auto)' &&
      wordStyle.clip.includes('0px')) ||
      (wordStyle.position === 'absolute' &&
        (parseFloat(wordStyle.width) <= 1 || parseFloat(wordStyle.height) <= 1)) ||
      wordStyle.visibility === 'hidden' ||
      wordStyle.opacity === '0' ||
      wordStyle.display === 'none');

  const rectOf = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      left: Math.round(r.left), right: Math.round(r.right),
      top: Math.round(r.top), bottom: Math.round(r.bottom),
    };
  };

  const accountR = rectOf(account);
  const coreR = rectOf(core);
  const brandR = rectOf(brand);
  const markR = rectOf(mark);
  const wordR = rectOf(word);
  const ruleR = rectOf(rule);
  const sectionR = rectOf(section);
  const menuR = rectOf(menu);
  const barR = rectOf(bar);

  const sectionText = (section || {}).textContent?.trim() || '';
  const wordText = (word || {}).textContent?.trim() || '';
  const accountCs = account ? getComputedStyle(account) : null;
  const menuCs = menu ? getComputedStyle(menu) : null;
  const sectionCs = section ? getComputedStyle(section) : null;
  const coreCs = core ? getComputedStyle(core) : null;
  const barCs = bar ? getComputedStyle(bar) : null;

  const accountVisible = intersects(accountR);
  const markVisible = intersects(markR);
  const wordVisible = intersects(wordR) && !wordClipped && /CartFlow/i.test(wordText);
  const brandVisible = intersects(brandR) && markVisible && wordVisible;
  const ruleVisible = !!ruleR && ruleR.w >= 1 && ruleR.h >= 8 &&
    ruleR.right > 2 && ruleR.left < vw - 2 &&
    ruleR.top < Math.min(vh, 80) && ruleR.bottom > 0;
  const sectionVisible =
    intersects(sectionR) && sectionText === expectedSection && (sectionR.w >= 28);
  const menuVisible = intersects(menuR);
  const coreVisible = intersects(coreR);

  // Core cluster: brand + rule + section as one contiguous unit (tight gap)
  const brandToSectionGap =
    brandVisible && sectionVisible ? sectionR.left - brandR.right : null;
  const coreTight =
    brandToSectionGap != null && brandToSectionGap >= 8 && brandToSectionGap <= 48;

  const threeZoneOrder =
    accountVisible && coreVisible && menuVisible &&
    accountR.left < coreR.left && coreR.left < menuR.left &&
    brandVisible && ruleVisible && sectionVisible &&
    brandR.left < ruleR.left && ruleR.left < sectionR.left;

  const wrap =
    !!barR &&
    [accountR, coreR, brandR, sectionR, menuR].some(
      (r) => r && r.bottom > barR.bottom + 3
    );

  const edgeQuiet =
    !!accountCs && !!menuCs &&
    accountCs.borderWidth === '0px' &&
    menuCs.borderWidth === '0px';

  const sectionQuieterThanBrand =
    !!sectionCs && !!wordStyle &&
    parseFloat(sectionCs.fontWeight) <= parseFloat(wordStyle.fontWeight) &&
    parseFloat(sectionCs.fontSize) <= parseFloat(wordStyle.fontSize);

  return {
    viewport: { w: vw, h: vh },
    appbarMarker: bar ? bar.getAttribute('data-cf2-appbar') : '',
    expectedSection,
    sectionText,
    wordText,
    wordClipped,
    brandToSectionGap,
    coreTight,
    threeZoneOrder,
    edgeQuiet,
    sectionQuieterThanBrand,
    barDisplay: barCs ? barCs.display : '',
    coreDisplay: coreCs ? coreCs.display : '',
    rects: {
      bar: barR, account: accountR, core: coreR, brand: brandR,
      mark: markR, word: wordR, rule: ruleR, section: sectionR, menu: menuR,
    },
    visible: {
      account: accountVisible, core: coreVisible, brand: brandVisible,
      mark: markVisible, word: wordVisible, rule: ruleVisible,
      section: sectionVisible, menu: menuVisible,
    },
    noWrap: !wrap,
    noOverflow: document.documentElement.scrollWidth <= vw + 1,
    homeMarker:
      document.querySelector('[data-cf2=\"home-stage-closure-v1\"]')?.getAttribute('data-cf2') || '',
    workspaceMarker:
      document.querySelector('[data-cf2=\"workspace-final-v1\"]')?.getAttribute('data-cf2') || '',
    allFourVisible:
      accountVisible && brandVisible && sectionVisible && menuVisible,
  };
}"""


def visual_probe(page, expected_section: str) -> dict:
    return page.evaluate(COMPOSITION_PROBE, expected_section)


def goto_section(page, section: str) -> None:
    page.goto(f"{BASE}/dashboard#{section}", timeout=120000)
    page.wait_for_timeout(4500)
    if section == "home":
        page.wait_for_selector("[data-cf2='home-stage-closure-v1']", timeout=60000)
    else:
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)


def make_before_after(after_path: Path, out_path: Path) -> bool:
    if Image is None or not BEFORE.exists() or not after_path.exists():
        return False
    before = Image.open(BEFORE).convert("RGB")
    after = Image.open(after_path).convert("RGB")
    w = max(before.width, after.width)
    gap = 24
    label_h = 36
    canvas = Image.new("RGB", (w * 2 + gap, max(before.height, after.height) + label_h), (8, 32, 72))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), "BEFORE — reality fix (four siblings)", fill=(255, 255, 255))
    draw.text((w + gap + 12, 10), "AFTER — visual final (three zones)", fill=(255, 255, 255))
    canvas.paste(before, (0, label_h))
    canvas.paste(after, (w + gap, label_h))
    canvas.save(out_path)
    return True


def pass_closed(p: dict) -> bool:
    return bool(
        p.get("allFourVisible")
        and p.get("threeZoneOrder")
        and p.get("coreTight")
        and p.get("edgeQuiet")
        and p.get("sectionQuieterThanBrand")
        and p.get("noWrap")
        and p.get("noOverflow")
        and not p.get("wordClipped")
        and p.get("appbarMarker") == "mobile-visual-final-v1"
        and (p.get("visible") or {}).get("rule")
    )


def main() -> int:
    import os

    sha_prefix = os.environ.get("CF_EXPECTED_SHA", EXPECTED_SHA_PREFIX).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    deploy = wait_for_deploy(sha_prefix) if sha_prefix else wait_for_deploy("")
    probe: dict = {"deploy": deploy}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 390, "height": 844}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        cookie = session_cookie(boot)
        boot.close()

        # —— 390px class ——
        m390 = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
            device_scale_factor=3,
        )
        m390.add_cookies([cookie])
        page = m390.new_page()

        goto_section(page, "home")
        probe["01_home_closed"] = visual_probe(page, "الرئيسية")
        page.screenshot(path=str(OUT / "01_mobile_home_closed.png"), full_page=False)
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "03_mobile_home_appbar_closeup.png"))
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "08_mobile_390px.png"))

        page.query_selector(".cf2-menu-btn").click()
        page.wait_for_timeout(450)
        probe["05_drawer_open"] = page.evaluate(
            """() => ({
              open: document.body.classList.contains('is-drawer-open'),
              overflow: getComputedStyle(document.body).overflow,
            })"""
        )
        page.screenshot(path=str(OUT / "05_mobile_drawer_open.png"), full_page=False)

        page.query_selector(".cf2-drawer__close").click()
        page.wait_for_timeout(400)
        probe["06_after_drawer_close"] = visual_probe(page, "الرئيسية")
        page.locator(".cf2-appbar").screenshot(path=str(OUT / "06_mobile_after_drawer_close.png"))
        probe["06_body_lock"] = page.evaluate(
            """() => ({
              open: document.body.classList.contains('is-drawer-open'),
              overflowY: getComputedStyle(document.body).overflowY,
              inline: document.body.style.overflow || '',
            })"""
        )

        page.evaluate("() => { location.hash = '#workspace'; }")
        page.wait_for_timeout(5000)
        page.wait_for_selector("[data-cf2='workspace-final-v1']", timeout=60000)
        probe["02_workspace_closed"] = visual_probe(page, "مساحة القرار")
        page.screenshot(path=str(OUT / "02_mobile_workspace_closed.png"), full_page=False)
        page.locator(".cf2-appbar").screenshot(
            path=str(OUT / "04_mobile_workspace_appbar_closeup.png")
        )
        page.locator(".cf2-appbar").screenshot(
            path=str(OUT / "07_mobile_after_home_workspace_switch.png")
        )

        page.evaluate("() => { location.hash = '#home'; }")
        page.wait_for_timeout(3500)
        page.wait_for_selector("[data-cf2='home-stage-closure-v1']", timeout=60000)
        probe["back_home"] = visual_probe(page, "الرئيسية")

        page.evaluate(
            """() => {
              const el = document.querySelector('.cf2-stage') || document.body;
              const h = Math.max(el.scrollHeight || 0, document.documentElement.scrollHeight || 0);
              window.scrollTo(0, Math.min(320, Math.max(120, h - window.innerHeight + 40)));
            }"""
        )
        page.wait_for_timeout(300)
        probe["scroll_after"] = page.evaluate("() => window.scrollY || 0")
        page.evaluate("() => window.scrollTo(0, 0)")
        probe["scroll_capable"] = page.evaluate(
            """() => {
              const h = Math.max(
                document.documentElement.scrollHeight || 0,
                document.body.scrollHeight || 0
              );
              return h > window.innerHeight + 40;
            }"""
        )
        m390.close()

        # —— 430px class ——
        m430 = browser.new_context(
            viewport={"width": 430, "height": 932},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
            device_scale_factor=3,
        )
        m430.add_cookies([cookie])
        p430 = m430.new_page()
        goto_section(p430, "home")
        probe["09_430"] = visual_probe(p430, "الرئيسية")
        p430.locator(".cf2-appbar").screenshot(path=str(OUT / "09_mobile_430px.png"))
        m430.close()

        # Desktop regression (unchanged architecture)
        dctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        dctx.add_cookies([cookie])
        dpage = dctx.new_page()
        goto_section(dpage, "workspace")
        probe["desktop"] = dpage.evaluate(
            """() => ({
              identity: !!(document.querySelector('#cf2-account-btn') &&
                getComputedStyle(document.querySelector('#cf2-account-btn')).display !== 'none'),
              identityName: (document.querySelector('.cf2-appbar__identity-name')||{}).textContent||'',
              coreDisplay: getComputedStyle(document.querySelector('.cf2-appbar__core')).display,
              sectionHidden: getComputedStyle(document.querySelector('#cf2-appbar-section')).display === 'none',
              homeFrozen: !!document.querySelector('[data-cf2=\"home-stage-closure-v1\"]'),
              workspace: document.querySelector('[data-cf2=\"workspace-final-v1\"]')?.getAttribute('data-cf2') || '',
              noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
            })"""
        )
        dctx.close()
        browser.close()

    make_before_after(OUT / "03_mobile_home_appbar_closeup.png", OUT / "10_before_after_appbar.png")
    probe["before_after_written"] = (OUT / "10_before_after_appbar.png").exists()

    gates = {
        "compositionHome": pass_closed(probe.get("01_home_closed") or {}),
        "compositionWorkspace": pass_closed(probe.get("02_workspace_closed") or {}),
        "composition390": pass_closed(probe.get("01_home_closed") or {}),
        "composition430": pass_closed(probe.get("09_430") or {}),
        "wordmarkNotClipped": not (probe.get("01_home_closed") or {}).get("wordClipped")
        and (probe.get("01_home_closed") or {}).get("wordText") == "CartFlow",
        "sectionHome": (probe.get("01_home_closed") or {}).get("sectionText") == "الرئيسية",
        "sectionWorkspace": (probe.get("02_workspace_closed") or {}).get("sectionText")
        == "مساحة القرار",
        "afterDrawerClose": pass_closed(probe.get("06_after_drawer_close") or {}),
        "afterHomeWorkspaceSwitch": pass_closed(probe.get("02_workspace_closed") or {}),
        "backHomePreserved": pass_closed(probe.get("back_home") or {}),
        "drawerBodyLockReleased": (probe.get("06_body_lock") or {}).get("overflowY") != "hidden"
        and not (probe.get("06_body_lock") or {}).get("open"),
        "pageVerticalScroll": (probe.get("scroll_after") or 0) > 40
        or bool(probe.get("scroll_capable")),
        "desktopIdentityIntact": bool((probe.get("desktop") or {}).get("identity"))
        and (probe.get("desktop") or {}).get("coreDisplay") == "contents",
        "homeCompositionUntouched": (probe.get("01_home_closed") or {}).get("homeMarker")
        == "home-stage-closure-v1",
        "workspaceCompositionUntouched": (probe.get("desktop") or {}).get("workspace")
        == "workspace-final-v1",
        "markerFinal": (probe.get("01_home_closed") or {}).get("appbarMarker")
        == "mobile-visual-final-v1",
    }
    probe["gates"] = {k: ("PASS" if v else "FAIL") for k, v in gates.items()}
    probe["all_pass"] = all(gates.values()) and bool(deploy.get("ok"))

    (OUT / "production_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"gates": probe["gates"], "all_pass": probe["all_pass"], "deploy": deploy},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if probe["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
