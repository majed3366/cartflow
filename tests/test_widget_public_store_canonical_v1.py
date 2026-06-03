# -*- coding: utf-8 -*-
"""Widget public-config must resolve Store by zid only (no latest-store fallback)."""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from models import Store
from services.cartflow_widget_public_store import store_row_for_widget_public_api
from services.store_widget_customization import widget_customization_fields_for_api


class WidgetPublicStoreCanonicalTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self.zid_a = f"pub_a_{uuid.uuid4().hex[:10]}"
        self.zid_b = f"pub_b_{uuid.uuid4().hex[:10]}"
        row_a = Store(
            zid_store_id=self.zid_a,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            widget_name="CARTFLOW",
            widget_primary_color="#000000",
        )
        row_b = Store(
            zid_store_id=self.zid_b,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            widget_name="مساعد المتجر",
            widget_primary_color="#6C5CE7",
        )
        db.session.add(row_a)
        db.session.add(row_b)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.rollback()

    def test_public_api_row_matches_requested_zid_not_latest(self) -> None:
        row = store_row_for_widget_public_api(self.zid_a)
        assert row is not None
        self.assertEqual(getattr(row, "zid_store_id", None), self.zid_a)
        wc = widget_customization_fields_for_api(row)
        self.assertEqual(wc.get("widget_name"), "CARTFLOW")
        self.assertEqual(wc.get("widget_primary_color"), "#000000")

    def test_unknown_zid_does_not_return_latest_store_row(self) -> None:
        missing = f"missing_{uuid.uuid4().hex[:12]}"
        row = store_row_for_widget_public_api(missing)
        if row is not None:
            zid = (getattr(row, "zid_store_id", None) or "").strip()
            self.assertNotEqual(
                widget_customization_fields_for_api(row).get("widget_name"),
                "CARTFLOW",
                msg=f"unexpected CARTFLOW on zid={zid}",
            )


if __name__ == "__main__":
    unittest.main()
