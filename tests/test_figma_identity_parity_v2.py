# -*- coding: utf-8 -*-
"""Figma Identity Parity V2 — structural/semantic contract, not pixel CI."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_runtime_identity_v1 import (
    CANONICAL_RENDERER,
    CANONICAL_SHELL,
    CANONICAL_TEMPLATE,
)
from services.merchant_visual_identity_v1 import (
    CANONICAL_CARTS_EMITTERS,
    CANONICAL_COMMS_EMITTERS,
    CANONICAL_HOME_EMITTERS,
    CANONICAL_SETTINGS_EMITTERS,
    CANONICAL_SHELL_MARKERS,
    CANONICAL_VISUAL_LAWS,
    CANONICAL_WORKSPACE_EMITTERS,
    CONSTITUTION_STATES_SUPERSEDED_BY_SEMANTIC_MODEL,
    FIGMA_IDENTITY_PARITY,
    FIGMA_MAPPED_PRIMITIVES,
    FIGMA_PARITY_CONTRACT,
    VISUAL_INVARIANTS,
    VISUAL_LAW_SET,
    VISUAL_SYSTEM_VERSION,
    forbidden_present,
    missing_markers,
)
from services.semantic_visual_model_v1 import SEMANTIC_MODEL_VERSION

ROOT = Path(__file__).resolve().parents[1]
V2 = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(encoding="utf-8")
FRAME_CSS = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(encoding="utf-8")
LANG_CSS = (ROOT / "static" / "merchant_ui_v2_language.css").read_text(encoding="utf-8")
SEM_JS = (ROOT / "static" / "merchant_ui_v2_semantic_model.js").read_text(encoding="utf-8")
IDENT_HTML = (
    ROOT / "templates" / "partials" / "merchant_runtime_identity_v1.html"
).read_text(encoding="utf-8")


class FigmaIdentityParityV2Contract(unittest.TestCase):
    def test_identity_parity_is_pass_and_law_set_is_bound(self) -> None:
        self.assertEqual(FIGMA_IDENTITY_PARITY, "pass")
        self.assertEqual(VISUAL_LAW_SET, "constitution-v1+semantic-visual-model-v1")
        self.assertEqual(FIGMA_PARITY_CONTRACT, "visual-language-constitution-v1")
        self.assertEqual(len(CANONICAL_VISUAL_LAWS), 19)
        self.assertEqual(len(VISUAL_INVARIANTS), 10)
        self.assertTrue(all(k.startswith("VIS-INV-") for k in VISUAL_INVARIANTS))
        self.assertGreaterEqual(len(CONSTITUTION_STATES_SUPERSEDED_BY_SEMANTIC_MODEL), 3)

    def test_dashboard_exposes_figma_identity_headers(self) -> None:
        r = TestClient(app).get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), CANONICAL_RENDERER)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Template"), CANONICAL_TEMPLATE)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Shell"), CANONICAL_SHELL)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Visual-System"), VISUAL_SYSTEM_VERSION)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Figma-Parity"), FIGMA_PARITY_CONTRACT)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Semantic-Model"), SEMANTIC_MODEL_VERSION)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Visual-Law"), VISUAL_LAW_SET)
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Figma-Identity-Parity"),
            FIGMA_IDENTITY_PARITY,
        )
        self.assertIn("cartflow-runtime-visual-law", r.text)
        self.assertIn("cartflow-runtime-figma-identity-parity", r.text)
        self.assertEqual(forbidden_present(r.text), [])

    def test_identity_probe_matches_headers(self) -> None:
        probe = TestClient(app).get("/dev/merchant-runtime-identity").json()
        self.assertTrue(probe.get("canonical"))
        self.assertEqual(probe.get("visual_system_version"), VISUAL_SYSTEM_VERSION)
        self.assertEqual(probe.get("semantic_model_version"), SEMANTIC_MODEL_VERSION)
        self.assertEqual(probe.get("figma_parity_contract"), FIGMA_PARITY_CONTRACT)
        self.assertEqual(probe.get("visual_law_set"), VISUAL_LAW_SET)
        self.assertEqual(probe.get("figma_identity_parity"), "pass")
        self.assertEqual(probe.get("visual_invariants"), list(VISUAL_INVARIANTS.keys()))


class FigmaIdentityParityV2Anchors(unittest.TestCase):
    def test_home_workspace_remain_identity_anchors(self) -> None:
        self.assertEqual(missing_markers(HOME_JS + LANG_CSS, CANONICAL_HOME_EMITTERS), [])
        self.assertEqual(missing_markers(WS_JS, CANONICAL_WORKSPACE_EMITTERS), [])
        self.assertIn("CartFlowSemanticVisualV1", HOME_JS)
        self.assertIn("CartFlowSemanticVisualV1", WS_JS)
        self.assertNotIn("buildMomentum", HOME_JS)
        self.assertNotIn("mapHomeObjects", HOME_JS)

    def test_ops_surfaces_share_grammar_without_copying_home(self) -> None:
        self.assertEqual(missing_markers(CARTS_JS + CARTS_CSS, CANONICAL_CARTS_EMITTERS), [])
        self.assertEqual(missing_markers(COMMS_JS + COMMS_CSS, CANONICAL_COMMS_EMITTERS), [])
        self.assertEqual(missing_markers(SETTINGS_JS + SETTINGS_CSS, CANONICAL_SETTINGS_EMITTERS), [])
        self.assertNotIn("cf2-home__board", CARTS_JS)
        self.assertNotIn("cf2-home__board", COMMS_JS)
        self.assertNotIn("cf2-home__board", SETTINGS_JS)
        self.assertNotIn("cf2-dmass", CARTS_JS)
        self.assertNotIn("cf2-dobj--primary", SETTINGS_JS)

    def test_shell_and_legacy_dashboard_cannot_become_canonical(self) -> None:
        self.assertEqual(missing_markers(V2, CANONICAL_SHELL_MARKERS), [])
        self.assertNotIn("merchant_app.html", V2)
        self.assertNotIn("home_executive_summary_v1.js", V2)
        self.assertNotIn("cf-rail", FRAME_CSS)
        self.assertNotIn('data-cf-frame="v1"', V2)

    def test_signature_primitives_remain_in_language_layer(self) -> None:
        blob = LANG_CSS + HOME_JS + WS_JS
        self.assertEqual(missing_markers(blob, FIGMA_MAPPED_PRIMITIVES), [])
        self.assertIn("clip-path: polygon", LANG_CSS)
        self.assertIn("open-C", LANG_CSS)

    def test_mobile_keeps_structural_identity(self) -> None:
        self.assertIn("@media (max-width: 1023px)", FRAME_CSS)
        self.assertIn("cf2-ctx-handle", V2)
        self.assertNotIn("cf-rail__brand", V2)

    def test_semantic_primitives_are_not_static_decorative(self) -> None:
        self.assertIn("projectHomeSurface", HOME_JS)
        self.assertIn("evidenceFieldFromSufficiency", WS_JS)
        self.assertIn("data-cf2-organism", HOME_JS)
        self.assertIn("data-cf2-organism", WS_JS)
        self.assertIn("semantic-visual-model-v1", SEM_JS)
        self.assertNotIn("densityFromCount", HOME_JS)
        self.assertNotIn("densityFromCount", WS_JS)
        self.assertNotIn("L().commerceClause", HOME_JS)
        self.assertNotIn("L().commerceClause", WS_JS)

    def test_visual_law_traceability_is_encoded(self) -> None:
        self.assertIn("cartflow-runtime-visual-law", IDENT_HTML)
        self.assertIn("cartflow-runtime-figma-identity-parity", IDENT_HTML)
        self.assertIn("VIS-INV-08", VISUAL_INVARIANTS)
        self.assertIn("retain traceability", VISUAL_INVARIANTS["VIS-INV-08"])
        self.assertIn("momentum / living-route animation", CONSTITUTION_STATES_SUPERSEDED_BY_SEMANTIC_MODEL)

    def test_versions_do_not_diverge(self) -> None:
        self.assertEqual(VISUAL_SYSTEM_VERSION, "merchant-visual-system-v1")
        self.assertEqual(SEMANTIC_MODEL_VERSION, "semantic-visual-model-v1")
        self.assertIn("merchant_ui_v2_semantic_model.js", V2)
        self.assertIn("merchant_ui_v2_home.js", V2)
        self.assertIn("merchant_ui_v2_workspace.js", V2)


if __name__ == "__main__":
    unittest.main()
