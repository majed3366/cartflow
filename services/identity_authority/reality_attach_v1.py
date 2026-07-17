# -*- coding: utf-8 -*-
"""
Reality Attach — INV-002 Phase 5.

Binds Reality Simulator declarations to Platform Authorities by changing
**authority inputs only**:

  SimulationClock / as-of  →  Time Authority (Query Time Context)
  Run canonical store      →  Identity Authority (MQIC ATTACH path)

Reality Attach is **not** an authority. It must never resolve merchant
identity independently, create a second MQIC, rewrite consumers, or bypass
Time / Identity Authority.

Rollback removes only this attach layer; Platform Authorities remain intact.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator, Mapping, Optional, Protocol, runtime_checkable
from uuid import uuid4

from services.identity_authority.authority import resolve_and_bind, resolve_only
from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
    ResolutionPath,
)
from services.identity_authority.context import clear_mqic, get_mqic
from services.identity_authority.exceptions import IdentityError
from services.identity_authority.mqic import MerchantQueryIdentityContext
from services.identity_authority.observability import record
from services.identity_authority.resolve import ResolveIdentityInput
from services.identity_authority.session_membership_v1 import (
    SessionMembershipSnapshot,
    build_session_resolve_input,
)
from services.time_authority.contracts import ClockSourceKind, QueryTimeContextKind
from services.time_authority.providers import SimulationClockProvider
from services.time_authority.query_context import (
    QueryTimeContext,
    activate_query_time_context,
    get_query_time_context,
)


TIME_AUTHORITY_SOURCE_ID = "platform_time_authority"
ATTACH_LAYER_ID = "reality_attach_v1"


class AttachState(str, Enum):
    """Attach lifecycle for diagnostics (ops only)."""

    DETACHED = "detached"
    ATTACHING = "attaching"
    ATTACHED = "attached"
    FAILED = "failed"
    DETACHING = "detaching"


class LifecycleState(str, Enum):
    """Simulation attach lifecycle (ops only)."""

    IDLE = "idle"
    ACTIVE = "active"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


@runtime_checkable
class _ClockLike(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class RealityAttachDeclaration:
    """
    Declared simulation → authority input bind (immutable after register).

    Callers (Lab / walkthrough composition) supply these; Attach never invents
    merchant identity or provider shop ids.
    """

    simulation_run_id: str
    simulation_canonical_store_id: str
    store_slug: str
    simulation_start: datetime
    replay_id: str = ""
    correlation_id: str = ""
    simulation_time_source: str = ClockSourceKind.SIMULATION.value
    authority_source_identity: str = AUTHORITY_SOURCE_ID
    authority_source_time: str = TIME_AUTHORITY_SOURCE_ID

    def __post_init__(self) -> None:
        run_id = (self.simulation_run_id or "").strip()
        cid = (self.simulation_canonical_store_id or "").strip()
        slug = (self.store_slug or "").strip()
        if not run_id:
            raise IdentityError("attach_run_required", "simulation_run_id_required")
        if not cid:
            raise IdentityError(
                "attach_canonical_required", "simulation_canonical_store_id_required"
            )
        if not slug:
            raise IdentityError("attach_slug_required", "store_slug_required")
        start = self.simulation_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        object.__setattr__(self, "simulation_run_id", run_id[:128])
        object.__setattr__(self, "simulation_canonical_store_id", cid)
        object.__setattr__(self, "store_slug", slug[:255])
        object.__setattr__(self, "simulation_start", start)
        object.__setattr__(self, "replay_id", (self.replay_id or "").strip()[:128])
        object.__setattr__(
            self, "correlation_id", (self.correlation_id or "").strip()[:128]
        )


@dataclass
class RealityAttachHandle:
    """Mutable attach/lifecycle diagnostics handle (not merchant chrome)."""

    declaration: RealityAttachDeclaration
    attach_state: AttachState = AttachState.DETACHED
    lifecycle_state: LifecycleState = LifecycleState.IDLE
    identity_bound: bool = False
    time_bound: bool = False
    mqic_snapshot: Optional[Mapping[str, Any]] = None
    time_snapshot: Optional[Mapping[str, Any]] = None
    failure_code: str = ""
    notes: dict[str, Any] = field(default_factory=dict)


_active_attach: ContextVar[Optional[RealityAttachHandle]] = ContextVar(
    "cartflow_reality_attach_v1", default=None
)


def get_active_attach() -> Optional[RealityAttachHandle]:
    """Return the active Reality Attach handle, if any."""
    return _active_attach.get()


def peek_attach_resolve_inputs() -> Optional[dict[str, str]]:
    """
    Authority-input overlay for Phase 3 ResolveIdentityInput.

    Returns simulation_run_id / simulation_canonical_store_id / replay_id when
    an attach is ATTACHED; otherwise None. Does not resolve identity.
    """
    handle = get_active_attach()
    if handle is None or handle.attach_state != AttachState.ATTACHED:
        return None
    d = handle.declaration
    return {
        "simulation_run_id": d.simulation_run_id,
        "simulation_canonical_store_id": d.simulation_canonical_store_id,
        "replay_id": d.replay_id,
        "correlation_id": d.correlation_id,
    }


def clear_reality_attach() -> None:
    """Force-clear attach context (tests / emergency detach)."""
    _active_attach.set(None)


def _fail(code: str, message: str = "") -> None:
    record("attach_fail")
    raise IdentityError(code, message or code)


def _ensure_member(
    membership_store_ids: frozenset[str], canonical_store_id: str
) -> None:
    if canonical_store_id not in membership_store_ids:
        _fail(
            "attach_membership_denied",
            f"simulation_store_not_in_membership:{canonical_store_id}",
        )


def _resolve_start(
    *,
    simulation_start: Optional[datetime],
    simulation_clock: Optional[_ClockLike],
) -> datetime:
    if simulation_clock is not None:
        try:
            when = simulation_clock.now()
        except Exception as exc:  # noqa: BLE001
            _fail("attach_clock_failed", f"simulation_clock_now_failed:{exc}")
        if when.tzinfo is None:
            return when.replace(tzinfo=timezone.utc)
        return when.astimezone(timezone.utc)
    if simulation_start is None:
        _fail("attach_time_required", "simulation_start_or_clock_required")
    if simulation_start.tzinfo is None:
        return simulation_start.replace(tzinfo=timezone.utc)
    return simulation_start.astimezone(timezone.utc)


def build_attach_declaration(
    *,
    simulation_run_id: str,
    simulation_canonical_store_id: str,
    store_slug: str,
    simulation_start: Optional[datetime] = None,
    simulation_clock: Optional[_ClockLike] = None,
    replay_id: str = "",
    correlation_id: str = "",
) -> RealityAttachDeclaration:
    """Validate and build an immutable attach declaration (no side effects)."""
    start = _resolve_start(
        simulation_start=simulation_start, simulation_clock=simulation_clock
    )
    corr = (correlation_id or "").strip() or uuid4().hex[:16]
    return RealityAttachDeclaration(
        simulation_run_id=simulation_run_id,
        simulation_canonical_store_id=simulation_canonical_store_id,
        store_slug=store_slug,
        simulation_start=start,
        replay_id=replay_id,
        correlation_id=corr,
    )


def build_attach_resolve_input(
    snap: SessionMembershipSnapshot,
    declaration: RealityAttachDeclaration,
    *,
    explicit_store_id: str = "",
    explicit_store_slug: str = "",
    session_active_store_id: str = "",
) -> ResolveIdentityInput:
    """
    Compose ResolveIdentityInput for ATTACH path from membership + declaration.

    Uses Phase 3 membership snapshot; Attach only adds simulation fields.
    """
    _ensure_member(snap.membership_store_ids, declaration.simulation_canonical_store_id)
    store = snap.stores_by_id.get(declaration.simulation_canonical_store_id)
    if store is None:
        _fail(
            "attach_unknown_store",
            f"unknown_simulation_canonical:{declaration.simulation_canonical_store_id}",
        )
    if store.store_slug != declaration.store_slug:
        _fail(
            "attach_slug_mismatch",
            "declaration_store_slug_ne_membership_store_slug",
        )
    base = build_session_resolve_input(
        snap,
        explicit_store_id=explicit_store_id,
        explicit_store_slug=explicit_store_slug,
        session_active_store_id=session_active_store_id,
        correlation_id=declaration.correlation_id,
    )
    # Attach fields win — ResolveMQIC ATTACH path (Authority-owned).
    return ResolveIdentityInput(
        merchant_id=base.merchant_id,
        stores_by_id=base.stores_by_id,
        membership_store_ids=base.membership_store_ids,
        primary_store_id=base.primary_store_id,
        session_active_store_id=base.session_active_store_id,
        explicit_store_id=base.explicit_store_id,
        explicit_store_slug=base.explicit_store_slug,
        membership_role=base.membership_role,
        alias_directory=base.alias_directory,
        provider=base.provider,
        external_shop_id=base.external_shop_id,
        install_id=base.install_id,
        simulation_run_id=declaration.simulation_run_id,
        simulation_canonical_store_id=declaration.simulation_canonical_store_id,
        replay_id=declaration.replay_id,
        correlation_id=declaration.correlation_id or base.correlation_id,
    )


def _time_provider_for_declaration(
    declaration: RealityAttachDeclaration,
    *,
    simulation_clock: Optional[_ClockLike],
) -> SimulationClockProvider:
    """
    Bind SimulationClock into Time Authority's SimulationClockProvider.

    If a live clock is supplied, seed the Authority provider from clock.now()
    so merchant-relevant now() goes through Time Authority — not a parallel
    simulator clock authority.
    """
    start = declaration.simulation_start
    if simulation_clock is not None:
        start = _resolve_start(simulation_start=None, simulation_clock=simulation_clock)
    return SimulationClockProvider(start, run_id=declaration.simulation_run_id)


def attach_diagnostics(
    handle: Optional[RealityAttachHandle] = None,
) -> dict[str, Any]:
    """Ops diagnostics — attach state, authority health, provenance. Not UX."""
    h = handle if handle is not None else get_active_attach()
    mqic = get_mqic()
    qtc = get_query_time_context()
    if h is None:
        return {
            "attach_layer": ATTACH_LAYER_ID,
            "attach_state": AttachState.DETACHED.value,
            "lifecycle_state": LifecycleState.IDLE.value,
            "authority_health": {
                "identity_authority": AUTHORITY_SOURCE_ID,
                "time_authority": TIME_AUTHORITY_SOURCE_ID,
                "mqic_bound": mqic is not None,
                "qtc_explicit": qtc is not None,
            },
            "simulation_provenance": None,
            "is_authority": False,
        }
    d = h.declaration
    return {
        "attach_layer": ATTACH_LAYER_ID,
        "attach_state": h.attach_state.value,
        "lifecycle_state": h.lifecycle_state.value,
        "identity_bound": h.identity_bound,
        "time_bound": h.time_bound,
        "failure_code": h.failure_code or None,
        "is_authority": False,
        "authority_health": {
            "identity_authority": AUTHORITY_SOURCE_ID,
            "time_authority": TIME_AUTHORITY_SOURCE_ID,
            "mqic_bound": mqic is not None,
            "qtc_explicit": qtc is not None,
            "mqic_resolution_path": (
                mqic.resolution_path.value if mqic is not None else None
            ),
            "qtc_mode": qtc.mode.value if qtc is not None else None,
            "qtc_source_id": qtc.source_id if qtc is not None else None,
        },
        "simulation_provenance": {
            "simulation_run_id": d.simulation_run_id,
            "simulation_time_source": d.simulation_time_source,
            "authority_source_identity": d.authority_source_identity,
            "authority_source_time": d.authority_source_time,
            "identity_provenance": (
                dict(mqic.identity_provenance) if mqic is not None else None
            ),
            "canonical_store_id": d.simulation_canonical_store_id,
            "store_slug": d.store_slug,
            "replay_id": d.replay_id or None,
            "correlation_id": d.correlation_id or None,
            "simulation_start": d.simulation_start.isoformat(),
        },
        "lifecycle_diagnostics": {
            "attach_state": h.attach_state.value,
            "lifecycle_state": h.lifecycle_state.value,
            "notes": dict(h.notes),
        },
        "mqic_snapshot": h.mqic_snapshot,
        "time_snapshot": h.time_snapshot,
    }


def _assert_chain_contracts(
    mqic: MerchantQueryIdentityContext,
    qtc: QueryTimeContext,
    declaration: RealityAttachDeclaration,
) -> None:
    """Fail closed if attach produced a duplicate / mismatched authority chain."""
    if mqic.resolution_path != ResolutionPath.ATTACH:
        _fail("attach_path_mismatch", "mqic_resolution_path_must_be_attach")
    if mqic.simulation_run_id != declaration.simulation_run_id:
        _fail("attach_run_mismatch", "mqic_simulation_run_id_mismatch")
    if mqic.canonical_store_id != declaration.simulation_canonical_store_id:
        _fail("attach_canonical_mismatch", "mqic_canonical_ne_declaration")
    if mqic.store_slug != declaration.store_slug:
        _fail("attach_slug_mismatch", "mqic_slug_ne_declaration")
    if qtc.mode != QueryTimeContextKind.SIMULATION:
        _fail("attach_time_mode_mismatch", "qtc_must_be_simulation")
    if qtc.simulation_run_id != declaration.simulation_run_id:
        _fail("attach_time_run_mismatch", "qtc_simulation_run_id_mismatch")
    if qtc.source_id != ClockSourceKind.SIMULATION.value:
        _fail("attach_time_source_mismatch", "qtc_source_must_be_simulation")


@contextmanager
def reality_attach_scope(
    *,
    simulation_run_id: str,
    simulation_canonical_store_id: str,
    store_slug: str,
    membership: SessionMembershipSnapshot,
    simulation_start: Optional[datetime] = None,
    simulation_clock: Optional[_ClockLike] = None,
    replay_id: str = "",
    correlation_id: str = "",
    bind_identity: bool = True,
    bind_time: bool = True,
) -> Iterator[RealityAttachHandle]:
    """
    Activate Reality Attach for a block: Time Authority + Identity Authority inputs.

    On exit: detach cleanly (clear attach handle; clear MQIC if this scope bound it;
    restore prior Time Authority context via nested activation).
    """
    if get_active_attach() is not None:
        _fail("attach_already_active", "reality_attach_already_active")
    if bind_identity and get_mqic() is not None:
        _fail("attach_mqic_already_bound", "mqic_already_bound_before_attach")

    handle = RealityAttachHandle(
        declaration=build_attach_declaration(
            simulation_run_id=simulation_run_id,
            simulation_canonical_store_id=simulation_canonical_store_id,
            store_slug=store_slug,
            simulation_start=simulation_start,
            simulation_clock=simulation_clock,
            replay_id=replay_id,
            correlation_id=correlation_id,
        ),
        attach_state=AttachState.ATTACHING,
        lifecycle_state=LifecycleState.IDLE,
    )
    token = _active_attach.set(handle)
    bound_identity = False
    time_cm = None
    try:
        declaration = handle.declaration
        _ensure_member(
            membership.membership_store_ids,
            declaration.simulation_canonical_store_id,
        )

        qtc: Optional[QueryTimeContext] = None
        if bind_time:
            provider = _time_provider_for_declaration(
                declaration, simulation_clock=simulation_clock
            )
            time_cm = activate_query_time_context(
                QueryTimeContextKind.SIMULATION,
                simulation_start=declaration.simulation_start,
                simulation_run_id=declaration.simulation_run_id,
                replay_id=declaration.replay_id,
                correlation_id=declaration.correlation_id,
                scope_key=declaration.store_slug,
                label="reality_attach",
                provider=provider,
            )
            qtc = time_cm.__enter__()
            handle.time_bound = True
            handle.time_snapshot = {
                "mode": qtc.mode.value,
                "source_id": qtc.source_id,
                "simulation_run_id": qtc.simulation_run_id,
                "authoritative_now": qtc.authoritative_now.isoformat(),
            }
        else:
            qtc = get_query_time_context()

        mqic: Optional[MerchantQueryIdentityContext] = None
        if bind_identity:
            # Mark ATTACHED before resolve so Phase 3 merge helpers see inputs.
            handle.attach_state = AttachState.ATTACHED
            inp = build_attach_resolve_input(membership, declaration)
            mqic = resolve_and_bind(inp)
            bound_identity = True
            handle.identity_bound = True
            handle.mqic_snapshot = mqic.internal_snapshot()
        else:
            # Declaration registered so Phase 3 resolve merges ATTACH inputs.
            handle.attach_state = AttachState.ATTACHED
            mqic = get_mqic()

        if bind_identity and bind_time:
            assert mqic is not None and qtc is not None
            _assert_chain_contracts(mqic, qtc, declaration)

        handle.lifecycle_state = LifecycleState.ACTIVE
        record("attach_ok")
        yield handle
        handle.lifecycle_state = LifecycleState.COMPLETED
    except IdentityError as exc:
        handle.attach_state = AttachState.FAILED
        handle.lifecycle_state = LifecycleState.ROLLED_BACK
        handle.failure_code = getattr(exc, "code", "") or "identity_error"
        raise
    except Exception:
        handle.attach_state = AttachState.FAILED
        handle.lifecycle_state = LifecycleState.ROLLED_BACK
        handle.failure_code = "attach_unexpected_error"
        raise
    finally:
        handle.attach_state = AttachState.DETACHING
        try:
            if bound_identity:
                clear_mqic()
                handle.identity_bound = False
            if time_cm is not None:
                time_cm.__exit__(None, None, None)
                handle.time_bound = False
        finally:
            handle.attach_state = AttachState.DETACHED
            if handle.lifecycle_state == LifecycleState.ACTIVE:
                handle.lifecycle_state = LifecycleState.ROLLED_BACK
            _active_attach.reset(token)
            record("detach_ok")


@contextmanager
def reality_attach_declaration_scope(
    declaration: RealityAttachDeclaration,
) -> Iterator[RealityAttachHandle]:
    """
    Register attach declaration only (no Time/Identity bind).

    Phase 3 ``resolve_mqic_from_session`` / ``build_session_resolve_input`` merge
    ATTACH fields while this scope is active. Use when composition will bind MQIC.
    """
    if get_active_attach() is not None:
        _fail("attach_already_active", "reality_attach_already_active")
    handle = RealityAttachHandle(
        declaration=declaration,
        attach_state=AttachState.ATTACHED,
        lifecycle_state=LifecycleState.ACTIVE,
        notes={"mode": "declaration_only"},
    )
    token = _active_attach.set(handle)
    try:
        record("attach_ok")
        yield handle
        handle.lifecycle_state = LifecycleState.COMPLETED
    finally:
        handle.attach_state = AttachState.DETACHED
        if handle.lifecycle_state == LifecycleState.ACTIVE:
            handle.lifecycle_state = LifecycleState.ROLLED_BACK
        _active_attach.reset(token)
        record("detach_ok")


def attach_from_membership_stores(
    *,
    simulation_run_id: str,
    store: CanonicalStoreIdentity,
    membership_store_ids: frozenset[str],
    stores_by_id: Mapping[str, CanonicalStoreIdentity],
    merchant_id: str,
    simulation_start: datetime,
    primary_store_id: str = "",
    replay_id: str = "",
    correlation_id: str = "",
    bind: bool = True,
) -> MerchantQueryIdentityContext:
    """
    One-shot ATTACH resolve (optional bind) for tests / composition roots.

    Prefer ``reality_attach_scope`` for full Time + Identity attach lifecycle.
    """
    snap = SessionMembershipSnapshot(
        merchant_id=merchant_id,
        primary_store_id=primary_store_id or store.canonical_store_id,
        membership_store_ids=membership_store_ids,
        stores_by_id=dict(stores_by_id),
    )
    declaration = build_attach_declaration(
        simulation_run_id=simulation_run_id,
        simulation_canonical_store_id=store.canonical_store_id,
        store_slug=store.store_slug,
        simulation_start=simulation_start,
        replay_id=replay_id,
        correlation_id=correlation_id,
    )
    inp = build_attach_resolve_input(snap, declaration)
    if bind:
        return resolve_and_bind(inp)
    return resolve_only(inp)


__all__ = [
    "ATTACH_LAYER_ID",
    "TIME_AUTHORITY_SOURCE_ID",
    "AttachState",
    "LifecycleState",
    "RealityAttachDeclaration",
    "RealityAttachHandle",
    "attach_diagnostics",
    "attach_from_membership_stores",
    "build_attach_declaration",
    "build_attach_resolve_input",
    "clear_reality_attach",
    "get_active_attach",
    "peek_attach_resolve_inputs",
    "reality_attach_declaration_scope",
    "reality_attach_scope",
]
