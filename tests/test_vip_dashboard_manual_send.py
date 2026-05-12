# -*- coding: utf-8 -*-
"""POST /api/dashboard/vip-cart/{id}/merchant-alert — VIP تنبيه تاجر فقط."""
from __future__ import annotations

import logging
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from extensions import db
from fastapi.testclient import TestClient

from main import (
    _normal_recovery_merchant_lightweight_alert_list,
    _vip_dashboard_cart_link,
    _vip_priority_cart_alert_list,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store

VIP_MANUAL_ALERT_TEST_MERCHANT_WHATSAPP = "+966579706669"


def _persist_store_whatsapp_via_recovery_api(tc: unittest.TestCase, client: TestClient, phone: str) -> None:
    """يضبط ‎store_whatsapp_number‎ عبر ‎GET‎ ثم ‎POST /api/recovery-settings‎ (نفس مسار الواجهة)."""
    rg = client.get("/api/recovery-settings")
    tc.assertEqual(rg.status_code, 200, rg.text)
    body = rg.json()
    tc.assertTrue(body.get("ok"), body)
    body.pop("ok", None)
    body["store_whatsapp_number"] = phone
    rp = client.post("/api/recovery-settings", json=body)
    tc.assertEqual(rp.status_code, 200, rp.text)
    out = rp.json()
    tc.assertTrue(out.get("ok"), out)
    tc.assertEqual((out.get("store_whatsapp_number") or "").strip(), phone.strip())


class VipDashboardMerchantAlertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    @patch("main.vip_dashboard_review_link", return_value="https://example.test/dashboard/vip-cart-settings-fixed")
    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_manual_send_ok_returns_arabic_success(self, mock_send, _mock_review_link):
        mock_send.return_value = {"ok": True, "sid": "wx_1"}
        db.create_all()

        store = Store(
            zid_store_id=f"vip_manual_send_store_{uuid.uuid4().hex[:12]}",
            vip_cart_threshold=500,
        )
        db.session.add(store)
        db.session.commit()

        _persist_store_whatsapp_via_recovery_api(self, self.client, VIP_MANUAL_ALERT_TEST_MERCHANT_WHATSAPP)

        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-1-{uid}",
            cart_value=999.0,
            status="abandoned",
            vip_mode=True,
        )
        db.session.add(ac)
        db.session.commit()
        rid = int(ac.id)

        r = self.client.post(f"/api/dashboard/vip-cart/{rid}/merchant-alert", json={})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body.get("message"), "تم إرسال تنبيه التاجر")
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        msg = kwargs.get("message", "")
        expected_msg = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 999 ريال\n\n"
            "رابط المراجعة:\n"
            "https://example.test/dashboard/vip-cart-settings-fixed"
        )
        self.assertEqual(msg, expected_msg)

    @patch("main.vip_dashboard_review_link", return_value="https://example.test/with-reason")
    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_manual_send_exact_body_includes_reason_when_in_raw_payload(
        self, mock_send: object, _mock_review_link: object
    ) -> None:
        import json

        mock_send.return_value = {"ok": True, "sid": "wx_2"}
        db.create_all()
        store = Store(
            zid_store_id=f"vip_reason_body_{uuid.uuid4().hex[:12]}",
            vip_cart_threshold=200,
        )
        db.session.add(store)
        db.session.commit()
        _persist_store_whatsapp_via_recovery_api(self, self.client, VIP_MANUAL_ALERT_TEST_MERCHANT_WHATSAPP)

        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-reason-{uid}",
            cart_value=250.55,
            status="abandoned",
            vip_mode=True,
        )
        ac.raw_payload = json.dumps({"reason_tag": "price"}, ensure_ascii=False)
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(f"/api/dashboard/vip-cart/{int(ac.id)}/merchant-alert", json={})
        self.assertEqual(r.status_code, 200, r.text)
        kwargs = mock_send.call_args[1]
        msg = kwargs.get("message", "")
        expected = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 250.55 ريال\n\n"
            "السبب: السعر\n\n"
            "رابط المراجعة:\n"
            "https://example.test/with-reason"
        )
        self.assertEqual(msg, expected)

    def test_non_vip_cart_rejected(self) -> None:
        db.create_all()
        store = Store(
            zid_store_id=f"vip_ns_1_{uuid.uuid4().hex[:12]}",
            vip_cart_threshold=500,
        )
        db.session.add(store)
        db.session.commit()

        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-2-{uid}",
            cart_value=100.0,
            status="detected",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()
        r = self.client.post(f"/api/dashboard/vip-cart/{ac.id}/merchant-alert", json={})
        self.assertEqual(r.status_code, 400)
        self.assertIn("VIP", r.json().get("error", ""))

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_no_merchant_phone_arabic_error(self, mock_send) -> None:
        mock_send.return_value = {"ok": False, "error": "no_merchant_phone", "source": "no_merchant_contact"}
        db.create_all()
        store = Store(
            zid_store_id=f"vip_ns_2_{uuid.uuid4().hex[:12]}",
            store_whatsapp_number=None,
            whatsapp_support_url=None,
            vip_cart_threshold=250,
        )
        db.session.add(store)
        db.session.commit()
        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-3-{uid}",
            cart_value=300.0,
            status="detected",
            vip_mode=True,
        )
        db.session.add(ac)
        db.session.commit()
        r = self.client.post(f"/api/dashboard/vip-cart/{ac.id}/merchant-alert", json={})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get("error"), "لا يوجد رقم واتساب للمتجر")

    @patch("services.whatsapp_send.send_whatsapp")
    def test_manual_send_real_path_logs_success_after_recovery_api_whatsapp(self, mock_sw) -> None:
        """بعد ضبط ‎store_whatsapp_number‎ عبر ‎POST /api/recovery-settings‎: مسار حقيقي لـ try_send بدون لا يوجد رقم؛ سجل VIP المتوقعة."""
        mock_sw.return_value = {"ok": True, "sid": "SM_integration_test"}

        db.create_all()
        store = Store(
            zid_store_id=f"vip_integration_{uuid.uuid4().hex[:12]}",
            vip_cart_threshold=500,
        )
        db.session.add(store)
        db.session.commit()

        _persist_store_whatsapp_via_recovery_api(self, self.client, VIP_MANUAL_ALERT_TEST_MERCHANT_WHATSAPP)

        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-integration-{uid}",
            cart_value=750.0,
            status="detected",
            vip_mode=True,
        )
        db.session.add(ac)
        db.session.commit()

        with self.assertLogs(level=logging.INFO) as alog_ctx:
            r = self.client.post(f"/api/dashboard/vip-cart/{int(ac.id)}/merchant-alert", json={})

        self.assertEqual(r.status_code, 200, r.text)
        rd = r.json()
        self.assertTrue(rd.get("ok"), rd)
        self.assertEqual(rd.get("message"), "تم إرسال تنبيه التاجر")
        blob = "\n".join(alog_ctx.output)
        self.assertIn("[VIP MANUAL SEND CLICKED]", blob)
        self.assertIn("[VIP STORE RESOLUTION]", blob)
        self.assertIn("[VIP MERCHANT ALERT ATTEMPT]", blob)
        self.assertIn("[VIP MERCHANT ALERT SENT]", blob)

    def test_vip_cart_settings_placeholder_has_no_demo_vip_section(self) -> None:
        db.create_all()
        r = self.client.get("/dashboard/vip-cart-settings", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text)
        loc = r.headers.get("location") or ""
        self.assertIn("#vip", loc)
        r2 = self.client.get("/dashboard")
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertNotIn("demo_vip_cart_zid", r2.text or "")
        self.assertNotIn("vip-demo-heading", r2.text or "")

    def test_vip_merchant_ready_reply_bodies_omits_link_when_empty(self) -> None:
        from main import _vip_merchant_ready_reply_bodies

        with_link = _vip_merchant_ready_reply_bodies(cart_link="https://store.example/cart/1")
        self.assertIn("تقدر تكمل من هنا", with_link["offer"])
        self.assertIn("https://store.example/cart/1", with_link["offer"])
        self.assertIn("هذا رابط السلة", with_link["reminder"])
        no_link = _vip_merchant_ready_reply_bodies(cart_link="")
        self.assertNotIn("تقدر تكمل من هنا", no_link["offer"])
        self.assertNotIn("هذا رابط السلة", no_link["reminder"])
        self.assertIn("أنا من المتجر", no_link["direct"])

    def test_vip_dashboard_cart_link_column_then_raw_payload(self) -> None:
        import json

        from main import _vip_dashboard_cart_link

        ac = AbandonedCart(zid_cart_id=f"link-col-{uuid.uuid4().hex[:8]}", cart_url="https://column/c")
        self.assertEqual(_vip_dashboard_cart_link(ac), "https://column/c")
        ac2 = AbandonedCart(zid_cart_id=f"link-raw-{uuid.uuid4().hex[:8]}", cart_url=None)
        ac2.raw_payload = json.dumps({"checkout_url": "https://payload/checkout"}, ensure_ascii=False)
        self.assertEqual(_vip_dashboard_cart_link(ac2), "https://payload/checkout")

    def test_vip_priority_payload_includes_merchant_ready_replies_when_phone(self) -> None:
        db.create_all()
        slug = f"vip_mr_{uuid.uuid4().hex[:12]}"
        store = Store(
            zid_store_id=slug,
            vip_offer_enabled=True,
            vip_offer_type="free_shipping",
            vip_cart_threshold=500,
        )
        db.session.add(store)
        db.session.commit()

        uid = uuid.uuid4().hex[:8]
        zid_val = f"prio-mr-{uid}"
        cart_url_test = "https://example-ready.test/c/u1"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=zid_val,
            cart_value=501.0,
            status="abandoned",
            vip_mode=True,
            customer_phone="0501234567",
            cart_url=cart_url_test,
        )
        db.session.add(ac)
        db.session.commit()

        alerts = _vip_priority_cart_alert_list()
        by_id = {int(a.get("id") or 0): a for a in alerts}
        self.assertIn(int(ac.id), by_id)
        row = by_id[int(ac.id)]
        self.assertTrue(bool((row.get("customer_wa_phone") or "").strip()))
        self.assertIn("merchant_reply_offer_ar", row)
        self.assertIn("merchant_reply_reminder_ar", row)
        self.assertIn("merchant_reply_direct_ar", row)
        blob = (
            str(row.get("merchant_reply_reminder_ar", ""))
            + str(row.get("merchant_reply_offer_ar", ""))
            + str(row.get("merchant_reply_direct_ar", ""))
        )
        self.assertIn(cart_url_test, blob)

    def test_vip_priority_payload_omits_customer_phone_when_missing(self) -> None:
        db.create_all()
        slug = f"vip_nomr_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug, vip_cart_threshold=500)
        db.session.add(store)
        db.session.commit()

        uid = uuid.uuid4().hex[:8]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"prio-nophone-{uid}",
            cart_value=502.0,
            status="abandoned",
            vip_mode=True,
            customer_phone=None,
            cart_url="https://x/c",
        )
        db.session.add(ac)
        db.session.commit()

        alerts = _vip_priority_cart_alert_list()
        by_id = {int(a.get("id") or 0): a for a in alerts}
        self.assertIn(int(ac.id), by_id)
        row = by_id[int(ac.id)]
        self.assertFalse(bool((row.get("customer_wa_phone") or "").strip()))

    @patch("main._cleanup_duplicate_vip_abandoned_rows", return_value=0)
    def test_vip_priority_merges_same_session_for_display_and_phone(
        self, _noop_cleanup
    ) -> None:
        """بدون تنظيف ‎DB‎: مجموعة واحدة لكل ‎session‎، أحدث سلة مع رقم من أي صف في المجموعة."""
        db.create_all()
        slug = f"vip_sess_grp_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug, vip_cart_threshold=400)
        db.session.add(store)
        db.session.commit()

        sess = f"rs_grp_{uuid.uuid4().hex[:8]}"
        ts_old = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts_new = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
        ac_old = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"z-o-{uuid.uuid4().hex[:8]}",
            recovery_session_id=sess,
            cart_value=400.0,
            status="abandoned",
            vip_mode=True,
            customer_phone="0501234567",
            last_seen_at=ts_old,
        )
        ac_new = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"z-n-{uuid.uuid4().hex[:8]}",
            recovery_session_id=sess,
            cart_value=500.0,
            status="abandoned",
            vip_mode=True,
            customer_phone=None,
            last_seen_at=ts_new,
        )
        db.session.add_all([ac_old, ac_new])
        db.session.commit()

        alerts = _vip_priority_cart_alert_list()
        ids = [int(a.get("id") or 0) for a in alerts]
        self.assertIn(int(ac_new.id), ids)
        self.assertNotIn(int(ac_old.id), ids)
        row = next(a for a in alerts if int(a.get("id") or 0) == int(ac_new.id))
        self.assertIn("966501234567", (row.get("customer_wa_phone") or ""))

        db.session.expire_all()
        self.assertIsNotNone(db.session.get(AbandonedCart, ac_old.id))
        self.assertIsNotNone(db.session.get(AbandonedCart, ac_new.id))

    def test_vip_cart_settings_priority_requires_vip_mode_and_abandoned_status(self) -> None:
        db.create_all()
        slug = f"vip_pri_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug, vip_cart_threshold=500)
        db.session.add(store)
        db.session.commit()

        uid1 = uuid.uuid4().hex[:8]
        uid2 = uuid.uuid4().hex[:8]
        zid_mode = f"prio-mode-{uid1}"
        zid_log = f"prio-logonly-{uid2}"
        ac1 = AbandonedCart(
            store_id=store.id,
            zid_cart_id=zid_mode,
            cart_value=500.0,
            status="abandoned",
            vip_mode=True,
        )
        ac2 = AbandonedCart(
            store_id=store.id,
            zid_cart_id=zid_log,
            cart_value=600.0,
            status="detected",
            vip_mode=False,
        )
        db.session.add_all([ac1, ac2])
        db.session.commit()

        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=f"sess-{uid2}",
            cart_id=zid_log,
            message="VIP log",
            status="vip_manual_handling",
        )
        db.session.add(lg)
        db.session.commit()

        alerts = _vip_priority_cart_alert_list()
        ids = {int(x.get("id") or 0) for x in alerts}
        self.assertIn(int(ac1.id), ids)
        self.assertNotIn(int(ac2.id), ids)

    @patch("main._cleanup_duplicate_vip_abandoned_rows", return_value=0)
    def test_high_value_cart_exclusive_vip_lane_by_threshold_not_vip_mode(
        self, _noop_cleanup: object,
    ) -> None:
        """سلة ‎1299‎ بعتبة ‎1000‎: تظهر في VIP فقط حتى لو ‎vip_mode=False‎ في DB."""
        db.create_all()
        slug = f"vip_lane_ex_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug, vip_cart_threshold=1000)
        db.session.add(store)
        db.session.commit()
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"lane-ex-{uuid.uuid4().hex[:8]}",
            recovery_session_id=f"rs_lane_{uuid.uuid4().hex[:8]}",
            cart_value=1299.0,
            status="abandoned",
            vip_mode=False,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        light = _normal_recovery_merchant_lightweight_alert_list(80, lifecycle="active")
        light_ids = {int(x.get("merchant_case_row_id") or 0) for x in light}
        vip_ids = {int(x.get("id") or 0) for x in _vip_priority_cart_alert_list()}
        self.assertIn(int(ac.id), vip_ids)
        self.assertNotIn(int(ac.id), light_ids)


if __name__ == "__main__":
    unittest.main()
