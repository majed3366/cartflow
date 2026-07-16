# -*- coding: utf-8 -*-
"""WP-1 — Platform Identity Authority foundation (no consumer migration)."""
from __future__ import annotations

import pytest

from services.identity_authority import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
    DualResolveViolation,
    IdentityError,
    IdentityImmutabilityViolation,
    IdentityOwnershipViolation,
    MerchantQueryIdentityContext,
    MissingMerchantQueryIdentityContext,
    ProviderAliasDirectory,
    ProviderBinding,
    ResolutionPath,
    ResolveIdentityInput,
    assert_immutable_fields_unchanged,
    authority_source_id,
    bind_mqic,
    clear_mqic,
    get_mqic,
    identity_diagnostics,
    mqic_scope,
    peek_resolve_count,
    reject_field_mutation,
    require_mqic,
    reset_counters,
    resolve_and_bind,
    resolve_mqic,
    resolve_only,
    seal_mqic,
)


DEMO = CanonicalStoreIdentity(
    canonical_store_id="store_demo",
    store_slug="demo",
    store_display_name="Demo Store",
)
SIGNUP = CanonicalStoreIdentity(
    canonical_store_id="store_signup",
    store_slug="متجر-واقع-صغير-test",
    store_display_name="Signup Store",
)
STORES = {
    DEMO.canonical_store_id: DEMO,
    SIGNUP.canonical_store_id: SIGNUP,
}


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def _input(**kwargs) -> ResolveIdentityInput:
    base = dict(
        merchant_id="m_1",
        stores_by_id=STORES,
        membership_store_ids=frozenset(
            {DEMO.canonical_store_id, SIGNUP.canonical_store_id}
        ),
        primary_store_id=SIGNUP.canonical_store_id,
    )
    base.update(kwargs)
    return ResolveIdentityInput(**base)


# --- Canonical Identity / Authority ownership ---


def test_authority_source_stable() -> None:
    assert authority_source_id() == AUTHORITY_SOURCE_ID
    assert AUTHORITY_SOURCE_ID == "platform_identity_authority"


def test_seal_mqic_is_authority_owned() -> None:
    mqic = seal_mqic(
        merchant_id="m_1",
        canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
    )
    mqic.assert_authority_owned()
    assert mqic.tenant_key() == "demo"


def test_unsealed_mqic_fails_ownership() -> None:
    raw = MerchantQueryIdentityContext(
        merchant_id="m_1",
        canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
    )
    with pytest.raises(IdentityOwnershipViolation):
        raw.assert_authority_owned()
    with pytest.raises(IdentityOwnershipViolation):
        bind_mqic(raw)


# --- Resolve paths ---


def test_resolve_primary() -> None:
    mqic = resolve_mqic(_input())
    assert mqic.store_slug == SIGNUP.store_slug
    assert mqic.resolution_path == ResolutionPath.PRIMARY
    assert mqic.identity_confidence.value == "resolved"
    mqic.assert_authority_owned()


def test_resolve_session_over_primary() -> None:
    mqic = resolve_mqic(
        _input(session_active_store_id=DEMO.canonical_store_id)
    )
    assert mqic.canonical_store_id == DEMO.canonical_store_id
    assert mqic.resolution_path == ResolutionPath.SESSION


def test_resolve_explicit_slug() -> None:
    mqic = resolve_mqic(_input(explicit_store_slug="demo"))
    assert mqic.store_slug == "demo"
    assert mqic.resolution_path == ResolutionPath.EXPLICIT


def test_resolve_attach() -> None:
    mqic = resolve_mqic(
        _input(
            simulation_run_id="srs_1",
            simulation_canonical_store_id=DEMO.canonical_store_id,
        )
    )
    assert mqic.resolution_path == ResolutionPath.ATTACH
    assert mqic.simulation_run_id == "srs_1"
    assert mqic.store_slug == "demo"


def test_no_active_store_fail_closed() -> None:
    with pytest.raises(IdentityError) as ei:
        resolve_mqic(
            _input(primary_store_id="", session_active_store_id="")
        )
    assert ei.value.code == "no_active_store"


def test_membership_denied() -> None:
    with pytest.raises(IdentityError) as ei:
        resolve_mqic(
            _input(
                membership_store_ids=frozenset({SIGNUP.canonical_store_id}),
                explicit_store_id=DEMO.canonical_store_id,
            )
        )
    assert ei.value.code == "membership_denied"


# --- Provider Independence (IA-1) ---


