# -*- coding: utf-8 -*-
"""Zid OAuth store schema ensure + verify."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid

import models  # noqa: F401 — register Store on Base.metadata
from extensions import db, init_database
from models import Store
from schema_zid_dev_oauth import (
    ensure_store_zid_integration_schema,
    reset_store_zid_integration_schema_cache_for_tests,
    verify_store_zid_integration_schema,
)


class SchemaZidDevOauthTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_integration_schema_cache_for_tests()
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_schema_zid_test_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()

    def tearDown(self) -> None:
        reset_store_zid_integration_schema_cache_for_tests()
        db.session.remove()

    def test_verify_reports_required_columns(self) -> None:
        status = verify_store_zid_integration_schema(db)
        self.assertIn("integration_source", status["required_columns"])
        self.assertIn("connected_at", status["required_columns"])

    def test_ensure_then_store_orm_loads_without_error(self) -> None:
        self.assertTrue(ensure_store_zid_integration_schema(db))
        status = verify_store_zid_integration_schema(db)
        self.assertTrue(status["ok"])
        row = Store(zid_store_id="schema-test-1", is_active=True)
        db.session.add(row)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        loaded.integration_source = "zid_dev"
        db.session.commit()
        self.assertEqual(loaded.integration_source, "zid_dev")


if __name__ == "__main__":
    unittest.main()
