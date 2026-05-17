# -*- coding: utf-8 -*-
"""VIP dashboard UI reflects merchant_automation_mode (display only)."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store


class MerchantVipAutomationUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.zid = f"vip_auto_{uuid.uuid4().hex[:12]}"
        for row in db.session.query(Store).filter_by(zid_store_id=self.zid).all():
            db.session.delete(row)
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

    def _set_mode(self, mode: str) -> None:
        r = self.client.post(
            "/api/recovery-settings",
            json={
                "merchant_automation_mode": mode,
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(r.status_code, 200, r.text[:300])

    def test_vip_carts_api_includes_automation_mode(self) -> None:
        self._set_mode("assistant")
        data = self.client.get("/api/dashboard/vip-carts").json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("merchant_automation_mode"), "assistant")

    def test_dashboard_vip_page_has_automation_ui(self) -> None:
        html = self.client.get("/dashboard").text or ""
        self.assertIn("merchant_vip_automation_ui.js", html)
        self.assertIn("ma-vip-automation-helper", html)
        self.assertIn("ma-vip-suggest-panel", html)
        self.assertIn("اقتراح متابعة VIP", html)
        self.assertIn("طريقة التشغيل تغيّر أسلوب المتابعة فقط", html)

    def test_get_scope_vip_is_minimal(self) -> None:
        data = self.client.get("/api/recovery-settings?scope=vip").json()
        self.assertTrue(data.get("ok"))
        self.assertIn("vip_cart_threshold", data)
        self.assertNotIn("recovery_delay", data)
        self.assertNotIn("widget_trigger_config", data)

    def test_modes_persist_via_recovery_settings_get(self) -> None:
        for mode in ("manual", "assistant", "auto"):
            self._set_mode(mode)
            got = self.client.get("/api/recovery-settings").json()
            self.assertEqual(got.get("merchant_automation_mode"), mode)
            vip = self.client.get("/api/dashboard/vip-carts").json()
            self.assertEqual(vip.get("merchant_automation_mode"), mode)


if __name__ == "__main__":
    unittest.main()
