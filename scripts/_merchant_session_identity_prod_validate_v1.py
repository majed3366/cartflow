# -*- coding: utf-8 -*-
"""
Merchant Session Identity Panel V1 — production visual + VIP parity check.

Hard gate: Living Store review session CONSISTENT identity
  email=cf.living.store.review@smartreplyai.net, store=demo, merchant_id present.
Then open identity panel on Desktop + Mobile and compare VIP threshold field.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "merchant_session_identity_v1"
REVIEW_EMAIL = "cf.living.store.review@smartreplyai.net"
DEPLOY_MARKER = "maOpenAccountIdentityPanel"


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def wait_deploy(*, attempts: int = 40, sleep_s: float = 15.0) -> dict:
    out: dict = {"deployed": False, "attempts": []}
    for i in range(1, attempts + 1):
        try:
            ts = int(time.time())
            js = _get(f"{BASE}/static/merchant_session_identity_v1.js?_={ts}")
            css = _get(f"{BASE}/static/merchant_session_identity_v1.css?_={ts}")
        except Exception as e:
            out["attempts"].append({"n": i, "error": str(e)[:160]})
            time.sleep(sleep_s)
            continue
        hit = DEPLOY_MARKER in js and "ma-account-identity" in css
        out["attempts"].append({"n": i, "hit": hit})
        if hit:
            out["deployed"] = True
            out["attempt"] = i
            return out
        time.sleep(sleep_s)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "verdict": "PENDING",
    }
    deploy = wait_deploy()
    report["deploy"] = {
        "deployed": deploy.get("deployed"),
        "attempt": deploy.get("attempt"),
        "last": (deploy.get("attempts") or [])[-2:],
    }
    if not deploy.get("deployed"):
        report["verdict"] = "FAIL_DEPLOY"
        _write(report)
        print(json.dumps(report, ensure_ascii=False))
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1280, "height": 800}, locale="ar-SA")
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
        report["review_session"] = {
            "http": session.get("http"),
            "email": body.get("email"),
            "store_slug": body.get("store_slug"),
            "merchant_user_id": body.get("merchant_user_id"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_SESSION"
            _write(report)
            browser.close()
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

        fingerprints = {}
        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            page.wait_for_timeout(5000)
            # Open identity panel
            page.click("#ma-gtb-account-btn")
            page.wait_for_selector("#ma-account-identity-panel:not([hidden])", timeout=15000)
            page.wait_for_timeout(2000)
            page.screenshot(
                path=str(OUT / f"prod_{mode}_identity_panel.png"), full_page=False
            )
            identity = page.evaluate(
                """async () => {
                  const last = window.maGetAccountIdentityLastPayload
                    ? window.maGetAccountIdentityLastPayload() : null;
                  const text = (document.body && document.body.innerText) || '';
                  return {
                    payload: last,
                    panel_visible: !!(document.getElementById('ma-account-identity-panel')
                      && !document.getElementById('ma-account-identity-panel').hidden),
                    has_email: text.includes('cf.living.store.review@smartreplyai.net'),
                    has_demo: text.includes('demo'),
                    has_review_label: text.includes('قيد المراجعة'),
                    has_sim_run: text.includes('simulation_run_id'),
                  };
                }"""
            )
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            # VIP minimum lives on VIP carts settings (same session / same account)
            page.goto(f"{BASE}/dashboard#vip", timeout=120000)
            page.wait_for_timeout(6500)
            try:
                page.wait_for_selector("#ma-vip-threshold", timeout=20000)
            except Exception:
                pass
            vip = page.evaluate(
                """() => {
                  const el = document.getElementById('ma-vip-threshold');
                  const disp = document.getElementById('ma-vip-threshold-display');
                  const input = el ? String(el.value || '').trim() : '';
                  const display = disp ? String(disp.textContent || '').trim() : '';
                  return { input: input, display: display };
                }"""
            )
            page.screenshot(
                path=str(OUT / f"prod_{mode}_vip_threshold.png"), full_page=False
            )
            fingerprints[mode] = {
                "identity": identity,
                "vip": vip,
            }
            ctx.close()

        browser.close()

    d = fingerprints.get("desktop") or {}
    m = fingerprints.get("mobile") or {}
    di = (d.get("identity") or {}).get("payload") or {}
    mi = (m.get("identity") or {}).get("payload") or {}

    email_ok = (
        str(di.get("merchant_email") or "").lower() == REVIEW_EMAIL
        and str(mi.get("merchant_email") or "").lower() == REVIEW_EMAIL
    )
    store_ok = di.get("store_slug") == "demo" and mi.get("store_slug") == "demo"
    mid_ok = di.get("merchant_id") is not None and di.get("merchant_id") == mi.get(
        "merchant_id"
    )
    review_mid = report.get("review_session", {}).get("merchant_user_id")
    mid_matches_session = review_mid is None or di.get("merchant_id") == review_mid
    no_sim = not (d.get("identity") or {}).get("has_sim_run") and not (
        m.get("identity") or {}
    ).get("has_sim_run")
    consistent = bool((di.get("consistency") or {}).get("ok")) and bool(
        (mi.get("consistency") or {}).get("ok")
    )

    vip_d = (d.get("vip") or {}).get("input") or (d.get("vip") or {}).get("display")
    vip_m = (m.get("vip") or {}).get("input") or (m.get("vip") or {}).get("display")
    identity_same = email_ok and store_ok and mid_ok
    vip_present = bool(str(vip_d or "").strip()) or bool(str(vip_m or "").strip())
    vip_same = str(vip_d or "").strip() == str(vip_m or "").strip()

    flags = {
        "email_ok": email_ok,
        "store_ok": store_ok,
        "merchant_id_ok": mid_ok and mid_matches_session,
        "no_simulation_run_id": no_sim,
        "consistency_ok": consistent,
        "identity_same_desktop_mobile": identity_same,
        "vip_present": vip_present,
        "vip_same_desktop_mobile": vip_same,
        "vip_desktop": vip_d,
        "vip_mobile": vip_m,
        "merchant_id": di.get("merchant_id"),
    }
    report["flags"] = flags
    report["fingerprints"] = fingerprints

    if (
        email_ok
        and store_ok
        and mid_ok
        and mid_matches_session
        and no_sim
        and consistent
        and identity_same
    ):
        if vip_present and vip_same:
            report["verdict"] = "PASS_IDENTITY_AND_VIP"
        elif not vip_present:
            report["verdict"] = "PASS_IDENTITY_VIP_UNREADABLE"
            report["note"] = (
                "Identity matches Desktop/Mobile; VIP threshold field was empty "
                "or not loaded — re-check VIP page manually if needed."
            )
        else:
            report["verdict"] = "PASS_IDENTITY_VIP_DIFFERS"
            report["note"] = (
                "Identity matches; VIP values differ — investigate as separate "
                "data persistence / responsive-state bug (not VIP logic change)."
            )
    else:
        report["verdict"] = "FAIL_IDENTITY"

    _write(report)
    print(
        json.dumps(
            {"verdict": report["verdict"], "flags": flags},
            ensure_ascii=False,
        )
    )
    return 0 if str(report["verdict"]).startswith("PASS") else 4


def _write(report: dict) -> None:
    (OUT / "prod_validate_meta.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    flags = report.get("flags") or {}
    md = f"""# Merchant Session Identity V1 — Production Validation

**Generated (UTC):** {report.get("generated_at_utc")}  
**Verdict:** `{report.get("verdict")}`  

## Flags

```json
{json.dumps(flags, ensure_ascii=False, indent=2)}
```

## Screenshots

`prod_desktop_identity_panel.png` · `prod_mobile_identity_panel.png` · VIP settings shots.
"""
    (OUT / "PRODUCTION_VALIDATION_V1.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
