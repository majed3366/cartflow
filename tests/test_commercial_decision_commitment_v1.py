# -*- coding: utf-8 -*-
"""Commercial Decision Commitment V1 — gates + failure modes + eval proof."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class CommercialDecisionCommitmentV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_cdc_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        from extensions import db, init_database

        init_database()
        db.create_all()
        from schema_commercial_decision_commitment_v1 import (
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )

        reset_commercial_decision_commitment_schema_guard_for_tests()

    def setUp(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment

        db.session.query(CommercialDecisionCommitment).delete()
        db.session.commit()

    def _ready_col(self, slug: str = "cdc_test_store") -> dict[str, Any]:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        return compose_commercial_opportunity_layer_v1(
            {
                "store_slug": slug,
                "merchant_reason_counts_week": {
                    "shipping": 12,
                    "price": 5,
                    "thinking": 3,
                },
            },
            store_slug=slug,
        )

    def test_accept_leaves_measurement_null(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            PHASE_ACTION_CHOSEN,
            accept_commitment,
            derive_commitment_state,
            get_active_commitment,
        )

        slug = "cdc_accept_store"
        col = self._ready_col(slug)
        self.assertTrue(col.get("primary"))
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(
            store_slug=slug, opportunity_key=key, col_package=col
        )
        self.assertTrue(out["ok"])
        row = get_active_commitment(slug, key)
        assert row is not None
        self.assertIsNone(row.measurement_started_at)
        self.assertIsNone(row.baseline_snapshot_json)
        self.assertEqual(derive_commitment_state(row), PHASE_ACTION_CHOSEN)
        self.assertEqual(out["commitment"]["console_mode"], "accepted")

    def test_accept_idempotent_and_uniqueness(self) -> None:
        from services.commercial_decision_commitment_v1 import accept_commitment
        from models import CommercialDecisionCommitment
        from extensions import db

        slug = "cdc_idem_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        a = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        b = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        self.assertFalse(a.get("idempotent"))
        self.assertTrue(b.get("idempotent"))
        self.assertEqual(a["commitment"]["commitment_id"], b["commitment"]["commitment_id"])
        n = (
            db.session.query(CommercialDecisionCommitment)
            .filter(
                CommercialDecisionCommitment.store_slug == slug,
                CommercialDecisionCommitment.closed_at.is_(None),
            )
            .count()
        )
        self.assertEqual(n, 1)

    def test_concurrent_accept_one_active(self) -> None:
        from services.commercial_decision_commitment_v1 import accept_commitment
        from models import CommercialDecisionCommitment
        from extensions import db

        slug = "cdc_race_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        errors: list[str] = []

        def worker() -> None:
            try:
                accept_commitment(
                    store_slug=slug, opportunity_key=key, col_package=col
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        n = (
            db.session.query(CommercialDecisionCommitment)
            .filter(
                CommercialDecisionCommitment.store_slug == slug,
                CommercialDecisionCommitment.closed_at.is_(None),
            )
            .count()
        )
        self.assertEqual(n, 1)
        self.assertEqual(errors, [])

    def test_wrong_store_isolation(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            start_measurement,
        )

        slug = "cdc_iso_a"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        cid = out["commitment"]["commitment_id"]
        with self.assertRaises(CommitmentError) as ctx:
            start_measurement(
                store_slug="cdc_iso_b",
                commitment_id=cid,
                authority="merchant_execution_confirm",
                metric_key="hesitation_share",
            )
        self.assertEqual(ctx.exception.code, "commitment_not_found")

    def test_stale_opportunity_refused(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
        )

        with self.assertRaises(CommitmentError) as ctx:
            accept_commitment(
                store_slug="cdc_stale",
                opportunity_key="col:shipping_friction:shipping:cdc_stale",
                col_package={"ok": True, "empty": True, "primary": None},
            )
        self.assertEqual(ctx.exception.code, "stale_opportunity")

    def test_measurement_authority_refused(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            start_measurement,
        )

        slug = "cdc_auth_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        cid = out["commitment"]["commitment_id"]
        with self.assertRaises(CommitmentError) as ctx:
            start_measurement(
                store_slug=slug,
                commitment_id=cid,
                authority="external_unproven",
                metric_key="hesitation_share",
            )
        self.assertEqual(ctx.exception.code, "measurement_authority_refused")

    def test_cartflow_execution_requires_ref(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            start_measurement,
        )

        slug = "cdc_exec_ref"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        with self.assertRaises(CommitmentError) as ctx:
            start_measurement(
                store_slug=slug,
                commitment_id=out["commitment"]["commitment_id"],
                authority="cartflow_execution",
                measurement_start_ref="",
                metric_key="hesitation_share",
            )
        self.assertEqual(ctx.exception.code, "execution_ref_required")

    def test_start_measurement_freezes_baseline_idempotent(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            PHASE_UNDER_MEASUREMENT,
            accept_commitment,
            derive_commitment_state,
            get_active_commitment,
            start_measurement,
        )
        from services.commercial_decision_commitment_v1.snapshots_v1 import (
            parse_and_validate_baseline_snapshot,
        )

        slug = "cdc_measure_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        cid = out["commitment"]["commitment_id"]
        m1 = start_measurement(
            store_slug=slug,
            commitment_id=cid,
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
            metric_value=0.6,
            truth_class_at_start="PRODUCTION_TRUTH_READY",
            recheck_condition="after_window",
        )
        self.assertFalse(m1.get("idempotent"))
        row = get_active_commitment(slug, key)
        assert row is not None
        self.assertIsNotNone(row.measurement_started_at)
        self.assertIsNotNone(row.baseline_snapshot_json)
        parse_and_validate_baseline_snapshot(row.baseline_snapshot_json or "{}")
        self.assertEqual(derive_commitment_state(row), PHASE_UNDER_MEASUREMENT)
        m2 = start_measurement(
            store_slug=slug,
            commitment_id=cid,
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
        )
        self.assertTrue(m2.get("idempotent"))

    def test_invalid_metric_and_schema(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            start_measurement,
        )
        from services.commercial_decision_commitment_v1.snapshots_v1 import (
            SnapshotContractError,
            parse_and_validate_baseline_snapshot,
        )

        slug = "cdc_metric_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        with self.assertRaises(CommitmentError):
            start_measurement(
                store_slug=slug,
                commitment_id=out["commitment"]["commitment_id"],
                authority="merchant_execution_confirm",
                metric_key="!!!bad",
            )
        with self.assertRaises(SnapshotContractError):
            parse_and_validate_baseline_snapshot(
                {"schema_version": "wrong", "metric_key": "x"}
            )

    def test_recheck_due_keeps_open_no_won(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            PHASE_RECHECK_DUE,
            accept_commitment,
            derive_commitment_state,
            get_active_commitment,
            start_measurement,
        )

        slug = "cdc_recheck_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        start_measurement(
            store_slug=slug,
            commitment_id=out["commitment"]["commitment_id"],
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
            metric_value=0.5,
        )
        row = get_active_commitment(slug, key)
        assert row is not None
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(hours=1)
        from extensions import db

        db.session.commit()
        phase = derive_commitment_state(row)
        self.assertEqual(phase, PHASE_RECHECK_DUE)
        self.assertIsNone(row.closed_at)
        # purchase / evidence must not auto-close — row still open
        self.assertIsNotNone(get_active_commitment(slug, key))

    def test_close_twice_and_invalid_reason(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            close_commitment,
        )

        slug = "cdc_close_store"
        col = self._ready_col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        cid = out["commitment"]["commitment_id"]
        with self.assertRaises(CommitmentError) as ctx:
            close_commitment(
                store_slug=slug,
                commitment_id=cid,
                close_reason="won",
                actor="merchant",
            )
        self.assertEqual(ctx.exception.code, "invalid_close_reason")
        c1 = close_commitment(
            store_slug=slug,
            commitment_id=cid,
            close_reason="merchant_cancel",
            actor="merchant",
        )
        c2 = close_commitment(
            store_slug=slug,
            commitment_id=cid,
            close_reason="merchant_cancel",
            actor="merchant",
        )
        self.assertFalse(c1.get("idempotent"))
        self.assertTrue(c2.get("idempotent"))

    def test_attach_backward_compat_and_query_delta(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            accept_commitment,
            attach_commitment_truth,
        )

        slug = "cdc_attach_empty"
        summary: dict[str, Any] = {
            "store_slug": slug,
            "commercial_opportunity_layer_v1": {
                "ok": True,
                "empty": True,
                "primary": None,
            },
        }
        attach_commitment_truth(summary, store_slug=slug)
        cdc = summary["commercial_decision_commitment_v1"]
        self.assertTrue(cdc["ok"])
        self.assertEqual(cdc["open_count"], 0)
        self.assertEqual(cdc["query_delta"], 1)

        slug2 = "cdc_attach_nested"
        col = self._ready_col(slug2)
        key = col["primary"]["opportunity_id"]
        accept_commitment(store_slug=slug2, opportunity_key=key, col_package=col)
        summary2 = {
            "store_slug": slug2,
            "commercial_opportunity_layer_v1": col,
        }
        attach_commitment_truth(summary2, store_slug=slug2)
        primary = summary2["commercial_opportunity_layer_v1"]["primary"]
        self.assertIn("commitment", primary)
        self.assertEqual(primary["commitment"]["phase"], "ACTION_CHOSEN")
        self.assertEqual(primary["commitment"]["console_mode"], "accepted")

    def test_console_js_reads_backend_mode(self) -> None:
        root = os.path.join(os.path.dirname(__file__), "..")
        js = open(
            os.path.join(root, "static/merchant_ui_v2_workspace.js"),
            encoding="utf-8",
        ).read()
        self.assertIn("commercial-opportunity-workspace-v1", js)
        self.assertIn("opp.commitment", js)
        self.assertIn("console_mode", js)
        self.assertIn("ACTION_CHOSEN", js)
        self.assertIn("UNDER_MEASUREMENT", js)
        self.assertIn("RECHECK_DUE", js)
        self.assertNotIn("SIMULATION_TRUTH", js)
        self.assertNotIn("rrv_sim_store", js)
        html = open(
            os.path.join(root, "templates/merchant_app_v2.html"),
            encoding="utf-8",
        ).read()
        self.assertIn("cdc1", html)

    def test_eval_tenants_five_console_states(self) -> None:
        """Prove actionable / accepted / measuring / recheck / insufficient via backend."""
        from services.commercial_decision_commitment_v1 import (
            accept_commitment,
            attach_commitment_truth,
            console_mode_for_opportunity,
            start_measurement,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.dashboard_kpi_time_v1 import merchant_reason_counts_store_window
        from services.founder_evaluation_reality_v1.constants_v1 import (
            STORE_ACTIONABLE,
            STORE_INSUFFICIENT,
        )
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )
        from extensions import db

        seed_founder_evaluation_tenants_v1(reset=True)

        def col_for(slug: str) -> dict:
            from models import Store
            from extensions import db

            store = (
                db.session.query(Store)
                .filter(Store.zid_store_id == slug)
                .first()
            )
            counts = merchant_reason_counts_store_window(store, days=7)
            return compose_commercial_opportunity_layer_v1(
                {"store_slug": slug, "merchant_reason_counts_week": counts},
                store_slug=slug,
            )

        # 1 actionable — COL READY, no commitment
        col_a = col_for(STORE_ACTIONABLE)
        self.assertTrue(col_a.get("primary"))
        self.assertEqual(
            console_mode_for_opportunity(
                truth_class=col_a["primary"]["truth_class"], commitment_phase=None
            ),
            "actionable",
        )

        # 2 action chosen
        key = col_a["primary"]["opportunity_id"]
        out = accept_commitment(
            store_slug=STORE_ACTIONABLE, opportunity_key=key, col_package=col_a
        )
        self.assertEqual(out["commitment"]["console_mode"], "accepted")

        # 3 under measurement
        start_measurement(
            store_slug=STORE_ACTIONABLE,
            commitment_id=out["commitment"]["commitment_id"],
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
            metric_value=0.6,
        )
        summary = {
            "store_slug": STORE_ACTIONABLE,
            "commercial_opportunity_layer_v1": col_a,
        }
        attach_commitment_truth(summary, store_slug=STORE_ACTIONABLE)
        self.assertEqual(
            summary["commercial_opportunity_layer_v1"]["primary"]["commitment"][
                "console_mode"
            ],
            "measuring",
        )

        # 4 recheck due
        from models import CommercialDecisionCommitment

        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == out["commitment"]["commitment_id"])
            .first()
        )
        assert row is not None
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.commit()
        attach_commitment_truth(summary, store_slug=STORE_ACTIONABLE)
        self.assertEqual(
            summary["commercial_opportunity_layer_v1"]["primary"]["commitment"][
                "console_mode"
            ],
            "recheck",
        )

        # 5 insufficient
        col_i = col_for(STORE_INSUFFICIENT)
        self.assertTrue(col_i.get("empty") or not col_i.get("primary"))
        self.assertEqual(
            console_mode_for_opportunity(
                truth_class="INSUFFICIENT", commitment_phase=None
            ),
            "insufficient",
        )

    def test_no_won_lost_learned_in_service(self) -> None:
        root = os.path.join(os.path.dirname(__file__), "..")
        svc = open(
            os.path.join(
                root,
                "services/commercial_decision_commitment_v1/service_v1.py",
            ),
            encoding="utf-8",
        ).read()
        self.assertNotIn("WON", svc)
        self.assertNotIn("LOST", svc)
        self.assertNotIn("LEARNED", svc)


if __name__ == "__main__":
    unittest.main()
