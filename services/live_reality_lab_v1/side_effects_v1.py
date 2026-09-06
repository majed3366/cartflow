# -*- coding: utf-8 -*-
"""Live Reality Lab — external side-effect block (default ON)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.live_reality_lab_v1.contract_v1 import (
    LAB_INTEGRATION_SOURCE,
    LAB_STORE_SLUG,
)
from services.live_reality_lab_v1.gate_v1 import (
    is_live_reality_lab_tenant,
    normalize_store_slug,
)


def lab_blocks_external_side_effects(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> bool:
    if is_live_reality_lab_tenant(
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
    ):
        return True
    slug = normalize_store_slug(store_slug)
    if slug == LAB_STORE_SLUG:
        return True
    src = str(integration_source or "").strip().lower()
    if store is not None:
        raw = (
            store.get("integration_source")
            if isinstance(store, Mapping)
            else getattr(store, "integration_source", None)
        )
        if raw is not None:
            src = str(raw or "").strip().lower()
    if src == LAB_INTEGRATION_SOURCE.lower():
        return True
    return False


def lab_side_effect_block_reason(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> Optional[str]:
    if lab_blocks_external_side_effects(
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
    ):
        return "live_reality_lab_side_effects_blocked"
    return None


__all__ = [
    "lab_blocks_external_side_effects",
    "lab_side_effect_block_reason",
]
