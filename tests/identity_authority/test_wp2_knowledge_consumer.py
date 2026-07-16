# -*- coding: utf-8 -*-
"""INV-002 WP-2 — Knowledge consumes Identity Authority (no independent resolve)."""
from __future__ import annotations

import pytest

from extensions import db
from services.identity_authority import (
    AUTHORITY_SOURCE_ID,
    DualResolveViolation,
    IdentityError,
    IdentityImmutabilityViolation,
    ResolveIdentityInput,
    clear_mqic,
    get_mqic,
    knowledge_identity_diagnostics,
    knowledge_identity_scope,
    mqic_from_caller_store_slug,
    reject_field_mutation,
    reset_counters,
    resolve_and_bind,
)
from services.identity_authority.contracts import CanonicalStoreIdentity
from services.knowledge_layer_v1 import build_knowledge_report
from services.knowledge_metrics_v1 import collect_knowledge_metrics


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def test_knowledge_consumes_mqic_store_slug() -> None:
    mqic = mqic_from_caller_store_slug("demo-kl-wp2", merchant_id="9")
    with knowledge_identity_scope(mqic=mqic):
        report = build_knowledge_report(
            db.session, mqic.store_slug, window_days=7, mqic=mqic
        )
    assert report.store_slug == "demo-kl-wp2"
    assert get_mqic() is None


def test_knowledge_caller_slug_sealed_via_authority() -> None:
    report = build_knowledge_report(db.session, "caller-slug-wp2", window_days=7)
    assert report.store_slug == "caller-slug-wp2"
    assert get_mqic() is None  # scope cleared


def test_knowledge_slug_mismatch_fail_closed() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with knowledge_identity_scope(mqic=mqic):
        with pytest.raises(IdentityError) as ei:
            build_knowledge_report(
                db.session, "store-b", window_days=7, mqic=mqic
            )
        assert ei.value.code == "store_slug_mismatch"


def test_identity_resolved_once_in_knowledge_scope() -> None:
    mqic = mqic_from_caller_store_slug("once-store", merchant_id="1")
    with knowledge_identity_scope(mqic=mqic):
        collect_knowledge_metrics(db.session, mqic.store_slug, mqic=mqic)
        other = mqic_from_caller_store_slug("once-store", merchant_id="1")
        with pytest.raises(DualResolveViolation):
            resolve_and_bind(
                ResolveIdentityInput(
                    merchant_id="1",
                    stores_by_id={
                        other.canonical_store_id: CanonicalStoreIdentity(
                            canonical_store_id=other.canonical_store_id,
                            store_slug=other.store_slug,
                        )
                    },
                    membership_store_ids=frozenset({other.canonical_store_id}),
                    primary_store_id=other.canonical_store_id,
                )
            )


def test_immutability_preserved_under_knowledge() -> None:
    mqic = mqic_from_caller_store_slug("imm-store", merchant_id="1")
    with knowledge_identity_scope(mqic=mqic):
        build_knowledge_report(db.session, mqic.store_slug, mqic=mqic)
        with pytest.raises(IdentityImmutabilityViolation):
            reject_field_mutation(mqic, "store_slug")


def test_provider_independence_knowledge_tenant_is_canonical() -> None:
    mqic = mqic_from_caller_store_slug("canonical-tenant", merchant_id="1")
    assert mqic.store_slug == "canonical-tenant"
    assert mqic.canonical_store_id.startswith("canonical:")


def test_knowledge_cannot_use_unsealed_identity() -> None:
    from services.identity_authority.mqic import MerchantQueryIdentityContext
    from services.identity_authority.exceptions import IdentityOwnershipViolation

    raw = MerchantQueryIdentityContext(
        merchant_id="1",
        canonical_store_id="x",
        store_slug="raw-slug",
    )
    with pytest.raises(IdentityOwnershipViolation):
        with knowledge_identity_scope(mqic=raw):
            build_knowledge_report(db.session, "raw-slug", mqic=raw)


def test_knowledge_identity_diagnostics_shape() -> None:
    mqic = mqic_from_caller_store_slug("diag-store", merchant_id="1")
    with knowledge_identity_scope(mqic=mqic):
        diag = knowledge_identity_diagnostics()
    assert diag["authority_owner"] == AUTHORITY_SOURCE_ID
    assert diag["authority_consumer"] == "knowledge"
    assert diag["knowledge_authority_source"] == AUTHORITY_SOURCE_ID
