# -*- coding: utf-8 -*-
"""
Home Semantic Composition V1 — cross-section deduplication + cognitive roles.

Owns Home-level composition AFTER commercial interpretation and Daily Brief finalize,
BEFORE Adaptive Cognition sequencing / rendering.

Rules:
- One merchant_problem may advance cognition (condition → action → explain).
- Different wording does not create a different identity.
- Opportunity must not be the inverse of an admitted risk/priority problem.
- Learning must show new knowledge / confidence change — not a paraphrase.
- Timeline must not restate an admitted conclusion.
- Deterministic; no AI authority.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

COMPOSITION_VERSION = "home_semantic_composition_v1"

# Canonical merchant problems (semantic topics).
PROBLEM_MISSING_CONTACT = "missing_contact_blocks_recovery"
PROBLEM_RECOVERY_READY = "recovery_ready_with_contact"
PROBLEM_WAITING_SEND = "waiting_send_followup"
PROBLEM_GENERIC = "generic"

# Cognitive roles sections may claim.
ROLE_CONDITION = "condition"  # business_health
ROLE_ACTION = "action"  # todays_priority
ROLE_RISK = "risk"  # biggest_revenue_risk
ROLE_EXPLAIN = "explain"  # business_understanding
ROLE_OPPORTUNITY = "opportunity"  # biggest_opportunity
ROLE_LEARNING = "learning_progress"
ROLE_EVENT = "event"  # business_timeline

# Progressive disclosure: for one problem, these roles may coexist (in order).
ALLOWED_PROGRESSION = (ROLE_CONDITION, ROLE_ACTION, ROLE_EXPLAIN)

# Same-problem roles that are always suppressed once ACTION or EXPLAIN is claimed.
REDUNDANT_AFTER_ACTION = (ROLE_RISK, ROLE_OPPORTUNITY, ROLE_LEARNING)

# Fact / decision / interpretation aliases → merchant_problem
_TOPIC_ALIASES: dict[str, str] = {
    "missing_contact_blocks_recovery_v1": PROBLEM_MISSING_CONTACT,
    "fact:obtain_contact": PROBLEM_MISSING_CONTACT,
    "fact:commercial_interpretation:missing_contact_blocks_recovery_v1": PROBLEM_MISSING_CONTACT,
    "decision:obtain_contact": PROBLEM_MISSING_CONTACT,
    "fact:learning:contact_blocker_pattern": PROBLEM_MISSING_CONTACT,
    "fact:opportunity:recoverable_with_contact": PROBLEM_RECOVERY_READY,
    "insight:missing_contact": PROBLEM_MISSING_CONTACT,
    "fact:opportunity:waiting_send": PROBLEM_WAITING_SEND,
    "decision:waiting_send": PROBLEM_WAITING_SEND,
    # Commercial findings — distinct problems (must not collapse into contact).
    "high_interest_low_purchase_product_v1": "product_conversion_gap",
    "repeated_interest_v1": "product_repeated_interest",
    "low_product_interest_v1": "product_low_interest",
    "dominant_hesitation_reason_v1": "hesitation_dominant",
    "hesitation_resolution_effectiveness_v1": "hesitation_resolution",
    "traffic_versus_conversion_v1": "traffic_quality_unknown",
    "return_without_purchase_v1": "recovery_return_without_purchase",
    "recovery_channel_effectiveness_v1": "recovery_channel_effect",
    "whatsapp_message_timing_test_v1": "whatsapp_timing_test",
    "insufficient_or_conflicting_evidence_v1": "missing_evidence",
    "fact:finding:high_interest_low_purchase_product_v1": "product_conversion_gap",
    "fact:finding:dominant_hesitation_reason_v1": "hesitation_dominant",
    "fact:finding:traffic_versus_conversion_v1": "traffic_quality_unknown",
    "fact:finding:insufficient_or_conflicting_evidence_v1": "missing_evidence",
}

# Opportunity topic → problem it must not invert
_INVERSE_OF: dict[str, str] = {
    PROBLEM_RECOVERY_READY: PROBLEM_MISSING_CONTACT,
}

SECTION_KEYS = (
    "business_health",
    "todays_priority",
    "attention_today",
    "biggest_revenue_risk",
    "biggest_opportunity",
    "business_understanding",
    "store_understanding",
    "learning_progress",
    "business_timeline",
    "while_away",
)

# Adaptive path → section eligibility (order still owned by ACF; visibility here).
PATH_SECTION_POLICY: dict[str, dict[str, Any]] = {
    "A": {
        "required": ["business_health", "business_understanding"],
        "optional": [
            "learning_progress",
            "business_timeline",
            "biggest_opportunity",
            "todays_priority",
            "biggest_revenue_risk",
        ],
        "deferred": [],
    },
    "B": {
        "required": ["business_health", "todays_priority"],
        "optional": ["business_understanding", "business_timeline"],
        "deferred": ["learning_progress"],
        "prefer_suppress": [
            "biggest_revenue_risk",
            "biggest_opportunity",
            "learning_progress",
        ],
    },
    "C": {
        "required": ["business_health", "todays_priority"],
        "optional": ["business_timeline", "learning_progress"],
        "deferred": ["business_understanding", "biggest_opportunity"],
        "prefer_suppress": ["biggest_revenue_risk", "biggest_opportunity"],
    },
    "D": {
        "required": ["business_health", "todays_priority"],
        "optional": ["learning_progress", "business_understanding", "business_timeline"],
        "deferred": ["biggest_opportunity"],
        "prefer_suppress": ["biggest_opportunity"],
    },
    "E": {
        "required": ["business_health"],
        "optional": ["business_timeline", "learning_progress"],
        "deferred": [
            "todays_priority",
            "biggest_revenue_risk",
            "biggest_opportunity",
            "business_understanding",
        ],
        "prefer_suppress": [
            "todays_priority",
            "biggest_revenue_risk",
            "biggest_opportunity",
        ],
    },
    "F": {
        "required": ["business_health", "business_understanding"],
        "optional": ["learning_progress", "business_timeline"],
        "deferred": ["todays_priority", "biggest_revenue_risk", "biggest_opportunity"],
        "prefer_suppress": [
            "todays_priority",
            "biggest_revenue_risk",
            "biggest_opportunity",
        ],
    },
}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def resolve_merchant_problem_v1(item: Mapping[str, Any] | None) -> str:
    """Map any Home item fields to a canonical merchant_problem."""
    if not isinstance(item, Mapping):
        return PROBLEM_GENERIC
    candidates = [
        item.get("merchant_problem"),
        item.get("semantic_topic"),
        item.get("commercial_interpretation_id"),
        item.get("insight_key"),
        item.get("operational_decision_key"),
        item.get("decision_id"),
        item.get("fact_key"),
        item.get("knowledge_id"),
        item.get("truth_id"),
    ]
    for raw in candidates:
        key = _norm(raw).lower()
        if not key:
            continue
        if key in _TOPIC_ALIASES:
            return _TOPIC_ALIASES[key]
        for alias, problem in _TOPIC_ALIASES.items():
            if alias in key or key in alias:
                return problem
    # Heuristic fallback from Arabic/English contact language (last resort).
    blob = " ".join(
        _norm(item.get(k))
        for k in (
            "headline_ar",
            "observation_ar",
            "why_ar",
            "progress_ar",
            "detail_ar",
            "summary_ar",
        )
    ).lower()
    if any(
        t in blob
        for t in (
            "بيانات التواصل",
            "بدون رقم",
            "no_phone",
            "obtain_contact",
            "missing contact",
        )
    ):
        return PROBLEM_MISSING_CONTACT
    return PROBLEM_GENERIC


def build_semantic_identity_v1(
    item: Mapping[str, Any] | None,
    *,
    cognitive_role: str,
    surface: str,
) -> dict[str, Any]:
    """Attach canonical semantic identity (different wording → same identity)."""
    item = item if isinstance(item, Mapping) else {}
    problem = resolve_merchant_problem_v1(item)
    truth_id = (
        _norm(item.get("truth_id"))
        or _norm(item.get("commercial_interpretation_id"))
        or _norm(item.get("fact_key"))
        or _norm(item.get("insight_key"))
        or f"truth:{problem}"
    )
    knowledge_id = (
        _norm(item.get("knowledge_id"))
        or _norm(item.get("source_knowledge_id"))
        or _norm(item.get("insight_key"))
        or ""
    )
    decision_id = (
        _norm(item.get("decision_id"))
        or _norm(item.get("operational_decision_key"))
        or ""
    )
    evidence_scope = (
        _norm(item.get("evidence_scope"))
        or _norm(item.get("evidence_label_ar"))
        or _norm(item.get("evidence_ar"))
        or _norm(item.get("evidence_summary_ar"))
        or ""
    )
    return {
        "truth_id": truth_id,
        "knowledge_id": knowledge_id or None,
        "decision_id": decision_id or None,
        "semantic_topic": problem,
        "merchant_problem": problem,
        "cognitive_role": cognitive_role,
        "evidence_scope": evidence_scope[:240] if evidence_scope else "",
        "freshness": _norm(item.get("freshness") or item.get("as_of") or ""),
        "confidence": _norm(item.get("confidence")),
        "surface_eligibility": True,
        "surface": surface,
        "composition_version": COMPOSITION_VERSION,
    }


def _stamp_item(item: dict[str, Any], *, role: str, surface: str) -> dict[str, Any]:
    ident = build_semantic_identity_v1(item, cognitive_role=role, surface=surface)
    item["semantic_identity_v1"] = ident
    item["merchant_problem"] = ident["merchant_problem"]
    item["semantic_topic"] = ident["semantic_topic"]
    item["cognitive_role"] = role
    return item


def _clear_section_items(section: dict[str, Any]) -> None:
    if "item" in section:
        section["item"] = None
    section["items"] = []
    if "count" in section:
        section["count"] = 0


def _admit_section(
    section: dict[str, Any],
    *,
    admitted: bool,
    reason: str,
    cognitive_role: str,
) -> None:
    section["home_admission_v1"] = {
        "admitted": bool(admitted),
        "reason": reason,
        "cognitive_role": cognitive_role,
        "composition_version": COMPOSITION_VERSION,
    }
    section["suppressed"] = not bool(admitted)


def _first_item(section: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not isinstance(section, Mapping):
        return None
    item = section.get("item")
    if isinstance(item, dict):
        return item
    items = section.get("items") or []
    if items and isinstance(items[0], dict):
        return items[0]
    return None


def apply_home_semantic_composition_v1(
    home: MutableMapping[str, Any],
    *,
    path: str = "",
) -> MutableMapping[str, Any]:
    """
    Home-level composition pass: stamp identities, progressive disclosure,
    suppress semantic duplicates, apply path eligibility.
    """
    if not isinstance(home, MutableMapping):
        return home

    suppressed: list[dict[str, Any]] = []
    claimed_roles: dict[str, set[str]] = {}  # problem -> roles claimed

    def _claim(problem: str, role: str) -> None:
        claimed_roles.setdefault(problem, set()).add(role)

    def _has(problem: str, role: str) -> bool:
        return role in claimed_roles.get(problem, set())

    def _has_any(problem: str, roles: tuple[str, ...]) -> bool:
        return bool(claimed_roles.get(problem, set()) & set(roles))

    # --- Priority (ACTION) — highest claim for merchant problem ---
    attention = home.get("attention_today")
    if not isinstance(attention, dict):
        attention = {}
        home["attention_today"] = attention
    pri = _first_item(attention)
    if pri:
        problem = resolve_merchant_problem_v1(pri)
        _stamp_item(pri, role=ROLE_ACTION, surface="todays_priority")
        attention["items"] = [pri]
        _claim(problem, ROLE_ACTION)
        _admit_section(
            attention,
            admitted=True,
            reason="owns_action_for_problem",
            cognitive_role=ROLE_ACTION,
        )
    else:
        _admit_section(
            attention,
            admitted=False,
            reason="empty_priority",
            cognitive_role=ROLE_ACTION,
        )
    home["todays_priority"] = attention

    # --- Understanding (EXPLAIN) — keep if progressive evidence, not if only duplicate ---
    understanding = home.get("store_understanding")
    if not isinstance(understanding, dict):
        understanding = {"items": []}
        home["store_understanding"] = understanding
    kept_u: list[dict[str, Any]] = []
    for raw in list(understanding.get("items") or []):
        if not isinstance(raw, dict):
            continue
        problem = resolve_merchant_problem_v1(raw)
        # Allow explain alongside action (progressive disclosure).
        if _has(problem, ROLE_EXPLAIN):
            suppressed.append(
                {
                    "section": "business_understanding",
                    "merchant_problem": problem,
                    "reason": "duplicate_explain_same_problem",
                    "truth_id": _norm(raw.get("fact_key")),
                }
            )
            continue
        _stamp_item(raw, role=ROLE_EXPLAIN, surface="business_understanding")
        kept_u.append(raw)
        _claim(problem, ROLE_EXPLAIN)
        break  # one understanding lead
    understanding["items"] = kept_u
    _admit_section(
        understanding,
        admitted=bool(kept_u),
        reason="owns_explain" if kept_u else "empty_or_duplicate_explain",
        cognitive_role=ROLE_EXPLAIN,
    )
    home["business_understanding"] = understanding
    home["store_understanding"] = understanding

    # --- Revenue risk — suppress if same problem already has action/explain ---
    risk = home.get("biggest_revenue_risk")
    if not isinstance(risk, dict):
        risk = {"item": None, "items": []}
        home["biggest_revenue_risk"] = risk
    risk_item = _first_item(risk)
    if risk_item:
        problem = resolve_merchant_problem_v1(risk_item)
        if _has_any(problem, (ROLE_ACTION, ROLE_EXPLAIN, ROLE_RISK)):
            suppressed.append(
                {
                    "section": "biggest_revenue_risk",
                    "merchant_problem": problem,
                    "reason": "semantic_duplicate_of_priority_or_explain",
                    "truth_id": _norm(risk_item.get("fact_key")),
                    "headline_ar": _norm(risk_item.get("headline_ar")),
                }
            )
            _clear_section_items(risk)
            _admit_section(
                risk,
                admitted=False,
                reason="semantic_duplicate_of_priority_or_explain",
                cognitive_role=ROLE_RISK,
            )
        else:
            _stamp_item(risk_item, role=ROLE_RISK, surface="biggest_revenue_risk")
            risk["item"] = risk_item
            risk["items"] = [risk_item]
            _claim(problem, ROLE_RISK)
            _admit_section(
                risk,
                admitted=True,
                reason="distinct_financial_risk",
                cognitive_role=ROLE_RISK,
            )
    else:
        _admit_section(
            risk,
            admitted=False,
            reason="empty_risk",
            cognitive_role=ROLE_RISK,
        )

    # --- Opportunity — suppress inverse / same problem ---
    opp = home.get("biggest_opportunity")
    if not isinstance(opp, dict):
        opp = {"item": None, "items": []}
        home["biggest_opportunity"] = opp
    opp_item = _first_item(opp)
    if opp_item:
        problem = resolve_merchant_problem_v1(opp_item)
        inverse_of = _INVERSE_OF.get(problem)
        inverse_blocked = False
        if problem != PROBLEM_GENERIC and _has_any(
            problem, (ROLE_ACTION, ROLE_RISK, ROLE_EXPLAIN)
        ):
            inverse_blocked = True
        elif inverse_of and _has_any(
            inverse_of, (ROLE_ACTION, ROLE_RISK, ROLE_EXPLAIN)
        ):
            inverse_blocked = True
        if inverse_blocked:
            suppressed.append(
                {
                    "section": "biggest_opportunity",
                    "merchant_problem": problem,
                    "reason": "inverse_or_same_problem_as_admitted_risk_or_priority",
                    "truth_id": _norm(opp_item.get("fact_key")),
                    "headline_ar": _norm(opp_item.get("headline_ar")),
                }
            )
            _clear_section_items(opp)
            _admit_section(
                opp,
                admitted=False,
                reason="inverse_or_same_problem_as_admitted_risk_or_priority",
                cognitive_role=ROLE_OPPORTUNITY,
            )
        else:
            _stamp_item(opp_item, role=ROLE_OPPORTUNITY, surface="biggest_opportunity")
            opp["item"] = opp_item
            opp["items"] = [opp_item]
            _claim(problem, ROLE_OPPORTUNITY)
            _admit_section(
                opp,
                admitted=True,
                reason="distinct_executable_opportunity",
                cognitive_role=ROLE_OPPORTUNITY,
            )
    else:
        _admit_section(
            opp,
            admitted=False,
            reason="empty_opportunity",
            cognitive_role=ROLE_OPPORTUNITY,
        )

    # --- Learning — require new knowledge; suppress contact paraphrase ---
    learning = home.get("learning_progress")
    if not isinstance(learning, dict):
        learning = {"items": []}
        home["learning_progress"] = learning
    kept_l: list[dict[str, Any]] = []
    for raw in list(learning.get("items") or []):
        if not isinstance(raw, dict):
            continue
        problem = resolve_merchant_problem_v1(raw)
        if problem != PROBLEM_GENERIC and _has_any(
            problem, (ROLE_ACTION, ROLE_EXPLAIN, ROLE_RISK, ROLE_LEARNING)
        ):
            suppressed.append(
                {
                    "section": "learning_progress",
                    "merchant_problem": problem,
                    "reason": "learning_restates_admitted_problem",
                    "truth_id": _norm(raw.get("fact_key")),
                }
            )
            continue
        _stamp_item(raw, role=ROLE_LEARNING, surface="learning_progress")
        kept_l.append(raw)
        if problem != PROBLEM_GENERIC:
            _claim(problem, ROLE_LEARNING)
        if len(kept_l) >= 2:
            break
    if not kept_l:
        # Keep a single non-problem accumulating signal only if no action story.
        if not any(ROLE_ACTION in roles for roles in claimed_roles.values()):
            kept_l = [
                _stamp_item(
                    {
                        "kind": "unknown_becoming_known",
                        "progress_ar": "الفهم يتراكم مع كل يوم تشغيل",
                        "detail_ar": (
                            "كل نشاط في المتجر يغذّي صورة أوضح عن التردد والاسترجاع والشراء."
                        ),
                        "confidence": "low",
                        "fact_key": "fact:learning:accumulating",
                    },
                    role=ROLE_LEARNING,
                    surface="learning_progress",
                )
            ]
    learning["items"] = kept_l
    _admit_section(
        learning,
        admitted=bool(kept_l),
        reason="new_learning_signal" if kept_l else "suppressed_duplicate_learning",
        cognitive_role=ROLE_LEARNING,
    )

    # --- Timeline — drop events that restate admitted problems ---
    timeline = home.get("while_away")
    if not isinstance(timeline, dict):
        timeline = {"items": []}
        home["while_away"] = timeline
    kept_t: list[dict[str, Any]] = []
    for raw in list(timeline.get("items") or []):
        if not isinstance(raw, dict):
            continue
        problem = resolve_merchant_problem_v1(raw)
        if problem != PROBLEM_GENERIC and _has_any(
            problem, (ROLE_ACTION, ROLE_EXPLAIN, ROLE_RISK)
        ):
            suppressed.append(
                {
                    "section": "business_timeline",
                    "merchant_problem": problem,
                    "reason": "timeline_duplicates_executive_conclusion",
                    "truth_id": _norm(raw.get("fact_key")),
                }
            )
            continue
        _stamp_item(raw, role=ROLE_EVENT, surface="business_timeline")
        kept_t.append(raw)
    timeline["items"] = kept_t
    _admit_section(
        timeline,
        admitted=bool(kept_t),
        reason="distinct_events" if kept_t else "empty_or_duplicate_timeline",
        cognitive_role=ROLE_EVENT,
    )
    home["business_timeline"] = timeline
    home["while_away"] = timeline

    # --- Health (CONDITION) — strip evidence that repeats admitted problem ---
    health = home.get("business_health")
    if not isinstance(health, dict):
        health = {}
        home["business_health"] = health
    # Remove contact-count evidence line when priority/explain already owns it.
    evidence = _norm(health.get("evidence_summary_ar"))
    if PROBLEM_MISSING_CONTACT in claimed_roles and evidence:
        parts = [p.strip() for p in evidence.split("·")]
        parts = [p for p in parts if "تواصل" not in p and "رقم" not in p]
        health["evidence_summary_ar"] = " · ".join(parts)
    if PROBLEM_MISSING_CONTACT in claimed_roles:
        health["semantic_identity_v1"] = build_semantic_identity_v1(
            {
                "truth_id": f"truth:{PROBLEM_MISSING_CONTACT}:condition",
                "merchant_problem": PROBLEM_MISSING_CONTACT,
                "confidence": health.get("confidence"),
                "evidence_summary_ar": health.get("evidence_summary_ar"),
            },
            cognitive_role=ROLE_CONDITION,
            surface="business_health",
        )
        _claim(PROBLEM_MISSING_CONTACT, ROLE_CONDITION)
    else:
        health["semantic_identity_v1"] = build_semantic_identity_v1(
            {
                "truth_id": "truth:business_health",
                "confidence": health.get("confidence"),
            },
            cognitive_role=ROLE_CONDITION,
            surface="business_health",
        )
    _admit_section(
        health,
        admitted=True,
        reason="orientation_condition",
        cognitive_role=ROLE_CONDITION,
    )

    admitted_sections = [
        key
        for key in (
            "business_health",
            "todays_priority",
            "biggest_revenue_risk",
            "biggest_opportunity",
            "business_understanding",
            "learning_progress",
            "business_timeline",
        )
        if _section_admitted(home, key)
    ]

    home["home_semantic_composition_v1"] = {
        "version": COMPOSITION_VERSION,
        "claimed_roles": {k: sorted(v) for k, v in claimed_roles.items()},
        "suppressed": suppressed,
        "admitted_sections": admitted_sections,
        "path_policy_applied": None,
        "progressive_disclosure": list(ALLOWED_PROGRESSION),
    }
    obs = home.get("observability")
    if not isinstance(obs, dict):
        obs = {}
        home["observability"] = obs
    obs["home_semantic_composition_v1"] = True
    obs["home_semantic_suppressed_count"] = len(suppressed)
    obs["home_semantic_admitted_sections"] = list(admitted_sections)

    path_key = _norm(path).upper()
    if path_key:
        apply_path_eligibility_v1(home, path=path_key)
    return home


def apply_path_eligibility_v1(
    home: MutableMapping[str, Any],
    *,
    path: str,
) -> MutableMapping[str, Any]:
    """Path-level defer/suppress after semantic composition (does not re-rank truth)."""
    path_key = _norm(path).upper()
    policy = PATH_SECTION_POLICY.get(path_key)
    if not policy or not isinstance(home, MutableMapping):
        return home
    path_suppress: list[dict[str, Any]] = []
    required = set(policy.get("required") or [])
    for sec_key in list(policy.get("deferred") or []):
        if sec_key in required:
            continue
        if sec_key not in (
            "biggest_revenue_risk",
            "biggest_opportunity",
            "learning_progress",
        ):
            continue
        section = _section_by_key(home, sec_key)
        if not isinstance(section, dict):
            continue
        adm = (
            section.get("home_admission_v1")
            if isinstance(section.get("home_admission_v1"), Mapping)
            else {}
        )
        if not adm.get("admitted"):
            continue
        _clear_section_items(section)
        _admit_section(
            section,
            admitted=False,
            reason=f"path_{path_key}_deferred",
            cognitive_role=_norm(adm.get("cognitive_role")),
        )
        path_suppress.append({"section": sec_key, "reason": f"path_{path_key}_deferred"})

    meta = home.get("home_semantic_composition_v1")
    if not isinstance(meta, dict):
        meta = {}
        home["home_semantic_composition_v1"] = meta
    prev = list(meta.get("suppressed") or [])
    meta["suppressed"] = prev + path_suppress
    meta["path_policy_applied"] = path_key
    meta["admitted_sections"] = [
        key
        for key in (
            "business_health",
            "todays_priority",
            "biggest_revenue_risk",
            "biggest_opportunity",
            "business_understanding",
            "learning_progress",
            "business_timeline",
        )
        if _section_admitted(home, key)
    ]
    obs = home.get("observability")
    if isinstance(obs, dict):
        obs["home_semantic_suppressed_count"] = len(meta["suppressed"])
        obs["home_semantic_admitted_sections"] = list(meta["admitted_sections"])
    return home


def _section_by_key(home: Mapping[str, Any], key: str) -> Any:
    if key == "todays_priority":
        return home.get("todays_priority") or home.get("attention_today")
    if key == "business_understanding":
        return home.get("business_understanding") or home.get("store_understanding")
    if key == "business_timeline":
        return home.get("business_timeline") or home.get("while_away")
    return home.get(key)


def _section_admitted(home: Mapping[str, Any], key: str) -> bool:
    section = _section_by_key(home, key)
    if not isinstance(section, Mapping):
        return False
    adm = section.get("home_admission_v1")
    if isinstance(adm, Mapping):
        return bool(adm.get("admitted"))
    # Health always if present
    if key == "business_health":
        return True
    return False


def filter_section_order_by_admission_v1(
    order: list[str],
    home: Mapping[str, Any],
    *,
    path: str = "",
) -> list[str]:
    """Filter ACF section_order to admitted sections only (health always kept)."""
    out: list[str] = []
    seen: set[str] = set()
    path_key = _norm(path).upper()
    policy = PATH_SECTION_POLICY.get(path_key) or {}
    required = set(policy.get("required") or [])
    for key in order:
        if key in seen:
            continue
        if key == "business_health" or _section_admitted(home, key) or key in required:
            # Required but empty → still include health; skip empty required others
            if key != "business_health" and not _section_admitted(home, key):
                if key in required:
                    continue
                continue
            out.append(key)
            seen.add(key)
    # Ensure required admitted sections appear even if order missed them
    for key in required:
        if key not in seen and _section_admitted(home, key):
            out.append(key)
            seen.add(key)
    if "business_health" not in seen:
        out.insert(0, "business_health")
    return out


__all__ = [
    "COMPOSITION_VERSION",
    "PATH_SECTION_POLICY",
    "PROBLEM_MISSING_CONTACT",
    "apply_home_semantic_composition_v1",
    "apply_path_eligibility_v1",
    "build_semantic_identity_v1",
    "filter_section_order_by_admission_v1",
    "resolve_merchant_problem_v1",
]
