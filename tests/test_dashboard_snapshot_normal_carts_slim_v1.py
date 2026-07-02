# -*- coding: utf-8 -*-
"""Normal-carts snapshot slim payload tests."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from extensions import db
from models import DashboardSnapshot
from services.dashboard_snapshot_normal_carts_parity_v1 import (
    evaluate_normal_carts_snapshot_write,
    extract_row_parity_records,
)
from services.dashboard_snapshot_normal_carts_slim_v1 import (
    NORMAL_CARTS_SNAPSHOT_STRIPPED_HEAVY_FIELDS,
    slim_normal_carts_payload_for_snapshot,
    slim_normal_carts_row_for_snapshot,
)
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    encode_snapshot_payload_json,
    snapshot_payload_json_cap,
)


def _fat_row(*, rk: str, cart_id: str, aid: int) -> dict:
    return {
        "recovery_key": rk,
        "zid_cart_id": cart_id,
        "cart_id": cart_id,
        "merchant_case_row_id": aid,
        "merchant_cart_value": 449.0,
        "merchant_has_customer_phone": True,
        "merchant_phone_line_ar": "رقم العميل متوفر",
        "merchant_cart_bucket": "sent",
        "merchant_cart_primary_bucket": "sent",
        "merchant_cart_visible_tabs": ["all", "sent"],
        "customer_lifecycle_state": "waiting_customer_reply",
        "customer_lifecycle_label_ar": "بانتظار رد العميل",
        "customer_lifecycle_what_happened_ar": "أرسلنا رسالة للعميل",
        "customer_lifecycle_what_next_ar": "ننتظر تفاعل العميل",
        "customer_lifecycle_dashboard_action": "none",
        "customer_lifecycle_status_row_class": "s-sent",
        "merchant_cart_fact_v1": {"kind": "returned", "label_ar": "عاد للموقع"},
        "message_preview": "x" * 500,
        "recovery_message_context": {
            "message_body": "y" * 20_000,
            "timeline": [{"step": i} for i in range(200)],
        },
        "durable_lifecycle_closure": {"closure_status": "purchase_completed", "blob": "z" * 5000},
        "last_sent_message_body": "y" * 20_000,
        "truth_mismatch_detected": True,
        "truth_mismatch_reason": "debug_only",
        "_perf": {"query_count": 99},
    }


class DashboardSnapshotNormalCartsSlimTests(unittest.TestCase):
    store_slug = "slim-snapshot-store"

    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-snapshot-slim-v1")
        os.environ[ENV_SNAPSHOT_MODE] = "1"
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.commit()

    def test_strips_heavy_debug_fields_from_row(self) -> None:
        row = _fat_row(rk=f"{self.store_slug}:cf_a", cart_id="cf_a", aid=1)
        slim = slim_normal_carts_row_for_snapshot(row)
        for key in NORMAL_CARTS_SNAPSHOT_STRIPPED_HEAVY_FIELDS:
            self.assertNotIn(key, slim)
        self.assertEqual(slim["recovery_key"], row["recovery_key"])
        self.assertEqual(slim["merchant_cart_value"], 449.0)
        self.assertEqual(slim["merchant_cart_fact_v1"]["kind"], "returned")
        self.assertLessEqual(len(slim["message_preview"]), 120)

    def test_slim_payload_preserves_row_identities(self) -> None:
        rows = [
            _fat_row(rk=f"{self.store_slug}:cf_{i}", cart_id=f"cf_{i}", aid=10 + i)
            for i in range(12)
        ]
        full = {
            "merchant_carts_page_rows": rows,
            "merchant_archived_carts_page_rows": rows[:3],
            "merchant_cart_filter_counts": {"all": 12, "sent": 12},
            "merchant_dashboard_refresh_token": "tok",
            "_perf": {"duration_ms": 1},
        }
        slim = slim_normal_carts_payload_for_snapshot(full)
        full_sigs = {r["signature"] for r in extract_row_parity_records(full)}
        slim_sigs = {r["signature"] for r in extract_row_parity_records(slim)}
        self.assertEqual(full_sigs, slim_sigs)
        self.assertEqual(len(slim["merchant_table_rows"]), 8)
        self.assertNotIn("_perf", slim)

    def test_large_payload_writes_without_truncation(self) -> None:
        rows = [
            _fat_row(rk=f"{self.store_slug}:cf_{i}", cart_id=f"cf_{i}", aid=100 + i)
            for i in range(60)
        ]
        archived = [
            _fat_row(rk=f"{self.store_slug}:arch_{i}", cart_id=f"arch_{i}", aid=200 + i)
            for i in range(40)
        ]
        payload = {
            "merchant_carts_page_rows": rows,
            "merchant_archived_carts_page_rows": archived,
            "merchant_cart_filter_counts": {"all": 60, "sent": 60},
            "merchant_nav_badge_abandoned": 2,
            "merchant_dashboard_refresh_token": "refresh-tok",
        }
        slim = slim_normal_carts_payload_for_snapshot(payload)
        encoded = encode_snapshot_payload_json(slim, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS)
        cap = snapshot_payload_json_cap(SNAPSHOT_TYPE_NORMAL_CARTS)
        self.assertLessEqual(len(encoded.encode("utf-8")), cap)
        decoded = json.loads(encoded)
        self.assertEqual(
            len(extract_row_parity_records(decoded)),
            len(extract_row_parity_records(payload)),
        )
        decision = evaluate_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            live_payload=payload,
            candidate_payload=payload,
        )
        self.assertTrue(decision.allow_write)
        self.assertEqual(decision.drop_stage, "included")
        self.assertFalse(decision.parity["serialization"]["truncated"])

    @patch(
        "services.dashboard_snapshot_normal_carts_parity_v1.snapshot_payload_json_cap",
        return_value=800,
    )
    def test_blocks_when_slim_payload_still_exceeds_cap(self, _mock_cap: unittest.mock.Mock) -> None:
        rows = [
            _fat_row(rk=f"{self.store_slug}:cf_{i}", cart_id=f"cf_{i}", aid=300 + i)
            for i in range(30)
        ]
        payload = {
            "merchant_carts_page_rows": rows,
            "merchant_archived_carts_page_rows": rows,
            "merchant_cart_filter_counts": {"all": 30, "sent": 30},
        }
        decision = evaluate_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            live_payload=payload,
            candidate_payload=payload,
        )
        self.assertFalse(decision.allow_write)
        self.assertEqual(decision.drop_stage, "snapshot_write")
        self.assertEqual(decision.reason, "payload_truncated_or_invalid_json")


if __name__ == "__main__":
    unittest.main()
