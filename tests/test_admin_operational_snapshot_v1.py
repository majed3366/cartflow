# -*- coding: utf-8 -*-
"""Admin operational snapshot export v1 — read-only JSON."""
from __future__ import annotations

import json
import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import Store
from services.admin_operational_snapshot_v1 import (
    build_admin_operational_snapshot_v1,
    redact_operational_snapshot,
)
from services.cartflow_admin_http_auth import admin_cookie_name


class AdminOperationalSnapshotV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "snapshot-v1-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)
        db.create_all()

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)
        db.session.remove()

    def _login(self) -> None:
        r = self.client.post(
            "/admin/operations/login",
            data={"password": "snapshot-v1-pass", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])

    def test_snapshot_builds_successfully(self) -> None:
        snap = build_admin_operational_snapshot_v1(generated_by="test")
        self.assertEqual(
            snap.get("metadata", {}).get("snapshot_version"),
            "admin_operational_snapshot_v1",
        )
        for section in (
            "metadata",
            "runtime_health",
            "store_readiness",
            "recovery_overview",
            "operational_signals",
            "recent_events",
            "support_context",
        ):
            self.assertIn(section, snap, section)

    def test_no_secrets_exported(self) -> None:
        slug = f"snap-secret-{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            access_token="super-secret-access-token-xyz",
            refresh_token="super-secret-refresh",
            store_whatsapp_number="+966501234567",
            widget_name="Test Store",
        )
        db.session.add(store)
        db.session.commit()

        snap = build_admin_operational_snapshot_v1(
            store_slug=slug,
            generated_by="test",
        )
        blob = json.dumps(snap)
        self.assertNotIn("super-secret-access-token", blob)
        self.assertNotIn("super-secret-refresh", blob)
        self.assertNotIn("966501234567", blob)
        self.assertNotIn('"access_token":', blob)
        ctx = snap.get("support_context") or {}
        self.assertTrue(ctx.get("has_oauth_access_token"))
        self.assertTrue(ctx.get("store_connected"))

    def test_redact_strips_sensitive_keys(self) -> None:
        raw = {
            "ok": True,
            "access_token": "tok",
            "phone": "+966500000000",
            "nested": {"message": "hello", "status": "ok"},
        }
        out = redact_operational_snapshot(raw)
        self.assertNotIn("access_token", out)
        self.assertNotIn("phone", out)
        self.assertNotIn("message", out.get("nested", {}))
        self.assertEqual(out["nested"]["status"], "ok")

    def test_missing_optional_sections_handled_safely(self) -> None:
        snap = build_admin_operational_snapshot_v1(store_slug="nonexistent-slug-xyz")
        self.assertEqual(snap.get("metadata", {}).get("store_slug_warning"), "store_not_found_for_slug")
        self.assertIn("recovery_overview", snap)
        self.assertIsInstance(snap.get("recent_events"), list)

    def test_store_scoped_export_works(self) -> None:
        slug = f"snap-scoped-{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            access_token="",
            widget_name="Scoped",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()

        snap = build_admin_operational_snapshot_v1(store_slug=slug)
        readiness = snap.get("store_readiness") or {}
        self.assertEqual(readiness.get("scope"), "store")
        self.assertEqual(readiness.get("store_slug"), slug)
        ctx = snap.get("support_context") or {}
        self.assertEqual(ctx.get("store_slug"), slug)
        self.assertEqual(ctx.get("zid_store_id"), slug)

    def test_endpoint_requires_auth(self) -> None:
        r = self.client.get("/admin/operations/snapshot")
        self.assertEqual(r.status_code, 401)

    def test_endpoint_returns_json_snapshot(self) -> None:
        self._login()
        cookies = self.client.cookies
        r = self.client.get(
            "/admin/operations/snapshot",
            cookies={admin_cookie_name(): cookies.get(admin_cookie_name())},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/json", r.headers.get("content-type", ""))
        body = r.json()
        self.assertTrue(body.get("ok"))
        snap = body.get("snapshot") or {}
        self.assertEqual(
            snap.get("metadata", {}).get("snapshot_version"),
            "admin_operational_snapshot_v1",
        )


if __name__ == "__main__":
    unittest.main()
