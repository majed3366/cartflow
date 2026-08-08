# -*- coding: utf-8 -*-
"""Living Store captures — Home Desktop Density V1.2."""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_home_desktop_density_v1_2"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_home_final_composition_v1_1"
    / "01_desktop_home.png"
)
BASE = "https://smartreplyai.net"
EXPECTED_SHA_PREFIX = ""


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
        except Exception as exc:  # noqa: BLE001
            last = {"sha": last.get("sha", ""), "status": "error", "error": str(exc)}
        time.sleep(12)
    return {"ok": False, **last}


def make_before_after(before: Path, after: Path, dest: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        shutil.copy2(after, dest)
        return
    if not before.is_file() or not after.is_file():
        return
    a = Image.open(before).convert("RGB")
    b = Image.open(after).convert("RGB")
    h = max(a.height, b.height)
    gap = 24
    label_h = 36
    canvas = Image.new("RGB", (a.width + b.width + gap, h + label_h), (243, 246, 249))
    canvas.paste(a, (0, label_h))
    canvas.paste(b, (a.width + gap, label_h))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), "V1.1 Before", fill=(8, 32, 72))
    draw.text((a.width + gap + 12, 10), "V1.2 After", fill=(8, 32, 72))
    canvas.save(dest)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "before").mkdir(exist_ok=True)
    if BEFORE.is_file():
        shutil.copy2(BEFORE, OUT / "before" / "01_desktop_home_v1_1.png")

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
                  const board = document.querySelector('.cf2-home__board');
                  const primary = document.querySelector('.cf2-home__primary');
                  const rail = document.querySelector('.cf2-home__rail');
                  const br = board ? board.getBoundingClientRect() : null;
                  const pr = primary ? primary.getBoundingClientRect() : null;
                  const rr = rail ? rail.getBoundingClientRect() : null;
                  const primaryShare = br && pr && br.width ? pr.width / br.width : 0;
                  const stance = document.querySelector('.cf2-home__stance');
                  const stanceTop = stance ? stance.getBoundingClientRect().top : 0;
                  const boardBottom = br ? br.bottom : 0;
                  const deadBelowStance = boardBottom && stanceTop
                    ? Math.max(0, boardBottom - stance.getBoundingClientRect().bottom)
                    : 999;
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    version: document.querySelector('.cf2-home')?.getAttribute('data-cf2') || '',
                    board: !!board,
                    rail: !!rail,
                    primaryShare: Math.round(primaryShare * 1000) / 1000,
                    boardHeight: br ? Math.round(br.height) : 0,
                    deadBelowStance: Math.round(deadBelowStance),
                    railTitles: [...document.querySelectorAll('.cf2-home__rail-title')]
                      .map(el => (el.textContent || '').trim()),
                    cache: [...document.querySelectorAll('link[rel=stylesheet]')]
                      .some(l => (l.href || '').includes('uiv2m')),
                    noOverflow: document.documentElement.scrollWidth <= window.innerWidth + 1,
                  };
                }"""
            )

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard?cf_ui=v2#home", timeout=120000)
        page.wait_for_timeout(5000)
        probe["desktop"] = home_probe(page)
        page.screenshot(path=str(OUT / "01_desktop_home_1440.png"), full_page=False)
        board = page.query_selector(".cf2-home__board")
        if board:
            board.screenshot(path=str(OUT / "02_desktop_board_closeup.png"))
        prim = page.query_selector(".cf2-home__primary")
        if prim:
            prim.screenshot(path=str(OUT / "03_desktop_primary_zone.png"))
        rail = page.query_selector(".cf2-home__rail")
        if rail:
            rail.screenshot(path=str(OUT / "04_desktop_secondary_zone.png"))
        page.evaluate("() => document.body.setAttribute('data-cf2-proof','grayscale')")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "06_desktop_grayscale.png"), full_page=False)
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
        mpage.screenshot(path=str(OUT / "05_mobile_home.png"), full_page=False)
        mctx.close()
        browser.close()

    make_before_after(
        OUT / "before" / "01_desktop_home_v1_1.png",
        OUT / "01_desktop_home_1440.png",
        OUT / "07_before_after.png",
    )

    (OUT / "gate_probe.json").write_text(
        json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    d = probe.get("desktop") or {}
    m = probe.get("mobile") or {}
    ok = all(
        [
            bool(probe.get("deploy", {}).get("ok")),
            d.get("version") == "home-density-v12",
            d.get("board"),
            d.get("rail"),
            d.get("cache"),
            0.58 <= float(d.get("primaryShare") or 0) <= 0.78,
            int(d.get("deadBelowStance") or 999) < 80,
            int(d.get("boardHeight") or 9999) < 620,
            m.get("noOverflow"),
            m.get("version") == "home-density-v12",
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
