# -*- coding: utf-8 -*-
"""Merged CartRecoveryReason bulk load matches dual-query precedence."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from extensions import db
from models import CartRecoveryReason, Store

from services.merchant_reason_bulk_prefetch_v1 import (
    build_reason_bulk_comparison,
    build_reason_maps_from_rows,
    bulk_load_reason_maps_by_session,
    reason_bulk_prof_reset,
    reason_bulk_prof_snapshot,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MerchantReasonBulkPrefetchTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        reason_bulk_prof_reset()

    def tearDown(self) -> None:
        db.session.rollback()

    def _row(
        self,
        *,
        slug: str,
        session_id: str,
        reason: str,
        updated_at: datetime,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            session_id=session_id,
            store_slug=slug,
            reason=reason,
            updated_at=updated_at,
            customer_phone="+966500000000",
        )

    def test_store_scoped_wins_over_any_store(self) -> None:
        now = _utc_now()
        slug = "store-a"
        rows = [
            self._row(
                slug="store-b",
                session_id="s1",
                reason="price_high",
                updated_at=now,
            ),
            self._row(
                slug=slug,
                session_id="s1",
                reason="quality_issue",
                updated_at=now - timedelta(minutes=5),
            ),
        ]
        store_map, any_map, fallback = build_reason_maps_from_rows(rows, store_slug=slug)
        self.assertEqual(store_map["s1"].reason, "quality_issue")
        self.assertEqual(any_map["s1"].reason, "price_high")
        self.assertEqual(fallback, 0)

    def test_any_store_fallback_when_store_missing(self) -> None:
        now = _utc_now()
        rows = [
            self._row(
                slug="other-store",
                session_id="s2",
                reason="shipping_delay",
                updated_at=now,
            ),
        ]
        store_map, any_map, fallback = build_reason_maps_from_rows(
            rows, store_slug="my-store"
        )
        self.assertNotIn("s2", store_map)
        self.assertEqual(any_map["s2"].reason, "shipping_delay")
        self.assertEqual(fallback, 1)

    def test_bulk_load_matches_dual_query_semantics(self) -> None:
        slug = f"sim-reason-{uuid.uuid4().hex[:8]}"
        st = Store(zid_store_id=slug)
        db.session.add(st)
        now = _utc_now()
        r_store = CartRecoveryReason(
            store_slug=slug,
            session_id="sess-r1",
            reason="quality_issue",
            updated_at=now - timedelta(minutes=1),
        )
        r_other = CartRecoveryReason(
            store_slug="other",
            session_id="sess-r1",
            reason="price_high",
            updated_at=now,
        )
        db.session.add_all([r_store, r_other])
        db.session.commit()

        store_map, any_map, fetched, fallback = bulk_load_reason_maps_by_session(
            store_slug=slug,
            session_keys={"sess-r1"},
        )
        self.assertEqual(fetched, 2)
        self.assertEqual(store_map["sess-r1"].reason, "quality_issue")
        self.assertEqual(any_map["sess-r1"].reason, "price_high")
        self.assertEqual(fallback, 0)

        # Legacy dual-query equivalent
        rs_rows = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == slug,
                CartRecoveryReason.session_id.in_(["sess-r1"]),
            )
            .order_by(CartRecoveryReason.updated_at.desc())
            .all()
        )
        ra_rows = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id.in_(["sess-r1"]))
            .order_by(CartRecoveryReason.updated_at.desc())
            .all()
        )
        legacy_store: dict[str, CartRecoveryReason] = {}
        for r in rs_rows:
            k = (r.session_id or "").strip()
            if k and k not in legacy_store:
                legacy_store[k] = r
        legacy_any: dict[str, CartRecoveryReason] = {}
        for r in ra_rows:
            k = (r.session_id or "").strip()
            if k and k not in legacy_any:
                legacy_any[k] = r
        self.assertEqual(store_map["sess-r1"].reason, legacy_store["sess-r1"].reason)
        self.assertEqual(any_map["sess-r1"].reason, legacy_any["sess-r1"].reason)

    def test_profiling_snapshot_one_query(self) -> None:
        slug = f"sim-reason-prof-{uuid.uuid4().hex[:8]}"
        db.session.add(
            CartRecoveryReason(
                store_slug=slug,
                session_id="sess-p",
                reason="other",
            )
        )
        db.session.commit()
        reason_bulk_prof_reset()
        bulk_load_reason_maps_by_session(store_slug=slug, session_keys={"sess-p"})
        snap = reason_bulk_prof_snapshot()
        self.assertEqual(int(snap.get("reason_bulk_queries_after") or 0), 1)

    def test_build_reason_bulk_comparison_shape(self) -> None:
        cmp = build_reason_bulk_comparison(
            avg_total_dashboard_queries=44.0,
            avg_reason_bulk_queries_after=1.0,
            avg_fallback_reason_rows_used=0.5,
        )
        self.assertEqual(cmp.get("reason_bulk_queries_before"), 2)
        self.assertTrue(cmp.get("dual_query_eliminated"))


if __name__ == "__main__":
    unittest.main()
