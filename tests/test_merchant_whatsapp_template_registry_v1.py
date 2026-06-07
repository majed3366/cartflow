# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 2 — template registry & reason mapping."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.admin_whatsapp_template_visibility_v1 import (
    build_admin_store_template_rows,
    list_admin_template_registry_rows,
)
from services.merchant_whatsapp_reason_mapping_v1 import (
    normalize_reason_tag,
    resolve_template_key_for_reason,
)
from services.merchant_whatsapp_template_layer_v1 import (
    apply_whatsapp_template_layer_from_body,
    merchant_whatsapp_template_layer_for_api,
    parse_whatsapp_template_overrides_column,
)
from services.merchant_whatsapp_template_registry_v1 import (
    MERCHANT_EDITABLE_TEMPLATE_KEYS,
    TEMPLATE_REGISTRY,
)


class MerchantWhatsappTemplateRegistryV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_tpl_{uuid.uuid4().hex[:12]}"
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

    def test_registry_has_required_template_keys(self) -> None:
        required = {
            "PRICE_TEMPLATE",
            "QUALITY_TEMPLATE",
            "SHIPPING_TEMPLATE",
            "DELIVERY_TEMPLATE",
            "WARRANTY_TEMPLATE",
            "OTHER_TEMPLATE",
            "UNKNOWN_REASON_TEMPLATE",
            "FOLLOWUP_1_TEMPLATE",
            "FOLLOWUP_2_TEMPLATE",
            "FOLLOWUP_3_TEMPLATE",
            "VIP_ALERT_TEMPLATE",
        }
        self.assertTrue(required.issubset(set(TEMPLATE_REGISTRY.keys())))

    def test_reason_mapping_price_to_price_template(self) -> None:
        self.assertEqual(normalize_reason_tag("price_high"), "price")
        self.assertEqual(resolve_template_key_for_reason("price"), "PRICE_TEMPLATE")
        self.assertEqual(resolve_template_key_for_reason("shipping"), "SHIPPING_TEMPLATE")
        self.assertEqual(resolve_template_key_for_reason("unknown"), "UNKNOWN_REASON_TEMPLATE")
        self.assertEqual(resolve_template_key_for_reason(None), "UNKNOWN_REASON_TEMPLATE")

    def test_merchant_editable_keys_are_six_reason_templates(self) -> None:
        self.assertEqual(len(MERCHANT_EDITABLE_TEMPLATE_KEYS), 6)
        self.assertIn("PRICE_TEMPLATE", MERCHANT_EDITABLE_TEMPLATE_KEYS)
        self.assertNotIn("VIP_ALERT_TEMPLATE", MERCHANT_EDITABLE_TEMPLATE_KEYS)

    def test_apply_custom_content_persists(self) -> None:
        custom = "نص مخصص للسعر"
        apply_whatsapp_template_layer_from_body(
            self.row,
            {
                "whatsapp_template_overrides": {
                    "PRICE_TEMPLATE": {"enabled": True, "custom_content": custom},
                }
            },
        )
        db.session.commit()
        db.session.refresh(self.row)
        parsed = parse_whatsapp_template_overrides_column(
            self.row.whatsapp_template_overrides_json
        )
        self.assertEqual(parsed["PRICE_TEMPLATE"]["custom_content"], custom)
        layer = merchant_whatsapp_template_layer_for_api(self.row)
        price_row = next(
            r
            for r in layer["whatsapp_template_merchant_rows"]
            if r["template_key"] == "PRICE_TEMPLATE"
        )
        self.assertTrue(price_row["is_customized"])
        self.assertEqual(price_row["effective_content"], custom)

    def test_restore_default_clears_override(self) -> None:
        apply_whatsapp_template_layer_from_body(
            self.row,
            {
                "whatsapp_template_overrides": {
                    "PRICE_TEMPLATE": {"custom_content": "مخصص"},
                }
            },
        )
        apply_whatsapp_template_layer_from_body(
            self.row,
            {"whatsapp_template_restore_defaults": ["PRICE_TEMPLATE"]},
        )
        db.session.commit()
        parsed = parse_whatsapp_template_overrides_column(
            self.row.whatsapp_template_overrides_json
        )
        self.assertNotIn("PRICE_TEMPLATE", parsed)

    def test_api_includes_template_layer_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        for key in (
            "whatsapp_template_merchant_rows",
            "whatsapp_template_reason_mapping",
            "whatsapp_template_registry_version",
        ):
            self.assertIn(key, data, msg=f"missing {key}")
        self.assertEqual(len(data.get("whatsapp_template_merchant_rows") or []), 6)

    def test_rejects_non_editable_template_key_in_overrides(self) -> None:
        apply_whatsapp_template_layer_from_body(
            self.row,
            {
                "whatsapp_template_overrides": {
                    "VIP_ALERT_TEMPLATE": {"custom_content": "hack"},
                }
            },
        )
        db.session.commit()
        parsed = parse_whatsapp_template_overrides_column(
            self.row.whatsapp_template_overrides_json
        )
        self.assertNotIn("VIP_ALERT_TEMPLATE", parsed)

    def test_admin_registry_rows(self) -> None:
        rows = list_admin_template_registry_rows()
        self.assertGreaterEqual(len(rows), 11)
        keys = {r.template_key for r in rows}
        self.assertIn("PRICE_TEMPLATE", keys)

    def test_admin_store_template_rows(self) -> None:
        apply_whatsapp_template_layer_from_body(
            self.row,
            {
                "whatsapp_template_overrides": {
                    "SHIPPING_TEMPLATE": {"custom_content": "شحن مخصص"},
                }
            },
        )
        db.session.commit()
        rows = build_admin_store_template_rows(self.row)
        shipping = next(r for r in rows if r.template_key == "SHIPPING_TEMPLATE")
        self.assertEqual(shipping.default_or_customized_ar, "مخصص")

    def test_dashboard_whatsapp_page_transport_only(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn("ma-wa-enable-recovery-btn", html)
        self.assertIn("فتح قوالب الاسترجاع", html)
        self.assertNotIn("ma-wa-templates-list", html)
        self.assertNotIn("ma-wa-templates-save", html)

    def test_dashboard_trigger_templates_page_owns_content(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn("page-trigger-templates", html)
        self.assertIn("ma-tpl-root", html)


if __name__ == "__main__":
    unittest.main()
