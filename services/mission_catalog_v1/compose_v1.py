# -*- coding: utf-8 -*-
"""Mission Catalog V1 — compose Home/Workspace read model (no UI redesign)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.commercial_mission_v1.contract_v1 import get_mission_profile
from services.mission_catalog_v1.contract_v1 import (
    LAYER_SCHEMA,
    LAYER_VERSION,
    MAX_SECONDARIES,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
)
from services.mission_catalog_v1.inventory_v1 import catalog_inventory_v1
from services.mission_catalog_v1.rank_v1 import (
    explain_primary_selection_v1,
    rank_mission_catalog_v1,
)


def _cdc_phase(opp: Mapping[str, Any] | None) -> Optional[str]:
    if not isinstance(opp, Mapping):
        return None
    c = opp.get("commitment") if isinstance(opp.get("commitment"), Mapping) else None
    if not c:
        return None
    return str(c.get("phase") or "") or None


def _public_mission_card(
    opp: Mapping[str, Any],
    *,
    role: str,
) -> dict[str, Any]:
    fam = str(opp.get("family") or "")
    profile = get_mission_profile(fam)
    phase = _cdc_phase(opp)
    return {
        "role": role,
        "opportunity_id": opp.get("opportunity_id"),
        "family": fam,
        "truth_class": opp.get("truth_class"),
        "title_ar": opp.get("title_ar"),
        "why_ar": opp.get("why_ar"),
        "action_ar": opp.get("action_ar"),
        "measure_ar": opp.get("measure_ar"),
        "recheck_ar": opp.get("recheck_ar"),
        "workspace_href": opp.get("workspace_href") or "#workspace",
        "cdc_phase": phase,
        "mission_ready": profile is not None,
        "metric_key": profile.metric_key if profile else None,
        "execution_authority": profile.execution_authority if profile else None,
        "commitment": dict(opp["commitment"])
        if isinstance(opp.get("commitment"), Mapping)
        else None,
    }


def empty_catalog_package_v1(*, reason: str = "empty") -> dict[str, Any]:
    return {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "schema": LAYER_SCHEMA,
        "empty": True,
        "empty_reason": reason,
        "question_ar": "ما أهم فرصة تجارية الآن، ولماذا هي أهم من البقية؟",
        "primary": None,
        "secondaries": [],
        "suppressed_count": 0,
        "suppressed": [],
        "explain": {
            "why_this_one_now_ar": "لا توجد مهمة تجارية جاهزة من أدلة متجرك الآن.",
            "why_not_others_ar": "",
            "reasons": {
                "evidence": "none",
                "lifecycle": "none",
                "commercial": "insufficient_catalog",
                "conflict": None,
            },
        },
        "home": {"primary": None, "secondaries": [], "suppressed_count": 0},
        "workspace": {
            "active_mission": None,
            "cdc_phase": None,
            "action_ar": None,
            "measure_ar": None,
            "recheck_ar": None,
        },
        "inventory_ref": "catalog_inventory_v1",
        "max_secondaries": MAX_SECONDARIES,
        "query_delta": 0,
    }


def compose_mission_catalog_v1(
    *,
    col_package: Mapping[str, Any] | None,
    commitments_by_key: Mapping[str, Mapping[str, Any]] | None = None,
    store_slug: str = "",
) -> dict[str, Any]:
    """
    In-memory ranking over already-loaded COL + CDC attach maps.

    query_delta: 0 (no new DB reads).
    """
    ranked = rank_mission_catalog_v1(
        col_package,
        commitments_by_key=commitments_by_key,
        store_slug=store_slug,
    )
    primary = ranked.get("primary")
    secondaries = list(ranked.get("secondaries") or [])
    suppressed = list(ranked.get("suppressed") or [])
    explain = explain_primary_selection_v1(
        primary=primary if isinstance(primary, Mapping) else None,
        secondaries=secondaries,
        suppressed=suppressed,
        ordered_debug=ranked.get("_ordered_debug"),
    )

    primary_card = (
        _public_mission_card(primary, role=ROLE_PRIMARY)
        if isinstance(primary, Mapping)
        else None
    )
    secondary_cards = [
        _public_mission_card(s, role=ROLE_SECONDARY)
        for s in secondaries
        if isinstance(s, Mapping)
    ]
    is_empty = primary_card is None

    return {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "schema": LAYER_SCHEMA,
        "empty": is_empty,
        "store_slug": store_slug,
        "question_ar": "ما أهم فرصة تجارية الآن، ولماذا هي أهم من البقية؟",
        "primary": primary_card,
        "secondaries": secondary_cards,
        "suppressed_count": int(ranked.get("suppressed_count") or len(suppressed)),
        "suppressed": suppressed,
        "explain": explain,
        "home": {
            "primary": primary_card,
            "secondaries": secondary_cards,
            "suppressed_count": int(ranked.get("suppressed_count") or len(suppressed)),
        },
        "workspace": {
            "active_mission": primary_card,
            "cdc_phase": primary_card.get("cdc_phase") if primary_card else None,
            "action_ar": primary_card.get("action_ar") if primary_card else None,
            "measure_ar": primary_card.get("measure_ar") if primary_card else None,
            "recheck_ar": primary_card.get("recheck_ar") if primary_card else None,
        },
        "max_secondaries": MAX_SECONDARIES,
        "query_delta": 0,
        "inventory_families": [e["family"] for e in catalog_inventory_v1()],
    }


__all__ = [
    "compose_mission_catalog_v1",
    "empty_catalog_package_v1",
]
