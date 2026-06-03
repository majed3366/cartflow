# -*- coding: utf-8 -*-
"""Core widget settings wired to storefront runtime (enable + name)."""
from __future__ import annotations

import json
import pathlib
import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import Store
from services.cartflow_widget_trigger_settings import widget_trigger_config_from_store_row

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SHELL = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_shell.js"
_CONFIG = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_config.js"
_PANEL_JS = _ROOT / "static" / "merchant_widget_panel.js"


class WidgetSettingsRuntimeTruthWiringTests(unittest.TestCase):
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

    def test_general_disable_updates_public_config_gate(self) -> None:
        ss = self._widget_public_store_slug()
        pr = self.client.post(
            "/api/recovery-settings",
            json={
                "cartflow_widget_enabled": False,
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertFalse(pub.get("cartflow_widget_enabled"))

    def test_split_columns_display_name_reaches_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        self.assertIsNotNone(row)
        row.widget_name = "مساعد المتجر"
        row.widget_display_name = "CARTFLOW"
        db.session.commit()
        from services.widget_config_cache import update_from_dashboard_store_row

        update_from_dashboard_store_row(row)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertEqual(pub.get("widget_name"), "CARTFLOW")

    def test_general_widget_name_reaches_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        pr = self.client.post(
            "/api/recovery-settings",
            json={
                "widget_name": "ودجيت الحقيقة",
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertEqual(pub.get("widget_name"), "ودجيت الحقيقة")

    def test_v2_shell_uses_merchant_brand_title(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        config = _CONFIG.read_text(encoding="utf-8")
        ui = (_ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_ui.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("function merchantShellTitle()", shell)
        self.assertIn("widget_brand_name", shell)
        self.assertIn("refreshShellVisuals", shell)
        self.assertIn("logWidgetSettingsTruth", config)
        self.assertIn("WIDGET SETTINGS TRUTH", config)
        self.assertIn("restampPrimaryButtons", ui)
        flows = (_ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_flows.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("bootTriggersAfterConfig", flows)

    def test_merchant_widget_panel_preserves_brand_line(self) -> None:
        panel = _PANEL_JS.read_text(encoding="utf-8")
        self.assertNotIn('t.widget_brand_line_ar = "";', panel)
        self.assertIn("widget_brand_line_ar", panel)

    def test_widget_panel_save_keeps_brand_line_in_db(self) -> None:
        db.create_all()
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        self.assertIsNotNone(row)
        before = widget_trigger_config_from_store_row(row)
        before["widget_brand_line_ar"] = "سطر العلامة"
        row.cf_widget_trigger_settings_json = json.dumps(before, ensure_ascii=False)
        db.session.commit()
        r = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={"widget_name": "اختبار"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.expire(row)
        refreshed = db.session.get(Store, row.id)
        assert refreshed is not None
        after = widget_trigger_config_from_store_row(refreshed)
        self.assertEqual(after.get("widget_brand_line_ar"), "سطر العلامة")


if __name__ == "__main__":
    unittest.main()
