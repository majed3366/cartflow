# -*- coding: utf-8 -*-
"""Production acceptance — reason POST client-wait detach V1.1."""
from __future__ import annotations

import json
import statistics
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
TARGET = "v2-widget-reason-post-detach-v1-5"
OUT = Path(__file__).resolve().parent / "_widget_reason_post_detach_v1_out"
N = 20
BEFORE = {
    "post_reason_p50_ms": 5772.0,
    "click_to_phone_p50_ms": 6588.5,
    "bridge_ensure_p50_ms": 2.6,
    "server_handler_p50_ms": 179.0,
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


def poll_deploy(rounds: int = 50, sleep_s: float = 12.0) -> bool:
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(rounds):
        try:
            body = (
                urllib.request.urlopen(
                    urllib.request.Request(
                        f"{BASE}/static/widget_loader.js?_ts={int(time.time()*1000)}",
                        headers={"Cache-Control": "no-cache"},
                    ),
                    timeout=30,
                )
                .read()
                .decode("utf-8", "replace")
            )
            ok = TARGET in body
            print(f"poll {i} detach={ok}", flush=True)
            if ok:
                return True
        except Exception as exc:
            print(f"poll {i} err {exc}", flush=True)
        time.sleep(sleep_s)
    return False


def _signup(page) -> bool:
    uid = uuid.uuid4().hex[:10]
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1200)
    page.locator('input[name="store_name"]').fill(f"Pd {uid[:6]}")
    page.locator('input[name="email"]').fill(f"cf.pd.{uid}@smartreplyai.net")
    page.locator('input[name="password"]').first.fill(f"CfPd!{uid[:8]}")
    page.locator('input[name="confirm_password"]').fill(f"CfPd!{uid[:8]}")
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(4500)
    return "/login" not in page.url


