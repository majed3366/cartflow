# -*- coding: utf-8 -*-
"""
Executive Control & Merchant Surface Parity V1 — merchant_publication_v1.

Single executive authority for Home / Workspace / Products / Carts / Communication.
Not a new engine — pure composition over Decision Composition + Commerce Situations.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import BAND_NEEDS_ACTION
from services.decision_composition_engine_v1.merchant_understanding_v1 import (
    PREFERRED_COMM_ATTENTION_AR,
    PREFERRED_COMM_HEALTHY_AR,
)

MERCHANT_PUBLICATION_VERSION_V1 = "merchant_publication_v1_executive_control"
PUBLICATION_SCHEMA_V1 = "merchant_publication_v1"

# Store-condition status labels (merchant Arabic).
STATUS_STABLE_AR = "مستقر"
STATUS_STABLE_WITH_OPPORTUNITY_AR = "مستقر مع فرصة تستحق الانتباه"
STATUS_NEEDS_ATTENTION_AR = "يحتاج انتباهك"
STATUS_URGENT_AR = "يحتاج تدخلاً عاجلاً"
STATUS_INSUFFICIENT_AR = "أدلة غير كافية"

COMM_CONTACT_CONSTRAINT_AR = (
    "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
)
CART_NO_INDIVIDUAL_ACTION_AR = "لا يحتاج إجراءً فردياً الآن."
CART_OPS_NEED_FOLLOW_AR = "سلال العملاء تحتاج متابعة تشغيلية."
CART_OPS_STABLE_AR = "تقدّم سلال العملاء مستقر."

PRODUCT_SITUATION_KINDS = frozenset(
    {
        "interest_without_purchase",
        "shipping_friction",
        "product_demand",
    }
)
ACTIONABLE_SITUATION_KINDS = frozenset(
    set(PRODUCT_SITUATION_KINDS) | {"recovery_opportunity"}
)
PASSIVE_SITUATION_KINDS = frozenset({"store_health", "communication_coverage"})

_WS_RE = re.compile(r"\s+", re.UNICODE)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def normalize_action_key_v1(text: str) -> str:
    return _WS_RE.sub(" ", _norm(text)).casefold()


def _decision_action(d: Mapping[str, Any]) -> str:
    return _norm(
        d.get("merchant_decision")
        or d.get("executive_decision_ar")
        or d.get("recommended_action")
        or d.get("title")
    )


def _is_needs_action(d: Mapping[str, Any]) -> bool:
    band = _norm(d.get("priority_band"))
    return band in (BAND_NEEDS_ACTION, "needs_action", "needs_action_now")


def _subject_name(s: Mapping[str, Any]) -> str:
    sub = s.get("subject") if isinstance(s.get("subject"), Mapping) else {}
    return _norm(
        sub.get("name_ar")
        or s.get("product_name_ar")
        or s.get("title_ar")
    )


def _situation_action_ar(s: Mapping[str, Any]) -> str:
    """Product-specific merchant action — never a generic checkout loop."""
    kind = _norm(s.get("situation_kind"))
    name = _subject_name(s)
    short = name.split("—")[0].strip() if name else ""
    short = short or name or "المنتج"
    explicit = _norm(s.get("merchant_action_ar"))
    if explicit and "إتمام الشراء ومتابعة" not in explicit:
        return explicit
    if kind == "interest_without_purchase":
        return f"راجع مسار شراء {short}."
    if kind == "shipping_friction":
        return f"راجع تكلفة الشحن لمنتج {short}."
    if kind == "product_demand":
        return f"راجع أدلة الطلب لـ {short}."
    if kind == "recovery_opportunity":
        return "راجع متابعة السلال المؤهلة للاستعادة."
    return explicit or f"راجع {short}."


def _truth_version_v1(
    composition_pkg: Mapping[str, Any], situations_pkg: Mapping[str, Any] | None
) -> str:
    parts = [
        _norm(composition_pkg.get("composition_version")),
        _norm(composition_pkg.get("domain_composition_version")),
        _norm(composition_pkg.get("merchant_understanding_version")),
        _norm((situations_pkg or {}).get("version") or (situations_pkg or {}).get("schema")),
        MERCHANT_PUBLICATION_VERSION_V1,
    ]
    raw = "|".join(p for p in parts if p)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"ec1:{digest}"


def _published_situations(situations_pkg: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(situations_pkg, Mapping) or not situations_pkg.get("ok"):
        return []
    rows = list(
        situations_pkg.get("published_situations") or situations_pkg.get("situations") or []
    )
    out = [dict(s) for s in rows if isinstance(s, Mapping) and s.get("admitted")]
    out.sort(key=lambda s: (-int(s.get("priority") or 0), _norm(s.get("situation_id"))))
    return out


def _actionable_situations(situations: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(s)
        for s in situations
        if _norm(s.get("situation_kind")) in ACTIONABLE_SITUATION_KINDS
        or (
            _norm(s.get("situation_kind")) not in PASSIVE_SITUATION_KINDS
            and int(s.get("priority") or 0) >= 55
        )
    ]


def _merchant_situation_row(s: Mapping[str, Any], *, primary: bool = False) -> dict[str, Any]:
    """Merchant-safe situation projection (no technical ids in display fields)."""
    sid = _norm(s.get("situation_id"))
    subject = _subject_name(s)
    short = subject.split("—")[0].strip() if subject else ""
    short = short or subject
    kind = _norm(s.get("situation_kind"))
    statement = _norm(s.get("executive_summary_ar") or s.get("why_it_matters_ar"))
    title = _norm(s.get("title_ar"))
    # Prefer product-named merchant titles when subject is known.
    if short and kind == "interest_without_purchase":
        title = f"{short}: اهتمام مرتفع دون شراء"
        if not statement or short not in statement:
            statement = f"{short} يجذب اهتماماً واضحاً، لكن العملاء لا يكملون الشراء."
    elif short and kind == "shipping_friction":
        title = f"{short}: احتكاك الشحن يضعف الإتمام"
        if not statement or short not in statement:
            statement = f"تكلفة الشحن لـ {short} تضعف إتمام الشراء."
    elif short and kind == "product_demand":
        title = f"{short}: طلب المنتج"
        if not statement or short not in statement:
            statement = f"طلب واضح على {short} — راجع جودة الأدلة قبل التوسع."
    return {
        "situation_id": sid,  # transport / linking only — never paint on merchant UI
        "situation_kind": kind,
        "title_ar": title,
        "statement_ar": statement,
        "subject_ar": subject,
        "product_name_ar": short or subject,
        "action_ar": _situation_action_ar(s),
        "href": "#workspace",
        "is_primary": primary,
        "merchant_display": True,
    }


def compose_merchant_publication_v1(
    composition_pkg: Mapping[str, Any] | None,
    *,
    situations_pkg: Mapping[str, Any] | None = None,
    identity_pkg: Mapping[str, Any] | None = None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the executive publication envelope."""
    pkg = composition_pkg if isinstance(composition_pkg, Mapping) else {}
    sit_pkg = situations_pkg
    if sit_pkg is None and isinstance(summary, Mapping):
        raw = summary.get("commerce_situations_v1")
        sit_pkg = raw if isinstance(raw, Mapping) else None
    if sit_pkg is None:
        raw = pkg.get("commerce_situations_v1")
        sit_pkg = raw if isinstance(raw, Mapping) else None

    id_pkg = identity_pkg
    if id_pkg is None and isinstance(summary, Mapping):
        raw = summary.get("reality_validation_identity_v1")
        id_pkg = raw if isinstance(raw, Mapping) else None

    portfolio = [
        dict(d)
        for d in list(pkg.get("portfolio") or pkg.get("decisions") or [])
        if isinstance(d, Mapping) and not d.get("suppressed")
    ]
    needs = [d for d in portfolio if _is_needs_action(d)]

    situations = _published_situations(sit_pkg if isinstance(sit_pkg, Mapping) else None)
    actionable_sits = _actionable_situations(situations)
    product_sits = [
        s
        for s in actionable_sits
        if _norm(s.get("situation_kind")) in PRODUCT_SITUATION_KINDS
    ]

    signals: dict[str, Any] = {}
    domains = (
        pkg.get("business_domains_v1")
        if isinstance(pkg.get("business_domains_v1"), Mapping)
        else {}
    )
    if isinstance(domains.get("signals"), Mapping):
        signals = dict(domains.get("signals") or {})

    no_phone = _as_int(signals.get("no_phone_total"))
    waiting = _as_int(signals.get("waiting_total"))
    active = _as_int(signals.get("active_total"))
    available = bool(signals.get("available", True))
    missing_contact = no_phone > 0 or any(
        "missing_contact" in _norm(d.get("root_cause_key")).lower()
        or _norm(d.get("decision_type")).lower() == "recoverability_gap"
        for d in portfolio
    )

    # --- Primary executive decision (exactly one) ---
    # Prefer a product commerce situation as the merchant-facing lead when present.
    primary_sit: dict[str, Any] | None = None
    primary_dec: dict[str, Any] | None = None
    if product_sits:
        primary_sit = dict(product_sits[0])
        # Prefer a matching portfolio decision when present; else synthesize from situation.
        sit_id = _norm(primary_sit.get("situation_id"))
        for d in portfolio:
            if _norm(d.get("situation_id")) == sit_id:
                primary_dec = dict(d)
                break
        if primary_dec is None:
            primary_dec = {
                "decision_id": f"dce:cs:{sit_id}" if sit_id else "dce:primary_product",
                "merchant_decision": _situation_action_ar(primary_sit),
                "business_domain": "products",
                "priority_band": BAND_NEEDS_ACTION,
                "situation_id": sit_id,
                "why": _norm(
                    primary_sit.get("why_it_matters_ar")
                    or primary_sit.get("executive_summary_ar")
                ),
                "priority": int(primary_sit.get("priority") or 70),
            }
    elif needs:
        primary_dec = dict(needs[0])
        sid = _norm(primary_dec.get("situation_id"))
        if sid:
            for s in actionable_sits:
                if _norm(s.get("situation_id")) == sid:
                    primary_sit = dict(s)
                    break
    elif actionable_sits:
        primary_sit = dict(actionable_sits[0])
        primary_dec = {
            "decision_id": f"dce:cs:{_norm(primary_sit.get('situation_id'))}",
            "merchant_decision": _situation_action_ar(primary_sit),
            "business_domain": "recovery"
            if _norm(primary_sit.get("situation_kind")) == "recovery_opportunity"
            else "products",
            "priority_band": BAND_NEEDS_ACTION,
            "situation_id": _norm(primary_sit.get("situation_id")),
            "why": _norm(primary_sit.get("why_it_matters_ar")),
            "priority": int(primary_sit.get("priority") or 60),
        }

    primary_situation_id = _norm(
        (primary_sit or {}).get("situation_id")
        or (primary_dec or {}).get("situation_id")
    )
    primary_subject = ""
    if primary_sit:
        primary_subject = _subject_name(primary_sit)
    if not primary_subject and primary_dec:
        primary_subject = _norm(
            primary_dec.get("product_name_ar")
            or primary_dec.get("decision_subject_id")
        )
    if primary_sit:
        primary_action = _situation_action_ar(primary_sit)
    else:
        primary_action = _decision_action(primary_dec) if primary_dec else ""
    # Never publish the banned generic loop phrase as primary.
    if "إتمام الشراء ومتابعة العملاء" in primary_action:
        if primary_sit:
            primary_action = _situation_action_ar(primary_sit)
        elif missing_contact:
            primary_action = "راجع آلية جمع رقم العميل قبل مغادرة المتجر."
        else:
            primary_action = "راجع حالات الشراء التي تحتاج تدخلك."

    primary_decision_id = _norm((primary_dec or {}).get("decision_id"))
    primary_executive_decision = {
        "decision_id": primary_decision_id,
        "title_ar": "أهم قرار اليوم",
        "summary_ar": primary_action,
        "why_ar": _norm((primary_dec or {}).get("why") or (primary_sit or {}).get("why_it_matters_ar")),
        "subject_ar": primary_subject,
        "situation_id": primary_situation_id,
        "action_ar": primary_action,
        "is_primary": True,
        "priority_band": _norm((primary_dec or {}).get("priority_band")) or BAND_NEEDS_ACTION,
    } if primary_dec or primary_sit else None

    # Secondary situations — distinct from primary, merchant-readable only.
    supporting_secondary: list[dict[str, Any]] = []
    for s in actionable_sits:
        if _norm(s.get("situation_id")) == primary_situation_id:
            continue
        if _norm(s.get("situation_kind")) in PASSIVE_SITUATION_KINDS:
            continue
        supporting_secondary.append(_merchant_situation_row(s, primary=False))
    supporting_secondary = supporting_secondary[:4]

    secondary_decision_ids: list[str] = []
    for d in portfolio:
        did = _norm(d.get("decision_id"))
        if not did or did == primary_decision_id:
            continue
        # Suppress near-duplicate actions.
        if normalize_action_key_v1(_decision_action(d)) == normalize_action_key_v1(
            primary_action
        ):
            continue
        secondary_decision_ids.append(did)

    suppressed_dupes = [
        dict(r)
        for r in list(pkg.get("suppression_registry") or [])
        if isinstance(r, Mapping)
        and _norm(r.get("suppression_reason"))
        in {
            "duplicate",
            "duplicate_root_cause",
            "duplicate_recommended_action",
            "subsumed_by_canonical_decision",
        }
    ]

    # --- Store condition (Part 2) ---
    opportunity_n = len(product_sits) or len(actionable_sits)
    if not available and not situations and not portfolio:
        store_condition = {
            "status_ar": STATUS_INSUFFICIENT_AR,
            "summary_ar": "لا توجد أدلة كافية لتقييم حالة المتجر اليوم.",
            "needs_attention": False,
            "calm_forbidden": False,
            "state_key": "insufficient_evidence",
        }
    elif missing_contact and no_phone >= 8:
        store_condition = {
            "status_ar": STATUS_URGENT_AR,
            "summary_ar": "المتجر يحتاج تدخلاً عاجلاً — متابعة العملاء مقيدة بسبب نقص معلومات التواصل.",
            "needs_attention": True,
            "calm_forbidden": True,
            "state_key": "urgent",
        }
    elif product_sits and not (missing_contact and no_phone >= 8):
        if opportunity_n == 1:
            subj = _subject_name(product_sits[0]) or "منتج"
            short = subj.split("—")[0].strip() or subj
            summary_ar = (
                f"المتجر مستقر، لكن انخفاض التحويل في {short} يستحق انتباهك."
                if _norm(product_sits[0].get("situation_kind"))
                == "interest_without_purchase"
                else f"المتجر مستقر، لكن توجد فرصة تجارية تستحق انتباهك في {short}."
            )
        else:
            summary_ar = (
                f"المتجر مستقر، لكن توجد {opportunity_n} فرصتان تجاريتان تستحقان انتباهك."
                if opportunity_n == 2
                else f"المتجر مستقر، لكن توجد {opportunity_n} فرص تجارية تستحق انتباهك."
            )
            if opportunity_n == 2:
                summary_ar = "المتجر مستقر، لكن توجد فرصتان تجاريتان تستحقان انتباهك."
        store_condition = {
            "status_ar": STATUS_STABLE_WITH_OPPORTUNITY_AR,
            "summary_ar": summary_ar,
            "needs_attention": True,
            "calm_forbidden": True,
            "state_key": "stable_with_opportunity",
            "opportunity_count": opportunity_n,
        }
    elif needs or missing_contact:
        store_condition = {
            "status_ar": STATUS_NEEDS_ATTENTION_AR,
            "summary_ar": "المتجر يحتاج انتباهك اليوم.",
            "needs_attention": True,
            "calm_forbidden": True,
            "state_key": "needs_attention",
        }
    elif active > 0:
        store_condition = {
            "status_ar": STATUS_STABLE_AR,
            "summary_ar": "المتجر مستقر.",
            "needs_attention": False,
            "calm_forbidden": False,
            "state_key": "stable",
        }
    else:
        store_condition = {
            "status_ar": STATUS_STABLE_AR,
            "summary_ar": "المتجر مستقر.",
            "needs_attention": False,
            "calm_forbidden": False,
            "state_key": "stable",
        }

    # --- Communication ---
    if missing_contact:
        communication_condition = {
            "status_ar": STATUS_NEEDS_ATTENTION_AR,
            "summary_ar": COMM_CONTACT_CONSTRAINT_AR,
            "constrained": True,
            "normal_forbidden": True,
        }
    elif waiting > 0:
        communication_condition = {
            "status_ar": STATUS_NEEDS_ATTENTION_AR,
            "summary_ar": PREFERRED_COMM_ATTENTION_AR,
            "constrained": False,
            "normal_forbidden": True,
        }
    else:
        communication_condition = {
            "status_ar": "يعمل بصورة طبيعية",
            "summary_ar": PREFERRED_COMM_HEALTHY_AR,
            "constrained": False,
            "normal_forbidden": False,
        }

    # --- Carts ---
    if waiting > 0:
        cart_condition = {
            "summary_ar": f"{waiting} سلة تحتاج متابعة تشغيلية."
            if waiting == 1
            else f"{waiting} سلة تحتاج متابعة تشغيلية.",
            "status_ar": STATUS_NEEDS_ATTENTION_AR,
            "individual_action_ar": CART_NO_INDIVIDUAL_ACTION_AR,
            "count": waiting,
            "empty": False,
        }
        # Arabic dual for 2 is optional; keep simple count phrasing.
        if waiting == 2:
            cart_condition["summary_ar"] = "سلتان تحتاجان متابعة تشغيلية."
        elif waiting > 2:
            cart_condition["summary_ar"] = f"{waiting} سلة تحتاج متابعة تشغيلية."
    elif active > 0 or _as_int(signals.get("recovered_total")) > 0:
        cart_condition = {
            "summary_ar": CART_OPS_STABLE_AR,
            "status_ar": STATUS_STABLE_AR,
            "individual_action_ar": CART_NO_INDIVIDUAL_ACTION_AR,
            "count": active,
            "empty": False,
        }
    else:
        cart_condition = {
            "summary_ar": "لا توجد سلال تحتاج متابعة فردية حالياً.",
            "status_ar": "لا مهام",
            "individual_action_ar": CART_NO_INDIVIDUAL_ACTION_AR,
            "count": 0,
            "empty": True,
        }

    systemic = {
        "summary_ar": primary_action,
        "decision_id": primary_decision_id,
        "situation_id": primary_situation_id,
        "workspace_href": "#workspace",
    }

    home_product = None
    if primary_sit and _norm(primary_sit.get("situation_kind")) in PRODUCT_SITUATION_KINDS:
        home_product = _merchant_situation_row(primary_sit, primary=True)
    elif product_sits:
        # Primary was non-product — still surface top product as "أهم منتج".
        home_product = _merchant_situation_row(product_sits[0], primary=False)

    sim_run = ""
    if isinstance(id_pkg, Mapping):
        sim_run = _norm(id_pkg.get("simulation_run_id"))
    if not sim_run and isinstance(sit_pkg, Mapping):
        sim_run = _norm(sit_pkg.get("simulation_run_id"))

    return {
        "ok": True,
        "schema": PUBLICATION_SCHEMA_V1,
        "version": MERCHANT_PUBLICATION_VERSION_V1,
        "truth_version": _truth_version_v1(
            pkg, sit_pkg if isinstance(sit_pkg, Mapping) else None
        ),
        "simulation_run_id": sim_run,
        # Executive Control Contract V1 fields
        "store_condition": store_condition,
        "primary_executive_decision": primary_executive_decision,
        "primary_situation_id": primary_situation_id,
        "primary_subject": primary_subject,
        "primary_action": primary_action,
        "supporting_secondary_situations": supporting_secondary,
        "communication_condition": communication_condition,
        "cart_condition": cart_condition,
        # Back-compat aliases (Repair V1 consumers)
        "highest_priority_situation_id": primary_situation_id,
        "highest_priority_decision_id": primary_decision_id,
        "primary_business_action": primary_action,
        "secondary_decision_ids": secondary_decision_ids,
        "cart_operational_action": cart_condition,
        "systemic_business_action": systemic,
        "suppressed_duplicate_decisions": suppressed_dupes,
        "primary_decision": primary_executive_decision,
        "home_product_situation": home_product,
        "secondary_decisions": [
            {
                "decision_id": did,
                "is_primary": False,
                "rank": i + 2,
            }
            for i, did in enumerate(secondary_decision_ids)
        ],
        "counts": {
            "portfolio": len(portfolio),
            "needs_action_now": len(needs),
            "secondary": len(secondary_decision_ids),
            "actionable_situations": len(actionable_sits),
            "product_situations": len(product_sits),
            "suppressed_duplicates": len(suppressed_dupes),
        },
        "gate_merchant_understanding_repair_v1": True,
        "gate_executive_control_v1": True,
        "product_intelligence": False,
        "merchant_safe": True,
    }


