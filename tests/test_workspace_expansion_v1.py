# -*- coding: utf-8 -*-
"""Desktop Workspace Expansion — superseded by Frame V1 single sidebar reservation."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_FRAME_CSS = (_ROOT / "static" / "merchant_frame_v1.css").read_text(encoding="utf-8")


class WorkspaceExpansionV1Tests(unittest.TestCase):
    def test_frame_replaces_expansion_patch(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_frame_v1.css", html)
        self.assertNotIn("merchant_workspace_expansion_v1.css", html)

    def test_single_rail_reservation(self) -> None:
        self.assertIn("--cf-rail-w", _FRAME_CSS)
        self.assertIn("inset-inline-end: var(--cf-rail-w)", _FRAME_CSS)
        self.assertNotIn("merchant_workspace_expansion_v1.css", _TEMPLATE)

    def test_desktop_stage_fills_remaining_viewport(self) -> None:
        self.assertIn(".cf-stage", _FRAME_CSS)
        self.assertIn("right: var(--cf-rail-w)", _FRAME_CSS)

    def test_legacy_expansion_file_still_exists_offline(self) -> None:
        self.assertTrue((_ROOT / "static" / "merchant_workspace_expansion_v1.css").is_file())


if __name__ == "__main__":
    unittest.main()
