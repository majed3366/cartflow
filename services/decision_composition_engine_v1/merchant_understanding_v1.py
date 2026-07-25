# -*- coding: utf-8 -*-
"""
Gate 2X — Merchant Understanding V1.

Constitutional publication layer above Business Understanding / Store Executive.

Business Understanding explains the store.
Merchant Understanding explains what the merchant should care about.

Before any executive statement is published:

1. Does this help the merchant understand the business?
2. Is this about the store rather than CartFlow?
3. Does it naturally lead to a business decision?
4. Would a merchant act differently after reading it?

If the answer is "No", suppress (or replace with a safe understanding fallback).

Guiding outcome: "I understand my store." — not "I understand what CartFlow is doing."
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

from services.decision_composition_engine_v1.store_executive_understanding_v1 import (
    is_system_centric_executive_text_v1,
    sanitize_executive_text_v1,
)

MERCHANT_UNDERSTANDING_VERSION_V1 = "merchant_understanding_v1"

# Preferred executive language (Arabic) — store performance, not CartFlow internals.
PREFERRED_HEALTH_LIMITED_AR = "فرص استعادة المبيعات محدودة اليوم."
PREFERRED_PURCHASE_SLOW_AR = "إتمام الشراء أبطأ من المعتاد."
PREFERRED_NO_CRITICAL_AR = "لا توجد مشكلات تجارية حرجة ظاهرة."
PREFERRED_INTEREST_GROWING_AR = "اهتمام العملاء بالمنتجات يتزايد."
PREFERRED_SHIPPING_HURTS_AR = "يبدو أن الشحن يضعف إتمام الشراء."
PREFERRED_CARTS_NEED_ATTENTION_AR = "سلال العملاء تحتاج متابعة نشطة."
PREFERRED_CARTS_STABLE_AR = "تقدّم سلال العملاء مستقر."
PREFERRED_COMM_ATTENTION_AR = "تواصل العملاء يحتاج انتباهاً."
PREFERRED_COMM_HEALTHY_AR = "تواصل العملاء يسير بشكل طبيعي."
PREFERRED_DECISION_CHECKOUT_AR = "راجع تجربة إتمام الشراء ومتابعة العملاء."

_AVOID_TOKENS = (
    "scheduler",
    "dispatch",
    "cartflow",
    "queue",
    "validation",
    "waiting_total",
    "no_phone_total",
    "عدّاد",
    "مجدول",
    "محرك الاسترجاع",
    "حالة المحرك",
    "infrastructure",
    "module",
    "تحقق داخلي",
    "قائمة الانتظار",
)

_QUEUE_COUNT_RE = re.compile(
    r"^\d+\s*(سلة|سلال|عميل|عملاء)\b",
    re.UNICODE,
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def violates_merchant_understanding_language_v1(text: str) -> bool:
    """True when text uses forbidden technical / CartFlow-process language."""
    raw = _norm(text)
    if not raw:
        return False
    low = raw.lower()
    if any(tok in low for tok in _AVOID_TOKENS):
        return True
    if is_system_centric_executive_text_v1(raw):
        return True
    if _QUEUE_COUNT_RE.search(raw):
        # Leading queue/customer counts — ops report, not understanding.
        return True
    return False


def evaluate_merchant_understanding_v1(
    text: str,
    *,
    surface: str = "home",
    leads_to_decision: bool = False,
    store_about: bool = True,
) -> dict[str, Any]:
    """
    Apply the four constitutional questions.

    Returns ``publish`` False when the statement must not reach the merchant.
    """
    cleaned = _norm(text)
    reasons: list[str] = []
    if not cleaned:
        return {
            "publish": False,
            "reasons": ["empty"],
            "helps_understand_business": False,
            "about_store_not_cartflow": False,
            "leads_to_business_decision": False,
            "merchant_would_act_differently": False,
        }

    about_store = store_about and not violates_merchant_understanding_language_v1(
        cleaned
    )
    helps = about_store
    # Status that confirms "no critical issues" still increases understanding.
    act_differently = True
    if cleaned in (PREFERRED_NO_CRITICAL_AR, PREFERRED_COMM_HEALTHY_AR, PREFERRED_CARTS_STABLE_AR):
        act_differently = False  # reassurance — still publish for understanding
    leads = bool(leads_to_decision) or surface in ("decisions", "workspace")
    if surface in ("health", "observations", "carts", "communication", "home"):
        # Understanding surfaces may publish without an immediate decision CTA.
        leads = leads or helps

    if not helps:
        reasons.append("does_not_help_understand_business")
    if not about_store:
        reasons.append("about_cartflow_or_internals")
    if surface in ("decisions", "workspace") and not (
        leads_to_decision or "راجع" in cleaned
    ):
        reasons.append("does_not_lead_to_business_decision")
        leads = False

    publish = bool(helps and about_store and (leads or surface not in ("decisions", "workspace")))
    if surface in ("decisions", "workspace"):
        publish = bool(helps and about_store and ("راجع" in cleaned or leads_to_decision))

    return {
        "publish": publish,
        "reasons": reasons,
        "helps_understand_business": helps,
        "about_store_not_cartflow": about_store,
        "leads_to_business_decision": leads,
        "merchant_would_act_differently": act_differently,
    }


def rewrite_for_merchant_understanding_v1(
    text: str,
    *,
    surface: str,
    fallback: str,
) -> str:
    """Map ops/queue phrasing into preferred understanding language."""
    cleaned = _norm(text)
    if not cleaned:
        return _norm(fallback)

    if _QUEUE_COUNT_RE.search(cleaned) or re.search(r"\d+\s*سلة\s*قيد\s*المتابعة", cleaned):
        if surface in ("carts", "home"):
            return PREFERRED_CARTS_NEED_ATTENTION_AR
        if surface == "communication":
            return PREFERRED_COMM_ATTENTION_AR

    if "بلا رقم" in cleaned or "مقيدة" in cleaned and "تواصل" in cleaned:
        if surface == "communication":
            return PREFERRED_COMM_ATTENTION_AR
        if surface in ("carts", "health", "home"):
            return PREFERRED_HEALTH_LIMITED_AR

    if "مسار الاسترجاع" in cleaned or "محرك" in cleaned:
        return PREFERRED_DECISION_CHECKOUT_AR if surface in ("decisions", "workspace") else PREFERRED_HEALTH_LIMITED_AR

    if violates_merchant_understanding_language_v1(cleaned):
        return sanitize_executive_text_v1(cleaned, fallback=fallback)

    # Soft prefer list alignments
    if "انخفض" in cleaned and "استرجاع" in cleaned:
        return PREFERRED_HEALTH_LIMITED_AR
    return cleaned


def publish_executive_statement_v1(
    text: str,
    *,
    surface: str,
    fallback: str,
    leads_to_decision: bool = False,
) -> dict[str, Any]:
    """Rewrite + evaluate; return final text or fallback when suppressed."""
    rewritten = rewrite_for_merchant_understanding_v1(
        text, surface=surface, fallback=fallback
    )
    verdict = evaluate_merchant_understanding_v1(
        rewritten,
        surface=surface,
        leads_to_decision=leads_to_decision,
    )
    if verdict["publish"]:
        return {
            "text_ar": rewritten,
            "published": True,
            "suppressed": False,
            "verdict": verdict,
            "source_text_ar": _norm(text),
        }
    safe = _norm(fallback) or PREFERRED_NO_CRITICAL_AR
    safe_verdict = evaluate_merchant_understanding_v1(
        safe, surface=surface, leads_to_decision=leads_to_decision
    )
    return {
        "text_ar": safe if safe_verdict["publish"] else PREFERRED_NO_CRITICAL_AR,
        "published": True,
        "suppressed": True,
        "verdict": verdict,
        "source_text_ar": _norm(text),
    }


def compose_business_understanding_v1(
    domains_pkg: Mapping[str, Any] | None,
    store_executive_pkg: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Explain the store (facts) — distinct from what the merchant should care about."""
    domains = {}
    signals = {}
    if isinstance(domains_pkg, Mapping):
        domains = (
            domains_pkg.get("domains")
            if isinstance(domains_pkg.get("domains"), Mapping)
            else {}
        )
        signals = (
            domains_pkg.get("signals")
            if isinstance(domains_pkg.get("signals"), Mapping)
            else {}
        )
    exec_pkg = store_executive_pkg if isinstance(store_executive_pkg, Mapping) else {}
    briefing = (
        exec_pkg.get("briefing") if isinstance(exec_pkg.get("briefing"), Mapping) else {}
    )
    teasers = (
        exec_pkg.get("home_teasers")
        if isinstance(exec_pkg.get("home_teasers"), Mapping)
        else {}
    )
    return {
        "ok": True,
        "schema": "business_understanding_v1",
        "responsibility": "explain_the_store",
        "domains": domains,
        "signals": {
            "available": bool(signals.get("available")),
            "has_active_carts": int(signals.get("active_total") or 0) > 0,
            "has_waiting_carts": int(signals.get("waiting_total") or 0) > 0,
            "has_phone_gap": int(signals.get("no_phone_total") or 0) > 0,
        },
        "store_facts_ar": {
            "health": _norm(teasers.get("store_health_ar")),
            "carts": _norm(teasers.get("carts_ar")),
            "communication": _norm(teasers.get("communication_ar")),
            "revenue": _norm(briefing.get("revenue_signal_ar")),
            "products": _norm(briefing.get("products_attention_ar")),
            "recovery": _norm(briefing.get("recovery_healthy_ar")),
        },
    }


