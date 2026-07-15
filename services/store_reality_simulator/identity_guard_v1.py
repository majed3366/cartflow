# -*- coding: utf-8 -*-
"""
Simulation identity isolation guard — Phase 3.1.

Mandatory before every simulated write:
  store_slug == demo  AND  simulation_run_id exists

Never silently remaps. Abort + CRITICAL log on failure.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG
from services.store_reality_simulator.context_v1 import (
    get_simulation_context,
    is_simulation_active,
)

log = logging.getLogger("cartflow.store_reality_simulator")

CRITICAL_ISOLATION_FAILURE = "CRITICAL SIMULATION ISOLATION FAILURE"


class SimulationIdentityIsolationError(RuntimeError):
    """Raised when a simulated write would escape demo identity."""

    def __init__(self, reason: str, *, details: Optional[dict[str, Any]] = None):
        self.reason = str(reason)
        self.details = dict(details or {})
        super().__init__(f"{CRITICAL_ISOLATION_FAILURE}: {self.reason}")


def _critical(reason: str, **fields: Any) -> None:
    parts = [f"[{CRITICAL_ISOLATION_FAILURE}]", f"reason={reason}"]
    for k, v in fields.items():
        if v is None:
            continue
        parts.append(f"{k}={str(v)[:220]}")
    msg = " | ".join(parts)
    try:
        print(msg, flush=True)
    except OSError:
        pass
    log.critical("%s", msg)


def require_simulation_write_identity(
    *,
    store_slug: Optional[str] = None,
    simulation_run_id: Optional[str] = None,
    surface: str = "write",
) -> dict[str, str]:
    """
    Permanent architectural gate before every simulated durable write.

    Requires:
    - active simulation context (preferred) OR explicit simulation_run_id
    - store_slug == demo
    - non-empty simulation_run_id
    """
    ctx = get_simulation_context()
    # Explicit simulation_run_id="" must abort (do not fall back to context).
    if simulation_run_id is not None:
        run_id = str(simulation_run_id).strip()
    else:
        run_id = str(getattr(ctx, "simulation_run_id", "") if ctx else "").strip()
    if store_slug is not None:
        slug = str(store_slug).strip()
    else:
        slug = str(getattr(ctx, "store_slug", None) if ctx else "").strip()

    if not run_id:
        _critical("missing_simulation_run_id", surface=surface, store_slug=slug)
        raise SimulationIdentityIsolationError(
            "missing_simulation_run_id",
            details={"surface": surface, "store_slug": slug},
        )
    if slug != DEMO_STORE_SLUG:
        _critical(
            "non_demo_store_slug",
            surface=surface,
            store_slug=slug,
            simulation_run_id=run_id,
        )
        raise SimulationIdentityIsolationError(
            "non_demo_store_slug",
            details={
                "surface": surface,
                "store_slug": slug,
                "simulation_run_id": run_id,
            },
        )
    if not is_simulation_active() and ctx is None:
        # Explicit run id + demo slug allowed for ledger/plan writers outside scope,
        # but durable platform writes must be inside simulation_scope.
        pass
    return {"store_slug": DEMO_STORE_SLUG, "simulation_run_id": run_id}


def assert_recovery_key_isolated(recovery_key: str, *, surface: str = "recovery_key") -> str:
    """recovery_key must be prefixed with demo: during simulation writes."""
    rk = str(recovery_key or "").strip()
    prefix = f"{DEMO_STORE_SLUG}:"
    if not rk.startswith(prefix):
        _critical(
            "recovery_key_not_demo_prefixed",
            surface=surface,
            recovery_key=rk,
        )
        raise SimulationIdentityIsolationError(
            "recovery_key_not_demo_prefixed",
            details={"surface": surface, "recovery_key": rk},
        )
    return rk


def assert_written_store_is_demo(
    written_store_slug: Optional[str],
    *,
    surface: str,
    simulation_run_id: str = "",
    recovery_key: str = "",
) -> str:
    """Post-write assertion — any non-demo durable identity is a failed architecture."""
    slug = str(written_store_slug or "").strip()
    if slug != DEMO_STORE_SLUG:
        _critical(
            "written_store_escape",
            surface=surface,
            written_store_slug=slug,
            simulation_run_id=simulation_run_id,
            recovery_key=recovery_key,
        )
        raise SimulationIdentityIsolationError(
            "written_store_escape",
            details={
                "surface": surface,
                "written_store_slug": slug,
                "simulation_run_id": simulation_run_id,
                "recovery_key": recovery_key,
            },
        )
    return slug


def predict_purchase_truth_escape(
    *,
    recovery_key: str,
    payload_store_slug: str = DEMO_STORE_SLUG,
) -> dict[str, Any]:
    """
    Predict whether platform Purchase Truth resolution would leave demo
    *without* applying the simulation pin (audit / failure-injection).
    """
    from services.recovery_store_context import (  # noqa: PLC0415
        canonical_store_slug_from_recovery_key,
        resolve_purchase_truth_store_slug,
    )
    from services.store_reality_simulator.context_v1 import (  # noqa: PLC0415
        _active_context,
    )

    # Temporarily clear simulation context so prediction sees production remap behaviour
    token = None
    try:
        token = _active_context.set(None)
        resolved = resolve_purchase_truth_store_slug(
            recovery_key=recovery_key,
            payload_store_slug=payload_store_slug,
        )
        canon_head = canonical_store_slug_from_recovery_key(recovery_key)
    finally:
        if token is not None:
            _active_context.reset(token)

    escaped = str(resolved or "").strip() != DEMO_STORE_SLUG
    return {
        "recovery_key": recovery_key,
        "payload_store_slug": payload_store_slug,
        "resolved_store_slug": resolved,
        "canonical_from_recovery_key": canon_head,
        "would_escape": escaped,
        "safe": not escaped,
    }


def pin_store_slug_for_active_simulation(store_slug: Optional[str] = None) -> Optional[str]:
    """
    When simulation is active, force demo identity for Purchase Truth / mapping.
    Returns DEMO_STORE_SLUG if pinned, else None (caller continues platform logic).
    """
    if not is_simulation_active():
        return None
    ctx = get_simulation_context()
    run_id = str(getattr(ctx, "simulation_run_id", "") or "").strip() if ctx else ""
    if not run_id:
        _critical("pin_missing_simulation_run_id", store_slug=store_slug)
        raise SimulationIdentityIsolationError("pin_missing_simulation_run_id")
    # Reject attempts to pin under a non-demo requested slug
    requested = str(store_slug or DEMO_STORE_SLUG).strip()
    if requested and requested != DEMO_STORE_SLUG:
        _critical(
            "pin_rejected_non_demo_request",
            store_slug=requested,
            simulation_run_id=run_id,
        )
        raise SimulationIdentityIsolationError(
            "pin_rejected_non_demo_request",
            details={"store_slug": requested, "simulation_run_id": run_id},
        )
    return DEMO_STORE_SLUG
