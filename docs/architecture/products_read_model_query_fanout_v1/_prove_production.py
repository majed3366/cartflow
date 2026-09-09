# -*- coding: utf-8 -*-
"""Production endpoint proof for PRODUCTS_READ_MODEL_QUERY_FANOUT_V1. Not a UI change."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "PRODUCTION_PROOF.json"
BASE = "https://smartreplyai.net"
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"
FE_EMAIL = "founder.evaluation@cartflow.local"
FE_PASSWORD = "FounderEval-Prod-Tenant-V1!"
RUNTIME = "57fa657093d55ea481240d8f56128911642ff0f6"


def _login(page, email: str, password: str) -> None:
    page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_url("**/dashboard**", timeout=60000)


def main() -> int:
    proof: dict = {"runtime_sha": RUNTIME}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ar-SA")
        page = context.new_page()
        ident = page.request.get(BASE + "/")
        proof["live_sha"] = ident.headers.get("x-cartflow-git-sha")
        proof["exact_sha_match"] = proof["live_sha"] == RUNTIME

        _login(page, LAB_EMAIL, LAB_PASSWORD)
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
        oud = rows.get("nf-oud-royal") or {}
        amber = rows.get("nf-amber-night") or {}
        gift = rows.get("nf-gift-set") or {}
        missing = rows.get("nf-missing-name") or {}
        proof["lab_products"] = {
            "http": pkg_resp.status,
            "ok": pkg.get("ok"),
            "store_slug": pkg.get("store_slug"),
            "lab_tenant": pkg.get("lab_tenant"),
            "counts": pkg.get("counts"),
            "query_delta": pkg.get("query_delta"),
            "n_plus_one": pkg.get("n_plus_one"),
            "frontend_ranking": pkg.get("frontend_ranking"),
            "read_model_owner": pkg.get("read_model_owner"),
            "unique_visitor_claim": pkg.get("unique_visitor_claim"),
            "oud": {
                "name": oud.get("product_name"),
                "cart_count": oud.get("cart_count"),
                "cart_value": oud.get("cart_value"),
                "purchases": oud.get("purchases"),
                "hesitation": oud.get("hesitation_reason_counts"),
                "exposure": oud.get("exposure"),
            },
            "amber": {
                "name": amber.get("product_name"),
                "cart_count": amber.get("cart_count"),
                "cart_value": amber.get("cart_value"),
                "purchases": amber.get("purchases"),
                "hesitation": amber.get("hesitation_reason_counts"),
                "exposure": amber.get("exposure"),
            },
            "gift": {
                "name": gift.get("product_name"),
                "cart_count": gift.get("cart_count"),
                "cart_value": gift.get("cart_value"),
                "purchases": gift.get("purchases"),
                "exposure_state": (gift.get("exposure") or {}).get("state"),
                "exposure_count": (gift.get("exposure") or {}).get("count"),
            },
            "missing": {
                "name": missing.get("product_name"),
                "identity": missing.get("product_identity"),
                "missing_name": missing.get("missing_name"),
            },
        }

        home = page.request.get(f"{BASE}/api/dashboard/summary")
        home_body = home.json() if home.ok else {}
        col = ((home_body.get("commercial_opportunity_layer_v1") or {}))
        ogl = home_body.get("operational_guidance_v1") or {}
        cat = home_body.get("mission_catalog_v1") or {}
        cdc = home_body.get("commercial_decision_commitment_v1") or {}
        port = home_body.get("mission_portfolio_v1") or {}
        proof["lab_home"] = {
            "http": home.status,
            "col_family": (col.get("primary") or col.get("family") or col.get("opportunity_family")),
            "col_keys": sorted(list(col.keys()))[:12] if isinstance(col, dict) else type(col).__name__,
            "has_products_compose": "products_commercial_truth_v1" in json.dumps(home_body),
        }
        ws = page.request.get(f"{BASE}/api/cart-workspace/v1/projection")
        proof["lab_workspace"] = {"http": ws.status, "ok": bool(ws.ok)}
        carts = page.request.get(f"{BASE}/api/dashboard/normal-carts")
        proof["lab_carts"] = {"http": carts.status, "ok": bool(carts.ok)}

        page.goto(BASE + "/logout", wait_until="networkidle", timeout=60000)
        _login(page, FE_EMAIL, FE_PASSWORD)
        fe = page.request.get(f"{BASE}/api/dashboard/products")
        fe_pkg = fe.json()
        fe_ids = [r.get("product_id") for r in (fe_pkg.get("products") or [])]
        fe_states = sorted(
            {
                (r.get("exposure") or {}).get("state")
                for r in (fe_pkg.get("products") or [])
            }
        )
        proof["founder_eval_products"] = {
            "http": fe.status,
            "lab_tenant": fe_pkg.get("lab_tenant"),
            "query_delta": fe_pkg.get("query_delta"),
            "n_plus_one": fe_pkg.get("n_plus_one"),
            "counts": fe_pkg.get("counts"),
            "product_ids_sample": fe_ids[:8],
            "has_lab_sku": any(
                i in fe_ids
                for i in ("nf-oud-royal", "nf-amber-night", "nf-gift-set", "nf-missing-name")
            ),
            "exposure_states": fe_states,
            "visit_field_label": fe_pkg.get("visit_field_label"),
        }
        browser.close()

    OUT.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
