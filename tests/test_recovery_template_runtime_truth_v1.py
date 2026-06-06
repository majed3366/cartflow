# -*- coding: utf-8 -*-
"""Task 2: dashboard price template must match schedule delay and WhatsApp body."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import unittest

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryReason, RecoverySchedule, Store
from schema_widget import ensure_store_widget_schema
from services.reason_template_recovery import (
    resolve_recovery_whatsapp_message_with_reason_templates,
)
from services.recovery_multi_message import resolve_recovery_schedule_timing
from tests.test_recovery_isolation import _reset_recovery_memory


_PRICE_MSG = "PRICE_TEMPLATE_TRUTH_TEST_60_MIN"
_QUALITY_MSG = "QUALITY_TEMPLATE_TRUTH_TEST_90_MIN"


def _store_with_templates(reason_templates: dict) -> Store:
    row = Store(
        zid_store_id=f"tpl-truth-{uuid.uuid4().hex[:8]}",
        reason_templates_json=json.dumps(reason_templates, ensure_ascii=False),
        recovery_attempts=1,
        whatsapp_recovery_enabled=True,
    )
    db.session.add(row)
    db.session.flush()
    return row


class RecoveryTemplateRuntimeTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        _reset_recovery_memory()
        ensure_store_widget_schema(db)
        self.client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            sfx = self._suffix
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_price_template_delay_60_resolves_to_3600_seconds(self) -> None:
        store = _store_with_templates(
            {
                "price": {
                    "enabled": True,
                    "message": _PRICE_MSG,
                    "message_count": 1,
                    "messages": [
                        {"delay": 60, "unit": "minute", "text": _PRICE_MSG},
                    ],
                }
            }
        )
        timing = resolve_recovery_schedule_timing("price", store, stage_index=0)
        self.assertEqual(3600.0, timing["effective_delay_seconds"])
        self.assertEqual("reason_templates.messages", timing["source"])

    def test_price_template_text_resolves_for_whatsapp(self) -> None:
        store = _store_with_templates(
            {
                "price": {
                    "enabled": True,
                    "message": "",
                    "message_count": 1,
                    "messages": [
                        {"delay": 60, "unit": "minute", "text": _PRICE_MSG},
                    ],
                }
            }
        )
        msg = resolve_recovery_whatsapp_message_with_reason_templates("price", store=store)
        self.assertEqual(_PRICE_MSG, msg)

    def test_quality_template_unchanged(self) -> None:
        store = _store_with_templates(
            {
                "quality": {
                    "enabled": True,
                    "message": _QUALITY_MSG,
                    "message_count": 1,
                    "messages": [
                        {"delay": 90, "unit": "minute", "text": _QUALITY_MSG},
                    ],
                }
            }
        )
        timing = resolve_recovery_schedule_timing("quality", store, stage_index=0)
        self.assertEqual(5400.0, timing["effective_delay_seconds"])
        msg = resolve_recovery_whatsapp_message_with_reason_templates(
            "quality", store=store
        )
        self.assertEqual(_QUALITY_MSG, msg)

    def test_wrong_store_template_not_selected(self) -> None:
        store_a = _store_with_templates(
            {
                "price": {
                    "enabled": True,
                    "message": "STORE_A_PRICE",
                    "message_count": 1,
                    "messages": [{"delay": 60, "unit": "minute", "text": "STORE_A_PRICE"}],
                }
            }
        )
        store_b = _store_with_templates(
            {
                "price": {
                    "enabled": True,
                    "message": "STORE_B_PRICE",
                    "message_count": 1,
                    "messages": [{"delay": 30, "unit": "minute", "text": "STORE_B_PRICE"}],
                }
            }
        )
        msg_a = resolve_recovery_whatsapp_message_with_reason_templates(
            "price", store=store_a
        )
        msg_b = resolve_recovery_whatsapp_message_with_reason_templates(
            "price", store=store_b
        )
        self.assertEqual("STORE_A_PRICE", msg_a)
        self.assertEqual("STORE_B_PRICE", msg_b)
        self.assertNotEqual(msg_a, msg_b)

    @patch("main._persist_cart_recovery_log")
    def test_cf_cart_reason_after_abandon_arms_schedule_with_template_delay(
        self,
        _pcl: object,
    ) -> None:
        """Stable cf_cart_* key must consume pending abandon context and schedule."""
        slug = f"tpl-truth-{self._suffix}"
        store = Store(
            zid_store_id=slug,
            reason_templates_json=json.dumps(
                {
                    "price": {
                        "enabled": True,
                        "message": _PRICE_MSG,
                        "message_count": 1,
                        "messages": [
                            {"delay": 60, "unit": "minute", "text": _PRICE_MSG},
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            recovery_attempts=1,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(store)
        db.session.commit()

        sid = f"s-tpl-truth-{self._suffix}"
        cid = f"cf_cart_{self._suffix}"
        abandon = {
            "event": "cart_abandoned",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 149.0,
            "cart": [{"name": "Item", "price": 149.0}],
        }
        j_ab = self.client.post("/api/cart-event", json=abandon).json()
        self.assertEqual("waiting_for_reason", j_ab.get("recovery_state"))

        r_reason = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": slug,
                "session_id": sid,
                "reason": "price",
                "sub_category": "price_discount_request",
                "customer_phone": "966512345678",
                "cart_id": cid,
            },
        )
        self.assertEqual(200, r_reason.status_code, r_reason.text)

        sched = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .order_by(RecoverySchedule.id.desc())
            .first()
        )
        self.assertIsNotNone(sched, "RecoverySchedule must exist after reason+phone")
        due = getattr(sched, "due_at", None)
        created = getattr(sched, "created_at", None)
        self.assertIsNotNone(due)
        self.assertIsNotNone(created)
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        delay_sec = (due - created).total_seconds()
        self.assertAlmostEqual(3600.0, delay_sec, delta=30.0)
