# -*- coding: utf-8 -*-
"""
ResolveMQIC — pure identity resolution (INV-002 WP-1).

No database queries. No I/O. No provider HTTP.
Callers supply membership + canonical store records already loaded.
Later WPs may load inputs; this module only resolves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence
from uuid import uuid4

from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
    IdentityConfidence,
    MembershipRole,
    ProviderAliasDirectory,
    ProviderBinding,
    ResolutionPath,
    identity_provenance_dict,
)
from services.identity_authority.exceptions import IdentityError
from services.identity_authority.mqic import MerchantQueryIdentityContext, seal_mqic


@dataclass(frozen=True)
class ResolveIdentityInput:
    """
    Explicit resolve inputs (composition root / tests supply these).

    WP-1 does not fetch MerchantUser / Store rows — no new DB queries.
    """

    merchant_id: str
    stores_by_id: Mapping[str, CanonicalStoreIdentity]
    membership_store_ids: frozenset[str]
    primary_store_id: str = ""
    session_active_store_id: str = ""
    explicit_store_id: str = ""
    explicit_store_slug: str = ""
    membership_role: MembershipRole = MembershipRole.OPERATOR
    alias_directory: Optional[ProviderAliasDirectory] = None
    provider: str = ""
    external_shop_id: str = ""
    install_id: str = ""
    simulation_run_id: str = ""
    simulation_canonical_store_id: str = ""
    replay_id: str = ""
    correlation_id: str = ""


def _store_or_fail(
    stores_by_id: Mapping[str, CanonicalStoreIdentity], store_id: str
) -> CanonicalStoreIdentity:
    store = stores_by_id.get(store_id)
    if store is None:
        raise IdentityError("unknown_canonical_store", f"unknown_store:{store_id}")
    return store


def _find_by_slug(
    stores_by_id: Mapping[str, CanonicalStoreIdentity], slug: str
) -> Optional[CanonicalStoreIdentity]:
    needle = (slug or "").strip()
    if not needle:
        return None
    matches = [s for s in stores_by_id.values() if s.store_slug == needle]
    if len(matches) > 1:
        raise IdentityError("ambiguous_store_slug", f"ambiguous_slug:{needle}")
    return matches[0] if matches else None


def _assert_member(membership: frozenset[str], store_id: str) -> None:
    if store_id not in membership:
        raise IdentityError(
            "membership_denied", f"merchant_not_member_of_store:{store_id}"
        )


def resolve_mqic(inp: ResolveIdentityInput) -> MerchantQueryIdentityContext:
    """
    Single resolve function (Architecture §1.8).

    Order:
      1. merchant_id required
      2. candidate active store: explicit → session → primary → fail
         (attach / alias may supply candidate when declared)
      3. alias → canonical when provider external id supplied
      4. optional simulation/replay stamps
      5. emit sealed MQIC + provenance
    """
    merchant_id = (inp.merchant_id or "").strip()
    if not merchant_id:
        raise IdentityError("merchant_required", "merchant_id_required")

    membership = frozenset(
        (s or "").strip() for s in inp.membership_store_ids if (s or "").strip()
    )
    stores = dict(inp.stores_by_id or {})
    alias_used = False
    path: Optional[ResolutionPath] = None
    candidate_id = ""

    # Attach path (simulation review): declared run store wins when authorized.
    sim_run = (inp.simulation_run_id or "").strip()
    sim_store = (inp.simulation_canonical_store_id or "").strip()
    if sim_run and sim_store:
        _assert_member(membership, sim_store)
        candidate_id = sim_store
        path = ResolutionPath.ATTACH
    else:
        explicit_id = (inp.explicit_store_id or "").strip()
        explicit_slug = (inp.explicit_store_slug or "").strip()
        if explicit_id or explicit_slug:
            if explicit_id:
                store = _store_or_fail(stores, explicit_id)
            else:
                found = _find_by_slug(stores, explicit_slug)
                if found is None:
                    raise IdentityError(
                        "unknown_store_slug", f"unknown_slug:{explicit_slug}"
                    )
                store = found
            _assert_member(membership, store.canonical_store_id)
            candidate_id = store.canonical_store_id
            path = ResolutionPath.EXPLICIT
        else:
            session_id = (inp.session_active_store_id or "").strip()
            if session_id:
                _assert_member(membership, session_id)
                candidate_id = session_id
                path = ResolutionPath.SESSION
            else:
                primary = (inp.primary_store_id or "").strip()
                if primary:
                    _assert_member(membership, primary)
                    candidate_id = primary
                    path = ResolutionPath.PRIMARY

    # Provider alias may resolve candidate when no store selected yet (IA-1).
    provider = (inp.provider or "").strip().lower()
    external = (inp.external_shop_id or "").strip()
    if not candidate_id and provider and external:
        if inp.alias_directory is None:
            raise IdentityError("alias_directory_required", "alias_directory_required")
        try:
            mapped = inp.alias_directory.resolve(
                provider, external, install_id=inp.install_id or ""
            )
        except ValueError as exc:
            raise IdentityError("alias_resolve_failed", str(exc)) from exc
        _assert_member(membership, mapped)
        candidate_id = mapped
        path = ResolutionPath.ALIAS
        alias_used = True

    if not candidate_id or path is None:
        raise IdentityError("no_active_store", "no_active_store")

    store = _store_or_fail(stores, candidate_id)
    _assert_member(membership, store.canonical_store_id)

    # Primary must remain in membership when present (I-1).
    primary = (inp.primary_store_id or "").strip()
    if primary and primary not in membership:
        raise IdentityError("orphan_primary", "primary_not_in_membership")

    bindings: Sequence[ProviderBinding] = ()
    if inp.alias_directory is not None:
        bindings = inp.alias_directory.bindings_for_canonical(store.canonical_store_id)
        if provider and external:
            # Ensure requested alias maps to the same canonical (no silent remap).
            try:
                mapped = inp.alias_directory.resolve(
                    provider, external, install_id=inp.install_id or ""
                )
            except ValueError as exc:
                raise IdentityError("alias_resolve_failed", str(exc)) from exc
            if mapped != store.canonical_store_id:
                raise IdentityError(
                    "alias_canonical_mismatch",
                    "provider_alias_resolves_to_different_canonical",
                )
            alias_used = True

    corr = (inp.correlation_id or "").strip()[:128] or uuid4().hex[:16]
    confidence = IdentityConfidence.RESOLVED
    provenance = identity_provenance_dict(
        authority_source=AUTHORITY_SOURCE_ID,
        resolution_path=path,
        identity_confidence=confidence,
        correlation_id=corr,
        alias_used=alias_used,
        notes={
            "primary_store_id": primary or None,
            "session_active_store_id": (inp.session_active_store_id or "").strip()
            or None,
        },
    )

    return seal_mqic(
        merchant_id=merchant_id,
        canonical_store_id=store.canonical_store_id,
        store_slug=store.store_slug,
        store_display_name=store.store_display_name,
        membership_role=inp.membership_role,
        resolution_path=path,
        provider_bindings=tuple(bindings),
        simulation_run_id=sim_run if path == ResolutionPath.ATTACH else "",
        replay_id=(inp.replay_id or "").strip(),
        identity_confidence=confidence,
        correlation_id=corr,
        identity_provenance=provenance,
    )
