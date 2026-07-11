# -*- coding: utf-8 -*-
"""
Merchant Value Composition v1 — governed value stories from MI + explanation.

Composes existing intelligence, recommendations, memory, and explanation into
merchant-facing value stories. Does not mint groups, recommendations, or truth.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.merchant_cart_fact_v1 import FACT_KIND_PURCHASED
from services.merchant_intelligence_v1 import (
    GROUP_AWAITING_SEND,
    GROUP_COMPLETED,
    GROUP_NEEDS_MERCHANT,
    GROUP_REPEATED_HESITATION,
    GROUP_RETURNED,
    GROUP_WAITING_PURCHASE,
    GROUP_WAITING_REPLY,
    REC_NO_ACTION,
    REC_REQUIRED,
    REC_SUGGESTED,
    REC_WATCH,
    SURFACE_CARTS,
)

VALUE_VERSION = "v1"
AUTHORITY = "merchant_value_composition_v1"

STORY_PRICE_HESITATION = "price_hesitation_story"
STORY_SHIPPING_HESITATION = "shipping_hesitation_story"
STORY_RETURNED_WITHOUT_PURCHASE = "returned_without_purchase_story"
STORY_RECOVERED_PURCHASE = "recovered_purchase_story"
STORY_NEEDS_MERCHANT = "needs_merchant_story"
STORY_WAITING_REPLY = "waiting_reply_story"
STORY_AWAITING_SEND = "awaiting_send_story"

_REASON_TAG_AR = {
    "price": "السعر",
    "shipping": "الشحن",
    "delivery": "التوصيل",
    "quality": "الجودة",
    "size": "المقاس",
    "payment": "الدفع",
    "trust": "الثقة",
    "other": "أسباب أخرى",
}

_STORY_TYPE_ORDER = (
    STORY_NEEDS_MERCHANT,
    STORY_PRICE_HESITATION,
    STORY_SHIPPING_HESITATION,
    STORY_RETURNED_WITHOUT_PURCHASE,
    STORY_AWAITING_SEND,
    STORY_WAITING_REPLY,
    STORY_RECOVERED_PURCHASE,
)

_ROI_FORBIDDEN_FRAGMENTS = (
    "استعدنا",
    "حققنا لك",
    "مبيعات مستردة",
    "revenue",
    "ROI",
)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _recovery_key(row: Mapping[str, Any]) -> str:
    return _norm(row.get("recovery_key") or row.get("zid_cart_id") or row.get("cart_id"))


def _rows_by_recovery_key(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        rk = _recovery_key(row)
        if rk:
            out[rk] = row
    return out


def _group_rows(group: Mapping[str, Any], rows_by_key: Mapping[str, Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    keys = group.get("affected_cart_keys")
    if isinstance(keys, list) and keys:
        return [rows_by_key[_norm(k)] for k in keys if _norm(k) in rows_by_key]
    gid = _norm(group.get("group_id"))
    pk = _norm(group.get("pattern_key"))
    if pk.startswith("reason:"):
        tag = pk[7:].lower()
        return [
            r
            for r in rows_by_key.values()
            if _norm_lower(r.get("reason_tag")) == tag
        ]
    return [r for r in rows_by_key.values() if _row_group_key(r) == gid]


def _row_group_key(row: Mapping[str, Any]) -> str:
    key = _norm(row.get("intelligence_group_key"))
    if key:
        return key
    mi = row.get("merchant_intelligence_v1")
    if isinstance(mi, Mapping):
        return _norm(mi.get("intelligence_group_key"))
    return ""


def _explanation(row: Mapping[str, Any]) -> Mapping[str, Any]:
    expl = row.get("merchant_explanation_v1")
    return expl if isinstance(expl, Mapping) else {}


def _purchase_evidence_row(row: Mapping[str, Any]) -> bool:
    fact = row.get("merchant_cart_fact_v1")
    if isinstance(fact, Mapping) and _norm(fact.get("kind")) == FACT_KIND_PURCHASED:
        return True
    expl = _explanation(row)
    diag = expl.get("diagnostic") if isinstance(expl.get("diagnostic"), Mapping) else {}
    if diag.get("purchase_truth") is True:
        return True
    if _norm_lower(diag.get("purchase_truth")) in ("true", "1", "yes"):
        return True
    proof = row.get("merchant_proof_surface_v1")
    if isinstance(proof, Mapping):
        for item in proof.get("evidence_items") or []:
            if isinstance(item, Mapping) and _norm(item.get("type")) == "purchase_truth":
                return True
    return False


def _rec_for_group(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    recommendations: Sequence[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    gid = _norm(group.get("group_id"))
    best: Optional[Mapping[str, Any]] = None
    for rec in recommendations:
        if not isinstance(rec, Mapping):
            continue
        if _norm(rec.get("group_id")) != gid:
            continue
        if best is None or int(rec.get("priority") or 0) > int(best.get("priority") or 0):
            best = rec
    for row in group_rows:
        mi = row.get("merchant_intelligence_v1")
        if not isinstance(mi, Mapping):
            continue
        rec = mi.get("recommendation")
        if not isinstance(rec, Mapping):
            continue
        if best is None or int(rec.get("priority") or 0) > int(best.get("priority") or 0):
            best = rec
    return best


def _aggregate_system_did(rows: Sequence[Mapping[str, Any]]) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    for row in rows:
        expl = _explanation(row)
        line = _norm(expl.get("system_did_ar"))
        if line and line not in seen:
            seen.add(line)
            parts.append(line)
    if parts:
        return parts[0] if len(parts) == 1 else " · ".join(parts[:2])
    return ""


def _aggregate_what_happened(rows: Sequence[Mapping[str, Any]]) -> str:
    for row in rows:
        expl = _explanation(row)
        line = _norm(expl.get("what_happened_ar"))
        if line:
            return line
    return ""


def _action_required_label(rec_type: str, *, merchant_needed: bool = False) -> tuple[bool, str]:
    rt = _norm(rec_type)
    if rt == REC_REQUIRED or merchant_needed:
        return True, "نعم — يلزم تدخلك"
    if rt == REC_SUGGESTED:
        return False, "مقترح — راجع إذا رأيت أنه مناسب"
    if rt == REC_WATCH:
        return False, "لا — CartFlow يراقب هذا النمط"
    if rt == REC_NO_ACTION:
        return False, "لا — CartFlow يتابع تلقائياً"
    return False, "لا — CartFlow يتابع تلقائياً"


def _sanitize_merchant_line(text: str) -> str:
    s = _norm(text)
    lower = s.lower()
    for frag in _ROI_FORBIDDEN_FRAGMENTS:
        if frag.lower() in lower:
            return ""
    return s


def _count_phrase(count: int, *, singular: str, plural: str) -> str:
    if count == 1:
        return f"1 {singular}"
    if count == 2:
        return f"2 {singular}"
    if 3 <= count <= 10:
        return f"{count} {plural}"
    return f"{count} {plural}"


def _story_type_for_group(group: Mapping[str, Any]) -> Optional[str]:
    gid = _norm(group.get("group_id"))
    pk = _norm(group.get("pattern_key"))
    if gid == GROUP_REPEATED_HESITATION and pk.startswith("reason:"):
        tag = pk[7:].lower()
        if tag == "price":
            return STORY_PRICE_HESITATION
        if tag == "shipping":
            return STORY_SHIPPING_HESITATION
        return None
    mapping = {
        GROUP_NEEDS_MERCHANT: STORY_NEEDS_MERCHANT,
        GROUP_AWAITING_SEND: STORY_AWAITING_SEND,
        GROUP_WAITING_REPLY: STORY_WAITING_REPLY,
        GROUP_RETURNED: STORY_RETURNED_WITHOUT_PURCHASE,
        GROUP_WAITING_PURCHASE: STORY_RETURNED_WITHOUT_PURCHASE,
        GROUP_COMPLETED: STORY_RECOVERED_PURCHASE,
    }
    return mapping.get(gid)


def _compose_price_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    headline = _count_phrase(count, singular="عميلًا تردّد", plural="عميلًا تردّدوا") + " بسبب السعر."
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow أرسل طمأنة توضّح قيمة المنتج."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "راقب هذا النمط إذا استمر خلال الأيام القادمة."
    action_required, action_line = _action_required_label(_norm((rec or {}).get("recommendation_type")))
    return _story_dict(
        story_type=STORY_PRICE_HESITATION,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="تردد بسبب السعر",
        headline_ar=headline,
        merchant_meaning_ar="قد يشير هذا إلى أن وضوح قيمة المنتج يحتاج انتباهًا.",
        cartflow_action_ar=cartflow,
        observed_result_ar="",
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _compose_shipping_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    headline = _count_phrase(count, singular="عميلًا تردّد", plural="عميلًا تردّدوا") + " بسبب الشحن."
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow أرسل توضيحًا حول الشحن."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "قد تستحق سياسة الشحن المراجعة إذا تكرر النمط."
    action_required, action_line = _action_required_label(_norm((rec or {}).get("recommendation_type")))
    return _story_dict(
        story_type=STORY_SHIPPING_HESITATION,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="تردد بسبب الشحن",
        headline_ar=headline,
        merchant_meaning_ar="تكلفة أو وضوح الشحن قد يؤثر على إكمال الشراء.",
        cartflow_action_ar=cartflow,
        observed_result_ar="",
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _compose_returned_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    headline = (
        _count_phrase(count, singular="عميلًا عاد", plural="عملاء عادوا")
        + " للمتجر بعد الرسالة ولم يكملوا الشراء بعد."
    )
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow أوقف المتابعة مؤقتًا ثم سيواصل إذا لم يتم الشراء."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "لا يلزم إجراء الآن."
    action_required, action_line = _action_required_label(
        _norm((rec or {}).get("recommendation_type")) or REC_WATCH
    )
    observed = _sanitize_merchant_line(_aggregate_what_happened(group_rows))
    return _story_dict(
        story_type=STORY_RETURNED_WITHOUT_PURCHASE,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="عادوا دون شراء",
        headline_ar=headline,
        merchant_meaning_ar="عودة بعد الرسالة تعني اهتمامًا — CartFlow يراقب نافذة الشراء.",
        cartflow_action_ar=cartflow,
        observed_result_ar=observed,
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _compose_recovered_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    purchased = [r for r in group_rows if _purchase_evidence_row(r)]
    count = len(purchased) if purchased else int(group.get("affected_carts") or 0)
    if count < 1:
        return None
    if purchased and len(purchased) < len(group_rows):
        count = len(purchased)
        rows = purchased
    else:
        rows = list(group_rows)
        if not any(_purchase_evidence_row(r) for r in rows):
            return None
    headline = (
        _count_phrase(count, singular="عميلًا عاد وأكمل", plural="عميلًا عادوا وأكملوا")
        + " الشراء."
    )
    cartflow = _sanitize_merchant_line(_aggregate_system_did(rows))
    if not cartflow:
        cartflow = "CartFlow أوقف المتابعة حتى لا يزعج العملاء."
    recommendation = _norm((rec or {}).get("merchant_message_ar")) or "لا يلزم إجراء."
    action_required, action_line = _action_required_label(REC_NO_ACTION)
    return _story_dict(
        story_type=STORY_RECOVERED_PURCHASE,
        group=group,
        group_rows=rows,
        rec=rec,
        title_ar="اكتملت مشتريات",
        headline_ar=headline,
        merchant_meaning_ar="مسارات اكتملت بنجاح — CartFlow يحافظ على تجربة العميل.",
        cartflow_action_ar=cartflow,
        observed_result_ar="تم إيقاف المتابعة بعد الشراء.",
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _compose_needs_merchant_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    if count == 1:
        headline = "عميل واحد يحتاج تدخلك الشخصي."
    elif count == 2:
        headline = "عميلان يحتاجان تدخلك الشخصي."
    else:
        headline = f"{count} عملاء يحتاجون تدخلك الشخصي."
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow وصل إلى مرحلة يكون فيها ردك المباشر أفضل من المتابعة التلقائية."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "راجع هذه الحالات أولًا."
    action_required, action_line = _action_required_label(REC_REQUIRED, merchant_needed=True)
    return _story_dict(
        story_type=STORY_NEEDS_MERCHANT,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="يحتاج تدخلك",
        headline_ar=headline,
        merchant_meaning_ar="هذه الحالات تستفيد من تواصلك المباشر أكثر من الأتمتة.",
        cartflow_action_ar=cartflow,
        observed_result_ar="",
        recommendation_ar=recommendation,
        action_required=True,
        merchant_action_line=action_line,
    )


def _compose_awaiting_send_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    headline = (
        _count_phrase(count, singular="سلة جاهزة", plural="سلال جاهزة")
        + " وبانتظار أول رسالة استرجاع."
    )
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow جهّز المسار — لم يُؤكَّد إرسال من المزود بعد."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "لا يلزم إجراء الآن — سيتابع CartFlow تلقائيًا."
    action_required, action_line = _action_required_label(REC_NO_ACTION)
    return _story_dict(
        story_type=STORY_AWAITING_SEND,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="بانتظار الإرسال",
        headline_ar=headline,
        merchant_meaning_ar="البيانات مكتملة — لم تُثبت رسالة مُرسلة عبر المزود بعد.",
        cartflow_action_ar=cartflow,
        observed_result_ar="",
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _compose_waiting_reply_story(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    count = int(group.get("affected_carts") or len(group_rows) or 0)
    if count < 1:
        return None
    headline = (
        _count_phrase(count, singular="عميلًا تلقى", plural="عميلًا تلقوا")
        + " رسالة CartFlow وينتظرون الرد."
    )
    cartflow = _sanitize_merchant_line(_aggregate_system_did(group_rows))
    if not cartflow:
        cartflow = "CartFlow سيتابع تلقائيًا حسب المسار المحدد."
    rec_msg = _norm((rec or {}).get("merchant_message_ar"))
    recommendation = rec_msg or "لا يلزم إجراء الآن."
    action_required, action_line = _action_required_label(REC_NO_ACTION)
    return _story_dict(
        story_type=STORY_WAITING_REPLY,
        group=group,
        group_rows=group_rows,
        rec=rec,
        title_ar="بانتظار رد العميل",
        headline_ar=headline,
        merchant_meaning_ar="CartFlow يتابع المحادثة — لا حاجة للانتظار السلبي.",
        cartflow_action_ar=cartflow,
        observed_result_ar="",
        recommendation_ar=recommendation,
        action_required=action_required,
        merchant_action_line=action_line,
    )


def _story_dict(
    *,
    story_type: str,
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
    title_ar: str,
    headline_ar: str,
    merchant_meaning_ar: str,
    cartflow_action_ar: str,
    observed_result_ar: str,
    recommendation_ar: str,
    action_required: bool,
    merchant_action_line: str,
) -> dict[str, Any]:
    gid = _norm(group.get("group_id"))
    pk = _norm(group.get("pattern_key"))
    story_id = f"{story_type}:{gid}:{pk or 'op'}"
    evidence_ids: list[str] = []
    for eid in group.get("evidence_ids") or []:
        s = _norm(eid)
        if s and s not in evidence_ids:
            evidence_ids.append(s)
    for row in group_rows:
        expl = _explanation(row)
        for eid in expl.get("evidence_ids") or []:
            s = _norm(eid)
            if s and s not in evidence_ids:
                evidence_ids.append(s)
    rec_ids: list[str] = []
    if rec:
        rid = _norm(rec.get("recommendation_id"))
        if rid:
            rec_ids.append(rid)
    if not headline_ar or not cartflow_action_ar:
        return {}
    return {
        "story_id": story_id,
        "story_type": story_type,
        "title_ar": title_ar,
        "headline_ar": headline_ar,
        "merchant_meaning_ar": merchant_meaning_ar,
        "cartflow_action_ar": cartflow_action_ar,
        "observed_result_ar": observed_result_ar,
        "recommendation_ar": recommendation_ar,
        "merchant_action_line_ar": merchant_action_line,
        "action_required": bool(action_required),
        "confidence": _norm(group.get("confidence")) or "medium",
        "evidence_ids": evidence_ids,
        "source_group_ids": [gid] if gid else [],
        "source_recommendation_ids": rec_ids,
        "pattern_key": pk or None,
        "affected_cart_keys": [_recovery_key(r) for r in group_rows if _recovery_key(r)],
        "affected_carts": len(group_rows),
        "eligible_surfaces": list(group.get("eligible_surfaces") or [SURFACE_CARTS]),
        "display_priority": int(group.get("priority") or 0),
        "diagnostics_internal": {
            "composition_reason": f"composed_from_{gid or pk}",
            "group_creation_reason": _norm(group.get("creation_reason")),
            "authority": AUTHORITY,
        },
    }


def _compose_story_for_group(
    group: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    rec: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    story_type = _story_type_for_group(group)
    if not story_type:
        return None
    composers = {
        STORY_PRICE_HESITATION: _compose_price_story,
        STORY_SHIPPING_HESITATION: _compose_shipping_story,
        STORY_RETURNED_WITHOUT_PURCHASE: _compose_returned_story,
        STORY_RECOVERED_PURCHASE: _compose_recovered_story,
        STORY_NEEDS_MERCHANT: _compose_needs_merchant_story,
        STORY_AWAITING_SEND: _compose_awaiting_send_story,
        STORY_WAITING_REPLY: _compose_waiting_reply_story,
    }
    composer = composers.get(story_type)
    if not composer:
        return None
    story = composer(group, group_rows, rec)
    if not story:
        return None
    if not story.get("evidence_ids") and not story.get("affected_cart_keys"):
        return None
    return story


def build_merchant_value_stories_v1(
    rows: Sequence[Mapping[str, Any]],
    store_mi: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose merchant value stories from governed MI store bundle + rows."""
    groups = list(store_mi.get("groups") or [])
    recommendations = list(store_mi.get("recommendations") or [])
    memory = list(store_mi.get("memory") or [])
    rows_by_key = _rows_by_recovery_key(rows)

    raw_stories: list[dict[str, Any]] = []
    seen_types: set[str] = set()

    for group in groups:
        if not isinstance(group, Mapping):
            continue
        gid = _norm(group.get("group_id"))
        pk = _norm(group.get("pattern_key"))
        story_type = _story_type_for_group(group)
        if not story_type:
            continue
        dedupe_key = f"{story_type}:{pk or gid}"
        if dedupe_key in seen_types and story_type in (
            STORY_PRICE_HESITATION,
            STORY_SHIPPING_HESITATION,
        ):
            continue
        group_rows = _group_rows(group, rows_by_key)
        if not group_rows and int(group.get("affected_carts") or 0) < 1:
            continue
        rec = _rec_for_group(group, group_rows, recommendations)
        story = _compose_story_for_group(group, group_rows, rec)
        if story:
            for beat in memory:
                if not isinstance(beat, Mapping):
                    continue
                ev = beat.get("evidence") if isinstance(beat.get("evidence"), Mapping) else {}
                if _norm(ev.get("group_id")) == gid and not story.get("observed_result_ar"):
                    finding = _sanitize_merchant_line(_norm(beat.get("finding_ar")))
                    if finding:
                        story["observed_result_ar"] = finding
            raw_stories.append(story)
            seen_types.add(dedupe_key)

    def _sort_key(s: Mapping[str, Any]) -> tuple[int, int]:
        st = _norm(s.get("story_type"))
        try:
            type_rank = _STORY_TYPE_ORDER.index(st)
        except ValueError:
            type_rank = len(_STORY_TYPE_ORDER)
        return (type_rank, -int(s.get("display_priority") or 0))

    stories = sorted(raw_stories, key=_sort_key)

    return {
        "version": VALUE_VERSION,
        "authority": AUTHORITY,
        "stories": stories,
        "observability": {
            "stories_composed": len(stories),
            "groups_considered": len(groups),
            "authority": AUTHORITY,
            "reviewable": True,
        },
    }


