# -*- coding: utf-8 -*-
"""Product Identity Foundation V1 — production post-deploy verification."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_product_identity_foundation_prod_verify_out"
NEEDLES = (
    "product_identity_v1",
    "اسم المنتج غير متوفر",
    "merchant_product_identity_status",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()


def _fetch(url: str) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CartFlow-PI-F6/1.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.status, resp.read(), dict(resp.headers.items())


def _deploy_probe(expected_sha: str) -> dict:
    status, body, headers = _fetch(f"{BASE}/health")
    health = json.loads(body.decode("utf-8", "replace"))
    _, lazy, lazy_h = _fetch(f"{BASE}/static/merchant_dashboard_lazy.js?_={int(time.time())}")
    committed = subprocess.check_output(
        ["git", "show", f"{expected_sha}:static/merchant_dashboard_lazy.js"]
    )
    text = lazy.decode("utf-8", "replace")
    return {
        "health": health,
        "health_ok": bool(health.get("ok")),
        "lazy_sha256": hashlib.sha256(lazy).hexdigest()[:16],
        "committed_lazy_sha256": hashlib.sha256(committed).hexdigest()[:16],
        "lazy_matches_commit": lazy == committed,
        "lazy_last_modified": lazy_h.get("Last-Modified") or lazy_h.get("last-modified"),
        "needles": {n: n in text for n in NEEDLES},
        "has_product_x_literal": "Product X" in text,
    }


def _auth(page) -> dict:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator('input[name="email"], input[type="email"]').first.fill(email)
        page.locator('input[name="password"], input[type="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(5000)
        return {"mode": "env_login", "email": email}
    uid = uuid.uuid4().hex[:10]
    email = f"pi.f6.{uid}@smartreplyai.net"
    password = f"PiF6!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"PI F6 {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(6000)
    return {"mode": "signup", "email": email}


def _seed_cart(page) -> dict:
    """Create a cart via test widget so Carts has a row with product identity path."""
    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.evaluate("try{sessionStorage.clear();localStorage.clear();}catch(e){}")
    # Prefer named product button if present
    add = page.locator(".add-btn").first
    add.click(timeout=30000)
    page.wait_for_timeout(2000)
    page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
    page.evaluate("window.__cfV2ShowNow()")
    page.wait_for_timeout(800)
    if page.get_by_role("button", name="نعم").count():
        page.get_by_role("button", name="نعم").click(timeout=20000)
        page.wait_for_timeout(500)
    if page.get_by_role("button", name="السعر").count():
        page.get_by_role("button", name="السعر").click(timeout=20000)
        page.wait_for_timeout(500)
    if page.get_by_role("button", name="شكراً").count():
        page.get_by_role("button", name="شكراً").click(timeout=20000)
        page.wait_for_timeout(400)
    tel = page.locator('input[type="tel"]').last
    if tel.count():
        tel.fill("05988771234")
        if page.get_by_role("button", name="حفظ الرقم").count():
            page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
            page.wait_for_timeout(2000)
    product_label = page.evaluate(
        """() => {
          const el = document.querySelector('.add-btn, .product-name, [data-product-name]');
          return el ? (el.textContent || '').trim().slice(0, 80) : '';
        }"""
    )
    return {"seeded": True, "product_label_hint": product_label}


def _page_text_checks(text: str) -> dict:
    return {
        "has_product_x": bool(re.search(r"\bProduct X\b", text, re.I)),
        "has_product_x_ar": "منتج X" in text or "منتج x" in text,
        "has_unresolved_ar": "اسم المنتج غير متوفر" in text,
        "has_demo_rich": "demo_rich_fixture" in text,
        "has_fixture_marker": "demo_rich_fixture_v1" in text,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    merge_sha = _git("rev-parse", "origin/main")
    short = merge_sha[:7]
    feature_sha = "8b884a50d963d6ac18d0c6e388126c7ce9fb83a8"

    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "production_url": f"{BASE}/dashboard#home",
        "merge_commit": merge_sha,
        "feature_commit": feature_sha,
        "checks": {},
    }

    deploy = _deploy_probe(feature_sha if True else merge_sha)
    # lazy.js is from feature commit content; probe against feature SHA content via merge tree
    try:
        deploy = _deploy_probe(merge_sha)
    except Exception:
        deploy = _deploy_probe(feature_sha)
    report["deploy"] = deploy
    report["checks"]["deploy_health_ok"] = deploy["health_ok"]
    report["checks"]["lazy_matches_main"] = deploy["lazy_matches_commit"]
    report["checks"]["pi_needles_live"] = all(deploy["needles"].values())

    console_errors: list[str] = []
    api_samples: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        page = context.new_page()

        def on_console(msg):
            if msg.type in ("error", "warning"):
                t = msg.text or ""
                if any(
                    k in t.lower()
                    for k in (
                        "product_identity",
                        "cart_line_snapshot",
                        "business_findings",
                        "demo_rich",
                        "product_name",
                    )
                ):
                    console_errors.append(f"{msg.type}: {t[:300]}")

        page.on("console", on_console)

        def on_response(resp):
            u = resp.url
            if any(
                x in u
                for x in (
                    "/api/dashboard/summary",
                    "normal-carts",
                    "home",
                    "commercial",
                    "findings",
                )
            ):
                try:
                    if "json" in (resp.headers.get("content-type") or ""):
                        body = resp.json()
                        key = u.split("?")[0].split(BASE)[-1][-80:]
                        api_samples[key] = body
                except Exception:
                    pass

        page.on("response", on_response)

        auth = _auth(page)
        report["auth"] = auth
        page.screenshot(path=str(OUT / "00_after_auth.png"), full_page=False)

        # Home
        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        page.screenshot(path=str(OUT / "01_home.png"), full_page=True)
        home_text = page.inner_text("body")
        report["home_text_checks"] = _page_text_checks(home_text)
        report["home_excerpt"] = home_text[:1200]

        # Seed cart then Carts
        try:
            report["seed"] = _seed_cart(page)
        except Exception as exc:  # noqa: BLE001
            report["seed"] = {"seeded": False, "error": f"{type(exc).__name__}: {exc}"}

        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        page.screenshot(path=str(OUT / "02_carts.png"), full_page=True)
        carts_text = page.inner_text("body")
        report["carts_text_checks"] = _page_text_checks(carts_text)
        report["carts_excerpt"] = carts_text[:1200]

        # DOM product identity markers
        report["carts_dom"] = page.evaluate(
            """() => {
              const nodes = Array.from(document.querySelectorAll(
                '[data-product-identity-status], .v2-queue-product, .ma-cart-product-name, p'
              )).slice(0, 40).map(el => (el.textContent || '').trim()).filter(Boolean);
              const unresolved = nodes.filter(t => t.includes('اسم المنتج غير متوفر'));
              const productX = nodes.filter(t => /Product X|منتج X/i.test(t));
              return {
                sample_nodes: nodes.slice(0, 20),
                unresolved_count: unresolved.length,
                product_x_count: productX.length,
                has_product_identity_attr: !!document.querySelector('[data-product-identity-status]')
              };
            }"""
        )

        # API composition check via same-origin fetch
        report["api_home"] = page.evaluate(
            """async () => {
              const urls = [
                '/api/dashboard/summary?_pi=' + Date.now(),
                '/api/dashboard/summary?activation_inspect=0&_pi=' + Date.now(),
              ];
              const out = {};
              for (const u of urls) {
                try {
                  const r = await fetch(u, { credentials: 'same-origin', cache: 'no-store' });
                  const j = await r.json();
                  const blob = JSON.stringify(j);
                  out[u.split('?')[0]] = {
                    status: r.status,
                    ok: !!j.ok || j.status === 'ok' || typeof j === 'object',
                    has_product_x: /Product X|منتج X/.test(blob),
                    has_demo_rich: blob.includes('demo_rich_fixture'),
                    has_fixture_loaded_from: blob.includes('demo_rich_fixture_v1'),
                    keys: Object.keys(j || {}).slice(0, 30),
                  };
                } catch (e) {
                  out[u.split('?')[0]] = { error: String(e) };
                }
              }
              // normal carts
              try {
                const r = await fetch('/api/dashboard/normal-carts?limit=20&_pi=' + Date.now(), {
                  credentials: 'same-origin', cache: 'no-store'
                });
                const j = await r.json();
                const rows = j.rows || j.carts || j.items || [];
                const blob = JSON.stringify(j);
                out['/api/dashboard/normal-carts'] = {
                  status: r.status,
                  row_count: Array.isArray(rows) ? rows.length : null,
                  has_product_x: /Product X|منتج X/.test(blob),
                  has_demo_rich: blob.includes('demo_rich_fixture'),
                  sample_identity: (Array.isArray(rows) ? rows : []).slice(0, 3).map(row => ({
                    product_identity_v1: row.product_identity_v1 || null,
                    merchant_product_display_name: row.merchant_product_display_name || row.product_display_name || null,
                    merchant_product_identity_status: row.merchant_product_identity_status || null,
                  })),
                };
              } catch (e) {
                out['/api/dashboard/normal-carts'] = { error: String(e) };
              }
              return out;
            }"""
        )

        browser.close()

    report["console_pi_related_errors"] = console_errors
    report["api_samples_keys"] = list(api_samples.keys())[:20]

    # Verdicts
    home_ok = (
        not report["home_text_checks"]["has_product_x"]
        and not report["home_text_checks"]["has_product_x_ar"]
        and not report["home_text_checks"]["has_demo_rich"]
    )
    api_home = report.get("api_home") or {}
    api_ok = True
    for k, v in api_home.items():
        if isinstance(v, dict) and (v.get("has_product_x") or v.get("has_demo_rich") or v.get("has_fixture_loaded_from")):
            api_ok = False
    carts_ok = (
        not report["carts_text_checks"]["has_product_x"]
        and not report["carts_text_checks"]["has_product_x_ar"]
        and (report.get("carts_dom") or {}).get("product_x_count", 0) == 0
    )
    report["verdicts"] = {
        "deploy_live": bool(report["checks"]["lazy_matches_main"] and report["checks"]["pi_needles_live"]),
        "home_no_fixture_product_x": home_ok and api_ok,
        "carts_no_placeholders": carts_ok,
        "no_pi_console_errors": len(console_errors) == 0,
        "overall_ready_for_product_review": False,
    }
    report["verdicts"]["overall_ready_for_product_review"] = all(
        [
            report["verdicts"]["deploy_live"],
            report["verdicts"]["home_no_fixture_product_x"],
            report["verdicts"]["carts_no_placeholders"],
            report["verdicts"]["no_pi_console_errors"],
            report["checks"]["deploy_health_ok"],
        ]
    )

    out_json = OUT / "PRODUCT_IDENTITY_FOUNDATION_PROD_EVIDENCE_V1.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # also root copy for docs convenience
    root_copy = Path(__file__).resolve().parents[1] / "PRODUCT_IDENTITY_FOUNDATION_PROD_EVIDENCE_V1.json"
    root_copy.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["verdicts"], ensure_ascii=False, indent=2))
    print("evidence:", out_json)
    print("screenshots:", OUT / "01_home.png", OUT / "02_carts.png")
    return 0 if report["verdicts"]["overall_ready_for_product_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
