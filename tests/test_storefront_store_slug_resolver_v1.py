# -*- coding: utf-8 -*-
"""Platform-neutral storefront store slug resolver (Zid hostname, embed attrs)."""
from __future__ import annotations

import pathlib
import unittest

from services.store_identity_v1 import extract_zid_permalink_from_url

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RESOLVER = _ROOT / "static" / "cartflow_storefront_store_slug.js"
_LOADER = _ROOT / "static" / "widget_loader.js"
_API = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_api.js"


class StorefrontStoreSlugResolverTests(unittest.TestCase):
    def test_resolver_module_priority_chain(self) -> None:
        src = _RESOLVER.read_text(encoding="utf-8")
        self.assertIn("data-store-slug", src)
        self.assertIn("slugFromScriptAttributes", src)
        self.assertIn("slugFromLoaderUrlQuery", src)
        self.assertIn("slugFromPlatformGlobals", src)
        self.assertIn("slugFromHostname", src)
        self.assertIn(".zid.store", src)
        self.assertIn(".salla.sa", src)
        self.assertIn(".salla.store", src)
        self.assertIn("isPlatformStorefrontHost", src)
        self.assertIn("platform_host_unresolved", src)
        self.assertIn("window.cartflowResolveStorefrontStoreSlug", src)
        chain_ix = src.index("var chain = [")
        chain_block = src[chain_ix : chain_ix + 400]
        attrs_ix = chain_block.index("slugFromScriptAttributes")
        query_ix = chain_block.index("slugFromLoaderUrlQuery")
        globals_ix = chain_block.index("slugFromPlatformGlobals")
        host_ix = chain_block.index("slugFromHostname")
        self.assertLess(attrs_ix, query_ix)
        self.assertLess(query_ix, globals_ix)
        self.assertLess(globals_ix, host_ix)

    def test_widget_loader_wires_resolver_before_runtime(self) -> None:
        loader = _LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflow_storefront_store_slug.js", loader)
        self.assertIn("cartflowEnsureStoreSlugResolverLoaded", loader)
        self.assertIn("cartflowApplyResolvedStoreSlug", loader)
        self.assertIn("v2-store-identity-truth-1", loader)
        init_ix = loader.index("cartflowInitStoreSlugFromLoaderTag")
        beacon_ix = loader.index("cartflowStorefrontWidgetSeenBeacon")
        self.assertLess(beacon_ix, init_ix)

    def test_runtime_api_delegates_to_resolver(self) -> None:
        api = _API.read_text(encoding="utf-8")
        self.assertIn("cartflowResolveStorefrontStoreSlug", api)
        self.assertIn("[CF STORE SLUG FALLBACK DEMO]", api)
        self.assertIn("data-store-slug", api)

    def test_hostname_permalink_matches_server_identity_for_zid(self) -> None:
        self.assertEqual(
            extract_zid_permalink_from_url("https://4hz49e.zid.store/"),
            "4hz49e",
        )
        self.assertEqual(
            extract_zid_permalink_from_url("https://other-shop.zid.store/cart"),
            "other-shop",
        )

    def test_no_hardcoded_merchant_slug(self) -> None:
        for path in (_RESOLVER, _LOADER, _API):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("4hz49e", text, msg=str(path.relative_to(_ROOT)))


if __name__ == "__main__":
    unittest.main()
