# -*- coding: utf-8 -*-
"""
Reality Attach composition root — INV-002 RC-3 Fix (B1).

Activates Reality Attach **before** Phase 3 ``bind_mqic_*`` / resolve so
merchant HTTP requests can observe attached Authority truth.

Attach remains an input binder only — not an authority, not middleware that
owns identity or time. Consumers still receive sealed MQIC.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Mapping, Optional

from services.identity_authority.context import clear_mqic, get_mqic
from services.identity_authority.exceptions import IdentityError
from services.identity_authority.mqic import MerchantQueryIdentityContext
from services.identity_authority.reality_attach_v1 import (
    clear_reality_attach,
    get_active_attach,
    reality_attach_scope,
)
from services.identity_authority.session_membership_v1 import (
    load_session_membership,
    resolve_mqic_from_session,
)
from services.time_authority.query_context import clear_query_time_context


# Lab / walkthrough headers (composition inputs — not merchant chrome)
HEADER_ATTACH_RUN_ID = "x-cartflow-reality-attach-run-id"
HEADER_ATTACH_START = "x-cartflow-reality-attach-start"


@dataclass(frozen=True)
class WalkthroughAttachInputs:
    """Declared attach inputs for one request (Authority inputs only)."""

    simulation_run_id: str
    simulation_start: datetime

    def __post_init__(self) -> None:
        run = (self.simulation_run_id or "").strip()
        if not run:
            raise IdentityError("attach_run_required", "simulation_run_id_required")
        start = self.simulation_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        else:
            start = start.astimezone(timezone.utc)
        object.__setattr__(self, "simulation_run_id", run[:128])
        object.__setattr__(self, "simulation_start", start)


def _header_get(headers: Mapping[str, Any], name: str) -> str:
    if headers is None:
        return ""
    # Starlette headers are case-insensitive; Mapping may be plain dict.
    lower = name.lower()
    for key, val in headers.items():
        if str(key).lower() == lower:
            return str(val or "").strip()
    return ""


def parse_walkthrough_attach_inputs(
    *,
    headers: Optional[Mapping[str, Any]] = None,
    attach_run_id: str = "",
    attach_start: Optional[datetime] = None,
    attach_start_iso: str = "",
) -> Optional[WalkthroughAttachInputs]:
    """
    Build walkthrough Attach inputs from explicit args or Lab headers.

    No inputs → None (normal unattached session path).
    Partial inputs → fail closed.
    """
    run = (attach_run_id or "").strip() or _header_get(
        headers or {}, HEADER_ATTACH_RUN_ID
    )
    start = attach_start
    if start is None:
        iso = (attach_start_iso or "").strip() or _header_get(
            headers or {}, HEADER_ATTACH_START
        )
        if iso:
            try:
                raw = iso.replace("Z", "+00:00")
                start = datetime.fromisoformat(raw)
            except ValueError as exc:
                raise IdentityError(
                    "attach_start_invalid", "attach_start_iso_invalid"
                ) from exc
    if not run and start is None:
        return None
    if not run or start is None:
        raise IdentityError(
            "attach_inputs_incomplete",
            "simulation_run_id_and_start_required_together",
        )
    return WalkthroughAttachInputs(simulation_run_id=run, simulation_start=start)


@contextmanager
def merchant_request_identity_bind(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    headers: Optional[Mapping[str, Any]] = None,
    attach_run_id: str = "",
    attach_start: Optional[datetime] = None,
    attach_start_iso: str = "",
    explicit_store_slug: str = "",
) -> Iterator[Optional[MerchantQueryIdentityContext]]:
    """
    Composition root for merchant session identity (+ optional Reality Attach).

    Order:
      1. Parse optional walkthrough Attach inputs (fail closed if partial)
      2. If Attach: load membership → reality_attach_scope → MQIC ATTACH + QTC
      3. Else: Phase 3 resolve_mqic_from_session (unchanged production path)
      4. On exit: clear MQIC + Attach + explicit QTC (clean detach)

    Does not invent store_slug. Does not create a second Authority.
    """
    attach_inputs = parse_walkthrough_attach_inputs(
        headers=headers,
        attach_run_id=attach_run_id,
        attach_start=attach_start,
        attach_start_iso=attach_start_iso,
    )
    # Fail closed on dual attach before clearing parent scope.
    if attach_inputs is not None and get_active_attach() is not None:
        raise IdentityError("attach_already_active", "reality_attach_already_active")

    clear_mqic()
    clear_reality_attach()
    # Do not clear ambient TA globally before attach — attach scope nests.

    if attach_inputs is None:
        mqic = resolve_mqic_from_session(
            cookies=cookies,
            explicit_store_slug=explicit_store_slug,
            bind=True,
        )
        try:
            yield mqic
        finally:
            clear_mqic()
            clear_reality_attach()
        return

    snap = load_session_membership(cookies=cookies)
    if snap is None:
        raise IdentityError("attach_session_required", "session_membership_required")

    # Attach target = Lab simulation tenant in membership (not signup primary).
    # Onboarding primary may remain a non-demo store; B3 links demo ownership.
    from services.store_reality_simulator.contracts_v1 import (  # noqa: PLC0415
        DEMO_STORE_SLUG,
    )

    store = None
    for cid in snap.membership_store_ids:
        candidate = snap.stores_by_id.get(cid)
        if candidate is not None and candidate.store_slug == DEMO_STORE_SLUG:
            store = candidate
            break
    if store is None:
        raise IdentityError(
            "attach_membership_denied",
            "simulation_store_not_in_membership",
        )

    with reality_attach_scope(
        simulation_run_id=attach_inputs.simulation_run_id,
        simulation_canonical_store_id=store.canonical_store_id,
        store_slug=store.store_slug,
        membership=snap,
        simulation_start=attach_inputs.simulation_start,
        bind_identity=True,
        bind_time=True,
    ):
        mqic = get_mqic()
        if mqic is None:
            raise IdentityError("attach_mqic_missing", "attach_did_not_bind_mqic")
        # Explicit slug (query) must match attached tenant — fail closed.
        slug_in = (explicit_store_slug or "").strip()
        if slug_in and slug_in != mqic.store_slug:
            raise IdentityError(
                "store_slug_mismatch",
                f"attach_slug_mismatch:{slug_in}!={mqic.store_slug}",
            )
        yield mqic
    # reality_attach_scope detaches MQIC + QTC; ensure attach handle cleared
    clear_reality_attach()
    clear_mqic()


def composition_diagnostics() -> dict[str, Any]:
    """Ops diagnostics for composition bind — not merchant chrome."""
    from services.identity_authority.reality_attach_v1 import attach_diagnostics

    mqic = get_mqic()
    return {
        "composition": "reality_attach_composition_v1",
        "mqic_bound": mqic is not None,
        "resolution_path": mqic.resolution_path.value if mqic is not None else None,
        "attach": attach_diagnostics(),
    }


__all__ = [
    "HEADER_ATTACH_RUN_ID",
    "HEADER_ATTACH_START",
    "WalkthroughAttachInputs",
    "composition_diagnostics",
    "merchant_request_identity_bind",
    "parse_walkthrough_attach_inputs",
]