def apply_merchant_understanding_to_decisions_v1(
    decisions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter/rewrite decision titles for merchant understanding."""
    published: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for raw in decisions:
        if not isinstance(raw, Mapping):
            continue
        d = dict(raw)
        title = _norm(
            d.get("executive_decision_ar")
            or d.get("merchant_decision")
            or d.get("title")
        )
        out = publish_executive_statement_v1(
            title,
            surface="decisions",
            fallback=PREFERRED_DECISION_CHECKOUT_AR,
            leads_to_decision=True,
        )
        d["merchant_decision"] = out["text_ar"]
        d["executive_decision_ar"] = out["text_ar"]
        d["title"] = out["text_ar"]
        d["gate_2x_merchant_understanding"] = True
        d["merchant_understanding_published"] = not out["suppressed"]
        if out["suppressed"]:
            suppressed.append(
                {
                    "decision_id": d.get("decision_id"),
                    "source_text_ar": out["source_text_ar"],
                    "reasons": (out.get("verdict") or {}).get("reasons") or [],
                }
            )
        # Soften why if it fails language rules.
        why = _norm(d.get("why"))
        if why and violates_merchant_understanding_language_v1(why):
            d["why"] = (
                "هذا يؤثر على فهم أداء المتجر وإتمام الشراء، "
                "ويستحق قراراً اليوم."
            )
        published.append(d)
    return published, suppressed


def compose_merchant_understanding_v1(
    business_understanding: Mapping[str, Any] | None,
    *,
    decisions: list[Mapping[str, Any]] | None = None,
    home_teasers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    What the merchant should care about — publication gate for Home / Workspace.
    """
    biz = business_understanding if isinstance(business_understanding, Mapping) else {}
    facts = (
        biz.get("store_facts_ar")
        if isinstance(biz.get("store_facts_ar"), Mapping)
        else {}
    )
    teasers_in = dict(home_teasers or {})

    health = publish_executive_statement_v1(
        _norm(teasers_in.get("store_health_ar") or facts.get("health")),
        surface="health",
        fallback=PREFERRED_NO_CRITICAL_AR,
    )
    carts = publish_executive_statement_v1(
        _norm(teasers_in.get("carts_ar") or facts.get("carts")),
        surface="carts",
        fallback=PREFERRED_CARTS_STABLE_AR,
    )
    comm = publish_executive_statement_v1(
        _norm(teasers_in.get("communication_ar") or facts.get("communication")),
        surface="communication",
        fallback=PREFERRED_COMM_HEALTHY_AR,
    )

    decs = [dict(d) for d in (decisions or []) if isinstance(d, Mapping)]
    decs, suppressed_decs = apply_merchant_understanding_to_decisions_v1(decs)
    top_title = ""
    if decs:
        top_title = _norm(decs[0].get("merchant_decision"))
    else:
        top_pub = publish_executive_statement_v1(
            _norm(teasers_in.get("decisions_top_title_ar")),
            surface="decisions",
            fallback="لا توجد أولوية قرار واضحة اليوم.",
            leads_to_decision=False,
        )
        # Empty portfolio — allow honest empty without forcing a fake decision.
        top_title = (
            top_pub["text_ar"]
            if top_pub["source_text_ar"]
            else "لا توجد أولوية قرار واضحة اليوم."
        )
        if not decs and not top_pub["source_text_ar"]:
            top_title = "لا توجد أولوية قرار واضحة اليوم."

    home_teasers_out = {
        **teasers_in,
        "store_health_ar": health["text_ar"],
        "carts_ar": carts["text_ar"],
        "communication_ar": comm["text_ar"],
        "decisions_top_title_ar": top_title,
        "merchant_understanding_gate": True,
    }

    suppressed_statements = []
    for label, pub in (
        ("health", health),
        ("carts", carts),
        ("communication", comm),
    ):
        if pub.get("suppressed"):
            suppressed_statements.append(
                {
                    "surface": label,
                    "source_text_ar": pub.get("source_text_ar"),
                    "reasons": (pub.get("verdict") or {}).get("reasons") or [],
                }
            )

    return {
        "ok": True,
        "version": MERCHANT_UNDERSTANDING_VERSION_V1,
        "gate_2x_merchant_understanding": True,
        "responsibility": "explain_what_merchant_should_care_about",
        "guiding_principle": "merchant_understands_store_not_cartflow",
        "page_questions": {
            "home": "What should I know about my business right now?",
            "decision_workspace": "What should I decide today, and why?",
            "carts": "What is happening to every customer cart?",
            "communication": "What happened during customer communication?",
            "settings": "How do I configure CartFlow?",
        },
        "home_teasers": home_teasers_out,
        "decisions": decs,
        "care_about_ar": {
            "business_now": health["text_ar"],
            "top_decision": top_title,
            "carts": carts["text_ar"],
            "communication": comm["text_ar"],
        },
        "suppressed_statements": suppressed_statements,
        "suppressed_decisions": suppressed_decs,
        "business_understanding_ref": "business_understanding_v1",
    }


def apply_merchant_understanding_package_v1(
    *,
    domains_pkg: Mapping[str, Any] | None,
    store_executive_pkg: Mapping[str, Any] | None,
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Full Gate 2X pass: Business Understanding → Merchant Understanding."""
    biz = compose_business_understanding_v1(domains_pkg, store_executive_pkg)
    teasers = {}
    if isinstance(store_executive_pkg, Mapping):
        teasers = (
            store_executive_pkg.get("home_teasers")
            if isinstance(store_executive_pkg.get("home_teasers"), Mapping)
            else {}
        )
    mu = compose_merchant_understanding_v1(
        biz, decisions=decisions, home_teasers=teasers
    )
    return {
        "business_understanding_v1": biz,
        "merchant_understanding_v1": mu,
        "home_teasers": mu.get("home_teasers") or {},
        "decisions": list(mu.get("decisions") or []),
    }


__all__ = [
    "MERCHANT_UNDERSTANDING_VERSION_V1",
    "PREFERRED_CARTS_NEED_ATTENTION_AR",
    "PREFERRED_COMM_HEALTHY_AR",
    "PREFERRED_DECISION_CHECKOUT_AR",
    "PREFERRED_HEALTH_LIMITED_AR",
    "PREFERRED_NO_CRITICAL_AR",
    "PREFERRED_PURCHASE_SLOW_AR",
    "apply_merchant_understanding_package_v1",
    "apply_merchant_understanding_to_decisions_v1",
    "compose_business_understanding_v1",
    "compose_merchant_understanding_v1",
    "evaluate_merchant_understanding_v1",
    "publish_executive_statement_v1",
    "rewrite_for_merchant_understanding_v1",
    "violates_merchant_understanding_language_v1",
]
