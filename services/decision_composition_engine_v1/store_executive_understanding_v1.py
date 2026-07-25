# -*- coding: utf-8 -*-
"""
Gate 2F — Store Executive Understanding.

Mandatory before any executive statement reaches Home / Decision Portfolio.

Ask: "If I were preparing the merchant's morning executive briefing,
what would deserve attention first?"

Never ask: "What recovery event happened?"
Never describe CartFlow internals.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

STORE_EXECUTIVE_VERSION_V1 = "store_executive_understanding_v1"

# Reject system-centric / infrastructure language on executive surfaces.
_FORBIDDEN_EXECUTIVE_TOKENS = (
    "scheduler",
    "dispatch",
    "cartflow",
    "queue waiting",
    "عدّاد",
    "مجدول",
    "scheduler",
    "محرك الاسترجاع",
    "حالة المحرك",
    "module",
    "infrastructure",
    "waiting_total",
    "no_phone_total",
    "abandonedcart",
)

_OBS_EMPTY_AR = "لا يوجد منتج حالياً بأدلة كافية لملاحظة تجارية."


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def is_system_centric_executive_text_v1(text: str) -> bool:
    """True when text primarily describes CartFlow / internals / raw counters."""
    raw = _norm(text).lower()
    if not raw:
        return False
    if any(tok in raw for tok in _FORBIDDEN_EXECUTIVE_TOKENS):
        return True
    # Raw counter report as the whole message (e.g. "43 سلة بلا رقم").
    if re.search(r"^\d+\s*سلة\s*بلا\s*رقم", raw):
        return True
    if "بلا رقم تواصل" in raw and "عميل" not in raw and "متابعة" not in raw:
        # Bare phone-gap report without business framing.
        if re.search(r"\d+\s*سلة\s*بلا", raw):
            return True
    return False


def sanitize_executive_text_v1(text: str, *, fallback: str) -> str:
    """Accept merchant-centric text; replace system-centric with fallback."""
    cleaned = _norm(text)
    if not cleaned or is_system_centric_executive_text_v1(cleaned):
        return _norm(fallback)
    return cleaned


def _store_health_ar(signals: Mapping[str, Any], domains: Mapping[str, Any]) -> str:
    available = bool(signals.get("available"))
    recovery = domains.get("recovery") if isinstance(domains.get("recovery"), Mapping) else {}
    ops = domains.get("operations") if isinstance(domains.get("operations"), Mapping) else {}
    products = domains.get("products") if isinstance(domains.get("products"), Mapping) else {}
    active = _as_int(signals.get("active_total"))
    recovered = _as_int(signals.get("recovered_total"))

    if not available:
        return "لا توجد أدلة كافية لتقييم حالة المتجر اليوم."
    if recovery.get("has_attention"):
        return "فرص استعادة المبيعات محدودة اليوم."
    if ops.get("has_attention"):
        return "إتمام الشراء أبطأ من المعتاد."
    if products.get("has_attention"):
        return "اهتمام المنتجات صحي — راقب فرص التحويل."
    if recovered > 0 and active > 0:
        return "نشاط المتجر مستقر."
    if active > 0:
        return "نشاط المتجر مستقر."
    return "لا توجد مشكلات تجارية حرجة ظاهرة."


def _carts_ar(signals: Mapping[str, Any]) -> str:
    waiting = _as_int(signals.get("waiting_total"))
    no_phone = _as_int(signals.get("no_phone_total"))
    recovered = _as_int(signals.get("recovered_total"))
    active = _as_int(signals.get("active_total"))

    if waiting > 0:
        return f"{waiting} سلة قيد المتابعة مع العملاء."
    if no_phone > 0:
        return "متابعة بعض العملاء مقيدة حالياً."
    if recovered > 0:
        return f"{recovered} سلة اكتملت متابعتها — التقدم مستقر."
    if active > 0:
        return "تقدّم سلال العملاء مستقر."
    return "لا توجد سلال تحتاج متابعة حالياً."


def _communication_ar(signals: Mapping[str, Any], *, sent: int = 0) -> str:
    waiting = _as_int(signals.get("waiting_total"))
    no_phone = _as_int(signals.get("no_phone_total"))
    if waiting > 0 and no_phone > 0:
        return "تواصل العملاء يحتاج انتباهاً — المتابعة مقيدة لبعض الحالات."
    if waiting > 0:
        return f"{waiting} عملاء بانتظار متابعة."
    if no_phone > 0:
        return "متابعة العملاء مقيدة لبعض الحالات حالياً."
    if sent > 0:
        return f"{sent} رسالة وصلت للعملاء اليوم."
    return "تواصل العملاء يسير بشكل طبيعي."


def _executive_decision_title_v1(decision: Mapping[str, Any]) -> str:
    """Merchant attention title — never a counter report."""
    domain = _norm(decision.get("business_domain") or decision.get("decision_category")).lower()
    title = _norm(
        decision.get("executive_decision_ar")
        or decision.get("merchant_decision")
        or decision.get("title")
    )
    # Soft rewrite known recovery system phrasing into morning-briefing language.
    if domain == "recovery" or "استرجاع" in title:
        return "راجع تجربة إتمام الشراء ومتابعة العملاء."
    if domain == "shipping" or "شحن" in title:
        return "راجع تكلفة أو تجربة الشحن."
    if domain == "pricing" or "سعر" in title or "تسعير" in title:
        return "راجع استراتيجية التسعير أو الخصم."
    if domain == "products" or "منتج" in title:
        # Keep named product if present; otherwise generic product attention.
        if title and "راجع" in title:
            return sanitize_executive_text_v1(
                title, fallback="راجع منتجاً يستحق انتباهك اليوم."
            )
        return "راجع منتجاً يستحق انتباهك اليوم."
    if domain == "operations":
        return "راجع حالات الشراء التي تحتاج تدخلك."
    if title:
        return sanitize_executive_text_v1(
            title, fallback="راجع أولوية العمل اليوم."
        )
    return "راجع أولوية العمل اليوم."


def compose_store_executive_understanding_v1(
    domains_pkg: Mapping[str, Any] | None,
    *,
    decisions: list[Mapping[str, Any]] | None = None,
    sent_messages: int = 0,
) -> dict[str, Any]:
    """
    Produce the merchant morning briefing package.

    Every Home teaser and decision title must pass through here.
    """
    pkg = domains_pkg if isinstance(domains_pkg, Mapping) else {}
    domains = pkg.get("domains") if isinstance(pkg.get("domains"), Mapping) else {}
    signals = dict(pkg.get("signals") if isinstance(pkg.get("signals"), Mapping) else {})
    # Carry recovered if present on home path later
    home_prev = pkg.get("home_teasers") if isinstance(pkg.get("home_teasers"), Mapping) else {}

    health = sanitize_executive_text_v1(
        _store_health_ar(signals, domains),
        fallback="لا توجد مشكلات تجارية حرجة ظاهرة.",
    )
    carts = sanitize_executive_text_v1(
        _carts_ar(signals),
        fallback="تقدّم سلال العملاء مستقر.",
    )
    comm = sanitize_executive_text_v1(
        _communication_ar(signals, sent=_as_int(sent_messages)),
        fallback="تواصل العملاء يسير بشكل طبيعي.",
    )

    decs = [d for d in (decisions or []) if isinstance(d, Mapping)]
    top_title = ""
    if decs:
        top_title = _executive_decision_title_v1(decs[0])

    briefing = {
        "store_healthy": not bool(
            (domains.get("recovery") or {}).get("has_attention")
            or (domains.get("operations") or {}).get("has_attention")
        )
        and bool(signals.get("available")),
        "revenue_signal_ar": (
            "إتمام الشراء أبطأ من المعتاد."
            if (domains.get("operations") or {}).get("has_attention")
            or (domains.get("recovery") or {}).get("has_attention")
            else "لا إشارة واضحة لتباطؤ الإيراد اليوم."
        ),
        "products_attention_ar": (
            "يوجد منتج يستحق المراجعة."
            if (domains.get("products") or {}).get("has_attention")
            else _OBS_EMPTY_AR
        ),
        "top_decision_ar": top_title or "لا توجد أولوية قرار واضحة اليوم.",
        "recovery_healthy_ar": (
            "فرص الاستعادة محدودة اليوم."
            if (domains.get("recovery") or {}).get("has_attention")
            else "مسار متابعة العملاء يعمل بشكل طبيعي."
        ),
        "communication_healthy_ar": (
            "تواصل العملاء يحتاج انتباهاً."
            if (domains.get("communication") or {}).get("has_attention")
            or _as_int(signals.get("no_phone_total")) > 0
            or _as_int(signals.get("waiting_total")) > 0
            else "تواصل العملاء يسير بشكل طبيعي."
        ),
    }

    return {
        "ok": True,
        "version": STORE_EXECUTIVE_VERSION_V1,
        "gate_2f_store_executive": True,
        "briefing": briefing,
        "home_teasers": {
            "store_health_ar": health,
            "store_health_attention": bool(
                (domains.get("recovery") or {}).get("has_attention")
                or (domains.get("operations") or {}).get("has_attention")
            ),
            "carts_ar": carts,
            "communication_ar": comm,
            "communication_attention": bool(
                (domains.get("communication") or {}).get("has_attention")
                or _as_int(signals.get("waiting_total")) > 0
                or _as_int(signals.get("no_phone_total")) > 0
            ),
            "decisions_top_title_ar": top_title,
            "observations_empty_ar": _OBS_EMPTY_AR,
            # Preserve prior keys for callers that merge.
            "legacy_domain_teasers": dict(home_prev),
        },
        "rejected_system_centric": False,
    }


def apply_store_executive_to_decisions_v1(
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stamp executive titles on published decisions (merchant attention language)."""
    out: list[dict[str, Any]] = []
    for raw in decisions:
        d = dict(raw)
        title = _executive_decision_title_v1(d)
        d["executive_decision_ar"] = title
        # Home / teaser consume merchant_decision — keep constitution why fields intact.
        d["merchant_decision"] = title
        d["title"] = title
        d["gate_2f_store_executive"] = True
        # Soften why lead-in to business opportunity language when system-centric.
        why = _norm(d.get("why"))
        if is_system_centric_executive_text_v1(why) or "عدّاد" in why:
            d["why"] = (
                "فرص إتمام الشراء أو متابعة العملاء محدودة، "
                "فيستحق الأمر انتباهك اليوم."
            )
        out.append(d)
    return out


__all__ = [
    "STORE_EXECUTIVE_VERSION_V1",
    "apply_store_executive_to_decisions_v1",
    "compose_store_executive_understanding_v1",
    "is_system_centric_executive_text_v1",
    "sanitize_executive_text_v1",
]
