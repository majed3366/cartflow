# -*- coding: utf-8 -*-
"""Admin recovery resume inspect / scan v1 — read-only."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import RecoverySchedule
from services.admin_recovery_resume_inspect_scan_v1 import (
    build_recovery_resume_inspect_readonly,
    build_recovery_resume_scan_readonly,
)
from services.cartflow_admin_http_auth import admin_cookie_name
from services.recovery_restart_survival import STATUS_SCHEDULED


class AdminRecoveryResumeInspectScanV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "rr-inspect-v1-pass"
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
            data={"password": "rr-inspect-v1-pass", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303)

    def _add_schedule(
        self,
        *,
        slug: str,
        rk: str,
        status: str = STATUS_SCHEDULED,
        due_offset_minutes: int = -5,
    ) -> RecoverySchedule:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = RecoverySchedule(
            recovery_key=rk,
            store_slug=slug,
            session_id=f"sess-{uuid.uuid4().hex[:8]}",
            scheduled_at=now,
            due_at=now + timedelta(minutes=due_offset_minutes),
            effective_delay_seconds=120.0,
            delay_source="test",
            status=status,
            step=1,
        )
        db.session.add(row)
        db.session.commit()
        db.session.refresh(row)
        return row

    def test_inspect_builds_summary_and_items(self) -> None:
        slug = f"rr-insp-{uuid.uuid4().hex[:8]}"
        rk = f"{slug}:sess-1"
        self._add_schedule(slug=slug, rk=rk, due_offset_minutes=-10)
        payload = build_recovery_resume_inspect_readonly(store_slug=slug)
        self.assertTrue(payload.get("read_only"))
        self.assertIn("summary", payload)
        self.assertIn("items", payload)
        self.assertGreaterEqual(int(payload["summary"].get("scheduled") or 0), 1)

    def test_scan_dry_run_no_db_writes(self) -> None:
        slug = f"rr-scan-{uuid.uuid4().hex[:8]}"
        rk = f"{slug}:sess-scan"
        row = self._add_schedule(slug=slug, rk=rk, due_offset_minutes=-15)
        before_status = row.status
        before_updated = row.updated_at
        scan = build_recovery_resume_scan_readonly(store_slug=slug)
        self.assertTrue(scan.get("dry_run"))
        self.assertTrue(scan.get("no_db_writes"))
        self.assertIn("would_resume", scan)
        self.assertIn("results", scan)
        db.session.refresh(row)
        self.assertEqual(row.status, before_status)
        self.assertEqual(row.updated_at, before_updated)

    def test_inspect_filters_status_and_resume_only(self) -> None:
        slug = f"rr-filt-{uuid.uuid4().hex[:8]}"
        self._add_schedule(slug=slug, rk=f"{slug}:due", due_offset_minutes=-5)
        self._add_schedule(
            slug=slug,
            rk=f"{slug}:future",
            due_offset_minutes=120,
        )
        due_only = build_recovery_resume_inspect_readonly(
            store_slug=slug,
            resume_only=True,
        )
        for item in due_only.get("items") or []:
            self.assertTrue(item.get("resume_eligible"))
        scheduled = build_recovery_resume_inspect_readonly(
            store_slug=slug,
            status="scheduled",
        )
        for item in scheduled.get("items") or []:
            self.assertEqual(item.get("status"), "scheduled")

    def test_endpoint_requires_auth(self) -> None:
        r = self.client.get("/admin/operations/recovery-resume-inspect")
        self.assertEqual(r.status_code, 401)
        r2 = self.client.get("/admin/operations/recovery-resume-scan")
        self.assertEqual(r2.status_code, 401)

    def test_endpoints_return_json(self) -> None:
        self._login()
        cookies = {admin_cookie_name(): self.client.cookies.get(admin_cookie_name())}
        r = self.client.get(
            "/admin/operations/recovery-resume-inspect",
            cookies=cookies,
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("read_only"))
        r2 = self.client.get(
            "/admin/operations/recovery-resume-scan",
            cookies=cookies,
        )
        self.assertEqual(r2.status_code, 200)
        body2 = r2.json()
        self.assertTrue(body2.get("ok"))
        self.assertTrue(body2.get("dry_run"))


if __name__ == "__main__":
    unittest.main()
