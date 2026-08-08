# -*- coding: utf-8 -*-
"""Living Store captures — Home Executive Composition V1.3."""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_home_executive_composition_v1_3"
BEFORE = (
    ROOT
    / "docs"
    / "product"
    / "merchant_ui_v2_home_desktop_density_v1_2"
    / "01_desktop_home_1440.png"
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
        from PIL import Image, ImageDraw
    except ImportError:
        if after.is_file():
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
    draw.text((12, 10), "V1.2 Before", fill=(8, 32, 72))
    draw.text((a.width + gap + 12, 10), "V1.3 After", fill=(8, 32, 72))
    canvas.save(dest)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "before").mkdir(exist_ok=True)
    if BEFORE.is_file():
        shutil.copy2(BEFORE, OUT / "before" / "01_desktop_home_v1_2.png")

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
                  const scene = document.querySelector('.cf2-home__scene');
                  const monitor = document.querySelector('.cf2-home__monitor');
                  const rail = document.querySelector('.cf2-home__rail');
                  const stance = document.querySelector('.cf2-home__stance');
                  const lead = document.querySelector('.cf2-home__lead');
                  const br = board ? board.getBoundingClientRect() : null;
                  const mr = monitor ? monitor.getBoundingClientRect() : null;
                  const stage = document.querySelector('.cf2-stage__inner');
                  const sr = stage ? stage.getBoundingClientRect() : null;
                  const boardShare = br && sr && sr.width ? br.width / sr.width : 1;
                  const monitorIsColumn = !!(rail);
                  const monitorBelow = !!(br && mr && mr.top >= (scene?.getBoundingClientRect().bottom || 0) - 4);
                  return {
                    ui: document.body.getAttribute('data-cf-ui'),
                    version: document.querySelector('.cf2-home')?.getAttribute('data-cf2') || '',
                    scene: !!scene,
                    monitor: !!monitor,
                    lead: !!lead,
                    terminus: !!(stance && stance.classList.contains('cf2-terminus')),
                    noRailColumn: !monitorIsColumn,
                    monitorBelow,
                    boardShare: Math.round(boardShare * 1000) / 1000,
                    boardWidth: br ? Math.round(br.width) : 0,
                    cache: [...document.querySelectorAll('link[rel=stylesheet]')]
                      .some(l => (l.href || '').includes('uiv2n')),
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
        scene = page.query_selector(".cf2-home__scene")
        if scene:
            scene.screenshot(path=str(OUT / "03_primary_reading_path.png"))
        # Relationship: board includes monitor under scene
        if board:
            board.screenshot(path=str(OUT / "04_secondary_monitoring_relationship.png"))

        page.evaluate(
            """() => {
              document.body.setAttribute('data-cf2-proof', 'grayscale');
              document.querySelectorAll('.cf2-brand, .cf2-brand__name, [data-cf2-brand]').forEach(el => {
                el.style.visibility = 'hidden';
              });
            }"""
        )
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "06_desktop_grayscale_logo_hidden.png"), full_page=False)
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
        OUT / "before" / "01_desktop_home_v1_2.png",
        OUT / "01_desktop_home_1440.png",
        OUT / "07_v12_vs_v13.png",
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
            d.get("version") == "home-exec-v13",
            d.get("scene"),
            d.get("monitor"),
            d.get("terminus"),
            d.get("lead"),
            d.get("noRailColumn"),
            d.get("monitorBelow"),
            d.get("cache"),
            float(d.get("boardShare") or 1) < 0.72,
            m.get("noOverflow"),
            m.get("version") == "home-exec-v13",
        ]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
