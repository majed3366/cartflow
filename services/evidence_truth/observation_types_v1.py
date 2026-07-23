# -*- coding: utf-8 -*-
"""
Canonical observation types for WP-ET-03 priority Raw kinds (Blueprint Stage 2).

Provider-neutral names. Adapters map provider payloads into these types.
"""
from __future__ import annotations

from services.evidence_truth.families_v1 import (
    FAMILY_BEHAVIOUR,
    FAMILY_CART,
    FAMILY_COMMUNICATION,
    FAMILY_PRODUCT,
    FAMILY_PURCHASE,
    FAMILY_RECOVERY,
    FAMILY_VISITOR,
)

# Priority Raw kinds (Stage 2 + recovery WP-ET-06 + behaviour WP-ET-07)
RAW_KIND_CART_EVENT = "cart_event"
RAW_KIND_PURCHASE = "purchase"
RAW_KIND_COMMUNICATION = "communication"
RAW_KIND_PRODUCT_SIGNAL = "product_signal"
RAW_KIND_TRAFFIC = "traffic"
RAW_KIND_RECOVERY = "recovery"
RAW_KIND_BEHAVIOUR = "behaviour"

PRIORITY_RAW_KINDS_V1: frozenset[str] = frozenset(
    {
        RAW_KIND_CART_EVENT,
        RAW_KIND_PURCHASE,
        RAW_KIND_COMMUNICATION,
        RAW_KIND_PRODUCT_SIGNAL,
        RAW_KIND_TRAFFIC,
        RAW_KIND_RECOVERY,
        RAW_KIND_BEHAVIOUR,
    }
)

# Canonical observation_type values (provider-neutral)
OBS_CART_STATE = "cart_state_observed_v1"
OBS_PURCHASE = "purchase_observed_v1"
OBS_MESSAGE_LIFECYCLE = "message_lifecycle_observed_v1"
OBS_PRODUCT_INTEREST = "product_interest_observed_v1"
OBS_STORE_VISIT = "store_visit_observed_v1"
OBS_RECOVERY_PROGRESSION = "recovery_progression_observed_v1"
OBS_HESITATION_REASON = "hesitation_reason_observed_v1"

RAW_KIND_TO_OBSERVATION_TYPE_V1: dict[str, str] = {
    RAW_KIND_CART_EVENT: OBS_CART_STATE,
    RAW_KIND_PURCHASE: OBS_PURCHASE,
    RAW_KIND_COMMUNICATION: OBS_MESSAGE_LIFECYCLE,
    RAW_KIND_PRODUCT_SIGNAL: OBS_PRODUCT_INTEREST,
    RAW_KIND_TRAFFIC: OBS_STORE_VISIT,
    RAW_KIND_RECOVERY: OBS_RECOVERY_PROGRESSION,
    RAW_KIND_BEHAVIOUR: OBS_HESITATION_REASON,
}

# Raw kind → canonical Evidence family (ownership / Observation governance)
RAW_KIND_TO_FAMILY_V1: dict[str, str] = {
    RAW_KIND_CART_EVENT: FAMILY_CART,
    RAW_KIND_PURCHASE: FAMILY_PURCHASE,
    RAW_KIND_COMMUNICATION: FAMILY_COMMUNICATION,
    RAW_KIND_PRODUCT_SIGNAL: FAMILY_PRODUCT,
    RAW_KIND_TRAFFIC: FAMILY_VISITOR,
    RAW_KIND_RECOVERY: FAMILY_RECOVERY,
    RAW_KIND_BEHAVIOUR: FAMILY_BEHAVIOUR,
}

CHANNEL_WIDGET = "widget"
CHANNEL_API = "api"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_PROVIDER_WEBHOOK = "provider_webhook"
CHANNEL_SDK = "sdk"
CHANNEL_UNKNOWN = "unknown"

# Observation constitutional metadata vocabulary (WP-ET-04)
TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC = "wall_clock_utc"
TIMESTAMP_AUTHORITY_PLATFORM_QTC = "platform_time_authority_qtc"
OBS_ACCOUNTING_RECORDED = "recorded"
OBS_ACCOUNTING_REJECTED = "rejected"
OBS_ACCOUNTING_PENDING = "pending"
OBS_OBSERVABILITY_OPS_VISIBLE = "ops_visible"
OBS_OBSERVABILITY_HIDDEN = "hidden"
OBSERVATION_GOVERNANCE_VERSION = 1
