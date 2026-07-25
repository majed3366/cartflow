# -*- coding: utf-8 -*-
"""
Gate 2D — Business Domain Normalization.

Operational Truth → Business Domains (before Candidate Decisions).
Surfaces consume domain summaries; composers consume domain signals — not raw counters.
"""
from __future__ import annotations

from typing import Any, Mapping

DOMAIN_STORE_HEALTH = "store_health"
DOMAIN_RECOVERY = "recovery"
DOMAIN_PRODUCTS = "products"
DOMAIN_PRICING = "pricing"
DOMAIN_SHIPPING = "shipping"
DOMAIN_CUSTOMER_BEHAVIOUR = "customer_behaviour"
DOMAIN_COMMUNICATION = "communication"
DOMAIN_REVENUE = "revenue"
DOMAIN_OPERATIONS = "operations"

ALL_BUSINESS_DOMAINS_V1 = (
    DOMAIN_STORE_HEALTH,
    DOMAIN_RECOVERY,
    DOMAIN_PRODUCTS,
    DOMAIN_PRICING,
    DOMAIN_SHIPPING,
    DOMAIN_CUSTOMER_BEHAVIOUR,
    DOMAIN_COMMUNICATION,
    DOMAIN_REVENUE,
    DOMAIN_OPERATIONS,
)

DOMAIN_LABEL_AR = {
    DOMAIN_STORE_HEALTH: "صحة المتجر",
    DOMAIN_RECOVERY: "الاسترجاع",
    DOMAIN_PRODUCTS: "المنتجات",
    DOMAIN_PRICING: "التسعير",
    DOMAIN_SHIPPING: "الشحن",
    DOMAIN_CUSTOMER_BEHAVIOUR: "سلوك العملاء",
    DOMAIN_COMMUNICATION: "التواصل",
    DOMAIN_REVENUE: "الإيرادات",
    DOMAIN_OPERATIONS: "التشغيل",
}

ROOT_MISSING_CONTACT = "recovery:missing_contact"
ROOT_WAITING_INTERVENTION = "recovery:waiting_intervention"
ROOT_STORE_CONNECTION = "store_health:connection"
ROOT_PRODUCT_PREFIX = "products:"
ROOT_PRICING_PREFIX = "pricing:"
ROOT_SHIPPING_PREFIX = "shipping:"
ROOT_BEHAVIOUR_PREFIX = "customer_behaviour:"
ROOT_COMMUNICATION_PREFIX = "communication:"
ROOT_REVENUE_PREFIX = "revenue:"
ROOT_OPERATIONS_PREFIX = "operations:"

DOMAIN_COMPOSITION_VERSION_V1 = "business_domain_composition_v1"


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _norm(v: Any) -> str:
    return str(v or "").strip().lower()


def _empty_domain(domain_id: str) -> dict[str, Any]:
    return {
        "domain_id": domain_id,
        "domain_ar": DOMAIN_LABEL_AR.get(domain_id, domain_id),
        "has_attention": False,
        "executive_summary_ar": "لا إجراء مطلوب.",
        "signals": [],
        "root_causes": [],
        "finding_ids": [],
    }


def map_finding_to_domain_v1(finding: Mapping[str, Any]) -> str:
    ftype = _norm(finding.get("finding_type") or finding.get("type"))
    blob = " ".join(
        [
            ftype,
            _norm(finding.get("title")),
            _norm(finding.get("merchant_statement_ar")),
            " ".join(str(x) for x in (finding.get("tags") or [])),
        ]
    )
    if "missing_contact" in ftype or "no_phone" in blob:
        return DOMAIN_RECOVERY
    if any(t in blob for t in ("shipping", "شحن", "delivery", "توصيل")):
        return DOMAIN_SHIPPING
    if any(t in blob for t in ("pricing", "price", "سعر", "تسعير", "cost")):
        return DOMAIN_PRICING
    if any(
        t in ftype
        for t in (
            "high_interest_low_purchase",
            "low_product_interest",
            "repeated_interest",
            "return_without_purchase",
        )
    ):
        return DOMAIN_PRODUCTS
    if "dominant_hesitation" in ftype or "hesitation" in ftype or "سلوك" in blob:
        return DOMAIN_CUSTOMER_BEHAVIOUR
    if any(
        t in ftype for t in ("whatsapp", "recovery_channel", "message_timing", "communication")
    ) or "whatsapp" in blob:
        return DOMAIN_COMMUNICATION
    if "traffic" in ftype or "conversion" in ftype or "revenue" in ftype:
        return DOMAIN_REVENUE
    return DOMAIN_STORE_HEALTH


