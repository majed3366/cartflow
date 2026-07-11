# -*- coding: utf-8 -*-
"""Widget Journey V2.2 — measure production reason/phone persist timings."""
from __future__ import annotations

import json
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_widget_zero_friction_v2_2_out"
N = 20


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
    s = sorted(vals)
    return {
        "n": len(s),
        "min": round(s[0], 1) if s else None,
        "max": round(s[-1], 1) if s else None,
        "mean": round(statistics.mean(s), 1) if s else None,
        "p50": _pct(s, 50),
        "p90": _pct(s, 90),
        "p95": _pct(s, 95),
        "p99": _pct(s, 99),
        "samples_ms": [round(v, 1) for v in s],
    }


def _signup(page) -> dict:
    uid = uuid.uuid4().hex[:10]
    email = f"cf.zf22.{uid}@smartreplyai.net"
    password = f"CfZf22!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"Zf {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(4500)
    return {"email": email, "ok": "/login" not in page.url, "url": page.url}


def _one(page, i: int) -> dict:
    entry: dict = {"i": i, "ok": False}
    reason_ms: list[float] = []
    phone_ms: list[float] = []
    pending: dict[str, float] = {}

    def on_req(req) -> None:
        if req.method != "POST" or "/api/cartflow/reason" not in req.url:
            return
        pending[req.url + str(id(req))] = time.perf_counter()
        req._cf_mark = pending  # type: ignore[attr-defined]

    def on_resp(resp) -> None:
        req = resp.request
        if req.method != "POST" or "/api/cartflow/reason" not in req.url:
            return
        # Prefer Playwright timing when available
        t_ms = None
        try:
            timing = req.timing or {}
            # responseEnd - requestStart (ms)
            rs = timing.get("requestStart")
            re = timing.get("responseEnd")
            if rs is not None and re is not None and re >= 0 and rs >= 0:
                t_ms = float(re) - float(rs)
        except Exception:
            pass
        if t_ms is None or t_ms < 0:
            # fallback wall clock from our mark — match by url+approx
            t_ms = None
            for k, t0 in list(pending.items()):
                if req.url in k:
                    t_ms = (time.perf_counter() - t0) * 1000.0
                    pending.pop(k, None)
                    break
        if t_ms is None:
            return
        # Classify: phone merge includes customer_phone in post data
        is_phone = False
        try:
            raw = req.post_data or ""
            is_phone = "customer_phone" in raw
        except Exception:
            pass
        if is_phone:
            phone_ms.append(t_ms)
        else:
            reason_ms.append(t_ms)

    page.on("request", on_req)
    page.on("response", on_resp)

    auth = _signup(page)
    entry["auth_ok"] = auth["ok"]
    if not auth["ok"]:
        entry["error"] = "auth_failed"
        return entry

    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(4000)
    for sel in (
        'button:has-text("أضف إلى السلة")',
        'button:has-text("أضف")',
        'button:has-text("Add")',
    ):
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            loc.click(timeout=15000)
            break
    page.wait_for_timeout(2500)
    page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
    page.evaluate("window.__cfV2ShowNow()")
    page.wait_for_timeout(1000)
    try:
        page.get_by_role("button", name="نعم").click(timeout=12000)
        page.wait_for_timeout(400)
    except Exception:
        pass

    clicked = False
    for name in ("السعر", "أفكر", "التفكير"):
        try:
            btn = page.get_by_role("button", name=name)
            if btn.count():
                btn.first.click(timeout=8000)
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        page.locator("[data-cf-reason-key]").first.click(timeout=8000)

    for _ in range(50):
        if page.locator('input[type="tel"]').count() and page.locator(
            'input[type="tel"]'
        ).last.is_visible():
            break
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=5000)
            page.wait_for_timeout(300)
        page.wait_for_timeout(200)

    try:
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=8000)
            page.wait_for_timeout(300)
        if page.locator('input[type="tel"]').count():
            page.locator('input[type="tel"]').last.fill("0598877660")
            page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
            page.wait_for_timeout(2500)
    except Exception as exc:
        entry["phone_error"] = str(exc)[:200]

    entry["reason_persist_ms"] = [round(x, 1) for x in reason_ms]
    entry["phone_persist_ms"] = [round(x, 1) for x in phone_ms]
    entry["ok"] = len(reason_ms) >= 1 and len(phone_ms) >= 1
    return entry


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    journeys = []
    reason_all: list[float] = []
    phone_all: list[float] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i in range(N):
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            try:
                entry = _one(page, i)
            except Exception as exc:
                entry = {"i": i, "ok": False, "error": str(exc)[:300]}
            journeys.append(entry)
            reason_all.extend(entry.get("reason_persist_ms") or [])
            phone_all.extend(entry.get("phone_persist_ms") or [])
            print("journey", i, entry, flush=True)
            page.close()
            context.close()
        browser.close()

    report = {
        "audit": "Widget Journey V2.2 production persist timing",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_journeys": N,
        "reason_persist": _dist(reason_all),
        "phone_persist": _dist(phone_all),
        "journeys": journeys,
    }
    (OUT / "timing_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("REASON", report["reason_persist"], flush=True)
    print("PHONE", report["phone_persist"], flush=True)
    return 0 if reason_all and phone_all else 2


if __name__ == "__main__":
    raise SystemExit(main())
