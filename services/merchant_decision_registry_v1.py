# -*- coding: utf-8 -*-
"""
Merchant Decision Registry v1 — governed decision template metadata.

Single registry for stable decision_id definitions consumed by the decision layer.
Presentation reads decision payloads — never defines decision wording or contracts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

REGISTRY_VERSION = "v1"

# Stable decision identifiers (extend here — consumers stay unchanged)
DECISION_ID_OBTAIN_CONTACT = "decision_obtain_contact"
DECISION_ID_FIX_CHANNEL = "decision_fix_channel"
DECISION_ID_CONTACT_CUSTOMER = "decision_contact_customer"
DECISION_ID_MONITOR_RETURN = "decision_monitor_return"
DECISION_ID_KL_OBSERVATION = "decision_kl_observation"

# Maps legacy action keys from merchant_decision_layer_v1 resolve path
ACTION_KEY_OBTAIN_CONTACT = "obtain_contact"
ACTION_KEY_FIX_CHANNEL = "fix_channel"
ACTION_KEY_CONTACT_CUSTOMER = "contact_customer"
ACTION_KEY_MONITOR = "monitor"


@dataclass(frozen=True)
class MerchantDecisionRegistryEntry:
    decision_id: str
    action_key: str
    commercial_goal: str
    default_merchant_action: str
    verification_method: str
    owner_module: str
    merge_key_prefix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action_key": self.action_key,
            "commercial_goal": self.commercial_goal,
            "default_merchant_action": self.default_merchant_action,
            "verification_method": self.verification_method,
            "owner_module": self.owner_module,
            "merge_key_prefix": self.merge_key_prefix,
        }


_MERCHANT_DECISION_REGISTRY: dict[str, MerchantDecisionRegistryEntry] = {
    DECISION_ID_OBTAIN_CONTACT: MerchantDecisionRegistryEntry(
        decision_id=DECISION_ID_OBTAIN_CONTACT,
        action_key=ACTION_KEY_OBTAIN_CONTACT,
        commercial_goal="recover_revenue",
        default_merchant_action="execute",
        verification_method="lifecycle_truth_query + phone_presence_check",
        owner_module="merchant_decision_layer_v1",
        merge_key_prefix="cart",
    ),
    DECISION_ID_FIX_CHANNEL: MerchantDecisionRegistryEntry(
        decision_id=DECISION_ID_FIX_CHANNEL,
        action_key=ACTION_KEY_FIX_CHANNEL,
        commercial_goal="improve_operations",
        default_merchant_action="execute",
        verification_method="recovery_log_fail_status + provider_truth_check",
        owner_module="merchant_decision_layer_v1",
        merge_key_prefix="cart",
    ),
    DECISION_ID_CONTACT_CUSTOMER: MerchantDecisionRegistryEntry(
        decision_id=DECISION_ID_CONTACT_CUSTOMER,
        action_key=ACTION_KEY_CONTACT_CUSTOMER,
        commercial_goal="recover_revenue",
        default_merchant_action="execute",
        verification_method="intervention_executable_flag + wa_me_href",
        owner_module="merchant_decision_layer_v1",
        merge_key_prefix="cart",
    ),
    DECISION_ID_MONITOR_RETURN: MerchantDecisionRegistryEntry(
        decision_id=DECISION_ID_MONITOR_RETURN,
        action_key=ACTION_KEY_MONITOR,
        commercial_goal="improve_conversion",
        default_merchant_action="monitor",
        verification_method="lifecycle_return_state_check",
        owner_module="merchant_decision_layer_v1",
        merge_key_prefix="cart",
    ),
    DECISION_ID_KL_OBSERVATION: MerchantDecisionRegistryEntry(
        decision_id=DECISION_ID_KL_OBSERVATION,
        action_key="",
        commercial_goal="reduce_hesitation",
        default_merchant_action="none",
        verification_method="knowledge_insight_key + claim_evidence_id",
        owner_module="merchant_decision_layer_v1",
        merge_key_prefix="insight",
    ),
}

_ACTION_KEY_TO_DECISION_ID: dict[str, str] = {
    ACTION_KEY_OBTAIN_CONTACT: DECISION_ID_OBTAIN_CONTACT,
    ACTION_KEY_FIX_CHANNEL: DECISION_ID_FIX_CHANNEL,
    ACTION_KEY_CONTACT_CUSTOMER: DECISION_ID_CONTACT_CUSTOMER,
    ACTION_KEY_MONITOR: DECISION_ID_MONITOR_RETURN,
}


def get_merchant_decision_registry_entry(
    decision_id: str,
) -> Optional[MerchantDecisionRegistryEntry]:
    key = (decision_id or "").strip()
    if not key:
        return None
    return _MERCHANT_DECISION_REGISTRY.get(key)


def decision_id_for_action_key(action_key: str) -> Optional[str]:
    return _ACTION_KEY_TO_DECISION_ID.get((action_key or "").strip().lower())


def build_merchant_decision_registry_payload() -> dict[str, Any]:
    return {
        "version": REGISTRY_VERSION,
        "entries": [e.to_dict() for e in _MERCHANT_DECISION_REGISTRY.values()],
    }


__all__ = [
    "ACTION_KEY_CONTACT_CUSTOMER",
    "ACTION_KEY_FIX_CHANNEL",
    "ACTION_KEY_MONITOR",
    "ACTION_KEY_OBTAIN_CONTACT",
    "DECISION_ID_CONTACT_CUSTOMER",
    "DECISION_ID_FIX_CHANNEL",
    "DECISION_ID_KL_OBSERVATION",
    "DECISION_ID_MONITOR_RETURN",
    "DECISION_ID_OBTAIN_CONTACT",
    "REGISTRY_VERSION",
    "build_merchant_decision_registry_payload",
    "decision_id_for_action_key",
    "get_merchant_decision_registry_entry",
]