def attach_merchant_value_stories_v1(
    target: Mapping[str, Any] | dict[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    store_mi: Optional[Mapping[str, Any]] = None,
) -> None:
    if not isinstance(target, dict):
        return
    store = store_mi if isinstance(store_mi, Mapping) else target.get("merchant_intelligence_store_v1")
    if not isinstance(store, Mapping):
        return
    target["merchant_value_stories_v1"] = build_merchant_value_stories_v1(rows, store)


def ensure_normal_carts_merchant_value_stories_v1(
    payload: Mapping[str, Any] | dict[str, Any],
) -> None:
    """Normal-carts transport — value stories after MI store bundle."""
    if not isinstance(payload, dict):
        return
    rows = list(payload.get("merchant_carts_page_rows") or [])
    if not isinstance(payload.get("merchant_intelligence_store_v1"), Mapping):
        from services.merchant_intelligence_v1 import (  # noqa: PLC0415
            ensure_normal_carts_merchant_intelligence_store_v1,
        )

        ensure_normal_carts_merchant_intelligence_store_v1(payload)
    attach_merchant_value_stories_v1(payload, rows)


def validate_merchant_value_story_v1(story: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "story_id",
        "story_type",
        "title_ar",
        "headline_ar",
        "merchant_meaning_ar",
        "cartflow_action_ar",
        "recommendation_ar",
        "action_required",
        "confidence",
        "evidence_ids",
        "source_group_ids",
        "eligible_surfaces",
        "display_priority",
    )
    for key in required:
        if key not in story:
            errors.append(f"missing {key}")
    for field in ("title_ar", "headline_ar", "merchant_meaning_ar", "cartflow_action_ar"):
        val = _norm(story.get(field))
        if not val:
            errors.append(f"empty {field}")
        for forbidden in ("group_key", "reason_tag", "waiting_first_send", "lifecycle_state"):
            if forbidden in val.lower():
                errors.append(f"forbidden token in {field}")
    headline = _norm(story.get("headline_ar"))
    if headline and not _sanitize_merchant_line(headline):
        errors.append("roi claim blocked in headline")
    return errors


__all__ = [
    "AUTHORITY",
    "STORY_AWAITING_SEND",
    "STORY_NEEDS_MERCHANT",
    "STORY_PRICE_HESITATION",
    "STORY_RECOVERED_PURCHASE",
    "STORY_RETURNED_WITHOUT_PURCHASE",
    "STORY_SHIPPING_HESITATION",
    "STORY_WAITING_REPLY",
    "VALUE_VERSION",
    "attach_merchant_value_stories_v1",
    "build_merchant_value_stories_v1",
    "ensure_normal_carts_merchant_value_stories_v1",
    "validate_merchant_value_story_v1",
]
