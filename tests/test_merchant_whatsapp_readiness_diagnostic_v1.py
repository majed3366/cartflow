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
    evaluate_whatsapp_connection_readiness,
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

    def _sandbox_flags(self) -> dict:
        return {
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

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_diagnostic_builder_exposes_failing_sandbox_condition(
        self, mock_ob: object
    ) -> None:
        flags = self._sandbox_flags()
        mock_ob.return_value = flags
        ev = evaluate_whatsapp_connection_readiness(self.row, onboarding=flags)
        diag = build_whatsapp_readiness_diagnostic_temp(
            ev,
            self.row,
            action_first={},
            onboarding_flags=dict(flags["flags"]),
            blocking_steps=[],
        )
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
    def test_merchant_api_excludes_diagnostic_temp(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        self.assertNotIn("readiness_diagnostic_temp", ev)

    def test_js_hides_diagnostic_panel_from_merchants(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertNotIn("تشخيص مؤقت", js)
        self.assertIn("function renderReadinessDiagnosticTemp", js)

    def test_admin_route_includes_diagnostic_builder(self) -> None:
        from pathlib import Path

        src = Path("routes/admin_operations.py").read_text(encoding="utf-8")
        self.assertIn("build_whatsapp_readiness_diagnostic_temp", src)
        self.assertIn("readiness_diagnostic_temp", src)


if __name__ == "__main__":
    unittest.main()
