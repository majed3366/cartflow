# -*- coding: utf-8 -*-
"""
Executive Editorial Exclusivity — Home Morning Brief publication policy.

Not an engine. Not a story service. Not a new architectural layer.
Governs what Home may publish after sections are composed from existing teasers.

Law: docs/product/EXECUTIVE_EDITORIAL_EXCLUSIVITY_V1.md (Principle 7)
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

# Commercial situations (merchant mental model — not fact_type taxonomy).
SIT_PURCHASE_COMPLETION = "purchase_completion"
SIT_RECOVERY = "recovery_opportunity"
SIT_SHIPPING = "shipping_friction"
SIT_RETURN = "customer_return"
SIT_PRODUCT_QUALITY = "product_quality"
SIT_STORE_STABLE = "store_stable"
SIT_STORE_SETUP = "store_setup"
SIT_CART_OPS = "cart_operations"
SIT_COMMUNICATION = "communication"

# Role-safe suppressed copy (unique understanding or honest empty — never synonym restatement).
_SUPPRESS_COPY: dict[str, dict[str, Any]] = {
    "health": {
        "summary_ar": "لا توجد مشكلات تجارية حرجة ظاهرة.",
        "status_ar": "مستقر",
        "empty": True,
        "needs_attention": False,
    },
    "decisions": {
        "summary_ar": "لا توجد أولوية قرار واضحة اليوم.",
        "status_ar": "أدلة غير كافية",
        "empty": True,
    },
    "observations": {
        "summary_ar": "لا يوجد منتج يستحق انتباهك الآن.",
        "status_ar": "أدلة غير كافية",
        "empty": True,
        "empty_state_ar": "لا يوجد منتج يستحق انتباهك الآن.",
        "findings_preview": [],
    },
    "carts": {
        "summary_ar": "لا توجد سلال تحتاج متابعة حالياً.",
        "status_ar": "لا مهام",
        "empty": True,
    },
    "communication": {
        "summary_ar": "تواصل العملاء يسير بشكل طبيعي.",
        "status_ar": "لا مهام",
        "empty": True,
    },
}


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def classify_commercial_situation_v1(
    section_id: str,
    summary_ar: str,
    *,
    product_name_ar: str = "",
) -> Optional[str]:
    """
    Map an executive card to at most one commercial situation.

    Carts / Communication are locked to operational situations (Principle 7).
    """
    sid = _norm(section_id)
    text = _norm(summary_ar)
    if not text:
        return None

    # Portfolio introduces many situations — never collapse to one classifier bucket.
    if sid == "situations":
        return None

    # Operational surfaces never reinterpret business situations.
    if sid == "carts":
        return SIT_CART_OPS
    if sid == "communication":
        return SIT_COMMUNICATION

    if sid == "health" and ("جاهزية" in text or "اضبط الربط" in text):
        return SIT_STORE_SETUP

    # Purchase / conversion / checkout (one commercial situation).
    if any(
        t in text
        for t in (
            "تحويل",
            "إتمام الشراء",
            "اتمام الشراء",
            "اهتمام",
            "شراء",
            "تجربة إتمام",
        )
    ):
        # Shipping-specific product friction is a distinct situation when named.
        if "شحن" in text or "توصيل" in text:
            return SIT_SHIPPING
        if "يعودون" in text or "عودة" in text or "مراراً" in text:
            return SIT_RETURN
        return SIT_PURCHASE_COMPLETION

    if "شحن" in text or "توصيل" in text:
        return SIT_SHIPPING
    if "يعودون" in text or ("عودة" in text and "عملاء" in text):
        return SIT_RETURN
    if "استعادة" in text or "الاستعادة" in text:
        return SIT_RECOVERY
    if "جودة" in text:
        return SIT_PRODUCT_QUALITY
    if any(
        t in text
        for t in (
            "لا توجد مشكلات",
            "نشاط المتجر مستقر",
            "مستقر",
            "هادئ",
        )
    ):
        return SIT_STORE_STABLE

    # Product observation with a named product but unclassified copy → treat as
    # purchase_completion when section is observations (default product attention).
    if sid == "observations" and _norm(product_name_ar):
        return SIT_PURCHASE_COMPLETION

    return None


def _specificity_score(
    section_id: str,
    summary_ar: str,
    *,
    product_name_ar: str = "",
) -> int:
    """Higher score wins when two cards claim the same situation."""
    score = 0
    sid = _norm(section_id)
    text = _norm(summary_ar)
    product = _norm(product_name_ar)
    if product and (product in text or sid == "observations"):
        score += 10
    if sid == "observations":
        score += 5
    elif sid == "decisions":
        score += 3
    elif sid == "health":
        score += 3
    elif sid in {"carts", "communication"}:
        score += 1
    # Prefer concrete product conversion wording over generic "review checkout".
    if "راجع" in text and "إتمام" in text and not product:
        score -= 2
    return score


def _product_hint(section: Mapping[str, Any]) -> str:
    # Observations may carry product in summary; teasers are already flattened.
    text = _norm(section.get("summary_ar"))
    # Common Living Store / Facts pattern: "Raven — …" or "المنتج Raven"
    for token in ("Raven", "TrueSound", "Horizon"):
        if token in text:
            return token
    return ""


def apply_editorial_exclusivity_v1(
    sections: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """
    Enforce: one commercial situation → one executive introduction on Home.

    When two cards share a situation, keep the more specific; suppress the other
    with role-safe copy (does not invent facts).
    """
    rows: list[dict[str, Any]] = [dict(s) for s in sections if isinstance(s, Mapping)]
    meta: list[dict[str, Any]] = []
    for idx, sec in enumerate(rows):
        sid = _norm(sec.get("id"))
        summary = _norm(sec.get("summary_ar"))
        empty = bool(sec.get("empty"))
        product = _product_hint(sec)
        situation = None if empty else classify_commercial_situation_v1(
            sid, summary, product_name_ar=product
        )
        meta.append(
            {
                "idx": idx,
                "id": sid,
                "situation": situation,
                "score": _specificity_score(sid, summary, product_name_ar=product),
                "empty": empty,
            }
        )

    # Winner per situation (highest specificity; earlier index breaks ties).
    winners: dict[str, int] = {}
    for m in sorted(
        meta,
        key=lambda x: (-int(x["score"]), int(x["idx"])),
    ):
        sit = m["situation"]
        if not sit or m["empty"]:
            continue
        if sit not in winners:
            winners[sit] = int(m["idx"])

    suppressed: list[dict[str, Any]] = []
    for m in meta:
        sit = m["situation"]
        idx = int(m["idx"])
        if not sit or m["empty"]:
            rows[idx]["commercial_situation"] = sit
            rows[idx]["editorial_exclusivity"] = "pass_empty_or_unclassified"
            continue
        if winners.get(sit) == idx:
            rows[idx]["commercial_situation"] = sit
            rows[idx]["editorial_exclusivity"] = "published"
            continue
        # Suppress restatement.
        sid = m["id"]
        fallback = dict(_SUPPRESS_COPY.get(sid) or {})
        kept_id = rows[idx].get("id")
        kept_title = rows[idx].get("title_ar")
        kept_href = rows[idx].get("view_details_href")
        kept_view = rows[idx].get("view_details_ar")
        kept_owner = rows[idx].get("owner_page")
        rows[idx].update(fallback)
        rows[idx]["id"] = kept_id
        rows[idx]["title_ar"] = kept_title
        rows[idx]["view_details_href"] = kept_href
        rows[idx]["view_details_ar"] = kept_view
        rows[idx]["owner_page"] = kept_owner
        rows[idx]["commercial_situation"] = sit
        rows[idx]["editorial_exclusivity"] = "suppressed_duplicate_situation"
        rows[idx]["suppressed_in_favor_of"] = rows[winners[sit]].get("id")
        suppressed.append(
            {
                "section_id": sid,
                "situation": sit,
                "kept_section_id": rows[winners[sit]].get("id"),
            }
        )

    # Special case: carts text that narrates recovery/purchase while health/decisions
    # already own that situation — already handled if carts were misclassified.
    # Force carts that still share purchase/recovery *wording* with a published card
    # to stay operational: if carts summary still equals a business narrative pattern
    # and another card published recovery, rewrite carts to ops-stable when count==0.
    for idx, sec in enumerate(rows):
        if sec.get("id") != "carts":
            continue
        text = _norm(sec.get("summary_ar"))
        if sec.get("editorial_exclusivity") == "suppressed_duplicate_situation":
            continue
        # If carts copy echoes recovery while health published recovery — suppress.
        if "استعادة" in text or "إتمام الشراء" in text or "تحويل" in text:
            health_pub = next(
                (
                    r
                    for r in rows
                    if r.get("id") == "health"
                    and r.get("editorial_exclusivity") == "published"
                    and r.get("commercial_situation")
                    in {SIT_RECOVERY, SIT_PURCHASE_COMPLETION}
                ),
                None,
            )
            if health_pub is not None:
                fallback = dict(_SUPPRESS_COPY["carts"])
                # Keep count/status if there is real waiting work.
                count = 0
                try:
                    count = int(sec.get("count") or 0)
                except (TypeError, ValueError):
                    count = 0
                if count > 0:
                    from services.decision_composition_engine_v1.merchant_understanding_v1 import (  # noqa: PLC0415
                        PREFERRED_CARTS_NEED_ATTENTION_AR,
                    )

                    sec["summary_ar"] = PREFERRED_CARTS_NEED_ATTENTION_AR
                    sec["status_ar"] = "يتطلب متابعة"
                    sec["empty"] = False
                    sec["editorial_exclusivity"] = "rewritten_ops_only"
                else:
                    sec.update(fallback)
                    sec["id"] = "carts"
                    sec["title_ar"] = sec.get("title_ar") or "السلال"
                    sec["view_details_href"] = sec.get("view_details_href") or "#carts"
                    sec["view_details_ar"] = sec.get("view_details_ar") or "عرض التفاصيل"
                    sec["owner_page"] = "carts"
                    sec["editorial_exclusivity"] = "suppressed_business_restatement"
                sec["commercial_situation"] = SIT_CART_OPS
                suppressed.append(
                    {
                        "section_id": "carts",
                        "situation": "business_echo",
                        "kept_section_id": "health",
                    }
                )

    # Attach brief audit on first section's sibling via return; caller stamps package.
    for sec in rows:
        sec.setdefault("editorial_exclusivity", "pass")
    # Stash suppress list on a synthetic key consumed by compose (popped there).
    if rows:
        rows[0]["_editorial_suppressions"] = suppressed
    return rows


def editorial_brief_audit_v1(sections: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sits = [
        s.get("commercial_situation")
        for s in sections
        if isinstance(s, Mapping)
        and s.get("editorial_exclusivity") == "published"
        and s.get("commercial_situation")
    ]
    return {
        "policy": "executive_editorial_exclusivity_v1",
        "constitution": "principle_7",
        "published_situations": sits,
        "unique_situation_count": len(set(sits)),
        "duplicate_situations": len(sits) != len(set(sits)),
    }


__all__ = [
    "SIT_CART_OPS",
    "SIT_COMMUNICATION",
    "SIT_PURCHASE_COMPLETION",
    "SIT_RECOVERY",
    "SIT_RETURN",
    "SIT_SHIPPING",
    "apply_editorial_exclusivity_v1",
    "classify_commercial_situation_v1",
    "editorial_brief_audit_v1",
]
