# -*- coding: utf-8 -*-
"""Local SQLite EXPLAIN QUERY PLAN for the consolidated Products read. Not a product path."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main() -> None:
    fd, db_path = tempfile.mkstemp(prefix="cf_plan_", suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
    os.environ["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
    os.environ["ENV"] = "development"
    os.environ["SECRET_KEY"] = "plan"

    from sqlalchemy import text

    from extensions import db, init_database, remove_scoped_session
    import models  # noqa: F401
    from models import Store
    from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
    from schema_commercial_decision_commitment_v1 import (
        ensure_commercial_decision_commitment_schema,
        reset_commercial_decision_commitment_schema_guard_for_tests,
    )
    from schema_product_catalog_v1 import ensure_product_catalog_schema
    from schema_product_hesitation_mapping_v1 import (
        ensure_product_hesitation_mapping_schema,
    )
    from schema_product_purchase_mapping_v1 import (
        ensure_product_purchase_mapping_schema,
    )
    from schema_product_signal_events_v1 import ensure_product_signal_events_schema
    from services.live_reality_lab_v1 import (
        apply_lab_scenario_v1,
        ensure_live_reality_lab_tenant_v1,
    )
    from services.live_reality_lab_v1.contract_v1 import (
        LAB_STORE_SLUG,
        LAB_SYNTHETIC_VISIT_SOURCE,
    )
    from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_VIEWED
    from services.products_commercial_truth_v1.contract_v1 import (
        MAX_CART_LINK_ROWS,
        MAX_PRODUCTS,
    )
    from services.products_commercial_truth_v1.load_consolidated_v1 import (
        products_read_sql_v1,
    )

    try:
        remove_scoped_session()
        db.engine.dispose()
    except Exception:
        pass
    init_database()
    db.create_all()
    reset_commercial_decision_commitment_schema_guard_for_tests()
    ensure_commercial_decision_commitment_schema(db)
    ensure_product_catalog_schema(db)
    ensure_cart_line_snapshots_schema(db)
    ensure_product_signal_events_schema(db)
    ensure_product_hesitation_mapping_schema(db)
    ensure_product_purchase_mapping_schema(db)
    ensure_live_reality_lab_tenant_v1()
    apply_lab_scenario_v1(
        authenticated_store_slug=LAB_STORE_SLUG,
        scenario_id="R17_shipping_hesitation",
    )
    store = (
        db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    )
    params = {
        "slug": LAB_STORE_SLUG,
        "store_id": int(store.id),
        "max_products": MAX_PRODUCTS,
        "max_cart_pairs": MAX_CART_LINK_ROWS,
        "lab_source": LAB_SYNTHETIC_VISIT_SOURCE,
        "lab_signal": SIGNAL_PRODUCT_VIEWED,
    }
    sql = products_read_sql_v1(lab_tenant=True, dialect="sqlite")
    rows = db.session.execute(text("EXPLAIN QUERY PLAN " + sql), params).fetchall()
    print("=== LAB R17 EXPLAIN QUERY PLAN ===")
    for row in rows:
        print(tuple(row))
    idxs = db.session.execute(
        text(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' "
            "AND tbl_name IN ("
            "'product_catalog_entries','cart_line_snapshots','abandoned_carts',"
            "'product_purchase_mappings','product_hesitation_mappings',"
            "'product_signal_events') ORDER BY tbl_name, name"
        )
    ).fetchall()
    print("=== INDEXES ===")
    for name, tbl, sql_txt in idxs:
        print(tbl, name, (sql_txt or "")[:140])
    try:
        os.remove(db_path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
