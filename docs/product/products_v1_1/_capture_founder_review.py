# -*- coding: utf-8 -*-
"""Founder evidence — Products V1.1. Local R17, 390px, 6 shots. DEPLOY: NO."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DESKTOP = Path(r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Products_V1_1")

SHOTS = [
    "01_products_first_view_mobile.png",
    "02_product_strong_signal_mobile.png",
    "03_product_numeric_evidence_mobile.png",
    "04_product_unknown_exposure_mobile.png",
    "05_product_missing_identity_mobile.png",
    "06_products_full_flow_mobile.png",
]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = int(s.getsockname()[1])
    s.close()
    return p


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP.mkdir(parents=True, exist_ok=True)
    db_path = os.path.join(
        tempfile.gettempdir(),
        "cartflow_products_v1_1_%s.db" % os.getpid(),
    )
    if os.path.exists(db_path):
        os.remove(db_path)

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    env["ENV"] = "development"
    env["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
    env["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
    env["CARTFLOW_MERCHANT_UI_V2"] = "1"
    env["CARTFLOW_CART_WORKSPACE_V1"] = "true"
    env["SECRET_KEY"] = "products-v1-1-founder-review"
    env["CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"] = "1"

    sys.path.insert(0, str(ROOT))
    for k, v in env.items():
        os.environ[k] = v

    from extensions import db, init_database  # noqa: E402
    import models  # noqa: F401, E402
    from schema_cart_line_snapshots_v1 import (  # noqa: E402
        ensure_cart_line_snapshots_schema,
    )
    from schema_commercial_decision_commitment_v1 import (  # noqa: E402
        ensure_commercial_decision_commitment_schema,
        reset_commercial_decision_commitment_schema_guard_for_tests,
    )
    from schema_product_catalog_v1 import ensure_product_catalog_schema  # noqa: E402
    from schema_product_hesitation_mapping_v1 import (  # noqa: E402
        ensure_product_hesitation_mapping_schema,
    )
    from schema_product_purchase_mapping_v1 import (  # noqa: E402
        ensure_product_purchase_mapping_schema,
    )
    from schema_product_signal_events_v1 import (  # noqa: E402
        ensure_product_signal_events_schema,
    )
    from services.live_reality_lab_v1 import (  # noqa: E402
        LAB_STORE_SLUG,
        SCENARIO_R17,
        apply_lab_scenario_v1,
        ensure_live_reality_lab_tenant_v1,
    )
    from services.live_reality_lab_v1.contract_v1 import LAB_EMAIL  # noqa: E402
    from services.merchant_auth_http import (  # noqa: E402
        issue_merchant_session_cookie_value,
        merchant_cookie_name,
    )
    from services.merchant_auth_v1 import get_merchant_user_by_email  # noqa: E402

    init_database()
    db.create_all()
    reset_commercial_decision_commitment_schema_guard_for_tests()
    ensure_commercial_decision_commitment_schema(db)
    ensure_product_catalog_schema(db)
    ensure_cart_line_snapshots_schema(db)
    ensure_product_signal_events_schema(db)
    ensure_product_hesitation_mapping_schema(db)
    ensure_product_purchase_mapping_schema(db)
    ensure_live_reality_lab_tenant_v1()
    apply_lab_scenario_v1(
        authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R17
    )

    user = get_merchant_user_by_email(LAB_EMAIL)
    assert user is not None
    cookie = issue_merchant_session_cookie_value(int(user.id))

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proof = {"mobile_clipping": None, "shots": [], "deploy": "NO"}
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(base + "/ping", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("server_start_timeout")

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=2,
                locale="ar-SA",
            )
            context.add_cookies(
                [
                    {
                        "name": merchant_cookie_name(),
                        "value": cookie,
                        "domain": "127.0.0.1",
                        "path": "/",
                        "httpOnly": False,
                        "secure": False,
                        "sameSite": "Lax",
                    }
                ]
            )
            page = context.new_page()

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

            page.goto(
                base + "/dashboard?cf_ui=v2#products",
                wait_until="domcontentloaded",
                timeout=90000,
            )
            page.wait_for_timeout(2500)
            page.evaluate(
                """() => {
  if (window.CartFlowUiV2 && window.CartFlowUiV2.go) {
    window.CartFlowUiV2.go('products');
  }
}"""
            )
            try:
                page.wait_for_selector(
                    '#cf2-products-root [data-cf2-prd="1"]',
                    timeout=20000,
                    state="attached",
                )
            except Exception:
                body = page.locator("#cf2-products-root").inner_html()
                print("PRODUCTS_ROOT", body[:800])
                print(
                    "HAS_JS",
                    page.evaluate("() => !!(window.CartFlowUiV2Products)"),
                )
                raise
            page.wait_for_timeout(700)
            snap(SHOTS[0])

            into('[data-cf2-prd-id="nf-oud-royal"]', "start")
            snap(SHOTS[1])

            into('[data-cf2-prd-id="nf-amber-night"]', "center")
            snap(SHOTS[2])

            into('[data-cf2-prd-id="nf-gift-set"]', "center")
            snap(SHOTS[3])

            into('[data-cf2-prd-id="nf-missing-name"]', "center")
            snap(SHOTS[4])

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(250)
            into('[data-cf2-prd-id="nf-amber-night"]', "start")
            snap(SHOTS[5])

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
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()

    proof_path = OUT / "local_proof.json"
    proof_path.write_text(
        json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy2(proof_path, DESKTOP / "local_proof.json")
    count = len([n for n in SHOTS if (OUT / n).exists()])
    print("COUNT", count)
    print("CLIP", proof.get("mobile_clipping"))
    print("DESKTOP", DESKTOP)
    return 0 if count == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
