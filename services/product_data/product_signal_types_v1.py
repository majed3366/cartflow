# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — canonical signal catalog (types only).

Facts vocabulary for durable product signals. No scoring, ranking, or decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Families
FAMILY_PRODUCT_EXPOSURE = "product_exposure"
FAMILY_PRODUCT_VIEW = "product_view"
FAMILY_PRODUCT_INTEREST = "product_interest"
FAMILY_PRODUCT_CART_ACTIVITY = "product_cart_activity"
FAMILY_PRODUCT_CHECKOUT_ACTIVITY = "product_checkout_activity"
FAMILY_PRODUCT_PURCHASE = "product_purchase"
FAMILY_PRODUCT_RECOVERY_INTERACTION = "product_recovery_interaction"
FAMILY_PRODUCT_CUSTOMER_RETURN = "product_customer_return"
FAMILY_PRODUCT_EVIDENCE = "product_evidence"

SIGNAL_FAMILIES = frozenset(
    {
        FAMILY_PRODUCT_EXPOSURE,
        FAMILY_PRODUCT_VIEW,
        FAMILY_PRODUCT_INTEREST,
        FAMILY_PRODUCT_CART_ACTIVITY,
        FAMILY_PRODUCT_CHECKOUT_ACTIVITY,
        FAMILY_PRODUCT_PURCHASE,
        FAMILY_PRODUCT_RECOVERY_INTERACTION,
        FAMILY_PRODUCT_CUSTOMER_RETURN,
        FAMILY_PRODUCT_EVIDENCE,
    }
)

# Atomic signal types (past facts)
SIGNAL_PRODUCT_EXPOSED = "product_exposed"  # deferred
SIGNAL_PRODUCT_VIEWED = "product_viewed"  # deferred
SIGNAL_PRODUCT_INTEREST_HESITATION = "product_interest_hesitation"
SIGNAL_PRODUCT_CART_ADDED = "product_cart_added"
SIGNAL_PRODUCT_CART_REMOVED = "product_cart_removed"
SIGNAL_PRODUCT_CART_SYNCED = "product_cart_synced"
SIGNAL_PRODUCT_CART_ABANDONED = "product_cart_abandoned"
SIGNAL_PRODUCT_CHECKOUT_TOUCHED = "product_checkout_touched"
SIGNAL_PRODUCT_PURCHASED = "product_purchased"
SIGNAL_PRODUCT_RECOVERY_STARTED = "product_recovery_started"
SIGNAL_PRODUCT_RECOVERY_PROGRESSED = "product_recovery_progressed"
SIGNAL_PRODUCT_CUSTOMER_RETURNED = "product_customer_returned"
SIGNAL_PRODUCT_EVIDENCE_LINKED = "product_evidence_linked"

SIGNAL_TYPES_WIRED = frozenset(
    {
        SIGNAL_PRODUCT_INTEREST_HESITATION,
        SIGNAL_PRODUCT_CART_ADDED,
        SIGNAL_PRODUCT_CART_REMOVED,
        SIGNAL_PRODUCT_CART_SYNCED,
        SIGNAL_PRODUCT_CART_ABANDONED,
        SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
        SIGNAL_PRODUCT_PURCHASED,
        SIGNAL_PRODUCT_RECOVERY_STARTED,
        SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
        SIGNAL_PRODUCT_CUSTOMER_RETURNED,
        SIGNAL_PRODUCT_EVIDENCE_LINKED,
    }
)

SIGNAL_TYPES_DEFERRED = frozenset(
    {
        SIGNAL_PRODUCT_EXPOSED,
        SIGNAL_PRODUCT_VIEWED,
    }
)

SIGNAL_TYPE_TO_FAMILY: dict[str, str] = {
    SIGNAL_PRODUCT_EXPOSED: FAMILY_PRODUCT_EXPOSURE,
    SIGNAL_PRODUCT_VIEWED: FAMILY_PRODUCT_VIEW,
    SIGNAL_PRODUCT_INTEREST_HESITATION: FAMILY_PRODUCT_INTEREST,
    SIGNAL_PRODUCT_CART_ADDED: FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_REMOVED: FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_SYNCED: FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CART_ABANDONED: FAMILY_PRODUCT_CART_ACTIVITY,
    SIGNAL_PRODUCT_CHECKOUT_TOUCHED: FAMILY_PRODUCT_CHECKOUT_ACTIVITY,
    SIGNAL_PRODUCT_PURCHASED: FAMILY_PRODUCT_PURCHASE,
    SIGNAL_PRODUCT_RECOVERY_STARTED: FAMILY_PRODUCT_RECOVERY_INTERACTION,
    SIGNAL_PRODUCT_RECOVERY_PROGRESSED: FAMILY_PRODUCT_RECOVERY_INTERACTION,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED: FAMILY_PRODUCT_CUSTOMER_RETURN,
    SIGNAL_PRODUCT_EVIDENCE_LINKED: FAMILY_PRODUCT_EVIDENCE,
}

