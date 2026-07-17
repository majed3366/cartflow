# -*- coding: utf-8 -*-
"""
Commercial Interpretation Layer V1 — deterministic merchant-value conclusions.

Transforms canonical CartFlow operational truth into governed commercial
interpretation (conclusion, evidence, impact, platform action, merchant action,
confidence). Not AI. Not Home-/JS-owned meaning.

Threshold ownership (V1):
- Rule owner: this module (Commercial Interpretation Layer).
- Evidence owner: ``merchant_store_cart_counts.no_phone_total`` via
  ``dashboard_counter_totals_v1`` + ``dashboard_no_phone_facet_v1``
  (same rule as Cart page ``nophone`` facet).
- Generate when ``no_phone_total > 0``; suppress when ``0``.
- Mark ``is_primary_commercial_blocker`` when this is the largest executable
  recovery blocker among evaluated V1 interpretations (only this ID in V1).
- Confidence reflects evidence quality (direct canonical count → High), not
  presentation importance.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

log = logging.getLogger("cartflow")

INTERPRETATION_VERSION = "v1"
INTERPRETATION_MISSING_CONTACT = "missing_contact_blocks_recovery_v1"

EVIDENCE_SOURCE_NO_PHONE = "merchant_store_cart_counts.no_phone_total"
DRILLDOWN_NOPHONE = "#carts?tab=nophone"
CTA_AFFECTED_CARTS_AR = "عرض السلال المتأثرة"

DESTINATION_HOME = "merchant_home"
DESTINATION_KNOWLEDGE = "knowledge_layer"

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# Last valid package per store — used only when generation fails and a prior
# governed package for the same store exists (never cross-store).
_LAST_VALID_BY_STORE: dict[str, dict[str, Any]] = {}

_TECHNICAL_LEAK_TOKENS = (
    "phone = null",
    "no_phone_total",
    "facet=nophone",
    "schedule missing",
    "recovery materialization",
    "nophone",
    "merchant_has_customer_phone",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def merchant_facing_text_is_clean(text: str) -> bool:
    blob = _norm_lower(text)
    if not blob:
        return True
    return not any(tok in blob for tok in _TECHNICAL_LEAK_TOKENS)


def canonical_no_phone_count_from_payload(payload: Mapping[str, Any] | None) -> Optional[int]:
    """Read store-level no-phone count already present on a dashboard payload."""
    if not isinstance(payload, Mapping):
        return None
    store = payload.get("merchant_store_cart_counts")
    if isinstance(store, Mapping) and "no_phone_total" in store:
        try:
            return max(0, int(store.get("no_phone_total") or 0))
        except (TypeError, ValueError):
            return None
    filters = payload.get("merchant_cart_filter_counts")
    if isinstance(filters, Mapping) and "nophone" in filters:
        try:
            return max(0, int(filters.get("nophone") or 0))
        except (TypeError, ValueError):
            return None
    nav = payload.get("nav_metadata")
    if isinstance(nav, Mapping) and "canonical_no_phone_total" in nav:
        try:
            return max(0, int(nav.get("canonical_no_phone_total") or 0))
        except (TypeError, ValueError):
            return None
    return None


def resolve_canonical_no_phone_total(
    *,
    store_slug: str = "",
    dash_store: Any = None,
    payload: Optional[Mapping[str, Any]] = None,
) -> tuple[Optional[int], dict[str, Any]]:
    """
    Resolve canonical no-phone count without inventing a second classification.

    Preference: payload counter fields → counter totals builder (same SoT).
    """
    meta: dict[str, Any] = {
        "evidence_source": EVIDENCE_SOURCE_NO_PHONE,
        "query_cost": 0,
        "resolve_path": "none",
    }
    from_payload = canonical_no_phone_count_from_payload(payload)
    if from_payload is not None:
        meta["resolve_path"] = "payload_counters"
        return from_payload, meta

    slug = _norm(store_slug)
    t0 = time.perf_counter()
    try:
        store_row = dash_store
        if store_row is None and slug:
            from services.dashboard_store_context import (  # noqa: PLC0415
                dashboard_canonical_store_row,
            )

            store_row = dashboard_canonical_store_row(slug)
        if store_row is None:
            meta["resolve_path"] = "store_missing"
            return None, meta

        from services.dashboard_counter_totals_v1 import (  # noqa: PLC0415
            build_merchant_cart_counter_totals,
        )

        counter_payload = build_merchant_cart_counter_totals(store_row)
        counts = counter_payload.counts.to_counts_dict()
        meta["query_cost"] = 1
        meta["resolve_path"] = "canonical_counter_totals"
        meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        return max(0, int(counts.get("no_phone_total") or 0)), meta
    except Exception as exc:  # noqa: BLE001
        meta["resolve_path"] = "resolve_failed"
        meta["failure_reason"] = _norm(type(exc).__name__)
        meta["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        log.warning(
            "commercial_interpretation_v1 no_phone resolve failed store=%s: %s",
            slug,
            exc,
        )
        return None, meta


def _confidence_for_direct_canonical(count: int) -> tuple[str, str]:
    if count > 0:
        return (
            CONFIDENCE_HIGH,
            "مستمد مباشرة من عدد السلال النشطة المحظورة بسبب غياب رقم تواصل صالح في عدّاد السلال المعتمد.",
        )
    return (
        CONFIDENCE_LOW,
        "لا توجد حالات محظورة بغياب رقم تواصل في العدّاد المعتمد.",
    )


def build_missing_contact_blocks_recovery_v1(
    *,
    store_slug: str,
    no_phone_total: int,
    active_total: Optional[int] = None,
    generated_at: Optional[str] = None,
) -> tuple[Optional[dict[str, Any]], dict[str, Any]]:
    """
    Evaluate ``missing_contact_blocks_recovery_v1``.

    Returns (interpretation_or_None, eval_observability).
    """
    obs: dict[str, Any] = {
        "interpretation_id": INTERPRETATION_MISSING_CONTACT,
        "evaluated": True,
        "generated": False,
        "suppressed": False,
        "suppression_reason": None,
        "evidence_count": int(no_phone_total),
        "confidence": None,
        "is_primary_commercial_blocker": False,
    }
    count = max(0, int(no_phone_total))
    if count <= 0:
        obs["suppressed"] = True
        obs["suppression_reason"] = "count_zero"
        return None, obs

    confidence, confidence_reason = _confidence_for_direct_canonical(count)
    # V1: sole recovery-blocker interpretation → primary whenever generated.
    is_primary = True
    if active_total is not None and int(active_total) > 0 and count > int(active_total):
        # Defensive: never claim more blocked than active.
        obs["suppressed"] = True
        obs["suppression_reason"] = "count_exceeds_active_total"
        return None, obs

    conclusion = "أكبر عائق أمام الاسترجاع حاليًا هو نقص بيانات التواصل."
    evidence_text = (
        f"تعذر بدء الاسترجاع لـ {count} سلة لعدم توفر رقم عميل صالح."
    )
    business_impact = (
        "هذه السلال لا يمكنها الانتقال إلى واتساب أو متابعة الاسترجاع حتى تتوفر وسيلة تواصل."
    )
    cartflow_action = (
        "CartFlow يحتفظ بهذه الحالات ويراقب اكتمال بيانات التواصل دون إرسال رسائل غير قابلة للتنفيذ."
    )
    merchant_action = (
        "راجع السلال المتأثرة، وحسّن جمع رقم العميل قبل مغادرته المتجر."
    )
    expected_result = "زيادة عدد السلال القابلة للدخول في مسار الاسترجاع."

    # Knowledge-facing progressive disclosure (merchant Arabic; no technical leaks).
    kl_observation = (
        "نقص بيانات التواصل يمنع بدء الاسترجاع لعدد كبير من السلال."
    )
    kl_evidence = evidence_text
    kl_explanation = (
        "قنوات الاسترجاع التي تتطلب تواصلاً مباشراً لا يمكن تنفيذها بدون بيانات تواصل صالحة."
    )
    kl_recommendation = (
        "حسّن التقاط رقم العميل وراجع السلال المحظورة حالياً."
    )

    interpretation = {
        "interpretation_id": INTERPRETATION_MISSING_CONTACT,
        "store_slug": _norm(store_slug),
        "generated_at": _norm(generated_at) or _utc_now_iso(),
        "conclusion": conclusion,
        "evidence_text": evidence_text,
        "evidence_count": count,
        "evidence_source": EVIDENCE_SOURCE_NO_PHONE,
        "business_impact": business_impact,
        "cartflow_action": cartflow_action,
        "merchant_action": merchant_action,
        "expected_result": expected_result,
        "confidence_level": confidence,
        "confidence_reason": confidence_reason,
        "destination_surfaces": [DESTINATION_HOME, DESTINATION_KNOWLEDGE],
        "drilldown_target": DRILLDOWN_NOPHONE,
        "cta_label_ar": CTA_AFFECTED_CARTS_AR,
        "interpretation_version": INTERPRETATION_VERSION,
        "is_primary_commercial_blocker": is_primary,
        "knowledge_progression": {
            "observation_ar": kl_observation,
            "evidence_ar": kl_evidence,
            "explanation_ar": kl_explanation,
            "recommendation_ar": kl_recommendation,
            "confidence_level": confidence,
            "confidence_reason": confidence_reason,
        },
        # Home presentation shorthand (still governed here — UI must not invent).
        "home_headline_ar": conclusion,
        "home_impact_ar": (
            "هذه الحالات لا تستطيع الانتقال إلى متابعة الاسترجاع حتى تتوفر وسيلة تواصل."
        ),
        "home_cartflow_action_ar": (
            "CartFlow يحتفظ بالحالات ويراقب جاهزيتها تلقائيًا."
        ),
        "home_merchant_action_ar": (
            "مراجعة السلال المتأثرة وتحسين جمع رقم العميل."
        ),
    }
    obs["generated"] = True
    obs["confidence"] = confidence
    obs["is_primary_commercial_blocker"] = is_primary
    return interpretation, obs


def build_commercial_interpretation_package_v1(
    *,
    store_slug: str,
    no_phone_total: Optional[int],
    active_total: Optional[int] = None,
    resolve_meta: Optional[Mapping[str, Any]] = None,
    generation_failed: bool = False,
    failure_reason: str = "",
) -> dict[str, Any]:
    """Build the governed package Home and Knowledge consume."""
    t0 = time.perf_counter()
    slug = _norm(store_slug)
    evaluated = 0
    generated = 0
    suppressed = 0
    eval_rows: list[dict[str, Any]] = []
    interpretations: list[dict[str, Any]] = []
    primary: Optional[dict[str, Any]] = None

    if generation_failed:
        cached = _LAST_VALID_BY_STORE.get(slug)
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "ok": False,
            "interpretation_version": INTERPRETATION_VERSION,
            "store_slug": slug,
            "generated_at": _utc_now_iso(),
            "primary": dict(cached["primary"]) if isinstance(cached, Mapping) and isinstance(cached.get("primary"), Mapping) else None,
            "interpretations": list(cached.get("interpretations") or [])
            if isinstance(cached, Mapping)
            else [],
            "used_last_valid": bool(
                isinstance(cached, Mapping) and cached.get("primary")
            ),
            "observability": {
                "interpretations_evaluated": 0,
                "interpretations_generated": 0,
                "interpretations_suppressed": 0,
                "suppression_reasons": [],
                "evidence_count": None,
                "confidence": None,
                "generation_duration_ms": duration_ms,
                "destination_routing": [DESTINATION_HOME, DESTINATION_KNOWLEDGE],
                "query_cost": int((resolve_meta or {}).get("query_cost") or 0),
                "failure_reason": _norm(failure_reason) or "generation_failed",
                "resolve": dict(resolve_meta or {}),
                "ai_used": False,
                "probabilistic": False,
            },
        }

    if no_phone_total is None:
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "ok": True,
            "interpretation_version": INTERPRETATION_VERSION,
            "store_slug": slug,
            "generated_at": _utc_now_iso(),
            "primary": None,
            "interpretations": [],
            "used_last_valid": False,
            "observability": {
                "interpretations_evaluated": 0,
                "interpretations_generated": 0,
                "interpretations_suppressed": 0,
                "suppression_reasons": ["evidence_unavailable"],
                "evidence_count": None,
                "confidence": None,
                "generation_duration_ms": duration_ms,
                "destination_routing": [DESTINATION_HOME, DESTINATION_KNOWLEDGE],
                "query_cost": int((resolve_meta or {}).get("query_cost") or 0),
                "failure_reason": None,
                "resolve": dict(resolve_meta or {}),
                "ai_used": False,
                "probabilistic": False,
            },
        }

    interp, eval_obs = build_missing_contact_blocks_recovery_v1(
        store_slug=slug,
        no_phone_total=int(no_phone_total),
        active_total=active_total,
    )
    evaluated += 1
    eval_rows.append(eval_obs)
    if interp is not None:
        generated += 1
        interpretations.append(interp)
        if interp.get("is_primary_commercial_blocker"):
            primary = interp
        elif primary is None:
            primary = interp
    elif eval_obs.get("suppressed"):
        suppressed += 1

    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    package = {
        "ok": True,
        "interpretation_version": INTERPRETATION_VERSION,
        "store_slug": slug,
        "generated_at": _utc_now_iso(),
        "primary": primary,
        "interpretations": interpretations,
        "used_last_valid": False,
        "observability": {
            "interpretations_evaluated": evaluated,
            "interpretations_generated": generated,
            "interpretations_suppressed": suppressed,
            "suppression_reasons": [
                r.get("suppression_reason")
                for r in eval_rows
                if r.get("suppression_reason")
            ],
            "evidence_count": int(no_phone_total),
            "confidence": (primary or {}).get("confidence_level"),
            "generation_duration_ms": duration_ms,
            "destination_routing": [DESTINATION_HOME, DESTINATION_KNOWLEDGE],
            "query_cost": int((resolve_meta or {}).get("query_cost") or 0),
            "failure_reason": None,
            "resolve": dict(resolve_meta or {}),
            "evaluations": eval_rows,
            "ai_used": False,
            "probabilistic": False,
        },
    }
    if primary is not None and slug:
        _LAST_VALID_BY_STORE[slug] = {
            "primary": dict(primary),
            "interpretations": [dict(x) for x in interpretations],
            "saved_at": package["generated_at"],
        }
    return package


def interpretation_to_home_understanding_item(
    interpretation: Mapping[str, Any],
) -> dict[str, Any]:
    """Map governed interpretation → Home ``store_understanding`` card fields."""
    kp = interpretation.get("knowledge_progression")
    if not isinstance(kp, Mapping):
        kp = {}
    count = int(interpretation.get("evidence_count") or 0)
    return {
        "title_ar": _norm(interpretation.get("home_headline_ar"))
        or _norm(interpretation.get("conclusion")),
        "observation_ar": _norm(kp.get("observation_ar"))
        or _norm(interpretation.get("conclusion")),
        "evidence_label_ar": _norm(interpretation.get("evidence_text")),
        "impact_ar": _norm(interpretation.get("home_impact_ar"))
        or _norm(interpretation.get("business_impact")),
        "action_ar": _norm(interpretation.get("home_merchant_action_ar"))
        or _norm(interpretation.get("merchant_action")),
        "cartflow_action_ar": _norm(interpretation.get("home_cartflow_action_ar"))
        or _norm(interpretation.get("cartflow_action")),
        "expected_result_ar": _norm(interpretation.get("expected_result")),
        "confidence": _norm(interpretation.get("confidence_level")) or CONFIDENCE_HIGH,
        "confidence_reason_ar": _norm(interpretation.get("confidence_reason")),
        "insight_key": INTERPRETATION_MISSING_CONTACT,
        "fact_key": f"fact:commercial_interpretation:{INTERPRETATION_MISSING_CONTACT}",
        "source_knowledge_id": f"cil:{INTERPRETATION_MISSING_CONTACT}",
        "section": "store_understanding",
        "evidence_count": count,
        "drilldown_href": _norm(interpretation.get("drilldown_target"))
        or DRILLDOWN_NOPHONE,
        "cta_label_ar": _norm(interpretation.get("cta_label_ar"))
        or CTA_AFFECTED_CARTS_AR,
        "commercial_interpretation_id": INTERPRETATION_MISSING_CONTACT,
        "is_primary_commercial_blocker": bool(
            interpretation.get("is_primary_commercial_blocker")
        ),
        "window_days": 0,
    }


def interpretation_to_knowledge_display_card(
    interpretation: Mapping[str, Any],
) -> dict[str, Any]:
    """Map governed interpretation → Knowledge Layer display card."""
    kp = interpretation.get("knowledge_progression")
    if not isinstance(kp, Mapping):
        kp = {}
    count = int(interpretation.get("evidence_count") or 0)
    return {
        "display_card_id": f"cil:{INTERPRETATION_MISSING_CONTACT}",
        "routing_knowledge_id": f"cil:{INTERPRETATION_MISSING_CONTACT}",
        "source_knowledge_id": f"cil:{INTERPRETATION_MISSING_CONTACT}",
        "routing_priority": 1000,
        "section": "attention",
        "insight_key": INTERPRETATION_MISSING_CONTACT,
        "category": "operational_health",
        "severity": "attention",
        "confidence": _norm(interpretation.get("confidence_level")) or CONFIDENCE_HIGH,
        "evidence_id": "canonical_no_phone_total",
        "evidence_label_ar": _norm(interpretation.get("evidence_text")),
        "title_ar": _norm(interpretation.get("conclusion")),
        "observation_ar": _norm(kp.get("observation_ar")),
        "impact_ar": _norm(kp.get("explanation_ar"))
        or _norm(interpretation.get("business_impact")),
        "action_ar": _norm(kp.get("recommendation_ar"))
        or _norm(interpretation.get("merchant_action")),
        "cartflow_action_ar": _norm(interpretation.get("cartflow_action")),
        "expected_result_ar": _norm(interpretation.get("expected_result")),
        "evidence_count": count,
        "drilldown_href": _norm(interpretation.get("drilldown_target"))
        or DRILLDOWN_NOPHONE,
        "cta_label_ar": _norm(interpretation.get("cta_label_ar"))
        or CTA_AFFECTED_CARTS_AR,
        "commercial_interpretation_id": INTERPRETATION_MISSING_CONTACT,
        "commercial_interpretation_v1": True,
        "traceability": {
            "evidence_source": EVIDENCE_SOURCE_NO_PHONE,
            "interpretation_id": INTERPRETATION_MISSING_CONTACT,
            "interpretation_version": INTERPRETATION_VERSION,
        },
    }


def interpretation_to_knowledge_insight(
    interpretation: Mapping[str, Any],
) -> dict[str, Any]:
    """Map governed interpretation → Knowledge insight row (deterministic)."""
    kp = interpretation.get("knowledge_progression")
    if not isinstance(kp, Mapping):
        kp = {}
    count = int(interpretation.get("evidence_count") or 0)
    return {
        "insight_key": INTERPRETATION_MISSING_CONTACT,
        "category": "operational_health",
        "severity": "attention",
        "title_ar": _norm(interpretation.get("conclusion")),
        "message_ar": _norm(kp.get("observation_ar"))
        or _norm(interpretation.get("conclusion")),
        "evidence": {
            "canonical_no_phone_count": count,
            "evidence_source": EVIDENCE_SOURCE_NO_PHONE,
        },
        "confidence": _norm(interpretation.get("confidence_level")) or CONFIDENCE_HIGH,
        "data_window": {"days": 0, "scope": "store_active_recovery"},
        "sample_size": count,
        "source_tables": ["abandoned_carts", "merchant_store_cart_counts"],
        "recommended_action_ar": _norm(kp.get("recommendation_ar"))
        or _norm(interpretation.get("merchant_action")),
        "evidence_id": "canonical_no_phone_total",
        "evidence_label_ar": _norm(interpretation.get("evidence_text")),
        "commercial_interpretation_id": INTERPRETATION_MISSING_CONTACT,
        "commercial_interpretation_v1": True,
    }


def evaluate_commercial_interpretations_v1(
    *,
    store_slug: str,
    no_phone_total: Optional[int] = None,
    active_total: Optional[int] = None,
    dash_store: Any = None,
    payload: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Public entry: resolve evidence (if needed) and build package."""
    resolve_meta: dict[str, Any] = {"query_cost": 0, "resolve_path": "caller"}
    count = no_phone_total
    if count is None:
        count, resolve_meta = resolve_canonical_no_phone_total(
            store_slug=store_slug,
            dash_store=dash_store,
            payload=payload,
        )
    try:
        return build_commercial_interpretation_package_v1(
            store_slug=store_slug,
            no_phone_total=count,
            active_total=active_total,
            resolve_meta=resolve_meta,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "commercial_interpretation_v1 package failed store=%s: %s",
            _norm(store_slug),
            exc,
        )
        return build_commercial_interpretation_package_v1(
            store_slug=store_slug,
            no_phone_total=count,
            active_total=active_total,
            resolve_meta=resolve_meta,
            generation_failed=True,
            failure_reason=type(exc).__name__,
        )