def root_cause_for_finding_v1(finding: Mapping[str, Any], *, store_slug: str) -> str:
    domain = map_finding_to_domain_v1(finding)
    ftype = _norm(finding.get("finding_type") or finding.get("type"))
    fid = str(finding.get("finding_id") or "").strip() or "unknown"
    product = ""
    entity = finding.get("entity") if isinstance(finding.get("entity"), Mapping) else {}
    if isinstance(entity, Mapping):
        product = str(entity.get("product_id") or entity.get("id") or "").strip()
    if not product:
        product = str(finding.get("product_id") or "").strip()

    if domain == DOMAIN_RECOVERY and "missing_contact" in ftype:
        return ROOT_MISSING_CONTACT
    if domain == DOMAIN_PRODUCTS:
        return f"{ROOT_PRODUCT_PREFIX}{product or fid}:{ftype or 'product'}"
    if domain == DOMAIN_PRICING:
        return f"{ROOT_PRICING_PREFIX}{product or fid}"
    if domain == DOMAIN_SHIPPING:
        return f"{ROOT_SHIPPING_PREFIX}{product or fid}"
    if domain == DOMAIN_CUSTOMER_BEHAVIOUR:
        return f"{ROOT_BEHAVIOUR_PREFIX}{product or fid}:{ftype or 'behaviour'}"
    if domain == DOMAIN_COMMUNICATION:
        return f"{ROOT_COMMUNICATION_PREFIX}{ftype or fid}"
    if domain == DOMAIN_REVENUE:
        return f"{ROOT_REVENUE_PREFIX}{ftype or fid}"
    if domain == DOMAIN_OPERATIONS:
        return f"{ROOT_OPERATIONS_PREFIX}{ftype or fid}"
    return f"store_health:{store_slug}:{ftype or fid}"


