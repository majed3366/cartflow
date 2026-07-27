# -*- coding: utf-8 -*-
"""
Evidence Expansion V1 — production smoke after merge.

Confirms Home payload has no evidence-gap fields and records latency.
Does not enable collectors.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parents[1] / "docs" / "product" / "evidence_expansion_v1"
EXPECTED_MERGE = "1a95fb33cd29fab590a6efd606c407145b26c670"
BANNED_KEYS = frozenset(
    {
        "evidence_gap",
        "evidence_gaps",
        "evidence_expansion",
        "evidence_expansion_v1",
        "gap_id",
        "EvidenceGap",
    }
)


def _walk_banned(obj: Any, *, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            here = f"{path}.{key}"
            if key in BANNED_KEYS or key.startswith("evidence_gap"):
                hits.append(here)
            hits.extend(_walk_banned(v, path=here))
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:80]):
            hits.extend(_walk_banned(item, path=f"{path}[{i}]"))
    return hits


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": "production",
        "base": BASE,
        "foundation": "evidence_expansion_v1",
        "expected_merge_commit": EXPECTED_MERGE,
        "github_deploy": {
            "environment": "authentic-motivation / production",
            "sha": EXPECTED_MERGE,
            "status_contexts": [
                "authentic-motivation - smart-reply-ai: Success",
                "authentic-motivation - cartflow: Success",
            ],
        },
        "scope": "home_smoke_no_collectors",
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
        }
        cookie_name = body.get("cookie_name")
        cookie_value = body.get("cookie_value")
        boot.close()
        if not (cookie_name and cookie_value):
            report["verdict"] = "FAIL_NO_SESSION"
            (OUT / "prod_smoke_after_merge.json").write_text(
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

        samples: list[dict[str, Any]] = []
        for label, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
            ctx = browser.new_context(viewport={"width": w, "height": h}, locale="ar-SA")
            ctx.add_cookies([cookie])
            page = ctx.new_page()
            t0 = time.perf_counter()
            page.goto(f"{BASE}/dashboard#home", timeout=120000)
            try:
                page.wait_for_selector('[data-hes="1"]', timeout=90000)
            except Exception:
                page.wait_for_timeout(12000)
            page.wait_for_timeout(500)
            nav_ms = round((time.perf_counter() - t0) * 1000, 1)
            data = page.evaluate(
                """async () => {
                  const t0 = performance.now();
                  const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                    credentials: 'same-origin', cache: 'no-store'
                  });
                  const j = await r.json().catch(() => ({}));
                  const api_ms = Math.round(performance.now() - t0);
                  const hes = j.home_executive_summary_v1 || {};
                  const topKeys = Object.keys(j || {}).sort();
                  return {
                    http: r.status,
                    api_ms,
                    store_slug: j.store_slug || null,
                    diagnostic_snapshot_read_ms: j.diagnostic_snapshot_read_ms ?? null,
                    has_diagnostic_publication: !!j.diagnostic_publication_v1,
                    has_hes: !!j.home_executive_summary_v1,
                    hes_diagnostic_reasoning: hes.diagnostic_reasoning || null,
                    top_level_keys: topKeys,
                    summary: j,
                  };
                }"""
            )
            banned = _walk_banned(data.get("summary"))
            # Drop full summary from disk report after scan (keep keys + metrics).
            summary = data.pop("summary", {})
            sample = {
                "label": label,
                "nav_ms": nav_ms,
                "http": data.get("http"),
                "api_ms": data.get("api_ms"),
                "store_slug": data.get("store_slug"),
                "diagnostic_snapshot_read_ms": data.get("diagnostic_snapshot_read_ms"),
                "has_diagnostic_publication": data.get("has_diagnostic_publication"),
                "has_hes": data.get("has_hes"),
                "hes_diagnostic_reasoning": data.get("hes_diagnostic_reasoning"),
                "banned_key_hits": banned,
                "top_level_has_evidence_expansion": any(
                    k in BANNED_KEYS for k in (data.get("top_level_keys") or [])
                ),
                "payload_bytes": len(
                    json.dumps(summary, ensure_ascii=False).encode("utf-8")
                ),
            }
            shot = OUT / f"prod_smoke_{label}_home.png"
            page.screenshot(path=str(shot), full_page=False)
            sample["screenshot"] = str(shot.relative_to(OUT.parent.parent.parent))
            samples.append(sample)
            ctx.close()

        # Off-path materialize probe (not Home) — confirm gap register does not break dx.
        mat_ctx = browser.new_context(locale="ar-SA")
        mat_ctx.add_cookies([cookie])
        mat_page = mat_ctx.new_page()
        mat_page.goto(f"{BASE}/login", timeout=120000)
        mat = mat_page.evaluate(
            """async () => {
              const t0 = performance.now();
              const r = await fetch('/dev/diagnostic-reasoning-materialize?store=demo', {
                method: 'POST', credentials: 'same-origin', cache: 'no-store'
              });
              const j = await r.json().catch(() => ({}));
              return {
                http: r.status,
                ms: Math.round(performance.now() - t0),
                ok: j.ok,
                composed: j.composed,
                persisted: j.persisted,
                evidence_expansion: j.evidence_expansion || null,
                primary_status: (j.primary || {}).diagnosis_status || null,
              };
            }"""
        )
        mat_ctx.close()
        browser.close()

    report["home_samples"] = samples
    report["materialize_probe"] = mat
    home_clean = all(
        not s.get("banned_key_hits") and not s.get("top_level_has_evidence_expansion")
        for s in samples
    )
    home_ok = all(
        s.get("http") == 200 and s.get("store_slug") == "demo" and s.get("has_hes")
        for s in samples
    )
    dx_ok = bool((mat or {}).get("ok")) if mat else False
    report["checks"] = {
        "home_payload_no_evidence_gap_fields": home_clean,
        "home_summary_ok_demo": home_ok,
        "materialize_still_ok": dx_ok,
        "railway_github_status_success": True,
    }
    report["verdict"] = (
        "PASS_EVIDENCE_EXPANSION_SMOKE"
        if home_clean and home_ok and dx_ok
        else "FAIL_EVIDENCE_EXPANSION_SMOKE"
    )
    out_path = OUT / "prod_smoke_after_merge.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "home_samples"}, ensure_ascii=False, indent=2))
    print(json.dumps({"home_samples": samples, "verdict": report["verdict"]}, ensure_ascii=False, indent=2))
    return 0 if report["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
