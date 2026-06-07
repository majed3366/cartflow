# -*- coding: utf-8 -*-
"""WhatsApp Template Library — versioning, approval states, fallback chains (no Meta)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.merchant_whatsapp_template_registry_v1 import (
    TEMPLATE_REGISTRY,
    TemplateRegistryEntry,
    get_registry_entry,
    meta_status_label_ar,
)

APPROVAL_DRAFT = "draft"
APPROVAL_PENDING_REVIEW = "pending_review"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_DISABLED = "disabled"

CANONICAL_APPROVAL_STATES: frozenset[str] = frozenset(
    {
        APPROVAL_DRAFT,
        APPROVAL_PENDING_REVIEW,
        APPROVAL_APPROVED,
        APPROVAL_REJECTED,
        APPROVAL_DISABLED,
    }
)

APPROVAL_STATE_LABEL_AR: Mapping[str, str] = {
    APPROVAL_DRAFT: "مسودة",
    APPROVAL_PENDING_REVIEW: "قيد المراجعة",
    APPROVAL_APPROVED: "معتمد",
    APPROVAL_REJECTED: "مرفوض",
    APPROVAL_DISABLED: "معطّل",
}

VALID_APPROVAL_TRANSITIONS: Mapping[str, frozenset[str]] = {
    APPROVAL_DRAFT: frozenset({APPROVAL_PENDING_REVIEW, APPROVAL_DISABLED}),
    APPROVAL_PENDING_REVIEW: frozenset(
        {APPROVAL_APPROVED, APPROVAL_REJECTED, APPROVAL_DRAFT}
    ),
    APPROVAL_APPROVED: frozenset({APPROVAL_DISABLED, APPROVAL_PENDING_REVIEW}),
    APPROVAL_REJECTED: frozenset({APPROVAL_DRAFT, APPROVAL_DISABLED}),
    APPROVAL_DISABLED: frozenset({APPROVAL_DRAFT}),
}

_LIBRARY_EPOCH = datetime(2026, 6, 7, tzinfo=timezone.utc).isoformat()


@dataclass(frozen=True)
class TemplateLibraryVersion:
    template_key: str
    logical_key: str
    template_version: str
    reason_tag: Optional[str]
    default_content: str
    enabled: bool
    active_version: bool
    fallback_template_key: Optional[str]
    approval_state: str
    created_at: str
    updated_at: str
    display_name_ar: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_key": self.template_key,
            "logical_key": self.logical_key,
            "template_version": self.template_version,
            "reason_tag": self.reason_tag,
            "default_content": self.default_content,
            "enabled": self.enabled,
            "active_version": self.active_version,
            "fallback_template_key": self.fallback_template_key,
            "approval_state": self.approval_state,
            "approval_state_ar": approval_state_label_ar(self.approval_state),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "display_name_ar": self.display_name_ar,
        }


def approval_state_label_ar(state: str) -> str:
    return APPROVAL_STATE_LABEL_AR.get((state or "").strip().lower(), state)


def normalize_approval_state(raw: Any) -> str:
    key = (raw or "").strip().lower()
    return key if key in CANONICAL_APPROVAL_STATES else APPROVAL_DRAFT


def version_key(logical_key: str, version: str) -> str:
    lk = (logical_key or "").strip().upper()
    ver = (version or "v1").strip().lower()
    if ver.startswith("v"):
        return f"{lk}_{ver.upper()}"
    return f"{lk}_V{ver.upper()}"


def _fallback_for_logical(logical_key: str) -> Optional[str]:
    lk = (logical_key or "").strip().upper()
    if lk == "UNKNOWN_REASON_TEMPLATE":
        return None
    if lk.startswith("FOLLOWUP_") or lk == "VIP_ALERT_TEMPLATE":
        return None
    return "UNKNOWN_REASON_TEMPLATE"


def _build_library_from_registry() -> dict[str, TemplateLibraryVersion]:
    out: dict[str, TemplateLibraryVersion] = {}
    for logical_key, entry in TEMPLATE_REGISTRY.items():
        vk = version_key(logical_key, "v1")
        out[vk] = TemplateLibraryVersion(
            template_key=vk,
            logical_key=logical_key,
            template_version="v1",
            reason_tag=entry.reason_tag,
            default_content=entry.default_content,
            enabled=entry.enabled,
            active_version=True,
            fallback_template_key=_fallback_for_logical(logical_key),
            approval_state=normalize_approval_state(entry.future_meta_status),
            created_at=_LIBRARY_EPOCH,
            updated_at=_LIBRARY_EPOCH,
            display_name_ar=entry.display_name_ar,
        )
        if logical_key == "PRICE_TEMPLATE":
            v2 = version_key(logical_key, "v2")
            out[v2] = TemplateLibraryVersion(
                template_key=v2,
                logical_key=logical_key,
                template_version="v2",
                reason_tag=entry.reason_tag,
                default_content=entry.default_content + "\n(نسخة محسّنة — مسودة)",
                enabled=False,
                active_version=False,
                fallback_template_key=vk,
                approval_state=APPROVAL_DRAFT,
                created_at=_LIBRARY_EPOCH,
                updated_at=_LIBRARY_EPOCH,
                display_name_ar=entry.display_name_ar,
            )
    return out


TEMPLATE_LIBRARY: dict[str, TemplateLibraryVersion] = _build_library_from_registry()

ACTIVE_VERSION_BY_LOGICAL_KEY: dict[str, str] = {
    entry.logical_key: entry.template_key
    for entry in TEMPLATE_LIBRARY.values()
    if entry.active_version
}

FALLBACK_CHAINS: dict[str, tuple[str, ...]] = {
    logical: (
        ACTIVE_VERSION_BY_LOGICAL_KEY.get(logical, version_key(logical, "v1")),
        *(
            (fallback,)
            if (fallback := _fallback_for_logical(logical))
            else ()
        ),
    )
    for logical in TEMPLATE_REGISTRY
}


def get_library_version(template_key: str) -> Optional[TemplateLibraryVersion]:
    return TEMPLATE_LIBRARY.get((template_key or "").strip().upper())


def list_library_versions(
    *,
    logical_key: Optional[str] = None,
) -> list[TemplateLibraryVersion]:
    lk_filter = (logical_key or "").strip().upper()
    rows = list(TEMPLATE_LIBRARY.values())
    if lk_filter:
        rows = [r for r in rows if r.logical_key == lk_filter]
    return sorted(rows, key=lambda r: (r.logical_key, r.template_version))


def resolve_active_version_key(logical_key: str) -> str:
    lk = (logical_key or "").strip().upper()
    return ACTIVE_VERSION_BY_LOGICAL_KEY.get(lk, version_key(lk, "v1"))


def resolve_merchant_visible_template(logical_key: str) -> dict[str, Any]:
    """Merchant sees active version only — not internal version complexity."""
    active_key = resolve_active_version_key(logical_key)
    ver = get_library_version(active_key)
    entry = get_registry_entry(logical_key)
    return {
        "logical_key": logical_key,
        "active_template_key": active_key,
        "display_name_ar": ver.display_name_ar if ver else (entry.display_name_ar if entry else logical_key),
        "default_content": ver.default_content if ver else (entry.default_content if entry else ""),
        "approval_state": ver.approval_state if ver else APPROVAL_DRAFT,
        "approval_state_ar": approval_state_label_ar(
            ver.approval_state if ver else APPROVAL_DRAFT
        ),
    }


def can_transition_approval_state(from_state: str, to_state: str) -> bool:
    src = normalize_approval_state(from_state)
    dst = normalize_approval_state(to_state)
    if src == dst:
        return True
    return dst in VALID_APPROVAL_TRANSITIONS.get(src, frozenset())


def transition_approval_state(
    template_key: str,
    to_state: str,
    *,
    from_state: Optional[str] = None,
) -> dict[str, Any]:
    """Validate state transition — read-only; does not mutate library."""
    ver = get_library_version(template_key)
    if ver is None:
        return {"ok": False, "error": "unknown_template_key"}
    src = normalize_approval_state(from_state or ver.approval_state)
    dst = normalize_approval_state(to_state)
    if not can_transition_approval_state(src, dst):
        return {
            "ok": False,
            "error": "invalid_transition",
            "from_state": src,
            "to_state": dst,
        }
    return {
        "ok": True,
        "template_key": ver.template_key,
        "from_state": src,
        "to_state": dst,
        "from_state_ar": approval_state_label_ar(src),
        "to_state_ar": approval_state_label_ar(dst),
    }


def resolve_fallback_chain(logical_key: str) -> list[str]:
    lk = (logical_key or "").strip().upper()
    chain = FALLBACK_CHAINS.get(lk)
    if chain:
        return list(chain)
    active = resolve_active_version_key(lk)
    fb = _fallback_for_logical(lk)
    return [active] + ([fb] if fb else [])


def _version_is_sendable(
    ver: TemplateLibraryVersion,
    *,
    prefer_approved_only: bool = False,
) -> bool:
    if not ver.enabled:
        return False
    if ver.approval_state in (APPROVAL_REJECTED, APPROVAL_DISABLED):
        return False
    usable = {APPROVAL_APPROVED, APPROVAL_DRAFT}
    if prefer_approved_only:
        usable = {APPROVAL_APPROVED}
    return ver.approval_state in usable


def resolve_sendable_template_key(
    logical_key: str,
    *,
    prefer_approved_only: bool = False,
) -> Optional[str]:
    """
    Walk fallback chain; skip rejected/disabled/unavailable versions.
    Architecture only — runtime send unchanged.
    """
    for key in resolve_fallback_chain(logical_key):
        ver = get_library_version(key)
        if ver is None:
            reg = get_registry_entry(key.replace("_V1", "").replace("_V2", ""))
            if reg and reg.enabled:
                return key
            continue
        if _version_is_sendable(ver, prefer_approved_only=prefer_approved_only):
            return ver.template_key
    return None


def template_library_summary_for_api() -> dict[str, Any]:
    return {
        "library_version": "v1",
        "architecture_only": True,
        "approval_states": sorted(CANONICAL_APPROVAL_STATES),
        "active_versions": dict(ACTIVE_VERSION_BY_LOGICAL_KEY),
        "fallback_chains": {k: list(v) for k, v in FALLBACK_CHAINS.items()},
        "version_count": len(TEMPLATE_LIBRARY),
        "logical_template_count": len(TEMPLATE_REGISTRY),
    }
