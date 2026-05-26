# -*- coding: utf-8 -*-
"""
Merchant-visible E2E: sent recovery message must appear on Messages and Carts APIs.

Reproduces: messages show sent rows while normal-carts returns 0 rows / mismatched counts.
"""
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
    _NORMAL_RECOVERY_SENT_LOG_STATUSES,
    _api_json_dashboard_messages,
    _api_json_dashboard_normal_carts,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
    _normal_carts_dashboard_stats,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store  # noqa: E402
from schema_recovery_message_context import (  # noqa: E402
    ensure_recovery_message_context_schema,
)
from services.recovery_message_context_v1 import (  # noqa: E402
    CONTEXT_OK,
    build_recovery_message_context,
    serialize_context_json,
)


class MerchantSentRecoveryCartsVisibleE2ETests(unittest.TestCase):
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

    def _seed_sent_recovery_cart(
        self,
        *,
        last_seen_at: datetime | None = None,
    ) -> tuple[Store, AbandonedCart, CartRecoveryLog]:
        slug = f"mshop-{self._suffix}"
        sid = f"sess-{self._suffix}"
        zid = f"cf_cart_{self._suffix}"
        now = datetime.now(timezone.utc)
        seen = last_seen_at or now
        st = Store(
            zid_store_id=slug,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            cartflow_widget_enabled=True,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501112233",
            status="abandoned",
            vip_mode=False,
            cart_value=199.0,
            last_seen_at=seen,
        )
        db.session.add(ac)
        db.session.flush()
        ctx = build_recovery_message_context(
            recovery_key=f"{slug}:{sid}",
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            customer_phone="966501112233",
            reason_tag="price",
            message_body="مرحباً — سلة بقيمة 199",
            message_type="reason_template",
            attempt=1,
            send_status="mock_sent",
            sent_at=now,
            source="e2e_test",
            store=st,
            abandoned_cart=ac,
        )
        self.assertEqual(ctx.context_status, CONTEXT_OK)
        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            phone="966501112233",
            message=ctx.message_body,
            status="mock_sent",
            step=1,
            recovery_key=ctx.recovery_key,
            reason_tag="price",
            context_status=ctx.context_status,
            context_json=serialize_context_json(ctx),
            message_type=ctx.message_type,
            source=ctx.source,
            sent_at=now,
            created_at=now,
        )
        db.session.add(lg)
        db.session.commit()
        return st, ac, lg

    def _assert_cart_visible_in_normal_carts_api(self, st: Store) -> dict:
        with patch("main._dashboard_recovery_store_row", return_value=st):
            body, _prof = _api_json_dashboard_normal_carts(st)
        rows = body.get("merchant_carts_page_rows") or []
        fc = body.get("merchant_cart_filter_counts") or {}
        self.assertGreaterEqual(
            len(rows),
            1,
            msg=f"merchant_carts_page_rows empty; prof={_prof}",
        )
        cart_buckets = [str(r.get("merchant_cart_bucket") or "") for r in rows]
        self.assertTrue(
            any(b == "sent" for b in cart_buckets),
            msg=f"expected sent bucket; buckets={cart_buckets}",
        )
        self.assertGreaterEqual(int(fc.get("all") or 0), 1, msg=f"filter all=0 fc={fc}")
        self.assertGreaterEqual(
            int(fc.get("sent") or 0),
            1,
            msg=f"filter sent=0 fc={fc}",
        )
        sent_rows = [r for r in rows if r.get("merchant_cart_bucket") == "sent"]
        self.assertGreaterEqual(len(sent_rows), 1)
        self.assertEqual(int(fc.get("sent")), len(sent_rows))
        for sr in sent_rows:
            self.assertIn(
                "بانتظار تفاعل العميل",
                sr.get("merchant_status_label_ar") or "",
            )
        return body

    def test_sent_recovery_visible_on_messages_and_carts_apis(self) -> None:
        st, ac, _lg = self._seed_sent_recovery_cart()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            msgs = _api_json_dashboard_messages(st)
            stats = _normal_carts_dashboard_stats(st)

        hist = msgs.get("merchant_message_history_rows") or []
        self.assertGreaterEqual(len(hist), 1)
        self.assertTrue(
            any("تم الإرسال" in (h.get("status_ar") or "") for h in hist)
        )

        body = self._assert_cart_visible_in_normal_carts_api(st)

        with patch("main._dashboard_recovery_store_row", return_value=st):
            stats2 = _normal_carts_dashboard_stats(st)
        page_rows = body.get("merchant_carts_page_rows") or []
        self.assertGreaterEqual(int(stats2.get("normal_cart_count") or 0), 1)
        self.assertGreaterEqual(
            int(stats2.get("normal_cart_count") or 0),
            len(page_rows),
        )
        row_ids = {int(r.get("merchant_case_row_id") or 0) for r in page_rows}
        self.assertIn(int(ac.id), row_ids)

    def test_sent_cart_outside_last_seen_cap_still_on_carts_api(self) -> None:
        """Sent log exists but cart is older than newest-N abandoned rows (merchant bug)."""
        st, target_ac, lg = self._seed_sent_recovery_cart(
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        now = datetime.now(timezone.utc)
        slug = st.zid_store_id
        for i in range(100):
            db.session.add(
                AbandonedCart(
                    store_id=int(st.id),
                    zid_cart_id=f"cf_cart_filler_{self._suffix}_{i}",
                    recovery_session_id=f"sess-filler-{self._suffix}-{i}",
                    status="abandoned",
                    vip_mode=False,
                    cart_value=10.0 + i,
                    last_seen_at=now - timedelta(minutes=i),
                )
            )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            msgs = _api_json_dashboard_messages(st)
        self.assertGreaterEqual(
            len(msgs.get("merchant_message_history_rows") or []),
            1,
        )

        body = self._assert_cart_visible_in_normal_carts_api(st)
        row_ids = {
            int(r.get("merchant_case_row_id") or 0)
            for r in body.get("merchant_carts_page_rows") or []
        }
        self.assertIn(int(target_ac.id), row_ids)

    def test_stale_sent_cart_stays_on_active_carts_tab(self) -> None:
        from unittest.mock import patch as mock_patch

        st, _ac, _lg = self._seed_sent_recovery_cart(
            last_seen_at=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        tiny = {
            "active_sent_window_minutes": 1,
            "active_pending_window_minutes": 1,
            "stale_archive_enabled": True,
        }
        with mock_patch(
            "services.normal_recovery_merchant_stale.normal_recovery_merchant_stale_config",
            return_value=tiny,
        ):
            self._assert_cart_visible_in_normal_carts_api(st)

    def _active_and_archived_rows(
        self, st: Store, *, session_id: str
    ) -> tuple[list[dict], list[dict]]:
        with patch("main._dashboard_recovery_store_row", return_value=st):
            active, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
                50,
                0,
                nr_session=session_id,
                lifecycle="active",
                dash_store=st,
            )
            archived, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
                50,
                0,
                nr_session=session_id,
                lifecycle="archived",
                dash_store=st,
            )
        return list(active), list(archived)

    def test_sent_lifecycle_active_until_terminal_purchase(self) -> None:
        """After send cart stays on active Carts; archives only after purchase terminal."""
        st, ac, _lg = self._seed_sent_recovery_cart()
        sid = ac.recovery_session_id or ""
        slug = st.zid_store_id

        with patch("main._dashboard_recovery_store_row", return_value=st):
            msgs = _api_json_dashboard_messages(st)
        self.assertGreaterEqual(len(msgs.get("merchant_message_history_rows") or []), 1)

        body = self._assert_cart_visible_in_normal_carts_api(st)
        sent_row = next(
            r
            for r in body.get("merchant_carts_page_rows") or []
            if int(r.get("merchant_case_row_id") or 0) == int(ac.id)
        )
        self.assertEqual(sent_row.get("merchant_cart_bucket"), "sent")
        self.assertIn(
            "بانتظار تفاعل العميل",
            sent_row.get("merchant_status_label_ar") or "",
        )

        ac.raw_payload = json.dumps(
            {"cf_behavioral": {"customer_replied": True}}, ensure_ascii=False
        )
        db.session.commit()
        active_mid, archived_mid = self._active_and_archived_rows(st, session_id=sid)
        self.assertEqual(len(archived_mid), 0)
        self.assertEqual(len(active_mid), 1)

        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=ac.zid_cart_id,
                phone="966501112233",
                message="",
                status="stopped_converted",
                step=2,
                created_at=now,
            )
        )
        ac.status = "recovered"
        db.session.commit()

        active_end, archived_end = self._active_and_archived_rows(st, session_id=sid)
        self.assertEqual(len(active_end), 0)
        self.assertEqual(len(archived_end), 1)
        self.assertEqual(archived_end[0].get("merchant_coarse_status"), "converted")

    def test_sent_recovery_visible_via_http_normal_carts_endpoint(self) -> None:
        st, _ac, _lg = self._seed_sent_recovery_cart()
        with patch("main._dashboard_recovery_store_row", return_value=st):
            r = self._client.get("/api/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:400])
        payload = r.json()
        self.assertTrue(payload.get("ok"))
        rows = payload.get("merchant_carts_page_rows") or []
        self.assertGreaterEqual(len(rows), 1)
        fc = payload.get("merchant_cart_filter_counts") or {}
        self.assertGreaterEqual(int(fc.get("all") or 0), len(rows))
        self.assertGreaterEqual(int(fc.get("sent") or 0), 1)


if __name__ == "__main__":
    unittest.main()
