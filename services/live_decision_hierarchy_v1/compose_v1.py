# -*- coding: utf-8 -*-
"""
Live Decision Hierarchy V1 — presentation over existing catalog / CDC / portfolio.

Does not rank missions. Does not change COL / OGL / catalog / CDC / portfolio logic.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    MISSION_SHIPPING_AR,
    contract_for_family_v1,
)
from services.live_decision_hierarchy_v1.contract_v1 import (
    COMMERCIAL_STATUS_OWNER,
    CTA_OPEN_DECISION_AR,
    FAMILY_NOUN_AR,
    FORBIDDEN_INSUFFICIENCY_AR,
    JOURNEY_ACCEPT_AR,
    JOURNEY_CONFIRM_AR,
    JOURNEY_EXECUTE_AR,
    JOURNEY_MEASURE_AR,
    JOURNEY_RECHECK_AR,
    LABEL_DECISION_AR,
    LABEL_DONT_AR,
    LABEL_EXECUTION_AR,
    LABEL_HOME_QUESTION_AR,
    LABEL_LATER_AR,
    LABEL_MONITORING_AR,
    LABEL_NEXT_AR,
    LABEL_NOW_AR,
    LABEL_RECHECK_AR,
    LABEL_WHY_NOW_AR,
    LAYER_SCHEMA,
    LAYER_VERSION,
    OPERATIONAL_GUIDANCE_OWNER,
    PORTFOLIO_STATE_CURRENT,
    PORTFOLIO_STATE_DEFERRED,
    PORTFOLIO_STATE_NEXT_MISSION,
    PORTFOLIO_STATE_SAFE_SECONDARY,
    SIDEBAR_ACTION_CHOSEN_AR,
    SIDEBAR_LATER_AR,
    SIDEBAR_MEASURING_AR,
    SIDEBAR_NOW_AR,
    SIDEBAR_REVIEW_AR,
    SUBSTATE_AWAITING_EXEC_AR,
)
from services.live_decision_hierarchy_v1.gate_v1 import gate_payload


def _as_map(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _phase(card: Mapping[str, Any] | None) -> str:
    if not isinstance(card, Mapping):
        return ""
    raw = card.get("cdc_phase")
    if raw:
        return str(raw).strip()
    c = card.get("commitment")
    if isinstance(c, Mapping) and c.get("phase"):
        return str(c.get("phase") or "").strip()
    return ""


def _family(card: Mapping[str, Any] | None) -> str:
    if not isinstance(card, Mapping):
        return ""
    return str(card.get("family") or "").strip()


def _week_counts(summary: Mapping[str, Any]) -> dict[str, int]:
    raw = summary.get("merchant_reason_counts_week")
    src = raw if isinstance(raw, Mapping) else {}
    out: dict[str, int] = {}
    total = 0
    for key in src:
        try:
            n = int(src.get(key) or 0)
        except (TypeError, ValueError):
            n = 0
        if n < 0:
            n = 0
        out[str(key)] = n
        total += n
    out["total"] = total
    return out


def _share_pct(n: int, total: int) -> Optional[int]:
    if total <= 0:
        return None
    return int(round(100.0 * float(n) / float(total)))


def _reason_key_for_family(family: str) -> str:
    if family == "shipping_friction":
        return "shipping"
    if family == "price_hesitation":
        return "price"
    if family in {"product_confidence", "product_opportunity_focus"}:
        return "quality"
    return ""


def _cal_evidence(family: str, counts: Mapping[str, int]) -> dict[str, Any] | None:
    key = _reason_key_for_family(family)
    if not key:
        return None
    n = int(counts.get(key) or 0)
    total = int(counts.get("total") or 0)
    if n <= 0 or total <= 0:
        return None
    return {
        "counts": {
            "top_reason": key,
            "top_count": n,
            "hesitation_total": total,
            "top_share": float(n) / float(total),
        }
    }


def _monitor_body_ar(family: str, counts: Mapping[str, int]) -> str:
    noun = FAMILY_NOUN_AR.get(family) or "هذا السبب"
    key = _reason_key_for_family(family)
    n = int(counts.get(key) or 0) if key else 0
    total = int(counts.get("total") or 0)
    pct = _share_pct(n, total)
    if n and total and pct is not None:
        return f"{noun} يتكرر في {n} من {total} سبباً مسجلاً ({pct}٪)."
    return ""


def _evidence_line_ar(family: str, counts: Mapping[str, int]) -> str:
    """Numerator / denominator in RTL-safe Arabic: 12 من 20 (60٪)."""
    key = _reason_key_for_family(family)
    n = int(counts.get(key) or 0) if key else 0
    total = int(counts.get("total") or 0)
    pct = _share_pct(n, total)
    if n and total and pct is not None:
        return f"{n} من {total} ({pct}٪)"
    return ""


def _why_now_from_evidence(family: str, counts: Mapping[str, int]) -> str:
    """WHY this mission — evidence share, not a title repeat. Association only."""
    noun = FAMILY_NOUN_AR.get(family) or ""
    key = _reason_key_for_family(family)
    n = int(counts.get(key) or 0) if key else 0
    total = int(counts.get("total") or 0)
    if not noun or n <= 0 or total <= 0:
        return ""
    return (
        f"لأن {noun} يمثل {n} من {total} سبب تردد مسجّل "
        f"خلال نافذة المراقبة الحالية."
    )


def _journey_package(phase: str) -> dict[str, Any]:
    steps = [
        {"id": "accept", "label_ar": JOURNEY_ACCEPT_AR},
        {"id": "execute", "label_ar": JOURNEY_EXECUTE_AR},
        {"id": "confirm", "label_ar": JOURNEY_CONFIRM_AR},
        {"id": "measure", "label_ar": JOURNEY_MEASURE_AR},
        {"id": "recheck", "label_ar": JOURNEY_RECHECK_AR},
    ]
    current = "accept"
    if phase == "ACTION_CHOSEN":
        current = "execute"
    elif phase == "UNDER_MEASUREMENT":
        current = "measure"
    elif phase == "RECHECK_DUE":
        current = "recheck"
    return {"steps": steps, "current_step": current, "frontend_lifecycle_derivation": 0}


def _commercial_state_label(phase: str) -> str:
    if phase == "ACTION_CHOSEN":
        return ACCEPTED_STATE_AR
    if phase == "UNDER_MEASUREMENT":
        return "تحت القياس"
    if phase == "RECHECK_DUE":
        return "حان وقت المراجعة"
    return "جاهزة للتنفيذ"


def _has_closed_truth(summary: Mapping[str, Any], catalog: Mapping[str, Any]) -> bool:
    cdc = _as_map(summary.get("commercial_decision_commitment_v1"))
    by_key = cdc.get("by_opportunity_key")
    if isinstance(by_key, Mapping):
        for row in by_key.values():
            if isinstance(row, Mapping) and row.get("closed_at"):
                return True
            if isinstance(row, Mapping) and str(row.get("phase") or "") == "CLOSED":
                return True
    cards = [catalog.get("primary")]
    cards.extend(list(catalog.get("secondaries") or []))
    for card in cards:
        if not isinstance(card, Mapping):
            continue
        c = card.get("commitment")
        if isinstance(c, Mapping) and (c.get("closed_at") or str(c.get("phase") or "") == "CLOSED"):
            return True
    return False


def compose_live_decision_hierarchy_v1(
    summary: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    store: Any = None,
) -> Optional[dict[str, Any]]:
    """Return a presentation package or None (omit for normal merchants)."""
    src = summary if isinstance(summary, Mapping) else {}
    slug = str(store_slug or src.get("store_slug") or "").strip()[:191]
    gate = gate_payload(store_slug=slug, store=store)
    if not gate["enabled"]:
        return None

    catalog = _as_map(src.get("mission_catalog_v1"))
    portfolio = _as_map(src.get("mission_portfolio_v1"))
    primary = catalog.get("primary") if isinstance(catalog.get("primary"), Mapping) else None
    counts = _week_counts(src)
    now_family = _family(primary) if primary and primary.get("mission_ready") else ""
    now_phase = _phase(primary) if primary else ""

    next_raw = (
        portfolio.get("next_mission")
        if isinstance(portfolio.get("next_mission"), Mapping)
        else None
    )
    next_family = _family(next_raw)
    # Portfolio places READY catalog primary in next_mission when no slot owner.
    # That is CURRENT attention, not "المهمة التجارية التالية".
    distinct_next = bool(next_raw and next_family and next_family != now_family)

    cal_now = (
        contract_for_family_v1(
            now_family,
            evidence=_cal_evidence(now_family, counts),
            reason_label_ar=FAMILY_NOUN_AR.get(now_family, ""),
        )
        if now_family
        else None
    )
    title_ar = ""
    decision_ar = ""
    dont_ar = ""
    why_ar = ""
    execution_ar = ""
    measure_ar = ""
    recheck_ar = ""
    if isinstance(primary, Mapping):
        title_ar = str(primary.get("title_ar") or "").strip()
        decision_ar = str(primary.get("mission_ar") or primary.get("action_ar") or "").strip()
        dont_ar = str(primary.get("dont_ar") or "").strip()
        why_ar = str(primary.get("why_ar") or "").strip()
        execution_ar = str(primary.get("action_ar") or "").strip()
        measure_ar = str(primary.get("measure_ar") or "").strip()
        recheck_ar = str(primary.get("recheck_ar") or "").strip()
        expl = catalog.get("explain")
        if isinstance(expl, Mapping) and expl.get("why_this_one_now_ar"):
            why_ar = str(expl.get("why_this_one_now_ar") or why_ar).strip()
    if cal_now:
        title_ar = cal_now.get("situation_ar") or title_ar
        decision_ar = cal_now.get("mission_ar") or decision_ar
        dont_ar = cal_now.get("dont_ar") or dont_ar
        execution_ar = cal_now.get("action_ar") or execution_ar
        measure_ar = cal_now.get("measure_ar") or measure_ar
        recheck_ar = cal_now.get("recheck_ar") or recheck_ar
    why_from_evidence = _why_now_from_evidence(now_family, counts)
    if why_from_evidence:
        why_ar = why_from_evidence
    elif why_ar == title_ar:
        why_ar = ""
    if now_family == "shipping_friction" and not decision_ar:
        decision_ar = MISSION_SHIPPING_AR

    home_now = None
    if now_family:
        home_now = {
            "family": now_family,
            "portfolio_state": PORTFOLIO_STATE_CURRENT,
            "group_label_ar": LABEL_NOW_AR,
            "state_label_ar": LABEL_NOW_AR,
            "commercial_state_ar": _commercial_state_label(now_phase),
            "cdc_phase": now_phase or None,
            "title_ar": title_ar,
            "evidence_ar": _evidence_line_ar(now_family, counts),
            "decision_ar": decision_ar,
            "cta_ar": CTA_OPEN_DECISION_AR,
            "href": "#workspace",
            "opportunity_id": primary.get("opportunity_id") if isinstance(primary, Mapping) else None,
            "mission_ready": True,
        }

    monitoring: list[dict[str, Any]] = []
    for row in list(portfolio.get("safe_secondaries") or []):
        if not isinstance(row, Mapping):
            continue
        fam = _family(row)
        if not fam or fam == now_family:
            continue
        body = _monitor_body_ar(fam, counts)
        if not body:
            continue
        monitoring.append(
            {
                "family": fam,
                "portfolio_state": PORTFOLIO_STATE_SAFE_SECONDARY,
                "group_label_ar": LABEL_MONITORING_AR,
                "body_ar": body,
                "title_ar": str(row.get("title_ar") or "").strip(),
                "executable": False,
                "consumes_active_capacity": False,
                "cta_ar": None,
            }
        )

    home_next = None
    if distinct_next:
        home_next = {
            "family": next_family,
            "portfolio_state": PORTFOLIO_STATE_NEXT_MISSION,
            "group_label_ar": LABEL_NEXT_AR,
            "title_ar": str(next_raw.get("title_ar") or "").strip() if next_raw else "",
            "executable": False,
        }

    later: list[dict[str, Any]] = []
    for row in list(portfolio.get("deferred") or []):
        if not isinstance(row, Mapping):
            continue
        fam = _family(row)
        if not fam or fam == now_family:
            continue
        later.append(
            {
                "family": fam,
                "portfolio_state": PORTFOLIO_STATE_DEFERRED,
                "group_label_ar": LABEL_LATER_AR,
                "title_ar": str(row.get("title_ar") or "").strip(),
                "executable": False,
            }
        )

    # Sidebar organizes existing truth — does not rank.
    sidebar_items: list[dict[str, Any]] = []
    if now_family and now_phase == "ACTION_CHOSEN":
        sidebar_items.append(
            {
                "id": "in_progress",
                "label": SIDEBAR_ACTION_CHOSEN_AR,
                "count": 1,
                "family": now_family,
                "substate": SUBSTATE_AWAITING_EXEC_AR,
                "parent_label": "قيد التنفيذ / القياس",
            }
        )
    elif now_family and now_phase == "UNDER_MEASUREMENT":
        sidebar_items.append(
            {
                "id": "measuring",
                "label": SIDEBAR_MEASURING_AR,
                "count": 1,
                "family": now_family,
                "substate": None,
                "parent_label": "قيد التنفيذ / القياس",
            }
        )
    elif now_family and now_phase == "RECHECK_DUE":
        sidebar_items.append(
            {
                "id": "review",
                "label": SIDEBAR_REVIEW_AR,
                "count": 1,
                "family": now_family,
                "substate": None,
            }
        )
    elif now_family and now_phase != "CLOSED":
        sidebar_items.append(
            {
                "id": "now",
                "label": SIDEBAR_NOW_AR,
                "count": 1,
                "family": now_family,
                "substate": None,
            }
        )
    if later:
        sidebar_items.append(
            {
                "id": "later",
                "label": SIDEBAR_LATER_AR,
                "count": len(later),
                "family": later[0]["family"] if later else None,
                "substate": None,
            }
        )

    closed_supported = _has_closed_truth(src, catalog)
    mission_ready = bool(isinstance(primary, Mapping) and primary.get("mission_ready"))

    return {
        "ok": True,
        "enabled": True,
        "layer_version": LAYER_VERSION,
        "schema": LAYER_SCHEMA,
        "store_slug": slug,
        "gate": gate["gate"],
        "query_delta": 0,
        "n_plus_one": 0,
        "query_param_bypass": False,
        "frontend_ranking": 0,
        "frontend_lifecycle_derivation": 0,
        "commercial_status_owner": COMMERCIAL_STATUS_OWNER,
        "operational_guidance_owner": OPERATIONAL_GUIDANCE_OWNER,
        "suppress_same_mission_ogl_insufficiency": bool(mission_ready),
        "forbidden_insufficiency_ar": list(FORBIDDEN_INSUFFICIENCY_AR),
        "closed_history_supported": closed_supported,
        "home": {
            "question_ar": LABEL_HOME_QUESTION_AR,
            "now": home_now,
            "monitoring": monitoring,
            "next_mission": home_next,
            "later": later,
        },
        "workspace": {
            "title_ar": title_ar,
            "why_now_label_ar": LABEL_WHY_NOW_AR,
            "why_now_ar": why_ar,
            "evidence_label_ar": "الدليل",
            "evidence_ar": _evidence_line_ar(now_family, counts),
            "journey": _journey_package(now_phase),
            "decision_label_ar": LABEL_DECISION_AR,
            "decision_ar": decision_ar,
            "dont_label_ar": LABEL_DONT_AR,
            "dont_ar": dont_ar,
            "execution_label_ar": LABEL_EXECUTION_AR,
            "execution_ar": execution_ar,
            "measure_label_ar": LABEL_MONITORING_AR,
            "measure_ar": measure_ar,
            "recheck_label_ar": LABEL_RECHECK_AR,
            "recheck_ar": recheck_ar,
            "monitoring": monitoring,
            "next_mission": home_next,
            "later": later,
            "flow": [
                "EVIDENCE",
                "DECISION",
                "EXECUTION",
                "MEASUREMENT",
                "RECHECK",
            ],
        },
        "sidebar": {
            "title_ar": "مساحة القرار",
            "items": sidebar_items,
            "completed_supported": closed_supported,
        },
        "truth": {
            "primary_family": now_family or None,
            "cdc_phase": now_phase or None,
            "counts": {
                "shipping": int(counts.get("shipping") or 0),
                "price": int(counts.get("price") or 0),
                "thinking": int(counts.get("thinking") or 0),
                "total": int(counts.get("total") or 0),
            },
        },
    }


__all__ = ["compose_live_decision_hierarchy_v1"]
