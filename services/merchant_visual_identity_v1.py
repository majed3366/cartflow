# -*- coding: utf-8 -*-
"""Canonical Merchant visual identity contract — structure only, no secrets."""
from __future__ import annotations

from typing import Iterable

VISUAL_SYSTEM_VERSION = "merchant-visual-system-v1"
FIGMA_PARITY_CONTRACT = "visual-language-constitution-v1"
REGRESSION_GATE = "MERCHANT_VISUAL_IDENTITY_REGRESSION_GATE"

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
    "cf2-co-row",
    "cf2-evfield",
    "cf2-home__board",
    "مركز الجاذبية",
)

CANONICAL_WORKSPACE_EMITTERS = (
    "cf2-co-row",
    "cf2-dmass",
    "cf2-route",
    "cf2-dobj--primary",
)

CANONICAL_CARTS_EMITTERS = (
    "cf2-carts__empty",
    "cf2-carts__row",
    "cf2-carts__detail",
)

CANONICAL_COMMS_EMITTERS = (
    "cf2-comms__empty",
    "cf2-comms__row",
    "cf2-comms__detail",
    "Not an inbox",
)

CANONICAL_SETTINGS_EMITTERS = (
    "cf2-settings__row",
    "cf2-settings__detail",
    "cf2-settings__state",
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
    "FIGMA_MAPPED_PRIMITIVES",
    "FIGMA_PARITY_CONTRACT",
    "REGRESSION_GATE",
    "VISUAL_SYSTEM_VERSION",
    "forbidden_present",
    "missing_markers",
]
