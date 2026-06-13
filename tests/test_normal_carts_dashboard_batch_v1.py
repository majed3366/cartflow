# -*- coding: utf-8 -*-
"""Normal carts dashboard batch architecture recovery v1 — N+1 and partial guardrails."""
from __future__ import annotations

import time
import uuid
import unittest
from datetime import datetime, timezone

from sqlalchemy import event

from extensions import db
from fastapi.testclient import TestClient
from main import _api_json_dashboard_normal_carts, app
from models import AbandonedCart, CartRecoveryLog, Store
from services.normal_carts_dashboard_batch_v1 import (
    NORMAL_CARTS_LOCAL_MS_TARGET_50_ROWS,
    NORMAL_CARTS_MAX_BUSINESS_QUERIES_50_ROWS,
    build_normal_carts_unified_rows,
)


def _count_business_queries(fn, *args, **kwargs) -> tuple[int, float, object]:
    queries: list[str] = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany) -> None:
        if not statement.strip().upper().startswith("PRAGMA"):
            queries.append(statement)

    t0 = time.perf_counter()
    try:
        out = fn(*args, **kwargs)
    finally:
        event.remove(db.engine, "before_cursor_execute", _before)
    ms = (time.perf_counter() - t0) * 1000
    return len(queries), ms, out


class NormalCartsDashboardBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]
        db.create_all()

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def _make_store(self, slug: str | None = None) -> Store:
        slug = slug or f"nc-arch-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=5000)
        db.session.add(st)
        db.session.commit()
        return st

    def _seed_normal_rows(self, store: Store, n: int) -> list[AbandonedCart]:
        rows: list[AbandonedCart] = []
        now = datetime.now(timezone.utc)
        for i in range(n):
            sid = f"s-nc-{self._suffix}-{i}"
            ac = AbandonedCart(
                store_id=int(store.id),
                zid_cart_id=f"z-nc-{self._suffix}-{i}",
                recovery_session_id=sid,
                customer_phone="96650111" + f"{i:04d}"[-4:],
                status="abandoned",
                cart_value=120.0 + i,
                last_seen_at=now,
            )
            db.session.add(ac)
            rows.append(ac)
        db.session.commit()
        return rows

    def _warm_normal_carts_batch(self, store: Store) -> None:
        from main import _merchant_dashboard_db_ready

        _merchant_dashboard_db_ready()
        build_normal_carts_unified_rows(store, page_limit=50, page_offset=0)

    def test_unified_build_query_budget_10_rows(self) -> None:
        store = self._make_store()
        self._seed_normal_rows(store, 10)
        self._warm_normal_carts_batch(store)
        qn, ms, out = _count_business_queries(
            build_normal_carts_unified_rows,
            store,
            page_limit=50,
            page_offset=0,
        )
        active, archived, prof, perf = out
        self.assertLessEqual(
            qn,
            NORMAL_CARTS_MAX_BUSINESS_QUERIES_50_ROWS,
            f"query explosion: {qn} queries",
        )
        self.assertGreaterEqual(len(active), 1)
        self.assertFalse(perf.partial)
        self.assertFalse(perf.degraded)
        self.assertGreaterEqual(int(prof.get("logs_loaded") or 0), 0)

    def test_api_json_includes_perf_block(self) -> None:
        store = self._make_store()
        self._seed_normal_rows(store, 5)
        self._warm_normal_carts_batch(store)
        body, prof = _api_json_dashboard_normal_carts(store)
        self.assertIn("_perf", body)
        perf = body["_perf"]
        self.assertIn("query_count", perf)
        self.assertIn("duration_ms", perf)
        self.assertIn("candidate_rows", perf)
        self.assertIn("visible_rows", perf)
        self.assertIn("partial", perf)
        self.assertFalse(bool(perf.get("partial")))
        self.assertGreaterEqual(int(perf.get("visible_rows") or 0), 1)

    def test_unified_build_scales_50_rows_under_time_budget(self) -> None:
        store = self._make_store()
        self._seed_normal_rows(store, 50)
        self._warm_normal_carts_batch(store)
        qn, ms, out = _count_business_queries(
            build_normal_carts_unified_rows,
            store,
            page_limit=50,
            page_offset=0,
        )
        active, _arch, _prof, perf = out
        self.assertLessEqual(qn, NORMAL_CARTS_MAX_BUSINESS_QUERIES_50_ROWS + 15)
        self.assertLess(ms, NORMAL_CARTS_LOCAL_MS_TARGET_50_ROWS * 3)
        self.assertFalse(perf.partial)
        self.assertGreaterEqual(len(active), 1)


if __name__ == "__main__":
    unittest.main()
