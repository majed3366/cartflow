# -*- coding: utf-8 -*-
"""
Identity Authority contracts — stable types (INV-002 WP-1).

Consumers depend on these interfaces, not on resolver internals.
No I/O. No provider API clients. Provider ids are aliases only (IA-1).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence


class ResolutionPath(str, Enum):
    """How active store was chosen (Architecture §3.3)."""

    PRIMARY = "primary"
    EXPLICIT = "explicit"
    SESSION = "session"
    ATTACH = "attach"
    ALIAS = "alias"


class IdentityConfidence(str, Enum):
    """MQIC confidence (Architecture §3.3)."""

    RESOLVED = "resolved"
    DEGRADED = "degraded"
    FAILED = "failed"


class MembershipRole(str, Enum):
    """Operator rights on the active store (logical)."""

    OWNER = "owner"
    OPERATOR = "operator"
    VIEWER = "viewer"


AUTHORITY_SOURCE_ID = "platform_identity_authority"


@dataclass(frozen=True)
class CanonicalStoreIdentity:
    """
    CartFlow-native store identity (IA-1 / Canonical Store Registry logical record).

    Provider shop ids must never appear as store_slug.
    """

    canonical_store_id: str
    store_slug: str
    store_display_name: str = ""

    def __post_init__(self) -> None:
        cid = (self.canonical_store_id or "").strip()
        slug = (self.store_slug or "").strip()
        if not cid:
            raise ValueError("canonical_store_id_required")
        if not slug:
            raise ValueError("store_slug_required")
        object.__setattr__(self, "canonical_store_id", cid)
        object.__setattr__(self, "store_slug", slug)
        object.__setattr__(
            self, "store_display_name", (self.store_display_name or "").strip()
        )


@dataclass(frozen=True)
class ProviderBinding:
    """
    Provenance-only provider alias binding.

    Surfaces must not use external_shop_id as a tenant key (IA-1).
    """

    provider: str
    external_shop_id: str
    canonical_store_id: str
    install_id: str = ""

    def __post_init__(self) -> None:
        provider = (self.provider or "").strip().lower()
        external = (self.external_shop_id or "").strip()
        canonical = (self.canonical_store_id or "").strip()
        if not provider:
            raise ValueError("provider_required")
        if not external:
            raise ValueError("external_shop_id_required")
        if not canonical:
            raise ValueError("canonical_store_id_required")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "external_shop_id", external)
        object.__setattr__(self, "canonical_store_id", canonical)
        object.__setattr__(self, "install_id", (self.install_id or "").strip())


@dataclass(frozen=True)
class ProviderAliasKey:
    """External identity tuple — integration boundary only."""

    provider: str
    external_shop_id: str
    install_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", (self.provider or "").strip().lower())
        object.__setattr__(
            self, "external_shop_id", (self.external_shop_id or "").strip()
        )
        object.__setattr__(self, "install_id", (self.install_id or "").strip())

    def as_tuple(self) -> tuple[str, str, str]:
        return (self.provider, self.external_shop_id, self.install_id)


class ProviderAliasDirectory:
    """
    In-memory alias → canonical map (IA-1).

    WP-1: pure structure for resolve tests — no DB, no provider HTTP.
    Persistent alias storage is a later WP.
    """

    def __init__(
        self, bindings: Optional[Sequence[ProviderBinding]] = None
    ) -> None:
        self._by_key: dict[tuple[str, str, str], str] = {}
        self._by_provider_external: dict[tuple[str, str], list[str]] = {}
        for b in bindings or ():
            self.link(b)

    def link(self, binding: ProviderBinding) -> None:
        key = (
            binding.provider,
            binding.external_shop_id,
            binding.install_id,
        )
        existing = self._by_key.get(key)
        if existing is not None and existing != binding.canonical_store_id:
            raise ValueError(
                f"alias_conflict:{binding.provider}:{binding.external_shop_id}"
            )
        self._by_key[key] = binding.canonical_store_id
        pe = (binding.provider, binding.external_shop_id)
        bucket = self._by_provider_external.setdefault(pe, [])
        if binding.canonical_store_id not in bucket:
            bucket.append(binding.canonical_store_id)

    def resolve(
        self,
        provider: str,
        external_shop_id: str,
        *,
        install_id: str = "",
    ) -> str:
        """
        Resolve alias to exactly one canonical_store_id.

        Ambiguous fan-out (multiple canonicals for same provider+external
        without install disambiguation) fail closed.
        """
        p = (provider or "").strip().lower()
        ext = (external_shop_id or "").strip()
        inst = (install_id or "").strip()
        if not p or not ext:
            raise ValueError("alias_key_incomplete")
        if inst:
            cid = self._by_key.get((p, ext, inst))
            if cid:
                return cid
        pe = (p, ext)
        candidates = self._by_provider_external.get(pe) or []
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError(f"alias_ambiguous:{p}:{ext}")
        raise ValueError(f"alias_not_found:{p}:{ext}")

    def bindings_for_canonical(
        self, canonical_store_id: str
    ) -> tuple[ProviderBinding, ...]:
        cid = (canonical_store_id or "").strip()
        out: list[ProviderBinding] = []
        for (provider, external, install), mapped in self._by_key.items():
            if mapped == cid:
                out.append(
                    ProviderBinding(
                        provider=provider,
                        external_shop_id=external,
                        canonical_store_id=cid,
                        install_id=install,
                    )
                )
        return tuple(out)


def identity_provenance_dict(
    *,
    authority_source: str,
    resolution_path: ResolutionPath,
    identity_confidence: IdentityConfidence,
    correlation_id: str = "",
    alias_used: bool = False,
    notes: Optional[Mapping[str, object]] = None,
) -> dict:
    """Internal-only provenance (not merchant chrome)."""
    payload: dict = {
        "authority_source": authority_source,
        "resolution_path": resolution_path.value,
        "identity_confidence": identity_confidence.value,
        "correlation_id": (correlation_id or "")[:128] or None,
        "alias_used": bool(alias_used),
    }
    if notes:
        payload["notes"] = dict(notes)
    return payload