def apply_commercial_interpretation_to_home_v1(
    home: dict[str, Any],
    *,
    store_slug: str = "",
    no_phone_total: Optional[int] = None,
    active_total: Optional[int] = None,
    payload: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Attach governed package and promote primary interpretation into Understanding.

    Home must not rebuild conclusions — only consume the package.
    Failures never raise; Home continues loading.
    """
    if not isinstance(home, dict):
        return home
    slug = _norm(store_slug) or _norm(home.get("store_slug"))
    try:
        package = evaluate_commercial_interpretations_v1(
            store_slug=slug,
            no_phone_total=no_phone_total,
            active_total=active_total,
            payload=payload,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("commercial_interpretation_v1 home attach failed: %s", exc)
        home["commercial_interpretation_v1"] = build_commercial_interpretation_package_v1(
            store_slug=slug,
            no_phone_total=None,
            generation_failed=True,
            failure_reason=type(exc).__name__,
        )
        return home

    home["commercial_interpretation_v1"] = package
    primary = package.get("primary")
    if not isinstance(primary, Mapping):
        obs = home.get("observability")
        if isinstance(obs, dict):
            obs["commercial_interpretation_attached"] = True
            obs["commercial_interpretation_primary"] = False
        return home

    card = interpretation_to_home_understanding_item(primary)
    understanding = home.get("store_understanding")
    if not isinstance(understanding, dict):
        understanding = {}
        home["store_understanding"] = understanding
    items = list(understanding.get("items") or [])
    # Dedupe same commercial fact; keep interpretation primary.
    items = [
        it
        for it in items
        if isinstance(it, Mapping)
        and _norm(it.get("commercial_interpretation_id")) != INTERPRETATION_MISSING_CONTACT
        and _norm(it.get("insight_key")) != INTERPRETATION_MISSING_CONTACT
    ]
    understanding["items"] = [card] + items
    understanding["empty_message_ar"] = ""
    understanding["commercial_interpretation_primary"] = True

    # Align Attention CTAs with the same governed drilldown (presentation only).
    attention = home.get("attention_today")
    if isinstance(attention, Mapping):
        att_items = list(attention.get("items") or [])
        for att in att_items:
            if not isinstance(att, dict):
                continue
            op = _norm(att.get("operational_decision_key"))
            if op == "decision:obtain_contact" or "obtain_contact" in _norm_lower(
                att.get("action_key")
            ):
                att["drilldown_href"] = _norm(primary.get("drilldown_target")) or DRILLDOWN_NOPHONE
                if not _norm(att.get("cta_label_ar")):
                    att["cta_label_ar"] = CTA_AFFECTED_CARTS_AR
                # Prefer governed evidence count when Attention lacks a case count.
                if not int(att.get("decision_count") or 0):
                    att["decision_count"] = int(primary.get("evidence_count") or 0)
        if isinstance(attention, dict):
            attention["items"] = att_items

    obs = home.get("observability")
    if isinstance(obs, dict):
        obs["commercial_interpretation_attached"] = True
        obs["commercial_interpretation_primary"] = True
        obs["understanding_items"] = len(understanding["items"])
    home["empty_calm"] = False
    return home


def enrich_knowledge_report_commercial_interpretation_v1(
    payload: dict[str, Any],
    *,
    store_slug: str = "",
    dash_store: Any = None,
    no_phone_total: Optional[int] = None,
) -> None:
    """Attach the same governed interpretation to Knowledge report + projection."""
    if not isinstance(payload, dict):
        return
    slug = _norm(store_slug) or _norm(payload.get("store_slug"))
    try:
        package = evaluate_commercial_interpretations_v1(
            store_slug=slug,
            no_phone_total=no_phone_total,
            dash_store=dash_store,
            payload=payload,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("commercial_interpretation_v1 knowledge enrich failed: %s", exc)
        payload["commercial_interpretation_v1"] = build_commercial_interpretation_package_v1(
            store_slug=slug,
            no_phone_total=None,
            generation_failed=True,
            failure_reason=type(exc).__name__,
        )
        return

    payload["commercial_interpretation_v1"] = package
    primary = package.get("primary")
    if not isinstance(primary, Mapping):
        return

    insight = interpretation_to_knowledge_insight(primary)
    insights = payload.get("insights")
    if not isinstance(insights, list):
        insights = []
        payload["insights"] = insights
    insights = [
        row
        for row in insights
        if not (
            isinstance(row, Mapping)
            and _norm(row.get("insight_key")) == INTERPRETATION_MISSING_CONTACT
        )
    ]
    payload["insights"] = [insight] + insights

    card = interpretation_to_knowledge_display_card(primary)
    projection = payload.get("knowledge_layer_projection_v1")
    if not isinstance(projection, dict):
        projection = {
            "version": "v1",
            "surface": DESTINATION_KNOWLEDGE,
            "display_cards": [],
            "empty_reason": None,
            "observability": {},
        }
        payload["knowledge_layer_projection_v1"] = projection
    cards = [
        c
        for c in list(projection.get("display_cards") or [])
        if isinstance(c, Mapping)
        and _norm(c.get("insight_key")) != INTERPRETATION_MISSING_CONTACT
    ]
    projection["display_cards"] = [card] + cards
    projection["empty_reason"] = None
    obs = projection.get("observability")
    if isinstance(obs, dict):
        obs["display_card_count"] = len(projection["display_cards"])
        obs["commercial_interpretation_primary"] = True


def clear_commercial_interpretation_last_valid_cache_v1() -> None:
    """Test helper — clear per-store last-valid cache."""
    _LAST_VALID_BY_STORE.clear()


__all__ = [
    "CTA_AFFECTED_CARTS_AR",
    "DRILLDOWN_NOPHONE",
    "EVIDENCE_SOURCE_NO_PHONE",
    "INTERPRETATION_MISSING_CONTACT",
    "INTERPRETATION_VERSION",
    "apply_commercial_interpretation_to_home_v1",
    "build_commercial_interpretation_package_v1",
    "build_missing_contact_blocks_recovery_v1",
    "canonical_no_phone_count_from_payload",
    "clear_commercial_interpretation_last_valid_cache_v1",
    "enrich_knowledge_report_commercial_interpretation_v1",
    "evaluate_commercial_interpretations_v1",
    "interpretation_to_home_understanding_item",
    "interpretation_to_knowledge_display_card",
    "interpretation_to_knowledge_insight",
    "merchant_facing_text_is_clean",
    "resolve_canonical_no_phone_total",
]
