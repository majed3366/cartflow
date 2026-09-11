# -*- coding: utf-8 -*-
"""Migration Lineage Integrity V1 — walkable graph + stamp-only authority."""
from __future__ import annotations

import os
import tempfile
import unittest

from sqlalchemy import create_engine, inspect, text

from services.migration_lineage_integrity_v1.graph import inspect_lineage
from services.migration_lineage_integrity_v1.stamp import (
    EXPECTED_PRODUCTION_ANCESTORS,
    ancestor_paths_to_head,
    plan_or_stamp_heads,
    stamp_canonical_from_ancestors,
)

EXPECTED_HEADS = ("f10altparity01",)
BRIDGE_BASES = ("e0fnd250425a", "p2q3r4s5t6u7")


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


class MigrationLineageIntegrityTests(unittest.TestCase):
    def test_revision_map_walkable(self) -> None:
        out = inspect_lineage()
        self.assertTrue(out["walkable"], out.get("error"))
        self.assertEqual(tuple(out["heads"]), EXPECTED_HEADS)
        for rev in BRIDGE_BASES:
            self.assertIn(rev, out["bases"])
        self.assertGreaterEqual(out["revision_count"], 62)
        self.assertNotIn("m1n2o3p4q5r6", out["bases"])
        self.assertNotIn("a3ff333f6d46", out["bases"])
        self.assertEqual(out["missing_parents"], [])

    def test_stamp_plan_does_not_write(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            plan = plan_or_stamp_heads(database_url=url, execute=False)
            self.assertTrue(plan["ok"], plan)
            self.assertEqual(plan["reason"], "plan_only")
            self.assertEqual(plan["action"], "stamp_heads")
            engine = create_engine(url)
            self.assertFalse(inspect(engine).has_table("alembic_version"))
            engine.dispose()
        finally:
            _unlink(path)

    def test_stamp_execute_writes_heads_only(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            out = plan_or_stamp_heads(database_url=url, execute=True)
            self.assertTrue(out["ok"], out)
            self.assertEqual(out["reason"], "stamped")
            self.assertEqual(set(out["alembic_version_after"]), set(EXPECTED_HEADS))
            engine = create_engine(url)
            tables = set(inspect(engine).get_table_names())
            self.assertEqual(tables, {"alembic_version"})
            with engine.connect() as conn:
                rows = [r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version"))]
            self.assertEqual(set(rows), set(EXPECTED_HEADS))
            engine.dispose()
        finally:
            _unlink(path)

    def test_stamp_refuses_unexpected_version(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            engine = create_engine(url)
            with engine.begin() as conn:
                conn.execute(
                    text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                )
                conn.execute(text("INSERT INTO alembic_version VALUES ('not_a_head')"))
            engine.dispose()
            out = plan_or_stamp_heads(database_url=url, execute=True)
            self.assertFalse(out["ok"])
            self.assertTrue(str(out["reason"]).startswith("unexpected_alembic_version"))
        finally:
            _unlink(path)

    def test_ancestors_reach_canonical_head(self) -> None:
        graph = ancestor_paths_to_head()
        self.assertTrue(graph["ok"], graph)
        self.assertEqual(graph["heads"], [EXPECTED_HEADS[0]])
        for anc in EXPECTED_PRODUCTION_ANCESTORS:
            self.assertIn(anc, graph["paths"])
            self.assertEqual(graph["paths"][anc][0], anc)
            self.assertEqual(graph["paths"][anc][-1], EXPECTED_HEADS[0])

    def test_canonical_stamp_refuses_wrong_before(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            engine = create_engine(url)
            with engine.begin() as conn:
                conn.execute(
                    text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                )
                conn.execute(text("INSERT INTO alembic_version VALUES ('k1l2m3n4o5p6q7')"))
            engine.dispose()
            out = stamp_canonical_from_ancestors(database_url=url, execute=True)
            self.assertFalse(out["ok"])
            self.assertTrue(str(out["reason"]).startswith("unexpected_alembic_version"))
        finally:
            _unlink(path)

    def test_canonical_stamp_from_ancestors_metadata_only(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        url = "sqlite:///" + path.replace("\\", "/")
        try:
            engine = create_engine(url)
            with engine.begin() as conn:
                conn.execute(
                    text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
                )
                for rev in sorted(EXPECTED_PRODUCTION_ANCESTORS):
                    conn.execute(
                        text("INSERT INTO alembic_version VALUES (:v)"),
                        {"v": rev},
                    )
                conn.execute(text("CREATE TABLE stores (id INTEGER PRIMARY KEY)"))
            engine.dispose()
            plan = stamp_canonical_from_ancestors(database_url=url, execute=False)
            self.assertTrue(plan["ok"], plan)
            self.assertEqual(plan["reason"], "plan_only")
            out = stamp_canonical_from_ancestors(database_url=url, execute=True)
            self.assertTrue(out["ok"], out)
            self.assertEqual(out["alembic_version_after"], [EXPECTED_HEADS[0]])
            engine = create_engine(url)
            tables = set(inspect(engine).get_table_names())
            self.assertEqual(tables, {"alembic_version", "stores"})
            engine.dispose()
        finally:
            _unlink(path)


if __name__ == "__main__":
    unittest.main()

