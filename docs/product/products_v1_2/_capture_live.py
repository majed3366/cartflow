# -*- coding: utf-8 -*-
"""LIVE founder evidence — Products V1.2 on smartreplyai.net. 4 mobile shots."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "live"
DESKTOP = Path(r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Products_V1_2_Live")
PROOF = Path(__file__).resolve().parent / "live" / "live_proof.json"
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"
FE_EMAIL = "founder.evaluation@cartflow.local"
FE_PASSWORD = "FounderEval-Prod-Tenant-V1!"
BASE = "https://smartreplyai.net"

SHOTS = [
    "products_v1_2_live_top_mobile.png",
    "products_v1_2_live_truth_rich_mobile.png",
    "products_v1_2_live_truth_limited_mobile.png",
    "products_v1_2_live_identity_degraded_mobile.png",
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP.mkdir(parents=True, exist_ok=True)
    proof: dict = {"deploy": "YES", "sha": None, "shots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="ar-SA",
        )
        page = context.new_page()
        ident = page.request.get(BASE + "/")
        proof["sha"] = ident.headers.get("x-cartflow-git-sha")
        page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
        page.fill('input[name="email"]', LAB_EMAIL)
        page.fill('input[name="password"]', LAB_PASSWORD)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_url("**/dashboard**", timeout=60000)
        page.wait_for_timeout(800)

        apply = page.request.post(
            f"{BASE}/api/live-reality-lab/v1/apply",
            data=json.dumps({"scenario_id": "R17_shipping_hesitation"}),
            headers={"Content-Type": "application/json"},
        )
        try:
            apply_body = apply.json()
        except Exception:
            apply_body = {"raw": apply.text()[:400]}
        proof["r17_apply"] = {"status": apply.status, "ok": bool((apply_body or {}).get("ok"))}

        pkg_resp = page.request.get(f"{BASE}/api/dashboard/products")
        pkg = pkg_resp.json()
        rows = {r.get("product_id"): r for r in (pkg.get("products") or [])}
        strengths = {}
        html_probe = ""
        proof["products"] = {
            "http": pkg_resp.status,
            "ok": pkg.get("ok"),
            "store_slug": pkg.get("store_slug"),
            "lab_tenant": pkg.get("lab_tenant"),
            "counts": pkg.get("counts"),
            "query_delta": pkg.get("query_delta"),
            "n_plus_one": pkg.get("n_plus_one"),
            "frontend_ranking": pkg.get("frontend_ranking"),
            "unique_visitor_claim": pkg.get("unique_visitor_claim"),
            "read_model_owner": pkg.get("read_model_owner"),
            "oud": {
                "name": (rows.get("nf-oud-royal") or {}).get("product_name"),
                "signal": (rows.get("nf-oud-royal") or {}).get("signal_ar"),
                "exposure": (rows.get("nf-oud-royal") or {}).get("exposure"),
            },
            "gift": {
                "name": (rows.get("nf-gift-set") or {}).get("product_name"),
                "signal": (rows.get("nf-gift-set") or {}).get("signal_ar"),
                "exposure": (rows.get("nf-gift-set") or {}).get("exposure"),
            },
            "missing": {
                "name": (rows.get("nf-missing-name") or {}).get("product_name"),
                "identity": (rows.get("nf-missing-name") or {}).get("product_identity"),
            },
        }

        home = page.request.get(f"{BASE}/api/dashboard/summary")
        home_body = home.json() if home.ok else {}
        proof["home_has_products_key"] = "products" in home_body and "products_commercial_truth_v1" in json.dumps(
            home_body
        )
        proof["summary_http"] = home.status

        page.goto(BASE + "/dashboard?cf_ui=v2#products", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(1500)
        page.evaluate(
            """() => {
  if (window.CartFlowUiV2 && window.CartFlowUiV2.go) {
    window.CartFlowUiV2.go('products');
  }
}"""
        )
        page.wait_for_selector('#cf2-products-root [data-cf2-prd="1"]', timeout=25000)
        page.wait_for_timeout(700)

        strengths = page.evaluate(
            """() => {
  const out = {};
  document.querySelectorAll('[data-cf2-prd-card="1"]').forEach((el) => {
    out[el.getAttribute('data-cf2-prd-id')] = el.getAttribute('data-cf2-product-truth-strength');
  });
  return out;
}"""
        )
        proof["truth_strength"] = strengths
        html_probe = page.locator("#cf2-products-root").inner_html()
        proof["paint"] = {
            "short_signal": "أسباب تردد لهذا المنتج" in html_probe,
            "needs_attention_count": html_probe.count("يحتاج انتباه"),
            "lab_visit": "زيارات تجريبية" in html_probe,
            "unknown": "غير متاحة بعد" in html_probe,
            "missing_title": "منتج بدون اسم في الكتالوج" in html_probe,
            "cta_separated": 'class="cf2-prd__cta"' in html_probe,
            "frontend_ranking": 'data-cf2-frontend-ranking="0"' in html_probe,
        }

        def snap(name: str) -> None:
            dest = OUT / name
            page.screenshot(path=str(dest), full_page=False)
            shutil.copy2(dest, DESKTOP / name)
            proof["shots"].append(name)
            print("wrote", dest)

        def into(sel: str, block: str = "center") -> None:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=15000)
            loc.evaluate(
                "(el, b) => el.scrollIntoView({block: b, inline: 'nearest'})",
                block,
            )
            page.wait_for_timeout(350)

        snap(SHOTS[0])
        into('[data-cf2-prd-id="nf-oud-royal"]', "start")
        snap(SHOTS[1])
        into('[data-cf2-prd-id="nf-gift-set"]', "center")
        snap(SHOTS[2])
        into('[data-cf2-prd-id="nf-missing-name"]', "center")
        snap(SHOTS[3])

        clip = page.evaluate(
            """() => {
  const root = document.querySelector('#cf2-products-root');
  if (!root) return -1;
  let n = 0;
  root.querySelectorAll('*').forEach((el) => {
    if (el.scrollWidth > el.clientWidth + 2) n += 1;
  });
  return n;
}"""
        )
        proof["mobile_clipping"] = int(clip)

        page.goto(BASE + "/dashboard?cf_ui=v2#home", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(800)
        proof["home_has_prd_marker"] = page.locator("[data-cf2-prd='1']").count()
        page.goto(BASE + "/dashboard?cf_ui=v2#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(800)
        proof["workspace_has_prd_marker"] = page.locator("[data-cf2-prd='1']").count()
        page.goto(BASE + "/dashboard?cf_ui=v2#carts", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(800)
        proof["carts_has_prd_marker"] = page.locator("[data-cf2-prd='1']").count()

        fe = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
        )
        fe_page = fe.new_page()
        fe_page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
        fe_page.fill('input[name="email"]', FE_EMAIL)
        fe_page.fill('input[name="password"]', FE_PASSWORD)
        fe_page.click('button[type="submit"], input[type="submit"]')
        fe_page.wait_for_url("**/dashboard**", timeout=60000)
        fe_pkg = fe_page.request.get(f"{BASE}/api/dashboard/products")
        try:
            fe_body = fe_pkg.json()
        except Exception:
            fe_body = {}
        fe_ids = [r.get("product_id") for r in (fe_body.get("products") or [])]
        proof["founder_eval"] = {
            "http": fe_pkg.status,
            "store_slug": fe_body.get("store_slug"),
            "lab_tenant": fe_body.get("lab_tenant"),
            "product_count": (fe_body.get("counts") or {}).get("products"),
            "has_lab_oud": "nf-oud-royal" in fe_ids,
        }
        fe.close()
        browser.close()

    PROOF.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(PROOF, DESKTOP / "live_proof.json")
    print("PROOF", PROOF)
    print("COUNT", len(proof.get("shots") or []))
    print("CLIP", proof.get("mobile_clipping"))
    return 0 if len(proof.get("shots") or []) == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
