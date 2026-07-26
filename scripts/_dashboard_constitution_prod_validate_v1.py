# -*- coding: utf-8 -*-
"""
Dashboard Constitution V1 — production validation after deploy.

Hard gates:
  - Static marker from constitution commit is live
  - Living Store: CONSISTENT + CEO_REVIEW_SAFE=TRUE + store_slug=demo
  - One-question page purposes, View Details ownership, no banned tech copy
  - Desktop/Mobile meaning parity on publication fingerprint
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "dashboard_constitution_v1"
DEPLOY_MARKER = "Constitution: hide workspace question off-page"
APP_MARKER = "Constitution: empty entry is Home"
COMMS_MARKER = 'data-constitution="communication"'

SURFACES = (
    ("home", "#home"),
    ("workspace", "#workspace"),
    ("products", "#products"),
    ("carts", "#carts"),
    ("communication", "#communication"),
    ("settings", "#settings"),
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
    "قريباً",
)

EXPECTED_PURPOSE_SNIPPETS = {
    "home": ("الآن", "متج"),
    "workspace": ("قرار",),
    "products": ("منتج",),
    "carts": ("سلة",),
    "communication": ("تواصل",),
}


def _get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def wait_for_deploy(*, attempts: int = 40, sleep_s: float = 15.0) -> dict:
    out: dict = {"attempts": [], "deployed": False}
    for i in range(1, attempts + 1):
        ts = int(time.time())
        try:
            app = _get(f"{BASE}/static/merchant_app.js?_={ts}")
            cs = _get(f"{BASE}/static/commerce_situations_surfaces_v1.js?_={ts}")
        except Exception as e:
            out["attempts"].append({"n": i, "error": str(e)})
            time.sleep(sleep_s)
            continue
        hit = APP_MARKER in app and DEPLOY_MARKER in app and COMMS_MARKER in cs
        out["attempts"].append(
            {
                "n": i,
                "marker_app": APP_MARKER in app and DEPLOY_MARKER in app,
                "marker_comms": COMMS_MARKER in cs,
            }
        )
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
        "base": BASE,
        "gate": "dashboard_constitution_v1",
        "verdict": "PENDING",
    }

    deploy = wait_for_deploy()
    report["deploy"] = {
        "deployed": deploy.get("deployed"),
        "attempt": deploy.get("attempt"),
        "last_attempts": (deploy.get("attempts") or [])[-3:],
    }
    (OUT / "deploy_wait.json").write_text(
        json.dumps(deploy, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"deploy": report["deploy"]}, ensure_ascii=False))
    if not deploy.get("deployed"):
        report["verdict"] = "FAIL_DEPLOY_TIMEOUT"
        _write(report)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1280, "height": 800}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)

        run = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-reality-run', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        report["living_store_run"] = {"http": run.get("http"), "body": run.get("body")}

        status_body: dict = {}
        job_state = ""
        for _ in range(72):
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
            job_state = str(
                (job or {}).get("status")
                or (job or {}).get("state")
                or (job or {}).get("phase")
                or ""
            ).lower()
            # Multi-worker in_memory status may lag; finished_at is authoritative when present.
            finished = (job or {}).get("finished_at_utc")
            if finished or job_state in {"done", "completed", "success", "ready", "finished"}:
                job_state = job_state or "finished"
                break
            if job_state in {"failed", "error"}:
                break
        report["living_store_status"] = status_body
        report["living_store_job_state"] = job_state
        if job_state in {"failed", "error"}:
            report["verdict"] = "FAIL_LIVING_STORE_ERROR"
            _write(report)
            browser.close()
            return 5
        # Soft wait only — certify identity next (status endpoint can stay "running"
        # across workers while the DB-backed review session is already consistent).
        boot.wait_for_timeout(8000)

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
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_REVIEW_SESSION"
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

        cert_ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ar-SA")
        cert_ctx.add_cookies([cookie])
        cert = cert_ctx.new_page()
        cert.goto(
            f"{BASE}/dev/reality-validation-context?store=demo&format=html",
            timeout=120000,
        )
        cert.wait_for_timeout(2000)
        cert.screenshot(path=str(OUT / "prod_cert_identity.png"), full_page=True)
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
            _write(report)
            browser.close()
            return 3

        fingerprints: dict = {}
        tech_hits: dict = {}
        surface_checks: dict = {}

        # Parity: capture Home fingerprints back-to-back before long surface tours.
        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            try:
                page.wait_for_selector("text=عرض التفاصيل", timeout=45000)
            except Exception:
                page.wait_for_timeout(8000)
            fingerprints[mode] = page.evaluate(
                """async () => {
                  const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                    credentials: 'same-origin', cache: 'no-store'
                  });
                  const j = await r.json().catch(() => ({}));
                  const pub = j.merchant_publication_v1 || {};
                  const sc = pub.store_condition || {};
                  const cc = pub.communication_condition || {};
                  return {
                    store_slug: j.store_slug || null,
                    simulation_run_id: pub.simulation_run_id
                      || ((j.reality_validation_identity_v1||{}).simulation_run_id) || '',
                    store_condition: sc.summary_ar || '',
                    primary_action: pub.primary_action || pub.primary_business_action || '',
                    primary_subject: pub.primary_subject || '',
                    communication: cc.summary_ar || '',
                  };
                }"""
            )
            ctx.close()

        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            for name, hash_path in SURFACES:
                page.goto(f"{BASE}/dashboard{hash_path}", timeout=120000)
                if name == "home":
                    try:
                        page.wait_for_selector(
                            "text=عرض التفاصيل", timeout=45000
                        )
                    except Exception:
                        page.wait_for_timeout(8000)
                else:
                    page.wait_for_timeout(5500)
                shot = OUT / f"prod_{mode}_{name}.png"
                page.screenshot(path=str(shot), full_page=False)
                probe = page.evaluate(
                    """() => {
                      const pageAttr = document.body && document.body.getAttribute('data-ma-page');
                      const purposeEl = document.getElementById('pagePurpose');
                      const subEl = document.getElementById('pageSub');
                      const wq = document.getElementById('cw-constitution-question');
                      const purpose = ((purposeEl && !purposeEl.hidden && purposeEl.textContent) || '').trim();
                      const sub = ((subEl && !subEl.hidden && subEl.textContent) || '').trim();
                      const workspaceQ = (pageAttr === 'workspace' && wq && !wq.hidden)
                        ? ((wq.textContent || '').trim()) : '';
                      const question = pageAttr === 'workspace'
                        ? (workspaceQ || purpose || sub)
                        : (pageAttr === 'carts' ? (sub || purpose) : (purpose || sub));
                      const text = (document.body && document.body.innerText) || '';
                      const monthPage = document.getElementById('page-home-month');
                      const monthHidden = !monthPage || monthPage.hidden || monthPage.getAttribute('aria-hidden') === 'true';
                      const notify = document.getElementById('ma-gtb-notify');
                      const notifyHidden = !notify || notify.hidden || notify.hasAttribute('hidden');
                      const autoMode = document.getElementById('ma-automation-mode-card');
                      const autoHidden = !autoMode || autoMode.hidden || autoMode.hasAttribute('hidden');
                      const viewDetails = (text.match(/عرض التفاصيل/g) || []).length;
                      const systemicOnCarts = /قرار العمل:|الحالة التنفيذية|لماذا هذا القرار/.test(text);
                      const commsFacts = ['تم الإرسال','تم التسليم','تم الرد','عاد العميل','لا يوجد رقم','يحتاج متابعة']
                        .filter((k) => text.includes(k));
                      const actionLinks = Array.from(document.querySelectorAll('a[href]'))
                        .map((a) => ((a.getAttribute('href') || '') + '|' + ((a.textContent || '').trim())))
                        .filter((x) => /عرض|متابعة|بلا رقم|workspace|carts|communication/i.test(x))
                        .slice(0, 24);
                      return {
                        page: document.body && document.body.getAttribute('data-ma-page'),
                        purpose: question,
                        monthHidden,
                        notifyHidden,
                        autoHidden,
                        viewDetails,
                        systemicOnCarts,
                        commsFacts,
                        actionLinks,
                        text_sample: text.slice(0, 2200),
                        hash: location.hash || '',
                      };
                    }"""
                )
                pub = page.evaluate(
                    """async () => {
                      const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                        credentials: 'same-origin', cache: 'no-store'
                      });
                      const j = await r.json().catch(() => ({}));
                      const pub = j.merchant_publication_v1 || {};
                      const sc = pub.store_condition || {};
                      const cc = pub.communication_condition || {};
                      const cart = pub.cart_condition || pub.cart_operational_action || {};
                      return {
                        store_slug: j.store_slug || null,
                        simulation_run_id: pub.simulation_run_id
                          || ((j.reality_validation_identity_v1||{}).simulation_run_id) || '',
                        store_condition: sc.summary_ar || '',
                        primary_action: pub.primary_action || pub.primary_business_action || '',
                        primary_subject: pub.primary_subject || '',
                        communication: cc.summary_ar || '',
                        carts: cart.summary_ar || '',
                      };
                    }"""
                )
                key = f"{mode}_{name}"
                report.setdefault("screenshots", {})[key] = shot.name
                hits = [t for t in BANNED_VISIBLE if t in (probe.get("text_sample") or "")]
                tech_hits[key] = hits
                purpose = probe.get("purpose") or ""
                purpose_ok = True
                for snip in EXPECTED_PURPOSE_SNIPPETS.get(name, ()):
                    if snip not in purpose:
                        purpose_ok = False
                surface_checks[key] = {
                    "purpose": purpose,
                    "purpose_ok": purpose_ok if name in EXPECTED_PURPOSE_SNIPPETS else True,
                    "monthHidden": probe.get("monthHidden"),
                    "notifyHidden": probe.get("notifyHidden"),
                    "autoHidden": probe.get("autoHidden"),
                    "viewDetails": probe.get("viewDetails"),
                    "systemicOnCarts": probe.get("systemicOnCarts"),
                    "commsFacts": probe.get("commsFacts"),
                    "actionLinks": probe.get("actionLinks"),
                    "hash": probe.get("hash"),
                    "page_attr": probe.get("page"),
                }
            # empty hash → home
            page.goto(f"{BASE}/dashboard", timeout=120000)
            page.wait_for_timeout(3500)
            empty_hash = page.evaluate(
                """() => ({
                  hash: location.hash || '',
                  page: document.body && document.body.getAttribute('data-ma-page')
                })"""
            )
            surface_checks[f"{mode}_empty_hash"] = empty_hash or {}
            ctx.close()

        def _meaning(fp: dict | None) -> dict:
            fp = fp or {}
            return {
                "store_condition": fp.get("store_condition"),
                "primary_action": fp.get("primary_action"),
                "primary_subject": fp.get("primary_subject"),
                "communication": fp.get("communication"),
                "simulation_run_id": fp.get("simulation_run_id"),
                "store_slug": fp.get("store_slug"),
            }

        report["parity"] = {
            "desktop": fingerprints.get("desktop"),
            "mobile": fingerprints.get("mobile"),
            "match": _meaning(fingerprints.get("desktop"))
            == _meaning(fingerprints.get("mobile")),
        }
        report["technical_copy_scan"] = tech_hits
        report["surface_checks"] = surface_checks

        any_tech = any(bool(v) for v in tech_hits.values())
        parity_ok = bool(report["parity"].get("match"))
        same_run = (
            (fingerprints.get("desktop") or {}).get("simulation_run_id") == sim
            and (fingerprints.get("mobile") or {}).get("simulation_run_id") == sim
        )
        home_d = surface_checks.get("desktop_home") or {}
        home_m = surface_checks.get("mobile_home") or {}
        carts_ok = not (surface_checks.get("desktop_carts") or {}).get("systemicOnCarts") and not (
            surface_checks.get("mobile_carts") or {}
        ).get("systemicOnCarts")
        comms_ok = len((surface_checks.get("desktop_communication") or {}).get("commsFacts") or []) >= 4
        empty = surface_checks.get("desktop_empty_hash") or {}
        entry_ok = str(empty.get("hash") or "").startswith("#home") or empty.get(
            "page"
        ) == "home"
        month_ok = bool(home_d.get("monthHidden")) and bool(home_m.get("monthHidden"))
        purposes_ok = all(
            (surface_checks.get(f"desktop_{n}") or {}).get("purpose_ok")
            and (surface_checks.get(f"mobile_{n}") or {}).get("purpose_ok")
            for n in EXPECTED_PURPOSE_SNIPPETS
        )

        flags = {
            "parity_ok": parity_ok,
            "any_tech": any_tech,
            "same_run": same_run,
            "carts_operational_only": carts_ok,
            "comms_facts": comms_ok,
            "empty_hash_home": entry_ok,
            "month_wall_hidden": month_ok,
            "purposes_ok": purposes_ok,
        }
        report["acceptance_flags"] = flags
        if all(
            [
                parity_ok,
                not any_tech,
                same_run,
                carts_ok,
                comms_ok,
                entry_ok,
                month_ok,
                purposes_ok,
            ]
        ):
            report["verdict"] = "PASS_CONSTITUTION_PROD"
        else:
            report["verdict"] = "FAIL_CONSTITUTION_PROD"

        browser.close()

    _write(report)
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "precondition": report.get("precondition"),
                "flags": report.get("acceptance_flags"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if str(report["verdict"]).startswith("PASS") else 4


def _write(report: dict) -> None:
    (OUT / "prod_validate_meta.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pre = report.get("precondition") or {}
    flags = report.get("acceptance_flags") or {}
    md = f"""# Dashboard Constitution V1 — Production Validation

**Generated (UTC):** {report.get("generated_at_utc")}  
**Verdict:** `{report.get("verdict")}`  

## Precondition (certified Living Store)

| Field | Value |
|-------|-------|
| status | `{pre.get("status")}` |
| CEO_REVIEW_SAFE | `{pre.get("CEO_REVIEW_SAFE")}` |
| store_slug | `{pre.get("store_slug")}` |
| simulation_run_id | `{pre.get("simulation_run_id")}` |

## Acceptance flags

```json
{json.dumps(flags, ensure_ascii=False, indent=2)}
```

## Deploy

```json
{json.dumps(report.get("deploy") or {{}}, ensure_ascii=False, indent=2)}
```

## Screenshots

Desktop + Mobile: Home, Workspace, Products, Carts, Communication, Settings under `docs/product/dashboard_constitution_v1/prod_*.png`.
"""
    (OUT / "PRODUCTION_VALIDATION_V1.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
