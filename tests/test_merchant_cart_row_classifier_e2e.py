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
    _api_json_dashboard_summary,
    _normal_carts_dashboard_stats,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store  # noqa: E402
from schema_recovery_message_context import ensure_recovery_message_context_schema  # noqa: E402
from services.merchant_cart_row_classifier import (  # noqa: E402
    CUSTOMER_ENGAGED_CONTINUATION_LABEL_AR,
    CUSTOMER_REPLY_LABEL_AR,
    PRIMARY_CUSTOMER_ENGAGED,
    PRIMARY_CUSTOMER_REPLY,
    PRIMARY_NEEDS_FOLLOWUP,
    PRIMARY_NO_PHONE,
    PRIMARY_RECOVERED,
    PRIMARY_RETURN_TO_SITE,
    PRIMARY_SENT,
    PRIMARY_WAITING,
    RETURN_TO_SITE_LABEL_AR,
    SENT_STATUS_LABEL_AR,
    UI_FILTER_ALL,
    UI_FILTER_ATTENTION,
    UI_FILTER_NOPHONE,
    UI_FILTER_RECOVERED,
    UI_FILTER_SENT,
    UI_FILTER_WAITING,
    cart_tab_to_filter_mode,
    classify_merchant_cart_row,
    merchant_cart_filter_counts_from_rows,
    merchant_cart_row_matches_filter,
    merchant_cart_rows_matching_filter,
    merchant_nav_badge_waiting_count,
)
from services.customer_lifecycle_states_v1 import (  # noqa: E402
    LABEL_AR,
    STATE_ARCHIVED,
    STATE_WAITING_CUSTOMER_REPLY,
)
from services.recovery_truth_timeline_v1 import (  # noqa: E402
    STATUS_CONTINUATION_STARTED,
    STATUS_CUSTOMER_REPLY,
    STATUS_PROVIDER_SENT,
    record_recovery_truth_event,
)
from schema_recovery_truth_timeline import (  # noqa: E402
    ensure_recovery_truth_timeline_schema,
    reset_recovery_truth_timeline_schema_guard_for_tests,
)


def _tabs_for_bucket(rows: list[dict], bucket: str) -> list[dict]:
    return [r for r in rows if bucket in (r.get("merchant_cart_visible_tabs") or [])]


class MerchantCartRowClassifierUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()

    def setUp(self) -> None:
        db.create_all()
        ensure_recovery_truth_timeline_schema(db)

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

    def test_c_sent_with_customer_reply_uses_customer_reply_bucket(self) -> None:
        rk = f"demo:cl-reply-{uuid.uuid4().hex[:8]}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            phase_key="first_message_sent",
            recovery_key=rk,
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_CUSTOMER_REPLY)
        self.assertEqual(cl.merchant_status_label_ar, CUSTOMER_REPLY_LABEL_AR)
        self.assertIn(UI_FILTER_ATTENTION, cl.visible_tabs)

    def test_return_to_site_not_customer_engaged_bucket(self) -> None:
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent", "returned_to_site"}),
            coarse="returned",
            phase_key="customer_returned",
            behavioral={"customer_returned_to_site": True},
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_RETURN_TO_SITE)
        self.assertEqual(cl.merchant_status_label_ar, RETURN_TO_SITE_LABEL_AR)
        self.assertIn(UI_FILTER_SENT, cl.visible_tabs)
        self.assertNotIn("تفاعل العميل", cl.merchant_status_label_ar)

    def test_timeline_reply_and_continuation_aligns_all_tab_label(self) -> None:
        rk = f"demo:tl-class-{uuid.uuid4().hex[:8]}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CONTINUATION_STARTED,
            source="test",
            store_slug="demo",
        )
        cl = classify_merchant_cart_row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            recovery_key=rk,
        )
        self.assertEqual(cl.primary_bucket, PRIMARY_CUSTOMER_ENGAGED)
        self.assertEqual(cl.merchant_status_label_ar, CUSTOMER_ENGAGED_CONTINUATION_LABEL_AR)
        self.assertIn(UI_FILTER_ATTENTION, cl.visible_tabs)
        self.assertNotIn(UI_FILTER_SENT, cl.visible_tabs)

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


