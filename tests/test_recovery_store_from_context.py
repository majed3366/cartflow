# -*- coding: utf-8 -*-
"""Regression: delayed recovery must load Store by recovery_key merchant zid, not a stale store_id."""
from __future__ import annotations

import unittest
import uuid

import main
from extensions import db
from models import Store


class RecoveryStoreFromContextTests(unittest.TestCase):
    def test_prefers_recovery_key_zid_over_context_store_id(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()

        dash_z = f"cf_dash_{uuid.uuid4().hex[:12]}"
        for z in ("demo", dash_z):
            for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                db.session.delete(row)
        db.session.commit()

        row_demo = Store(
            zid_store_id="demo",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        row_dash = Store(
            zid_store_id=dash_z,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(row_demo)
        db.session.add(row_dash)
        db.session.commit()

        ctx = {
            "recovery_key": "demo:sess-regression",
            "store_id": row_dash.id,
            "store_slug": dash_z,
            "session_id": "sess-regression",
            "cart_id": None,
            "reason_tag": "quality",
            "abandon_event_phone": None,
        }
        resolved = main._recovery_store_from_context(ctx, store_slug=dash_z)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.zid_store_id, "demo")
        self.assertNotEqual(int(resolved.id), int(row_dash.id))


if __name__ == "__main__":
    unittest.main()
