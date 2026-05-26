# -*- coding: utf-8 -*-
"""Shared SQLite file DB for merchant dashboard tests (stable across main re-init)."""
from __future__ import annotations

import os
import tempfile


def pytest_configure() -> None:
    import models  # noqa: F401

    from extensions import db, init_database

    db_path = os.path.join(tempfile.gettempdir(), "cartflow_pytest_merchant.db")
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    init_database()
    db.create_all()
