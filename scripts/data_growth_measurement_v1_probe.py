# -*- coding: utf-8 -*-
"""Read-only Data Growth Measurement v1 probe — outputs JSON report."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "scripts" / "_data_growth_measurement_v1_out"
OUT_FILE = OUT_DIR / "measurement_report.json"
PROD_PARTIAL_FILE = OUT_DIR / "production_partial_report.json"
DEFAULT_PROBE_BASE = "https://smartreplyai.net"


def _fetch_remote_report(base: str) -> dict | None:
    url = base.rstrip("/") + "/dev/data-growth-measurement"
    req = urllib.request.Request(url, headers={"User-Agent": "cartflow-growth-measure/1"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                body["data_source"] = "production_dev_endpoint"
                body["probe_base"] = base
                return body
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print(f"Remote fetch HTTP {exc.code}: {url}", flush=True)
    except OSError as exc:
        print(f"Remote fetch failed: {exc}", flush=True)
    return None


def _fetch_production_partial(base: str) -> dict:
    """Partial counts from existing production dev/health endpoints."""
    out: dict = {"probe_base": base, "data_source": "production_partial_probes"}
    try:
        with urllib.request.urlopen(base + "/dev/recovery-health", timeout=60) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        by_status = (health.get("failed_detail") or {}).get("by_status") or {}
        schedule_total = sum(int(v) for v in by_status.values())
        out["recovery_schedules"] = {
            "status_breakdown": by_status,
            "estimated_total_rows": schedule_total,
            "scheduled": health.get("scheduled"),
            "running": health.get("running"),
            "cancelled": health.get("cancelled"),
        }
    except OSError as exc:
        out["recovery_schedules"] = {"error": str(exc)}

    timeline_stores: dict[str, int] = {}
    max_row_id = 0
    sample_keys = [
        "cartflow-42b491:cf_cart_3fa3805f-a539-4d35-a228-4370b86c9780",
        "pvgate-c6e1e1-f19d35:cf_cart_2f7d4efb-5eb5-4dc7-be78-861e35692a11",
    ]
    for rk in sample_keys:
        try:
            q = urllib.parse.urlencode({"recovery_key": rk})
            with urllib.request.urlopen(
                base + f"/dev/recovery-truth?{q}", timeout=60
            ) as resp:
                truth = json.loads(resp.read().decode("utf-8"))
            slug = rk.split(":")[0]
            persistence = truth.get("persistence") or {}
            timeline_stores[slug] = int(persistence.get("rows_store_slug") or 0)
            for ev in truth.get("timeline") or []:
                rid = int(ev.get("row_id") or 0)
                if rid > max_row_id:
                    max_row_id = rid
        except OSError:
            continue
    out["recovery_truth_timeline_events"] = {
        "max_row_id_observed": max_row_id,
        "estimated_minimum_total_rows": max_row_id,
        "sample_store_slug_counts": timeline_stores,
    }
    return out


def main() -> int:
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("SECRET_KEY", "data-growth-measurement-v1")

    base = (os.environ.get("CARTFLOW_PROBE_BASE") or DEFAULT_PROBE_BASE).strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    remote = _fetch_remote_report(base)
    if remote:
        OUT_FILE.write_text(
            json.dumps(remote, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote production report {OUT_FILE}")
        return 0

    partial = _fetch_production_partial(base)
    PROD_PARTIAL_FILE.write_text(
        json.dumps(partial, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote production partial {PROD_PARTIAL_FILE}")

    import models  # noqa: F401
    from extensions import db, get_database_url, init_database
    from services.data_growth_measurement_v1 import build_data_growth_measurement_report

    db_url = (os.environ.get("DATABASE_URL") or "").strip() or get_database_url()
    init_database(db_url)

    report = build_data_growth_measurement_report(db.session)
    report["data_source"] = "local_database"
    report["database_url_hint"] = (
        db_url.split("@")[-1][:80] if "@" in db_url else db_url[:80]
    )
    report["production_partial"] = partial
    report["note"] = (
        "Full production counts require DATABASE_URL on Railway shell or "
        "deploy GET /dev/data-growth-measurement"
    )

    OUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote local report {OUT_FILE}")
    print(f"dialect={report.get('database_dialect')} tables={len(report.get('tables', []))}")
    for t in report.get("tables", []):
        print(
            f"  {t['table']}: rows={t['row_count']} "
            f"7d={t['rows_added_last_7_days']} risk={t['risk_score']}"
        )
    snap = report.get("dashboard_snapshot_accumulation") or {}
    print(
        f"snapshots: total={snap.get('total_rows')} "
        f"historical_only={snap.get('historical_only_rows')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
