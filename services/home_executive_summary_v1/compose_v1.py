# -*- coding: utf-8 -*-
"""
Compose Home Executive Summary V1 (Gate 1-B — Executive Summary Composition).

Home answers: "What should the merchant know now?"
Prefers ``home_teaser_inputs_v1`` (lightweight). Never ships PI action/confidence
previews on Home — View Details routes to owning pages.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.home_executive_summary_v1.editorial_exclusivity_v1 import (
    apply_editorial_exclusivity_v1,
    editorial_brief_audit_v1,
)
from services.home_executive_summary_v1.flag_v1 import home_executive_summary_v1_enabled
from services.home_executive_summary_v1.slim_transport_v1 import (
    extract_home_teaser_inputs_v1,
    home_slim_transport_v1_enabled,
)

OWNERSHIP_V1 = {
    "home": "executive_summary",
    "decision_workspace": "decisions",
    "product_intelligence": "product_findings",
    "carts": "cart_operations",
    "communication": "communication",
    "settings": "configuration",
}

# Stable section ids (transport/UI). Titles are merchant-facing Arabic.
# Repair V1 order: condition → one primary decision → optional product situation
# (or observations fallback) → carts ops → communication condition.
SECTION_IDS_V1 = (
    "health",
    "decisions",
    "situations",
    "observations",
    "carts",
    "communication",
)

OBS_EMPTY_AR = "لا يوجد منتج حالياً بأدلة كافية لملاحظة تجارية."
DECISIONS_EMPTY_AR = "لا توجد أولوية قرار واضحة اليوم."

GOVERNANCE_V1 = {
    "sprint": "home_stabilization_v1",
    "gate": "gate_2x_merchant_understanding",
    "single_owner": "home_executive_summary_v1",
    "single_data_source": "home_teaser_inputs_v1",
    "single_render_path": "maApplyHomeExecutiveSummaryV1",
    "sections": list(SECTION_IDS_V1),
    "product_intelligence": False,
    "home_creates_decisions": False,
    "executive_business_language": True,
    "store_executive_thinking": True,
    "merchant_understanding": True,
    "page_question": "What is happening in my business today?",
    "executive_editorial_exclusivity": True,
    "morning_brief": True,
}

# Card → owning constitutional page (View Details).
SECTION_OWNERSHIP_HREF_V1 = {
    "health": "#carts",
    "decisions": "#workspace",
    "observations": "#workspace",
    "carts": "#carts",
    "communication": "#communication",
}

# Gate 2 — Home decision teasers must route explicitly to Cart Workspace.
DECISIONS_VIEW_DETAILS_AR = "عرض التفاصيل"


def _teasers(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("home_teaser_inputs_v1")
    if isinstance(raw, Mapping) and raw.get("schema") == "home_teaser_inputs_v1":
        return dict(raw)
    return extract_home_teaser_inputs_v1(summary)


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _situations_portfolio_section(summary: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """
    Home introduces at most one distinct product situation (Repair V1).
    Store condition + primary decision are separate sections — not duplicated here.
    """
    t = _teasers(summary)
    pub = _publication(summary)
    obs = t.get("observations") if isinstance(t.get("observations"), Mapping) else {}
    top = obs.get("top") if isinstance(obs.get("top"), Mapping) else None
    items_raw = []
    home_product = (
        pub.get("home_product_situation")
        if isinstance(pub.get("home_product_situation"), Mapping)
        else None
    )
    if home_product and str(home_product.get("situation_id") or "").strip():
        items_raw = [home_product]
    elif isinstance(top, Mapping) and isinstance(top.get("situations"), list):
        items_raw = [x for x in top.get("situations") or [] if isinstance(x, Mapping)]
    if not items_raw:
        # Prefer full package routing when available (fat summary / tests).
        cs = summary.get("commerce_situations_v1")
        if isinstance(cs, Mapping):
            routing = cs.get("routing") if isinstance(cs.get("routing"), Mapping) else {}
            teaser = (
                routing.get("home_teaser")
                if isinstance(routing, Mapping)
                else None
            )
            if isinstance(teaser, Mapping):
                items_raw = [
                    x
                    for x in list(teaser.get("situations") or [])
                    if isinstance(x, Mapping)
                    and str(x.get("situation_kind") or "")
                    in {
                        "interest_without_purchase",
                        "shipping_friction",
                        "product_demand",
                    }
                ]
    items: list[dict[str, Any]] = []
    primary_sid = str(pub.get("highest_priority_situation_id") or "").strip()
    for row in items_raw[:1]:
        sid = str(row.get("situation_id") or "").strip()
        title = str(row.get("title_ar") or "").strip()
        statement = str(row.get("statement_ar") or "").strip()
        if not sid or not (title or statement):
            continue
        items.append(
            {
                "situation_id": sid,
                "situation_kind": str(row.get("situation_kind") or "").strip(),
                "title_ar": title,
                "statement_ar": statement,
                "product_name_ar": str(row.get("product_name_ar") or "").strip(),
                "href": str(row.get("href") or f"#workspace?situation_id={sid}"),
                "source": "commerce_situations_v1",
            }
        )
    if len(items) < 1:
        return None
    lead = items[0]
    # Merchant-safe items — no situation_id / technical keys in display payload.
    safe_items = [
        {
            "title_ar": str(i.get("title_ar") or "").strip(),
            "statement_ar": str(i.get("statement_ar") or "").strip(),
            "product_name_ar": str(
                i.get("product_name_ar") or i.get("subject_ar") or ""
            ).strip(),
            "href": "#workspace",
        }
        for i in items
    ]
    return {
        "id": "situations",
        "title_ar": "أهم منتج يستحق الانتباه",
        "summary_ar": str(
            lead.get("statement_ar") or lead.get("title_ar") or ""
        ).strip(),
        "status_ar": "منتج",
        "count": 1,
        "items": safe_items,
        "view_details_href": "#workspace",
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
        "owner_page": "decision_workspace",
        "built_from": "merchant_publication_v1",
        "portfolio": False,
        "executive_rank": 3,
    }


def _observation_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Legacy fallback when Situations portfolio is unavailable."""
    t = _teasers(summary)
    obs = t.get("observations") if isinstance(t.get("observations"), Mapping) else {}
    count = _as_int(obs.get("count"))
    top = obs.get("top") if isinstance(obs.get("top"), Mapping) else None
    if count <= 0 or not top:
        return {
            "id": "observations",
            "title_ar": "ملاحظات المنتجات",
            "summary_ar": OBS_EMPTY_AR,
            "status_ar": "أدلة غير كافية",
            "count": 0,
            "view_details_href": SECTION_OWNERSHIP_HREF_V1["observations"],
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
            "empty_state_ar": OBS_EMPTY_AR,
            "findings_preview": [],
            "owner_page": "decision_workspace",
            "built_from": "business_facts_v1",
        }
    name = str(top.get("product_name_ar") or top.get("title_ar") or "").strip()
    statement = str(top.get("statement_ar") or "").strip()
    if name and statement and name not in statement:
        summary_ar = f"المنتج {name}: {statement}"
    elif statement:
        summary_ar = statement
    elif name:
        summary_ar = f"المنتج {name} يستحق الانتباه."
    else:
        summary_ar = OBS_EMPTY_AR
    return {
        "id": "observations",
        "title_ar": "ملاحظات المنتجات",
        "summary_ar": summary_ar,
        "status_ar": "يتطلب انتباهاً",
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["observations"],
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
        "empty_state_ar": "",
        "findings_preview": [],
        "owner_page": "decision_workspace",
        "built_from": str(top.get("source") or "business_facts_v1"),
    }


