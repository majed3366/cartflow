# -*- coding: utf-8 -*-
"""Canonical Merchant runtime identity + review/dashboard parity."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.merchant_runtime_identity_v1 import (
    CANONICAL_HOME_PAINTER,
    CANONICAL_RENDERER,
    CANONICAL_SHELL,
    CANONICAL_TEMPLATE,
    CANONICAL_UI_VERSION,
    CANONICAL_WORKSPACE_PAINTER,
    IDENTITY_ROUTE,
    REVIEW_BIND_ROUTE,
    build_canonical_identity,
    build_merchant_runtime_identity,
    parity_tuple,
)
from services.merchant_ui_v2.flag_v1 import merchant_ui_selection_source

ROOT = Path(__file__).resolve().parents[1]
LANDING = (ROOT / "templates" / "cartflow_landing.html").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


def _ident(html: str) -> dict[str, str]:
    def meta(name: str) -> str:
        needle = f'name="{name}" content="'
        i = html.find(needle)
        if i < 0:
            return ""
        start = i + len(needle)
        end = html.find('"', start)
        return html[start:end]

    return {
        "ui_version": meta("cartflow-runtime-ui"),
        "template_id": meta("cartflow-runtime-template"),
        "renderer_id": meta("cartflow-runtime-renderer"),
        "shell_version": meta("cartflow-runtime-shell"),
        "home_renderer_version": meta("cartflow-runtime-home-painter"),
        "workspace_renderer_version": meta("cartflow-runtime-workspace-painter"),
        "role": meta("cartflow-runtime-role"),
    }


class MerchantRuntimeIdentityUnitTests(unittest.TestCase):
    def test_canonical_identity_is_v2(self) -> None:
        ident = build_canonical_identity()
        self.assertTrue(ident["canonical"])
        self.assertEqual(ident["ui_version"], CANONICAL_UI_VERSION)
        self.assertEqual(ident["template_id"], CANONICAL_TEMPLATE)
        self.assertEqual(ident["renderer_id"], CANONICAL_RENDERER)
        self.assertEqual(ident["shell_version"], CANONICAL_SHELL)
        self.assertEqual(ident["home_renderer_version"], CANONICAL_HOME_PAINTER)
        self.assertEqual(ident["workspace_renderer_version"], CANONICAL_WORKSPACE_PAINTER)

    def test_v1_is_rollback_not_canonical(self) -> None:
        ident = build_merchant_runtime_identity(ui_v2=False, selection_source="query")
        self.assertFalse(ident["canonical"])
        self.assertEqual(ident["role"], "rollback_only")
        self.assertEqual(ident["ui_version"], "v1")
        self.assertNotEqual(parity_tuple(ident), parity_tuple(build_canonical_identity()))

    def test_selection_source_priority(self) -> None:
        self.assertEqual(
            merchant_ui_selection_source(query={"cf_ui": "v1"}, cookies={"cf_ui_v2": "1"}),
            "query",
        )
        self.assertEqual(
            merchant_ui_selection_source(query={}, cookies={"cf_ui_v2": "0"}),
            "cookie",
        )
        self.assertEqual(merchant_ui_selection_source(query={}, cookies={}), "default")

    def test_landing_is_not_merchant_runtime(self) -> None:
        self.assertNotIn("merchant_app_v2.html", LANDING)
        self.assertNotIn("CartFlowUiV2Home", LANDING)
        self.assertNotIn("data-cf-ui", LANDING)

    def test_v2_template_includes_identity_partial(self) -> None:
        self.assertIn("partials/merchant_runtime_identity_v1.html", V2_HTML)


class MerchantRuntimeParityRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_dashboard_default_is_canonical_v2(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        ident = _ident(r.text)
        self.assertEqual(ident["ui_version"], "v2")
        self.assertEqual(ident["template_id"], CANONICAL_TEMPLATE)
        self.assertEqual(ident["renderer_id"], CANONICAL_RENDERER)
        self.assertEqual(ident["home_renderer_version"], CANONICAL_HOME_PAINTER)
        self.assertEqual(ident["workspace_renderer_version"], CANONICAL_WORKSPACE_PAINTER)
        self.assertEqual(ident["role"], "canonical")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Route"), "/dashboard")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), CANONICAL_RENDERER)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Shell"), CANONICAL_SHELL)
        self.assertIn("CARTFLOW_MERCHANT_RUNTIME", r.text)
        self.assertIn("merchant_ui_v2_home.js", r.text)
        self.assertIn("merchant_ui_v2_workspace.js", r.text)
        self.assertNotIn("home_executive_summary_v1.js", r.text)
        self.assertTrue(r.headers.get("X-CartFlow-Git-Sha"))

    def test_dashboard_v1_rollback_is_explicit(self) -> None:
        r = self.client.get("/dashboard?cf_ui=v1")
        ident = _ident(r.text)
        self.assertEqual(ident["ui_version"], "v1")
        self.assertEqual(ident["role"], "rollback_only")
        self.assertEqual(ident["home_renderer_version"], "HomeExecutiveSummaryV1")
        self.assertIn("home_executive_summary_v1.js", r.text)
        self.assertNotIn("merchant_ui_v2_home.js", r.text)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Role"), "rollback_only")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v1")

    def test_identity_endpoint_matches_dashboard(self) -> None:
        dash = _ident(self.client.get("/dashboard").text)
        probe = self.client.get(IDENTITY_ROUTE).json()
        self.assertEqual(probe["ui_version"], dash["ui_version"])
        self.assertEqual(probe["renderer_id"], dash["renderer_id"])
        self.assertEqual(probe["home_renderer_version"], dash["home_renderer_version"])
        self.assertEqual(probe["workspace_renderer_version"], dash["workspace_renderer_version"])

    def test_identity_endpoint_exposes_cookie_rollback(self) -> None:
        probe = self.client.get(IDENTITY_ROUTE, cookies={"cf_ui_v2": "0"}).json()
        self.assertFalse(probe["canonical"])
        self.assertEqual(probe["selection_source"], "cookie")
        self.assertEqual(probe["ui_version"], "v1")

    @patch("services.living_store_reality_prod_v1.issue_demo_home_review_session_v1")
    def test_review_bind_forces_canonical_v2(self, mock_issue) -> None:
        mock_issue.return_value = {
            "cookie_name": "cartflow_merchant_session",
            "cookie_value": "review-token",
        }
        r = self.client.get(
            REVIEW_BIND_ROUTE,
            cookies={"cf_ui_v2": "0"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard", loc)
        self.assertTrue(loc.endswith("/dashboard#home"))
        self.assertNotIn("cf_ui=v1", loc)
        set_cookie = ";".join(r.headers.get_list("set-cookie"))
        self.assertIn("cf_ui_v2=1", set_cookie)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), CANONICAL_RENDERER)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Role"), "canonical")

    @patch("services.living_store_reality_prod_v1.issue_demo_home_review_session_v1")
    def test_review_and_dashboard_parity_family(self, mock_issue) -> None:
        mock_issue.return_value = {
            "cookie_name": "cartflow_merchant_session",
            "cookie_value": "review-token",
        }
        review = self.client.get(REVIEW_BIND_ROUTE, follow_redirects=False)
        dash = self.client.get("/dashboard")
        self.assertEqual(review.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(dash.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(
            review.headers.get("X-CartFlow-Merchant-Renderer"),
            dash.headers.get("X-CartFlow-Merchant-Renderer"),
        )
        self.assertEqual(
            review.headers.get("X-CartFlow-Merchant-Shell"),
            dash.headers.get("X-CartFlow-Merchant-Shell"),
        )
        ident = _ident(dash.text)
        self.assertEqual(ident["renderer_id"], CANONICAL_RENDERER)
        self.assertEqual(ident["ui_version"], CANONICAL_UI_VERSION)
        self.assertEqual(ident["home_renderer_version"], CANONICAL_HOME_PAINTER)
        self.assertEqual(ident["workspace_renderer_version"], CANONICAL_WORKSPACE_PAINTER)
        self.assertIn("cf2-utility", dash.text)


if __name__ == "__main__":
    unittest.main()
