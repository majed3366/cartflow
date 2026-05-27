# -*- coding: utf-8 -*-
"""
Continuation decision trace v1 — explain reason→path→template for merchants and ops.

Read-only on WhatsApp transport; enriches decisions and behavioral/dashboard fields.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional

log = logging.getLogger("cartflow")

CHOSEN_PATH_PRICE = "price_handling"
CHOSEN_PATH_SHIPPING = "shipping_handling"
CHOSEN_PATH_QUALITY = "quality_handling"
CHOSEN_PATH_WARRANTY = "warranty_handling"
CHOSEN_PATH_CHECKOUT = "checkout_handling"
CHOSEN_PATH_FALLBACK = "fallback"

_REASON_TO_PATH: dict[str, str] = {
    "price": CHOSEN_PATH_PRICE,
    "price_high": CHOSEN_PATH_PRICE,
    "shipping": CHOSEN_PATH_SHIPPING,
    "shipping_cost": CHOSEN_PATH_SHIPPING,
    "delivery": CHOSEN_PATH_SHIPPING,
    "delivery_time": CHOSEN_PATH_SHIPPING,
    "quality": CHOSEN_PATH_QUALITY,
    "quality_uncertainty": CHOSEN_PATH_QUALITY,
    "warranty": CHOSEN_PATH_WARRANTY,
}

_EXPLANATION_AR: dict[str, str] = {
    CHOSEN_PATH_PRICE: "اختار النظام هذا الرد لأن الاعتراض = السعر",
    CHOSEN_PATH_SHIPPING: "اختار النظام هذا الرد لأن الاعتراض = الشحن",
    CHOSEN_PATH_QUALITY: "اختار النظام هذا الرد لأن الاعتراض = الجودة",
    CHOSEN_PATH_WARRANTY: "اختار النظام هذا الرد لأن الاعتراض = الضمان",
    CHOSEN_PATH_CHECKOUT: "اختار النظام هذا الرد لأن العميل جاهز لإكمال الطلب",
    CHOSEN_PATH_FALLBACK: "اختار النظام رداً عاماً — لم يُحدَّد اعتراض واضح",
}

_ACTION_TEMPLATE: dict[str, str] = {
    "send_checkout_link": "checkout_link",
    "resend_checkout_link": "checkout_link_resend",
    "send_cheaper_alternative": "cheaper_alternative",
    "explain_shipping": "explain_shipping",
    "explain_delivery": "explain_delivery",
    "explain_warranty": "explain_warranty",
    "explain_price": "explain_price",
    "explain_quality": "explain_quality",
    "reassurance_followup": "reassurance_followup",
    "graceful_exit": "graceful_exit",
    "escalate_to_human": "escalate_to_human",
    "wait_for_customer_reply": "wait",
}


def normalize_reason_tag_for_trace(reason_tag: str) -> str:
    rt = (reason_tag or "").strip().lower()
    if not rt:
        return ""
    if rt in _REASON_TO_PATH:
        return rt
    if rt.startswith("price"):
        return "price"
    if rt in ("shipping_cost",):
        return "shipping"
    if rt in ("quality_uncertainty",):
        return "quality"
    return rt


def resolve_chosen_path(
    reason_tag: str,
    *,
    action: str,
    contextual_intent: str = "",
    base_intent: str = "",
    lifecycle_intent: str = "",
) -> str:
    """Map abandonment reason + continuation action to a stable chosen_path label."""
    del lifecycle_intent
    rt = normalize_reason_tag_for_trace(reason_tag)
    if rt in _REASON_TO_PATH:
        return _REASON_TO_PATH[rt]
    act = (action or "").strip()
    ctx = (contextual_intent or "").strip()
    if act in ("explain_shipping", "explain_delivery") or ctx in (
        "asks_shipping_detail",
        "asks_delivery_detail",
        "confirmation_after_shipping",
    ):
        return CHOSEN_PATH_SHIPPING
    if act == "explain_quality" or ctx == "asks_quality_detail":
        return CHOSEN_PATH_QUALITY
    if act == "explain_price" or ctx in (
        "asks_price_detail",
        "wants_cheaper_alternative",
        "yes_to_cheaper_alternative",
    ):
        return CHOSEN_PATH_PRICE
    if act in ("send_checkout_link", "resend_checkout_link") or ctx in (
        "ready_for_checkout",
        "wants_checkout_link",
    ):
        return CHOSEN_PATH_CHECKOUT
    if act == "explain_warranty" or ctx == "asks_warranty_detail":
        return CHOSEN_PATH_WARRANTY
    if act == "wait_for_customer_reply" and ctx == "unknown_reply":
        return CHOSEN_PATH_FALLBACK
    if base_intent == "unknown_reply":
        return CHOSEN_PATH_FALLBACK
    return CHOSEN_PATH_FALLBACK


def template_name_for_action(action: str, *, chosen_path: str = "") -> str:
    act = (action or "").strip()
    name = _ACTION_TEMPLATE.get(act, act or "unknown")
    if chosen_path == CHOSEN_PATH_PRICE and name == "reassurance_followup":
        return "price_reassurance_v1"
    if chosen_path == CHOSEN_PATH_SHIPPING and name == "reassurance_followup":
        return "shipping_reassurance_v1"
    if chosen_path == CHOSEN_PATH_QUALITY and name == "reassurance_followup":
        return "quality_reassurance_v1"
    return name


def fallback_used_for_vars(
    vars_map: Optional[Mapping[str, Any]],
    *,
    chosen_path: str,
    action: str = "",
) -> bool:
    if chosen_path == CHOSEN_PATH_FALLBACK:
        return True
    act = (action or "").strip()
    if act == "send_cheaper_alternative" and vars_map:
        if str(vars_map.get("cheaper_reply_mode") or "").strip().lower() == "fallback":
            return True
        if str(vars_map.get("cheaper_fallback_reason") or "").strip():
            return True
    return False


def dashboard_explanation_ar(reason_tag: str, chosen_path: str) -> str:
    rt = normalize_reason_tag_for_trace(reason_tag)
    if rt in _REASON_TO_PATH:
        path = _REASON_TO_PATH[rt]
        return _EXPLANATION_AR.get(path, _EXPLANATION_AR[CHOSEN_PATH_FALLBACK])
    return _EXPLANATION_AR.get(chosen_path, _EXPLANATION_AR[CHOSEN_PATH_FALLBACK])


def continuation_explanation_for_dashboard(behavioral: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(behavioral, dict):
        return ""
    direct = str(behavioral.get("continuation_dashboard_explanation_ar") or "").strip()
    if direct:
        return direct
    cp = str(behavioral.get("continuation_chosen_path") or "").strip()
    rt = str(behavioral.get("continuation_trace_reason_tag") or "").strip()
    if cp:
        return dashboard_explanation_ar(rt, cp)
    return ""


@dataclass(frozen=True)
class ContinuationTraceV1:
    recovery_key: str
    reason_tag: str
    customer_reply: str
    chosen_path: str
    template_name: str
    fallback_used: bool
    next_state: str
    store_slug: str

    def timeline_source_suffix(self, base_source: str) -> str:
        """Compact trace encoded in timeline ``source`` (≤128 chars) without new statuses."""
        base = (base_source or "continuation").strip()[:48]
        cp = (self.chosen_path or "")[:28]
        tn = (self.template_name or "")[:24]
        fb = "1" if self.fallback_used else "0"
        return f"{base}|cp={cp}|tn={tn}|fb={fb}"[:128]

    def behavioral_patch(self) -> dict[str, Any]:
        return {
            "continuation_chosen_path": self.chosen_path,
            "continuation_template_name": self.template_name,
            "continuation_fallback_used": bool(self.fallback_used),
            "continuation_dashboard_explanation_ar": dashboard_explanation_ar(
                self.reason_tag, self.chosen_path
            ),
            "continuation_trace_reason_tag": (self.reason_tag or "").strip()[:64],
        }


def build_continuation_trace_v1(
    *,
    recovery_key: str = "",
    reason_tag: str = "",
    customer_reply: str = "",
    action: str = "",
    contextual_intent: str = "",
    base_intent: str = "",
    lifecycle_intent: str = "",
    continuation_state: str = "",
    store_slug: str = "",
    vars_map: Optional[Mapping[str, Any]] = None,
) -> ContinuationTraceV1:
    chosen = resolve_chosen_path(
        reason_tag,
        action=action,
        contextual_intent=contextual_intent,
        base_intent=base_intent,
        lifecycle_intent=lifecycle_intent,
    )
    template = template_name_for_action(action, chosen_path=chosen)
    fb = fallback_used_for_vars(vars_map, chosen_path=chosen, action=action)
    return ContinuationTraceV1(
        recovery_key=(recovery_key or "").strip()[:512],
        reason_tag=(reason_tag or "").strip()[:64],
        customer_reply=(customer_reply or "").strip()[:500],
        chosen_path=chosen,
        template_name=template,
        fallback_used=fb,
        next_state=(continuation_state or "").strip()[:64],
        store_slug=(store_slug or "").strip()[:255],
    )


def log_continuation_trace(trace: ContinuationTraceV1) -> None:
    fb = "true" if trace.fallback_used else "false"
    lines = [
        "[CONTINUATION TRACE]",
        f"recovery_key={trace.recovery_key or '-'}",
        f"reason_tag={trace.reason_tag or '-'}",
        f"customer_reply={trace.customer_reply[:120] or '-'}",
        f"chosen_path={trace.chosen_path}",
        f"template_name={trace.template_name}",
        f"fallback_used={fb}",
        f"next_state={trace.next_state or '-'}",
        f"store_slug={trace.store_slug or '-'}",
    ]
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def enrich_continuation_decision(
    decision: Any,
    *,
    reason_tag: str,
    customer_reply: str,
    vars_map: Optional[Mapping[str, Any]] = None,
    recovery_key: str = "",
    store_slug: str = "",
) -> Any:
    """Attach trace fields to ContinuationDecision (dataclass replace)."""
    from dataclasses import replace

    trace = build_continuation_trace_v1(
        recovery_key=recovery_key,
        reason_tag=reason_tag,
        customer_reply=customer_reply,
        action=getattr(decision, "action", ""),
        contextual_intent=getattr(decision, "contextual_intent", ""),
        base_intent=getattr(decision, "base_intent", ""),
        lifecycle_intent=getattr(decision, "lifecycle_intent", ""),
        continuation_state=getattr(decision, "continuation_state", ""),
        store_slug=store_slug,
        vars_map=vars_map,
    )
    expl = dashboard_explanation_ar(reason_tag, trace.chosen_path)
    return replace(
        decision,
        chosen_path=trace.chosen_path,
        template_name=trace.template_name,
        fallback_used=trace.fallback_used,
        dashboard_explanation_ar=expl,
    )


__all__ = [
    "CHOSEN_PATH_FALLBACK",
    "CHOSEN_PATH_PRICE",
    "CHOSEN_PATH_QUALITY",
    "CHOSEN_PATH_SHIPPING",
    "ContinuationTraceV1",
    "build_continuation_trace_v1",
    "continuation_explanation_for_dashboard",
    "dashboard_explanation_ar",
    "enrich_continuation_decision",
    "log_continuation_trace",
    "normalize_reason_tag_for_trace",
    "resolve_chosen_path",
    "template_name_for_action",
]
