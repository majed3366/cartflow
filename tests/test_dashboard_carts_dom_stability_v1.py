# -*- coding: utf-8 -*-
"""Dashboard carts DOM visibility/stability — normal-carts partial/timeout guards."""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from extensions import db
from main import app, _api_json_dashboard_normal_carts
from models import AbandonedCart, Store


class DashboardCartsDomStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]
        self._client = TestClient(app)
        self._lazy_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")

    def tearDown(self) -> None:
        try:
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_lazy_js_does_not_clear_rows_on_partial_empty(self) -> None:
        js = self._lazy_js
        self.assertIn("normalCartsFetchGen", js)
        self.assertIn("normalCartsAppliedGen", js)
        self.assertIn("normal_carts_stale_skip", js)
        self.assertIn("appliedGen", js)
        self.assertIn("normal_carts_partial_empty", js)
        self.assertIn("lastNormalCartsPageRows.length", js)
        self.assertIn("جاري تحميل السلال", js)
        self.assertIn("normal_carts_empty_mismatch_retry", js)
        self.assertIn("boot_priority", js)
        self.assertIn("normalCartsBootInFlight", js)
        self.assertIn("hydrateNormalCartsCache", js)
        self.assertIn("pending_cart_poll", js)
        self.assertIn("partial_keep", js)
        self.assertIn("token_refresh_state", js)
        self.assertIn("snapshot_degraded", js)
        self.assertIn("normalCartsDegradedRetryStage", js)

    def test_lazy_js_new_cart_refresh_triggers_refetch(self) -> None:
        js = self._lazy_js
        self.assertIn("startPendingNewCartWatcher", js)
        self.assertIn("scheduleNormalCartsTokenRefetch", js)
        self.assertIn("cartflow_cart_event_id", js)

    def test_lazy_js_hash_all_tab_filter_after_render(self) -> None:
        js = self._lazy_js
        self.assertIn('applyCartTabFilters("all")', js)
        self.assertIn("applyCartTabFilters(tab)", js)

    def test_lazy_js_exposes_test_hooks(self) -> None:
        self.assertIn("__maNormalCartsTestHooks", self._lazy_js)
        self.assertIn("renderNormalCartsTables", self._lazy_js)

    def test_dashboard_shell_has_loading_skeleton_not_false_empty(self) -> None:
        r = self._client.get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:400])
        html = r.text or ""
        self.assertIn("ma-dash-skel-row", html)
        self.assertIn('id="ma-tbody-all-carts"', html)
        self.assertNotIn("لا توجد سلال متروكة مسجّلة حالياً", html)

    def test_normal_carts_filter_counts_match_row_list(self) -> None:
        slug = f"stab-{self._suffix}"
        st = Store(zid_store_id=slug)
        db.session.add(st)
        db.session.flush()
        sid = f"s-stab-{self._suffix}"
        for i, val in enumerate((149.0, 200.0)):
            db.session.add(
                AbandonedCart(
                    store_id=st.id,
                    recovery_session_id=sid,
                    zid_cart_id=f"cf_stab_{self._suffix}_{i}",
                    status="abandoned",
                    cart_value=val,
                    customer_phone="966500000001" if i == 0 else None,
                )
            )
        db.session.commit()

        body, _ = _api_json_dashboard_normal_carts(st)
        rows = body.get("merchant_carts_page_rows") or []
        counts = body.get("merchant_cart_filter_counts") or {}
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(int(counts.get("all") or 0), len(rows))

    def test_normal_carts_api_ok_includes_guard_fields(self) -> None:
        r = self._client.get("/api/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:300])
        payload = r.json()
        self.assertTrue(payload.get("ok"))
        self.assertIn("dashboard_partial", payload)
        self.assertIn("dashboard_wall_budget_s", payload)
        self.assertIn("merchant_cart_filter_counts", payload)


if __name__ == "__main__":
    unittest.main()
