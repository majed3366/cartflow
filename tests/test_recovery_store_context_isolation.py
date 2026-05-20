# -*- coding: utf-8 -*-
"""Recovery runtime must not mix store sources within one flow."""
from __future__ import annotations

import json
import unittest
import uuid
from unittest.mock import patch

import main
from extensions import db
from models import Store
from services.recovery_store_context import (
    canonical_store_slug_from_recovery_key,
    coerce_recovery_runtime_store_slug,
    log_store_context_check,
)
from services.recovery_multi_message import resolve_recovery_schedule_timing


class RecoveryStoreContextIsolationTests(unittest.TestCase):
    def test_canonical_slug_from_recovery_key(self) -> None:
        self.assertEqual(
            canonical_store_slug_from_recovery_key("demo:sess-1"),
            "demo",
        )
        self.assertIsNone(canonical_store_slug_from_recovery_key("nocolon"))

    def test_coerce_prefers_recovery_key_over_hint(self) -> None:
        with patch(
            "services.recovery_store_context.log_store_context_mismatch"
        ) as mismatch:
            slug = coerce_recovery_runtime_store_slug(
                "demo:sess-a",
                "loadtest-store-020",
            )
        self.assertEqual(slug, "demo")
        mismatch.assert_called_once()

    def test_recovery_store_from_context_never_uses_stale_store_id(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()

        dash_z = f"cf_dash_{uuid.uuid4().hex[:12]}"
        loadtest_z = f"loadtest-store-{uuid.uuid4().hex[:8]}"
        for z in ("demo", dash_z, loadtest_z):
            for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                db.session.delete(row)
        db.session.commit()

        demo_tpl = {
            "quality": {
                "enabled": True,
                "message": "DEMO-ONLY-TEMPLATE",
                "message_count": 1,
                "messages": [
                    {
                        "text": "DEMO-ONLY-TEMPLATE",
                        "delay": 3,
                        "unit": "minutes",
                    }
                ],
            }
        }
        load_tpl = {
            "quality": {
                "enabled": True,
                "message": "LOADTEST-ONLY-TEMPLATE",
                "message_count": 1,
                "messages": [
                    {
                        "text": "LOADTEST-ONLY-TEMPLATE",
                        "delay": 9,
                        "unit": "hours",
                    }
                ],
            }
        }
        row_demo = Store(
            zid_store_id="demo",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            reason_templates_json=json.dumps(demo_tpl),
        )
        row_load = Store(
            zid_store_id=loadtest_z,
            recovery_delay=9,
            recovery_delay_unit="hours",
            recovery_attempts=9,
            reason_templates_json=json.dumps(load_tpl),
        )
        row_dash = Store(
            zid_store_id=dash_z,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add_all([row_demo, row_load, row_dash])
        db.session.commit()

        ctx = {
            "recovery_key": "demo:sess-iso",
            "store_id": row_load.id,
            "store_slug": loadtest_z,
            "session_id": "sess-iso",
        }
        resolved = main._recovery_store_from_context(ctx, store_slug=loadtest_z)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.zid_store_id, "demo")
        self.assertNotEqual(int(resolved.id), int(row_load.id))

        timing = resolve_recovery_schedule_timing("quality", resolved, stage_index=0)
        self.assertEqual(timing["effective_delay_seconds"], 180.0)
        self.assertEqual(timing["source"], "reason_templates.messages")

        wrong_timing = resolve_recovery_schedule_timing(
            "quality", row_load, stage_index=0
        )
        self.assertEqual(wrong_timing["effective_delay_seconds"], 32400.0)

    def test_fresh_templates_no_latest_store_fallback(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()

        latest_z = f"latest-only-{uuid.uuid4().hex[:10]}"
        for row in db.session.query(Store).filter_by(zid_store_id=latest_z).all():
            db.session.delete(row)
        db.session.commit()

        latest_row = Store(
            zid_store_id=latest_z,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(latest_row)
        db.session.commit()

        missing = main._fresh_store_row_for_recovery_templates("nonexistent-store-zid")
        self.assertIsNone(missing)

        strict = main._load_store_row_for_recovery(
            "nonexistent-store-zid",
            allow_latest_fallback=False,
        )
        self.assertIsNone(strict)

        with_latest = main._load_store_row_for_recovery(
            "nonexistent-store-zid",
            allow_latest_fallback=True,
        )
        self.assertIsNotNone(with_latest)
        assert with_latest is not None
        self.assertEqual(with_latest.zid_store_id, latest_z)

    def test_bind_identity_aligns_slug_and_row(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
            db.session.delete(row)
        db.session.commit()
        row_demo = Store(
            zid_store_id="demo",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(row_demo)
        db.session.commit()

        slug, row = main._bind_recovery_runtime_store_identity(
            "demo:bind-test",
            "loadtest-store-020",
        )
        self.assertEqual(slug, "demo")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.zid_store_id, "demo")

    def test_store_context_check_ok_when_aligned(self) -> None:
        ok = log_store_context_check(
            recovery_key="demo:s1",
            canonical_store_slug="demo",
            template_store_slug="demo",
            delay_store_slug="demo",
            phone_store_slug="demo",
            selected_store_slug="demo",
        )
        self.assertTrue(ok)

    def test_store_context_check_false_on_mismatch(self) -> None:
        ok = log_store_context_check(
            recovery_key="demo:s1",
            canonical_store_slug="demo",
            template_store_slug="loadtest-store-020",
            delay_store_slug="demo",
            phone_store_slug="demo",
            selected_store_slug="demo",
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
