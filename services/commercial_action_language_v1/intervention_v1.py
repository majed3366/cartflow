# -*- coding: utf-8 -*-
"""
Commercial Intervention Intelligence V1 — merchant intervention governance.

Extension of Commercial Action Language. NOT a new runtime layer, lifecycle, or
ranker. Owns only the proven delta over ``contract_for_family_v1()``:

    why_this_is_safe_ar
    guardrail_metric
    mind_change_condition
    blocked_candidates

plus the derived governance metadata (recommendation_level, eligibility_state,
conflict_group). Fields already owned by ``contract_for_family_v1()`` are never
re-authored here; they are merged by ``compose_merchant_intervention_card_v1``.

Ownership consumed read-only, never overridden:
    COL        -> truth_class
    Catalog    -> role
    Portfolio  -> conflict_type
    CDC        -> phase

Pure and deterministic: no DB access, no AI, no external API, no scheduler work.
Every input arrives from the already-composed store bundle, so query delta is +0.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_PRODUCT,
    FAMILY_SHIPPING,
    FAMILY_WAIT,
    contract_for_family_v1,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
    resolve_measurement_window_days,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    SUPPORTED_FAMILIES,
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_READY,
)
from services.mission_catalog_v1.contract_v1 import (
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ROLE_SUPPRESSED,
)
from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_DUPLICATE_INTENT,
    CONFLICT_MEASUREMENT_CONTAMINATION,
    CONFLICT_MUTUALLY_EXCLUSIVE,
    CONFLICT_SAFE_TO_COEXIST,
)

LAYER_VERSION = "commercial_intervention_intelligence_v1"

# --- eligibility vocabulary (derived, never persisted) ----------------------
ELIGIBLE = "ELIGIBLE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
ECONOMIC_INPUTS_REQUIRED = "ECONOMIC_INPUTS_REQUIRED"
CONFLICTING_SIGNALS = "CONFLICTING_SIGNALS"
ALREADY_UNDER_MEASUREMENT = "ALREADY_UNDER_MEASUREMENT"
INTERVENTION_NOT_JUSTIFIED = "INTERVENTION_NOT_JUSTIFIED"
WAIT_AND_RECHECK = "WAIT_AND_RECHECK"

ELIGIBILITY_STATES = frozenset(
    {
        ELIGIBLE,
        INSUFFICIENT_EVIDENCE,
        ECONOMIC_INPUTS_REQUIRED,
        CONFLICTING_SIGNALS,
        ALREADY_UNDER_MEASUREMENT,
        INTERVENTION_NOT_JUSTIFIED,
        WAIT_AND_RECHECK,
    }
)

# Portfolio verdict -> meaning. CAPACITY_ONLY is a defer, not a rejection: the
# intervention is justified, the store is busy. Only duplicate intent is
# genuinely unjustified.
_BLOCKING_CONFLICTS = frozenset(
    {CONFLICT_MUTUALLY_EXCLUSIVE, CONFLICT_MEASUREMENT_CONTAMINATION}
)
_NOT_JUSTIFIED_CONFLICTS = frozenset({CONFLICT_DUPLICATE_INTENT})
_SAFE_CONFLICTS = frozenset({CONFLICT_SAFE_TO_COEXIST})
_OWN_COMMITTED_PHASES = frozenset({PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT})

# --- families ---------------------------------------------------------------
FAMILY_COMPLEMENTARY = "product_opportunity_focus"  # merchant term: منتجات مكملة

FAMILY_MAX_LEVEL: dict[str, int] = {
    FAMILY_SHIPPING: 3,
    FAMILY_PRICE: 3,
    FAMILY_PRODUCT: 2,
    FAMILY_COMPLEMENTARY: 4,
    FAMILY_WAIT: 0,
}

# --- economic input manifest (static registry; no acquisition implemented) ---
ECONOMIC_INPUT_FIELDS = (
    "shipping_cost",
    "shipping_subsidy",
    "product_cost",
    "gross_margin",
    "margin_floor",
    "payment_fees",
    "platform_commission",
    "inventory_quantity",
    "shipping_impact",
    "compatibility_evidence",
    "AOV",
    "product_pair_counts",
)

_L3_CORE = (
    "product_cost",
    "gross_margin",
    "margin_floor",
    "payment_fees",
    "platform_commission",
    "AOV",
)

# Levels not listed are undefined for the family. Undefined levels block the
# ladder, which is what keeps complementary products at 1 even with complete
# economics: naming a product can never be reached by acquiring money facts.
LEVEL_REQUIREMENTS: dict[str, dict[int, tuple[str, ...]]] = {
    FAMILY_SHIPPING: {0: (), 1: (), 2: (), 3: ("shipping_cost", "shipping_subsidy") + _L3_CORE},
    FAMILY_PRICE: {0: (), 1: (), 2: (), 3: _L3_CORE},
    FAMILY_PRODUCT: {0: (), 1: (), 2: ()},
    FAMILY_COMPLEMENTARY: {
        0: (),
        1: (),
        4: ("product_pair_counts", "inventory_quantity", "product_cost", "gross_margin",
            "margin_floor", "shipping_impact", "compatibility_evidence"),
    },
    FAMILY_WAIT: {0: ()},
}

LEVEL_NOT_DEFINED = "__level_not_defined_for_family__"


def economic_manifest_v1(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Static manifest. Every field is missing until an authority is registered.

    No database read, no default value. A missing input blocks a level; it never
    degrades into an estimate.
    """
    manifest: dict[str, Any] = {field: None for field in ECONOMIC_INPUT_FIELDS}
    if isinstance(overrides, Mapping):
        for key, value in overrides.items():
            if key in manifest:
                manifest[key] = value
    return manifest


