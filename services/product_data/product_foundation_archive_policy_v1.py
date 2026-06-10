# -*- coding: utf-8 -*-
"""
Product Foundation archive policy v1 — recommended retention windows only.

Policy constants for future archive jobs. No execution, no archive tables,
no deletion, no data movement. Active catalog entries remain mutable current
truth; archival applies to historical fact tables only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Recommended active retention before future archive (days).
ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS = 180
ARCHIVE_AFTER_HESITATION_MAPPINGS_DAYS = 365
ARCHIVE_AFTER_PURCHASE_MAPPINGS_DAYS = 365

# Canonical catalog is current truth — do not archive active rows.
# Future: mark inactive catalog rows after prolonged absence (policy TBD).
CATALOG_ARCHIVE_POLICY = "do_not_archive_active_catalog"
CATALOG_INACTIVE_MARK_FUTURE_DAYS = 730


@dataclass(frozen=True, slots=True)
class TableArchivePolicy:
    table: str
    active_window_days: int | None
    archive_after_days: int | None
    policy_note: str


TABLE_ARCHIVE_POLICIES: tuple[TableArchivePolicy, ...] = (
    TableArchivePolicy(
        table="cart_line_snapshots",
        active_window_days=ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS,
        archive_after_days=ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS,
        policy_note="Immutable cart line history; archive after active window.",
    ),
    TableArchivePolicy(
        table="product_catalog_entries",
        active_window_days=None,
        archive_after_days=None,
        policy_note=(
            "Do not archive active catalog. Future inactive marking only "
            f"(review after {CATALOG_INACTIVE_MARK_FUTURE_DAYS} days absent)."
        ),
    ),
    TableArchivePolicy(
        table="product_hesitation_mappings",
        active_window_days=ARCHIVE_AFTER_HESITATION_MAPPINGS_DAYS,
        archive_after_days=ARCHIVE_AFTER_HESITATION_MAPPINGS_DAYS,
        policy_note="Immutable Product↔Reason facts; archive after active window.",
    ),
    TableArchivePolicy(
        table="product_purchase_mappings",
        active_window_days=ARCHIVE_AFTER_PURCHASE_MAPPINGS_DAYS,
        archive_after_days=ARCHIVE_AFTER_PURCHASE_MAPPINGS_DAYS,
        policy_note="Immutable Product↔Purchase facts; archive after active window.",
    ),
)


def archive_policy_summary() -> dict[str, Any]:
    """Read-only policy export for governance diagnostics."""
    return {
        "principle": "archive_before_delete",
        "execution_enabled": False,
        "tables": [
            {
                "table": p.table,
                "active_window_days": p.active_window_days,
                "archive_after_days": p.archive_after_days,
                "policy_note": p.policy_note,
            }
            for p in TABLE_ARCHIVE_POLICIES
        ],
    }


__all__ = [
    "ARCHIVE_AFTER_CART_LINE_SNAPSHOTS_DAYS",
    "ARCHIVE_AFTER_HESITATION_MAPPINGS_DAYS",
    "ARCHIVE_AFTER_PURCHASE_MAPPINGS_DAYS",
    "CATALOG_ARCHIVE_POLICY",
    "CATALOG_INACTIVE_MARK_FUTURE_DAYS",
    "TABLE_ARCHIVE_POLICIES",
    "TableArchivePolicy",
    "archive_policy_summary",
]
