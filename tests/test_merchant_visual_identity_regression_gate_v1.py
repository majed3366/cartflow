# -*- coding: utf-8 -*-
"""MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE — fail closed on silent legacy."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_runtime_identity_v1 import (
    CANONICAL_RENDERER,
    CANONICAL_SHELL,
    CANONICAL_TEMPLATE,
    CANONICAL_UI_VERSION,
)
from services.merchant_visual_identity_v1 import (
    FIGMA_IDENTITY_PARITY,
    FIGMA_MAPPED_PRIMITIVES,
    FIGMA_PARITY_CONTRACT,
    REGRESSION_GATE,
    VISUAL_INVARIANTS,
    VISUAL_LAW_SET,
    VISUAL_SYSTEM_VERSION,
    forbidden_present,
    missing_markers,
)

ROOT = Path(__file__).resolve().parents[1]
V2 = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
FRAME_CSS = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(encoding="utf-8")
LANG_CSS = (ROOT / "static" / "merchant_ui_v2_language.css").read_text(encoding="utf-8")
LANG_JS = (ROOT / "static" / "merchant_ui_v2_language.js").read_text(encoding="utf-8")


class MerchantVisualIdentityRegressionGate(unittest.TestCase):
    """Binding gate. A future Merchant UI deploy must fail these assertions."""

    GATE = REGRESSION_GATE

    def test_gate_name_stable(self) -> None:
        self.assertEqual(self.GATE, "MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE")

    def test_canonical_renderer_not_legacy(self) -> None:
        client = TestClient(app)
        r = client.get("/dashboard")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Template"), CANONICAL_TEMPLATE)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), CANONICAL_RENDERER)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), CANONICAL_UI_VERSION)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Shell"), CANONICAL_SHELL)
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Visual-System"), VISUAL_SYSTEM_VERSION
        )
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Figma-Parity"), FIGMA_PARITY_CONTRACT
        )
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Semantic-Model"),
            "semantic-visual-model-v1",
        )
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Visual-Law"), VISUAL_LAW_SET)
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Figma-Identity-Parity"),
            FIGMA_IDENTITY_PARITY,
        )
        self.assertEqual(forbidden_present(r.text), [])

    def test_home_workspace_anchors_present(self) -> None:
        self.assertIn("cf2-home__kicker", HOME_JS)
        self.assertIn("cf2-co-row", HOME_JS)
        self.assertIn("cf2-co-row", WS_JS)
        self.assertIn("cf2-dmass", WS_JS)
        self.assertIn("cf2-route", WS_JS)

    def test_shell_not_legacy_app_bar(self) -> None:
        self.assertIn("cf2-utility", V2)
        self.assertIn("cf2-global", V2)
        self.assertIn("cf2-ctx", V2)
        self.assertNotIn("cf-rail", FRAME_CSS)
        self.assertNotIn("merchant_frame_v1.css", V2)

    def test_visual_system_version_matches_runtime(self) -> None:
        probe = TestClient(app).get("/dev/merchant-runtime-identity").json()
        self.assertEqual(probe.get("visual_system_version"), VISUAL_SYSTEM_VERSION)
        self.assertEqual(probe.get("figma_parity_contract"), FIGMA_PARITY_CONTRACT)
        self.assertEqual(probe.get("visual_law_set"), VISUAL_LAW_SET)
        self.assertEqual(probe.get("figma_identity_parity"), FIGMA_IDENTITY_PARITY)
        self.assertEqual(probe.get("visual_invariants"), list(VISUAL_INVARIANTS.keys()))
        self.assertTrue(probe.get("canonical"))

    def test_figma_mapped_primitives_remain_in_language_layer(self) -> None:
        blob = LANG_CSS + LANG_JS + HOME_JS + WS_JS
        self.assertEqual(missing_markers(blob, FIGMA_MAPPED_PRIMITIVES), [])
        self.assertIn("clip-path: polygon", LANG_CSS)
        self.assertIn("open-C", LANG_CSS)
        self.assertIn("cf2-co--attention", LANG_CSS)
        self.assertIn("cf2-co--recovery-opportunity", LANG_CSS)

    def test_mobile_frame_keeps_canonical_shell(self) -> None:
        self.assertIn("@media (max-width: 1023px)", FRAME_CSS)
        self.assertIn("cf2-ctx-handle", V2)
        self.assertNotIn("cf-rail__brand", V2)


if __name__ == "__main__":
    unittest.main()
