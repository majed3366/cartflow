# -*- coding: utf-8 -*-
"""
Merchant Query Identity Context (MQIC) — immutable request identity bundle (WP-1).

IA-3: fields must never be mutated after creation.
IA-4: only Identity Authority constructs MQIC instances for product use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from services.identity_authority.contracts import (
    AUTHORITY_SOURCE_ID,
    IdentityConfidence,
    MembershipRole,
    ProviderBinding,
    ResolutionPath,
    identity_provenance_dict,
)
from services.identity_authority.exceptions import (
    IdentityImmutabilityViolation,
    IdentityOwnershipViolation,
)


@dataclass(frozen=True)
class MerchantQueryIdentityContext:
    """
    Immutable Merchant Query Identity Context.

    Merchant-facing services consume this only — never invent store_slug.
    """

    merchant_id: str
    canonical_store_id: str
    store_slug: str
    store_display_name: str = ""
    membership_role: MembershipRole = MembershipRole.OPERATOR
    resolution_path: ResolutionPath = ResolutionPath.PRIMARY
    provider_bindings: Tuple[ProviderBinding, ...] = ()
    simulation_run_id: str = ""
    replay_id: str = ""
    identity_confidence: IdentityConfidence = IdentityConfidence.RESOLVED
    correlation_id: str = ""
    identity_provenance: Mapping[str, Any] = field(default_factory=dict)
    # Sealed marker — only Authority factory sets this.
    _authority_seal: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        mid = (self.merchant_id or "").strip()
        cid = (self.canonical_store_id or "").strip()
        slug = (self.store_slug or "").strip()
        if not mid:
            raise ValueError("merchant_id_required")
        if not cid:
            raise ValueError("canonical_store_id_required")
        if not slug:
            raise ValueError("store_slug_required")
        object.__setattr__(self, "merchant_id", mid)
        object.__setattr__(self, "canonical_store_id", cid)
        object.__setattr__(self, "store_slug", slug)
        object.__setattr__(
            self, "store_display_name", (self.store_display_name or "").strip()
        )
        object.__setattr__(
            self, "simulation_run_id", (self.simulation_run_id or "").strip()[:128]
        )
        object.__setattr__(
            self, "replay_id", (self.replay_id or "").strip()[:128]
        )
        object.__setattr__(
            self, "correlation_id", (self.correlation_id or "").strip()[:128]
        )
        if not isinstance(self.provider_bindings, tuple):
            object.__setattr__(self, "provider_bindings", tuple(self.provider_bindings))
        if not self.identity_provenance:
            object.__setattr__(
                self,
                "identity_provenance",
                identity_provenance_dict(
                    authority_source=AUTHORITY_SOURCE_ID,
                    resolution_path=self.resolution_path,
                    identity_confidence=self.identity_confidence,
                    correlation_id=self.correlation_id,
                    alias_used=bool(self.provider_bindings),
                ),
            )

    def assert_authority_owned(self) -> None:
        """IA-4: MQIC must carry Authority seal."""
        if self._authority_seal != AUTHORITY_SOURCE_ID:
            raise IdentityOwnershipViolation("mqic_not_authority_owned")

    def tenant_key(self) -> str:
        """Canonical tenant key for reads/writes — never a provider shop id."""
        return self.store_slug

    def internal_snapshot(self) -> dict:
        """Ops/diagnostics snapshot — not merchant chrome."""
        self.assert_authority_owned()
        return {
            "merchant_id": self.merchant_id,
            "canonical_store_id": self.canonical_store_id,
            "store_slug": self.store_slug,
            "store_display_name": self.store_display_name or None,
            "membership_role": self.membership_role.value,
            "resolution_path": self.resolution_path.value,
            "identity_confidence": self.identity_confidence.value,
            "simulation_run_id": self.simulation_run_id or None,
            "replay_id": self.replay_id or None,
            "correlation_id": self.correlation_id or None,
            "provider_bindings": [
                {
                    "provider": b.provider,
                    "external_shop_id": b.external_shop_id,
                    "canonical_store_id": b.canonical_store_id,
                    "install_id": b.install_id or None,
                }
                for b in self.provider_bindings
            ],
            "identity_provenance": dict(self.identity_provenance),
            "authority_source": AUTHORITY_SOURCE_ID,
        }


def seal_mqic(**kwargs: Any) -> MerchantQueryIdentityContext:
    """
    Sole supported constructor for product MQIC (IA-4).

    Direct MerchantQueryIdentityContext(...) without seal is rejected by
    assert_authority_owned / bind_mqic.
    """
    kwargs = dict(kwargs)
    kwargs["_authority_seal"] = AUTHORITY_SOURCE_ID
    return MerchantQueryIdentityContext(**kwargs)


def assert_immutable_fields_unchanged(
    original: MerchantQueryIdentityContext,
    candidate: MerchantQueryIdentityContext,
) -> None:
    """
    IA-3: core identity fields must never change after resolution.

    Compared fields: merchant_id, store, canonical, provider bindings,
    session-reflected path, simulation, replay.
    """
    checks = (
        ("merchant_id", original.merchant_id, candidate.merchant_id),
        ("canonical_store_id", original.canonical_store_id, candidate.canonical_store_id),
        ("store_slug", original.store_slug, candidate.store_slug),
        ("resolution_path", original.resolution_path, candidate.resolution_path),
        (
            "simulation_run_id",
            original.simulation_run_id,
            candidate.simulation_run_id,
        ),
        ("replay_id", original.replay_id, candidate.replay_id),
        (
            "provider_bindings",
            original.provider_bindings,
            candidate.provider_bindings,
        ),
    )
    for name, left, right in checks:
        if left != right:
            raise IdentityImmutabilityViolation(f"mqic_mutated:{name}")


def reject_field_mutation(mqic: MerchantQueryIdentityContext, field_name: str) -> None:
    """Explicit violation helper when callers attempt setattr-style mutation."""
    mqic.assert_authority_owned()
    raise IdentityImmutabilityViolation(f"mqic_mutation_forbidden:{field_name}")
