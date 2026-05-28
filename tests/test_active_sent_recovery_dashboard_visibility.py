# -*- coding: utf-8 -*-
"""Active sent recoveries must remain on merchant normal-carts after sequence complete."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import (
    _api_json_dashboard_normal_carts,
    _normal_recovery_group_is_terminal_archived,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store
from services.customer_lifecycle_states_v1 import STATE_WAITING_CUSTOMER_REPLY


class ActiveSentRecoveryDashboardVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"vis-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_two_sent_without_skip_log_not_terminal_archived(self) -> None:
        st = Store(zid_store_id=f"vis2-{self._suffix}", recovery_attempts=2)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"cf_vis2_{self._suffix}",
            recovery_session_id=f"sess-vis2-{self._suffix}",
            customer_phone="966501118877",
            status="abandoned",
            vip_mode=False,
            cart_value=99.0,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        arch = _normal_recovery_group_is_terminal_archived(
            [ac],
            recovery_log_statuses=frozenset({"sent_real", "sent_real"}),
            phase_key="reminder_sent",
        )
        self.assertFalse(arch)

    def test_skipped_attempt_limit_not_terminal_archived_after_full_send(self) -> None:
        st = Store(zid_store_id=f"vis-{self._suffix}", recovery_attempts=2)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"cf_vis_{self._suffix}",
            recovery_session_id=f"sess-vis-{self._suffix}",
            customer_phone="966501119988",
            status="abandoned",
            vip_mode=False,
            cart_value=120.0,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        grp = [ac]
        arch = _normal_recovery_group_is_terminal_archived(
            grp,
            recovery_log_statuses=frozenset({"sent_real", "sent_real", "skipped_attempt_limit"}),
            phase_key="reminder_sent",
        )
        self.assertFalse(arch)

    def test_two_sent_without_skip_visible_on_normal_carts_sent_bucket(self) -> None:
        slug = f"vis-ns-{self._suffix}"
        sid = f"sess-vis-ns-{self._suffix}"
        zid = f"cf_vis_ns_{self._suffix}"
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        st = Store(
            zid_store_id=slug,
            recovery_attempts=2,
            recovery_delay=1,
            recovery_delay_unit="minutes",
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501116655",
            status="abandoned",
            vip_mode=False,
            cart_value=77.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        for step in (1, 2):
            db.session.add(
                CartRecoveryLog(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=zid,
                    phone="966501116655",
                    message=f"m{step}",
                    status="sent_real",
                    step=step,
                    recovery_key=rk,
                    sent_at=now,
                    created_at=now,
                )
            )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            body, _ = _api_json_dashboard_normal_carts(st)
        rows = body.get("merchant_carts_page_rows") or []
        match = next(
            (r for r in rows if str(r.get("recovery_key") or "").strip() == rk),
            None,
        )
        self.assertIsNotNone(match, msg=rows)
        self.assertEqual(match.get("merchant_cart_bucket"), "sent")
        self.assertNotEqual(match.get("customer_lifecycle_state"), "archived")

    def test_two_sent_plus_skip_visible_on_normal_carts_api(self) -> None:
        slug = f"vis-{self._suffix}"
        sid = f"sess-vis-api-{self._suffix}"
        zid = f"cf_vis_api_{self._suffix}"
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        st = Store(
            zid_store_id=slug,
            recovery_attempts=2,
            recovery_delay=1,
            recovery_delay_unit="minutes",
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501119977",
            status="abandoned",
            vip_mode=False,
            cart_value=88.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        for step, stt in ((1, "sent_real"), (2, "sent_real"), (3, "skipped_attempt_limit")):
            db.session.add(
                CartRecoveryLog(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=zid,
                    phone="966501119977",
                    message=f"m{step}",
                    status=stt,
                    step=step,
                    recovery_key=rk,
                    sent_at=now,
                    created_at=now,
                )
            )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            body, _ = _api_json_dashboard_normal_carts(st)
        rows = body.get("merchant_carts_page_rows") or []
        match = next(
            (r for r in rows if str(r.get("recovery_key") or "").strip() == rk),
            None,
        )
        self.assertIsNotNone(match, msg=rows)
        self.assertEqual(int(match.get("merchant_case_row_id") or 0), int(ac.id))
        self.assertEqual(match.get("merchant_cart_bucket"), "sent")

    def test_operational_truth_dashboard_bucket_sent_after_full_sequence(self) -> None:
        slug = f"vis-ot-{self._suffix}"
        sid = f"sess-vis-ot-{self._suffix}"
        zid = f"cf_vis_ot_{self._suffix}"
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        st = Store(
            zid_store_id=slug,
            recovery_attempts=2,
            recovery_delay=1,
            recovery_delay_unit="minutes",
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501115544",
            status="abandoned",
            vip_mode=False,
            cart_value=66.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        for step, stt in ((1, "sent_real"), (2, "sent_real"), (3, "skipped_attempt_limit")):
            db.session.add(
                CartRecoveryLog(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=zid,
                    phone="966501115544",
                    message=f"m{step}",
                    status=stt,
                    step=step,
                    recovery_key=rk,
                    sent_at=now,
                    created_at=now,
                )
            )
        db.session.commit()

        client = TestClient(app)
        with patch("main._dashboard_recovery_store_row", return_value=st):
            res = client.get(
                "/dev/recovery-operational-truth",
                params={"recovery_key": rk},
            )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("dashboard_visible"))
        self.assertIsNone(body.get("dashboard_exclusion_reason"))
        self.assertFalse(body.get("excluded_by_archive"))
        self.assertEqual(int(body.get("sent_count") or 0), 2)
        self.assertEqual(body.get("dashboard_bucket"), "sent")

        with patch("main._dashboard_recovery_store_row", return_value=st):
            dash_body, _ = _api_json_dashboard_normal_carts(st)
        row = next(
            (
                r
                for r in (dash_body.get("merchant_carts_page_rows") or [])
                if str(r.get("recovery_key") or "").strip() == rk
            ),
            None,
        )
        self.assertIsNotNone(row)
        self.assertEqual(
            row.get("customer_lifecycle_state"),
            STATE_WAITING_CUSTOMER_REPLY,
        )
        self.assertEqual(row.get("merchant_cart_bucket"), "sent")
        self.assertNotEqual(row.get("merchant_cart_primary_bucket"), "archived")

    def test_full_sequence_includes_followup_clarity_fields(self) -> None:
        slug = f"vis-cl-{self._suffix}"
        sid = f"sess-vis-cl-{self._suffix}"
        zid = f"cf_vis_cl_{self._suffix}"
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        st = Store(
            zid_store_id=slug,
            recovery_attempts=2,
            recovery_delay=1,
            recovery_delay_unit="minutes",
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501114433",
            status="abandoned",
            vip_mode=False,
            cart_value=55.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        for step, stt in ((1, "sent_real"), (2, "sent_real"), (3, "skipped_attempt_limit")):
            db.session.add(
                CartRecoveryLog(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=zid,
                    phone="966501114433",
                    message=f"m{step}",
                    status=stt,
                    step=step,
                    recovery_key=rk,
                    sent_at=now,
                    created_at=now,
                )
            )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            body, _ = _api_json_dashboard_normal_carts(st)
        row = next(
            (
                r
                for r in (body.get("merchant_carts_page_rows") or [])
                if str(r.get("recovery_key") or "").strip() == rk
            ),
            None,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.get("merchant_followup_progress_ar"), "تم إرسال ٢ من ٢")
        self.assertEqual(
            row.get("merchant_followup_sequence_line_ar"),
            "اكتملت سلسلة المتابعة — بانتظار تفاعل العميل",
        )


if __name__ == "__main__":
    unittest.main()
