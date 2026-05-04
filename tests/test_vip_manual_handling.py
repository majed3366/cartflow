# -*- coding: utf-8 -*-
"""VIP manual handling: cart_abandoned skips scheduled customer WhatsApp recovery."""
from __future__ import annotations

import logging
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store
from tests.test_recovery_isolation import _post_recovery_reason_for_session, _reset_recovery_memory


class VipManualHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main._load_store_row_for_recovery")
    @patch("main.try_send_vip_merchant_whatsapp_alert", return_value={"ok": False})
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    def test_vip_cart_abandon_skips_customer_whatsapp(
        self, mock_send: object, _p: object, _m: object, mock_store: object
    ) -> None:
        mock_store.return_value = SimpleNamespace(
            zid_store_id="demo",
            vip_cart_threshold=400,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            recovery_delay_minutes=None,
            store_whatsapp_number=None,
            whatsapp_support_url=None,
        )
        db.create_all()
        main._ensure_store_widget_schema()

        cid = "vip-manual-cart-1"
        existing = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        sid = "vip-manual-session-1"
        _post_recovery_reason_for_session(self.client, "demo", sid, "price")

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_abandoned",
                "store": "demo",
                "session_id": sid,
                "cart_id": cid,
                "cart_value": 500.0,
                "phone": "+966501112233",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body.get("recovery_state"), "vip_manual_handling")
        self.assertTrue(body.get("recovery_vip_manual"))
        self.assertTrue(body.get("customer_recovery_skipped"))
        self.assertFalse(body.get("recovery_scheduled", True))
        mock_send.assert_not_called()

        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        self.assertTrue(bool(getattr(ac, "vip_mode", False)))
        self.assertEqual((ac.status or "").strip(), "abandoned")


class WidgetCartAbandonVipDetectionTests(unittest.TestCase):
    """Real POST /api/cart-event payloads with cart_total (widget-style) → VIP بدون dev endpoint."""

    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main.try_send_vip_merchant_whatsapp_alert", return_value={"ok": False})
    @patch("main.send_whatsapp")
    def test_cart_abandoned_cart_total_1200_logs_and_priority_list(self, _mock_sw: object, _mock_va: object) -> None:
        logging.getLogger("cartflow").setLevel(logging.INFO)
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"widgv_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=900,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(store)
        db.session.commit()

        cid = f"wid-cart-{uuid.uuid4().hex[:10]}"
        old_ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        if old_ac:
            db.session.delete(old_ac)
            db.session.commit()

        sid = f"wid-sess-{uuid.uuid4().hex[:8]}"
        _post_recovery_reason_for_session(self.client, slug, sid, "price")

        with self.assertLogs("cartflow", level="INFO") as alog_ctx:
            r = self.client.post(
                "/api/cart-event",
                json={
                    "event": "cart_abandoned",
                    "store": slug,
                    "session_id": sid,
                    "source": "beforeunload",
                    "cart_id": cid,
                    "cart_total": 1200,
                    "phone": "+966501112233",
                    "cart": [],
                },
            )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json().get("recovery_state"), "vip_manual_handling")

        blob = "\n".join(alog_ctx.output)
        self.assertIn("[WIDGET CART EVENT]", blob)
        self.assertIn("[ABANDONED CART SAVED]", blob)
        self.assertIn("[VIP CHECK]", blob)
        self.assertIn("[VIP MODE ACTIVATED] source=real_widget_cart_event", blob)

        lg = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.cart_id == cid,
                CartRecoveryLog.status == "vip_manual_handling",
            )
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
        self.assertIsNotNone(lg)
        self.assertEqual((lg.message or "").strip(), main.VIP_WIDGET_RECOVERY_LOG_MESSAGE)
        self.assertEqual(lg.step, main.VIP_WIDGET_RECOVERY_LOG_STEP)

        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).one()
        self.assertEqual(int(ac.store_id or 0), int(store.id))
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 1200.0)
        self.assertEqual((ac.status or "").strip(), "abandoned")
        self.assertTrue(ac.vip_mode)

        prios = main._vip_priority_cart_alert_list()
        self.assertTrue(any(int(x.get("id", 0)) == int(ac.id) for x in prios))

    @patch("main.try_send_vip_merchant_whatsapp_alert", return_value={"ok": False})
    @patch("main.send_whatsapp")
    def test_vip_without_cart_id_uses_stable_fallback_cf_w(self, _mock_sw: object, _mock_va: object) -> None:
        """واجهات بدون cart_id: يُنشأ cf_w_* وVIP يُسجَّل (>500) دون dev endpoint."""
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"widnc_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"wid-no-cid-{uuid.uuid4().hex[:8]}"

        rk = main._recovery_key_from_payload({"store": slug, "session_id": sid})
        fallback_cid = main._ensure_cart_abandon_payload_has_cart_id(
            {"store": slug, "session_id": sid, "event": "cart_abandoned"},
            rk,
        )["cart_id"]

        old_ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=fallback_cid).first()
        if old_ac:
            db.session.delete(old_ac)
            db.session.commit()

        _post_recovery_reason_for_session(self.client, slug, sid, "price")

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_abandoned",
                "store": slug,
                "session_id": sid,
                "source": "visibility",
                "cart_total": 750.5,
                "phone": "+966501112233",
                "cart": [],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json().get("recovery_state"), "vip_manual_handling")

        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=fallback_cid).first()
        self.assertIsNotNone(ac)
        self.assertEqual((ac.recovery_session_id or "").strip(), sid)
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 750.5)
        self.assertTrue(ac.vip_mode)
        self.assertEqual((ac.status or "").strip(), "abandoned")
        self.assertEqual(int(ac.store_id or 0), int(store.id))

        lg = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.cart_id == fallback_cid,
                CartRecoveryLog.status == "vip_manual_handling",
            )
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
        self.assertIsNotNone(lg)
        self.assertEqual((lg.message or "").strip(), main.VIP_WIDGET_RECOVERY_LOG_MESSAGE)

        prios = main._vip_priority_cart_alert_list()
        self.assertTrue(any(int(x.get("id", 0)) == int(ac.id) for x in prios))


