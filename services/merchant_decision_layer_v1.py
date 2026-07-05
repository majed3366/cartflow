# -*- coding: utf-8 -*-
"""
Merchant Decision Layer v1 — governed decision execution engine.

Transforms proof bundles into governed merchant decisions (Foundation + Governance).
Does not mint truth, evidence, or presentation copy.

V1-A: ``resolve_merchant_decision_key_v1`` / ``merchant_decision_key`` (legacy path).
V1 execution: ``merchant_decisions_v1`` full contract payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from services.merchant_decision_registry_v1 import (
    DECISION_ID_CONTACT_CUSTOMER,
    DECISION_ID_FIX_CHANNEL,
    DECISION_ID_KL_OBSERVATION,
    DECISION_ID_MONITOR_RETURN,
    DECISION_ID_OBTAIN_CONTACT,
    REGISTRY_VERSION as DECISION_REGISTRY_VERSION,
    build_merchant_decision_registry_payload,
    decision_id_for_action_key,
    get_merchant_decision_registry_entry,
)

DECISION_LAYER_VERSION = "v1"

# --- V1-A canonical action keys (unchanged) ---
DECISION_OBTAIN_CONTACT = "obtain_contact"
DECISION_FIX_CHANNEL = "fix_channel"
DECISION_CONTACT_CUSTOMER = "contact_customer"
DECISION_MONITOR = "monitor"

INTERVENTION_DECISION_KEYS = frozenset(
    {
        DECISION_OBTAIN_CONTACT,
        DECISION_FIX_CHANNEL,
        DECISION_CONTACT_CUSTOMER,
    }
)

_V1A_DECISION_KEYS = INTERVENTION_DECISION_KEYS | {DECISION_MONITOR}

# --- Governed decision classes ---
CLASS_OBSERVATION = "observation"
CLASS_NEEDS_ATTENTION = "needs_attention"
CLASS_SUGGESTED_ACTION = "suggested_action"
CLASS_CRITICAL_ACTION = "critical_action"

_CLASS_PRIORITY = {
    CLASS_CRITICAL_ACTION: 400,
    CLASS_SUGGESTED_ACTION: 300,
    CLASS_NEEDS_ATTENTION: 200,
    CLASS_OBSERVATION: 100,
}

_CLASS_RANK = {
    CLASS_OBSERVATION: 0,
    CLASS_NEEDS_ATTENTION: 1,
    CLASS_SUGGESTED_ACTION: 2,
    CLASS_CRITICAL_ACTION: 3,
}

# --- Merchant actions ---
ACTION_EXECUTE = "execute"
ACTION_WAIT = "wait"
ACTION_DISMISS = "dismiss"
ACTION_MONITOR = "monitor"
ACTION_NONE = "none"

# --- Lifecycle ---
LIFECYCLE_CANDIDATE = "candidate"
LIFECYCLE_ELIGIBLE = "eligible"
LIFECYCLE_PUBLISHED = "published"
LIFECYCLE_CONSUMED = "consumed"
LIFECYCLE_RESOLVED = "resolved"
LIFECYCLE_EXPIRED = "expired"
LIFECYCLE_ARCHIVED = "archived"

# --- Suppression ---
SUPPRESSION_EXPIRED = "expired"
SUPPRESSION_ALREADY_ADDRESSED = "already_addressed"
SUPPRESSION_DUPLICATE = "duplicate"
SUPPRESSION_MERGED = "merged"
SUPPRESSION_SUPPRESSED = "suppressed"
SUPPRESSION_NOT_ELIGIBLE = "not_eligible"
SUPPRESSION_SILENT = "silent"

# --- Verification ---
VERIFY_PASSED = "passed"
VERIFY_SUPPRESSED = "suppressed"
VERIFY_PENDING = "pending"

_PROOF_TO_GOV_CONFIDENCE = {
    "confirmed": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "unknown": "insufficient",
}

_CONF_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "insufficient": 0,
}

_STATE_COMPLETED = "completed"
_STATE_ARCHIVED = "archived"
_STATE_NEEDS_INTERVENTION = "needs_intervention"
_STATE_RECOVERY_FOLLOWUP_COMPLETE = "recovery_followup_complete"

_RETURN_STATES = frozenset({"return_to_site", "waiting_purchase_window"})

_PHONE_BLOCK_LOGS = frozenset(
    {"schedule_blocked_missing_phone", "skipped_missing_phone"}
)
_FAIL_LOGS = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})

_LABEL_WAITING_CONTACT_AR = "بانتظار اكتمال بيانات التواصل"
_MERCHANT_NEEDED_YES = "نعم"

_DEFAULT_EXPIRATION_HOURS = 72


@dataclass
class _DecisionObservability:
    generated: int = 0
    published: int = 0
    suppressed: int = 0
    expired: int = 0
    by_class: dict[str, int] = field(default_factory=dict)
    by_goal: dict[str, int] = field(default_factory=dict)
    by_confidence: dict[str, int] = field(default_factory=dict)
    latency_ms_total: float = 0.0
    latency_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        avg_latency = (
            self.latency_ms_total / self.latency_samples
            if self.latency_samples
            else 0.0
        )
        return {
            "generated_decisions": self.generated,
            "published_decisions": self.published,
            "suppressed_decisions": self.suppressed,
            "expired_decisions": self.expired,
            "decision_classes": dict(self.by_class),
            "commercial_goals": dict(self.by_goal),
            "confidence_distribution": dict(self.by_confidence),
            "decision_latency_ms_avg": round(avg_latency, 3),
        }


_OBS = _DecisionObservability()


def reset_merchant_decision_observability_v1() -> None:
    """Reset operational metrics (tests)."""
    global _OBS  # noqa: PLW0603
    _OBS = _DecisionObservability()


def get_merchant_decision_observability_v1() -> dict[str, Any]:
    """Operational visibility — not merchant UI."""
    return _OBS.to_dict()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _log_set(log_statuses: Optional[Iterable[str]]) -> frozenset[str]:
    out: set[str] = set()
    for raw in log_statuses or ():
        s = (str(raw) or "").strip().lower()
        if s:
            out.add(s)
    return frozenset(out)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _gov_confidence_from_proof(proof: Mapping[str, Any]) -> str:
    raw = _norm_lower(proof.get("confidence"))
    return _PROOF_TO_GOV_CONFIDENCE.get(raw, "insufficient")


def _collect_evidence_ids(
    proof: Mapping[str, Any],
    *,
    reason_tag: str = "",
) -> list[str]:
    ids: list[str] = []
    primary = _norm(proof.get("evidence_id"))
    if primary:
        ids.append(primary)
    if _norm(reason_tag):
        from services.merchant_evidence_registry_v1 import (  # noqa: PLC0415
            EVIDENCE_HESITATION_REASON,
        )

        if EVIDENCE_HESITATION_REASON not in ids:
            ids.append(EVIDENCE_HESITATION_REASON)
    for step in proof.get("recovery_steps") or ():
        if not isinstance(step, dict):
            continue
        sid = _norm(step.get("evidence_id"))
        if sid and sid not in ids:
            ids.append(sid)
    return ids


def _cap_class_for_confidence(decision_class: str, confidence: str) -> str:
    cls = decision_class
    rank = _CONF_RANK.get(confidence, 0)
    if rank <= _CONF_RANK["insufficient"]:
        return CLASS_OBSERVATION
    if rank <= _CONF_RANK["low"]:
        if _CLASS_RANK.get(cls, 0) >= _CLASS_RANK[CLASS_SUGGESTED_ACTION]:
            return CLASS_NEEDS_ATTENTION
    if rank <= _CONF_RANK["medium"]:
        if cls == CLASS_CRITICAL_ACTION:
            return CLASS_SUGGESTED_ACTION
    return cls


def _cap_class_for_eligible_action(
    decision_class: str,
    *,
    action_eligible: bool,
) -> str:
    if action_eligible:
        return decision_class
    if _CLASS_RANK.get(decision_class, 0) >= _CLASS_RANK[CLASS_SUGGESTED_ACTION]:
        return CLASS_NEEDS_ATTENTION
    return decision_class


def _proposed_class_for_action_key(action_key: str, *, fail_logs: bool) -> str:
    key = _norm_lower(action_key)
    if key == DECISION_MONITOR:
        return CLASS_OBSERVATION
    if key == DECISION_FIX_CHANNEL or fail_logs:
        return CLASS_CRITICAL_ACTION
    if key in (DECISION_OBTAIN_CONTACT, DECISION_CONTACT_CUSTOMER):
        return CLASS_SUGGESTED_ACTION
    return CLASS_NEEDS_ATTENTION


def _merge_key(*, prefix: str, subject: str) -> str:
    return f"{prefix}:{subject}"


def _expiration_rule(*, hours: int = _DEFAULT_EXPIRATION_HOURS) -> dict[str, Any]:
    return {
        "ttl_hours": hours,
        "resolve_on_purchase": True,
        "resolve_on_archive": True,
    }


def _record_observability(
    decision: Mapping[str, Any],
    *,
    published: bool,
    suppressed: bool,
) -> None:
    _OBS.generated += 1
    cls = _norm(decision.get("decision_class"))
    goal = _norm(decision.get("commercial_goal"))
    conf = _norm(decision.get("confidence"))
    if cls:
        _OBS.by_class[cls] = _OBS.by_class.get(cls, 0) + 1
    if goal:
        _OBS.by_goal[goal] = _OBS.by_goal.get(goal, 0) + 1
    if conf:
        _OBS.by_confidence[conf] = _OBS.by_confidence.get(conf, 0) + 1
    if published:
        _OBS.published += 1
    if suppressed:
        _OBS.suppressed += 1


def validate_merchant_decision_contract_v1(decision: Mapping[str, Any]) -> list[str]:
    """Return missing required field names (empty = valid)."""
    required = (
        "decision_id",
        "decision_class",
        "evidence_ids",
        "proof_sources",
        "confidence",
        "commercial_goal",
        "merchant_action",
        "priority",
        "expiration",
        "suppression_state",
        "verification_status",
        "decision_explanation",
        "decision_timestamp",
        "lifecycle_state",
        "owner",
        "verification_method",
    )
    missing: list[str] = []
    for key in required:
        if key not in decision or decision.get(key) in (None, ""):
            missing.append(key)
    if not isinstance(decision.get("evidence_ids"), list):
        missing.append("evidence_ids")
    if not isinstance(decision.get("proof_sources"), list):
        missing.append("proof_sources")
    return missing


def _build_explanation(
    *,
    action_key: str,
    lifecycle_state: str,
    what_happened_ar: str = "",
    why_we_know_ar: str = "",
    executable: bool = False,
) -> dict[str, str]:
    state = _norm_lower(lifecycle_state)
    key = _norm_lower(action_key)
    rationale = _norm(what_happened_ar) or _norm(why_we_know_ar) or "بيانات مسار العميل من سجل المتجر"
    if key == DECISION_OBTAIN_CONTACT:
        return {
            "rationale_ar": rationale,
            "why_now_ar": "لا يمكن متابعة الاسترجاع بدون رقم تواصل",
            "if_omitted_ar": "تبقى السلة بدون إرسال استرجاع آلي",
        }
    if key == DECISION_FIX_CHANNEL:
        return {
            "rationale_ar": rationale,
            "why_now_ar": "فشل إرسال رسالة الاسترجاع — يلزم إصلاح قناة واتساب",
            "if_omitted_ar": "تتوقف رسائل الاسترجاع على هذه السلة",
        }
    if key == DECISION_CONTACT_CUSTOMER:
        omitted = (
            "قد تفوت فرصة استرجاع يدوية"
            if executable
            else "لا يتوفر مسار تنفيذ مباشر من لوحة السلال بعد"
        )
        return {
            "rationale_ar": rationale,
            "why_now_ar": "السلة تحتاج تدخلاً بعد توفر بيانات التواصل",
            "if_omitted_ar": omitted,
        }
    if key == DECISION_MONITOR or state in _RETURN_STATES:
        if state == "waiting_purchase_window":
            return {
                "rationale_ar": rationale
                or "عاد عميل إلى المتجر بعد رسالة CartFlow",
                "why_now_ar": (
                    "تم إيقاف المتابعة مؤقتًا بانتظار إكمال الشراء — لا يلزم إجراء منك"
                ),
                "if_omitted_ar": (
                    "إذا لم يكتمل الشراء، سيواصل CartFlow المتابعة تلقائياً حسب الإعدادات"
                ),
            }
        if state == "return_to_site":
            return {
                "rationale_ar": rationale or "عاد عميل إلى المتجر",
                "why_now_ar": "CartFlow يراقب ما إذا أكمل العميل الشراء",
                "if_omitted_ar": "قد يكمل العميل الشراء دون تدخلك",
            }
        return {
            "rationale_ar": rationale or "عاد العميل للموقع",
            "why_now_ar": "إشارة عودة نشطة — CartFlow يراقب فرصة الشراء",
            "if_omitted_ar": "قد يكمل العميل الشراء دون تدخلك",
        }
    return {
        "rationale_ar": rationale,
        "why_now_ar": "حالة مسار تستدعي متابعة",
        "if_omitted_ar": "يستمر النظام حسب إعدادات الاسترجاع",
    }


def build_merchant_decision_v1(
    *,
    decision_id: str,
    action_key: str = "",
    proof: Mapping[str, Any],
    proof_source: str = "",
    lifecycle_state: str = "",
    what_happened_ar: str = "",
    why_we_know_ar: str = "",
    reason_tag: str = "",
    action_eligible: bool = False,
    merchant_needed_ar: str = "",
) -> dict[str, Any]:
    """Mint one governed decision candidate from proof (does not publish)."""
    entry = get_merchant_decision_registry_entry(decision_id)
    if entry is None:
        raise ValueError(f"unknown decision_id: {decision_id}")

    confidence = _gov_confidence_from_proof(proof)
    evidence_ids = _collect_evidence_ids(proof, reason_tag=reason_tag)
    sources = [s for s in [_norm(proof_source)] if s]
    proposed = _proposed_class_for_action_key(action_key or entry.action_key, fail_logs=False)
    decision_class = _cap_class_for_confidence(proposed, confidence)
    decision_class = _cap_class_for_eligible_action(
        decision_class,
        action_eligible=action_eligible,
    )
    merchant_action = entry.default_merchant_action
    if decision_class == CLASS_OBSERVATION and merchant_action == ACTION_EXECUTE:
        merchant_action = ACTION_MONITOR if action_key == DECISION_MONITOR else ACTION_NONE

    subject = _norm(proof_source) or decision_id
    decision: dict[str, Any] = {
        "decision_id": entry.decision_id,
        "decision_class": decision_class,
        "evidence_ids": evidence_ids,
        "proof_sources": sources,
        "confidence": confidence,
        "commercial_goal": entry.commercial_goal,
        "merchant_action": merchant_action,
        "priority": _CLASS_PRIORITY.get(decision_class, 100),
        "expiration": _expiration_rule(),
        "suppression_state": "none",
        "verification_status": VERIFY_PENDING,
        "decision_explanation": _build_explanation(
            action_key=action_key or entry.action_key,
            lifecycle_state=lifecycle_state,
            what_happened_ar=what_happened_ar,
            why_we_know_ar=why_we_know_ar,
            executable=action_eligible,
        ),
        "decision_timestamp": _utc_now_iso(),
        "lifecycle_state": LIFECYCLE_CANDIDATE,
        "owner": entry.owner_module,
        "verification_method": entry.verification_method,
        "merge_key": _merge_key(prefix=entry.merge_key_prefix, subject=subject),
        "action_key": action_key or entry.action_key or None,
    }
    return decision


def _suppress_decision(
    decision: dict[str, Any],
    *,
    reason: str,
    lifecycle: str = LIFECYCLE_ARCHIVED,
) -> dict[str, Any]:
    out = dict(decision)
    out["suppression_state"] = reason
    out["verification_status"] = VERIFY_SUPPRESSED
    out["lifecycle_state"] = lifecycle
    _record_observability(out, published=False, suppressed=True)
    return out


def _evaluate_suppression(
    decision: dict[str, Any],
    *,
    purchase_truth: bool,
    lifecycle_state: str,
    merchant_needed_ar: str,
    action_key: str,
) -> Optional[str]:
    state = _norm_lower(lifecycle_state)
    if purchase_truth or state in (_STATE_COMPLETED, _STATE_ARCHIVED, _STATE_RECOVERY_FOLLOWUP_COMPLETE):
        return SUPPRESSION_ALREADY_ADDRESSED
    key = _norm_lower(action_key)
    needed = _norm(merchant_needed_ar)
    if key in INTERVENTION_DECISION_KEYS and needed != _MERCHANT_NEEDED_YES:
        return SUPPRESSION_SILENT
    if not decision.get("proof_sources"):
        return SUPPRESSION_NOT_ELIGIBLE
    if _CONF_RANK.get(_norm(decision.get("confidence")), 0) == 0 and _CLASS_RANK.get(
        _norm(decision.get("decision_class")), 0
    ) >= _CLASS_RANK[CLASS_NEEDS_ATTENTION]:
        return SUPPRESSION_NOT_ELIGIBLE
    return None


def _merge_decisions(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge same merge_key — keep highest class; mark losers merged."""
    published: dict[str, dict[str, Any]] = {}
    suppressed: list[dict[str, Any]] = []
    for cand in candidates:
        mk = _norm(cand.get("merge_key"))
        if not mk:
            published[id(cand)] = cand
            continue
        existing = published.get(mk)
        if existing is None:
            published[mk] = cand
            continue
        existing_rank = _CLASS_RANK.get(_norm(existing.get("decision_class")), 0)
        cand_rank = _CLASS_RANK.get(_norm(cand.get("decision_class")), 0)
        if cand_rank > existing_rank:
            suppressed.append(
                _suppress_decision(existing, reason=SUPPRESSION_MERGED, lifecycle=LIFECYCLE_ARCHIVED)
            )
            merged_ids = list(existing.get("evidence_ids") or [])
            for eid in cand.get("evidence_ids") or ():
                if eid not in merged_ids:
                    merged_ids.append(eid)
            cand = dict(cand)
            cand["evidence_ids"] = merged_ids
            published[mk] = cand
        else:
            suppressed.append(
                _suppress_decision(cand, reason=SUPPRESSION_MERGED, lifecycle=LIFECYCLE_ARCHIVED)
            )
    return list(published.values()), suppressed


