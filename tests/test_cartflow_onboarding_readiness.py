# -*- coding: utf-8 -*-
"""Onboarding readiness evaluation (read-only)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store
from services import cartflow_onboarding_readiness as onb
from services import cartflow_runtime_health as rh


class CartflowOnboardingReadinessTests(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.store_slug.like("onb-%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like("onb-%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(Store.zid_store_id.like("onb-%")).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

    def test_blocker_catalog_merchant_safe(self) -> None:
        cat = onb.get_onboarding_blocker_catalog()
        self.assertIn("widget_not_installed", cat)
        for _k, v in cat.items():
            self.assertNotIn("twilio", (v.get("title_ar") or "").lower())
            self.assertNotIn("oauth", (v.get("title_ar") or "").lower())

    def test_no_store_incomplete(self) -> None:
        ev = onb.evaluate_onboarding_readiness(None)
        self.assertFalse(ev["ready"])
        self.assertIn("dashboard_not_initialized", ev["blocking_steps"])
        self.assertGreaterEqual(ev["completion_percent"], 0)

    def test_widget_disabled_blocks(self) -> None:
        st = Store(
            zid_store_id="onb-widget-off",
            access_token="tok",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=False,
        )
        db.session.add(st)
        db.session.commit()
        with patch(
            "services.whatsapp_send.recovery_uses_real_whatsapp",
            return_value=False,
        ):
            ev = onb.evaluate_onboarding_readiness(st)
        self.assertFalse(ev["ready"])
        self.assertIn("widget_not_installed", ev["blocking_steps"])

    def test_sandbox_does_not_require_twilio(self) -> None:
        st = Store(
            zid_store_id="onb-sandbox",
            access_token="x",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=True,
        )
        db.session.add(st)
        db.session.commit()
        with patch(
            "services.whatsapp_send.recovery_uses_real_whatsapp",
            return_value=False,
        ):
            ev = onb.evaluate_onboarding_readiness(st)
        self.assertTrue(ev["sandbox_mode_active"])
        self.assertNotIn("whatsapp_not_connected", ev["blocking_steps"])
        self.assertTrue(ev["ready"])

    def test_production_requires_messaging_path(self) -> None:
        st = Store(
            zid_store_id="onb-prod",
            access_token="x",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=True,
        )
        db.session.add(st)
        db.session.commit()
        with patch(
            "services.whatsapp_send.recovery_uses_real_whatsapp",
            return_value=True,
        ), patch(
            "services.whatsapp_send.whatsapp_real_configured",
            return_value=False,
        ):
            ev = onb.evaluate_onboarding_readiness(st)
        self.assertFalse(ev["sandbox_mode_active"])
        self.assertIn("whatsapp_not_connected", ev["blocking_steps"])
        self.assertFalse(ev["ready"])

    def test_milestones_from_db(self) -> None:
        st = Store(
            zid_store_id="onb-mile",
            access_token="x",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=True,
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=st.id,
            zid_cart_id="onb-cart-1",
            customer_phone="+10000000001",
            status="detected",
        )
        db.session.add(ac)
        db.session.add(
            CartRecoveryLog(
                store_slug="onb-mile",
                session_id="s",
                cart_id="onb-cart-1",
                status="mock_sent",
                message="hi",
            )
        )
        db.session.commit()
        with patch(
            "services.whatsapp_send.recovery_uses_real_whatsapp",
            return_value=False,
        ):
            ev = onb.evaluate_onboarding_readiness(st)
        m = ev["milestones"]
        self.assertTrue(m["first_cart_detected"])
        self.assertTrue(m["first_recovery_scheduled"])
        self.assertTrue(m["first_whatsapp_sent"])

    def test_health_section_shape(self) -> None:
        snap = rh.build_runtime_health_snapshot()
        self.assertIn("onboarding_runtime", snap)
        ob = snap["onboarding_runtime"]
        self.assertIn("onboarding_completion_percent", ob)
        self.assertIn("onboarding_ready", ob)

    def test_trust_includes_onboarding(self) -> None:
        s = rh.derive_runtime_trust_signals(
            {
                "provider_runtime": {
                    "whatsapp_provider_ready": True,
                    "provider_effectively_disabled": False,
                },
                "recovery_runtime": {"runtime_active": True},
                "identity_runtime": {
                    "identity_resolution_ok": True,
                    "identity_conflict_detected": False,
                },
                "duplicate_protection_runtime": {
                    "duplicate_prevention_runtime_ok": True,
                },
                "lifecycle_consistency_runtime": {"lifecycle_runtime_ok": True},
                "session_consistency_runtime": {
                    "session_runtime_consistent": True,
                    "stale_state_detected": False,
                },
                "onboarding_runtime": {"onboarding_ready": False},
            },
            recent_anomaly_count=0,
        )
        self.assertIn("onboarding_ready", s)
        self.assertFalse(s.get("onboarding_ready"))
        self.assertTrue(s.get("runtime_warning"))

    def test_dashboard_visibility_has_ar_status(self) -> None:
        st = Store(
            zid_store_id="onb-vis",
            access_token="a",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=True,
        )
        db.session.add(st)
        db.session.commit()
        vis = onb.get_onboarding_dashboard_visibility(st)
        self.assertTrue(vis.get("show_strip"))
        self.assertTrue(len(vis.get("status_ar") or "") > 0)

    def test_normal_carts_html_includes_onboarding_strip(self) -> None:
        from fastapi.testclient import TestClient

        client = TestClient(app)
        r = client.get("/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:1500] if r.text else "")
        self.assertIn("cf-onboarding-strip", (r.text or "").lower())


if __name__ == "__main__":
    unittest.main()
