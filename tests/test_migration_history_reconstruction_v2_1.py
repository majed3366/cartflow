# -*- coding: utf-8 -*-
"""Migration History Reconstruction V2.1 — lineage, failure, and helper replay."""
from __future__ import annotations

import inspect as pyinspect
import os
import tempfile
import unittest

from sqlalchemy import create_engine

from services.migration_lineage_integrity_v1.authority import (
    create_all_permitted,
    inspect_required_schema,
)
from services.migration_lineage_integrity_v1.future_rule import future_revision_parent_rule
from services.migration_lineage_integrity_v1.graph import inspect_lineage
from services.migration_lineage_integrity_v1.inventory import (
    DEPRECATED_PRODUCTION_ONLY_TABLES,
)
from services.migration_lineage_integrity_v1.migration_law import (
    LAWS,
    evaluate_migration_law,
)
from services.migration_lineage_integrity_v1.postgres_replay import (
    B_CLASS_TABLES,
    CANONICAL_HEAD,
)
from services.migration_lineage_integrity_v1.replay import upgrade_heads_from_empty


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


class ReconstructionLineageTests(unittest.TestCase):
    def test_single_head_and_approved_bases(self) -> None:
        out = inspect_lineage()
        self.assertTrue(out["walkable"], out.get("error"))
        self.assertEqual(out["heads"], [CANONICAL_HEAD])
        self.assertEqual(out["bases"], ["e0fnd250425a", "p2q3r4s5t6u7"])
        self.assertEqual(out["missing_parents"], [])
        self.assertGreaterEqual(out["revision_count"], 65)

    def test_only_approved_pointer_changes(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        versions = os.path.join(root, "alembic", "versions")

        def _rev(name: str) -> str:
            for fn in os.listdir(versions):
                if fn.startswith(name):
                    with open(os.path.join(versions, fn), encoding="utf-8") as fh:
                        return fh.read()
            self.fail(f"missing {name}")
            return ""

        self.assertIn('down_revision: Union[str, Sequence[str], None] = "e0fnd250425a"', _rev("a3ff333f6d46"))
        self.assertIn('down_revision: Union[str, Sequence[str], None] = "e0fnd250425a"', _rev("m1n2o3p4q5r6"))
        self.assertIn('down_revision: Union[str, Sequence[str], None] = "e3sch210521a"', _rev("o1p2q3r4s5t6"))
        p2q3 = _rev("p2q3r4s5t6u7")
        self.assertIn("def upgrade() -> None:", p2q3)
        self.assertNotIn("create_table", p2q3)
        self.assertNotIn("movement_snapshots", p2q3.split("def upgrade")[1])

    def test_future_parent_must_be_present(self) -> None:
        ok = future_revision_parent_rule(CANONICAL_HEAD)
        self.assertTrue(ok["ok"], ok)
        self.assertFalse(future_revision_parent_rule(None)["ok"])
        self.assertFalse(future_revision_parent_rule("not_a_real_revision")["ok"])


class SqliteHelperReplayTests(unittest.TestCase):
    def test_empty_sqlite_reaches_head(self) -> None:
        fd, path = tempfile.mkstemp(suffix="_v21.db")
        os.close(fd)
        _unlink(path)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            out = upgrade_heads_from_empty(database_url=url)
            self.assertTrue(out["ok"], out.get("failing_message"))
            self.assertEqual(out.get("alembic_version"), [CANONICAL_HEAD])
            tables = set(out.get("tables") or [])
            for name in B_CLASS_TABLES:
                self.assertIn(name, tables)
            self.assertIn("stores", tables)
            self.assertIn("order_economic_facts", tables)
            self.assertNotIn("commercial_decision_commitments", tables)
            chk = inspect_required_schema(create_engine(url))
            self.assertTrue(chk["ok"], chk)
        finally:
            _unlink(path)


class SchemaFailureTests(unittest.TestCase):
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

    def test_empty_db_fails_required_schema(self) -> None:
        os.environ["CARTFLOW_REFUSE_CREATE_ALL"] = "1"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        self.assertFalse(create_all_permitted())
        fd, path = tempfile.mkstemp(suffix="_v21_empty.db")
        os.close(fd)
        _unlink(path)
        url = "sqlite:///" + path.replace("\\", "/")
        engine = create_engine(url)
        try:
            chk = inspect_required_schema(engine)
            self.assertFalse(chk["ok"])
            self.assertIn("stores", chk["missing"])
        finally:
            engine.dispose()
            _unlink(path)

    def test_create_all_production_gate_disabled(self) -> None:
        os.environ["ENV"] = "production"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        os.environ.pop("CARTFLOW_ALLOW_CREATE_ALL", None)
        os.environ.pop("CARTFLOW_REFUSE_CREATE_ALL", None)
        self.assertFalse(create_all_permitted())
        from extensions import _DB

        src = pyinspect.getsource(_DB.create_all)
        self.assertIn("create_all_permitted", src)
        self.assertIn("note_create_all_refused", src)

    def test_future_revision_law_requires_parent(self) -> None:
        self.assertEqual(future_revision_parent_rule(None)["reason"], "parent_required")
        self.assertTrue(future_revision_parent_rule(CANONICAL_HEAD)["ok"])


class FutureMigrationLawTests(unittest.TestCase):
    def test_ten_invariants_frozen(self) -> None:
        self.assertEqual(len(LAWS), 10)
        out = evaluate_migration_law()
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["canonical_head"], CANONICAL_HEAD)
        self.assertEqual(
            DEPRECATED_PRODUCTION_ONLY_TABLES,
            frozenset({"commercial_decision_commitments"}),
        )

    def test_authoritative_replay_helper_is_postgres(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(
            root,
            "services",
            "migration_lineage_integrity_v1",
            "postgres_replay.py",
        )
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("pgembed", src)
        self.assertIn("CREATE DATABASE", src)
        self.assertNotIn("sqlite", src.lower())


if __name__ == "__main__":
    unittest.main()
