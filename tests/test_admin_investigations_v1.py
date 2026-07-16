# -*- coding: utf-8 -*-
"""Admin Investigation Dashboard V1 — auth, registry projection, read-only."""
from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services import cartflow_admin_http_auth as aauth
from services.product_investigation_registry_v1 import (
    APPROVED_DEPENDENCIES,
    REGISTRY_PATH,
    build_investigation_dashboard_payload,
    get_investigation_detail,
    load_all_investigations,
    severity_counts,
    status_counts,
)


class AdminInvestigationsV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "inv-dash-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def _login(self) -> None:
        r = self.client.post(
            "/admin/operations/login",
            data={
                "password": "inv-dash-auth-test-pass-9",
                "next": "/admin/investigations",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])
        self.assertIn(aauth.admin_cookie_name(), r.cookies)

    def test_admin_authorization_required(self) -> None:
        r = self.client.get("/admin/investigations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_api_unauthorized_without_admin(self) -> None:
        r = self.client.get("/api/admin/investigations")
        self.assertEqual(r.status_code, 401)

    def test_merchant_cookie_cannot_access(self) -> None:
        """Merchant session cookie is not an admin session."""
        self.client.cookies.set("cartflow_merchant_session", "not-an-admin-cookie")
        r = self.client.get("/admin/investigations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        r2 = self.client.get("/api/admin/investigations")
        self.assertEqual(r2.status_code, 401)

    def test_all_inv_001_through_009_appear(self) -> None:
        self._login()
        r = self.client.get("/admin/investigations")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        for i in range(1, 10):
            self.assertIn(f"INV-{i:03d}", body)
        self.assertIn("INV-009", body)
        self.assertIn("investigations-table", body)

    def test_status_and_severity_counts_match_registry(self) -> None:
        recs = load_all_investigations()
        self.assertEqual(len(recs), 9)
        payload = build_investigation_dashboard_payload()
        self.assertEqual(payload["counts"]["by_status"], status_counts(recs))
        self.assertEqual(payload["counts"]["by_severity"], severity_counts(recs))
        self.assertEqual(payload["counts"]["by_status"]["Open"], 8)
        self.assertEqual(payload["counts"]["by_status"]["Ready for Fix"], 1)
        self.assertEqual(payload["counts"]["by_severity"]["Critical"], 2)
        self.assertEqual(payload["counts"]["by_severity"]["High"], 4)
        self.assertEqual(payload["counts"]["by_severity"]["Medium"], 3)

    def test_dependency_relationships_render(self) -> None:
        self._login()
        r = self.client.get("/admin/investigations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("dependency-view", r.text)
        self.assertIn("INV-001 directly explains", r.text)
        self.assertIn("INV-002 remains independent", r.text)
        self.assertIn("INV-009 is an independent", r.text)
        dep = build_investigation_dashboard_payload()["dependency_view"]
        edges = {(e["from"], e["to"]) for e in dep["edges"] if e["kind"] == "depends_on"}
        for child, parents in APPROVED_DEPENDENCIES.items():
            for p in parents:
                self.assertIn((p, child), edges)

    def test_inv_009_non_wp6_regression_evidence(self) -> None:
        self._login()
        r = self.client.get("/admin/investigations/INV-009")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Non-WP-6-regression evidence", r.text)
        self.assertIn("stash", r.text.lower())
        detail = get_investigation_detail("INV-009")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail["depends_on"], [])
        self.assertIn("not a WP-6 regression", (detail["sections"].get("Evidence") or ""))

    def test_filters_work(self) -> None:
        self._login()
        r = self.client.get("/admin/investigations?severity=Critical")
        self.assertEqual(r.status_code, 200)
        self.assertIn("INV-001", r.text)
        self.assertIn("INV-002", r.text)
        self.assertNotIn('data-inv-id="INV-008"', r.text)
        r2 = self.client.get("/admin/investigations?parent=INV-001")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("INV-003", r2.text)
        self.assertIn("INV-006", r2.text)
        self.assertIn("INV-007", r2.text)

    def test_detail_links_canonical_evidence(self) -> None:
        self._login()
        r = self.client.get("/admin/investigations/INV-001")
        self.assertEqual(r.status_code, 200)
        self.assertIn("docs/investigations/INV-001.md", r.text)
        self.assertIn("Observed Symptoms", r.text)

    def test_no_duplicate_independent_registry(self) -> None:
        src = Path("services/product_investigation_registry_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("PRODUCT_INVESTIGATION_REGISTRY.md", src)
        self.assertTrue(REGISTRY_PATH.is_file())
        # Hardcoded title list for INV-001..009 must not exist as a parallel registry
        self.assertNotIn('{"INV-001": "Time Authority Drift"', src)

    def test_read_only_mutations_rejected(self) -> None:
        self._login()
        for method in ("post", "put", "patch", "delete"):
            r = getattr(self.client, method)("/api/admin/investigations/INV-001")
            self.assertEqual(r.status_code, 405, method)
            body = r.json()
            self.assertEqual(body.get("error"), "read_only")

    def test_main_py_composition_only_for_investigations(self) -> None:
        main_txt = Path("main.py").read_text(encoding="utf-8")
        self.assertIn("import routes.admin_investigations", main_txt)
        self.assertNotIn("def admin_investigations", main_txt)
        self.assertNotIn("load_all_investigations", main_txt)

    def test_no_scheduler_or_pool_in_service(self) -> None:
        src = Path("services/product_investigation_registry_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("scheduler", src.lower())
        self.assertNotIn("create_engine", src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, {"execute", "commit", "query"})

    def test_merchant_dashboard_route_unchanged(self) -> None:
        # Smoke: merchant dashboard path still registered (not replaced by admin)
        paths = {getattr(r, "path", None) for r in app.routes}
        self.assertIn("/dashboard", paths)
        self.assertIn("/admin/investigations", paths)


if __name__ == "__main__":
    unittest.main()
