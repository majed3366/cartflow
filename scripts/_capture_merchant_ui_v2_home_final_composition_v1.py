# -*- coding: utf-8 -*-
"""Living Store captures — Final Home Product Composition V1."""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_home_final_composition_v1"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_visual_language_maturity_v1"
    / "09_desktop_home.png"
)
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = "pending"


def wait_for_deploy(timeout_s: int = 600) -> dict:
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
        except Exception as exc:  # noqa: BLE001 — deploy flap (502/timeout)
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "before").mkdir(exist_ok=True)
    if BEFORE.is_file():
        shutil.copy2(BEFORE, OUT / "before" / "01_desktop_home.png")

    deploy = wait_for_deploy()
    probe: dict = {"deploy": deploy}

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
        cookie = {
            "name": session["cookie_name"],
            "value": session["cookie_value"],
            "url": BASE,
            "httpOnly": True,
            "sameSite": "Lax",
        }

        def home_probe(page):
            return page.evaluate(
                """() => {
                  const labels = [...document.querySelectorAll('.cf2-co__label')]
                    .map(el => (el.textContent || '').trim())
                    .filter(Boolean);
                  const visibleDesignVocab = labels.some(t =>
                    /تكثيف|تجميع|متناثر|متوافق|مركز الجاذبية|كثافة الدليل/.test(t)
                  );
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    home: !!document.querySelector('.cf2-home'),
                    primary: !!document.querySelector('.cf2-home__primary'),
                    eyebrow: !!(document.querySelector('.cf2-home__eyebrow') || {}).textContent,
                    confidence: (document.querySelector('.cf2-home__confidence') || {}).textContent || '',
                    stance: !!document.querySelector('.cf2-home__stance'),
                    coCount: document.querySelectorAll('.cf2-home__primary [data-cf2-co]').length,
                    noSceneGallery: !document.querySelector('.cf2-scene__co-rail'),
                    cache: [...document.querySelectorAll('link[rel=stylesheet]')].some(l => (l.href||'').includes('uiv2i')),
                    visibleDesignVocab,
                    support: !!document.querySelector('.cf2-home__support'),
                    secondaryDup: (() => {
                      const supportTitles = [...document.querySelectorAll('.cf2-home__support-title')]
                        .map(el => (el.textContent || '').trim());
                      const secondaryTitles = [...document.querySelectorAll('.cf2-home__item-title')]
                        .map(el => (el.textContent || '').trim());
                      return supportTitles.some(t => t && secondaryTitles.includes(t));
                    })(),
                  };
                }"""
            )

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop"] = home_probe(page)
        page.screenshot(path=str(OUT / "01_desktop_home.png"), full_page=False)
        prim = page.query_selector(".cf2-home__primary")
        if prim:
            prim.screenshot(path=str(OUT / "02_desktop_primary_closeup.png"))
        page.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "05_home_grayscale.png"), full_page=False)
        ctx.close()

        mctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
            is_mobile=True,
            has_touch=True,
        )
        mctx.add_cookies([cookie])
        mpage = mctx.new_page()
        mpage.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        mpage.wait_for_timeout(4500)
        probe["mobile"] = home_probe(mpage)
        mpage.screenshot(path=str(OUT / "03_mobile_home.png"), full_page=False)
        mp = mpage.query_selector(".cf2-home__primary")
        if mp:
            mp.screenshot(path=str(OUT / "04_mobile_primary.png"))
        mctx.close()
        browser.close()

    (OUT / "gate_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    d = probe.get("desktop") or {}
    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            d.get("home"),
            d.get("primary"),
            d.get("stance"),
            d.get("noSceneGallery"),
            d.get("cache"),
            (d.get("coCount") or 0) <= 2,
            not d.get("visibleDesignVocab"),
            not d.get("secondaryDup"),
            "أدلة" in (d.get("confidence") or "") or "إشارة" in (d.get("confidence") or "") or "اتخاذ" in (d.get("confidence") or ""),
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