def _decisions_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    """One highest-priority decision teaser only (F2)."""
    t = _teasers(summary)
    dec = t.get("decisions") if isinstance(t.get("decisions"), Mapping) else {}
    pub = _publication(summary)
    ped = (
        pub.get("primary_executive_decision")
        if isinstance(pub.get("primary_executive_decision"), Mapping)
        else {}
    )
    title = str(
        pub.get("primary_action")
        or ped.get("action_ar")
        or pub.get("primary_business_action")
        or dec.get("top_title_ar")
        or ""
    ).strip()
    subject = str(pub.get("primary_subject") or ped.get("subject_ar") or "").strip()
    primary_id = str(
        pub.get("highest_priority_decision_id")
        or ped.get("decision_id")
        or dec.get("highest_priority_decision_id")
        or ""
    ).strip()
    count = 1 if title and (primary_id or _as_int(dec.get("count")) > 0 or subject) else 0
    if count <= 0 or not title:
        return {
            "id": "decisions",
            "title_ar": "أهم قرار اليوم",
            "summary_ar": DECISIONS_EMPTY_AR,
            "status_ar": "أدلة غير كافية",
            "count": 0,
            "view_details_href": SECTION_OWNERSHIP_HREF_V1["decisions"],
            "view_details_ar": DECISIONS_VIEW_DETAILS_AR,
            "empty": True,
            "owner_page": "decision_workspace",
            "executive_rank": 2,
        }
    summary_ar = title
    if subject and subject.split("—")[0].strip() not in title:
        # Keep action dominant; subject is owned by the product section.
        summary_ar = title
    return {
        "id": "decisions",
        "title_ar": "أهم قرار اليوم",
        "summary_ar": summary_ar,
        "status_ar": "القرار الأهم",
        "count": 1,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["decisions"],
        "view_details_ar": DECISIONS_VIEW_DETAILS_AR,
        "empty": False,
        "owner_page": "decision_workspace",
        "is_primary": True,
        "executive_rank": 2,
        "subject_ar": subject,
        "dominant": True,
    }


