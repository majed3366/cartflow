# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 1 — mode architecture & UX."""
from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.dashboard_snapshot_enforcement_guard_v1 import (
    DashboardSnapshotHotPathViolation,
)
from services.dashboard_snapshot_hot_path_guard_v1 import (
    dashboard_api_snapshot_request_scope,
    guard_dashboard_hot_path,
)
from services.dashboard_snapshot_v1 import ENV_SNAPSHOT_MODE
from services.merchant_whatsapp_mode_v1 import (
    DEFAULT_WHATSAPP_MODE,
    MODE_SELECTION_TITLE_AR,
    SAVE_SUCCESS_MESSAGE_AR,
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_CTA_AR,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    merchant_whatsapp_mode_fields_for_api,
    normalize_whatsapp_mode,
    whatsapp_current_path_for_api,
    whatsapp_mode_selection_for_api,
)
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row


def _enable_snapshot_enforcement() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ENFORCE"] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-wa-mode-snapshot")


def _clear_snapshot_env() -> None:
    os.environ.pop(ENV_SNAPSHOT_MODE, None)
    os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_ENFORCE", None)


class MerchantWhatsappModeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_mode_{uuid.uuid4().hex[:12]}"
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

    def test_default_mode_cartflow_managed(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertEqual(fields["whatsapp_mode"], WHATSAPP_MODE_CARTFLOW_MANAGED)
        self.assertEqual(normalize_whatsapp_mode(None), DEFAULT_WHATSAPP_MODE)

    def test_api_includes_mode_and_connection_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        for key in (
            "whatsapp_mode",
            "whatsapp_mode_label_ar",
            "whatsapp_mode_selection",
            "whatsapp_mode_merchant_panel",
            "whatsapp_customer_connection_status_ar",
            "whatsapp_enable_recovery_cta_ar",
            "vip_destination_ar",
            "whatsapp_last_validation_ar",
        ):
            self.assertIn(key, data, msg=f"missing {key}")

    def test_mode_selection_api_shape(self) -> None:
        sel = whatsapp_mode_selection_for_api(self.row)
        block = sel["whatsapp_mode_selection"]
        self.assertEqual(block["title_ar"], MODE_SELECTION_TITLE_AR)
        self.assertEqual(block["selected"], WHATSAPP_MODE_CARTFLOW_MANAGED)
        self.assertEqual(len(block["options"]), 2)
        cartflow = block["options"][0]
        self.assertEqual(cartflow["key"], WHATSAPP_MODE_CARTFLOW_MANAGED)
        self.assertTrue(cartflow["bullets_ar"])
        self.assertEqual(cartflow["bullets_ar"][0], "لا يحتاج إعداد.")
        self.assertEqual(cartflow["subtitle_ar"], "الأسرع للبدء")
        self.assertEqual(
            cartflow["button_ar"], WHATSAPP_MODE_CTA_AR[WHATSAPP_MODE_CARTFLOW_MANAGED]
        )
        self.assertTrue(cartflow["recommended"])
        merchant = block["options"][1]
        self.assertEqual(merchant["key"], WHATSAPP_MODE_MERCHANT_WHATSAPP)
        self.assertNotIn("Meta", " ".join(merchant["bullets_ar"]))
        self.assertEqual(merchant["title_ar"], "💼 واتساب أعمالي")

    def test_current_path_status_cartflow(self) -> None:
        path = whatsapp_current_path_for_api(self.row)
        self.assertIn("CartFlow", path["title_ar"])
        self.assertIn("CartFlow", path["body_ar"])
        self.assertEqual(path["subtext_ar"], "يمكنك تغيير المسار في أي وقت.")
        self.assertEqual(path["card_tone"], "cartflow")

    def test_current_path_status_merchant(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        path = whatsapp_current_path_for_api(self.row)
        self.assertIn("واتساب أعمالي", path["title_ar"])
        self.assertIn("رقم الواتساب الخاص بمتجرك", path["body_ar"])
        self.assertEqual(path["subtext_ar"], "يمكنك تغيير المسار في أي وقت.")
        self.assertEqual(path["card_tone"], "merchant")

    def test_cartflow_hides_disconnected_technical_states(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertFalse(fields.get("whatsapp_show_advanced_settings"))
        self.assertFalse(fields.get("whatsapp_show_connection_status"))
        self.assertEqual(fields.get("whatsapp_customer_connection_status_ar"), "")
        self.assertEqual(fields.get("whatsapp_connection_state_ar"), "")
        self.assertFalse((fields.get("whatsapp_mode_merchant_panel") or {}).get("visible"))

    def test_merchant_mode_shows_advanced_flag(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        db.session.commit()
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertTrue(fields.get("whatsapp_show_advanced_settings"))
        self.assertTrue((fields.get("whatsapp_mode_merchant_panel") or {}).get("visible"))

    def test_api_includes_v2_experience_fields(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertTrue(fields.get("whatsapp_mode_experience_v2"))
        self.assertEqual(fields.get("whatsapp_save_success_message_ar"), SAVE_SUCCESS_MESSAGE_AR)
        self.assertIn("message_ar", fields.get("whatsapp_current_path") or {})

    def test_existing_store_without_whatsapp_mode_defaults(self) -> None:
        self.row.whatsapp_mode = None
        db.session.commit()
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertEqual(fields["whatsapp_mode"], WHATSAPP_MODE_CARTFLOW_MANAGED)
        sel = whatsapp_mode_selection_for_api(self.row)
        keys = [o["key"] for o in sel["whatsapp_mode_selection"]["options"]]
        self.assertEqual(
            keys,
            [WHATSAPP_MODE_CARTFLOW_MANAGED, WHATSAPP_MODE_MERCHANT_WHATSAPP],
        )

    def test_merchant_can_see_both_modes(self) -> None:
        r = self.client.get("/api/recovery-settings")
        data = r.json()
        options = (data.get("whatsapp_mode_selection") or {}).get("options") or []
        self.assertEqual(len(options), 2)
        titles = {o.get("key"): o.get("title_ar") for o in options}
        self.assertIn("🟢", titles[WHATSAPP_MODE_CARTFLOW_MANAGED])
        self.assertIn("💼", titles[WHATSAPP_MODE_MERCHANT_WHATSAPP])

    def test_merchant_mode_shows_merchant_panel(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        self.row.store_whatsapp_number = "+966501112233"
        self.row.whatsapp_recovery_enabled = True
        self.row.whatsapp_onboarding_journey = "existing_whatsapp_business"
        db.session.commit()
        sel = whatsapp_mode_selection_for_api(self.row)
        panel = sel["whatsapp_mode_merchant_panel"]
        self.assertTrue(panel["visible"])
        self.assertIn("connect_page_href", panel)
        self.assertIn("meta_pairing_status_ar", panel)
        self.assertIn("embedded_signup_status_ar", panel)
        self.assertIn("/dashboard#whatsapp-connect", panel["connect_page_href"])

    def test_post_returns_merchant_whatsapp_mode_in_api(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "whatsapp_mode": "merchant_whatsapp",
                "whatsapp_recovery_enabled": True,
            },
        )
        self.assertEqual(post.status_code, 200, post.text[:300])
        self.assertEqual(post.json().get("whatsapp_mode"), WHATSAPP_MODE_MERCHANT_WHATSAPP)

    def test_apply_whatsapp_mode_persists_on_store(self) -> None:
        from services.merchant_whatsapp_settings import apply_merchant_whatsapp_settings_from_body

        apply_merchant_whatsapp_settings_from_body(
            self.row,
            {"whatsapp_mode": WHATSAPP_MODE_MERCHANT_WHATSAPP},
        )
        db.session.commit()
        db.session.refresh(self.row)
        self.assertEqual(self.row.whatsapp_mode, WHATSAPP_MODE_MERCHANT_WHATSAPP)

    def test_admin_visibility_row(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        self.row.store_whatsapp_number = "+966501112233"
        db.session.commit()
        admin_row = build_admin_whatsapp_store_row(self.row)
        data = admin_row.to_api_dict()
        self.assertEqual(data["whatsapp_mode"], WHATSAPP_MODE_MERCHANT_WHATSAPP)
        self.assertIn("connection_status_ar", data)
        self.assertIn("vip_destination_ar", data)

    def test_dashboard_whatsapp_page_mode_ux(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn("ma-wa-mode-selection-root", html)
        self.assertIn("ma-wa-current-path-root", html)
        self.assertIn("ma-wa-advanced-settings-wrap", html)
        self.assertIn("ma-wa-mode-hidden", html)
        self.assertIn("merchant_whatsapp_settings.js", html)
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn(MODE_SELECTION_TITLE_AR, js)
        self.assertIn("renderCurrentPath", js)
        self.assertIn("renderAdvancedSettings", js)
        self.assertNotIn("renderReadinessCard(d)", js[js.index("function setReadOnly"): js.index("function fillForm")])


class WhatsappModeSnapshotArchitectureTests(unittest.TestCase):
    """WhatsApp mode UX must not weaken dashboard snapshot enforcement."""

    def setUp(self) -> None:
        _enable_snapshot_enforcement()
        self.client = TestClient(main.app)
        db.create_all()

    def tearDown(self) -> None:
        _clear_snapshot_env()

    def test_hot_path_guard_raises_during_snapshot_request(self) -> None:
        with dashboard_api_snapshot_request_scope(path="/api/dashboard/summary"):
            with self.assertRaises(DashboardSnapshotHotPathViolation):
                guard_dashboard_hot_path("summary_live", endpoint="summary")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._api_json_dashboard_summary")
    @patch("main._api_json_dashboard_normal_carts")
    def test_dashboard_endpoints_never_use_live_builders(
        self,
        mock_nc: unittest.mock.MagicMock,
        mock_summary: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        for path in (
            "/api/dashboard/summary",
            "/api/dashboard/normal-carts",
            "/api/dashboard/widget-panel",
            "/api/dashboard/refresh-state",
        ):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, msg=path)
            body = resp.json()
            self.assertTrue(body.get("snapshot_mode"), msg=path)
        mock_summary.assert_not_called()
        mock_nc.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_recovery_settings_serves_whatsapp_mode_without_snapshot_flag(
        self,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        """#whatsapp loads via /api/recovery-settings — separate from snapshot dashboard."""
        resp = self.client.get("/api/recovery-settings")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("whatsapp_mode_selection", data)
        self.assertFalse(data.get("snapshot_mode"))


if __name__ == "__main__":
    unittest.main()
