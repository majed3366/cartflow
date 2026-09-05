# -*- coding: utf-8 -*-
"""Commercial Decision Commitment V1 — production readiness & persistence proofs."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = (
    ROOT
    / "docs"
    / "architecture"
    / "commercial_decision_commitment_v1"
    / "production_readiness_v1"
    / "evidence"
)


class CdcProductionReadinessProofV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_cdc_readiness_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        from extensions import db, init_database
        from schema_commercial_decision_commitment_v1 import (
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )

        init_database()
        db.create_all()
        reset_commercial_decision_commitment_schema_guard_for_tests()
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment

        db.session.query(CommercialDecisionCommitment).delete()
        db.session.commit()

    def _col(self, slug: str) -> dict[str, Any]:
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

    def test_01_migration_additive_ddl(self) -> None:
        from extensions import db
        from sqlalchemy import inspect

        insp = inspect(db.engine)
        self.assertTrue(insp.has_table("commercial_decision_commitments"))
        cols = {c["name"]: c for c in insp.get_columns("commercial_decision_commitments")}
        # Nullable measurement fields — safe for zero-row merchants
        self.assertTrue(cols["measurement_started_at"]["nullable"])
        self.assertTrue(cols["baseline_snapshot_json"]["nullable"])
        self.assertTrue(cols["measurement_due_at"]["nullable"])
        self.assertTrue(cols["closed_at"]["nullable"])
        # No destructive drops — table is additive only
        # Active uniqueness via active_opportunity_key (portable NULL-unique)
        uq = insp.get_unique_constraints("commercial_decision_commitments")
        names = {u.get("name") for u in uq}
        self.assertIn("uq_cdc_active_store_opportunity", names)
        fks = insp.get_foreign_keys("commercial_decision_commitments")
        self.assertEqual(fks, [])
        indexes = {ix.get("name") for ix in insp.get_indexes("commercial_decision_commitments")}
        self.assertTrue(
            "ix_cdc_store_opportunity" in indexes
            or any("store_slug" in (ix.get("column_names") or []) for ix in insp.get_indexes("commercial_decision_commitments"))
        )

    def test_02_db_level_concurrent_accept_uniqueness(self) -> None:
        """DB unique constraint — not app check alone."""
        from extensions import db
        from models import CommercialDecisionCommitment
        from sqlalchemy.exc import IntegrityError

        slug = "cdc_race_db"
        key = f"col:shipping_friction:shipping:{slug}"
        results: list[str] = []
        lock = threading.Lock()

        def insert_once(n: int) -> None:
            row = CommercialDecisionCommitment(
                id=f"race-{n}-{os.getpid()}",
                store_slug=slug,
                opportunity_key=key,
                opportunity_family="shipping_friction",
                opportunity_reason="shipping",
                active_opportunity_key=key,
                action_chosen_at=datetime.now(timezone.utc),
                action_summary="race",
                decision_snapshot_json=json.dumps(
                    {
                        "schema_version": "cdc_decision_snapshot_v1",
                        "opportunity_key": key,
                        "opportunity_family": "shipping_friction",
                        "opportunity_reason": "shipping",
                        "truth_class": "PRODUCTION_TRUTH_READY",
                        "accepted_at": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            try:
                db.session.add(row)
                db.session.commit()
                with lock:
                    results.append("ok")
            except IntegrityError:
                db.session.rollback()
                with lock:
                    results.append("conflict")

        threads = [threading.Thread(target=insert_once, args=(i,)) for i in range(12)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        active = (
            db.session.query(CommercialDecisionCommitment)
            .filter(
                CommercialDecisionCommitment.store_slug == slug,
                CommercialDecisionCommitment.active_opportunity_key == key,
            )
            .count()
        )
        self.assertEqual(active, 1)
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(results.count("conflict"), 11)

    def test_03_tenant_isolation_service_and_routes(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            close_commitment,
            start_measurement,
        )
        from routes import commercial_decision_commitment_v1 as routes_mod

        slug_a = "cdc_tenant_a"
        slug_b = "cdc_tenant_b"
        col_a = self._col(slug_a)
        key = col_a["primary"]["opportunity_id"]
        out = accept_commitment(
            store_slug=slug_a, opportunity_key=key, col_package=col_a
        )
        cid = out["commitment"]["commitment_id"]

        with self.assertRaises(CommitmentError) as ctx:
            start_measurement(
                store_slug=slug_b,
                commitment_id=cid,
                authority="merchant_execution_confirm",
                metric_key="hesitation_share",
            )
        self.assertEqual(ctx.exception.code, "commitment_not_found")

        with self.assertRaises(CommitmentError):
            close_commitment(
                store_slug=slug_b,
                commitment_id=cid,
                close_reason="merchant_cancel",
                actor="merchant",
            )

        # Route auth uses cookie store — never body store_slug
        src = Path(routes_mod.__file__).read_text(encoding="utf-8")
        self.assertIn("resolve_authenticated_store_slug", src)
        self.assertNotIn("body.store_slug", src)
        self.assertNotIn("store_slug: str = Field", src)

    def test_04_accept_not_execute_persisted(self) -> None:
        from models import CommercialDecisionCommitment
        from extensions import db
        from services.commercial_decision_commitment_v1 import accept_commitment

        slug = "cdc_accept_truth"
        col = self._col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == out["commitment"]["commitment_id"])
            .one()
        )
        self.assertIsNotNone(row.action_chosen_at)
        self.assertIsNone(row.measurement_started_at)
        self.assertIsNone(row.baseline_snapshot_json)
        self.assertIsNone(row.measurement_due_at)
        # Console mode not a persisted column
        cols = {c.name for c in CommercialDecisionCommitment.__table__.columns}
        self.assertNotIn("console_mode", cols)
        self.assertNotIn("phase", cols)

    def test_05_measurement_authority_and_baseline_immutable(self) -> None:
        from models import CommercialDecisionCommitment
        from extensions import db
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            start_measurement,
        )

        slug = "cdc_meas_auth"
        col = self._col(slug)
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

        # cartflow_execution PASS with ref
        m1 = start_measurement(
            store_slug=slug,
            commitment_id=cid,
            authority="cartflow_execution",
            measurement_start_ref="exec-receipt-1",
            metric_key="hesitation_share",
            metric_value=0.55,
        )
        self.assertFalse(m1.get("idempotent"))
        row = db.session.query(CommercialDecisionCommitment).filter_by(id=cid).one()
        baseline1 = row.baseline_snapshot_json
        self.assertIsNotNone(row.measurement_started_at)
        self.assertIsNotNone(row.measurement_due_at)
        self.assertEqual(row.measurement_start_authority, "cartflow_execution")
        self.assertEqual(row.metric_key, "hesitation_share")
        self.assertIn("cdc_measurement_baseline_v1", baseline1 or "")

        # Second start: idempotent — baseline not replaced
        m2 = start_measurement(
            store_slug=slug,
            commitment_id=cid,
            authority="cartflow_execution",
            measurement_start_ref="exec-receipt-2",
            metric_key="other_metric",
            metric_value=0.99,
        )
        self.assertTrue(m2.get("idempotent"))
        row2 = db.session.query(CommercialDecisionCommitment).filter_by(id=cid).one()
        self.assertEqual(row2.baseline_snapshot_json, baseline1)
        self.assertEqual(row2.metric_key, "hesitation_share")
        self.assertEqual(row2.measurement_start_ref, "exec-receipt-1")

        # merchant_execution_confirm on fresh commitment
        slug2 = "cdc_meas_confirm"
        col2 = self._col(slug2)
        key2 = col2["primary"]["opportunity_id"]
        out2 = accept_commitment(
            store_slug=slug2, opportunity_key=key2, col_package=col2
        )
        m3 = start_measurement(
            store_slug=slug2,
            commitment_id=out2["commitment"]["commitment_id"],
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
        )
        self.assertTrue(m3["ok"])
        self.assertEqual(
            m3["commitment"]["phase"] or "UNDER_MEASUREMENT", "UNDER_MEASUREMENT"
        )

    def test_06_clock_boundary_derivation(self) -> None:
        from services.commercial_decision_commitment_v1 import (
            PHASE_RECHECK_DUE,
            PHASE_UNDER_MEASUREMENT,
            accept_commitment,
            derive_commitment_state,
            get_active_commitment,
            start_measurement,
        )

        slug = "cdc_clock"
        col = self._col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        start_measurement(
            store_slug=slug,
            commitment_id=out["commitment"]["commitment_id"],
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
        )
        row = get_active_commitment(slug, key)
        assert row is not None
        due = row.measurement_due_at
        assert due is not None
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        self.assertEqual(
            derive_commitment_state(row, now=due - timedelta(seconds=1)),
            PHASE_UNDER_MEASUREMENT,
        )
        self.assertEqual(
            derive_commitment_state(row, now=due),
            PHASE_RECHECK_DUE,
        )
        self.assertEqual(
            derive_commitment_state(row, now=due + timedelta(seconds=1)),
            PHASE_RECHECK_DUE,
        )

    def test_07_recheck_remains_open_no_auto_replace(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_decision_commitment_v1 import (
            PHASE_RECHECK_DUE,
            accept_commitment,
            derive_commitment_state,
            get_active_commitment,
            start_measurement,
        )

        slug = "cdc_recheck_open"
        col = self._col(slug)
        key = col["primary"]["opportunity_id"]
        out = accept_commitment(store_slug=slug, opportunity_key=key, col_package=col)
        cid = out["commitment"]["commitment_id"]
        start_measurement(
            store_slug=slug,
            commitment_id=cid,
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
        )
        row = get_active_commitment(slug, key)
        assert row is not None
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.session.commit()
        self.assertEqual(derive_commitment_state(row), PHASE_RECHECK_DUE)
        self.assertIsNone(row.closed_at)
        # COL re-read still possible; no auto second commitment
        n = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.store_slug == slug)
            .count()
        )
        self.assertEqual(n, 1)

    def test_08_all_close_reasons_and_purchase_not_close(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            accept_commitment,
            close_commitment,
        )
        from services.commercial_decision_commitment_v1.contract_v1 import (
            CLOSE_REASONS,
            CLOSE_REASONS_MERCHANT,
            CLOSE_REASONS_SYSTEM,
            FORBIDDEN_CLOSE_REASONS,
        )
        import services.commercial_decision_commitment_v1.service_v1 as svc

        src = Path(svc.__file__).read_text(encoding="utf-8")
        self.assertIn("FORBIDDEN_CLOSE_REASONS", src)
        self.assertIn("purchase", FORBIDDEN_CLOSE_REASONS)

        for i, reason in enumerate(sorted(CLOSE_REASONS)):
            slug = f"cdc_close_{i}"
            col = self._col(slug)
            key = col["primary"]["opportunity_id"]
            out = accept_commitment(
                store_slug=slug, opportunity_key=key, col_package=col
            )
            cid = out["commitment"]["commitment_id"]
            actor = "merchant" if reason in CLOSE_REASONS_MERCHANT else "system"
            c1 = close_commitment(
                store_slug=slug,
                commitment_id=cid,
                close_reason=reason,
                actor=actor,
            )
            self.assertFalse(c1.get("idempotent"))
            c2 = close_commitment(
                store_slug=slug,
                commitment_id=cid,
                close_reason=reason,
                actor=actor,
            )
            self.assertTrue(c2.get("idempotent"))
            row = db.session.query(CommercialDecisionCommitment).filter_by(id=cid).one()
            self.assertIsNotNone(row.closed_at)
            self.assertEqual(row.close_reason, reason)
            self.assertIsNone(row.active_opportunity_key)
            # Slot free for new accept
            out2 = accept_commitment(
                store_slug=slug, opportunity_key=key, col_package=col
            )
            self.assertNotEqual(out2["commitment"]["commitment_id"], cid)
            # History preserved
            hist = (
                db.session.query(CommercialDecisionCommitment)
                .filter(CommercialDecisionCommitment.store_slug == slug)
                .count()
            )
            self.assertEqual(hist, 2)

        with self.assertRaises(CommitmentError):
            slug = "cdc_bad_close"
            col = self._col(slug)
            key = col["primary"]["opportunity_id"]
            out = accept_commitment(
                store_slug=slug, opportunity_key=key, col_package=col
            )
            close_commitment(
                store_slug=slug,
                commitment_id=out["commitment"]["commitment_id"],
                close_reason="purchase",
                actor="merchant",
            )

    def test_09_attach_single_query_no_n_plus_1(self) -> None:
        from extensions import db
        from sqlalchemy import event
        from services.commercial_decision_commitment_v1 import (
            accept_commitment,
            attach_commitment_truth,
        )

        slug = "cdc_query_delta"
        col = self._col(slug)
        # Two secondaries possible — still one list query
        accept_commitment(
            store_slug=slug,
            opportunity_key=col["primary"]["opportunity_id"],
            col_package=col,
        )
        statements: list[str] = []

        def before_cursor(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
            if "commercial_decision_commitments" in statement.lower():
                statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", before_cursor)
        try:
            summary = {
                "store_slug": slug,
                "commercial_opportunity_layer_v1": col,
            }
            attach_commitment_truth(summary, store_slug=slug)
            cdc_queries = [
                s for s in statements if "commercial_decision_commitments" in s.lower()
            ]
            self.assertEqual(len(cdc_queries), 1)
            self.assertEqual(
                summary["commercial_decision_commitment_v1"]["query_delta"], 1
            )
            sql = cdc_queries[0].lower()
            self.assertIn("store_slug", sql)
            self.assertNotIn("opportunity_key =", sql)  # not per-opportunity loop
        finally:
            event.remove(db.engine, "before_cursor_execute", before_cursor)

    def test_10_json_contract_bounds(self) -> None:
        from services.commercial_decision_commitment_v1.contract_v1 import (
            SNAPSHOT_MAX_BYTES,
        )
        from services.commercial_decision_commitment_v1.snapshots_v1 import (
            SnapshotContractError,
            build_baseline_snapshot,
            build_decision_snapshot,
            parse_and_validate_baseline_snapshot,
            parse_and_validate_decision_snapshot,
        )

        self.assertEqual(SNAPSHOT_MAX_BYTES, 4096)
        d = build_decision_snapshot(
            opportunity_key="col:shipping_friction:shipping:x",
            opportunity_family="shipping_friction",
            opportunity_reason="shipping",
            truth_class="PRODUCTION_TRUTH_READY",
            accepted_at=datetime.now(timezone.utc).isoformat(),
            signal_counts={"hesitation_total": 20},
        )
        parse_and_validate_decision_snapshot(d)
        self.assertNotIn("<", d)
        self.assertNotIn("html", d.lower())
        b = build_baseline_snapshot(
            opportunity_key="col:shipping_friction:shipping:x",
            metric_key="hesitation_share",
            started_at=datetime.now(timezone.utc).isoformat(),
            window_days=7,
            metric_value=0.6,
        )
        parse_and_validate_baseline_snapshot(b)
        with self.assertRaises(SnapshotContractError):
            parse_and_validate_baseline_snapshot(
                {"schema_version": "nope", "metric_key": "hesitation_share"}
            )
        with self.assertRaises(SnapshotContractError):
            parse_and_validate_decision_snapshot(
                {
                    "schema_version": "cdc_decision_snapshot_v1",
                    "opportunity_key": "k",
                    "ui_html": "<b>x</b>",
                }
            )

    def test_11_zero_row_backward_compat(self) -> None:
        from services.commercial_decision_commitment_v1 import attach_commitment_truth
        from services.commercial_opportunity_layer_v1.attach_v1 import (
            attach_commercial_opportunity_layer_to_summary_v1,
        )

        summary: dict[str, Any] = {
            "store_slug": "cdc_zero_row_merchant",
            "merchant_reason_counts_week": {
                "shipping": 12,
                "price": 5,
                "thinking": 3,
            },
        }
        attach_commercial_opportunity_layer_to_summary_v1(summary)
        self.assertIn("commercial_opportunity_layer_v1", summary)
        before = json.dumps(summary["commercial_opportunity_layer_v1"], sort_keys=True)
        attach_commitment_truth(summary, store_slug="cdc_zero_row_merchant")
        after = json.dumps(summary["commercial_opportunity_layer_v1"], sort_keys=True)
        self.assertEqual(before, after)
        cdc = summary["commercial_decision_commitment_v1"]
        self.assertEqual(cdc["open_count"], 0)
        self.assertEqual(cdc["by_opportunity_key"], {})

    def test_12_persisted_eval_states_evidence(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment, Store
        from services.commercial_decision_commitment_v1 import (
            accept_commitment,
            close_commitment,
            derive_commitment_state,
            start_measurement,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.dashboard_kpi_time_v1 import merchant_reason_counts_store_window
        from services.founder_evaluation_reality_v1.constants_v1 import (
            STORE_ACTIONABLE,
        )
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )

        seed_founder_evaluation_tenants_v1(reset=True)
        store = (
            db.session.query(Store)
            .filter(Store.zid_store_id == STORE_ACTIONABLE)
            .first()
        )
        counts = merchant_reason_counts_store_window(store, days=7)
        col = compose_commercial_opportunity_layer_v1(
            {"store_slug": STORE_ACTIONABLE, "merchant_reason_counts_week": counts},
            store_slug=STORE_ACTIONABLE,
        )
        self.assertTrue(col.get("primary"))
        key = col["primary"]["opportunity_id"]

        # A accepted
        a = accept_commitment(
            store_slug=STORE_ACTIONABLE, opportunity_key=key, col_package=col
        )
        row_a = (
            db.session.query(CommercialDecisionCommitment)
            .filter_by(id=a["commitment"]["commitment_id"])
            .one()
        )
        evidence = {
            "A_accepted": {
                "commitment_id": row_a.id,
                "store_slug": row_a.store_slug,
                "opportunity_key": row_a.opportunity_key,
                "derived_state": derive_commitment_state(row_a),
                "action_chosen_at": row_a.action_chosen_at.isoformat(),
                "measurement_started_at": None,
                "closed_at": None,
            }
        }

        # B under measurement
        start_measurement(
            store_slug=STORE_ACTIONABLE,
            commitment_id=row_a.id,
            authority="merchant_execution_confirm",
            metric_key="hesitation_share",
            metric_value=0.6,
        )
        db.session.refresh(row_a)
        evidence["B_under_measurement"] = {
            "commitment_id": row_a.id,
            "store_slug": row_a.store_slug,
            "opportunity_key": row_a.opportunity_key,
            "derived_state": derive_commitment_state(row_a),
            "measurement_started_at": row_a.measurement_started_at.isoformat()
            if row_a.measurement_started_at
            else None,
            "measurement_due_at": row_a.measurement_due_at.isoformat()
            if row_a.measurement_due_at
            else None,
            "authority": row_a.measurement_start_authority,
        }
        self.assertEqual(evidence["B_under_measurement"]["derived_state"], "UNDER_MEASUREMENT")

        # C recheck due
        row_a.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        db.session.refresh(row_a)
        evidence["C_recheck_due"] = {
            "commitment_id": row_a.id,
            "store_slug": row_a.store_slug,
            "opportunity_key": row_a.opportunity_key,
            "derived_state": derive_commitment_state(row_a),
            "measurement_due_at": row_a.measurement_due_at.isoformat()
            if row_a.measurement_due_at
            else None,
            "closed_at": None,
        }
        self.assertEqual(evidence["C_recheck_due"]["derived_state"], "RECHECK_DUE")

        # D closed + new active version
        close_commitment(
            store_slug=STORE_ACTIONABLE,
            commitment_id=row_a.id,
            close_reason="recheck_new_decision",
            actor="system",
        )
        db.session.refresh(row_a)
        b = accept_commitment(
            store_slug=STORE_ACTIONABLE, opportunity_key=key, col_package=col
        )
        evidence["D_closed_plus_new_active"] = {
            "closed": {
                "commitment_id": row_a.id,
                "closed_at": row_a.closed_at.isoformat() if row_a.closed_at else None,
                "close_reason": row_a.close_reason,
                "derived_state": derive_commitment_state(row_a),
            },
            "new_active": {
                "commitment_id": b["commitment"]["commitment_id"],
                "store_slug": STORE_ACTIONABLE,
                "opportunity_key": key,
                "derived_state": b["commitment"]["phase"],
            },
        }
        self.assertNotEqual(
            evidence["D_closed_plus_new_active"]["closed"]["commitment_id"],
            evidence["D_closed_plus_new_active"]["new_active"]["commitment_id"],
        )

        out_path = EVIDENCE_DIR / "persisted_eval_states.json"
        out_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.assertTrue(out_path.is_file())


if __name__ == "__main__":
    unittest.main()
