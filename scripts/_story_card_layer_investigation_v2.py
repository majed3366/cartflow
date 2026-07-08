# -*- coding: utf-8 -*-
"""Expanded story layer investigation V2 — DOM + computed-style evidence."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "_story_card_layer_investigation_v2_out"
FIXTURE = Path(__file__).resolve().parent / "_story_card_ghost_fix_fixture.html"
BASE_LOCAL = os.environ.get("CARTFLOW_INVESTIGATE_BASE", "http://127.0.0.1:8767")
USE_PROD = os.environ.get("CARTFLOW_INVESTIGATE_PROD", "").strip() in ("1", "true", "yes")


def _node_probe(page, selector: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return { found: false, selector: sel };
          const cs = getComputedStyle(el);
          return {
            found: true,
            selector: sel,
            tag: el.tagName,
            className: el.className,
            text: (el.textContent || '').trim().slice(0, 200),
            childCount: el.children.length,
            display: cs.display,
            visibility: cs.visibility,
            opacity: cs.opacity,
            position: cs.position,
            zIndex: cs.zIndex,
            rect: el.getBoundingClientRect().toJSON(),
          };
        }""",
        selector,
    )


def _tree_probe(page, root_sel: str) -> dict:
    return page.evaluate(
        """(rootSel) => {
          const root = document.querySelector(rootSel);
          if (!root) return { found: false };
          function walk(node, depth) {
            if (!node || depth > 6) return null;
            const cs = getComputedStyle(node);
            const item = {
              tag: node.tagName,
              className: node.className || '',
              id: node.id || '',
              text: (node.childNodes.length === 1 && node.childNodes[0].nodeType === 3
                ? node.textContent : '').trim().slice(0, 120),
              display: cs.display,
              visibility: cs.visibility,
              opacity: cs.opacity,
              position: cs.position,
              zIndex: cs.zIndex,
            };
            const kids = [];
            node.childNodes.forEach((ch) => {
              if (ch.nodeType === 1) {
                const w = walk(ch, depth + 1);
                if (w) kids.push(w);
              }
            });
            if (kids.length) item.children = kids;
            return item;
          }
          return { found: true, tree: walk(root, 0) };
        }""",
        root_sel,
    )


def _auth_prod(page, base: str) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if not email or not password:
        raise RuntimeError("CARTFLOW_PROD_EMAIL and CARTFLOW_PROD_PASSWORD required for prod mode")
    page.goto(f"{base}/login", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.locator('input[name="email"]').fill(email, timeout=60000)
    page.locator('input[name="password"]').first.fill(password)
    page.get_by_role("button", name="دخول").click()
    page.wait_for_timeout(5000)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "production" if USE_PROD else "local_fixture",
        "root_cause": (
            "Collapsed summary preview (.ma-mi-group-card__preview) and expanded body "
            "sections render duplicate copy; CSS display:none is insufficient — preview "
            "must be removed from DOM on expand via syncMiGroupSummaryPreview()."
        ),
        "before": {},
        "after": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})

        if USE_PROD:
            base = "https://smartreplyai.net"
            _auth_prod(page, base)
            page.goto(f"{base}/dashboard#carts", timeout=120000, wait_until="networkidle")
            page.wait_for_timeout(6000)
            story_sel = "details.ma-mi-story"
            if page.locator(story_sel).count() == 0:
                story_sel = "details.ma-mi-group"
            root_sel = f"{story_sel}:not([open])"
            page.locator(f"{story_sel} summary").first.click()
            page.wait_for_timeout(1200)
            root_sel = f"{story_sel}[open]"
        else:
            url = f"{BASE_LOCAL}/scripts/_story_card_ghost_fix_fixture.html"
            page.goto(url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(500)
            page.evaluate(
                """() => {
                  document.querySelectorAll('details.ma-mi-group[open]').forEach((el) => {
                    el.open = false;
                  });
                }"""
            )
            root_sel = 'details.ma-mi-story[data-ma-story="waiting_reply"]'
            report["before"]["fixture_url"] = url

        report["before"]["tree"] = _tree_probe(page, root_sel)
        report["before"]["summary_preview"] = _node_probe(
            page, f"{root_sel} summary .ma-mi-group-card__preview"
        )
        report["before"]["summary_decision_rows"] = page.evaluate(
            """(sel) => Array.from(document.querySelectorAll(sel)).map((el) => ({
              text: (el.textContent || '').trim().slice(0, 120),
              display: getComputedStyle(el).display,
              parent: el.parentElement ? el.parentElement.className : ''
            }))""",
            f"{root_sel} summary .ma-mi-decision-row",
        )
        report["before"]["body_sections"] = page.evaluate(
            """(sel) => Array.from(document.querySelectorAll(sel)).map((el) => ({
              label: (el.querySelector('.ma-mi-group-section__label') || {}).textContent || '',
              text: (el.querySelector('.ma-mi-group-section__text') || {}).textContent || '',
            }))""",
            f"{root_sel} .ma-mi-group-body .ma-mi-group-section",
        )
        page.screenshot(path=str(OUT / "before_expand.png"), full_page=True)

        if not USE_PROD:
            page.locator(f'{root_sel} summary').click()
            page.wait_for_timeout(400)
        else:
            page.wait_for_timeout(400)

        open_sel = root_sel if USE_PROD or "[open]" in root_sel else f'{root_sel}'
        if not USE_PROD:
            open_sel = 'details.ma-mi-story[data-ma-story="waiting_reply"][open]'

        report["after"]["tree"] = _tree_probe(page, open_sel)
        report["after"]["summary_preview"] = _node_probe(
            page, f"{open_sel} summary .ma-mi-group-card__preview"
        )
        report["after"]["summary_decision_rows"] = page.evaluate(
            """(sel) => Array.from(document.querySelectorAll(sel)).map((el) => ({
              text: (el.textContent || '').trim().slice(0, 120),
              display: getComputedStyle(el).display,
              parent: el.parentElement ? el.parentElement.className : ''
            }))""",
            f"{open_sel} summary .ma-mi-decision-row",
        )
        report["after"]["body_sections"] = page.evaluate(
            """(sel) => Array.from(document.querySelectorAll(sel)).map((el) => ({
              label: (el.querySelector('.ma-mi-group-section__label') || {}).textContent || '',
              text: (el.querySelector('.ma-mi-group-section__text') || {}).textContent || '',
            }))""",
            f"{open_sel} .ma-mi-group-body .ma-mi-group-section",
        )
        report["after"]["acceptance"] = {
            "summary_preview_removed": report["after"]["summary_preview"].get("found") is False,
            "summary_decision_row_count": len(report["after"]["summary_decision_rows"]),
            "single_text_layer": len(report["after"]["summary_decision_rows"]) == 0,
        }
        page.screenshot(path=str(OUT / "after_expand.png"), full_page=True)

        if not USE_PROD:
            page.locator(f"{open_sel} summary").click()
            page.wait_for_timeout(400)
            report["collapsed_again"] = {
                "summary_preview_restored": _node_probe(
                    page, f'{root_sel} summary .ma-mi-group-card__preview'
                ).get("found"),
                "decision_row_count": page.evaluate(
                    """(sel) => document.querySelectorAll(sel).length""",
                    f'{root_sel} summary .ma-mi-decision-row',
                ),
            }

        browser.close()

    (OUT / "investigation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["after"]["acceptance"], ensure_ascii=False))
    if not report["after"]["acceptance"]["single_text_layer"]:
        raise SystemExit("acceptance failed: summary decision rows still mounted when expanded")


if __name__ == "__main__":
    main()
