# -*- coding: utf-8 -*-
"""Production store schema bootstrap."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid

import models  # noqa: F401
from extensions import db, init_database
from models import Store
from schema_production_store_bootstrap import (
    ensure_production_store_schema,
    log_production_database_identity,
    reset_production_store_schema_bootstrap_for_tests,
    verify_production_store_schema,
)


class SchemaProductionStoreBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_production_store_schema_bootstrap_for_tests()
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_schema_bootstrap_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()

    def tearDown(self) -> None:
        reset_production_store_schema_bootstrap_for_tests()
        db.session.remove()

    def test_bootstrap_verifies_minimum_columns(self) -> None:
        self.assertTrue(ensure_production_store_schema(db, context="test"))
        status = verify_production_store_schema(db)
        self.assertTrue(status["ok"])

    def test_store_orm_integration_source_after_bootstrap(self) -> None:
        ensure_production_store_schema(db, context="test")
        row = Store(zid_store_id=f"boot-{uuid.uuid4().hex[:8]}", is_active=True)
        db.session.add(row)
        db.session.commit()
        row.integration_source = "zid_dev"
        row.connected_at = None
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        self.assertEqual(loaded.integration_source, "zid_dev")

    def test_database_identity_log_does_not_require_password(self) -> None:
        ident = log_production_database_identity(context="test")
        self.assertIn("scheme", ident)


if __name__ == "__main__":
    unittest.main()
