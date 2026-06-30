# -*- coding: utf-8 -*-
"""WhatsApp Merchant Experience V2 — business decision page."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from extensions import db
from models import Store
from services.merchant_whatsapp_mode_v1 import (
    ADVANCED_SETTINGS_TITLE_AR,
    SAVE_SUCCESS_MESSAGE_AR,
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_CTA_AR,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    merchant_whatsapp_mode_fields_for_api,
    whatsapp_current_path_for_api,
)


class MerchantWhatsappExperienceV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_v2_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_main_copy_has_no_meta_in_cartflow_path(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        path = fields["whatsapp_current_path"]
        self.assertNotIn("Meta", path["message_ar"])
        for opt in fields["whatsapp_mode_selection"]["options"]:
            if opt["key"] == WHATSAPP_MODE_CARTFLOW_MANAGED:
                joined = " ".join(opt.get("bullets_ar") or [])
                self.assertNotIn("Meta", joined)

    def test_merchant_mode_advanced_panel_still_available_in_api(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        panel = fields["whatsapp_mode_merchant_panel"]
        self.assertTrue(panel.get("visible"))
        self.assertIn("meta_pairing_status_ar", panel)
        self.assertIn("embedded_signup_status_ar", panel)

    def test_save_success_message(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertEqual(fields["whatsapp_save_success_message_ar"], SAVE_SUCCESS_MESSAGE_AR)

    def test_advanced_settings_title(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertEqual(
            fields["whatsapp_advanced_settings_title_ar"], ADVANCED_SETTINGS_TITLE_AR
        )

    def test_mode_buttons_defined(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        options = {o["key"]: o for o in fields["whatsapp_mode_selection"]["options"]}
        self.assertEqual(
            options[WHATSAPP_MODE_CARTFLOW_MANAGED]["button_ar"],
            WHATSAPP_MODE_CTA_AR[WHATSAPP_MODE_CARTFLOW_MANAGED],
        )
        self.assertEqual(
            options[WHATSAPP_MODE_MERCHANT_WHATSAPP]["button_ar"],
            WHATSAPP_MODE_CTA_AR[WHATSAPP_MODE_MERCHANT_WHATSAPP],
        )

    def test_current_path_merchant_has_subtext(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        path = whatsapp_current_path_for_api(self.row)
        self.assertIn("رقم الواتساب الخاص بمتجرك", path["body_ar"])
        self.assertEqual(path["subtext_ar"], "يمكنك تغيير المسار في أي وقت.")

    def test_cartflow_scrubs_disconnected_labels(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertFalse(fields.get("whatsapp_show_advanced_settings"))
        joined = " ".join(
            [
                fields.get("whatsapp_customer_connection_status_ar") or "",
                fields.get("whatsapp_connection_summary_ar") or "",
                fields.get("whatsapp_status_display") or "",
            ]
        )
        self.assertNotIn("غير متصل", joined)
        self.assertNotIn("لم يتم الربط", joined)

    def test_js_renders_current_path_card(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("ma-wa-current-path-card", js)
        self.assertIn("ma-wa-current-path-body", js)
        self.assertIn("wrap.open = false", js)

    def test_js_hides_readiness_from_main_set_readonly(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        block = js[js.index("function setReadOnly"): js.index("function fillForm")]
        self.assertNotIn("renderReadinessCard", block)
        self.assertIn("renderCurrentPath", block)
        self.assertIn("renderAdvancedSettings", block)

    def test_template_advanced_collapsed_by_default(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        self.assertIn('id="ma-wa-advanced-settings-wrap" hidden', html)
        self.assertIn("إعدادات متقدمة", html)


if __name__ == "__main__":
    unittest.main()
