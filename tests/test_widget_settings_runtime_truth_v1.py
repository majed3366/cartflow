# -*- coding: utf-8 -*-
"""Widget settings runtime truth — dashboard vs public-config vs beacon."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from extensions import db
from models import Store
from services.widget_settings_runtime_truth_v1 import (
    build_admin_widget_runtime_mismatch_alerts,
    evaluate_widget_settings_runtime_truth,
    runtime_widget_settings_from_beacon,
)

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_CONFIG = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_config.js"


class WidgetSettingsRuntimeTruthServiceTests(unittest.TestCase):
    def test_runtime_beacon_maps_settings(self) -> None:
        beacon = {
            "runtime_truth": {
                "widget_enabled": False,
                "exit_intent_enabled": True,
                "hesitation_trigger_enabled": False,
                "exit_intent_frequency": "per_24h",
                "delay_configured_value": 10,
                "delay_configured_unit": "minutes",
                "delay_configured_ms": 600_000,
            }
        }
        rt = runtime_widget_settings_from_beacon(beacon)
        self.assertFalse(rt["enabled"])
        self.assertTrue(rt["exit_intent"])
        self.assertFalse(rt["hesitation"])
        self.assertEqual(rt["frequency"], "per_24h")
        self.assertEqual(rt["delay_value"], 10)
        self.assertEqual(rt["delay_unit"], "minutes")
        self.assertEqual(rt["delay_ms"], 600_000)

    def test_evaluate_pending_without_beacon(self) -> None:
        db.create_all()
        slug = f"truth-pending-{uuid.uuid4().hex[:8]}"
        row = Store(zid_store_id=slug)
        row.cartflow_widget_enabled = True
        row.cf_widget_trigger_settings_json = json.dumps(
            {
                "exit_intent_enabled": False,
                "hesitation_trigger_enabled": True,
                "exit_intent_frequency": "per_session",
            },
            ensure_ascii=False,
        )
        db.session.add(row)
        db.session.commit()
        report = evaluate_widget_settings_runtime_truth(
            row,
            storefront_slug=slug,
        )
        self.assertEqual(report["status"], "pending")
        self.assertTrue(report["passed"])
        self.assertIn("enabled", report["dashboard"])
        self.assertFalse(report["dashboard"]["exit_intent"])

    def test_evaluate_mismatch_when_beacon_differs(self) -> None:
        db.create_all()
        slug = f"truth-mismatch-{uuid.uuid4().hex[:8]}"
        row = Store(zid_store_id=slug)
        row.cartflow_widget_enabled = True
        row.cf_widget_trigger_settings_json = json.dumps(
            {"exit_intent_enabled": True, "exit_intent_frequency": "per_session"},
            ensure_ascii=False,
        )
        row.widget_last_beacon_json = json.dumps(
            {
                "store_slug": slug,
                "runtime_truth": {
                    "widget_enabled": True,
                    "exit_intent_enabled": False,
                    "hesitation_trigger_enabled": True,
                    "exit_intent_frequency": "per_session",
                    "delay_configured_value": 0,
                    "delay_configured_unit": "minutes",
                },
            },
            ensure_ascii=False,
        )
        db.session.add(row)
        db.session.commit()
        report = evaluate_widget_settings_runtime_truth(
            row,
            storefront_slug=slug,
        )
        self.assertEqual(report["status"], "mismatch")
        self.assertFalse(report["passed"])
        settings = {m["setting"] for m in report.get("mismatches") or []}
        self.assertIn("exit_intent", settings)

    def test_admin_runtime_mismatch_alert(self) -> None:
        db.create_all()
        slug = f"alert-{uuid.uuid4().hex[:8]}"
        row = Store(zid_store_id=slug)
        row.cartflow_widget_enabled = False
        row.widget_last_beacon_json = json.dumps(
            {
                "store_slug": slug,
                "runtime_truth": {"widget_enabled": True},
            },
            ensure_ascii=False,
        )
        db.session.add(row)
        db.session.commit()
        alerts = build_admin_widget_runtime_mismatch_alerts(
            stores=[
                {
                    "store_id": row.id,
                    "store_slug": slug,
                    "display_name": "Alert Store",
                    "widget_last_runtime_slug": slug,
                }
            ]
        )
        self.assertTrue(alerts)
        self.assertEqual(alerts[0].get("kind"), "widget_runtime_mismatch")
        recs = alerts[0].get("records") or []
        self.assertTrue(any(r.get("setting") == "enabled" for r in recs))


class WidgetSettingsRuntimeTruthEndpointTests(unittest.TestCase):
    def test_dev_widget_runtime_truth_route_registered(self) -> None:
        from main import app  # noqa: PLC0415

        paths = {getattr(r, "path", "") for r in app.routes}
        self.assertIn("/dev/widget-runtime-truth", paths)

    def test_dev_route_in_allowlist(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT  # noqa: PLC0415

        self.assertIn("/dev/widget-runtime-truth", _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT)

    def test_storefront_logs_runtime_truth_tags(self) -> None:
        text = _CONFIG.read_text(encoding="utf-8")
        for tag in (
            "[CF ENABLE TRUTH]",
            "[CF EXIT INTENT TRUTH]",
            "[CF HESITATION TRUTH]",
            "[CF DELAY TRUTH]",
            "[CF FREQUENCY TRUTH]",
        ):
            self.assertIn(tag, text)
        self.assertIn("runtime_truth: runtimeTruth", text)


if __name__ == "__main__":
    unittest.main()