class MerchantCartTabFilterE2ETests(unittest.TestCase):
    """Tab URL modes must show only rows matching classifier buckets (same as counts)."""

    def _row(self, **kwargs) -> dict:
        cl = classify_merchant_cart_row(**kwargs)
        return cl.to_payload_fields()

    def test_tab_waiting_sent_attention_only_matching_rows(self) -> None:
        waiting = self._row(
            has_phone=True,
            sent_count=0,
            log_statuses=frozenset(),
            coarse="pending",
            phase_key="pending_send",
        )
        sent = self._row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            phase_key="first_message_sent",
        )
        followup = self._row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent", "whatsapp_failed"}),
            coarse="blocked",
            phase_key="pending_send",
        )
        rows = [waiting, sent, followup]

        self.assertEqual(waiting["merchant_cart_primary_bucket"], PRIMARY_WAITING)
        self.assertEqual(sent["merchant_cart_primary_bucket"], PRIMARY_SENT)
        self.assertEqual(followup["merchant_cart_primary_bucket"], PRIMARY_NEEDS_FOLLOWUP)

        w_mode = cart_tab_to_filter_mode("waiting")
        s_mode = cart_tab_to_filter_mode("sent")
        a_mode = cart_tab_to_filter_mode("attention")

        self.assertEqual(w_mode, UI_FILTER_WAITING)
        self.assertEqual(s_mode, UI_FILTER_SENT)
        self.assertEqual(a_mode, UI_FILTER_ATTENTION)

        w_visible = merchant_cart_rows_matching_filter(rows, w_mode)
        s_visible = merchant_cart_rows_matching_filter(rows, s_mode)
        a_visible = merchant_cart_rows_matching_filter(rows, a_mode)

        self.assertEqual(len(w_visible), 1)
        self.assertEqual(w_visible[0]["merchant_cart_primary_bucket"], PRIMARY_WAITING)
        self.assertFalse(merchant_cart_row_matches_filter(sent, w_mode))
        self.assertFalse(merchant_cart_row_matches_filter(followup, w_mode))

        self.assertEqual(len(s_visible), 1)
        self.assertEqual(s_visible[0]["merchant_cart_primary_bucket"], PRIMARY_SENT)
        self.assertFalse(merchant_cart_row_matches_filter(waiting, s_mode))

        self.assertEqual(len(a_visible), 1)
        self.assertEqual(
            a_visible[0]["merchant_cart_primary_bucket"], PRIMARY_NEEDS_FOLLOWUP
        )
        self.assertFalse(merchant_cart_row_matches_filter(waiting, a_mode))
        self.assertFalse(merchant_cart_row_matches_filter(sent, a_mode))

        fc = merchant_cart_filter_counts_from_rows(rows)
        self.assertEqual(len(merchant_cart_rows_matching_filter(rows, w_mode)), fc[w_mode])
        self.assertEqual(len(merchant_cart_rows_matching_filter(rows, s_mode)), fc[s_mode])
        self.assertEqual(len(merchant_cart_rows_matching_filter(rows, a_mode)), fc[a_mode])
        self.assertEqual(merchant_nav_badge_waiting_count(rows), fc[w_mode])
        self.assertEqual(merchant_nav_badge_waiting_count(rows), len(w_visible))

    def test_customer_engaged_row_in_attention_tab(self) -> None:
        rk = f"demo:cl-eng-{uuid.uuid4().hex[:8]}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CONTINUATION_STARTED,
            source="test",
            store_slug="demo",
        )
        engaged = self._row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            recovery_key=rk,
        )
        self.assertEqual(engaged["merchant_cart_primary_bucket"], PRIMARY_CUSTOMER_ENGAGED)
        self.assertTrue(
            merchant_cart_row_matches_filter(engaged, cart_tab_to_filter_mode("attention"))
        )
        self.assertFalse(
            merchant_cart_row_matches_filter(engaged, cart_tab_to_filter_mode("sent"))
        )

    def test_sidebar_intervention_maps_to_attention_filter(self) -> None:
        row = self._row(
            has_phone=True,
            sent_count=1,
            log_statuses=frozenset({"whatsapp_failed"}),
            coarse="blocked",
        )
        self.assertTrue(
            merchant_cart_row_matches_filter(row, cart_tab_to_filter_mode("intervention"))
        )
        self.assertFalse(
            merchant_cart_row_matches_filter(row, cart_tab_to_filter_mode("waiting"))
        )


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
        lbl = row.get("merchant_status_label_ar") or ""
        lc_state = row.get("customer_lifecycle_state") or ""
        self.assertIn(
            lc_state,
            (STATE_WAITING_CUSTOMER_REPLY, STATE_ARCHIVED),
        )
        if lc_state == STATE_WAITING_CUSTOMER_REPLY:
            self.assertEqual(lbl, LABEL_AR[STATE_WAITING_CUSTOMER_REPLY])
        else:
            self.assertEqual(lbl, LABEL_AR[STATE_ARCHIVED])
        self.assertNotIn("جارٍ المتابعة", lbl)

        self.assertGreaterEqual(int(fc.get(UI_FILTER_SENT) or 0), 1)
        self._assert_tab_counts_match_rows(rows, fc)

        self.assertGreaterEqual(int(stats.get("normal_cart_count") or 0), 1)
        self.assertEqual(int(stats.get("normal_cart_count") or 0), len(rows))
        self.assertEqual(int(stats.get("merchant_nav_badge_waiting") or 0), 0)
        self.assertEqual(int(fc.get(UI_FILTER_WAITING) or 0), 0)
        self.assertGreaterEqual(len(msgs.get("merchant_message_history_rows") or []), 1)

        with patch("main._dashboard_recovery_store_row", return_value=st):
            summary = _api_json_dashboard_summary(st)
        self.assertEqual(int(summary.get("merchant_nav_badge_abandoned") or 0), 0)


if __name__ == "__main__":
    unittest.main()
