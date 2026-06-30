# -*- coding: utf-8 -*-
"""WhatsApp Merchant Experience V3 — hide disconnected, commercial connect page."""
from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path

from extensions import db
from models import Store
from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    whatsapp_connect_page_for_api,
)
from services.merchant_whatsapp_settings import merchant_whatsapp_settings_fields_for_api


class MerchantWhatsappExperienceV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_v3_{uuid.uuid4().hex[:12]}"
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

    def test_cartflow_full_api_never_surfaces_disconnected(self) -> None:
        fields = merchant_whatsapp_settings_fields_for_api(self.row)
        blob = json.dumps(fields, ensure_ascii=False)
        self.assertNotIn("غير متصل", blob)
        embedded = fields.get("whatsapp_embedded_signup") or {}
        self.assertFalse(embedded.get("applicable"))
        self.assertEqual(embedded.get("status_ar"), "")
        readiness = fields.get("whatsapp_connection_readiness") or {}
        self.assertEqual(readiness.get("connection_state_ar"), "")

    def test_cartflow_connect_page_is_commercial_redirect(self) -> None:
        page = whatsapp_connect_page_for_api(self.row)
        self.assertFalse(page.get("applicable"))
        self.assertIn("واتساب CartFlow", page.get("body_ar") or "")
        joined = " ".join(
            [
                page.get("headline_ar") or "",
                page.get("intro_ar") or "",
                page.get("body_ar") or "",
            ]
        )
        self.assertNotIn("Embedded Signup", joined)
        self.assertNotIn("Meta", joined)

    def test_merchant_connect_page_is_commercial(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        page = whatsapp_connect_page_for_api(self.row)
        self.assertTrue(page.get("applicable"))
        self.assertIn("ربط رقم", page.get("headline_ar") or "")
        self.assertTrue(page.get("steps_ar"))
        joined = json.dumps(page, ensure_ascii=False)
        self.assertNotIn("Embedded Signup", joined)
        self.assertNotIn("Foundation", joined)
        self.assertNotIn("placeholder", joined.lower())

    def test_connect_js_uses_commercial_api_block(self) -> None:
        js = Path("static/merchant_whatsapp_connect.js").read_text(encoding="utf-8")
        self.assertIn("whatsapp_connect_page", js)
        self.assertNotIn("Embedded Signup", js)
        self.assertNotIn("placeholder", js.lower())

    def test_template_pill_has_no_default_disconnected_label(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        self.assertIn('id="ma-wa-connection-pill" hidden></span>', html)
        self.assertNotIn('id="ma-wa-connection-pill" hidden>غير متصل</span>', html)

    def test_set_readonly_hides_connection_pill_for_cartflow(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        block = js[js.index("function setReadOnly"): js.index("function fillForm")]
        self.assertIn("whatsapp_show_connection_status", block)
        self.assertIn("ma-wa-connection-pill", block)

    def test_merchant_mode_still_has_connect_page(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        fields = merchant_whatsapp_settings_fields_for_api(self.row)
        page = fields.get("whatsapp_connect_page") or {}
        self.assertTrue(page.get("applicable"))
        self.assertEqual(self.row.whatsapp_mode, WHATSAPP_MODE_MERCHANT_WHATSAPP)


if __name__ == "__main__":
    unittest.main()
