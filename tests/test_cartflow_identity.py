# -*- coding: utf-8 -*-
"""Operational safeguards for store / session / cart identity (CartFlow)."""

from __future__ import annotations

import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from extensions import db
from fastapi.testclient import TestClient
from main import (
    _normal_recovery_identity_trust_surface,
    _normal_recovery_phase_steps_payload,
    _vip_dashboard_cart_alert_dict_from_group,
    app,
)
from models import AbandonedCart, Store
from services.behavioral_recovery.user_return import record_behavioral_user_return_from_payload
from services.cartflow_identity import (
    IDENTITY_TRUST_FAILED_KEY,
    MERCHANT_IDENTITY_TRUST_AR,
    detect_abandoned_cart_identity_anomaly,
    inferred_expected_store_pk_from_candidates,
    resolve_store_pk_for_event_slug,
    should_merge_behavioral_for_store,
)


class CartflowIdentityHelpersTests(unittest.TestCase):
    def test_should_merge_behavioral_rejects_store_mismatch_when_expected_set(self) -> None:
        ac = SimpleNamespace(store_id=5)
        ok, rsn = should_merge_behavioral_for_store(
            ac, expected_store_pk=9, inferred_only=False
        )
        self.assertFalse(ok)
        self.assertIn("store_mismatch", rsn)

    def test_should_merge_behavioral_allows_null_store_on_row(self) -> None:
        ac = SimpleNamespace(store_id=None)
        ok, rsn = should_merge_behavioral_for_store(
            ac, expected_store_pk=9, inferred_only=False
        )
        self.assertTrue(ok)
        self.assertEqual(rsn, "")

    def test_inferred_pk_ambiguous_when_two_stores(self) -> None:
        a = SimpleNamespace(vip_mode=False, store_id=1)
        b = SimpleNamespace(vip_mode=False, store_id=2)
        pk, tag = inferred_expected_store_pk_from_candidates([a, b])
        self.assertIsNone(pk)
        self.assertEqual(tag, "ambiguous_multi_store_cart_rows")

    def test_resolve_store_pk_matches_snapshot_with_same_stub(self) -> None:
        stub = SimpleNamespace(id=42, zid_store_id="zdemo")
        with patch("main._load_store_row_for_recovery", return_value=stub):
            from services.cartflow_identity import identity_snapshot_from_payload

            self.assertEqual(resolve_store_pk_for_event_slug("any-slug"), 42)
            snap = identity_snapshot_from_payload(
                {"store": "any-slug", "session_id": "s1", "cart_id": "c1"}
            )
            self.assertEqual(snap.store_pk, 42)


class CartflowIdentityDbTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

    def tearDown(self) -> None:
        try:
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_detect_multi_store_session_scope(self) -> None:
        s1 = Store(
            zid_store_id=f"id_st_1_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        s2 = Store(
            zid_store_id=f"id_st_2_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add_all([s1, s2])
        db.session.flush()
        sid = f"id_sess_{self._suffix}"
        ac_a = AbandonedCart(
            store_id=int(s1.id),
            zid_cart_id=f"cid_id_a_{self._suffix}",
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=10.0,
        )
        ac_b = AbandonedCart(
            store_id=int(s2.id),
            zid_cart_id=f"cid_id_b_{self._suffix}",
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=11.0,
        )
        db.session.add_all([ac_a, ac_b])
        db.session.commit()
        bad, rsn = detect_abandoned_cart_identity_anomaly(sid, ac_a.zid_cart_id)
        self.assertTrue(bad)
        self.assertIn("multi_store", rsn)

    def test_dashboard_payload_surfaces_merchant_safe_trust_copy(self) -> None:
        s = Store(
            zid_store_id=f"id_st_d_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(s)
        db.session.flush()
        sid = f"id_sess_d_{self._suffix}"
        raw = {
            "cf_behavioral": {
                IDENTITY_TRUST_FAILED_KEY: True,
            }
        }
        ac = AbandonedCart(
            store_id=int(s.id),
            zid_cart_id=f"cid_id_d_{self._suffix}",
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=10.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        msg = _normal_recovery_identity_trust_surface(ac)
        self.assertEqual(msg, MERCHANT_IDENTITY_TRUST_AR)
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(
            payload.get("normal_recovery_identity_trust_ar"),
            MERCHANT_IDENTITY_TRUST_AR,
        )

    def test_normal_card_dict_includes_trust_key(self) -> None:
        s = Store(
            zid_store_id=f"id_st_e_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(s)
        db.session.flush()
        raw = {"cf_behavioral": {IDENTITY_TRUST_FAILED_KEY: True}}
        ac = AbandonedCart(
            store_id=int(s.id),
            zid_cart_id=f"cid_id_e_{self._suffix}",
            recovery_session_id=f"id_sess_e_{self._suffix}",
            status="abandoned",
            vip_mode=False,
            cart_value=9.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        card = _vip_dashboard_cart_alert_dict_from_group(
            [ac], s, recovery_card_tier="normal"
        )
        self.assertEqual(
            card.get("normal_recovery_identity_trust_ar"),
            MERCHANT_IDENTITY_TRUST_AR,
        )

    @patch("services.behavioral_recovery.user_return.resolve_store_pk_for_event_slug")
    def test_return_to_site_skips_merge_and_marks_trust_on_store_mismatch(
        self, mock_pk: MagicMock
    ) -> None:
        s_event = Store(
            zid_store_id=f"id_st_rt_1_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        s_row = Store(
            zid_store_id=f"id_st_rt_2_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add_all([s_event, s_row])
        db.session.flush()
        mock_pk.return_value = int(s_event.id)
        sid = f"id_sess_rt_{self._suffix}"
        cid = f"cid_id_rt_{self._suffix}"
        ac = AbandonedCart(
            store_id=int(s_row.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=7.0,
            raw_payload=json.dumps({}, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        record_behavioral_user_return_from_payload(
            {
                "user_returned_to_site": True,
                "active_commercial_reengagement": True,
                "return_visit_kind": "active_commercial_reengagement",
                "returned_checkout_page": True,
                "session_id": sid,
                "cart_id": cid,
                "store": "demo",
            }
        )
        db.session.refresh(ac)
        bh = json.loads(ac.raw_payload or "{}").get("cf_behavioral") or {}
        self.assertTrue(bh.get(IDENTITY_TRUST_FAILED_KEY))
        self.assertNotIn("user_returned_to_site", bh)

    @patch("services.behavioral_recovery.user_return.resolve_store_pk_for_event_slug")
    def test_return_to_site_merges_when_store_matches(
        self, mock_pk: MagicMock
    ) -> None:
        s = Store(
            zid_store_id=f"id_st_ok_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(s)
        db.session.flush()
        mock_pk.return_value = int(s.id)
        sid = f"id_sess_ok_{self._suffix}"
        cid = f"cid_id_ok_{self._suffix}"
        ac = AbandonedCart(
            store_id=int(s.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=7.0,
            raw_payload=json.dumps({}, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        record_behavioral_user_return_from_payload(
            {
                "user_returned_to_site": True,
                "active_commercial_reengagement": True,
                "return_visit_kind": "active_commercial_reengagement",
                "returned_checkout_page": True,
                "session_id": sid,
                "cart_id": cid,
                "store": "demo",
            }
        )
        db.session.refresh(ac)
        bh = json.loads(ac.raw_payload or "{}").get("cf_behavioral") or {}
        self.assertTrue(bh.get("user_returned_to_site"))
        self.assertFalse(bh.get(IDENTITY_TRUST_FAILED_KEY))

    def test_normal_carts_dashboard_html_shows_identity_trust_banner(self) -> None:
        """Merchant-safe copy and marker must appear on normal carts dashboard HTML."""
        s1 = Store(
            zid_store_id=f"id_st_h1_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        s2 = Store(
            zid_store_id=f"id_st_h2_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add_all([s1, s2])
        db.session.flush()
        raw = {"cf_behavioral": {IDENTITY_TRUST_FAILED_KEY: True}}
        ac = AbandonedCart(
            store_id=int(s2.id),
            zid_cart_id=f"cid_id_h_{self._suffix}",
            recovery_session_id=f"id_sess_h_{self._suffix}",
            status="abandoned",
            vip_mode=False,
            cart_value=12.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        client = TestClient(app)
        r = client.get("/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, (r.text or "")[:1200])
        html = r.text or ""
        self.assertIn("data-normal-recovery-identity-trust", html)
        self.assertIn(MERCHANT_IDENTITY_TRUST_AR, html)


if __name__ == "__main__":
    unittest.main()
