# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — read-only purchase attribution counts.

Uses ``purchase_attribution_v1`` evidence only; does not write or alter attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from models import PurchaseTruthRecord
from services.purchase_attribution_v1 import (
    LEVEL_ASSISTED,
    LEVEL_CONFIRMED,
    LEVEL_LIKELY,
    compute_attribution_decision,
    gather_attribution_inputs,
)

ATTRIBUTED_RECOVERY_LEVELS = frozenset(
    {
        LEVEL_CONFIRMED,
        LEVEL_LIKELY,
        LEVEL_ASSISTED,
    }
)


@dataclass
class KnowledgePurchaseAttributionCounts:
    purchase_count: int = 0
    attributed_recovery_purchase_count: int = 0
    purchase_attribution_unknown_count: int = 0
    purchase_attribution_evaluated_count: int = 0
    attribution_level_distribution: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.attribution_level_distribution is None:
            self.attribution_level_distribution = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "purchase_count": self.purchase_count,
            "attributed_recovery_purchase_count": self.attributed_recovery_purchase_count,
            "purchase_attribution_unknown_count": self.purchase_attribution_unknown_count,
            "purchase_attribution_evaluated_count": self.purchase_attribution_evaluated_count,
            "attribution_level_distribution": dict(self.attribution_level_distribution),
        }


def count_knowledge_purchase_attribution(
    db_session: Any,
    store_slug: str,
    *,
    window_start: Any,
    window_end: Any,
) -> KnowledgePurchaseAttributionCounts:
    """
    Evaluate Purchase Truth rows in window; count only evidence-backed recovery attribution.
    """
    ss = (store_slug or "").strip()[:255]
    out = KnowledgePurchaseAttributionCounts()
    if not ss:
        return out

    try:
        rows = (
            db_session.query(PurchaseTruthRecord)
            .filter(
                PurchaseTruthRecord.store_slug == ss,
                PurchaseTruthRecord.purchase_time >= window_start,
                PurchaseTruthRecord.purchase_time < window_end,
            )
            .all()
        )
    except SQLAlchemyError:
        db_session.rollback()
        return out

    out.purchase_count = len(rows)
    out.purchase_attribution_evaluated_count = len(rows)
    dist: dict[str, int] = {}

    for row in rows:
        rk = (getattr(row, "recovery_key", None) or "").strip()
        sid = (getattr(row, "session_id", None) or "").strip()
        if not rk and sid:
            rk = f"{ss}:{sid}"
        purchase_at = getattr(row, "purchase_time", None)
        context: dict[str, Any] = {}
        if purchase_at is not None:
            context["purchase_completed_at"] = purchase_at

        try:
            inp = gather_attribution_inputs(
                rk,
                session_id=sid,
                store_slug=ss,
                context_payload=context or None,
            )
            decision = compute_attribution_decision(inp)
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            dist["evaluation_error"] = dist.get("evaluation_error", 0) + 1
            out.purchase_attribution_unknown_count += 1
            continue

        level = (decision.attribution_level or "").strip()
        dist[level] = dist.get(level, 0) + 1
        if level in ATTRIBUTED_RECOVERY_LEVELS:
            out.attributed_recovery_purchase_count += 1
        else:
            out.purchase_attribution_unknown_count += 1

    out.attribution_level_distribution = dist
    return out


__all__ = [
    "ATTRIBUTED_RECOVERY_LEVELS",
    "KnowledgePurchaseAttributionCounts",
    "count_knowledge_purchase_attribution",
]
