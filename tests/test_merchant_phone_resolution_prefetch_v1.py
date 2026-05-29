# -*- coding: utf-8 -*-
"""Bulk phone resolution matches per-row raw batch resolver."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, Store

from services.merchant_phone_resolution_prefetch_v1 import (
    build_cust_phone_by_ac_bulk,
    build_phone_resolution_comparison,
    phone_resolution_prof_reset,
    phone_resolution_prof_snapshot,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MerchantPhoneResolutionPrefetchTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        phone_resolution_prof_reset()

    def tearDown(self) -> None:
        db.session.rollback()

    def _unique_slug(self) -> str:
        return f"sim-phone-{uuid.uuid4().hex[:10]}"

    def _seed_rows(self, slug: str) -> tuple[Store, AbandonedCart]:
        suffix = uuid.uuid4().hex[:8]
        session_id = f"sess-phone-{suffix}"
        cart_id = f"cart-phone-{suffix}"
        st = Store(zid_store_id=slug)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=st.id,
            recovery_session_id=session_id,
            zid_cart_id=cart_id,
            customer_phone="+966511111111",
            status="abandoned",
            last_seen_at=_utc_now(),
        )
        db.session.add(ac)
        reason = CartRecoveryReason(
            store_slug=slug,
            session_id=session_id,
            customer_phone="+966533333333",
            reason="price_high",
        )
        db.session.add(reason)
        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=session_id,
            cart_id=cart_id,
            phone="+966544444444",
            status="sent",
            sent_at=_utc_now(),
        )
        db.session.add(lg)
        db.session.commit()
        db.session.refresh(st)
        db.session.refresh(ac)
        return st, ac

    def _batch_from_reads(self, slug: str, st: Store, ac: AbandonedCart, main: object) -> object:
        full_rows = [ac]
        return main._merchant_normal_dashboard_batch_reads(full_rows, st)

    def test_bulk_matches_raw_resolver(self) -> None:
        import main  # noqa: PLC0415

        slug = self._unique_slug()
        st, ac = self._seed_rows(slug)
        batch = self._batch_from_reads(slug, st, ac, main)
        bulk_map = build_cust_phone_by_ac_bulk([ac], st, batch)
        raw_map: dict[int, str] = {}
        empty_batch = batch
        empty_batch.cust_phone_by_ac = {}
        for row in [ac]:
            aid = int(row.id)
            raw_map[aid] = main._merchant_normal_batch_resolve_customer_phone_raw(
                row, st, empty_batch
            ).strip()
        self.assertEqual(bulk_map, raw_map)
        self.assertTrue(bulk_map.get(int(ac.id)))

    def test_batch_reads_populates_cust_phone_by_ac(self) -> None:
        import main  # noqa: PLC0415

        slug = self._unique_slug()
        st, ac = self._seed_rows(slug)
        batch = self._batch_from_reads(slug, st, ac, main)
        self.assertIn(int(ac.id), batch.cust_phone_by_ac)
        self.assertTrue((batch.cust_phone_by_ac.get(int(ac.id)) or "").strip())

    def test_profiling_snapshot_records_loop_count(self) -> None:
        import main  # noqa: PLC0415

        slug = self._unique_slug()
        st, ac = self._seed_rows(slug)
        batch = self._batch_from_reads(slug, st, ac, main)
        phone_resolution_prof_reset()
        build_cust_phone_by_ac_bulk([ac], st, batch)
        snap = phone_resolution_prof_snapshot()
        self.assertGreaterEqual(int(snap.get("phone_resolution_loop_count") or 0), 1)
        self.assertEqual(int(snap.get("phone_resolution_fallback_count") or 0), 0)

    def test_build_phone_resolution_comparison_shape(self) -> None:
        cmp = build_phone_resolution_comparison(
            avg_total_dashboard_queries=40.0,
            avg_loop_count=220.0,
            avg_fallback_count=0.0,
            avg_db_queries_after=0.0,
        )
        self.assertEqual(cmp.get("phone_resolution_db_queries_before"), 150)
        self.assertTrue(cmp.get("per_row_db_eliminated"))
        after = cmp.get("after_avg_per_dashboard_check") or {}
        self.assertIn("phone_resolution_loop_count", after)
        self.assertIn("phone_resolution_fallback_count", after)


if __name__ == "__main__":
    unittest.main()
