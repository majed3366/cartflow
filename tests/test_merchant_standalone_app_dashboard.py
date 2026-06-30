# -*- coding: utf-8 -*-
"""Route ownership and content for the standalone merchant app at /dashboard."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class MerchantStandaloneAppDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        import os

        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-for-merchant-dashboard")
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
            "بانتظار الإرسال",
            "تحتاج تدخل",
            "مكتملة",
            "VIP",
            "الرسائل",
            "أسباب التردد",
            "الودجيت",
            "واتساب",
            "الحساب والمتجر",
            "ربط المتجر",
            "اربط متجرك لقراءة الطلبات والسلال",
            "حفظ إعدادات الودجيت",
            "قوالب الاسترجاع",
            'id="page-trigger-templates"',
            "merchant_trigger_templates.js",
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
        self.assertNotIn("عرض توضيحي", t)
        self.assertNotIn("ارجع للرئيسية", t)
        self.assertNotIn("recovery_ops_dashboard", t)
        self.assertNotIn("cartflow_runtime_health", t)
        self.assertNotIn("db due scanner", t)
        self.assertNotIn("db-due-scanner", t)
        self.assertNotIn("/api/admin/db-due-scanner-health", t)
        self.assertIn("merchant_widget_panel.js", t)
        self.assertIn("merchant_dashboard_lazy.js", t)
        self.assertIn("merchant_knowledge_layer.js", t)

    def test_dashboard_contains_all_section_page_ids(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        for pid in (
            'id="page-home"',
            'id="page-carts"',
            'id="page-followup"',
            'id="page-completed"',
            'id="ma-tbody-completed"',
            'id="page-vip"',
            'id="page-messages"',
            'id="page-reasons"',
            'id="page-trigger-templates"',
            'id="page-widget"',
            'id="page-whatsapp"',
            'id="page-whatsapp-connect"',
            'id="page-settings"',
        ):
            self.assertIn(pid, html, msg=f"missing: {pid}")

    def test_dashboard_summary_api_returns_ok(self) -> None:
        r = self.client.get("/api/dashboard/summary")
        self.assertEqual(r.status_code, 200, r.text[:300])
        payload = r.json()
        self.assertTrue(payload.get("ok"))
        self.assertIn("merchant_kpi_abandoned_fmt", payload)

    def test_dashboard_normal_carts_api_ok_default_limit(self) -> None:
        r = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:400])
        payload = r.json()
        self.assertTrue(payload.get("ok"))
        rows = payload.get("merchant_carts_page_rows") or []
        self.assertIsInstance(rows, list)
        self.assertLessEqual(
            len(rows),
            50,
            msg="default normal-carts API payload should cap at 50 carts",
        )
        self.assertIn("merchant_cart_filter_counts", payload)

    def test_trigger_templates_js_has_restore_timing_action(self) -> None:
        from pathlib import Path

        js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_trigger_templates.js"
        ).read_text(encoding="utf-8")
        self.assertIn("data-ma-tpl-restore-timing", js)
        self.assertIn("restoreRecommendedTimingForActiveStage", js)
        self.assertIn("استعادة المقترح", js)

    def test_trigger_templates_js_has_save_debug_logs(self) -> None:
        from pathlib import Path

        js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_trigger_templates.js"
        ).read_text(encoding="utf-8")
        for tag in (
            "[SAVE TEMPLATE START]",
            "[SAVE TEMPLATE SUCCESS]",
            "[SAVE TEMPLATE FAIL]",
            "[TEMPLATE RELOAD START]",
            "[TEMPLATE RELOAD SUCCESS]",
            "[TEMPLATE RELOAD FAIL]",
        ):
            self.assertIn(tag, js, msg=tag)
        self.assertIn("stale_response_after_save", js)

    def test_trigger_templates_save_single_log_path_and_handler(self) -> None:
        import re
        from pathlib import Path

        js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_trigger_templates.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "trigLog(tag, out)",
            js,
            msg="tplDbg must not double-log via trigLog",
        )
        self.assertIn("[SAVE HANDLER]", js)
        self.assertIn("ma_tpl_root_delegate_v1", js)
        save_calls = len(re.findall(r"(?<!function )saveOne\s*\(", js))
        self.assertEqual(
            save_calls,
            1,
            msg="exactly one saveOne() call site (delegated click)",
        )

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

    def test_whatsapp_connect_redirects_to_hash_route(self) -> None:
        r = self.client.get("/dashboard/whatsapp-connect", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("#whatsapp-connect", loc)

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
