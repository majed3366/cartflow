# -*- coding: utf-8 -*-
"""
Cart ID truth audit — documents current stability classification (no behavior changes).

See docs/cartflow_cart_id_truth_audit.md
"""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from models import AbandonedCart, Store
from services.journey_identity_resolver_v1 import (
    has_stable_cart_id,
    is_synthetic_cart_id,
    resolve_journey_identity_shadow,
)


class CartIdStabilityClassificationTests(unittest.TestCase):
    """Mirror production rules in journey_identity_resolver_v1."""

    def test_cf_cart_browser_id_is_stable_for_jid(self) -> None:
        cid = f"cf_cart_{uuid.uuid4()}"
        self.assertFalse(is_synthetic_cart_id(cid))
        self.assertTrue(has_stable_cart_id(cid))

    def test_cf_w_server_synthetic_not_stable(self) -> None:
        self.assertTrue(is_synthetic_cart_id("cf_w_abc123deadbeef"))
        self.assertFalse(has_stable_cart_id("cf_w_abc123deadbeef"))

    def test_fp_fingerprint_not_stable(self) -> None:
        self.assertTrue(is_synthetic_cart_id("fp:deadbeef0123456789"))
        self.assertFalse(has_stable_cart_id("fp:deadbeef0123456789"))

    def test_platform_zid_style_stable(self) -> None:
        self.assertTrue(has_stable_cart_id("zid-platform-cart-99881"))

    def test_demo_integration_cart_stable(self) -> None:
        self.assertTrue(has_stable_cart_id("s_integration_demo_cart"))


class CartIdProducerBehaviorTests(unittest.TestCase):
    def test_server_synthetic_derived_from_recovery_key(self) -> None:
        from main import (
            _ensure_cart_abandon_payload_has_cart_id,
            _recovery_key_from_payload,
            _synthetic_zid_cart_id_from_recovery_key,
        )

        payload = {"store": "demo", "session_id": "s_prod_audit_1"}
        rk = _recovery_key_from_payload(payload)
        syn = _synthetic_zid_cart_id_from_recovery_key(rk)
        self.assertTrue(syn.startswith("cf_w_"))
        filled = _ensure_cart_abandon_payload_has_cart_id(payload, rk)
        self.assertEqual(filled.get("cart_id"), syn)
        # Deterministic for same recovery_key
        self.assertEqual(
            _synthetic_zid_cart_id_from_recovery_key(rk),
            _synthetic_zid_cart_id_from_recovery_key(rk),
        )

    def test_session_plus_browser_cart_mismatch_in_shadow(self) -> None:
        payload = {
            "store": "demo",
            "session_id": "s_mismatch_1",
            "cart_id": f"cf_cart_{uuid.uuid4()}",
        }
        r = resolve_journey_identity_shadow(payload)
        self.assertNotEqual(r.current_rk, r.recommended_rk)
        self.assertEqual(r.current_rk, r.bid_rk)
        self.assertEqual(r.recommended_rk, r.jid_rk)

    def test_normalize_zid_cart_fields_nested_paths(self) -> None:
        from main import normalize_zid_cart_fields

        nested = {
            "data": {
                "cart": {"id": "zid-nested-42"},
                "customer": {"name": "A", "phone": "966500000001"},
                "total": 99.0,
            }
        }
        fields = normalize_zid_cart_fields(nested)
        self.assertEqual(fields["zid_cart_id"], "zid-nested-42")

    def test_zid_webhook_maps_cart_id_into_session_when_missing(self) -> None:
        from services.zid_webhook_purchase_v2 import build_zid_purchase_truth_payload

        out = build_zid_purchase_truth_payload(
            {
                "event": "order.paid",
                "store_slug": "merchant-1",
                "zid_cart_id": "platform-cart-77",
                "order_status": "paid",
            }
        )
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.get("session_id"), "platform-cart-77")
        self.assertEqual(out.get("zid_cart_id"), "platform-cart-77")


class CartIdSyntheticUpgradeDbTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_upgrade_cf_w_to_real_platform_id(self) -> None:
        from main import _abandoned_cart_try_upgrade_synthetic_zid

        st = Store(
            zid_store_id=f"st_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        syn = f"cf_w_{self._suffix}"
        real = f"platform_{self._suffix}"
        row = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=syn,
            recovery_session_id=f"s_{self._suffix}",
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(row)
        db.session.commit()
        _abandoned_cart_try_upgrade_synthetic_zid(row, real)
        db.session.commit()
        db.session.refresh(row)
        self.assertEqual(row.zid_cart_id, real)

    def test_upgrade_refuses_second_real_id_collision(self) -> None:
        from main import _abandoned_cart_try_upgrade_synthetic_zid

        st = Store(
            zid_store_id=f"st2_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        real = f"taken_{self._suffix}"
        other = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=real,
            recovery_session_id=f"s_other_{self._suffix}",
            status="abandoned",
            vip_mode=False,
        )
        syn_row = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"cf_w_{self._suffix}",
            recovery_session_id=f"s_syn_{self._suffix}",
            status="abandoned",
            vip_mode=False,
        )
        db.session.add_all([other, syn_row])
        db.session.commit()
        _abandoned_cart_try_upgrade_synthetic_zid(syn_row, real)
        db.session.commit()
        db.session.refresh(syn_row)
        self.assertEqual(syn_row.zid_cart_id, f"cf_w_{self._suffix}")


if __name__ == "__main__":
    unittest.main()
