# -*- coding: utf-8 -*-
"""Widget Fast Path Root Cause V1 — production stage timing probe (investigation only)."""
from __future__ import annotations

import json
import statistics
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
TARGET = "v2-widget-fast-path-invest-v1"
OUT = Path(__file__).resolve().parent / "_widget_fast_path_invest_v1_out"
N = 12


def _pct(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 1)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return round(sorted_vals[f], 1)
    return round(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f), 1)


def _dist(vals: list[float]) -> dict:
    s = sorted(v for v in vals if v is not None)
    if not s:
        return {"n": 0}
    return {
        "n": len(s),
        "p50": _pct(s, 50),
        "p90": _pct(s, 90),
        "p95": _pct(s, 95),
        "max": round(s[-1], 1),
        "min": round(s[0], 1),
        "mean": round(statistics.mean(s), 1),
        "samples": [round(x, 1) for x in s],
    }


def poll_deploy(rounds: int = 40, sleep_s: float = 12.0) -> bool:
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(rounds):
        try:
            body = urllib.request.urlopen(
                urllib.request.Request(
                    f"{BASE}/static/widget_loader.js?_ts={int(time.time()*1000)}",
                    headers={"Cache-Control": "no-cache"},
                ),
                timeout=30,
            ).read().decode("utf-8", "replace")
            ok = TARGET in body
            print(f"poll {i} invest={ok}", flush=True)
            if ok:
                # also need server cf_timing — probe one OPTIONS/POST after journeys
                return True
        except Exception as exc:
            print(f"poll {i} err {exc}", flush=True)
        time.sleep(sleep_s)
    return False


def _signup(page) -> bool:
    uid = uuid.uuid4().hex[:10]
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1200)
    page.locator('input[name="store_name"]').fill(f"Fp {uid[:6]}")
    page.locator('input[name="email"]').fill(f"cf.fp.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"CfFp!{uid[:8]}")
    page.locator('input[name="confirm_password"]').fill(f"CfFp!{uid[:8]}")
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(4500)
    return "/login" not in page.url


def _one(page, i: int) -> dict:
    entry: dict = {"i": i, "ok": False}
    traces: list[dict] = []
    reason_bodies: list[dict] = []

    def on_console(m) -> None:
        t = m.text or ""
        if "[CF FAST PATH TRACE" in t:
            try:
                # Playwright may stringify object as {flow: reason, ...}
                traces.append({"raw": t[:2000]})
            except Exception:
                pass

    def on_resp(resp) -> None:
        if resp.request.method != "POST" or "/api/cartflow/reason" not in resp.url:
            return
        try:
            body = resp.json()
        except Exception:
            return
        if isinstance(body, dict) and body.get("cf_timing"):
            is_phone = False
            try:
                is_phone = "customer_phone" in (resp.request.post_data or "")
            except Exception:
                pass
            reason_bodies.append(
                {
                    "is_phone": is_phone,
                    "cf_timing": body.get("cf_timing"),
                    "status": resp.status,
                    "playwright_timing": getattr(resp.request, "timing", None),
                }
            )

    page.on("console", on_console)
    page.on("response", on_resp)

    if not _signup(page):
        entry["error"] = "auth"
        return entry
    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(4000)
    for sel in ('button:has-text("أضف إلى السلة")', 'button:has-text("أضف")'):
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            loc.click(timeout=15000)
            break
    page.wait_for_timeout(2500)
    page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
    page.evaluate("window.__cfV2ShowNow()")
    page.wait_for_timeout(800)
    try:
        page.get_by_role("button", name="نعم").click(timeout=12000)
        page.wait_for_timeout(400)
    except Exception:
        pass
    page.locator("[data-cf-reason-key]").first.click(timeout=10000)
    for _ in range(55):
        if page.locator('input[type="tel"]').count() and page.locator(
            'input[type="tel"]'
        ).last.is_visible():
            break
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=5000)
            page.wait_for_timeout(250)
        page.wait_for_timeout(200)
    try:
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=8000)
            page.wait_for_timeout(250)
        if page.locator('input[type="tel"]').count():
            page.locator('input[type="tel"]').last.fill("0598877660")
            page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
            page.wait_for_timeout(2800)
    except Exception as exc:
        entry["phone_error"] = str(exc)[:200]

    # Pull client traces via page evaluate (more reliable than console object string)
    client = page.evaluate(
        """() => {
          const logs = window.__CF_FAST_PATH_TRACES || [];
          return logs.slice(-4);
        }"""
    )
    entry["client_traces"] = client
    entry["console_hits"] = traces
    entry["server_posts"] = reason_bodies
    entry["ok"] = len(reason_bodies) >= 1
    return entry


