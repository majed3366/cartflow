# -*- coding: utf-8 -*-
"""
Merchant Daily Brief v1 — governed consumer of merchant_decisions_v1.

Presentation only: selects and projects published decisions into a daily brief.
Never mints decisions, evaluates truth, or generates recommendations.

INV-002 WP-4: consumes Platform Identity Authority MQIC — never resolves
merchant/store identity independently.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from services.merchant_daily_brief_time_v1 import (
    BRIEF_DEFAULT_WINDOW_DAYS,
    brief_date_iso,
    brief_stamp_now,
    brief_time_observability,
    resolve_brief_windows,
)
from services.merchant_decision_layer_v1 import (
    CLASS_CRITICAL_ACTION,
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)
from services.merchant_evidence_registry_v1 import merchant_evidence_label_ar

DAILY_BRIEF_VERSION = "v1"
MAX_BRIEF_ITEMS = 5

_EMPTY_TITLE_AR = "يوم هادئ في متجرك"
_EMPTY_MESSAGE_AR = (
    "لا توجد قرارات تتطلب انتباهك اليوم — CartFlow يتابع الحالات الروتينية تلقائياً"
)

_COMMERCIAL_GOAL_LABEL_AR = {
    "recover_revenue": "استرجاع المبيعات",
    "reduce_hesitation": "تقليل التردد",
    "improve_conversion": "تحسين التحويل",
    "reduce_workload": "تقليل عبء المتابعة",
    "increase_confidence": "رفع الثقة",
    "improve_operations": "تحسين التشغيل",
}

_DECISION_CLASS_LABEL_AR = {
    CLASS_OBSERVATION: "ملاحظة",
    CLASS_NEEDS_ATTENTION: "يحتاج انتباه",
    CLASS_SUGGESTED_ACTION: "إجراء مقترح",
    CLASS_CRITICAL_ACTION: "إجراء عاجل",
}

_CONFIDENCE_LABEL_AR = {
    "high": "عالية",
    "medium": "متوسطة",
    "low": "منخفضة",
    "insufficient": "غير كافية",
}

_ACTION_KEY_LABEL_AR = {
    "obtain_contact": "الحصول على رقم العميل",
    "fix_channel": "إصلاح قناة التواصل",
    "contact_customer": "التواصل مع العميل",
    "monitor": "مراقبة العميل",
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def is_decision_brief_eligible_v1(decision: Mapping[str, Any]) -> bool:
    """Published, passed verification, not suppressed — per foundation §5."""
    if _norm(decision.get("lifecycle_state")) != LIFECYCLE_PUBLISHED:
        return False
    if _norm(decision.get("verification_status")) != VERIFY_PASSED:
        return False
    suppression = _norm(decision.get("suppression_state")).lower()
    if suppression and suppression != "none":
        return False
    return True


def collect_published_decisions_from_bundles_v1(
    bundles: Iterable[Mapping[str, Any] | None],
) -> list[dict[str, Any]]:
    """Extract eligible published decisions from merchant_decisions_v1 bundles."""
    out: list[dict[str, Any]] = []
    for bundle in bundles:
        if not isinstance(bundle, Mapping):
            continue
        decisions = bundle.get("decisions")
        if not isinstance(decisions, list):
            continue
        for raw in decisions:
            if not isinstance(raw, Mapping):
                continue
            if not is_decision_brief_eligible_v1(raw):
                continue
            out.append(dict(raw))
    return out


def _select_brief_decisions_v1(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort by governance priority, dedupe merge_key, cap at MAX_BRIEF_ITEMS."""
    ranked = sorted(
        decisions,
        key=lambda d: (
            int(d.get("priority") or 0),
            _norm(d.get("decision_timestamp")),
        ),
        reverse=True,
    )

    seen_merge: set[str] = set()
    selected: list[dict[str, Any]] = []
    for decision in ranked:
        merge_key = _norm(decision.get("merge_key")) or _norm(decision.get("decision_id"))
        if merge_key in seen_merge:
            continue
        seen_merge.add(merge_key)
        selected.append(decision)
        if len(selected) >= MAX_BRIEF_ITEMS:
            break
    return selected


def _evidence_source_ar(decision: Mapping[str, Any]) -> str:
    evidence_ids = decision.get("evidence_ids")
    if isinstance(evidence_ids, list):
        for eid in evidence_ids:
            label = merchant_evidence_label_ar(_norm(eid), fallback="")
            if label:
                return label
    return "—"


def _commercial_goal_label_ar(goal: str) -> str:
    key = _norm(goal)
    return _COMMERCIAL_GOAL_LABEL_AR.get(key, key or "—")


