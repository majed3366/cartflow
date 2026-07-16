# -*- coding: utf-8 -*-
"""
Platform Identity Authority — public façade (INV-002 WP-1).

Stable imports for future consumers.
Consumer migration: later WPs. HTTP composition middleware: WP-2.
Simulation Attach product path: WP-5 / Phase 5.
"""
from __future__ import annotations

from services.identity_authority.authority import (
    authority_source_id,
    identity_diagnostics,
    resolve_and_bind,
    resolve_only,
)
from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    CanonicalStoreIdentity,
    IdentityConfidence,
    MembershipRole,
    ProviderAliasDirectory,
    ProviderAliasKey,
    ProviderBinding,
    ResolutionPath,
    identity_provenance_dict,
)
from services.identity_authority.context import (
    assert_mqic_active,
    bind_mqic,
    clear_mqic,
    get_mqic,
    mqic_scope,
    peek_resolve_count,
    require_mqic,
    reset_mqic,
)
from services.identity_authority.exceptions import (
    DualResolveViolation,
    IdentityAuthorityError,
    IdentityError,
    IdentityImmutabilityViolation,
    IdentityOwnershipViolation,
    MissingMerchantQueryIdentityContext,
)
from services.identity_authority.mqic import (
    MerchantQueryIdentityContext,
    assert_immutable_fields_unchanged,
    reject_field_mutation,
    seal_mqic,
)
from services.identity_authority.observability import (
    identity_context_metadata,
    record,
    reset_counters,
    resolution_provenance,
    snapshot_counters,
    violation_detection_snapshot,
)
from services.identity_authority.resolve import ResolveIdentityInput, resolve_mqic
from services.identity_authority.knowledge_consumer_v1 import (
    attach_knowledge_identity_observability,
    bind_mqic_from_merchant_session,
    ensure_knowledge_mqic,
    knowledge_identity_diagnostics,
    knowledge_identity_scope,
    mqic_from_caller_store_slug,
)
from services.identity_authority.session_membership_v1 import (
    SessionMembershipSnapshot,
    build_session_resolve_input,
    load_session_membership,
    resolve_mqic_from_session,
    session_membership_diagnostics,
)
from services.identity_authority.daily_brief_consumer_v1 import (
    attach_daily_brief_identity_observability,
    bind_mqic_for_daily_brief,
    daily_brief_identity_diagnostics,
    daily_brief_identity_scope,
    ensure_daily_brief_mqic,
)

__all__ = [
    # Authority
    "AUTHORITY_SOURCE_ID",
    "authority_source_id",
    "resolve_mqic",
    "resolve_only",
    "resolve_and_bind",
    "identity_diagnostics",
    # MQIC
    "MerchantQueryIdentityContext",
    "ResolveIdentityInput",
    "seal_mqic",
    "assert_immutable_fields_unchanged",
    "reject_field_mutation",
    # Context
    "get_mqic",
    "require_mqic",
    "bind_mqic",
    "reset_mqic",
    "clear_mqic",
    "mqic_scope",
    "peek_resolve_count",
    "assert_mqic_active",
    # Contracts
    "CanonicalStoreIdentity",
    "ProviderBinding",
    "ProviderAliasKey",
    "ProviderAliasDirectory",
    "ResolutionPath",
    "IdentityConfidence",
    "MembershipRole",
    "identity_provenance_dict",
    # Observability
    "resolution_provenance",
    "identity_context_metadata",
    "violation_detection_snapshot",
    "snapshot_counters",
    "reset_counters",
    "record",
    # Errors
    "IdentityAuthorityError",
    "IdentityError",
    "MissingMerchantQueryIdentityContext",
    "IdentityImmutabilityViolation",
    "IdentityOwnershipViolation",
    "DualResolveViolation",
    # Knowledge consumer (WP-2)
    "knowledge_identity_scope",
    "ensure_knowledge_mqic",
    "bind_mqic_from_merchant_session",
    "mqic_from_caller_store_slug",
    "knowledge_identity_diagnostics",
    "attach_knowledge_identity_observability",
    # Session & membership (WP-3 / Phase 3)
    "SessionMembershipSnapshot",
    "load_session_membership",
    "build_session_resolve_input",
    "resolve_mqic_from_session",
    "session_membership_diagnostics",
    # Daily Brief consumer (WP-4 / Phase 4 surface)
    "daily_brief_identity_scope",
    "ensure_daily_brief_mqic",
    "bind_mqic_for_daily_brief",
    "daily_brief_identity_diagnostics",
    "attach_daily_brief_identity_observability",
]

__version__ = "4"