# Sources
SOURCE_CART_STATE_SYNC = "cart_state_sync"
SOURCE_CART_ABANDONED = "cart_abandoned"
SOURCE_REASON_CAPTURE = "reason_capture"
SOURCE_PURCHASE_TRUTH = "purchase_truth"
SOURCE_RECOVERY_TIMELINE = "recovery_truth_timeline"
SOURCE_BEHAVIORAL_RETURN = "behavioral_return"

# Evidence ref types
EVIDENCE_REF_CART_LINE_SNAPSHOT = "cart_line_snapshot"
EVIDENCE_REF_HESITATION_MAPPING = "product_hesitation_mapping"
EVIDENCE_REF_PURCHASE_MAPPING = "product_purchase_mapping"
EVIDENCE_REF_RECOVERY_TIMELINE = "recovery_truth_timeline_event"
EVIDENCE_REF_SESSION = "session"

# Recovery timeline statuses → signal type
RECOVERY_START_STATUSES = frozenset(
    {
        "scheduled",
        "pending",
        "queued",
        "recovery_started",
        "started",
    }
)


@dataclass(frozen=True, slots=True)
class ProductSignalPersistResult:
    inserted: int = 0
    skipped_duplicate: int = 0
    skipped_empty: int = 0
    skipped_invalid: int = 0
    skipped_disabled: int = 0


def signal_family_for_type(signal_type: str) -> Optional[str]:
    return SIGNAL_TYPE_TO_FAMILY.get(str(signal_type or "").strip())


def product_signal_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": getattr(row, "id", None),
        "store_slug": getattr(row, "store_slug", "") or "",
        "session_id": getattr(row, "session_id", "") or "",
        "cart_id": getattr(row, "cart_id", "") or "",
        "recovery_key": getattr(row, "recovery_key", None),
        "stable_identity_key": getattr(row, "stable_identity_key", "") or "",
        "identity_tier": getattr(row, "identity_tier", "") or "",
        "product_id": getattr(row, "product_id", None),
        "signal_family": getattr(row, "signal_family", "") or "",
        "signal_type": getattr(row, "signal_type", "") or "",
        "observed_at": getattr(row, "observed_at", None),
        "source": getattr(row, "source", "") or "",
        "evidence_ref_type": getattr(row, "evidence_ref_type", None),
        "evidence_ref_id": getattr(row, "evidence_ref_id", None),
        "dedup_hash": getattr(row, "dedup_hash", "") or "",
    }


__all__ = [
    "FAMILY_PRODUCT_EXPOSURE",
    "FAMILY_PRODUCT_VIEW",
    "FAMILY_PRODUCT_INTEREST",
    "FAMILY_PRODUCT_CART_ACTIVITY",
    "FAMILY_PRODUCT_CHECKOUT_ACTIVITY",
    "FAMILY_PRODUCT_PURCHASE",
    "FAMILY_PRODUCT_RECOVERY_INTERACTION",
    "FAMILY_PRODUCT_CUSTOMER_RETURN",
    "FAMILY_PRODUCT_EVIDENCE",
    "SIGNAL_FAMILIES",
    "SIGNAL_PRODUCT_EXPOSED",
    "SIGNAL_PRODUCT_VIEWED",
    "SIGNAL_PRODUCT_INTEREST_HESITATION",
    "SIGNAL_PRODUCT_CART_ADDED",
    "SIGNAL_PRODUCT_CART_REMOVED",
    "SIGNAL_PRODUCT_CART_SYNCED",
    "SIGNAL_PRODUCT_CART_ABANDONED",
    "SIGNAL_PRODUCT_CHECKOUT_TOUCHED",
    "SIGNAL_PRODUCT_PURCHASED",
    "SIGNAL_PRODUCT_RECOVERY_STARTED",
    "SIGNAL_PRODUCT_RECOVERY_PROGRESSED",
    "SIGNAL_PRODUCT_CUSTOMER_RETURNED",
    "SIGNAL_PRODUCT_EVIDENCE_LINKED",
    "SIGNAL_TYPES_WIRED",
    "SIGNAL_TYPES_DEFERRED",
    "SIGNAL_TYPE_TO_FAMILY",
    "SOURCE_CART_STATE_SYNC",
    "SOURCE_CART_ABANDONED",
    "SOURCE_REASON_CAPTURE",
    "SOURCE_PURCHASE_TRUTH",
    "SOURCE_RECOVERY_TIMELINE",
    "SOURCE_BEHAVIORAL_RETURN",
    "EVIDENCE_REF_CART_LINE_SNAPSHOT",
    "EVIDENCE_REF_HESITATION_MAPPING",
    "EVIDENCE_REF_PURCHASE_MAPPING",
    "EVIDENCE_REF_RECOVERY_TIMELINE",
    "EVIDENCE_REF_SESSION",
    "RECOVERY_START_STATUSES",
    "ProductSignalPersistResult",
    "signal_family_for_type",
    "product_signal_to_dict",
]