def _confidence_label_ar(confidence: str) -> str:
    key = _norm(confidence).lower()
    return _CONFIDENCE_LABEL_AR.get(key, key or "—")


def _decision_class_label_ar(decision_class: str) -> str:
    key = _norm(decision_class)
    return _DECISION_CLASS_LABEL_AR.get(key, key or "—")


def _brief_action_ar(decision: Mapping[str, Any]) -> str:
    """Action line only when decision declares executable suggested/critical class."""
    decision_class = _norm(decision.get("decision_class"))
    merchant_action = _norm(decision.get("merchant_action")).lower()
    if merchant_action == "monitor":
        return "مراقبة الحالة — لا يلزم إجراء الآن"
    if merchant_action != "execute":
        return ""
    if decision_class not in (CLASS_SUGGESTED_ACTION, CLASS_CRITICAL_ACTION):
        return ""
    action_key = _norm(decision.get("action_key")).lower()
    return _ACTION_KEY_LABEL_AR.get(action_key, "")


def project_brief_item_v1(
    decision: Mapping[str, Any],
    *,
    brief_date: Optional[str] = None,
) -> dict[str, Any]:
    """Project one published decision into a brief item (presentation view)."""
    day = brief_date or brief_date_iso()
    decision_id = _norm(decision.get("decision_id"))
    explanation = decision.get("decision_explanation")
    if not isinstance(explanation, Mapping):
        explanation = {}

    action_ar = _brief_action_ar(decision)
    return {
        "brief_item_id": f"daily_brief:{day}:{decision_id}",
        "decision_id": decision_id,
        "decision_class": _norm(decision.get("decision_class")),
        "decision_class_label_ar": _decision_class_label_ar(
            _norm(decision.get("decision_class"))
        ),
        "priority": int(decision.get("priority") or 0),
        "what_ar": _norm(explanation.get("rationale_ar")) or "—",
        "why_ar": _norm(explanation.get("why_now_ar")) or "—",
        "action_ar": action_ar,
        "action_present": bool(action_ar),
        "confidence": _norm(decision.get("confidence")),
        "confidence_label_ar": _confidence_label_ar(_norm(decision.get("confidence"))),
        "evidence_source_ar": _evidence_source_ar(decision),
        "evidence_ids": list(decision.get("evidence_ids") or []),
        "commercial_goal": _norm(decision.get("commercial_goal")),
        "commercial_goal_label_ar": _commercial_goal_label_ar(
            _norm(decision.get("commercial_goal"))
        ),
        "merge_key": _norm(decision.get("merge_key")),
        "proof_sources": list(decision.get("proof_sources") or []),
    }


def compose_merchant_daily_brief_v1(
    *,
    decision_bundles: Iterable[Mapping[str, Any] | None],
    brief_date: Optional[str] = None,
) -> dict[str, Any]:
    """
    Compose daily brief from merchant_decisions_v1 bundles only.

    Does not read Truth, Proof, or KL insights directly.
    """
    day = brief_date or brief_date_iso()
    collected = collect_published_decisions_from_bundles_v1(decision_bundles)
    selected = _select_brief_decisions_v1(collected)
    items = [project_brief_item_v1(d, brief_date=day) for d in selected]
    empty = len(items) == 0
    return {
        "version": DAILY_BRIEF_VERSION,
        "brief_date": day,
        "item_count": len(items),
        "max_items": MAX_BRIEF_ITEMS,
        "empty": empty,
        "empty_state_ar": {
            "title_ar": _EMPTY_TITLE_AR,
            "message_ar": _EMPTY_MESSAGE_AR,
        },
        "items": items,
        "observability": {
            "decisions_collected": len(collected),
            "decisions_selected": len(selected),
            "bundles_scanned": sum(
                1
                for b in decision_bundles
                if isinstance(b, Mapping) and isinstance(b.get("decisions"), list)
            ),
        },
    }


def validate_merchant_daily_brief_v1(brief: Mapping[str, Any]) -> list[str]:
    """Return validation errors (empty = PV-18 compliant)."""
    errors: list[str] = []
    if _norm(brief.get("version")) != DAILY_BRIEF_VERSION:
        errors.append("version")
    items = brief.get("items")
    if not isinstance(items, list):
        errors.append("items")
        return errors
    if len(items) > MAX_BRIEF_ITEMS:
        errors.append("item_count_exceeds_max")
    for idx, item in enumerate(items):
        if not isinstance(item, Mapping):
            errors.append(f"items[{idx}]_type")
            continue
        for key in ("brief_item_id", "decision_id", "what_ar", "why_ar"):
            if not _norm(item.get(key)):
                errors.append(f"items[{idx}].{key}")
        if not _norm(item.get("decision_id")):
            errors.append(f"items[{idx}].decision_id_trace")
    return errors


