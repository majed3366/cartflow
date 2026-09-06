# -*- coding: utf-8 -*-
"""
Mission Catalog V1 — deterministic CDC-aware ranking.

No LLM. Prefer continuity of open commitments over fresh weaker opportunities.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
)
from services.commercial_opportunity_layer_v1.priority_v1 import (
    priority_explanation_ar,
    score_opportunity_v1,
)
from services.mission_catalog_v1.contract_v1 import (
    BOOST_ACTION_CHOSEN,
    BOOST_OPEN_COMMITMENT,
    BOOST_RECHECK_DUE,
    BOOST_UNDER_MEASUREMENT,
    CONFLICT_GROUPS,
    MAX_SECONDARIES,
    ROLE_SUPPRESSED,
    SUPPRESS_CONFLICT_GROUP,
    SUPPRESS_DUPLICATE_FAMILY,
    SUPPRESS_FAMILY_CONFIG_MISSING,
    SUPPRESS_INSUFFICIENT,
    SUPPRESS_OVERFLOW_SECONDARY,
    SUPPRESS_STALE_OR_MISSING,
    SUPPRESS_WEAKER_THAN_PRIMARY,
)
from services.mission_catalog_v1.inventory_v1 import (
    inventory_by_family,
    mission_ready_families,
)


def _cdc_phase(opp: Mapping[str, Any]) -> Optional[str]:
    c = opp.get("commitment") if isinstance(opp.get("commitment"), Mapping) else None
    if not c:
        return None
    return str(c.get("phase") or "") or None


def _lifecycle_boost(phase: Optional[str]) -> tuple[int, Optional[str]]:
    if phase == PHASE_RECHECK_DUE:
        return BOOST_RECHECK_DUE, "lifecycle_recheck_due"
    if phase == PHASE_UNDER_MEASUREMENT:
        return BOOST_UNDER_MEASUREMENT, "lifecycle_under_measurement"
    if phase == PHASE_ACTION_CHOSEN:
        return BOOST_ACTION_CHOSEN, "lifecycle_action_chosen"
    if phase:
        return BOOST_OPEN_COMMITMENT, "lifecycle_open_commitment"
    return 0, None


def catalog_score_v1(opp: Mapping[str, Any]) -> int:
    """Explainable integer score = COL commercial score + CDC continuity boost."""
    base = score_opportunity_v1(opp)
    boost, _ = _lifecycle_boost(_cdc_phase(opp))
    return int(base) + int(boost)


def _conflict_group_for(family: str) -> Optional[str]:
    for name, members in CONFLICT_GROUPS.items():
        if family in members:
            return name
    return None


def _is_surfaceable(opp: Mapping[str, Any]) -> bool:
    tc = str(opp.get("truth_class") or "")
    if tc in (TRUTH_PRODUCTION_READY, TRUTH_PRODUCTION_PARTIAL):
        return True
    return bool(_cdc_phase(opp))


def _collect_candidates(
    col_package: Mapping[str, Any],
    *,
    commitments_by_key: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(raw: Mapping[str, Any] | None) -> None:
        if not isinstance(raw, Mapping):
            return
        oid = str(raw.get("opportunity_id") or "")
        if not oid or oid in seen:
            return
        seen.add(oid)
        item = dict(raw)
        if (
            commitments_by_key
            and oid in commitments_by_key
            and not isinstance(item.get("commitment"), Mapping)
        ):
            item["commitment"] = dict(commitments_by_key[oid])
        pool.append(item)

    _add(col_package.get("primary") if isinstance(col_package, Mapping) else None)
    secs = col_package.get("secondaries") if isinstance(col_package, Mapping) else None
    if isinstance(secs, list):
        for s in secs:
            _add(s)

    if commitments_by_key:
        for key, pub in commitments_by_key.items():
            if key in seen or not isinstance(pub, Mapping):
                continue
            fam = str(pub.get("opportunity_family") or "")
            pool.append(
                {
                    "opportunity_id": key,
                    "family": fam,
                    "truth_class": TRUTH_PRODUCTION_PARTIAL,
                    "title_ar": str(pub.get("action_summary") or "")[:120],
                    "why_ar": "مهمة نشطة — الفرصة لم تعد الأولى في طبقة الفرص.",
                    "action_ar": str(pub.get("action_summary") or ""),
                    "commitment": dict(pub),
                    "_urgency": 10,
                    "_evidence_strength": 8,
                    "_catalog_continuity_only": True,
                }
            )
            seen.add(key)
    return pool


def _sort_key(opp: Mapping[str, Any]) -> tuple:
    return (
        -catalog_score_v1(opp),
        0 if str(opp.get("truth_class") or "") == TRUTH_PRODUCTION_READY else 1,
        str(opp.get("family") or ""),
        str(opp.get("opportunity_id") or ""),
    )


def rank_mission_catalog_v1(
    col_package: Mapping[str, Any] | None,
    *,
    commitments_by_key: Mapping[str, Mapping[str, Any]] | None = None,
    store_slug: str = "",
) -> dict[str, Any]:
    """Select PRIMARY (≤1), SECONDARIES (≤2), SUPPRESSED. Deterministic."""
    inv = inventory_by_family()
    ready_fams = mission_ready_families()
    col = col_package if isinstance(col_package, Mapping) else {}
    candidates = _collect_candidates(col, commitments_by_key=commitments_by_key or {})

    suppressed: list[dict[str, Any]] = []
    for s in col.get("suppressed") or []:
        if isinstance(s, Mapping):
            suppressed.append(
                {
                    "family": str(s.get("family") or ""),
                    "opportunity_id": None,
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_INSUFFICIENT
                    if "weak" in str(s.get("reason") or "")
                    or str(s.get("truth_class") or "") == "INSUFFICIENT"
                    else SUPPRESS_STALE_OR_MISSING,
                    "reason": str(s.get("reason") or ""),
                    "debug": dict(s),
                }
            )

    if not candidates:
        return {
            "ok": True,
            "primary": None,
            "secondaries": [],
            "suppressed": suppressed,
            "suppressed_count": len(suppressed),
            "empty": True,
            "store_slug": store_slug,
            "_ordered_debug": [],
        }

    ranked = sorted(candidates, key=_sort_key)

    by_family: dict[str, dict[str, Any]] = {}
    for opp in ranked:
        fam = str(opp.get("family") or "")
        oid = opp.get("opportunity_id")
        if not fam:
            suppressed.append(
                {
                    "family": "",
                    "opportunity_id": oid,
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_FAMILY_CONFIG_MISSING,
                    "reason": "missing_family",
                }
            )
            continue
        if fam not in inv:
            suppressed.append(
                {
                    "family": fam,
                    "opportunity_id": oid,
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_FAMILY_CONFIG_MISSING,
                    "reason": "family_not_in_catalog_inventory",
                }
            )
            continue
        if fam in by_family:
            suppressed.append(
                {
                    "family": fam,
                    "opportunity_id": oid,
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_DUPLICATE_FAMILY,
                    "reason": f"duplicate_of:{by_family[fam].get('opportunity_id')}",
                }
            )
            continue
        by_family[fam] = opp

    ordered = sorted(by_family.values(), key=_sort_key)

    with_cdc = [o for o in ordered if _cdc_phase(o) and _is_surfaceable(o)]
    without = [o for o in ordered if o not in with_cdc and _is_surfaceable(o)]

    primary: Optional[dict[str, Any]] = None
    if with_cdc:
        primary = sorted(with_cdc, key=_sort_key)[0]
    else:
        mission_ready = [
            o for o in without if str(o.get("family") or "") in ready_fams
        ]
        if mission_ready:
            primary = sorted(mission_ready, key=_sort_key)[0]
        elif without:
            primary = without[0]

    secondaries: list[dict[str, Any]] = []
    used_families: set[str] = set()
    used_groups: set[str] = set()
    if primary:
        used_families.add(str(primary.get("family") or ""))
        cg0 = _conflict_group_for(str(primary.get("family") or ""))
        if cg0:
            used_groups.add(cg0)

    for opp in ordered:
        if primary and opp.get("opportunity_id") == primary.get("opportunity_id"):
            continue
        if not _is_surfaceable(opp):
            suppressed.append(
                {
                    "family": str(opp.get("family") or ""),
                    "opportunity_id": opp.get("opportunity_id"),
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_INSUFFICIENT,
                    "reason": f"truth_class:{opp.get('truth_class')}",
                }
            )
            continue
        fam = str(opp.get("family") or "")
        if fam in used_families:
            suppressed.append(
                {
                    "family": fam,
                    "opportunity_id": opp.get("opportunity_id"),
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_DUPLICATE_FAMILY,
                    "reason": "family_already_surfaced",
                }
            )
            continue
        cg = _conflict_group_for(fam)
        if cg and cg in used_groups:
            suppressed.append(
                {
                    "family": fam,
                    "opportunity_id": opp.get("opportunity_id"),
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_CONFLICT_GROUP,
                    "reason": f"conflicts_with_group:{cg}",
                }
            )
            continue
        if len(secondaries) >= MAX_SECONDARIES:
            suppressed.append(
                {
                    "family": fam,
                    "opportunity_id": opp.get("opportunity_id"),
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_OVERFLOW_SECONDARY,
                    "reason": "secondary_cap",
                }
            )
            continue
        secondaries.append(opp)
        used_families.add(fam)
        if cg:
            used_groups.add(cg)

    selected = set()
    if primary:
        selected.add(str(primary.get("opportunity_id") or ""))
    for s in secondaries:
        selected.add(str(s.get("opportunity_id") or ""))
    already = {str(x.get("opportunity_id") or "") for x in suppressed if x.get("opportunity_id")}
    for opp in ordered:
        oid = str(opp.get("opportunity_id") or "")
        if oid and oid not in selected and oid not in already:
            suppressed.append(
                {
                    "family": str(opp.get("family") or ""),
                    "opportunity_id": oid,
                    "role": ROLE_SUPPRESSED,
                    "code": SUPPRESS_WEAKER_THAN_PRIMARY,
                    "reason": "not_selected_for_surface",
                }
            )

    return {
        "ok": True,
        "primary": primary,
        "secondaries": secondaries,
        "suppressed": suppressed,
        "suppressed_count": len(suppressed),
        "empty": primary is None,
        "store_slug": store_slug,
        "_ordered_debug": [
            {
                "opportunity_id": o.get("opportunity_id"),
                "family": o.get("family"),
                "score": catalog_score_v1(o),
                "phase": _cdc_phase(o),
            }
            for o in ordered
        ],
    }


def explain_primary_selection_v1(
    *,
    primary: Mapping[str, Any] | None,
    secondaries: Sequence[Mapping[str, Any]],
    suppressed: Sequence[Mapping[str, Any]],
    ordered_debug: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not primary:
        return {
            "why_this_one_now_ar": "لا توجد مهمة تجارية جاهزة من أدلة متجرك الآن.",
            "why_not_others_ar": "",
            "reasons": {
                "evidence": "none",
                "lifecycle": "none",
                "commercial": "insufficient_catalog",
                "conflict": None,
            },
            "debug": {"ordered": list(ordered_debug or [])},
        }

    fam = str(primary.get("family") or "")
    phase = _cdc_phase(primary)
    _, life_code = _lifecycle_boost(phase)
    evidence_ar = priority_explanation_ar(primary)
    commercial_ar = str(primary.get("priority_why_ar") or evidence_ar)

    if phase == PHASE_RECHECK_DUE:
        why_now = "حان وقت مراجعة مهمة قائمة — نعيد قراءة الأدلة قبل أي فرصة جديدة."
        life_reason = "recheck_due_continuity"
    elif phase == PHASE_UNDER_MEASUREMENT:
        why_now = "المهمة تحت القياس — نُبقي الاستمرارية أوضح من فرصة أضعف جديدة."
        life_reason = "under_measurement_continuity"
    elif phase == PHASE_ACTION_CHOSEN:
        why_now = "قرار معتمد بانتظار إثبات التنفيذ — لا نستبدله بفرصة أضعف."
        life_reason = "action_chosen_continuity"
    else:
        why_now = commercial_ar
        life_reason = "open_competition"

    why_not_parts = [f"«{s.get('family')}» أدنى أولوية تجارية الآن." for s in secondaries]
    conflict_codes = [
        str(x.get("code"))
        for x in suppressed
        if str(x.get("code") or "")
        in (SUPPRESS_CONFLICT_GROUP, SUPPRESS_DUPLICATE_FAMILY)
    ]
    if SUPPRESS_CONFLICT_GROUP in conflict_codes:
        why_not_parts.append("فُرص متعارضة في نفس محور القيمة أُخفيت لتفادي التشويش.")
    if SUPPRESS_DUPLICATE_FAMILY in conflict_codes:
        why_not_parts.append("تكرار نفس العائلة أُزيل.")
    why_not = (
        " ".join(why_not_parts) if why_not_parts else "لا توجد بدائل جاهزة أعلى أولوية."
    )

    return {
        "why_this_one_now_ar": why_now,
        "why_not_others_ar": why_not,
        "reasons": {
            "evidence": evidence_ar,
            "lifecycle": life_reason,
            "lifecycle_code": life_code,
            "commercial": commercial_ar,
            "conflict": conflict_codes[0] if conflict_codes else None,
            "family": fam,
            "phase": phase,
            "score": catalog_score_v1(primary),
        },
        "debug": {"ordered": list(ordered_debug or [])},
    }


__all__ = [
    "catalog_score_v1",
    "explain_primary_selection_v1",
    "rank_mission_catalog_v1",
]
