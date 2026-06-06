# -*- coding: utf-8 -*-
"""Production Truth Audit — read-only evidence collection (no code fixes)."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "_production_truth_audit_out"

MARKERS = {
    "price_fallback_fn": "applyLegacyPriceSubCategoryDefault",
    "recovery_flow_close": "CF RECOVERY FLOW COMPLETE CLOSE",
    "partial_retry": "normal_carts_partial_retry",
    "wall_budget_12": "_DEFAULT_WALL_BUDGET_S = 12.0",
}


def _git(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *cmd], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def _http_get(url: str, timeout: int = 30) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "cartflow-truth-audit/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body, dict(e.headers)
    except Exception as exc:
        return 0, str(exc), {}


def _probe_static_markers(base: str) -> dict[str, Any]:
    assets = {
        "cartflow_widget_fetch.js": f"{base}/static/cartflow_widget_runtime/cartflow_widget_fetch.js",
        "cartflow_widget_flows.js": f"{base}/static/cartflow_widget_runtime/cartflow_widget_flows.js",
        "merchant_dashboard_lazy.js": f"{base}/static/merchant_dashboard_lazy.js",
    }
    out: dict[str, Any] = {}
    for name, url in assets.items():
        status, body, _ = _http_get(url)
        entry = {"url": url, "status": status, "bytes": len(body)}
        for mk, needle in MARKERS.items():
            if needle in ("_DEFAULT_WALL_BUDGET_S = 12.0",):
                continue
            entry[mk] = needle in body if status == 200 else None
        out[name] = entry
    return out


def _github_main_sha() -> dict[str, Any]:
    url = "https://api.github.com/repos/majed3366/cartflow/commits/main"
    status, body, _ = _http_get(url)
    if status != 200:
        return {"error": body[:500], "status": status}
    data = json.loads(body)
    return {
        "sha": data.get("sha"),
        "short": (data.get("sha") or "")[:7],
        "message": (data.get("commit") or {}).get("message", "").split("\n")[0],
        "date": (data.get("commit") or {}).get("committer", {}).get("date"),
        "html_url": data.get("html_url"),
    }


def _run_journey(base: str, label: str) -> dict[str, Any]:
    """One fresh VIP-ish cart journey (1299 SAR) on demo store."""
    OUT.mkdir(parents=True, exist_ok=True)
    env_dir = OUT / label
    env_dir.mkdir(parents=True, exist_ok=True)

    console_logs: list[dict] = []
    network_events: list[dict] = []
    ids: dict = {}
    widget_states: list[dict] = []
    cart_add_ts = 0.0
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        page.on("console", lambda msg: console_logs.append({"type": msg.type, "text": msg.text}))

        def on_response(resp) -> None:
            url = resp.url
            if not any(
                x in url
                for x in (
                    "/api/cart-event",
                    "/api/cartflow/reason",
                    "/api/dashboard/normal-carts",
                    "/api/dashboard/vip-carts",
                )
            ):
                return
            entry: dict = {
                "url": url.split("?")[0],
                "status": resp.status,
                "method": resp.request.method,
                "t": time.time(),
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
            network_events.append(entry)

        page.on("response", on_response)

        bust = str(int(time.time()))
        page.goto(f"{base}/demo/store?_audit={bust}", timeout=120000)
        page.wait_for_timeout(3000)
        page.screenshot(path=str(env_dir / "A_before_journey.png"), full_page=False)

        page.evaluate("sessionStorage.clear(); try{localStorage.removeItem('cartflow_customer_phone');}catch(e){}")
        page.goto(f"{base}/demo/store?_audit={bust}&fresh=1", timeout=120000)
        page.wait_for_timeout(4000)

        page.locator("#p-watch_pro .add-btn").click()
        cart_add_ts = time.time()
        page.wait_for_timeout(3000)

        page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
        page.evaluate("window.__cfV2ShowNow()")
        page.wait_for_timeout(2000)

        page.get_by_role("button", name="نعم").click(timeout=20000)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="السعر").click(timeout=20000)
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="شكراً").click(timeout=20000)
        page.wait_for_timeout(1000)
        page.locator('input[type="tel"]').last.fill("0598877660")
        page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(env_dir / "B_after_phone_save.png"), full_page=False)

        ids = page.evaluate(
            """() => ({
              session_id: sessionStorage.getItem('cartflow_recovery_session_id'),
              cart_id: sessionStorage.getItem('cartflow_cart_event_id'),
              phone_done: sessionStorage.getItem('cartflow_cf_v2_optional_phone_done'),
              suppress: sessionStorage.getItem('cartflow_cf_suppress_after_dismiss'),
              runtime_version: window.CARTFLOW_RUNTIME_VERSION || null
            })"""
        )

        elapsed = time.time() - cart_add_ts
        remain = max(0, 22.0 - elapsed)
        if remain > 0:
            page.wait_for_timeout(int(remain * 1000))

        for wait_ms in (300, 1000, 5000, 10000, 22000):
            widget_states.append(
                page.evaluate(
                    """(ms) => {
                      var bubble = document.querySelector('[data-cartflow-bubble]');
                      var shell = document.querySelector('[data-cf-shell="1"]');
                      return {
                        wait_ms: ms,
                        bubble_display: bubble ? getComputedStyle(bubble).display : null,
                        shell_step: shell ? shell.getAttribute('data-cf-step') : null,
                        suppress: sessionStorage.getItem('cartflow_cf_suppress_after_dismiss')
                      };
                    }""",
                    wait_ms,
                )
            )

        page.screenshot(path=str(env_dir / "C_after_22s.png"), full_page=False)

        # Dashboard (dev bypass works on local only)
        page.goto(f"{base}/dashboard#carts?tab=all", timeout=120000)
        page.wait_for_timeout(12000)
        page.screenshot(path=str(env_dir / "D_dashboard_carts.png"), full_page=True)
        page.goto(f"{base}/dashboard#vip", timeout=120000)
        page.wait_for_timeout(6000)
        page.screenshot(path=str(env_dir / "E_dashboard_vip.png"), full_page=True)

        table_rows = page.evaluate(
            """() => {
              var tb = document.querySelector('#ma-tbody-all-carts');
              return tb ? tb.querySelectorAll('tr[data-ma-filter]').length : 0;
            }"""
        )

        browser.close()

    # Widget reopen detection
    phone_ok_idx = next(
        (i for i, c in enumerate(console_logs) if "CF REASON_PHONE_SAVE_SUCCESS V2" in c.get("text", "")),
        -1,
    )
    reopened = False
    if phone_ok_idx >= 0:
        for c in console_logs[phone_ok_idx + 1 :]:
            t = c.get("text", "")
            if "CF WIDGET SHOW V2" in t or "CF V2 SHOW YESNO" in t:
                reopened = True
                break

    reason_posts = [e for e in network_events if e.get("url", "").endswith("/api/cartflow/reason")]
    phone_post = None
    for e in reversed(reason_posts):
        req = e.get("request") or {}
        if req.get("customer_phone"):
            phone_post = e
            break

    dash_nc_events = [
        e for e in network_events if e.get("url", "").endswith("/api/dashboard/normal-carts")
    ]
    dash_vip_events = [
        e for e in network_events if e.get("url", "").endswith("/api/dashboard/vip-carts")
    ]

    def _last_json_resp(events: list[dict]) -> dict:
        for e in reversed(events):
            if isinstance(e.get("response"), dict):
                return e["response"]
        return {}

    dash_normal = _last_json_resp(dash_nc_events)
    dash_vip = _last_json_resp(dash_vip_events)

    cart_id = ids.get("cart_id")
    vip_row = None
    for r in dash_vip.get("merchant_vip_page_rows") or []:
        blob = json.dumps(r, default=str)
        if cart_id and cart_id in blob:
            vip_row = r
            break

    normal_row = None
    rows = dash_normal.get("merchant_carts_page_rows") or []
    for r in rows:
        if cart_id and r.get("cart_id") == cart_id:
            normal_row = r
            break

    db_row = None
    if label == "local_8011":
        db_path = str(Path(tempfile.gettempdir()) / "cartflow.db")
        if cart_id and Path(db_path).is_file():
            con = sqlite3.connect(db_path)
            con.row_factory = sqlite3.Row
            db_row = con.execute(
                """
                SELECT ac.id, ac.zid_cart_id, ac.customer_phone, ac.cart_value,
                       ac.vip_mode, ac.recovery_session_id, s.zid_store_id AS store_slug
                FROM abandoned_carts ac
                LEFT JOIN stores s ON s.id = ac.store_id
                WHERE ac.zid_cart_id = ?
                ORDER BY ac.id DESC LIMIT 1
                """,
                (cart_id,),
            ).fetchone()
            con.close()
            db_row = dict(db_row) if db_row else None

    recovery_key = f"demo:{cart_id}" if cart_id else None

    return {
        "base": base,
        "label": label,
        "ids": ids,
        "recovery_key": recovery_key,
        "db_row": db_row,
        "phone_post": phone_post,
        "vip_row": vip_row,
        "normal_row": normal_row,
        "widget_reopened_after_phone": reopened,
        "widget_states": widget_states,
        "dashboard_normal_last": {
            "dashboard_partial": dash_normal.get("dashboard_partial"),
            "dashboard_timeout": dash_normal.get("dashboard_timeout"),
            "dashboard_timeout_stage": dash_normal.get("dashboard_timeout_stage"),
            "dashboard_wall_budget_s": dash_normal.get("dashboard_wall_budget_s"),
            "row_count": len(rows),
            "filter_all": (dash_normal.get("merchant_cart_filter_counts") or {}).get("all"),
            "table_rows_dom": table_rows,
        },
        "dashboard_vip_last": {
            "vip_count": len(dash_vip.get("merchant_vip_page_rows") or []),
            "matched_has_phone": (vip_row or {}).get("has_phone"),
            "matched_manual_contact": (vip_row or {}).get("manual_contact_available"),
            "matched_unavailable_ar": (vip_row or {}).get("manual_contact_unavailable_ar"),
        },
        "console_tail": [
            c
            for c in console_logs
            if any(
                k in c.get("text", "")
                for k in (
                    "CF REASON",
                    "CF RECOVERY",
                    "CF HESITATION",
                    "CF WIDGET",
                    "CF V2 SHOW",
                    "CF TRIGGER",
                    "CF SHELL",
                )
            )
        ][-50:],
        "network_timings": [
            {
                "url": e.get("url"),
                "status": e.get("status"),
                "partial": (e.get("response") or {}).get("dashboard_partial"),
                "timeout_stage": (e.get("response") or {}).get("dashboard_timeout_stage"),
                "rows": len((e.get("response") or {}).get("merchant_carts_page_rows") or []),
            }
            for e in dash_nc_events
        ],
        "screenshots": [
            str(env_dir / "A_before_journey.png"),
            str(env_dir / "B_after_phone_save.png"),
            str(env_dir / "C_after_22s.png"),
            str(env_dir / "D_dashboard_carts.png"),
            str(env_dir / "E_dashboard_vip.png"),
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    local_head = _git(["rev-parse", "HEAD"])
    local_short = _git(["rev-parse", "--short", "HEAD"])
    remote_main = _git(["ls-remote", "origin", "refs/heads/main"]).split()[0] if _git(["ls-remote", "origin", "refs/heads/main"]) else ""
    ahead = _git(["rev-list", "--count", f"origin/main..HEAD"]) or "?"

    github = _github_main_sha()
    prod_markers = _probe_static_markers("https://smartreplyai.net")
    local_markers = {}
    try:
        local_markers = _probe_static_markers("http://127.0.0.1:8011")
    except Exception as exc:
        local_markers = {"error": str(exc)}

    local_journey: dict[str, Any] = {"skipped": "server not checked"}
    prod_journey: dict[str, Any] = {}

    status, _, _ = _http_get("http://127.0.0.1:8011/health", timeout=5)
    if status == 200:
        local_journey = _run_journey("http://127.0.0.1:8011", "local_8011")

    prod_journey = _run_journey("https://smartreplyai.net", "production")

    report = {
        "audit_at_utc": datetime.now(timezone.utc).isoformat(),
        "section_a_version_truth": {
            "local_git_head": local_head,
            "local_git_short": local_short,
            "origin_main_sha": remote_main,
            "origin_main_short": remote_main[:7] if remote_main else None,
            "commits_ahead_of_origin_main": ahead,
            "unpushed_commits": [
                _git(["log", "--oneline", f"origin/main..HEAD"]),
            ],
            "github_api_main": github,
            "production_static_markers": prod_markers,
            "local_static_markers": local_markers,
            "mismatch_summary": {
                "github_main_is": github.get("short"),
                "local_has_unpushed": int(ahead) > 0 if str(ahead).isdigit() else True,
                "production_missing_a77bdcf_marker": not (
                    (prod_markers.get("cartflow_widget_fetch.js") or {}).get("price_fallback_fn")
                ),
                "production_missing_5541e5c_markers": {
                    "recovery_flow_close": not (
                        (prod_markers.get("cartflow_widget_flows.js") or {}).get("recovery_flow_close")
                    ),
                    "partial_retry": not (
                        (prod_markers.get("merchant_dashboard_lazy.js") or {}).get("partial_retry")
                    ),
                },
            },
        },
        "section_b_vip": {
            "local": {
                "cart_id": (local_journey.get("ids") or {}).get("cart_id"),
                "session_id": (local_journey.get("ids") or {}).get("session_id"),
                "recovery_key": local_journey.get("recovery_key"),
                "db_customer_phone": (local_journey.get("db_row") or {}).get("customer_phone"),
                "abandoned_cart_id": (local_journey.get("db_row") or {}).get("id"),
                "phone_post_status": (local_journey.get("phone_post") or {}).get("status"),
                "vip_row": local_journey.get("vip_row"),
            },
            "production": {
                "cart_id": (prod_journey.get("ids") or {}).get("cart_id"),
                "session_id": (prod_journey.get("ids") or {}).get("session_id"),
                "recovery_key": prod_journey.get("recovery_key"),
                "phone_post_status": (prod_journey.get("phone_post") or {}).get("status"),
                "phone_post_request": (prod_journey.get("phone_post") or {}).get("request"),
                "phone_post_response": (prod_journey.get("phone_post") or {}).get("response"),
                "vip_row": prod_journey.get("vip_row"),
                "dashboard_requires_login": (prod_journey.get("dashboard_vip_last") or {}).get("vip_count") == 0
                and not prod_journey.get("vip_row"),
            },
        },
        "section_c_normal_carts": {
            "local": local_journey.get("dashboard_normal_last"),
            "local_network_timings": local_journey.get("network_timings"),
            "production": prod_journey.get("dashboard_normal_last"),
            "production_network_timings": prod_journey.get("network_timings"),
        },
        "section_d_widget": {
            "local_reopened": local_journey.get("widget_reopened_after_phone"),
            "production_reopened": prod_journey.get("widget_reopened_after_phone"),
            "local_console_tail": local_journey.get("console_tail"),
            "production_console_tail": prod_journey.get("console_tail"),
        },
        "raw_journeys": {
            "local": local_journey,
            "production": prod_journey,
        },
    }

    out_path = OUT / "production_truth_audit.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "report": str(out_path),
        "github_main": github.get("short"),
        "local_head": local_short,
        "ahead": ahead,
        "prod_price_fix": (prod_markers.get("cartflow_widget_fetch.js") or {}).get("price_fallback_fn"),
        "prod_widget_close_fix": (prod_markers.get("cartflow_widget_flows.js") or {}).get("recovery_flow_close"),
        "prod_local_reopen": prod_journey.get("widget_reopened_after_phone"),
        "local_reopen": local_journey.get("widget_reopened_after_phone"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
