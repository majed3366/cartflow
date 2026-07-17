# -*- coding: utf-8 -*-
"""Merchant Home Experience M1 activation — transport-independent summary contract tests."""
from __future__ import annotations

import os
import unittest

from services.dashboard_snapshot_change_v1 import write_dashboard_snapshot_guarded
from services.dashboard_snapshot_read_v1 import (
    _degraded_summary_payload,
    build_summary_from_snapshot,
)
from services.dashboard_snapshot_v1 import SNAPSHOT_TYPE_SUMMARY
from services.merchant_home_experience_activation_v1 import (
    SUMMARY_CONTRACT_SCHEMA_VERSION,
    TRANSPORT_DEGRADED,
    TRANSPORT_LIVE,
    TRANSPORT_SNAPSHOT,
    ensure_merchant_home_experience_on_summary,
    finalize_dashboard_summary_payload,
    summary_snapshot_contract_stale,
)


class MerchantHomeExperienceActivationTests(unittest.TestCase):
    def test_degraded_summary_receives_home_experience(self) -> None:
        body = _degraded_summary_payload(reason="no_snapshot")
        out = ensure_merchant_home_experience_on_summary(
            body,
            summary_source=TRANSPORT_DEGRADED,
            store_slug="demo",
        )
        home = out.get("merchant_home_experience_v1") or {}
        self.assertTrue(home.get("ok"))
        self.assertIn("greeting", home)
        self.assertIn("while_away", home)
        self.assertIn("attention_today", home)
        self.assertIn("store_understanding", home)
        self.assertIn("quick_nav", home)
        self.assertEqual(
            out.get("summary_contract_schema_version"),
            SUMMARY_CONTRACT_SCHEMA_VERSION,
        )
        diag = out.get("_merchant_home_transport") or {}
        self.assertTrue(diag.get("merchant_home_experience_attached"))
        self.assertEqual(diag.get("summary_source"), TRANSPORT_DEGRADED)

    def test_compose_from_embedded_daily_brief(self) -> None:
        body = {
            "merchant_ar_date_header": "الأحد 6 يوليو",
            "merchant_nav_badge_abandoned": 2,
            "normal_carts_stats": {"normal_cart_count": 5},
            "merchant_daily_brief_v1": {
                "ok": True,
                "version": "v2",
                "achievements": [
                    {
                        "headline_ar": "تم إرسال رسالة",
                        "why_ar": "أُرسلت رسالة استرجاع واحدة بنجاح.",
                        "aggregation_key": "ach:1",
                    }
                ],
                "attention_items": [],
            },
            "merchant_setup_experience": {"merchant_store_display_name": "متجر تجريبي"},
        }
        out = finalize_dashboard_summary_payload(
            {"ok": True, **body},
            summary_source=TRANSPORT_SNAPSHOT,
            store_slug="demo",
        )
        home = out["merchant_home_experience_v1"]
        self.assertTrue(home.get("ok"))
        self.assertEqual(len((home.get("while_away") or {}).get("items") or []), 1)
        diag = out.get("_merchant_home_transport") or {}
        self.assertEqual(diag.get("home_attach_mode"), "composed_from_summary")

    def test_idempotent_when_home_already_present(self) -> None:
        existing = {
            "ok": True,
            "version": "v1",
            "greeting": {"greeting_ar": "صباح الخير", "merchant_name_ar": "X"},
            "while_away": {"items": []},
            "attention_today": {"items": []},
            "store_understanding": {"items": []},
            "quick_nav": {"items": []},
        }
        body = {
            "merchant_home_experience_v1": existing,
            "summary_contract_schema_version": SUMMARY_CONTRACT_SCHEMA_VERSION,
        }
        out = ensure_merchant_home_experience_on_summary(
            body,
            summary_source=TRANSPORT_LIVE,
        )
        self.assertIs(out["merchant_home_experience_v1"], existing)
        self.assertEqual(
            (out.get("_merchant_home_transport") or {}).get("home_attach_mode"),
            "present",
        )

    def test_summary_snapshot_contract_stale_detects_pre_m1(self) -> None:
        self.assertTrue(summary_snapshot_contract_stale({}))
        self.assertTrue(
            summary_snapshot_contract_stale(
                {"merchant_kpi_abandoned_fmt": "0", "merchant_nav_badge_abandoned": 0}
            )
        )
        self.assertFalse(
            summary_snapshot_contract_stale(
                {
                    "summary_contract_schema_version": SUMMARY_CONTRACT_SCHEMA_VERSION,
                    "merchant_home_experience_v1": {"ok": True},
                }
            )
        )

    def test_snapshot_read_path_attaches_home_when_missing(self) -> None:
        os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_MODE"] = "1"
        try:
            from extensions import db
            from models import DashboardSnapshot
            from services.dashboard_snapshot_v1 import (
                SNAPSHOT_TYPE_SUMMARY,
                upsert_dashboard_snapshot,
            )

            db.session.query(DashboardSnapshot).delete()
            db.session.commit()
            slug = "m1-act-test-store"
            upsert_dashboard_snapshot(
                store_id=1,
                store_slug=slug,
                snapshot_type=SNAPSHOT_TYPE_SUMMARY,
                payload={
                    "merchant_ar_date_header": "test",
                    "merchant_nav_badge_abandoned": 0,
                    "normal_carts_stats": {"normal_cart_count": 0},
                },
                generation_reason="test_pre_m1",
            )
            db.session.commit()
            out = build_summary_from_snapshot(store_slug=slug)
        finally:
            os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_MODE", None)

        self.assertTrue((out.get("merchant_home_experience_v1") or {}).get("ok"))
        self.assertEqual(
            (out.get("_merchant_home_transport") or {}).get("summary_source"),
            TRANSPORT_SNAPSHOT,
        )

    def test_snapshot_write_forces_upgrade_for_stale_contract(self) -> None:
        os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_CHANGE_GATE"] = "1"
        try:
            from extensions import db
            from models import DashboardSnapshot
            from services.dashboard_snapshot_v1 import (
                SNAPSHOT_TYPE_SUMMARY,
                upsert_dashboard_snapshot,
            )

            db.session.query(DashboardSnapshot).delete()
            db.session.commit()
            slug = "m1-act-upgrade-store"
            upsert_dashboard_snapshot(
                store_id=1,
                store_slug=slug,
                snapshot_type=SNAPSHOT_TYPE_SUMMARY,
                payload={"merchant_kpi_abandoned_fmt": "0"},
                generation_reason="test_pre_m1",
            )
            db.session.commit()
            outcome = write_dashboard_snapshot_guarded(
                store_id=1,
                store_slug=slug,
                snapshot_type=SNAPSHOT_TYPE_SUMMARY,
                payload={
                    "summary_contract_schema_version": SUMMARY_CONTRACT_SCHEMA_VERSION,
                    "merchant_home_experience_v1": {"ok": True, "version": "v1"},
                    "merchant_kpi_abandoned_fmt": "0",
                },
            )
        finally:
            os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_CHANGE_GATE", None)

        self.assertEqual(outcome.mode, "write")
        self.assertEqual(outcome.reason, "summary_contract_upgrade")


if __name__ == "__main__":
    unittest.main()
