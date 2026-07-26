# -*- coding: utf-8 -*-
"""
Re-capture CEO merchant screenshots after certified Living Store.
Validation-only — no product logic changes.
Waits for merchant content (not skeleton) before each shot.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "executive_control_v1"

SURFACES = (
    ("home", "#home", "[data-hes='1'] .hes-section, [data-executive-control='1'] .hes-section"),
    ("workspace", "#workspace", "#page-workspace .cw-card, [data-cw-root] .cw-card"),
    ("products", "#products", "[data-cs-surface='products'], #cs-products-root .cs-card, #cs-products-root h2"),
    ("carts", "#carts", "#page-carts, #meif-carts-focus-root, .cs-pub-truth"),
    ("communication", "#communication", "#page-communication, #meif-communication-root, .cs-pub-truth"),
)


def _wait_ready(page, selector: str, *, timeout_ms: int = 45000) -> None:
    page.wait_for_timeout(1500)
    try:
        page.wait_for_selector(selector, timeout=timeout_ms, state="visible")
    except Exception:
        pass
    # Extra settle for summary paint after skeleton.
    page.wait_for_timeout(4000)
    # Home: specifically avoid skeleton-only capture.
    for _ in range(20):
        text = page.evaluate(
            """() => {
              const root = document.getElementById('ma-home-experience-root')
                || document.body;
              return (root && root.innerText) || '';
            }"""
        ) or ""
        if "نجهز ملخص" in text or "تجهيز ملخص" in text:
            page.wait_for_timeout(2000)
            continue
        if "حالة المتجر" in text or "أهم قرار" in text or "القرار الأهم" in text:
            break
        if "المنتجات التي تستحق" in text or "حالة السلال" in text or "حالة التواصل" in text:
            break
        page.wait_for_timeout(1500)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    meta: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "recapture_after_skeleton_miss",
        "precondition": {},
        "screenshots": {},
        "parity": {},
        "visible_home_sample": {},
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page()
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        body = session.get("body") or {}
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            print(json.dumps({"ok": False, "error": "no_session"}))
            return 2
        cookie = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }

        cert_ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ar-SA")
        cert_ctx.add_cookies([cookie])
        cert = cert_ctx.new_page()
        cert.goto(f"{BASE}/login", timeout=120000)
        cert_json = cert.evaluate(
            """async () => {
              const r = await fetch('/dev/reality-validation-context?store=demo', {
                credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        cj = cert_json.get("body") or {}
        status = str(cj.get("status") or "").upper()
        safe = cj.get("CEO_REVIEW_SAFE")
        store_slug = str(cj.get("store_slug") or "").strip()
        sim = str(cj.get("simulation_run_id") or "").strip()
        meta["precondition"] = {
            "status": status,
            "CEO_REVIEW_SAFE": safe,
            "store_slug": store_slug,
            "simulation_run_id": sim,
            "http": cert_json.get("http"),
        }
        cert.goto(
            f"{BASE}/dev/reality-validation-context?store=demo&format=html",
            timeout=120000,
        )
        cert.wait_for_timeout(2000)
        cert.screenshot(path=str(OUT / "prod_cert_identity.png"), full_page=True)
        cert_ctx.close()

        if status != "CONSISTENT" or safe is not True or store_slug != "demo":
            print(json.dumps({"ok": False, "verdict": "FAIL_PRECONDITION", **meta}, ensure_ascii=False))
            return 3

        fingerprints = {}
        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            for name, hash_path, ready_sel in SURFACES:
                page.goto(f"{BASE}/dashboard{hash_path}", timeout=120000)
                _wait_ready(page, ready_sel)
                shot = OUT / f"prod_{mode}_{name}.png"
                page.screenshot(path=str(shot), full_page=False)
                meta["screenshots"][f"{mode}_{name}"] = shot.name
                if name == "home":
                    probe = page.evaluate(
                        """async () => {
                          const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                            credentials: 'same-origin', cache: 'no-store'
                          });
                          const j = await r.json().catch(() => ({}));
                          const pub = j.merchant_publication_v1 || {};
                          const sc = pub.store_condition || {};
                          const cc = pub.communication_condition || {};
                          const cart = pub.cart_condition || pub.cart_operational_action || {};
                          const root = document.getElementById('ma-home-experience-root');
                          const text = (root && root.innerText) || '';
                          return {
                            store_condition: sc.summary_ar || '',
                            primary_action: pub.primary_action || pub.primary_business_action || '',
                            primary_subject: pub.primary_subject || '',
                            communication: cc.summary_ar || '',
                            carts: cart.summary_ar || '',
                            simulation_run_id: pub.simulation_run_id
                              || ((j.reality_validation_identity_v1||{}).simulation_run_id) || '',
                            store_slug: j.store_slug || null,
                            home_text: text.slice(0, 1200),
                            has_hes: !!(root && root.querySelector('[data-hes=\"1\"]')),
                          };
                        }"""
                    )
                    fingerprints[mode] = {
                        k: probe.get(k)
                        for k in (
                            "store_condition",
                            "primary_action",
                            "primary_subject",
                            "communication",
                            "carts",
                            "simulation_run_id",
                            "store_slug",
                        )
                    }
                    meta["visible_home_sample"][mode] = {
                        "has_hes": probe.get("has_hes"),
                        "home_text": probe.get("home_text"),
                    }
            ctx.close()

        meta["parity"] = {
            "desktop": fingerprints.get("desktop"),
            "mobile": fingerprints.get("mobile"),
            "match": fingerprints.get("desktop") == fingerprints.get("mobile"),
            "same_run": (
                (fingerprints.get("desktop") or {}).get("simulation_run_id") == sim
                and (fingerprints.get("mobile") or {}).get("simulation_run_id") == sim
            ),
        }
        home_ok = all(
            "حالة المتجر" in ((meta.get("visible_home_sample") or {}).get(m) or {}).get("home_text") or ""
            or "أهم قرار" in ((meta.get("visible_home_sample") or {}).get(m) or {}).get("home_text") or ""
            for m in ("desktop", "mobile")
        )
        meta["verdict"] = (
            "PASS_READY_FOR_CEO_30S"
            if meta["parity"].get("match") and meta["parity"].get("same_run") and home_ok
            else "FAIL_HOME_OR_PARITY"
        )
        browser.close()

    (OUT / "ceo_pack_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"verdict": meta["verdict"], "precondition": meta["precondition"], "home_ok": home_ok}, ensure_ascii=False))
    return 0 if str(meta["verdict"]).startswith("PASS") else 4


if __name__ == "__main__":
    raise SystemExit(main())
