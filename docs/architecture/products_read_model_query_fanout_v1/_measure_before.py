# -*- coding: utf-8 -*-
"""One-shot before-trace for PRODUCTS_READ_MODEL_QUERY_FANOUT_V1. Not a product path."""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main() -> None:
    fd, db_path = tempfile.mkstemp(prefix="cartflow_fanout_before_", suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
    os.environ["CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"] = "1"
    os.environ["ENV"] = "development"
    os.environ["SECRET_KEY"] = "fanout-before"

    from sqlalchemy import event

    from extensions import db, init_database, remove_scoped_session
    import models  # noqa: F401
    from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
    from schema_commercial_decision_commitment_v1 import (
        ensure_commercial_decision_commitment_schema,
        reset_commercial_decision_commitment_schema_guard_for_tests,
    )
    from schema_product_catalog_v1 import ensure_product_catalog_schema
    from schema_product_hesitation_mapping_v1 import ensure_product_hesitation_mapping_schema
    from schema_product_purchase_mapping_v1 import ensure_product_purchase_mapping_schema
    from schema_product_signal_events_v1 import ensure_product_signal_events_schema
    from services.live_reality_lab_v1 import apply_lab_scenario_v1, ensure_live_reality_lab_tenant_v1
    from services.live_reality_lab_v1.contract_v1 import LAB_STORE_SLUG
    from services.products_commercial_truth_v1.compose_v1 import compose_products_commercial_truth_v1
    from models import Store

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
    store = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()

    def _trace(label: str, slug: str, st):
        sqls: list[str] = []

        def _before(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            sqls.append(str(statement or ""))

        event.listen(db.engine, "before_cursor_execute", _before)
        t0 = time.perf_counter()
        pkg = compose_products_commercial_truth_v1(store_slug=slug, store=st)
        ms = (time.perf_counter() - t0) * 1000.0
        event.remove(db.engine, "before_cursor_execute", _before)
        interesting = [
            s.replace("\n", " ")[:180]
            for s in sqls
            if any(
                t in s.lower()
                for t in (
                    "product_catalog",
                    "cart_line",
                    "abandoned_cart",
                    "product_purchase",
                    "product_hesitation",
                    "product_signal",
                )
            )
        ]
        print(f"=== {label} ===")
        print("query_delta", pkg.get("query_delta"))
        print("products", pkg.get("counts"))
        print("wall_ms", round(ms, 3))
        print("sql_n", len(interesting))
        for i, s in enumerate(interesting, 1):
            print(f"  {i}. {s}")
        print("n_plus_one", pkg.get("n_plus_one"))
        return pkg

    _trace("LAB R17", LAB_STORE_SLUG, store)
    _trace("NORMAL empty slug", "acme_store", None)
    try:
        os.remove(db_path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
