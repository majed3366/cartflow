# -*- coding: utf-8 -*-
"""Zid storefront widget install orchestration."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from unittest import mock

import models  # noqa: F401
from extensions import db, init_database
from models import Store
from schema_zid_widget_install import (
    ensure_store_zid_widget_install_schema,
    reset_store_zid_widget_install_schema_cache_for_tests,
)
from services.zid_storefront_widget_install_v1 import (
    _manifest_contains_loader,
    build_widget_install_api_fields,
    maybe_install_zid_storefront_widget,
    record_widget_storefront_seen,
)


class ZidStorefrontWidgetInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_widget_install_schema_cache_for_tests()
        self._env_backup = dict(os.environ)
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_zid_widget_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()
        ensure_store_zid_widget_install_schema(db)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)
        reset_store_zid_widget_install_schema_cache_for_tests()
        db.session.remove()

    def test_manifest_contains_loader(self) -> None:
        loader = "https://smartreplyai.net/static/widget_loader.js"
        manifest = {
            "external_scripts": [{"url": loader, "status": 2}],
        }
        self.assertTrue(_manifest_contains_loader(manifest, loader))

    def test_unsupported_without_partner_path(self) -> None:
        os.environ.pop("ZID_PARTNER_WIDGET_SNIPPET_APPROVED", None)
        os.environ.pop("ZID_API_AUTHORIZATION", None)
        row = Store(
            zid_store_id=f"zid-w-{uuid.uuid4().hex[:8]}",
            access_token="tok-test",
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        with mock.patch(
            "integrations.zid_client.fetch_zid_app_scripts_manifest",
            return_value=({}, 0),
        ), mock.patch(
            "integrations.zid_client.fetch_zid_manager_store_url",
            return_value=None,
        ):
            out = maybe_install_zid_storefront_widget(row, trigger="test")
        self.assertEqual(out.get("status"), "unsupported")
        db.session.refresh(row)
        self.assertEqual(row.widget_installation_status, "unsupported")

    def test_installing_when_partner_snippet_env(self) -> None:
        os.environ["ZID_PARTNER_WIDGET_SNIPPET_APPROVED"] = "1"
        row = Store(
            zid_store_id=f"zid-w-{uuid.uuid4().hex[:8]}",
            access_token="tok-test",
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        with mock.patch(
            "integrations.zid_client.fetch_zid_app_scripts_manifest",
            return_value=({}, 0),
        ), mock.patch(
            "integrations.zid_client.fetch_zid_manager_store_url",
            return_value="https://shop.example.com",
        ), mock.patch(
            "integrations.zid_client.probe_storefront_for_widget_loader",
            return_value=(False, "not_found"),
        ):
            out = maybe_install_zid_storefront_widget(row, trigger="test")
        self.assertEqual(out.get("status"), "pending_partner_snippet")
        db.session.refresh(row)
        self.assertEqual(row.widget_installation_status, "pending_partner_snippet")

    def test_record_widget_seen_marks_installed(self) -> None:
        slug = f"zid-seen-{uuid.uuid4().hex[:8]}"
        row = Store(
            zid_store_id=slug,
            access_token="t",
            widget_installation_status="installing",
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        self.assertTrue(record_widget_storefront_seen(store_slug=slug))
        db.session.refresh(row)
        self.assertEqual(row.widget_installation_status, "installed")
        self.assertIsNotNone(row.widget_last_seen_at)

    def test_skip_reinstall_when_recently_installed(self) -> None:
        row = Store(
            zid_store_id=f"zid-w-{uuid.uuid4().hex[:8]}",
            access_token="tok",
            widget_installation_status="installed",
            widget_installed_at=datetime.now(timezone.utc),
            widget_last_seen_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        out = maybe_install_zid_storefront_widget(row, trigger="test")
        self.assertTrue(out.get("skipped"))

    def test_api_fields_connected(self) -> None:
        row = Store(
            zid_store_id="shop-1",
            widget_installation_status="installed",
            widget_installed_at=datetime.now(timezone.utc),
            is_active=True,
        )
        fields = build_widget_install_api_fields(row, connected=True)
        self.assertTrue(fields["widget_installed_ok"])
        self.assertEqual(fields["widget_status_label_ar"], "تم تثبيت الودجت")


if __name__ == "__main__":
    unittest.main()
