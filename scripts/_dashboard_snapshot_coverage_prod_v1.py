# -*- coding: utf-8 -*-
"""
Dashboard Snapshot Coverage V1 — Living Store production verification.

Checks Home summary snapshot presence for demo + eligibility notes.
Does not change Home behavior beyond waiting for builder coverage.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "dashboard_snapshot_coverage_v1"


def _summary_probe(page) -> dict[str, Any]:
    return page.evaluate(
        """async () => {
          const t0 = performance.now();
          const r = await fetch('/api/dashboard/summary?home_perf=1&_=' + Date.now(), {
            credentials: 'same-origin', cache: 'no-store'
          });
          const j = await r.json().catch(() => ({}));
          const snap = j._snapshot || {};
          const tl = j._home_perf_timeline_v1 || {};
          return {
            http: r.status,
            api_ms: Math.round(performance.now() - t0),
            store_slug: j.store_slug || null,
            snapshot_reason: j.snapshot_reason || snap.reason || null,
            snapshot_degraded: j.snapshot_degraded ?? snap.degraded ?? null,
            snapshot_stale: j.snapshot_stale ?? snap.stale ?? null,
            snapshot_version: snap.version ?? null,
            snapshot_generated_at: snap.generated_at ?? null,
            snapshot_read_ms: snap.read_ms ?? null,
            has_persisted_row: !!(snap.generated_at || (snap.version && snap.version > 0)),
            home_surface_mode: j.home_surface_mode || null,
            hes_ok: !!(j.home_executive_summary_v1 && (j.home_executive_summary_v1.sections||[]).length),
            timeline_notes: tl.notes || [],
            timeline_total_ms: tl.total_ms ?? null,
            top_stage: ((tl.top_stages||[])[0]||{}).stage || null,
          };
        }"""
    )


def _truth(page, slug: str = "demo") -> dict[str, Any]:
    return page.evaluate(
        """async (slug) => {
          const r = await fetch('/dev/snapshot-truth-diagnostics?store=' + encodeURIComponent(slug), {
            credentials: 'same-origin', cache: 'no-store'
          });
          const j = await r.json().catch(() => ({}));
          return { http: r.status, body: j };
        }""",
        slug,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "foundation": "dashboard_snapshot_coverage_v1",
        "base": BASE,
        "phase": "after_or_verify",
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
            "email": body.get("email"),
            "merchant_id": body.get("merchant_id"),
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_SESSION"
            (OUT / "prod_coverage_verify.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, indent=2))
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
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ar-SA")
        ctx.add_cookies([cookie])
        page = ctx.new_page()
        page.goto(f"{BASE}/dashboard#home", timeout=120000)
        try:
            page.wait_for_selector('[data-hes="1"]', timeout=90000)
        except Exception:
            page.wait_for_timeout(8000)

        samples = []
        # Immediate
        samples.append({"label": "immediate", **_summary_probe(page)})
        report["snapshot_truth"] = _truth(page, "demo")

        # Wait for builder tick (interval ~45s) if still missing
        if samples[0].get("snapshot_reason") == "no_snapshot" or not samples[0].get(
            "has_persisted_row"
        ):
            report["waited_for_builder_s"] = 75
            time.sleep(75)
            samples.append({"label": "after_builder_wait", **_summary_probe(page)})
            report["snapshot_truth_after_wait"] = _truth(page, "demo")
        else:
            report["waited_for_builder_s"] = 0
            samples.append({"label": "repeat", **_summary_probe(page)})

        page.screenshot(path=str(OUT / "prod_coverage_home.png"), full_page=False)
        ctx.close()
        browser.close()

    report["samples"] = samples
    last = samples[-1]
    report["checks"] = {
        "living_store_demo": report["review_session"].get("store_slug") == "demo",
        "has_persisted_summary_row": bool(last.get("has_persisted_row")),
        "not_no_snapshot": last.get("snapshot_reason") != "no_snapshot",
        "home_still_fast_or_ok": (last.get("api_ms") or 99999) < 2000,
        "hes_present": bool(last.get("hes_ok")),
    }
    report["verdict"] = (
        "PASS_SNAPSHOT_COVERAGE_V1"
        if all(report["checks"].values())
        else "FAIL_SNAPSHOT_COVERAGE_V1"
    )
    out = OUT / "prod_coverage_verify.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"], "last": last}, indent=2))
    return 0 if str(report["verdict"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
