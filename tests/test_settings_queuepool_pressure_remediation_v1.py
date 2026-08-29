# -*- coding: utf-8 -*-
"""Settings QueuePool Pressure Remediation V1 — first-load budget + schema memo."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from schema_merchant_auth import (
    ensure_merchant_auth_schema,
    reset_merchant_auth_schema_guard_for_tests,
)
from schema_production_store_bootstrap import (
    ensure_production_store_schema,
    reset_production_store_schema_bootstrap_for_tests,
)

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
STORE_JS = (ROOT / "static" / "merchant_store_connection.js").read_text(
    encoding="utf-8"
)
RECOVERY_JS = (ROOT / "static" / "merchant_recovery_policy_settings.js").read_text(
    encoding="utf-8"
)
VIP_JS = (ROOT / "static" / "merchant_vip_settings.js").read_text(encoding="utf-8")
GENERAL_JS = (ROOT / "static" / "merchant_general_settings.js").read_text(
    encoding="utf-8"
)
WA_JS = (ROOT / "static" / "merchant_whatsapp_settings.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")


class SettingsQueuepoolPressureRemediationV1Tests(unittest.TestCase):
    def test_first_load_is_sequential_two_reads(self) -> None:
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertIn('jsonGet("/api/merchant/store-connection")', SETTINGS_JS)
        self.assertIn('jsonGet("/api/recovery-settings")', SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)
        self.assertNotIn("scope=vip", SETTINGS_JS)
        self.assertNotIn("scope=general", SETTINGS_JS)
        self.assertNotIn("initExisting", SETTINGS_JS)
        self.assertIn("loadOverviewTruth", SETTINGS_JS)
        self.assertIn("paintFirstOverview", SETTINGS_JS)
        self.assertIn("initDetail", SETTINGS_JS)
        self.assertIn("opts.init !== false", SETTINGS_JS)

    def test_detail_inits_are_lazy_per_area(self) -> None:
        self.assertIn('if (id === "store")', SETTINGS_JS)
        self.assertIn("maInitStoreConnectionPage", SETTINGS_JS)
        self.assertIn("maInitWhatsappSettingsPage", SETTINGS_JS)
        self.assertIn("maInitRecoveryPolicySettingsPage", SETTINGS_JS)
        self.assertIn("maInitVipSettingsPage", SETTINGS_JS)
        self.assertIn("maInitGeneralSettingsPage", SETTINGS_JS)
        self.assertNotIn("maInitWhatsappConnectPage", SETTINGS_JS)

    def test_same_page_cache_hydrates_detail_without_refetch(self) -> None:
        self.assertIn("__cfSettingsReadCache", SETTINGS_JS)
        self.assertIn("__cfSettingsReadCache", STORE_JS)
        self.assertIn("__cfSettingsReadCache", RECOVERY_JS)
        self.assertIn("__cfSettingsReadCache", VIP_JS)
        self.assertIn("__cfSettingsReadCache", GENERAL_JS)
        self.assertIn("__cfSettingsReadCache", WA_JS)

    def test_protected_surfaces_untouched(self) -> None:
        for blob in (HOME_JS, CARTS_JS, COMMS_JS, WS_JS):
            self.assertNotIn("settings-queuepool-pressure-remediation-v1", blob)
            self.assertNotIn("__cfSettingsReadCache", blob)

    def test_recovery_settings_default_carries_overview_truth(self) -> None:
        src = (
            ROOT / "main.py"
        ).read_text(encoding="utf-8")
        self.assertIn("merchant_vip_settings_fields_for_api(row)", src)
        self.assertIn("merchant_general_settings_fields_for_api(row)", src)
        self.assertIn(
            "Settings V2 overview uses this default GET once",
            src,
        )

    def test_verified_schema_ensure_skips_inspect(self) -> None:
        reset_production_store_schema_bootstrap_for_tests()
        self.assertTrue(ensure_production_store_schema(db, context="test"))
        with patch(
            "schema_production_store_bootstrap.verify_production_store_schema"
        ) as mock_verify:
            self.assertTrue(ensure_production_store_schema(db, context="hot"))
            mock_verify.assert_not_called()

    def test_merchant_auth_ensure_skips_verify_when_memoized(self) -> None:
        reset_merchant_auth_schema_guard_for_tests()
        self.assertTrue(ensure_merchant_auth_schema(db))
        with patch("schema_merchant_auth.verify_merchant_auth_schema") as mock_verify:
            self.assertTrue(ensure_merchant_auth_schema(db))
            mock_verify.assert_not_called()

    def test_dashboard_still_hosts_settings_composition(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("merchant_ui_v2_settings.js", html)
            self.assertIn("qpool1", html)
            self.assertIn('data-cf-settings-composition="v1"', html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev


if __name__ == "__main__":
    unittest.main()
