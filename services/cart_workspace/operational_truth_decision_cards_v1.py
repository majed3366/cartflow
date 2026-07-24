# -*- coding: utf-8 -*-
"""
Gate 2A — Decision cards from existing operational truth only.

No Product Intelligence. No prediction. Counts → merchant decisions.
"""
from __future__ import annotations

from typing import Any, Mapping


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _confidence_ar(level: str) -> str:
    raw = (level or "").strip().lower()
    if raw in {"high", "مرتفع", "strong"}:
        return "مرتفع"
    if raw in {"medium", "متوسط", "moderate"}:
        return "متوسط"
    if raw in {"low", "منخفض", "weak"}:
        return "منخفض"
    return "غير متاح"


def _load_store_counts(store_slug: str) -> dict[str, int]:
    slug = _norm(store_slug)
    if not slug:
        return {}
    try:
        from services.dashboard_store_context import (  # noqa: PLC0415
            dashboard_canonical_store_row,
        )
        from services.dashboard_counter_totals_v1 import (  # noqa: PLC0415
            build_merchant_cart_counter_totals,
        )

        store_row = dashboard_canonical_store_row(slug)
        if store_row is None:
            return {}
        payload = build_merchant_cart_counter_totals(store_row)
        return dict(payload.counts.to_counts_dict())
    except Exception:  # noqa: BLE001
        return {}


def card_no_phone_v1(*, count: int) -> dict[str, Any] | None:
    n = _as_int(count)
    if n <= 0:
        return None
    decision = "راجع سلال بلا رقم تواصل"
    why = f"{n} سلة لا يمكن متابعتها لأن رقم العميل غير متوفر."
    evidence = f"{n} سلة نشطة بلا رقم تواصل صالح (عدّاد السلال المعتمد)."
    action = "حسّن جمع رقم العميل وراجع السلال المتأثرة."
    return {
        "decision_id": "ops-truth:no_phone",
        "card_kind": "operational_truth",
        "decision_class": "operational_truth",
        "constitution_v1": True,
        "has_decision": True,
        "decision_status": "DECISION",
        "title_ar": decision,
        "decision_ar": decision,
        "why_ar": why,
        "evidence_summary": evidence,
        "decision_confidence": "high",
        "decision_confidence_ar": _confidence_ar("high"),
        "required_merchant_action": action,
        "action_label_ar": action,
        "view_details_href": "#carts?tab=nophone",
        "view_details_ar": "عرض التفاصيل",
        "explanation": {
            "why_here": why,
            "cartflow_did": "نحتفظ بالحالات دون إرسال غير قابل للتنفيذ.",
            "why_stopped": "",
            "expected_after": "زيادة السلال القابلة للمتابعة.",
        },
        "required_action": "review_no_phone_carts",
        "governing_reason": "merchant_store_cart_counts.no_phone_total",
        "admission_rule_id": "gate_2a_operational_truth",
        "order_key": "0-ops-no-phone",
        "status": "open",
        "commands_enabled": False,
        "evidence_refs": ["merchant_store_cart_counts.no_phone_total"],
    }


def card_waiting_customers_v1(*, count: int) -> dict[str, Any] | None:
    n = _as_int(count)
    if n <= 0:
        return None
    decision = "تابع العملاء المنتظرين"
    why = f"{n} سلة بانتظار المتابعة التشغيلية."
    evidence = f"{n} سلة في حالة الانتظار (عدّاد السلال المعتمد)."
    action = "راجع سلال الانتظار واتخذ الخطوة التشغيلية التالية."
    return {
        "decision_id": "ops-truth:waiting",
        "card_kind": "operational_truth",
        "decision_class": "operational_truth",
        "constitution_v1": True,
        "has_decision": True,
        "decision_status": "DECISION",
        "title_ar": decision,
        "decision_ar": decision,
        "why_ar": why,
        "evidence_summary": evidence,
        "decision_confidence": "high",
        "decision_confidence_ar": _confidence_ar("high"),
        "required_merchant_action": action,
        "action_label_ar": action,
        "view_details_href": "#carts",
        "view_details_ar": "عرض التفاصيل",
        "explanation": {
            "why_here": why,
            "cartflow_did": "CartFlow يراقب سلال الانتظار.",
            "why_stopped": "",
            "expected_after": "تقليل السلال المعلقة.",
        },
        "required_action": "review_waiting_carts",
        "governing_reason": "merchant_store_cart_counts.waiting_total",
        "admission_rule_id": "gate_2a_operational_truth",
        "order_key": "0-ops-waiting",
        "status": "open",
        "commands_enabled": False,
        "evidence_refs": ["merchant_store_cart_counts.waiting_total"],
    }


def list_operational_truth_decision_cards_v1(
    store_slug: str,
    *,
    existing_cards: list[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build Decision cards from store counters when counts are real (>0).

    Skips a card when an existing FDE/ops card already covers the same concern.
    """
    counts = _load_store_counts(store_slug)
    if not counts:
        return []

    existing = list(existing_cards or [])
    existing_blob = " ".join(
        [
            _norm(c.get("finding_type"))
            + " "
            + _norm(c.get("decision_id"))
            + " "
            + _norm(c.get("governing_reason"))
            for c in existing
            if isinstance(c, Mapping)
        ]
    ).lower()

    out: list[dict[str, Any]] = []
    no_phone = _as_int(counts.get("no_phone_total"))
    waiting = _as_int(counts.get("waiting_total"))

    if no_phone > 0 and "missing_contact" not in existing_blob and "no_phone" not in existing_blob:
        card = card_no_phone_v1(count=no_phone)
        if card:
            out.append(card)

    # Waiting: emit when there is waiting beyond the no-phone set (or no no-phone).
    if waiting > 0 and "ops-truth:waiting" not in existing_blob:
        if no_phone <= 0 or waiting > no_phone:
            card = card_waiting_customers_v1(count=waiting)
            if card:
                out.append(card)

    return out


__all__ = [
    "card_no_phone_v1",
    "card_waiting_customers_v1",
    "list_operational_truth_decision_cards_v1",
]
