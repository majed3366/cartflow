# -*- coding: utf-8 -*-
"""Targeted operational control v1 — gates, dry-run, audit events."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import main  # noqa: F401 — app/db context for durable snapshot tests
from extensions import db
from models import OperationalControlSnapshot
from services.operational_control_v1 import (
    CONTROL_PAUSE_CONTINUATION,
    CONTROL_PAUSE_REASON,
    CONTROL_PAUSE_SCHEDULING,
    CONTROL_PAUSE_STORE,
    CONTROL_PAUSE_WA,
    apply_operational_control,
    clear_operational_control_state_for_tests,
    evaluate_continuation_allowed,
    evaluate_schedule_creation_allowed,
    evaluate_wa_send_allowed,
    get_operational_control_state,
    operational_control_blocks_whatsapp_send,
    resume_operational_control,
    simulate_operational_control_process_restart_for_tests,
)


class OperationalControlV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        clear_operational_control_state_for_tests()

    def tearDown(self) -> None:
        clear_operational_control_state_for_tests()

    def test_defaults_all_allowed(self) -> None:
        self.assertTrue(evaluate_wa_send_allowed().allowed)
        self.assertTrue(evaluate_schedule_creation_allowed(is_new_row=True).allowed)
        self.assertTrue(evaluate_continuation_allowed().allowed)
        st = get_operational_control_state()
        self.assertFalse(st["platform_wa_paused"])
        self.assertFalse(st["provider_paused"])

    def test_pause_wa_blocks_send(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_WA,
            enabled=True,
            operator="tester",
            reason="incident",
        )
        self.assertFalse(evaluate_wa_send_allowed().allowed)
        blocked = operational_control_blocks_whatsapp_send(store_slug="demo")
        self.assertIsNotNone(blocked)
        self.assertFalse(blocked.get("wa_send_allowed", True))

    def test_pause_scheduling_new_only(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_SCHEDULING,
            enabled=True,
            operator="tester",
            reason="backlog",
        )
        self.assertFalse(
            evaluate_schedule_creation_allowed(is_new_row=True).allowed
        )
        self.assertTrue(
            evaluate_schedule_creation_allowed(is_new_row=False).allowed
        )

    def test_pause_store_scoped(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_STORE,
            enabled=True,
            store_slug="shop-a",
            operator="tester",
            reason="store_issue",
        )
        self.assertFalse(
            evaluate_wa_send_allowed(store_slug="shop-a").allowed
        )
        self.assertTrue(evaluate_wa_send_allowed(store_slug="shop-b").allowed)

    def test_pause_reason_scoped(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_REASON,
            enabled=True,
            reason_tag="price",
            operator="tester",
            reason="price_spike",
        )
        self.assertFalse(
            evaluate_wa_send_allowed(reason_tag="price_high").allowed
        )
        self.assertTrue(evaluate_wa_send_allowed(reason_tag="shipping").allowed)

    def test_pause_continuation(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_CONTINUATION,
            enabled=True,
            operator="tester",
            reason="continuation_bug",
        )
        self.assertFalse(evaluate_continuation_allowed().allowed)

    def test_dry_run_does_not_pause(self) -> None:
        with patch("builtins.print"):
            r = apply_operational_control(
                control=CONTROL_PAUSE_WA,
                enabled=True,
                dry_run=True,
                operator="tester",
                reason="preview",
            )
        self.assertTrue(r.get("dry_run"))
        self.assertTrue(evaluate_wa_send_allowed().allowed)

    def test_resume_clears_platform_wa(self) -> None:
        apply_operational_control(
            control=CONTROL_PAUSE_WA,
            enabled=True,
            operator="tester",
            reason="x",
        )
        resume_operational_control(target="wa", operator="tester", reason="clear")
        self.assertTrue(evaluate_wa_send_allowed().allowed)

    def test_control_event_logged(self) -> None:
        with patch("builtins.print") as mock_print:
            apply_operational_control(
                control=CONTROL_PAUSE_WA,
                enabled=True,
                operator="ops1",
                reason="test_event",
            )
        joined = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("OPERATIONAL CONTROL EVENT", joined)
        events = get_operational_control_state().get("recent_events") or []
        self.assertTrue(any(e.get("operator") == "ops1" for e in events))

    def test_dry_run_log_prefix(self) -> None:
        with patch("builtins.print") as mock_print:
            apply_operational_control(
                control=CONTROL_PAUSE_WA,
                enabled=True,
                dry_run=True,
                operator="ops1",
                reason="dry",
            )
        joined = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("CONTROL DRY RUN", joined)

    def test_verification_shape(self) -> None:
        from services.operational_control_v1 import build_operational_control_verification

        v = build_operational_control_verification()
        self.assertIn("affected_stores", v)
        self.assertIn("affected_recoveries", v)
        self.assertIn("runtime_impact", v)

    def test_pause_wa_survives_process_restart(self) -> None:
        with patch("builtins.print"):
            apply_operational_control(
                control=CONTROL_PAUSE_WA,
                enabled=True,
                operator="tester",
                reason="incident",
            )
        row = db.session.get(OperationalControlSnapshot, 1)
        self.assertIsNotNone(row)
        self.assertTrue(row.platform_wa_paused)

        simulate_operational_control_process_restart_for_tests()
        self.assertFalse(evaluate_wa_send_allowed().allowed)
        blocked = operational_control_blocks_whatsapp_send(store_slug="demo")
        self.assertIsNotNone(blocked)
        self.assertEqual(blocked.get("error"), "platform_wa_paused")

    def test_pause_store_survives_process_restart(self) -> None:
        with patch("builtins.print"):
            apply_operational_control(
                control=CONTROL_PAUSE_STORE,
                enabled=True,
                store_slug="shop-a",
                operator="tester",
                reason="store_issue",
            )
        simulate_operational_control_process_restart_for_tests()
        self.assertFalse(evaluate_wa_send_allowed(store_slug="shop-a").allowed)
        self.assertTrue(evaluate_wa_send_allowed(store_slug="shop-b").allowed)


if __name__ == "__main__":
    unittest.main()
