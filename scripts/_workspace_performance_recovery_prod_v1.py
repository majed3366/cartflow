# -*- coding: utf-8 -*-
"""
Gate 0 — Workspace Performance Recovery production parity measure.

Compares Home (?home_perf=1) vs Workspace (?workspace_perf=1) on Living Store.
Desktop + Mobile · cold / warm / repeat.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "workspace_performance_recovery_v1"
)


def _sample_home(page, label: str) -> dict[str, Any]:
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
            surface: 'home',
            http: r.status,
            api_ms,
            server_ms: tl ? tl.total_ms : null,
            slowest_stage: tl && tl.top_stages && tl.top_stages[0]
              ? tl.top_stages[0].stage : null,
            snapshot_hit: !(snap.degraded || j.snapshot_degraded),
            snapshot_stale: j.snapshot_stale ?? snap.stale ?? null,
            total_queries: tl ? tl.total_queries : null,
            timeline: tl ? {
              total_ms: tl.total_ms,
              top_stages: (tl.top_stages || []).slice(0, 5),
              notes: tl.notes || [],
            } : null,
          };
        }"""
    )
    data["label"] = label
    data["wall_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
    return data


def _sample_workspace(page, label: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    data = page.evaluate(
        """async () => {
          const t0 = performance.now();
          const r = await fetch(
            '/api/cart-workspace/v1/projection?workspace_perf=1&_=' + Date.now(),
            { credentials: 'same-origin', cache: 'no-store' }
          );
          const j = await r.json().catch(() => ({}));
          const api_ms = Math.round(performance.now() - t0);
          const tl = j._workspace_perf_timeline_v1 || null;
          const proj = j.projection || {};
          return {
            surface: 'workspace',
            http: r.status,
            api_ms,
            server_ms: tl ? tl.total_ms : null,
            slowest_stage: tl && (tl.slowest_stage || (tl.top_stages||[])[0])
              ? (tl.slowest_stage || tl.top_stages[0].stage) : null,
            paint_cache_hit: !!j.workspace_paint_cache_hit,
            durable_snapshot_hit: !!j.workspace_durable_snapshot_hit,
            serve_path: j.workspace_serve_path || null,
            package_reuse: tl && tl.meta ? !!tl.meta.package_reuse : null,
            orv_rebuilt: tl && tl.meta ? !!tl.meta.orv_rebuilt : null,
            total_queries: tl ? tl.total_queries : null,
            decision_card_count: proj.decision_card_count ?? (proj.zone_b||[]).length,
            primary_id: proj.attention_focus_decision_id || proj.highest_priority_decision_id || null,
            timeline: tl ? {
              total_ms: tl.total_ms,
              top_stages: (tl.top_stages || []).slice(0, 8),
              stages: tl.stages || [],
              meta: tl.meta || {},
              notes: tl.notes || [],
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
        "foundation": "workspace_performance_recovery_gate_0",
        "base": BASE,
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
            (OUT / "prod_parity_measure.json").write_text(
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

            for phase in ("cold", "warm", "repeat"):
                report["samples"].append(_sample_home(page, f"{mode}_home_{phase}"))
                report["samples"].append(
                    _sample_workspace(page, f"{mode}_workspace_{phase}")
                )

            page.goto(f"{BASE}/dashboard#workspace", timeout=120000)
            page.wait_for_timeout(2500)
            page.screenshot(
                path=str(OUT / f"prod_{mode}_workspace.png"), full_page=False
            )
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / f"prod_{mode}_home.png"), full_page=False)
            ctx.close()
        browser.close()

    def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
        vals = [float(r[key]) for r in rows if r.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    home = [s for s in report["samples"] if s.get("surface") == "home"]
    ws = [s for s in report["samples"] if s.get("surface") == "workspace"]
    warm_ws = [s for s in ws if s["label"].endswith("_warm") or s["label"].endswith("_repeat")]
    warm_home = [
        s for s in home if s["label"].endswith("_warm") or s["label"].endswith("_repeat")
    ]

    report["parity"] = {
        "home_warm_avg_client_ms": _avg(warm_home, "api_ms"),
        "home_warm_avg_server_ms": _avg(warm_home, "server_ms"),
        "workspace_warm_avg_client_ms": _avg(warm_ws, "api_ms"),
        "workspace_warm_avg_server_ms": _avg(warm_ws, "server_ms"),
        "workspace_durable_hit_rate": round(
            sum(1 for s in warm_ws if s.get("durable_snapshot_hit") or s.get("paint_cache_hit"))
            / max(1, len(warm_ws)),
            2,
        ),
        "workspace_orv_rebuild_rate": round(
            sum(1 for s in warm_ws if s.get("orv_rebuilt")) / max(1, len(warm_ws)),
            2,
        ),
    }
    cold_ws = [s for s in ws if s["label"].endswith("_cold")]
    report["checks"] = {
        "timelines_present": all(s.get("timeline") for s in report["samples"]),
        "cold_workspace_under_3s": all(
            (s.get("api_ms") or 99999) < 3000 for s in cold_ws
        ),
        "warm_workspace_under_2s": all(
            (s.get("api_ms") or 99999) < 2000 for s in warm_ws
        ),
        "warm_no_orv_rebuild": all(not s.get("orv_rebuilt") for s in warm_ws),
        "warm_snapshot_or_paint_hit": all(
            s.get("durable_snapshot_hit") or s.get("paint_cache_hit") for s in warm_ws
        ),
        # Architectural parity: cold must not be an order of magnitude above Home.
        "cold_workspace_near_home": (
            (_avg(cold_ws, "api_ms") or 99999)
            < max(3000.0, 3.0 * (_avg([s for s in home if s["label"].endswith("_cold")], "api_ms") or 500.0))
        ),
    }
    report["verdict"] = (
        "PASS_WORKSPACE_PERFORMANCE_RECOVERY_GATE_0"
        if report["checks"]["timelines_present"]
        and report["checks"]["cold_workspace_under_3s"]
        and report["checks"]["warm_workspace_under_2s"]
        and report["checks"]["warm_no_orv_rebuild"]
        else "FAIL_WORKSPACE_PERFORMANCE_RECOVERY_GATE_0"
    )

    out = OUT / "prod_parity_measure.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "parity": report["parity"],
                "checks": report["checks"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    for s in report["samples"]:
        print(
            f"{s['label']}: api_ms={s.get('api_ms')} server_ms={s.get('server_ms')} "
            f"path={s.get('serve_path')} durable={s.get('durable_snapshot_hit')} "
            f"paint={s.get('paint_cache_hit')} orv={s.get('orv_rebuilt')} "
            f"slowest={s.get('slowest_stage')}"
        )
    return 0 if str(report["verdict"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
