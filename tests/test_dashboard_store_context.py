# -*- coding: utf-8 -*-
"""Canonical merchant dashboard store slug resolution."""
from __future__ import annotations

import unittest
from services.merchant_auth_context import reset_merchant_auth_store_slug, set_merchant_auth_store_slug

from services.dashboard_store_context import (
    DEFAULT_MERCHANT_DASHBOARD_STORE_SLUG,
    resolve_dashboard_merchant_store_slug,
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


if __name__ == "__main__":
    unittest.main()
