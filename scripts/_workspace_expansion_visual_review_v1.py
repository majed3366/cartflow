# -*- coding: utf-8 -*-
"""Desktop Workspace Expansion Fix V1 — local visual + width audit."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CARTFLOW_REVIEW_BASE", "http://127.0.0.1:8011")
OUT = Path(__file__).resolve().parent / "_workspace_expansion_visual_review_v1_out"

DESKTOP_PAGES = [
    ("carts", "/dashboard#carts"),
    ("messages", "/dashboard#messages"),
    ("home", "/dashboard#home"),
    ("whatsapp", "/dashboard#whatsapp"),
    ("plans", "/dashboard#plans"),
]

MOBILE_PAGES = [
    ("carts", "/dashboard#carts"),
]

WIDTH_SCRIPT = """
() => {
  const pick = (sel) => document.querySelector(sel);
  const rect = (el) => el ? el.getBoundingClientRect() : null;
  const cs = (el) => el ? getComputedStyle(el) : null;
  const frame = pick('.ma-dashboard-frame');
  const content = pick('.ma-content-root');
  const sidebar = pick('.ma-context-sidebar');
  const cartsShell = pick('#page-carts .ma-pe-v2-carts-shell');
  const cartsRoot = pick('#ma-carts-groups-v2');
  const frameR = rect(frame);
  const sidebarR = rect(sidebar);
  const contentR = rect(content);
  const shellR = rect(cartsShell);
  const gapBesideSidebar = frameR && sidebarR
    ? Math.round(sidebarR.left - frameR.right)
    : null;
  const contentFill = frameR && contentR && frameR.width
    ? Math.round((contentR.width / frameR.width) * 1000) / 1000
    : null;
  const shellFill = frameR && shellR && frameR.width
    ? Math.round((shellR.width / frameR.width) * 1000) / 1000
    : null;
  return {
    viewportWidth: window.innerWidth,
    bodyPage: document.body.getAttribute('data-ma-page'),
    frame: frameR ? {
      width: Math.round(frameR.width),
      right: Math.round(frameR.right),
      maxWidth: cs(frame).maxWidth,
      marginRight: cs(frame).marginRight,
    } : null,
    content: contentR ? {
      width: Math.round(contentR.width),
      maxWidth: cs(content).maxWidth,
    } : null,
    sidebar: sidebarR ? { width: Math.round(sidebarR.width), left: Math.round(sidebarR.left) } : null,
    cartsShell: shellR ? {
      width: Math.round(shellR.width),
      maxWidth: cartsShell ? cs(cartsShell).maxWidth : null,
    } : null,
    cartsRootMaxWidth: cartsRoot ? cs(cartsRoot).maxWidth : null,
    gapBesideSidebar,
    contentFillRatio: contentFill,
    cartsShellFillRatio: shellFill,
  };
}
"""


def _auth(page) -> None:
    email = (os.environ.get("CARTFLOW_REVIEW_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_REVIEW_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator('input[name="email"]').fill(email, timeout=60000)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        return
    uid = uuid.uuid4().hex[:8]
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"WS Expand {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(f"ws.expand.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"WsExpand!{uid}")
    page.locator('input[name="confirm_password"]').fill(f"WsExpand!{uid}")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)


def _passes_width_audit(page_key: str, metrics: dict, viewport: str) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if viewport != "desktop":
        return True, issues

    gap = metrics.get("gapBesideSidebar")
    if gap is not None and gap > 8:
        issues.append(f"frame/sidebar gap {gap}px > 8px")

    fill = metrics.get("contentFillRatio")
    if fill is not None and fill < 0.94:
        issues.append(f"content fill ratio {fill} < 0.94")

    if page_key == "carts":
        shell_fill = metrics.get("cartsShellFillRatio")
        if shell_fill is not None and shell_fill < 0.88:
            issues.append(f"carts shell fill ratio {shell_fill} < 0.88")
        shell = metrics.get("cartsShell") or {}
        max_w = shell.get("maxWidth")
        if max_w and max_w not in ("none", "0px"):
            issues.append(f"carts shell max-width still {max_w}")

    return len(issues) == 0, issues


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"base": BASE, "pages": {}, "screenshots": {}, "passed": True}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for viewport_name, size in (
            ("desktop", {"width": 1440, "height": 900}),
            ("mobile", {"width": 390, "height": 844}),
        ):
            page = browser.new_page(locale="ar-SA")
            page.set_viewport_size(size)
            _auth(page)

            pages = DESKTOP_PAGES if viewport_name == "desktop" else MOBILE_PAGES
            for page_key, path in pages:
                page.goto(f"{BASE}{path}", timeout=120000, wait_until="networkidle")
                page.wait_for_timeout(3500)
                prefix = f"{viewport_name}_{page_key}"
                shot = OUT / f"{prefix}.png"
                page.screenshot(path=str(shot), full_page=True)
                report["screenshots"][prefix] = shot.name

                metrics = page.evaluate(WIDTH_SCRIPT)
                ok, issues = _passes_width_audit(page_key, metrics, viewport_name)
                report["pages"][prefix] = {
                    "metrics": metrics,
                    "passed": ok,
                    "issues": issues,
                }
                if not ok:
                    report["passed"] = False

            page.close()
        browser.close()

    report_path = OUT / "workspace_expansion_review.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(report_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
