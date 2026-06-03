# -*- coding: utf-8 -*-
"""Store identity runtime truth report — dashboard vs storefront public-config."""
from __future__ import annotations

import unittest
import uuid
from unittest import mock

from extensions import db
from models import Store
from schema_store_identity import ensure_store_identity_schema
from services.store_identity_runtime_truth_v1 import (
    build_store_identity_runtime_truth_report,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    ALIAS_KIND_ZID_PERMALINK,
    PLATFORM_ZID,
    register_store_identity_alias,
    sync_zid_store_identities_after_oauth,
)
from services.widget_config_cache import update_from_dashboard_store_row


class StoreIdentityRuntimeTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        ensure_store_identity_schema(db)
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

    def test_runtime_truth_passes_when_aliases_aligned(self) -> None:
        report = build_store_identity_runtime_truth_report(
            storefront_slug=self.zid_permalink,
            dashboard_store_row=self.store,
        )
        self.assertTrue(report["passed"])
        self.assertTrue(report["alias_match"])
        self.assertEqual(report["resolved_store_id"], int(self.store.id))
        self.assertEqual(report["public_config_widget_name"], "CARTFLOW")
        self.assertEqual(report["public_config_color"], "#AABBCC")

    def test_dashboard_save_refreshes_all_alias_cache_keys(self) -> None:
        self.store.widget_name = "UPDATED NAME"
        self.store.widget_primary_color = "#010203"
        db.session.commit()
        update_from_dashboard_store_row(self.store)
        report = build_store_identity_runtime_truth_report(
            storefront_slug=self.zid_permalink,
            dashboard_store_row=self.store,
        )
        self.assertTrue(report["checks"]["widget_name_match"])
        self.assertTrue(report["checks"]["widget_color_match"])
        self.assertEqual(report["public_config_widget_name"], "UPDATED NAME")

    @mock.patch("integrations.zid_client.fetch_zid_manager_profile")
    def test_attempt_link_registers_permalink_from_profile(
        self, mock_profile: mock.MagicMock
    ) -> None:
        permalink = f"link{uuid.uuid4().hex[:5]}"
        mock_profile.return_value = {
            "data": {
                "store": {
                    "id": 999001,
                    "uuid": str(uuid.uuid4()),
                    "url": f"https://{permalink}.zid.store/",
                }
            }
        }
        sync_zid_store_identities_after_oauth(
            self.store,
            profile=mock_profile.return_value,
            warm_cache=True,
        )
        db.session.commit()
        report = build_store_identity_runtime_truth_report(
            storefront_slug=permalink,
            dashboard_store_row=self.store,
        )
        self.assertTrue(report["checks"]["storefront_resolved"])
        self.assertTrue(report["alias_match"])


if __name__ == "__main__":
    unittest.main()
