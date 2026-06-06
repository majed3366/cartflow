# -*- coding: utf-8 -*-
"""Production audit: VIP rows visible → refresh → empty. Read-only, no fixes."""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_vip_disappearing_rows_audit_out"

VIP_FETCH_HOOK = """
(() => {
  if (window.__vipAuditInstalled) return;
  window.__vipAuditInstalled = true;
  window.__vipAuditLog = window.__vipAuditLog || [];

  function vipDomSnapshot(label) {
    var tb = document.getElementById("ma-tbody-vip-page");
    var text = tb ? (tb.innerText || "") : "";
    return {
      kind: "dom",
      label: label,
      ts: Date.now(),
      data_rows: tb ? tb.querySelectorAll("tr").length : 0,
      data_row_filtered: tb
        ? tb.querySelectorAll("tr:not(.ma-dash-skel-row)").length
        : 0,
      has_skel: tb ? !!tb.querySelector(".ma-dash-skel-row") : false,
      empty_vip_text: text.indexOf("لا توجد سلال VIP") >= 0,
      error_text: text.indexOf("تعذر تحميل") >= 0,
      html_len: tb ? (tb.innerHTML || "").length : 0,
    };
  }

  window.__vipAuditSnapshot = vipDomSnapshot;

  var tb = document.getElementById("ma-tbody-vip-page");
  if (tb && window.MutationObserver) {
    var mo = new MutationObserver(function () {
      window.__vipAuditLog.push(vipDomSnapshot("mutation"));
    });
    mo.observe(tb, { childList: true, subtree: true, characterData: true });
  }

  var orig = window.fetch;
  window.fetch = function () {
    var url = String(arguments[0] || "");
    if (url.indexOf("/api/dashboard/vip-carts") < 0) {
      return orig.apply(this, arguments);
    }
    var t0 = performance.now();
    window.__vipAuditLog.push({
      kind: "vip_fetch_start",
      url: url.split("?")[0],
      ts: Date.now(),
      t0: t0,
    });
    return orig.apply(this, arguments).then(function (resp) {
      var clone = resp.clone();
      return clone
        .text()
        .then(function (raw) {
          var parsed = null;
          var parse_err = null;
          try {
            parsed = JSON.parse(raw);
          } catch (e) {
            parse_err = String(e);
          }
          window.__vipAuditLog.push({
            kind: "vip_fetch_done",
            ts: Date.now(),
            duration_ms: Math.round(performance.now() - t0),
            status: resp.status,
            raw_len: raw.length,
            parse_err: parse_err,
            ok: parsed && parsed.ok,
            row_count: parsed
              ? (parsed.merchant_vip_page_rows || []).length
              : null,
            nav_badge: parsed ? parsed.merchant_nav_badge_vip : null,
            threshold_configured: parsed
              ? parsed.merchant_vip_threshold_configured
              : null,
            alert_state_ar: parsed ? parsed.merchant_vip_alert_state_ar : null,
            payload: parsed,
          });
          window.__vipAuditLog.push(vipDomSnapshot("after_vip_fetch_done"));
          return resp;
        })
        .catch(function (err) {
          window.__vipAuditLog.push({
            kind: "vip_fetch_error",
            ts: Date.now(),
            error: String(err),
          });
          throw err;
        });
    });
  };
})();
"""


def _auth(page, report: dict) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        report["auth"] = {"mode": "login", "email": email}
        return

    uid = uuid.uuid4().hex[:10]
    email = f"cf.vip.audit.{uid}@smartreplyai.net"
    password = f"CfVipAudit!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.locator('input[name="store_name"]').fill(f"VipAudit {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email}


def _save_vip_threshold(page) -> None:
    page.goto(f"{BASE}/dashboard#vip", timeout=120000)
    page.wait_for_timeout(2500)
    page.evaluate(
        """() => {
          if (typeof window.maInitVipSettingsPage === 'function') window.maInitVipSettingsPage();
          var th = document.getElementById('ma-vip-threshold');
          if (th) th.value = '500';
          var en = document.getElementById('ma-vip-enabled');
          if (en) en.checked = true;
        }"""
    )
    page.locator("#ma-vip-settings-save").click(timeout=20000)
    page.wait_for_timeout(2000)


