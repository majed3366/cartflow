# -*- coding: utf-8 -*-
"""Route ownership and content for the standalone merchant app at /dashboard."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class MerchantStandaloneAppDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_dashboard_renders_merchant_app_marker(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:500])
        t = (r.text or "").lower()
        self.assertIn("data-cf-merchant-app", t)

    def test_dashboard_contains_section_labels(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        for needle in (
            "الرئيسية",
            "السلال المتروكة",
            "سلال تحتاج متابعة",
            "سلال VIP",
            "الرسائل المرسلة",
            "أسباب التردد",
            "الودجيت",
            "إعدادات واتساب",
            "إعدادات عامة",
            "توصيات",
            "حفظ إعدادات الودجيت",
            "معاينة سطح المكتب",
            "معاينة الجوال",
            'id="ma-widget-bootstrap"',
        ):
            self.assertIn(needle, html, msg=f"missing: {needle}")

    def test_dashboard_excludes_old_shell_and_placeholder(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        t = (r.text or "").lower()
        self.assertNotIn("cf-dash-shell", t)
        self.assertNotIn("merchant_reference_shell", t)
        self.assertNotIn("data-cf-merchant-dashboard-v1", t)
        self.assertNotIn("data-cf-merchant-dashboard-placeholder", t)
        self.assertNotIn("merchant dashboard is being rebuilt", t.lower())
        self.assertNotIn("placeholder", t)
        self.assertNotIn("عرض توضيحي", t)
        self.assertNotIn("ارجع للرئيسية", t)
        self.assertNotIn("recovery_ops_dashboard", t)
        self.assertNotIn("cartflow_runtime_health", t)
        self.assertIn("merchant_widget_panel.js", t)

    def test_dashboard_contains_all_section_page_ids(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        for pid in (
            'id="page-home"',
            'id="page-carts"',
            'id="page-followup"',
            'id="page-vip"',
            'id="page-messages"',
            'id="page-reasons"',
            'id="page-widget"',
            'id="page-whatsapp"',
            'id="page-settings"',
        ):
            self.assertIn(pid, html, msg=f"missing: {pid}")

    def test_dashboard_merchant_html_has_no_ops_session_field(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('name="nr_session"', r.text or "")

    def test_normal_carts_redirects_to_dashboard_carts_hash(self) -> None:
        r = self.client.get("/dashboard/normal-carts", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:300])
        loc = r.headers.get("location") or ""
        self.assertTrue(
            loc.endswith("/dashboard#carts") or "#carts" in loc,
            msg=loc,
        )

    def test_vip_cart_settings_redirects_to_dashboard_vip_hash(self) -> None:
        r = self.client.get("/dashboard/vip-cart-settings", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard", loc)
        self.assertIn("#vip", loc)

    def test_recovery_settings_redirects_to_whatsapp_section(self) -> None:
        r = self.client.get("/dashboard/recovery-settings", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("#whatsapp", loc)

    def test_widget_customization_redirects_to_widget_section(self) -> None:
        r = self.client.get("/dashboard/widget-customization", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("#widget", loc)

    def test_normal_alias_redirects_to_dashboard(self) -> None:
        r = self.client.get("/dashboard/normal", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = (r.headers.get("location") or "").rstrip("/")
        self.assertTrue(loc.endswith("/dashboard"), msg=r.headers.get("location"))

    def test_operations_dashboard_still_200(self) -> None:
        r = self.client.get("/dashboard/normal-carts/operations")
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertIn("text/html", (r.headers.get("content-type") or "").lower())


if __name__ == "__main__":
    unittest.main()
