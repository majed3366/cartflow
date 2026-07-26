# -*- coding: utf-8 -*-
"""
Executive Control V1 — certified Living Store CEO pack on production.

Precondition gate (hard stop if false):
  Status=CONSISTENT, CEO_REVIEW_SAFE=TRUE, store_slug=demo, shared simulation_run_id

Captures Desktop + Mobile for Home / Workspace / Products / Carts / Communication.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "executive_control_v1"

SURFACES = (
    ("home", "#home"),
    ("workspace", "#workspace"),
    ("products", "#products"),
    ("carts", "#carts"),
    ("communication", "#communication"),
)

BANNED_VISIBLE = (
    "CONSISTENT",
    "CEO_REVIEW_SAFE",
    "store_slug",
    "simulation_run_id",
    "truth_version",
    "cs:",
    "situation_id",
    "merchant_id",
    "operations",
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "gate": "executive_control_v1",
        "precondition": {},
        "screenshots": {},
        "parity": {},
        "technical_copy_scan": {},
        "verdict": "PENDING",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1280, "height": 800}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)

        # 1) Run Living Store (demo wall-clock; no body required)
        run = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-reality-run', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        report["living_store_run"] = {
            "http": run.get("http"),
            "body": run.get("body"),
        }

        # Poll status up to ~4 minutes (payload nests under job)
        status_body: dict = {}
        for _ in range(48):
            boot.wait_for_timeout(5000)
            st = boot.evaluate(
                """async () => {
                  const r = await fetch('/dev/living-store-reality-status', {
                    credentials: 'same-origin', cache: 'no-store'
                  });
                  return { http: r.status, body: await r.json().catch(() => ({})) };
                }"""
            )
            status_body = st.get("body") or {}
            job = status_body.get("job") if isinstance(status_body.get("job"), dict) else status_body
            state = str(
                (job or {}).get("status")
                or (job or {}).get("state")
                or (job or {}).get("phase")
                or ""
            ).lower()
            if state in {"done", "completed", "success", "ready", "finished"}:
                break
            if state in {"failed", "error"}:
                break
        report["living_store_status"] = status_body

        # 2) Bind review session
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
            "ok": body.get("ok"),
            "store_slug": body.get("store_slug"),
            "email": body.get("email"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_REVIEW_SESSION"
            (OUT / "CERTIFIED_LIVING_STORE_REPORT_V1.md").write_text(
                _md(report), encoding="utf-8"
            )
            (OUT / "ceo_pack_meta.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
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

        # 3) Certify identity
        cert_ctx = browser.new_context(
            viewport={"width": 1280, "height": 900}, locale="ar-SA"
        )
        cert_ctx.add_cookies([cookie])
        cert = cert_ctx.new_page()
        cert.goto(
            f"{BASE}/dev/reality-validation-context?store=demo&format=html",
            timeout=120000,
        )
        cert.wait_for_timeout(2500)
        cert.screenshot(
            path=str(OUT / "prod_cert_identity.png"), full_page=True
        )
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
        if safe is None:
            safe = cj.get("ceo_review_safe")
        store_slug = str(cj.get("store_slug") or "").strip()
        sim = str(cj.get("simulation_run_id") or "").strip()
        report["precondition"] = {
            "status": status,
            "CEO_REVIEW_SAFE": safe,
            "store_slug": store_slug,
            "simulation_run_id": sim,
            "http": cert_json.get("http"),
        }
        cert_ctx.close()

        if status != "CONSISTENT" or safe is not True or store_slug != "demo":
            report["verdict"] = "FAIL_PRECONDITION"
            (OUT / "CERTIFIED_LIVING_STORE_REPORT_V1.md").write_text(
                _md(report), encoding="utf-8"
            )
            (OUT / "ceo_pack_meta.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            browser.close()
            return 3

        fingerprints = {}
        tech_hits = {}
        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            for name, hash_path in SURFACES:
                page.goto(f"{BASE}/dashboard{hash_path}", timeout=120000)
                page.wait_for_timeout(6500)
                shot = OUT / f"prod_{mode}_{name}.png"
                page.screenshot(path=str(shot), full_page=False)
                report["screenshots"][f"{mode}_{name}"] = str(shot.name)
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
                      const root = document.body;
                      const text = (root && root.innerText) || '';
                      return {
                        store_slug: j.store_slug || null,
                        simulation_run_id: pub.simulation_run_id
                          || ((j.reality_validation_identity_v1||{}).simulation_run_id) || '',
                        store_condition: sc.summary_ar || '',
                        primary_action: pub.primary_action || pub.primary_business_action || '',
                        primary_subject: pub.primary_subject || '',
                        communication: cc.summary_ar || '',
                        carts: cart.summary_ar || '',
                        text_sample: text.slice(0, 1800),
                      };
                    }"""
                )
                if name == "home":
                    fingerprints[mode] = {
                        "store_condition": probe.get("store_condition"),
                        "primary_action": probe.get("primary_action"),
                        "primary_subject": probe.get("primary_subject"),
                        "communication": probe.get("communication"),
                        "carts": probe.get("carts"),
                        "simulation_run_id": probe.get("simulation_run_id"),
                        "store_slug": probe.get("store_slug"),
                    }
                hits = [t for t in BANNED_VISIBLE if t in (probe.get("text_sample") or "")]
                tech_hits[f"{mode}_{name}"] = hits
            ctx.close()

        report["parity"] = {
            "desktop": fingerprints.get("desktop"),
            "mobile": fingerprints.get("mobile"),
            "match": fingerprints.get("desktop") == fingerprints.get("mobile"),
        }
        report["technical_copy_scan"] = tech_hits
        any_tech = any(tech_hits.values())
        parity_ok = bool(report["parity"].get("match"))
        same_run = (
            (fingerprints.get("desktop") or {}).get("simulation_run_id") == sim
            and (fingerprints.get("mobile") or {}).get("simulation_run_id") == sim
        )
        if parity_ok and not any_tech and same_run:
            report["verdict"] = "PASS_READY_FOR_CEO_30S"
        else:
            report["verdict"] = "FAIL_SURFACE_OR_PARITY"
            report["fail_flags"] = {
                "parity_ok": parity_ok,
                "any_tech": any_tech,
                "same_run": same_run,
            }

        browser.close()

    (OUT / "ceo_pack_meta.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "CERTIFIED_LIVING_STORE_REPORT_V1.md").write_text(
        _md(report), encoding="utf-8"
    )
    (OUT / "CEO_VISUAL_REVIEW_PACK_V1.md").write_text(
        _ceo_pack_md(report), encoding="utf-8"
    )
    print(json.dumps({"verdict": report["verdict"], "precondition": report["precondition"]}, ensure_ascii=False))
    return 0 if str(report["verdict"]).startswith("PASS") else 4


