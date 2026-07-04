# -*- coding: utf-8 -*-
"""
Production safety verification for Snapshot Generation Optimization v1.

Exercises the real production generation path (write_dashboard_snapshot_guarded,
the function the builder calls) against a throwaway SQLite DB, for all six
snapshot types, and proves:

  * tick 1 WRITEs (first build), tick 2 (unchanged) SKIPs — no identical append
  * identical-but-stale -> TOUCH (freshness refreshed in place, no new row)
  * volatile-only churn -> still SKIP (SG-6)
  * decoded latest payload identical before/after (read-neutral)
  * metrics report: rows_written / rows_avoided / write_reduction_pct / by_reason
  * kill switch CARTFLOW_SNAPSHOT_CHANGE_GATE=0 -> old append behavior returns
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_db_path = os.path.join(tempfile.gettempdir(), "cartflow_snapopt_verify.db")
if os.path.exists(_db_path):
    os.remove(_db_path)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ.pop("CARTFLOW_SNAPSHOT_CHANGE_GATE", None)

import models  # noqa: E402,F401
from extensions import db, init_database  # noqa: E402

init_database()
db.create_all()

from models import DashboardSnapshot  # noqa: E402
from services.dashboard_snapshot_v1 import (  # noqa: E402
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_REFRESH_STATE,
    SNAPSHOT_TYPE_STORE_CONNECTION,
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    SNAPSHOT_TYPE_DASHBOARD_CARDS,
    canonical_snapshot_store_slug,
    decode_snapshot_payload,
    fetch_latest_snapshot_row,
)
from services.dashboard_snapshot_change_v1 import write_dashboard_snapshot_guarded  # noqa: E402
from services.dashboard_snapshot_generation_metrics_v1 import (  # noqa: E402
    reset_snapshot_generation_metrics,
    snapshot_generation_metrics_report,
)

SLUG = "verify-store"


def _count(stype: str) -> int:
    canon = canonical_snapshot_store_slug(store_slug=SLUG)
    return (
        db.session.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.store_slug == canon,
            DashboardSnapshot.snapshot_type == stype,
        )
        .count()
    )


def _latest_payload(stype: str) -> dict:
    row = fetch_latest_snapshot_row(store_slug=SLUG, snapshot_type=stype)
    return decode_snapshot_payload(row) if row is not None else {}


# Realistic, semantically-stable payloads for the 6 builder types. The volatile
# fields (merchant_counter_generated_at / counter_generated_at /
# merchant_time_relative_ar / merchant_followup_next_line_ar) intentionally
# CHANGE between tick 1 and tick 2 to prove they don't count as change.
def _payloads(counter_ts: str, rel: str, eta: str) -> dict[str, dict]:
    return {
        SNAPSHOT_TYPE_SUMMARY: {
            "merchant_kpi_abandoned_fmt": "12",
            "merchant_kpi_recovered_fmt": "4",
            "merchant_counter_health": {
                "counter_generated_at": counter_ts,
                "counter_snapshot_age_seconds": 3.5,
                "waiting_total": 7,
            },
            "merchant_ar_date_header": "السبت 4 يوليو",
        },
        SNAPSHOT_TYPE_DASHBOARD_CARDS: {
            "kpis": {"abandoned_today": 12, "recovered_today": 4},
            "normal_carts_stats": {"normal_cart_count": 7},
        },
        SNAPSHOT_TYPE_NORMAL_CARTS: {
            "merchant_carts_page_rows": [
                {
                    "recovery_key": "verify:s1",
                    "merchant_cart_bucket": "waiting",
                    "merchant_has_customer_phone": True,
                    "merchant_last_seen_display": "2026-07-04 00:16",
                    "next_attempt_due_at": "2026-07-04T02:00:00+00:00",
                    "merchant_time_relative_ar": rel,
                    "merchant_followup_next_line_ar": eta,
                }
            ],
            "merchant_nav_badge_abandoned": 1,
            "merchant_cart_filter_counts": {"all": 1, "attention": 1},
            "merchant_counter_generated_at": counter_ts,
        },
        SNAPSHOT_TYPE_REFRESH_STATE: {
            "merchant_dashboard_refresh_token": "verify-store:42:7:3:10",
            "merchant_dashboard_refresh_last_log_id": 42,
        },
        SNAPSHOT_TYPE_WIDGET_PANEL: {
            "merchant_widget_title_ar": "مساعد المتجر",
            "merchant_widget_installed": True,
            "merchant_widget_reason_rows": [{"label_ar": "السعر", "enabled": True}],
        },
        SNAPSHOT_TYPE_STORE_CONNECTION: {
            "store_connection": {
                "connected": True,
                "store_name": "Verify Store",
                "connected_at_ar": "٢٠٢٦-٠٧-٠١",
            }
        },
    }


def _tick(payloads: dict[str, dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for stype, payload in payloads.items():
        oc = write_dashboard_snapshot_guarded(
            store_id=None, store_slug=SLUG, snapshot_type=stype, payload=payload
        )
        out[stype] = f"{oc.mode}:{oc.reason}"
    return out


TYPES = [
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_DASHBOARD_CARDS,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_REFRESH_STATE,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    SNAPSHOT_TYPE_STORE_CONNECTION,
]


def main() -> None:
    reset_snapshot_generation_metrics()

    print("=" * 72)
    print("SNAPSHOT GENERATION OPTIMIZATION v1 — PRODUCTION SAFETY VERIFICATION")
    print("=" * 72)

    p1 = _payloads("2026-07-04T00:16:00+00:00", "منذ 5 دقائق", "الرسالة التالية خلال ساعة")
    # tick 2: volatile fields advanced, semantic content identical
    p2 = _payloads("2026-07-04T00:45:00+00:00", "منذ ساعة", "الرسالة التالية خلال 5 دقائق")

    # snapshot the exact stored payloads after tick 1 for read-identity check
    print("\n[TICK 1] (first build)")
    r1 = _tick(p1)
    for t in TYPES:
        print(f"  {t:16s} -> {r1[t]:26s} rows={_count(t)}")
    latest_after_1 = {t: _latest_payload(t) for t in TYPES}

    print("\n[TICK 2] (unchanged data; volatile fields advanced)")
    r2 = _tick(p2)
    for t in TYPES:
        print(f"  {t:16s} -> {r2[t]:26s} rows={_count(t)}")
    latest_after_2 = {t: _latest_payload(t) for t in TYPES}

    print("\n[CHECK] no identical append (row count must stay 1 per type)")
    append_ok = all(_count(t) == 1 for t in TYPES)
    for t in TYPES:
        print(f"  {t:16s} rows={_count(t)} {'OK' if _count(t) == 1 else 'FAIL'}")

    print("\n[CHECK] dashboard payload identical before/after (read-neutral)")
    read_ok = True
    for t in TYPES:
        same = latest_after_1[t] == latest_after_2[t]
        read_ok = read_ok and same
        print(f"  {t:16s} identical={same}")

    print("\n[TICK 3] identical-but-stale -> TOUCH (force summary row stale)")
    canon = canonical_snapshot_store_slug(store_slug=SLUG)
    srow = fetch_latest_snapshot_row(store_slug=SLUG, snapshot_type=SNAPSHOT_TYPE_SUMMARY)
    stale = datetime.now(timezone.utc) - timedelta(seconds=600)
    old_expires = srow.expires_at
    srow.generated_at = stale
    srow.expires_at = stale + timedelta(seconds=60)
    db.session.commit()
    oc = write_dashboard_snapshot_guarded(
        store_id=None, store_slug=SLUG, snapshot_type=SNAPSHOT_TYPE_SUMMARY, payload=p2[SNAPSHOT_TYPE_SUMMARY]
    )
    srow2 = fetch_latest_snapshot_row(store_slug=SLUG, snapshot_type=SNAPSHOT_TYPE_SUMMARY)
    touch_ok = (
        oc.mode == "touch"
        and _count(SNAPSHOT_TYPE_SUMMARY) == 1
        and srow2.version == 1
        and srow2.expires_at.replace(tzinfo=timezone.utc) > stale
    )
    print(f"  decision={oc.mode}:{oc.reason} rows={_count(SNAPSHOT_TYPE_SUMMARY)} "
          f"version={srow2.version} freshness_refreshed={srow2.expires_at.replace(tzinfo=timezone.utc) > stale} "
          f"{'OK' if touch_ok else 'FAIL'}")

    print("\n[METRICS] snapshot_generation report")
    rep = snapshot_generation_metrics_report()
    for k in (
        "decisions_total", "rows_written", "rows_avoided", "skips", "touches",
        "change_detection_checks", "change_detection_hit_rate_pct",
        "snapshot_skip_rate_pct", "write_reduction_pct",
    ):
        print(f"  {k:34s} = {rep[k]}")
    print(f"  by_reason = {json.dumps(rep['by_reason'], ensure_ascii=False)}")

    print("\n[KILL SWITCH] CARTFLOW_SNAPSHOT_CHANGE_GATE=0 -> old append behavior")
    os.environ["CARTFLOW_SNAPSHOT_CHANGE_GATE"] = "0"
    before = _count(SNAPSHOT_TYPE_WIDGET_PANEL)
    oc_a = write_dashboard_snapshot_guarded(
        store_id=None, store_slug=SLUG, snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
        payload=p2[SNAPSHOT_TYPE_WIDGET_PANEL],
    )
    oc_b = write_dashboard_snapshot_guarded(
        store_id=None, store_slug=SLUG, snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
        payload=p2[SNAPSHOT_TYPE_WIDGET_PANEL],
    )
    after = _count(SNAPSHOT_TYPE_WIDGET_PANEL)
    kill_ok = oc_a.mode == "write" and oc_b.mode == "write" and after == before + 2
    print(f"  identical writes appended rows: {before} -> {after} "
          f"(decisions={oc_a.mode},{oc_b.mode}) {'OK' if kill_ok else 'FAIL'}")
    os.environ.pop("CARTFLOW_SNAPSHOT_CHANGE_GATE", None)

    print("\n" + "=" * 72)
    verdict = append_ok and read_ok and touch_ok and kill_ok
    print(f"OVERALL: {'PASS' if verdict else 'FAIL'}  "
          f"(no_identical_append={append_ok} read_neutral={read_ok} "
          f"touch={touch_ok} kill_switch={kill_ok})")
    print("=" * 72)


if __name__ == "__main__":
    main()