def attach_merchant_publication_to_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str = "",
    composition_pkg: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Stamp ``merchant_publication_v1`` onto a dashboard summary or projection."""
    if not isinstance(summary, dict):
        return summary
    pkg = composition_pkg
    if pkg is None:
        slug = _norm(store_slug or summary.get("store_slug"))
        if slug:
            try:
                from services.decision_composition_engine_v1.compose_v1 import (  # noqa: PLC0415
                    compose_decisions_v1,
                )
                from services.decision_composition_engine_v1.inputs_v1 import (  # noqa: PLC0415
                    counters_from_summary_payload_v1,
                )

                counters = counters_from_summary_payload_v1(summary, store_slug=slug)
                pkg = compose_decisions_v1(
                    slug,
                    counters=counters,
                    use_cache=True,
                    allow_sync_miss=True,
                )
            except Exception:  # noqa: BLE001
                pkg = {}
    envelope = compose_merchant_publication_v1(
        pkg if isinstance(pkg, Mapping) else {},
        situations_pkg=summary.get("commerce_situations_v1")
        if isinstance(summary.get("commerce_situations_v1"), Mapping)
        else (pkg or {}).get("commerce_situations_v1"),
        identity_pkg=summary.get("reality_validation_identity_v1")
        if isinstance(summary.get("reality_validation_identity_v1"), Mapping)
        else None,
        summary=summary,
    )
    if not envelope.get("simulation_run_id") and isinstance(pkg, Mapping):
        cs = pkg.get("commerce_situations_v1")
        if isinstance(cs, Mapping):
            envelope["simulation_run_id"] = _norm(cs.get("simulation_run_id"))
    # Attach persisted primary diagnosis when available (read-only; no compose).
    try:
        from services.diagnostic_reasoning_v1.orchestrator_v1 import (  # noqa: PLC0415
            attach_diagnostic_publication_from_snapshots_v1,
        )

        attach_diagnostic_publication_from_snapshots_v1(
            summary, store_slug=_norm(store_slug or summary.get("store_slug"))
        )
        primary_dx = summary.get("diagnostic_publication_v1")
        if isinstance(primary_dx, Mapping) and primary_dx.get("diagnosis_ar"):
            envelope["primary_diagnosis"] = dict(primary_dx)
            envelope["diagnostic_reasoning_v1"] = True
    except Exception:  # noqa: BLE001
        pass
    summary["merchant_publication_v1"] = envelope
    return summary


def apply_publication_priority_to_decisions_v1(
    decisions: list[dict[str, Any]],
    publication: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Mark primary / secondary on decision cards; primary first; product-specific actions."""
    pub = publication if isinstance(publication, Mapping) else {}
    primary_id = _norm(
        pub.get("highest_priority_decision_id")
        or (pub.get("primary_executive_decision") or {}).get("decision_id")
    )
    primary_action = _norm(pub.get("primary_action") or pub.get("primary_business_action"))
    primary_sit = _norm(
        pub.get("primary_situation_id") or pub.get("highest_priority_situation_id")
    )
    secondary_ids = {
        _norm(x) for x in list(pub.get("secondary_decision_ids") or []) if _norm(x)
    }
    out: list[dict[str, Any]] = []
    for raw in decisions:
        if not isinstance(raw, Mapping):
            continue
        d = dict(raw)
        did = _norm(d.get("decision_id"))
        sid = _norm(d.get("situation_id"))
        is_primary = bool(
            (primary_id and did == primary_id)
            or (primary_sit and sid == primary_sit and not any(
                x.get("is_primary_decision") for x in out
            ))
        )
        if is_primary:
            d["is_primary_decision"] = True
            d["priority_rank_label_ar"] = "القرار الأهم"
            d["portfolio_rank"] = 1
            if primary_action:
                d["merchant_decision"] = primary_action
                d["title"] = primary_action
                d["executive_decision_ar"] = primary_action
                d["required_merchant_action"] = primary_action
        elif did in secondary_ids or (sid and sid != primary_sit):
            d["is_primary_decision"] = False
            d["priority_rank_label_ar"] = "قرار ثانوي"
            if not d.get("portfolio_rank"):
                d["portfolio_rank"] = 2
        else:
            d["is_primary_decision"] = False
        # Strip technical fields from merchant card payload display helpers.
        d["merchant_safe"] = True
        out.append(d)
    # Ensure exactly one primary when publication has one.
    if primary_id or primary_sit:
        seen_primary = False
        for d in out:
            if d.get("is_primary_decision"):
                if seen_primary:
                    d["is_primary_decision"] = False
                    d["priority_rank_label_ar"] = "قرار ثانوي"
                else:
                    seen_primary = True
    out.sort(
        key=lambda d: (
            0 if d.get("is_primary_decision") else 1,
            int(d.get("portfolio_rank") or 99),
            -int(d.get("priority") or 0),
            _norm(d.get("decision_id")),
        )
    )
    return out


