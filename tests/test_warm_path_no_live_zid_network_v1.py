# -*- coding: utf-8 -*-
"""
Regression guard for the real-demo break: the synchronous DB-warm hot path must NEVER
make blocking live Zid network calls.

Root cause that failed the real demo while unit tests passed: warm called
sync_connected_platform_identities(), which (for every store with an access_token)
issued a blocking HTTPS call to the Zid API while holding the db_warm lock. Tests ran
against an isolated DB with no connected-store tokens, so the network was never hit and
the hang was invisible; real runtime (Zid Development Store + production) has connected
stores and hung phone-capture / cart-list requests until timeout.

These tests pin the contract that warm is offline by default and only goes to the
network when explicitly opted in.
"""
from __future__ import annotations

import os
import unittest
import uuid
from unittest.mock import patch

from extensions import db
from models import Store
from services import store_identity_v1


class WarmPathNoLiveZidNetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        self._suffix = uuid.uuid4().hex[:10]
        db.create_all()
        os.environ.pop("CARTFLOW_WARM_LIVE_PLATFORM_SYNC", None)

    def tearDown(self) -> None:
        try:
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"warmnet-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
        os.environ.pop("CARTFLOW_WARM_LIVE_PLATFORM_SYNC", None)

    def _connected_store(self) -> Store:
        st = Store(
            zid_store_id=f"warmnet-{self._suffix}",
            access_token="fake-live-token",
            integration_source="zid",
        )
        db.session.add(st)
        db.session.commit()
        return st

    def test_warm_live_platform_sync_disabled_by_default(self) -> None:
        self.assertFalse(store_identity_v1.warm_live_platform_sync_enabled())

    def test_env_flag_enables_warm_live_platform_sync(self) -> None:
        os.environ["CARTFLOW_WARM_LIVE_PLATFORM_SYNC"] = "1"
        self.assertTrue(store_identity_v1.warm_live_platform_sync_enabled())

    def test_default_sync_never_touches_network_for_connected_store(self) -> None:
        self._connected_store()
        with patch.object(
            store_identity_v1, "sync_zid_store_identities_after_oauth"
        ) as live_sync:
            n = store_identity_v1.sync_connected_platform_identities()
        self.assertEqual(n, 0)
        live_sync.assert_not_called()

    def test_opt_in_allows_network_for_connected_store(self) -> None:
        self._connected_store()
        with patch.object(
            store_identity_v1, "sync_zid_store_identities_after_oauth"
        ) as live_sync:
            n = store_identity_v1.sync_connected_platform_identities(allow_network=True)
        self.assertGreaterEqual(n, 1)
        self.assertTrue(live_sync.called)

    def test_warm_body_does_not_call_live_zid_profile_api(self) -> None:
        """End-to-end: a full DB warm must not invoke the live Zid profile fetch."""
        self._connected_store()
        import main  # noqa: PLC0415

        main._cartflow_api_db_warmed = False
        with patch(
            "integrations.zid_client.fetch_zid_manager_profile",
            side_effect=AssertionError("warm must not call live Zid profile API"),
        ):
            main._ensure_cartflow_api_db_warmed(trace_source="test_warm")
        self.assertTrue(main._cartflow_api_db_warmed)


if __name__ == "__main__":
    unittest.main()
