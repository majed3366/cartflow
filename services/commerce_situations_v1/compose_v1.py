# -*- coding: utf-8 -*-
"""
Commerce Situation Engine V1.

Many Business Facts → entity-bound commercial situations.
Never Theme-style one-bucket-per-type. Never invents PI / recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.commerce_situations_v1.contract_v1 import (
    COMMERCE_SITUATIONS_VERSION_V1,
    KIND_COMMUNICATION,
    KIND_INTEREST_WITHOUT_PURCHASE,
    KIND_PRODUCT_DEMAND,
    KIND_RECOVERY_OPPORTUNITY,
    KIND_SHIPPING_FRICTION,
    KIND_STORE_HEALTH,
    OWNER_COMMUNICATION,
    OWNER_DECISION_WORKSPACE,
    OWNER_HOME,
    empty_situation_shell_v1,
    validate_commerce_situation_v1,
)
from services.commerce_situations_v1.flag_v1 import commerce_situations_v1_enabled

_MIN_FACTS = 1
_MIN_CONFIDENCE = 40


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _conf_score(fact: Mapping[str, Any]) -> int:
    conf = fact.get("confidence") if isinstance(fact.get("confidence"), Mapping) else {}
    try:
        return int(conf.get("score") or 0)
    except (TypeError, ValueError):
        level = _norm(conf.get("level")).lower()
        return {"high": 80, "medium": 55, "low": 30}.get(level, 0)


def _subject(fact: Mapping[str, Any]) -> dict[str, str]:
    sub = fact.get("subject") if isinstance(fact.get("subject"), Mapping) else {}
    return {
        "kind": _norm(sub.get("kind")) or "store",
        "id": _norm(sub.get("id")) or "store",
        "name_ar": _norm(sub.get("name_ar")) or "المتجر",
    }


def _caps(fact: Mapping[str, Any]) -> list[str]:
    evid = fact.get("evidence") if isinstance(fact.get("evidence"), Mapping) else {}
    return [str(c) for c in list(evid.get("capability_ids") or []) if str(c).strip()]


def _classify_fact_kind_v1(fact: Mapping[str, Any]) -> Optional[str]:
    """
    Map a fact into a commercial situation kind.

    Conversion + repeat-return on the same product both become
    interest_without_purchase (one situation, many facts).
    """
    ft = _norm(fact.get("fact_type"))
    meaning = _norm(fact.get("business_meaning_ar"))
    caps = _caps(fact)

    if "shipping_stronger_than_price" in caps or "الشحن" in meaning:
        return KIND_SHIPPING_FRICTION
    if (
        "high_interest_low_conversion" in caps
        or "repeated_return_without_purchase" in caps
        or ft == "conversion"
        or "تحويل" in meaning
        or "يعودون" in meaning
        or "اهتمام" in meaning
    ):
        return KIND_INTEREST_WITHOUT_PURCHASE
    if ft == "recovery" or "استعادة" in meaning:
        return KIND_RECOVERY_OPPORTUNITY
    if ft == "communication" or "تواصل" in meaning:
        return KIND_COMMUNICATION
    if ft == "store_health" or "مشكلات تجارية" in meaning:
        return KIND_STORE_HEALTH
    if ft == "product_demand" or "جودة" in meaning:
        return KIND_PRODUCT_DEMAND
    return None


def _bucket_key(kind: str, subject: Mapping[str, str]) -> str:
    # Entity-bound — never store-wide type collapse for product situations.
    if kind in {
        KIND_INTEREST_WITHOUT_PURCHASE,
        KIND_SHIPPING_FRICTION,
        KIND_PRODUCT_DEMAND,
    }:
        return f"{kind}|{subject.get('id') or 'unknown'}"
    return f"{kind}|store"


def _copy_for_kind(
    kind: str, subject_name: str, facts: list[Mapping[str, Any]]
) -> dict[str, str]:
    name = subject_name or "المتجر"
    meanings = [_norm(f.get("business_meaning_ar")) for f in facts if _norm(f.get("business_meaning_ar"))]
    lead = meanings[0] if meanings else ""

    if kind == KIND_INTEREST_WITHOUT_PURCHASE:
        title = f"اهتمام دون شراء — {name}"
        question = f"لماذا يجذب {name} الاهتمام دون إتمام الشراء؟"
        why = (
            f"{name} يحظى باهتمام واضح، لكن العملاء يترددون أو يعودون دون الشراء."
            if name != "المتجر"
            else "منتجات تجذب الاهتمام دون إتمام الشراء."
        )
        action = f"راجع مسار التحويل لـ {name}." if name != "المتجر" else "راجع مسار التحويل."
        impact = "تحسين التحويل على هذا المنتج يحمي إيرادات كانت قريبة من الشراء."
        return {
            "title_ar": title,
            "title_en": f"Interest without purchase — {name}",
            "business_question_ar": question,
            "business_question_en": f"Why does {name} attract interest without purchase?",
            "why_it_matters_ar": why,
            "why_it_matters_en": why,
            "executive_summary_ar": why,
            "merchant_action_ar": action,
            "expected_business_impact_ar": impact,
        }
    if kind == KIND_SHIPPING_FRICTION:
        why = lead or f"الشحن يبدو أنه يضعف إتمام الشراء لـ {name}."
        return {
            "title_ar": f"احتكاك الشحن — {name}",
            "title_en": f"Shipping friction — {name}",
            "business_question_ar": f"هل الشحن يعيق شراء {name}؟",
            "business_question_en": f"Is shipping blocking purchase of {name}?",
            "why_it_matters_ar": why,
            "why_it_matters_en": why,
            "executive_summary_ar": why,
            "merchant_action_ar": f"راجع تجربة الشحن عند شراء {name}.",
            "expected_business_impact_ar": "تقليل احتكاك الشحن قد يرفع إتمام الشراء.",
        }
    if kind == KIND_RECOVERY_OPPORTUNITY:
        why = lead or "فرص استعادة المبيعات محدودة حالياً."
        return {
            "title_ar": "فرصة استعادة المبيعات",
            "title_en": "Recovery opportunity",
            "business_question_ar": "ما حالة فرص استعادة المبيعات اليوم؟",
            "business_question_en": "What is today's recovery opportunity?",
            "why_it_matters_ar": why,
            "why_it_matters_en": why,
            "executive_summary_ar": why,
            "merchant_action_ar": "راجع متابعة السلال المؤهلة للاستعادة.",
            "expected_business_impact_ar": "وضوح فرص الاستعادة يحدد أولوية المتابعة اليوم.",
        }
    if kind == KIND_COMMUNICATION:
        why = lead or "تواصل العملاء يسير بشكل طبيعي."
        return {
            "title_ar": "تغطية التواصل",
            "title_en": "Communication coverage",
            "business_question_ar": "هل تواصل العملاء يحتاج انتباهاً؟",
            "business_question_en": "Does customer communication need attention?",
            "why_it_matters_ar": why,
            "why_it_matters_en": why,
            "executive_summary_ar": why,
            "merchant_action_ar": "راجع حالة التواصل مع العملاء.",
            "expected_business_impact_ar": "تواصل سليم يحافظ على متابعة العملاء.",
        }
    if kind == KIND_STORE_HEALTH:
        why = lead or "لا توجد مشكلات تجارية حرجة ظاهرة."
        return {
            "title_ar": "صحة المتجر",
            "title_en": "Store health",
            "business_question_ar": "ما حالة المتجر التجارية اليوم؟",
            "business_question_en": "What is the store's commercial condition today?",
            "why_it_matters_ar": why,
            "why_it_matters_en": why,
            "executive_summary_ar": why,
            "merchant_action_ar": "راجع حالة المتجر عند ظهور إشارات جديدة.",
            "expected_business_impact_ar": "وضوح صحة المتجر يمنع ضياع الانتباه.",
        }
    # product_demand / quality
    why = lead or f"طلب أو جودة {name} يظهر إشارات تستحق المتابعة."
    return {
        "title_ar": f"طلب المنتج — {name}",
        "title_en": f"Product demand — {name}",
        "business_question_ar": f"ماذا نعرف عن طلب {name}؟",
        "business_question_en": f"What do we know about demand for {name}?",
        "why_it_matters_ar": why,
        "why_it_matters_en": why,
        "executive_summary_ar": why,
        "merchant_action_ar": f"راجع أدلة الطلب لـ {name}.",
        "expected_business_impact_ar": "فهم الطلب يساعد على ترتيب أولوية المنتجات.",
    }


def _owner_for_kind(kind: str) -> str:
    if kind == KIND_COMMUNICATION:
        return OWNER_COMMUNICATION
    if kind == KIND_STORE_HEALTH:
        return OWNER_HOME
    return OWNER_DECISION_WORKSPACE


def _priority(kind: str, fact_count: int, score: int) -> int:
    base = {
        KIND_INTEREST_WITHOUT_PURCHASE: 92,
        KIND_SHIPPING_FRICTION: 88,
        KIND_RECOVERY_OPPORTUNITY: 70,
        KIND_PRODUCT_DEMAND: 55,
        KIND_COMMUNICATION: 45,
        KIND_STORE_HEALTH: 40,
    }.get(kind, 50)
    return min(99, base + min(6, fact_count) + (4 if score >= 70 else 0))


def compose_commerce_situations_v1(
    facts_package: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    slug = _norm(store_slug) or _norm(
        (facts_package or {}).get("store_slug") if isinstance(facts_package, Mapping) else ""
    )
    if not commerce_situations_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": COMMERCE_SITUATIONS_VERSION_V1,
            "store_slug": slug,
            "situations": [],
            "published_situations": [],
            "counts": {"facts_in": 0, "situations": 0, "published": 0},
        }

    facts = [
        f
        for f in list((facts_package or {}).get("facts") or [])
        if isinstance(f, Mapping)
    ]
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    kind_by_key: dict[str, str] = {}
    subject_by_key: dict[str, dict[str, str]] = {}
    for fact in facts:
        kind = _classify_fact_kind_v1(fact)
        if not kind:
            continue
        sub = _subject(fact)
        key = _bucket_key(kind, sub)
        buckets.setdefault(key, []).append(fact)
        kind_by_key[key] = kind
        # Prefer product subject when merging.
        prev = subject_by_key.get(key)
        if prev is None or (
            sub.get("kind") == "product" and prev.get("kind") != "product"
        ):
            subject_by_key[key] = sub

    situations: list[dict[str, Any]] = []
    for key, bucket in buckets.items():
        kind = kind_by_key[key]
        subject = subject_by_key.get(key) or {
            "kind": "store",
            "id": "store",
            "name_ar": "المتجر",
        }
        scores = [_conf_score(f) for f in bucket]
        avg = int(sum(scores) / max(1, len(scores)))
        copy = _copy_for_kind(kind, subject.get("name_ar") or "المتجر", bucket)
        caps: list[str] = []
        obs_ids: list[str] = []
        for f in bucket:
            for c in _caps(f):
                if c not in caps:
                    caps.append(c)
            evid = f.get("evidence") if isinstance(f.get("evidence"), Mapping) else {}
            for oid in list(evid.get("observation_ids") or []):
                if str(oid) not in obs_ids:
                    obs_ids.append(str(oid))

        owner = _owner_for_kind(kind)
        name = subject.get("name_ar") or "المتجر"
        products = []
        if subject.get("kind") == "product" and subject.get("name_ar"):
            products = [
                {
                    "product_id": subject.get("id"),
                    "name_ar": subject.get("name_ar"),
                    "situation_role_ar": "منتج مشارك في هذا الموقف",
                }
            ]

        if kind == KIND_INTEREST_WITHOUT_PURCHASE:
            cust_summary = f"عملاء مهتمون بـ {name} دون إتمام الشراء."
            cart_summary = f"سلال تتضمن {name} في مسار التحويل."
        elif kind == KIND_SHIPPING_FRICTION:
            cust_summary = f"عملاء يواجهون احتكاك الشحن عند شراء {name}."
            cart_summary = f"سلال شراء {name} تتأثر بالشحن."
        elif kind == KIND_COMMUNICATION:
            cust_summary = "عملاء في مسار التواصل الحالي."
            cart_summary = ""
        elif kind == KIND_RECOVERY_OPPORTUNITY:
            cust_summary = "عملاء مؤهلون لمتابعة الاستعادة."
            cart_summary = "سلال مؤهلة لاستعادة المبيعات."
        else:
            cust_summary = ""
            cart_summary = ""

        sit = empty_situation_shell_v1()
        sit.update(
            {
                "situation_id": f"cs:{key}:{slug or 'store'}",
                "situation_kind": kind,
                "subject": subject,
                **copy,
                "affected_products": products,
                "affected_customers": {
                    "summary_ar": cust_summary,
                    "count": None,
                    "product_names_ar": [name] if subject.get("kind") == "product" else [],
                },
                "affected_carts": {
                    "summary_ar": cart_summary,
                    "count": None,
                    "product_names_ar": [name] if subject.get("kind") == "product" else [],
                },
                "supporting_fact_ids": [
                    _norm(f.get("fact_id")) for f in bucket if _norm(f.get("fact_id"))
                ],
                "supporting_facts": [
                    {
                        "fact_id": f.get("fact_id"),
                        "fact_type": f.get("fact_type"),
                        "business_meaning_ar": f.get("business_meaning_ar"),
                    }
                    for f in bucket
                ],
                "evidence": {
                    "source_kinds": ["business_facts_v1"],
                    "fact_count": len(bucket),
                    "capability_ids": caps,
                    "observation_ids": obs_ids,
                },
                "confidence": {
                    "level": "high" if avg >= 70 else ("medium" if avg >= 45 else "low"),
                    "ar": "مرتفع" if avg >= 70 else ("متوسط" if avg >= 45 else "منخفض"),
                    "score": avg,
                },
                "freshness": {"status": "current", "as_of_utc": _utc_now()},
                "priority": _priority(kind, len(bucket), avg),
                "primary_owner": owner,
                "destination_surfaces": {
                    "home_teaser": False,
                    "decision_workspace": False,
                    "carts": False,
                    "communication": False,
                    "products": False,
                },
                "merchant_action_ar": copy["merchant_action_ar"],
                "expected_business_impact_ar": copy["expected_business_impact_ar"],
                "recommendation": None,
                "product_intelligence": False,
            }
        )

        # Admit
        has_impact = bool(_norm(sit.get("expected_business_impact_ar")))
        has_action = bool(_norm(sit.get("merchant_action_ar")))
        soft = owner in (OWNER_HOME, OWNER_COMMUNICATION) and kind in {
            KIND_STORE_HEALTH,
            KIND_COMMUNICATION,
        }
        ok = (
            len(bucket) >= _MIN_FACTS
            and avg >= _MIN_CONFIDENCE
            and has_impact
            and (has_action or soft)
        )
        sit["admitted"] = bool(ok)
        if ok:
            dest = sit["destination_surfaces"]
            if owner == OWNER_DECISION_WORKSPACE:
                dest["decision_workspace"] = True
                dest["home_teaser"] = True
                dest["products"] = True
            elif owner == OWNER_HOME:
                dest["home_teaser"] = True
            elif owner == OWNER_COMMUNICATION:
                dest["communication"] = True
                dest["home_teaser"] = True
            if kind in {KIND_INTEREST_WITHOUT_PURCHASE, KIND_SHIPPING_FRICTION}:
                dest["carts"] = True  # operational consumer — not reinterpret

        if validate_commerce_situation_v1(sit):
            continue
        situations.append(sit)

    situations.sort(key=lambda s: (-int(s.get("priority") or 0), str(s.get("situation_id"))))
    published = [s for s in situations if s.get("admitted")]
    return {
        "ok": True,
        "enabled": True,
        "schema": COMMERCE_SITUATIONS_VERSION_V1,
        "version": COMMERCE_SITUATIONS_VERSION_V1,
        "store_slug": slug,
        "constitution": "one_situation_one_owner_many_consumers",
        "principle_7": True,
        "situations": situations,
        "published_situations": published,
        "counts": {
            "facts_in": len(facts),
            "situations": len(situations),
            "published": len(published),
            "collapsed_ratio": (
                round(len(facts) / max(1, len(situations)), 2) if situations else 0
            ),
        },
        "recommendation": None,
        "product_intelligence": False,
        "composed_at_utc": _utc_now(),
    }


__all__ = ["compose_commerce_situations_v1"]