def _create_vip_cart(page, out_sub: Path) -> str | None:
    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(4000)
    page.locator("#p-watch_pro .add-btn").click()
    page.wait_for_timeout(2000)
    page.evaluate("window.__cfV2ShowNow && window.__cfV2ShowNow()")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="نعم").click(timeout=20000)
    page.get_by_role("button", name="السعر").click(timeout=20000)
    page.get_by_role("button", name="شكراً").click(timeout=20000)
    page.locator('input[type="tel"]').last.fill("0598877660")
    page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out_sub / "after_vip_cart_widget.png"))
    cart_id = page.evaluate(
        """() => sessionStorage.getItem('cartflow_cart_event_id')"""
    )
    return str(cart_id) if cart_id else None


def _wait_vip_data_rows(page, *, timeout_s: float = 90) -> dict[str, Any]:
    t0 = time.time()
    last: dict[str, Any] = {}
    while (time.time() - t0) < timeout_s:
        snap = page.evaluate(
            """() => {
              var tb = document.getElementById('ma-tbody-vip-page');
              if (!tb) return { rows: 0, empty: false, skel: false };
              var rows = tb.querySelectorAll('tr:not(.ma-dash-skel-row)').length;
              var text = tb.innerText || '';
              var empty = text.indexOf('لا توجد سلال VIP') >= 0 && rows <= 1;
              var skel = !!tb.querySelector('.ma-dash-skel-row');
              var hasAmount = /\\d+\\s*ريال/.test(text);
              return { rows: rows, empty: empty, skel: skel, has_amount: hasAmount, text_sample: text.slice(0, 200) };
            }"""
        )
        last = snap
        if int(snap.get("rows") or 0) >= 1 and snap.get("has_amount"):
            last["visible_ms"] = round((time.time() - t0) * 1000, 1)
            return last
        page.wait_for_timeout(200)
    last["visible_ms"] = None
    last["timeout"] = True
    return last