def build_cart_row_merchant_decisions_v1(
    *,
    proof: Mapping[str, Any],
    recovery_key: str = "",
    customer_lifecycle_state: str = "",
    customer_lifecycle_merchant_needed_ar: str = "",
    customer_lifecycle_what_happened_ar: str = "",
    merchant_decision_key: str = "",
    reason_tag: str = "",
    purchase_truth: bool = False,
    action_eligible: bool = False,
) -> dict[str, Any]:
    """Build governed decision bundle for one normal-carts row."""
    import time

    t0 = time.perf_counter()
    proof_source = _norm(recovery_key) or _norm(proof.get("proof_source"))
    what = _norm(customer_lifecycle_what_happened_ar) or _norm(proof.get("what_happened_ar"))
    why = _norm(proof.get("why_we_know_ar"))
    action_key = _norm_lower(merchant_decision_key)
    candidates: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    if action_key:
        decision_id = decision_id_for_action_key(action_key)
        if decision_id:
            cand = build_merchant_decision_v1(
                decision_id=decision_id,
                action_key=action_key,
                proof=proof,
                proof_source=proof_source,
                lifecycle_state=customer_lifecycle_state,
                what_happened_ar=what,
                why_we_know_ar=why,
                reason_tag=reason_tag,
                action_eligible=action_eligible,
                merchant_needed_ar=customer_lifecycle_merchant_needed_ar,
            )
            if action_key == DECISION_FIX_CHANNEL:
                cand["decision_class"] = _cap_class_for_confidence(
                    CLASS_CRITICAL_ACTION,
                    _norm(cand.get("confidence")),
                )
                cand["decision_class"] = _cap_class_for_eligible_action(
                    _norm(cand["decision_class"]),
                    action_eligible=False,
                )
                cand["priority"] = _CLASS_PRIORITY.get(_norm(cand["decision_class"]), 200)
            suppress_reason = _evaluate_suppression(
                cand,
                purchase_truth=purchase_truth,
                lifecycle_state=customer_lifecycle_state,
                merchant_needed_ar=customer_lifecycle_merchant_needed_ar,
                action_key=action_key,
            )
            if suppress_reason:
                suppressed.append(
                    _suppress_decision(cand, reason=suppress_reason, lifecycle=LIFECYCLE_ARCHIVED)
                )
            else:
                cand["lifecycle_state"] = LIFECYCLE_ELIGIBLE
                candidates.append(cand)

    published, merge_suppressed = _merge_decisions(candidates)
    suppressed.extend(merge_suppressed)
    for dec in published:
        dec["lifecycle_state"] = LIFECYCLE_PUBLISHED
        dec["verification_status"] = VERIFY_PASSED
        dec["suppression_state"] = "none"
        _record_observability(dec, published=True, suppressed=False)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    _OBS.latency_ms_total += elapsed_ms
    _OBS.latency_samples += 1

    return {
        "version": DECISION_LAYER_VERSION,
        "decisions": published,
        "suppressed": suppressed,
    }


