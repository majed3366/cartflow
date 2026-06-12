# -*- coding: utf-8 -*-
"""VIP dashboard query architecture recovery v1 — N+1 guardrails."""
from __future__ import annotations

import re
import time
import uuid
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import event

from extensions import db
from fastapi.testclient import TestClient
from main import _api_json_dashboard_vip_carts, app
from models import AbandonedCart, CartRecoveryReason, Store
from services.vip_dashboard_batch_v1 import (
    VIP_DASHBOARD_LOCAL_MS_TARGET_50_ROWS,
    VIP_DASHBOARD_MAX_BUSINESS_QUERIES_50_ROWS,
    load_vip_dashboard_batch_context,
    vip_dashboard_row_contract,
    vip_phone_from_batch,
)


def _count_business_queries(fn, *args, **kwargs) -> tuple[int, float, object]:
    queries: list[str] = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany) -> None:
        if not statement.strip().upper().startswith("PRAGMA"):
            queries.append(statement)

    t0 = time.perf_counter()
    try:
        out = fn(*args, **kwargs)
    finally:
        event.remove(db.engine, "before_cursor_execute", _before)
    ms = (time.perf_counter() - t0) * 1000
    return len(queries), ms, out


class VipDashboardQueryArchitectureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]
        db.create_all()

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def _make_store(self, slug: str | None = None) -> Store:
        slug = slug or f"vip-arch-{self._suffix}"
        st = Store(zid_store_id=slug, vip_cart_threshold=500)
        db.session.add(st)
        db.session.commit()
        return st

    def _seed_vip_rows(self, store: Store, n: int) -> list[AbandonedCart]:
        rows: list[AbandonedCart] = []
        now = datetime.now(timezone.utc)
        for i in range(n):
            sid = f"s-vip-{self._suffix}-{i}"
            ac = AbandonedCart(
                store_id=int(store.id),
                zid_cart_id=f"z-{self._suffix}-{i}",
                recovery_session_id=sid,
                customer_phone="96650222" + f"{i:04d}"[-4:],
                status="abandoned",
                cart_value=1200.0 + i,
                vip_mode=True,
                last_seen_at=now,
            )
            db.session.add(ac)
            rows.append(ac)
        db.session.commit()
        return rows

    def test_vip_endpoint_query_count_bounded_for_5_rows(self) -> None:
        st = self._make_store()
        self._seed_vip_rows(st, 5)
        load_vip_dashboard_batch_context(st)
        n, ms, body = _count_business_queries(_api_json_dashboard_vip_carts, st)
        self.assertLessEqual(n, VIP_DASHBOARD_MAX_BUSINESS_QUERIES_50_ROWS, n)
        self.assertEqual(len(body.get("merchant_vip_page_rows") or []), 5)
        self.assertLess(ms, VIP_DASHBOARD_LOCAL_MS_TARGET_50_ROWS * 4)

    def test_vip_endpoint_query_count_bounded_for_50_rows(self) -> None:
        st = self._make_store(f"vip-arch-50-{self._suffix}")
        self._seed_vip_rows(st, 50)
        n, ms, body = _count_business_queries(_api_json_dashboard_vip_carts, st)
        self.assertLessEqual(n, VIP_DASHBOARD_MAX_BUSINESS_QUERIES_50_ROWS, n)
        self.assertEqual(len(body.get("merchant_vip_page_rows") or []), 20)
        self.assertEqual(int(body.get("merchant_nav_badge_vip") or 0), 50)

    def test_projection_performs_zero_db_calls(self) -> None:
        st = self._make_store()
        rows = self._seed_vip_rows(st, 3)
        ctx = load_vip_dashboard_batch_context(st)

        def _fail_db(*_a, **_k):
            raise AssertionError("projection must not hit DB")

        with patch.object(db.session, "get", side_effect=_fail_db):
            with patch.object(db.session, "query", side_effect=_fail_db):
                proj = vip_dashboard_row_contract(
                    rows[0], ctx, avatar_letter="أ"
                )
        self.assertTrue(proj.get("has_phone"))
        self.assertIn("reason_tag", proj)

    def test_reason_lookup_is_batched(self) -> None:
        st = self._make_store()
        rows = self._seed_vip_rows(st, 2)
        db.session.add(
            CartRecoveryReason(
                store_slug=st.zid_store_id,
                session_id=rows[1].recovery_session_id,
                reason="price",
                customer_phone="966501111111",
            )
        )
        db.session.commit()
        ctx = load_vip_dashboard_batch_context(st)
        self.assertIn(rows[1].recovery_session_id, ctx.reason_store_by_session)

    def test_phone_lookup_does_not_loop_db_per_row(self) -> None:
        st = self._make_store()
        rows = self._seed_vip_rows(st, 5)
        ctx = load_vip_dashboard_batch_context(st)
        db_calls = {"n": 0}

        def _fail_db(*_a, **_k):
            db_calls["n"] += 1
            raise AssertionError("phone batch must not query DB")

        with patch.object(db.session, "get", side_effect=_fail_db):
            with patch.object(db.session, "query", side_effect=_fail_db):
                for ac in rows:
                    ph = vip_phone_from_batch(ac, ctx)
                    self.assertTrue(ph.startswith("966"))

    def test_response_shape_compatible_with_dashboard(self) -> None:
        st = self._make_store()
        self._seed_vip_rows(st, 2)
        body = _api_json_dashboard_vip_carts(st)
        for key in (
            "merchant_vip_page_rows",
            "merchant_vip_rows",
            "merchant_nav_badge_vip",
            "merchant_automation_mode",
            "merchant_vip_threshold_configured",
            "merchant_vip_alert_state_ar",
        ):
            self.assertIn(key, body)
        row = (body.get("merchant_vip_page_rows") or [])[0]
        for key in (
            "id",
            "amount_display",
            "subtitle_ar",
            "contact_href",
            "has_phone",
            "manual_contact_available",
            "vip_lifecycle_label_ar",
        ):
            self.assertIn(key, row)

    def test_manual_contact_and_unavailable_states(self) -> None:
        st = self._make_store()
        now = datetime.now(timezone.utc)
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=f"z-p-{self._suffix}",
                recovery_session_id=f"s-p-{self._suffix}",
                customer_phone="966503333333",
                status="abandoned",
                cart_value=900.0,
                vip_mode=True,
                last_seen_at=now,
            )
        )
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=f"z-np-{self._suffix}",
                recovery_session_id=f"s-np-{self._suffix}",
                status="abandoned",
                cart_value=850.0,
                vip_mode=True,
                last_seen_at=now,
            )
        )
        db.session.commit()
        body = _api_json_dashboard_vip_carts(st)
        page_rows = body.get("merchant_vip_page_rows") or []
        with_phone = next(x for x in page_rows if x.get("has_phone"))
        without = next(x for x in page_rows if not x.get("has_phone"))
        self.assertTrue(with_phone.get("manual_contact_available"))
        self.assertTrue(str(with_phone.get("contact_href") or "").startswith("https://wa.me/"))
        self.assertFalse(without.get("manual_contact_available"))

    def test_empty_vip_state(self) -> None:
        st = Store(zid_store_id=f"vip-empty-{self._suffix}", vip_cart_threshold=500)
        db.session.add(st)
        db.session.commit()
        body = _api_json_dashboard_vip_carts(st)
        self.assertEqual(body.get("merchant_vip_page_rows"), [])
        self.assertIn("لا سلال VIP", body.get("merchant_vip_alert_state_ar") or "")

    def test_debug_perf_metadata(self) -> None:
        st = self._make_store()
        self._seed_vip_rows(st, 1)
        body = _api_json_dashboard_vip_carts(st, debug_perf=True)
        perf = body.get("debug_perf") or {}
        self.assertIn("query_count", perf)
        self.assertLessEqual(int(perf.get("query_count") or 999), 20)

    def test_no_threshold_empty_state(self) -> None:
        st = Store(zid_store_id=f"vip-noth-{self._suffix}", vip_cart_threshold=None)
        db.session.add(st)
        db.session.commit()
        body = _api_json_dashboard_vip_carts(st)
        self.assertIn("لم يُضبط حد VIP", body.get("merchant_vip_alert_state_ar") or "")


if __name__ == "__main__":
    import unittest

    unittest.main()
