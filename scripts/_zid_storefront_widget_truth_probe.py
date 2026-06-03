# -*- coding: utf-8 -*-
"""One-off probe: Zid storefront public-config URL + widget DOM truth."""
from __future__ import annotations

import asyncio
import json
import sys
from urllib.parse import parse_qs, urlparse

EXPECTED_STORE_SLUG = "4hz49e"


def _store_slug_from_url(url: str) -> str | None:
    try:
        qs = parse_qs(urlparse(url).query)
        for key in ("store_slug", "store"):
            vals = qs.get(key) or []
            if vals and str(vals[0]).strip():
                return str(vals[0]).strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _assert_widget_api_store_slug(captured: dict) -> list[str]:
    errors: list[str] = []
    widget_urls = [
        u
        for u in captured.get("requests") or []
        if "public-config" in u or "/api/cartflow/ready" in u
    ]
    if not widget_urls:
        errors.append("no widget API requests captured (ready/public-config)")
        return errors

    slugs = [_store_slug_from_url(u) for u in widget_urls]
    slugs = [s for s in slugs if s]
    if not slugs:
        errors.append("widget API requests missing store_slug query param")
        return errors

    if any(s == "demo" for s in slugs):
        errors.append(f"store_slug=demo in widget API calls: {widget_urls}")

    if not any(s == EXPECTED_STORE_SLUG for s in slugs):
        errors.append(
            f"expected store_slug={EXPECTED_STORE_SLUG}, got slugs={sorted(set(slugs))}"
        )

    pub = captured.get("public_config") or {}
    pub_url = str(pub.get("url") or "")
    pub_slug = _store_slug_from_url(pub_url) if pub_url else None
    if pub_slug != EXPECTED_STORE_SLUG:
        errors.append(
            f"public-config url store_slug={pub_slug!r}, expected {EXPECTED_STORE_SLUG!r}"
        )

    captured["assertions"] = {
        "expected_store_slug": EXPECTED_STORE_SLUG,
        "widget_api_slugs": sorted(set(slugs)),
        "passed": not errors,
        "errors": errors,
    }
    return errors


async def main() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("NO_PLAYWRIGHT", file=sys.stderr)
        return 1

    captured: dict = {"requests": [], "public_config": None, "dom": None}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        def on_request(req) -> None:
            u = req.url
            if "public-config" in u or "/api/cartflow/ready" in u:
                captured["requests"].append(u)

        async def on_response(resp) -> None:
            if "public-config" in resp.url:
                try:
                    captured["public_config"] = {
                        "url": resp.url,
                        "body": await resp.json(),
                    }
                except Exception as exc:  # noqa: BLE001
                    captured["public_config"] = {"url": resp.url, "error": str(exc)}

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto(
            "https://4hz49e.zid.store/",
            wait_until="networkidle",
            timeout=90000,
        )
        await page.wait_for_timeout(15000)

        captured["dom"] = await page.evaluate(
            """() => {
              var w = document.querySelector('[data-cf-widget-root]')
                || document.querySelector('#cartflow-widget-root')
                || document.querySelector('[class*="cf-widget"]');
              if (!w) {
                return { found: false, roots: document.querySelectorAll('[id*="cartflow"],[class*="cartflow"]').length };
              }
              var t = w.querySelector('[data-cf-shell-title]');
              var bar = w.querySelector('[data-cf-chrome="1"]');
              return {
                found: true,
                title: t ? (t.textContent || '').trim() : null,
                barBg: bar && bar.style ? (bar.style.background || bar.style.backgroundColor) : null,
              };
            }"""
        )

        await browser.close()

    errors = _assert_widget_api_store_slug(captured)

    out_path = __file__.replace("_zid_storefront_widget_truth_probe.py", "_zid_probe_out.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(captured, fh, ensure_ascii=False, indent=2)
    print(out_path)
    if errors:
        for err in errors:
            print("PROBE_FAIL:", err, file=sys.stderr)
        return 1
    print("PROBE_OK store_slug=" + EXPECTED_STORE_SLUG)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
