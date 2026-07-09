# -*- coding: utf-8 -*-
"""Cart Reopen Semantics V1-A — manual archive reopen frontend sync + API split."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import (
    _api_json_dashboard_normal_carts,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store
from services.merchant_cart_lifecycle_archive_v1 import is_merchant_archived
from services.recovery_message_context_v1 import recovery_key_from_parts


class CartReopenSemanticsV1aJsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._lazy_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")

    def test_sync_reopened_cart_row_memory_removes_archived_pool_entry(self) -> None:
        js = self._lazy_js
        self.assertIn("function syncReopenedCartRowMemory", js)
        fn = js[js.index("function syncReopenedCartRowMemory") : js.index("function patchCartRowArchivedVisual")]
        self.assertIn("lastArchivedCartsPageRows = lastArchivedCartsPageRows.filter", fn)
        self.assertIn("lastNormalCartsPageRows.push", fn)
        self.assertIn("applyLifecyclePayloadToRow", fn)

    def test_patch_cart_row_archived_visual_delegates_to_sync_archived(self) -> None:
        js = self._lazy_js
        fn = js[js.index("function patchCartRowArchivedVisual") : js.index("function refreshCompletedCartsTableAfterLifecycleChange")]
        self.assertIn("syncArchivedCartRowMemory", fn)
        self.assertNotIn("customer_lifecycle_is_archived_visual = true", fn)

    def test_reopen_refreshes_completed_before_refetch(self) -> None:
        js = self._lazy_js
        block = js[js.index('[data-lc-reopen]') : js.index("function cartRowHome")]
        self.assertIn("syncReopenedCartRowMemory", block)
        self.assertIn("refreshCompletedCartsTableAfterLifecycleChange", block)
        self.assertNotIn("fetchNormalCarts(\"lifecycle_reopen\");", block)

    def test_reopen_navigates_to_all_after_refetch(self) -> None:
        js = self._lazy_js
        block = js[js.index('fetchNormalCarts("lifecycle_reopen")') : js.index("function cartRowHome")]
        self.assertIn('goToCartTab("all")', block)

    def test_archive_still_navigates_to_completed(self) -> None:
        js = self._lazy_js
        block = js[js.index('[data-lc-archive]') : js.index('[data-lc-reopen]')]
        self.assertIn('goToCartTab("completed")', block)
        self.assertNotIn('goToCartTab("all")', block)

    def test_test_hooks_expose_reopen_memory_helpers(self) -> None:
        js = self._lazy_js
        hooks = js[js.index("window.__maNormalCartsTestHooks") : js.index("window.__maVipCartsTestHooks")]
        self.assertIn("getLastArchivedRows", hooks)
        self.assertIn("syncReopenedCartRowMemory", hooks)
        self.assertIn("completedCartsFromRows", hooks)


class CartReopenSemanticsV1aManualArchiveApiTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]
        self._client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    @patch("main._dashboard_recovery_store_row")
    def test_manual_archive_reopen_moves_cart_active_not_archived_payload(
        self, mock_dash_store
    ) -> None:
        """Manual archive → reopen: API active/archived split (V1-A backend path)."""
        slug = f"v1a-reopen-{self._suffix}"
        sid = f"s-v1a-{self._suffix}"
        zid = f"z-v1a-{self._suffix}"
        now = datetime.now(timezone.utc)
        st = Store(zid_store_id=slug, recovery_attempts=1, vip_cart_threshold=5000)
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501234567",
            status="abandoned",
            cart_value=120.0,
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        rk = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                recovery_key=rk,
                phone="966501234567",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()
        mock_dash_store.return_value = st

        def _rows_for_sid(rows: list) -> list:
            return [
                r
                for r in rows
                if str(r.get("session_id") or "").strip() == sid
                or sid in str(r.get("recovery_key") or "")
            ]

        arch_resp = self._client.post(
            "/api/dashboard/cart-lifecycle/archive",
            json={
                "recovery_key": rk,
                "store_slug": slug,
                "abandoned_cart_id": int(ac.id),
                "session_id": sid,
                "cart_id": zid,
            },
        )
        self.assertEqual(arch_resp.status_code, 200, arch_resp.text)
        self.assertTrue(arch_resp.json().get("ok"), arch_resp.text)
        self.assertTrue(is_merchant_archived(rk))

        dash_arch, _ = _api_json_dashboard_normal_carts(st)
        self.assertEqual(len(_rows_for_sid(dash_arch.get("merchant_carts_page_rows") or [])), 0)
        self.assertEqual(
            len(_rows_for_sid(dash_arch.get("merchant_archived_carts_page_rows") or [])),
            1,
        )

        reopen_resp = self._client.post(
            "/api/dashboard/cart-lifecycle/reopen",
            json={
                "recovery_key": rk,
                "store_slug": slug,
                "abandoned_cart_id": int(ac.id),
                "session_id": sid,
                "cart_id": zid,
            },
        )
        self.assertEqual(reopen_resp.status_code, 200, reopen_resp.text)
        reopen_body = reopen_resp.json()
        self.assertTrue(reopen_body.get("ok"), reopen_body)
        self.assertFalse(is_merchant_archived(rk))
        life = reopen_body.get("lifecycle") or {}
        self.assertNotEqual(str(life.get("customer_lifecycle_state") or ""), "archived")

        dash_open, _ = _api_json_dashboard_normal_carts(st)
        active_open = _rows_for_sid(dash_open.get("merchant_carts_page_rows") or [])
        archived_open = _rows_for_sid(dash_open.get("merchant_archived_carts_page_rows") or [])
        self.assertEqual(len(active_open), 1)
        self.assertEqual(len(archived_open), 0)

        active_list, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        archived_list, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="archived",
            dash_store=st,
        )
        self.assertEqual(len(active_list), 1)
        self.assertEqual(len(archived_list), 0)

    def test_completed_row_detection_uses_archived_visual_not_archived_pool_only(self) -> None:
        js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")
        self.assertIn("function completedCartsFromRows", js)
        self.assertIn("function isCompletedDashboardRow", js)
        self.assertIn("isArchivedDestinationRow(mc)", js)


if __name__ == "__main__":
    unittest.main()
