# -*- coding: utf-8 -*-
"""V2.2 zero-friction prod verify: poll deploy, 5 video journeys, assert deferred loading."""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
TARGET = "v2-widget-zero-friction-v2_2"
OUT = Path(__file__).resolve().parent / "_widget_zero_friction_v2_2_out"


def poll_deploy(rounds: int = 40, sleep_s: float = 15.0) -> bool:
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
            print(f"poll {i} zero_friction={ok}", flush=True)
            if ok:
                flows = urllib.request.urlopen(
                    urllib.request.Request(
                        f"{BASE}/static/cartflow_widget_runtime/cartflow_widget_flows.js?_ts={int(time.time()*1000)}",
                        headers={"Cache-Control": "no-cache"},
                    ),
                    timeout=30,
                ).read().decode("utf-8", "replace")
                print("DEFERRED", "PERSIST_LOADING_THRESHOLD_MS = 400" in flows, flush=True)
                print("DEPLOY_OK", flush=True)
                return True
        except Exception as exc:
            print(f"poll {i} err {exc}", flush=True)
        time.sleep(sleep_s)
    print("DEPLOY_TIMEOUT", flush=True)
    return False


def _signup(page) -> dict:
    uid = uuid.uuid4().hex[:10]
    email = f"cf.zf22v.{uid}@smartreplyai.net"
    password = f"CfZf22!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"Zfv {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(4500)
    return {"ok": "/login" not in page.url, "url": page.url}


def _run(page, i: int) -> dict:
    entry: dict = {"i": i, "ok": False}
    console: list[str] = []
    page.on(
        "console",
        lambda m: console.append(m.text)
        if m.text
        and (
            "PERSIST TIMING" in m.text
            or "SLOW PATH" in m.text
            or "REASON ACK" in m.text
            or "PHONE SAVE" in m.text
        )
        else None,
    )
    auth = _signup(page)
    if not auth["ok"]:
        entry["error"] = "auth_failed"
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
    # Immediate: selected, no saving text yet
    page.wait_for_timeout(120)
    selected = page.locator("[data-cf-reason-selected='1']").count()
    early_saving = page.evaluate(
        """() => {
          const t = (document.body.innerText || '');
          const st = document.querySelector('[data-cf-reason-status]');
          return {
            body_has_saving: t.includes('جاري الحفظ'),
            status: st ? (st.textContent || '') : null,
            transition: (document.querySelector('[data-cf-reason-transition]') || {}).getAttribute
              ? document.querySelector('[data-cf-reason-transition]').getAttribute('data-cf-reason-transition')
              : null
          };
        }"""
    )
    entry["selected_count"] = selected
    entry["early_ui"] = early_saving
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
    entry["console"] = console[:20]
    has_timing = any("PERSIST TIMING" in c for c in console)
    has_ack = any("REASON ACK" in c for c in console)
    # At t≈120ms, saving must not be default (transition selected, no status yet)
    early_ok = selected >= 1 and not (early_saving or {}).get("body_has_saving")
    entry["ok"] = bool(has_ack and has_timing and early_ok)
    entry["early_ok"] = early_ok
    entry["has_timing"] = has_timing
    return entry


def record(n: int = 5) -> dict:
    from playwright.sync_api import sync_playwright

    vid = OUT / "videos"
    vid.mkdir(parents=True, exist_ok=True)
    for old in vid.glob("*.webm"):
        try:
            old.unlink()
        except Exception:
            pass
    report = {
        "runtime": TARGET,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "journeys": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i in range(n):
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(vid),
                record_video_size={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            try:
                entry = _run(page, i)
            except Exception as exc:
                entry = {"i": i, "ok": False, "error": str(exc)[:300]}
            report["journeys"].append(entry)
            page.close()
            ctx.close()
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
                    entry["video"] = dest.name
                except Exception:
                    entry["video"] = unnamed[-1].name
            print("journey", i, entry, flush=True)
        browser.close()
    report["pass_count"] = sum(1 for j in report["journeys"] if j.get("ok"))
    (OUT / "verify_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("PASS", report["pass_count"], "/", n, flush=True)
    return report


def main() -> int:
    if "--skip-poll" not in sys.argv and not poll_deploy():
        return 1
    rep = record(5)
    return 0 if rep.get("pass_count", 0) >= 4 else 2


if __name__ == "__main__":
    raise SystemExit(main())
