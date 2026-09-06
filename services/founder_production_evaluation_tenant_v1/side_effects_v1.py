# -*- coding: utf-8 -*-
"""
Founder evaluation tenant — external side-effect policy.

Default: block WhatsApp / Meta / customer communications / billing-facing
integrations for evaluation identities. Internal COL/CDC/missions allowed.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.founder_production_evaluation_tenant_v1.contract_v1 import (
    FIXTURE_EVAL_INTEGRATION_SOURCE,
    FOUNDER_EVAL_INTEGRATION_SOURCE,
    FOUNDER_EVAL_STORE_SLUG,
)
from services.founder_production_evaluation_tenant_v1.gate_v1 import (
    is_fixture_evaluation_slug,
    is_founder_evaluation_tenant,
    normalize_store_slug,
)


def evaluation_tenant_blocks_external_side_effects(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> bool:
    """
    True → callers must not enqueue/send WhatsApp, Meta ads, billing, etc.

    Covers production founder tenant and local cf_fe_v1_* fixtures.
    """
    if is_founder_evaluation_tenant(
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
    ):
        return True
    if is_fixture_evaluation_slug(store_slug):
        return True
    slug = normalize_store_slug(store_slug)
    if store is not None:
        src = getattr(store, "integration_source", None)
        if src is None and isinstance(store, Mapping):
            src = store.get("integration_source")
        src_s = str(src or integration_source or "").strip().lower()
    else:
        src_s = str(integration_source or "").strip().lower()
    if src_s in {
        FOUNDER_EVAL_INTEGRATION_SOURCE.lower(),
        FIXTURE_EVAL_INTEGRATION_SOURCE.lower(),
    }:
        return True
    if slug == FOUNDER_EVAL_STORE_SLUG:
        return True
    return False


def evaluation_side_effect_block_reason(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> Optional[str]:
    if evaluation_tenant_blocks_external_side_effects(
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
    ):
        return "founder_evaluation_tenant_side_effects_blocked"
    return None


__all__ = [
    "evaluation_side_effect_block_reason",
    "evaluation_tenant_blocks_external_side_effects",
]