def _publication(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("merchant_publication_v1")
    if isinstance(raw, Mapping) and raw.get("ok"):
        return dict(raw)
    t = _teasers(summary)
    nested = t.get("merchant_publication_v1")
    if isinstance(nested, Mapping) and nested.get("ok"):
        return dict(nested)
    return {}


def _health_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Store condition — must agree with admitted priority / situations (F1)."""
    t = _teasers(summary)
    health = t.get("health") if isinstance(t.get("health"), Mapping) else {}
    waiting = _as_int(health.get("abandoned_carts"))
    active = _as_int(health.get("active_carts"))
    recovered = _as_int(health.get("recovered_today"))
    no_phone = _as_int(health.get("no_phone"))
    store_ok = health.get("store_connected")
    pub = _publication(summary)
    sc = pub.get("store_condition") if isinstance(pub.get("store_condition"), Mapping) else {}

    href = SECTION_OWNERSHIP_HREF_V1["health"]
    if store_ok is False:
        summary_ar = "جاهزية المتجر غير مكتملة — اضبط الربط أولاً."
        status_ar = "يتطلب متابعة"
        href = "#home-setup"
        empty = False
        needs = True
    elif sc:
        # Canonical publication — never invent calm over a high-priority decision.
        summary_ar = str(sc.get("summary_ar") or "").strip()
        status_ar = str(sc.get("status_ar") or "").strip() or (
            "يتطلب متابعة" if sc.get("needs_attention") else "هادئ"
        )
        needs = bool(sc.get("needs_attention"))
        empty = not needs
        if needs and summary_ar in {"لا توجد مشكلات تجارية حرجة ظاهرة.", ""}:
            summary_ar = "المتجر يحتاج انتباهك اليوم."
            status_ar = "يتطلب متابعة"
    else:
        needs = bool(health.get("needs_attention")) or waiting > 0 or no_phone > 0
        domain_summary = str(health.get("domain_summary_ar") or "").strip()
        status_hint = str(health.get("status_ar") or "").strip()
        if domain_summary:
            summary_ar = domain_summary
            status_ar = status_hint or ("يتطلب متابعة" if needs else "مستقر")
            empty = not needs
        elif waiting > 0 or no_phone > 0:
            summary_ar = "فرص استعادة المبيعات محدودة اليوم."
            status_ar = "يتطلب متابعة"
            empty = False
        elif recovered > 0 or active > 0:
            summary_ar = "نشاط المتجر مستقر."
            status_ar = "مستقر"
            empty = False
            needs = False
        else:
            summary_ar = "لا توجد مشكلات تجارية حرجة ظاهرة."
            status_ar = "هادئ"
            empty = True
            needs = False

    out = {
        "id": "health",
        "title_ar": "حالة المتجر",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "view_details_href": href,
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "needs_attention": needs,
        "owner_page": "carts" if href == "#carts" else "settings",
        "executive_rank": 1,
    }
    return out


def _carts_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Cart operational summary — never a competing business decision (F5)."""
    t = _teasers(summary)
    carts = t.get("carts") if isinstance(t.get("carts"), Mapping) else {}
    pub = _publication(summary)
    cart_ops = (
        pub.get("cart_condition")
        if isinstance(pub.get("cart_condition"), Mapping)
        else (
            pub.get("cart_operational_action")
            if isinstance(pub.get("cart_operational_action"), Mapping)
            else {}
        )
    )
    systemic = (
        pub.get("systemic_business_action")
        if isinstance(pub.get("systemic_business_action"), Mapping)
        else {}
    )
    waiting = _as_int(carts.get("waiting") if carts.get("waiting") is not None else carts.get("count"))
    active = _as_int(carts.get("active"))
    no_phone = _as_int(carts.get("no_phone"))
    recovered = _as_int(
        (t.get("health") or {}).get("recovered_today")
        if isinstance(t.get("health"), Mapping)
        else 0
    )
    count = waiting
    from services.decision_composition_engine_v1.merchant_understanding_v1 import (  # noqa: PLC0415
        PREFERRED_CARTS_NEED_ATTENTION_AR,
        PREFERRED_CARTS_STABLE_AR,
        publish_executive_statement_v1,
    )

    if cart_ops:
        summary_ar = str(cart_ops.get("summary_ar") or "").strip()
        status_ar = str(cart_ops.get("status_ar") or "").strip() or (
            "يتطلب متابعة" if waiting > 0 or no_phone > 0 else "لا مهام"
        )
        empty = bool(cart_ops.get("empty")) and waiting <= 0
        individual = str(cart_ops.get("individual_action_ar") or "").strip()
        if waiting > 0:
            count = waiting
        elif no_phone > 0:
            count = no_phone
        elif active > 0:
            count = active
    else:
        domain_summary = str(carts.get("domain_summary_ar") or "").strip()
        individual = str(carts.get("individual_action_ar") or "").strip()
        if domain_summary:
            summary_ar = publish_executive_statement_v1(
                domain_summary,
                surface="carts",
                fallback=PREFERRED_CARTS_STABLE_AR,
            )["text_ar"]
            empty = waiting <= 0 and no_phone <= 0 and "مستقر" in summary_ar
            status_ar = (
                "يتطلب متابعة"
                if (waiting > 0 or no_phone > 0)
                else ("نشط" if active > 0 else "لا مهام")
            )
            if waiting <= 0 and no_phone > 0:
                count = no_phone
            elif waiting <= 0 and active > 0:
                count = active
        elif waiting > 0:
            summary_ar = PREFERRED_CARTS_NEED_ATTENTION_AR
            status_ar = "يتطلب متابعة"
            empty = False
        elif no_phone > 0:
            summary_ar = "متابعة بعض العملاء مقيدة حالياً."
            status_ar = "يتطلب متابعة"
            empty = False
            count = no_phone
        elif recovered > 0:
            summary_ar = PREFERRED_CARTS_STABLE_AR
            status_ar = "مستقر"
            empty = False
            count = recovered
        elif active > 0:
            summary_ar = PREFERRED_CARTS_STABLE_AR
            status_ar = "نشط"
            empty = False
            count = active
        else:
            summary_ar = "لا توجد سلال تحتاج متابعة فردية حالياً."
            status_ar = "لا مهام"
            empty = True

    out = {
        "id": "carts",
        "title_ar": "السلال",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["carts"],
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "owner_page": "carts",
        "cart_level_action_ar": individual
        or "لا يحتاج إجراءً فردياً الآن.",
        "systemic_business_action_ar": str(systemic.get("summary_ar") or "").strip(),
        "systemic_workspace_href": "#workspace",
        "executive_rank": 4,
    }
    return out


def _communication_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Communication condition — same canonical truth as Workspace (F4)."""
    t = _teasers(summary)
    comm = t.get("communication") if isinstance(t.get("communication"), Mapping) else {}
    pub = _publication(summary)
    cc = (
        pub.get("communication_condition")
        if isinstance(pub.get("communication_condition"), Mapping)
        else {}
    )
    sent = _as_int(comm.get("sent"))
    schedules = _as_int(comm.get("schedules"))
    no_phone = _as_int(comm.get("no_phone"))
    waiting = _as_int(comm.get("waiting"))
    wa_state = str(comm.get("wa_state_key") or "").strip().lower()
    count = sent + schedules

    if cc:
        summary_ar = str(cc.get("summary_ar") or "").strip()
        status_ar = str(cc.get("status_ar") or "").strip() or (
            "يتطلب متابعة" if cc.get("constrained") or cc.get("normal_forbidden") else "لا مهام"
        )
        empty = not bool(cc.get("constrained") or cc.get("normal_forbidden"))
        if cc.get("constrained"):
            count = max(count, no_phone, 1)
        # Never publish "normal" when constrained.
        if cc.get("normal_forbidden") and "بشكل طبيعي" in summary_ar:
            summary_ar = "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
            status_ar = "يتطلب متابعة"
            empty = False
    elif domain_summary := str(comm.get("domain_summary_ar") or "").strip():
        summary_ar = domain_summary
        status_ar = "يتطلب متابعة" if (no_phone > 0 or waiting > 0 or comm.get("constrained")) else "نشط"
        empty = False
        count = max(count, waiting, no_phone, sent)
    elif waiting > 0 and no_phone > 0:
        summary_ar = "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
        status_ar = "يتطلب متابعة"
        empty = False
        count = max(count, waiting, no_phone)
    elif waiting > 0 or schedules > 0:
        n = max(waiting, schedules)
        summary_ar = f"{n} عملاء بانتظار متابعة."
        status_ar = "بانتظار متابعة"
        empty = False
        count = n
    elif no_phone > 0:
        summary_ar = "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
        status_ar = "يتطلب متابعة"
        empty = False
        count = no_phone
    elif sent > 0:
        summary_ar = f"{sent} رسالة وصلت للعملاء اليوم."
        status_ar = "مكتمل اليوم"
        empty = False
        count = sent
    elif wa_state and wa_state not in {"ready", "connected", ""}:
        summary_ar = "تواصل العملاء يحتاج ضبطاً بسيطاً."
        status_ar = "يحتاج ضبطاً"
        empty = False
    else:
        summary_ar = "تواصل العملاء يسير بشكل طبيعي."
        status_ar = "لا مهام"
        empty = True

    return {
        "id": "communication",
        "title_ar": "التواصل",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["communication"],
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "owner_page": "communication",
        "reports_condition_only": True,
        "executive_rank": 5,
    }


def build_home_executive_summary_v1(
    summary: Mapping[str, Any] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not home_executive_summary_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": "home_executive_summary_v1",
            "sections": [],
            "governance": dict(GOVERNANCE_V1),
        }
    src = summary if isinstance(summary, Mapping) else {}
    portfolio = _situations_portfolio_section(src)
    # Repair V1: health + one primary decision + optional distinct product situation.
    raw_sections: list[dict[str, Any]] = [
        _health_section(src),
        _decisions_section(src),
    ]
    if portfolio is not None:
        raw_sections.append(portfolio)
    else:
        raw_sections.append(_observation_section(src))
    raw_sections.extend(
        [
            _carts_section(src),
            _communication_section(src),
        ]
    )
    sections = apply_editorial_exclusivity_v1(raw_sections)
    suppressions = []
    if sections and isinstance(sections[0], dict):
        suppressions = list(sections[0].pop("_editorial_suppressions", []) or [])
    audit = editorial_brief_audit_v1(sections)
    audit["suppressions"] = suppressions
    return {
        "ok": True,
        "enabled": True,
        "schema": "home_executive_summary_v1",
        "eyebrow_ar": "ملخص تنفيذي",
        "title_ar": "ماذا يجب أن تعرف الآن؟",
        "lede_ar": "ملخص سريع فقط — التفاصيل في صفحاتها.",
        "ownership": dict(OWNERSHIP_V1),
        "section_ownership_href": dict(SECTION_OWNERSHIP_HREF_V1),
        "governance": dict(GOVERNANCE_V1),
        "editorial_brief": audit,
        "sections": sections,
        "product_intelligence": False,
        "slim_transport": home_slim_transport_v1_enabled(environ=environ),
        "ui": True,
    }


def slim_observation_package_for_home_v1(pkg: Mapping[str, Any] | None) -> dict[str, Any]:
    """Gate 1: Home must not transport ORV detail — return empty stub only."""
    del pkg  # unused — never forward findings on Home
    return {
        "ok": True,
        "enabled": True,
        "findings": [],
        "count": 0,
        "empty_state_ar": OBS_EMPTY_AR,
        "schema": "observation_reality_validation_v1_home_stripped",
        "stripped_for_home_slim_transport": True,
    }


def attach_home_executive_summary_to_summary_v1(
    summary: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    if not home_executive_summary_v1_enabled(environ=environ):
        return summary
    summary["home_surface_mode"] = "executive_summary_v1"
    try:
        if "home_teaser_inputs_v1" not in summary:
            summary["home_teaser_inputs_v1"] = extract_home_teaser_inputs_v1(summary)
        if home_slim_transport_v1_enabled(environ=environ):
            summary["observation_reality_validation_v1"] = (
                slim_observation_package_for_home_v1(None)
            )
        pkg = build_home_executive_summary_v1(summary, environ=environ)
        summary["home_executive_summary_v1"] = pkg
    except Exception:  # noqa: BLE001
        summary["home_executive_summary_v1"] = {
            "ok": False,
            "enabled": True,
            "error": "attach_failed",
            "sections": [],
            "governance": dict(GOVERNANCE_V1),
            "eyebrow_ar": "ملخص تنفيذي",
            "title_ar": "ماذا يجب أن تعرف الآن؟",
            "lede_ar": "تعذّر تحميل الملخص — أعد المحاولة.",
        }
    return summary


__all__ = [
    "DECISIONS_EMPTY_AR",
    "DECISIONS_VIEW_DETAILS_AR",
    "GOVERNANCE_V1",
    "OBS_EMPTY_AR",
    "OWNERSHIP_V1",
    "SECTION_IDS_V1",
    "SECTION_OWNERSHIP_HREF_V1",
    "attach_home_executive_summary_to_summary_v1",
    "build_home_executive_summary_v1",
    "slim_observation_package_for_home_v1",
]
