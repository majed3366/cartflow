# -*- coding: utf-8 -*-
"""MEIF V1 — Integration Map (page inventory + consumer contracts)."""
from __future__ import annotations

from typing import Any

from services.product_data.merchant_experience_integration_types_v1 import (
    INTEGRATION_MAP_VERSION_V1,
    PAGE_CARTS,
    PAGE_COMMUNICATION,
    PAGE_DECISION,
    PAGE_HOME,
    PAGE_SETTINGS,
    QUESTION_CARTS,
    QUESTION_COMMUNICATION,
    QUESTION_DECISION,
    QUESTION_HOME,
    QUESTION_SETTINGS,
)


def _page(
    *,
    page_id: str,
    owner: str,
    merchant_question: str,
    current_sources: tuple[str, ...],
    governed_sources: tuple[str, ...],
    duplicated_logic: tuple[str, ...],
    obsolete_logic: tuple[str, ...],
    placeholders: tuple[str, ...],
    missing_integrations: tuple[str, ...],
    nav_target: str,
) -> dict[str, Any]:
    return {
        "page_id": page_id,
        "page_owner": owner,
        "merchant_question_answered": merchant_question,
        "current_data_sources": list(current_sources),
        "governed_data_sources": list(governed_sources),
        "duplicated_logic": list(duplicated_logic),
        "obsolete_logic": list(obsolete_logic),
        "placeholder_sections": list(placeholders),
        "missing_integrations": list(missing_integrations),
        "nav_target": nav_target,
        "version": INTEGRATION_MAP_VERSION_V1,
    }


INTEGRATION_MAP_V1: dict[str, dict[str, Any]] = {
    PAGE_HOME: _page(
        page_id=PAGE_HOME,
        owner="merchant_experience_integration_foundation_v1",
        merchant_question=QUESTION_HOME,
        current_sources=(
            "merchant_home_composition_v1",
            "knowledge_layer_v1",
            "dashboard_summary_kpis",
        ),
        governed_sources=(
            "surface_composition",
            "commercial_guidance",
            "knowledge",
            "merchant_operational_state",
        ),
        duplicated_logic=("home_semantic_composition_select_rank", "page_owned_empty_calm"),
        obsolete_logic=("skeleton_as_default_when_ops_truth_exists",),
        placeholders=("ma-home-experience--loading", "تجهز ملخص عملك اليومي"),
        missing_integrations=("scf_home_package", "guidance_highlights", "ops_kpi_truth"),
        nav_target="#home",
    ),
    PAGE_DECISION: _page(
        page_id=PAGE_DECISION,
        owner="merchant_experience_integration_foundation_v1",
        merchant_question=QUESTION_DECISION,
        current_sources=("cart_workspace_projection_v1",),
        governed_sources=("surface_composition", "commercial_guidance", "knowledge"),
        duplicated_logic=("workspace_admission_vs_scf",),
        obsolete_logic=("hidden_nav_when_flag_off",),
        placeholders=("blank_workspace_hash",),
        missing_integrations=("always_on_nav", "scf_decision_package"),
        nav_target="#workspace",
    ),
    PAGE_CARTS: _page(
        page_id=PAGE_CARTS,
        owner="merchant_experience_integration_foundation_v1",
        merchant_question=QUESTION_CARTS,
        current_sources=("api_dashboard_normal_carts", "rsc_loading_controller"),
        governed_sources=("surface_composition", "merchant_operational_state"),
        duplicated_logic=("page_owned_wait_gates",),
        obsolete_logic=("false_please_wait_with_durable_carts",),
        placeholders=("ma-carts-unified-loading", "يرجى الانتظار قليلاً"),
        missing_integrations=("ops_durable_cart_truth", "scf_carts_package"),
        nav_target="#carts",
    ),
    PAGE_COMMUNICATION: _page(
        page_id=PAGE_COMMUNICATION,
        owner="merchant_experience_integration_foundation_v1",
        merchant_question=QUESTION_COMMUNICATION,
        current_sources=("messages_page", "whatsapp_settings_fallback"),
        governed_sources=("surface_composition", "merchant_operational_state"),
        duplicated_logic=("comms_nav_to_settings_whatsapp",),
        obsolete_logic=("settings_as_communication_surface",),
        placeholders=("جاري تحميل إعدادات واتساب",),
        missing_integrations=("dedicated_communication_page", "recovery_followup_state"),
        nav_target="#communication",
    ),
    PAGE_SETTINGS: _page(
        page_id=PAGE_SETTINGS,
        owner="merchant_experience_integration_foundation_v1",
        merchant_question=QUESTION_SETTINGS,
        current_sources=("whatsapp_settings", "widget_settings", "account_settings"),
        governed_sources=("surface_composition",),
        duplicated_logic=(),
        obsolete_logic=("settings_nav_defaulting_to_whatsapp",),
        placeholders=(),
        missing_integrations=("settings_nav_to_settings_hash",),
        nav_target="#settings",
    ),
}


def integration_map_v1() -> dict[str, Any]:
    return {
        "version": INTEGRATION_MAP_VERSION_V1,
        "pages": dict(INTEGRATION_MAP_V1),
    }


def integration_map_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in (
        PAGE_HOME,
        PAGE_DECISION,
        PAGE_CARTS,
        PAGE_COMMUNICATION,
        PAGE_SETTINGS,
    ):
        if key not in INTEGRATION_MAP_V1:
            errors.append(f"missing_page:{key}")
    return (len(errors) == 0, errors)


__all__ = [
    "INTEGRATION_MAP_V1",
    "integration_map_v1",
    "integration_map_valid_v1",
]
