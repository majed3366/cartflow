# -*- coding: utf-8 -*-
"""Commercial Decision Commitment V1 — contracts, vocabularies, windows."""
from __future__ import annotations

from datetime import timedelta
from typing import FrozenSet

LAYER_VERSION = "commercial_decision_commitment_v1"

PHASE_ACTION_CHOSEN = "ACTION_CHOSEN"
PHASE_UNDER_MEASUREMENT = "UNDER_MEASUREMENT"
PHASE_RECHECK_DUE = "RECHECK_DUE"

PHASES = frozenset(
    {PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT, PHASE_RECHECK_DUE}
)

AUTHORITY_CARTFLOW_EXECUTION = "cartflow_execution"
AUTHORITY_MERCHANT_EXECUTION_CONFIRM = "merchant_execution_confirm"

AUTHORITIES = frozenset(
    {AUTHORITY_CARTFLOW_EXECUTION, AUTHORITY_MERCHANT_EXECUTION_CONFIRM}
)

# Families where merchant confirmation is accepted as execution evidence (V1).
MERCHANT_CONFIRM_FAMILY_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        "shipping_friction",
        "price_hesitation",
        "product_confidence",
        "recovery_hesitation",
        "communication_followup",
        "cart_behavior",
    }
)

CLOSE_MERCHANT_CANCEL = "merchant_cancel"
CLOSE_MERCHANT_ABANDON = "merchant_abandon"
CLOSE_OPPORTUNITY_INVALID = "opportunity_invalid"
CLOSE_SUPERSEDED = "superseded"
CLOSE_RECHECK_NEW_DECISION = "recheck_new_decision"
CLOSE_STORE_INVALIDATED = "store_invalidated"

CLOSE_REASONS_MERCHANT = frozenset({CLOSE_MERCHANT_CANCEL, CLOSE_MERCHANT_ABANDON})
CLOSE_REASONS_SYSTEM = frozenset(
    {
        CLOSE_OPPORTUNITY_INVALID,
        CLOSE_SUPERSEDED,
        CLOSE_RECHECK_NEW_DECISION,
        CLOSE_STORE_INVALIDATED,
    }
)
CLOSE_REASONS = CLOSE_REASONS_MERCHANT | CLOSE_REASONS_SYSTEM

FORBIDDEN_CLOSE_REASONS = frozenset(
    {"won", "lost", "learned", "purchase", "measurement_expired"}
)

DECISION_SNAPSHOT_SCHEMA = "cdc_decision_snapshot_v1"
BASELINE_SNAPSHOT_SCHEMA = "cdc_measurement_baseline_v1"
SNAPSHOT_MAX_BYTES = 4096
SIGNAL_COUNTS_MAX_KEYS = 16

DEFAULT_MEASUREMENT_WINDOW_DAYS = 7

# Server → Console mode (presentation only; not persisted as SoT)
PHASE_TO_CONSOLE_MODE = {
    PHASE_ACTION_CHOSEN: "accepted",
    PHASE_UNDER_MEASUREMENT: "measuring",
    PHASE_RECHECK_DUE: "recheck",
}


def resolve_measurement_window_days(family: str) -> int:
    _ = family
    return DEFAULT_MEASUREMENT_WINDOW_DAYS


def resolve_measurement_window(family: str) -> timedelta:
    return timedelta(days=resolve_measurement_window_days(family))


__all__ = [
    "AUTHORITIES",
    "AUTHORITY_CARTFLOW_EXECUTION",
    "AUTHORITY_MERCHANT_EXECUTION_CONFIRM",
    "BASELINE_SNAPSHOT_SCHEMA",
    "CLOSE_MERCHANT_ABANDON",
    "CLOSE_MERCHANT_CANCEL",
    "CLOSE_OPPORTUNITY_INVALID",
    "CLOSE_REASONS",
    "CLOSE_REASONS_MERCHANT",
    "CLOSE_REASONS_SYSTEM",
    "CLOSE_RECHECK_NEW_DECISION",
    "CLOSE_STORE_INVALIDATED",
    "CLOSE_SUPERSEDED",
    "DECISION_SNAPSHOT_SCHEMA",
    "DEFAULT_MEASUREMENT_WINDOW_DAYS",
    "FORBIDDEN_CLOSE_REASONS",
    "LAYER_VERSION",
    "MERCHANT_CONFIRM_FAMILY_ALLOWLIST",
    "PHASE_ACTION_CHOSEN",
    "PHASE_RECHECK_DUE",
    "PHASE_TO_CONSOLE_MODE",
    "PHASE_UNDER_MEASUREMENT",
    "PHASES",
    "SIGNAL_COUNTS_MAX_KEYS",
    "SNAPSHOT_MAX_BYTES",
    "resolve_measurement_window",
    "resolve_measurement_window_days",
]
