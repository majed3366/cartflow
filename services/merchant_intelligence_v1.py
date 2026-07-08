# -*- coding: utf-8 -*-
"""
Merchant Intelligence v1 — governed intelligence layer.

Consumes Truth + Knowledge outputs (decisions, buckets, explanation, proof).
Produces groups, recommendations, memory beats, and priorities only.
Never renders UI, never mints truth or decisions, never routes knowledge.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from services.knowledge_routing_v1 import (
    SURFACE_CART_DETAIL,
    SURFACE_DAILY_BRIEF,
    SURFACE_KNOWLEDGE_LAYER,
    SURFACE_MERCHANT_HOME,
)
from services.merchant_cart_row_classifier import (
    PRIMARY_NEEDS_FOLLOWUP,
    PRIMARY_NO_PHONE,
    PRIMARY_RECOVERED,
    PRIMARY_RETURN_TO_SITE,
    PRIMARY_SENT,
)
from services.merchant_decision_layer_v1 import (
    CLASS_CRITICAL_ACTION,
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
    DECISION_FIX_CHANNEL,
    INTERVENTION_DECISION_KEYS,
    LIFECYCLE_PUBLISHED,
)

_MERCHANT_NEEDED_YES = "نعم"

INTELLIGENCE_VERSION = "v1"
AUTHORITY = "merchant_intelligence_v1"

GROUP_WAITING_PHONE = "waiting_phone"
GROUP_WAITING_REPLY = "waiting_reply"
GROUP_RETURNED = "returned"
GROUP_NEEDS_MERCHANT = "needs_merchant"
GROUP_WAITING_PURCHASE = "waiting_purchase"
GROUP_COMPLETED = "completed"
GROUP_VIP = "vip"
GROUP_NO_CONTACT = "no_contact"
GROUP_REPEATED_HESITATION = "repeated_hesitation"
GROUP_PRODUCT_HESITATION = "product_hesitation"
GROUP_RISK_PATTERN = "risk_pattern"

_OPERATIONAL_GROUP_ORDER = (
    GROUP_NEEDS_MERCHANT,
    GROUP_VIP,
    GROUP_NO_CONTACT,
    GROUP_WAITING_PHONE,
    GROUP_RETURNED,
    GROUP_WAITING_PURCHASE,
    GROUP_WAITING_REPLY,
    GROUP_COMPLETED,
)

REC_REQUIRED = "required_action"
REC_SUGGESTED = "suggested_action"
REC_WATCH = "watch_only"
REC_INFORMATIONAL = "informational"
REC_NO_ACTION = "no_action"
REC_BLOCKED = "blocked"
REC_SUPPRESSED = "suppressed"

MEMORY_VS_YESTERDAY = "compared_to_yesterday"
MEMORY_VS_LAST_WEEK = "compared_to_last_week"
MEMORY_REPEATED_PATTERN = "repeated_pattern"
MEMORY_IMPROVED = "improved"
MEMORY_DECLINED = "declined"
MEMORY_RESOLVED = "resolved"

PRIORITY_HIGHEST = "highest"
PRIORITY_TODAY = "today"
PRIORITY_WATCHING = "watching"
PRIORITY_COMPLETED = "completed"

SURFACE_CARTS = "carts"
SURFACE_WEEKLY_BRIEF = "weekly_brief"
SURFACE_NOTIFICATIONS = "notifications"
SURFACE_EXECUTIVE = "executive_view"
SURFACE_FUTURE_AI = "future_ai"

SURFACES_ALL = frozenset(
    {
        SURFACE_MERCHANT_HOME,
        SURFACE_CARTS,
        SURFACE_CART_DETAIL,
        SURFACE_DAILY_BRIEF,
        SURFACE_KNOWLEDGE_LAYER,
        SURFACE_WEEKLY_BRIEF,
        SURFACE_NOTIFICATIONS,
        SURFACE_EXECUTIVE,
        SURFACE_FUTURE_AI,
    }
)

PATTERN_HESITATION_MIN = 3
PATTERN_HESITATION_WINDOW_DAYS = 7
PRODUCT_HESITATION_MIN = 2

_GROUP_REGISTRY: dict[str, dict[str, Any]] = {
    GROUP_WAITING_PHONE: {
        "title_ar": "بانتظار الجوال",
        "meaning_ar": "سلة بانتظار رقم تواصل قبل متابعة الاسترداد",
        "default_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL, SURFACE_MERCHANT_HOME],
    },
    GROUP_WAITING_REPLY: {
        "title_ar": "بانتظار رد العميل",
        "meaning_ar": "تم الإرسال — بانتظار رد العميل",
        "default_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL, SURFACE_MERCHANT_HOME],
    },
    GROUP_RETURNED: {
        "title_ar": "عاد للمتجر",
        "meaning_ar": "عاد العميل للموقع — CartFlow يراقب نافذة الشراء",
        "default_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL, SURFACE_MERCHANT_HOME],
    },
    GROUP_NEEDS_MERCHANT: {
        "title_ar": "يحتاج تدخلك",
        "meaning_ar": "قرار يستدعي انتباهك أو إجراءً منك",
        "default_surfaces": [
            SURFACE_MERCHANT_HOME,
            SURFACE_CARTS,
            SURFACE_CART_DETAIL,
            SURFACE_DAILY_BRIEF,
            SURFACE_NOTIFICATIONS,
        ],
    },
    GROUP_WAITING_PURCHASE: {
        "title_ar": "نافذة الشراء",
        "meaning_ar": "بانتظار إكمال الشراء بعد تفاعل أو عودة",
        "default_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL, SURFACE_MERCHANT_HOME],
    },
    GROUP_COMPLETED: {
        "title_ar": "مكتملة",
        "meaning_ar": "تم الاسترجاع أو إغلاق المسار",
        "default_surfaces": [SURFACE_CARTS, SURFACE_MERCHANT_HOME, SURFACE_DAILY_BRIEF],
    },
    GROUP_VIP: {
        "title_ar": "سلة مهمة — VIP",
        "meaning_ar": "سلة VIP تستحق أولوية",
        "default_surfaces": [
            SURFACE_MERCHANT_HOME,
            SURFACE_CARTS,
            SURFACE_CART_DETAIL,
            SURFACE_NOTIFICATIONS,
        ],
    },
    GROUP_NO_CONTACT: {
        "title_ar": "لا يمكن التواصل",
        "meaning_ar": "لا يوجد رقم — مسار الاسترداد محدود",
        "default_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL],
    },
    GROUP_REPEATED_HESITATION: {
        "title_ar": "تردد متكرر",
        "meaning_ar": "نمط تردد متكرر على نفس السبب",
        "default_surfaces": [
            SURFACE_MERCHANT_HOME,
            SURFACE_CARTS,
            SURFACE_KNOWLEDGE_LAYER,
            SURFACE_WEEKLY_BRIEF,
        ],
    },
    GROUP_PRODUCT_HESITATION: {
        "title_ar": "تردد على منتج",
        "meaning_ar": "نمط تردد على منتج أو عائلة منتجات",
        "default_surfaces": [SURFACE_KNOWLEDGE_LAYER, SURFACE_CARTS, SURFACE_WEEKLY_BRIEF],
    },
    GROUP_RISK_PATTERN: {
        "title_ar": "نمط يستحق المراقبة",
        "meaning_ar": "CartFlow يراقب — لا يلزم إجراء الآن",
        "default_surfaces": [SURFACE_MERCHANT_HOME, SURFACE_KNOWLEDGE_LAYER],
    },
}

_CLASS_RANK = {
    CLASS_CRITICAL_ACTION: 4,
    CLASS_SUGGESTED_ACTION: 3,
    CLASS_NEEDS_ATTENTION: 2,
    CLASS_OBSERVATION: 1,
}

_CONF_RANK = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}

_RETURN_LIFECYCLE = frozenset({"return_to_site", "waiting_purchase_window"})
_COMPLETED_LIFECYCLE = frozenset({"completed", "archived"})


@dataclass
class _Observability:
    groups_assigned: int = 0
    recommendations_projected: int = 0
    memory_beats: int = 0
    priorities_built: int = 0
    carts_processed: int = 0


_OBS = _Observability()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _norm_lower(value) in ("true", "1", "yes")


def _cart_amount(row: Mapping[str, Any]) -> float:
    for key in ("cart_value", "cart_total", "amount", "total"):
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return 0.0


def _recovery_key(row: Mapping[str, Any]) -> str:
    return _norm(row.get("recovery_key")) or _norm(row.get("proof_source"))


def _primary_bucket(row: Mapping[str, Any]) -> str:
    return _norm_lower(row.get("merchant_cart_primary_bucket"))


def _lifecycle_state(row: Mapping[str, Any]) -> str:
    return _norm_lower(row.get("customer_lifecycle_state"))


def _has_phone(row: Mapping[str, Any]) -> bool:
    if row.get("has_phone") is False:
        return False
    if row.get("has_phone") is True:
        return True
    expl = row.get("merchant_explanation_v1")
    if isinstance(expl, Mapping) and expl.get("has_phone") is False:
        return False
    return bool(_norm(row.get("customer_phone")) or _norm(row.get("phone")))


def _is_vip_lane(row: Mapping[str, Any]) -> bool:
    return _as_bool(row.get("is_vip_lane"))


def _is_purchase_truth(row: Mapping[str, Any]) -> bool:
    if _as_bool(row.get("purchase_truth")):
        return True
    return _norm_lower(row.get("customer_lifecycle_completed_variant")) == "purchased"


def _published_decisions(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    bundle = row.get("merchant_decisions_v1")
    if not isinstance(bundle, Mapping):
        return []
    decisions = bundle.get("decisions")
    if not isinstance(decisions, list):
        return []
    out: list[dict[str, Any]] = []
    for item in decisions:
        if not isinstance(item, Mapping):
            continue
        if _norm_lower(item.get("lifecycle_state")) != LIFECYCLE_PUBLISHED:
            continue
        out.append(dict(item))
    return out


def _primary_decision(decisions: Sequence[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    if not decisions:
        return None
    ranked = sorted(
        decisions,
        key=lambda d: (
            int(d.get("priority") or 0),
            _CLASS_RANK.get(_norm(d.get("decision_class")), 0),
            _CONF_RANK.get(_norm_lower(d.get("confidence")), 0),
        ),
        reverse=True,
    )
    return dict(ranked[0])


def _merchant_needed_truth(row: Mapping[str, Any]) -> bool:
    return _norm(row.get("customer_lifecycle_merchant_needed_ar")) == _MERCHANT_NEEDED_YES


def _intervention_action_key(decision: Mapping[str, Any]) -> str:
    return _norm_lower(decision.get("action_key"))


def _needs_merchant_decision(
    decisions: Sequence[Mapping[str, Any]],
    row: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    merchant_needed = _merchant_needed_truth(row)
    for dec in sorted(
        decisions,
        key=lambda d: (
            _CLASS_RANK.get(_norm(d.get("decision_class")), 0),
            int(d.get("priority") or 0),
        ),
        reverse=True,
    ):
        cls = _norm(dec.get("decision_class"))
        action_key = _intervention_action_key(dec)
        if cls in (CLASS_CRITICAL_ACTION, CLASS_SUGGESTED_ACTION):
            return dict(dec)
        if cls == CLASS_NEEDS_ATTENTION and merchant_needed:
            return dict(dec)
        if merchant_needed and action_key in INTERVENTION_DECISION_KEYS:
            return dict(dec)
        if _as_bool(dec.get("action_required")) and _CLASS_RANK.get(cls, 0) >= _CLASS_RANK[
            CLASS_NEEDS_ATTENTION
        ]:
            return dict(dec)
    return None


def _collect_evidence_ids(
    row: Mapping[str, Any],
    decision: Optional[Mapping[str, Any]],
) -> list[str]:
    ids: list[str] = []
    if decision:
        for eid in decision.get("evidence_ids") or []:
            s = _norm(eid)
            if s and s not in ids:
                ids.append(s)
    proof = row.get("merchant_proof_surface_v1")
    if isinstance(proof, Mapping):
        eid = _norm(proof.get("evidence_id"))
        if eid and eid not in ids:
            ids.append(eid)
    return ids


def _group_meta(group_id: str) -> dict[str, Any]:
    return dict(_GROUP_REGISTRY.get(group_id) or {})


def _eligible_surfaces(group_id: str) -> list[str]:
    meta = _group_meta(group_id)
    return list(meta.get("default_surfaces") or [])


def assign_cart_intelligence_group(row: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Deterministic operational group assignment for one cart row."""
    lifecycle = _lifecycle_state(row)
    bucket = _primary_bucket(row)
    decisions = _published_decisions(row)
    needs_dec = _needs_merchant_decision(decisions, row)
    primary_dec = _primary_decision(decisions)
    evidence_ids = _collect_evidence_ids(row, primary_dec or needs_dec)
    confidence = _norm_lower((needs_dec or primary_dec or {}).get("confidence")) or "medium"

    group_id: Optional[str] = None
    reason = ""
    creation_reason = ""

    if _is_purchase_truth(row) or bucket == PRIMARY_RECOVERED or lifecycle in _COMPLETED_LIFECYCLE:
        group_id = GROUP_COMPLETED
        reason = "purchase_or_lifecycle_completed"
        creation_reason = "lifecycle_or_purchase_truth"
        confidence = "high"
    elif needs_dec is not None:
        group_id = GROUP_NEEDS_MERCHANT
        reason = f"decision:{_norm(needs_dec.get('decision_id'))}"
        creation_reason = "published_decision_needs_merchant"
        confidence = _norm_lower(needs_dec.get("confidence")) or confidence
    elif _is_vip_lane(row):
        group_id = GROUP_VIP
        reason = "is_vip_lane"
        creation_reason = "vip_operational_lane"
        confidence = "high"
    elif bucket == PRIMARY_NO_PHONE:
        group_id = GROUP_NO_CONTACT
        reason = "missing_phone_blocked"
        creation_reason = "primary_no_phone_bucket"
        confidence = "high"
    elif not _has_phone(row):
        group_id = GROUP_WAITING_PHONE
        reason = "missing_phone"
        creation_reason = "no_phone_before_send"
        confidence = "high"
    elif lifecycle in _RETURN_LIFECYCLE or bucket == PRIMARY_RETURN_TO_SITE:
        if lifecycle == "waiting_purchase_window":
            group_id = GROUP_WAITING_PURCHASE
            reason = "waiting_purchase_window"
            creation_reason = "lifecycle_purchase_window"
        else:
            group_id = GROUP_RETURNED
            reason = "return_to_site"
            creation_reason = "lifecycle_or_bucket_return"
        confidence = "high"
    elif bucket in (PRIMARY_SENT, PRIMARY_NEEDS_FOLLOWUP, "customer_engaged", "customer_reply"):
        group_id = GROUP_WAITING_REPLY
        reason = f"bucket:{bucket}"
        creation_reason = "sent_awaiting_customer"
        confidence = "medium"

    if group_id is None:
        return None

    meta = _group_meta(group_id)
    assignment = {
        "group_id": group_id,
        "intelligence_group_key": group_id,
        "title_ar": _norm(meta.get("title_ar")) or group_id,
        "meaning_ar": _norm(meta.get("meaning_ar")),
        "reason": reason,
        "priority": int((needs_dec or primary_dec or {}).get("priority") or 0),
        "confidence": confidence,
        "evidence_count": len(evidence_ids),
        "evidence_ids": evidence_ids,
        "decision_ids": [
            _norm(d.get("decision_id")) for d in decisions if _norm(d.get("decision_id"))
        ],
        "recovery_key": _recovery_key(row),
        "authority": AUTHORITY,
        "creation_reason": creation_reason,
        "inputs": [
            "merchant_cart_primary_bucket",
            "customer_lifecycle_state",
            "merchant_decisions_v1",
            "is_vip_lane",
            "has_phone",
        ],
        "assigned_at": _utc_now_iso(),
        "eligible_surfaces": _eligible_surfaces(group_id),
    }
    _OBS.groups_assigned += 1
    return assignment


