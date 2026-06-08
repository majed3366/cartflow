# -*- coding: utf-8 -*-
"""Temporary diagnostic for «واتساب جاهز» checklist audit."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from extensions import db
from models import Store
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_readiness_diagnostic_v1 import (
    build_whatsapp_readiness_diagnostic_temp,
)


class MerchantWhatsappReadinessDiagnosticV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self.zid = f"wa_diag_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            store_whatsapp_number="+966500000222",
            whatsapp_recovery_enabled=True,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_diagnostic_exposes_failing_sandbox_condition(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        diag = ev.get("readiness_diagnostic_temp") or {}
        self.assertTrue(diag.get("temporary"))
        item = diag.get("checklist_item") or {}
        self.assertFalse(item.get("complete"))
        self.assertEqual(item.get("mark_ar"), "✗")
        failing = diag.get("failing_conditions") or []
        fields = {f.get("field") for f in failing}
        self.assertIn("flags.sandbox_mode_active", fields)
        self.assertIn("sandbox_merchant_setup_complete_override", fields)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_merchant_api_includes_diagnostic_temp(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        self.assertIn("readiness_diagnostic_temp", ev)
        self.assertEqual(
            (ev["readiness_diagnostic_temp"].get("checklist_item") or {}).get("label_ar"),
            "واتساب جاهز",
        )

    def test_js_renders_diagnostic_panel(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("readiness_diagnostic_temp", js)
        self.assertIn("renderReadinessDiagnosticTemp", js)


if __name__ == "__main__":
    unittest.main()