def missing_economic_inputs_v1(
    family: str, level: int, manifest: Mapping[str, Any] | None = None
) -> list[str]:
    m = manifest if isinstance(manifest, Mapping) else economic_manifest_v1()
    required = LEVEL_REQUIREMENTS.get(str(family or ""), {}).get(int(level), None)
    if required is None:
        return [LEVEL_NOT_DEFINED]
    return [field for field in required if not m.get(field)]


def level_supported_by_inputs_v1(
    family: str, manifest: Mapping[str, Any] | None = None
) -> int:
    """Highest contiguous level whose inputs are all present. No level skipping."""
    best = 0
    for level in sorted(LEVEL_REQUIREMENTS.get(str(family or ""), {})):
        if level == 0:
            continue
        if level > best + 1:
            break
        if missing_economic_inputs_v1(family, level, manifest):
            break
        best = level
    return best


def effective_level_v1(family: str, manifest: Mapping[str, Any] | None = None) -> int:
    return min(
        FAMILY_MAX_LEVEL.get(str(family or ""), 0),
        level_supported_by_inputs_v1(family, manifest),
    )


def derive_eligibility_v1(
    *,
    col_truth_class: str | None,
    own_cdc_phase: str | None,
    portfolio_conflict_type: str | None,
    catalog_role: str | None,
    family: str,
    requested_level: int,
    missing_inputs: Sequence[str] | None = None,
) -> str:
    """Derived projection over existing owners. Never persisted.

    First-match-wins. ``ELIGIBLE`` requires positive recognition of every input,
    so any unknown token falls through to ``WAIT_AND_RECHECK``.
    """
    missing = list(missing_inputs or [])

    if col_truth_class == TRUTH_INSUFFICIENT or col_truth_class is None:
        return INSUFFICIENT_EVIDENCE
    if own_cdc_phase in _OWN_COMMITTED_PHASES:
        return ALREADY_UNDER_MEASUREMENT
    if portfolio_conflict_type in _BLOCKING_CONFLICTS:
        return CONFLICTING_SIGNALS
    if catalog_role == ROLE_SUPPRESSED or portfolio_conflict_type in _NOT_JUSTIFIED_CONFLICTS:
        return INTERVENTION_NOT_JUSTIFIED
    if int(requested_level) >= 3 and missing:
        return ECONOMIC_INPUTS_REQUIRED

    recognized = (
        col_truth_class == TRUTH_PRODUCTION_READY
        and (family in SUPPORTED_FAMILIES or family == FAMILY_WAIT)
        and catalog_role in (ROLE_PRIMARY, ROLE_SECONDARY)
        and portfolio_conflict_type in _SAFE_CONFLICTS
        and own_cdc_phase in (None, PHASE_RECHECK_DUE)
        and not missing
    )
    return ELIGIBLE if recognized else WAIT_AND_RECHECK