def test_provider_alias_resolves_to_canonical_not_external_slug() -> None:
    directory = ProviderAliasDirectory(
        [
            ProviderBinding(
                provider="zid",
                external_shop_id="zid-shop-999",
                canonical_store_id=DEMO.canonical_store_id,
            )
        ]
    )
    mqic = resolve_mqic(
        _input(
            primary_store_id="",
            provider="zid",
            external_shop_id="zid-shop-999",
            alias_directory=directory,
        )
    )
    assert mqic.store_slug == "demo"
    assert mqic.store_slug != "zid-shop-999"
    assert mqic.resolution_path == ResolutionPath.ALIAS
    assert mqic.provider_bindings[0].external_shop_id == "zid-shop-999"
    assert mqic.canonical_store_id == DEMO.canonical_store_id


def test_alias_ambiguous_fail_closed() -> None:
    directory = ProviderAliasDirectory()
    directory.link(
        ProviderBinding(
            provider="salla",
            external_shop_id="ext-1",
            canonical_store_id=DEMO.canonical_store_id,
            install_id="a",
        )
    )
    directory.link(
        ProviderBinding(
            provider="salla",
            external_shop_id="ext-1",
            canonical_store_id=SIGNUP.canonical_store_id,
            install_id="b",
        )
    )
    with pytest.raises(IdentityError) as ei:
        resolve_mqic(
            _input(
                primary_store_id="",
                provider="salla",
                external_shop_id="ext-1",
                alias_directory=directory,
            )
        )
    assert ei.value.code == "alias_resolve_failed"


# --- Single Identity Resolution (IA-2) ---


def test_single_resolve_and_bind() -> None:
    mqic = resolve_and_bind(_input())
    assert get_mqic() is mqic
    assert peek_resolve_count() == 1
    assert require_mqic().store_slug == SIGNUP.store_slug


def test_dual_resolve_violation() -> None:
    resolve_and_bind(_input())
    with pytest.raises(DualResolveViolation):
        # Identical second resolve still violates IA-2 (exactly once).
        resolve_and_bind(_input())


def test_dual_bind_identical_still_violation() -> None:
    mqic = resolve_only(_input())
    bind_mqic(mqic)
    with pytest.raises(DualResolveViolation):
        bind_mqic(mqic)


def test_request_context_propagation_via_scope() -> None:
    assert get_mqic() is None
    mqic = resolve_only(_input(explicit_store_slug="demo"))
    with mqic_scope(mqic):
        assert require_mqic().store_slug == "demo"
        assert peek_resolve_count() == 1
    assert get_mqic() is None


def test_require_mqic_when_missing() -> None:
    with pytest.raises(MissingMerchantQueryIdentityContext):
        require_mqic()


# --- Identity Immutability (IA-3) ---


def test_mqic_frozen_rejects_setattr() -> None:
    mqic = resolve_only(_input())
    with pytest.raises(Exception):
        mqic.store_slug = "hacked"  # type: ignore[misc]


def test_reject_field_mutation_helper() -> None:
    mqic = resolve_only(_input())
    with pytest.raises(IdentityImmutabilityViolation):
        reject_field_mutation(mqic, "store_slug")


def test_assert_immutable_fields_detects_change() -> None:
    a = resolve_only(_input())
    b = resolve_only(_input(session_active_store_id=DEMO.canonical_store_id))
    with pytest.raises(IdentityImmutabilityViolation):
        assert_immutable_fields_unchanged(a, b)


def test_bind_different_identity_is_immutability_or_dual() -> None:
    a = resolve_only(_input())
    b = resolve_only(_input(session_active_store_id=DEMO.canonical_store_id))
    bind_mqic(a)
    with pytest.raises((DualResolveViolation, IdentityImmutabilityViolation)):
        bind_mqic(b)


# --- Observability ---


def test_identity_diagnostics_exposes_provenance() -> None:
    mqic = resolve_and_bind(_input(explicit_store_slug="demo"))
    diag = identity_diagnostics()
    assert diag["authority_source"] == AUTHORITY_SOURCE_ID
    assert diag["context"]["bound"] is True
    assert diag["context"]["store_slug"] == "demo"
    assert diag["resolution_provenance"]["resolution_path"] == "explicit"
    assert "violations" in diag
    assert diag["counters"]["resolve_ok"] >= 1


# --- No I/O foundation guarantee (structural) ---


def test_resolve_uses_only_provided_stores() -> None:
    """Unknown store id fails without inventing a slug."""
    with pytest.raises(IdentityError) as ei:
        resolve_mqic(
            _input(
                primary_store_id="missing",
                membership_store_ids=frozenset({"missing"}),
            )
        )
    assert ei.value.code == "unknown_canonical_store"