def _collect_vip_api_responses(page) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    def on_resp(resp) -> None:
        if "/api/dashboard/vip-carts" not in resp.url:
            return
        entry: dict[str, Any] = {
            "wall_ms": round(time.time() * 1000),
            "url": resp.url,
            "status": resp.status,
        }
        try:
            body = resp.json()
            entry["ok"] = body.get("ok")
            entry["row_count"] = len(body.get("merchant_vip_page_rows") or [])
            entry["nav_badge"] = body.get("merchant_nav_badge_vip")
            entry["threshold_configured"] = body.get("merchant_vip_threshold_configured")
            entry["alert_state_ar"] = body.get("merchant_vip_alert_state_ar")
            entry["dashboard_partial"] = body.get("dashboard_partial")
            entry["dashboard_timeout"] = body.get("dashboard_timeout")
            entry["payload"] = body
        except Exception as exc:  # noqa: BLE001
            entry["parse_error"] = str(exc)
        events.append(entry)

    page.on("response", on_resp)
    return events


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "phase": {},
        "network_vip_responses": [],
        "client_audit_log": [],
        "root_cause": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.add_init_script(VIP_FETCH_HOOK)

        _auth(page, report)
        setup_dir = OUT / "setup"
        setup_dir.mkdir(parents=True, exist_ok=True)
        _save_vip_threshold(page)
        cart_id = _create_vip_cart(page, setup_dir)

        vip_events: list[dict[str, Any]] = []
        page.on("response", lambda r: vip_events.append(r) if False else None)
        net: list[dict[str, Any]] = []

        def capture(resp) -> None:
            if "/api/dashboard/vip-carts" not in resp.url:
                return
            e: dict[str, Any] = {"ts": time.time(), "status": resp.status, "url": resp.url}
            try:
                b = resp.json()
                e.update(
                    {
                        "ok": b.get("ok"),
                        "row_count": len(b.get("merchant_vip_page_rows") or []),
                        "nav_badge": b.get("merchant_nav_badge_vip"),
                        "threshold_configured": b.get("merchant_vip_threshold_configured"),
                        "alert_state_ar": b.get("merchant_vip_alert_state_ar"),
                        "dashboard_partial": b.get("dashboard_partial"),
                        "payload": b,
                    }
                )
            except Exception as ex:  # noqa: BLE001
                e["parse_error"] = str(ex)
            net.append(e)

        page.on("response", capture)

        page.goto(f"{BASE}/dashboard#vip", timeout=120000)
        before = _wait_vip_data_rows(page, timeout_s=120)
        page.screenshot(path=str(OUT / "01_before_refresh_rows_visible.png"), full_page=True)
        page.evaluate("window.__vipAuditSnapshot && window.__vipAuditSnapshot('before_refresh')")

        iso_before = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/vip-carts?_audit_before=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' });
              const t = await r.text();
              let j = null; try { j = JSON.parse(t); } catch(e) { return { parse_error: true, raw: t.slice(0, 500) }; }
              return {
                row_count: (j.merchant_vip_page_rows || []).length,
                ok: j.ok,
                threshold_configured: j.merchant_vip_threshold_configured,
                alert_state_ar: j.merchant_vip_alert_state_ar,
                rows: j.merchant_vip_page_rows
              };
            }"""
        )

        report["phase"]["before_refresh"] = {
            "cart_id": cart_id,
            "dom": before,
            "isolated_api": iso_before,
            "vip_fetches_so_far": list(net),
        }

        # --- REFRESH ---
        net.clear()
        page.evaluate("window.__vipAuditLog = []")
        t_reload = time.time()
        page.reload(timeout=120000)
        reload_ms = round((time.time() - t_reload) * 1000, 1)

        timeline: list[dict[str, Any]] = []
        empty_seen_at: float | None = None
        rows_seen_at: float | None = None
        for i in range(150):
            snap = page.evaluate(
                """() => {
                  var tb = document.getElementById('ma-tbody-vip-page');
                  var text = tb ? (tb.innerText || '') : '';
                  return {
                    ms_since_reload: Math.round(performance.now()),
                    rows: tb ? tb.querySelectorAll('tr:not(.ma-dash-skel-row)').length : 0,
                    skel: tb ? !!tb.querySelector('.ma-dash-skel-row') : false,
                    empty_vip: text.indexOf('لا توجد سلال VIP') >= 0,
                    error: text.indexOf('تعذر تحميل') >= 0,
                    has_amount: /\\d+\\s*ريال/.test(text)
                  };
                }"""
            )
            snap["poll_i"] = i
            snap["elapsed_ms"] = round((time.time() - t_reload) * 1000, 1)
            timeline.append(snap)
            if empty_seen_at is None and snap.get("empty_vip") and not snap.get("has_amount"):
                empty_seen_at = snap["elapsed_ms"]
            if rows_seen_at is None and snap.get("has_amount") and int(snap.get("rows") or 0) >= 1:
                rows_seen_at = snap["elapsed_ms"]
            page.wait_for_timeout(100)

        page.screenshot(path=str(OUT / "02_after_refresh_final.png"), full_page=True)

        client_log = page.evaluate("() => window.__vipAuditLog || []")
        iso_after = page.evaluate(
            """async () => {
              const r = await fetch('/api/dashboard/vip-carts?_audit_after=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' });
              const t = await r.text();
              let j = null; try { j = JSON.parse(t); } catch(e) { return { parse_error: true, raw: t.slice(0, 500) }; }
              return {
                row_count: (j.merchant_vip_page_rows || []).length,
                ok: j.ok,
                threshold_configured: j.merchant_vip_threshold_configured,
                alert_state_ar: j.merchant_vip_alert_state_ar,
                dashboard_partial: j.dashboard_partial,
                rows: j.merchant_vip_page_rows
              };
            }"""
        )

        report["phase"]["after_refresh"] = {
            "reload_ms": reload_ms,
            "dom_timeline": timeline,
            "empty_seen_at_ms": empty_seen_at,
            "rows_seen_at_ms": rows_seen_at,
            "isolated_api": iso_after,
            "vip_fetches_on_reload": list(net),
            "client_hook_log": client_log,
        }

        # Second refresh if first ended empty — capture intermittent return
        if empty_seen_at is not None and rows_seen_at is None:
            net2: list[dict[str, Any]] = []

            def capture2(resp) -> None:
                if "/api/dashboard/vip-carts" not in resp.url:
                    return
                e = {"ts": time.time(), "status": resp.status}
                try:
                    b = resp.json()
                    e["row_count"] = len(b.get("merchant_vip_page_rows") or [])
                    e["payload"] = b
                except Exception as ex:  # noqa: BLE001
                    e["parse_error"] = str(ex)
                net2.append(e)

            page.on("response", capture2)
            page.reload(timeout=120000)
            page.wait_for_timeout(15000)
            page.screenshot(path=str(OUT / "03_second_refresh.png"), full_page=True)
            report["phase"]["second_refresh"] = {
                "vip_fetches": net2,
                "dom": page.evaluate(
                    """() => {
                      var tb = document.getElementById('ma-tbody-vip-page');
                      var text = tb ? tb.innerText : '';
                      return {
                        rows: tb ? tb.querySelectorAll('tr:not(.ma-dash-skel-row)').length : 0,
                        empty_vip: text.indexOf('لا توجد سلال VIP') >= 0,
                        has_amount: /\\d+\\s*ريال/.test(text)
                      };
                    }"""
                ),
            }

        browser.close()

    # Root-cause inference (read-only analysis)
    after = report["phase"].get("after_refresh") or {}
    fetches = after.get("vip_fetches_on_reload") or []
    hook = after.get("client_hook_log") or []
    empty_at = after.get("empty_seen_at_ms")
    rows_at = after.get("rows_seen_at_ms")
    iso = after.get("isolated_api") or {}

    first_fetch = next((x for x in fetches if "row_count" in x), None)
    first_hook_done = next((x for x in hook if x.get("kind") == "vip_fetch_done"), None)

    cause = {
        "file": "static/merchant_dashboard_lazy.js",
        "function": "applyVipCarts",
        "clear_lines": "2858-2863 (tb.innerHTML = vipPageEmptyHtml() when merchant_vip_page_rows.length === 0)",
        "failed_lines": "2832-2834 (applyVipCartsFailed when !d.ok)",
    }

    if first_fetch and first_fetch.get("row_count", 0) == 0 and first_fetch.get("ok"):
        cause["category"] = "api_returned_ok_empty_rows"
        cause["api_evidence"] = {
            "row_count": 0,
            "threshold_configured": first_fetch.get("threshold_configured"),
            "alert_state_ar": first_fetch.get("alert_state_ar"),
        }
    elif first_fetch and first_fetch.get("row_count", 0) > 0 and empty_at is not None:
        cause["category"] = "api_had_rows_dom_still_empty_timing_or_render"
    elif first_fetch and not first_fetch.get("ok"):
        cause["category"] = "api_ok_false_applyVipCartsFailed"
    elif len(fetches) >= 2:
        cause["category"] = "multiple_vip_fetches_possible_overwrite"
        cause["fetch_sequence"] = [
            {"row_count": x.get("row_count"), "ok": x.get("ok")} for x in fetches
        ]
    else:
        cause["category"] = "deferred_vip_fetch_after_normal_carts_boot"

    cause["disappearance_timing"] = {
        "empty_dom_ms": empty_at,
        "rows_dom_ms": rows_at,
        "isolated_api_row_count_after": iso.get("row_count"),
    }
    if first_hook_done:
        cause["first_vip_fetch_hook"] = {
            k: first_hook_done.get(k)
            for k in (
                "duration_ms",
                "status",
                "row_count",
                "ok",
                "threshold_configured",
                "alert_state_ar",
            )
        }

    report["root_cause"] = cause
    out_json = OUT / "vip_disappearing_rows_audit.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(out_json), "root_cause": cause}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
