# -*- coding: utf-8 -*-
"""
Founder evidence — Founder UX Closure V1.

Local lab R17, 390px, exactly 7 shots. DEPLOY: NO.
"""
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
DESKTOP = Path(
    r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Founder_UX_Closure_V1"
)

SHOTS = [
    "01_home_complete_text.png",
    "02_workspace_accepted.png",
    "03_execution_cta.png",
    "04_settings_deeplink_shipping.png",
    "05_settings_timing.png",
    "06_sidebar_handle_refined.png",
    "07_decision_organism_refined.png",
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
        "cartflow_founder_ux_closure_v1_%s.db" % os.getpid(),
    )
    if os.path.exists(db_path):
        os.remove(db_path)

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    env["ENV"] = "development"
    env["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
    env["CARTFLOW_MERCHANT_UI_V2"] = "1"
    env["CARTFLOW_CART_WORKSPACE_V1"] = "true"
    env["SECRET_KEY"] = "founder-ux-closure-v1-local"
    env["CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"] = "1"

    sys.path.insert(0, str(ROOT))
    for k, v in env.items():
        os.environ[k] = v

    from extensions import db, init_database  # noqa: E402
    import models  # noqa: F401, E402
    from schema_commercial_decision_commitment_v1 import (  # noqa: E402
        ensure_commercial_decision_commitment_schema,
        reset_commercial_decision_commitment_schema_guard_for_tests,
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
    ensure_live_reality_lab_tenant_v1()
    apply_lab_scenario_v1(
        authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R17
    )

    store = (
        db.session.query(models.Store)
        .filter(models.Store.zid_store_id == LAB_STORE_SLUG)
        .first()
    )
    assert store is not None
    store.reason_templates_json = json.dumps(
        {
            "price": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 30, "unit": "minute", "text": "سعر"}],
            },
            "shipping": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 60, "unit": "minute", "text": "شحن"}],
            },
            "delivery": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 3, "unit": "hour", "text": "توصيل"}],
            },
            "quality": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 90, "unit": "minute", "text": "جودة"}],
            },
            "warranty": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 2, "unit": "hour", "text": "ضمان"}],
            },
            "thinking": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 45, "unit": "minute", "text": "تفكير"}],
            },
            "other": {
                "enabled": True,
                "message_count": 1,
                "messages": [{"delay": 3, "unit": "hour", "text": "آخر"}],
            },
        },
        ensure_ascii=False,
    )
    db.session.commit()

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
                print("wrote", dest)

            page.goto(
                base + "/dashboard?cf_ui=v2#home",
                wait_until="networkidle",
                timeout=90000,
            )
            page.wait_for_timeout(2500)
            try:
                page.wait_for_selector(".cf2-home__title", timeout=15000)
            except Exception:
                pass
            snap(SHOTS[0])

            page.goto(
                base + "/dashboard?cf_ui=v2#workspace",
                wait_until="networkidle",
                timeout=90000,
            )
            page.wait_for_timeout(2000)
            page.evaluate(
                """async () => {
  try {
    await fetch('/api/commercial-mission/v1/accept', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
  } catch (e) {}
  var raw = sessionStorage.getItem('cf2_col_focus_v1');
  var opp = raw ? JSON.parse(raw) : {};
  opp.commitment = {
    phase: 'ACTION_CHOSEN',
    console_mode: 'accepted',
    commitment_id: 'capture-action-chosen',
  };
  sessionStorage.setItem('cf2_col_focus_v1', JSON.stringify(opp));
  var root = document.getElementById('cf2-workspace-root');
  if (root && window.CartFlowUiV2Workspace) {
    await window.CartFlowUiV2Workspace.loadAndPaint(root);
  }
}"""
            )
            page.wait_for_timeout(1800)
            try:
                page.locator(".cf-cda").first.scroll_into_view_if_needed()
            except Exception:
                pass
            snap(SHOTS[1])

            try:
                page.locator("[data-cf2-mission-exec='settings']").first.scroll_into_view_if_needed()
            except Exception:
                pass
            page.wait_for_timeout(400)
            snap(SHOTS[2])

            page.goto(
                base
                + "/dashboard?cf_ui=v2#settings?area=recovery&focus=shipping-hesitation",
                wait_until="networkidle",
                timeout=90000,
            )
            page.wait_for_timeout(3200)
            try:
                page.wait_for_selector("#cf2-rec-reasons", timeout=15000)
                page.locator("#cf2-rec-reasons").first.scroll_into_view_if_needed()
            except Exception:
                pass
            page.wait_for_timeout(500)
            snap(SHOTS[3])

            page.evaluate(
                """() => {
  var pick = document.querySelector('[data-cf2-rec-pick=\"shipping\"]');
  if (pick) pick.click();
  var summary = document.querySelector('.cf2-rec-summary')
    || document.querySelector('#ma-rec-sum-delay');
  if (summary) summary.scrollIntoView({ block: 'start', inline: 'nearest' });
}"""
            )
            page.wait_for_timeout(1200)
            snap(SHOTS[4])

            page.goto(
                base + "/dashboard?cf_ui=v2#workspace",
                wait_until="networkidle",
                timeout=90000,
            )
            page.wait_for_timeout(1500)
            handle = page.locator("#cf2-ctx-handle")
            if handle.count():
                handle.first.evaluate("el => el.hidden = false")
            snap(SHOTS[5])

            try:
                page.locator(".cf-cda").first.scroll_into_view_if_needed()
            except Exception:
                pass
            page.wait_for_timeout(400)
            snap(SHOTS[6])

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()

    count = len([n for n in SHOTS if (OUT / n).exists()])
    print("COUNT", count)
    print("DESKTOP", DESKTOP)
    return 0 if count == 7 else 1


if __name__ == "__main__":
    raise SystemExit(main())
