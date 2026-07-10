# -*- coding: utf-8 -*-
"""
Merchant Pulse V1 — immutable store-level projection.

Answers only:
  1. What is happening?          → executive_brief
  2. Should the merchant act?    → decision_summary
  3. What has CartFlow done?     → cartflow_progress
  4. What is the single next?    → merchant_decision

Projection only: consumes existing summary / Brief / Home / Decision /
WhatsApp readiness / store connection fields. When
CARTFLOW_COMMERCE_SIGNALS_V1 is on and store-scoped Signals are
attached, Recovery/Purchase Signals feed “what happened” facts for
executive_brief + cartflow_progress only. Recovered-purchase wording is
owned by Commerce Language V1 (amounts from existing recovered cart
truth). Decision slots stay on governed Decision inputs except calm
Leave copy when a recovered purchase outcome applies. Does not mint
Truth, Decisions, or Guidance. No AI. No persistence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.commerce_language_v1 import (
    DECISION_SUMMARY_NO_INTERVENTION_AR,
    MERCHANT_DECISION_NO_DECISION_AR,
    collect_recovered_purchase_keys,
    is_recovered_purchase_signal_type,
    recovered_purchase_outcome_ar,
    resolve_recovered_purchase_total,
)
from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_BLOCKED,
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_RECOVERY_PROGRESSED,
    SIGNAL_RECOVERY_STARTED,
)
from services.commerce_signals_v1_flag import commerce_signals_v1_enabled
from services.merchant_decision_layer_v1 import (
    CLASS_CRITICAL_ACTION,
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
)
from services.merchant_pulse_v1_flag import merchant_pulse_v1_enabled

# Fallback Pulse fact lines for non-recovered Signal types (not Commerce Language).
# Recovered purchase / recovery_completed copy is owned by commerce_language_v1.
_SIGNAL_FACT_AR: dict[str, str] = {
    SIGNAL_PURCHASE_CONFIRMED: "تم تأكيد شراء مرتبط بسلة قيد المتابعة.",
    SIGNAL_RECOVERY_COMPLETED: "اكتمل مسار استرجاع بعد تأكيد الشراء.",
    SIGNAL_RECOVERY_PROGRESSED: "تحرّك مسار الاسترجاع على سلة واحدة على الأقل.",
    SIGNAL_RECOVERY_STARTED: "بدأ مسار استرجاع لسلة.",
    SIGNAL_RECOVERY_BLOCKED: "توقف مسار استرجاع — حقيقة مسجّلة دون طلب تدخل من الإشارة.",
}

_WHAT_HAPPENED_PRIORITY: tuple[str, ...] = (
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_PROGRESSED,
    SIGNAL_RECOVERY_STARTED,
    SIGNAL_RECOVERY_BLOCKED,
)

PULSE_VERSION = "v1"
PULSE_PROJECTION = "MerchantPulseV1"

STATUS_HEALTHY = "healthy"
STATUS_REQUIRE_ACTION = "require_action"
STATUS_NO_ACTION = "no_action"
STATUS_UNKNOWN = "unknown"
STATUS_LOADING = "loading"

FORK_LEAVE = "leave"
FORK_ENTER_WORK = "enter_work"

_CONF_HIGH = "high"
_CONF_MEDIUM = "medium"
_CONF_LOW = "low"
_CONF_UNKNOWN = "unknown"
_CONF_INSUFFICIENT = "insufficient"

_REQUIRE_CLASSES = frozenset({CLASS_CRITICAL_ACTION, CLASS_NEEDS_ATTENTION})
_RECOMMEND_CLASSES = frozenset({CLASS_SUGGESTED_ACTION})


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_map(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _conf_norm(value: Any) -> str:
    c = _norm(value).lower()
    if c in (_CONF_HIGH, _CONF_MEDIUM, _CONF_LOW, _CONF_UNKNOWN, _CONF_INSUFFICIENT):
        return c
    return _CONF_UNKNOWN


def _slot(
    *,
    status: str,
    message: str,
    confidence: str,
    last_updated: str,
    **extra: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": status,
        "message": _norm(message) or "—",
        "confidence": _conf_norm(confidence),
        "last_updated": _norm(last_updated) or _utc_now_iso(),
    }
    for key, val in extra.items():
        if val is not None:
            out[key] = val
    return out


def _loading_slot(last_updated: str) -> dict[str, Any]:
    return _slot(
        status=STATUS_LOADING,
        message="جارٍ التحديث…",
        confidence=_CONF_UNKNOWN,
        last_updated=last_updated,
    )


def _first_item(items: Any) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}
    for raw in items:
        if isinstance(raw, Mapping):
            return dict(raw)
    return {}


def _attention_items(home: Mapping[str, Any], brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    section = _as_map(home.get("attention_today"))
    items = section.get("items")
    if isinstance(items, list) and items:
        return [dict(x) for x in items if isinstance(x, Mapping)]
    for key in ("attention_items", "items"):
        raw = brief.get(key)
        if isinstance(raw, list) and raw:
            return [dict(x) for x in raw if isinstance(x, Mapping)]
    return []


def _while_away_items(home: Mapping[str, Any], brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    section = _as_map(home.get("while_away"))
    items = section.get("items")
    if isinstance(items, list) and items:
        return [dict(x) for x in items if isinstance(x, Mapping)]
    raw = brief.get("achievements")
    if isinstance(raw, list) and raw:
        return [dict(x) for x in raw if isinstance(x, Mapping)]
    return []


def _top_require_item(attention: list[Mapping[str, Any]]) -> dict[str, Any]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for raw in attention:
        cls = _norm(raw.get("decision_class")).lower()
        if cls == CLASS_CRITICAL_ACTION:
            ranked.append((2, dict(raw)))
        elif cls == CLASS_NEEDS_ATTENTION:
            ranked.append((1, dict(raw)))
    if not ranked:
        return {}
    ranked.sort(key=lambda t: t[0], reverse=True)
    return ranked[0][1]


def _wa_blocks_health(wa: Mapping[str, Any]) -> bool:
    overall = _norm(wa.get("readiness_overall")).lower()
    if overall and overall not in ("ready", "ok", "healthy"):
        # Connected/paused may still be operable; treat explicit not-ready.
        if overall in ("not_ready", "blocked", "setup_required", "provider_issue"):
            return True
    state = _norm(wa.get("connection_state")).lower()
    if state in (
        "setup_required",
        "provider_issue",
        "pending_configuration",
    ):
        return True
    badge = _norm(wa.get("badge") or wa.get("status") or wa.get("tone")).lower()
    if badge in ("error", "danger", "blocked", "critical"):
        return True
    return False


def _store_connection_ok(conn: Mapping[str, Any]) -> Optional[bool]:
    if not conn:
        return None
    if "ok" in conn:
        return bool(conn.get("ok"))
    if "connected" in conn:
        return bool(conn.get("connected"))
    state = _norm(conn.get("connection_state") or conn.get("status")).lower()
    if not state:
        return None
    if state in ("connected", "ok", "ready", "live"):
        return True
    if state in ("disconnected", "error", "missing", "not_connected"):
        return False
    return None


def _mi_needs_merchant(mi: Mapping[str, Any]) -> Optional[bool]:
    if not mi:
        return None
    for group in mi.get("groups") or []:
        if not isinstance(group, Mapping):
            continue
        gid = _norm(group.get("group_id") or group.get("id")).lower()
        if gid == "needs_merchant":
            count = int(group.get("cart_count") or group.get("count") or 0)
            return count > 0
    for rec in mi.get("recommendations") or []:
        if not isinstance(rec, Mapping):
            continue
        if _norm(rec.get("recommendation_type")).lower() == "required_action":
            return True
    for pri in mi.get("priorities") or []:
        if not isinstance(pri, Mapping):
            continue
        if _norm(pri.get("band")).lower() == "highest":
            return True
    return False


def _commerce_signals_from_body(
    src: Mapping[str, Any],
    *,
    store_slug: str,
) -> list[dict[str, Any]]:
    """Read store-scoped Signals from summary. Empty when flag off or unavailable."""
    if not commerce_signals_v1_enabled():
        return []
    raw = src.get("commerce_signals_v1")
    if isinstance(raw, Mapping):
        items = raw.get("signals")
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    if not isinstance(items, list) or not items:
        return []
    ss = _norm(store_slug)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        st = _norm(item.get("signal_type"))
        if st not in _SIGNAL_FACT_AR:
            continue
        subject = _as_map(item.get("subject"))
        sub_store = _norm(subject.get("store_slug"))
        if ss and sub_store and sub_store != ss:
            continue
        rk = _norm(subject.get("recovery_key"))
        dedupe = (st, rk)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        out.append(dict(item))
    return out


def _pick_what_happened_signal(
    signals: list[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    if not signals:
        return None
    by_type: dict[str, dict[str, Any]] = {}
    for sig in signals:
        st = _norm(sig.get("signal_type"))
        if st and st not in by_type:
            by_type[st] = dict(sig)
    for st in _WHAT_HAPPENED_PRIORITY:
        if st in by_type:
            return by_type[st]
    return None


def _hidden_progress_slot(*, last_updated: str, signal_type: str = "") -> dict[str, Any]:
    """cartflow_progress must not repeat executive_brief — hide the slot."""
    return _slot(
        status=STATUS_NO_ACTION,
        message="—",
        confidence=_CONF_UNKNOWN,
        last_updated=last_updated,
        signal_type=signal_type or None,
        hidden=True,
    )


def _recovered_purchase_message(
    signals: list[Mapping[str, Any]],
    *,
    store_slug: str,
    amounts_by_key: Optional[Mapping[str, Optional[float]]] = None,
) -> str:
    keys = collect_recovered_purchase_keys(signals)
    count, total = resolve_recovered_purchase_total(
        count=len(keys),
        amounts_by_key=amounts_by_key,
        recovery_keys=keys,
        store_slug=store_slug,
    )
    if count <= 0:
        count = 1
    return recovered_purchase_outcome_ar(count=count, total_value=total)


def _what_happened_slots_from_signals(
    signals: list[Mapping[str, Any]],
    *,
    last_updated: str,
    store_slug: str = "",
    amounts_by_key: Optional[Mapping[str, Optional[float]]] = None,
) -> Optional[tuple[dict[str, Any], dict[str, Any], list[str], bool, dict[str, Any]]]:
    """
    Build executive_brief + cartflow_progress candidates from Signals only.

    Returns (brief, progress_hidden, types_used, recovered_outcome, progress_visible).
    progress_hidden avoids duplicating brief on Leave; progress_visible is for
    Require when Decision owns the brief.
    recovery_blocked never implies Require / Enter Work.
    """
    picked = _pick_what_happened_signal(signals)
    if not picked:
        return None
    st = _norm(picked.get("signal_type"))
    observed = _norm(picked.get("observed_at")) or last_updated
    types_used = sorted(
        {
            _norm(s.get("signal_type"))
            for s in signals
            if _norm(s.get("signal_type")) in _SIGNAL_FACT_AR
        }
    )

    recovered_outcome = is_recovered_purchase_signal_type(st)
    if recovered_outcome:
        fact = _recovered_purchase_message(
            signals,
            store_slug=store_slug,
            amounts_by_key=amounts_by_key,
        )
        conf = _CONF_HIGH
        brief_status = STATUS_HEALTHY
    else:
        fact = _SIGNAL_FACT_AR.get(st)
        if not fact:
            return None
        conf = _CONF_MEDIUM
        brief_status = (
            STATUS_NO_ACTION if st == SIGNAL_RECOVERY_BLOCKED else STATUS_HEALTHY
        )

    brief = _slot(
        status=brief_status,
        message=fact,
        confidence=conf,
        last_updated=observed,
        signal_type=st,
    )
    # Visible progress copy for Require path (brief owned by Decision).
    progress_visible = _slot(
        status=STATUS_HEALTHY if recovered_outcome else brief_status,
        message=fact,
        confidence=conf,
        last_updated=observed,
        signal_type=st,
    )
    progress_hidden = _hidden_progress_slot(last_updated=observed, signal_type=st)
    # Default Leave assignment: never duplicate brief in progress.
    return brief, progress_hidden, types_used, recovered_outcome, progress_visible


def build_merchant_pulse_v1_from_summary(
    body: Optional[Mapping[str, Any]] = None,
    *,
    loading: bool = False,
    store_slug: str = "",
    now_iso: Optional[str] = None,
    recovered_amounts_by_key: Optional[Mapping[str, Optional[float]]] = None,
) -> dict[str, Any]:
    """
    Build immutable MerchantPulseV1 from a dashboard summary body.

    Snapshot-safe for Decision/Home fields. Recovered purchase amounts are
    read from existing AbandonedCart cart_value (or recovered_amounts_by_key
    in tests) — never invented.
    """
    ts = _norm(now_iso) or _utc_now_iso()
    src = body if isinstance(body, Mapping) else {}
    slug = _norm(store_slug) or _norm(src.get("store_slug"))

    if loading or src.get("ok") is False:
        loading_slot = _loading_slot(ts)
        return {
            "ok": True,
            "version": PULSE_VERSION,
            "projection": PULSE_PROJECTION,
            "generated_at": ts,
            "store_slug": slug,
            "status": STATUS_LOADING,
            "fork": FORK_LEAVE,
            "executive_brief": dict(loading_slot),
            "decision_summary": dict(loading_slot),
            "cartflow_progress": dict(loading_slot),
            "merchant_decision": dict(loading_slot),
            "sources": {"mode": "loading"},
        }

    home = _as_map(src.get("merchant_home_experience_v1"))
    brief = _as_map(src.get("merchant_daily_brief_v1"))
    if not brief:
        brief = _as_map(home.get("daily_brief_v1"))
    mi = _as_map(src.get("merchant_intelligence_store_v1"))
    wa = _as_map(src.get("whatsapp_readiness_card"))
    conn = _as_map(src.get("store_connection"))
    counter_health = _as_map(src.get("merchant_counter_health"))

    last_updated = (
        _norm(home.get("generated_at"))
        or _norm(brief.get("generated_at"))
        or _norm(brief.get("brief_date"))
        or _norm(src.get("generated_at"))
        or ts
    )

    attention = _attention_items(home, brief)
    while_away = _while_away_items(home, brief)
    require_item = _top_require_item(attention)
    first_attention = _first_item(attention)
    first_away = _first_item(while_away)
    signals = _commerce_signals_from_body(src, store_slug=slug)
    # Optional test/summary override: body.commerce_language_v1.amounts_by_key
    amounts_override = recovered_amounts_by_key
    if amounts_override is None:
        cl = _as_map(src.get("commerce_language_v1"))
        raw_amounts = cl.get("amounts_by_key")
        if isinstance(raw_amounts, Mapping):
            amounts_override = {}
            for k, v in raw_amounts.items():
                key = _norm(k)
                if not key:
                    continue
                if v is None:
                    amounts_override[key] = None
                    continue
                try:
                    amounts_override[key] = float(v)
                except (TypeError, ValueError):
                    amounts_override[key] = None
    signal_what = _what_happened_slots_from_signals(
        signals,
        last_updated=last_updated,
        store_slug=slug,
        amounts_by_key=amounts_override,
    )

    # --- decision_summary (Should I act?) ---
    # Governed Decision / Home / MI inputs only — Signals never set stance.
    mi_needed = _mi_needs_merchant(mi)
    has_require = bool(require_item)
    has_recommend_only = bool(first_attention) and not has_require and (
        _norm(first_attention.get("decision_class")).lower() in _RECOMMEND_CLASSES
        or bool(first_attention.get("action_present"))
    )

    if has_require:
        cls = _norm(require_item.get("decision_class")).lower() or CLASS_NEEDS_ATTENTION
        decision_summary = _slot(
            status=STATUS_REQUIRE_ACTION,
            message=_norm(require_item.get("headline_ar"))
            or _norm(require_item.get("action_ar"))
            or "يوجد أمر يحتاج قرارك الآن.",
            confidence=_conf_norm(require_item.get("confidence")) or _CONF_HIGH,
            last_updated=last_updated,
            decision_class=cls,
            stance="require",
        )
    elif mi_needed is True and not attention and not while_away:
        # MI says needed but no brief line yet — honest unknown ask, not invent Work copy
        decision_summary = _slot(
            status=STATUS_UNKNOWN,
            message="قد يوجد ما يحتاجك — لا تتوفر تفاصيل كافية بعد.",
            confidence=_CONF_INSUFFICIENT,
            last_updated=last_updated,
            stance="unknown",
        )
    elif has_recommend_only:
        # Recommend is not Interrupt — Leave fork; stance optional
        decision_summary = _slot(
            status=STATUS_NO_ACTION,
            message="لا يوجد ما يفرض تدخلك الآن — خطوة اختيارية فقط إن رغبت لاحقاً.",
            confidence=_conf_norm(first_attention.get("confidence")) or _CONF_MEDIUM,
            last_updated=last_updated,
            decision_class=_norm(first_attention.get("decision_class")).lower(),
            stance="recommend_optional",
        )
    elif attention or while_away or mi_needed is False or home.get("empty_calm"):
        decision_summary = _slot(
            status=STATUS_NO_ACTION,
            message=_norm(_as_map(home.get("attention_today")).get("empty_message_ar"))
            or "لا شيء يحتاجك الآن.",
            confidence=_CONF_HIGH if (attention or while_away or home.get("empty_calm")) else _CONF_MEDIUM,
            last_updated=last_updated,
            stance="no_action",
        )
    else:
        decision_summary = _slot(
            status=STATUS_UNKNOWN,
            message="غير معروف بعد — لن نخترع عملاً.",
            confidence=_CONF_UNKNOWN,
            last_updated=last_updated,
            stance="unknown",
        )

    # --- executive_brief (What is happening?) ---
    # Prefer Signals for Recovery/Purchase facts when available and Decision
    # is not Require (Require brief stays Decision-owned). Avoid duplicating
    # the same fact from while_away when Signals already supplied it.
    if signal_what is not None and not has_require:
        executive_brief = dict(signal_what[0])
    elif has_require:
        why = _norm(require_item.get("why_ar"))
        msg = _norm(require_item.get("headline_ar")) or _norm(require_item.get("what_ar"))
        if why and why not in msg:
            msg = f"{msg} — {why}" if msg else why
        executive_brief = _slot(
            status=STATUS_REQUIRE_ACTION,
            message=msg or "المتجر يحتاج انتباهك الآن.",
            confidence=decision_summary["confidence"],
            last_updated=last_updated,
        )
    elif first_away:
        msg = _norm(first_away.get("headline_ar")) or _norm(first_away.get("detail_ar"))
        executive_brief = _slot(
            status=STATUS_HEALTHY,
            message=msg or "المتجر هادئ نسبياً الآن.",
            confidence=_CONF_MEDIUM,
            last_updated=last_updated,
        )
    elif first_attention and not has_require:
        msg = _norm(first_attention.get("headline_ar")) or _norm(first_attention.get("what_ar"))
        executive_brief = _slot(
            status=STATUS_HEALTHY,
            message=msg or "لا يوجد ما يفرض تدخلك الآن.",
            confidence=_CONF_MEDIUM,
            last_updated=last_updated,
        )
    elif home.get("empty_calm") or (not attention and not while_away and mi_needed is not True):
        executive_brief = _slot(
            status=STATUS_HEALTHY if decision_summary["status"] == STATUS_NO_ACTION else STATUS_UNKNOWN,
            message=_norm(_as_map(home.get("while_away")).get("empty_message_ar"))
            or "لا تتوفر صورة كافية بعد — أو المتجر هادئ.",
            confidence=_CONF_MEDIUM if home.get("empty_calm") else _CONF_UNKNOWN,
            last_updated=last_updated,
        )
    else:
        executive_brief = _slot(
            status=STATUS_UNKNOWN,
            message="غير معروف بعد ما يحدث في المتجر بثقة كافية.",
            confidence=_CONF_UNKNOWN,
            last_updated=last_updated,
        )

    # --- cartflow_progress (What did CartFlow accomplish?) ---
    # Never duplicate executive_brief. Recovered Leave → hide progress.
    # Require + Signals → show Signal/Commerce Language outcome in progress only.
    recovered_outcome = bool(signal_what is not None and signal_what[3])
    if signal_what is not None and has_require:
        cartflow_progress = dict(signal_what[4])
    elif signal_what is not None:
        cartflow_progress = dict(signal_what[1])
    elif first_away:
        detail = _norm(first_away.get("detail_ar"))
        headline = _norm(first_away.get("headline_ar"))
        msg = headline
        if detail and detail not in headline:
            msg = f"{headline} — {detail}" if headline else detail
        cartflow_progress = _slot(
            status=STATUS_HEALTHY,
            message=msg or "أنجز CartFlow متابعة قابلة للقياس.",
            confidence=_CONF_MEDIUM,
            last_updated=last_updated,
            evidence_ref=_norm(first_away.get("source_knowledge_id") or first_away.get("aggregation_key"))
            or None,
        )
    elif has_require:
        cartflow_progress = _slot(
            status=STATUS_UNKNOWN,
            message="لا يوجد إنجاز مكتمل للعرض — التركيز على ما يحتاجك الآن.",
            confidence=_CONF_LOW,
            last_updated=last_updated,
        )
    elif home.get("empty_calm"):
        cartflow_progress = _slot(
            status=STATUS_NO_ACTION,
            message="لا إنجازات للعرض بعد — المتابعة الروتينية مستمرة.",
            confidence=_CONF_MEDIUM,
            last_updated=last_updated,
        )
    else:
        cartflow_progress = _slot(
            status=STATUS_UNKNOWN,
            message="غير معروف بعد ما أنجزه CartFlow في هذه النافذة.",
            confidence=_CONF_UNKNOWN,
            last_updated=last_updated,
        )

    # --- merchant_decision (single next) ---
    # Signals never set fork / merchant_decision.
    if has_require:
        action = _norm(require_item.get("action_ar"))
        headline = _norm(require_item.get("headline_ar"))
        msg = action or headline or "راجع السلة التي تحتاج قرارك."
        merchant_decision = _slot(
            status=STATUS_REQUIRE_ACTION,
            message=msg,
            confidence=decision_summary["confidence"],
            last_updated=last_updated,
            decision_class=_norm(require_item.get("decision_class")).lower(),
            action_present=bool(require_item.get("action_present") or action),
            work_entry="carts",
            source_knowledge_id=_norm(require_item.get("source_knowledge_id")) or None,
            aggregation_key=_norm(require_item.get("aggregation_key")) or None,
        )
        fork = FORK_ENTER_WORK
    else:
        # Health interrupt: only when readiness clearly blocked AND we have no calm empty
        wa_bad = _wa_blocks_health(wa)
        conn_ok = _store_connection_ok(conn)
        counter_degraded = bool(counter_health.get("degraded") or counter_health.get("unhealthy"))
        if wa_bad or conn_ok is False or counter_degraded:
            # Trust-ish — Pulse must not become diagnostics; force unknown leave
            # unless Decision already required (handled above).
            merchant_decision = _slot(
                status=STATUS_UNKNOWN,
                message="لا يمكن تأكيد أن شيئاً يحتاجك بثقة — لن نخترع عملاً.",
                confidence=_CONF_INSUFFICIENT,
                last_updated=last_updated,
                work_entry=None,
            )
            fork = FORK_LEAVE
            if decision_summary["status"] == STATUS_NO_ACTION:
                decision_summary = _slot(
                    status=STATUS_UNKNOWN,
                    message="غير معروف — جاهزية القناة أو الاتصال غير مؤكدة.",
                    confidence=_CONF_INSUFFICIENT,
                    last_updated=last_updated,
                    stance="unknown",
                )
        elif decision_summary["status"] == STATUS_NO_ACTION:
            merchant_decision = _slot(
                status=STATUS_NO_ACTION,
                message="لا قرار مطلوب — يمكنك المغادرة.",
                confidence=_CONF_HIGH,
                last_updated=last_updated,
                work_entry=None,
            )
            fork = FORK_LEAVE
        else:
            merchant_decision = _slot(
                status=STATUS_UNKNOWN,
                message="لا قرار واحد واضح بعد.",
                confidence=_CONF_UNKNOWN,
                last_updated=last_updated,
                work_entry=None,
            )
            fork = FORK_LEAVE

    # Commerce Language: recovered purchase Leave — calm decision copy (no invent).
    # Applies even when Home/Brief is empty (would otherwise be UNKNOWN).
    if recovered_outcome and not has_require and fork == FORK_LEAVE:
        wa_bad = _wa_blocks_health(wa)
        conn_ok = _store_connection_ok(conn)
        counter_degraded = bool(
            counter_health.get("degraded") or counter_health.get("unhealthy")
        )
        if not (wa_bad or conn_ok is False or counter_degraded):
            decision_summary = _slot(
                status=STATUS_NO_ACTION,
                message=DECISION_SUMMARY_NO_INTERVENTION_AR,
                confidence=_CONF_HIGH,
                last_updated=last_updated,
                stance="no_action",
            )
            merchant_decision = _slot(
                status=STATUS_NO_ACTION,
                message=MERCHANT_DECISION_NO_DECISION_AR,
                confidence=_CONF_HIGH,
                last_updated=last_updated,
                work_entry=None,
            )

    # Guard: never allow the same merchant sentence in two slots.
    brief_msg = _norm(executive_brief.get("message"))
    progress_msg = _norm(cartflow_progress.get("message"))
    if (
        brief_msg
        and progress_msg
        and brief_msg == progress_msg
        and not cartflow_progress.get("hidden")
    ):
        cartflow_progress = _hidden_progress_slot(
            last_updated=_norm(cartflow_progress.get("last_updated")) or last_updated,
            signal_type=_norm(cartflow_progress.get("signal_type")),
        )

    # --- overall status ---
    if fork == FORK_ENTER_WORK:
        overall = STATUS_REQUIRE_ACTION
    elif (
        decision_summary["status"] == STATUS_UNKNOWN
        or executive_brief["status"] == STATUS_UNKNOWN
        or merchant_decision["status"] == STATUS_UNKNOWN
    ):
        overall = STATUS_UNKNOWN
    elif decision_summary["status"] == STATUS_NO_ACTION:
        overall = STATUS_HEALTHY if cartflow_progress["status"] in (
            STATUS_HEALTHY,
            STATUS_NO_ACTION,
        ) else STATUS_NO_ACTION
    else:
        overall = STATUS_NO_ACTION

    return {
        "ok": True,
        "version": PULSE_VERSION,
        "projection": PULSE_PROJECTION,
        "generated_at": ts,
        "store_slug": slug,
        "status": overall,
        "fork": fork,
        "executive_brief": executive_brief,
        "decision_summary": decision_summary,
        "cartflow_progress": cartflow_progress,
        "merchant_decision": merchant_decision,
        "sources": {
            "home_attached": bool(home.get("ok")),
            "brief_version": _norm(brief.get("version")),
            "attention_count": len(attention),
            "while_away_count": len(while_away),
            "mi_attached": bool(mi),
            "whatsapp_readiness_attached": bool(wa),
            "store_connection_attached": bool(conn),
            "commerce_signals_used": bool(signal_what is not None),
            "commerce_signal_types": list(signal_what[2]) if signal_what is not None else [],
        },
    }


def attach_merchant_pulse_v1_to_summary(
    body: dict[str, Any],
    *,
    store_slug: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Attach MerchantPulseV1 when flag enabled (or force=True for tests)."""
    if not isinstance(body, dict):
        body = dict(body or {})
    if not force and not merchant_pulse_v1_enabled():
        body.pop("merchant_pulse_v1", None)
        return body
    if body.get("ok") is False:
        body["merchant_pulse_v1"] = build_merchant_pulse_v1_from_summary(
            body,
            loading=True,
            store_slug=store_slug,
        )
        return body
    body["merchant_pulse_v1"] = build_merchant_pulse_v1_from_summary(
        body,
        store_slug=store_slug,
    )
    return body


__all__ = [
    "FORK_ENTER_WORK",
    "FORK_LEAVE",
    "PULSE_PROJECTION",
    "PULSE_VERSION",
    "STATUS_HEALTHY",
    "STATUS_LOADING",
    "STATUS_NO_ACTION",
    "STATUS_REQUIRE_ACTION",
    "STATUS_UNKNOWN",
    "attach_merchant_pulse_v1_to_summary",
    "build_merchant_pulse_v1_from_summary",
]
