# -*- coding: utf-8 -*-
"""
Purchase truth gap visibility v1 — read-only drift detection.

Surfaces non-durable purchase stop paths without changing purchase truth logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryLog, LifecycleClosureRecord, PurchaseTruthRecord
from services.lifecycle_closure_records_v1 import CLOSURE_PURCHASE_COMPLETED

_REPLY_PURCHASE_MARKERS = (
    "reply_purchase",
    "reply_purchase_claim",
    "reply_intent_purchase",
    "customer_reply_purchase",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_reply_purchase_source(source: str, reason: str) -> bool:
    blob = f"{source} {reason}".lower()
    return any(m in blob for m in _REPLY_PURCHASE_MARKERS)


def build_purchase_truth_gap_summary(*, sample_limit: int = 15) -> dict[str, Any]:
    """Read-only summary of purchase closures without durable purchase truth."""
    limit = max(1, min(int(sample_limit or 15), 50))
    out: dict[str, Any] = {
        "generated_at": _utc_now_iso(),
        "gaps_detected": False,
        "durable_purchase_truth_count": 0,
        "purchase_closure_without_durable_truth": 0,
        "stopped_converted_log_without_durable_truth": 0,
        "reply_purchase_closure_without_durable_truth": 0,
        "non_durable_stop_total": 0,
        "severity": "ok",
        "summary": "Purchase truth and closure records are aligned in sampled scope.",
        "samples": {
            "closure_without_truth": [],
            "stopped_converted_without_truth": [],
            "reply_purchase_without_truth": [],
        },
        "error": None,
    }

    try:
        db.create_all()
        durable_count = int(db.session.query(PurchaseTruthRecord).count())

        closure_rows = (
            db.session.query(LifecycleClosureRecord)
            .filter(LifecycleClosureRecord.closure_status == CLOSURE_PURCHASE_COMPLETED)
            .order_by(LifecycleClosureRecord.closure_time.desc())
            .limit(500)
            .all()
        )
        closure_gap_keys: list[dict[str, Any]] = []
        reply_gap_keys: list[dict[str, Any]] = []
        for row in closure_rows:
            rk = str(row.recovery_key or "").strip()
            if not rk:
                continue
            has_truth = (
                db.session.query(PurchaseTruthRecord.id)
                .filter(PurchaseTruthRecord.recovery_key == rk)
                .first()
                is not None
            )
            if has_truth:
                continue
            entry = {
                "recovery_key": rk[:120],
                "closure_source": (row.closure_source or "")[:64],
                "closure_reason": (row.closure_reason or "")[:64],
            }
            closure_gap_keys.append(entry)
            if _is_reply_purchase_source(
                str(row.closure_source or ""),
                str(row.closure_reason or ""),
            ):
                reply_gap_keys.append(entry)

        log_rows = (
            db.session.query(CartRecoveryLog.recovery_key, CartRecoveryLog.status)
            .filter(CartRecoveryLog.status == "stopped_converted")
            .order_by(CartRecoveryLog.id.desc())
            .limit(500)
            .all()
        )
        log_gap_keys: list[dict[str, Any]] = []
        seen_log: set[str] = set()
        for rk_raw, status in log_rows:
            rk = str(rk_raw or "").strip()
            if not rk or rk in seen_log:
                continue
            seen_log.add(rk)
            has_truth = (
                db.session.query(PurchaseTruthRecord.id)
                .filter(PurchaseTruthRecord.recovery_key == rk)
                .first()
                is not None
            )
            if has_truth:
                continue
            has_closure = (
                db.session.query(LifecycleClosureRecord.id)
                .filter(
                    LifecycleClosureRecord.recovery_key == rk,
                    LifecycleClosureRecord.closure_status == CLOSURE_PURCHASE_COMPLETED,
                )
                .first()
                is not None
            )
            if has_closure:
                continue
            log_gap_keys.append(
                {
                    "recovery_key": rk[:120],
                    "log_status": str(status or "")[:64],
                }
            )

        closure_gap_n = len(closure_gap_keys)
        log_gap_n = len(log_gap_keys)
        reply_gap_n = len(reply_gap_keys)
        non_durable_total = closure_gap_n + log_gap_n

        out["durable_purchase_truth_count"] = durable_count
        out["purchase_closure_without_durable_truth"] = closure_gap_n
        out["stopped_converted_log_without_durable_truth"] = log_gap_n
        out["reply_purchase_closure_without_durable_truth"] = reply_gap_n
        out["non_durable_stop_total"] = non_durable_total
        out["gaps_detected"] = non_durable_total > 0 or reply_gap_n > 0
        out["samples"] = {
            "closure_without_truth": closure_gap_keys[:limit],
            "stopped_converted_without_truth": log_gap_keys[:limit],
            "reply_purchase_without_truth": reply_gap_keys[:limit],
        }

        if non_durable_total > 0 or reply_gap_n > 0:
            out["severity"] = "warning" if non_durable_total < 10 else "critical"
            out["summary"] = (
                f"Detected {non_durable_total} non-durable purchase stop path(s) "
                f"({reply_gap_n} reply-purchase closure gap(s))."
            )
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:200]
        out["severity"] = "critical"
        out["summary"] = "Purchase truth gap summary unavailable due to database error."

    return out


__all__ = ["build_purchase_truth_gap_summary"]
