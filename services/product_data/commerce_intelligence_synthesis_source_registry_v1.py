# -*- coding: utf-8 -*-
"""
Commerce Intelligence Synthesis — source contract registry (cisrc_v1).

Only governed canonical contracts. No provider-specific or raw payloads.
"""
from __future__ import annotations

from typing import Any

from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    SOURCE_CONTRACT_REGISTRY_VERSION_V1,
)

SOURCE_CONTRACTS_V1: tuple[dict[str, Any], ...] = (
    {
        "source_domain": "knowledge",
        "contract_key": "generate_knowledge_v1",
        "contract_version": "kf_v1",
        "accepted_subject_types": ("store", "product"),
        "required_fields": ("statements", "canonical_fingerprint", "ok"),
        "timestamp_authority": "as_of",
        "identity_authority": "subject_id",
        "freshness_policy": "bounded_assembly_window",
        "deduplication_key": "knowledge_id",
        "required": True,
        "unsupported_reason_behavior": "block_required_rules",
    },
    {
        "source_domain": "product_hesitation",
        "contract_key": "product_hesitation_mapping_read_v1",
        "contract_version": "phm_v1",
        "accepted_subject_types": ("product", "hesitation_reason"),
        "required_fields": ("reason", "stable_identity_key", "store_slug"),
        "timestamp_authority": "captured_at",
        "identity_authority": "stable_identity_key",
        "freshness_policy": "bounded_window_filter",
        "deduplication_key": "id",
        "required": False,
        "unsupported_reason_behavior": "mark_missing_optional",
    },
    {
        "source_domain": "product_purchase",
        "contract_key": "product_purchase_mapping_read_v1",
        "contract_version": "ppm_v1",
        "accepted_subject_types": ("product",),
        "required_fields": ("stable_identity_key", "store_slug"),
        "timestamp_authority": "purchased_at",
        "identity_authority": "stable_identity_key",
        "freshness_policy": "bounded_window_filter",
        "deduplication_key": "id",
        "required": False,
        "unsupported_reason_behavior": "mark_missing_optional",
    },
    {
        "source_domain": "commerce_signals",
        "contract_key": "load_store_commerce_signals_v1",
        "contract_version": "commerce_signals_v1",
        "accepted_subject_types": ("store", "cart_cohort"),
        "required_fields": ("signals", "ok"),
        "timestamp_authority": "signal_event_time",
        "identity_authority": "recovery_key",
        "freshness_policy": "recent_recovery_keys",
        "deduplication_key": "signal_type+evidence_refs",
        "required": False,
        "unsupported_reason_behavior": "mark_missing_optional",
    },
)


def source_contract_by_domain_v1(domain: str) -> dict[str, Any] | None:
    key = (domain or "").strip()
    for row in SOURCE_CONTRACTS_V1:
        if row["source_domain"] == key:
            return dict(row)
    return None


def source_registry_valid_v1() -> bool:
    domains = [r["source_domain"] for r in SOURCE_CONTRACTS_V1]
    if len(domains) != len(set(domains)):
        return False
    required = [r for r in SOURCE_CONTRACTS_V1 if r.get("required")]
    return bool(required) and SOURCE_CONTRACT_REGISTRY_VERSION_V1 == "cisrc_v1"


def source_registry_summary_v1() -> dict[str, Any]:
    return {
        "registry_version": SOURCE_CONTRACT_REGISTRY_VERSION_V1,
        "contract_count": len(SOURCE_CONTRACTS_V1),
        "domains": [r["source_domain"] for r in SOURCE_CONTRACTS_V1],
        "required_domains": [
            r["source_domain"] for r in SOURCE_CONTRACTS_V1 if r.get("required")
        ],
        "valid": source_registry_valid_v1(),
    }


__all__ = [
    "SOURCE_CONTRACTS_V1",
    "source_contract_by_domain_v1",
    "source_registry_valid_v1",
    "source_registry_summary_v1",
]
