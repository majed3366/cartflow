# -*- coding: utf-8 -*-
"""
Provider Reliability — Truth Foundation & Failure Disposition (V1).

Implements Provider Reliability Governance V1:
  * §2 Provider Truth Model — four altitudes (Acceptance -> Provider Delivery ->
    Customer Delivery -> Terminal), reconciled under one owner, **no inference**
    across altitudes (PR-1, PR-2, PR-5, PR-TM-1..5).
  * §3 Failure Taxonomy Governance — every provider outcome maps deterministically
    to one disposition axis: retry | terminal | suppressed | unknown | non_provider
    (PR-7, PR-9). No implicit behavior.

Read-only reconciliation over the existing stores (CartRecoveryLog acceptance/terminal
+ WhatsAppDeliveryTruth delivery). Does not mutate Purchase Truth or Lifecycle Truth.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.cartflow_provider_readiness import (
    FAILURE_PROVIDER_AUTH,
    FAILURE_PROVIDER_NOT_CONFIGURED,
    FAILURE_RATE_LIMITED,
    FAILURE_REJECTED,
    FAILURE_SANDBOX_RECIPIENT,
    FAILURE_TEMPLATE_NOT_APPROVED,
    FAILURE_UNAVAILABLE,
    FAILURE_UNKNOWN,
    classify_provider_failure,
)

# --------------------------------------------------------------------------- #
# §2 Truth altitudes (strict order, one owner each).
# --------------------------------------------------------------------------- #
ALT_NONE = "none"
ALT_ACCEPTANCE = "acceptance"
ALT_PROVIDER_DELIVERY = "provider_delivery"
ALT_CUSTOMER_DELIVERY = "customer_delivery"
ALT_TERMINAL = "terminal"

_ALTITUDE_RANK: dict[str, int] = {
    ALT_NONE: 0,
    ALT_ACCEPTANCE: 10,
    ALT_PROVIDER_DELIVERY: 20,
    ALT_CUSTOMER_DELIVERY: 30,
    ALT_TERMINAL: 40,
}

TERMINAL_DELIVERED = "delivered"
TERMINAL_READ = "read"
TERMINAL_FAILED = "failed"
TERMINAL_UNKNOWN = "unknown"

# CartRecoveryLog.status buckets (mirror of whatsapp_send.py truth table).
_ACCEPTANCE_STATUSES = frozenset({"sent_real", "mock_sent"})
_TERMINAL_FAIL_STATUSES = frozenset({"whatsapp_failed", "failed_final"})
_SUPPRESSED_STATUSES = frozenset(
    {"skipped_duplicate", "stopped_converted", "skipped_user_rejected_help"}
)

# --------------------------------------------------------------------------- #
# §3 Failure disposition axis.
# --------------------------------------------------------------------------- #
DISPOSITION_RETRY = "retry"
DISPOSITION_TERMINAL = "terminal"
DISPOSITION_SUPPRESSED = "suppressed"
DISPOSITION_UNKNOWN = "unknown"
DISPOSITION_NON_PROVIDER = "non_provider"

# Governed mapping: provider failure class -> disposition (PR-FX-1, deterministic).
_CLASS_DISPOSITION: dict[str, str] = {
    # retryable / transient
    FAILURE_RATE_LIMITED: DISPOSITION_RETRY,
    FAILURE_UNAVAILABLE: DISPOSITION_RETRY,  # includes provider_timeout via classify
    # terminal (no retry will fix)
    FAILURE_REJECTED: DISPOSITION_TERMINAL,
    FAILURE_TEMPLATE_NOT_APPROVED: DISPOSITION_TERMINAL,
    FAILURE_SANDBOX_RECIPIENT: DISPOSITION_TERMINAL,
    FAILURE_PROVIDER_AUTH: DISPOSITION_TERMINAL,
    FAILURE_PROVIDER_NOT_CONFIGURED: DISPOSITION_TERMINAL,
    # unknown remains observable, never silent (PR-6)
    FAILURE_UNKNOWN: DISPOSITION_UNKNOWN,
}

# Non-provider / internal skip markers — not a provider failure.
_NON_PROVIDER_ERRORS = frozenset(
    {"empty_message", "invalid_phone", "user_rejected_help", "operational_control_unavailable"}
)
_SUPPRESSED_MARKERS = frozenset({"duplicate", "skipped_duplicate"})


def is_retryable(disposition: str) -> bool:
    return (disposition or "").strip() == DISPOSITION_RETRY


def resolve_failure_disposition(
    *,
    failure_class: Optional[str] = None,
    error: Any = None,
    status: Any = None,
    marker: Optional[str] = None,
) -> str:
    """
    Deterministically map a provider outcome to its disposition axis.

    Precedence: explicit internal marker > non-provider error string >
    provider failure class (explicit or classified from error/status).
    """
    mk = (marker or "").strip().lower()
    if mk in _SUPPRESSED_MARKERS:
        return DISPOSITION_SUPPRESSED
    if mk in ("converted", "user_rejected", "operational_control", "internal_skip"):
        return DISPOSITION_NON_PROVIDER

    err_s = str(error or "").strip().lower()
    if err_s in _NON_PROVIDER_ERRORS:
        return DISPOSITION_NON_PROVIDER

    fc = (failure_class or "").strip()
    if not fc:
        fc = classify_provider_failure(error=error, status=status)
    return _CLASS_DISPOSITION.get(fc, DISPOSITION_UNKNOWN)


# --------------------------------------------------------------------------- #
# §2 Reconciled provider truth (single owner, no cross-altitude inference).
# --------------------------------------------------------------------------- #
@dataclass
class ReconciledProviderTruth:
    correlation_key: str = ""
    provider: str = ""
    altitude: str = ALT_NONE
    terminal_outcome: str = ""  # delivered|read|failed|unknown|"" (not terminal)
    accepted: bool = False
    delivered: bool = False
    failed: bool = False
    reason: str = ""
    sources: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _delivery_truth_altitude(truth_level: str) -> str:
    """Map WhatsAppDeliveryTruth.truth_level -> reconciled altitude (delivery evidence only)."""
    lv = (truth_level or "").strip()
    if lv in ("delivered_to_customer",):
        return ALT_CUSTOMER_DELIVERY
    if lv in ("read_by_customer",):
        return ALT_CUSTOMER_DELIVERY
    if lv in ("sent_to_network",):
        return ALT_PROVIDER_DELIVERY
    if lv in ("accepted_by_provider",):
        return ALT_ACCEPTANCE
    if lv in ("failed_delivery",):
        return ALT_TERMINAL
    return ALT_NONE


def reconcile_provider_truth(
    correlation_key: str,
    *,
    provider: str = "",
) -> ReconciledProviderTruth:
    """
    Reconcile acceptance (CartRecoveryLog) + delivery (WhatsAppDeliveryTruth) for one
    correlation_key into a single authoritative disposition.

    Governance: acceptance NEVER implies delivery (PR-1/PR-2). Delivery is only set by
    delivery evidence. Truth advances altitude; failed is terminal. Read-only.
    """
    ck = (correlation_key or "").strip()[:512]
    out = ReconciledProviderTruth(correlation_key=ck, provider=(provider or ""))
    if not ck:
        out.reason = "missing_correlation_key"
        return out

    acceptance_status = ""
    delivery_level = ""
    delivery_error = ""
    try:
        from extensions import db
        from models import CartRecoveryLog, WhatsAppDeliveryTruth
        from schema_widget import ensure_whatsapp_delivery_truth_schema

        ensure_whatsapp_delivery_truth_schema(db)
        db.create_all()

        # Acceptance / terminal-failure from CartRecoveryLog (latest by recovery_key).
        crl = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.recovery_key == ck)
            .order_by(CartRecoveryLog.id.desc())
            .first()
        )
        if crl is not None:
            acceptance_status = (crl.status or "").strip()
            if not out.provider:
                out.provider = (getattr(crl, "provider", "") or "")

        # Delivery evidence from WhatsAppDeliveryTruth (linked by recovery_key — PR-14).
        dt = (
            db.session.query(WhatsAppDeliveryTruth)
            .filter(WhatsAppDeliveryTruth.recovery_key == ck)
            .order_by(WhatsAppDeliveryTruth.id.desc())
            .first()
        )
        if dt is not None:
            delivery_level = (dt.truth_level or "").strip()
            delivery_error = (dt.provider_error or "").strip()
            if not out.provider:
                out.provider = (getattr(dt, "provider", "") or "")
    except Exception as exc:  # noqa: BLE001
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        out.reason = f"reconcile_error:{type(exc).__name__}"
        return out

    out.sources = {
        "cart_recovery_log_status": acceptance_status or None,
        "delivery_truth_level": delivery_level or None,
        "delivery_provider_error": delivery_error or None,
    }

    # --- Reconcile WITHOUT inference. ---
    altitude = ALT_NONE

    # Acceptance altitude — from acceptance evidence only.
    if acceptance_status in _ACCEPTANCE_STATUSES:
        out.accepted = True
        altitude = _max_altitude(altitude, ALT_ACCEPTANCE)

    # Delivery altitude — from delivery evidence only (never inferred from acceptance).
    da = _delivery_truth_altitude(delivery_level)
    if da == ALT_CUSTOMER_DELIVERY:
        out.delivered = True
    altitude = _max_altitude(altitude, da if da != ALT_TERMINAL else ALT_NONE)

    # Terminal failure — from either store.
    delivery_failed = delivery_level == "failed_delivery"
    acceptance_failed = acceptance_status in _TERMINAL_FAIL_STATUSES
    if delivery_failed or acceptance_failed:
        out.failed = True
        out.altitude = ALT_TERMINAL
        out.terminal_outcome = TERMINAL_FAILED
        out.reason = "terminal_failed"
        return out

    # Suppressed / non-provider (converted, opt-out, duplicate).
    if acceptance_status in _SUPPRESSED_STATUSES:
        out.altitude = altitude if altitude != ALT_NONE else ALT_NONE
        out.reason = f"suppressed:{acceptance_status}"
        return out

    # Terminal-success altitudes.
    if out.delivered:
        out.altitude = ALT_CUSTOMER_DELIVERY
        out.terminal_outcome = TERMINAL_READ if delivery_level == "read_by_customer" else TERMINAL_DELIVERED
        out.reason = "delivered"
        return out

    if altitude == ALT_ACCEPTANCE:
        # Accepted but no delivery evidence yet — NOT delivered, NOT terminal (PR-1).
        out.altitude = ALT_ACCEPTANCE
        out.terminal_outcome = ""
        out.reason = "accepted_awaiting_delivery"
        return out

    out.altitude = altitude
    out.terminal_outcome = TERMINAL_UNKNOWN if altitude == ALT_NONE else ""
    out.reason = "no_provider_evidence" if altitude == ALT_NONE else "in_flight"
    return out


def _max_altitude(a: str, b: str) -> str:
    return a if _ALTITUDE_RANK.get(a, 0) >= _ALTITUDE_RANK.get(b, 0) else b


__all__ = [
    "ALT_ACCEPTANCE",
    "ALT_CUSTOMER_DELIVERY",
    "ALT_NONE",
    "ALT_PROVIDER_DELIVERY",
    "ALT_TERMINAL",
    "DISPOSITION_NON_PROVIDER",
    "DISPOSITION_RETRY",
    "DISPOSITION_SUPPRESSED",
    "DISPOSITION_TERMINAL",
    "DISPOSITION_UNKNOWN",
    "ReconciledProviderTruth",
    "is_retryable",
    "reconcile_provider_truth",
    "resolve_failure_disposition",
]