# --- merchant copy owned by this extension only -----------------------------
WHY_SAFE_AR: dict[str, str] = {
    FAMILY_SHIPPING: (
        "هذا التدخل يوضّح المعلومة للعميل فقط — لا يغيّر سعرك ولا تكلفة الشحن التي تتحملها."
    ),
    FAMILY_PRICE: (
        "هذا التدخل يوضّح ما يحصل عليه العميل مقابل السعر الحالي — لا يغيّر سعرك ولا يمنح خصماً."
    ),
    FAMILY_PRODUCT: (
        "هذا التدخل يعرض ما هو قائم عندك فعلاً — لا يغيّر سعراً ولا يختلق إثباتاً جديداً."
    ),
    FAMILY_COMPLEMENTARY: (
        "هذه ملاحظة فرصة فقط — لا تسمّي منتجاً ولا تغيّر سعراً ولا عرضاً."
    ),
    FAMILY_WAIT: (
        "الانتظار هنا قرار — التوصية على عيّنة غير كافية توجّه متجرك في الاتجاه الخطأ."
    ),
}

MIND_CHANGE_AR: dict[str, str] = {
    FAMILY_SHIPPING: "انتقال التردد الأقوى إلى عائلة أخرى، أو اتضاح أن السبب هو المدة لا التكلفة.",
    FAMILY_PRICE: (
        "بقاء حصة السعر مرتفعة بعد توضيح القيمة — عندها تصبح الأولوية جلب الحقائق الاقتصادية "
        "لا إطلاق خصم."
    ),
    FAMILY_PRODUCT: "انتقال التردد إلى السعر أو الشحن بعد عرض إثبات الجودة أو الضمان.",
    FAMILY_COMPLEMENTARY: "ظهور أدلة اقتران منتجات كافية مع مخزون واقتصاديات موثوقة.",
    FAMILY_WAIT: "ظهور سبب مهيمن واحد ضمن حد الكفاية المعتمد.",
}

GUARDRAIL_METRIC_AR = "لا تراجع في تحوّل السلة إلى شراء"

# Level 1 generic copy for complementary products. contract_for_family_v1 covers
# only the four governed decision kinds, so this family has no base contract yet.
COMPLEMENTARY_SITUATION_AR = "قد توجد فرصة لرفع قيمة السلة عبر منتج مكمل."
COMPLEMENTARY_ACTION_AR = (
    "قد توجد فرصة لرفع قيمة السلة عبر منتج مكمل — دون تسمية منتج محدد بعد."
)
COMPLEMENTARY_DONT_AR = (
    "لا تقترح منتجاً مكملاً بالاسم قبل توفر أدلة الاقتران والمخزون واقتصاديات المنتج."
)
COMPLEMENTARY_MEASURE_AR = "حصة السلال التي تحتوي أكثر من منتج."
COMPLEMENTARY_RECHECK_AR = "عند توفر أدلة اقتران منتجات كافية مع مخزون واقتصاديات موثوقة."

CONFLICT_GROUP_DISCLOSURE = "disclosure_only"
CONFLICT_GROUP_CONFIDENCE_CONTENT = "product_confidence_content"
CONFLICT_GROUP_OPPORTUNITY_NOTE = "opportunity_note_only"

_CONFLICT_GROUPS: dict[str, str] = {
    FAMILY_SHIPPING: CONFLICT_GROUP_DISCLOSURE,
    FAMILY_PRICE: CONFLICT_GROUP_DISCLOSURE,
    FAMILY_PRODUCT: CONFLICT_GROUP_CONFIDENCE_CONTENT,
    FAMILY_COMPLEMENTARY: CONFLICT_GROUP_OPPORTUNITY_NOTE,
}

NO_STRONGER_LEVEL_DEFINED = "NO_STRONGER_LEVEL_DEFINED"

_BLOCKED_TEMPLATES: dict[str, dict[str, Any]] = {
    FAMILY_SHIPPING: {
        "level": 3,
        "class_ar": "شحن مجاني / دعم الشحن / حد شحن مجاني",
        "merchant_ar": (
            "لا نقترح شحناً مجانياً ولا دعماً للشحن ولا حداً للشحن، لأننا لا نعرف تكلفة الشحن "
            "التي تتحملها ولا هامشك — لا نستطيع إثبات أن التدخل لن يخسّرك."
        ),
    },
    FAMILY_PRICE: {
        "level": 3,
        "class_ar": "خصم مباشر / تخفيض سعر / سعر حزمة",
        "merchant_ar": (
            "لا نقترح خصماً ولا تخفيض سعر، لأننا لا نعرف تكلفة المنتج ولا هامشك ولا حدّك "
            "الأدنى المقبول للربح."
        ),
    },
    FAMILY_COMPLEMENTARY: {
        "level": 4,
        "class_ar": "اقتراح منتج مكمل محدد بالاسم",
        "merchant_ar": (
            "لا نسمّي منتجاً مكملاً محدداً، لأن أدلة اقتران المنتجات وكمية المخزون "
            "واقتصاديات المنتج غير متوفرة."
        ),
    },
}

