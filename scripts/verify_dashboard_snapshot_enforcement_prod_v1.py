# -*- coding: utf-8 -*-
"""
Production verification — dashboard snapshot enforcement (no live path, no MISS).

Requires merchant auth via env:
  CARTFLOW_PROD_EMAIL / CARTFLOW_PROD_PASSWORD

Optional Railway log scan:
  RAILWAY_TOKEN + --railway-service smart-reply-ai
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_DEFAULT = "https://smartreplyai.net"
OUT_DIR = Path(__file__).resolve().parent / "_dashboard_snapshot_enforcement_verify_v1_out"

ENFORCED_ENDPOINTS: tuple[tuple[str, str, str], ...] = (
    ("/api/dashboard/summary", "summary", "summary"),
    ("/api/dashboard/normal-carts", "normal_carts", "normal-carts"),
    ("/api/dashboard/widget-panel", "widget_panel", "widget-panel"),
    ("/api/dashboard/refresh-state", "refresh_state", "refresh-state"),
    ("/api/merchant/store-connection", "store_connection", "store-connection"),
)

LOG_MARKERS = (
    "[DASHBOARD SNAPSHOT READ]",
    "[DASHBOARD SNAPSHOT MISS]",
    "[DASHBOARD HOT PATH VIOLATION]",
)


def _fetch_json(url: str, cookie_header: str) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Cookie": cookie_header,
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return int(resp.status), json.loads(resp.read().decode())


def _login_playwright(base: str) -> tuple[str, dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if not email or not password:
        raise RuntimeError("CARTFLOW_PROD_EMAIL and CARTFLOW_PROD_PASSWORD required")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{base}/login", timeout=120000)
        page.wait_for_timeout(1500)
        page.locator('input[name="email"], input[type="email"]').first.fill(email)
        page.locator('input[name="password"], input[type="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(4000)
        page.goto(f"{base}/dashboard#home", timeout=120000)
        page.wait_for_timeout(3000)
        cookies = ctx.cookies()
        browser.close()

    cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
    return cookie_header, {"email": email, "cookie_count": len(cookies)}


def _verify_endpoint(
    *,
    base: str,
    path: str,
    snapshot_type: str,
    cookie_header: str,
) -> dict[str, Any]:
    url = f"{base}{path}?_={int(time.time())}"
    out: dict[str, Any] = {"path": path, "snapshot_type": snapshot_type}
    try:
        status, body = _fetch_json(url, cookie_header)
        out["status"] = status
        out["snapshot_mode"] = body.get("snapshot_mode")
        out["snapshot_degraded"] = body.get("snapshot_degraded")
        out["snapshot_stale"] = body.get("snapshot_stale")
        out["snapshot_reason"] = body.get("snapshot_reason")
        snap = body.get("_snapshot") or {}
        out["_snapshot"] = snap
        out["read_ok"] = bool(body.get("snapshot_mode")) and status == 200
        out["miss_like"] = body.get("snapshot_reason") == "no_snapshot"
        out["has_snapshot_row"] = not out["miss_like"] and bool(snap.get("version"))
    except urllib.error.HTTPError as exc:
        out["status"] = exc.code
        out["error"] = exc.read(400).decode("utf-8", "replace")[:300]
        out["read_ok"] = False
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:300]
        out["read_ok"] = False
    return out


def _scan_railway_logs(*, service: str, lines: int, store_slug: str) -> dict[str, Any]:
    token = (os.environ.get("RAILWAY_TOKEN") or "").strip()
    if not token:
        return {"skipped": True, "reason": "RAILWAY_TOKEN unset"}
    try:
        proc = subprocess.run(
            ["railway", "logs", "--service", service, "--lines", str(lines)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**os.environ, "RAILWAY_TOKEN": token},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return {"skipped": True, "reason": str(exc)[:200]}

    slug = store_slug.strip()
    reads = [ln for ln in text.splitlines() if "[DASHBOARD SNAPSHOT READ]" in ln and slug in ln]
    misses = [ln for ln in text.splitlines() if "[DASHBOARD SNAPSHOT MISS]" in ln and slug in ln]
    violations = [ln for ln in text.splitlines() if "[DASHBOARD HOT PATH VIOLATION]" in ln]
    return {
        "skipped": False,
        "service": service,
        "read_lines": reads[-10:],
        "miss_lines": misses[-10:],
        "violation_lines": violations[-10:],
        "read_count": len(reads),
        "miss_count": len(misses),
        "violation_count": len(violations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify dashboard snapshot enforcement in production")
    parser.add_argument("--base", default=os.environ.get("CARTFLOW_VERIFY_BASE", BASE_DEFAULT))
    parser.add_argument("--store-slug", default=os.environ.get("CARTFLOW_VERIFY_STORE_SLUG", "cartflow-42b491"))
    parser.add_argument("--railway-service", default=os.environ.get("CARTFLOW_VERIFY_RAILWAY_SERVICE", "smart-reply-ai"))
    parser.add_argument("--railway-lines", type=int, default=800)
    parser.add_argument("--skip-railway", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "base": args.base,
        "store_slug": args.store_slug,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": [],
    }

    try:
        cookie_header, auth_meta = _login_playwright(args.base)
        report["auth"] = auth_meta
    except Exception as exc:  # noqa: BLE001
        report["auth_error"] = str(exc)[:300]
        out_path = OUT_DIR / "verify_report.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        print(f"\nFAIL auth: {exc}")
        return 1

    all_ok = True
    for path, snap_type, _label in ENFORCED_ENDPOINTS:
        ep = _verify_endpoint(
            base=args.base,
            path=path,
            snapshot_type=snap_type,
            cookie_header=cookie_header,
        )
        report["endpoints"].append(ep)
        ok = bool(ep.get("read_ok")) and not bool(ep.get("miss_like"))
        print(
            f"{path}: read_ok={ep.get('read_ok')} miss_like={ep.get('miss_like')} "
            f"degraded={ep.get('snapshot_degraded')} stale={ep.get('snapshot_stale')}"
        )
        if not ok:
            all_ok = False

    if not args.skip_railway:
        report["railway_logs"] = _scan_railway_logs(
            service=args.railway_service,
            lines=args.railway_lines,
            store_slug=args.store_slug,
        )
        rl = report["railway_logs"]
        if not rl.get("skipped"):
            print(
                f"\nRailway {args.railway_service}: reads={rl.get('read_count')} "
                f"misses={rl.get('miss_count')} violations={rl.get('violation_count')}"
            )
            if rl.get("miss_count") or rl.get("violation_count"):
                all_ok = False

    out_path = OUT_DIR / "verify_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {out_path}")
    print("PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
