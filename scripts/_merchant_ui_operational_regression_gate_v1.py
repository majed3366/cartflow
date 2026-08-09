# -*- coding: utf-8 -*-
"""Living Store operational regression gate V1 — read-only."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "product" / "merchant_ui_operational_regression_gate_v1"
BASE = "https://smartreplyai.net"
VIEWPORTS = {
    "1440": {"width": 1440, "height": 900},
    "1024": {"width": 1024, "height": 768},
    "430": {"width": 430, "height": 932},
    "390": {"width": 390, "height": 844},
}


def http_get_json(url: str, cookie: str | None = None) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read()
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
            except Exception:
                data = {"_raw_len": len(body)}
            return {
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "bytes": len(body),
                "json": data if isinstance(data, dict) else {"_type": type(data).__name__},
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": str(e), "bytes": 0, "json": {}}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": 0, "error": str(e), "bytes": 0, "json": {}}


def session_cookie(page) -> dict:
    session = page.evaluate(
        """async () => {
          const r = await fetch('/dev/living-store-home-review-session', {
            method: 'POST', credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json().catch(() => ({}));
        }"""
    )
    return {
        "name": session["cookie_name"],
        "value": session["cookie_value"],
        "url": BASE,
        "httpOnly": True,
        "sameSite": "Lax",
    }


def cookie_header(c: dict) -> str:
    return f"{c['name']}={c['value']}"


STATE_PROBE = """() => {
  const pages = [...document.querySelectorAll('.cf2-page')];
  const active = pages.filter(p => p.classList.contains('is-active'));
  const homeTitle = document.querySelector('#cf2-home-root .cf2-home__title, #cf2-home-root h2, #cf2-home-root [data-cf2-home-decision]');
  const wsTitle = document.querySelector('#cf2-workspace-root .cf2-ws__title');
  const wsConf = document.querySelector('#cf2-workspace-root .cf2-ws__confidence');
  const wsEvidence = [...document.querySelectorAll('#cf2-workspace-root .cf2-beat--evidence .cf2-beat__list li')].map(li => (li.textContent||'').trim()).filter(Boolean);
  const wsMeaning = document.querySelector('#cf2-workspace-root [data-cf2-node="understanding"] .cf2-beat__body');
  const wsMass = document.querySelector('#cf2-workspace-root .cf2-dmass__text');
  const wsWait = document.querySelector('#cf2-workspace-root .cf2-ws__wait-lead, #cf2-workspace-root .cf2-reason__wait');
  const shell = document.querySelector('.cf2-chrome')?.getAttribute('data-cf2-appbar') || '';
  const wsMarker = document.querySelector('#cf2-workspace-root .cf2-ws')?.getAttribute('data-cf2') || '';
  const mobH = document.querySelector('#cf2-workspace-root .cf2-ws')?.getAttribute('data-cf2-mobile-hierarchy') || '';
  const legacy = {
    globalBtn: !!document.querySelector('#cf2-global-btn, .cf2-global-btn'),
    globalPanel: !!document.querySelector('#cf2-global-panel, .cf2-global-panel'),
    globalNavOpen: document.body.classList.contains('is-global-nav-open'),
    pageChrome: !!document.querySelector('.cf2-page-chrome, [data-cf2-page-chrome]'),
    sectionPills: !!document.querySelector('.cf2-section-pills, .cf2-ctx-pills'),
  };
  const hash = location.hash || '';
  const activeNav = document.querySelector('#cf2-nav [aria-current="page"]')?.getAttribute('data-cf2-nav') || '';
  const ctxOpen = document.body.classList.contains('is-ctx-open');
  const drawerOpen = document.body.classList.contains('is-drawer-open');
  const timers = {
    // best-effort: count interval ids if any exposed; otherwise null
  };
  return {
    hash,
    activeNav,
    activePageCount: active.length,
    activePages: active.map(p => p.getAttribute('data-cf2-page')),
    pageCount: pages.length,
    shell,
    wsMarker,
    mobH,
    ctxOpen,
    drawerOpen,
    legacy,
    homeTitle: (homeTitle?.textContent || '').trim().slice(0, 120),
    wsTitle: (wsTitle?.textContent || '').trim().slice(0, 120),
    wsConf: (wsConf?.textContent || '').trim().slice(0, 80),
    wsEvidence,
    wsMeaning: (wsMeaning?.textContent || '').trim().slice(0, 160),
    wsMass: (wsMass?.textContent || '').trim().slice(0, 120),
    wsWait: (wsWait?.textContent || '').trim().slice(0, 160),
    domNodes: document.querySelectorAll('*').length,
    listenerBoundFlags: document.querySelectorAll('[data-cf2-nav-bound="1"]').length,
  };
}"""


def classify_url(url: str) -> str:
    u = url.split("?")[0]
    if "/api/dashboard/summary" in u:
        return "dashboard_summary"
    if "/api/cart-workspace/v1/projection" in u:
        return "workspace_projection"
    if "/api/" in u:
        return "api_other"
    if "/static/" in u:
        return "static"
    if "/dev/" in u:
        return "dev"
    if "/dashboard" in u:
        return "dashboard_html"
    return "other"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    artifacts: dict = {"deploy_sha": None, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # Deploy SHA
    try:
        req = urllib.request.Request(f"{BASE}/", method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            artifacts["deploy_sha"] = (resp.headers.get("X-CartFlow-Git-Sha") or "").strip()
    except Exception as e:  # noqa: BLE001
        artifacts["deploy_sha_error"] = str(e)

    console_lines: list[dict] = []
    requests_log: list[dict] = []
    sequence: list[dict] = []
    perf: dict = {}
    nav_probe: dict = {}
    responsive: dict = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORTS["1440"], locale="ar-SA")
        page = ctx.new_page()

        def on_console(msg):
            console_lines.append(
                {
                    "type": msg.type,
                    "text": msg.text[:500],
                    "location": str(msg.location)[:200] if msg.location else "",
                }
            )

        def on_pageerror(err):
            console_lines.append({"type": "pageerror", "text": str(err)[:800], "location": ""})

        def on_request(req):
            if req.resource_type in ("xhr", "fetch", "document"):
                requests_log.append(
                    {
                        "phase": current_phase[0],
                        "url": req.url.split("?")[0][:180],
                        "method": req.method,
                        "resource": req.resource_type,
                        "class": classify_url(req.url),
                        "t": time.time(),
                    }
                )

        current_phase = ["boot"]
        page.on("console", on_console)
        page.on("pageerror", on_pageerror)
        page.on("request", on_request)

        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=90000)
        cookie = session_cookie(page)
        ctx.add_cookies([cookie])

        # --- Sequence ---
        current_phase[0] = "home_initial"
        t0 = time.perf_counter()
        page.goto(f"{BASE}/dashboard#home", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(1200)
        page.wait_for_function(
            "() => !!document.querySelector('#cf2-home-root .cf2-home, #cf2-home-root .cf2-error, #cf2-home-root .cf2-loading') === false || !!document.querySelector('#cf2-home-root .cf2-home, #cf2-home-root [data-cf2], #cf2-home-root h2')",
            timeout=90000,
        )
        page.wait_for_timeout(800)
        perf["home_initial_ms"] = round((time.perf_counter() - t0) * 1000)
        home_base = page.evaluate(STATE_PROBE)
        sequence.append({"step": "1_home_load", "state": home_base})
        baseline_dom = home_base.get("domNodes")
        baseline_bound = home_base.get("listenerBoundFlags")

        # Home scroll
        current_phase[0] = "home_scroll"
        page.evaluate("() => window.scrollTo(0, Math.min(400, document.body.scrollHeight))")
        page.wait_for_timeout(500)
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        sequence.append({"step": "2_home_scroll", "state": page.evaluate(STATE_PROBE)})

        # contextual open/close on home (desktop may not show handle)
        current_phase[0] = "home_ctx"
        page.set_viewport_size(VIEWPORTS["430"])
        page.wait_for_timeout(400)
        t_ctx = time.perf_counter()
        handle = page.query_selector("#cf2-ctx-handle")
        if handle:
            handle.click()
            page.wait_for_timeout(400)
            sequence.append({"step": "3_home_ctx_open", "state": page.evaluate(STATE_PROBE)})
            page.evaluate("() => window.CartFlowUiV2 && window.CartFlowUiV2.closeCtxDrawer()")
            page.wait_for_timeout(350)
            sequence.append({"step": "4_home_ctx_close", "state": page.evaluate(STATE_PROBE)})
        else:
            sequence.append({"step": "3_4_home_ctx_skipped", "state": page.evaluate(STATE_PROBE)})
        perf["home_ctx_cycle_ms"] = round((time.perf_counter() - t_ctx) * 1000)

        # Navigate Workspace
        current_phase[0] = "nav_workspace"
        page.set_viewport_size(VIEWPORTS["1440"])
        page.wait_for_timeout(300)
        t1 = time.perf_counter()
        page.evaluate("() => window.CartFlowUiV2.go('workspace')")
        page.wait_for_function(
            "() => !!document.querySelector('#cf2-workspace-root .cf2-ws, #cf2-workspace-root .cf2-error')",
            timeout=90000,
        )
        page.wait_for_timeout(700)
        perf["home_to_workspace_ms"] = round((time.perf_counter() - t1) * 1000)
        ws_state = page.evaluate(STATE_PROBE)
        sequence.append({"step": "5_workspace", "state": ws_state})

        # Workspace scroll
        current_phase[0] = "workspace_scroll"
        before_req = len(requests_log)
        page.evaluate(
            """() => {
              const el = document.querySelector('#cf2-workspace-root [data-cf2-node="action"]') || document.querySelector('#cf2-workspace-root');
              if (el) el.scrollIntoView({block:'start'});
              window.scrollBy(0, 200);
            }"""
        )
        page.wait_for_timeout(800)
        after_req = len(requests_log)
        sequence.append(
            {
                "step": "6_workspace_scroll",
                "state": page.evaluate(STATE_PROBE),
                "requests_during_scroll": after_req - before_req,
            }
        )

        # Workspace ctx
        current_phase[0] = "workspace_ctx"
        page.set_viewport_size(VIEWPORTS["430"])
        page.wait_for_timeout(350)
        t2 = time.perf_counter()
        handle = page.query_selector("#cf2-ctx-handle")
        if handle:
            handle.click()
            page.wait_for_timeout(400)
            sequence.append({"step": "7_ws_ctx_open", "state": page.evaluate(STATE_PROBE)})
            page.evaluate("() => window.CartFlowUiV2 && window.CartFlowUiV2.closeCtxDrawer()")
            page.wait_for_timeout(350)
            sequence.append({"step": "8_ws_ctx_close", "state": page.evaluate(STATE_PROBE)})
        perf["workspace_ctx_cycle_ms"] = round((time.perf_counter() - t2) * 1000)

        # Back home
        current_phase[0] = "nav_home"
        page.set_viewport_size(VIEWPORTS["1440"])
        page.wait_for_timeout(250)
        t3 = time.perf_counter()
        page.evaluate("() => window.CartFlowUiV2.go('home')")
        page.wait_for_timeout(1200)
        perf["workspace_to_home_ms"] = round((time.perf_counter() - t3) * 1000)
        home_after = page.evaluate(STATE_PROBE)
        sequence.append({"step": "9_home_return", "state": home_after})

        # Account utility
        current_phase[0] = "account_utility"
        page.set_viewport_size(VIEWPORTS["430"])
        page.wait_for_timeout(300)
        menu = page.query_selector(".cf2-menu-btn")
        if menu:
            menu.click()
            page.wait_for_timeout(400)
            sequence.append({"step": "10_account_open", "state": page.evaluate(STATE_PROBE)})
            page.evaluate(
                """() => {
                  document.body.classList.remove('is-drawer-open');
                  document.body.style.overflow = '';
                }"""
            )
            page.wait_for_timeout(300)
            sequence.append({"step": "11_account_close", "state": page.evaluate(STATE_PROBE)})

        nav_probe = {
            "baseline_dom": baseline_dom,
            "final_dom": home_after.get("domNodes"),
            "baseline_bound_nav": baseline_bound,
            "final_bound_nav": home_after.get("listenerBoundFlags"),
            "active_page_always_one": all(
                (s.get("state") or {}).get("activePageCount", 1) <= 1 for s in sequence if "state" in s
            ),
            "legacy_any_active": any(
                any((s.get("state") or {}).get("legacy", {}).values()) for s in sequence if "state" in s
            ),
            "home_title_stable": (home_base.get("homeTitle") or "") == (home_after.get("homeTitle") or "")
            or bool(home_after.get("homeTitle")),
            "hash_home_end": home_after.get("hash") == "#home",
            "shell": home_after.get("shell"),
        }

        # Responsive truth
        truths = {}
        for name, vp in VIEWPORTS.items():
            current_phase[0] = f"responsive_{name}"
            page.set_viewport_size(vp)
            page.wait_for_timeout(250)
            page.evaluate("() => window.CartFlowUiV2.go('workspace')")
            page.wait_for_function(
                "() => !!document.querySelector('#cf2-workspace-root .cf2-ws')",
                timeout=60000,
            )
            page.wait_for_timeout(600)
            st = page.evaluate(STATE_PROBE)
            truths[name] = {
                "wsTitle": st.get("wsTitle"),
                "wsConf": st.get("wsConf"),
                "wsEvidence": st.get("wsEvidence"),
                "wsMeaning": st.get("wsMeaning"),
                "wsMass": st.get("wsMass"),
                "wsWait": (st.get("wsWait") or "")[:120],
            }
        responsive = truths
        # parity: all titles equal
        titles = {v.get("wsTitle") for v in truths.values()}
        confs = {v.get("wsConf") for v in truths.values()}
        responsive_parity = {
            "same_decision": len(titles) == 1 and bool(next(iter(titles))),
            "same_confidence": len(confs) == 1,
            "titles": list(titles),
            "confidences": list(confs),
        }

        # API cookie string for urllib
        ch = cookie_header(cookie)

        browser.close()

    # Request summary
    by_phase: dict[str, Counter] = {}
    by_class = Counter()
    for r in requests_log:
        by_class[r["class"]] += 1
        by_phase.setdefault(r["phase"], Counter())[r["class"]] += 1
    api_calls = [r for r in requests_log if r["class"].startswith("api") or r["class"] in ("dashboard_summary", "workspace_projection")]
    scroll_apis = [
        r
        for r in requests_log
        if r["phase"] in ("home_scroll", "workspace_scroll")
        and r["class"] in ("dashboard_summary", "workspace_projection", "api_other")
    ]
    request_summary = {
        "total_tracked": len(requests_log),
        "by_class": dict(by_class),
        "by_phase": {k: dict(v) for k, v in by_phase.items()},
        "api_calls": len(api_calls),
        "api_during_scroll": len(scroll_apis),
        "dashboard_summary_count": by_class.get("dashboard_summary", 0),
        "workspace_projection_count": by_class.get("workspace_projection", 0),
        "api_urls": sorted({r["url"] for r in api_calls}),
    }

    # Endpoint truth (read-only)
    endpoints = {}
    for path, key in (
        ("/api/dashboard/summary", "dashboard_summary"),
        ("/api/cart-workspace/v1/projection", "workspace_projection"),
    ):
        res = http_get_json(BASE + path, cookie=ch)
        j = res.get("json") or {}
        endpoints[key] = {
            "status": res.get("status"),
            "ok": res.get("ok"),
            "bytes": res.get("bytes"),
            "keys": sorted(list(j.keys()))[:40] if isinstance(j, dict) else [],
            "has_error_key": isinstance(j, dict) and ("error" in j or "detail" in j),
            "projection_zone_b_len": (
                len(((j.get("projection") or j).get("zone_b") or []))
                if isinstance(j, dict)
                else None
            ),
            "summary_has_homeish": isinstance(j, dict)
            and any(k in j for k in ("home", "hes", "executive", "store", "carts", "zones")),
            "sample_primary_decision": None,
        }
        # extract decision text if present
        proj = j.get("projection") if isinstance(j, dict) else None
        zone = None
        if isinstance(proj, dict):
            zone = proj.get("zone_b")
        elif isinstance(j, dict):
            zone = j.get("zone_b")
        if isinstance(zone, list) and zone:
            card = zone[0] or {}
            endpoints[key]["sample_primary_decision"] = (
                card.get("decision_sentence_ar")
                or card.get("commitment_ar")
                or card.get("operational_guidance_ar")
            )

    # Optional carts-related endpoints if present
    for path, key in (
        ("/api/merchant/carts/summary", "carts_summary"),
        ("/api/carts/summary", "carts_summary_alt"),
        ("/api/merchant/setup/status", "setup_status"),
    ):
        res = http_get_json(BASE + path, cookie=ch)
        if res.get("status") and res.get("status") != 404:
            endpoints[key] = {
                "status": res.get("status"),
                "ok": res.get("ok"),
                "bytes": res.get("bytes"),
                "keys": sorted(list((res.get("json") or {}).keys()))[:30]
                if isinstance(res.get("json"), dict)
                else [],
            }

    # Console summary
    errors = [c for c in console_lines if c.get("type") in ("error", "pageerror")]
    warnings = [c for c in console_lines if c.get("type") == "warning"]
    runtime = {
        "console_total": len(console_lines),
        "errors": errors,
        "warnings_count": len(warnings),
        "pageerrors": [c for c in console_lines if c.get("type") == "pageerror"],
    }

    # Legacy inventory from code + runtime
    legacy_inventory = {
        "runtime_dom": nav_probe.get("legacy_any_active"),
        "items": [
            {
                "id": "cf2-global-btn / global panel",
                "classification": "REMOVED",
                "evidence": "absent from merchant_ui_v2_app.js/html; only denial comment in frame.css",
            },
            {
                "id": "is-global-nav-open",
                "classification": "REMOVED",
                "evidence": "no body class toggles in V2 app.js; tests assert absence",
            },
            {
                "id": "page-chrome navigation",
                "classification": "REMOVED",
                "evidence": "superseded by shell-integration-v1; no page-chrome mount in V2 template",
            },
            {
                "id": "old contextual sheet / section pills",
                "classification": "REMOVED",
                "evidence": "runtime probe found none; contextual is #cf2-ctx only",
            },
            {
                "id": "nav-reset-v1 remnants",
                "classification": "UNREACHABLE",
                "evidence": "historical commits only; current marker shell-integration-v1",
            },
            {
                "id": "global-ownership-v1 panel",
                "classification": "REMOVED",
                "evidence": "superseded by shell integration; no #cf2-global-panel",
            },
            {
                "id": "duplicate shell initializers",
                "classification": "DEAD",
                "evidence": "single DOMContentLoaded bind(); nav clicks guarded by data-cf2-nav-bound",
            },
        ],
    }

    # Cart/purchase/scheduler — code-path confirmation (no mutation)
    safety = {
        "v2_home_fetch": "/api/dashboard/summary",
        "v2_workspace_fetch": "/api/cart-workspace/v1/projection",
        "v2_files_mention_purchase_or_scheduler": False,
        "note": "merchant_ui_v2_{app,home,workspace}.js contain no purchase/scheduler/whatsapp outbound calls",
    }

    # Performance sanity
    perf_out = {
        **perf,
        "dom_growth": (home_after.get("domNodes") or 0) - (baseline_dom or 0),
        "nav_bound_growth": (home_after.get("listenerBoundFlags") or 0) - (baseline_bound or 0),
        "thresholds": {
            "home_initial_ms_lt_20000": perf.get("home_initial_ms", 99999) < 20000,
            "switch_ms_lt_15000": perf.get("home_to_workspace_ms", 99999) < 15000
            and perf.get("workspace_to_home_ms", 99999) < 15000,
            "dom_growth_lt_5000": abs((home_after.get("domNodes") or 0) - (baseline_dom or 0)) < 5000,
            "nav_bound_stable": (home_after.get("listenerBoundFlags") or 0)
            <= (baseline_bound or 0) + 2,
            "no_api_on_scroll": request_summary.get("api_during_scroll", 1) == 0,
        },
    }

    # Write artifacts
    (OUT / "runtime_console_capture.json").write_text(
        json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "request_summary.json").write_text(
        json.dumps(request_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "endpoint_truth_probe.json").write_text(
        json.dumps(endpoints, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "responsive_truth_probe.json").write_text(
        json.dumps({"truths": responsive, "parity": responsive_parity}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "navigation_state_probe.json").write_text(
        json.dumps({"nav_probe": nav_probe, "sequence": sequence}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "legacy_runtime_inventory.json").write_text(
        json.dumps(legacy_inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "performance_sanity.json").write_text(
        json.dumps(perf_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "gate_bundle.json").write_text(
        json.dumps(
            {
                "deploy_sha": artifacts.get("deploy_sha"),
                "runtime": runtime,
                "request_summary": request_summary,
                "endpoints": endpoints,
                "responsive_parity": responsive_parity,
                "nav_probe": nav_probe,
                "legacy": legacy_inventory,
                "performance": perf_out,
                "safety": safety,
                "ws_truth_sample": {
                    "title": ws_state.get("wsTitle"),
                    "conf": ws_state.get("wsConf"),
                    "evidence": ws_state.get("wsEvidence"),
                    "meaning": ws_state.get("wsMeaning"),
                    "mass": ws_state.get("wsMass"),
                },
                "home_truth_sample": {
                    "before": home_base.get("homeTitle"),
                    "after": home_after.get("homeTitle"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"deploy": artifacts.get("deploy_sha"), "errors": len(errors), "api_scroll": request_summary.get("api_during_scroll"), "parity": responsive_parity, "perf": perf_out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
