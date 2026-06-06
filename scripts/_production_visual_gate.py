# -*- coding: utf-8 -*-
"""Production visual proof gate — smartreplyai.net only."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_production_visual_gate_out"
GIT_HEAD = ""


def _git_short() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _ensure_vip_threshold_saved(page, out_sub: Path) -> dict[str, Any]:
    """Fresh signups show 500 as placeholder — must POST before VIP lane classifies."""
    page.goto(f"{BASE}/dashboard#vip", timeout=120000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(out_sub / "00_vip_settings_before_save.png"), full_page=False)

    page.evaluate(
        """() => {
          if (typeof window.maInitVipSettingsPage === 'function') window.maInitVipSettingsPage();
          var th = document.getElementById('ma-vip-threshold');
          if (th) th.value = '500';
          var en = document.getElementById('ma-vip-enabled');
          if (en) en.checked = true;
          var nt = document.getElementById('ma-vip-notify-enabled');
          if (nt) nt.checked = true;
        }"""
    )
    page.wait_for_timeout(800)
    page.locator("#ma-vip-settings-save").click(timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out_sub / "00_vip_settings_after_save.png"), full_page=False)

    settings = page.evaluate(
        """async () => {
          const r = await fetch('/api/recovery-settings?scope=vip&_gate=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json();
        }"""
    )
    return {
        "vip_cart_threshold": settings.get("vip_cart_threshold"),
        "vip_notify_enabled": settings.get("vip_notify_enabled"),
        "vip_enabled": settings.get("vip_enabled"),
        "save_ok": bool(settings.get("ok")),
    }


def _ensure_auth(page, report: dict) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    auth_dir = OUT / "00_auth"
    auth_dir.mkdir(parents=True, exist_ok=True)

    if email and password:
        page.goto(f"{BASE}/login", timeout=120000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(auth_dir / "login_form.png"))
        page.locator('input[name="email"], input[type="email"]').first.fill(email)
        page.locator('input[name="password"], input[type="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        report["auth"] = {"mode": "env_login", "email": email}
    else:
        uid = uuid.uuid4().hex[:10]
        email = f"cf.pvgate.{uid}@smartreplyai.net"
        password = f"CfGate!{uid[:8]}"
        page.goto(f"{BASE}/signup", timeout=120000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(auth_dir / "signup_form.png"))
        page.locator('input[name="store_name"]').fill(f"PVGate {uid[:6]}")
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["auth"] = {"mode": "signup", "email": email, "password_hint": password[:4] + "***"}

    page.screenshot(path=str(auth_dir / "after_auth.png"), full_page=False)
    if "/login" in page.url and "signup" not in page.url:
        raise RuntimeError(f"auth_failed url={page.url}")


def _widget_journey(
    page,
    *,
    product_selector: str,
    flow_label: str,
    out_sub: Path,
) -> dict[str, Any]:
    console_logs: list[dict] = []
    network: list[dict] = []
    page.on("console", lambda m: console_logs.append({"type": m.type, "text": m.text}))

    def on_resp(resp) -> None:
        url = resp.url
        if not any(
            x in url
            for x in (
                "/api/cart-event",
                "/api/cartflow/reason",
                "/api/dashboard/normal-carts",
                "/api/dashboard/vip-carts",
                "/api/dashboard/summary",
            )
        ):
            return
        t0 = time.time()
        entry: dict[str, Any] = {
            "url": url.split("?")[0],
            "status": resp.status,
            "method": resp.request.method,
            "started_at": t0,
        }
        try:
            if resp.request.post_data:
                entry["request"] = json.loads(resp.request.post_data)
        except Exception:
            pass
        try:
            if "json" in (resp.headers.get("content-type") or ""):
                entry["response"] = resp.json()
        except Exception:
            pass
        network.append(entry)

    page.on("response", on_resp)

    cart_add_mono = time.time()
    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(out_sub / "01_test_widget_store.png"), full_page=False)

    page.evaluate(
        """() => {
          try { sessionStorage.clear(); } catch(e) {}
          try { localStorage.removeItem('cartflow_customer_phone'); } catch(e) {}
        }"""
    )
    page.wait_for_timeout(500)

    page.locator(product_selector).click()
    cart_add_mono = time.time()
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out_sub / "02_after_add_cart.png"), full_page=False)

    page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
    page.evaluate("window.__cfV2ShowNow()")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(out_sub / "03_widget_yesno.png"), full_page=False)

    page.get_by_role("button", name="نعم").click(timeout=20000)
    page.wait_for_timeout(800)
    page.screenshot(path=str(out_sub / "04_after_yes.png"), full_page=False)

    page.get_by_role("button", name="السعر").click(timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(out_sub / "05_after_price.png"), full_page=False)

    page.get_by_role("button", name="شكراً").click(timeout=20000)
    page.wait_for_timeout(800)
    page.locator('input[type="tel"]').last.fill("0598877660")
    page.screenshot(path=str(out_sub / "06_phone_entered.png"), full_page=False)

    page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out_sub / "07_after_phone_save.png"), full_page=False)

    ids = page.evaluate(
        """() => ({
          session_id: sessionStorage.getItem('cartflow_recovery_session_id'),
          cart_id: sessionStorage.getItem('cartflow_cart_event_id'),
          suppress: sessionStorage.getItem('cartflow_cf_suppress_after_dismiss')
        })"""
    )

    phone_ok = next(
        (c for c in console_logs if "CF REASON_PHONE_SAVE_SUCCESS V2" in c.get("text", "")),
        None,
    )
    phone_fail = next(
        (c for c in console_logs if "CF REASON_PHONE_SAVE_FAILED V2" in c.get("text", "")),
        None,
    )

    elapsed = time.time() - cart_add_mono
    remain = max(0, 22.0 - elapsed)
    if remain > 0:
        page.wait_for_timeout(int(remain * 1000))
    page.screenshot(path=str(out_sub / "08_after_22s_widget.png"), full_page=False)

    reopened = False
    if phone_ok:
        idx = console_logs.index(phone_ok)
        for c in console_logs[idx + 1 :]:
            if "CF V2 SHOW YESNO" in c.get("text", "") or "CF WIDGET SHOW V2" in c.get("text", ""):
                reopened = True
                break

    phone_post = None
    for e in reversed(network):
        if e.get("url", "").endswith("/api/cartflow/reason") and (e.get("request") or {}).get(
            "customer_phone"
        ):
            phone_post = e
            break

    return {
        "flow": flow_label,
        "ids": ids,
        "recovery_key": f"{ids.get('session_id') and ''}"
        + (
            f"store:{ids.get('cart_id')}"
            if False
            else (f"see_cart_id:{ids.get('cart_id')}")
        ),
        "cart_add_mono": cart_add_mono,
        "phone_save_ok_console": phone_ok is not None,
        "phone_save_failed_console": phone_fail is not None,
        "phone_post": phone_post,
        "widget_reopened": reopened,
        "suppress_after_close": ids.get("suppress"),
        "console_tail": [
            c
            for c in console_logs
            if "CF " in c.get("text", "")
        ][-40:],
        "network": network,
    }


def _dashboard_probe(page, *, cart_id: str, flow: str, out_sub: Path) -> dict[str, Any]:
    t_nav = time.time()
    if flow == "vip":
        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
    else:
        page.goto(f"{BASE}/dashboard#carts?tab=all", timeout=120000)

    nc_events: list[dict] = []
    timings: list[dict] = []

    def capture_nc(resp) -> None:
        if "/api/dashboard/normal-carts" not in resp.url:
            return
        t_end = time.time()
        body = {}
        try:
            body = resp.json()
        except Exception:
            pass
        nc_events.append(
            {
                "status": resp.status,
                "duration_ms": round((t_end - t_nav) * 1000, 1),
                "dashboard_partial": body.get("dashboard_partial"),
                "dashboard_timeout": body.get("dashboard_timeout"),
                "dashboard_timeout_stage": body.get("dashboard_timeout_stage"),
                "dashboard_wall_budget_s": body.get("dashboard_wall_budget_s"),
                "row_count": len(body.get("merchant_carts_page_rows") or []),
                "filter_all": (body.get("merchant_cart_filter_counts") or {}).get("all"),
            }
        )

    page.on("response", capture_nc)
    page.wait_for_timeout(15000)
    page.screenshot(path=str(out_sub / "09_dashboard.png"), full_page=True)

    # isolated normal-carts timing (performance audit)
    iso = page.evaluate(
        """async () => {
          const t0 = performance.now();
          const r = await fetch('/api/dashboard/normal-carts?_iso=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          const t1 = performance.now();
          const j = await r.json();
          return {
            client_duration_ms: Math.round(t1 - t0),
            dashboard_partial: j.dashboard_partial,
            dashboard_timeout: j.dashboard_timeout,
            dashboard_timeout_stage: j.dashboard_timeout_stage,
            dashboard_wall_budget_s: j.dashboard_wall_budget_s,
            row_count: (j.merchant_carts_page_rows || []).length,
            filter_all: (j.merchant_cart_filter_counts || {}).all
          };
        }"""
    )
    timings.append({"label": "isolated_normal_carts_fetch", **iso})

    vip_payload = page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/vip-carts?_iso=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json();
        }"""
    )
    summary_payload = page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/summary?_iso=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json();
        }"""
    )

    table_rows = page.evaluate(
        """() => {
          if (location.hash.indexOf('vip') >= 0) {
            return document.querySelectorAll('#ma-vip-tbody tr, #ma-tbody-vip-carts tr').length;
          }
          var tb = document.querySelector('#ma-tbody-all-carts');
          return tb ? tb.querySelectorAll('tr[data-ma-filter]').length : 0;
        }"""
    )

    normal_rows = page.evaluate(
        """async (cid) => {
          const r = await fetch('/api/dashboard/normal-carts?_iso2=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          const j = await r.json();
          const rows = j.merchant_carts_page_rows || [];
          return rows.find(x => x.cart_id === cid) || null;
        }""",
        cart_id,
    )

    vip_row = None
    for r in vip_payload.get("merchant_vip_page_rows") or []:
        blob = json.dumps(r, default=str)
        if cart_id and (cart_id in blob or (cart_id.split("_")[-1] in blob)):
            vip_row = r
            break
    if vip_row is None and isinstance(normal_rows, dict):
        ac_id = normal_rows.get("merchant_case_row_id")
        if ac_id:
            for r in vip_payload.get("merchant_vip_page_rows") or []:
                if int(r.get("id") or 0) == int(ac_id):
                    vip_row = r
                    break

    recovery_settings = page.evaluate(
        """async () => {
          const r = await fetch('/api/recovery-settings?scope=vip&_dash=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          return await r.json();
        }"""
    )

    time_to_visible_ms = None
    false_empty_seen = False
    for wait in range(200):
        snap = page.evaluate(
            """() => {
              var tb = document.querySelector('#ma-tbody-all-carts');
              if (!tb) return { rows: 0, falseEmpty: false, loading: false };
              var dataRows = tb.querySelectorAll('tr[data-ma-filter]').length;
              var text = tb.innerText || '';
              var falseEmpty = text.indexOf('لا توجد سلال متروكة') >= 0 && dataRows === 0;
              var loading = !!tb.querySelector('[data-ma-carts-loading]');
              return { rows: dataRows, falseEmpty: falseEmpty, loading: loading };
            }"""
        )
        if snap.get("falseEmpty"):
            false_empty_seen = True
        if flow != "vip" and cart_id:
            has_cid = page.evaluate(
                """(cid) => {
                  var tb = document.querySelector('#ma-tbody-all-carts');
                  if (!tb) return 0;
                  return (tb.innerHTML || '').indexOf(cid) >= 0 ? 1 : 0;
                }""",
                cart_id,
            )
            if has_cid:
                time_to_visible_ms = round((time.time() - t_nav) * 1000, 1)
                break
        if flow == "vip":
            n2 = page.evaluate(
                """() => {
                  var tb = document.querySelector('#ma-vip-tbody, #ma-tbody-vip-carts');
                  if (!tb) return document.body.innerText.indexOf('966') >= 0 ? 1 : 0;
                  return (tb.innerText || '').length > 20 ? 1 : 0;
                }"""
            )
            if n2:
                time_to_visible_ms = round((time.time() - t_nav) * 1000, 1)
                break
        if flow != "vip" and not cart_id and int(snap.get("rows") or 0) > 0:
            time_to_visible_ms = round((time.time() - t_nav) * 1000, 1)
            break
        page.wait_for_timeout(100)

    page.screenshot(path=str(out_sub / "10_dashboard_final.png"), full_page=True)

    return {
        "flow": flow,
        "cart_id": cart_id,
        "time_to_visible_ms": time_to_visible_ms,
        "normal_carts_boot_events": nc_events,
        "isolated_fetch": iso,
        "table_rows_dom": table_rows,
        "vip_row": vip_row,
        "normal_row": normal_rows,
        "summary_notification": {
            "merchant_nav_badge_vip": summary_payload.get("merchant_nav_badge_vip"),
            "merchant_nav_badge_abandoned": summary_payload.get("merchant_nav_badge_abandoned"),
            "merchant_nav_badge_followup": summary_payload.get("merchant_nav_badge_followup"),
        },
        "vip_payload_count": len(vip_payload.get("merchant_vip_page_rows") or []),
        "vip_alert_state_ar": vip_payload.get("merchant_vip_alert_state_ar"),
        "vip_threshold_configured": vip_payload.get("merchant_vip_threshold_configured"),
        "vip_notify_path": {
            "vip_notify_enabled": recovery_settings.get("vip_notify_enabled"),
            "vip_cart_threshold": recovery_settings.get("vip_cart_threshold"),
            "merchant_nav_badge_vip": summary_payload.get("merchant_nav_badge_vip"),
            "vip_alert_state_ar": vip_payload.get("merchant_vip_alert_state_ar"),
        },
        "false_empty_state_seen": false_empty_seen,
    }


def _dashboard_stability_three_loads(page, out_sub: Path) -> dict[str, Any]:
    """Load #carts?tab=all three times; require rows + count parity each time."""
    runs: list[dict[str, Any]] = []
    for i in range(3):
        t0 = time.time()
        page.goto(f"{BASE}/dashboard#carts?tab=all", timeout=120000)
        visible_ms = None
        false_empty = False
        partial_empty_overwrite = False
        row_count = 0
        filter_all = None
        for _ in range(200):
            snap = page.evaluate(
                """async () => {
                  var tb = document.querySelector('#ma-tbody-all-carts');
                  var domRows = tb ? tb.querySelectorAll('tr[data-ma-filter]').length : 0;
                  var text = tb ? (tb.innerText || '') : '';
                  var falseEmpty = text.indexOf('لا توجد سلال متروكة') >= 0 && domRows === 0;
                  var filt = document.getElementById('ma-filt-all');
                  var filterAll = filt ? parseInt(filt.textContent || '0', 10) : null;
                  return { domRows: domRows, falseEmpty: falseEmpty, filterAll: filterAll };
                }"""
            )
            if snap.get("falseEmpty"):
                false_empty = True
            row_count = int(snap.get("domRows") or 0)
            filter_all = snap.get("filterAll")
            if row_count > 0:
                visible_ms = round((time.time() - t0) * 1000, 1)
                break
            page.wait_for_timeout(100)
        page.screenshot(path=str(out_sub / f"stability_load_{i + 1}.png"), full_page=True)
        iso = page.evaluate(
            """async () => {
              const t0 = performance.now();
              const r = await fetch('/api/dashboard/normal-carts?_stab=' + Date.now(), {
                credentials: 'same-origin', cache: 'no-store'
              });
              const t1 = performance.now();
              const j = await r.json();
              return {
                client_duration_ms: Math.round(t1 - t0),
                dashboard_partial: j.dashboard_partial,
                row_count: (j.merchant_carts_page_rows || []).length,
                filter_all: (j.merchant_cart_filter_counts || {}).all,
              };
            }"""
        )
        if iso.get("dashboard_partial") and not iso.get("row_count"):
            partial_empty_overwrite = True
        count_match = (
            filter_all is not None
            and row_count > 0
            and int(filter_all) == int(row_count)
        )
        runs.append(
            {
                "run": i + 1,
                "time_to_visible_ms": visible_ms,
                "dom_rows": row_count,
                "filter_all": filter_all,
                "count_match": count_match,
                "false_empty": false_empty,
                "partial_empty_overwrite": partial_empty_overwrite,
                "isolated_fetch": iso,
            }
        )
        page.wait_for_timeout(800)
    return {"runs": runs, "all_pass": all(
        r.get("time_to_visible_ms") is not None
        and r.get("dom_rows", 0) > 0
        and r.get("count_match")
        and not r.get("false_empty")
        and not r.get("partial_empty_overwrite")
        for r in runs
    )}


def _wait_cart_visible_in_dashboard(
    page, *, cart_id: str, t0: float, out_path: Path
) -> dict[str, Any]:
    api_has = False
    dom_has = False
    false_empty = False
    visible_ms = None
    last_api_rows = 0
    for _ in range(300):
        snap = page.evaluate(
            """(cid) => {
              var tb = document.querySelector('#ma-tbody-all-carts');
              var domHas = false;
              if (tb && cid) domHas = (tb.innerHTML || '').indexOf(cid) >= 0;
              var domRows = tb ? tb.querySelectorAll('tr[data-ma-filter]').length : 0;
              var text = tb ? (tb.innerText || '') : '';
              var falseEmpty = text.indexOf('لا توجد سلال متروكة') >= 0 && domRows === 0;
              return { domHas: domHas, domRows: domRows, falseEmpty: falseEmpty };
            }""",
            cart_id,
        )
        if snap.get("falseEmpty"):
            false_empty = True
        if snap.get("domHas"):
            dom_has = True
            visible_ms = round((time.time() - t0) * 1000, 1)
            break
        page.wait_for_timeout(100)
    iso = page.evaluate(
        """async (cid) => {
          try {
            const r = await fetch('/api/dashboard/normal-carts?_nc=' + Date.now(), {
              credentials: 'same-origin', cache: 'no-store'
            });
            const text = await r.text();
            var j = {};
            try { j = JSON.parse(text); } catch (pe) {
              return { api_has: false, row_count: 0, filter_all: null, dashboard_partial: null, api_error: 'json_parse' };
            }
            const rows = j.merchant_carts_page_rows || [];
            const has = rows.some(x => x.cart_id === cid);
            return {
              api_has: has,
              row_count: rows.length,
              filter_all: (j.merchant_cart_filter_counts || {}).all,
              dashboard_partial: j.dashboard_partial,
              api_error: null,
            };
          } catch (e) {
            return { api_has: false, row_count: 0, filter_all: null, dashboard_partial: null, api_error: String(e) };
          }
        }""",
        cart_id,
    )
    api_has = bool(iso.get("api_has"))
    last_api_rows = int(iso.get("row_count") or 0)
    page.screenshot(path=str(out_path), full_page=True)
    return {
        "cart_id": cart_id,
        "time_to_visible_ms": visible_ms,
        "api_has_row": api_has,
        "dom_has_row": dom_has,
        "false_empty": false_empty,
        "api_row_count": last_api_rows,
        "filter_all": iso.get("filter_all"),
        "dashboard_partial": iso.get("dashboard_partial"),
        "pass": dom_has and api_has and not false_empty,
    }


def _three_new_carts_visibility(page, out_sub: Path) -> dict[str, Any]:
    products = (
        "#p-perfume_velvet .add-btn",
        "#p-perfume .add-btn",
        "#p-hoodie_essentials .add-btn",
    )
    runs: list[dict[str, Any]] = []
    for i, sel in enumerate(products):
        sub = out_sub / f"new_cart_{i + 1}"
        sub.mkdir(parents=True, exist_ok=True)
        page.evaluate(
            """() => {
              try { sessionStorage.removeItem('cartflow_cf_suppress_after_dismiss'); } catch(e) {}
            }"""
        )
        j = _widget_journey(
            page,
            product_selector=sel,
            flow_label=f"new_cart_{i + 1}",
            out_sub=sub,
        )
        cart_id = (j.get("ids") or {}).get("cart_id") or ""
        phone_post = j.get("phone_post") or {}
        req = phone_post.get("request") or {}
        if not cart_id and req.get("cart_id"):
            cart_id = str(req.get("cart_id"))
        t0 = time.time()
        page.goto(f"{BASE}/dashboard#carts?tab=all", timeout=120000)
        page.wait_for_timeout(1500)
        probe = _wait_cart_visible_in_dashboard(
            page,
            cart_id=cart_id,
            t0=t0,
            out_path=sub / "dashboard_visible.png",
        )
        probe["run"] = i + 1
        probe["product_selector"] = sel
        runs.append(probe)
        page.wait_for_timeout(500)
    return {
        "runs": runs,
        "all_pass": all(r.get("pass") for r in runs),
        "max_visible_ms": max((r.get("time_to_visible_ms") or 999999) for r in runs),
    }


def main() -> int:
    global GIT_HEAD
    GIT_HEAD = _git_short()
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "git_head": GIT_HEAD,
        "deploy_markers": {},
        "vip": {},
        "normal": {},
        "performance": {},
        "acceptance": {},
    }

    import urllib.request

    for name, path in (
        ("fetch.js", "/static/cartflow_widget_runtime/cartflow_widget_fetch.js"),
        ("flows.js", "/static/cartflow_widget_runtime/cartflow_widget_flows.js"),
        ("dashboard_lazy.js", "/static/merchant_dashboard_lazy.js"),
    ):
        body = urllib.request.urlopen(BASE + path, timeout=30).read().decode("utf-8", errors="replace")
        markers = {
            "bytes": len(body),
            "price_fallback": "applyLegacyPriceSubCategoryDefault" in body,
            "recovery_close": "CF RECOVERY FLOW COMPLETE CLOSE" in body,
            "partial_retry": "normal_carts_partial_retry" in body,
        }
        if name == "dashboard_lazy.js":
            markers["boot_priority"] = "boot_priority" in body
            markers["stale_skip"] = "normal_carts_stale_skip" in body
            markers["row_retention"] = "normal_carts_partial_empty" in body
            markers["applied_gen"] = "normalCartsAppliedGen" in body
            markers["cache_hydrate"] = "hydrateNormalCartsCache" in body
            markers["pending_cart_poll"] = "pending_cart_poll" in body
        report["deploy_markers"][name] = markers

    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        _ensure_auth(page, report)

        reliability_only = (os.environ.get("CARTFLOW_RELIABILITY_ONLY") or "").strip() in (
            "1",
            "true",
            "yes",
        )

        stab_dir = OUT / "stability"
        stab_dir.mkdir(parents=True, exist_ok=True)
        new_dir = OUT / "new_carts"
        new_dir.mkdir(parents=True, exist_ok=True)

        if not reliability_only:
            vip_dir = OUT / "vip_flow"
            vip_dir.mkdir(parents=True, exist_ok=True)
            vip_settings = _ensure_vip_threshold_saved(page, vip_dir)
            report["vip_settings_saved"] = vip_settings
            if not vip_settings.get("save_ok") or not vip_settings.get("vip_cart_threshold"):
                failures.append("vip_threshold_not_saved")

            vip_j = _widget_journey(
                page,
                product_selector="#p-watch_pro .add-btn",
                flow_label="vip",
                out_sub=vip_dir,
            )
            cart_id_vip = (vip_j.get("ids") or {}).get("cart_id")
            vip_dash = _dashboard_probe(page, cart_id=cart_id_vip or "", flow="vip", out_sub=vip_dir)
            report["vip"] = {**vip_j, "dashboard": vip_dash}

            normal_dir = OUT / "normal_flow"
            normal_dir.mkdir(parents=True, exist_ok=True)
            page.evaluate("sessionStorage.clear()")
            normal_j = _widget_journey(
                page,
                product_selector="#p-perfume_velvet .add-btn",
                flow_label="normal",
                out_sub=normal_dir,
            )
            if page.locator("#p-perfume_velvet .add-btn").count() == 0:
                normal_j = _widget_journey(
                    page,
                    product_selector=".add-btn",
                    flow_label="normal_fallback_cheapest",
                    out_sub=normal_dir,
                )
            cart_id_norm = (normal_j.get("ids") or {}).get("cart_id")
            normal_dash = _dashboard_probe(
                page, cart_id=cart_id_norm or "", flow="normal", out_sub=normal_dir
            )
            report["normal"] = {**normal_j, "dashboard": normal_dash}

        report["stability"] = _dashboard_stability_three_loads(page, stab_dir)
        report["stability"]["before_baseline_ms"] = 39038
        report["new_carts_three"] = _three_new_carts_visibility(page, new_dir)

        browser.close()

    # Acceptance checks
    lazy_m = report["deploy_markers"].get("dashboard_lazy.js") or {}
    if not lazy_m.get("boot_priority"):
        failures.append("deploy_missing_dashboard_boot_priority")
    if not lazy_m.get("applied_gen"):
        failures.append("deploy_missing_applied_gen_guard")
    if not report["deploy_markers"].get("fetch.js", {}).get("price_fallback"):
        failures.append("deploy_missing_price_fallback")
    vip_phone = (report["vip"].get("phone_post") or {}).get("status") == 200
    if not vip_phone:
        failures.append("vip_phone_post_not_200")
    if report["vip"].get("widget_reopened"):
        failures.append("vip_widget_reopened")
    vip_row = (report["vip"].get("dashboard") or {}).get("vip_row") or {}
    if not vip_row.get("has_phone"):
        failures.append("vip_row_missing_has_phone")
    if not vip_row.get("manual_contact_available"):
        failures.append("vip_manual_contact_unavailable")

    norm_iso = (report["normal"].get("dashboard") or {}).get("isolated_fetch") or {}
    if norm_iso.get("dashboard_partial"):
        failures.append("normal_isolated_partial")
    if norm_iso.get("dashboard_timeout_stage") == "payload_row":
        failures.append("normal_payload_row_timeout")
    filt = norm_iso.get("filter_all")
    dom = (report["normal"].get("dashboard") or {}).get("table_rows_dom")
    if filt is not None and dom is not None and int(filt) != int(dom):
        failures.append(f"normal_count_mismatch filter={filt} dom={dom}")
    norm_dash = (report["normal"].get("dashboard") or {})
    if norm_dash.get("false_empty_state_seen"):
        failures.append("normal_false_empty_state_during_load")
    stab = report.get("stability") or {}
    if not stab.get("all_pass"):
        failures.append("stability_three_loads_failed")
    stab_runs = stab.get("runs") or []
    if stab_runs:
        max_vis = max((r.get("time_to_visible_ms") or 0) for r in stab_runs)
        if max_vis >= 39038:
            failures.append(f"stability_visibility_not_improved max_ms={max_vis}")

    new3 = report.get("new_carts_three") or {}
    if not new3.get("all_pass"):
        failures.append("new_carts_three_visibility_failed")
    norm_vis = (report["normal"].get("dashboard") or {}).get("time_to_visible_ms")
    if norm_vis is not None and float(norm_vis) > 45000:
        failures.append(f"normal_cart_visible_too_slow ms={norm_vis}")
    if new3.get("max_visible_ms", 0) > 45000:
        failures.append(f"new_cart_max_visible_too_slow ms={new3.get('max_visible_ms')}")

    vip_iso = (report["vip"].get("dashboard") or {}).get("isolated_fetch") or {}
    norm_boot = (report["normal"].get("dashboard") or {}).get("normal_carts_boot_events") or []
    first_boot = norm_boot[0] if norm_boot else {}
    report["performance"] = {
        "vip_isolated_normal_carts_ms": vip_iso.get("client_duration_ms"),
        "normal_isolated_fetch_ms": norm_iso.get("client_duration_ms"),
        "normal_first_boot_fetch_ms": first_boot.get("duration_ms"),
        "normal_time_to_visible_ms": (report["normal"].get("dashboard") or {}).get(
            "time_to_visible_ms"
        ),
        "normal_boot_events": norm_boot,
        "stage_measurement_note": (
            "candidates_loaded / payload_row / batch_reads are server-side "
            "[DASHBOARD STAGE] spans — not returned in production JSON. "
            "Client total API duration is the measurable production truth."
        ),
        "bottleneck_inference": {
            "total_api_ms_isolated": norm_iso.get("client_duration_ms"),
            "dashboard_partial": norm_iso.get("dashboard_partial"),
            "dashboard_timeout_stage": norm_iso.get("dashboard_timeout_stage"),
            "wall_budget_s": norm_iso.get("dashboard_wall_budget_s"),
            "dominant_cost": (
                "payload_row + batch_reads (inferred from code path and "
                f"~{norm_iso.get('client_duration_ms')}ms isolated wall time; "
                "no payload_row timeout on isolated fetch)"
            ),
            "visibility_delay_ms": (report["normal"].get("dashboard") or {}).get(
                "time_to_visible_ms"
            ),
            "visibility_note": (
                "DOM visibility can lag isolated API if lazy dashboard boot "
                "defers table paint until concurrent fetches settle."
            ),
        },
    }

    report["acceptance"] = {"pass": len(failures) == 0, "failures": failures}
    out_json = OUT / "production_visual_gate_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"pass": report["acceptance"]["pass"], "failures": failures, "report": str(out_json)}, indent=2))
    return 0 if report["acceptance"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