def semantic_parity_fingerprint_v1(publication: Mapping[str, Any] | None) -> dict[str, Any]:
    """Canonical meaning fields for Mobile/Desktop parity tests."""
    pub = publication if isinstance(publication, Mapping) else {}
    sc = pub.get("store_condition") if isinstance(pub.get("store_condition"), Mapping) else {}
    ped = (
        pub.get("primary_executive_decision")
        if isinstance(pub.get("primary_executive_decision"), Mapping)
        else {}
    )
    cc = (
        pub.get("communication_condition")
        if isinstance(pub.get("communication_condition"), Mapping)
        else {}
    )
    cart = pub.get("cart_condition") if isinstance(pub.get("cart_condition"), Mapping) else {}
    secondary = list(pub.get("supporting_secondary_situations") or [])
    return {
        "store_condition_status_ar": _norm(sc.get("status_ar")),
        "store_condition_summary_ar": _norm(sc.get("summary_ar")),
        "primary_action": _norm(pub.get("primary_action") or ped.get("action_ar")),
        "primary_subject": _norm(pub.get("primary_subject") or ped.get("subject_ar")),
        "primary_situation_id": _norm(pub.get("primary_situation_id")),
        "primary_decision_id": _norm(
            pub.get("highest_priority_decision_id") or ped.get("decision_id")
        ),
        "communication_summary_ar": _norm(cc.get("summary_ar")),
        "cart_summary_ar": _norm(cart.get("summary_ar")),
        "secondary_titles_ar": [
            _norm(s.get("title_ar"))
            for s in secondary
            if isinstance(s, Mapping) and _norm(s.get("title_ar"))
        ],
        "truth_version": _norm(pub.get("truth_version")),
        "simulation_run_id": _norm(pub.get("simulation_run_id")),
        "opportunity_count": int((sc.get("opportunity_count") or 0) or 0),
    }


__all__ = [
    "CART_NO_INDIVIDUAL_ACTION_AR",
    "COMM_CONTACT_CONSTRAINT_AR",
    "MERCHANT_PUBLICATION_VERSION_V1",
    "STATUS_NEEDS_ATTENTION_AR",
    "STATUS_STABLE_AR",
    "STATUS_STABLE_WITH_OPPORTUNITY_AR",
    "STATUS_URGENT_AR",
    "apply_publication_priority_to_decisions_v1",
    "attach_merchant_publication_to_summary_v1",
    "compose_merchant_publication_v1",
    "normalize_action_key_v1",
    "semantic_parity_fingerprint_v1",
]
