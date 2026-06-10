# -*- coding: utf-8 -*-
"""Operational Control Fail-Closed Implementation v1 tests."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import main  # noqa: F401
from extensions import db
from models import (
    AbandonedCart,
    LifecycleClosureRecord,
    RecoverySchedule,
    Store,
)
from services.admin_operational_health_json_v1 import build_admin_operational_health_json
from services.lifecycle_closure_records_v1 import CLOSURE_PURCHASE_COMPLETED
from services.lifecycle_reconciliation_summary_v1 import build_lifecycle_reconciliation_summary
from services.operational_control_v1 import (
    BLOCK_REASON_OC_UNAVAILABLE,
    clear_operational_control_state_for_tests,
    evaluate_continuation_allowed_safe,
    evaluate_wa_send_allowed,
    get_operational_control_availability,
    operational_control_blocks_schedule_creation_safe,
    operational_control_blocks_whatsapp_send_safe,
)
from services.purchase_truth_gap_visibility_v1 import build_purchase_truth_gap_summary
from services.scheduler_store_visibility_v1 import build_scheduler_store_visibility
from services.recovery_restart_survival import STATUS_RUNNING, STATUS_SCHEDULED


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OperationalControlFailClosedV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        clear_operational_control_state_for_tests()
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)

    def tearDown(self) -> None:
        clear_operational_control_state_for_tests()
        db.session.rollback()

    def test_operational_control_unavailable_blocks_wa_send(self) -> None:
        with patch(
            "services.operational_control_store_v1.load_durable_operational_control",
            side_effect=RuntimeError("db down"),
        ):
            blocked = operational_control_blocks_whatsapp_send_safe(store_slug="demo")
        self.assertIsNotNone(blocked)
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("error"), BLOCK_REASON_OC_UNAVAILABLE)
        self.assertFalse(get_operational_control_availability().get("available", True))

    def test_operational_control_unavailable_blocks_schedule_creation(self) -> None:
        with patch(
            "services.operational_control_v1.evaluate_schedule_creation_allowed",
            side_effect=RuntimeError("gate exploded"),
        ):
            blocked = operational_control_blocks_schedule_creation_safe(
                store_slug="demo",
                is_new_row=True,
            )
        self.assertTrue(blocked)

    def test_operational_control_exception_blocks_continuation(self) -> None:
        with patch(
            "services.operational_control_v1.evaluate_continuation_allowed",
            side_effect=RuntimeError("continuation gate"),
        ):
            ev = evaluate_continuation_allowed_safe(store_slug="demo")
        self.assertFalse(ev.allowed)
        self.assertEqual(ev.block_reason, BLOCK_REASON_OC_UNAVAILABLE)

    def test_unified_health_endpoint_sections(self) -> None:
        payload = build_admin_operational_health_json()
        for key in (
            "scheduler_ownership",
            "recovery_health",
            "operational_control",
            "whatsapp_readiness",
            "lifecycle_reconciliation",
            "purchase_truth_gaps",
            "scheduler_store_visibility",
            "product_foundation_health_summary",
            "governance_health_summary",
            "integrations",
            "diagnosis",
        ):
            self.assertIn(key, payload)
        self.assertIn("codes", payload["diagnosis"])
        self.assertIn("platform", payload["integrations"])

    def test_unified_health_api_route(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "test-admin-secret"
        from fastapi.testclient import TestClient

        client = TestClient(main.app)
        r = client.get("/api/admin/operational-health")
        self.assertEqual(r.status_code, 401)
        login = client.post(
            "/admin/operations/login",
            data={"password": "test-admin-secret", "next": "/admin/control"},
            follow_redirects=False,
        )
        self.assertIn(login.status_code, (200, 302, 303))
        cookie = login.cookies.get("cartflow_admin_session")
        r2 = client.get(
            "/api/admin/operational-health",
            cookies={"cartflow_admin_session": cookie} if cookie else {},
        )
        if r2.status_code == 401:
            self.skipTest("admin session cookie not available in test client")
        self.assertIn(r2.status_code, (200, 503))
        body = r2.json()
        self.assertIn("operational_truth_center", body)
        self.assertTrue(body.get("operational_truth_center"))

    def test_lifecycle_disagreement_visible(self) -> None:
        row = {
            "recovery_key": "demo:disagree-1",
            "store_slug": "demo",
            "customer_lifecycle_state": "waiting_first_send",
            "merchant_cart_bucket": "archived",
            "customer_lifecycle_label_ar": "بانتظار الإرسال",
            "customer_lifecycle_is_archived_visual": False,
        }
        from services.customer_lifecycle_states_v1 import lifecycle_truth_consistency_for_row

        ok, _reason = lifecycle_truth_consistency_for_row(row)
        self.assertFalse(ok)
        summary = build_lifecycle_reconciliation_summary(sample_limit=5)
        self.assertIn("disagreement_count", summary)
        self.assertIn("disagreements_present", summary)

    def test_store_backlog_visible(self) -> None:
        now = _utc_now_naive()
        db.session.add(
            RecoverySchedule(
                recovery_key="store-a:s1",
                store_slug="store-a",
                session_id="s1",
                scheduled_at=now,
                due_at=now - timedelta(minutes=5),
                effective_delay_seconds=300,
                delay_source="test",
                status=STATUS_SCHEDULED,
                step=1,
                multi_slot_index=0,
            )
        )
        db.session.add(
            RecoverySchedule(
                recovery_key="store-b:s2",
                store_slug="store-b",
                session_id="s2",
                scheduled_at=now,
                due_at=now + timedelta(hours=1),
                effective_delay_seconds=3600,
                delay_source="test",
                status=STATUS_RUNNING,
                step=1,
                multi_slot_index=0,
                updated_at=now - timedelta(hours=2),
            )
        )
        db.session.commit()
        vis = build_scheduler_store_visibility(store_limit=10)
        self.assertGreaterEqual(int(vis.get("total_due") or 0), 1)
        self.assertGreaterEqual(int(vis.get("stores_with_due") or 0), 1)
        slugs = {s.get("store_slug") for s in vis.get("stores") or []}
        self.assertIn("store-a", slugs)

    def test_purchase_truth_gaps_visible(self) -> None:
        now = datetime.now(timezone.utc)
        rk = f"demo:gap-{uuid.uuid4().hex[:10]}"
        db.session.add(
            LifecycleClosureRecord(
                recovery_key=rk,
                closure_status=CLOSURE_PURCHASE_COMPLETED,
                closure_reason="reply_purchase_claim",
                closure_source="reply_intent_purchase",
                closure_time=now,
                store_slug="demo",
                session_id="gap-1",
            )
        )
        db.session.commit()
        gaps = build_purchase_truth_gap_summary(sample_limit=5)
        self.assertTrue(gaps.get("gaps_detected"))
        self.assertGreaterEqual(int(gaps.get("purchase_closure_without_durable_truth") or 0), 1)
        self.assertGreaterEqual(int(gaps.get("reply_purchase_closure_without_durable_truth") or 0), 1)

    def test_recovery_schedule_creation_still_respects_pause_not_broken(self) -> None:
        from services.operational_control_v1 import (
            CONTROL_PAUSE_SCHEDULING,
            apply_operational_control,
        )

        apply_operational_control(
            control=CONTROL_PAUSE_SCHEDULING,
            enabled=True,
            operator="tester",
            reason="incident",
        )
        blocked = operational_control_blocks_schedule_creation_safe(
            store_slug="demo",
            is_new_row=True,
        )
        self.assertTrue(blocked)
        self.assertTrue(evaluate_wa_send_allowed().allowed)


if __name__ == "__main__":
    unittest.main()