# Blocked cards explain; they never instruct.
DEFERRAL_AR: dict[str, str] = {
    CONFLICTING_SIGNALS: (
        "مؤجّل الآن: لديك مهمة نشطة قد يفسد قياسها هذا التدخل. ما ننتظره هو إغلاق المهمة الحالية."
    ),
    ALREADY_UNDER_MEASUREMENT: (
        "قيد القياس بالفعل: لا تبدأ تدخلاً موازياً على نفس الفرصة. ما ننتظره هو نتيجة نافذة القياس."
    ),
    INTERVENTION_NOT_JUSTIFIED: (
        "لا نقترح هذا الآن: نفس النية مغطاة بمهمة قائمة."
    ),
    ECONOMIC_INPUTS_REQUIRED: (
        "لا نقترح هذا الآن: الحقائق الاقتصادية المطلوبة غير متوفرة. ما ننتظره هو تسجيلها بمصدر موثوق."
    ),
    INSUFFICIENT_EVIDENCE: (
        "لا نقترح تدخلاً الآن: العيّنة لا تكفي لتحديد السبب. ما ننتظره هو أسباب تردد إضافية."
    ),
    WAIT_AND_RECHECK: (
        "ننتظر الآن: سنعيد التقييم عند اكتمال الصورة أو انتهاء المهمة الحالية."
    ),
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _blocked_candidates(
    *,
    family: str,
    level: int,
    state: str,
    manifest: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Section 4 is never empty: a blocked stronger candidate, or why none exists."""
    if state == INSUFFICIENT_EVIDENCE:
        return [
            {
                "level": 2,
                "class_ar": "أي تدخل تجاري",
                "blocked_reason": INSUFFICIENT_EVIDENCE,
                "missing_inputs": [],
                "merchant_ar": "لا نقترح تدخلاً الآن لأن العيّنة لا تكفي لتحديد السبب.",
            }
        ]
    template = _BLOCKED_TEMPLATES.get(family)
    if template and level < int(template["level"]):
        return [
            {
                "level": int(template["level"]),
                "class_ar": template["class_ar"],
                "blocked_reason": ECONOMIC_INPUTS_REQUIRED,
                "missing_inputs": missing_economic_inputs_v1(
                    family, int(template["level"]), manifest
                ),
                "merchant_ar": template["merchant_ar"],
            }
        ]
    return [
        {
            "level": None,
            "class_ar": "لا يوجد تدخل أقوى معرّف لهذه العائلة",
            "blocked_reason": NO_STRONGER_LEVEL_DEFINED,
            "missing_inputs": [],
            "merchant_ar": (
                "لا يوجد مستوى أقوى معرّف لهذه العائلة — الخطوة التالية هي القياس لا التصعيد."
            ),
        }
    ]


def intervention_contract_v1(
    *,
    family: str,
    col_truth_class: str | None,
    catalog_role: str | None,
    portfolio_conflict_type: str | None,
    own_cdc_phase: str | None = None,
    manifest: Mapping[str, Any] | None = None,
    requested_level: int | None = None,
) -> dict[str, Any]:
    """Governance + the four delta fields. Does not restate the base contract."""
    fam = str(family or "")
    level = effective_level_v1(fam, manifest)
    missing = missing_economic_inputs_v1(fam, level, manifest)
    state = derive_eligibility_v1(
        col_truth_class=col_truth_class,
        own_cdc_phase=own_cdc_phase,
        portfolio_conflict_type=portfolio_conflict_type,
        catalog_role=catalog_role,
        family=fam,
        requested_level=level,
        missing_inputs=missing,
    )

    requested_candidate = None
    if requested_level is not None and int(requested_level) > level:
        requested_missing = missing_economic_inputs_v1(fam, int(requested_level), manifest)
        requested_candidate = {
            "level": int(requested_level),
            "eligibility_state": derive_eligibility_v1(
                col_truth_class=col_truth_class,
                own_cdc_phase=own_cdc_phase,
                portfolio_conflict_type=portfolio_conflict_type,
                catalog_role=catalog_role,
                family=fam,
                requested_level=int(requested_level),
                missing_inputs=requested_missing,
            ),
            "missing_inputs": requested_missing,
            "offered_level_instead": level,
        }

    return {
        "layer_version": LAYER_VERSION,
        "intervention_id": f"civ1:{fam}:{level}:{'hold' if level == 0 else 'act'}",
        "family": fam,
        "recommendation_level": level,
        "eligibility_state": state,
        "conflict_group": _CONFLICT_GROUPS.get(fam),
        # --- the four proven delta fields ---
        "why_this_is_safe_ar": WHY_SAFE_AR.get(fam, ""),
        "guardrail_metric": GUARDRAIL_METRIC_AR if level >= 2 else None,
        "mind_change_condition": MIND_CHANGE_AR.get(fam, ""),
        "blocked_candidates": _blocked_candidates(
            family=fam, level=level, state=state, manifest=manifest
        ),
        # --- governance metadata ---
        "required_economic_inputs": list(LEVEL_REQUIREMENTS.get(fam, {}).get(level, ())),
        "missing_inputs": missing,
        "requested_candidate": requested_candidate,
        "measurement_window_days": resolve_measurement_window_days(fam),
        "cta_allowed": state == ELIGIBLE,
        "economic_inputs_state": "none_required" if not missing else f"missing:{len(missing)}",
    }


def compose_merchant_intervention_card_v1(
    *,
    family: str,
    intervention: Mapping[str, Any],
    evidence: Mapping[str, Any] | None = None,
    reason_label_ar: str = "",
) -> dict[str, Any]:
    """Merge the base CAL contract with the intervention delta into 8 sections.

    The base contract remains the sole author of situation/evidence/action/dont/
    measure/recheck. This function only merges, gates the CTA, and converts a
    blocked card's instruction into explanatory defer language.
    """
    fam = str(family or "")
    state = str(intervention.get("eligibility_state") or "")
    base = contract_for_family_v1(fam, evidence=evidence, reason_label_ar=reason_label_ar)

    if base:
        what_we_see = _norm(f"{base.get('situation_ar', '')} {base.get('evidence_ar', '')}")
        suggest = _norm(base.get("action_ar"))
        dont = _norm(base.get("dont_ar"))
        measure = _norm(base.get("measure_ar"))
        recheck = _norm(base.get("recheck_ar"))
    elif fam == FAMILY_COMPLEMENTARY:
        what_we_see = COMPLEMENTARY_SITUATION_AR
        suggest = COMPLEMENTARY_ACTION_AR
        dont = COMPLEMENTARY_DONT_AR
        measure = COMPLEMENTARY_MEASURE_AR
        recheck = COMPLEMENTARY_RECHECK_AR
    else:
        return {}

    if state != ELIGIBLE:
        suggest = _norm(f"{DEFERRAL_AR.get(state, DEFERRAL_AR[WAIT_AND_RECHECK])} {suggest}")

    return {
        "intervention_id": intervention.get("intervention_id"),
        "family": fam,
        "recommendation_level": intervention.get("recommendation_level"),
        "eligibility_state": state,
        "conflict_group": intervention.get("conflict_group"),
        "what_we_see_ar": what_we_see,
        "what_we_suggest_ar": suggest,
        "why_this_is_safe_ar": intervention.get("why_this_is_safe_ar"),
        "blocked_candidates": list(intervention.get("blocked_candidates") or []),
        "dont_do_ar": dont,
        "primary_metric": measure,
        "guardrail_metric": intervention.get("guardrail_metric"),
        "recheck_condition": recheck,
        "mind_change_condition": intervention.get("mind_change_condition"),
        "measurement_window_days": intervention.get("measurement_window_days"),
        # Hard CTA invariant: executable CTA only on an ELIGIBLE card.
        "cta_ar": CTA_ACCEPT_MISSION_AR if state == ELIGIBLE else None,
    }


# --- validation -------------------------------------------------------------
ERROR_CTA_ON_BLOCKED_CARD = "cta_on_blocked_card"
ERROR_LEVEL_JUMP = "level_jump"

# Economic-lever markers that must never appear as an instruction below Level 3.
_ECONOMIC_LEVER_MARKERS = (
    "خصم", "خفّض", "خفض", "شحن مجاني", "مجانًا", "مجانا", "مجاني",
    "ر.س", "٪", "%", "حد أدنى", "دعم الشحن",
)
_NEGATORS = ("لا ", "لا،", "بدون", "دون ", "ليس", "لن ", "قبل أي", "غير ")


def unnegated_economic_markers_v1(text: Any) -> list[str]:
    """Forbidden markers used as an instruction, ignoring negated guardrails."""
    raw = str(text or "")
    hits: list[str] = []
    for marker in _ECONOMIC_LEVER_MARKERS:
        start = 0
        while True:
            index = raw.find(marker, start)
            if index < 0:
                break
            window = raw[max(0, index - 40): index]
            if not any(neg in window for neg in _NEGATORS):
                hits.append(marker)
            start = index + len(marker)
    return hits


def validate_intervention_card_v1(card: Mapping[str, Any] | None) -> list[str]:
    """Fail-closed structural validation of a composed merchant card."""
    if not isinstance(card, Mapping):
        return ["not_a_mapping"]
    errors: list[str] = []

    state = card.get("eligibility_state")
    if state not in ELIGIBILITY_STATES:
        errors.append("unknown_eligibility_state")

    family = str(card.get("family") or "")
    if family not in SUPPORTED_FAMILIES and family != FAMILY_WAIT:
        errors.append("unsupported_family")

    level = card.get("recommendation_level")
    if not isinstance(level, int) or not 0 <= level <= 4:
        errors.append("bad_level")
    elif level > FAMILY_MAX_LEVEL.get(family, 0):
        errors.append(ERROR_LEVEL_JUMP)

    intervention_id = str(card.get("intervention_id") or "")
    if not intervention_id.startswith("civ1:") or intervention_id.count(":") != 3:
        errors.append("unknown_intervention_id")

    blocked = card.get("blocked_candidates")
    if not isinstance(blocked, list) or not blocked:
        errors.append("missing_blocked_candidates")
    else:
        for candidate in blocked:
            if not isinstance(candidate, Mapping) or not {
                "level",
                "blocked_reason",
                "missing_inputs",
            } <= set(candidate):
                errors.append("malformed_blocked_candidate")

    if isinstance(level, int) and level >= 2:
        if not card.get("guardrail_metric"):
            errors.append("missing_guardrail_metric")
        if not _norm(card.get("mind_change_condition")):
            errors.append("missing_mind_change_condition")

    if isinstance(level, int) and level <= 2:
        hits = unnegated_economic_markers_v1(card.get("what_we_suggest_ar"))
        hits += unnegated_economic_markers_v1(card.get("why_this_is_safe_ar"))
        if hits:
            errors.append(f"level2_invariant_violation:{sorted(set(hits))}")

    if card.get("cta_ar") and state != ELIGIBLE:
        errors.append(ERROR_CTA_ON_BLOCKED_CARD)

    return errors


__all__ = [
    "ALREADY_UNDER_MEASUREMENT",
    "COMPLEMENTARY_ACTION_AR",
    "CONFLICTING_SIGNALS",
    "CONFLICT_GROUP_CONFIDENCE_CONTENT",
    "CONFLICT_GROUP_DISCLOSURE",
    "CONFLICT_GROUP_OPPORTUNITY_NOTE",
    "DEFERRAL_AR",
    "ECONOMIC_INPUTS_REQUIRED",
    "ECONOMIC_INPUT_FIELDS",
    "ELIGIBILITY_STATES",
    "ELIGIBLE",
    "ERROR_CTA_ON_BLOCKED_CARD",
    "ERROR_LEVEL_JUMP",
    "FAMILY_COMPLEMENTARY",
    "FAMILY_MAX_LEVEL",
    "GUARDRAIL_METRIC_AR",
    "INSUFFICIENT_EVIDENCE",
    "INTERVENTION_NOT_JUSTIFIED",
    "LAYER_VERSION",
    "LEVEL_NOT_DEFINED",
    "LEVEL_REQUIREMENTS",
    "MIND_CHANGE_AR",
    "NO_STRONGER_LEVEL_DEFINED",
    "WAIT_AND_RECHECK",
    "WHY_SAFE_AR",
    "compose_merchant_intervention_card_v1",
    "derive_eligibility_v1",
    "economic_manifest_v1",
    "effective_level_v1",
    "intervention_contract_v1",
    "level_supported_by_inputs_v1",
    "missing_economic_inputs_v1",
    "unnegated_economic_markers_v1",
    "validate_intervention_card_v1",
]