class WidgetDemoStoreResolutionTests(unittest.TestCase):
    """Widget store=demo must match dashboard Store (latest id), not an older zid=demo row."""

    def setUp(self) -> None:
        _reset_recovery_memory()

    def test_demo_slug_uses_latest_store_vip_threshold(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        stale_demo = Store(
            zid_store_id="demo",
            vip_cart_threshold=None,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        dashboard_row = Store(
            zid_store_id="merchant_dashboard_zid",
            vip_cart_threshold=500,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(stale_demo)
        db.session.add(dashboard_row)
        db.session.commit()

        resolved = main._load_store_row_for_recovery("demo")
        self.assertIsNotNone(resolved)
        self.assertEqual(int(resolved.id), int(dashboard_row.id))
        self.assertEqual(resolved.vip_cart_threshold, 500)

    def test_default_slug_uses_latest_store(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        first = Store(
            zid_store_id="something",
            vip_cart_threshold=None,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        latest = Store(
            zid_store_id="live_merchant",
            vip_cart_threshold=500,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(first)
        db.session.add(latest)
        db.session.commit()

        resolved = main._load_store_row_for_recovery("default")
        self.assertIsNotNone(resolved)
        self.assertEqual(int(resolved.id), int(latest.id))
        self.assertEqual(resolved.vip_cart_threshold, 500)


class VipMerchantResolveTests(unittest.TestCase):
    def test_resolve_store_number(self) -> None:
        from services.vip_merchant_alert import resolve_merchant_whatsapp_phone

        st = SimpleNamespace(
            store_whatsapp_number="+966501112233",
            whatsapp_support_url=None,
        )
        phone, src = resolve_merchant_whatsapp_phone(st)
        self.assertIsNotNone(phone)
        self.assertEqual(src, "store_whatsapp_number")

    def test_resolve_wa_me(self) -> None:
        from services.vip_merchant_alert import resolve_merchant_whatsapp_phone

        st = SimpleNamespace(
            store_whatsapp_number=None,
            whatsapp_support_url="https://wa.me/966501112233",
        )
        phone, src = resolve_merchant_whatsapp_phone(st)
        self.assertEqual(phone, "966501112233")
        self.assertEqual(src, "whatsapp_support_url_wa_me")

    def test_vip_merchant_alert_body_plain(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        link = "https://example.test/dashboard/vip-cart-settings"
        expected = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 1200 ريال\n\n"
            "رابط المراجعة:\n"
            + link
        )
        self.assertEqual(
            build_vip_merchant_alert_body(1200.0, dashboard_link=link),
            expected,
        )

    def test_vip_merchant_alert_body_with_reason_tag(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        link = "https://example.test/dashboard/vip-cart-settings"
        expected = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 500 ريال\n\n"
            "السبب: السعر\n\n"
            "رابط المراجعة:\n"
            + link
        )
        self.assertEqual(
            build_vip_merchant_alert_body(500.0, reason_tag="price", dashboard_link=link),
            expected,
        )

    def test_vip_merchant_alert_not_old_colon_intro(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        body = build_vip_merchant_alert_body(999.0, dashboard_link="https://x.test/dash")
        self.assertNotIn("تنبيه VIP:", body)


if __name__ == "__main__":
    unittest.main()