def normalize_business_domains_v1(
    counters: Mapping[str, Any] | None,
    findings: list[Mapping[str, Any]] | None,
    *,
    store_slug: str = "",
) -> dict[str, Any]:
    """
    Normalize operational truth + findings into business domains.

    Does not create decisions. Emits domain signals and root-cause keys only.
    """
    slug = str(store_slug or (counters or {}).get("store_slug") or "").strip()
    ctr = counters if isinstance(counters, Mapping) else {}
    finds = [f for f in (findings or []) if isinstance(f, Mapping)]

    domains: dict[str, dict[str, Any]] = {
        d: _empty_domain(d) for d in ALL_BUSINESS_DOMAINS_V1
    }
    root_causes: list[dict[str, Any]] = []

    available = bool(ctr.get("available"))
    no_phone = _as_int(ctr.get("no_phone_total"))
    waiting = _as_int(ctr.get("waiting_total"))
    engaged = _as_int(ctr.get("engaged_total"))
    active = _as_int(ctr.get("active_total"))

    if available and no_phone > 0:
        rc = ROOT_MISSING_CONTACT
        domains[DOMAIN_RECOVERY]["has_attention"] = True
        domains[DOMAIN_RECOVERY]["signals"].append(
            {
                "signal_id": "ot_no_phone",
                "kind": "recoverability_gap",
                "magnitude": no_phone,
                "root_cause_key": rc,
            }
        )
        domains[DOMAIN_RECOVERY]["root_causes"].append(rc)
        domains[DOMAIN_RECOVERY]["executive_summary_ar"] = (
            "أداء الاسترجاع انخفض — فرص الإيراد المعلّقة تتأثر."
        )
        root_causes.append(
            {
                "root_cause_key": rc,
                "domain_id": DOMAIN_RECOVERY,
                "source": "operational_truth",
                "magnitude": no_phone,
            }
        )

    # Waiting that is mostly no-phone is the same root cause — do not fork.
    waiting_is_missing_contact = (
        available and waiting > 0 and no_phone > 0 and waiting <= no_phone + 1
    )
    merchant_waiting_needed = engaged > 0 or (waiting > no_phone and waiting >= 5)
    if available and waiting > 0 and merchant_waiting_needed and not waiting_is_missing_contact:
        rc = ROOT_WAITING_INTERVENTION
        domains[DOMAIN_OPERATIONS]["has_attention"] = True
        domains[DOMAIN_OPERATIONS]["signals"].append(
            {
                "signal_id": "ot_waiting_intervention",
                "kind": "waiting_recovery_work",
                "magnitude": max(waiting - no_phone, engaged, waiting),
                "root_cause_key": rc,
            }
        )
        domains[DOMAIN_OPERATIONS]["root_causes"].append(rc)
        domains[DOMAIN_OPERATIONS]["executive_summary_ar"] = (
            "مسار الاسترجاع يحتاج تدخلاً لإبقاء فرص إتمام الشراء مفتوحة."
        )
        root_causes.append(
            {
                "root_cause_key": rc,
                "domain_id": DOMAIN_OPERATIONS,
                "source": "operational_truth",
                "magnitude": waiting,
            }
        )

    # Store health — business condition only; never restates Today's Decision.
    recovered = _as_int(ctr.get("recovered_total") or ctr.get("recovered_today"))
    if not available:
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "لا توجد أدلة كافية لتقييم صحة المتجر بعد."
        )
    elif domains[DOMAIN_RECOVERY]["has_attention"]:
        domains[DOMAIN_STORE_HEALTH]["has_attention"] = True
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "أداء الاسترجاع انخفض اليوم."
        )
        domains[DOMAIN_STORE_HEALTH]["signals"].append(
            {"signal_id": "attention_via_domains", "kind": "store_attention"}
        )
    elif domains[DOMAIN_OPERATIONS]["has_attention"]:
        domains[DOMAIN_STORE_HEALTH]["has_attention"] = True
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "نشاط الشراء يحتاج متابعة لإتمامه."
        )
    elif recovered > 0 and active > 0:
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "نشاط الشراء مستقر — أداء الاسترجاع يتحسّن."
        )
    elif active > 0:
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "المتجر يعمل بشكل طبيعي."
        )
    else:
        domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"] = (
            "لا توجد مشكلات حرجة ظاهرة — بانتظار نشاط كافٍ."
        )

    # Communication — executive communication facts (not decisions).
    if available and (waiting > 0 or no_phone > 0):
        domains[DOMAIN_COMMUNICATION]["signals"].append(
            {
                "signal_id": "comm_followup_facts",
                "kind": "communication_facts",
                "needs_follow_up": waiting > 0,
                "no_phone": no_phone > 0,
            }
        )
        if waiting > 0 and no_phone > 0:
            domains[DOMAIN_COMMUNICATION]["executive_summary_ar"] = (
                f"{waiting} عملاء بانتظار المتابعة · {no_phone} بلا رقم تواصل."
            )
            domains[DOMAIN_COMMUNICATION]["has_attention"] = True
        elif waiting > 0:
            domains[DOMAIN_COMMUNICATION]["executive_summary_ar"] = (
                f"{waiting} عملاء بانتظار المتابعة."
            )
            domains[DOMAIN_COMMUNICATION]["has_attention"] = True
        elif no_phone > 0:
            domains[DOMAIN_COMMUNICATION]["executive_summary_ar"] = (
                f"{no_phone} سلة بلا رقم تواصل."
            )
            domains[DOMAIN_COMMUNICATION]["has_attention"] = True

    for finding in finds:
        domain_id = map_finding_to_domain_v1(finding)
        rc = root_cause_for_finding_v1(finding, store_slug=slug)
        fid = str(finding.get("finding_id") or "").strip()
        d = domains[domain_id]
        d["finding_ids"].append(fid)
        if rc not in d["root_causes"]:
            d["root_causes"].append(rc)
        d["signals"].append(
            {
                "signal_id": f"finding:{fid}",
                "kind": "finding",
                "finding_id": fid,
                "finding_type": finding.get("finding_type"),
                "root_cause_key": rc,
            }
        )
        # Attention only when FDE says DECISION — domains don't invent decisions.
        dec = finding.get("merchant_decision_v1")
        if isinstance(dec, Mapping) and bool(dec.get("has_decision")):
            d["has_attention"] = True
            if d["executive_summary_ar"] in {"", "لا إجراء مطلوب."}:
                title = str(
                    dec.get("decision") or finding.get("title") or ""
                ).strip()
                d["executive_summary_ar"] = (
                    "يوجد أمر يحتاج مراجعة — راجع قرارات اليوم."
                    if not title
                    else "يوجد أمر يحتاج مراجعة — راجع قرارات اليوم."
                )
        root_causes.append(
            {
                "root_cause_key": rc,
                "domain_id": domain_id,
                "source": "finding",
                "finding_id": fid,
            }
        )

    # Carts — executive ops summary only (counts OK; no recommendations).
    if available and waiting > 0:
        carts_summary = f"{waiting} سلة تحتاج متابعة."
    elif available and no_phone > 0:
        carts_summary = f"{no_phone} سلة خارج مسار المتابعة حالياً."
    elif available and recovered > 0:
        carts_summary = f"{recovered} سلة استُعيدت — نشاط الاسترجاع مستقر."
    elif available and active > 0:
        carts_summary = "نشاط الاسترجاع مستقر."
    else:
        carts_summary = "لا توجد سلال تحتاج متابعة حالياً."

    return {
        "ok": True,
        "store_slug": slug,
        "composition_version": DOMAIN_COMPOSITION_VERSION_V1,
        "gate_2d_business_domains": True,
        "gate_2e_executive_business": True,
        "domains": domains,
        "domain_order": list(ALL_BUSINESS_DOMAINS_V1),
        "root_causes": root_causes,
        "signals": {
            "available": available,
            "no_phone_total": no_phone,
            "waiting_total": waiting,
            "engaged_total": engaged,
            "active_total": active,
            "recovered_total": recovered,
            "waiting_collapsed_into_missing_contact": waiting_is_missing_contact,
            "merchant_waiting_needed": merchant_waiting_needed,
        },
        # Gate 2F — raw domain teasers are inputs only; Store Executive overwrites for Home.
        "home_teasers": {
            "store_health_ar": domains[DOMAIN_STORE_HEALTH]["executive_summary_ar"],
            "store_health_attention": domains[DOMAIN_STORE_HEALTH]["has_attention"],
            "carts_ar": carts_summary,
            "communication_ar": domains[DOMAIN_COMMUNICATION]["executive_summary_ar"],
            "communication_attention": domains[DOMAIN_COMMUNICATION]["has_attention"],
        },
    }


__all__ = [
    "ALL_BUSINESS_DOMAINS_V1",
    "DOMAIN_COMPOSITION_VERSION_V1",
    "DOMAIN_LABEL_AR",
    "ROOT_MISSING_CONTACT",
    "ROOT_WAITING_INTERVENTION",
    "map_finding_to_domain_v1",
    "normalize_business_domains_v1",
    "root_cause_for_finding_v1",
]
