# -*- coding: utf-8 -*-
"""
Identity Authority observability — ops/diagnostics only (INV-002 WP-1).

No merchant-facing behaviour. Counters are process-local for tests/foundation.
"""
from __future__ import annotations

from threading import Lock
from typing import Any, Optional

from services.identity_authority.contracts import AUTHORITY_SOURCE_ID
from services.identity_authority.mqic import MerchantQueryIdentityContext

_lock = Lock()
_counters: dict[str, int] = {
    "resolve_ok": 0,
    "resolve_fail": 0,
    "dual_resolve_violation": 0,
    "immutability_violation": 0,
    "ownership_violation": 0,
    "bind_ok": 0,
    "clear_ok": 0,
}


def record(event: str, *, n: int = 1) -> None:
    key = (event or "").strip()
    if not key:
        return
    with _lock:
        _counters[key] = int(_counters.get(key, 0)) + int(n)


def snapshot_counters() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def reset_counters() -> None:
    with _lock:
        for k in list(_counters.keys()):
            _counters[k] = 0


def resolution_provenance(mqic: MerchantQueryIdentityContext) -> dict[str, Any]:
    """Resolution provenance for diagnostics (not merchant chrome)."""
    mqic.assert_authority_owned()
    return {
        "authority_source": AUTHORITY_SOURCE_ID,
        "resolution_path": mqic.resolution_path.value,
        "identity_confidence": mqic.identity_confidence.value,
        "correlation_id": mqic.correlation_id or None,
        "identity_provenance": dict(mqic.identity_provenance),
    }


def identity_context_metadata(
    mqic: Optional[MerchantQueryIdentityContext],
) -> dict[str, Any]:
    """Identity context metadata for Admin/ops."""
    if mqic is None:
        return {
            "bound": False,
            "authority_source": AUTHORITY_SOURCE_ID,
        }
    snap = mqic.internal_snapshot()
    return {
        "bound": True,
        "authority_source": AUTHORITY_SOURCE_ID,
        "merchant_id": snap["merchant_id"],
        "canonical_store_id": snap["canonical_store_id"],
        "store_slug": snap["store_slug"],
        "resolution_path": snap["resolution_path"],
        "identity_confidence": snap["identity_confidence"],
        "correlation_id": snap["correlation_id"],
        "simulation_run_id": snap["simulation_run_id"],
        "replay_id": snap["replay_id"],
        "provider_binding_count": len(snap["provider_bindings"]),
    }


def violation_detection_snapshot() -> dict[str, Any]:
    """Violation counters for Investigation Health / ops."""
    c = snapshot_counters()
    return {
        "authority_source": AUTHORITY_SOURCE_ID,
        "dual_resolve_violation": c.get("dual_resolve_violation", 0),
        "immutability_violation": c.get("immutability_violation", 0),
        "ownership_violation": c.get("ownership_violation", 0),
        "resolve_fail": c.get("resolve_fail", 0),
        "resolve_ok": c.get("resolve_ok", 0),
    }
