# -*- coding: utf-8 -*-
"""Storefront runtime truth verification gate — DB vs public-config vs beacon."""
from __future__ import annotations

import json
import pathlib
import unittest
import uuid

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import Store
from schema_store_identity import ensure_store_identity_schema
from schema_storefront_runtime_truth import ensure_storefront_runtime_truth_schema
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    ALIAS_KIND_ZID_PERMALINK,
    PLATFORM_ZID,
    register_store_identity_alias,
)
from services.storefront_runtime_truth_gate_v1 import (
    MSG_MISMATCH_AR,
    MSG_PENDING_AR,
    MSG_VERIFIED_AR,
    TRUTH_STATUS_MISMATCH,
    TRUTH_STATUS_PENDING,
    TRUTH_STATUS_VERIFIED,
    build_admin_widget_settings_mismatch_alerts,
    evaluate_storefront_runtime_truth,
    merchant_message_for_status,
    record_storefront_runtime_beacon,
    run_post_save_storefront_truth_gate,
)
from services.widget_config_cache import update_from_dashboard_store_row

_ROOT = pathlib.Path(__file__).resolve().parent.parent


class StorefrontRuntimeTruthGateTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        ensure_store_identity_schema(db)
        ensure_storefront_runtime_truth_schema(db)
        self.cartflow_zid = f"merchant-{uuid.uuid4().hex[:8]}"
        self.zid_permalink = f"z{uuid.uuid4().hex[:6]}"
        self.store = Store(
            zid_store_id=self.cartflow_zid,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            widget_name="CARTFLOW",
            widget_primary_color="#AABBCC",
            cartflow_widget_enabled=True,
            access_token="test-token",
        )
        db.session.add(self.store)
        db.session.commit()
        register_store_identity_alias(
            store_id=int(self.store.id),
            alias_kind=ALIAS_KIND_CARTFLOW_ZID,
            alias_value=self.cartflow_zid,
            platform="cartflow",
        )
        register_store_identity_alias(
            store_id=int(self.store.id),
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=self.zid_permalink,
            platform=PLATFORM_ZID,
        )
        db.session.commit()
        update_from_dashboard_store_row(self.store)

    def tearDown(self) -> None:
        db.session.rollback()

    def test_pending_when_public_config_matches_but_no_beacon(self) -> None:
        gate = evaluate_storefront_runtime_truth(
            self.store,
            storefront_slug=self.zid_permalink,
            trigger="test",
        )
        self.assertEqual(gate["status"], TRUTH_STATUS_PENDING)
        self.assertFalse(gate["verified"])
        self.assertEqual(gate["message_ar"], MSG_PENDING_AR)

    def test_verified_when_db_public_config_and_beacon_align(self) -> None:
        self.store.widget_last_beacon_json = json.dumps(
            {
                "store_slug": self.zid_permalink,
                "rendered_title_text": "CARTFLOW",
                "rendered_primary_color_computed": "#AABBCC",
                "runtime_version": "v2-test",
            }
        )
        db.session.commit()
        gate = evaluate_storefront_runtime_truth(
            self.store,
            storefront_slug=self.zid_permalink,
            trigger="test",
        )
        self.assertEqual(gate["status"], TRUTH_STATUS_VERIFIED)
        self.assertTrue(gate["verified"])
        self.assertEqual(gate["message_ar"], MSG_VERIFIED_AR)

    def test_intended_beacon_without_dom_fields_stays_pending(self) -> None:
        self.store.widget_last_beacon_json = json.dumps(
            {
                "store_slug": self.zid_permalink,
                "widget_name": "CARTFLOW",
                "widget_color": "#AABBCC",
            }
        )
        db.session.commit()
        gate = evaluate_storefront_runtime_truth(
            self.store,
            storefront_slug=self.zid_permalink,
            trigger="test",
        )
        self.assertEqual(gate["status"], TRUTH_STATUS_PENDING)
        self.assertFalse(gate["verified"])

    def test_mismatch_when_beacon_color_differs(self) -> None:
        self.store.widget_last_beacon_json = json.dumps(
            {
                "store_slug": self.zid_permalink,
                "rendered_title_text": "CARTFLOW",
                "rendered_primary_color_computed": "#000000",
            }
        )
        db.session.commit()
        gate = evaluate_storefront_runtime_truth(
            self.store,
            storefront_slug=self.zid_permalink,
            trigger="test",
        )
        self.assertEqual(gate["status"], TRUTH_STATUS_MISMATCH)
        self.assertFalse(gate["verified"])
        self.assertEqual(gate["message_ar"], MSG_MISMATCH_AR)
        self.assertIn("beacon", gate.get("mismatch_reason") or "")

    def test_record_beacon_persists_and_re_evaluates(self) -> None:
        updated, store_id = record_storefront_runtime_beacon(
            {
                "store_slug": self.zid_permalink,
                "rendered_title_text": "CARTFLOW",
                "rendered_primary_color_computed": "#AABBCC",
                "runtime_version": "v2-test",
                "page_url": f"https://{self.zid_permalink}.zid.store/",
                "timestamp": "2026-06-02T12:00:00Z",
            }
        )
        self.assertTrue(updated)
        self.assertEqual(store_id, int(self.store.id))
        row = db.session.get(Store, int(self.store.id))
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.widget_runtime_truth_status, TRUTH_STATUS_VERIFIED)
        beacon = json.loads(row.widget_last_beacon_json or "{}")
        self.assertEqual(beacon.get("rendered_title_text"), "CARTFLOW")

    def test_post_save_gate_returns_truth_payload(self) -> None:
        gate = run_post_save_storefront_truth_gate(
            self.store, trigger="merchant_widget_settings_save"
        )
        self.assertTrue(gate.get("ok"))
        self.assertIn(gate.get("status"), (TRUTH_STATUS_PENDING, TRUTH_STATUS_VERIFIED))
        self.assertIn("message_ar", gate)

    def test_admin_mismatch_alert_for_unverified_store(self) -> None:
        gate = evaluate_storefront_runtime_truth(
            self.store,
            storefront_slug=self.zid_permalink,
            trigger="test",
        )
        alerts = build_admin_widget_settings_mismatch_alerts(
            stores=[
                {
                    "store_id": int(self.store.id),
                    "store_slug": self.cartflow_zid,
                    "display_name": "Test Store",
                    "widget_runtime_truth_status": TRUTH_STATUS_MISMATCH,
                    "widget_runtime_truth_json": json.dumps(gate),
                    "widget_last_runtime_slug": self.zid_permalink,
                }
            ]
        )
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].get("kind"), "widget_settings_mismatch")
        records = alerts[0].get("records") or []
        self.assertTrue(records)
        self.assertEqual(records[0].get("storefront_slug"), self.zid_permalink)

    def test_merchant_messages_by_status(self) -> None:
        self.assertEqual(merchant_message_for_status(TRUTH_STATUS_VERIFIED), MSG_VERIFIED_AR)
        self.assertEqual(merchant_message_for_status(TRUTH_STATUS_PENDING), MSG_PENDING_AR)
        self.assertEqual(merchant_message_for_status(TRUTH_STATUS_MISMATCH), MSG_MISMATCH_AR)


class StorefrontRuntimeTruthApiWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_widget_seen_api_accepts_extended_beacon(self) -> None:
        db.create_all()
        ensure_store_identity_schema(db)
        ensure_storefront_runtime_truth_schema(db)
        zid = f"api-{uuid.uuid4().hex[:8]}"
        permalink = f"p{uuid.uuid4().hex[:5]}"
        row = Store(
            zid_store_id=zid,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            widget_name="BEACON",
            widget_primary_color="#112233",
            cartflow_widget_enabled=True,
        )
        db.session.add(row)
        db.session.commit()
        register_store_identity_alias(
            store_id=int(row.id),
            alias_kind=ALIAS_KIND_CARTFLOW_ZID,
            alias_value=zid,
            platform="cartflow",
        )
        register_store_identity_alias(
            store_id=int(row.id),
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=permalink,
            platform=PLATFORM_ZID,
        )
        db.session.commit()
        update_from_dashboard_store_row(row)
        r = self.client.post(
            "/api/storefront/widget-seen",
            json={
                "store_slug": permalink,
                "rendered_title_text": "BEACON",
                "rendered_primary_color_computed": "#112233",
                "runtime_version": "v2-test",
                "page_url": f"https://{permalink}.zid.store/",
                "timestamp": "2026-06-02T12:00:00Z",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"))
        self.assertTrue(j.get("updated"))

    def test_static_files_include_truth_beacon_wiring(self) -> None:
        loader = (_ROOT / "static" / "widget_loader.js").read_text(encoding="utf-8")
        config = (_ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_config.js").read_text(
            encoding="utf-8"
        )
        panel = (_ROOT / "static" / "merchant_widget_panel.js").read_text(encoding="utf-8")
        general = (_ROOT / "static" / "merchant_general_settings.js").read_text(encoding="utf-8")
        self.assertIn("runtime_version", loader)
        self.assertIn("scheduleStorefrontDomTruthBeacon", config)
        self.assertIn("rendered_title_text", config)
        self.assertIn("storefront_runtime_truth", panel)
        self.assertIn("storefront_runtime_truth", general)


if __name__ == "__main__":
    unittest.main()
