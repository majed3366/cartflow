# -*- coding: utf-8 -*-
"""Canonical Merchant visual identity contract — structure only, no secrets."""
from __future__ import annotations

from typing import Iterable

VISUAL_SYSTEM_VERSION = "merchant-visual-system-v1"
FIGMA_PARITY_CONTRACT = "visual-language-constitution-v1"
VISUAL_LAW_SET = "constitution-v1+semantic-visual-model-v1"
FIGMA_IDENTITY_PARITY = "pass"
REGRESSION_GATE = "MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE"

# Constitution states the semantic model currently does not drive.
# They are superseded, not missing implementations.
CONSTITUTION_STATES_SUPERSEDED_BY_SEMANTIC_MODEL = (
    "momentum / living-route animation",
    "evidence density sparse/gathering/mixed/aligned/converging",
    "CO kinds without a bounded semantic variable",
)

VISUAL_INVARIANTS = {
    "VIS-INV-01": "Home and Workspace remain the strongest CartFlow identity anchors.",
    "VIS-INV-02": "No canonical surface may collapse into generic card-grid SaaS composition.",
    "VIS-INV-03": "Signature geometry remains recognizable without logo or color.",
    "VIS-INV-04": "Semantic truth overrides decorative symmetry.",
    "VIS-INV-05": "Core Silence remains intentional, not empty or generic.",
    "VIS-INV-06": "Carts / Communication / Settings share CartFlow grammar without becoming copies of Home.",
    "VIS-INV-07": "Mobile preserves structural identity, not just responsive layout.",
    "VIS-INV-08": "Any future material visual change must retain traceability to an approved visual law or explicitly supersede it.",
    "VIS-INV-09": "No visual implementation may weaken semantic truth mappings in semantic-visual-model-v1.",
    "VIS-INV-10": "Current Shell remains canonical unless separately authorized.",
}

# Binding visual laws still in force after semantic-visual-model-v1 filter.
CANONICAL_VISUAL_LAWS = (
    "VL-DNA-01-open-geometry",
    "VL-DNA-02-controlled-interruption",
    "VL-DNA-03-central-silence",
    "VL-DNA-04-tapered-direction",
    "VL-DNA-05-asymmetric-balance",
    "VL-DNA-06-densification-via-sufficiency",
    "VL-DNA-07-recovery-scoop",
    "VL-DNA-08-directional-termination",
    "VL-CO-01-truth-supported-roles",
    "VL-HOME-01-executive-scene",
    "VL-WS-01-decision-object",
    "VL-MASS-01-readiness",
    "VL-TENS-01-conflict-block",
    "VL-EV-01-sufficiency-field",
    "VL-SIL-01-intentional-silence",
    "VL-DIR-01-rtl-start-edge",
    "VL-MOB-01-structural-identity",
    "VL-SHELL-01-canonical-shell",
    "VL-OPS-01-shared-grammar-not-home-copies",
)

FIGMA_MAPPED_PRIMITIVES = (
    "cf2-co__glyph",
    "cf2-co-row",
    "cf2-evfield",
    "cf2-mtrace",
    "cf2-route",
    "cf2-dmass",
    "cf2-capsule",
    "cf2-taper",
    "cf2-terminus",
    "cf2-home__board",
    "cf2-dobj--primary",
    "data-cf2-organism",
)

CANONICAL_SHELL_MARKERS = (
    "cf2-utility",
    "cf2-global",
    "cf2-ctx",
    "cf2-stage",
    'data-cf-ui="v2"',
)

CANONICAL_HOME_EMITTERS = (
    "cf2-home__kicker",
    "مشهد تنفيذي",
    "gravity-well",
    "cf2-evfield",
    "cf2-home__board",
    "مركز الجاذبية",
    "data-cf2-organism",
)

CANONICAL_WORKSPACE_EMITTERS = (
    "formation",
    "cf2-dmass",
    "cf2-route",
    "cf2-dobj--primary",
    "data-cf2-organism",
)

CANONICAL_CARTS_EMITTERS = (
    "cf2-carts__empty",
    "cf2-carts__row",
    "cf2-carts__detail",
    "weighted-queue",
)

CANONICAL_COMMS_EMITTERS = (
    "cf2-comms__empty",
    "cf2-comms__row",
    "cf2-comms__detail",
    "Not an inbox",
    "lifecycle-continuum",
)

CANONICAL_SETTINGS_EMITTERS = (
    "cf2-settings__row",
    "cf2-settings__detail",
    "cf2-settings__state",
    "config-ledger",
)

FORBIDDEN_CANONICAL_MARKERS = (
    "merchant_frame_v1.css",
    "merchant_experience_home_v1.css",
    "home_executive_summary_v1.js",
    "merchant_dashboard_home_v1.css",
    'data-cf-frame="v1"',
    "cf-rail__brand",
    "meif-card",
    "hes-root",
)

LEGACY_SIGNATURE = {
    "merchant_app.html": "MUST_NOT_RENDER_CANONICALLY",
    "merchant_ui_v1": "ROLLBACK_ONLY",
    "merchant_frame_v1.css": "ROLLBACK_ONLY",
    "home_executive_summary_v1.js": "ROLLBACK_ONLY",
    "HomeExecutiveSummaryV1": "ROLLBACK_ONLY",
    "cf-rail": "ROLLBACK_ONLY",
    "meif-card": "LEGACY_ONLY",
    "merchant_experience_home_v1.css": "ROLLBACK_ONLY",
    "data-cf-frame=v1": "ROLLBACK_ONLY",
    "merchant_ui_v2_language.css": "STILL_SHARED",
    "/api/dashboard/summary": "STILL_SHARED",
    "/api/cart-workspace/v1/projection": "STILL_SHARED",
}


def missing_markers(text: str, required: Iterable[str]) -> list[str]:
    return [m for m in required if m not in (text or "")]


def forbidden_present(text: str, forbidden: Iterable[str] = FORBIDDEN_CANONICAL_MARKERS) -> list[str]:
    return [m for m in forbidden if m in (text or "")]


__all__ = [
    "CANONICAL_CARTS_EMITTERS",
    "CANONICAL_COMMS_EMITTERS",
    "CANONICAL_HOME_EMITTERS",
    "CANONICAL_SETTINGS_EMITTERS",
    "CANONICAL_SHELL_MARKERS",
    "CANONICAL_WORKSPACE_EMITTERS",
    "FORBIDDEN_CANONICAL_MARKERS",
    "LEGACY_SIGNATURE",
    "CANONICAL_VISUAL_LAWS",
    "CONSTITUTION_STATES_SUPERSEDED_BY_SEMANTIC_MODEL",
    "FIGMA_IDENTITY_PARITY",
    "FIGMA_MAPPED_PRIMITIVES",
    "FIGMA_PARITY_CONTRACT",
    "REGRESSION_GATE",
    "VISUAL_INVARIANTS",
    "VISUAL_LAW_SET",
    "VISUAL_SYSTEM_VERSION",
    "forbidden_present",
    "missing_markers",
]
