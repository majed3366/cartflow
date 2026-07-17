# -*- coding: utf-8 -*-
"""
Session & membership binding — INV-002 WP-3 / Execution Architecture Phase 3.

Auth principal → membership → active store (explicit → session → primary)
→ sealed MQIC via ResolveMQIC. Session active store is never left implicit
without failing closed when no candidate exists.

No new query class: reuses merchant auth / onboarding store lookups already
used by the merchant session path. No provider-specific identity leakage.
No global HTTP middleware (would add I/O on public routes).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from services.identity_authority.authority import resolve_and_bind, resolve_only
from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
    MembershipRole,
    ResolutionPath,
)
from services.identity_authority.exceptions import IdentityError
from services.identity_authority.mqic import MerchantQueryIdentityContext
from services.identity_authority.observability import record
from services.identity_authority.resolve import ResolveIdentityInput


@dataclass(frozen=True)
class SessionMembershipSnapshot:
    """Loaded session identity inputs (ops/diagnostics; not merchant chrome)."""

    merchant_id: str
    primary_store_id: str
    membership_store_ids: frozenset[str]
    stores_by_id: Mapping[str, CanonicalStoreIdentity]
    session_active_store_id: str = ""
    membership_role: MembershipRole = MembershipRole.OWNER
    source: str = "merchant_session"


def _store_to_canonical(store: object) -> Optional[CanonicalStoreIdentity]:
    from services.recovery_store_lookup import is_widget_recovery_zid  # noqa: PLC0415

    slug = (getattr(store, "zid_store_id", None) or "").strip()[:255]
    if not slug or is_widget_recovery_zid(slug):
        return None
    store_pk = int(getattr(store, "id", 0) or 0)
    canonical_id = str(store_pk) if store_pk else f"canonical:{slug}"
    display = (getattr(store, "name", None) or "").strip()
    if not display:
        # onboarding helper may supply display separately
        display = ""
    return CanonicalStoreIdentity(
        canonical_store_id=canonical_id,
        store_slug=slug,
        store_display_name=display,
    )


def _membership_from_primary(store: object) -> SessionMembershipSnapshot:
    """
    Build membership from the merchant primary store.

    Uses the same single-store membership reality as today's session path
    (primary / linked store) — no additional multi-store enumeration query.
    """
    from services.merchant_onboarding_store import (  # noqa: PLC0415
        merchant_store_display_name,
    )

    canonical = _store_to_canonical(store)
    if canonical is None:
        raise IdentityError("rejected_system_slug", "rejected_system_slug")
    display = merchant_store_display_name(store, merchant_user=None)
    if display:
        canonical = CanonicalStoreIdentity(
            canonical_store_id=canonical.canonical_store_id,
            store_slug=canonical.store_slug,
            store_display_name=display,
        )
    cid = canonical.canonical_store_id
    return SessionMembershipSnapshot(
        merchant_id="",  # filled by caller
        primary_store_id=cid,
        membership_store_ids=frozenset({cid}),
        stores_by_id={cid: canonical},
        membership_role=MembershipRole.OWNER,
        source="merchant_primary_store",
    )


def load_session_membership(
    *,
    cookies: Optional[Mapping[str, str]] = None,
) -> Optional[SessionMembershipSnapshot]:
    """
    Load merchant principal + membership + primary from the session cookie.

    Same lookup class as ``resolve_merchant_onboarding_store`` / prior Knowledge
    session bind — not a new database query pattern.
    """
    from services.merchant_onboarding_store import (  # noqa: PLC0415
        resolve_merchant_onboarding_store,
    )

    store, meta = resolve_merchant_onboarding_store(cookies=dict(cookies or {}))
    if store is None:
        return None
    mid = getattr(meta, "merchant_id", None)
    if mid is None:
        return None
    try:
        snap = _membership_from_primary(store)
    except IdentityError:
        return None
    display = (getattr(meta, "store_name", None) or "").strip()
    stores = dict(snap.stores_by_id)
    if display:
        primary = stores[snap.primary_store_id]
        stores[snap.primary_store_id] = CanonicalStoreIdentity(
            canonical_store_id=primary.canonical_store_id,
            store_slug=primary.store_slug,
            store_display_name=display,
        )
    merchant_id = str(int(mid))
    membership_ids = set(snap.membership_store_ids)
    # RC-3 B3: when Lab linked demo.merchant_user_id to this merchant, include
    # demo in membership so Reality Attach can authorize the sim tenant.
    # Primary remains the signup store (onboarding rejects system slug demo).
    try:
        from extensions import db  # noqa: PLC0415
        from models import Store  # noqa: PLC0415
        from services.store_reality_simulator.contracts_v1 import (  # noqa: PLC0415
            DEMO_STORE_SLUG,
        )

        demo_row = (
            db.session.query(Store)
            .filter(
                Store.zid_store_id == DEMO_STORE_SLUG,
                Store.merchant_user_id == int(mid),
            )
            .first()
        )
    except Exception:  # noqa: BLE001
        demo_row = None
    if demo_row is not None:
        # _store_to_canonical rejects demo (widget-recovery guard). Lab Attach
        # membership must admit the sim tenant explicitly when owned.
        demo_pk = str(int(demo_row.id))
        stores[demo_pk] = CanonicalStoreIdentity(
            canonical_store_id=demo_pk,
            store_slug=DEMO_STORE_SLUG,
            store_display_name=(getattr(demo_row, "name", None) or "").strip()
            or DEMO_STORE_SLUG,
        )
        membership_ids.add(demo_pk)

    return SessionMembershipSnapshot(
        merchant_id=merchant_id,
        primary_store_id=snap.primary_store_id,
        membership_store_ids=frozenset(membership_ids),
        stores_by_id=stores,
        membership_role=MembershipRole.OWNER,
        source=str(getattr(meta, "source", None) or snap.source),
    )


def _session_active_canonical_id(
    snap: SessionMembershipSnapshot,
) -> str:
    """
    Session active store pointer (Architecture §1.8).

    Reads existing request-scoped ``merchant_auth_store_slug`` when set and
    membership-valid. Does not invent a second authority.
    """
    try:
        from services.merchant_auth_context import (  # noqa: PLC0415
            get_merchant_auth_store_slug,
        )

        slug = (get_merchant_auth_store_slug() or "").strip()[:255]
    except Exception:  # noqa: BLE001
        slug = ""
    if not slug:
        return ""
    for cid, store in snap.stores_by_id.items():
        if store.store_slug == slug and cid in snap.membership_store_ids:
            return cid
    # Slug set but not in membership → ignore (fail closed at explicit mismatch)
    return ""


def build_session_resolve_input(
    snap: SessionMembershipSnapshot,
    *,
    explicit_store_id: str = "",
    explicit_store_slug: str = "",
    session_active_store_id: str = "",
    correlation_id: str = "",
) -> ResolveIdentityInput:
    """
    Compose ResolveIdentityInput for session (Phase 3 contract).

    Phase 5: when Reality Attach is active, merge simulation fields so the
    same Phase 3 entry yields ATTACH-path MQIC. Attach never resolves here —
    it only supplies Authority inputs.
    """
    session_id = (session_active_store_id or "").strip() or _session_active_canonical_id(
        snap
    )
    sim_run = ""
    sim_store = ""
    replay = ""
    corr = (correlation_id or "").strip()
    try:
        from services.identity_authority.reality_attach_v1 import (  # noqa: PLC0415
            peek_attach_resolve_inputs,
        )

        attach = peek_attach_resolve_inputs()
    except Exception:  # noqa: BLE001
        attach = None
    if attach:
        sim_run = attach.get("simulation_run_id") or ""
        sim_store = attach.get("simulation_canonical_store_id") or ""
        replay = attach.get("replay_id") or ""
        if not corr:
            corr = attach.get("correlation_id") or ""
    return ResolveIdentityInput(
        merchant_id=snap.merchant_id,
        stores_by_id=snap.stores_by_id,
        membership_store_ids=snap.membership_store_ids,
        primary_store_id=snap.primary_store_id,
        session_active_store_id=session_id,
        explicit_store_id=(explicit_store_id or "").strip(),
        explicit_store_slug=(explicit_store_slug or "").strip(),
        membership_role=snap.membership_role,
        simulation_run_id=sim_run,
        simulation_canonical_store_id=sim_store,
        replay_id=replay,
        correlation_id=corr,
    )


def resolve_mqic_from_session(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    explicit_store_id: str = "",
    explicit_store_slug: str = "",
    session_active_store_id: str = "",
    correlation_id: str = "",
    bind: bool = True,
) -> Optional[MerchantQueryIdentityContext]:
    """
    Phase 3 entry: session → membership → active store → MQIC.

    ``bind=True`` (default) enforces single resolve for the request scope.
    """
    snap = load_session_membership(cookies=cookies)
    if snap is None:
        return None
    inp = build_session_resolve_input(
        snap,
        explicit_store_id=explicit_store_id,
        explicit_store_slug=explicit_store_slug,
        session_active_store_id=session_active_store_id,
        correlation_id=correlation_id,
    )
    try:
        if bind:
            return resolve_and_bind(inp)
        return resolve_only(inp)
    except IdentityError:
        record("resolve_fail")
        return None


def session_membership_diagnostics(
    mqic: Optional[MerchantQueryIdentityContext] = None,
) -> dict:
    """Ops diagnostics for Phase 3 — not merchant chrome."""
    from services.identity_authority.context import get_mqic
    from services.identity_authority.authority import identity_diagnostics

    active = mqic if mqic is not None else get_mqic()
    path = active.resolution_path.value if active is not None else None
    return {
        "authority_owner": AUTHORITY_SOURCE_ID,
        "phase": "session_membership_v1",
        "resolution_path": path,
        "paths_supported": [
            ResolutionPath.EXPLICIT.value,
            ResolutionPath.SESSION.value,
            ResolutionPath.PRIMARY.value,
            ResolutionPath.ATTACH.value,
        ],
        "identity_diagnostics": identity_diagnostics(active),
    }


__all__ = [
    "SessionMembershipSnapshot",
    "build_session_resolve_input",
    "load_session_membership",
    "resolve_mqic_from_session",
    "session_membership_diagnostics",
]
