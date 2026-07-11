# -*- coding: utf-8 -*-
"""Production acceptance — bridge fail-fast V1 (reason path only)."""
from __future__ import annotations

import json
import statistics
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
TARGET = "v2-widget-bridge-fail-fast-v1"
OUT = Path(__file__).resolve().parent / "_widget_bridge_fail_fast_v1_out"
N = 20
BEFORE = {
    "bridge_ensure_p50_ms": 3390.7,
    "total_click_to_phone_p50_ms": 6345.5,
}


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
            print(f"poll {i} fail_fast={ok}", flush=True)
            if ok:
                core = urllib.request.urlopen(
                    urllib.request.Request(
                        f"{BASE}/static/cartflow_widget_runtime/cartflow_storefront_cart_bridge_core.js?_ts={int(time.time()*1000)}",
                        headers={"Cache-Control": "no-cache"},
                    ),
                    timeout=30,
                ).read().decode("utf-8", "replace")
                print("MARKER", "[CF BRIDGE ENSURE FAIL FAST]" in core, flush=True)
                return True
        except Exception as exc:
            print(f"poll {i} err {exc}", flush=True)
        time.sleep(sleep_s)
    return False


def _signup(page) -> bool:
    uid = uuid.uuid4().hex[:10]
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1200)
    page.locator('input[name="store_name"]').fill(f"Bf {uid[:6]}")
    page.locator('input[name="email"]').fill(f"cf.bf.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"CfBf!{uid[:8]}")
    page.locator('input[name="confirm_password"]').fill(f"CfBf!{uid[:8]}")
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(4500)
    return "/login" not in page.url


def _one(page, i: int, vid_dir: Path | None) -> dict:
    entry: dict = {"i": i, "ok": False}
    reason_posts = 0

    def on_req(req) -> None:
        nonlocal reason_posts
        if req.method == "POST" and "/api/cartflow/reason" in req.url:
            # count reason-only (no phone) until phone filled
            raw = req.post_data or ""
            if "customer_phone" not in raw:
                reason_posts += 1

    page.on("request", on_req)
    page.add_init_script(
        """
        (() => {
          window.__CF_FAST_PATH_TRACES = [];
          window.__CF_BRIDGE_FF = [];
          const orig = console.log;
          console.log = function() {
            try {
              if (arguments[0] === '[CF FAST PATH TRACE]') {
                window.__CF_FAST_PATH_TRACES.push(arguments[1]);
              }
              if (arguments[0] === '[CF BRIDGE ENSURE FAIL FAST]') {
                window.__CF_BRIDGE_FF.push(arguments[1]);
              }
            } catch (e) {}
            return orig.apply(console, arguments);
          };
        })();
        """
    )

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

    t_click = time.perf_counter()
    page.locator("[data-cf-reason-key]").first.click(timeout=10000)
    phone_ms = None
    for _ in range(60):
        if page.locator('input[type="tel"]').count() and page.locator(
            'input[type="tel"]'
        ).last.is_visible():
            phone_ms = round((time.perf_counter() - t_click) * 1000, 1)
            break
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=5000)
            page.wait_for_timeout(200)
        page.wait_for_timeout(100)
    entry["click_to_phone_ms"] = phone_ms

    # Do not complete phone save in this acceptance (reason path only)
    traces = page.evaluate("() => window.__CF_FAST_PATH_TRACES || []")
    ff = page.evaluate("() => window.__CF_BRIDGE_FF || []")
    entry["traces"] = traces
    entry["bridge_ff"] = ff
    entry["reason_posts"] = reason_posts

    bridge_ms = None
    path = None
    for t in traces:
        if isinstance(t, dict) and t.get("flow") == "reason":
            stages = t.get("stages_ms") or {}
            if "bridge_ensure" in stages:
                bridge_ms = stages["bridge_ensure"]
            entry["total_ms"] = t.get("total_ms")
    for f in ff:
        if isinstance(f, dict):
            path = f.get("fail_fast_path") or f.get("path")
            if f.get("ms") is not None and bridge_ms is None:
                bridge_ms = f.get("ms")
    entry["bridge_ensure_ms"] = bridge_ms
    entry["fail_fast_path"] = path
    entry["ok"] = (
        phone_ms is not None
        and bridge_ms is not None
        and bridge_ms < 100
        and reason_posts == 1
        and path
        and path != "missing_identity"
    )
    return entry


def main() -> int:
    from playwright.sync_api import sync_playwright

    if not poll_deploy():
        print("DEPLOY_TIMEOUT", flush=True)
        return 1

    vid = OUT / "videos"
    vid.mkdir(parents=True, exist_ok=True)
    for old in vid.glob("*.webm"):
        try:
            old.unlink()
        except Exception:
            pass

    journeys = []
    bridges: list[float] = []
    totals: list[float] = []
    phones: list[float] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i in range(N):
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(vid) if i < 5 else None,
                record_video_size={"width": 1280, "height": 800} if i < 5 else None,
            )
            page = ctx.new_page()
            try:
                entry = _one(page, i, vid if i < 5 else None)
            except Exception as exc:
                entry = {"i": i, "ok": False, "error": str(exc)[:300]}
            journeys.append(entry)
            if entry.get("bridge_ensure_ms") is not None:
                bridges.append(float(entry["bridge_ensure_ms"]))
            if entry.get("click_to_phone_ms") is not None:
                phones.append(float(entry["click_to_phone_ms"]))
            if entry.get("total_ms") is not None:
                totals.append(float(entry["total_ms"]))
            print("journey", i, entry.get("ok"), entry.get("bridge_ensure_ms"), entry.get("click_to_phone_ms"), entry.get("fail_fast_path"), flush=True)
            page.close()
            ctx.close()
            if i < 5:
                unnamed = sorted(
                    [x for x in vid.glob("*.webm") if not x.name.startswith("journey_")],
                    key=lambda p: p.stat().st_mtime,
                )
                if unnamed:
                    dest = vid / f"journey_{i+1:02d}.webm"
                    try:
                        if dest.exists():
                            dest.unlink()
                        unnamed[-1].replace(dest)
                    except Exception:
                        pass
        browser.close()

    bridge_d = _dist(bridges)
    phone_d = _dist(phones)
    report = {
        "audit": "Widget Fast Path V1 — bridge ensure fail-fast",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": TARGET,
        "before": BEFORE,
        "after": {
            "bridge_ensure": bridge_d,
            "click_to_phone": phone_d,
            "trace_total": _dist(totals),
        },
        "targets": {
            "bridge_ensure_p50_lt_100": (bridge_d.get("p50") or 999) < 100,
            "click_to_phone_p50_lt_500": (phone_d.get("p50") or 9999) < 500,
        },
        "pass_count": sum(1 for j in journeys if j.get("ok")),
        "journeys": journeys,
    }
    (OUT / "acceptance_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("BRIDGE", bridge_d, flush=True)
    print("CLICK_TO_PHONE", phone_d, flush=True)
    print("PASS", report["pass_count"], "/", N, flush=True)
    print("TARGETS", report["targets"], flush=True)
    ok = (
        report["pass_count"] >= 16
        and report["targets"]["bridge_ensure_p50_lt_100"]
    )
    # click_to_phone <500 is stretch if POST net remains slow — report honestly
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
