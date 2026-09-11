# -*- coding: utf-8 -*-
"""Classification of db.create_all() call sites. Audit only — not executed."""
from __future__ import annotations

# Production startup used create_all as schema recovery. That path is now gated.
# Request helpers still call db.create_all(); extensions.db.create_all no-ops
# when create_all_permitted() is false, so they cannot materialize tables.

CREATE_ALL_SITE_CLASSES: dict[str, str] = {
    "extensions.py:_DB.create_all": "PRODUCTION_STARTUP",
    "main.py:_ensure_cartflow_api_db_warmed": "PRODUCTION_STARTUP",
    "main.py:_ensure_db_schema": "LEGACY",
    "schema_*.py:ensure_*": "LEGACY",
    "schema_widget.py": "LEGACY",
    "schema_merchant_auth.py": "LEGACY",
    "schema_store_identity.py": "LEGACY",
    "schema_purchase_truth.py": "LEGACY",
    "schema_order_economic_fact_v1.py": "LEGACY",
    "routes/ops.py:admin_init_db": "LEGACY",
    "routes/ops.py:_dev_set_token_impl": "DEV_BOOTSTRAP",
    "routes/dev_diagnostics.py": "DEV_BOOTSTRAP",
    "routes/cartflow.py": "LEGACY",
    "routes/knowledge.py": "LEGACY",
    "routes/daily_brief.py": "LEGACY",
    "services/* (request helpers)": "LEGACY",
    "tests/*": "TEST_ONLY",
    "scripts/*": "DEV_BOOTSTRAP",
}

PRODUCTION_CREATE_ALL_BEFORE = "ENABLED"
PRODUCTION_CREATE_ALL_AFTER = "DISABLED"
