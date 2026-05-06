# -*- coding: utf-8 -*-
"""لوحة المشرف: تسجيل الدخول، الحماية، والتنبيهات."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AdminAlert


class AdminAlertsTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("ADMIN_USERNAME", "admin")
        os.environ.setdefault("ADMIN_PASSWORD", "admin")
        self.client = TestClient(app)

    def test_admin_redirects_to_login_when_unauthenticated(self) -> None:
        r = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers.get("location", "").endswith("/admin/login"))

    def test_login_then_dashboard_subpages(self) -> None:
        lg = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin"},
            follow_redirects=False,
        )
        self.assertEqual(lg.status_code, 302, lg.text)
        self.assertTrue(lg.headers.get("location", "").endswith("/admin"))

        dash = self.client.get("/admin")
        self.assertEqual(dash.status_code, 200, dash.text)
        self.assertIn(b"Admin Alerts", dash.content)

        for path in (
            "/admin/integrations/whatsapp",
            "/admin/stores",
            "/admin/cart-events",
            "/admin/errors",
            "/admin/settings",
        ):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertIn(b"Back to Admin Dashboard", resp.content, path)

    def test_logout_clears_session(self) -> None:
        self.client.post("/admin/login", data={"username": "admin", "password": "admin"})
        lo = self.client.get("/admin/logout", follow_redirects=False)
        self.assertEqual(lo.status_code, 302)
        r2 = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(r2.status_code, 302)

    def test_mark_alert_monitoring(self) -> None:
        db.create_all()
        row = AdminAlert(
            alert_type="test_alert",
            title="Test",
            status="active",
            severity="low",
            cause="Cause text required.",
            action_label="Go",
            action_route="/admin/settings",
            store_slug=None,
        )
        db.session.add(row)
        db.session.commit()
        aid = int(row.id)
        try:
            self.client.post("/admin/login", data={"username": "admin", "password": "admin"})
            r = self.client.post(
                f"/admin/alerts/{aid}/status",
                data={"status": "monitoring"},
                follow_redirects=False,
            )
            self.assertEqual(r.status_code, 302)
            db.session.refresh(row)
            self.assertEqual((row.status or "").lower(), "monitoring")
        finally:
            db.session.query(AdminAlert).filter(AdminAlert.id == aid).delete()
            db.session.commit()


if __name__ == "__main__":
    unittest.main()