def build_merchant_daily_brief_api_payload(
    db_session: Any,
    store_slug: str = "",
    dash_store: Any = None,
    *,
    page_limit: int = 250,
    mqic: Any = None,
) -> dict[str, Any]:
    """
    Build store daily brief by aggregating existing merchant_decisions_v1 outputs.

    Reuses decision-layer enrichment paths — does not evaluate truth directly.

    INV-002 WP-4: tenant key from Platform Identity Authority MQIC — Brief
    never resolves store identity independently.
    """
    from services.identity_authority import (  # noqa: PLC0415
        daily_brief_identity_scope,
        ensure_daily_brief_mqic,
    )

    with daily_brief_identity_scope(store_slug=store_slug, mqic=mqic) as bound:
        identity = ensure_daily_brief_mqic(store_slug=store_slug, mqic=bound)
        slug = identity.store_slug
        bundles: list[Mapping[str, Any]] = []
        kl_insights: list[Mapping[str, Any]] = []

        try:
            from services.knowledge_layer_v1 import build_knowledge_report  # noqa: PLC0415
            from services.merchant_claim_evidence_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_claim_evidence_v1,
            )
            from services.knowledge_producer_metadata_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_producer_metadata_v1,
            )
            from services.merchant_decision_layer_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_merchant_decisions_v1,
            )

            report = build_knowledge_report(
                db_session,
                slug,
                window_days=BRIEF_DEFAULT_WINDOW_DAYS,
                mqic=identity,
            )
            kl_payload = report.to_dict()
            enrich_knowledge_report_claim_evidence_v1(kl_payload)
            enrich_knowledge_report_producer_metadata_v1(kl_payload)
            enrich_knowledge_report_merchant_decisions_v1(kl_payload)
            kl_bundle = kl_payload.get("merchant_decisions_v1")
            if isinstance(kl_bundle, Mapping):
                bundles.append(kl_bundle)
            for raw in kl_payload.get("insights") or []:
                if isinstance(raw, Mapping):
                    kl_insights.append(raw)
        except (OSError, TypeError, ValueError, ImportError):
            pass

        try:
            from services.normal_carts_dashboard_batch_v1 import (  # noqa: PLC0415
                build_normal_carts_dashboard_api_payload,
            )

            body, _, _ = build_normal_carts_dashboard_api_payload(
                dash_store,
                page_limit=min(250, max(1, int(page_limit))),
                page_offset=0,
                debug_perf=False,
            )
            for row in body.get("merchant_carts_page_rows") or []:
                if not isinstance(row, Mapping):
                    continue
                cart_bundle = row.get("merchant_decisions_v1")
                if isinstance(cart_bundle, Mapping):
                    bundles.append(cart_bundle)
        except (OSError, TypeError, ValueError, ImportError):
            pass

        try:
            from services.merchant_daily_brief_composer_v2 import (  # noqa: PLC0415
                compose_merchant_daily_brief_v2,
            )
        except ImportError:
            compose_merchant_daily_brief_v2 = None  # type: ignore[misc, assignment]

        # One QTC-derived calendar day + window for this brief build
        tw = resolve_brief_windows(window_days=BRIEF_DEFAULT_WINDOW_DAYS)
        day = brief_date_iso()

        brief_fn = compose_merchant_daily_brief_v2 or compose_merchant_daily_brief_v1
        if compose_merchant_daily_brief_v2 is not None:
            brief = compose_merchant_daily_brief_v2(
                decision_bundles=bundles,
                kl_insights=kl_insights,
                brief_date=day,
            )
        else:
            brief = brief_fn(decision_bundles=bundles, brief_date=day)
        brief["ok"] = True
        brief["generated_at"] = brief_stamp_now().replace(microsecond=0).isoformat()
        brief["store_slug"] = slug
        obs = brief.get("observability")
        if not isinstance(obs, dict):
            obs = {}
            brief["observability"] = obs
        obs["time_window"] = brief_time_observability(tw)
        return brief


__all__ = [
    "DAILY_BRIEF_VERSION",
    "MAX_BRIEF_ITEMS",
    "build_merchant_daily_brief_api_payload",
    "collect_published_decisions_from_bundles_v1",
    "compose_merchant_daily_brief_v1",
    "is_decision_brief_eligible_v1",
    "project_brief_item_v1",
    "validate_merchant_daily_brief_v1",
]
