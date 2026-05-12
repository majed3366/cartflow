# -*- coding: utf-8 -*-
"""Storefront widget runtime: public-config must mirror saved merchant widget settings."""
from __future__ import annotations

import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import Store
from services.cartflow_widget_public_store import store_row_for_widget_public_api
from services.cartflow_widget_trigger_settings import widget_trigger_config_from_store_row
from services.merchant_widget_panel import merchant_visible_reason_keys_for_runtime
from services.store_reason_templates import parse_reason_templates_column


def _visible_reason_keys_for_runtime(row: Store) -> list[str]:
    """Mirrors static/cartflow_widget.js cfBuildVisibleReasonRows ordering/filter."""
    wtc = widget_trigger_config_from_store_row(row)
    order = wtc.get("reason_display_order") or []
    rt = parse_reason_templates_column(getattr(row, "reason_templates_json", None))
    out: list[str] = []
    for raw in order:
        k = str(raw or "").strip().lower()
        if not k:
            continue
        entry = rt.get(k) if isinstance(rt, dict) else None
        if isinstance(entry, dict) and entry.get("enabled") is False:
            continue
        out.append(k)
    return out


class CartflowWidgetRuntimePublicConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def _widget_public_store_slug(self) -> str:
        """Same Store row as the dashboard: match zid_store_id from recovery-settings."""
        db.create_all()
        from main import _ensure_default_store_for_recovery  # noqa: PLC0415

        _ensure_default_store_for_recovery()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200, r.text)
        zid = (r.json() or {}).get("zid_store_id")
        self.assertIsInstance(zid, str)
        self.assertTrue(zid.strip(), zid)
        return zid.strip()

    def _reset_common_trigger_flags(self) -> None:
        self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "widget_trigger_config": {
                    "exit_intent_enabled": True,
                    "visibility_widget_globally_enabled": True,
                    "widget_phone_capture_mode": "after_reason",
                }
            },
        )

    def test_dashboard_save_updates_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "widget_trigger_config": {
                    "hesitation_after_seconds": 60,
                    "visibility_page_scope": "cart",
                }
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        self.assertTrue(pr.json().get("ok"), pr.json())
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertTrue(pub.get("ok"), pub)
        wtc = pub.get("widget_trigger_config") or {}
        self.assertEqual(wtc.get("hesitation_after_seconds"), 60)
        self.assertEqual(wtc.get("visibility_page_scope"), "cart")

    def test_disabled_reason_in_templates_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "reason_templates": {
                    "price": {"enabled": False, "message": "x"},
                }
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertTrue(pub.get("ok"), pub)
        rt = pub.get("reason_templates") or {}
        self.assertIn("price", rt)
        self.assertFalse(rt["price"].get("enabled", True))
        row = store_row_for_widget_public_api(ss)
        assert row is not None
        vis = _visible_reason_keys_for_runtime(row)
        self.assertNotIn("price", vis)

    def test_reason_order_preserved_in_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        custom_order = [
            "thinking",
            "other",
            "warranty",
            "quality",
            "shipping",
            "delivery",
            "price",
        ]
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={"widget_trigger_config": {"reason_display_order": custom_order}},
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertEqual(
            (pub.get("widget_trigger_config") or {}).get("reason_display_order"),
            custom_order,
        )

    def test_exit_intent_disabled_in_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={"widget_trigger_config": {"exit_intent_enabled": False}},
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertFalse((pub.get("widget_trigger_config") or {}).get("exit_intent_enabled"))

    def test_phone_capture_mode_in_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={"widget_trigger_config": {"widget_phone_capture_mode": "none"}},
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertEqual(
            (pub.get("widget_trigger_config") or {}).get("widget_phone_capture_mode"),
            "none",
        )

    def test_widget_disabled_in_public_config(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        pr = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "widget_trigger_config": {"visibility_widget_globally_enabled": False}
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        pub = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": ss}
        ).json()
        self.assertFalse(
            (pub.get("widget_trigger_config") or {}).get(
                "visibility_widget_globally_enabled", True
            )
        )

    def test_merchant_visible_reason_keys_matches_runtime_filter(self) -> None:
        ss = self._widget_public_store_slug()
        self._reset_common_trigger_flags()
        self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "reason_templates": {
                    "quality": {"enabled": False, "message": "x"},
                }
            },
        )
        row = store_row_for_widget_public_api(ss)
        assert row is not None
        mvis = merchant_visible_reason_keys_for_runtime(row)
        helper = _visible_reason_keys_for_runtime(row)
        self.assertEqual(mvis, helper)
        self.assertNotIn("quality", mvis)


if __name__ == "__main__":
    unittest.main()
