# -*- coding: utf-8 -*-
"""Regression: merchant dashboard runtime truth — delay, archive, VIP actions."""

from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import (
    app,
    _api_json_dashboard_vip_carts,
    _merchant_batch_manual_archived,
    _merchant_dashboard_refresh_state_payload,
    _merchant_normal_dashboard_batch_reads,
    _merchant_vip_row_safe_projection,
    _normal_recovery_merchant_lifecycle_bucket_ok,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
    _vip_dashboard_cart_alert_dict_from_group,
    _vip_priority_cart_alert_list,
)
from services.recovery_restart_survival import persist_recovery_schedule_durable
from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    MerchantCartLifecycleArchive,
    RecoverySchedule,
    Store,
)
from services.merchant_cart_lifecycle_archive_v1 import (
    archive_recovery_key,
    archive_recovery_keys,
    is_merchant_archived,
    reopen_recovery_key,
    reopen_recovery_keys,
)
from services.merchant_dashboard_recovery_resolve_v1 import (
    canonical_recovery_keys_for_abandoned_cart,
)
from services.recovery_message_context_v1 import recovery_key_from_parts
from services.recovery_multi_message import resolve_recovery_schedule_timing
from services.store_reason_templates import apply_reason_templates_from_body
from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS


class MerchantDashboardRuntimeTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]
        self._client = TestClient(app)
    def tearDown(self) -> None:
        try:
            for model, filt in (
                (RecoverySchedule, RecoverySchedule.session_id.like(f"%{self._suffix}%")),
                (CartRecoveryLog, CartRecoveryLog.session_id.like(f"%{self._suffix}%")),
                (CartRecoveryReason, CartRecoveryReason.session_id.like(f"%{self._suffix}%")),
                (AbandonedCart, AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")),
                (MerchantCartLifecycleArchive, MerchantCartLifecycleArchive.recovery_key.like(f"%{self._suffix}%")),
                (Store, Store.zid_store_id.like(f"%-{self._suffix}")),
            ):
                db.session.query(model).filter(filt).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_quality_ninety_minute_delay_persists_to_schedule_and_dashboard(self) -> None:
        slug = f"rt-delay-{self._suffix}"
        sid = f"s-delay-{self._suffix}"
        zid = f"z-delay-{self._suffix}"
        stage1 = DASHBOARD_STAGE_TEXTS["quality"][0]

        st = Store(zid_store_id=slug, recovery_attempts=1)
        db.session.add(st)
        db.session.commit()

        apply_reason_templates_from_body(
            st,
            {
                "reason_templates": {
                    "quality": {
                        "enabled": True,
                        "message": stage1,
                        "message_count": 1,
                        "messages": [
                            {"delay": 90, "unit": "minute", "text": stage1},
                        ],
                    }
                }
            },
        )
        db.session.commit()
        db.session.refresh(st)

        timing = resolve_recovery_schedule_timing("quality", st, path="test_quality_90")
        self.assertEqual(timing.get("effective_delay_seconds"), 5400.0)
        self.assertNotEqual(timing.get("effective_delay_seconds"), 120.0)

        rk = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        sched_row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            reason_tag="quality",
            abandon_event_phone="966501234567",
            delay_seconds_scheduled=float(timing["effective_delay_seconds"]),
            schedule_timing=timing,
            recovery_context={"store_slug": slug, "recovery_key": rk},
        )
        self.assertIsNotNone(sched_row)
        assert sched_row is not None
        self.assertEqual(float(sched_row.effective_delay_seconds), 5400.0)

        now = datetime.now(timezone.utc)
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=zid,
                recovery_session_id=sid,
                customer_phone="966501234567",
                status="abandoned",
                cart_value=120.0,
                last_seen_at=now,
                raw_payload=json.dumps({"reason_tag": "quality"}, ensure_ascii=False),
            )
        )
        db.session.commit()

        rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        follow = (
            row.get("customer_lifecycle_next_followup_line_ar")
            or row.get("merchant_followup_next_line_ar")
            or ""
        )
        due_iso = row.get("next_attempt_due_at")
        self.assertTrue(follow or due_iso, msg=row)
        if follow:
            self.assertIn("٩٠", follow)

    def test_manual_archive_persists_across_dashboard_refresh(self) -> None:
        slug = f"rt-arch-{self._suffix}"
        sid = f"s-arch-{self._suffix}"
        zid = f"z-arch-{self._suffix}"
        now = datetime.now(timezone.utc)

        st = Store(zid_store_id=slug, recovery_attempts=1, vip_cart_threshold=5000)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111111",
            status="abandoned",
            cart_value=80.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        rk_parts = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        rk_log = f"{slug}:log-{self._suffix}"
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                recovery_key=rk_log,
                phone="966501111111",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()

        before_token = _merchant_dashboard_refresh_state_payload(st).get(
            "merchant_dashboard_refresh_token"
        )
        arch = archive_recovery_key(
            recovery_key=rk_log,
            store_slug=slug,
            abandoned_cart_id=int(ac.id),
        )
        self.assertTrue(arch.get("ok"), arch)
        self.assertTrue(is_merchant_archived(rk_log))

        after_token = _merchant_dashboard_refresh_state_payload(st).get(
            "merchant_dashboard_refresh_token"
        )
        self.assertNotEqual(before_token, after_token)

        batch = _merchant_normal_dashboard_batch_reads([ac], st)
        self.assertTrue(_merchant_batch_manual_archived(ac, batch))
        self.assertFalse(
            _normal_recovery_merchant_lifecycle_bucket_ok(
                lc_raw="active",
                terminal_archived=False,
                coarse="sent",
                stale_flag=False,
                log_statuses=frozenset({"mock_sent"}),
                merchant_manual_archived=True,
            )
        )
        self.assertTrue(
            _normal_recovery_merchant_lifecycle_bucket_ok(
                lc_raw="archived",
                terminal_archived=False,
                coarse="sent",
                stale_flag=False,
                log_statuses=frozenset({"mock_sent"}),
                merchant_manual_archived=True,
            )
        )
        self.assertFalse(
            _normal_recovery_merchant_lifecycle_bucket_ok(
                lc_raw="all",
                terminal_archived=False,
                coarse="sent",
                stale_flag=False,
                log_statuses=frozenset({"mock_sent"}),
                merchant_manual_archived=True,
            )
        )

        active_rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(active_rows), 0)
        all_rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="all",
            dash_store=st,
        )
        self.assertEqual(len(all_rows), 0)
        archived_rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="archived",
            dash_store=st,
        )
        self.assertEqual(len(archived_rows), 1)

        multi = archive_recovery_keys(
            recovery_keys=[rk_parts, rk_log],
            store_slug=slug,
            abandoned_cart_id=int(ac.id),
        )
        self.assertTrue(multi.get("ok"), multi)
        self.assertTrue(is_merchant_archived(rk_parts))

        reopen = reopen_recovery_keys([rk_log, rk_parts])
        self.assertTrue(reopen.get("ok"), reopen)
        self.assertFalse(is_merchant_archived(rk_log))
        self.assertFalse(is_merchant_archived(rk_parts))

        batch_open = _merchant_normal_dashboard_batch_reads([ac], st)
        self.assertFalse(_merchant_batch_manual_archived(ac, batch_open))
        self.assertTrue(
            _normal_recovery_merchant_lifecycle_bucket_ok(
                lc_raw="active",
                terminal_archived=False,
                coarse="sent",
                stale_flag=False,
                log_statuses=frozenset({"mock_sent"}),
                merchant_manual_archived=False,
            )
        )

    def test_vip_cart_list_and_alert_state_with_and_without_phone(self) -> None:
        slug = f"rt-vip-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=1000, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()

        sid_phone = f"s-vip-p-{self._suffix}"
        sid_nophone = f"s-vip-np-{self._suffix}"
        now = datetime.now(timezone.utc)
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=f"z-vip-p-{self._suffix}",
                recovery_session_id=sid_phone,
                customer_phone="966502222222",
                status="abandoned",
                cart_value=2500.0,
                vip_mode=True,
                last_seen_at=now,
            )
        )
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=f"z-vip-np-{self._suffix}",
                recovery_session_id=sid_nophone,
                customer_phone=None,
                status="abandoned",
                cart_value=1800.0,
                vip_mode=True,
                last_seen_at=now - timedelta(minutes=5),
            )
        )
        db.session.commit()

        vip_raw = _vip_priority_cart_alert_list(dash_store=st)
        self.assertGreaterEqual(len(vip_raw), 2)

        body = _api_json_dashboard_vip_carts(st)
        self.assertGreaterEqual(int(body.get("merchant_nav_badge_vip") or 0), 2)
        self.assertIn("سلال VIP نشطة", body.get("merchant_vip_alert_state_ar") or "")

        page_rows = body.get("merchant_vip_page_rows") or []
        with_phone = next(
            (x for x in page_rows if x.get("has_phone")), None
        )
        without_phone = next(
            (x for x in page_rows if not x.get("has_phone")), None
        )
        self.assertIsNotNone(with_phone)
        self.assertIsNotNone(without_phone)
        assert with_phone is not None
        assert without_phone is not None
        self.assertTrue(with_phone.get("manual_contact_available"))
        self.assertTrue(str(with_phone.get("contact_href") or "").startswith("https://wa.me/"))
        self.assertFalse(without_phone.get("manual_contact_available"))
        self.assertIn(
            "لا يوجد رقم متاح",
            without_phone.get("manual_contact_unavailable_ar") or "",
        )

    def test_vip_manual_contact_projection_phone_and_unavailable_state(self) -> None:
        slug = f"rt-vip-end-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=500, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()
        now = datetime.now(timezone.utc)
        ac_phone = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"z-vip-p2-{self._suffix}",
            recovery_session_id=f"s-vip-p2-{self._suffix}",
            customer_phone="966503333333",
            status="abandoned",
            cart_value=900.0,
            vip_mode=True,
            last_seen_at=now,
        )
        ac_nophone = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"z-vip-np2-{self._suffix}",
            recovery_session_id=f"s-vip-np2-{self._suffix}",
            status="abandoned",
            cart_value=850.0,
            vip_mode=True,
            last_seen_at=now,
        )
        db.session.add(ac_phone)
        db.session.add(ac_nophone)
        db.session.commit()

        vc_phone = _vip_dashboard_cart_alert_dict_from_group([ac_phone], st)
        vc_nophone = _vip_dashboard_cart_alert_dict_from_group([ac_nophone], st)
        proj_phone = _merchant_vip_row_safe_projection(
            vc_phone, avatar_letter="A", dash_store=st
        )
        proj_nophone = _merchant_vip_row_safe_projection(
            vc_nophone, avatar_letter="B", dash_store=st
        )
        self.assertTrue(proj_phone.get("manual_contact_available"))
        self.assertTrue(str(proj_phone.get("contact_href") or "").startswith("https://wa.me/"))
        self.assertFalse(proj_nophone.get("manual_contact_available"))
        self.assertIn(
            "لا يوجد رقم متاح",
            proj_nophone.get("manual_contact_unavailable_ar") or "",
        )

    def test_canonical_recovery_keys_for_abandoned_cart_includes_parts_and_log(
        self,
    ) -> None:
        slug = f"rt-alias-{self._suffix}"
        sid = f"s-alias-{self._suffix}"
        zid = f"z-alias-{self._suffix}"
        st = Store(zid_store_id=slug, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            cart_value=50.0,
        )
        db.session.add(ac)
        db.session.commit()
        rk_parts = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        rk_log = f"{slug}:log-{self._suffix}"
        keys = canonical_recovery_keys_for_abandoned_cart(
            ac,
            store_slug=slug,
            recovery_key=rk_log,
        )
        self.assertIn(rk_log, keys)
        self.assertIn(rk_parts, keys)

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._dashboard_recovery_store_row")
    def test_archive_http_endpoint_persists_and_hides_active(
        self, mock_dash_store, _mock_auth_bypass
    ) -> None:
        slug = f"rt-arch-http-{self._suffix}"
        sid = f"s-arch-http-{self._suffix}"
        zid = f"z-arch-http-{self._suffix}"
        now = datetime.now(timezone.utc)
        st = Store(zid_store_id=slug, recovery_attempts=1, vip_cart_threshold=5000)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111111",
            status="abandoned",
            cart_value=80.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        rk_parts = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        rk_log = f"{slug}:log-http-{self._suffix}"
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                recovery_key=rk_log,
                phone="966501111111",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()
        mock_dash_store.return_value = st

        resp = self._client.post(
            "/api/dashboard/cart-lifecycle/archive",
            json={
                "recovery_key": rk_log,
                "store_slug": slug,
                "abandoned_cart_id": int(ac.id),
                "session_id": sid,
                "cart_id": zid,
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body.get("ok"), body)
        self.assertTrue(is_merchant_archived(rk_log))
        self.assertTrue(is_merchant_archived(rk_parts))

        active_rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(active_rows), 0)

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._dashboard_recovery_store_row")
    def test_reopen_http_endpoint_restores_active_visibility(
        self, mock_dash_store, _mock_auth_bypass
    ) -> None:
        slug = f"rt-reopen-http-{self._suffix}"
        sid = f"s-reopen-http-{self._suffix}"
        zid = f"z-reopen-http-{self._suffix}"
        now = datetime.now(timezone.utc)
        st = Store(zid_store_id=slug, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501222222",
            status="abandoned",
            cart_value=120.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        rk_log = f"{slug}:log-reopen-{self._suffix}"
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                recovery_key=rk_log,
                phone="966501222222",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()
        mock_dash_store.return_value = st

        arch = self._client.post(
            "/api/dashboard/cart-lifecycle/archive",
            json={
                "recovery_key": rk_log,
                "store_slug": slug,
                "abandoned_cart_id": int(ac.id),
                "session_id": sid,
                "cart_id": zid,
            },
        )
        self.assertTrue(arch.json().get("ok"), arch.text)

        reopen = self._client.post(
            "/api/dashboard/cart-lifecycle/reopen",
            json={
                "recovery_key": rk_log,
                "store_slug": slug,
                "abandoned_cart_id": int(ac.id),
                "session_id": sid,
                "cart_id": zid,
            },
        )
        self.assertEqual(reopen.status_code, 200, reopen.text)
        self.assertTrue(reopen.json().get("ok"), reopen.json())
        self.assertFalse(is_merchant_archived(rk_log))

        active_rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(active_rows), 1)

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._dashboard_recovery_store_row")
    def test_vip_manual_contact_endpoint_no_phone_unavailable(
        self, mock_dash_store, _mock_auth_bypass
    ) -> None:
        slug = f"rt-vip-mc-np-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=500, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"z-vip-mc-np-{self._suffix}",
            recovery_session_id=f"s-vip-mc-np-{self._suffix}",
            status="abandoned",
            cart_value=900.0,
            vip_mode=True,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        mock_dash_store.return_value = st

        resp = self._client.get(f"/api/dashboard/vip-cart/{int(ac.id)}/manual-contact")
        self.assertEqual(resp.status_code, 400, resp.text)
        body = resp.json()
        self.assertFalse(body.get("ok"))
        self.assertFalse(body.get("manual_contact_available"))
        self.assertIn("لا يوجد رقم متاح", body.get("error") or body.get("manual_contact_unavailable_ar") or "")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._dashboard_recovery_store_row")
    def test_vip_manual_contact_endpoint_with_phone_returns_action(
        self, mock_dash_store, _mock_auth_bypass
    ) -> None:
        slug = f"rt-vip-mc-p-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=500, recovery_attempts=1)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"z-vip-mc-p-{self._suffix}",
            recovery_session_id=f"s-vip-mc-p-{self._suffix}",
            customer_phone="966504444444",
            status="abandoned",
            cart_value=950.0,
            vip_mode=True,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        mock_dash_store.return_value = st

        resp = self._client.get(f"/api/dashboard/vip-cart/{int(ac.id)}/manual-contact")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertTrue(body.get("ok"), body)
        self.assertTrue(body.get("manual_contact_available"))
        self.assertEqual(body.get("action"), "open_whatsapp")
        self.assertTrue(str(body.get("contact_href") or "").startswith("https://wa.me/"))


if __name__ == "__main__":
    unittest.main()
