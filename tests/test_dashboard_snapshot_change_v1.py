# -*- coding: utf-8 -*-
"""
Snapshot Generation Optimization v1 tests.

Covers Snapshot Generation Governance contracts:
  SG-2  identical payload never appends a new row
  SG-6  volatile-only differences do not count as change
  SG-7  identical-but-stale -> in-place freshness touch (no new row)
  SG-4  generation metrics (writes executed / avoided / hit rate / skip rate)
Read-neutrality: after a skip, the latest row still returns identical content.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from extensions import db
from models import DashboardSnapshot
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_SUMMARY,
    canonical_snapshot_store_slug,
    decode_snapshot_payload,
    fetch_latest_snapshot_row,
)
from services.dashboard_snapshot_change_v1 import (
    VOLATILE_SNAPSHOT_KEYS,
    generation_policy_for,
    semantic_snapshot_fingerprint,
    write_dashboard_snapshot_guarded,
)
from services.dashboard_snapshot_generation_metrics_v1 import (
    reset_snapshot_generation_metrics,
    snapshot_generation_metrics_report,
)

_SLUG = "chg-optim-store"


def _rows(slug: str, stype: str) -> list[DashboardSnapshot]:
    canon = canonical_snapshot_store_slug(store_slug=slug)
    return (
        db.session.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.store_slug == canon,
            DashboardSnapshot.snapshot_type == stype,
        )
        .all()
    )


class SemanticFingerprintTests(unittest.TestCase):
    def test_identical_payload_same_fingerprint(self) -> None:
        a = {"kpis": {"abandoned_today": 3}, "x": [1, 2, 3]}
        b = {"x": [1, 2, 3], "kpis": {"abandoned_today": 3}}  # different key order
        self.assertEqual(
            semantic_snapshot_fingerprint(a, snapshot_type=SNAPSHOT_TYPE_SUMMARY),
            semantic_snapshot_fingerprint(b, snapshot_type=SNAPSHOT_TYPE_SUMMARY),
        )

    def test_volatile_only_difference_is_not_change(self) -> None:
        base = {
            "kpis": {"abandoned_today": 3},
            "merchant_counter_generated_at": "2026-07-04T00:00:00+00:00",
            "merchant_counter_health": {
                "counter_generated_at": "2026-07-04T00:00:00+00:00",
                "counter_snapshot_age_seconds": 1.2,
                "waiting_total": 5,
            },
            "merchant_carts_page_rows": [
                {
                    "recovery_key": "rk-1",
                    "merchant_cart_bucket": "waiting",
                    "merchant_time_relative_ar": "منذ 5 دقائق",
                    "merchant_followup_next_line_ar": "الرسالة التالية خلال ساعة",
                    "merchant_last_seen_display": "2026-07-04 00:00",
                }
            ],
        }
        volatile_changed = {
            "kpis": {"abandoned_today": 3},
            "merchant_counter_generated_at": "2026-07-04T09:99:99+00:00",
            "merchant_counter_health": {
                "counter_generated_at": "2026-07-04T09:00:00+00:00",
                "counter_snapshot_age_seconds": 44.0,
                "waiting_total": 5,
            },
            "merchant_carts_page_rows": [
                {
                    "recovery_key": "rk-1",
                    "merchant_cart_bucket": "waiting",
                    "merchant_time_relative_ar": "منذ ساعة",
                    "merchant_followup_next_line_ar": "الرسالة التالية خلال 5 دقائق",
                    "merchant_last_seen_display": "2026-07-04 00:00",
                }
            ],
        }
        self.assertEqual(
            semantic_snapshot_fingerprint(base, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS),
            semantic_snapshot_fingerprint(
                volatile_changed, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS
            ),
        )

    def test_semantic_difference_changes_fingerprint(self) -> None:
        base = {"kpis": {"abandoned_today": 3}}
        changed_kpi = {"kpis": {"abandoned_today": 4}}
        self.assertNotEqual(
            semantic_snapshot_fingerprint(base, snapshot_type=SNAPSHOT_TYPE_SUMMARY),
            semantic_snapshot_fingerprint(changed_kpi, snapshot_type=SNAPSHOT_TYPE_SUMMARY),
        )

    def test_meaningful_row_change_detected(self) -> None:
        base = {
            "merchant_carts_page_rows": [
                {"recovery_key": "rk-1", "merchant_has_customer_phone": False}
            ]
        }
        phone_added = {
            "merchant_carts_page_rows": [
                {"recovery_key": "rk-1", "merchant_has_customer_phone": True}
            ]
        }
        self.assertNotEqual(
            semantic_snapshot_fingerprint(base, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS),
            semantic_snapshot_fingerprint(phone_added, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS),
        )

    def test_absolute_last_seen_change_detected(self) -> None:
        # merchant_last_seen_display is an ABSOLUTE timestamp (kept), so a real
        # "customer returned" event must still be treated as a change.
        base = {
            "merchant_carts_page_rows": [
                {"recovery_key": "rk-1", "merchant_last_seen_display": "2026-07-04 00:00"}
            ]
        }
        returned = {
            "merchant_carts_page_rows": [
                {"recovery_key": "rk-1", "merchant_last_seen_display": "2026-07-04 06:30"}
            ]
        }
        self.assertNotEqual(
            semantic_snapshot_fingerprint(base, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS),
            semantic_snapshot_fingerprint(returned, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS),
        )


class GuardedWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        for r in _rows(_SLUG, SNAPSHOT_TYPE_SUMMARY):
            db.session.delete(r)
        db.session.commit()
        reset_snapshot_generation_metrics()

    def tearDown(self) -> None:
        for r in _rows(_SLUG, SNAPSHOT_TYPE_SUMMARY):
            db.session.delete(r)
        db.session.commit()

    def _write(self, payload: dict, **kw):
        return write_dashboard_snapshot_guarded(
            store_id=None,
            store_slug=_SLUG,
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload=payload,
            **kw,
        )

    def test_first_build_writes(self) -> None:
        out = self._write({"kpis": {"abandoned_today": 1}})
        self.assertEqual(out.mode, "write")
        self.assertEqual(out.reason, "first_build")
        self.assertEqual(len(_rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)), 1)

    def test_identical_payload_skipped(self) -> None:
        self._write({"kpis": {"abandoned_today": 1}})
        out = self._write({"kpis": {"abandoned_today": 1}})
        self.assertEqual(out.mode, "skip")
        self.assertEqual(out.reason, "identical_skip")
        self.assertEqual(len(_rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)), 1)
        # version did not advance
        self.assertEqual(_rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)[0].version, 1)

    def test_volatile_only_change_skipped(self) -> None:
        self._write({
            "kpis": {"abandoned_today": 1},
            "merchant_counter_generated_at": "2026-07-04T00:00:00+00:00",
        })
        out = self._write({
            "kpis": {"abandoned_today": 1},
            "merchant_counter_generated_at": "2026-07-04T09:00:00+00:00",
        })
        self.assertEqual(out.mode, "skip")
        self.assertEqual(len(_rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)), 1)

    def test_semantic_change_writes_new_version(self) -> None:
        self._write({"kpis": {"abandoned_today": 1}})
        out = self._write({"kpis": {"abandoned_today": 2}})
        self.assertEqual(out.mode, "write")
        self.assertEqual(out.reason, "content_change")
        rows = _rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)
        self.assertEqual(len(rows), 2)
        self.assertEqual(max(r.version for r in rows), 2)

    def test_identical_but_stale_touches_in_place(self) -> None:
        self._write({"kpis": {"abandoned_today": 1}})
        row = _rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)[0]
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=600)
        row.generated_at = stale_time
        row.expires_at = stale_time + timedelta(seconds=60)
        db.session.commit()

        out = self._write({"kpis": {"abandoned_today": 1}})
        self.assertEqual(out.mode, "touch")
        self.assertEqual(out.reason, "failsafe_touch")
        rows = _rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)
        self.assertEqual(len(rows), 1)  # no new row
        refreshed = rows[0]
        self.assertGreater(refreshed.expires_at.replace(tzinfo=timezone.utc), stale_time)
        self.assertEqual(refreshed.version, 1)

    def test_gate_disabled_always_writes(self) -> None:
        self._write({"kpis": {"abandoned_today": 1}}, apply_change_gate=False)
        out = self._write({"kpis": {"abandoned_today": 1}}, apply_change_gate=False)
        self.assertEqual(out.mode, "write")
        self.assertEqual(out.reason, "gate_disabled")
        self.assertEqual(len(_rows(_SLUG, SNAPSHOT_TYPE_SUMMARY)), 2)

    def test_read_neutrality_after_skip(self) -> None:
        payload = {"kpis": {"abandoned_today": 7}, "note": "hello"}
        self._write(payload)
        self._write(payload)  # skip
        latest = fetch_latest_snapshot_row(
            store_slug=_SLUG, snapshot_type=SNAPSHOT_TYPE_SUMMARY
        )
        self.assertIsNotNone(latest)
        self.assertEqual(decode_snapshot_payload(latest), payload)

    def test_metrics_reflect_reduction(self) -> None:
        self._write({"kpis": {"abandoned_today": 1}})   # write (first_build)
        self._write({"kpis": {"abandoned_today": 1}})   # skip
        self._write({"kpis": {"abandoned_today": 1}})   # skip
        self._write({"kpis": {"abandoned_today": 2}})   # write (change)
        report = snapshot_generation_metrics_report()
        self.assertEqual(report["decisions_total"], 4)
        self.assertEqual(report["rows_written"], 2)
        self.assertEqual(report["rows_avoided"], 2)
        self.assertEqual(report["skips"], 2)
        # two change-detection checks (2nd & 3rd), both identical; 4th was a check too
        self.assertGreaterEqual(report["change_detection_checks"], 3)
        self.assertGreater(report["write_reduction_pct"], 0.0)


class GenerationPolicyTests(unittest.TestCase):
    def test_dashboard_cards_derives_from_summary(self) -> None:
        from services.dashboard_snapshot_v1 import SNAPSHOT_TYPE_DASHBOARD_CARDS

        policy = generation_policy_for(SNAPSHOT_TYPE_DASHBOARD_CARDS)
        self.assertEqual(policy.derived_from, SNAPSHOT_TYPE_SUMMARY)

    def test_all_active_types_have_gate_enabled_by_default(self) -> None:
        from services.dashboard_snapshot_v1 import (
            SNAPSHOT_TYPE_REFRESH_STATE,
            SNAPSHOT_TYPE_STORE_CONNECTION,
            SNAPSHOT_TYPE_WIDGET_PANEL,
        )

        for stype in (
            SNAPSHOT_TYPE_SUMMARY,
            SNAPSHOT_TYPE_NORMAL_CARTS,
            SNAPSHOT_TYPE_REFRESH_STATE,
            SNAPSHOT_TYPE_WIDGET_PANEL,
            SNAPSHOT_TYPE_STORE_CONNECTION,
        ):
            self.assertTrue(generation_policy_for(stype).change_gate_enabled)

    def test_volatile_set_contains_known_fields(self) -> None:
        for key in (
            "merchant_counter_generated_at",
            "counter_generated_at",
            "merchant_time_relative_ar",
            "merchant_followup_next_line_ar",
        ):
            self.assertIn(key, VOLATILE_SNAPSHOT_KEYS)


if __name__ == "__main__":
    unittest.main()