def decision_class_to_recommendation_type(
    decision_class: str,
    *,
    action_eligible: bool = False,
    suppressed: bool = False,
) -> str:
    if suppressed:
        return REC_SUPPRESSED
    cls = _norm(decision_class)
    if cls == CLASS_CRITICAL_ACTION:
        return REC_REQUIRED
    if cls == CLASS_SUGGESTED_ACTION:
        return REC_SUGGESTED
    if cls == CLASS_NEEDS_ATTENTION:
        return REC_SUGGESTED if action_eligible else REC_WATCH
    if cls == CLASS_OBSERVATION:
        return REC_INFORMATIONAL
    return REC_NO_ACTION


def _project_recommendation_type_v1(
    row: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    action_eligible: bool = False,
) -> str:
    cls = _norm(decision.get("decision_class"))
    rec_type = decision_class_to_recommendation_type(cls, action_eligible=action_eligible)
    action_key = _intervention_action_key(decision)
    if _merchant_needed_truth(row) and action_key in INTERVENTION_DECISION_KEYS:
        if cls == CLASS_CRITICAL_ACTION or action_key == DECISION_FIX_CHANNEL:
            return REC_REQUIRED
        if rec_type in (REC_INFORMATIONAL, REC_WATCH, REC_NO_ACTION):
            return REC_SUGGESTED if action_eligible else REC_WATCH
    if _as_bool(decision.get("action_required")) and cls == CLASS_NEEDS_ATTENTION:
        return REC_SUGGESTED if action_eligible else REC_WATCH
    return rec_type


