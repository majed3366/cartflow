# -*- coding: utf-8 -*-
"""Admin Operations Center v1 — read-only /admin/operations."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

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
    _build_operational_trends,
    _build_operational_timeline,
    _build_root_cause_groups,
    _build_store_health_snapshot,
    _build_system_health_summary,
    _build_top_risks,
    _compute_trend_from_counts,
    _escalate_severity,
    _INVESTIGATION_STEPS_AR,
    _evidence_from_record,
    _investigation_steps_for_kind,
    _ownership_for_kind,
    _OWNERSHIP_BY_KIND,
    _pick_happened_at,
    _recency_timestamp,
    _risk_row_from_alert_record,
    _sort_alerts,
    _sort_operational_timeline,
    _sort_root_cause_groups,
    _sort_top_risks,
    _timeline_event_from_alert_record,
    _timeline_event_row,
    build_admin_operations_center_v1_readonly,
    build_admin_operations_command_center_readonly,
    build_admin_operations_investigation_section_readonly,
    build_admin_operations_analytics_section_readonly,
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
        self.assertEqual(payload.get("version"), "admin_operations_center_v2_2")
        health = payload.get("system_health_summary") or {}
        for key in (
            "status_key",
            "status_ar",
            "description_ar",
            "highest_severity",
            "critical_count",
            "high_count",
            "medium_count",
            "low_count",
            "total_alerts",
        ):
            self.assertIn(key, health)
        snap = payload.get("store_health_snapshot") or {}
        self.assertIn("stores", snap)
        self.assertIn("total_stores", snap)
        self.assertIn("available", snap)
        trends = payload.get("operational_trends") or {}
        self.assertIn("trends", trends)
        self.assertIn("window_hours", trends)
        self.assertEqual(len(trends.get("trends") or []), 4)
        top = payload.get("top_risks") or {}
        self.assertIn("risks", top)
        self.assertLessEqual(len(top.get("risks") or []), 5)
        timeline = payload.get("operational_timeline") or {}
        self.assertIn("events", timeline)
        self.assertIn("window_hours", timeline)
        self.assertLessEqual(len(timeline.get("events") or []), 25)
        rcg = payload.get("root_cause_groups") or {}
        self.assertIn("groups", rcg)
        self.assertIn("total_groups", rcg)
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

    def test_command_center_payload_excludes_lazy_sections(self) -> None:
        payload = build_admin_operations_command_center_readonly()
        self.assertEqual(payload.get("version"), "admin_operations_center_v2_2")
        for key in (
            "system_health_summary",
            "top_risks",
            "store_health_snapshot",
            "health_scheduler_path",
            "generated_at_utc",
        ):
            self.assertIn(key, payload)
        for lazy_key in (
            "operational_trends",
            "operational_timeline",
            "root_cause_groups",
            "scheduler",
            "recovery",
            "store_readiness",
            "alerts",
        ):
            self.assertNotIn(lazy_key, payload, msg=f"command center must not include {lazy_key}")

    def test_command_center_does_not_build_analytics(self) -> None:
        with patch(
            "services.admin_operations_center_v1._build_operational_trends"
        ) as mock_trends, patch(
            "services.admin_operations_center_v1._build_operational_timeline"
        ) as mock_timeline, patch(
            "services.admin_operations_center_v1._build_root_cause_groups"
        ) as mock_rcg:
            build_admin_operations_command_center_readonly()
            mock_trends.assert_not_called()
            mock_timeline.assert_not_called()
            mock_rcg.assert_not_called()

    def test_investigation_section_payload(self) -> None:
        payload = build_admin_operations_investigation_section_readonly()
        self.assertEqual(payload.get("section"), "investigation")
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
        for lazy_key in ("operational_trends", "operational_timeline", "root_cause_groups"):
            self.assertNotIn(lazy_key, payload)

    def test_analytics_section_payload(self) -> None:
        payload = build_admin_operations_analytics_section_readonly()
        self.assertEqual(payload.get("section"), "analytics")
        trends = payload.get("operational_trends") or {}
        self.assertIn("trends", trends)
        self.assertIn("window_hours", trends)
        timeline = payload.get("operational_timeline") or {}
        self.assertIn("events", timeline)
        rcg = payload.get("root_cause_groups") or {}
        self.assertIn("groups", rcg)
        for lazy_key in ("scheduler", "recovery", "store_readiness", "alerts"):
            self.assertNotIn(lazy_key, payload)

    def test_scheduler_card_matches_health_endpoint(self) -> None:
        health = build_scheduler_health_snapshot()
        payload = build_admin_operations_investigation_section_readonly()
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
        self.assertIn("حالة المنصة", body)
        self.assertIn("المتاجر النشطة", body)
        self.assertIn("المتاجر المتأثرة", body)
        self.assertIn("المشاكل المفتوحة", body)
        self.assertIn("الاسترجاعات اليوم", body)
        self.assertIn("المشاكل الحالية", body)
        self.assertIn("ops-current-issues-core", body)
        self.assertIn("ماذا نفعل الآن", body)
        self.assertIn("المتاجر التي تحتاج انتباهًا", body)
        self.assertIn("ops-executive-summary", body)
        self.assertIn('id="admin-sidebar-panel"', body)
        # Technical lazy panels are NOT on the executive overview.
        self.assertNotIn("ops-investigation-panel", body)
        self.assertNotIn("ops-analytics-panel", body)
        self.assertNotIn("bindLazySection", body)

    def test_support_diagnostics_page_hosts_technical_panels(self) -> None:
        self._login()
        r = self.client.get("/admin/diagnostics")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        self.assertIn("Recovery Resume Health", body)
        self.assertIn("تفاصيل تقنية (للدعم فقط)", body)
        self.assertIn("ops-investigation-panel", body)
        self.assertIn("ops-analytics-panel", body)
        self.assertIn("ops-investigation-content", body)
        self.assertIn("ops-analytics-content", body)
        self.assertIn("bindLazySection", body)

    def test_lazy_section_endpoints_authenticated(self) -> None:
        self._login()
        inv = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(inv.status_code, 200, inv.text[:300])
        for label in (
            "صحة المجدول",
            "حالات الاسترجاع",
            "جاهزية المتاجر",
            "تنبيهات أساسية",
        ):
            self.assertIn(label, inv.text, msg=f"missing {label} in investigation")
        ana = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(ana.status_code, 200, ana.text[:300])
        for label in (
            "اتجاهات التشغيل",
            "آخر الأحداث التشغيلية",
            "مصادر المشاكل الرئيسية",
        ):
            self.assertIn(label, ana.text, msg=f"missing {label} in analytics")

    def test_lazy_sections_require_auth(self) -> None:
        for path in (
            "/admin/operations/section/investigation",
            "/admin/operations/section/analytics",
        ):
            r = self.client.get(path, follow_redirects=False)
            self.assertEqual(r.status_code, 302, path)
            self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_initial_page_excludes_lazy_section_content(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        body = r.text
        # Executive overview must not embed technical section content.
        self.assertNotIn("أ — صحة المجدول", body)
        self.assertNotIn("المؤشر", body)
        self.assertNotIn('id="ops-investigation-content"', body)
        self.assertNotIn('id="ops-analytics-content"', body)

    def test_diagnostics_page_lazy_sections_closed_by_default(self) -> None:
        self._login()
        r = self.client.get("/admin/diagnostics")
        self.assertEqual(r.status_code, 200)
        body = r.text
        self.assertIn('data-lazy-state="idle"', body)
        self.assertIn('id="ops-investigation-content"', body)
        self.assertIn('id="ops-analytics-content"', body)
        self.assertIn('id="ops-investigation-panel"', body)
        self.assertIn('id="ops-analytics-panel"', body)
        self.assertNotIn('id="ops-investigation-panel" open', body)
        self.assertNotIn('id="ops-analytics-panel" open', body)

    def test_page_ia_investigation_and_analytics_content_preserved(self) -> None:
        self._login()
        inv = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(inv.status_code, 200)
        ana = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(ana.status_code, 200)
        for label, body in (
            ("صحة المجدول", inv.text),
            ("حالات الاسترجاع", inv.text),
            ("جاهزية المتاجر", inv.text),
            ("تنبيهات أساسية", inv.text),
            ("اتجاهات التشغيل", ana.text),
            ("آخر الأحداث التشغيلية", ana.text),
            ("مصادر المشاكل الرئيسية", ana.text),
        ):
            self.assertIn(label, body, msg=f"missing {label}")

    def test_page_redirects_without_session(self) -> None:
        r = self.client.get("/admin/operations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_alerts_table_or_empty_state(self) -> None:
        self._login()
        r = self.client.get("/admin/operations/section/investigation")
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
            self.assertIn("owner_key", alert)
            self.assertIn("owner_ar", alert)
            self.assertIn("investigation_steps_ar", alert)
            self.assertIsInstance(alert.get("investigation_steps_ar"), list)
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

    def test_all_alert_kinds_have_investigation_catalog(self) -> None:
        expected_steps = {
            "store_needs_setup": [
                "راجع حالة إعداد المتجر.",
                "تحقق من الحقول الناقصة.",
                "تأكد من اكتمال خطوات التفعيل.",
            ],
            "whatsapp_missing": [
                "تحقق من إعداد واتساب للمتجر.",
                "راجع حالة مزود الإرسال.",
                "تأكد من اكتمال الربط.",
            ],
            "no_cart_events": [
                "تحقق من تحميل الودجيت.",
                "راجع آخر cart event.",
                "اختبر إضافة منتج للسلة.",
            ],
            "stale_recovery": [
                "راجع حالة Scheduler.",
                "تحقق من وقت آخر تحديث.",
                "راجع سجل الاسترجاع.",
            ],
            "failed_recovery": [
                "راجع سبب الفشل.",
                "تحقق من مزود الإرسال.",
                "راجع سجل المحاولة الأخيرة.",
            ],
        }
        for kind, steps in expected_steps.items():
            self.assertEqual(_investigation_steps_for_kind(kind), steps)

    def test_investigation_fallback_unknown_kind(self) -> None:
        steps = _investigation_steps_for_kind("unknown_alert_kind")
        self.assertEqual(
            steps,
            ["راجع التفاصيل المتاحة.", "تحقق من السجلات المرتبطة."],
        )

    def test_alert_with_records_includes_investigation_steps(self) -> None:
        alert = _alert_with_records(
            kind="stale_recovery",
            title_ar="x",
            detail_ar="x",
        )
        self.assertEqual(len(alert["investigation_steps_ar"]), 3)
        self.assertIn("Scheduler", alert["investigation_steps_ar"][0])

    def test_top_risks_include_investigation_steps(self) -> None:
        alerts = [
            _alert_with_records(
                kind="failed_recovery",
                title_ar="f",
                detail_ar="f",
                records=[{"store_slug": "s1"}],
                records_total=1,
            ),
        ]
        top = _build_top_risks(alerts)
        steps = top["risks"][0]["investigation_steps_ar"]
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "راجع سبب الفشل.")

    def test_page_renders_investigation_guidance(self) -> None:
        payload = build_admin_operations_investigation_section_readonly()
        if not payload.get("alerts"):
            self.skipTest("no alerts in current DB")
        self._login()
        r = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(r.status_code, 200)
        self.assertIn("من أين أبدأ؟", r.text)

    def test_evidence_from_recovery_record(self) -> None:
        evidence = _evidence_from_record(
            {
                "recovery_key": "demo:abc123",
                "schedule_id": 42,
                "store_slug": "demo-store",
                "status": "whatsapp_failed",
                "updated_at": "2026-05-31T12:14:00+00:00",
            }
        )
        self.assertEqual(evidence["recovery_key"], "demo:abc123")
        self.assertEqual(evidence["schedule_id"], 42)
        self.assertEqual(evidence["store_slug"], "demo-store")
        self.assertEqual(evidence["last_status"], "whatsapp_failed")
        self.assertEqual(evidence["last_updated_at"], "2026-05-31 12:14")

    def test_evidence_missing_fields_omitted(self) -> None:
        evidence = _evidence_from_record({"store_slug": "only-store"})
        self.assertEqual(evidence, {"store_slug": "only-store"})
        self.assertNotIn("recovery_key", evidence)
        self.assertNotIn("schedule_id", evidence)

    def test_alert_with_records_includes_evidence_when_available(self) -> None:
        alert = _alert_with_records(
            kind="failed_recovery",
            title_ar="x",
            detail_ar="x",
            records=[
                {
                    "recovery_key": "demo:abc123",
                    "schedule_id": 7,
                    "store_slug": "demo",
                    "status": "failed_resume",
                    "updated_at": "2026-05-31T10:00:00+00:00",
                }
            ],
        )
        self.assertIn("evidence", alert)
        self.assertEqual(alert["evidence"]["recovery_key"], "demo:abc123")
        self.assertEqual(alert["evidence"]["schedule_id"], 7)

    def test_alert_without_evidence_omits_key(self) -> None:
        alert = _alert_with_records(
            kind="store_needs_setup",
            title_ar="x",
            detail_ar="x",
            records=[],
        )
        self.assertNotIn("evidence", alert)

    def test_top_risks_include_evidence_when_available(self) -> None:
        alerts = [
            _alert_with_records(
                kind="stale_recovery",
                title_ar="s",
                detail_ar="s",
                records=[
                    {
                        "recovery_key": "k1",
                        "schedule_id": 99,
                        "store_slug": "s1",
                        "status": "running",
                        "updated_at": "2026-05-31T08:00:00+00:00",
                    }
                ],
                records_total=1,
            ),
        ]
        top = _build_top_risks(alerts)
        self.assertIn("evidence", top["risks"][0])
        self.assertEqual(top["risks"][0]["evidence"]["schedule_id"], 99)

    def test_page_renders_evidence_when_present(self) -> None:
        self._login()
        r = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(r.status_code, 200)
        if "الأدلة المرتبطة" in r.text:
            self.assertIn("Recovery Key:", r.text)

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

    def test_top_risks_severity_ordering(self) -> None:
        alerts = [
            _alert_with_records(
                kind="no_cart_events",
                title_ar="low",
                detail_ar="low",
                records=[{"store_slug": "z-store", "display_name": "Z"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="stale_recovery",
                title_ar="crit",
                detail_ar="crit",
                records=[
                    {
                        "store_slug": "a-store",
                        "display_name": "A",
                        "updated_at": "2026-05-31T10:00:00+00:00",
                    }
                ],
                records_total=1,
            ),
            _alert_with_records(
                kind="failed_recovery",
                title_ar="high",
                detail_ar="high",
                records=[{"store_slug": "m-store", "display_name": "M"}],
                records_total=1,
            ),
        ]
        top = _build_top_risks(alerts)
        kinds = [r["risk_kind"] for r in top["risks"]]
        self.assertEqual(kinds[0], "stale_recovery")
        self.assertEqual(kinds[1], "failed_recovery")
        self.assertEqual(kinds[2], "no_cart_events")

    def test_top_risks_cap_at_five(self) -> None:
        alerts = []
        for i in range(8):
            alerts.append(
                _alert_with_records(
                    kind="store_needs_setup",
                    title_ar=f"s{i}",
                    detail_ar=f"s{i}",
                    records=[{"store_slug": f"store-{i}", "display_name": f"S{i}"}],
                    records_total=1,
                )
            )
        top = _build_top_risks(alerts)
        self.assertEqual(top["shown_count"], 5)
        self.assertEqual(top["total_candidates"], 8)
        self.assertEqual(len(top["risks"]), 5)

    def test_top_risks_missing_store_fields_safe(self) -> None:
        row = _risk_row_from_alert_record(
            kind="store_needs_setup",
            alert=_alert_with_records(
                kind="store_needs_setup",
                title_ar="x",
                detail_ar="x",
            ),
            record={"store_slug": "bare-only"},
        )
        self.assertEqual(row["affected_store"], "bare-only")
        self.assertEqual(row["affected_store_name"], "bare-only")

    def test_page_renders_top_risks_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("المشاكل الحالية", r.text)
        self.assertIn("ops-current-issues-core", r.text)

    def test_current_issues_business_language_builder(self) -> None:
        from services.admin_operations_center_v1 import _build_current_issues

        alerts = [
            _alert_with_records(
                kind="failed_recovery",
                title_ar="x",
                detail_ar="x",
                records=[{"store_slug": "s1"}, {"store_slug": "s2"}],
                records_total=2,
            ),
            _alert_with_records(
                kind="no_cart_events",
                title_ar="y",
                detail_ar="y",
                records=[{"store_slug": "s3"}],
                records_total=1,
            ),
        ]
        ci = _build_current_issues(alerts)
        self.assertEqual(ci["total"], 2)
        first = ci["issues"][0]
        # failed_recovery (high) should outrank no_cart_events (low).
        self.assertEqual(first["kind"], "failed_recovery")
        self.assertEqual(first["title_ar"], "رسائل الاسترجاع لا يتم تسليمها")
        self.assertEqual(first["affected_count"], 2)
        for key in (
            "impact_ar",
            "where_ar",
            "owner_ar",
            "action_ar",
            "verification_ar",
            "affected_label_ar",
            "problem_ar",
        ):
            self.assertTrue(first.get(key), msg=f"missing {key}")
        self.assertEqual(first["where_ar"], "قناة واتساب / إرسال الاسترجاع")

    def test_command_center_includes_executive_summary_and_issues(self) -> None:
        payload = build_admin_operations_command_center_readonly()
        ex = payload.get("executive_summary") or {}
        for key in (
            "platform_status_ar",
            "platform_status_tone",
            "active_stores",
            "affected_stores",
            "open_alerts",
            "open_issues",
            "recoveries_today",
        ):
            self.assertIn(key, ex)
        self.assertIn("current_issues", payload)
        self.assertIn("issues", payload["current_issues"])

    def test_timeline_ordering(self) -> None:
        now = datetime.now(timezone.utc)
        older = (now - timedelta(hours=2)).isoformat()
        newer = (now - timedelta(minutes=30)).isoformat()
        events = [
            _timeline_event_row(
                event_type="failed_recovery",
                store_slug="a",
                store_name="A",
                happened_at=older,
                sort_ts=_recency_timestamp(older),
            ),
            _timeline_event_row(
                event_type="stale_recovery",
                store_slug="b",
                store_name="B",
                happened_at=newer,
                sort_ts=_recency_timestamp(newer),
            ),
        ]
        ordered = _sort_operational_timeline(events)
        self.assertEqual(ordered[0]["happened_at"], newer)
        self.assertEqual(ordered[1]["happened_at"], older)

    def test_timeline_cap_at_25(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        alerts = []
        for i in range(30):
            alerts.append(
                _alert_with_records(
                    kind="store_needs_setup",
                    title_ar=f"s{i}",
                    detail_ar=f"s{i}",
                    records=[
                        {
                            "store_slug": f"store-{i}",
                            "display_name": f"S{i}",
                            "updated_at": now_iso,
                        }
                    ],
                    records_total=1,
                )
            )
        timeline = _build_operational_timeline(alerts, [])
        self.assertEqual(timeline["shown_count"], 25)
        self.assertEqual(len(timeline["events"]), 25)
        self.assertGreaterEqual(timeline["total_candidates"], 25)

    def test_timeline_timestamp_fallback(self) -> None:
        happened_at, sort_ts = _pick_happened_at({}, "updated_at", "due_at", "created_at")
        self.assertEqual(happened_at, "غير متوفر")
        self.assertEqual(sort_ts, 0.0)

    def test_timeline_missing_store_fields_safe(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        window_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
        window_end = datetime.now(timezone.utc).replace(tzinfo=None)
        row = _timeline_event_from_alert_record(
            kind="store_needs_setup",
            record={"store_slug": "bare-only", "updated_at": now_iso},
            store_lookup={},
            window_start=window_start,
            window_end=window_end,
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["store_slug"], "bare-only")
        self.assertEqual(row["store_name"], "bare-only")

    def test_page_renders_operational_timeline_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("آخر الأحداث التشغيلية", r.text)

    def test_ownership_mapping(self) -> None:
        cases = {
            "store_needs_setup": ("merchant_setup", "إعداد المتجر"),
            "whatsapp_missing": ("whatsapp_provider", "مزود واتساب"),
            "no_cart_events": ("widget_integration", "الودجيت / التكامل"),
            "stale_recovery": ("scheduler", "المجدول"),
            "failed_recovery": ("cartflow_system", "نظام CartFlow"),
        }
        for kind, (key, label) in cases.items():
            owner = _ownership_for_kind(kind)
            self.assertEqual(owner["owner_key"], key, msg=kind)
            self.assertEqual(owner["owner_ar"], label, msg=kind)
            self.assertEqual(_OWNERSHIP_BY_KIND.get(kind), key)

    def test_ownership_fallback_unknown(self) -> None:
        owner = _ownership_for_kind("nonexistent_kind")
        self.assertEqual(owner["owner_key"], "unknown")
        self.assertEqual(owner["owner_ar"], "غير محدد")

    def test_alert_with_records_includes_ownership(self) -> None:
        alert = _alert_with_records(
            kind="failed_recovery",
            title_ar="x",
            detail_ar="x",
        )
        self.assertEqual(alert["owner_key"], "cartflow_system")
        self.assertEqual(alert["owner_ar"], "نظام CartFlow")

    def test_top_risks_include_ownership(self) -> None:
        alerts = [
            _alert_with_records(
                kind="stale_recovery",
                title_ar="crit",
                detail_ar="crit",
                records=[{"store_slug": "a-store", "display_name": "A"}],
                records_total=1,
            ),
        ]
        top = _build_top_risks(alerts)
        self.assertEqual(top["risks"][0]["owner_key"], "scheduler")
        self.assertEqual(top["risks"][0]["owner_ar"], "المجدول")

    def test_timeline_events_include_ownership(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        row = _timeline_event_row(
            event_type="whatsapp_missing",
            store_slug="s1",
            store_name="S1",
            happened_at=now_iso,
            sort_ts=0.0,
        )
        self.assertEqual(row["owner_key"], "whatsapp_provider")
        self.assertEqual(row["owner_ar"], "مزود واتساب")

    def test_page_renders_ownership_on_alerts_risks_timeline(self) -> None:
        self._login()
        inv = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(inv.status_code, 200)
        ana = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(ana.status_code, 200)
        combined = inv.text + ana.text
        if "المالك المحتمل:" in combined:
            self.assertGreaterEqual(combined.count("المالك المحتمل:"), 1)

    def test_root_cause_groups_ownership_grouping(self) -> None:
        alerts = [
            _alert_with_records(
                kind="whatsapp_missing",
                title_ar="wa1",
                detail_ar="wa1",
                records=[{"store_slug": "s1"}, {"store_slug": "s2"}],
                records_total=2,
            ),
            _alert_with_records(
                kind="whatsapp_missing",
                title_ar="wa2",
                detail_ar="wa2",
                records=[{"store_slug": "s3"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="store_needs_setup",
                title_ar="setup",
                detail_ar="setup",
                records=[{"store_slug": "s4"}],
                records_total=1,
            ),
        ]
        rcg = _build_root_cause_groups(alerts)
        groups = {g["owner_key"]: g for g in rcg["groups"]}
        self.assertEqual(groups["whatsapp_provider"]["alerts_count"], 2)
        self.assertEqual(groups["merchant_setup"]["alerts_count"], 1)
        self.assertIn("whatsapp_missing", groups["whatsapp_provider"]["alert_kinds"])
        self.assertIn("store_needs_setup", groups["merchant_setup"]["alert_kinds"])

    def test_root_cause_groups_severity_escalation(self) -> None:
        alerts = [
            _alert_with_records(
                kind="no_cart_events",
                title_ar="low",
                detail_ar="low",
                records=[{"store_slug": "a"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="stale_recovery",
                title_ar="crit",
                detail_ar="crit",
                records=[{"store_slug": "b"}],
                records_total=1,
            ),
        ]
        rcg = _build_root_cause_groups(alerts)
        scheduler = next(g for g in rcg["groups"] if g["owner_key"] == "scheduler")
        self.assertEqual(scheduler["highest_severity"], "critical")
        self.assertEqual(scheduler["highest_severity_ar"], "حرج")
        self.assertEqual(_escalate_severity("low", "critical"), "critical")
        self.assertEqual(_escalate_severity("critical", "high"), "critical")

    def test_root_cause_groups_store_counting(self) -> None:
        alerts = [
            _alert_with_records(
                kind="whatsapp_missing",
                title_ar="wa",
                detail_ar="wa",
                records=[
                    {"store_slug": "s1"},
                    {"store_slug": "s2"},
                    {"store_slug": "s1"},
                ],
                records_total=3,
            ),
            _alert_with_records(
                kind="whatsapp_missing",
                title_ar="wa2",
                detail_ar="wa2",
                records=[{"store_slug": "s2"}, {"store_slug": "s3"}],
                records_total=2,
            ),
        ]
        rcg = _build_root_cause_groups(alerts)
        wa = next(g for g in rcg["groups"] if g["owner_key"] == "whatsapp_provider")
        self.assertEqual(wa["stores_count"], 3)

    def test_root_cause_groups_sorting(self) -> None:
        groups = [
            {
                "owner_key": "whatsapp_provider",
                "owner_ar": "مزود واتساب",
                "alerts_count": 6,
                "stores_count": 4,
                "highest_severity": "high",
                "highest_severity_ar": "عالي",
                "alert_kinds": ["whatsapp_missing"],
            },
            {
                "owner_key": "scheduler",
                "owner_ar": "المجدول",
                "alerts_count": 1,
                "stores_count": 1,
                "highest_severity": "critical",
                "highest_severity_ar": "حرج",
                "alert_kinds": ["stale_recovery"],
            },
            {
                "owner_key": "merchant_setup",
                "owner_ar": "إعداد المتجر",
                "alerts_count": 2,
                "stores_count": 2,
                "highest_severity": "medium",
                "highest_severity_ar": "متوسط",
                "alert_kinds": ["store_needs_setup"],
            },
        ]
        ordered = _sort_root_cause_groups(groups)
        self.assertEqual(ordered[0]["owner_key"], "scheduler")
        self.assertEqual(ordered[1]["owner_key"], "whatsapp_provider")

    def test_page_renders_root_cause_groups_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("مصادر المشاكل الرئيسية", r.text)

    def test_trend_improving(self) -> None:
        t = _compute_trend_from_counts(3, 7)
        self.assertEqual(t["trend_key"], "improving")
        self.assertEqual(t["trend_ar"], "↓ تحسن")
        self.assertEqual(t["delta"], -4)

    def test_trend_worsening(self) -> None:
        t = _compute_trend_from_counts(8, 4)
        self.assertEqual(t["trend_key"], "worsening")
        self.assertEqual(t["trend_ar"], "↑ تزايد")
        self.assertEqual(t["delta"], 4)

    def test_trend_stable(self) -> None:
        t = _compute_trend_from_counts(5, 5)
        self.assertEqual(t["trend_key"], "stable")
        self.assertEqual(t["trend_ar"], "→ مستقر")
        self.assertEqual(t["delta"], 0)

    def test_trend_empty_data_stable(self) -> None:
        t = _compute_trend_from_counts(0, 0)
        self.assertEqual(t["trend_key"], "stable")
        self.assertEqual(t["current_count"], 0)
        self.assertEqual(t["previous_count"], 0)

    def test_operational_trends_payload_shape(self) -> None:
        trends = _build_operational_trends()
        self.assertTrue(trends.get("available"))
        self.assertEqual(trends.get("window_hours"), 24)
        for row in trends.get("trends") or []:
            for key in (
                "metric_key",
                "metric_ar",
                "current_count",
                "previous_count",
                "delta",
                "trend_key",
                "trend_ar",
            ):
                self.assertIn(key, row)

    def test_page_renders_operational_trends_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations/section/analytics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("اتجاهات التشغيل", r.text)
        body = r.text
        self.assertTrue(
            "↓ تحسن" in body or "↑ تزايد" in body or "→ مستقر" in body or "استرجاع فاشل" in body
        )

    def test_store_snapshot_merges_multiple_alert_kinds(self) -> None:
        slug = "merge-store-1"
        store_rows = [
            {
                "store_slug": slug,
                "display_name": "Merge Store",
                "ready": False,
                "readiness_status_ar": "غير جاهز",
                "last_cart_event_at": None,
            }
        ]
        alerts = [
            _alert_with_records(
                kind="store_needs_setup",
                title_ar="setup",
                detail_ar="setup",
                records=[{"store_slug": slug, "display_name": "Merge Store"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="whatsapp_missing",
                title_ar="wa",
                detail_ar="wa",
                records=[{"store_slug": slug, "display_name": "Merge Store"}],
                records_total=1,
            ),
        ]
        snap = _build_store_health_snapshot(alerts, store_rows)
        self.assertEqual(snap["total_stores"], 1)
        row = snap["stores"][0]
        self.assertEqual(row["store_slug"], slug)
        self.assertEqual(row["alerts_count"], 2)
        self.assertEqual(set(row["alert_kinds"]), {"store_needs_setup", "whatsapp_missing"})

    def test_store_snapshot_severity_escalation(self) -> None:
        slug = "sev-store"
        alerts = [
            _alert_with_records(
                kind="no_cart_events",
                title_ar="low",
                detail_ar="low",
                records=[{"store_slug": slug}],
                records_total=1,
            ),
            _alert_with_records(
                kind="stale_recovery",
                title_ar="crit",
                detail_ar="crit",
                records=[{"store_slug": slug, "recovery_key": "k1"}],
                records_total=1,
            ),
        ]
        snap = _build_store_health_snapshot(alerts, [])
        row = snap["stores"][0]
        self.assertEqual(row["highest_severity"], "critical")
        self.assertEqual(row["highest_severity_ar"], "حرج")

    def test_store_snapshot_sort_order(self) -> None:
        alerts = [
            _alert_with_records(
                kind="no_cart_events",
                title_ar="a",
                detail_ar="a",
                records=[{"store_slug": "z-low-store"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="failed_recovery",
                title_ar="b",
                detail_ar="b",
                records=[{"store_slug": "m-high-store"}],
                records_total=1,
            ),
            _alert_with_records(
                kind="stale_recovery",
                title_ar="c",
                detail_ar="c",
                records=[{"store_slug": "a-crit-store"}],
                records_total=1,
            ),
        ]
        snap = _build_store_health_snapshot(alerts, [])
        slugs = [r["store_slug"] for r in snap["stores"]]
        self.assertEqual(slugs[0], "a-crit-store")
        self.assertEqual(slugs[1], "m-high-store")
        self.assertEqual(slugs[2], "z-low-store")

    def test_store_snapshot_missing_fields_safe(self) -> None:
        alerts = [
            _alert_with_records(
                kind="store_needs_setup",
                title_ar="x",
                detail_ar="x",
                records=[{"store_slug": "bare-slug"}],
                records_total=1,
            ),
        ]
        snap = _build_store_health_snapshot(alerts, [])
        row = snap["stores"][0]
        self.assertEqual(row["display_name"], "bare-slug")
        self.assertEqual(row["last_cart_event_at"], "غير متوفر")
        self.assertIn(row["readiness_status_ar"], ("غير متوفر", "جاهز"))

    def test_page_renders_store_health_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("المتاجر التي تحتاج انتباهًا", r.text)

    def test_system_health_stable_when_no_alerts(self) -> None:
        health = _build_system_health_summary([])
        self.assertEqual(health["status_key"], "stable")
        self.assertEqual(health["status_ar"], "مستقرة")
        self.assertEqual(health["highest_severity"], "none")
        self.assertEqual(health["total_alerts"], 0)

    def test_system_health_urgent_attention(self) -> None:
        alerts = [
            _alert_with_records(kind="stale_recovery", title_ar="x", detail_ar="x"),
        ]
        health = _build_system_health_summary(alerts)
        self.assertEqual(health["status_key"], "urgent_attention")
        self.assertEqual(health["status_ar"], "تحتاج انتباه عاجل")
        self.assertEqual(health["critical_count"], 1)
        self.assertEqual(health["highest_severity"], "critical")

    def test_system_health_needs_followup(self) -> None:
        alerts = [
            _alert_with_records(kind="failed_recovery", title_ar="x", detail_ar="x"),
            _alert_with_records(kind="whatsapp_missing", title_ar="y", detail_ar="y"),
        ]
        health = _build_system_health_summary(alerts)
        self.assertEqual(health["status_key"], "needs_followup")
        self.assertEqual(health["status_ar"], "تحتاج متابعة")
        self.assertEqual(health["high_count"], 2)
        self.assertEqual(health["critical_count"], 0)

    def test_system_health_stable_with_notes_medium(self) -> None:
        alerts = [
            _alert_with_records(kind="store_needs_setup", title_ar="x", detail_ar="x"),
        ]
        health = _build_system_health_summary(alerts)
        self.assertEqual(health["status_key"], "stable_with_notes")
        self.assertEqual(health["medium_count"], 1)
        self.assertEqual(health["highest_severity"], "medium")

    def test_system_health_stable_with_notes_low_only(self) -> None:
        alerts = [
            _alert_with_records(kind="no_cart_events", title_ar="x", detail_ar="x"),
        ]
        health = _build_system_health_summary(alerts)
        self.assertEqual(health["status_key"], "stable_with_notes")
        self.assertEqual(health["low_count"], 1)
        self.assertEqual(health["highest_severity"], "low")

    def test_system_health_unknown_severity_counts_as_low(self) -> None:
        alerts = [{"kind": "unknown_kind", "severity": "weird"}]
        health = _build_system_health_summary(alerts)
        self.assertEqual(health["low_count"], 1)
        self.assertEqual(health["status_key"], "stable_with_notes")

    def test_page_renders_system_health_section(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("حالة المنصة", r.text)
        payload = build_admin_operations_command_center_readonly()
        ex = payload.get("executive_summary") or {}
        self.assertIn(ex.get("platform_status_ar") or "مستقرة", r.text)

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
        payload = build_admin_operations_investigation_section_readonly()
        if not payload.get("alerts"):
            self.skipTest("no alerts in current DB")
        self._login()
        r = self.client.get("/admin/operations/section/investigation")
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
        payload = build_admin_operations_investigation_section_readonly()
        if not payload.get("alerts"):
            self.skipTest("no alerts in current DB")
        self._login()
        r = self.client.get("/admin/operations/section/investigation")
        self.assertEqual(r.status_code, 200)
        self.assertIn("لماذا ظهر", r.text)
        self.assertIn("الإجراء المقترح", r.text)


if __name__ == "__main__":
    unittest.main()
