# -*- coding: utf-8 -*-
"""
Home Performance Hardening V1 — Living Store production measurement.

Cold / warm / repeat × Desktop / Mobile with ``?home_perf=1`` timeline.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "home_performance_hardening_v1"


def _sample(page, label: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    data = page.evaluate(
        """async () => {
          const t0 = performance.now();
          const r = await fetch('/api/dashboard/summary?home_perf=1&_=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          const j = await r.json().catch(() => ({}));
          const api_ms = Math.round(performance.now() - t0);
          const tl = j._home_perf_timeline_v1 || null;
          const snap = j._snapshot || {};
          return {
            http: r.status,
            api_ms,
            store_slug: j.store_slug || null,
            diagnostic_snapshot_read_ms: j.diagnostic_snapshot_read_ms ?? null,
            snapshot_stale: j.snapshot_stale ?? snap.stale ?? null,
            snapshot_degraded: j.snapshot_degraded ?? snap.degraded ?? null,
            snapshot_read_ms: snap.read_ms ?? null,
            snapshot_route_ms: snap.route_ms ?? null,
            home_surface_mode: j.home_surface_mode || null,
            hes_diagnostic_reasoning: ((j.home_executive_summary_v1||{}).diagnostic_reasoning)||null,
            has_evidence_gap_fields: Object.keys(j).some(k => k.includes('evidence_gap') || k === 'evidence_expansion'),
            timeline: tl ? {
              total_ms: tl.total_ms,
              top_stages: tl.top_stages,
              notes: tl.notes,
              stage_count: tl.stage_count,
            } : null,
          };
        }"""
    )
    data["label"] = label
    data["wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
    return data


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "foundation": "home_performance_hardening_v1",
        "base": BASE,
        "baseline_before_ms": {
            "source": "evidence_expansion_v1/prod_smoke_after_merge.json",
            "desktop_api_ms": 3327,
            "mobile_api_ms": 3297,
            "diagnostic_snapshot_read_ms": 13.8,
        },
        "samples": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        boot = browser.new_page(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        boot.goto(f"{BASE}/login", timeout=120000)
        session = boot.evaluate(
            """async () => {
              const r = await fetch('/dev/living-store-home-review-session', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              return { http: r.status, body: await r.json().catch(() => ({})) };
            }"""
        )
        body = session.get("body") or {}
        report["review_session"] = {
            "http": session.get("http"),
            "ok": body.get("ok"),
            "store_slug": body.get("store_slug"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_SESSION"
            (OUT / "prod_measure.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2
        cookie = {
            "name": cookie_name,
            "value": cookie_value,
            "domain": "smartreplyai.net",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }

        for mode, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            try:
                page.wait_for_selector('[data-hes="1"]', timeout=90000)
            except Exception:
                page.wait_for_timeout(8000)
            # Cold (first timed fetch after nav may be warm from boot — still capture)
            cold = _sample(page, f"{mode}_cold")
            warm = _sample(page, f"{mode}_warm")
            repeat = _sample(page, f"{mode}_repeat")
            report["samples"].extend([cold, warm, repeat])
            page.screenshot(path=str(OUT / f"prod_{mode}_home.png"), full_page=False)
            ctx.close()
        browser.close()

    apis = [s.get("api_ms") for s in report["samples"] if s.get("api_ms") is not None]
    report["summary"] = {
        "api_ms_min": min(apis) if apis else None,
        "api_ms_max": max(apis) if apis else None,
        "api_ms_avg": round(sum(apis) / len(apis), 1) if apis else None,
        "timelines_present": sum(1 for s in report["samples"] if s.get("timeline")),
    }
    # Success: warm/repeat under 500ms server timeline total OR clear dominant stage removed
    warm_apis = [
        s["api_ms"]
        for s in report["samples"]
        if s["label"].endswith("_warm") or s["label"].endswith("_repeat")
    ]
    report["checks"] = {
        "home_perf_timeline_present": report["summary"]["timelines_present"] >= 2,
        "warm_faster_than_baseline_3_3s": all(
            (a or 99999) < 2000 for a in warm_apis
        )
        if warm_apis
        else False,
        "no_evidence_gap_fields": all(
            not s.get("has_evidence_gap_fields") for s in report["samples"]
        ),
    }
    report["verdict"] = (
        "PASS_HOME_PERFORMANCE_HARDENING_V1"
        if report["checks"]["home_perf_timeline_present"]
        and report["checks"]["warm_faster_than_baseline_3_3s"]
        and report["checks"]["no_evidence_gap_fields"]
        else "FAIL_HOME_PERFORMANCE_HARDENING_V1"
    )
    out = OUT / "prod_measure.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"], "checks": report["checks"]}, indent=2))
    for s in report["samples"]:
        top = ((s.get("timeline") or {}).get("top_stages") or [])[:3]
        print(
            f"{s['label']}: api_ms={s.get('api_ms')} timeline_total="
            f"{(s.get('timeline') or {}).get('total_ms')} top={top}"
        )
    return 0 if str(report["verdict"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
