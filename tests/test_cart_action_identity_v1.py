# -*- coding: utf-8 -*-
"""Cart archive identity V1 — session-only keys must not mutate sibling carts."""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.cart_action_identity_v1 import (
    any_merchant_archived_for_mutation_keys,
    filter_mutation_recovery_keys,
    is_session_only_recovery_key,
    mutation_recovery_keys_for_abandoned_cart,
    session_only_recovery_key,
)
from services.merchant_cart_lifecycle_archive_v1 import (
    archive_recovery_keys,
    dashboard_cart_lifecycle_archive_from_body,
    dashboard_cart_lifecycle_reopen_from_body,
    is_merchant_archived,
    reopen_recovery_keys,
)
from services.recovery_message_context_v1 import recovery_key_from_parts


class CartActionIdentityV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self.uid = uuid.uuid4().hex[:10]
        self.slug = f"id-store-{self.uid}"
        self.sid = f"id-sess-{self.uid}"
        self.zid_a = f"z-cart-a-{self.uid}"
        self.zid_b = f"z-cart-b-{self.uid}"
        self.st = Store(zid_store_id=self.slug, recovery_attempts=1)
        db.session.add(self.st)
        db.session.flush()
        self.ac_a = AbandonedCart(
            store_id=int(self.st.id),
            zid_cart_id=self.zid_a,
            recovery_session_id=self.sid,
            customer_phone="966501000001",
            status="abandoned",
            cart_value=100.0,
        )
        self.ac_b = AbandonedCart(
            store_id=int(self.st.id),
            zid_cart_id=self.zid_b,
            recovery_session_id=self.sid,
            customer_phone="966501000002",
            status="abandoned",
            cart_value=200.0,
        )
        db.session.add_all([self.ac_a, self.ac_b])
        db.session.flush()
        self.rk_session = session_only_recovery_key(
            store_slug=self.slug, session_id=self.sid
        )
        self.rk_a = recovery_key_from_parts(
            store_slug=self.slug, session_id=self.sid, cart_id=self.zid_a
        )
        self.rk_b = recovery_key_from_parts(
            store_slug=self.slug, session_id=self.sid, cart_id=self.zid_b
        )
        self.rk_log_a = f"{self.slug}:log-a-{self.uid}"
        db.session.add(
            CartRecoveryLog(
                store_slug=self.slug,
                session_id=self.sid,
                cart_id=self.zid_a,
                recovery_key=self.rk_log_a,
                phone="966501000001",
                message="m",
                status="mock_sent",
                step=1,
            )
        )
        db.session.commit()

    def tearDown(self) -> None:
        from models import MerchantCartLifecycleArchive

        db.session.query(MerchantCartLifecycleArchive).filter(
            MerchantCartLifecycleArchive.store_slug == self.slug
        ).delete(synchronize_session=False)
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == self.slug
        ).delete(synchronize_session=False)
        db.session.query(AbandonedCart).filter(
            AbandonedCart.store_id == int(self.st.id)
        ).delete(synchronize_session=False)
        db.session.query(Store).filter(Store.id == int(self.st.id)).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_session_only_key_detected(self) -> None:
        self.assertTrue(
            is_session_only_recovery_key(
                self.rk_session, store_slug=self.slug, session_id=self.sid
            )
        )
        self.assertFalse(
            is_session_only_recovery_key(
                self.rk_a, store_slug=self.slug, session_id=self.sid
            )
        )

    def test_filter_mutation_keys_drops_session_only(self) -> None:
        keys = filter_mutation_recovery_keys(
            [self.rk_session, self.rk_a, self.rk_log_a],
            store_slug=self.slug,
            session_id=self.sid,
            cart_id=self.zid_a,
        )
        self.assertNotIn(self.rk_session, keys)
        self.assertIn(self.rk_a, keys)
        self.assertIn(self.rk_log_a, keys)

    def test_mutation_keys_for_abandoned_cart_excludes_session_only(self) -> None:
        keys = mutation_recovery_keys_for_abandoned_cart(
            self.ac_a,
            store_slug=self.slug,
            recovery_key=self.rk_log_a,
        )
        self.assertNotIn(self.rk_session, keys)
        self.assertTrue(keys)

    def test_archive_two_carts_same_session_only_first_archived(self) -> None:
        body = {
            "recovery_key": self.rk_log_a,
            "store_slug": self.slug,
            "abandoned_cart_id": int(self.ac_a.id),
            "session_id": self.sid,
            "cart_id": self.zid_a,
        }
        out = dashboard_cart_lifecycle_archive_from_body(body)
        self.assertTrue(out.get("ok"), out)
        self.assertNotIn(self.rk_session, out.get("recovery_keys") or [])

        self.assertTrue(is_merchant_archived(self.rk_log_a))
        self.assertTrue(is_merchant_archived(self.rk_a))
        self.assertFalse(is_merchant_archived(self.rk_session))
        self.assertFalse(is_merchant_archived(self.rk_b))

        keys_b = mutation_recovery_keys_for_abandoned_cart(
            self.ac_b, store_slug=self.slug, recovery_key=self.rk_b
        )
        archived_map = {
            self.rk_log_a: is_merchant_archived(self.rk_log_a),
            self.rk_b: is_merchant_archived(self.rk_b),
        }
        self.assertFalse(
            any_merchant_archived_for_mutation_keys(
                archived_map,
                keys_b,
                store_slug=self.slug,
                session_id=self.sid,
                cart_id=self.zid_b,
            )
        )

    def test_reopen_first_cart_does_not_reopen_second(self) -> None:
        dashboard_cart_lifecycle_archive_from_body(
            {
                "recovery_key": self.rk_log_a,
                "store_slug": self.slug,
                "abandoned_cart_id": int(self.ac_a.id),
                "session_id": self.sid,
                "cart_id": self.zid_a,
            }
        )
        archive_recovery_keys(
            recovery_keys=[self.rk_b],
            store_slug=self.slug,
            abandoned_cart_id=int(self.ac_b.id),
            session_id=self.sid,
            cart_id=self.zid_b,
        )
        self.assertTrue(is_merchant_archived(self.rk_b))

        reopen = dashboard_cart_lifecycle_reopen_from_body(
            {
                "recovery_key": self.rk_log_a,
                "store_slug": self.slug,
                "abandoned_cart_id": int(self.ac_a.id),
                "session_id": self.sid,
                "cart_id": self.zid_a,
            }
        )
        self.assertTrue(reopen.get("ok"), reopen)
        self.assertFalse(is_merchant_archived(self.rk_log_a))
        self.assertTrue(is_merchant_archived(self.rk_b))

    def test_archive_recovery_keys_rejects_session_only_list(self) -> None:
        out = archive_recovery_keys(
            recovery_keys=[self.rk_session],
            store_slug=self.slug,
            abandoned_cart_id=int(self.ac_a.id),
            session_id=self.sid,
            cart_id="",
        )
        self.assertFalse(out.get("ok"))
        self.assertFalse(is_merchant_archived(self.rk_session))

    def test_js_row_match_logic_documented_in_source(self) -> None:
        js = open("static/merchant_dashboard_lazy.js", encoding="utf-8").read()
        fn = js[js.index("function rowMatchesLifecycleKey") : js.index("function patchCartRowArchivedVisual")]
        self.assertNotIn("session_id", fn)
        self.assertIn("merchant_case_row_id", fn)


if __name__ == "__main__":
    unittest.main()
