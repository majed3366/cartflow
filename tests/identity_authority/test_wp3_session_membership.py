# -*- coding: utf-8 -*-
"""INV-002 WP-3 — Session & membership binding (Phase 3)."""
from __future__ import annotations

from unittest import mock

import pytest

from services.identity_authority import (
    AUTHORITY_SOURCE_ID,
    DualResolveViolation,
    IdentityError,
    IdentityImmutabilityViolation,
    ResolutionPath,
    clear_mqic,
    get_mqic,
    reject_field_mutation,
    reset_counters,
    resolve_mqic_from_session,
    session_membership_diagnostics,
)
from services.identity_authority.contracts import CanonicalStoreIdentity
from services.identity_authority.session_membership_v1 import (
    SessionMembershipSnapshot,
    build_session_resolve_input,
)
from services.identity_authority.resolve import resolve_mqic as resolve_mqic_core
from services.merchant_auth_context import (
    reset_merchant_auth_store_slug,
    set_merchant_auth_store_slug,
)


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def _snap(
    *,
    primary: str = "1",
    slug: str = "sess-primary",
    extra: dict | None = None,
) -> SessionMembershipSnapshot:
    stores = {
        primary: CanonicalStoreIdentity(
            canonical_store_id=primary,
            store_slug=slug,
            store_display_name="Primary",
        )
    }
    if extra:
        stores.update(extra)
    return SessionMembershipSnapshot(
        merchant_id="42",
        primary_store_id=primary,
        membership_store_ids=frozenset(stores.keys()),
        stores_by_id=stores,
    )


def test_primary_path_when_no_session_active() -> None:
    inp = build_session_resolve_input(_snap())
    mqic = resolve_mqic_core(inp)
    assert mqic.resolution_path == ResolutionPath.PRIMARY
    assert mqic.store_slug == "sess-primary"
    assert mqic.merchant_id == "42"


def test_session_active_overrides_primary() -> None:
    secondary = CanonicalStoreIdentity(
        canonical_store_id="2",
        store_slug="sess-active",
    )
    snap = _snap(
        extra={"2": secondary},
    )
    token = set_merchant_auth_store_slug("sess-active")
    try:
        inp = build_session_resolve_input(snap)
        mqic = resolve_mqic_core(inp)
        assert mqic.resolution_path == ResolutionPath.SESSION
        assert mqic.store_slug == "sess-active"
    finally:
        reset_merchant_auth_store_slug(token)


def test_explicit_overrides_session_and_primary() -> None:
    secondary = CanonicalStoreIdentity(
        canonical_store_id="2",
        store_slug="sess-explicit",
    )
    snap = _snap(extra={"2": secondary})
    token = set_merchant_auth_store_slug("sess-primary")
    try:
        inp = build_session_resolve_input(
            snap, explicit_store_slug="sess-explicit"
        )
        mqic = resolve_mqic_core(inp)
        assert mqic.resolution_path == ResolutionPath.EXPLICIT
        assert mqic.store_slug == "sess-explicit"
    finally:
        reset_merchant_auth_store_slug(token)


def test_membership_denied_for_explicit_outsider() -> None:
    snap = _snap()
    inp = build_session_resolve_input(snap, explicit_store_id="999")
    # unknown canonical fails before membership
    with pytest.raises(IdentityError):
        resolve_mqic_core(inp)


def test_membership_denied_when_not_member() -> None:
    outsider = CanonicalStoreIdentity(
        canonical_store_id="9",
        store_slug="other",
    )
    # Put outsider in stores_by_id but NOT membership — simulate bad input
    stores = dict(_snap().stores_by_id)
    stores["9"] = outsider
    snap = SessionMembershipSnapshot(
        merchant_id="42",
        primary_store_id="1",
        membership_store_ids=frozenset({"1"}),
        stores_by_id=stores,
    )
    inp = build_session_resolve_input(snap, explicit_store_id="9")
    with pytest.raises(IdentityError) as ei:
        resolve_mqic_core(inp)
    assert ei.value.code == "membership_denied"


def test_resolve_mqic_from_session_bind_once() -> None:
    store = mock.Mock(
        id=7,
        zid_store_id="wp3-sess",
        name="S",
        widget_display_name="",
    )
    meta = mock.Mock(merchant_id=7, store_name="S", source="merchant_primary_store")
    with mock.patch(
        "services.identity_authority.session_membership_v1.resolve_merchant_onboarding_store",
        create=True,
    ):
        with mock.patch(
            "services.merchant_onboarding_store.resolve_merchant_onboarding_store",
            return_value=(store, meta),
        ):
            mqic = resolve_mqic_from_session(cookies={"x": "y"}, bind=True)
            assert mqic is not None
            assert mqic.store_slug == "wp3-sess"
            assert get_mqic() is mqic
            with pytest.raises(DualResolveViolation):
                resolve_mqic_from_session(cookies={"x": "y"}, bind=True)


def test_immutability_after_session_bind() -> None:
    store = mock.Mock(
        id=8,
        zid_store_id="imm-sess",
        name="S",
        widget_display_name="",
    )
    meta = mock.Mock(merchant_id=8, store_name="S", source="merchant_primary_store")
    with mock.patch(
        "services.merchant_onboarding_store.resolve_merchant_onboarding_store",
        return_value=(store, meta),
    ):
        mqic = resolve_mqic_from_session(cookies={}, bind=True)
        assert mqic is not None
        with pytest.raises(IdentityImmutabilityViolation):
            reject_field_mutation(mqic, "canonical_store_id")


def test_session_diagnostics_owner() -> None:
    mqic = resolve_mqic_core(build_session_resolve_input(_snap()))
    diag = session_membership_diagnostics(mqic)
    assert diag["authority_owner"] == AUTHORITY_SOURCE_ID
    assert diag["phase"] == "session_membership_v1"
    assert "primary" in diag["paths_supported"]


def test_knowledge_bind_delegates_to_session_phase() -> None:
    from services.identity_authority import bind_mqic_from_merchant_session

    store = mock.Mock(
        id=3,
        zid_store_id="kl-via-sess",
        name="K",
        widget_display_name="",
    )
    meta = mock.Mock(merchant_id=3, store_name="K", source="merchant_primary_store")
    with mock.patch(
        "services.merchant_onboarding_store.resolve_merchant_onboarding_store",
        return_value=(store, meta),
    ):
        mqic = bind_mqic_from_merchant_session(cookies={"a": "b"})
        assert mqic is not None
        assert mqic.store_slug == "kl-via-sess"
        assert mqic.resolution_path == ResolutionPath.PRIMARY
