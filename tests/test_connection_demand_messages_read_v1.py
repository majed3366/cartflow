# -*- coding: utf-8 -*-
"""
Connection-demand messages read model — INV-ADM + multiplicity + release.

NullPool is forbidden for the QueuePool equilibrium cases.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from services.dashboard_messages_read_v1 import (
    compose_messages_after_db_phase,
    compose_messages_payload,
)
from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool
from services.db_resource_safety_v1.admission_v1 import (
    HEAVY_GLOBAL_LIMIT,
    reset_for_tests as reset_admission,
    snapshot as admission_snapshot,
    try_acquire,
)
from services.db_lifecycle_v1.http_bind import maybe_reject_heavy_before_db
from services.lifecycle_authority_recovery_v1 import (
    enrich_message_history_rows_with_lifecycle,
    prefetch_recovery_schedule_facts,
)
from schema_recovery_truth_timeline import (
    reset_recovery_truth_timeline_schema_guard_for_tests,
    timeline_schema_is_verified,
)


def _qp():
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        pool_reset_on_return="rollback",
        connect_args={"check_same_thread": False},
    )


class MessagesComposeTests(unittest.TestCase):
    def test_empty_history_keeps_honest_placeholder(self) -> None:
        out = compose_messages_payload(message_history_rows=[], refresh_state={})
        self.assertEqual(out["merchant_message_history_rows"], [])
        self.assertEqual(out["merchant_wa_last_send_ar"], "—")

    def test_compose_does_not_drop_row_fields(self) -> None:
        rows = [
            {
                "time_ar": "منذ دقيقتين",
                "customer_lifecycle_state": "waiting_customer_reply",
                "preview_ar": "مرحبا",
            }
        ]
        out = compose_messages_payload(
            message_history_rows=rows,
            refresh_state={"merchant_dashboard_refresh_token": "tok"},
        )
        self.assertEqual(out["merchant_wa_last_send_ar"], "منذ دقيقتين")
        self.assertEqual(
            out["merchant_message_history_rows"][0]["customer_lifecycle_state"],
            "waiting_customer_reply",
        )
        self.assertEqual(out["merchant_dashboard_refresh_token"], "tok")

    def test_release_happens_before_compose(self) -> None:
        order: list[str] = []

        def _release(*, reason: str = "") -> bool:
            order.append(f"release:{reason}")
            return True

        with patch(
            "services.dashboard_messages_read_v1.close_request_uow_if_clean",
            side_effect=_release,
        ):
            out = compose_messages_after_db_phase(
                [{"time_ar": "الآن"}],
                {"merchant_dashboard_refresh_sent_total": 1},
            )
        self.assertEqual(order, ["release:messages_read_db_phase"])
        self.assertEqual(out["merchant_wa_last_send_ar"], "الآن")
        self.assertEqual(out["merchant_dashboard_refresh_sent_total"], 1)


class TimelineEnsureInspectSkipTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()

    def test_repeated_ensure_does_not_reinspect(self) -> None:
        from services import recovery_truth_timeline_v1 as tl
        import schema_recovery_truth_timeline as sch

        sch._schema_once = True
        with patch.object(tl, "_table_exists") as exists:
            for i in range(40):
                self.assertTrue(tl.ensure_timeline_table_ready(recovery_key=f"rk-{i}"))
            exists.assert_not_called()
        self.assertTrue(timeline_schema_is_verified())


class EnrichBatchTests(unittest.TestCase):
    def test_prefetch_empty_keys(self) -> None:
        self.assertEqual(prefetch_recovery_schedule_facts([]), {})

    def test_enrich_uses_bulk_timeline_and_schedule_not_per_row(self) -> None:
        rows = [{"recovery_key": f"rk-{i}"} for i in range(40)]
        dash = MagicMock()
        dash.zid_store_id = "demo-store"
        log_row = MagicMock()
        log_row.recovery_key = "rk-0"
        log_row.status = "sent_real"

        query = MagicMock()
        query.filter.return_value = query
        query.limit.return_value = query
        query.all.return_value = [log_row]

        session = MagicMock()
        session.query.return_value = query

        tl_map = {f"rk-{i}": frozenset({"provider_sent"}) for i in range(40)}
        sched_map = {
            f"rk-{i}": {"due_at": None, "effective_delay_seconds": None} for i in range(40)
        }

        with (
            patch(
                "services.merchant_dashboard_recovery_resolve_v1.store_slug_from_dash",
                return_value="demo-store",
            ),
            patch("extensions.db") as db_mod,
            patch(
                "services.recovery_truth_timeline_v1.bulk_timeline_status_sets",
                return_value=tl_map,
            ) as bulk,
            patch(
                "services.lifecycle_authority_recovery_v1.prefetch_recovery_schedule_facts",
                return_value=sched_map,
            ) as prefetch,
            patch(
                "services.recovery_truth_timeline_v1.timeline_status_set",
                side_effect=AssertionError("per-row timeline_status_set"),
            ),
            patch(
                "services.customer_lifecycle_states_v1._next_schedule_due_at",
                side_effect=AssertionError("per-row schedule due"),
            ),
            patch(
                "services.customer_lifecycle_states_v1._scheduled_effective_delay_seconds",
                side_effect=AssertionError("per-row schedule delay"),
            ),
        ):
            db_mod.session = session
            enrich_message_history_rows_with_lifecycle(rows, dash_store=dash)
            bulk.assert_called_once()
            prefetch.assert_called_once()
            passed_keys = list(bulk.call_args[0][0])
            self.assertEqual(len(passed_keys), 40)
        self.assertTrue(
            all(r.get("customer_lifecycle_state") for r in rows if r.get("recovery_key"))
        )

    def test_enrich_caps_keys_at_80(self) -> None:
        rows = [{"recovery_key": f"rk-{i}"} for i in range(100)]
        dash = MagicMock()
        query = MagicMock()
        query.filter.return_value = query
        query.limit.return_value = query
        query.all.return_value = []
        session = MagicMock()
        session.query.return_value = query
        with (
            patch(
                "services.merchant_dashboard_recovery_resolve_v1.store_slug_from_dash",
                return_value="demo-store",
            ),
            patch("extensions.db") as db_mod,
            patch(
                "services.recovery_truth_timeline_v1.bulk_timeline_status_sets",
                return_value={},
            ) as bulk,
            patch(
                "services.lifecycle_authority_recovery_v1.prefetch_recovery_schedule_facts",
                return_value={},
            ),
        ):
            db_mod.session = session
            enrich_message_history_rows_with_lifecycle(rows, dash_store=dash)
            self.assertEqual(len(list(bulk.call_args[0][0])), 80)

    def test_partial_lifecycle_failure_does_not_raise(self) -> None:
        rows = [{"recovery_key": "rk-1", "preview_ar": "x"}]
        dash = MagicMock()
        with (
            patch(
                "services.merchant_dashboard_recovery_resolve_v1.store_slug_from_dash",
                return_value="demo-store",
            ),
            patch("extensions.db") as db_mod,
        ):
            db_mod.session.query.side_effect = RuntimeError("db down")
            db_mod.session.rollback.return_value = None
            enrich_message_history_rows_with_lifecycle(rows, dash_store=dash)
        self.assertEqual(rows[0]["preview_ar"], "x")
        self.assertNotIn("customer_lifecycle_state", rows[0])


class AdmissionBeforeCheckoutTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_admission()

    def tearDown(self) -> None:
        reset_admission()

    def test_rejected_heavy_get_does_not_need_db(self) -> None:
        for i in range(HEAVY_GLOBAL_LIMIT):
            self.assertTrue(try_acquire(f"/fill-{i}"))
        req = MagicMock()
        req.url.path = "/api/dashboard/messages"
        req.method = "GET"
        req.cookies = {}
        with (
            patch(
                "services.merchant_auth_v1.development_dashboard_bypass_active",
                return_value=True,
            ),
            patch(
                "services.merchant_auth_v1.path_requires_merchant_auth",
                return_value=False,
            ),
        ):
            resp = maybe_reject_heavy_before_db(req)
        self.assertIsNotNone(resp)
        self.assertGreaterEqual(admission_snapshot()["rejected"], 1)

    def test_admission_weight_remains_one_after_demand_reduction(self) -> None:
        from services.db_resource_safety_v1 import admission_v1 as adm

        src = open(adm.__file__, encoding="utf-8").read()
        self.assertIn("try_acquire cost stays 1", src)
        self.assertNotIn("messages_weight", src)


class QueuePoolEquilibriumAfterReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _qp()
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.checkouts = 0

        def _on_checkout(_dbapi, _con, _rec):  # noqa: ANN001
            self.checkouts += 1

        event.listen(self.engine, "checkout", _on_checkout)
        self._unlisten = lambda: event.remove(self.engine, "checkout", _on_checkout)

    def tearDown(self) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()
        self._unlisten()
        self.engine.dispose()

    def test_scoped_phase_then_release_returns_to_baseline(self) -> None:
        base = int(pool_truth_from_pool(self.engine.pool).get("checked_out") or 0)
        sess = self.Session()
        sess.execute(text("SELECT 1"))
        held = int(pool_truth_from_pool(self.engine.pool)["checked_out"] or 0)
        self.assertGreater(held, base)
        sess.close()
        self.assertEqual(
            int(pool_truth_from_pool(self.engine.pool)["checked_out"] or 0),
            base,
        )
        self.assertGreaterEqual(self.checkouts, 1)
        self.assertLess(self.checkouts, 10)

    def test_inspect_skip_avoids_sixty_checkouts(self) -> None:
        """Stand-in for the proven ~60 inspect checkouts on one messages request."""
        from services import recovery_truth_timeline_v1 as tl
        import schema_recovery_truth_timeline as sch

        sch._schema_once = True
        inspect_calls = {"n": 0}

        def _fake_exists() -> bool:
            inspect_calls["n"] += 1
            return True

        with patch.object(tl, "_table_exists", side_effect=_fake_exists):
            for i in range(40):
                tl.ensure_timeline_table_ready(recovery_key=f"rk-{i}")
        self.assertEqual(inspect_calls["n"], 0)


class SourceContractTests(unittest.TestCase):
    def test_messages_api_uses_release_before_compose(self) -> None:
        from pathlib import Path

        main_py = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("compose_messages_payload", main_py)
        self.assertIn("release_messages_db_phase", main_py)
        self.assertIn("dashboard_messages_read_v1", main_py)

    def test_pool_bounds_unchanged(self) -> None:
        from services.db_pool_bounds_v1 import API_DEFAULT_OVERFLOW, API_DEFAULT_SIZE

        self.assertEqual(API_DEFAULT_SIZE, 5)
        self.assertEqual(API_DEFAULT_OVERFLOW, 5)
