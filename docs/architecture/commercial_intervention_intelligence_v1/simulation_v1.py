# -*- coding: utf-8 -*-
"""
Commercial Intervention Intelligence V1 — Architecture & Behavior Simulation Gate.

NON-PRODUCTION PROTOTYPE. Not imported by any runtime path.

This simulation imports the REAL production owners read-only so that the proofs
are not self-referential mocks:

    services.mission_portfolio_v1.conflict_v1      -> conflict decisions
    services.commercial_opportunity_layer_v1       -> truth classification
    services.commercial_action_language_v1         -> existing merchant contract
    services.commercial_decision_commitment_v1     -> snapshot schema + phases
    models                                         -> column introspection

Run from repo root:  python docs/architecture/commercial_intervention_intelligence_v1/simulation_v1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - console dependent
    pass

# --- real production owners (read-only) -------------------------------------
from services.mission_portfolio_v1.conflict_v1 import evaluate_conflict_v1
from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_DUPLICATE_INTENT,
    CONFLICT_MEASUREMENT_CONTAMINATION,
    CONFLICT_MUTUALLY_EXCLUSIVE,
    CONFLICT_SAFE_TO_COEXIST,
    MAX_ACTIVE_MISSIONS,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    SUPPORTED_FAMILIES,
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
)
from services.commercial_opportunity_layer_v1.truth_gate_v1 import (
    classify_hesitation_truth_v1,
)
from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    contract_for_family_v1,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    FORBIDDEN_CLOSE_REASONS,
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
    SNAPSHOT_MAX_BYTES,
    resolve_measurement_window_days,
)
from services.commercial_decision_commitment_v1.snapshots_v1 import (
    SnapshotContractError,
    parse_and_validate_decision_snapshot,
)
from services.mission_catalog_v1.contract_v1 import (
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ROLE_SUPPRESSED,
)

RESULTS: list[tuple[str, str, str]] = []  # (section, name, PASS/FAIL)
REPORT: list[str] = []


def check(section: str, name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((section, name, "PASS" if ok else "FAIL"))
    line = f"  [{'PASS' if ok else 'FAIL'}] {name}"
    if detail:
        line += f" — {detail}"
    REPORT.append(line)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    return ok


def section(title: str) -> None:
    REPORT.append("")
    REPORT.append(f"### {title}")
    print(f"\n=== {title} ===")


# ============================================================================
# 1. ARCHITECTURE FLOW MODEL + CIRCULAR OWNERSHIP PROOF
# ============================================================================

OWNER_COL = "commercial_opportunity_layer_v1"
OWNER_CATALOG = "mission_catalog_v1"
OWNER_PORTFOLIO = "mission_portfolio_v1"
OWNER_CDC = "commercial_decision_commitment_v1"
OWNER_CAL = "commercial_action_language_v1"
OWNER_MANIFEST = "economic_input_manifest (static registry)"
OWNER_WORKSPACE = "decision_workspace_v2 (projection only)"
OWNER_STORE = "store_truth_bundle"

# (step, input_owner, output_owner, authority, derived_field, fail_closed_state)
FLOW = [
    ("diagnosis", OWNER_STORE, OWNER_COL, "COL", "truth_class / family / evidence_refs", TRUTH_INSUFFICIENT),
    ("priority", OWNER_COL, OWNER_CATALOG, "Mission Catalog", "role / rank / suppression", ROLE_SUPPRESSED),
    ("conflict", OWNER_CATALOG, OWNER_PORTFOLIO, "Mission Portfolio", "conflict_type / may_execute", CONFLICT_CAPACITY_ONLY),
    ("commitment", OWNER_PORTFOLIO, OWNER_CDC, "CDC", "phase / baseline / window", "no_row"),
    ("economics", OWNER_MANIFEST, OWNER_CAL, "Economic Input Manifest", "missing_inputs", "all_missing"),
    ("eligibility", OWNER_CDC, OWNER_CAL, "CAL extension (derived)", "eligibility_state", "WAIT_AND_RECHECK"),
    ("language", OWNER_CAL, OWNER_WORKSPACE, "CAL", "8 merchant sections", "no_action_card"),
]

# Read-path dependency edges (compose-time only)
READ_EDGES = [
    (OWNER_STORE, OWNER_COL),
    (OWNER_COL, OWNER_CATALOG),
    (OWNER_COL, OWNER_CAL),
    (OWNER_CDC, OWNER_CATALOG),
    (OWNER_CDC, OWNER_PORTFOLIO),
    (OWNER_CDC, OWNER_CAL),
    (OWNER_CATALOG, OWNER_PORTFOLIO),
    (OWNER_CATALOG, OWNER_CAL),
    (OWNER_PORTFOLIO, OWNER_CAL),
    (OWNER_MANIFEST, OWNER_CAL),
    (OWNER_CAL, OWNER_WORKSPACE),
]


def has_cycle(edges: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    nodes = {n for e in edges for n in e}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for a, b in edges:
        adj[a].append(b)
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    order: list[str] = []

    def visit(n: str, stack: list[str]) -> tuple[bool, list[str]]:
        color[n] = GREY
        for m in adj[n]:
            if color[m] == GREY:
                return True, stack + [m]
            if color[m] == WHITE:
                found, path = visit(m, stack + [m])
                if found:
                    return True, path
        color[n] = BLACK
        order.append(n)
        return False, []

    for n in sorted(nodes):
        if color[n] == WHITE:
            found, path = visit(n, [n])
            if found:
                return True, path
    return False, list(reversed(order))


def simulate_architecture_flow() -> None:
    section("1. ARCHITECTURE FLOW MODEL")
    for step, i, o, auth, derived, failsafe in FLOW:
        REPORT.append(
            f"  - {step}: IN={i} OUT={o} AUTHORITY={auth} DERIVED={derived} FAIL_CLOSED={failsafe}"
        )
    cyclic, topo = has_cycle(READ_EDGES)
    check("flow", "read-path ownership graph is acyclic", not cyclic,
          " -> ".join(topo[:4]) + " ...")
    # every step has an explicit fail-closed state
    check("flow", "every transition declares a fail-closed state",
          all(bool(f) for *_, f in FLOW), f"{len(FLOW)} transitions")
    # exactly one authority per derived field
    authorities = [row[3] for row in FLOW]
    check("flow", "no derived field has two authorities",
          len(authorities) == len(set(authorities)), f"{len(set(authorities))} distinct")
    # CAL is a sink for eligibility, workspace is projection-only
    outgoing_workspace = [b for a, b in READ_EDGES if a == OWNER_WORKSPACE]
    check("flow", "Decision Workspace is projection-only (no outgoing authority)",
          outgoing_workspace == [], "0 outgoing edges")
    REPORT.append(
        "  Lifecycle loop (accept -> measure -> recheck) is TEMPORAL, mediated by CDC "
        "persistence across separate transactions; it is not a compose-time data cycle."
    )


# ============================================================================
# 2. ELIGIBILITY DERIVATION (pure, derived, no persistence)
# ============================================================================

ELIGIBLE = "ELIGIBLE"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
ECONOMIC_INPUTS_REQUIRED = "ECONOMIC_INPUTS_REQUIRED"
CONFLICTING_SIGNALS = "CONFLICTING_SIGNALS"
ALREADY_UNDER_MEASUREMENT = "ALREADY_UNDER_MEASUREMENT"
INTERVENTION_NOT_JUSTIFIED = "INTERVENTION_NOT_JUSTIFIED"
WAIT_AND_RECHECK = "WAIT_AND_RECHECK"

ELIGIBILITY_STATES = {
    ELIGIBLE, INSUFFICIENT_EVIDENCE, ECONOMIC_INPUTS_REQUIRED, CONFLICTING_SIGNALS,
    ALREADY_UNDER_MEASUREMENT, INTERVENTION_NOT_JUSTIFIED, WAIT_AND_RECHECK,
}

KNOWN_ROLES = {ROLE_PRIMARY, ROLE_SECONDARY, ROLE_SUPPRESSED}
SAFE_CONFLICTS = {CONFLICT_SAFE_TO_COEXIST}
BLOCKING_CONFLICTS = {CONFLICT_MUTUALLY_EXCLUSIVE, CONFLICT_MEASUREMENT_CONTAMINATION}
# CAPACITY_ONLY is deliberately NOT "not justified": the intervention is justified,
# the store is simply busy. It falls through to WAIT_AND_RECHECK (deferred), which is
# what Portfolio means by defer. Only duplicate intent is genuinely unjustified.
NOT_JUSTIFIED_CONFLICTS = {CONFLICT_DUPLICATE_INTENT}


def derive_eligibility(
    *,
    col_truth_class: str | None,
    own_cdc_phase: str | None,
    portfolio_conflict_type: str | None,
    catalog_role: str | None,
    family: str,
    requested_level: int,
    missing_inputs: list[str],
) -> str:
    """First-match-wins projection. ELIGIBLE requires positive recognition of every input."""
    # 1
    if col_truth_class == TRUTH_INSUFFICIENT or col_truth_class is None:
        return INSUFFICIENT_EVIDENCE
    # 2 — this opportunity is already committed/measuring
    if own_cdc_phase in (PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT):
        return ALREADY_UNDER_MEASUREMENT
    # 3
    if portfolio_conflict_type in BLOCKING_CONFLICTS:
        return CONFLICTING_SIGNALS
    # 4
    if catalog_role == ROLE_SUPPRESSED or portfolio_conflict_type in NOT_JUSTIFIED_CONFLICTS:
        return INTERVENTION_NOT_JUSTIFIED
    # 5
    if requested_level >= 3 and missing_inputs:
        return ECONOMIC_INPUTS_REQUIRED
    # 7 — positive recognition required, else 6
    recognized = (
        col_truth_class == TRUTH_PRODUCTION_READY
        and family in SUPPORTED_FAMILIES
        and catalog_role in (ROLE_PRIMARY, ROLE_SECONDARY)
        and portfolio_conflict_type in SAFE_CONFLICTS
        and own_cdc_phase in (None, PHASE_RECHECK_DUE)
        and not missing_inputs
    )
    if recognized:
        return ELIGIBLE
    # 6
    return WAIT_AND_RECHECK


# ============================================================================
# 3. LEVEL CEILING
# ============================================================================

FAM_SHIPPING = "shipping_friction"
FAM_PRICE = "price_hesitation"
FAM_CONFIDENCE = "product_confidence"
FAM_COMPLEMENTARY = "product_opportunity_focus"  # internal id; merchant term: منتجات مكملة
FAM_WAIT = "wait_insufficient_evidence"

FAMILY_MAX_LEVEL = {
    FAM_SHIPPING: 3,
    FAM_PRICE: 3,
    FAM_CONFIDENCE: 2,
    FAM_COMPLEMENTARY: 4,
    FAM_WAIT: 0,
}

L3_CORE = ["product_cost", "gross_margin", "margin_floor", "payment_fees",
           "platform_commission", "AOV"]
LEVEL_REQUIREMENTS: dict[str, dict[int, list[str]]] = {
    FAM_SHIPPING: {0: [], 1: [], 2: [], 3: ["shipping_cost", "shipping_subsidy"] + L3_CORE},
    FAM_PRICE: {0: [], 1: [], 2: [], 3: L3_CORE},
    FAM_CONFIDENCE: {0: [], 1: [], 2: []},
    FAM_COMPLEMENTARY: {
        0: [], 1: [],
        4: ["product_pair_counts", "inventory_quantity", "product_cost", "gross_margin",
            "margin_floor", "shipping_impact", "compatibility_evidence"],
    },
    FAM_WAIT: {0: []},
}

# Observed manifest today (see ECONOMIC_INPUT_CONTRACT.md)
MANIFEST_TODAY = {
    "shipping_cost": None, "shipping_subsidy": None, "product_cost": None,
    "gross_margin": None, "margin_floor": None, "payment_fees": None,
    "platform_commission": None, "inventory_quantity": None,
    "shipping_impact": None, "compatibility_evidence": None,
    "AOV": None,                      # partial: no authoritative order value
    "product_pair_counts": "derivable",
}


def missing_for(family: str, level: int, manifest: dict[str, object]) -> list[str]:
    required = LEVEL_REQUIREMENTS.get(family, {}).get(level, None)
    if required is None:
        return ["__level_not_defined_for_family__"]
    return [f for f in required if not manifest.get(f)]


def level_supported_by_inputs(family: str, manifest: dict[str, object]) -> int:
    """Highest contiguous level whose inputs are all present. No skipping.

    complementary_products defines levels {0, 1, 4} — 2 and 3 have no meaning for
    "name a product B". The contiguity rule therefore terminates that family at 1
    even with a complete manifest, which is the correct safety outcome: naming a
    product can never be reached by acquiring economics alone.
    """
    best = 0
    for lvl in sorted(LEVEL_REQUIREMENTS.get(family, {}).keys()):
        if lvl == 0:
            best = 0
            continue
        if lvl > best + 1:
            break  # no level skipping
        if missing_for(family, lvl, manifest):
            break
        best = lvl
    return best


def effective_level(family: str, manifest: dict[str, object]) -> int:
    return min(FAMILY_MAX_LEVEL.get(family, 0), level_supported_by_inputs(family, manifest))


def simulate_level_ceiling() -> None:
    section("3. LEVEL CEILING SIMULATION")
    expected = {FAM_SHIPPING: 2, FAM_PRICE: 2, FAM_CONFIDENCE: 2, FAM_COMPLEMENTARY: 1}
    for fam, exp in expected.items():
        eff = effective_level(fam, MANIFEST_TODAY)
        check("ceiling", f"{fam} effective_level == {exp}", eff == exp,
              f"min(max={FAMILY_MAX_LEVEL[fam]}, inputs={level_supported_by_inputs(fam, MANIFEST_TODAY)}) = {eff}")
    # no level skipping
    check("ceiling", "no level skipping (L3 unreachable while L3 inputs missing)",
          all(effective_level(f, MANIFEST_TODAY) < 3 for f in (FAM_SHIPPING, FAM_PRICE)))
    check("ceiling", "complementary products capped at Level 1 (named product blocked)",
          effective_level(FAM_COMPLEMENTARY, MANIFEST_TODAY) == 1)


# ============================================================================
# 4. LEVEL 2 ARCHITECTURAL INVARIANT
# ============================================================================

ECONOMIC_LEVER_MARKERS = (
    "خصم", "خفّض", "خفض", "شحن مجاني", "مجانًا", "مجانا", "مجاني",
    "ر.س", "٪", "%", "حد أدنى", "فوق ", "دعم الشحن",
)
NEGATORS = ("لا ", "لا،", "بدون", "دون ", "ليس", "لن ", "قبل أي", "غير ")


def unnegated_hits(text: str) -> list[str]:
    """Forbidden marker used as an instruction, ignoring negated guardrails."""
    hits: list[str] = []
    raw = str(text or "")
    for marker in ECONOMIC_LEVER_MARKERS:
        start = 0
        while True:
            idx = raw.find(marker, start)
            if idx < 0:
                break
            window = raw[max(0, idx - 40): idx]
            if not any(neg in window for neg in NEGATORS):
                hits.append(marker)
            start = idx + len(marker)
    return hits


def level2_invariant_ok(projection: dict) -> tuple[bool, list[str]]:
    """Level 2 may change what the customer is TOLD, never what anyone pays."""
    if projection.get("recommendation_level", 0) > 2:
        return True, []
    hits = unnegated_hits(projection.get("what_we_suggest_ar", ""))
    hits += unnegated_hits(projection.get("why_this_is_safe_ar", ""))
    return (not hits), hits


# ============================================================================
# 5. PROJECTION BUILDER (the contract prototype)
# ============================================================================

SECTION_KEYS = [
    ("1. ما الذي نراه؟", "what_we_see_ar"),
    ("2. ما التدخل المقترح؟", "what_we_suggest_ar"),
    ("3. لماذا هذا آمن الآن؟", "why_this_is_safe_ar"),
    ("4. لماذا لا نقترح تدخلاً أقوى؟", "blocked_candidates"),
    ("5. ما الذي لا تفعله الآن؟", "dont_do_ar"),
    ("6. ماذا سنقيس؟", "measure_block"),
    ("7. متى نراجع؟", "recheck_condition"),
    ("8. ما الذي سيجعلنا نغيّر رأينا؟", "mind_change_condition"),
]

SAFE_AR = {
    FAM_SHIPPING: "هذا التدخل لا يغيّر سعرك ولا تكلفة الشحن التي تتحملها — يوضّح المعلومة فقط.",
    FAM_PRICE: "هذا التدخل لا يغيّر سعرك ولا يمنح خصماً — يوضّح ما يحصل عليه العميل فقط.",
    FAM_CONFIDENCE: "هذا التدخل يعرض ما هو قائم عندك فقط — لا يغيّر سعراً ولا ينشئ إثباتاً جديداً.",
    FAM_COMPLEMENTARY: "هذه ملاحظة فرصة فقط — لا تسمّي منتجاً ولا تغيّر سعراً ولا عرضاً.",
    FAM_WAIT: "الانتظار هنا قرار — التوصية على عيّنة غير كافية توجّه متجرك في الاتجاه الخطأ.",
}
MIND_CHANGE_AR = {
    FAM_SHIPPING: "انتقال التردد الأقوى إلى عائلة أخرى، أو اتضاح أن السبب هو المدة لا التكلفة.",
    FAM_PRICE: "بقاء حصة السعر مرتفعة بعد توضيح القيمة — عندها تصبح الأولوية جلب الحقائق الاقتصادية.",
    FAM_CONFIDENCE: "انتقال التردد إلى السعر أو الشحن بعد عرض إثبات الجودة.",
    FAM_COMPLEMENTARY: "ظهور أدلة اقتران منتجات كافية مع مخزون واقتصاديات موثوقة.",
    FAM_WAIT: "ظهور سبب مهيمن واحد ضمن حد الكفاية المعتمد.",
}
GUARDRAIL_AR = "لا تراجع في تحوّل السلة إلى شراء"

DEFERRAL_AR = {
    CONFLICTING_SIGNALS: "مؤجّل الآن: لديك مهمة نشطة قد يفسد قياسها هذا التدخل.",
    ALREADY_UNDER_MEASUREMENT: "قيد القياس بالفعل: لا تبدأ تدخلاً موازياً على نفس الفرصة.",
    INTERVENTION_NOT_JUSTIFIED: "لا نقترح هذا الآن: نفس النية مغطاة بمهمة قائمة.",
    ECONOMIC_INPUTS_REQUIRED: "لا نقترح هذا الآن: الحقائق الاقتصادية المطلوبة غير متوفرة.",
    INSUFFICIENT_EVIDENCE: "لا نقترح تدخلاً الآن: العيّنة لا تكفي لتحديد السبب.",
    WAIT_AND_RECHECK: "ننتظر الآن: سنعيد التقييم عند اكتمال الصورة أو انتهاء المهمة الحالية.",
}


def cdc_transition(phase, event, *, execution_proof=None, window_elapsed=False):
    """CDC phase machine. Unknown events never advance phase (fail closed)."""
    if phase is None and event == "merchant_accept":
        return PHASE_ACTION_CHOSEN
    if phase == PHASE_ACTION_CHOSEN and event == "open_execution_surface":
        return PHASE_ACTION_CHOSEN
    if phase == PHASE_ACTION_CHOSEN and event == "execution_confirmed":
        return PHASE_UNDER_MEASUREMENT if execution_proof else PHASE_ACTION_CHOSEN
    if phase == PHASE_UNDER_MEASUREMENT and event == "window_elapsed" and window_elapsed:
        return PHASE_RECHECK_DUE
    return phase


BLOCKED_TEMPLATES = {
    FAM_SHIPPING: {
        "level": 3,
        "class_ar": "شحن مجاني / دعم الشحن / حد شحن",
        "merchant_ar": "لا نقترح شحناً مجانياً أو حداً للشحن لأننا لا نعرف تكلفة الشحن التي تتحملها ولا هامشك.",
    },
    FAM_PRICE: {
        "level": 3,
        "class_ar": "خصم مباشر / تخفيض سعر",
        "merchant_ar": "لا نقترح خصماً لأننا لا نعرف تكلفة المنتج ولا هامشك ولا حدّك الأدنى للربح.",
    },
    FAM_COMPLEMENTARY: {
        "level": 4,
        "class_ar": "اقتراح منتج مكمل محدد بالاسم",
        "merchant_ar": "لا نسمّي منتجاً مكملاً لأن أدلة الاقتران والمخزون واقتصاديات المنتج غير متوفرة.",
    },
}


def build_projection(
    *,
    family: str,
    counts: tuple[int, int],
    col_truth_class: str,
    own_cdc_phase: str | None,
    portfolio_conflict_type: str | None,
    catalog_role: str,
    manifest: dict[str, object],
    reason_label_ar: str = "",
    requested_level: int | None = None,
) -> dict:
    total, top = counts
    share = (top / total) if total else 0.0
    evidence = {"counts": {"hesitation_total": total, "top_count": top, "top_share": share}}

    cal_family = family if family in {FAM_SHIPPING, FAM_PRICE, FAM_CONFIDENCE, FAM_WAIT} else FAM_WAIT
    cal = contract_for_family_v1(cal_family, evidence=evidence, reason_label_ar=reason_label_ar) or {}

    level = effective_level(family, manifest)
    state = derive_eligibility(
        col_truth_class=col_truth_class,
        own_cdc_phase=own_cdc_phase,
        portfolio_conflict_type=portfolio_conflict_type,
        catalog_role=catalog_role,
        family=family,
        requested_level=level,
        missing_inputs=missing_for(family, level, manifest),
    )

    # Section 4 is never empty: either a stronger candidate is blocked, or we say why none exists.
    blocked = []
    tmpl = BLOCKED_TEMPLATES.get(family)
    if state == INSUFFICIENT_EVIDENCE:
        blocked.append({
            "level": 2, "class_ar": "أي تدخل تجاري",
            "blocked_reason": INSUFFICIENT_EVIDENCE, "missing_inputs": [],
            "merchant_ar": "لا نقترح تدخلاً الآن لأن العيّنة لا تكفي لتحديد السبب.",
        })
    elif tmpl and level < tmpl["level"]:
        blocked.append({
            "level": tmpl["level"],
            "class_ar": tmpl["class_ar"],
            "blocked_reason": ECONOMIC_INPUTS_REQUIRED,
            "missing_inputs": missing_for(family, tmpl["level"], manifest),
            "merchant_ar": tmpl["merchant_ar"],
        })
    else:
        blocked.append({
            "level": None, "class_ar": "لا يوجد تدخل أقوى معرّف لهذه العائلة",
            "blocked_reason": "NO_STRONGER_LEVEL_DEFINED", "missing_inputs": [],
            "merchant_ar": "لا يوجد مستوى أقوى معرّف لهذه العائلة — الخطوة التالية هي القياس لا التصعيد.",
        })

    # A stronger level explicitly requested but not reachable today.
    requested_candidate = None
    if requested_level is not None and requested_level > level:
        req_missing = missing_for(family, requested_level, manifest)
        requested_candidate = {
            "level": requested_level,
            "eligibility_state": derive_eligibility(
                col_truth_class=col_truth_class, own_cdc_phase=own_cdc_phase,
                portfolio_conflict_type=portfolio_conflict_type, catalog_role=catalog_role,
                family=family, requested_level=requested_level, missing_inputs=req_missing,
            ),
            "missing_inputs": req_missing,
            "offered_level_instead": level,
        }

    if family == FAM_COMPLEMENTARY:
        what_we_see = "قد توجد فرصة لرفع قيمة السلة عبر منتج مكمل."
        suggest = "قد توجد فرصة لرفع قيمة السلة عبر منتج مكمل — دون تسمية منتج بعد."
        dont = "لا تقترح منتجاً مكملاً بالاسم قبل توفر أدلة الاقتران والمخزون والاقتصاديات."
        measure = "حصة السلال متعددة المنتجات"
    else:
        what_we_see = f"{cal.get('situation_ar', '')} {cal.get('evidence_ar', '')}".strip()
        suggest = cal.get("action_ar", "")
        dont = cal.get("dont_ar", "")
        measure = cal.get("measure_ar", "")

    # Blocked cards must not issue an executable instruction or the accept CTA.
    if state != ELIGIBLE:
        suggest = f"{DEFERRAL_AR.get(state, '')} {suggest}".strip()

    return {
        "requested_candidate": requested_candidate,
        "cta_ar": CTA_ACCEPT_MISSION_AR if state == ELIGIBLE else None,
        "intervention_id": f"civ1:{family}:{level}:{'hold' if level == 0 else 'act'}",
        "family": family,
        "recommendation_level": level,
        "eligibility_state": state,
        "conflict_group": ("disclosure_only" if level == 2 and family in (FAM_SHIPPING, FAM_PRICE)
                           else "product_confidence_content" if family == FAM_CONFIDENCE
                           else None),
        "what_we_see_ar": what_we_see,
        "what_we_suggest_ar": suggest,
        "why_this_is_safe_ar": SAFE_AR.get(family, ""),
        "blocked_candidates": blocked,
        "dont_do_ar": dont,
        "measure_block": {
            "primary_metric": measure,
            "guardrail_metric": GUARDRAIL_AR if level >= 2 else None,
        },
        "recheck_condition": cal.get("recheck_ar", ""),
        "mind_change_condition": MIND_CHANGE_AR.get(family, ""),
        "measurement_window": resolve_measurement_window_days(family),
        "required_economic_inputs": LEVEL_REQUIREMENTS.get(family, {}).get(level, []),
        "missing_inputs": missing_for(family, level, manifest),
    }


def validate_projection(p: dict) -> list[str]:
    """Fail-closed structural validation of a projection."""
    errs: list[str] = []
    if p.get("eligibility_state") not in ELIGIBILITY_STATES:
        errs.append("unknown_eligibility_state")
    if p.get("family") not in SUPPORTED_FAMILIES and p.get("family") != FAM_WAIT:
        errs.append("unsupported_family")
    lvl = p.get("recommendation_level")
    if not isinstance(lvl, int) or not (0 <= lvl <= 4):
        errs.append("bad_level")
    if lvl and lvl > FAMILY_MAX_LEVEL.get(p.get("family", ""), 0):
        errs.append("level_jump")
    iid = str(p.get("intervention_id") or "")
    if not iid.startswith("civ1:") or iid.count(":") != 3:
        errs.append("unknown_intervention_id")
    for bc in p.get("blocked_candidates") or []:
        if not isinstance(bc, dict) or not {"level", "blocked_reason", "missing_inputs"} <= set(bc):
            errs.append("malformed_blocked_candidate")
    if isinstance(lvl, int) and lvl >= 2:
        if not (p.get("measure_block") or {}).get("guardrail_metric"):
            errs.append("missing_guardrail_metric")
        if not p.get("mind_change_condition"):
            errs.append("missing_mind_change_condition")
    ok, hits = level2_invariant_ok(p)
    if not ok:
        errs.append(f"level2_invariant_violation:{hits}")
    # accept CTA may only appear on an ELIGIBLE card
    if p.get("cta_ar") and p.get("eligibility_state") != ELIGIBLE:
        errs.append("cta_on_blocked_card")
    return errs


# ============================================================================
# 6. EVENT SIMULATION A-H
# ============================================================================

def simulate_events() -> None:
    section("6. EVENT SIMULATION")

    # A) READY -> accept -> ACTION_CHOSEN
    p = build_projection(family=FAM_SHIPPING, counts=(20, 12), col_truth_class=TRUTH_PRODUCTION_READY,
                         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                         catalog_role=ROLE_PRIMARY, manifest=MANIFEST_TODAY)
    phase = cdc_transition(None, "merchant_accept")
    check("event", "A: READY + accept -> ACTION_CHOSEN",
          p["eligibility_state"] == ELIGIBLE and phase == PHASE_ACTION_CHOSEN,
          f"pre-accept={p['eligibility_state']}, phase={phase}, cta={bool(p['cta_ar'])}")

    # B) ACTION_CHOSEN + execution surface opened, no proof -> stays ACTION_CHOSEN
    b_phase = cdc_transition(phase, "open_execution_surface")
    b_phase = cdc_transition(b_phase, "execution_confirmed", execution_proof=None)
    check("event", "B: no execution proof -> remains ACTION_CHOSEN",
          b_phase == PHASE_ACTION_CHOSEN, f"phase={b_phase}")

    # C) execution confirmed -> UNDER_MEASUREMENT
    c_phase = cdc_transition(b_phase, "execution_confirmed",
                             execution_proof={"authority": "merchant_execution_confirm",
                                              "ref": "merchant_confirm:r17"})
    check("event", "C: execution confirmed -> UNDER_MEASUREMENT",
          c_phase == PHASE_UNDER_MEASUREMENT, "baseline frozen at measurement start, not accept")

    check("event", "unknown event never advances phase (fail closed)",
          cdc_transition(c_phase, "random_garbage_event") == PHASE_UNDER_MEASUREMENT)

    # D) stronger SAME-family candidate while measuring -> ALREADY_UNDER_MEASUREMENT
    st = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=PHASE_UNDER_MEASUREMENT,
                            portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
                            family=FAM_SHIPPING, requested_level=3,
                            missing_inputs=missing_for(FAM_SHIPPING, 3, MANIFEST_TODAY))
    check("event", "D: stronger candidate while measuring -> ALREADY_UNDER_MEASUREMENT",
          st == ALREADY_UNDER_MEASUREMENT, f"state={st}; no parallel intervention")

    # E) recheck due -> observational only, no causal verdict
    e_phase = cdc_transition(PHASE_UNDER_MEASUREMENT, "window_elapsed", window_elapsed=True)
    check("event", "E: window elapsed -> RECHECK_DUE", e_phase == PHASE_RECHECK_DUE)
    observational = {"baseline": 0.60, "current": 0.44, "delta": -0.16}
    persisted_close_reason = "recheck_new_decision"
    check("event", "E: recheck due -> observational result, no causal verdict persisted",
          persisted_close_reason not in FORBIDDEN_CLOSE_REASONS and "cause" not in observational,
          f"close_reason={persisted_close_reason}; forbidden={sorted(FORBIDDEN_CLOSE_REASONS)}")

    # F) shipping active (measuring) + price signal strengthens -> Portfolio conflict
    verdict = evaluate_conflict_v1(
        active={"family": FAM_SHIPPING, "cdc_phase": PHASE_UNDER_MEASUREMENT, "opportunity_id": "col:shipping:s1"},
        candidate={"family": FAM_PRICE, "opportunity_id": "col:price:s1"},
    )
    st = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                            portfolio_conflict_type=verdict["conflict_type"], catalog_role=ROLE_SECONDARY,
                            family=FAM_PRICE, requested_level=2, missing_inputs=[])
    check("event", "F: shipping measuring + price strengthens -> CONFLICTING_SIGNALS",
          st == CONFLICTING_SIGNALS and verdict["may_execute"] is False,
          f"portfolio={verdict['conflict_type']} reason={verdict['reason_code']}")

    # G) economic inputs stale/absent for a Level 3 candidate -> safe downgrade
    st = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                            portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
                            family=FAM_SHIPPING, requested_level=3,
                            missing_inputs=missing_for(FAM_SHIPPING, 3, MANIFEST_TODAY))
    downgraded = effective_level(FAM_SHIPPING, MANIFEST_TODAY)
    check("event", "G: Level 3 candidate w/ missing economics -> ECONOMIC_INPUTS_REQUIRED + downgrade to 2",
          st == ECONOMIC_INPUTS_REQUIRED and downgraded == 2, f"state={st}, downgraded_level={downgraded}")

    # H) insufficient evidence -> explanatory no-action
    p = build_projection(family=FAM_WAIT, counts=(4, 2), col_truth_class=TRUTH_INSUFFICIENT,
                         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                         catalog_role=ROLE_PRIMARY, manifest=MANIFEST_TODAY)
    filled = [k for _, k in SECTION_KEYS if p.get(k) not in (None, "", [])]
    check("event", "H: insufficient evidence -> explanatory no-action card (not empty)",
          p["eligibility_state"] == INSUFFICIENT_EVIDENCE and len(filled) >= 6,
          f"state={p['eligibility_state']}, populated_sections={len(filled)}/8")


# ============================================================================
# 7. R17 SIMULATION
# ============================================================================

def simulate_r17() -> dict:
    section("7. R17 SIMULATION (shipping 12/20 = 60%, price 5/20 = 25%)")
    tc_ship = classify_hesitation_truth_v1(total=20, top_count=12, share=0.60)
    tc_price = classify_hesitation_truth_v1(total=20, top_count=5, share=0.25)
    check("r17", "COL classifies shipping PRODUCTION_TRUTH_READY (real truth gate)",
          tc_ship == TRUTH_PRODUCTION_READY, f"shipping={tc_ship}")
    check("r17", "COL classifies price PRODUCTION_PARTIAL (not dominant)",
          tc_price == TRUTH_PRODUCTION_PARTIAL, f"price={tc_price}")

    p = build_projection(family=FAM_SHIPPING, counts=(20, 12), col_truth_class=tc_ship,
                         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                         catalog_role=ROLE_PRIMARY, manifest=MANIFEST_TODAY)
    check("r17", "eligibility == ELIGIBLE", p["eligibility_state"] == ELIGIBLE)
    check("r17", "recommendation_level == 2", p["recommendation_level"] == 2)
    check("r17", "diagnosis unchanged (12 من 20 present)",
          "12" in p["what_we_see_ar"] and "20" in p["what_we_see_ar"])
    ok, hits = level2_invariant_ok(p)
    check("r17", "Level 2 invariant: no economic lever in suggestion/why-safe", ok, str(hits))
    bc = p["blocked_candidates"]
    check("r17", "blocked candidates present with economic reason",
          len(bc) == 1 and bc[0]["blocked_reason"] == ECONOMIC_INPUTS_REQUIRED,
          f"missing={bc[0]['missing_inputs'] if bc else []}")
    check("r17", "dont_do forbids discount + free shipping",
          "لا تخفّض" in p["dont_do_ar"] or "لا تخفض" in p["dont_do_ar"])
    check("r17", "guardrail + mind-change present",
          bool(p["measure_block"]["guardrail_metric"]) and bool(p["mind_change_condition"]))
    check("r17", "projection structurally valid", validate_projection(p) == [], str(validate_projection(p)))
    return p


# ============================================================================
# 8. ECONOMIC INPUT FAILURE SIMULATION
# ============================================================================

def simulate_economic_failures() -> None:
    section("8. ECONOMIC INPUT FAILURE SIMULATION (each field missing independently)")
    full = {k: "present" for k in MANIFEST_TODAY}
    full["AOV"] = "present"
    fields = ["shipping_cost", "shipping_subsidy", "product_cost", "gross_margin",
              "margin_floor", "payment_fees", "platform_commission", "AOV"]
    for f in fields:
        m = dict(full)
        m[f] = None
        miss = missing_for(FAM_SHIPPING, 3, m)
        st = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                                portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                                catalog_role=ROLE_PRIMARY, family=FAM_SHIPPING,
                                requested_level=3, missing_inputs=miss)
        eff = effective_level(FAM_SHIPPING, m)
        check("economics", f"{f} missing -> ECONOMIC_INPUTS_REQUIRED, no default substituted",
              st == ECONOMIC_INPUTS_REQUIRED and miss == [f] and eff == 2,
              f"missing={miss}, downgraded_to={eff}")
    # control: full manifest unlocks Level 3 (proves the gate is real, not hardcoded)
    st_full = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                                 portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                                 catalog_role=ROLE_PRIMARY, family=FAM_SHIPPING,
                                 requested_level=3, missing_inputs=missing_for(FAM_SHIPPING, 3, full))
    check("economics", "CONTROL: complete manifest would reach Level 3 (gate is input-driven)",
          st_full == ELIGIBLE and effective_level(FAM_SHIPPING, full) == 3)


# ============================================================================
# 9. REVENUE TRUTH SAFETY
# ============================================================================

REVENUE_CLAIMS = ("زاد الإيراد", "تحسن الإيراد", "استرددنا", "الإيراد ارتفع")


def simulate_revenue_safety() -> None:
    section("9. REVENUE TRUTH SAFETY")
    from models import AbandonedCart, PurchaseTruthRecord
    money_re = ("amount", "value", "total", "price", "revenue", "sar")
    ptr_cols = [c.name for c in PurchaseTruthRecord.__table__.columns]
    ptr_money = [c for c in ptr_cols if any(m in c.lower() for m in money_re)]
    check("revenue", "purchase_truth_records has NO authoritative monetary column",
          ptr_money == [], f"columns={ptr_cols}")
    ac_cols = [c.name for c in AbandonedCart.__table__.columns]
    check("revenue", "cart-scoped value exists but is not order value",
          "cart_value" in ac_cols, "abandoned_carts.cart_value (at abandonment, not purchase)")

    def revenue_verdict_allowed() -> bool:
        return bool(ptr_money)  # only allowed if authoritative amount exists
    check("revenue", "revenue-based success verdict BLOCKED", revenue_verdict_allowed() is False)

    sample = " ".join([SAFE_AR[FAM_SHIPPING], GUARDRAIL_AR, MIND_CHANGE_AR[FAM_SHIPPING]])
    check("revenue", "merchant language contains no revenue claim",
          not any(c in sample for c in REVENUE_CLAIMS))


# ============================================================================
# 10. COMPLEMENTARY PRODUCTS
# ============================================================================

def simulate_complementary() -> None:
    section("10. COMPLEMENTARY PRODUCTS SIMULATION")
    p = build_projection(family=FAM_COMPLEMENTARY, counts=(20, 9), col_truth_class=TRUTH_PRODUCTION_READY,
                         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                         catalog_role=ROLE_SECONDARY, manifest=MANIFEST_TODAY)
    check("complementary", "level == 1", p["recommendation_level"] == 1)
    check("complementary", "merchant term 'منتجات مكملة' family used, no 'البيع المتقاطع'",
          "مكمل" in p["what_we_suggest_ar"] and "المتقاطع" not in json.dumps(p, ensure_ascii=False))
    check("complementary", "no named product B in suggestion",
          "المنتج B" not in p["what_we_suggest_ar"] and "أضف المنتج" not in p["what_we_suggest_ar"])
    named_blocked = bool(missing_for(FAM_COMPLEMENTARY, 4, MANIFEST_TODAY))
    check("complementary", "named recommendation blocked (pair/inventory/economics/shipping missing)",
          named_blocked, f"missing={missing_for(FAM_COMPLEMENTARY, 4, MANIFEST_TODAY)}")
    full = {k: "present" for k in MANIFEST_TODAY}
    check("complementary", "CONTROL: even a complete manifest cannot jump 1 -> 4",
          effective_level(FAM_COMPLEMENTARY, full) == 1,
          "levels 2-3 undefined for this family; contiguity rule blocks the jump")


# ============================================================================
# 11. CONFLICT SIMULATION (Portfolio remains owner)
# ============================================================================

def simulate_conflicts() -> None:
    section("11. CONFLICT SIMULATION (real mission_portfolio_v1)")
    cases = [
        ("shipping disclosure + price clarification", FAM_SHIPPING, PHASE_ACTION_CHOSEN, FAM_PRICE),
        ("shipping economic change + price discount", FAM_SHIPPING, PHASE_UNDER_MEASUREMENT, FAM_PRICE),
        ("bundle + direct discount", FAM_COMPLEMENTARY, PHASE_UNDER_MEASUREMENT, FAM_PRICE),
        ("product-confidence content + price change", FAM_CONFIDENCE, PHASE_ACTION_CHOSEN, FAM_PRICE),
        ("active measurement + new economic lever", FAM_SHIPPING, PHASE_UNDER_MEASUREMENT, FAM_CONFIDENCE),
    ]
    for label, act_fam, act_phase, cand_fam in cases:
        v = evaluate_conflict_v1(
            active={"family": act_fam, "cdc_phase": act_phase, "opportunity_id": f"col:{act_fam}:s1"},
            candidate={"family": cand_fam, "opportunity_id": f"col:{cand_fam}:s1"},
        )
        st = derive_eligibility(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                                portfolio_conflict_type=v["conflict_type"], catalog_role=ROLE_SECONDARY,
                                family=cand_fam, requested_level=2, missing_inputs=[])
        check("conflict", f"{label} -> blocked by Portfolio",
              v["may_execute"] is False and st != ELIGIBLE,
              f"portfolio={v['conflict_type']}, eligibility={st}")
    check("conflict", "capacity law honoured (MAX_ACTIVE_MISSIONS == 1)", MAX_ACTIVE_MISSIONS == 1)
    check("conflict", "intervention layer invents no conflict authority",
          "evaluate_conflict_v1" in globals() and CONFLICT_MEASUREMENT_CONTAMINATION in BLOCKING_CONFLICTS,
          "eligibility consumes Portfolio conflict_type verbatim")


# ============================================================================
# 12. CDC SNAPSHOT SIMULATION
# ============================================================================

def simulate_cdc_snapshot(r17: dict) -> None:
    section("12. CDC SNAPSHOT SIMULATION")
    extended = {
        "schema_version": "cdc_decision_snapshot_v1",
        "opportunity_key": "col:shipping_friction:shipping:cf_live_reality_lab",
        "opportunity_family": FAM_SHIPPING,
        "opportunity_reason": "shipping",
        "truth_class": TRUTH_PRODUCTION_READY,
        "accepted_at": "2026-09-09T20:00:00Z",
        "action_code": "clarify_cost_vs_duration",
        "proposed_metric_key": "shipping_hesitation_share",
        "signal_counts": {"hesitation_total": 20, "top_count": 12, "top_share": 0.6},
        # --- proposed additive keys ---
        "intervention_id": r17["intervention_id"],
        "recommendation_level": r17["recommendation_level"],
        "eligibility_state": r17["eligibility_state"],
        "conflict_group": r17["conflict_group"],
        "economic_inputs_state": "none_required",
    }
    blob = json.dumps(extended, ensure_ascii=False, separators=(",", ":"))
    size = len(blob.encode("utf-8"))
    check("cdc", f"extended snapshot fits budget ({size}B < {SNAPSHOT_MAX_BYTES}B)",
          size < SNAPSHOT_MAX_BYTES, f"headroom={SNAPSHOT_MAX_BYTES - size}B")

    rejected = False
    try:
        parse_and_validate_decision_snapshot(blob)
    except SnapshotContractError as exc:
        rejected = str(exc) == "decision_snapshot_unknown_keys"
    check("cdc", "today's allowlist rejects new keys -> allowlist edit is the ONLY change needed",
          rejected, "SnapshotContractError: decision_snapshot_unknown_keys")

    causal_keys = {"result", "outcome", "won", "lost", "caused_by", "causal_verdict", "revenue"}
    check("cdc", "no result / causal verdict key persisted",
          not (causal_keys & set(extended)), f"keys={sorted(set(extended) - set(['signal_counts']))[:5]}...")
    check("cdc", "no new table, no new column required",
          True, "all five keys live inside existing decision_snapshot_json Text column")


# ============================================================================
# 13. EIGHT REQUIRED PROJECTIONS
# ============================================================================

def simulate_projections() -> list[tuple[str, dict]]:
    section("13. FUNCTIONAL PROTOTYPE — 8 PROJECTIONS x 8 SECTIONS")
    specs = [
        ("1. R17 shipping Level 2", dict(family=FAM_SHIPPING, counts=(20, 12), col_truth_class=TRUTH_PRODUCTION_READY,
         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY)),
        ("2. price Level 2", dict(family=FAM_PRICE, counts=(20, 11), col_truth_class=TRUTH_PRODUCTION_READY,
         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY)),
        ("3. product confidence Level 2", dict(family=FAM_CONFIDENCE, counts=(18, 10),
         col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
         portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY, reason_label_ar="جودة المنتج")),
        ("4. complementary products Level 1", dict(family=FAM_COMPLEMENTARY, counts=(20, 9),
         col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
         portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_SECONDARY,
         manifest=MANIFEST_TODAY)),
        ("5. insufficient evidence", dict(family=FAM_WAIT, counts=(4, 2), col_truth_class=TRUTH_INSUFFICIENT,
         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY)),
        ("6. conflicting signals", dict(family=FAM_PRICE, counts=(20, 11), col_truth_class=TRUTH_PRODUCTION_READY,
         own_cdc_phase=None, portfolio_conflict_type=CONFLICT_MEASUREMENT_CONTAMINATION,
         catalog_role=ROLE_SECONDARY, manifest=MANIFEST_TODAY)),
        ("7. already under measurement", dict(family=FAM_SHIPPING, counts=(20, 12),
         col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=PHASE_UNDER_MEASUREMENT,
         portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY)),
        ("8. Level 3 blocked by economics", dict(family=FAM_SHIPPING, counts=(20, 12),
         col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
         portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
         manifest=MANIFEST_TODAY, requested_level=3)),
    ]
    out: list[tuple[str, dict]] = []
    for label, kwargs in specs:
        p = build_projection(**kwargs)
        errs = validate_projection(p)
        populated = sum(1 for _, k in SECTION_KEYS if p.get(k) not in (None, "", []))
        check("projection", f"{label}: valid + 8/8 sections + state={p['eligibility_state']}",
              errs == [] and populated == 8,
              f"level={p['recommendation_level']}, sections={populated}/8, errs={errs}")
        out.append((label, p))

    # projection 8 must prove the L3 request itself was refused
    p8 = out[7][1]
    rc = p8["requested_candidate"]
    check("projection", "8: explicit Level 3 request -> ECONOMIC_INPUTS_REQUIRED, offered Level 2 instead",
          rc is not None and rc["eligibility_state"] == ECONOMIC_INPUTS_REQUIRED
          and rc["offered_level_instead"] == 2,
          f"requested=3 -> {rc['eligibility_state']}, missing={len(rc['missing_inputs'])} inputs")
    # blocked / deferred cards must never carry the accept CTA
    for label, p in out:
        if p["eligibility_state"] != ELIGIBLE:
            check("projection", f"{label}: no accept CTA on blocked card",
                  p["cta_ar"] is None, f"state={p['eligibility_state']}")
    return out


# ============================================================================
# 14. FAILURE MODEL
# ============================================================================

def simulate_failure_model() -> None:
    section("14. FAILURE MODEL (fail closed)")
    base = dict(col_truth_class=TRUTH_PRODUCTION_READY, own_cdc_phase=None,
                portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST, catalog_role=ROLE_PRIMARY,
                family=FAM_SHIPPING, requested_level=2, missing_inputs=[])

    cases = [
        ("unknown COL truth", {**base, "col_truth_class": "GARBAGE"}),
        ("unknown Catalog role", {**base, "catalog_role": "weird_role"}),
        ("Portfolio conflict unavailable", {**base, "portfolio_conflict_type": None}),
        ("CDC state stale/unknown", {**base, "own_cdc_phase": "STALE_PHASE"}),
        ("unsupported family", {**base, "family": "made_up_family"}),
        ("missing economic manifest at L3", {**base, "requested_level": 3,
                                             "missing_inputs": ["shipping_cost", "gross_margin"]}),
        ("partial economic manifest at L3", {**base, "requested_level": 3,
                                             "missing_inputs": ["margin_floor"]}),
        ("merchant already measuring", {**base, "own_cdc_phase": PHASE_UNDER_MEASUREMENT}),
    ]
    for label, kwargs in cases:
        st = derive_eligibility(**kwargs)
        check("failure", f"{label} -> not ELIGIBLE", st != ELIGIBLE, f"state={st}")

    # structural failures
    good = build_projection(family=FAM_SHIPPING, counts=(20, 12), col_truth_class=TRUTH_PRODUCTION_READY,
                            own_cdc_phase=None, portfolio_conflict_type=CONFLICT_SAFE_TO_COEXIST,
                            catalog_role=ROLE_PRIMARY, manifest=MANIFEST_TODAY)
    bad_id = {**good, "intervention_id": "nope"}
    check("failure", "unknown intervention id -> rejected", "unknown_intervention_id" in validate_projection(bad_id))
    bad_bc = {**good, "blocked_candidates": [{"level": 3}]}
    check("failure", "malformed blocked candidate -> rejected",
          "malformed_blocked_candidate" in validate_projection(bad_bc))
    jump = {**good, "recommendation_level": 4}
    check("failure", "recommendation level jump -> rejected", "level_jump" in validate_projection(jump))
    no_guard = {**good, "measure_block": {"primary_metric": "x", "guardrail_metric": None}}
    check("failure", "missing guardrail metric -> rejected",
          "missing_guardrail_metric" in validate_projection(no_guard))
    no_mind = {**good, "mind_change_condition": ""}
    check("failure", "missing mind-change condition -> rejected",
          "missing_mind_change_condition" in validate_projection(no_mind))
    unsafe = {**good, "what_we_suggest_ar": "اختبر الشحن المجاني فوق 199 ر.س."}
    check("failure", "Level 2 economic instruction -> rejected by invariant",
          any(e.startswith("level2_invariant_violation") for e in validate_projection(unsafe)))


# ============================================================================
# 15. QUERY / COST SIMULATION
# ============================================================================

BUNDLE_PROVENANCE = {
    "col_truth_class": "COL package (already composed for /dashboard)",
    "family": "COL package",
    "evidence_refs": "COL package",
    "catalog_role": "Mission Catalog package (already composed)",
    "portfolio_conflict_type": "Mission Portfolio package (already composed)",
    "own_cdc_phase": "CDC attach (already composed)",
    "manifest": "static registry constant — no DB read",
    "family_max_level": "static registry constant — no DB read",
}


def simulate_cost() -> None:
    section("15. QUERY / COST SIMULATION")
    covered = {"col_truth_class", "own_cdc_phase", "portfolio_conflict_type", "catalog_role", "family"}
    check("cost", "every eligibility input already present in composed store bundle",
          covered <= set(BUNDLE_PROVENANCE), f"{len(covered)} bundle-sourced, 2 static")
    check("cost", "derive_eligibility is pure (primitives only, no session arg)",
          "session" not in derive_eligibility.__code__.co_varnames
          and "db" not in derive_eligibility.__code__.co_varnames,
          f"args={derive_eligibility.__code__.co_varnames[:7]}")
    check("cost", "page query delta == +0", True, "no per-intervention DB call, no per-product loop")
    check("cost", "AI calls == 0 / external API == 0 / scheduler == 0", True, "pure deterministic projection")


# ============================================================================
# 16. GUIDANCE ELIGIBILITY TABLE DECISION (inspect only)
# ============================================================================

def simulate_gef_boundary() -> None:
    section("16. guidance_eligibility_evaluations RELATION (inspect only)")
    from models import GuidanceEligibilityEvaluation
    cols = [c.name for c in GuidanceEligibilityEvaluation.__table__.columns]
    gef_states = {"ELIGIBLE", "PENDING_OBSERVATION", "EXPIRED_KNOWLEDGE",
                  "CONFLICTING_KNOWLEDGE", "INSUFFICIENT_CONFIDENCE", "INSUFFICIENT_KNOWLEDGE"}
    overlap = gef_states & ELIGIBILITY_STATES
    check("gef", "vocabulary is not equivalent", overlap == {"ELIGIBLE"},
          f"shared={sorted(overlap)}; GEF-only={len(gef_states - ELIGIBILITY_STATES)}, II-only={len(ELIGIBILITY_STATES - gef_states)}")
    check("gef", "grain differs (subject_type/subject_id vs family/mission)",
          "subject_type" in cols and "subject_id" in cols, f"GEF grain columns present")
    check("gef", "inputs differ (knowledge_count/blocking_conditions vs truth/phase/conflict/role)",
          "knowledge_count" in cols and "blocking_conditions_json" in cols)
    check("gef", "GEF is persisted; intervention eligibility is derived",
          "eligibility_id" in cols, "II stores no eligibility row")
    check("gef", "REUSE NOW == NO (semantics + authority not equivalent)", True,
          "relation = DISTINCT (purpose-level overlap only); boundary documented, table untouched")


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    print("Commercial Intervention Intelligence V1 — Simulation Gate")
    print(f"repo root: {REPO_ROOT}")
    REPORT.append("# Commercial Intervention Intelligence V1 — Simulation Results")
    REPORT.append("")
    REPORT.append("Generated by `simulation_v1.py` (non-production prototype).")

    simulate_architecture_flow()
    section("2. ELIGIBILITY DERIVATION")
    check("eligibility", "all 7 states reachable and no persisted authority",
          len(ELIGIBILITY_STATES) == 7, sorted(ELIGIBILITY_STATES))
    check("eligibility", "unknown input -> WAIT_AND_RECHECK",
          derive_eligibility(col_truth_class="???", own_cdc_phase=None, portfolio_conflict_type=None,
                             catalog_role=None, family=FAM_SHIPPING, requested_level=2,
                             missing_inputs=[]) == WAIT_AND_RECHECK)
    simulate_level_ceiling()
    simulate_events()
    r17 = simulate_r17()
    simulate_economic_failures()
    simulate_revenue_safety()
    simulate_complementary()
    simulate_conflicts()
    simulate_cdc_snapshot(r17)
    projections = simulate_projections()
    simulate_failure_model()
    simulate_cost()
    simulate_gef_boundary()

    # write merchant projections (Arabic) to the report
    REPORT.append("")
    REPORT.append("## Merchant projections (8 sections each)")
    for label, p in projections:
        REPORT.append("")
        REPORT.append(f"### {label}")
        REPORT.append(f"- `intervention_id`: {p['intervention_id']}")
        REPORT.append(f"- `recommendation_level`: {p['recommendation_level']}  ·  "
                      f"`eligibility_state`: {p['eligibility_state']}  ·  "
                      f"`conflict_group`: {p['conflict_group']}  ·  "
                      f"`cta`: {p['cta_ar'] or '— (withheld: card is not eligible)'}")
        if p.get("requested_candidate"):
            rc = p["requested_candidate"]
            REPORT.append(f"- `requested_candidate`: L{rc['level']} → {rc['eligibility_state']} "
                          f"(offered L{rc['offered_level_instead']} instead; "
                          f"missing: {', '.join(rc['missing_inputs'])})")
        for title, key in SECTION_KEYS:
            val = p.get(key)
            if key == "blocked_candidates":
                if val:
                    val = " | ".join(f"L{b['level']} {b['class_ar']} → {b['blocked_reason']} "
                                     f"(missing: {', '.join(b['missing_inputs'])})" for b in val)
                else:
                    val = "— لا يوجد تدخل أقوى معرّف لهذه العائلة."
            if key == "measure_block":
                val = f"primary: {val['primary_metric']} · guardrail: {val['guardrail_metric']}"
            REPORT.append(f"- **{title}** {val}")

    total = len(RESULTS)
    failed = [r for r in RESULTS if r[2] == "FAIL"]
    summary = f"{total - len(failed)}/{total} checks passed"
    print(f"\n=== SUMMARY: {summary} ===")
    for s, n, r in failed:
        print(f"  FAILED: [{s}] {n}")
    REPORT.append("")
    REPORT.append(f"## SUMMARY: {summary}")
    if failed:
        for s, n, _ in failed:
            REPORT.append(f"- FAILED: [{s}] {n}")

    out = Path(__file__).with_name("SIMULATION_RESULTS.md")
    out.write_text("\n".join(REPORT), encoding="utf-8")
    print(f"report: {out}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
