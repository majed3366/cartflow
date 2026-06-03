# -*- coding: utf-8 -*-
"""Widget settings end-to-end truth audit — locks known dashboard/runtime gaps."""
from __future__ import annotations

import pathlib
import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app
from services.cartflow_widget_public_bundle import merge_widget_template_bundle_from_store_row
from services.merchant_general_settings import apply_merchant_general_settings_from_body
from models import Store

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_FLOWS = _RUNTIME / "cartflow_widget_flows.js"
_SHELL = _RUNTIME / "cartflow_widget_shell.js"
_CONFIG = _RUNTIME / "cartflow_widget_config.js"
_PANEL_JS = _ROOT / "static" / "merchant_widget_panel.js"
_BUNDLE_PY = _ROOT / "services" / "cartflow_widget_public_bundle.py"


class WidgetSettingsRuntimeTruthAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def _widget_public_store_slug(self) -> str:
        db.create_all()
        from main import _ensure_default_store_for_recovery  # noqa: PLC0415

        _ensure_default_store_for_recovery()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200, r.text)
        zid = (r.json() or {}).get("zid_store_id")
        self.assertIsInstance(zid, str)
        self.assertTrue((zid or "").strip(), zid)
        return zid.strip()

    def test_public_bundle_excludes_general_settings_only_fields(self) -> None:
        bundle = merge_widget_template_bundle_from_store_row(None)
        self.assertNotIn("widget_enabled", bundle)
        self.assertNotIn("widget_display_name", bundle)
        self.assertIn("cartflow_widget_enabled", bundle)
        self.assertIn("widget_name", bundle)

    def test_general_widget_enabled_maps_to_public_gate(self) -> None:
        ss = self._widget_public_store_slug()
        pr = self.client.post(
            "/api/recovery-settings",
            json={
                "widget_enabled": False,
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertTrue(pub.get("ok"), pub)
        self.assertFalse(pub.get("cartflow_widget_enabled"))

    def test_widget_color_reaches_public_config_after_dashboard_save(self) -> None:
        ss = self._widget_public_store_slug()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={"widget_primary_color": "#AABBCC"},
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertEqual(pub.get("widget_primary_color"), "#AABBCC")

    def test_v2_runtime_reads_color_and_gate_from_config_module(self) -> None:
        cfg = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("cartflow_widget_enabled", cfg)
        self.assertIn("widget_primary_color", cfg)
        self.assertIn("applyMerchantGate", cfg)
        self.assertIn("applyVisual", cfg)

    def test_v2_flows_use_primary_hex_from_merchant_config(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("function primaryHex()", flows)
        self.assertIn("widget_primary_color", flows)

    def test_widget_style_not_applied_in_v2_shell(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        config = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("widget_chrome_style", config)
        self.assertNotIn("widget_chrome_style", shell)
        self.assertNotIn("widget_style", shell)

    def test_widget_name_applied_to_shell_header(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        config = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("widget_brand_name", config)
        self.assertIn("merchantShellTitle", shell)
        self.assertIn("widget_brand_name", shell)

    def test_recovery_question_hardcoded_not_exit_intent_template(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("function getCartRecoveryQuestion()", flows)
        self.assertIn("تبي أساعدك تكمل طلبك؟", flows)
        self.assertNotIn("exit_intent_custom_text", flows)
        self.assertNotIn("exit_intent_template_mode", flows)

    def test_merchant_widget_panel_does_not_clear_brand_line_on_save(self) -> None:
        panel = _PANEL_JS.read_text(encoding="utf-8")
        self.assertNotIn('t.widget_brand_line_ar = "";', panel)

    def test_public_bundle_source_documents_customization_fields(self) -> None:
        src = _BUNDLE_PY.read_text(encoding="utf-8")
        self.assertIn("widget_customization_fields_for_api", src)
        self.assertNotIn("merchant_general_settings_fields_for_api", src)


if __name__ == "__main__":
    unittest.main()
