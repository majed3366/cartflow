# -*- coding: utf-8 -*-
"""E2E: centralized merchant cart tab classification (rows, counts, badge)."""
from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

import models  # noqa: F401

from extensions import db

from main import (  # noqa: E402
    _api_json_dashboard_messages,
    _normal_carts_dashboard_stats,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store  # noqa: E402
from schema_recovery_message_context import ensure_recovery_message_context_schema  # noqa: E402
from services.merchant_cart_row_classifier import (  # noqa: E402
    PRIMARY_NEEDS_FOLLOWUP,
    PRIMARY_NO_PHONE,
    PRIMARY_RECOVERED,
    PRIMARY_SENT,
    PRIMARY_WAITING,
    SENT_STATUS_LABEL_AR,
    UI_FILTER_ALL,
    UI_FILTER_ATTENTION,
    UI_FILTER_NOPHONE,
    UI_FILTER_RECOVERED,
    UI_FILTER_SENT,
    UI_FILTER_WAITING,
    classify_merchant_cart_row,
    merchant_cart_filter_counts_from_rows,
)


def _tabs_for_bucket(rows: list[dict], bucket: str) -> list[dict]:
    return [r for r in rows if bucket in (r.get("merchant_cart_visible_tabs") or [])]


class MerchantCartRowClassifierUnitTests(unittest.TestCase):
    def test_a_waiting_only_in_waiting_tab(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=0,
            log_statuses=frozenset(),
            coarse="pending",
            phase_key="pending_send",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_WAITING)
        self.assertEqual(cl.visible_tabs, (UI_FILTER_ALL, UI_FILTER_WAITING))
        self.assertNotIn(UI_FILTER_SENT, cl.visible_tabs)

    def test_b_sent_in_all_and_sent_with_label(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            phase_key="first_message_sent",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_SENT)
        self.assertEqual(cl.merchant_status_label_ar, SENT_STATUS_LABEL_AR)
        self.assertIn(UI_FILTER_SENT, cl.visible_tabs)
        self.assertIn(UI_FILTER_ALL, cl.visible_tabs)

    def test_c_sent_with_customer_reply_not_needs_followup(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="replied",
            phase_key="behavioral_replied",
            behavioral={"customer_replied": True},
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_SENT)
        self.assertNotEqual(cl.primary_bucket, PRIMARY_NEEDS_FOLLOWUP)

    def test_d_reply_needing_action_in_needs_followup(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent", "whatsapp_failed"}),
            coarse="blocked",
            phase_key="pending_send",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_NEEDS_FOLLOWUP)
        self.assertIn(UI_FILTER_ATTENTION, cl.visible_tabs)

    def test_e_purchased_in_recovered(self) -> None:
        cl = classify_merchant_cart_row(
            purchase_truth=True,
            cart_status="recovered",
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent", "stopped_converted"}),
            coarse="converted",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_RECOVERED)
        self.assertIn(UI_FILTER_RECOVERED, cl.visible_tabs)
        self.assertTrue(cl.is_terminal)

    def test_f_counts_equal_visible_tab_rows(self) -> None:
        rows = [
            {
                "merchant_cart_visible_tabs": [UI_FILTER_ALL, UI_FILTER_SENT],
            },
            {
                "merchant_cart_visible_tabs": [UI_FILTER_ALL, UI_FILTER_WAITING],
            },
            {
                "merchant_cart_visible_tabs": [UI_FILTER_ALL, UI_FILTER_ATTENTION],
            },
        ]
        fc = merchant_cart_filter_counts_from_rows(rows)
        self.assertEqual(fc[UI_FILTER_ALL], 3)
        self.assertEqual(fc[UI_FILTER_SENT], len(_tabs_for_bucket(rows, UI_FILTER_SENT)))
        self.assertEqual(fc[UI_FILTER_WAITING], len(_tabs_for_bucket(rows, UI_FILTER_WAITING)))
        self.assertEqual(
            fc[UI_FILTER_ATTENTION], len(_tabs_for_bucket(rows, UI_FILTER_ATTENTION))
        )

    def test_g_old_sent_log_classifies_sent(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=0,
            log_statuses=frozenset({"mock_sent"}),
            coarse="pending",
            latest_log_status="mock_sent",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_SENT)

    def test_no_phone_before_send(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=False,
            sent_count=0,
            log_statuses=frozenset(),
            coarse="pending",
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_NO_PHONE)
        self.assertIn(UI_FILTER_NOPHONE, cl.visible_tabs)


class MerchantCartRowClassifierApiE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_recovery_message_context_schema(db)

    def setUp(self) -> None:
        db.create_all()
        ensure_recovery_message_context_schema(db)
        self._suffix = uuid.uuid4().hex[:10]
        self._client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"mshop-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _seed_store(self) -> Store:
        st = Store(
            zid_store_id=f"mshop-{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            cartflow_widget_enabled=True,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(st)
        db.session.flush()
        return st

    def _assert_tab_counts_match_rows(self, rows: list[dict], fc: dict) -> None:
        self.assertEqual(int(fc.get(UI_FILTER_ALL) or 0), len(rows))
        for tab in (UI_FILTER_SENT, UI_FILTER_ATTENTION, UI_FILTER_RECOVERED, UI_FILTER_NOPHONE, UI_FILTER_WAITING):
            self.assertEqual(
                int(fc.get(tab) or 0),
                len(_tabs_for_bucket(rows, tab)),
                msg=f"tab={tab}",
            )

    def test_api_sent_cart_tab_and_badge_aligned(self) -> None:
        st = self._seed_store()
        sid = f"sess-{self._suffix}"
        zid = f"cf_cart_{self._suffix}"
        now = datetime.now(timezone.utc)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501112233",
            status="abandoned",
            vip_mode=False,
            cart_value=199.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone="966501112233",
                message="مرحباً",
                status="mock_sent",
                step=1,
                sent_at=now,
                created_at=now,
            )
        )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
                50,
                0,
                nr_session=sid,
                lifecycle="active",
                dash_store=st,
            )
            msgs = _api_json_dashboard_messages(st)
            stats = _normal_carts_dashboard_stats(st)

        fc = merchant_cart_filter_counts_from_rows(rows)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.get("merchant_cart_primary_bucket"), PRIMARY_SENT)
        self.assertEqual(row.get("merchant_cart_bucket"), UI_FILTER_SENT)
        self.assertIn(SENT_STATUS_LABEL_AR, row.get("merchant_status_label_ar") or "")
        self.assertNotIn("جارٍ المتابعة", row.get("merchant_status_label_ar") or "")

        self.assertGreaterEqual(int(fc.get(UI_FILTER_SENT) or 0), 1)
        self._assert_tab_counts_match_rows(rows, fc)

        self.assertGreaterEqual(int(stats.get("normal_cart_count") or 0), 1)
        self.assertEqual(int(stats.get("normal_cart_count") or 0), len(rows))
        self.assertGreaterEqual(len(msgs.get("merchant_message_history_rows") or []), 1)


if __name__ == "__main__":
    unittest.main()
