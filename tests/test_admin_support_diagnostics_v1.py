# -*- coding: utf-8 -*-
"""Admin support diagnostics v1 — read-only diagnostic builder."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

import main  # noqa: F401 — init_database

from extensions import db
from models import CartRecoveryLog, Store
from services.admin_support_diagnostics_v1 import build_admin_support_diagnostics


class TestAdminSupportDiagnosticsV1(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "test-admin-diag-v1"
        db.create_all()
        try:
            db.session.query(CartRecoveryLog).delete()
            db.session.query(Store).filter(Store.zid_store_id == "diag-store").delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
        st = Store(
            zid_store_id="diag-store",
            is_active=True,
            recovery_attempts=1,
            cartflow_widget_enabled=True,
        )
        db.session.add(st)
        db.session.commit()

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:
            pass

    def test_blocked_template_required(self) -> None:
        db.session.add(
            CartRecoveryLog(
                store_slug="diag-store",
                session_id="sess-block",
                cart_id=None,
                phone="966501234567",
                message="test",
                status="blocked_template_required",
                step=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        out = build_admin_support_diagnostics(
            store_slug="diag-store",
            session_id="sess-block",
            recovery_key="diag-store:sess-block",
        )
        self.assertTrue(out.get("ok"))
        d = out.get("diagnostic") or {}
        self.assertEqual(d.get("issue_type"), "blocked_template_required")
        self.assertIn("24", d.get("likely_cause", "") or d.get("summary", ""))
        self.assertTrue(d.get("merchant_safe_message"))

    def test_mock_sent(self) -> None:
        db.session.add(
            CartRecoveryLog(
                store_slug="diag-store",
                session_id="sess-mock",
                status="mock_sent",
                message="m",
                step=1,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        out = build_admin_support_diagnostics(
            store_slug="diag-store",
            session_id="sess-mock",
        )
        d = out.get("diagnostic") or {}
        self.assertEqual(d.get("issue_type"), "mock_sent")

    def test_missing_store_slug(self) -> None:
        out = build_admin_support_diagnostics()
        self.assertFalse(out.get("ok"))


if __name__ == "__main__":
    unittest.main()
