# -*- coding: utf-8 -*-
"""Migration Lineage Integrity V1.1 — empty replay + schema authority."""
from __future__ import annotations

import os
import tempfile
import unittest

from sqlalchemy import create_engine, inspect, text

from extensions import Base
from services.migration_lineage_integrity_v1.authority import (
    REQUIRED_PRODUCTION_TABLES,
    create_all_permitted,
    inspect_required_schema,
)
from services.migration_lineage_integrity_v1.graph import inspect_lineage
from services.migration_lineage_integrity_v1.inventory import (
    CREATE_ALL_OWNED_TABLES,
    classify_table_presence,
)
from services.migration_lineage_integrity_v1.future_rule import future_revision_parent_rule
from services.migration_lineage_integrity_v1.replay import upgrade_heads_from_empty


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


class EmptyDatabaseReplayTests(unittest.TestCase):
    def test_upgrade_heads_from_empty_reaches_reconstructed_head(self) -> None:
        """V2.1: E0 birth CREATE makes empty SQLite helper replay succeed."""
        fd, path = tempfile.mkstemp(suffix="_mli11.db")
        os.close(fd)
        _unlink(path)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            out = upgrade_heads_from_empty(database_url=url)
            self.assertTrue(out["ok"], out.get("failing_message"))
            self.assertEqual(out.get("alembic_version"), ["f10altparity01"])
            tables = set(out.get("tables") or [])
            self.assertIn("stores", tables)
            self.assertIn("recovery_schedules", tables)
            self.assertIn("purchase_truth_records", tables)
            self.assertIn("movement_snapshots", tables)
            self.assertNotIn("commercial_decision_commitments", tables)
        finally:
            _unlink(path)

    def test_replay_does_not_call_create_all(self) -> None:
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "services",
            "migration_lineage_integrity_v1",
            "replay.py",
        )
        with open(src_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("create_all(", src)
        self.assertIn("command.upgrade", src)


class FutureRevisionParentRuleTests(unittest.TestCase):
    def test_every_down_revision_exists(self) -> None:
        out = inspect_lineage()
        self.assertTrue(out["walkable"], out.get("error"))
        self.assertEqual(out["missing_parents"], [])
        self.assertIn("e0fnd250425a", out["bases"])
        self.assertIn("p2q3r4s5t6u7", out["bases"])
        self.assertNotIn("a3ff333f6d46", out["bases"])
        self.assertNotIn("m1n2o3p4q5r6", out["bases"])

    def test_proposed_parent_must_exist(self) -> None:
        ok = future_revision_parent_rule("k2l3m4n5o6p7")
        self.assertTrue(ok["ok"], ok)
        bad = future_revision_parent_rule("not_a_real_revision")
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["reason"], "parent_not_in_map")
        missing = future_revision_parent_rule(None)
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["reason"], "parent_required")

    def test_db_create_all_is_gated(self) -> None:
        import inspect as ins

        from extensions import _DB

        src = ins.getsource(_DB.create_all)
        self.assertIn("create_all_permitted", src)
        self.assertIn("note_create_all_refused", src)


class SchemaAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {
            k: os.environ.get(k)
            for k in (
                "CARTFLOW_ALLOW_CREATE_ALL",
                "CARTFLOW_REFUSE_CREATE_ALL",
                "ENV",
                "CARTFLOW_PROCESS_ROLE",
            )
        }

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_create_all_allowed_in_development(self) -> None:
        os.environ["ENV"] = "development"
        os.environ.pop("CARTFLOW_REFUSE_CREATE_ALL", None)
        os.environ.pop("CARTFLOW_PROCESS_ROLE", None)
        self.assertTrue(create_all_permitted())

    def test_create_all_refused_for_api_role(self) -> None:
        os.environ["CARTFLOW_REFUSE_CREATE_ALL"] = "1"
        self.assertFalse(create_all_permitted())

    def test_create_all_does_not_repair_missing_table(self) -> None:
        os.environ["CARTFLOW_REFUSE_CREATE_ALL"] = "1"
        self.assertFalse(create_all_permitted())
        fd, path = tempfile.mkstemp(suffix="_mli11_fail.db")
        os.close(fd)
        _unlink(path)
        url = "sqlite:///" + path.replace("\\", "/")
        engine = create_engine(url)
        try:
            import models  # noqa: F401

            if create_all_permitted():
                Base.metadata.create_all(bind=engine)
            names = set(inspect(engine).get_table_names())
            self.assertNotIn("stores", names)
            self.assertNotIn("purchase_truth_records", names)
            chk = inspect_required_schema(engine)
            self.assertFalse(chk["ok"])
            self.assertIn("stores", chk["missing"])
            self.assertEqual(chk["authority"], "alembic")
        finally:
            engine.dispose()
            _unlink(path)

    def test_required_schema_passes_when_tables_exist(self) -> None:
        os.environ.pop("CARTFLOW_REFUSE_CREATE_ALL", None)
        os.environ["CARTFLOW_ALLOW_CREATE_ALL"] = "1"
        fd, path = tempfile.mkstemp(suffix="_mli11_ok.db")
        os.close(fd)
        _unlink(path)
        url = "sqlite:///" + path.replace("\\", "/")
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                for table in REQUIRED_PRODUCTION_TABLES:
                    conn.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            chk = inspect_required_schema(engine)
            self.assertTrue(chk["ok"], chk)
        finally:
            engine.dispose()
            _unlink(path)


class DriftClassificationTests(unittest.TestCase):
    def test_deprecated_cdc_is_expected_deprecated_drift(self) -> None:
        rows = classify_table_presence(
            fresh_names={"stores", "order_economic_facts"},
            production_names={
                "stores",
                "order_economic_facts",
                "commercial_decision_commitments",
            },
        )
        by_name = {r["table"]: r for r in rows}
        self.assertEqual(by_name["stores"]["class"], "MATCH")
        self.assertEqual(
            by_name["commercial_decision_commitments"]["class"],
            "EXPECTED_DEPRECATED_DRIFT",
        )
        self.assertEqual(
            by_name["commercial_decision_commitments"]["owner"], "deprecate"
        )
        self.assertTrue("commercial_decision_commitments" in CREATE_ALL_OWNED_TABLES)

    def test_alembic_missing_in_production_is_unresolved(self) -> None:
        rows = classify_table_presence(
            fresh_names={"order_economic_facts"},
            production_names=set(),
        )
        self.assertEqual(rows[0]["class"], "UNRESOLVED_DRIFT")
        self.assertEqual(rows[0]["owner"], "alembic_missing_in_production")


if __name__ == "__main__":
    unittest.main()
