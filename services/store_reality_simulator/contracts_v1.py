# -*- coding: utf-8 -*-
"""Shared contracts for Store Reality Simulator V1 (Phase 2)."""
from __future__ import annotations

from typing import Any, Final

DEMO_STORE_SLUG: Final[str] = "demo"
SIMULATION_SOURCE: Final[str] = "store_reality_simulator_v1"

# Run statuses
STATUS_CREATED: Final[str] = "created"
STATUS_DRY_RUN: Final[str] = "dry_run"
STATUS_RUNNING: Final[str] = "running"
STATUS_PAUSED: Final[str] = "paused"
STATUS_COMPLETED: Final[str] = "completed"
STATUS_FAILED: Final[str] = "failed"
STATUS_CANCELLED: Final[str] = "cancelled"
STATUS_CLEANED: Final[str] = "cleaned"

RUN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        STATUS_CREATED,
        STATUS_DRY_RUN,
        STATUS_RUNNING,
        STATUS_PAUSED,
        STATUS_COMPLETED,
        STATUS_FAILED,
        STATUS_CANCELLED,
        STATUS_CLEANED,
    }
)

# Accounting buckets (exist before events)
BUCKET_PLANNED: Final[str] = "planned"
BUCKET_PERSISTED: Final[str] = "persisted"
BUCKET_PROCESSED: Final[str] = "processed"
BUCKET_FAILED: Final[str] = "failed"
BUCKET_UNSUPPORTED: Final[str] = "unsupported"
BUCKET_DUPLICATE: Final[str] = "duplicate"
BUCKET_REPLAYED: Final[str] = "replayed"
BUCKET_SUPPRESSED: Final[str] = "suppressed"
BUCKET_REJECTED: Final[str] = "rejected"

ACCOUNTING_BUCKETS: Final[tuple[str, ...]] = (
    BUCKET_PLANNED,
    BUCKET_PERSISTED,
    BUCKET_PROCESSED,
    BUCKET_FAILED,
    BUCKET_UNSUPPORTED,
    BUCKET_DUPLICATE,
    BUCKET_REPLAYED,
    BUCKET_SUPPRESSED,
    BUCKET_REJECTED,
)

PROVIDER_SUPPRESSED_SIMULATION: Final[str] = "provider_suppressed_simulation"


def empty_accounting() -> dict[str, int]:
    return {k: 0 for k in ACCOUNTING_BUCKETS}


def provenance_envelope(
    *,
    simulation_run_id: str,
    simulation_scenario_id: str = "",
    simulation_customer_id: str = "",
    simulated_event_id: str = "",
    seed: int | None = None,
) -> dict[str, Any]:
    """Attach to operational context JSON — never injects derived truth."""
    out: dict[str, Any] = {
        "simulation": True,
        "source": SIMULATION_SOURCE,
        "simulation_run_id": str(simulation_run_id or "").strip(),
    }
    if simulation_scenario_id:
        out["simulation_scenario_id"] = str(simulation_scenario_id).strip()
    if simulation_customer_id:
        out["simulation_customer_id"] = str(simulation_customer_id).strip()
    if simulated_event_id:
        out["simulated_event_id"] = str(simulated_event_id).strip()
    if seed is not None:
        out["seed"] = int(seed)
    return out


def assert_demo_store(store_slug: str) -> str:
    slug = str(store_slug or "").strip()
    if slug != DEMO_STORE_SLUG:
        raise ValueError(f"store_reality_simulator_demo_only: got {slug!r}")
    return slug
