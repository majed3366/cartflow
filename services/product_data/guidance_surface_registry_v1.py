# -*- coding: utf-8 -*-
"""Guidance Routing Foundation V1 — canonical merchant surface registry."""
from __future__ import annotations

from typing import Any

from services.product_data.guidance_routing_types_v1 import (
    SCOPE_CONTROL,
    SCOPE_FOLLOW_UP,
    SCOPE_FULL,
    SCOPE_INTERNAL,
    SCOPE_OPERATIONAL,
    SCOPE_SUMMARY,
    SURFACE_CARTS,
    SURFACE_COMMUNICATION,
    SURFACE_DECISION,
    SURFACE_HOME,
    SURFACE_REGISTRY_VERSION_V1,
    SURFACE_SETTINGS,
)


def _surface(
    *,
    key: str,
    responsibility: str,
    accepted_scopes: tuple[str, ...],
    prohibited_scopes: tuple[str, ...],
    accepted_subjects: tuple[str, ...],
    prohibited_subjects: tuple[str, ...],
    accepted_guidance_statuses: tuple[str, ...],
    prerequisites: tuple[str, ...],
    active: bool = True,
) -> dict[str, Any]:
    return {
        "surface_key": key,
        "surface_responsibility": responsibility,
        "accepted_guidance_scopes": list(accepted_scopes),
        "prohibited_guidance_scopes": list(prohibited_scopes),
        "accepted_subject_types": list(accepted_subjects),
        "prohibited_subject_types": list(prohibited_subjects),
        "accepted_guidance_statuses": list(accepted_guidance_statuses),
        "routing_prerequisites": list(prerequisites),
        "surface_contract_version": SURFACE_REGISTRY_VERSION_V1,
        "active": active,
    }


SURFACE_REGISTRY_V1: dict[str, dict[str, Any]] = {
    SURFACE_HOME: _surface(
        key=SURFACE_HOME,
        responsibility="What should the merchant know now?",
        accepted_scopes=(SCOPE_SUMMARY, SCOPE_INTERNAL),
        prohibited_scopes=(SCOPE_CONTROL,),
        accepted_subjects=("store", "product", "cart"),
        prohibited_subjects=(),
        accepted_guidance_statuses=("active", "deferred", "abstained"),
        prerequisites=("commercial_guidance_current",),
    ),
    SURFACE_DECISION: _surface(
        key=SURFACE_DECISION,
        responsibility="What decision requires merchant reasoning or review?",
        accepted_scopes=(SCOPE_FULL, SCOPE_SUMMARY, SCOPE_INTERNAL),
        prohibited_scopes=(SCOPE_CONTROL,),
        accepted_subjects=("store", "product", "cart"),
        prohibited_subjects=(),
        accepted_guidance_statuses=("active", "deferred", "abstained"),
        prerequisites=("commercial_guidance_current",),
    ),
    SURFACE_CARTS: _surface(
        key=SURFACE_CARTS,
        responsibility="What is happening in carts, and what operational attention is required?",
        accepted_scopes=(SCOPE_OPERATIONAL, SCOPE_SUMMARY),
        prohibited_scopes=(SCOPE_CONTROL, SCOPE_FOLLOW_UP),
        accepted_subjects=("cart", "product", "store"),
        prohibited_subjects=(),
        accepted_guidance_statuses=("active",),
        prerequisites=("commercial_guidance_current", "cart_related_when_operational"),
    ),
    SURFACE_COMMUNICATION: _surface(
        key=SURFACE_COMMUNICATION,
        responsibility="What happened in customer communication, and what needs follow-up?",
        accepted_scopes=(SCOPE_FOLLOW_UP,),
        prohibited_scopes=(SCOPE_CONTROL, SCOPE_OPERATIONAL),
        accepted_subjects=("store", "cart", "product"),
        prohibited_subjects=(),
        accepted_guidance_statuses=("active",),
        prerequisites=("communication_scope_future",),
    ),
    SURFACE_SETTINGS: _surface(
        key=SURFACE_SETTINGS,
        responsibility="How does the merchant control platform behavior and configuration?",
        accepted_scopes=(SCOPE_CONTROL,),
        prohibited_scopes=(SCOPE_OPERATIONAL, SCOPE_FOLLOW_UP, SCOPE_FULL),
        accepted_subjects=("store",),
        prohibited_subjects=("product", "cart"),
        accepted_guidance_statuses=("active",),
        prerequisites=("configuration_relevance",),
    ),
}


def list_active_surfaces_v1() -> list[str]:
    return sorted(k for k, v in SURFACE_REGISTRY_V1.items() if v.get("active"))


def get_surface_v1(surface_key: str) -> dict[str, Any] | None:
    entry = SURFACE_REGISTRY_V1.get(str(surface_key or ""))
    if not entry or not entry.get("active"):
        return None
    return dict(entry)


def surface_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in (
        SURFACE_HOME,
        SURFACE_DECISION,
        SURFACE_CARTS,
        SURFACE_COMMUNICATION,
        SURFACE_SETTINGS,
    ):
        if key not in SURFACE_REGISTRY_V1:
            errors.append(f"missing_surface:{key}")
    for key, entry in SURFACE_REGISTRY_V1.items():
        if entry.get("surface_key") != key:
            errors.append(f"key_mismatch:{key}")
        # Forbid Home-presentation fields in registry.
        for banned in ("show_on_home", "home_card_title", "home_priority"):
            if banned in entry:
                errors.append(f"home_presentation_field:{banned}")
    return (len(errors) == 0, errors)


__all__ = [
    "SURFACE_REGISTRY_V1",
    "list_active_surfaces_v1",
    "get_surface_v1",
    "surface_registry_valid_v1",
]
