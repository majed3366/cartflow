# -*- coding: utf-8 -*-
"""Admin Operations Center v1 — read-only /admin/operations."""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from datetime import datetime, timedelta, timezone

from extensions import db
from main import app
from models import RecoverySchedule, Store
from services.recovery_restart_survival import STATUS_RUNNING, STATUS_WHATSAPP_FAILED
from services.admin_operations_center_v1 import (
    _ALERT_EXPLANATIONS_AR,
    _ALERT_SEVERITY_AR,
    _alert_with_records,
    _sort_alerts,
    build_admin_operations_center_v1_readonly,
)
from services.cartflow_admin_http_auth import admin_cookie_name
from services.recovery_process_role_v1 import build_scheduler_health_snapshot


class AdminOperationsCenterV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ops-center-v1-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def _login(self) -> None:
        r = self.client.post(
            "/admin/operations/login",
            data={"password": "ops-center-v1-pass", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])

    def test_build_payload_has_required_sections(self) -> None:
        payload = build_admin_operations_center_v1_readonly()
        self.assertEqual(payload.get("version"), "admin_operations_center_v1_3")
        sch = payload.get("scheduler") or {}
        for key in ("role", "overdue_scheduled_count", "running_stale_count"):
            self.assertIn(key, sch)
        rec = payload.get("recovery") or {}
        for key in ("scheduled", "running", "completed", "failed", "expired"):
            self.assertIn(key, rec)
        st = payload.get("store_readiness") or {}
        for key in (
            "total_stores",
            "ready_stores",
            "stores_missing_whatsapp",
            "stores_no_recent_cart_events",
            "stores_needing_setup",
        ):
            self.assertIn(key, st)
        self.assertIsInstance(payload.get("alerts"), list)

    def test_scheduler_card_matches_health_endpoint(self) -> None:
        health = build_scheduler_health_snapshot()
        payload = build_admin_operations_center_v1_readonly()
        sch = payload.get("scheduler") or {}
        self.assertEqual(sch.get("role"), health.get("role"))
        self.assertEqual(
            sch.get("overdue_scheduled_count"), health.get("overdue_scheduled_count")
        )
        self.assertEqual(
            sch.get("running_stale_count"), health.get("running_stale_count")
        )

    def test_page_loads_authenticated(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        self.assertIn("مركز العمليات", body)
        self.assertIn("صحة المجدول", body)
        self.assertIn("حالات الاسترجاع", body)
        self.assertIn("جاهزية المتاجر", body)
        self.assertIn("تنبيهات أساسية", body)
        self.assertIn('id="admin-sidebar-panel"', body)

    def test_page_redirects_without_session(self) -> None:
        r = self.client.get("/admin/operations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_alerts_table_or_empty_state(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            "لا تنبيهات تشغيلية بارزة" in r.text or "<table" in r.text,
            msg="expected alerts table or empty state",
        )

    def test_alert_payload_shape_with_records(self) -> None:
        payload = build_admin_operations_center_v1_readonly()
        for alert in payload.get("alerts") or []:
            self.assertIn("kind", alert)
            self.assertIn("title_ar", alert)
            self.assertIn("detail_ar", alert)
            self.assertIn("why_ar", alert)
            self.assertIn("suggested_fix_ar", alert)
            self.assertIn("severity", alert)
            self.assertIn("severity_ar", alert)
            self.assertIn("priority_order", alert)
            self.assertTrue(alert.get("severity_ar"), msg=f"missing severity_ar for {alert.get('kind')}")
            self.assertTrue(alert.get("why_ar"), msg=f"missing why_ar for {alert.get('kind')}")
            self.assertTrue(
                alert.get("suggested_fix_ar"),
                msg=f"missing suggested_fix_ar for {alert.get('kind')}",
            )
            self.assertIn("records", alert)
            self.assertIn("records_total", alert)
            self.assertIn("records_hidden", alert)
            records = alert.get("records") or []
            self.assertLessEqual(len(records), 5)
            if alert.get("records_total", 0) > 5:
                self.assertGreater(alert.get("records_hidden", 0), 0)

    def test_all_alert_kinds_have_explanation_catalog(self) -> None:
        for kind in (
            "store_needs_setup",
            "whatsapp_missing",
            "no_cart_events",
            "failed_recovery",
            "stale_recovery",
        ):
            self.assertIn(kind, _ALERT_EXPLANATIONS_AR)
            self.assertTrue(_ALERT_EXPLANATIONS_AR[kind].get("why_ar"))
            self.assertTrue(_ALERT_EXPLANATIONS_AR[kind].get("suggested_fix_ar"))

    def test_all_alert_kinds_have_severity_catalog(self) -> None:
        expected = {
            "stale_recovery": ("critical", "حرج", 10),
            "failed_recovery": ("high", "عالي", 20),
            "whatsapp_missing": ("high", "عالي", 30),
            "store_needs_setup": ("medium", "متوسط", 40),
            "no_cart_events": ("low", "منخفض", 50),
        }
        for kind, (sev, sev_ar, order) in expected.items():
            self.assertIn(kind, _ALERT_SEVERITY_AR)
            meta = _ALERT_SEVERITY_AR[kind]
            self.assertEqual(meta["severity"], sev)
            self.assertEqual(meta["severity_ar"], sev_ar)
            self.assertEqual(meta["priority_order"], order)

    def test_alert_with_records_applies_explanations_by_kind(self) -> None:
        alert = _alert_with_records(
            kind="failed_recovery",
            title_ar="test",
            detail_ar="test",
        )
        self.assertEqual(alert["why_ar"], _ALERT_EXPLANATIONS_AR["failed_recovery"]["why_ar"])
        self.assertEqual(
            alert["suggested_fix_ar"],
            _ALERT_EXPLANATIONS_AR["failed_recovery"]["suggested_fix_ar"],
        )
        self.assertEqual(alert["severity"], "high")
        self.assertEqual(alert["severity_ar"], "عالي")
        self.assertEqual(alert["priority_order"], 20)

    def test_sort_alerts_priority_order(self) -> None:
        unsorted = [
            _alert_with_records(kind="no_cart_events", title_ar="z", detail_ar="z"),
            _alert_with_records(kind="stale_recovery", title_ar="a", detail_ar="a"),
            _alert_with_records(kind="whatsapp_missing", title_ar="b", detail_ar="b"),
            _alert_with_records(kind="failed_recovery", title_ar="c", detail_ar="c"),
            _alert_with_records(kind="store_needs_setup", title_ar="d", detail_ar="d"),
        ]
        ordered = _sort_alerts(unsorted)
        kinds = [a["kind"] for a in ordered]
        self.assertEqual(
            kinds,
            [
                "stale_recovery",
                "failed_recovery",
                "whatsapp_missing",
                "store_needs_setup",
                "no_cart_events",
            ],
        )

    def test_sort_alerts_tiebreak_by_records_total(self) -> None:
        low_count = _alert_with_records(
            kind="failed_recovery",
            title_ar="a",
            detail_ar="a",
            records_total=1,
        )
        high_count = _alert_with_records(
            kind="failed_recovery",
            title_ar="b",
            detail_ar="b",
            records_total=9,
        )
        ordered = _sort_alerts([low_count, high_count])
        self.assertEqual(ordered[0]["records_total"], 9)

    def test_alert_with_records_hidden_count(self) -> None:
        recs = [{"recovery_key": f"k{i}", "status": "failed"} for i in range(8)]
        alert = _alert_with_records(
            kind="failed_recovery",
            title_ar="test",
            detail_ar="test",
            records=recs,
            records_total=8,
        )
        self.assertEqual(len(alert["records"]), 5)
        self.assertEqual(alert["records_hidden"], 3)

    def test_failed_recovery_alert_includes_recovery_key(self) -> None:
        try:
            db.create_all()
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.recovery_key == "ops-v11:fail-key"
            ).delete()
            now = datetime.now(timezone.utc)
            db.session.add(
                RecoverySchedule(
                    recovery_key="ops-v11:fail-key",
                    store_slug="ops-v11-store",
                    session_id="sess-fail",
                    scheduled_at=now,
                    due_at=now,
                    effective_delay_seconds=60.0,
                    delay_source="test",
                    status=STATUS_WHATSAPP_FAILED,
                    step=1,
                    last_error="provider timeout",
                    updated_at=now.replace(tzinfo=None),
                )
            )
            db.session.commit()
            payload = build_admin_operations_center_v1_readonly()
            failed = [
                a
                for a in (payload.get("alerts") or [])
                if a.get("kind") == "failed_recovery"
            ]
            self.assertTrue(failed, msg="expected failed_recovery alert")
            records = failed[0].get("records") or []
            self.assertTrue(records, msg="expected record details")
            self.assertEqual(records[0].get("recovery_key"), "ops-v11:fail-key")
            self.assertEqual(records[0].get("store_slug"), "ops-v11-store")
            self.assertEqual(records[0].get("status"), STATUS_WHATSAPP_FAILED)
            self.assertIn("updated_at", records[0])
        finally:
            db.session.rollback()
            try:
                db.session.query(RecoverySchedule).filter(
                    RecoverySchedule.recovery_key == "ops-v11:fail-key"
                ).delete()
                db.session.commit()
            except Exception:  # noqa: BLE001
                db.session.rollback()

    def test_stale_recovery_alert_includes_stale_reason(self) -> None:
        try:
            db.create_all()
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.recovery_key == "ops-v11:stale-key"
            ).delete()
            old = datetime.now(timezone.utc) - timedelta(minutes=20)
            db.session.add(
                RecoverySchedule(
                    recovery_key="ops-v11:stale-key",
                    store_slug="ops-v11-store",
                    session_id="sess-stale",
                    scheduled_at=old,
                    due_at=old.replace(tzinfo=None),
                    effective_delay_seconds=60.0,
                    delay_source="test",
                    status=STATUS_RUNNING,
                    step=1,
                    updated_at=old.replace(tzinfo=None),
                )
            )
            db.session.commit()
            payload = build_admin_operations_center_v1_readonly()
            stale = [
                a
                for a in (payload.get("alerts") or [])
                if a.get("kind") == "stale_recovery"
                and (a.get("records") or [{}])[0].get("recovery_key") == "ops-v11:stale-key"
            ]
            self.assertTrue(stale, msg="expected stale_recovery alert for inserted row")
            rec = stale[0]["records"][0]
            self.assertEqual(rec.get("recovery_key"), "ops-v11:stale-key")
            self.assertIn("stale_reason_ar", rec)
            self.assertIn("updated_at", rec)
        finally:
            db.session.rollback()
            try:
                db.session.query(RecoverySchedule).filter(
                    RecoverySchedule.recovery_key == "ops-v11:stale-key"
                ).delete()
                db.session.commit()
            except Exception:  # noqa: BLE001
                db.session.rollback()

    def test_store_alert_includes_setup_details(self) -> None:
        try:
            db.create_all()
            slug = "ops-v11-setup-store"
            db.session.query(Store).filter(Store.zid_store_id == slug).delete()
            st = Store(
                zid_store_id=slug,
                widget_name="Ops Setup Store",
                is_active=False,
                recovery_attempts=0,
                cartflow_widget_enabled=False,
            )
            db.session.add(st)
            db.session.commit()
            payload = build_admin_operations_center_v1_readonly()
            setup = [
                a
                for a in (payload.get("alerts") or [])
                if a.get("kind") == "store_needs_setup"
                and any(
                    (r.get("store_slug") == slug)
                    for r in (a.get("records") or [])
                )
            ]
            self.assertTrue(setup, msg="expected store_needs_setup alert")
            rec = setup[0]["records"][0]
            self.assertEqual(rec.get("store_slug"), slug)
            self.assertFalse(rec.get("readiness_ready"))
            self.assertTrue(rec.get("missing_setup_fields"))
        finally:
            db.session.rollback()
            try:
                db.session.query(Store).filter(
                    Store.zid_store_id == "ops-v11-setup-store"
                ).delete()
                db.session.commit()
            except Exception:  # noqa: BLE001
                db.session.rollback()

    def test_page_renders_severity_labels_when_alerts_present(self) -> None:
        payload = build_admin_operations_center_v1_readonly()
        if not payload.get("alerts"):
            self.skipTest("no alerts in current DB")
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        body = r.text
        self.assertIn("الأولوية", body)
        for label in ("حرج", "عالي", "متوسط", "منخفض"):
            if label in body:
                break
        else:
            sev_ar = (payload["alerts"][0].get("severity_ar") or "")
            self.assertIn(sev_ar, body)

    def test_page_renders_explanation_labels_when_alerts_present(self) -> None:
        payload = build_admin_operations_center_v1_readonly()
        if not payload.get("alerts"):
            self.skipTest("no alerts in current DB")
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("لماذا ظهر", r.text)
        self.assertIn("الإجراء المقترح", r.text)


if __name__ == "__main__":
    unittest.main()
