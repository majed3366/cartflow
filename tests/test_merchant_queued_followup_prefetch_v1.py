# -*- coding: utf-8 -*-
"""Queued followup bulk prefetch matches per-group DB stale-meta probe."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store

from services.merchant_queued_followup_prefetch_v1 import (
    QueuedFollowupPrefetchIndex,
    bulk_load_queued_followup_index,
)
from services.normal_recovery_merchant_stale import (
    _has_recent_queued_followup,
    merchant_group_stale_meta,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QueuedFollowupPrefetchTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()

    def tearDown(self) -> None:
        db.session.rollback()

    def _seed_store_cart_and_queued_log(
        self,
        *,
        session_id: str,
        cart_id: str,
        created_at: datetime,
    ) -> tuple[Store, AbandonedCart]:
        slug = f"sim-prefetch-{session_id}"
        st = Store(zid_store_id=slug)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=st.id,
            recovery_session_id=session_id,
            zid_cart_id=cart_id,
            status="abandoned",
            last_seen_at=_utc_now() - timedelta(days=5),
        )
        db.session.add(ac)
        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=session_id,
            cart_id=cart_id,
            status="queued",
            created_at=created_at,
        )
        db.session.add(lg)
        db.session.commit()
        return st, ac

    def test_prefetch_matches_db_for_recent_queued(self) -> None:
        now = _utc_now()
        st, ac = self._seed_store_cart_and_queued_log(
            session_id="sess-qf-1",
            cart_id="cart-qf-1",
            created_at=now - timedelta(minutes=1),
        )
        since = now - timedelta(minutes=5)
        idx = bulk_load_queued_followup_index(
            store_slug=st.zid_store_id,
            session_ids={"sess-qf-1"},
            cart_ids={"cart-qf-1"},
        )
        self.assertTrue(idx.has_recent_for_abandoned(ac, since_utc=since))
        self.assertTrue(
            _has_recent_queued_followup(
                [ac],
                store_slug=st.zid_store_id,
                since_utc=since,
                queued_followup_prefetch=idx,
            )
        )

    def test_prefetch_respects_created_at_cutoff(self) -> None:
        now = _utc_now()
        st, ac = self._seed_store_cart_and_queued_log(
            session_id="sess-qf-old",
            cart_id="cart-qf-old",
            created_at=now - timedelta(hours=2),
        )
        since = now - timedelta(minutes=30)
        idx = bulk_load_queued_followup_index(
            store_slug=st.zid_store_id,
            session_ids={"sess-qf-old"},
            cart_ids={"cart-qf-old"},
        )
        self.assertFalse(idx.has_recent_for_abandoned(ac, since_utc=since))
        self.assertFalse(
            _has_recent_queued_followup(
                [ac],
                store_slug=st.zid_store_id,
                since_utc=since,
                queued_followup_prefetch=idx,
            )
        )

    def test_merchant_group_stale_meta_same_with_prefetch(self) -> None:
        now = _utc_now()
        st, ac = self._seed_store_cart_and_queued_log(
            session_id="sess-stale",
            cart_id="cart-stale",
            created_at=now - timedelta(minutes=1),
        )
        activity = {int(ac.id): now - timedelta(days=4)}
        idx = bulk_load_queued_followup_index(
            store_slug=st.zid_store_id,
            session_ids={"sess-stale"},
            cart_ids={"cart-stale"},
        )
        with_prefetch = merchant_group_stale_meta(
            [ac],
            store_slug=st.zid_store_id,
            activity_map=activity,
            coarse="pending",
            now_utc=now,
            queued_followup_prefetch=idx,
        )
        without_prefetch = merchant_group_stale_meta(
            [ac],
            store_slug=st.zid_store_id,
            activity_map=activity,
            coarse="pending",
            now_utc=now,
        )
        self.assertEqual(with_prefetch, without_prefetch)

    def test_index_keys_session_cart_recovery_key(self) -> None:
        now = _utc_now()
        idx = QueuedFollowupPrefetchIndex(store_slug="demo")
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id="s1",
            cart_id="c1",
            recovery_key="demo:s1",
            status="queued",
            created_at=now,
        )
        idx.ingest_row(lg)
        self.assertIn("s1", idx.by_session_id)
        self.assertIn("c1", idx.by_cart_id)
        self.assertIn("demo:s1", idx.by_recovery_key)


if __name__ == "__main__":
    unittest.main()