def build_kl_observation_decision_v1(insight: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Mint Observation-class decision from one KL insight (claim-level evidence)."""
    key = _norm(insight.get("insight_key"))
    if not key:
        return None
    eid = _norm(insight.get("evidence_id"))
    if not eid:
        return None
    conf_raw = _norm_lower(insight.get("confidence"))
    confidence = conf_raw if conf_raw in _CONF_RANK else "insufficient"
    entry = get_merchant_decision_registry_entry(DECISION_ID_KL_OBSERVATION)
    assert entry is not None
    decision: dict[str, Any] = {
        "decision_id": f"{DECISION_ID_KL_OBSERVATION}:{key}",
        "decision_class": CLASS_OBSERVATION,
        "evidence_ids": [eid],
        "proof_sources": [f"insight_key:{key}"],
        "confidence": confidence,
        "commercial_goal": entry.commercial_goal,
        "merchant_action": ACTION_NONE,
        "priority": _CLASS_PRIORITY[CLASS_OBSERVATION],
        "expiration": _expiration_rule(hours=168),
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": _norm(insight.get("title_ar")) or key,
            "why_now_ar": "ملخص Knowledge Layer للفترة المحددة",
            "if_omitted_ar": "لا يتغير مسار الاسترجاع — للمعلومة فقط",
        },
        "decision_timestamp": _utc_now_iso(),
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": entry.owner_module,
        "verification_method": entry.verification_method,
        "merge_key": _merge_key(prefix=entry.merge_key_prefix, subject=key),
    }
    _record_observability(decision, published=True, suppressed=False)
    return decision


def enrich_knowledge_report_merchant_decisions_v1(
    target: Mapping[str, Any] | dict[str, Any],
) -> None:
    """Attach KL observation decisions — presentation consumes; does not mint in JS."""
    if not isinstance(target, dict):
        return
    insights = target.get("insights")
    if not isinstance(insights, list):
        return
    decisions: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in insights:
        if not isinstance(raw, dict):
            continue
        dec = build_kl_observation_decision_v1(raw)
        if dec is None:
            continue
        mk = _norm(dec.get("merge_key"))
        if mk in seen:
            suppressed.append(
                _suppress_decision(dec, reason=SUPPRESSION_DUPLICATE, lifecycle=LIFECYCLE_ARCHIVED)
            )
            continue
        seen.add(mk)
        decisions.append(dec)
    target["merchant_decisions_v1"] = {
        "version": DECISION_LAYER_VERSION,
        "decisions": decisions,
        "suppressed": suppressed,
        "registry": build_merchant_decision_registry_payload(),
        "observability": get_merchant_decision_observability_v1(),
    }


# --- V1-A (unchanged behavior) ---


def resolve_merchant_decision_key_v1(
    *,
    customer_lifecycle_state: str = "",
    customer_lifecycle_merchant_needed_ar: str = "",
    customer_lifecycle_label_ar: str = "",
    has_phone: bool = True,
    phase_key: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    purchase_truth: bool = False,
) -> Optional[str]:
    """Return canonical decision key for V1-A in-scope cases only."""
    state = (customer_lifecycle_state or "").strip().lower()
    if purchase_truth or state == _STATE_COMPLETED:
        return None
    if state in (_STATE_ARCHIVED, _STATE_RECOVERY_FOLLOWUP_COMPLETE):
        return None

    if state in _RETURN_STATES:
        return DECISION_MONITOR

    needed = (customer_lifecycle_merchant_needed_ar or "").strip()
    if needed != _MERCHANT_NEEDED_YES:
        return None

    if state != _STATE_NEEDS_INTERVENTION:
        return None

    label = (customer_lifecycle_label_ar or "").strip()
    logs = _log_set(log_statuses)

    if (
        not has_phone
        or logs & _PHONE_BLOCK_LOGS
        or label == _LABEL_WAITING_CONTACT_AR
    ):
        return DECISION_OBTAIN_CONTACT

    if logs & _FAIL_LOGS:
        return DECISION_FIX_CHANNEL

    return DECISION_CONTACT_CUSTOMER


def attach_merchant_decision_layer_v1(
    target: dict[str, Any],
    *,
    customer_lifecycle_state: str = "",
    customer_lifecycle_merchant_needed_ar: str = "",
    customer_lifecycle_label_ar: str = "",
    has_phone: bool = True,
    phase_key: str = "",
    log_statuses: Optional[Iterable[str]] = None,
    purchase_truth: bool = False,
) -> None:
    """Attach ``merchant_decision_key`` when V1-A resolves a recommended action."""
    key = resolve_merchant_decision_key_v1(
        customer_lifecycle_state=customer_lifecycle_state,
        customer_lifecycle_merchant_needed_ar=customer_lifecycle_merchant_needed_ar,
        customer_lifecycle_label_ar=customer_lifecycle_label_ar,
        has_phone=has_phone,
        phase_key=phase_key,
        log_statuses=log_statuses,
        purchase_truth=purchase_truth,
    )
    if key and key in _V1A_DECISION_KEYS:
        target["merchant_decision_key"] = key


def attach_merchant_decisions_v1(
    target: Mapping[str, Any] | dict[str, Any],
    *,
    purchase_truth: bool = False,
) -> None:
    """
    Attach governed ``merchant_decisions_v1`` bundle after proof surface exists.

    Presentation layers consume this payload read-only.
    """
    if not isinstance(target, dict):
        return
    proof = target.get("merchant_proof_surface_v1")
    if not isinstance(proof, dict):
        return
    bundle = build_cart_row_merchant_decisions_v1(
        proof=proof,
        recovery_key=_norm(target.get("recovery_key")),
        customer_lifecycle_state=_norm(target.get("customer_lifecycle_state")),
        customer_lifecycle_merchant_needed_ar=_norm(
            target.get("customer_lifecycle_merchant_needed_ar")
        ),
        customer_lifecycle_what_happened_ar=_norm(
            target.get("customer_lifecycle_what_happened_ar")
        ),
        merchant_decision_key=_norm_lower(target.get("merchant_decision_key")),
        reason_tag=_norm(target.get("reason_tag")),
        purchase_truth=bool(
            purchase_truth
            or target.get("customer_lifecycle_completed_variant") == "purchased"
        ),
        action_eligible=bool(target.get("merchant_intervention_executable")),
    )
    bundle["observability"] = get_merchant_decision_observability_v1()
    target["merchant_decisions_v1"] = bundle


__all__ = [
    "ACTION_DISMISS",
    "ACTION_EXECUTE",
    "ACTION_MONITOR",
    "ACTION_NONE",
    "ACTION_WAIT",
    "CLASS_CRITICAL_ACTION",
    "CLASS_NEEDS_ATTENTION",
    "CLASS_OBSERVATION",
    "CLASS_SUGGESTED_ACTION",
    "DECISION_CONTACT_CUSTOMER",
    "DECISION_FIX_CHANNEL",
    "DECISION_LAYER_VERSION",
    "DECISION_MONITOR",
    "DECISION_OBTAIN_CONTACT",
    "INTERVENTION_DECISION_KEYS",
    "LIFECYCLE_PUBLISHED",
    "SUPPRESSION_SILENT",
    "VERIFY_PASSED",
    "attach_merchant_decision_layer_v1",
    "attach_merchant_decisions_v1",
    "build_cart_row_merchant_decisions_v1",
    "build_kl_observation_decision_v1",
    "build_merchant_decision_v1",
    "enrich_knowledge_report_merchant_decisions_v1",
    "get_merchant_decision_observability_v1",
    "reset_merchant_decision_observability_v1",
    "resolve_merchant_decision_key_v1",
    "validate_merchant_decision_contract_v1",
]
