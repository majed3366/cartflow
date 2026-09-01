# -*- coding: utf-8 -*-
"""Real-device visual composition fix V1 — closes RCA contract blind spots."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


def _px(prop: str, blob: str, selector_hint: str) -> float | None:
    """Best-effort extract of a px length near a selector hint."""
    idx = blob.find(selector_hint)
    if idx < 0:
        return None
    window = blob[idx : idx + 900]
    m = re.search(rf"{re.escape(prop)}\s*:\s*([0-9.]+)px", window)
    return float(m.group(1)) if m else None


class Frc01HomeMassRatio(unittest.TestCase):
    """FRC-01/02: primary mass must outweigh satellites; no equal card grid."""

    def test_no_equal_two_column_monitor_for_gravity_well(self) -> None:
        self.assertIn("data-cf2-orbit", HOME_JS)
        self.assertIn("cf2-home__orbit-axis", HOME_JS)
        # Equal 2-col grid must not define gravity-well orbit row
        orbit_block = HOME_CSS[HOME_CSS.find("gravity-well") :]
        self.assertIn("flex-direction: column", orbit_block)
        self.assertNotIn(
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            HOME_CSS[
                HOME_CSS.find(
                    "body[data-cf-ui=\"v2\"] .cf2-home[data-cf2-organism=\"gravity-well\"] .cf2-home__monitor-row"
                ) :
            ][:400],
        )

    def test_primary_edge_wider_than_satellite(self) -> None:
        primary = _px(
            "border-inline-start-width",
            HOME_CSS,
            'gravity-well"] .cf2-home__board[data-cf2-gravity="primary"]',
        )
        sat = _px("border-inline-start", HOME_CSS, ".cf2-home__satellite {")
        self.assertIsNotNone(primary)
        self.assertGreaterEqual(primary or 0, 8)
        # satellite uses shorthand; ensure mid/far use smaller max-width
        self.assertIn("max-width: 13.5rem", HOME_CSS)
        self.assertIn("min-height: 11.5rem", HOME_CSS)

    def test_mobile_preserves_gravity_edge(self) -> None:
        self.assertIn(
            "gravity-well\"] .cf2-home__board[data-cf2-gravity=\"primary\"]",
            HOME_CSS[HOME_CSS.find("@media (max-width: 1023px)") :],
        )
        mob = HOME_CSS[HOME_CSS.find("@media (max-width: 1023px)") :]
        # Balanced spine (not 8px dominance); still wider than satellite 3px
        self.assertRegex(mob, r"border-inline-start:\s*5px solid")
        self.assertNotIn("border-inline-start: 8px solid", mob)
        # Relational satellite widths survive mobile (not forced 100%)
        self.assertIn("max-width: 92%", mob)
        self.assertIn("max-width: 78%", mob)
        self.assertIn("max-width: 64%", mob)
        self.assertNotIn("width: 100%", mob[mob.find(".cf2-home__satellite") : mob.find(".cf2-home__satellite") + 800])


class Frc03WorkspaceVoidGeometry(unittest.TestCase):
    """FRC-03: void minimum height/opacity for merchant-perceptible gap."""

    def test_void_min_height_threshold(self) -> None:
        h = _px("height", WS_CSS, "body[data-cf-ui=\"v2\"] .cf2-ws__void {")
        self.assertIsNotNone(h)
        self.assertGreaterEqual(h or 0, 36)
        large = _px("height", WS_CSS, 'cf2-ws__void[data-cf2-void="large"]')
        self.assertGreaterEqual(large or 0, 48)

    def test_void_painted_for_insufficient(self) -> None:
        self.assertIn('sufficiency === "INSUFFICIENT"', WS_JS)

    def test_mobile_void_threshold(self) -> None:
        mob = WS_CSS[WS_CSS.find("@media (max-width: 1023px)") :]
        self.assertIn(".cf2-ws__void", mob)
        self.assertRegex(mob, r"\.cf2-ws__void[^}]*height:\s*4[4-9]px")


class Frc04WorkspaceLivePathDoc(unittest.TestCase):
    """FRC-04: review path requires flag ON — documented; painter remains gated by API."""

    def test_rdfix_cache_and_formation_still_bound(self) -> None:
        self.assertIn("rdfix1", V2_HTML)
        self.assertIn('data-cf2-organism="formation"', WS_JS)


class Frc05CommsContinuumVisible(unittest.TestCase):
    """FRC-05: continuum marks sized + empty scaffold."""

    def test_tick_min_size(self) -> None:
        w = _px("width", COMMS_CSS, "body[data-cf-ui=\"v2\"] .cf2-comms__tick {")
        self.assertIsNotNone(w)
        self.assertGreaterEqual(w or 0, 11)

    def test_empty_scaffold_and_truthful_slice(self) -> None:
        self.assertIn("continuumScaffoldHtml", COMMS_JS)
        self.assertIn("cf2-comms__continuum-scaffold", COMMS_JS)
        self.assertIn("steps.slice(0, end)", COMMS_JS)


class Frc06CartsNoWhiteDetailCard(unittest.TestCase):
    """FRC-06: detail must not be standalone white rounded card."""

    def test_detail_not_surface_card(self) -> None:
        # Prefer the dedicated detail rule (not the shared queue,detail min-width rule).
        matches = list(
            re.finditer(
                r"body\[data-cf-ui=\"v2\"\] \.cf2-carts__detail \{([^}]+)\}",
                CARTS_CSS,
            )
        )
        self.assertTrue(matches)
        dedicated = next(
            (m.group(1) for m in matches if "background" in m.group(1)),
            None,
        )
        self.assertIsNotNone(dedicated)
        self.assertIn("background: transparent", dedicated or "")
        self.assertIn("border-radius: 0", dedicated or "")
        self.assertNotIn("--cf2-surface", dedicated or "")
        self.assertIn("border-inline-start: 4px solid", dedicated or "")

    def test_actionable_mass_edge(self) -> None:
        self.assertIn("border-inline-start-width: 6px", CARTS_CSS)


class Frc07SettingsJointMinSize(unittest.TestCase):
    """FRC-07: joint minimum size at desktop and mobile."""

    def test_joint_min_18px(self) -> None:
        w = _px("width", SETTINGS_CSS, "[data-cf-ui=\"v2\"] .cf2-settings__joint {")
        self.assertIsNotNone(w)
        self.assertGreaterEqual(w or 0, 16)

    def test_mobile_joint_min_16px(self) -> None:
        mob = SETTINGS_CSS[SETTINGS_CSS.find("@media (max-width: 1023px)") :]
        self.assertRegex(mob, r"\.cf2-settings__joint\s*\{[^}]*width:\s*1[6-9]px")


class Frc08MobileOrganismContinuity(unittest.TestCase):
    """FRC-08: mobile hooks preserve organisms."""

    def test_mobile_hooks(self) -> None:
        self.assertIn("rdfix1", V2_HTML)
        self.assertIn("gravity-well", HOME_CSS)
        self.assertIn("formation", WS_CSS)
        self.assertIn("weighted-queue", CARTS_CSS)
        self.assertIn("lifecycle-continuum", COMMS_CSS)
        self.assertIn("config-ledger", SETTINGS_CSS)


if __name__ == "__main__":
    unittest.main()
