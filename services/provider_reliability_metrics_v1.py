# -*- coding: utf-8 -*-
"""
Provider Reliability — Operational Visibility (§6) & Metrics (§7), V1.

Implements Provider Reliability Governance V1:
  * §6 Operational Visibility — provider health, retry queue, retry exhaustion,
    delivery success, provider failures, unknown states, provider availability.
  * §7 Metrics Governance — denominator-based rates (PR-10): acceptance_rate,
    delivery_rate, retry_rate, retry_success_rate, retry_exhaustion_rate,
    provider_latency, provider_availability, unknown_state_rate. Raw counts are
    exposed only as denominators/inputs, never as the KPI (PR-MT-1).

Read-only. Reconciles the real production stores (CartRecoveryLog acceptance +
WhatsAppDeliveryTruth delivery + ProviderRetryLedger retries) plus provider readiness.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

STATUS_HEALTHY = "healthy"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_UNKNOWN = "unknown"

DEFAULT_WINDOW_HOURS = 24

_ACCEPTANCE_STATUSES = ("sent_real", "mock_sent")
_FAILED_STATUSES = ("whatsapp_failed", "failed_final")
_DELIVERED_LEVELS = ("delivered_to_customer", "read_by_customer")


def _pct(n: int, d: int) -> Optional[float]:
    """Rate as percent over an explicit denominator; None when denominator is 0 (PR-10)."""
    if not d:
        return None
    return round(100.0 * float(n) / float(d), 2)


def _cutoff(window_hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=max(1, int(window_hours)))


def _acceptance_counts(cutoff: datetime) -> dict[str, int]:
    from extensions import db
    from models import CartRecoveryLog

    out = {"accepted": 0, "failed": 0}
    try:
        db.create_all()
        base = db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.created_at >= cutoff
        )
        out["accepted"] = int(
            base.filter(CartRecoveryLog.status.in_(_ACCEPTANCE_STATUSES)).count()
        )
        out["failed"] = int(
            base.filter(CartRecoveryLog.status.in_(_FAILED_STATUSES)).count()
        )
    except Exception:  # noqa: BLE001
        try:
            db.session.rollback()
        except Exception:
            pass
    return out


def _delivery_counts(cutoff: datetime) -> dict[str, int]:
    from extensions import db
    from models import WhatsAppDeliveryTruth
    from schema_widget import ensure_whatsapp_delivery_truth_schema

    out = {"delivered": 0, "delivery_failed": 0}
    try:
        ensure_whatsapp_delivery_truth_schema(db)
        db.create_all()
        base = db.session.query(WhatsAppDeliveryTruth).filter(
            WhatsAppDeliveryTruth.last_event_time >= cutoff
        )
        out["delivered"] = int(
            base.filter(WhatsAppDeliveryTruth.truth_level.in_(_DELIVERED_LEVELS)).count()
        )
        out["delivery_failed"] = int(
            base.filter(WhatsAppDeliveryTruth.truth_level == "failed_delivery").count()
        )
    except Exception:  # noqa: BLE001
        try:
            db.session.rollback()
        except Exception:
            pass
    return out


def _retry_counts() -> dict[str, int]:
    from services.provider_retry_ledger_v1 import (
        STATUS_EXHAUSTED,
        STATUS_SUCCEEDED,
        ledger_status_counts,
    )
    from extensions import db
    from models import ProviderRetryLedger

    counts = ledger_status_counts()
    out = {
        "retried": 0,
        "exhausted": int(counts.get(STATUS_EXHAUSTED, 0)),
        "succeeded_after_retry": 0,
        "pending": int(counts.get("pending", 0)),
        "cancelled": int(counts.get("cancelled", 0)),
        "unknown": int(counts.get("unknown", 0)),
    }
    try:
        out["retried"] = int(
            db.session.query(ProviderRetryLedger)
            .filter(ProviderRetryLedger.attempt >= 1)
            .count()
        )
        out["succeeded_after_retry"] = int(
            db.session.query(ProviderRetryLedger)
            .filter(
                ProviderRetryLedger.attempt >= 1,
                ProviderRetryLedger.status == STATUS_SUCCEEDED,
            )
            .count()
        )
    except Exception:  # noqa: BLE001
        try:
            db.session.rollback()
        except Exception:
            pass
    return out


def _provider_health() -> dict[str, Any]:
    try:
        from services.cartflow_provider_readiness import get_whatsapp_provider_readiness

        r = get_whatsapp_provider_readiness()
        return {
            "provider": r.get("provider"),
            "configured": bool(r.get("configured")),
            "ready": bool(r.get("ready")),
            "mode": r.get("mode"),
            "failure_class": r.get("failure_class"),
        }
    except Exception:  # noqa: BLE001
        return {"provider": "unknown", "configured": False, "ready": False}


def _provider_latency() -> dict[str, Any]:
    """Latency is not yet durably sampled (audit §6.2). Expose the enforced ceiling honestly."""
    try:
        from services.provider_send_timeout_v1 import provider_send_timeout_seconds

        ceiling = provider_send_timeout_seconds()
    except Exception:  # noqa: BLE001
        ceiling = None
    return {"sampled": False, "p50_ms": None, "p95_ms": None, "ceiling_seconds": ceiling}


def build_provider_reliability_report(
    *, window_hours: int = DEFAULT_WINDOW_HOURS, now: Optional[datetime] = None
) -> dict[str, Any]:
    """
    §6+§7 read-model. Denominator-based rates over a rolling window plus live retry-queue
    state and provider health. Read-only; never mutates truth.
    """
    cutoff = _cutoff(window_hours)

    acc = _acceptance_counts(cutoff)
    dlv = _delivery_counts(cutoff)
    retry = _retry_counts()
    health = _provider_health()

    accepted = acc["accepted"]
    failed = acc["failed"]
    attempted = accepted + failed
    delivered = dlv["delivered"]
    delivery_failed = dlv["delivery_failed"]
    retried = retry["retried"]
    exhausted = retry["exhausted"]
    succeeded_after_retry = retry["succeeded_after_retry"]
    unknown_delivery = max(0, accepted - delivered - delivery_failed)

    try:
        from services.provider_retry_ledger_v1 import due_retry_backlog

        due_backlog = due_retry_backlog(now=now)
    except Exception:  # noqa: BLE001
        due_backlog = 0

    ready = bool(health.get("ready"))
    availability = {
        "twilio_ready": ready,
        "available_pct": 100.0 if ready else 0.0,
        "point_in_time": True,
    }

    metrics = {
        # denominator-based rates (PR-10). None => denominator was 0.
        "acceptance_rate": _pct(accepted, attempted),
        "delivery_rate": _pct(delivered, accepted),
        "retry_rate": _pct(retried, attempted),
        "retry_success_rate": _pct(succeeded_after_retry, retried),
        "retry_exhaustion_rate": _pct(exhausted, retried),
        "unknown_state_rate": _pct(unknown_delivery, accepted),
        "provider_availability": availability,
        "provider_latency": _provider_latency(),
    }

    denominators = {
        "window_hours": int(window_hours),
        "attempted": attempted,
        "accepted": accepted,
        "failed": failed,
        "delivered": delivered,
        "delivery_failed": delivery_failed,
        "unknown_delivery": unknown_delivery,
        "retried": retried,
        "exhausted": exhausted,
        "succeeded_after_retry": succeeded_after_retry,
    }

    retry_queue = {
        "pending": retry["pending"],
        "due_backlog": due_backlog,
        "exhausted": exhausted,
        "cancelled": retry["cancelled"],
        "unknown": retry["unknown"],
    }

    status = _classify_status(
        ready=ready,
        attempted=attempted,
        acceptance_rate=metrics["acceptance_rate"],
        exhausted=exhausted,
        delivery_failed=delivery_failed,
    )

    return {
        "status": status,
        "provider_health": health,
        "metrics": metrics,
        "denominators": denominators,
        "retry_queue": retry_queue,
        "governance": "provider_reliability_governance_v1",
        "notes": {
            "delivery_rate_requires_webhooks": True,
            "latency_sampled": False,
            "retry_live_dispatch_active": _retry_active_flag(),
        },
    }


def _retry_active_flag() -> bool:
    try:
        from services.provider_retry_ledger_v1 import retry_active

        return retry_active()
    except Exception:  # noqa: BLE001
        return False


def _classify_status(
    *,
    ready: bool,
    attempted: int,
    acceptance_rate: Optional[float],
    exhausted: int,
    delivery_failed: int,
) -> str:
    if not ready:
        return STATUS_WARNING if attempted > 0 else STATUS_UNKNOWN
    if attempted == 0:
        return STATUS_UNKNOWN
    if acceptance_rate is not None and acceptance_rate < 80.0:
        return STATUS_CRITICAL
    if exhausted > 0 or (acceptance_rate is not None and acceptance_rate < 95.0):
        return STATUS_WARNING
    return STATUS_HEALTHY


__all__ = [
    "DEFAULT_WINDOW_HOURS",
    "STATUS_CRITICAL",
    "STATUS_HEALTHY",
    "STATUS_UNKNOWN",
    "STATUS_WARNING",
    "build_provider_reliability_report",
]
