# -*- coding: utf-8 -*-
"""Living Store — Mobile App Bar Geometry Correction V2 screenshots."""
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
OUT = ROOT / "docs" / "product" / "merchant_ui_v2_mobile_app_bar_geometry_v2"
BASE = "https://smartreplyai.net"
VIEWPORT = {"width": 390, "height": 844}


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
  const bar = document.querySelector('.cf2-appbar');
  const account = document.querySelector('#cf2-mobile-account');
  const core = document.querySelector('.cf2-appbar__core');
  const brand = document.querySelector('.cf2-brand');
  const section = document.querySelector('#cf2-appbar-section');
  const menu = document.querySelector('.cf2-menu-btn');
  const marker = bar && bar.getAttribute('data-cf2-appbar');
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      left: Math.round(r.left), right: Math.round(r.right),
      top: Math.round(r.top), bottom: Math.round(r.bottom),
      w: Math.round(r.width), h: Math.round(r.height),
    };
  };
  const b = box(bar);
  const a = box(account);
  const c = box(core);
  const m = box(menu);
  const br = box(brand);
  const s = box(section);
  // Physical LTR: account should be left of core; menu right of core (when closed)
  const geometry = {
    accountLeftOfCore: !!(a && c && a.right <= c.left + 2),
    coreLeftOfMenu: !!(c && m && c.right <= m.left + 2),
    menuNearRightEdge: !!(m && b && (b.right - m.right) < 24),
    accountNearLeftEdge: !!(a && b && (a.left - b.left) < 24),
    coreNotViewportCentered: !!(c && b && Math.abs((c.left + c.right) / 2 - (b.left + b.right) / 2) > 28),
  };
  return {
    marker,
    sectionText: section ? section.textContent.trim() : null,
    drawerOpen: document.body.classList.contains('is-drawer-open'),
    boxes: { bar: b, account: a, core: c, brand: br, section: s, menu: m },
    geometry,
    noWrap: !!(b && b.h <= 60),
    noOverflow: !!(b && b.right <= window.innerWidth + 1 && b.left >= -1),
  };
}"""


def shot(page, name: str) -> Path:
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    return path


def bar_closeup(page, name: str) -> Path:
    path = OUT / name
    page.locator(".cf2-appbar").screenshot(path=str(path))
    return path


def compose_relationship(closed: Path, opened: Path, out: Path) -> None:
    if Image is None:
        return
    a = Image.open(closed).convert("RGB")
    b = Image.open(opened).convert("RGB")
    w = max(a.width, b.width)
    gap = 16
    label_h = 36
    canvas = Image.new("RGB", (w, a.height + b.height + gap + label_h * 2), (245, 247, 250))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    draw.text((12, 10), "Closed", fill=(8, 32, 72), font=font)
    canvas.paste(a, (0, label_h))
    y2 = label_h + a.height + gap
    draw.text((12, y2 - 26), "Drawer open", fill=(8, 32, 72), font=font)
    canvas.paste(b, (0, y2))
    canvas.save(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sha_prefix = (Path(OUT / "expected_sha.txt").read_text(encoding="utf-8").strip()
                  if (OUT / "expected_sha.txt").exists() else "")

    deploy = wait_for_deploy(sha_prefix)
    evidence: dict = {"deploy": deploy, "viewport": VIEWPORT, "probes": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,
            locale="ar-SA",
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
        )
        page = context.new_page()
        page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=90000)
        context.add_cookies([session_cookie(page)])

        # Home closed
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1800)
        page.wait_for_selector(".cf2-appbar[data-cf2-appbar='mobile-geometry-v2']", timeout=60000)
        evidence["probes"]["home_closed"] = page.evaluate(PROBE)
        shot(page, "01_mobile_home_closed.png")
        bar_closeup(page, "03_mobile_home_bar_closeup.png")

        # Home drawer open
        page.click(".cf2-menu-btn")
        page.wait_for_timeout(600)
        evidence["probes"]["home_drawer"] = page.evaluate(PROBE)
        shot(page, "05_mobile_home_drawer_open.png")
        page.click(".cf2-drawer__chrome-close")
        page.wait_for_timeout(400)

        # Workspace closed
        page.goto(f"{BASE}/dashboard#workspace", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1800)
        evidence["probes"]["workspace_closed"] = page.evaluate(PROBE)
        shot(page, "02_mobile_workspace_closed.png")
        bar_closeup(page, "04_mobile_workspace_bar_closeup.png")

        # Workspace drawer open
        page.click(".cf2-menu-btn")
        page.wait_for_timeout(600)
        evidence["probes"]["workspace_drawer"] = page.evaluate(PROBE)
        shot(page, "06_mobile_workspace_drawer_open.png")

        compose_relationship(
            OUT / "03_mobile_home_bar_closeup.png",
            OUT / "05_mobile_home_drawer_open.png",
            OUT / "07_closed_vs_open_relationship.png",
        )

        browser.close()

    (OUT / "production_probe.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(OUT), "deploy": deploy}, ensure_ascii=False))


if __name__ == "__main__":
    main()