def _one(page, i: int) -> dict:
    entry: dict = {"i": i, "ok": False}
    reason_posts = 0
    arm_header = None

    def on_req(req) -> None:
        nonlocal reason_posts
        if req.method == "POST" and "/api/cartflow/reason" in req.url:
            raw = req.post_data or ""
            if "customer_phone" not in raw:
                reason_posts += 1

    def on_resp(resp) -> None:
        nonlocal arm_header
        if resp.request.method == "POST" and "/api/cartflow/reason" in resp.url:
            try:
                arm_header = resp.headers.get("x-cf-reason-arm")
            except Exception:
                pass

    page.on("request", on_req)
    page.on("response", on_resp)
    page.add_init_script(
        """
        (() => {
          window.__CF_FAST_PATH_TRACES = [];
          window.__CF_PHONE_SHOWN_AT = null;
          const orig = console.log;
          console.log = function() {
            try {
              if (arguments[0] === '[CF FAST PATH TRACE]') {
                window.__CF_FAST_PATH_TRACES.push(arguments[1]);
              }
              if (arguments[0] === '[CF V2 SHOW PHONE]') {
                window.__CF_PHONE_SHOWN_AT =
                  (typeof performance !== 'undefined' && performance.now)
                    ? performance.now()
                    : Date.now();
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

    # Warm same-origin connection before reason click (avoid cold start_to_request).
    try:
        page.evaluate(
            """async () => {
              try {
                await fetch('/api/cartflow/ready?store_slug=warm&session_id=warm', {
                  cache: 'no-store',
                });
              } catch (e) {}
            }"""
        )
        page.wait_for_timeout(150)
    except Exception:
        pass

    page.evaluate("() => { window.__CF_PHONE_SHOWN_AT = null; window.__CF_CLICK_AT = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now(); }")
    t_click = time.perf_counter()
    page.locator("[data-cf-reason-key]").first.click(timeout=10000)
    phone_ms = None
    for _ in range(80):
        shown = page.evaluate(
            """() => {
              if (window.__CF_PHONE_SHOWN_AT == null || window.__CF_CLICK_AT == null) return null;
              return Math.round((window.__CF_PHONE_SHOWN_AT - window.__CF_CLICK_AT) * 10) / 10;
            }"""
        )
        if shown is not None:
            phone_ms = float(shown)
            break
        if page.locator('input[type="tel"]').count() and page.locator(
            'input[type="tel"]'
        ).last.is_visible():
            phone_ms = round((time.perf_counter() - t_click) * 1000, 1)
            break
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=5000)
        page.wait_for_timeout(25)
    entry["click_to_phone_ms"] = phone_ms

    traces = page.evaluate("() => window.__CF_FAST_PATH_TRACES || []")
    entry["traces"] = traces
    entry["reason_posts"] = reason_posts
    entry["arm_header"] = arm_header

    post_ms = None
    server_ms = None
    net_ms = None
    for t in traces:
        if isinstance(t, dict) and t.get("flow") == "reason":
            stages = t.get("stages_ms") or {}
            post_ms = stages.get("post_reason")
            entry["total_ms"] = t.get("total_ms")
            entry["resource_timing"] = t.get("resource_timing")
            entry["reason_arm"] = t.get("reason_arm")
            entry["server_timing"] = t.get("server_timing")
            net_ms = t.get("client_net_ms")
            srv = t.get("server") or {}
            server_ms = srv.get("total_handler_ms")
            # Prefer instrumented next-screen total when phone opened directly.
            if phone_ms is None and t.get("total_ms") is not None:
                phone_ms = float(t["total_ms"])
                entry["click_to_phone_ms"] = phone_ms
    entry["post_reason_ms"] = post_ms
    entry["client_net_ms"] = net_ms
    entry["server_handler_ms"] = server_ms
    entry["ok"] = (
        phone_ms is not None
        and post_ms is not None
        and post_ms < 300
        and phone_ms < 500
        and reason_posts == 1
        and (arm_header == "detached_thread" or entry.get("reason_arm") == "detached_thread")
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
    posts: list[float] = []
    phones: list[float] = []
    servers: list[float] = []

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
                entry = _one(page, i)
            except Exception as exc:
                entry = {"i": i, "ok": False, "error": str(exc)[:300]}
            journeys.append(entry)
            if entry.get("post_reason_ms") is not None:
                posts.append(float(entry["post_reason_ms"]))
            if entry.get("click_to_phone_ms") is not None:
                phones.append(float(entry["click_to_phone_ms"]))
            if entry.get("server_handler_ms") is not None:
                servers.append(float(entry["server_handler_ms"]))
            print(
                "journey",
                i,
                entry.get("ok"),
                entry.get("post_reason_ms"),
                entry.get("click_to_phone_ms"),
                entry.get("arm_header") or entry.get("reason_arm"),
                flush=True,
            )
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

    post_d = _dist(posts)
    phone_d = _dist(phones)
    report = {
        "audit": "Widget Fast Path V1.1 — reason POST client-wait detach",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": TARGET,
        "root_cause": (
            "Extra ~5.7s spent in FastAPI BackgroundTasks recovery arm still "
            "awaited inside BaseHTTPMiddleware call_next before browser TTFB"
        ),
        "before": BEFORE,
        "after": {
            "post_reason": post_d,
            "click_to_phone": phone_d,
            "server_handler": _dist(servers),
        },
        "targets": {
            "post_reason_p50_lt_300": (post_d.get("p50") or 9999) < 300,
            "click_to_phone_p50_lt_500": (phone_d.get("p50") or 9999) < 500,
        },
        "pass_count": sum(1 for j in journeys if j.get("ok")),
        "journeys": journeys,
    }
    (OUT / "acceptance_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("POST_REASON", post_d, flush=True)
    print("CLICK_TO_PHONE", phone_d, flush=True)
    print("PASS", report["pass_count"], "/", N, flush=True)
    print("TARGETS", report["targets"], flush=True)
    ok = (
        report["pass_count"] >= 16
        and report["targets"]["post_reason_p50_lt_300"]
        and report["targets"]["click_to_phone_p50_lt_500"]
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
