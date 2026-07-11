# -*- coding: utf-8 -*-
"""Poll production for v2-widget-interaction-trust-v1 then record 5 journeys."""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://smartreplyai.net"
TARGET = "v2-widget-interaction-trust-v1b"
OUT = Path(__file__).resolve().parent / "_widget_interaction_trust_v1_out"


def poll_deploy(rounds: int = 36, sleep_s: float = 15.0) -> bool:
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(rounds):
        try:
            req = urllib.request.Request(
                f"{BASE}/static/widget_loader.js?_ts={int(time.time()*1000)}",
                headers={"Cache-Control": "no-cache"},
            )
            body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            ok = TARGET in body
            print(f"poll {i} trust_runtime={ok}", flush=True)
            if ok:
                flows = urllib.request.urlopen(
                    urllib.request.Request(
                        f"{BASE}/static/cartflow_widget_runtime/cartflow_widget_flows.js?_ts={int(time.time()*1000)}",
                        headers={"Cache-Control": "no-cache"},
                    ),
                    timeout=30,
                ).read().decode("utf-8", "replace")
                print("REASON_ACK", "[CF REASON ACK]" in flows, flush=True)
                (OUT / "deploy_ok.json").write_text(
                    json.dumps(
                        {
                            "deployed": True,
                            "runtime": TARGET,
                            "at": datetime.now(timezone.utc).isoformat(),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print("DEPLOY_OK", flush=True)
                return True
        except Exception as exc:
            print(f"poll {i} err {exc}", flush=True)
        time.sleep(sleep_s)
    print("DEPLOY_TIMEOUT", flush=True)
    return False


def _signup(page) -> dict:
    uid = uuid.uuid4().hex[:10]
    email = f"cf.trust.{uid}@smartreplyai.net"
    password = f"CfTrust!{uid[:8]}"
    page.goto(f"{BASE}/signup", timeout=120000)
    page.wait_for_timeout(2000)
    page.locator('input[name="store_name"]').fill(f"Trust {uid[:6]}")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.get_by_role("button", name="إنشاء الحساب").click()
    page.wait_for_timeout(5000)
    return {"email": email, "ok": "/login" not in page.url, "url": page.url}


def _run_one_journey(page, i: int) -> dict:
    entry: dict = {"i": i, "ok": False}
    console: list[str] = []
    reason_posts_before_phone = 0
    phone_phase = False

    def on_console(m) -> None:
        t = m.text or ""
        if "[CF REASON" in t or "[CF PHONE" in t:
            console.append(t)

    def on_req(req) -> None:
        nonlocal reason_posts_before_phone
        if phone_phase:
            return
        if req.method == "POST" and "/api/cartflow/reason" in req.url:
            reason_posts_before_phone += 1

    page.on("console", on_console)
    page.on("request", on_req)

    auth = _signup(page)
    entry["auth"] = auth
    if not auth["ok"]:
        entry["error"] = f"auth_failed:{auth['url']}"
        return entry

    page.goto(f"{BASE}/dashboard/test-widget", timeout=120000)
    page.wait_for_timeout(5000)

    added = False
    for sel in (
        'button:has-text("أضف إلى السلة")',
        'button:has-text("أضف")',
        'button:has-text("Add")',
        "[data-product-add]",
    ):
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            loc.click(timeout=15000)
            added = True
            break
    entry["add_to_cart"] = added
    page.wait_for_timeout(3000)

    page.wait_for_function('typeof window.__cfV2ShowNow === "function"', timeout=90000)
    page.evaluate("window.__cfV2ShowNow()")
    page.wait_for_timeout(1200)

    try:
        page.get_by_role("button", name="نعم").click(timeout=15000)
        page.wait_for_timeout(500)
    except Exception:
        pass

    # Measure ack: click then immediately poll selected attribute
    t0 = time.perf_counter()
    reason_clicked = False
    for name in ("السعر", "أفكر", "التفكير", "price"):
        try:
            btn = page.get_by_role("button", name=name)
            if btn.count():
                btn.first.click(timeout=10000)
                reason_clicked = True
                break
        except Exception:
            continue
    if not reason_clicked:
        page.locator("[data-cf-reason-key]").first.click(timeout=10000)
        reason_clicked = True
    entry["reason_clicked"] = reason_clicked

    # Poll selection within ~150ms window (ack target <100ms; allow measurement slack)
    selected = 0
    ack_ms = None
    for _ in range(30):
        selected = page.locator("[data-cf-reason-selected='1']").count()
        if selected >= 1:
            ack_ms = round((time.perf_counter() - t0) * 1000, 1)
            break
        page.wait_for_timeout(5)
    if ack_ms is None:
        ack_ms = round((time.perf_counter() - t0) * 1000, 1)
    entry["ack_selected_ms_dom"] = ack_ms
    entry["selected_count"] = selected
    # Authoritative ack: console log from same-tick acknowledgeReasonPick
    console_ack_ms = None
    for c in console:
        if "[CF REASON ACK]" in c and "ack_ms:" in c:
            try:
                console_ack_ms = float(c.split("ack_ms:")[-1].split("}")[0].strip().rstrip(","))
            except Exception:
                pass
    entry["ack_console_ms"] = console_ack_ms

    # Wait for phone / thanks continuation
    phone_step = False
    for _ in range(50):
        try:
            if page.locator('input[type="tel"]').count() and page.locator(
                'input[type="tel"]'
            ).last.is_visible():
                phone_step = True
                break
            if page.get_by_role("button", name="شكراً").count():
                page.get_by_role("button", name="شكراً").click(timeout=5000)
                page.wait_for_timeout(400)
        except Exception:
            pass
        page.wait_for_timeout(200)
    entry["phone_step"] = phone_step

    phone_saved = False
    phone_confirm = False
    try:
        if page.get_by_role("button", name="شكراً").count():
            page.get_by_role("button", name="شكراً").click(timeout=8000)
            page.wait_for_timeout(400)
        if page.locator('input[type="tel"]').count():
            page.locator('input[type="tel"]').last.fill("0598877660")
            # Wait reason POST settled so phone merge is not counted as duplicate reason click
            for _ in range(40):
                if reason_posts_before_phone >= 1:
                    break
                page.wait_for_timeout(100)
            phone_phase = True
            t_phone = time.perf_counter()
            page.get_by_role("button", name="حفظ الرقم").click(timeout=20000)
            # Immediate busy/ack footer or disabled save
            for _ in range(40):
                body = page.evaluate(
                    """() => {
                      const f = document.querySelector('[data-cf-footer-msg], .cf-footer-msg, #cf-footer-msg');
                      const t = (f && f.textContent) || (document.body.innerText || '');
                      return t.slice(0, 500);
                    }"""
                )
                if "جاري الحفظ" in body or "تم حفظ" in body:
                    entry["phone_ack_ms"] = round((time.perf_counter() - t_phone) * 1000, 1)
                    if "تم حفظ" in body:
                        phone_confirm = True
                    break
                page.wait_for_timeout(25)
            page.wait_for_timeout(1500)
            body2 = page.evaluate("() => (document.body.innerText || '').slice(0, 800)")
            if "تم حفظ" in body2 or "سنتابع" in body2:
                phone_confirm = True
            if any("PHONE SAVE ACK SUCCESS" in c for c in console):
                phone_confirm = True
            phone_saved = True
    except Exception as exc:
        entry["phone_error"] = str(exc)[:300]

    entry["phone_saved"] = phone_saved
    entry["phone_confirm"] = phone_confirm
    entry["reason_posts_before_phone"] = reason_posts_before_phone
    entry["console_hits"] = [c for c in console if "ACK" in c or "PHONE" in c][:12]
    entry["ok"] = (
        reason_clicked
        and selected >= 1
        and console_ack_ms is not None
        and console_ack_ms < 100
        and reason_posts_before_phone == 1
        and phone_saved
        and phone_confirm
    )
    return entry


def record_journeys(n: int = 5) -> dict:
    from playwright.sync_api import sync_playwright

    vid_dir = OUT / "videos"
    if vid_dir.exists():
        for old in vid_dir.glob("*.webm"):
            try:
                old.unlink()
            except Exception:
                pass
    vid_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "journeys": [],
        "runtime": TARGET,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for i in range(n):
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(vid_dir),
                record_video_size={"width": 1280, "height": 800},
            )
            page = context.new_page()
            entry: dict = {"i": i, "ok": False}
            try:
                entry = _run_one_journey(page, i)
            except Exception as exc:
                entry["error"] = str(exc)[:400]
            report["journeys"].append(entry)
            page.close()
            context.close()
            vids = sorted(vid_dir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
            # Prefer newest unnamed webm from this context
            for v in reversed(vids):
                if v.name.startswith("journey_"):
                    continue
                dest = vid_dir / f"journey_{i+1:02d}.webm"
                try:
                    if dest.exists():
                        dest.unlink()
                    v.replace(dest)
                    entry["video"] = dest.name
                except Exception:
                    entry["video"] = v.name
                break
            else:
                named = vid_dir / f"journey_{i+1:02d}.webm"
                if named.exists():
                    entry["video"] = named.name
            print("journey", i, entry, flush=True)
        browser.close()

    report["pass_count"] = sum(1 for j in report["journeys"] if j.get("ok"))
    report["ack_console_ms"] = [j.get("ack_console_ms") for j in report["journeys"]]
    report["reason_posts_before_phone"] = [
        j.get("reason_posts_before_phone") for j in report["journeys"]
    ]
    (OUT / "verify_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("PASS", report["pass_count"], "/", n, flush=True)
    return report


def main() -> int:
    if "--skip-poll" not in sys.argv:
        if not poll_deploy():
            return 1
    else:
        print("SKIP_POLL", flush=True)
    rep = record_journeys(5)
    return 0 if rep.get("pass_count", 0) >= 4 else 2


if __name__ == "__main__":
    raise SystemExit(main())
