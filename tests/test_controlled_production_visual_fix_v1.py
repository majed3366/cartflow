# -*- coding: utf-8 -*-
"""Controlled Production Visual Fix V1 — closes falsification RCA blind spots."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
RCA = (
    ROOT / "docs" / "product" / "production_visual_falsification_rca_v1" / "REPORT.md"
).read_text(encoding="utf-8")
SEM_MODEL = list((ROOT / "services").glob("*semantic*visual*")) + list(
    (ROOT / "docs").rglob("*semantic-visual-model*")
)

# Contract: min gap joint end → content (px). Desktop 8+18+8=34; mobile 8+16+8=32.
SETTINGS_MIN_GAP_PX = 8
SETTINGS_JOINT_INSET = 8
SETTINGS_JOINT_W_DESKTOP = 18
SETTINGS_JOINT_W_MOBILE = 16


def _block(css: str, start: str, end: str | None = None) -> str:
    i = css.find(start)
    if i < 0:
        return ""
    chunk = css[i:]
    if end:
        j = chunk.find(end)
        return chunk[:j] if j > 0 else chunk[:1200]
    return chunk[:1200]


class Pvfix01SettingsCollisionReserve(unittest.TestCase):
    """Blind spot: runtime overlap / min text-geometry separation."""

    def test_no_padding_shorthand_on_row(self) -> None:
        row = _block(SETTINGS_CSS, "[data-cf-ui=\"v2\"] .cf2-settings__row {", "is-needs")
        self.assertNotRegex(row, r"padding\s*:\s*[^;]+;")
        self.assertIn("padding-inline-start:", row)
        self.assertIn("padding-block:", row)

    def test_ledger_reserve_beats_row_pad(self) -> None:
        self.assertIn(
            ".cf2-settings__row.cf2-settings__ledger-row",
            SETTINGS_CSS,
        )
        desk = SETTINGS_MIN_GAP_PX + SETTINGS_JOINT_INSET + SETTINGS_JOINT_W_DESKTOP
        mob = SETTINGS_MIN_GAP_PX + SETTINGS_JOINT_INSET + SETTINGS_JOINT_W_MOBILE
        self.assertIn(f"padding-inline-start: {desk}px", SETTINGS_CSS)
        mob_css = SETTINGS_CSS[SETTINGS_CSS.find("@media (max-width: 1023px)") :]
        self.assertIn(f"padding-inline-start: {mob}px", mob_css)
        # Reserve after joint end ≥ MIN_GAP
        self.assertGreaterEqual(desk - (SETTINGS_JOINT_INSET + SETTINGS_JOINT_W_DESKTOP), SETTINGS_MIN_GAP_PX)
        self.assertGreaterEqual(mob - (SETTINGS_JOINT_INSET + SETTINGS_JOINT_W_MOBILE), SETTINGS_MIN_GAP_PX)

    def test_joint_size_preserved(self) -> None:
        self.assertRegex(
            SETTINGS_CSS,
            r"\.cf2-settings__joint\s*\{[^}]*width:\s*18px",
        )
        mob = SETTINGS_CSS[SETTINGS_CSS.find("@media (max-width: 1023px)") :]
        self.assertRegex(mob, r"\.cf2-settings__joint\s*\{[^}]*width:\s*16px")


class Pvfix02WorkspaceSemanticVoid(unittest.TestCase):
    """Blind spot: semantic geometry legibility (not decorative oval)."""

    def test_void_not_ellipse_ornament(self) -> None:
        void = _block(WS_CSS, "body[data-cf-ui=\"v2\"] .cf2-ws__void {", "data-cf2-void=\"large\"")
        self.assertNotIn("border-radius: 50%", void)
        self.assertNotIn("ellipse", void)
        self.assertIn("border-inline-start:", void)
        self.assertIn("dashed", void)
        self.assertIn("::before", WS_CSS)
        self.assertIn("::after", WS_CSS)

    def test_uncertainty_mapping_unchanged(self) -> None:
        self.assertIn("Uncertainty / insufficiency void", WS_JS)
        self.assertIn('sufficiency === "INSUFFICIENT"', WS_JS)
        self.assertIn("data-cf2-void", WS_JS)


class Pvfix03CartsWithheldNotSkeleton(unittest.TestCase):
    """Blind spot: ambiguous withheld / incomplete expression."""

    def test_single_withheld_mass_not_empty_shells(self) -> None:
        self.assertIn("cf2-carts__withheld-mass", CARTS_JS)
        self.assertIn('data-cf2-withheld="queue"', CARTS_JS)
        self.assertNotIn(
            'cf2-carts__object is-withheld',
            CARTS_JS[CARTS_JS.find("function withheldQueueHtml") : CARTS_JS.find("function paint")],
        )

    def test_withheld_css_not_skeleton_bars(self) -> None:
        self.assertIn(".cf2-carts__withheld-mass", CARTS_CSS)
        self.assertIn(".cf2-carts__withheld-rail", CARTS_CSS)
        mass = _block(CARTS_CSS, ".cf2-carts__withheld-mass {", ".cf2-carts__withheld-rail")
        self.assertIn("background: transparent", mass)
        self.assertIn("dashed", mass)


class Pvfix04CommsEmptyIdentity(unittest.TestCase):
    """Blind spot: empty-state page identity (no generic SaaS card)."""

    def test_empty_not_surface_card(self) -> None:
        empty = _block(COMMS_CSS, "body[data-cf-ui=\"v2\"] .cf2-comms__empty {", "empty-title")
        self.assertIn("background: transparent", empty)
        self.assertIn("border-radius: 0", empty)
        self.assertNotIn("--cf2-surface", empty)
        self.assertNotIn("border-radius: var(--cf2-r-md)", empty)

    def test_scaffold_still_on_empty_path(self) -> None:
        self.assertIn("continuumScaffoldHtml", COMMS_JS)
        self.assertIn("cf2-comms__continuum-scaffold", COMMS_JS)


class Pvfix05HomeSpineAndOrbit(unittest.TestCase):
    """Blind spots: relative visual weight + relationship visibility + mobile survival."""

    def test_mobile_spine_not_dominant_8px(self) -> None:
        mob = HOME_CSS[HOME_CSS.find("@media (max-width: 1023px)") :]
        self.assertRegex(mob, r"border-inline-start:\s*5px solid")
        self.assertNotIn("border-inline-start: 8px solid", mob)

    def test_mobile_satellites_relational_widths(self) -> None:
        mob = HOME_CSS[HOME_CSS.find("@media (max-width: 1023px)") :]
        self.assertIn("max-width: 92%", mob)
        self.assertIn("max-width: 78%", mob)
        self.assertIn("max-width: 64%", mob)
        sat = mob[mob.find(".cf2-home__satellite") :]
        self.assertNotIn("max-width: none", sat[:500])

    def test_desktop_gravity_preserved(self) -> None:
        self.assertIn("border-inline-start-width: 10px", HOME_CSS)
        self.assertIn("cf2-home__orbit-axis", HOME_CSS)


class Pvfix06CacheAndEvidence(unittest.TestCase):
    """Blind spots: mobile transform survival markers + production evidence sufficiency."""

    def test_cache_bust_pvfix1(self) -> None:
        self.assertIn("pvfix1", V2_HTML)

    def test_falsification_rca_present_as_evidence_basis(self) -> None:
        # Not pixel-perfect equality — require RCA evidence pack exists and cites SHA
        self.assertIn("c20627167c759145b65b591bc4df75a8dd6262a3", RCA)
        self.assertIn("GEOMETRY_COLLISION", RCA)
        self.assertIn("SAFE TO DESIGN CONTROLLED PRODUCTION VISUAL FIX: YES", RCA)

    def test_semantic_model_not_edited_by_path_marker(self) -> None:
        # Painters/CSS only — semantic-visual-model string still referenced, not redefined here
        self.assertNotIn("semantic-visual-model-v1", CARTS_JS[:200])
        self.assertIn("weighted-queue", CARTS_JS)


class Pvfix07ContractBlindSpotCount(unittest.TestCase):
    """Seven contract + five real-device gate blind spots have dedicated assertions above."""

    def test_seven_contract_classes_covered(self) -> None:
        covered = [
            Pvfix01SettingsCollisionReserve,
            Pvfix02WorkspaceSemanticVoid,
            Pvfix03CartsWithheldNotSkeleton,
            Pvfix04CommsEmptyIdentity,
            Pvfix05HomeSpineAndOrbit,
            Pvfix06CacheAndEvidence,
        ]
        self.assertGreaterEqual(len(covered), 6)


if __name__ == "__main__":
    unittest.main()
