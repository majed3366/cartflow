# -*- coding: utf-8 -*-
"""Widget Configuration Trust Recovery v1 — parity, fail-closed, diagnostics."""
from __future__ import annotations

import unittest
from pathlib import Path

from extensions import db
from fastapi.testclient import TestClient

from main import app
from services.widget_config_cache import update_from_dashboard_store_row
from services.widget_configuration_trust_v1 import (
    build_configuration_parity_report,
    build_widget_configuration_trust_report,
    validate_root_causes_v1,
)

_ROOT = Path(__file__).resolve().parent.parent
_STATIC = _ROOT / "static"


class WidgetConfigurationTrustRecoveryV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def _dashboard_store_slug(self) -> str:
        db.create_all()
        from main import _ensure_default_store_for_recovery  # noqa: PLC0415

        _ensure_default_store_for_recovery()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200, r.text)
        zid = (r.json() or {}).get("zid_store_id")
        self.assertIsInstance(zid, str)
        self.assertTrue(str(zid).strip(), zid)
        return str(zid).strip()

    def test_unresolved_slug_public_config_fails_closed(self) -> None:
        slug = "cf-trust-unresolved-v1-xyz"
        r = self.client.get(
            "/api/cartflow/public-config",
            params={"store_slug": slug},
        )
        self.assertEqual(r.status_code, 422, r.text)
        body = r.json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "store_identity_unresolved")
        self.assertIsNone(body.get("canonical_store_slug"))

    def test_unresolved_slug_ready_fails_closed(self) -> None:
        slug = "cf-trust-unresolved-ready-v1"
        r = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": slug, "session_id": "sess-trust-v1"},
        )
        self.assertEqual(r.status_code, 422, r.text)
        body = r.json()
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "store_identity_unresolved")

    def test_sandbox_demo_slug_still_serves_config(self) -> None:
        r = self.client.get(
            "/api/cartflow/public-config",
            params={"store_slug": "demo"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"), r.json())

    def test_dashboard_public_config_parity_after_save(self) -> None:
        ss = self._dashboard_store_slug()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "widget_name": "TRUST-PARITY-NAME",
                "widget_primary_color": "#AABBCC",
                "widget_style": "bold",
                "exit_intent_template_mode": "custom",
                "exit_intent_custom_text": "Trust custom exit copy",
                "widget_trigger_config": {
                    "exit_intent_enabled": True,
                    "hesitation_trigger_enabled": True,
                    "hesitation_after_seconds": 42,
                },
                "cartflow_widget_enabled": True,
                "cartflow_widget_delay_value": 3,
                "cartflow_widget_delay_unit": "minutes",
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        row = db.session.query(
            __import__("models", fromlist=["Store"]).Store
        ).filter_by(zid_store_id=ss).first()
        self.assertIsNotNone(row)
        update_from_dashboard_store_row(row)
        report = build_configuration_parity_report(row, storefront_slug=ss)
        self.assertTrue(report.get("ok"), report)
        self.assertTrue(report.get("parity_pass"), report.get("mismatches"))

    def test_root_cause_validation_structure(self) -> None:
        rc = validate_root_causes_v1()
        self.assertEqual(rc.get("version"), "widget_configuration_trust_recovery_v1")
        causes = rc.get("root_causes") or {}
        for key in (
            "RC1_client_demo_fallback",
            "RC2_platform_permalink_resolution",
            "RC3_identity_alias_gaps",
            "RC4_dual_enable_ownership",
            "RC5_runtime_execution_gaps",
            "RC6_cache_stickiness",
            "RC7_canonical_slug_split",
        ):
            self.assertIn(key, causes)
            self.assertIn(causes[key].get("status"), ("fixed", "partially_fixed", "still_active"))

    def test_trust_report_includes_closure_criteria(self) -> None:
        ss = self._dashboard_store_slug()
        from main import _dashboard_recovery_store_row  # noqa: PLC0415

        row = _dashboard_recovery_store_row()
        report = build_widget_configuration_trust_report(row, storefront_slug=ss)
        self.assertTrue(report.get("ok"))
        self.assertIn("closure_criteria", report)
        self.assertIn("visibility_diagnostics", report)

    def test_v2_shell_applies_widget_style_classes(self) -> None:
        shell = (_STATIC / "cartflow_widget_runtime" / "cartflow_widget_shell.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("applyChromeStyleClasses", shell)
        self.assertIn("cf-widget-style-", shell)
        self.assertIn("widget_chrome_style", shell)

    def test_v2_flows_exit_intent_template_from_config(self) -> None:
        flows = (_STATIC / "cartflow_widget_runtime" / "cartflow_widget_flows.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("getExitIntentOpeningText", flows)
        self.assertIn("exit_intent_custom_text", flows)
        self.assertIn("exit_intent_template_mode", flows)

    def test_production_storefront_never_demo_fallback_in_fetch(self) -> None:
        fetch_js = (
            _STATIC / "cartflow_widget_runtime" / "cartflow_widget_fetch.js"
        ).read_text(encoding="utf-8")
        slug_js = (_STATIC / "cartflow_storefront_store_slug.js").read_text(encoding="utf-8")
        self.assertIn("isProductionStorefrontContext", fetch_js)
        self.assertIn("production_storefront_unresolved", slug_js)
        self.assertIn("UNRESOLVED PRODUCTION STOREFRONT", fetch_js)


if __name__ == "__main__":
    unittest.main()
