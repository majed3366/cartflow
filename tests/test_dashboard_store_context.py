# -*- coding: utf-8 -*-
"""Canonical merchant dashboard store slug resolution."""
from __future__ import annotations

import unittest
from services.merchant_auth_context import reset_merchant_auth_store_slug, set_merchant_auth_store_slug

from extensions import db
from models import Store

from services.dashboard_store_context import (
    DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG,
    resolve_dashboard_merchant_store_slug,
    resolve_dashboard_trigger_templates_store,
)


class DashboardStoreContextTests(unittest.TestCase):
    def test_defaults_to_demo(self) -> None:
        self.assertEqual(resolve_dashboard_merchant_store_slug(), "demo")
        self.assertEqual(DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG, "demo")

    def test_query_overrides_default(self) -> None:
        self.assertEqual(
            resolve_dashboard_merchant_store_slug(query_slug="demo2"),
            "demo2",
        )

    def test_body_wins_when_query_empty(self) -> None:
        self.assertEqual(
            resolve_dashboard_merchant_store_slug(body_slug="demo2"),
            "demo2",
        )

    def test_ignores_latest_store_placeholder(self) -> None:
        self.assertEqual(
            resolve_dashboard_merchant_store_slug(query_slug="(dashboard_latest_store)"),
            "demo",
        )

    def test_uses_authenticated_slug_when_no_explicit_slug(self) -> None:
        tok = set_merchant_auth_store_slug("cartflow3-91bd2e")
        try:
            self.assertEqual(
                resolve_dashboard_merchant_store_slug(),
                "cartflow3-91bd2e",
            )
        finally:
            reset_merchant_auth_store_slug(tok)

    def test_trigger_templates_store_prefers_auth_over_demo_body(self) -> None:
        db.create_all()
        z_merchant = "ctx-merchant-save-slug"
        z_demo = "demo"
        for z in (z_merchant, z_demo):
            for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                db.session.delete(row)
        db.session.commit()
        merchant_row = Store(zid_store_id=z_merchant, recovery_attempts=1)
        demo_row = Store(zid_store_id=z_demo, recovery_attempts=1)
        db.session.add(merchant_row)
        db.session.add(demo_row)
        db.session.commit()
        tok = set_merchant_auth_store_slug(z_merchant)
        try:
            slug, row = resolve_dashboard_trigger_templates_store(
                body={"store_slug": "demo"},
            )
            self.assertEqual(slug, z_merchant)
            self.assertIsNotNone(row)
            self.assertEqual(getattr(row, "zid_store_id", None), z_merchant)
        finally:
            reset_merchant_auth_store_slug(tok)
            for z in (z_merchant, z_demo):
                for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                    db.session.delete(row)
            db.session.commit()


if __name__ == "__main__":
    unittest.main()