def derive_recommendation_v1(
    row: Mapping[str, Any],
    *,
    group_assignment: Optional[Mapping[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    decisions = _published_decisions(row)
    primary = _primary_decision(decisions)
    if primary is None:
        if group_assignment and _norm(group_assignment.get("group_id")) == GROUP_COMPLETED:
            return {
                "recommendation_id": f"rec:completed:{_recovery_key(row)}",
                "recommendation_type": REC_NO_ACTION,
                "decision_class": CLASS_OBSERVATION,
                "priority": 50,
                "confidence": "high",
                "merchant_message_ar": "CartFlow أنجز هذا المسار — لا يلزم إجراء",
                "supporting_evidence": _collect_evidence_ids(row, None),
                "expiration": None,
                "eligible_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL],
                "authority": AUTHORITY,
                "basis": "group_completed",
                "decision_id": None,
                "creation_reason": "completed_group_calm",
            }
        if not _has_phone(row) and _primary_bucket(row) == PRIMARY_NO_PHONE:
            return {
                "recommendation_id": f"rec:blocked:{_recovery_key(row)}",
                "recommendation_type": REC_BLOCKED,
                "decision_class": CLASS_NEEDS_ATTENTION,
                "priority": 100,
                "confidence": "high",
                "merchant_message_ar": "لا يمكن المتابعة — رقم التواصل غير متوفر",
                "supporting_evidence": ["missing_phone"],
                "expiration": None,
                "eligible_surfaces": [SURFACE_CARTS, SURFACE_CART_DETAIL],
                "authority": AUTHORITY,
                "basis": "policy_block",
                "decision_id": None,
                "creation_reason": "missing_phone_block",
            }
        return None

    action_eligible = _as_bool(row.get("merchant_intervention_executable"))
    rec_type = _project_recommendation_type_v1(
        row,
        primary,
        action_eligible=action_eligible,
    )
    if rec_type == REC_SUPPRESSED:
        return None

    expl = primary.get("decision_explanation")
    message = ""
    if isinstance(expl, Mapping):
        message = _norm(expl.get("rationale_ar")) or _norm(expl.get("why_now_ar"))
    if not message:
        expl_row = row.get("merchant_explanation_v1")
        if isinstance(expl_row, Mapping):
            message = _norm(expl_row.get("what_happened_ar"))
    if not message:
        message = "CartFlow يقترح متابعة هذه السلة"

    rec = {
        "recommendation_id": f"rec:{_norm(primary.get('decision_id'))}:{_recovery_key(row)}",
        "recommendation_type": rec_type,
        "decision_class": _norm(primary.get("decision_class")),
        "priority": int(primary.get("priority") or 0),
        "confidence": _norm_lower(primary.get("confidence")) or "medium",
        "merchant_message_ar": message,
        "supporting_evidence": _collect_evidence_ids(row, primary),
        "expiration": primary.get("expiration"),
        "eligible_surfaces": _eligible_surfaces(
            _norm((group_assignment or {}).get("group_id")) or GROUP_NEEDS_MERCHANT,
        ),
        "authority": AUTHORITY,
        "basis": "decision",
        "decision_id": _norm(primary.get("decision_id")) or None,
        "creation_reason": f"decision_class:{_norm(primary.get('decision_class'))}",
        "group_id": _norm((group_assignment or {}).get("group_id")) or None,
    }
    _OBS.recommendations_projected += 1
    return rec


def _representative_item(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best = members[0]
    best_score: tuple[int, float, str] = (-1, -1.0, "")
    for row in members:
        rec = derive_recommendation_v1(row, group_assignment=row.get("_mi_group_assignment"))
        pri = int((rec or {}).get("priority") or 0)
        score = (pri, _cart_amount(row), _recovery_key(row))
        if score > best_score:
            best_score = score
            best = row
    return {
        "recovery_key": _recovery_key(best),
        "cart_value": _cart_amount(best),
        "customer_lifecycle_state": _lifecycle_state(best),
        "reason_tag": _norm(best.get("reason_tag")),
    }


def aggregate_intelligence_groups(
    rows: Sequence[Mapping[str, Any]],
    assignments: Sequence[Optional[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row, assignment in zip(rows, assignments):
        if assignment is None:
            continue
        gid = _norm(assignment.get("group_id"))
        if not gid:
            continue
        row_copy = dict(row)
        row_copy["_mi_group_assignment"] = assignment
        by_group[gid].append(row_copy)

    groups: list[dict[str, Any]] = []
    for gid in _OPERATIONAL_GROUP_ORDER:
        members = by_group.get(gid) or []
        if not members:
            continue
        meta = _group_meta(gid)
        rep = _representative_item(members)
        rec = None
        for m in members:
            candidate = derive_recommendation_v1(m, group_assignment={"group_id": gid})
            if candidate and (
                rec is None or int(candidate.get("priority") or 0) > int(rec.get("priority") or 0)
            ):
                rec = candidate

        total_value = sum(_cart_amount(m) for m in members)
        evidence_union: list[str] = []
        for m in members:
            for eid in _collect_evidence_ids(m, _primary_decision(_published_decisions(m))):
                if eid not in evidence_union:
                    evidence_union.append(eid)

        group_rec_type = REC_NO_ACTION
        if rec:
            group_rec_type = _norm(rec.get("recommendation_type")) or REC_NO_ACTION
        elif gid in (GROUP_RETURNED, GROUP_WAITING_PURCHASE):
            group_rec_type = REC_WATCH

        groups.append(
            {
                "group_id": gid,
                "title_ar": _norm(meta.get("title_ar")) or gid,
                "meaning_ar": _norm(meta.get("meaning_ar")),
                "reason": f"{len(members)} carts qualify via {gid}",
                "priority": max(int((rec or {}).get("priority") or 0) for m in members),
                "confidence": _norm_lower((rec or {}).get("confidence")) or "medium",
                "evidence_count": len(evidence_union),
                "evidence_ids": evidence_union,
                "affected_carts": len(members),
                "affected_cart_keys": [_recovery_key(m) for m in members],
                "total_cart_value": round(total_value, 2),
                "representative_item": rep,
                "merchant_summary_ar": (
                    f"{len(members)} سلات · SR {round(total_value, 0):,.0f}"
                    if total_value
                    else f"{len(members)} سلات"
                ),
                "recommended_action_type": group_rec_type,
                "eligible_surfaces": _eligible_surfaces(gid),
                "authority": AUTHORITY,
                "creation_reason": "aggregate_operational_group",
            }
        )
    return groups


def build_pattern_groups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    reason_counts: Counter[str] = Counter()
    product_counts: Counter[str] = Counter()
    for row in rows:
        tag = _norm_lower(row.get("reason_tag"))
        if tag:
            reason_counts[tag] += 1
        pid = _norm(row.get("product_id") or row.get("zid_product_id"))
        if pid:
            product_counts[pid] += 1

    patterns: list[dict[str, Any]] = []
    for tag, count in reason_counts.items():
        if count < PATTERN_HESITATION_MIN:
            continue
        conf = "high" if count >= 5 else "medium"
        patterns.append(
            {
                "group_id": GROUP_REPEATED_HESITATION,
                "pattern_key": f"reason:{tag}",
                "title_ar": f"تردد متكرر — {tag}",
                "meaning_ar": f"نمط تردد ({tag})",
                "reason": f"reason_tag:{tag} count={count}",
                "priority": 150 if count >= 5 else 120,
                "confidence": conf,
                "evidence_count": count,
                "evidence_ids": ["hesitation_reason"],
                "affected_carts": count,
                "representative_item": {"reason_tag": tag},
                "merchant_summary_ar": f"{count} سلات · سبب: {tag}",
                "recommended_action_type": REC_WATCH if count < 5 else REC_SUGGESTED,
                "eligible_surfaces": _eligible_surfaces(GROUP_REPEATED_HESITATION),
                "authority": AUTHORITY,
                "creation_reason": "pattern_reason_threshold",
            }
        )

    for pid, count in product_counts.items():
        if count < PRODUCT_HESITATION_MIN:
            continue
        patterns.append(
            {
                "group_id": GROUP_PRODUCT_HESITATION,
                "pattern_key": f"product:{pid}",
                "title_ar": "تردد على منتج",
                "meaning_ar": f"نمط تردد على منتج {pid}",
                "reason": f"product_id:{pid} count={count}",
                "priority": 110,
                "confidence": "medium",
                "evidence_count": count,
                "evidence_ids": ["product_history"],
                "affected_carts": count,
                "representative_item": {"product_id": pid},
                "merchant_summary_ar": f"{count} سلات · منتج {pid}",
                "recommended_action_type": REC_WATCH,
                "eligible_surfaces": _eligible_surfaces(GROUP_PRODUCT_HESITATION),
                "authority": AUTHORITY,
                "creation_reason": "pattern_product_threshold",
            }
        )

    watch_decisions = sum(
        1
        for row in rows
        for dec in _published_decisions(row)
        if _norm(dec.get("decision_class")) == CLASS_OBSERVATION
    )
    if watch_decisions >= PATTERN_HESITATION_MIN:
        patterns.append(
            {
                "group_id": GROUP_RISK_PATTERN,
                "pattern_key": "watch:observations",
                "title_ar": "نمط يستحق المراقبة",
                "meaning_ar": "CartFlow يراقب — لا يلزم إجراء فوري",
                "reason": f"observation_decisions={watch_decisions}",
                "priority": 80,
                "confidence": "low",
                "evidence_count": watch_decisions,
                "evidence_ids": ["customer_journey"],
                "affected_carts": watch_decisions,
                "representative_item": {},
                "merchant_summary_ar": f"{watch_decisions} ملاحظات للمراقبة",
                "recommended_action_type": REC_WATCH,
                "eligible_surfaces": _eligible_surfaces(GROUP_RISK_PATTERN),
                "authority": AUTHORITY,
                "creation_reason": "observation_pattern_threshold",
            }
        )
    return patterns


def build_memory_beats_v1(
    rows: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    *,
    comparison_context: Optional[Mapping[str, Any]] = None,
) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    ctx = comparison_context if isinstance(comparison_context, Mapping) else {}
    group_counts = {_norm(g.get("group_id")): int(g.get("affected_carts") or 0) for g in groups}

    prior_day = ctx.get("group_counts_yesterday")
    if isinstance(prior_day, Mapping):
        for gid, count in group_counts.items():
            prev = int(prior_day.get(gid) or 0)
            if prev == count:
                continue
            beats.append(
                {
                    "memory_type": MEMORY_VS_YESTERDAY,
                    "comparison_window": "1d",
                    "finding_ar": (
                        f"{_norm(_group_meta(gid).get('title_ar'))}: "
                        f"{count} اليوم مقابل {prev} أمس"
                    ),
                    "evidence": {"group_id": gid, "current": count, "previous": prev},
                    "confidence": "high",
                    "direction": MEMORY_IMPROVED if count < prev else MEMORY_DECLINED,
                    "eligible_surfaces": [SURFACE_MERCHANT_HOME, SURFACE_WEEKLY_BRIEF],
                    "authority": AUTHORITY,
                    "creation_reason": "comparison_context_yesterday",
                }
            )

    prior_week = ctx.get("group_counts_last_week")
    if isinstance(prior_week, Mapping):
        for gid, count in group_counts.items():
            prev = int(prior_week.get(gid) or 0)
            if prev == count:
                continue
            beats.append(
                {
                    "memory_type": MEMORY_VS_LAST_WEEK,
                    "comparison_window": "7d",
                    "finding_ar": (
                        f"{_norm(_group_meta(gid).get('title_ar'))}: "
                        f"{count} مقابل {prev} الأسبوع الماضي"
                    ),
                    "evidence": {"group_id": gid, "current": count, "previous": prev},
                    "confidence": "medium",
                    "direction": MEMORY_IMPROVED if count < prev else MEMORY_DECLINED,
                    "eligible_surfaces": [SURFACE_MERCHANT_HOME, SURFACE_KNOWLEDGE_LAYER],
                    "authority": AUTHORITY,
                    "creation_reason": "comparison_context_week",
                }
            )

    reason_counts: Counter[str] = Counter()
    for row in rows:
        tag = _norm_lower(row.get("reason_tag"))
        if tag:
            reason_counts[tag] += 1
    for tag, count in reason_counts.items():
        if count < 2:
            continue
        beats.append(
            {
                "memory_type": MEMORY_REPEATED_PATTERN,
                "comparison_window": f"{PATTERN_HESITATION_WINDOW_DAYS}d",
                "finding_ar": f"تكرار سبب التردد ({tag}) في {count} سلات",
                "evidence": {"reason_tag": tag, "count": count},
                "confidence": "high" if count >= PATTERN_HESITATION_MIN else "medium",
                "direction": MEMORY_REPEATED_PATTERN,
                "eligible_surfaces": [SURFACE_MERCHANT_HOME, SURFACE_KNOWLEDGE_LAYER],
                "authority": AUTHORITY,
                "creation_reason": "in_batch_reason_distribution",
            }
        )

    completed = group_counts.get(GROUP_COMPLETED, 0)
    if completed:
        beats.append(
            {
                "memory_type": MEMORY_RESOLVED,
                "comparison_window": "current",
                "finding_ar": f"تم إنجاز {completed} مسارات",
                "evidence": {"group_id": GROUP_COMPLETED, "count": completed},
                "confidence": "high",
                "direction": MEMORY_RESOLVED,
                "eligible_surfaces": [SURFACE_MERCHANT_HOME, SURFACE_DAILY_BRIEF],
                "authority": AUTHORITY,
                "creation_reason": "completed_group_count",
            }
        )

    _OBS.memory_beats += len(beats)
    return beats


def build_merchant_priorities_v1(
    groups: Sequence[Mapping[str, Any]],
    recommendations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    priorities: list[dict[str, Any]] = []
    rank = 0
    rec_by_type = sorted(recommendations, key=lambda r: int(r.get("priority") or 0), reverse=True)
    for rec in rec_by_type:
        rtype = _norm(rec.get("recommendation_type"))
        if rtype in (REC_SUPPRESSED, REC_NO_ACTION, REC_INFORMATIONAL):
            continue
        rank += 1
        band = PRIORITY_HIGHEST if rtype == REC_REQUIRED else PRIORITY_TODAY
        if rtype in (REC_WATCH, REC_BLOCKED):
            band = PRIORITY_WATCHING
        priorities.append(
            {
                "priority_rank": rank,
                "priority_band": band,
                "reason": _norm(rec.get("creation_reason")),
                "merchant_message_ar": _norm(rec.get("merchant_message_ar")),
                "recommended_action_type": rtype,
                "recommended_action_decision_id": rec.get("decision_id"),
                "confidence": _norm_lower(rec.get("confidence")) or "medium",
                "eligible_surfaces": list(rec.get("eligible_surfaces") or []),
                "authority": AUTHORITY,
                "creation_reason": "recommendation_priority",
            }
        )

    for group in sorted(groups, key=lambda g: int(g.get("priority") or 0), reverse=True):
        if _norm(group.get("group_id")) != GROUP_COMPLETED:
            continue
        rank += 1
        priorities.append(
            {
                "priority_rank": rank,
                "priority_band": PRIORITY_COMPLETED,
                "reason": GROUP_COMPLETED,
                "merchant_message_ar": _norm(group.get("merchant_summary_ar")),
                "recommended_action_type": REC_NO_ACTION,
                "recommended_action_decision_id": None,
                "confidence": _norm_lower(group.get("confidence")) or "high",
                "eligible_surfaces": list(group.get("eligible_surfaces") or []),
                "authority": AUTHORITY,
                "creation_reason": "completed_group_priority",
            }
        )

    _OBS.priorities_built += len(priorities)
    return priorities


def build_cart_merchant_intelligence_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    assignment = assign_cart_intelligence_group(row)
    recommendation = derive_recommendation_v1(row, group_assignment=assignment)
    return {
        "version": INTELLIGENCE_VERSION,
        "authority": AUTHORITY,
        "group_assignment": assignment,
        "intelligence_group_key": _norm((assignment or {}).get("group_id")) or None,
        "recommendation": recommendation,
        "observability": {
            "why_exists": _norm((assignment or {}).get("creation_reason")) or "calm_monitoring",
            "evidence_source": (assignment or {}).get("evidence_ids") or [],
            "confidence": _norm_lower((assignment or recommendation or {}).get("confidence"))
            or "medium",
            "authority": AUTHORITY,
            "creation_reason": _norm((recommendation or assignment or {}).get("creation_reason")),
            "reviewable": True,
        },
    }


def build_store_merchant_intelligence_v1(
    rows: Sequence[Mapping[str, Any]],
    *,
    comparison_context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    row_list = [dict(r) for r in rows if isinstance(r, Mapping)]
    assignments = [assign_cart_intelligence_group(r) for r in row_list]
    for row, assignment in zip(row_list, assignments):
        row["intelligence_group_key"] = _norm((assignment or {}).get("group_id")) or None

    operational = aggregate_intelligence_groups(row_list, assignments)
    patterns = build_pattern_groups(row_list)
    groups = operational + patterns

    recommendations: list[dict[str, Any]] = []
    seen_rec: set[str] = set()
    for row in row_list:
        rec = derive_recommendation_v1(
            row,
            group_assignment={"group_id": _norm(row.get("intelligence_group_key"))},
        )
        if rec is None:
            continue
        rid = _norm(rec.get("recommendation_id"))
        if rid in seen_rec:
            continue
        seen_rec.add(rid)
        recommendations.append(rec)

    memory = build_memory_beats_v1(row_list, groups, comparison_context=comparison_context)
    priorities = build_merchant_priorities_v1(groups, recommendations)
    _OBS.carts_processed += len(row_list)

    return {
        "version": INTELLIGENCE_VERSION,
        "authority": AUTHORITY,
        "generated_at": _utc_now_iso(),
        "groups": groups,
        "recommendations": recommendations,
        "memory": memory,
        "priorities": priorities,
        "cart_assignments": [a for a in assignments if a is not None],
        "observability": {
            "carts_processed": len(row_list),
            "groups_active": len(operational),
            "patterns_active": len(patterns),
            "recommendations_count": len(recommendations),
            "memory_beats_count": len(memory),
            "priorities_count": len(priorities),
            "authority": AUTHORITY,
            "reviewable": True,
        },
    }


def attach_merchant_intelligence_v1(target: Mapping[str, Any] | dict[str, Any]) -> None:
    if not isinstance(target, dict):
        return
    bundle = build_cart_merchant_intelligence_v1(target)
    target["merchant_intelligence_v1"] = bundle
    key = bundle.get("intelligence_group_key")
    if key:
        target["intelligence_group_key"] = key


def attach_store_merchant_intelligence_v1(
    target: Mapping[str, Any] | dict[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    comparison_context: Optional[Mapping[str, Any]] = None,
) -> None:
    if not isinstance(target, dict):
        return
    target["merchant_intelligence_store_v1"] = build_store_merchant_intelligence_v1(
        rows,
        comparison_context=comparison_context,
    )


def ensure_normal_carts_merchant_intelligence_store_v1(
    payload: Mapping[str, Any] | dict[str, Any],
) -> None:
    """Normal-carts transport contract — store MI bundle on every API/snapshot payload."""
    if not isinstance(payload, dict):
        return
    rows = list(payload.get("merchant_carts_page_rows") or [])
    attach_store_merchant_intelligence_v1(payload, rows)


def get_merchant_intelligence_observability_v1() -> dict[str, Any]:
    return {
        "version": INTELLIGENCE_VERSION,
        "groups_assigned": _OBS.groups_assigned,
        "recommendations_projected": _OBS.recommendations_projected,
        "memory_beats": _OBS.memory_beats,
        "priorities_built": _OBS.priorities_built,
        "carts_processed": _OBS.carts_processed,
    }


def reset_merchant_intelligence_observability_v1() -> None:
    global _OBS
    _OBS = _Observability()


def validate_merchant_intelligence_contract_v1(bundle: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if _norm(bundle.get("version")) != INTELLIGENCE_VERSION:
        errors.append("version mismatch")
    if _norm(bundle.get("authority")) != AUTHORITY:
        errors.append("authority mismatch")
    ga = bundle.get("group_assignment")
    if ga is not None and not isinstance(ga, Mapping):
        errors.append("group_assignment must be object or null")
    rec = bundle.get("recommendation")
    if rec is not None:
        if not isinstance(rec, Mapping):
            errors.append("recommendation must be object or null")
        elif not _norm(rec.get("recommendation_type")):
            errors.append("recommendation_type required")
    obs = bundle.get("observability")
    if not isinstance(obs, Mapping) or not obs.get("reviewable"):
        errors.append("observability.reviewable required")
    return errors


__all__ = [
    "AUTHORITY",
    "GROUP_COMPLETED",
    "GROUP_NEEDS_MERCHANT",
    "GROUP_REPEATED_HESITATION",
    "GROUP_RETURNED",
    "GROUP_VIP",
    "GROUP_WAITING_REPLY",
    "INTELLIGENCE_VERSION",
    "REC_REQUIRED",
    "REC_SUGGESTED",
    "REC_WATCH",
    "SURFACE_CARTS",
    "SURFACE_MERCHANT_HOME",
    "assign_cart_intelligence_group",
    "attach_merchant_intelligence_v1",
    "attach_store_merchant_intelligence_v1",
    "ensure_normal_carts_merchant_intelligence_store_v1",
    "build_cart_merchant_intelligence_v1",
    "build_memory_beats_v1",
    "build_merchant_priorities_v1",
    "build_store_merchant_intelligence_v1",
    "decision_class_to_recommendation_type",
    "derive_recommendation_v1",
    "get_merchant_intelligence_observability_v1",
    "reset_merchant_intelligence_observability_v1",
    "validate_merchant_intelligence_contract_v1",
]