def _aggregate(server_posts: list[dict]) -> dict:
    reason_stages: dict[str, list[float]] = {}
    phone_stages: dict[str, list[float]] = {}
    reason_totals: list[float] = []
    phone_totals: list[float] = []
    for p in server_posts:
        t = (p.get("cf_timing") or {}) if isinstance(p, dict) else {}
        stages = t.get("stages_ms") or {}
        total = t.get("total_handler_ms")
        bucket = phone_stages if p.get("is_phone") else reason_stages
        totals = phone_totals if p.get("is_phone") else reason_totals
        if total is not None:
            totals.append(float(total))
        for k, v in stages.items():
            try:
                bucket.setdefault(k, []).append(float(v))
            except Exception:
                pass
    return {
        "reason_handler_total": _dist(reason_totals),
        "phone_handler_total": _dist(phone_totals),
        "reason_stages": {k: _dist(v) for k, v in sorted(reason_stages.items())},
        "phone_stages": {k: _dist(v) for k, v in sorted(phone_stages.items())},
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    if not poll_deploy():
        print("DEPLOY_TIMEOUT", flush=True)
        return 1

    # Patch client to stash traces (evaluate inject after load each journey)
    inject = """
    (() => {
      if (window.__CF_FAST_PATH_HOOK) return;
      window.__CF_FAST_PATH_HOOK = true;
      window.__CF_FAST_PATH_TRACES = [];
      const orig = console.log;
      console.log = function() {
        try {
          if (arguments[0] === '[CF FAST PATH TRACE]' || arguments[0] === '[CF FAST PATH TRACE CLOSE]') {
            window.__CF_FAST_PATH_TRACES.push(arguments[1] || arguments[0]);
          }
        } catch (e) {}
        return orig.apply(console, arguments);
      };
    })();
    """

    journeys = []
    all_server: list[dict] = []
    all_client: list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i in range(N):
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.add_init_script(inject)
            try:
                entry = _one(page, i)
            except Exception as exc:
                entry = {"i": i, "ok": False, "error": str(exc)[:300]}
            journeys.append(entry)
            all_server.extend(entry.get("server_posts") or [])
            all_client.extend(entry.get("client_traces") or [])
            print("journey", i, "server_n", len(entry.get("server_posts") or []), flush=True)
            page.close()
            ctx.close()
        browser.close()

    agg = _aggregate(all_server)
    # Client stage aggregation
    client_reason: dict[str, list[float]] = {}
    client_phone: dict[str, list[float]] = {}
    for tr in all_client:
        if not isinstance(tr, dict):
            continue
        stages = tr.get("stages_ms") or {}
        bucket = client_phone if tr.get("flow") == "phone" else client_reason
        for k, v in stages.items():
            try:
                bucket.setdefault(k, []).append(float(v))
            except Exception:
                pass
        if tr.get("total_ms") is not None:
            bucket.setdefault("total_ms", []).append(float(tr["total_ms"]))
        if tr.get("client_net_ms") is not None:
            bucket.setdefault("client_net_ms", []).append(float(tr["client_net_ms"]))

    report = {
        "audit": "Widget Fast Path Root Cause Investigation V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_journeys": N,
        "budgets_ms": {
            "ui_feedback": 50,
            "bridge": 100,
            "api_receive": 50,
            "database": 100,
            "lifecycle": 100,
            "total_click_to_next": 500,
        },
        "server": agg,
        "client_reason_stages": {k: _dist(v) for k, v in sorted(client_reason.items())},
        "client_phone_stages": {k: _dist(v) for k, v in sorted(client_phone.items())},
        "journeys": journeys,
    }

    # Identify first over-budget server stage by P50 order
    order = [
        "db_warm",
        "json_parse",
        "validate_coerce",
        "phone_normalize",
        "db_lookup_crr",
        "db_prepare_writes",
        "db_flush",
        "phone_sync_session",
        "db_commit",
        "phone_side_effects",
        "vip_alert_optional",
        "schedule_recovery_bg",
    ]
    budgets = {
        "db_warm": 50,
        "json_parse": 50,
        "validate_coerce": 50,
        "phone_normalize": 50,
        "db_lookup_crr": 100,
        "db_prepare_writes": 50,
        "db_flush": 100,
        "phone_sync_session": 100,
        "db_commit": 100,
        "phone_side_effects": 100,
        "vip_alert_optional": 100,
        "schedule_recovery_bg": 50,
    }
    first = None
    chain = []
    for name in order:
        d = (agg.get("reason_stages") or {}).get(name) or {}
        p50 = d.get("p50")
        if p50 is None:
            continue
        over = p50 > budgets.get(name, 100)
        chain.append({"stage": name, "p50": p50, "budget": budgets.get(name), "over": over})
        if over and first is None:
            first = name

    report["first_over_budget_reason_server"] = first
    report["reason_server_budget_chain"] = chain

    (OUT / "timing_breakdown.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("FIRST_OVER", first, flush=True)
    print("REASON_STAGES", json.dumps(agg.get("reason_stages"), indent=2), flush=True)
    print("PHONE_STAGES", json.dumps(agg.get("phone_stages"), indent=2), flush=True)
    return 0 if agg.get("reason_handler_total", {}).get("n", 0) >= 5 else 2


if __name__ == "__main__":
    raise SystemExit(main())
