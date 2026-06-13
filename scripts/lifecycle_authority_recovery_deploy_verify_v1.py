# -*- coding: utf-8 -*-
"""Post-deploy verification: Lifecycle Authority Recovery v1 on production."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import urllib.request
from playwright.sync_api import Page, sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_lifecycle_authority_recovery_deploy_verify_v1_out"
COMMIT_EXPECTED = ""  # filled after commit


def _auth(page: Page, report: dict[str, Any]) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.locator('input[name="email"]').fill(email, timeout=60000)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        report["auth"] = {"mode": "login", "email": email}
        return
    uid = uuid.uuid4().hex[:10]
    email = f"cf.lc.auth.{uid}@smartreplyai.net"
    password = f"CfLcAuth!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.locator('input[name="store_name"]').fill(f"LcAuth {uid[:6]}", timeout=60000)
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(5000)
    report["auth"] = {"mode": "signup", "email": email, "password": password}


def _fetch_json(page: Page, path: str) -> dict[str, Any]:
    return page.evaluate(
        """async (path) => {
          const r = await fetch(path, { credentials: 'same-origin', cache: 'no-store' });
          const t = await r.text();
          try { return { status: r.status, body: JSON.parse(t) }; }
          catch (e) { return { status: r.status, body: null, parse_error: t.slice(0, 200) }; }
        }""",
        path,
    )


def _check_lifecycle_rows(rows: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    missing = 0
    vip_authority = 0
    followup_conflicts = 0
    display_mismatch = 0
    samples: list[dict[str, Any]] = []
    return_states: list[str] = []
    reply_states: list[str] = []
    for row in rows:
        state = str(row.get("customer_lifecycle_state") or "").strip()
        if not state:
            missing += 1
            continue
        if state in ("return_to_site", "waiting_purchase_window"):
            return_states.append(state)
        if state in ("customer_reply", "customer_engaged"):
            reply_states.append(state)
        vip_st = str(row.get("vip_lifecycle_status") or "").strip()
        label_ar = str(row.get("customer_lifecycle_label_ar") or "").strip()
        display = str(row.get("display_status_ar") or row.get("vip_lifecycle_label_ar") or "").strip()
        if label_ar and display and label_ar != display:
            display_mismatch += 1
        if vip_st and vip_st in ("abandoned", "contacted", "closed", "converted"):
            if state not in (
                "needs_intervention",
                "archived",
                "completed",
                "lifecycle_unavailable",
            ):
                if vip_st == "converted" and state != "completed":
                    vip_authority += 1
                elif vip_st == "closed" and state != "archived":
                    vip_authority += 1
        seq = row.get("merchant_followup_sequence_line_ar")
        nxt = row.get("merchant_followup_next_line_ar")
        nfu = str(row.get("customer_lifecycle_next_followup_line_ar") or "")
        what = str(row.get("customer_lifecycle_what_next_ar") or "")
        if nxt and nfu and nxt != nfu:
            followup_conflicts += 1
        if seq and "لا مزيد" in what and seq != what and "اكتملت" not in str(seq):
            followup_conflicts += 1
        if len(samples) < 6:
            samples.append(
                {
                    "recovery_key": (row.get("recovery_key") or "")[:64],
                    "customer_lifecycle_state": state,
                    "label_ar": label_ar[:60],
                    "merchant_cart_bucket": row.get("merchant_cart_bucket"),
                }
            )
    ok = missing == 0 and vip_authority == 0 and followup_conflicts == 0
    return {
        "label": label,
        "rows": len(rows),
        "missing_lifecycle": missing,
        "vip_status_as_authority": vip_authority,
        "followup_conflicts": followup_conflicts,
        "display_label_mismatch": display_mismatch,
        "return_detection_states": return_states,
        "reply_engaged_states": reply_states,
        "samples": samples,
        "ok": ok,
    }


def _lifecycle_filter_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "all": len(rows),
        "waiting": 0,
        "sent": 0,
        "attention": 0,
        "recovered": 0,
        "archived": 0,
    }
    for row in rows:
        tabs = row.get("merchant_cart_visible_tabs") or []
        if not isinstance(tabs, list):
            continue
        for tab in tabs:
            t = str(tab or "").strip().lower()
            if t in counts and t != "all":
                counts[t] += 1
    return counts


def _active_lifecycle_count(rows: list[dict[str, Any]]) -> int:
    n = 0
    for row in rows:
        sk = str(row.get("customer_lifecycle_state") or "").strip()
        if not sk or sk in ("archived", "completed", "lifecycle_unavailable"):
            continue
        n += 1
    return n


def _poll_deploy(commit: str, max_polls: int = 18) -> dict[str, Any]:
    out: dict[str, Any] = {"commit_expected": commit, "polls": [], "deployed": False}
    for i in range(max_polls):
        try:
            req = urllib.request.Request(
                f"{BASE}/login",
                headers={"User-Agent": "lc-authority-deploy-poll"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
            marker = commit[:7] if commit else ""
            hit = marker and marker in html
            out["polls"].append({"poll": i, "marker_found": hit, "marker": marker})
            if hit:
                out["deployed"] = True
                break
        except Exception as exc:  # noqa: BLE001
            out["polls"].append({"poll": i, "error": str(exc)[:120]})
        time.sleep(20)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "task": "Lifecycle Authority Recovery v1 Deploy Verification",
        "ts": time.time(),
        "base": BASE,
    }

    try:
        import subprocess

        commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        )
    except Exception:  # noqa: BLE001
        commit = COMMIT_EXPECTED
    report["commit"] = commit
    report["deploy_poll"] = _poll_deploy(commit)

    checks: dict[str, Any] = {}
    js_checks: dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        _auth(page, report)
        page.goto(f"{BASE}/dashboard", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        nc = _fetch_json(page, f"/api/dashboard/normal-carts?_ts={int(time.time())}")
        vip = _fetch_json(page, f"/api/dashboard/vip-carts?_ts={int(time.time())}")
        msg = _fetch_json(page, f"/api/dashboard/messages?_ts={int(time.time())}")
        summ = _fetch_json(page, f"/api/dashboard/summary?_ts={int(time.time())}")
        arch = _fetch_json(
            page, f"/api/dashboard/normal-carts?lifecycle=archived&_ts={int(time.time())}"
        )

        nc_body = nc.get("body") or {}
        nc_rows = (
            nc_body.get("merchant_normal_page_rows")
            or nc_body.get("rows")
            or nc_body.get("merchant_carts")
            or []
        )
        if not isinstance(nc_rows, list):
            nc_rows = []

        vip_body = vip.get("body") or {}
        vip_rows = vip_body.get("merchant_vip_page_rows") or []
        if not isinstance(vip_rows, list):
            vip_rows = []

        msg_body = msg.get("body") or {}
        msg_rows = msg_body.get("merchant_message_history_rows") or msg_body.get("rows") or []
        if not isinstance(msg_rows, list):
            msg_rows = []

        arch_body = arch.get("body") or {}
        arch_rows = arch_body.get("merchant_normal_page_rows") or arch_body.get("rows") or []
        if not isinstance(arch_rows, list):
            arch_rows = []

        checks["normal_carts"] = {
            "status": nc.get("status"),
            "partial": nc_body.get("dashboard_partial"),
            "lifecycle": _check_lifecycle_rows(nc_rows, label="normal_carts"),
            "filter_counts_api": nc_body.get("merchant_cart_filter_counts"),
            "filter_counts_derived": _lifecycle_filter_counts(nc_rows),
        }
        checks["vip_carts"] = {
            "status": vip.get("status"),
            "partial": vip_body.get("dashboard_partial"),
            "lifecycle": _check_lifecycle_rows(vip_rows, label="vip_carts"),
        }
        checks["messages"] = {
            "status": msg.get("status"),
            "rows": len(msg_rows),
            "missing_lifecycle": sum(
                1 for r in msg_rows if not str(r.get("customer_lifecycle_state") or "").strip()
            ),
            "with_lifecycle": sum(
                1 for r in msg_rows if str(r.get("customer_lifecycle_state") or "").strip()
            ),
            "ok": all(
                str(r.get("customer_lifecycle_state") or "").strip()
                or not str(r.get("recovery_key") or "").strip()
                for r in msg_rows
            ),
        }
        summ_body = summ.get("body") or {}
        active_from_rows = _active_lifecycle_count(nc_rows)
        normal_cart_count = summ_body.get("normal_cart_count")
        checks["summary"] = {
            "status": summ.get("status"),
            "normal_cart_count": normal_cart_count,
            "active_from_normal_carts": active_from_rows,
            "count_match": normal_cart_count == active_from_rows,
            "ok": summ.get("status") == 200 and normal_cart_count == active_from_rows,
        }
        checks["archive"] = {
            "status": arch.get("status"),
            "lifecycle": _check_lifecycle_rows(arch_rows, label="archived_tab"),
            "archived_states": [
                str(r.get("customer_lifecycle_state") or "")
                for r in arch_rows[:10]
            ],
            "ok": arch.get("status") == 200 and all(
                str(r.get("customer_lifecycle_state") or "") == "archived"
                for r in arch_rows
                if str(r.get("customer_lifecycle_state") or "")
            ),
        }

        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        js_checks = page.evaluate(
            """() => {
              var lazy = window.maDashboardLazy || {};
              var html = document.documentElement.innerHTML || '';
              return {
                has_customerLifecycleExplanationHtml: typeof lazy.customerLifecycleExplanationHtml === 'function',
                compact_fallback_in_html: html.indexOf('recovery-truth-compact') >= 0 && html.indexOf('merchantLifecycleCompact') >= 0,
                merchant_dashboard_lazy_v: (function(){
                  var s = document.querySelector('script[src*="merchant_dashboard_lazy"]');
                  return s ? s.src : null;
                })(),
              };
            }"""
        )

        browser.close()

    report["checks"] = checks
    report["js"] = js_checks
    report["pass"] = (
        report.get("deploy_poll", {}).get("deployed")
        and all(
            c.get("ok")
            for c in [
                checks.get("normal_carts", {}).get("lifecycle"),
                checks.get("vip_carts", {}).get("lifecycle"),
                checks.get("messages"),
                checks.get("summary"),
            ]
            if isinstance(c, dict)
        )
        and checks.get("normal_carts", {}).get("status") == 200
        and checks.get("vip_carts", {}).get("status") == 200
    )

    out_path = OUT / "deploy_verify_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
