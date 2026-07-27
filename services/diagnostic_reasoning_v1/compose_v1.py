# -*- coding: utf-8 -*-
"""
Diagnostic composer V1 — off-path only.

Never call from Home request finalize.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.contract_v1 import (
    AR_CONFLICTING,
    AR_CONTACT_BLOCKED,
    AR_INSUFFICIENT_GENERIC,
    AR_INSUFFICIENT_INTEREST,
    AR_INSUFFICIENT_SHIPPING_STAGE,
    AR_PAYMENT_FRICTION,
    AR_SHIPPING_COST,
    DIAGNOSIS_STATUS_CONFLICTING,
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPORTED,
    DIAGNOSTIC_VERSION_V1,
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
    FAMILY_PAYMENT_FRICTION,
    empty_contract_v1,
    validate_contract_v1,
)
from services.diagnostic_reasoning_v1.recommendation_registry_v1 import (
    recommendation_for_diagnosis_v1,
)
from services.diagnostic_reasoning_v1.scoring_v1 import select_diagnosis_v1

DEFAULT_TTL_HOURS = 24
DEFAULT_WINDOW_DAYS = 14


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _diagnostic_id(store_slug: str, family: str, subject_id: str) -> str:
    raw = f"{store_slug}|{family}|{subject_id}|{DIAGNOSTIC_VERSION_V1}"
    return "dx_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _observation_ar(family: str, bag: Mapping[str, Any]) -> str:
    product = str(bag.get("product_name_ar") or "").strip()
    if family == FAMILY_CHECKOUT_AFTER_SHIPPING:
        if product:
            return f"يغادر العملاء بعد خطوة الشحن في مسار {product}."
        return "يغادر العملاء بعد خطوة الشحن."
    if family == FAMILY_INTEREST_WITHOUT_PURCHASE:
        if product:
            return f"اهتمام متكرر بـ {product} دون إتمام الشراء."
        return "اهتمام متكرر بمنتج دون إتمام الشراء."
    if family == FAMILY_PAYMENT_FRICTION:
        return "يغادر العملاء عند خطوة الدفع."
    if family == FAMILY_CONTACT_FOLLOWUP_BLOCKED:
        return "متابعة بعض العملاء غير ممكنة حالياً."
    return "لوحظ سلوك عملاء يحتاج تفسيراً."


def _diagnosis_ar(
    family: str,
    *,
    status: str,
    selected: Optional[str],
) -> str:
    if status == DIAGNOSIS_STATUS_CONFLICTING:
        return AR_CONFLICTING
    if status == DIAGNOSIS_STATUS_INSUFFICIENT or not selected:
        if family == FAMILY_CHECKOUT_AFTER_SHIPPING:
            return AR_INSUFFICIENT_SHIPPING_STAGE
        if family == FAMILY_INTEREST_WITHOUT_PURCHASE:
            return AR_INSUFFICIENT_INTEREST
        return AR_INSUFFICIENT_GENERIC
    if selected == "shipping_cost":
        return AR_SHIPPING_COST
    if selected == "payment_friction":
        return AR_PAYMENT_FRICTION
    if selected == "missing_contact":
        return AR_CONTACT_BLOCKED
    # Supported but no merchant subtype copy — stay honest.
    return AR_INSUFFICIENT_GENERIC


def compose_diagnostic_contract_v1(
    *,
    store_slug: str,
    family: str,
    evidence_bag: Mapping[str, Any],
    subject_type: str = "product",
    subject_id: str = "",
    ttl_hours: int = DEFAULT_TTL_HOURS,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Compose one diagnostic contract from a bounded evidence bag."""
    slug = (store_slug or "").strip()
    sid = (subject_id or str(evidence_bag.get("subject_id") or "store")).strip() or "store"
    stype = (subject_type or str(evidence_bag.get("subject_type") or "store")).strip()
    dx_id = _diagnostic_id(slug, family, sid)
    contract = empty_contract_v1(
        diagnostic_id=dx_id,
        store_slug=slug,
        subject_type=stype,
        subject_id=sid,
        family=family,
    )
    now = _utc_now()
    expires = now + timedelta(hours=max(1, int(ttl_hours)))
    window = {
        "days": int(window_days),
        "sample_n": int(evidence_bag.get("sample_n") or 0),
        "bounded": True,
    }

    selection = select_diagnosis_v1(family, evidence_bag=evidence_bag)
    status = str(selection.get("diagnosis_status") or DIAGNOSIS_STATUS_INSUFFICIENT)
    selected = selection.get("selected_diagnosis")
    rec = recommendation_for_diagnosis_v1(
        family,
        selected_diagnosis=str(selected) if selected else None,
        diagnosis_status=status,
    )

    signals = evidence_bag.get("signals") if isinstance(evidence_bag.get("signals"), Mapping) else {}
    supporting = []
    contradicting = []
    for score in list(selection.get("candidate_scores") or []):
        key = str(score.get("cause_key") or "")
        if key == "insufficient_evidence":
            continue
        entry = {
            "cause_key": key,
            "score": score.get("score"),
            "support_n": score.get("support_n"),
            "contradict_n": score.get("contradict_n"),
            "meets_minimum": score.get("meets_minimum"),
        }
        if key == selected and status == DIAGNOSIS_STATUS_SUPPORTED:
            supporting.append(entry)
        elif int(score.get("contradict_n") or 0) > 0 or (
            status == DIAGNOSIS_STATUS_CONFLICTING
            and key in list(selection.get("tied_causes") or [])
        ):
            contradicting.append(entry)

    # Traceable evidence refs (bounded tokens — not raw event dumps).
    observation_refs = list(evidence_bag.get("observation_refs") or [])
    if not observation_refs and signals:
        observation_refs = [
            f"signal:{k}:{v}" for k, v in list(signals.items())[:12] if int(v or 0) > 0
        ]

    obs_ar = _observation_ar(family, evidence_bag)
    diag_ar = _diagnosis_ar(family, status=status, selected=str(selected) if selected else None)

    # Causal recommendation only when supported diagnosis answers "why".
    if status != DIAGNOSIS_STATUS_SUPPORTED:
        rec = {
            "cause_key": "insufficient_evidence",
            "text_ar": recommendation_for_diagnosis_v1(
                family,
                selected_diagnosis=None,
                diagnosis_status=DIAGNOSIS_STATUS_INSUFFICIENT,
            )["text_ar"],
        }
        selected = None if status == DIAGNOSIS_STATUS_CONFLICTING else "insufficient_evidence"

    contract.update(
        {
            "observation_refs": observation_refs,
            "supporting_evidence": supporting,
            "contradicting_evidence": contradicting,
            "candidate_causes": list(selection.get("candidate_scores") or []),
            "selected_diagnosis": selected,
            "diagnosis_status": status,
            "confidence_level": selection.get("confidence_level"),
            "confidence_reason": selection.get("confidence_reason"),
            "recommendation": rec,
            "observation_ar": obs_ar,
            "diagnosis_ar": diag_ar,
            "recommendation_ar": str(rec.get("text_ar") or ""),
            "evidence_window": window,
            "generated_at": _iso(now),
            "expires_at": _iso(expires),
            "diagnostic_version": DIAGNOSTIC_VERSION_V1,
            "tied_causes": list(selection.get("tied_causes") or []),
        }
    )
    ok, errors = validate_contract_v1(contract)
    contract["contract_ok"] = ok
    contract["contract_errors"] = errors
    return contract


def compose_store_diagnostics_v1(
    *,
    store_slug: str,
    evidence_bags: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Compose diagnostics for multiple bounded bags (background only)."""
    out: list[dict[str, Any]] = []
    for bag in evidence_bags:
        if not isinstance(bag, Mapping):
            continue
        family = str(bag.get("diagnostic_family") or "").strip()
        if not family:
            continue
        out.append(
            compose_diagnostic_contract_v1(
                store_slug=store_slug,
                family=family,
                evidence_bag=bag,
                subject_type=str(bag.get("subject_type") or "product"),
                subject_id=str(bag.get("subject_id") or ""),
            )
        )
    return out


__all__ = [
    "DEFAULT_TTL_HOURS",
    "DEFAULT_WINDOW_DAYS",
    "compose_diagnostic_contract_v1",
    "compose_store_diagnostics_v1",
]
