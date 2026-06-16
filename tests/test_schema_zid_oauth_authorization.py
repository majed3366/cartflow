# -*- coding: utf-8 -*-
"""Zid OAuth Authorization store column schema ensure + verify."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid

import models  # noqa: F401
from extensions import db, init_database
from models import Store
from schema_zid_oauth_authorization import (
    ensure_store_zid_oauth_authorization_schema,
    reset_store_zid_oauth_authorization_schema_cache_for_tests,
    verify_store_zid_oauth_authorization_schema,
)


class SchemaZidOauthAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_schema_zid_auth_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()

    def tearDown(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db.session.remove()

    def test_verify_reports_required_column(self) -> None:
        status = verify_store_zid_oauth_authorization_schema(db)
        self.assertIn("zid_authorization_token", status["required_columns"])

    def test_ensure_then_store_orm_loads_without_error(self) -> None:
        self.assertTrue(ensure_store_zid_oauth_authorization_schema(db))
        status = verify_store_zid_oauth_authorization_schema(db)
        self.assertTrue(status["ok"])
        row = Store(zid_store_id="schema-auth-test-1", is_active=True)
        db.session.add(row)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        loaded.zid_authorization_token = "partner-auth-value"
        db.session.commit()
        self.assertEqual(loaded.zid_authorization_token, "partner-auth-value")


if __name__ == "__main__":
    unittest.main()
