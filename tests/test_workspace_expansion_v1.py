# -*- coding: utf-8 -*-
"""Desktop Workspace Expansion Fix V1 — layout shell tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_WORKSPACE_CSS = (_ROOT / "static" / "merchant_workspace_expansion_v1.css").read_text(
    encoding="utf-8"
)
_SHELL_CSS = (_ROOT / "static" / "merchant_shell_identity_v1.css").read_text(encoding="utf-8")
_RESPONSIVE_CSS = (_ROOT / "static" / "merchant_responsive_layout_v1.css").read_text(
    encoding="utf-8"
)
_CURRENCY_CSS = (_ROOT / "static" / "merchant_currency_certification_v1.css").read_text(
    encoding="utf-8"
)

_DATA_PAGES = ("carts", "messages", "followup", "completed", "vip", "reasons")
_SETTINGS_PAGES = ("whatsapp", "widget", "plans", "settings")


class WorkspaceExpansionV1Tests(unittest.TestCase):
    def test_dashboard_loads_workspace_expansion_stylesheet(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_workspace_expansion_v1.css", html)

    def test_workspace_styles_load_after_responsive_layout(self) -> None:
        responsive_idx = _TEMPLATE.index("merchant_responsive_layout_v1.css")
        workspace_idx = _TEMPLATE.index("merchant_workspace_expansion_v1.css")
        self.assertGreater(workspace_idx, responsive_idx)

    def test_root_cause_shell_double_offset_documented_and_fixed(self) -> None:
        self.assertIn("margin-right: var(--cfpds-sidebar-width)", _SHELL_CSS)
        self.assertIn("margin-right: 0", _WORKSPACE_CSS)
        self.assertIn(".ma-dashboard-frame", _WORKSPACE_CSS)

    def test_desktop_data_pages_use_full_workspace_selectors(self) -> None:
        for page in _DATA_PAGES:
            self.assertIn(f'data-ma-page="{page}"] #page-{page}', _WORKSPACE_CSS)
        self.assertIn("max-width: none", _WORKSPACE_CSS)
        self.assertIn("#ma-carts-groups-v2", _WORKSPACE_CSS)
        self.assertIn(".ma-pe-v2-carts-shell", _WORKSPACE_CSS)

    def test_data_page_parent_does_not_keep_legacy_compact_cap(self) -> None:
        self.assertIn(
            'data-ma-page="carts"] #page-carts .v2-app',
            _WORKSPACE_CSS,
        )
        self.assertIn(
            'data-ma-page="carts"] #page-carts .ma-pe-v2-carts-shell',
            _WORKSPACE_CSS,
        )

    def test_settings_pages_keep_comfort_width(self) -> None:
        for page in _SETTINGS_PAGES:
            self.assertIn(f'data-ma-page="{page}"] #page-{page}', _WORKSPACE_CSS)
        self.assertIn("--cfrl-family-c-max", _WORKSPACE_CSS)

    def test_home_pages_keep_medium_width(self) -> None:
        self.assertIn('data-ma-page="home"] #page-home', _WORKSPACE_CSS)
        self.assertIn("--cfrl-family-a-max", _WORKSPACE_CSS)

    def test_desktop_only_media_query(self) -> None:
        self.assertIn("@media (min-width: 1024px)", _WORKSPACE_CSS)
        self.assertNotIn("@media (max-width:", _WORKSPACE_CSS)

    def test_mobile_breakpoint_untouched_in_workspace_layer(self) -> None:
        self.assertNotIn("max-width: 1023px", _WORKSPACE_CSS)

    def test_currency_atom_behavior_unchanged(self) -> None:
        self.assertIn(".cf-currency-atom", _CURRENCY_CSS)
        self.assertIn("white-space: nowrap", _CURRENCY_CSS)
        self.assertNotIn("cf-currency-atom", _WORKSPACE_CSS)


if __name__ == "__main__":
    unittest.main()
