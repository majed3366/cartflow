# -*- coding: utf-8 -*-
"""Tests for OAuth redirect_uri match helpers (Phase 2B Meta 100/36008)."""
from __future__ import annotations

import unittest

from services.oauth_redirect_uri_v1 import (
    build_token_exchange_params,
    compare_redirect_uris,
    oauth_redirect_uris_match,
    rebuild_uri_for_test,
    safe_redirect_uri_diag,
)


class ExactMatchTests(unittest.TestCase):
    def test_exact_uri_match(self) -> None:
        uri = (
            "https://staticxx.facebook.com/x/connect/xd_arbiter/"
            "?version=46#cb=abc&domain=example&origin=1&relation=opener"
        )
        self.assertTrue(oauth_redirect_uris_match(uri, uri))
        cmp = compare_redirect_uris(uri, uri)
        self.assertTrue(cmp["exact_match"])
        self.assertEqual(cmp["component_mismatch"], [])


class MismatchTests(unittest.TestCase):
    def test_trailing_slash_mismatch(self) -> None:
        left = rebuild_uri_for_test(
            scheme="https", host="www.facebook.com", path="/dialog/oauth"
        )
        right = rebuild_uri_for_test(
            scheme="https", host="www.facebook.com", path="/dialog/oauth/"
        )
        self.assertFalse(oauth_redirect_uris_match(left, right))
        cmp = compare_redirect_uris(left, right)
        self.assertFalse(cmp["exact_match"])
        self.assertIn("path", cmp["component_mismatch"])
        self.assertIn("trailing_slash", cmp["component_mismatch"])

    def test_scheme_mismatch(self) -> None:
        left = rebuild_uri_for_test(
            scheme="https", host="example.com", path="/callback"
        )
        right = rebuild_uri_for_test(
            scheme="http", host="example.com", path="/callback"
        )
        self.assertFalse(oauth_redirect_uris_match(left, right))
        cmp = compare_redirect_uris(left, right)
        self.assertFalse(cmp["exact_match"])
        self.assertIn("scheme", cmp["component_mismatch"])

    def test_host_mismatch(self) -> None:
        left = rebuild_uri_for_test(
            scheme="https", host="smartreplyai.net", path="/admin/cb"
        )
        right = rebuild_uri_for_test(
            scheme="https", host="www.smartreplyai.net", path="/admin/cb"
        )
        self.assertFalse(oauth_redirect_uris_match(left, right))
        cmp = compare_redirect_uris(left, right)
        self.assertFalse(cmp["exact_match"])
        self.assertIn("host", cmp["component_mismatch"])

    def test_query_mismatch(self) -> None:
        left = rebuild_uri_for_test(
            scheme="https",
            host="staticxx.facebook.com",
            path="/x/connect/xd_arbiter/",
            query="version=46",
        )
        right = rebuild_uri_for_test(
            scheme="https",
            host="staticxx.facebook.com",
            path="/x/connect/xd_arbiter/",
            query="version=47",
        )
        # Character-for-character differs even if query_keys match.
        self.assertFalse(oauth_redirect_uris_match(left, right))
        cmp = compare_redirect_uris(left, right)
        self.assertFalse(cmp["exact_match"])
        # Same key set — component_mismatch may be empty for keys; exact_match still false.
        self.assertEqual(cmp["auth"]["query_keys"], cmp["exchange"]["query_keys"])


class SafeDiagTests(unittest.TestCase):
    def test_safe_diag_omits_query_values(self) -> None:
        uri = (
            "https://staticxx.facebook.com/x/connect/xd_arbiter/"
            "?version=46&frame=SECRET_FRAME_ID"
        )
        diag = safe_redirect_uri_diag(uri)
        assert diag is not None
        self.assertTrue(diag["parse_ok"])
        self.assertEqual(diag["host"], "staticxx.facebook.com")
        self.assertEqual(diag["path"], "/x/connect/xd_arbiter/")
        self.assertEqual(diag["query_keys"], ["frame", "version"])
        blob = str(diag)
        self.assertNotIn("SECRET_FRAME_ID", blob)
        self.assertNotIn("version=46", blob)


class BuildExchangeParamsTests(unittest.TestCase):
    def test_omit_when_no_dialog_uri(self) -> None:
        params, diag = build_token_exchange_params(
            client_id="app",
            client_secret="secret",
            code="auth-code-value",
            dialog_redirect_uri="",
        )
        self.assertNotIn("redirect_uri", params)
        self.assertEqual(diag["redirect_uri_mode"], "omit")
        self.assertFalse(diag["redirect_uri_included"])
        self.assertTrue(diag["auth_exchange_compare"]["exact_match"])
        self.assertEqual(diag["auth_exchange_compare"]["note"], "both_omitted")
        # Never put secret/code *values* into diag (key names like client_secret are ok).
        blob = str(diag)
        self.assertNotIn("auth-code-value", blob)
        self.assertNotIn('"client_secret": "secret"', blob)

    def test_dialog_exact_passthrough(self) -> None:
        dialog = (
            "https://staticxx.facebook.com/x/connect/xd_arbiter/"
            "?version=46#cb=abc"
        )
        params, diag = build_token_exchange_params(
            client_id="app",
            client_secret="secret",
            code="auth-code-value",
            dialog_redirect_uri=dialog,
        )
        self.assertEqual(params["redirect_uri"], dialog)
        self.assertEqual(diag["redirect_uri_mode"], "dialog_exact")
        self.assertTrue(diag["redirect_uri_included"])
        self.assertTrue(diag["auth_exchange_compare"]["exact_match"])
        # No rewrite / trailing slash mutation.
        self.assertFalse(params["redirect_uri"].endswith("//"))


if __name__ == "__main__":
    unittest.main()
