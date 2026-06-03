# -*- coding: utf-8 -*-
"""Canonical store identity mapping — platform slugs resolve to one Store row."""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from models import Store, StoreIdentityAlias
from schema_store_identity import ensure_store_identity_schema
from services.cartflow_widget_public_store import store_row_for_widget_public_api
from services.recovery_store_lookup import resolve_recovery_store_row_canonical
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    ALIAS_KIND_ZID_NUMERIC_ID,
    ALIAS_KIND_ZID_PERMALINK,
    ALIAS_KIND_ZID_UUID,
    PLATFORM_ZID,
    extract_zid_permalink_from_url,
    list_public_cache_keys_for_store_row,
    register_store_identity_alias,
    resolve_canonical_store_slug,
    resolve_store_row_by_identifier,
    sync_zid_store_identities_after_oauth,
)
from services.store_widget_customization import widget_customization_fields_for_api


class StoreIdentityV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        ensure_store_identity_schema(db)
        self.cartflow_zid = f"merchant-{uuid.uuid4().hex[:8]}"
        self.zid_permalink = f"z{uuid.uuid4().hex[:6]}"
        self.zid_numeric = str(3000000 + uuid.uuid4().int % 900000)
        self.zid_uuid = str(uuid.uuid4())
        for z in (self.cartflow_zid,):
            for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                db.session.delete(row)
        db.session.commit()
        self.store = Store(
            zid_store_id=self.cartflow_zid,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            widget_name="CARTFLOW",
            widget_primary_color="#112233",
        )
        db.session.add(self.store)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.rollback()

    def _register_zid_aliases(self) -> None:
        sid = int(self.store.id)
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_CARTFLOW_ZID,
            alias_value=self.cartflow_zid,
            platform="cartflow",
        )
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=self.zid_permalink,
            platform=PLATFORM_ZID,
        )
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_ZID_NUMERIC_ID,
            alias_value=self.zid_numeric,
            platform=PLATFORM_ZID,
        )
        register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_ZID_UUID,
            alias_value=self.zid_uuid,
            platform=PLATFORM_ZID,
        )
        db.session.commit()

    def test_extract_zid_permalink_from_url(self) -> None:
        self.assertEqual(
            extract_zid_permalink_from_url("https://4hz49e.zid.store/"),
            "4hz49e",
        )
        self.assertEqual(
            extract_zid_permalink_from_url("4hz49e.zid.store"),
            "4hz49e",
        )

    def test_zid_permalink_resolves_same_store_row(self) -> None:
        self._register_zid_aliases()
        for ident in (
            self.cartflow_zid,
            self.zid_permalink,
            self.zid_numeric,
            self.zid_uuid,
        ):
            row, via = resolve_store_row_by_identifier(ident)
            self.assertIsNotNone(row, msg=f"missing row for {ident}")
            assert row is not None
            self.assertEqual(int(row.id), int(self.store.id))
            self.assertIn("alias", via)

    def test_public_config_path_uses_permalink(self) -> None:
        self._register_zid_aliases()
        row = store_row_for_widget_public_api(self.zid_permalink)
        self.assertIsNotNone(row)
        assert row is not None
        wc = widget_customization_fields_for_api(row)
        self.assertEqual(wc.get("widget_name"), "CARTFLOW")
        self.assertEqual(wc.get("widget_primary_color"), "#112233")

    def test_recovery_resolver_uses_permalink(self) -> None:
        self._register_zid_aliases()
        row = resolve_recovery_store_row_canonical(self.zid_permalink)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(getattr(row, "zid_store_id", None), self.cartflow_zid)

    def test_canonical_slug_normalizes_alias(self) -> None:
        self._register_zid_aliases()
        self.assertEqual(
            resolve_canonical_store_slug(self.zid_permalink),
            self.cartflow_zid,
        )

    def test_cache_keys_include_all_aliases(self) -> None:
        self._register_zid_aliases()
        keys = list_public_cache_keys_for_store_row(self.store)
        for expected in (
            self.cartflow_zid,
            self.zid_permalink,
            self.zid_numeric,
            self.zid_uuid,
        ):
            self.assertIn(expected, keys)

    def test_alias_conflict_does_not_reassign(self) -> None:
        self._register_zid_aliases()
        other = Store(
            zid_store_id=f"other-{uuid.uuid4().hex[:8]}",
            recovery_attempts=1,
        )
        db.session.add(other)
        db.session.commit()
        ok = register_store_identity_alias(
            store_id=int(other.id),
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=self.zid_permalink,
            platform=PLATFORM_ZID,
        )
        db.session.commit()
        self.assertFalse(ok)
        row, _ = resolve_store_row_by_identifier(self.zid_permalink)
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(int(row.id), int(self.store.id))

    def test_sync_zid_identities_from_profile_shape(self) -> None:
        profile = {
            "data": {
                "store": {
                    "id": 3121837,
                    "uuid": self.zid_uuid,
                    "url": f"https://{self.zid_permalink}.zid.store/",
                }
            }
        }
        sync_zid_store_identities_after_oauth(self.store, profile=profile)
        db.session.commit()
        row, _ = resolve_store_row_by_identifier(self.zid_permalink)
        self.assertIsNotNone(row)
        count = (
            db.session.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.store_id == int(self.store.id))
            .count()
        )
        self.assertGreaterEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
