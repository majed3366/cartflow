# -*- coding: utf-8 -*-
"""Final merchant UX cleanup for completed WhatsApp journey."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from extensions import db
from models import Store
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_journey_execution_v1 import (
    CTA_ACTION_SCROLL_SETTINGS,
    CTA_CONTINUE_ACTIVATION_AR,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
)
from services.merchant_whatsapp_readiness_presentation_v1 import (
    MERCHANT_COMPLETED_HEADLINE_AR,
    MERCHANT_CTA_EDIT_SETTINGS_AR,
    MERCHANT_NO_ACTION_AR,
    MERCHANT_SENDING_STATUS_PREPARING_AR,
)


class MerchantWhatsappReadinessFinalMerchantUxV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_final_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            store_whatsapp_number="+966500000444",
            whatsapp_recovery_enabled=True,
            whatsapp_onboarding_journey=JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def _completed_ev(self) -> dict:
        with patch(
            "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
            return_value={
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
            },
        ):
            return connection_readiness_for_merchant_api(self.row)

    def test_completed_journey_does_not_show_continue_activation(self) -> None:
        ev = self._completed_ev()
        af = ev.get("action_first") or {}
        self.assertNotEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)

    def test_completed_journey_does_not_show_activation_step_copy(self) -> None:
        ev = self._completed_ev()
        af = ev.get("action_first") or {}
        self.assertNotIn("أكمل خطوة التفعيل الحالية", af.get("next_action_ar") or "")
        cb = af.get("cta_behavior") or {}
        self.assertNotIn("أكمل خطوات التفعيل للإنتاج", cb.get("inline_guidance_ar") or "")

    def test_merchant_ui_does_not_show_diagnostic_panel(self) -> None:
        ev = self._completed_ev()
        self.assertNotIn("readiness_diagnostic_temp", ev)
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertNotIn("تشخيص مؤقت", js)

    def test_merchant_ui_shows_setup_completed_headline(self) -> None:
        ev = self._completed_ev()
        ux = ev.get("merchant_completed_ux") or {}
        self.assertTrue(ux.get("active"))
        self.assertEqual(ux.get("headline_ar"), MERCHANT_COMPLETED_HEADLINE_AR)

    def test_production_sending_state_is_calm_and_separate(self) -> None:
        ev = self._completed_ev()
        prod = ev.get("production_sending_readiness") or {}
        self.assertEqual(prod.get("title_ar"), "حالة الإرسال")
        self.assertEqual(prod.get("status_ar"), MERCHANT_SENDING_STATUS_PREPARING_AR)
        self.assertIn("أكملت إعداداتك", prod.get("explanation_ar") or "")

    def test_cta_scrolls_to_settings_without_unfinished_copy(self) -> None:
        ev = self._completed_ev()
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), MERCHANT_CTA_EDIT_SETTINGS_AR)
        cb = af.get("cta_behavior") or {}
        self.assertEqual(cb.get("cta_action"), CTA_ACTION_SCROLL_SETTINGS)
        self.assertEqual(cb.get("inline_guidance_ar"), "")
        self.assertEqual(af.get("next_action_ar"), MERCHANT_NO_ACTION_AR)

    def test_admin_diagnostics_remain_available(self) -> None:
        from services.merchant_whatsapp_readiness_diagnostic_v1 import (
            build_whatsapp_readiness_diagnostic_temp,
        )

        ev = self._completed_ev()
        diag = build_whatsapp_readiness_diagnostic_temp(
            ev,
            self.row,
            action_first=ev.get("action_first") or {},
            onboarding_flags={
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            blocking_steps=[],
        )
        self.assertTrue(diag.get("temporary"))
        admin_src = Path("routes/admin_operations.py").read_text(encoding="utf-8")
        self.assertIn("readiness_diagnostic_temp", admin_src)

    def test_status_monitor_card_reworded_in_template(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        self.assertIn("تفاصيل الحالة", html)
        self.assertNotIn("الحالة والمراقبة — قراءة فقط", html)
        self.assertIn("ma-wa-status-monitor-card", html)


if __name__ == "__main__":
    unittest.main()