def _md(report: dict) -> str:
    pre = report.get("precondition") or {}
    return f"""# Certified Living Store Report V1 — Executive Control

**Generated (UTC):** {report.get("generated_at_utc")}  
**Verdict:** `{report.get("verdict")}`

## Precondition

| Field | Value |
|-------|-------|
| Status | `{pre.get("status")}` |
| CEO_REVIEW_SAFE | `{pre.get("CEO_REVIEW_SAFE")}` |
| store_slug | `{pre.get("store_slug")}` |
| simulation_run_id | `{pre.get("simulation_run_id")}` |

## Parity

Desktop vs Mobile fingerprint match: `{((report.get("parity") or {}).get("match"))}`

## Screenshots

See `prod_desktop_*.png` / `prod_mobile_*.png` and `prod_cert_identity.png`.

## Meta

`ceo_pack_meta.json`
"""


def _ceo_pack_md(report: dict) -> str:
    shots = report.get("screenshots") or {}
    lines = [
        "# CEO Visual Review Pack V1 — Executive Control",
        "",
        f"**Verdict:** `{report.get('verdict')}`",
        "",
        "## 30-second questions",
        "",
        "1. How is my store?",
        "2. What is the most important issue?",
        "3. Which product is affected?",
        "4. What should I do first?",
        "5. Where are the operational details?",
        "",
        "## Screenshots",
        "",
    ]
    for key in sorted(shots):
        lines.append(f"- `{shots[key]}`")
    lines.extend(
        [
            "",
            "## Invalid sessions (do not use)",
            "",
            "- Any session with `CEO_REVIEW_SAFE=FALSE`",
            "- Any session with `store_slug != demo` (e.g. `cartflow-42b491`)",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
